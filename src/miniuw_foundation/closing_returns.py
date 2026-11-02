"""T30 bind one conditional closing to separate empty gross equity events."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .closing_cash import ClosingCashRun,produce_closing_cash
from .investor_returns import parse_investor_returns,produce_investor_returns,InvestorReturnsRun
from .debt_service import _fraction
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class ClosingReturnBinding:
    profile_id:str
    closing_source_sha256:str
    closing_run_sha256:str
    investor_source_sha256:str
    distribution_event_id:str
    contribution_event_id:str|None
    def __post_init__(self):
        if self.profile_id!='SYNTHETIC-CLOSING-EMPTY-EQUITY-SLOTS-v1':raise ValidationError('explicit conditional closing empty-slot profile required')
        for key in ['closing_source_sha256','closing_run_sha256','investor_source_sha256']:
            value=getattr(self,key)
            if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact source/run SHA-256 required')
        nonempty(self.distribution_event_id,'distribution_event_id')
        if self.contribution_event_id is not None:nonempty(self.contribution_event_id,'contribution_event_id')
        if self.contribution_event_id==self.distribution_event_id:raise ValidationError('gross equity events must be distinct')


@dataclass(frozen=True)
class ClosingReturnRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def compiled_raw(self):
        s=self.payload['compiled_investor_json'];return None if s is None else s.encode()
    @property
    def investor_run(self):
        p=self.payload['investor_run'];return None if p is None else InvestorReturnsRun(**p)


def assemble_closing_returns(closing_raw,closing_run,investor_raw,binding):
    if type(binding)is not ClosingReturnBinding:raise ValidationError('explicit closing/investor binding required')
    if type(closing_run)is not ClosingCashRun or produce_closing_cash(closing_raw)!=closing_run:raise ValidationError('closing source and exact producer run must reproduce')
    source=parse_investor_returns(investor_raw);c=closing_run.payload;blockers=[];compiled=None;run=None;changes=[]
    for key,actual in [('closing_source_sha256',c['source_sha256']),('closing_run_sha256',closing_run.sha256),('investor_source_sha256',hashlib.sha256(investor_raw).hexdigest())]:
        if getattr(binding,key)!=actual:blockers.append(key+'_mismatch')
    if c['state']!='computed_synthetic_closing':blockers.append('closing_plan_blocked')
    if source['context']!=c['context']:blockers.append('investor_closing_context_mismatch')
    if source['currency']!=c['currency']:blockers.append('investor_closing_currency_mismatch')
    if c['closing_date']not in source['grid']['dates']:blockers.append('closing_date_not_bound_to_investor_grid')
    distribution_category='net_refinance_distribution'if c['kind']=='refinance'else'net_sale_distribution'
    contribution_category='refinance_cash_in'if c['kind']=='refinance'else'additional_capital'
    targets=[(binding.distribution_event_id,'distribution',distribution_category,'exportable_equity_distribution')]
    if binding.contribution_event_id is not None:targets.append((binding.contribution_event_id,'contribution',contribution_category,'exportable_equity_contribution'))
    elif c['exportable_equity_contribution']is not None and _fraction(c['exportable_equity_contribution'],1300)>0:blockers.append('cash_in_requires_explicit_gross_contribution_slot')
    events={e['event_id']:e for e in source['events']}
    for eid,kind,category,field in targets:
        e=events.get(eid)
        if e is None:blockers.append(eid+':target_event_missing');continue
        if e['kind']!=kind or e['category']!=category:blockers.append(eid+':wrong_closing_equity_classification')
        if e['date']!=c['closing_date']:blockers.append(eid+':closing_date_mismatch')
        if e['currency']!=c['currency']:blockers.append(eid+':currency_mismatch')
        if e['amount']is not None:blockers.append(eid+':target_not_empty_no_implicit_override')
    if not blockers:
        for eid,kind,category,field in targets:
            e=events[eid];before=json.loads(canonical(e));e['amount']=c[field];e['source_ref']='miniuw:closing-cash:'+closing_run.sha256+'#/'+field
            changes.append({'event_id':eid,'before':before,'after':json.loads(canonical(e)),'closing_output_pointer':'/'+field})
        compiled=canonical(source)
        try:run=produce_investor_returns(compiled.encode())
        except ValidationError:compiled=None;blockers.append('compiled_investor_source_outside_consumer_contract')
    p={'component':'T30','purpose':'synthetic_conditional_closing_to_investor_returns','engine_sha256':ENGINE_SHA256,
        'binding':asdict(binding),'closing_run_sha256':closing_run.sha256,'context':c['context'],
        'original_investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),'compiled_investor_json':compiled,
        'compiled_investor_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),
        'investor_run':None if run is None else asdict(run),'changes':changes,'blockers':sorted(set(blockers)),'closing_blockers':c['blockers'],
        'state':'compiled_synthetic'if compiled is not None else'blocked','closing_producer_replayed':True,
        'original_source_overwritten':False,'whole_project_cash_reconciled':False,'whole_investor_story_complete':False,
        'equity_funding_available_verified':False,'distribution_authorized':False,'financial_module_closed':False,
        'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return ClosingReturnRun(encoded,digest(encoded))
