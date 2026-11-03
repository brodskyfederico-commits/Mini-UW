"""T71 current synthetic construction cash evidence and internal review only."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .construction_bundle import recover_construction_bundle
from .evidence_currency import EvidenceCurrencyRun,evaluate_evidence_currency
from .investor_review import literal,amount,ENGINE_SHA256 as PRESENTATION_ENGINE_SHA256

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T70-T71.md'


def required_construction_sources(recovered,bundle_raw):
    rows=[]
    for path,raw in [('/transport/bundle',bundle_raw),('/preopening/draft',recovered.preopening_raw),('/preopening/binding',recovered.binding_raw)]+[('/construction/loans/'+str(i),e.raw)for i,e in enumerate(recovered.loans)]:
        rows.append(dict(requirement_id=path,source_sha256=hashlib.sha256(raw).hexdigest(),source_locator=path))
    return rows


@dataclass(frozen=True)
class CurrentConstructionCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_construction_cash(bundle_raw,registry_raw,registry_run,as_of):
    recovered=recover_construction_bundle(bundle_raw);p=recovered.run.payload
    if type(registry_run)is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw,as_of)!=registry_run:raise ValidationError('construction evidence registry must reproduce at exact supplied UTC instant')
    r=registry_run.payload;required=required_construction_sources(recovered,bundle_raw);blockers=[];summary=None
    if sorted(required,key=lambda row:row['requirement_id'])!=sorted([row['requirement']for row in r['requirements']],key=lambda row:row['requirement_id']):blockers.append('complete_construction_source_binding_inventory_mismatch')
    if r['context']!=p['context']:blockers.append('construction_registry_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('construction_evidence_not_current')
    if p['state']!='reconciled_synthetic_staged_preopening_cash':blockers.append('construction_cash_calculation_blocked')
    if not blockers:
        cash=recovered.run.preopening_run.payload
        summary=dict(currency=p['currency'],loan_plans=[e.run.payload for e in recovered.loans],preopening_cash_totals=cash['totals'],terminal_balances=cash['date_close_balances'][-1],whole_project_return_connected=False)
    lines=['# Deuda de obra por desembolsos y caja previa','',
        'Datos sintéticos. Decisión: **PENDING**. Evaluación UTC: '+literal(as_of)+'.',
        'Importes propuestos bajo factores expresos por intervalo; no acreditan pagos ni disponibilidad bancaria real. Presentación a cuatro decimales; las fuentes conservan fracciones exactas.','']
    if summary is None:
        lines+=['Resultado actual pendiente; se retiran las cifras vigentes sin sustituir faltantes por cero. El cálculo histórico se conserva.','']
        reasons=blockers+r['blockers']+p['blockers']+p['cash_blockers']+[loan+':'+reason for loan,bs in p['loan_blockers'].items()for reason in bs]
        lines+=['- '+literal(v)for v in sorted(set(reasons))]
    else:
        for loan in summary['loan_plans']:
            lines+=['## Préstamo '+literal(loan['loan_id']),'','| Inicio | Fin | Draw | Exposición | Interés al fin | Fee al inicio | Repago al fin | Saldo |','|---|---|---:|---:|---:|---:|---:|---:|']
            for row in loan['periods']:lines.append('| '+literal(row['start_date'])+' | '+literal(row['end_date'])+' | '+' | '.join(amount(row[k])for k in ['draw_at_start','interest_exposure','interest_due_at_end','fee_due_at_start','principal_repayment_at_end','closing_principal'])+' |')
        cash=summary['preopening_cash_totals'];last=summary['terminal_balances']
        lines+=['','## Caja conciliada en la frontera preoperativa','',
            '| Concepto | Importe |','|---|---:|','| Aporte inicial declarado | '+amount(cash['initial_equity_contribution'])+' |','| Aporte adicional declarado | '+amount(cash['additional_equity_contribution'])+' |',
            '| Interés propuesto pagado en el plan | '+amount(cash['debt_interest_payment'])+' |','| Fees propuestos pagados en el plan | '+amount(cash['debt_fee_payment'])+' |',
            '| Caja libre final | '+amount(last['free_cash'])+' |','| Caja restringida final | '+amount(last['restricted_cash'])+' |']
    lines+=['','Los intereses no aumentan principal en este perfil. Repagar no restaura el compromiso no revolvente. No se generan aportes/draws para cerrar déficits ni prórrogas. La transición a deuda operativa y el retorno de toda la inversión siguen pendientes; no se presentan EM/IRR de un recorrido aún no conectado.','',
        'Sin aprobación profesional, publicación financiera, PDF externo, monitor automático, despliegue o decisiones reales.','']
    markdown='\n'.join(lines)
    result={'component':'T71','purpose':'synthetic_current_staged_construction_cash_review','engine_sha256':ENGINE_SHA256,'presentation_engine_sha256':PRESENTATION_ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'bundle_sha256':recovered.bundle_sha256,'historical_cash_run_sha256':recovered.run.sha256,'registry_source_sha256':hashlib.sha256(registry_raw).hexdigest(),'registry_run_sha256':registry_run.sha256,
        'context':p['context'],'currency':p['currency'],'evaluated_as_of_UTC':as_of,'required_source_bindings':required,'current_construction_summary':summary,
        'markdown':markdown,'markdown_sha256':digest(markdown),'blockers':sorted(set(blockers)),'evidence_blockers':r['blockers'],'cash_blockers':p['cash_blockers'],'calculation_blockers':p['blockers'],'loan_blockers':p['loan_blockers'],
        'state':'current_synthetic_staged_construction_cash'if summary is not None else'PENDING','historical_calculation_preserved':True,'live_expiry_monitor_enabled':False,
        'source_or_review_authority_authenticated':False,'financial_publication_authorized':False,'whole_project_return_connected':False,'external_decision_pdf_produced':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return CurrentConstructionCashRun(encoded,digest(encoded))
