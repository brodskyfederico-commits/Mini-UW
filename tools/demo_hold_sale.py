"""Run, recover and inspect independent synthetic holding/sale cases without refinance."""
from pathlib import Path
import copy,json,hashlib
from hold_sale_demo_support import sources,build,raw
from miniuw_foundation.hold_sale_bundle import export_hold_sale_bundle,recover_hold_sale_bundle
from miniuw_foundation.current_hold_sale import required_hold_sale_sources,assemble_current_hold_sale
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.investor_review import amount
from demo_lifecycle_returns import annual_ranges

ROOT=Path(__file__).resolve().parents[1]
AT='2027-07-01T12:00:00Z'
LABELS={'initial_capital':'Aporte inicial','additional_capital':'Aporte adicional','operating_distribution':'Cobro operativo','net_sale_distribution':'Cobro neto de venta'}


def registry(recovered,bundle):
    requirements=required_hold_sale_sources(recovered,bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=recovered.run.payload['context'],inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-complete-hold-sale-transport-not-original-document-authentication',requirements=requirements,
        evidence=[dict(evidence_id='SYNTHETIC-hold-sale-evidence-'+str(i),**r,issued_at='2027-01-01T00:00:00Z',valid_from='2027-01-01T00:00:00Z',valid_until='2027-07-02T00:00:00Z',review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,basis_ref='SYNTHETIC-explicit-software-test-validity-not-professional-approval')for i,r in enumerate(requirements)])


def summary(case):
    p=case[-1].investor_run.payload;n=p['normalized_story'];risk=json.loads(case[-1].payload['cash_risk_run']['payload_json'])['metrics']
    lines=['# Compra, tenencia y venta sin refinanciación','',
        'Este caso sintético independiente conserva el préstamo inicial durante la operación y lo liquida en la venta. No genera un refi ni una extensión automática del vencimiento. La decisión sigue **PENDING**, sin despliegue ni decisiones reales.','',
        '| Retorno del equity agregado del proyecto | USD |','|---|---:|',
        '| Aportes brutos | '+amount(p['gross_contributions'])+' |','| Cobros brutos | '+amount(p['gross_distributions'])+' |',
        '| Resultado neto de caja | '+amount(p['net_cash_profit'])+' |','| EM (x) | '+amount(p['equity_multiple'])+' |','',
        'El ejemplo aporta 1.000 en octubre de 2026 y 400 en noviembre. Un draw de deuda de 120 en diciembre, junto con esos aportes, financia pagos previos de 520 y deja caja de apertura de 1.000. Esa caja se arrastra al período operativo y no cuenta como otro aporte.','',
        '## Cuánto se cobra por cada 10 aportados','',
        'La base expresa es el total de equity aportado, 1.400, escalado a 10. El aporte inicial representa 7,1429 y el adicional 2,8571. La escala pertenece al proyecto; el retorno personal depende de términos de reparto.','',
        '| Fecha | Movimiento bruto | USD del proyecto | Escala por 10 |','|---|---|---:|---:|']
    normalized={e['event_id']:e for e in n['events']}
    for e in sorted(p['events'],key=lambda e:e['date']):lines.append('| '+e['date']+' | '+LABELS[e['category']]+' | '+amount(e['amount'])+' | '+amount(normalized[e['event_id']]['amount'])+' |')
    lines+=['','Los cobros suman '+amount(n['total_distributions'])+' por cada 10 aportados; el resultado neto de caja es '+amount(n['net_cash_profit'])+'. Los aportes de cero son explícitos, no datos faltantes.','',
        '## Deuda y caja hasta la venta','',
        'El préstamo del caso nuevo declara origen en diciembre de 2026 y vencimiento en julio de 2027. En operación se pagan seis cuotas de principal de 10; la venta liquida los 60 restantes, más fee suministrado de 10. La tasa cero es un dato de esta prueba, no una condición bancaria adoptada. No se cuenta un balloon adicional al principal ya liquidado.','',
        'En este ejemplo, la caja operativa parte de 1.000; los cobros operativos suman 150, los pagos de capex 40, los depósitos a reserva 100 y las distribuciones operativas 200. Antes de vender quedan 750 libres y 100 restringidos. La venta cobra 400, libera la reserva y paga principal 60, fee 10 y costo de cierre 20: el cobro neto de equity en venta es 1.160.','',
        'El préstamo anterior con vencimiento en abril se conserva sin cambios. Si se intenta llevar ese contrato hasta julio sin otra solución, el resultado permanece pendiente: no se fabrica financiación ni una prórroga. Los ejemplos con/sin deuda y con refi tienen entradas propias y no constituyen un ranking de estrategias.','',
        '## IRR y riesgos','',
        'Se usa la grilla mensual expresa desde octubre hasta julio para la IRR periódica anualizada; se conservan todas las raíces/intervalos sin elegir una tasa preferida.','']+annual_ranges(p['annual_irr_roots'])
    lines+=['','- Caja aportada no recuperada al corte: '+amount(risk['cash_shortfall_at_horizon'])+' USD; no equivale automáticamente a pérdida económica definitiva.',
        '- Pico neto de financiación de equity al cierre de fecha: '+amount(risk['peak_cumulative_net_equity_funding_at_date_close'])+' USD.',
        '- Proporción de cobros procedente de venta: '+amount(risk['sale_share_of_distributions'])+' como fracción.','',
        'CoC, capital remanente y equity retenido siguen pendientes de bases expresas. Los valores retenidos no se suman a cobros. Tampoco se verifican documentos, pagos, disponibilidad bancaria o activos/TDC reales. El caso se recupera desde sus fuentes y su vista actual exige vigencia de 16 bindings al instante UTC declarado; una fuente vencida retira las cifras actuales y conserva la historia.','',
        '[Evidencia del ejemplo](synthetic-hold-sale-demo.json) · [Vista interna actual](Revision_Vigente_Sin_Refi_T67.md) · [Vista pendiente](Revision_Pendiente_Sin_Refi_T67.md) · [Contrato del recorrido](../technical-implementation-T63-T65.md).','']
    return '\n'.join(lines)


