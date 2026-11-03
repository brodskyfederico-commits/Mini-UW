"""Run, recover and describe the synthetic purchase-to-sale cash lifecycle."""
from pathlib import Path
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
import json,hashlib
from lifecycle_demo_support import make_case,q
from demo_preopening_cash import make_source as original_preopening
from miniuw_foundation.lifecycle_bundle import export_lifecycle_bundle,recover_lifecycle_bundle
from miniuw_foundation.investor_review import amount
from miniuw_foundation.debt_service import _fraction

ROOT=Path(__file__).resolve().parents[1]
LABELS={'initial_capital':'Aporte inicial','additional_capital':'Aporte adicional','operating_distribution':'Cobro operativo',
    'net_refinance_distribution':'Cobro neto de refi','refinance_cash_in':'Cash-in de refi','net_sale_distribution':'Cobro neto de venta','other_distribution':'Otro cobro'}


def annual_ranges(roots):
    lines=[]
    for root in roots:
        if root['exact_annual_rate']is not None:lines.append('- Tasa anual exacta como fracción: '+str(_fraction(root['exact_annual_rate'],1300))+'.');continue
        interval=root['annual_rate_interval']
        with localcontext()as ctx:
            ctx.prec=2700
            bounds=[]
            for key,rounding in [('lower',ROUND_FLOOR),('upper',ROUND_CEILING)]:
                r=_fraction(interval[key],1300);v=Decimal(r.numerator)*100/Decimal(r.denominator)
                bounds.append(format(v.quantize(Decimal('0.01'),rounding=rounding),'f'))
        lines.append('- Intervalo anual contenido entre '+bounds[0]+'% y '+bounds[1]+'% (extremos ampliados sólo para presentación).')
    return lines or ['- Pendiente: ninguna raíz anual disponible.']


def report(case):
    run=case[-1]
    p=run.investor_run.payload;n=p['normalized_story'];risk=json.loads(run.payload['cash_risk_run']['payload_json'])['metrics']
    rows=['# Retorno sintético desde la compra hasta la venta','',
        'El recorrido conecta compra y obra, deuda de apertura, operación, refinanciación y venta. La decisión continúa **PENDING**; son cifras de prueba del equity agregado del proyecto, sin reparto personal ni uso para decisiones reales.','',
        '| Resultado del ejemplo en USD | Importe |','|---|---:|',
        '| Aportes brutos de equity | '+amount(p['gross_contributions'])+' |',
        '| Cobros brutos de equity | '+amount(p['gross_distributions'])+' |',
        '| Resultado neto de caja | '+amount(p['net_cash_profit'])+' |',
        '| Equity Multiple (x) | '+amount(p['equity_multiple'])+' |',
        '| Cash-in de refi del caso base | '+amount(p['cash_by_category']['refinance_cash_in'])+' |','',
        'Los aportes son 1.000 en octubre de 2026 y 400 en noviembre. La caja de 1.000 al iniciar la operación ya procede de esa historia y de la deuda: no se cuenta como otro aporte. El préstamo inicial recibe 120 en diciembre; su principal de apertura se concilia con el calendario de deuda utilizado en la operación y el refi.','',
        '## Aportes y cobros por cada 10 de equity total','',
        'La base es el total de aportes declarados de 1.400, escalado a 10. El aporte inicial representa 7,1429 y el adicional 2,8571. Es una escala del proyecto; el retorno personal requiere términos de reparto.','',
        '| Fecha | Movimiento | USD del proyecto | Escala por 10 |','|---|---|---:|---:|']
    scaled={e['event_id']:e for e in n['events']}
    for e in sorted(p['events'],key=lambda e:e['date']):rows.append('| '+e['date']+' | '+LABELS[e['category']]+' | '+amount(e['amount'])+' | '+amount(scaled[e['event_id']]['amount'])+' |')
    opening=case[1].payload['loan_checks'][0];checks=case[0][5].payload['operating_debt_checks'];closings=case[0][3]
    rows+=['','Por cada 10 aportados, los cobros suman '+amount(n['total_distributions'])+' y el resultado de caja es '+amount(n['net_cash_profit'])+'.','',
        '## Recorrido del principal de deuda','',
        '| Punto | Principal USD |','|---|---:|',
        '| Préstamo previo al refi en la apertura operativa | '+amount(opening['scheduled_opening_principal'])+' |',
        '| Principal regular pagado antes del refi | '+amount(checks[0]['computed_principal'])+' |',
        '| Principal liquidado en el refi | '+amount(closings[0].debt_run.payload['loans'][0]['computed_principal_to_close'])+' |',
        '| Nuevo principal después del refi | '+amount(closings[0].closing_run.payload['new_loan_principal'])+' |',
        '| Principal regular pagado después del refi | '+amount(checks[1]['computed_principal'])+' |',
        '| Principal liquidado en la venta | '+amount(closings[1].debt_run.payload['loans'][0]['computed_principal_to_close'])+' |','',
        'Estas cifras provienen de los cierres y calendarios reproducidos. Interés, fees, reservas y otros usos se conservan aparte; principal de deuda no equivale a un cobro del inversor.','',
        '## IRR anual y caja anual','',
        'El calendario empieza en octubre de 2026 y termina en julio de 2027. Se usa la grilla mensual expresa para la IRR periódica anualizada. Se conservan todas las raíces/intervalos; no se elige una raíz automáticamente. Los racionales exactos están en el paquete recuperable.','']+annual_ranges(p['annual_irr_roots'])
    rows+=['','| Año de cobro | Distribución operativa USD | CoC |','|---|---:|---|']
    for year in p['annual_cash_receipts']:rows.append('| '+str(year['calendar_cash_receipt_year'])+' | '+amount(year['operating_distributions_only'])+' | '+amount(year['conditional_coc'])+' |')
    rows+=['','CoC, capital aún invertido y equity retenido permanecen pendientes de bases expresas. El equity retenido no se suma a los cobros.','',
        '## Riesgos y controles','',
        '- Caja aportada no recuperada al corte: '+amount(risk['cash_shortfall_at_horizon'])+' USD; no certifica pérdida económica definitiva.',
        '- Pico de financiación neta de equity al cierre de fecha: '+amount(risk['peak_cumulative_net_equity_funding_at_date_close'])+' USD.',
        '- Proporción de cobros procedente de venta: '+amount(risk['sale_share_of_distributions'])+' como fracción.',
        '- Un caso separado que requiere cash-in lo registra como aporte bruto y mantiene en cero el cobro de refi. Sin una hipótesis expresa de financiación, queda bloqueado.',
        '- Se conserva el bloqueo del ejemplo previo de deuda no conciliada y el fallo bancario con NOI 50. El caso completo usa una rama de prueba independiente con NOI bancario 2.000; no corrige ni reemplaza los originales.',
        '- El paquete sintético se recupera desde sus fuentes exactas y reproduce deuda, capacidad, caja y retorno; un hash actualizado no valida cifras manipuladas.','',
        'La base de activos/TDC, documentación y pagos reales, disponibilidad de financiación, términos personales y revisión financiera siguen abiertos. Este recorrido no habilita despliegue, publicación financiera ni decisiones reales.','',
        '[Evidencia del recorrido](synthetic-lifecycle-returns-demo.json) · [Paquete recuperable sintético](../../templates/synthetic-lifecycle-bundle-example.json) · [Contrato del retorno](../technical-implementation-T59.md).','']
    return '\n'.join(rows)


