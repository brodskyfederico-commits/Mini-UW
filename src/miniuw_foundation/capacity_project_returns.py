"""T36 optional bank-capacity guard around the complete synthetic cash-window path."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .refinance_capacity import RefinanceInputs,RefinanceCapacityRun,size_refinance
from .project_cash import ProjectCashRun,reconcile_project_cash
from .project_returns import ProjectReturnBinding,ProjectReturnRun,assemble_project_returns,binding_from_record as project_binding_from_record
from .investor_returns import parse_investor_returns
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class CapacityProjectBinding:
    profile_id:str
    capacity_spec_sha256:str
    capacity_run_sha256:str
    refinance_node_id:str
    project_return_binding:ProjectReturnBinding
    def __post_init__(self):
        if self.profile_id!='SYNTHETIC-CAPACITY-CHECKED-PROJECT-RETURN-v1':raise ValidationError('explicit capacity-checked project profile required')
        for key in ['capacity_spec_sha256','capacity_run_sha256']:
            value=getattr(self,key)
            if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact capacity source/run SHA-256 required')
        nonempty(self.refinance_node_id,'refinance_node_id')
        if type(self.project_return_binding)is not ProjectReturnBinding:raise ValidationError('typed exact cash-window investor binding required')


def binding_from_record(p):
    if type(p)is not dict or set(p)!={'profile_id','capacity_spec_sha256','capacity_run_sha256','refinance_node_id','project_return_binding'}:raise ValidationError('exact archived capacity project binding required')
    return CapacityProjectBinding(**dict(p,project_return_binding=project_binding_from_record(p['project_return_binding'])))


@dataclass(frozen=True)
class CapacityProjectReturnRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def project_return_run(self):
        p=self.payload['project_return_run'];return None if p is None else ProjectReturnRun(**p)
    @property
    def compiled_raw(self):
        r=self.project_return_run;return None if r is None else r.compiled_raw
    @property
    def investor_run(self):
        r=self.project_return_run;return None if r is None else r.investor_run


def assemble_capacity_checked_returns(periods,closings,manifest_raw,project_run,inputs,spec_raw,capacity_run,investor_raw,binding):
    if type(binding)is not CapacityProjectBinding:raise ValidationError('explicit typed capacity project binding required')
    parse_investor_returns(investor_raw)
    if type(project_run)is not ProjectCashRun or reconcile_project_cash(periods,closings,manifest_raw)!=project_run:raise ValidationError('all project NOI/cash/debt/closing sources must reproduce')
    if type(capacity_run)is not RefinanceCapacityRun or size_refinance(inputs,spec_raw)!=capacity_run:raise ValidationError('entire refinance sizing branch must reproduce')
    p=project_run.payload;c=capacity_run.payload;blockers=[];underlying=None
    if binding.capacity_spec_sha256!=hashlib.sha256(spec_raw).hexdigest():blockers.append('capacity_spec_sha256_mismatch')
    if binding.capacity_run_sha256!=capacity_run.sha256:blockers.append('capacity_run_sha256_mismatch')
    if p['state']!='reconciled_synthetic_cash_window':blockers.append('project_cash_window_blocked')
    if c['state']!='compatible_synthetic_refinance_capacity':blockers.append('refinance_capacity_or_selection_blocked')
    node=next((n for n in p['nodes']if n['node_id']==binding.refinance_node_id),None)
    if node is None or node['kind']!='refinance':blockers.append('exact_refinance_node_not_identified')
    else:
        if node['source_sha256']!=c['input_bindings']['closing_source_sha256']or node['run_sha256']!=c['input_bindings']['closing_run_sha256']:blockers.append('sizing_closing_source_or_run_does_not_match_cash_refinance_node')
        if node['equity_cash_date']!=c['as_of_date']:blockers.append('sizing_date_does_not_match_project_refinance')
    if p['context']!=c['context']or p['currency']!=c['currency']:blockers.append('project_and_sizing_context_or_currency_mismatch')
    # The permanent loan used later at sale must have the exact same terms/window run.
    candidates=[e for close in closings for e in close.loans if e.run.payload['loan_id']==inputs.new_loan.run.payload['loan_id']]
    if len(candidates)!=1 or hashlib.sha256(candidates[0].loan_raw).hexdigest()!=c['input_bindings']['new_loan_source_sha256']or candidates[0].run.sha256!=c['input_bindings']['new_loan_run_sha256']:blockers.append('capacity_loan_source_and_run_do_not_match_project_permanent_loan')
    if not blockers:
        underlying=assemble_project_returns(periods,closings,manifest_raw,project_run,investor_raw,binding.project_return_binding);blockers.extend(underlying.payload['blockers'])
    result={'component':'T36','purpose':'synthetic_capacity_checked_integrated_cash_return','engine_sha256':ENGINE_SHA256,'binding':asdict(binding),'project_run_sha256':project_run.sha256,'capacity_run_sha256':capacity_run.sha256,
        'original_investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),'project_return_run':None if underlying is None else asdict(underlying),'blockers':sorted(set(blockers)),'capacity_blockers':c['blockers'],'project_cash_blockers':p['blockers'],
        'state':'compiled_synthetic'if underlying is not None and underlying.compiled_raw is not None and not blockers else'blocked','all_sources_replayed':True,'original_source_overwritten':False,
        'bank_credit_approved':False,'funds_available_verified':False,'bank_policy_adopted':False,'whole_project_cash_reconciled':False,'distribution_authorized':False,'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(result);return CapacityProjectReturnRun(encoded,digest(encoded))
