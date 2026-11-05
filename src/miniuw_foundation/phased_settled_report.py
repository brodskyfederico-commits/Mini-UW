"""T110 bounded one-page aggregate cash story from the exact current source gate."""
from fractions import Fraction as F
from pathlib import Path
from .drafts import ValidationError,canonical,digest
from .debt_service import _fraction,rational
from .operating_noi import _bounded
from .scheduled_expense_case import sha
from .phased_settled_output import PhasedSettledRun,assemble_phased_settled_output,DEFINITION
from .synthetic_onepager import _pdf,_pdf_string,PreviewLayoutError,ENGINE_SHA256 as PDF_ENGINE_SHA256
from .v1_report import V1Report,amount,annual_irr,EVENTS,LABELS,ENGINE_SHA256 as FORMAT_ENGINE_SHA256
from .long_horizon_report import ORDER,compact

ENGINE_SHA256=sha(Path(__file__).read_bytes())
MAX_ANNUAL_ROWS=12
STORY='/current_project_return_story'


def groups(story):
    if story is None:return []
    events=story['events']
    if len(events)>256:raise PreviewLayoutError('settled event inventory exceeds one-page grouping budget')
    if any(e['category']not in ORDER for e in events):raise ValidationError('unknown cash category cannot be omitted')
    result=[];gross_a=gross_c=F(0)
    for category in ORDER:
        indices=[i for i,e in enumerate(events)if e['category']==category];total=F(0)
        for i in indices:total=_bounded(total+_fraction(events[i]['amount'],1300))
        if rational(total)!=story['cash_by_category'][category]:raise ValidationError('cash category grouping differs from current source')
        if category in ORDER[:3]:gross_a=_bounded(gross_a+total)
        else:gross_c=_bounded(gross_c+total)
        dates=[events[i]['date']for i in indices]
        result.append(dict(category=category,amount=rational(total),event_indices=indices,event_count=len(indices),zero_event_count=sum(_fraction(events[i]['amount'],1300)==0 for i in indices),
            first_date=min(dates)if dates else None,last_date=max(dates)if dates else None))
    if rational(gross_a)!=story['gross_contributions']or rational(gross_c)!=story['gross_distributions']:raise ValidationError('grouped gross contributions/distributions differ')
    return result


