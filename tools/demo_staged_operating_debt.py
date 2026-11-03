"""Reproduce a same-liability debt phase, full cash return and current/pending views."""
from pathlib import Path
import json,copy,hashlib
from staged_phase_demo_support import make_case,raw,q
from miniuw_foundation.staged_lifecycle_bundle import export_staged_lifecycle_bundle,recover_staged_lifecycle_bundle,required_staged_lifecycle_sources,assemble_current_staged_lifecycle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.investor_review import amount
from demo_lifecycle_returns import annual_ranges

ROOT=Path(__file__).resolve().parents[1]
AT='2027-07-01T12:00:00Z'


def registry(recovered,bundle):
    requirements=required_staged_lifecycle_sources(recovered,bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=recovered.run.payload['context'],inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-complete-staged-operating-source-inventory-not-original-authority',requirements=requirements,
        evidence=[dict(evidence_id='SYNTHETIC-staged-operating-'+str(i),**r,issued_at='2027-01-01T00:00:00Z',valid_from='2027-01-01T00:00:00Z',valid_until='2027-07-02T00:00:00Z',review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,basis_ref='SYNTHETIC-new-test-validity-not-real-renewal-or-approval')for i,r in enumerate(requirements)])


def report(case):
    p=case[-1].investor_run.payload;n=p['normalized_story'];risk=json.loads(case[-1].payload['cash_risk_run']['payload_json'])['metrics']
    lines=['# Deuda de obra, deuda operativa y retorno hasta la venta','',
        'El caso sintético conecta los desembolsos de obra con una fase amortizante de la misma obligación, la operación y la venta. El principal y la caja se arrastran sin generar otro préstamo o aporte. La decisión sigue **PENDING**; no hay despliegue ni decisiones reales.','',
        '## Cómo pasa la deuda a operación','',
        '| Concepto del ejemplo | USD o fecha |','|---|---:|',
        '| Draws brutos de obra | 250 |','| Principal repagado durante obra | 50 |','| Interés de obra pagado según el plan | 5 |','| Fees de obra pagados según el plan | 5 |',
        '| Principal trasladado a la fase operativa | 200 |','| Caja libre trasladada a operación | 590 |','| Nuevos fondos en la frontera de fases | 0 |','| Inicio de fase operativa | 2027-01-01 |','| Vencimiento original conservado | 2027-07-01 |','',
        'Los draws de obra empiezan en octubre de 2026. El ancla de enero de 2027 sirve para el cálculo del calendario operativo; no es una nueva fecha de financiación. La continuidad de la misma obligación y la liquidación previa de intereses/fees son hipótesis expresas del contrato sintético, todavía sin autenticación documental.','',
        'Los términos operativos suministran tasa cero por intervalo de pago, frecuencia 12, amortización de 10 pagos y vencimiento en el sexto. El pago regular calculado es 20: dos pagos antes de abril y tres entre abril y julio reducen el principal de 200 a 100. La venta liquida esos 100 antes de la cuota regular de julio, sin añadir otra vez el balloon. La tasa operativa cero es un dato de prueba nuevo; no se deduce del factor de obra de 1%.','',
        'Cambiar el principal a 201, mover el ancla o extender el vencimiento sin otro perfil deja el caso pendiente. Una caja operativa que reinicia con un saldo distinto de 590 también queda bloqueada, aunque sus cuentas locales cuadren.','',
        '## Retorno del equity agregado del proyecto','',
        '| Concepto | USD o múltiplo |','|---|---:|','| Aportes brutos históricos | '+amount(p['gross_contributions'])+' |','| Cobros brutos | '+amount(p['gross_distributions'])+' |','| Resultado neto de caja | '+amount(p['net_cash_profit'])+' |','| EM (x) | '+amount(p['equity_multiple'])+' |','',
        'Los aportes son 1.000 en octubre y 400 en noviembre de 2026. Los 200 de principal y los 590 de caja de enero no se cuentan como movimientos nuevos del inversor. La escala siguiente usa el total aportado de 1.400 como base equivalente a 10; es una escala del proyecto, no una participación LP/JV.','',
        '| Fecha | Movimiento | USD | Escala por 10 |','|---|---|---:|---:|']
    labels={'initial_capital':'Aporte inicial','additional_capital':'Aporte adicional','operating_distribution':'Cobro operativo','net_sale_distribution':'Cobro neto de venta'};normalized={e['event_id']:e for e in n['events']}
    for e in sorted(p['events'],key=lambda e:e['date']):lines.append('| '+e['date']+' | '+labels[e['category']]+' | '+amount(e['amount'])+' | '+amount(normalized[e['event_id']]['amount'])+' |')
    lines+=['','Por cada 10 de equity total, los cobros suman '+amount(n['total_distributions'])+' y el resultado neto de caja es '+amount(n['net_cash_profit'])+'. Se conserva el resultado negativo.','',
        '## IRR anual y riesgos','',
        'La grilla mensual expresa va de octubre de 2026 a julio de 2027. La IRR periódica se anualiza bajo esa frecuencia; se conservan todas las raíces/intervalos sin elegir una tasa preferida. Los racionales exactos permanecen en el paquete recuperable.','']+annual_ranges(p['annual_irr_roots'])
    lines+=['','- Caja aportada no recuperada al corte: '+amount(risk['cash_shortfall_at_horizon'])+' USD, sin certificar pérdida económica final.',
        '- Pico de financiación neta de equity al cierre de fecha: '+amount(risk['peak_cumulative_net_equity_funding_at_date_close'])+' USD.',
        '- Proporción de cobros que procede de venta: '+amount(risk['sale_share_of_distributions'])+' como fracción.','',
        'CoC, capital remanente, equity retenido y retorno personal conservan sus pendientes de bases/términos. Los valores retenidos no se suman a cobros. Contratos, pagos, disponibilidad real, activos/devengos/TDC y revisión financiera siguen sin verificarse. La fase no autoriza una novación, capitalización o prórroga real.','',
        'La recuperación reproduce todo el recorrido desde las fuentes exactas. La vista actual exige vigencia de 22 bindings al instante UTC declarado; una fuente vencida retira cifras actuales y conserva la historia.','',
        '[Vista actual](Revision_Vigente_Obra_Operacion_T75.md) · [Vista pendiente](Revision_Pendiente_Obra_Operacion_T75.md) · [Evidencia](synthetic-staged-operating-demo.json) · [Contrato técnico](../technical-implementation-T72-T75.md).','']
    return '\n'.join(lines)