def main():
    case=make_case();bundle=export_lifecycle_bundle(*case);recovered=recover_lifecycle_bundle(bundle);assert recovered.run==case[-1]
    (ROOT/'templates/synthetic-lifecycle-bundle-example.json').write_bytes(bundle)
    bank=make_case(bank_noi=50);bank_recovered=recover_lifecycle_bundle(export_lifecycle_bundle(*bank));assert bank_recovered.run==bank[-1]and bank[-1].compiled_raw is None
    def old(p):p.clear();p.update(original_preopening(case[1].payload['context']))
    unmatched=make_case(pre_change=old);assert unmatched[-1].compiled_raw is None
    def cashin(d):
        d['closings'][0]['amounts']['closing_costs_paid']['value']=q(1020);d['closings'][0]['equity_funding_assumption_ref']='SYNTHETIC-projected-cash-in-not-available-funds-proof'
    contribution=make_case(project_change=cashin,include_refinance_cash_in=True);assert contribution[-1].compiled_raw is not None
    text=report(case);(ROOT/'docs/review/Retorno_Compra_a_Venta_T58_T60.md').write_text(text)
    p=case[-1].investor_run.payload
    return {'purpose':'synthetic_purchase_to_sale_debt_cash_return_and_recovery','components':['T58','T59','T60'],
        'opening_run_sha256':case[1].sha256,'capacity_project_run_sha256':case[3].sha256,'lifecycle_run_sha256':case[-1].sha256,
        'portable_bundle_sha256':hashlib.sha256(bundle).hexdigest(),'portable_bundle_bytes':len(bundle),'exact_full_recovery':True,
        'report_sha256':hashlib.sha256(text.encode()).hexdigest(),
        'base_case':{k:p[k]for k in ['gross_contributions','gross_distributions','net_cash_profit','equity_multiple','normalized_story','cash_horizon','annual_cash_receipts','annual_irr_roots','story_blockers']},
        'cash_in_case':{'state':contribution[-1].payload['state'],'gross_contributions':contribution[-1].investor_run.payload['gross_contributions'],'cash_by_category':contribution[-1].investor_run.payload['cash_by_category']},
        'original_bank_failure':{'state':bank[-1].payload['state'],'blockers':bank[-1].payload['blockers'],'capacity_blockers':bank[3].payload['capacity_blockers'],'recovered_still_blocked':True},
        'prior_unmatched_T57_case':{'state':unmatched[1].payload['state'],'blockers':unmatched[1].payload['blockers'],'lifecycle_generated':False},
        'fixture_note':'Independent software branch: declared bank NOI 2000. Original bank NOI 50, unmatched T57 history and all prior examples preserved.',
        'personal_investor_return':None,'financial_model_complete':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