def main():
    case=build(sources());bundle=export_hold_sale_bundle(*case);recovered=recover_hold_sale_bundle(bundle);assert recovered.run==case[-1]
    (ROOT/'templates/synthetic-hold-sale-bundle-example.json').write_bytes(bundle)
    declared=registry(recovered,bundle);path=ROOT/'templates/synthetic-hold-sale-evidence-example.json';path.write_text(json.dumps(declared,ensure_ascii=False,indent=2)+'\n');source=path.read_bytes()
    current=assemble_current_hold_sale(bundle,source,evaluate_evidence_currency(source,AT),AT)
    stale=copy.deepcopy(declared);next(e for e in stale['evidence']if e['requirement_id']=='/preopening/cash')['valid_until']=AT;stale_raw=raw(stale)
    pending=assemble_current_hold_sale(bundle,stale_raw,evaluate_evidence_currency(stale_raw,AT),AT);assert pending.payload['current_project_return_story']is None
    d=sources();d['loans'][0].update(maturity_payment=4,payment_dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01']);early=build(d);early_recovered=recover_hold_sale_bundle(export_hold_sale_bundle(*early));assert early_recovered.run.compiled_raw is None
    all_equity=build(sources(True));assert recover_hold_sale_bundle(export_hold_sale_bundle(*all_equity)).run==all_equity[-1]
    text=summary(case);(ROOT/'docs/review/Compra_Tenencia_Venta_Sin_Refi_T63_T67.md').write_text(text)
    for path,result in [('docs/review/Revision_Vigente_Sin_Refi_T67.md',current),('docs/review/Revision_Pendiente_Sin_Refi_T67.md',pending)]:(ROOT/path).write_text(result.payload['markdown'])
    p=case[-1].investor_run.payload
    return dict(purpose='synthetic_no_refinance_cash_opening_return_recovery_and_currency',components=['T63','T64','T65','T66','T67'],
        hold_sale_run_sha256=case[0][7].sha256,opening_run_sha256=case[1].sha256,return_run_sha256=case[-1].sha256,
        bundle_sha256=hashlib.sha256(bundle).hexdigest(),full_recovery=True,registry_source_sha256=hashlib.sha256(source).hexdigest(),required_source_bindings=len(current.payload['required_source_bindings']),evaluated_as_of_UTC=AT,
        summary_report_sha256=hashlib.sha256(text.encode()).hexdigest(),current_run_sha256=current.sha256,current_report_sha256=current.payload['markdown_sha256'],pending_report_sha256=pending.payload['markdown_sha256'],expired_registry_json=stale_raw.decode(),
        base_case={k:p[k]for k in ['gross_contributions','gross_distributions','net_cash_profit','equity_multiple','normalized_story','annual_cash_receipts','annual_irr_roots','story_blockers']},
        earlier_maturity_case=dict(state=early[-1].payload['state'],sale_debt_blockers=early[-1].payload['sale_debt_blockers'],automatic_extension_generated=False,recovered_still_blocked=True),
        explicit_no_debt_case=dict(state=all_equity[-1].payload['state'],loan_inventory=[],full_recovery=True),
        pending_current_story=pending.payload['current_project_return_story'],pending_evidence_blockers=pending.payload['evidence_blockers'],
        scenario_comparison_or_ranking=False,personal_investor_return=None,financial_model_complete=False,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
