"""T75 exact-source staged lifecycle recovery and explicit-time internal view."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .intake import _unique_object,_invalid_constant
from . import operating_debt_phase,staged_operating_window,staged_lifecycle_returns,lifecycle_bundle
from .operating_debt_phase import produce_operating_debt_phase
from .staged_operating_window import StagedOperatingWindowRun,reconcile_staged_operating_window
from .staged_lifecycle_returns import StagedLifecycleReturnRun,assemble_staged_lifecycle_returns
from .construction_bundle import recover_construction_bundle
from .lifecycle_bundle import _shape,_list,_bytes,_loan_record,_loan,MAX_BYTES
from .operating_noi import produce_operating_noi
from .operating_cash import reconcile_operating_cash
from .holding_cash import OperatingPeriodEvidence,reconcile_holding_cash
from .closing_cash import produce_closing_cash
from .debt_closing import reconcile_debt_closing
from .project_cash import CheckedClosingEvidence
from .hold_sale_cash import reconcile_hold_sale_cash
from .evidence_currency import EvidenceCurrencyRun,evaluate_evidence_currency
from .investor_review import _render,literal,amount,ENGINE_SHA256 as PRESENTATION_ENGINE_SHA256

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T72-T75.md'
def versions():return dict(T72=operating_debt_phase.ENGINE_SHA256,T73=staged_operating_window.ENGINE_SHA256,T74=staged_lifecycle_returns.ENGINE_SHA256,T75=ENGINE_SHA256,transport_utilities=lifecycle_bundle.ENGINE_SHA256,definition=hashlib.sha256(DEFINITION.read_bytes()).hexdigest())
def _nested(value):
    if type(value)is not str:raise ValidationError('nested bundle must be exact UTF-8 text')
    try:b=value.encode()
    except UnicodeError as error:raise ValidationError('invalid nested bundle UTF-8')from error
    if not b or len(b)>MAX_BYTES:raise ValidationError('nested staged bundle budget exceeded')
    return b


def export_staged_lifecycle_bundle(window_args,window_run,investor_raw,binding_raw,run):
    if type(run)is not StagedLifecycleReturnRun or assemble_staged_lifecycle_returns(window_args,window_run,investor_raw,binding_raw)!=run:raise ValidationError('complete staged lifecycle must reproduce before export')
    bundle,phase,_,holding,_,cash_binding,window_spec=window_args;periods,sale,manifest,_,hold_spec=holding
    body=dict(schema='miniuw.synthetic-staged-lifecycle-bundle.v1',versions=versions(),construction_bundle=bundle.decode(),phase_contract=phase.decode(),
        periods=[dict(noi_source=e.noi_raw.decode(),cash_spec=e.spec_raw.decode())for e in periods],
        sale=dict(closing_id=sale.closing_id,closing_source=sale.closing_raw.decode(),loans=[_loan_record(e)for e in sale.loans],debt_spec=sale.debt_spec_raw.decode()),
        holding_manifest=manifest.decode(),hold_sale_spec=hold_spec.decode(),cash_boundary_binding=cash_binding.decode(),window_spec=window_spec.decode(),
        investor_source=investor_raw.decode(),investor_binding=binding_raw.decode(),expected_run=asdict(run))
    raw=canonical(body).encode()
    if len(raw)>MAX_BYTES:raise ValidationError('staged lifecycle bundle transport budget exceeded')
    return raw


@dataclass(frozen=True)
class RecoveredStagedLifecycle:
    window_args:tuple
    window_run:StagedOperatingWindowRun
    investor_raw:bytes
    binding_raw:bytes
    run:StagedLifecycleReturnRun
    bundle_sha256:str


def recover_staged_lifecycle_bundle(raw):
    if type(raw)is not bytes or not raw or len(raw)>MAX_BYTES:raise ValidationError('bounded immutable staged lifecycle bundle required')
    try:b=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid staged lifecycle bundle JSON')from error
    _shape(b,['schema','versions','construction_bundle','phase_contract','periods','sale','holding_manifest','hold_sale_spec','cash_boundary_binding','window_spec','investor_source','investor_binding','expected_run'])
    if b['schema']!='miniuw.synthetic-staged-lifecycle-bundle.v1'or b['versions']!=versions():raise ValidationError('unsupported staged lifecycle bundle schema or version')
    construction=_nested(b['construction_bundle']);phase_raw=_bytes(b['phase_contract']);phase=produce_operating_debt_phase(construction,phase_raw);periods=[]
    for row in _list(b['periods'],65):
        _shape(row,['noi_source','cash_spec']);nr=_bytes(row['noi_source']);sr=_bytes(row['cash_spec']);noi=produce_operating_noi(nr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=reconcile_operating_cash(nr,noi,sr)))
    periods=tuple(periods);s=_shape(b['sale'],['closing_id','closing_source','loans','debt_spec']);cr=_bytes(s['closing_source']);dr=_bytes(s['debt_spec']);closing=produce_closing_cash(cr);loans=tuple(_loan(e)for e in _list(s['loans'],64))
    sale=CheckedClosingEvidence(closing_id=s['closing_id'],closing_raw=cr,closing_run=closing,loans=loans,debt_spec_raw=dr,debt_run=reconcile_debt_closing(loans,cr,closing,dr))
    hr=_bytes(b['holding_manifest']);holding=reconcile_holding_cash(periods,hr);hs=_bytes(b['hold_sale_spec']);hold_args=(periods,sale,hr,holding,hs);hold=reconcile_hold_sale_cash(*hold_args)
    wa=(construction,phase_raw,phase,hold_args,hold,_bytes(b['cash_boundary_binding']),_bytes(b['window_spec']));window=reconcile_staged_operating_window(*wa)
    ir=_bytes(b['investor_source']);binding=_bytes(b['investor_binding']);run=assemble_staged_lifecycle_returns(wa,window,ir,binding)
    _shape(b['expected_run'],['payload_json','sha256'])
    if b['expected_run']!=asdict(run):raise ValidationError('stored staged lifecycle result does not reproduce from exact sources')
    return RecoveredStagedLifecycle(wa,window,ir,binding,run,hashlib.sha256(raw).hexdigest())


def required_staged_lifecycle_sources(recovered,bundle_raw):
    wa=recovered.window_args;construction=recover_construction_bundle(wa[0]);rows=[]
    def add(path,raw):rows.append(dict(requirement_id=path,source_sha256=hashlib.sha256(raw).hexdigest(),source_locator=path))
    for path,value in [('/transport/lifecycle_bundle',bundle_raw),('/construction/bundle',wa[0]),('/construction/preopening_draft',construction.preopening_raw),('/construction/binding',construction.binding_raw),('/transition/phase_contract',wa[1]),('/boundary/cash_binding',wa[5]),('/boundary/window_binding',wa[6]),('/investor/source',recovered.investor_raw),('/investor/binding',recovered.binding_raw)]:add(path,value)
    for i,e in enumerate(construction.loans):add('/construction/loans/'+str(i),e.raw)
    for i,row in enumerate(json.loads(wa[1])['loan_phases']):
        add('/transition/loans/'+str(i)+'/schedule',_bytes(row['schedule_source_utf8']));add('/transition/loans/'+str(i)+'/windows_record',canonical(row['windows']).encode())
    periods,sale,manifest,_,hold_spec=wa[3]
    for i,e in enumerate(periods):add('/operation/periods/'+str(i)+'/noi',e.noi_raw);add('/operation/periods/'+str(i)+'/cash',e.spec_raw)
    add('/operation/manifest',manifest);add('/operation/sale_binding',hold_spec);add('/sale/cash',sale.closing_raw);add('/sale/debt_binding',sale.debt_spec_raw)
    for i,e in enumerate(sale.loans):add('/sale/loans/'+str(i)+'/terms',e.loan_raw);add('/sale/loans/'+str(i)+'/windows_record',canonical([asdict(w)for w in e.windows]).encode())
    if len(rows)>256:raise ValidationError('staged lifecycle source inventory budget exceeded')
    return rows


@dataclass(frozen=True)
class CurrentStagedLifecycleRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_staged_lifecycle(bundle_raw,registry_raw,registry_run,as_of):
    recovered=recover_staged_lifecycle_bundle(bundle_raw);base=recovered.run;p=base.payload
    if type(registry_run)is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw,as_of)!=registry_run:raise ValidationError('staged lifecycle registry must reproduce at exact supplied UTC instant')
    r=registry_run.payload;required=required_staged_lifecycle_sources(recovered,bundle_raw);blockers=[];story=None
    if sorted(required,key=lambda e:e['requirement_id'])!=sorted([e['requirement']for e in r['requirements']],key=lambda e:e['requirement_id']):blockers.append('complete_staged_lifecycle_source_inventory_mismatch')
    if r['context']!=p['context']:blockers.append('staged_lifecycle_evidence_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('staged_lifecycle_sources_not_current')
    if p['state']!='compiled_synthetic_staged_purchase_to_sale':blockers.append('staged_lifecycle_calculation_blocked')
    if not blockers:
        inv=base.investor_run.payload;story={k:inv[k]for k in ['currency','gross_contributions','gross_distributions','net_cash_profit','equity_multiple','cash_by_category','cash_horizon','normalized_story','capital_snapshots','annual_cash_receipts','periodic_irr','annual_irr_roots']}
        story.update(equity_level='aggregate_project_equity',dated_events=inv['events'],upstream_story_blockers=inv['story_blockers'],selected_IRR=None,risk_observations=json.loads(p['cash_risk_run']['payload_json'])['metrics'],personal_investor_return=None,decision='PENDING')
    row=dict(case_id='Obra por etapas, misma deuda operativa y venta: ejemplo sintético',state='current_synthetic_staged_lifecycle_at_declared_time'if story is not None else'PENDING',current_matched_case=None if story is None else{'candidate_project_return_story':story},
        blockers=blockers,comparison_blockers=[],reference_evidence_blockers=[],candidate_evidence_blockers=r['blockers'],reference_calculation_blockers=[],candidate_calculation_blockers=p['blockers']+p['window_blockers']+p['phase_blockers']+p['construction_blockers']+p['operating_blockers'],reference_original_cost_blockers=[],candidate_original_cost_blockers=[])
    markdown=_render(dict(evaluated_as_of_UTC=as_of,blockers=[],case_rows=[row]))
    if story is not None:
        markdown+='\n## Continuidad del principal sin nuevos fondos\n\n| Préstamo | Principal de obra trasladado | Ancla operativa | Vencimiento conservado |\n|---|---:|---|---|\n'
        for loan in recovered.window_args[2].payload['loan_phases']:markdown+='| '+literal(loan['loan_id'])+' | '+amount(loan['construction_terminal_principal'])+' | '+literal(loan['phase_start_date'])+' | '+literal(loan['original_maturity_date'])+' |\n'
        markdown+='\nEl ancla del calendario no es un draw: principal y caja se trasladan sin crear otros aportes o cobros. Contrato/liquidaciones reales, activos/TDC y retorno personal siguen pendientes.\n'
    result={'component':'T75','purpose':'synthetic_current_staged_construction_operating_sale_review','engine_sha256':ENGINE_SHA256,'presentation_engine_sha256':PRESENTATION_ENGINE_SHA256,
        'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),'bundle_sha256':recovered.bundle_sha256,'historical_run_sha256':base.sha256,'registry_source_sha256':hashlib.sha256(registry_raw).hexdigest(),'registry_run_sha256':registry_run.sha256,
        'context':p['context'],'currency':p['currency'],'evaluated_as_of_UTC':as_of,'required_source_bindings':required,'current_project_return_story':story,'markdown':markdown,'markdown_sha256':digest(markdown),
        'blockers':sorted(set(blockers)),'evidence_blockers':r['blockers'],'calculation_blockers':row['candidate_calculation_blockers'],'state':row['state'],
        'historical_calculation_preserved':True,'live_expiry_monitor_enabled':False,'real_source_or_phase_contract_authenticated':False,'financial_publication_authorized':False,
        'external_decision_pdf_produced':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return CurrentStagedLifecycleRun(encoded,digest(encoded))
