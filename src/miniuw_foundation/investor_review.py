"""T56 internal human-readable case review from fully replayed T55 evidence."""
from dataclasses import dataclass
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from pathlib import Path
import hashlib,html,json,re
from .drafts import ValidationError,canonical,digest
from .debt_service import _fraction
from .recovery_case_inventory import RecoveryCaseInventoryRun,assemble_recovery_case_inventory

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T56.md'
LABELS={'initial_capital':'Aporte inicial','additional_capital':'Aporte adicional','refinance_cash_in':'Cash-in de refi',
    'net_refinance_distribution':'Cobro neto de refi','operating_distribution':'Distribución operativa','net_sale_distribution':'Cobro neto de venta','other_distribution':'Otra distribución'}


def literal(value):
    text=''.join(c if ord(c)>=32 and ord(c)!=127 else ' [U+'+format(ord(c),'04X')+'] 'for c in str(value))
    return html.escape(re.sub(r'([\\`*_{}\[\]()#+.!|>~-])',r'\\\1',text),quote=False)


def amount(record):
    if record is None:return 'Pendiente'
    value=_fraction(record,max_digits=1300)
    with localcontext()as ctx:
        ctx.prec=2700;ctx.rounding=ROUND_HALF_EVEN
        number=Decimal(value.numerator)/Decimal(value.denominator)
        rounded=number.quantize(Decimal('0.0001'))
        result=format(rounded,'f')
        if value and not rounded:result+=' (no es cero exacto; '+str(value)+')'
        return result