def main():
    case=make_case();assert case[-1].payload['state']=='compiled_synthetic_staged_purchase_to_sale';bundle=export_staged_lifecycle_bundle(*case);recovered=recover_staged_lifecycle_bundle(bundle);assert recovered.run==case[-1]
    (ROOT/'templates/synthetic-staged-lifecycle-bundle-example.json').write_bytes(bundle)
    declared=registry(recovered,bundle);path=ROOT/'templates/synthetic-staged-lifecycle-evidence-example.json';path.write_text(json.dumps(declared,ensure_ascii=False,indent=2)+'\n');source=path.read_bytes()
    current=assemble_current_staged_lifecycle(bundle,source,evaluate_evidence_currency(source,AT),AT)
    stale=copy.deepcopy(declared);next(e for e in stale['evidence']if e['requirement_id']=='/transition/phase_contract')['valid_until']=AT;stale_raw=raw(stale)
    pending=assemble_current_staged_lifecycle(bundle,stale_raw,evaluate_evidence_currency(stale_raw,AT),AT);assert pending.payload['current_project_return_story']is None
    wrong=make_case(terms_change=lambda t:t.update(principal=q(201)));assert wrong[-1].compiled_raw is None;assert recover_staged_lifecycle_bundle(export_staged_lifecycle_bundle(*wrong)).run==wrong[-1]
    extended=make_case(terms_change=lambda t:t['payment_dates'].__setitem__(-1,'2027-08-01'));assert extended[-1].compiled_raw is None
    text=report(case);(ROOT/'docs/review/Deuda_Obra_a_Operacion_y_Retorno_T72_T75.md').write_text(text)
    for path,result in [('docs/review/Revision_Vigente_Obra_Operacion_T75.md',current),('docs/review/Revision_Pendiente_Obra_Operacion_T75.md',pending)]:(ROOT/path).write_text(result.payload['markdown'])
    p=case[-1].investor_run.payload
    return dict(purpose='synthetic_staged_debt_to_operating_phase_and_full_cash_returns',components=['T72','T73','T74','T75'],
        phase_run_sha256=case[0][2].sha256,window_run_sha256=case[1].sha256,return_run_sha256=case[-1].sha256,bundle_sha256=hashlib.sha256(bundle).hexdigest(),full_recovery=True,
        registry_source_sha256=hashlib.sha256(source).hexdigest(),required_source_bindings=len(current.payload['required_source_bindings']),evaluated_as_of_UTC=AT,
        current_run_sha256=current.sha256,current_report_sha256=current.payload['markdown_sha256'],pending_report_sha256=pending.payload['markdown_sha256'],summary_report_sha256=hashlib.sha256(text.encode()).hexdigest(),expired_registry_json=stale_raw.decode(),
        base_case={k:p[k]for k in ['gross_contributions','gross_distributions','net_cash_profit','equity_multiple','normalized_story','annual_cash_receipts','annual_irr_roots','story_blockers']},
        wrong_principal_case=dict(state=wrong[-1].payload['state'],phase_blockers=wrong[-1].payload['phase_blockers'],recovered_still_blocked=True),
        maturity_extension_case=dict(state=extended[-1].payload['state'],phase_blockers=extended[-1].payload['phase_blockers'],extension_generated=False),
        expired_current_story=pending.payload['current_project_return_story'],expired_evidence_blockers=pending.payload['evidence_blockers'],
        phase_boundary_funding_generated=False,personal_investor_return=None,financial_model_complete=False,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
