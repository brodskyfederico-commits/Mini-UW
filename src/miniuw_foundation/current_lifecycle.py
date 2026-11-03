"""T61 explicit-time complete-source gate for the declared purchase-to-sale return."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .lifecycle_returns import LifecycleReturnRun,assemble_lifecycle_returns
from .evidence_currency import EvidenceCurrencyRun,evaluate_evidence_currency

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T61-T62.md'


def required_lifecycle_sources(arguments):
    if type(arguments)is not tuple or len(arguments)!=6:raise ValidationError('complete immutable lifecycle arguments required')
    opening,_,capacity,_,investor,binding=arguments
    if type(opening)is not tuple or len(opening)!=8 or type(capacity)is not tuple or len(capacity)!=9:raise ValidationError('complete opening/capacity transport required')
    rows=[]
    def add(path,raw):
        if type(raw)is not bytes:raise ValidationError('exact source transport bytes required')
        rows.append(dict(requirement_id=path,source_sha256=hashlib.sha256(raw).hexdigest(),source_locator=path))
    def loan(path,e):
        add(path+'/terms',e.loan_raw);add(path+'/windows_record',canonical([asdict(w)for w in e.windows]).encode())
    def project(prefix,periods,closings,manifest):
        for i,e in enumerate(periods):add(prefix+'/periods/'+str(i)+'/noi',e.noi_raw);add(prefix+'/periods/'+str(i)+'/cash',e.spec_raw)
        for i,e in enumerate(closings):
            path=prefix+'/closings/'+str(i);add(path+'/cash',e.closing_raw);add(path+'/debt_spec',e.debt_spec_raw)
            for j,l in enumerate(e.loans):loan(path+'/loans/'+str(j),l)
        add(prefix+'/manifest',manifest)
    add('/opening/preopening_cash',opening[0]);add('/opening/cash_boundary_binding',opening[6]);add('/opening/debt_spec',opening[7])
    project('/opening/project',opening[2],opening[3],opening[4]);project('/window/project',capacity[0],capacity[1],capacity[2])
    inputs=capacity[4]
    for name,value in [('valuation_noi',inputs.valuation_noi_raw),('bank_noi',inputs.bank_noi_raw),('closing',inputs.closing_raw),('spec',capacity[5])]:add('/capacity/'+name,value)
    loan('/capacity/new_loan',inputs.new_loan)
    add('/window/investor',capacity[7]);add('/window/binding_record',canonical(asdict(capacity[8])).encode())
    add('/lifecycle/investor',investor);add('/lifecycle/binding',binding)
    if len(rows)>256:raise ValidationError('current lifecycle source-binding budget exceeded')
    return rows


@dataclass(frozen=True)
class CurrentLifecycleRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_lifecycle(arguments,base_run,registry_raw,registry_run,as_of):
    if type(arguments)is not tuple or len(arguments)!=6 or type(base_run)is not LifecycleReturnRun or assemble_lifecycle_returns(*arguments)!=base_run:raise ValidationError('complete historical lifecycle must reproduce')
    if type(registry_run)is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw,as_of)!=registry_run:raise ValidationError('registry must reproduce at exact declared UTC instant')
    p=base_run.payload;r=registry_run.payload;required=required_lifecycle_sources(arguments);blockers=[];story=None
    supplied=[row['requirement']for row in r['requirements']]
    if sorted(required,key=lambda x:x['requirement_id'])!=sorted(supplied,key=lambda x:x['requirement_id']):blockers.append('complete_lifecycle_source_binding_inventory_mismatch')
    if r['context']!=p['context']:blockers.append('registry_lifecycle_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('required_lifecycle_evidence_not_current')
    if p['state']!='compiled_synthetic_purchase_to_sale':blockers.append('historical_lifecycle_calculation_blocked')
    if not blockers:
        investor=base_run.investor_run.payload
        story={k:investor[k]for k in ['currency','gross_contributions','gross_distributions','net_cash_profit','equity_multiple','cash_by_category','cash_horizon','normalized_story','capital_snapshots','annual_cash_receipts','periodic_irr','annual_irr_roots']}
        story.update(equity_level='aggregate_project_equity',dated_events=investor['events'],upstream_story_blockers=investor['story_blockers'],selected_IRR=None,
            risk_observations=json.loads(p['cash_risk_run']['payload_json'])['metrics'],opening_debt_checks=arguments[1].payload['loan_checks'],personal_investor_return=None,decision='PENDING')
    result={'component':'T61','purpose':'synthetic_current_declared_purchase_to_sale_output','engine_sha256':ENGINE_SHA256,
        'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),'lifecycle_run_sha256':base_run.sha256,'registry_source_sha256':hashlib.sha256(registry_raw).hexdigest(),'registry_run_sha256':registry_run.sha256,
        'context':p['context'],'currency':p['currency'],'evaluated_as_of_UTC':as_of,'required_source_bindings':required,
        'state':'current_synthetic_lifecycle_at_declared_time'if story is not None else'PENDING','current_project_return_story':story,
        'blockers':sorted(set(blockers)),'evidence_blockers':r['blockers'],'calculation_blockers':p['blockers'],
        'opening_debt_blockers':arguments[1].payload['blockers'],'bank_capacity_blockers':arguments[3].payload['capacity_blockers'],
        'historical_calculation_preserved':True,'real_source_or_review_authentication':False,'live_expiry_monitor_enabled':False,
        'financial_publication_authorized':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return CurrentLifecycleRun(encoded,digest(encoded))
