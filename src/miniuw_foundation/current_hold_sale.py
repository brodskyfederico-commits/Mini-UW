"""T67 explicit-time source gate and internal review for recovered hold/sale evidence."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .hold_sale_bundle import recover_hold_sale_bundle
from .evidence_currency import EvidenceCurrencyRun,evaluate_evidence_currency
from .investor_review import _render,ENGINE_SHA256 as PRESENTATION_ENGINE_SHA256

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T66-T67.md'


def required_hold_sale_sources(recovered,bundle_raw):
    a=recovered.opening_args;rows=[]
    def add(path,raw):
        if type(raw)is not bytes:raise ValidationError('exact source bytes required')
        rows.append(dict(requirement_id=path,source_sha256=hashlib.sha256(raw).hexdigest(),source_locator=path))
    for path,value in [('/transport/bundle',bundle_raw),('/preopening/cash',a[0]),('/holding/manifest',a[4]),('/holding/sale_binding',a[6]),('/opening/cash_binding',a[8]),('/opening/debt_binding',a[9]),('/investor/source',recovered.investor_raw),('/investor/binding',recovered.binding_raw)]:add(path,value)
    for i,p in enumerate(a[2]):add('/holding/periods/'+str(i)+'/noi',p.noi_raw);add('/holding/periods/'+str(i)+'/cash',p.spec_raw)
    sale=a[3];add('/sale/cash',sale.closing_raw);add('/sale/debt_binding',sale.debt_spec_raw)
    for i,e in enumerate(sale.loans):
        add('/sale/loans/'+str(i)+'/terms',e.loan_raw);add('/sale/loans/'+str(i)+'/windows_record',canonical([asdict(w)for w in e.windows]).encode())
    if len(rows)>256:raise ValidationError('hold/sale current source inventory budget exceeded')
    return rows


@dataclass(frozen=True)
class CurrentHoldSaleRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_hold_sale(bundle_raw,registry_raw,registry_run,as_of):
    recovered=recover_hold_sale_bundle(bundle_raw);base=recovered.run;p=base.payload
    if type(registry_run)is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw,as_of)!=registry_run:raise ValidationError('hold/sale source registry must reproduce at exact supplied UTC instant')
    r=registry_run.payload;required=required_hold_sale_sources(recovered,bundle_raw);supplied=[e['requirement']for e in r['requirements']];blockers=[];story=None
    if sorted(required,key=lambda e:e['requirement_id'])!=sorted(supplied,key=lambda e:e['requirement_id']):blockers.append('complete_hold_sale_source_binding_inventory_mismatch')
    if r['context']!=p['context']:blockers.append('hold_sale_registry_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('hold_sale_evidence_not_current')
    if p['state']!='compiled_synthetic_no_refinance_return':blockers.append('hold_sale_calculation_blocked')
    if not blockers:
        inv=base.investor_run.payload;story={k:inv[k]for k in ['currency','gross_contributions','gross_distributions','net_cash_profit','equity_multiple','cash_by_category','cash_horizon','normalized_story','capital_snapshots','annual_cash_receipts','periodic_irr','annual_irr_roots']}
        story.update(equity_level='aggregate_project_equity',dated_events=inv['events'],upstream_story_blockers=inv['story_blockers'],selected_IRR=None,risk_observations=json.loads(p['cash_risk_run']['payload_json'])['metrics'],personal_investor_return=None,decision='PENDING')
    row={'case_id':'Compra, tenencia y venta sin refinanciación: caso sintético independiente','state':'current_synthetic_hold_sale_at_declared_time'if story is not None else'PENDING',
        'current_matched_case':None if story is None else{'candidate_project_return_story':story},'blockers':blockers,'comparison_blockers':[],
        'reference_evidence_blockers':[],'candidate_evidence_blockers':r['blockers'],'reference_calculation_blockers':[],
        'candidate_calculation_blockers':p['blockers']+p['opening_blockers']+p['hold_sale_blockers']+p['sale_debt_blockers'],
        'reference_original_cost_blockers':[],'candidate_original_cost_blockers':[]}
    markdown=_render(dict(evaluated_as_of_UTC=as_of,blockers=[],case_rows=[row]))
    result={'component':'T67','purpose':'synthetic_current_no_refinance_return_and_internal_review','engine_sha256':ENGINE_SHA256,'presentation_engine_sha256':PRESENTATION_ENGINE_SHA256,
        'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),'bundle_sha256':recovered.bundle_sha256,'historical_run_sha256':base.sha256,
        'registry_source_sha256':hashlib.sha256(registry_raw).hexdigest(),'registry_run_sha256':registry_run.sha256,'evaluated_as_of_UTC':as_of,'context':p['context'],'currency':p['currency'],
        'required_source_bindings':required,'current_project_return_story':story,'markdown':markdown,'markdown_sha256':digest(markdown),'state':row['state'],
        'blockers':sorted(set(blockers)),'evidence_blockers':r['blockers'],'calculation_blockers':row['candidate_calculation_blockers'],
        'historical_calculation_preserved':True,'live_expiry_monitor_enabled':False,'source_or_review_authority_authenticated':False,
        'financial_publication_authorized':False,'external_decision_pdf_produced':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return CurrentHoldSaleRun(encoded,digest(encoded))