def _render(payload):
    lines=['# Mini-UW — revisión interna sintética','',
        'Decisión: **PENDING**. Evaluación UTC: '+literal(payload['evaluated_as_of_UTC'])+'.',
        'Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.',
        'Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.',
        'Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.','']
    if payload['blockers']:
        lines+=['## Bloqueos del inventario','']+['- '+literal(b)for b in payload['blockers']]+['']
    for row in payload['case_rows']:
        lines+=['## Caso: '+literal(row['case_id']),'','Decisión: **PENDING**. Estado técnico: '+literal(row['state'])+'.','']
        current=row['current_matched_case']
        if current is None:
            lines+=['Resultado actual pendiente; no se sustituye por cero ni se presenta una cifra histórica como vigente.','']
            for key in ['blockers','comparison_blockers','reference_evidence_blockers','candidate_evidence_blockers','reference_calculation_blockers','candidate_calculation_blockers','reference_original_cost_blockers','candidate_original_cost_blockers']:
                if row[key]:lines+=['- '+literal(key)+': '+literal('; '.join(row[key]))]
            lines+=[''];continue
        story=current['candidate_project_return_story'];norm=story['normalized_story'];currency=literal(story['currency'])
        lines+=['### Caja del proyecto ('+currency+')','','| Concepto | Importe |','|---|---:|']
        for name,key in [('Aportes brutos totales','gross_contributions'),('Cobros brutos totales','gross_distributions'),('Resultado neto de caja','net_cash_profit'),('Equity Multiple (x)','equity_multiple')]:
            lines.append('| '+name+' | '+amount(story[key])+' |')
        lines+=['','| Desglose bruto | Importe ('+currency+') |','|---|---:|']
        for key,label in LABELS.items():lines.append('| '+label+' | '+amount(story['cash_by_category'].get(key))+' |')
        lines+=['','### Por el aporte base declarado','']
        if norm is None or norm['events']is None:lines+=['Normalización pendiente: no se infiere un aporte base.','']
        else:
            lines+=['Referencia: '+amount(norm['reference_amount'])+' '+currency+' por una base de '+amount(norm['basis_amount'])+' '+currency+'. Base: '+literal(norm['basis_ref'])+'.',
                'La escala pertenece al proyecto; no aplica porcentajes LP/JV ni términos personales.','',
                '| Fecha | Movimiento | Importe escalado |','|---|---|---:|']
            for event in norm['events']:lines.append('| '+literal(event['date'])+' | '+literal(LABELS[event['category']])+' | '+amount(event['amount'])+' |')
            lines+=['','Total aportado escalado: '+amount(norm['total_contributions'])+'; cobrado: '+amount(norm['total_distributions'])+'; resultado: '+amount(norm['net_cash_profit'])+'.','']
        lines+=['### Movimientos brutos y fechas','', '| Fecha | Movimiento | Importe ('+currency+') |','|---|---|---:|']
        for event in story['dated_events']:lines.append('| '+literal(event['date'])+' | '+literal(LABELS[event['category']])+' | '+amount(event['amount'])+' |')
        lines+=['','### Capital, equity retenido y caja anual','',
            'Capital aún invertido y equity retenido son stocks declarados, no cobros ni una resta automática de aportes menos distribuciones.','',
            '| Corte | Capital aún invertido | Equity retenido (no caja) |','|---|---:|---:|']
        for snapshot in story['capital_snapshots']:
            blocked=any(b.startswith('snapshot:'+snapshot['as_of_date']+':')for b in story['upstream_story_blockers'])
            lines.append('| '+literal(snapshot['as_of_date'])+' | '+amount(None if blocked else snapshot['capital_still_invested'])+' | '+amount(None if blocked else snapshot['retained_equity_value'])+' |')
        if not story['capital_snapshots']:lines+=['| Pendiente | Pendiente | Pendiente |']
        lines+=['','| Año de cobro | Distribución operativa | CoC condicional (fracción) |','|---|---:|---:|']
        for year in story['annual_cash_receipts']:lines.append('| '+str(year['calendar_cash_receipt_year'])+' | '+amount(year['operating_distributions_only'])+' | '+amount(year['conditional_coc'])+' |')
        lines+=['','### IRR anual','', 'No se selecciona automáticamente una raíz. Tasas como fracciones anuales; no son porcentajes enteros.','']
        if not story['annual_irr_roots']:lines+=['- Pendiente o sin raíz anual disponible.']
        for root in story['annual_irr_roots']:
            if root['exact_annual_rate']is not None:lines+=['- Raíz exacta: '+literal(str(_fraction(root['exact_annual_rate'],max_digits=1300)))+'.']
            else:lines+=['- Intervalo exacto: '+literal(canonical(root['annual_rate_interval']))+'.']
        lines+=['','### Riesgos y pendientes','']
        risk=story['risk_observations']
        if risk:
            for name,key in [('Aportes no recuperados al corte','cash_shortfall_at_horizon'),('Pico de financiación neta de equity al cierre de fecha','peak_cumulative_net_equity_funding_at_date_close'),('Cota superior intradía sin orden verificado','possible_intraday_peak_upper_bound'),('Proporción de cobros que depende de venta (fracción)','sale_share_of_distributions')]:
                lines+=['- '+name+': '+amount(risk[key])+'.']
        lines+=['- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.',
            '- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.']
        lines+=['- '+literal(b)for b in story['upstream_story_blockers']]+['']
    lines+=['No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.','']
    return '\n'.join(lines)


@dataclass(frozen=True)
class InvestorReviewRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def render_investor_review(cases,inventory_raw,inventory_run):
    if type(inventory_run)is not RecoveryCaseInventoryRun or assemble_recovery_case_inventory(cases,inventory_raw)!=inventory_run:
        raise ValidationError('complete current case inventory must reproduce before rendering')
    markdown=_render(inventory_run.payload)
    p={'component':'T56','purpose':'internal_synthetic_investor_story_review',
       'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
       'inventory_run_sha256':inventory_run.sha256,'markdown':markdown,'markdown_sha256':digest(markdown),
       'new_financial_calculations_produced':False,'external_decision_pdf_produced':False,
       'personal_investor_return':None,'financial_publication_authorized':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(p);return InvestorReviewRun(encoded,digest(encoded))