def _render_verified(run):
    p=run.payload;s=p['current_project_return_story'];g=groups(s);years=[]if s is None else s['annual_cash_receipts']
    if len(years)>MAX_ANNUAL_ROWS:raise PreviewLayoutError('all annual rows required; more than twelve cannot fit this profile')
    commands=[b'0.06 0.17 0.25 rg 24 524 744 64 re f 1 1 1 rg'];spans=[]
    def text(x,y,value,size=7,width=232,bold=False,refs=()):
        encoded=_pdf_string(value)
        if len(value)*size*.6>width or x<24 or x+width>768 or y<25 or y+size>588:raise PreviewLayoutError('settled one-page span exceeds explicit layout budget; no clipping')
        commands.append(f'BT /{"F2"if bold else"F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+encoded+b') Tj ET')
        spans.append(dict(text=value,x=x,y=y,font_size=size,width=width,result_pointers=list(refs)))
    text(36,566,'MINI-UW | RENTA, POLIZAS Y VENTA',15,720,True)
    text(36,546,'PENDIENTE | Prueba sintetica - equity agregado del proyecto',10,720,True,['/decision'])
    text(36,532,'Sin despliegue, decisiones reales ni aprobacion profesional.',7.5,720)
    commands.append(b'0.06 0.17 0.25 rg')
    text(28,510,'Caso '+p['context']['deal_id']+' | Escenario '+p['context']['scenario_id'],7,736,refs=['/context'])
    context='Evaluacion UTC '+p['evaluated_as_of_UTC']
    context+=(' | '+s['currency']+' | '+s['cash_horizon']['start']+' a '+s['cash_horizon']['end'])if s else' | Moneda/ventana/cifras actuales pendientes'
    text(28,498,context,7,736,refs=['/evaluated_as_of_UTC',STORY+'/currency',STORY+'/cash_horizon'])
    for i,(label,key)in enumerate((('Aportes brutos','gross_contributions'),('Cobros brutos','gross_distributions'),('Neto de caja','net_cash_profit'),('Equity Multiple','equity_multiple'))):
        text(28+i*184,476,label,8,178,True);text(28+i*184,457,compact(None if s is None else s[key]),12,178,True,[STORY+'/'+key])
    text(28,440,'MOVIMIENTOS POR CONCEPTO',8,232,True)
    if s is None:text(28,419,'Cifras retiradas por fuentes/calculo.',7,232,refs=['/blockers'])
    for i,row in enumerate(g):
        y=421-i*25;ref=STORY+'/cash_by_category/'+row['category'];text(28,y,EVENTS[row['category']]+': '+compact(row['amount']),7,232,refs=[ref])
        date='Sin movimientos (n=0 z=0)'if not row['event_count']else row['first_date']+' a '+row['last_date']+' n='+str(row['event_count'])+' z='+str(row['zero_event_count'])
        text(28,y-11,date,6.1,232,refs=[STORY+'/events'])
    text(28,243,'n=eventos; z=ceros. Calendario en JSON.',6.3,232)
    text(28,232,'Los rangos no implican pagos periodicos.',6.3,232)
    text(28,214,'TIR ANUAL (INTERVALO, NO PUNTO)',8,232,True)
    text(28,199,annual_irr([]if s is None else s['annual_irr_roots']),9,232,True,refs=[STORY+'/annual_irr_roots'])
    text(28,185,'Todas las raices y parametros en evidencia.',6.3,232)
    text(280,440,'SEGURO / LIQUIDACION EN VENTA',8,232,True)
    accounting=p['current_settlement_summary'];operating=p['current_operating_totals'];holding=p['current_holding_sale_totals']
    nominal=p['current_nominal_insurance_totals']
    text(280,421,'Gasto del seguro: '+compact(None if nominal is None else nominal['allocated_expense']),7,232,refs=['/current_nominal_insurance_totals/allocated_expense'])
    text(280,408,'Pagos operativos: '+compact(None if nominal is None else nominal['cash_by_cut_bucket']['before_cut']),7,232,refs=['/current_nominal_insurance_totals/cash_by_cut_bucket/before_cut'])
    for i,(label,key)in enumerate((('Payable antes','before_payables'),('Pago en cierre','settlement_cash'),('Payable despues','after_payables'))):
        text(280,395-i*13,label+': '+compact(None if accounting is None else accounting[key]),7,232,refs=['/current_settlement_summary/'+key])
    text(280,356,'Prepago antes / despues: '+compact(None if accounting is None else accounting['before_prepaid'])+' / '+compact(None if accounting is None else accounting['after_prepaid']),7,232,refs=['/current_settlement_summary/before_prepaid','/current_settlement_summary/after_prepaid'])
    text(280,344,'Caja final operativa: '+compact(None if operating is None else operating['closing_free_cash_claim']),7,232,refs=['/current_operating_totals/closing_free_cash_claim'])
    text(280,330,'Otros usos de venta: '+compact(None if holding is None else holding['closing_other_uses']),7,232,refs=['/current_holding_sale_totals/closing_other_uses'])
    rent=p['current_rental_totals'];policies=p['current_policy_totals']
    text(280,316,'Renta: '+compact(None if rent is None else rent['effective_rent'])+' | polizas: '+('Pte'if policies is None else str(policies['policy_count'])),6.2,232,refs=['/current_rental_totals','/current_policy_totals'])
    text(280,294,'REFERENCIA DEL PROYECTO',8,232,True)
    norm=None if s is None else s['normalized_story']
    text(280,278,'Base aportes: '+compact(None if norm is None else norm['basis_amount']),7,232,refs=[STORY+'/normalized_story/basis_amount'])
    text(280,264,'Por '+compact(None if norm is None else norm['reference_amount'])+' aportado: cobros '+compact(None if norm is None else norm['total_distributions']),7,232,refs=[STORY+'/normalized_story'])
    text(280,250,'Neto escalado: '+compact(None if norm is None else norm['net_cash_profit']),7,232,refs=[STORY+'/normalized_story/net_cash_profit'])
    text(280,236,'Escala agregada; reparto personal pendiente.',6.1,232)
    text(280,214,'CAPITAL / EQUITY RETENIDO',8,232,True)
    stocks=[]if s is None else s['capital_snapshots'];latest=max(stocks,key=lambda r:r['as_of_date'])if stocks else None
    # With unresolved stock blockers, do not display a declared snapshot as a current verified amount.
    stock_pending=latest is None or any(b.startswith('snapshot:'+latest['as_of_date']+':')or b=='capital_and_retained_equity_snapshots_missing'for b in s['story_blockers'])
    text(280,199,'Capital declarado: '+compact(None if stock_pending else latest['capital_still_invested']),6.8,232,refs=[STORY+'/capital_snapshots'])
    text(280,185,'Equity retenido (no caja): '+compact(None if latest is None or stock_pending else latest['retained_equity_value']),6.8,232,refs=[STORY+'/capital_snapshots'])
    text(532,440,'CAJA ANUAL | A / C / NETO / OP / CoC',7.5,232,True)
    text(532,427,'A=aportes; C=cobros; OP=operacion',6.2,232)
    if s is None:text(532,411,'Cifras anuales pendientes.',7,232)
    for i,row in enumerate(years):
        value=str(row['calendar_cash_receipt_year'])+' A'+compact(row['gross_contributions'])+' C'+compact(row['gross_distributions'])+' N'+compact(row['net_equity_cash'])+' OP'+compact(row['operating_distributions_only'])+' CoC:'+('Pte'if row['conditional_coc']is None else compact(row['conditional_coc']))
        text(532,411-i*13,value,6.1,232,refs=[STORY+'/annual_cash_receipts/'+str(i)])
    text(532,244,'CoC condicionado a base anual suministrada.',6.1,232)
    text(532,224,'RIESGOS DE CAJA',8,232,True);risk=p['current_risk_observations']
    for i,(label,key)in enumerate((('No recuperado al corte','cash_shortfall_at_horizon'),('Pico neto por fecha','peak_cumulative_net_equity_funding_at_date_close'),('Venta / cobros (fraccion)','sale_share_of_distributions'))):
        text(532,208-i*13,label+': '+compact(None if risk is None else risk[key]),6.5,232,refs=['/current_risk_observations/'+key])
    text(28,164,'DIEZ CRITERIOS PENDIENTES | Umbrales no suministrados; no es una comparacion PASS/FAIL.',7.5,736,True)
    for i,row in enumerate(p['criterion_slots']):text(28+(i%5)*148,150-(i//5)*12,LABELS[row['metric_id']]+': Pte',6.3,144,refs=['/criterion_slots/'+str(i)])
    gate=p['blockers'];count_calc=sum(len(v)for v in gate['calculation'].values())
    text(28,122,'Fuentes: '+str(p['source_requirements_checked'])+' | bloqueos puerta '+str(len(gate['gate']))+' / evidencia '+str(len(gate['evidence']))+' / calculo '+str(count_calc),7,736,refs=['/source_requirements_checked','/blockers'])
    text(28,110,'55 campos: adaptador pendiente. Motivos, eventos y fracciones completos en current-results.json.',6.5,736)
    text(28,98,'Retorno personal pendiente; deficit de caja al corte no equivale a perdida economica final.',6.5,736)
    text(28,86,'Redondeo monetario 4 decimales mitad par; TIR exterior ampliada. Sin tolerancia financiera adoptada.',6.2,736)
    text(28,71,'Entrada SHA256: '+p['source_sha256'],5.8,736,refs=['/source_sha256']);text(28,60,'Resultado T110 SHA256: '+run.sha256,5.8,736)
    text(28,40,'PRUEBA SINTETICA. No usar como dictamen, aprobacion de inversion o autorizacion para Full UW.',7,736,True)
    pdf=_pdf(commands);manifest=dict(component='T110-report',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        pdf_engine_sha256=PDF_ENGINE_SHA256,format_engine_sha256=FORMAT_ENGINE_SHA256,input_sha256=p['source_sha256'],result_sha256=run.sha256,
        pdf_sha256=sha(pdf),display_spans=spans,event_groups=g,event_count=0 if s is None else len(s['events']),annual_years=[r['calendar_cash_receipt_year']for r in years],
        annual_rows_omitted=0,all_source_events_grouped_exactly_once=True,individual_event_calendar_in_pdf=False,grouped_ranges_imply_frequency=False,
        page_count_by_construction=1,all_current_money_withheld=s is None,financial_values_recalculated=False,personal_return_verified=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(manifest);return V1Report(pdf,value,digest(value))


def render_phased_settled_output(raw,run):
    if type(run)is not PhasedSettledRun or assemble_phased_settled_output(raw)!=run:raise ValidationError('settled one-page output requires complete exact current-source replay')
    return _render_verified(run)
