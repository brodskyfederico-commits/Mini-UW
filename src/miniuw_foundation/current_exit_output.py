"""T47 opt-in complete transport-source currency gate around replayed T44 output."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .costed_exit_sale import CostedExitSaleRun,assemble_costed_exit_sale
from .evidence_currency import EvidenceCurrencyRun,evaluate_evidence_currency

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T46-T47.md'


def required_exit_sources(arguments):
    if type(arguments)is not tuple or len(arguments)!=8:raise ValidationError('complete immutable T44 arguments required')
    e,nr,_,vr,_,cr,_,br=arguments
    rows=[]
    def add(locator,raw):
        if type(raw)is not bytes:raise ValidationError('source bytes required')
        rows.append(dict(requirement_id=locator,source_sha256=hashlib.sha256(raw).hexdigest(),source_locator=locator))
    for i,p in enumerate(e.periods):
        add('/project/periods/'+str(i)+'/noi',p.noi_raw);add('/project/periods/'+str(i)+'/cash',p.spec_raw)
    for i,c in enumerate(e.closings):
        add('/project/closings/'+str(i)+'/cash',c.closing_raw);add('/project/closings/'+str(i)+'/debt_binding',c.debt_spec_raw)
        for j,loan in enumerate(c.loans):add('/project/closings/'+str(i)+'/loans/'+str(j),loan.loan_raw)
    add('/project/manifest',e.manifest_raw);add('/project/investor_slots',e.investor_raw)
    inputs=e.capacity_inputs
    for name,raw in [('valuation_noi',inputs.valuation_noi_raw),('bank_noi',inputs.bank_noi_raw),('new_loan',inputs.new_loan.loan_raw),('closing',inputs.closing_raw),('spec',e.capacity_spec_raw)]:add('/capacity/'+name,raw)
    for name,raw in [('forward_noi',nr),('value_spec',vr),('cost_inventory',cr),('bridge_spec',br)]:add('/exit/'+name,raw)
    return rows


@dataclass(frozen=True)
class CurrentExitOutputRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_exit_output(arguments,base_run,registry_raw,registry_run,as_of):
    if type(arguments)is not tuple or len(arguments)!=8 or type(base_run)is not CostedExitSaleRun:raise ValidationError('typed complete costed-exit source/run required')
    if assemble_costed_exit_sale(*arguments)!=base_run:raise ValidationError('entire costed exit source/run must reproduce')
    if type(registry_run)is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw,as_of)!=registry_run:raise ValidationError('evidence registry must reproduce at exact evaluation time')
    p=base_run.payload;r=registry_run.payload;blockers=[];output=None
    required=required_exit_sources(arguments)
    supplied=[row['requirement']for row in r['requirements']]
    # Order is immaterial; missing/extra identities or any changed alias/hash/locator block.
    if sorted(required,key=lambda x:x['requirement_id'])!=sorted(supplied,key=lambda x:x['requirement_id']):blockers.append('complete_exit_source_binding_inventory_mismatch')
    if r['context']!=arguments[4].payload['context']:blockers.append('evidence_and_exit_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('required_evidence_not_current')
    if p['state']!='compiled_synthetic':blockers.append('guarded_calculation_blocked')
    if not blockers:
        investor=base_run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload
        output={'equity_level':'aggregate_project_equity','gross_contributions':investor['gross_contributions'],
            'gross_distributions':investor['gross_distributions'],'net_cash_profit':investor['net_cash_profit'],
            'equity_multiple':investor['equity_multiple'],'annual_irr_roots':investor['annual_irr_roots'],
            'selected_IRR':None,'upstream_story_blockers':investor['story_blockers'],
            'personal_investor_return':None,'decision':'PENDING'}
        for key in ['currency','cash_horizon','cash_by_category','normalized_story','capital_snapshots','annual_cash_receipts','periodic_irr']:
            output[key]=investor[key]
        output['dated_events']=investor['events']
        risk=base_run.exit_sale_run.sale_revision_run.payload['risk_run']
        output['risk_observations']=None if risk is None else json.loads(risk['payload_json'])['metrics']
    payload={'component':'T47','purpose':'synthetic_current_evidence_exit_output_gate',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'base_costed_run_sha256':base_run.sha256,'registry_source_sha256':hashlib.sha256(registry_raw).hexdigest(),
        'registry_run_sha256':registry_run.sha256,'evaluated_as_of_UTC':as_of,'required_source_bindings':required,
        'context':arguments[4].payload['context'],'currency':arguments[4].payload['currency'],
        'state':'current_synthetic_output_at_declared_time'if output is not None else'PENDING',
        'current_project_return_summary':output,'blockers':sorted(set(blockers)),
        'calculation_blockers':p['blockers'],'evidence_blockers':r['blockers'],
        'historical_calculation_preserved':True,'all_external_document_sources_authenticated':False,
        'professional_review_authenticated':False,'live_expiry_monitor_enabled':False,
        'financial_publication_authorized':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(payload);return CurrentExitOutputRun(encoded,digest(encoded))


def verify_current_exit_output(arguments,base_run,registry_raw,registry_run,as_of,report):
    if type(report)is not CurrentExitOutputRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed current-output result with matching hash required')
    if assemble_current_exit_output(arguments,base_run,registry_raw,registry_run,as_of)!=report:raise ValidationError('current output report replay mismatch')
    return report
