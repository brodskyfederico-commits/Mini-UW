"""T99 exhaustive category/annual presentation, from the replayed T98 view."""
from fractions import Fraction
from pathlib import Path

from .drafts import ValidationError,canonical,digest
from .capital_checked_output import (CapitalCheckedRun,assemble_capital_checked_output,
    ENGINE_SHA256 as CAPITAL_ENGINE_SHA256,DEFINITION as CAPITAL_DEFINITION)
from .debt_service import _fraction,rational
from .operating_noi import _bounded
from .scheduled_expense_case import sha
from .synthetic_onepager import _pdf,_pdf_string,PreviewLayoutError,ENGINE_SHA256 as PDF_ENGINE_SHA256
from .v1_report import V1Report,amount,annual_irr,LABELS,EVENTS,ENGINE_SHA256 as FORMAT_ENGINE_SHA256

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T99.md'
STORY='/current_project_return_story'
MAX_ANNUAL_ROWS=12
ORDER=('initial_capital','additional_capital','refinance_cash_in','net_refinance_distribution',
       'operating_distribution','net_sale_distribution','other_distribution')


def compact(value):
    text=amount(value)
    return text.rstrip('0').rstrip('.') if '.' in text and text.endswith('0') else text


def _groups(story):
    if story is None:return []
    events=story['dated_events']
    if len(events)>256:raise PreviewLayoutError('T99 source event budget exceeded')
    if any(e['category']not in ORDER for e in events):raise ValidationError('exact known category inventory required')
    groups=[];gross_a=gross_c=Fraction(0)
    for category in ORDER:
        indices=[i for i,e in enumerate(events)if e['category']==category]
        total=Fraction(0)
        for i in indices:total=_bounded(total+_fraction(events[i]['amount'],1300))
        if rational(total)!=story['cash_by_category'][category]:raise ValidationError('group differs from current gross category total')
        if category in ORDER[:3]:gross_a=_bounded(gross_a+total)
        else:gross_c=_bounded(gross_c+total)
        days=[events[i]['date']for i in indices]
        groups.append(dict(category=category,amount=rational(total),event_indices=indices,event_count=len(indices),
            zero_event_count=sum(_fraction(events[i]['amount'],1300)==0 for i in indices),
            first_date=min(days)if days else None,last_date=max(days)if days else None,
            result_pointers=[STORY+'/cash_by_category/'+category]+[STORY+'/dated_events/'+str(i)for i in indices]))
    if rational(gross_a)!=story['gross_contributions']or rational(gross_c)!=story['gross_distributions']:
        raise ValidationError('gross presentation totals do not reconcile')
    return groups


def _render_verified(run):
    p=run.payload;s=p['current_project_return_story'];groups=_groups(s)
    years=[]if s is None else s['annual_cash_receipts']
    if len(years)>MAX_ANNUAL_ROWS:raise PreviewLayoutError('T99 annual inventory exceeds twelve-row budget; no years omitted')
    commands=[b'0.06 0.17 0.25 rg 24 524 744 64 re f 1 1 1 rg'];spans=[]
    def text(x,y,value,size=7,width=232,bold=False,refs=()):
        if len(value)*size*.6>width or x<24 or x+width>768 or y<25 or y+size>588:
            raise PreviewLayoutError('T99 span exceeds explicit one-page budget; no clipping')
        encoded=_pdf_string(value)
        commands.append(f'BT /{"F2"if bold else"F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+encoded+b') Tj ET')
        spans.append(dict(text=value,x=x,y=y,font_size=size,width=width,result_pointers=list(refs)))
    text(36,566,p['title'],15,720,True,['/title'])
    text(36,546,'PENDIENTE | Mini-UW sintetico - equity agregado del proyecto',10,720,True,['/decision'])
    text(36,532,'Sin despliegue, decisiones reales ni aprobacion profesional.',7.5,720)
    commands.append(b'0.06 0.17 0.25 rg')
    text(28,510,'Caso '+p['case_id']+' | Revision '+str(p['case_revision']),7,736,refs=['/case_id','/case_revision'])
    context='UTC '+p['evaluated_as_of_UTC']
    context+=(' | Moneda '+s['currency']+' | Ventana '+s['cash_horizon']['start']+' a '+s['cash_horizon']['end'])if s else' | Moneda y ventana actuales: pendientes'
    text(28,498,context,7,736,refs=['/evaluated_as_of_UTC',STORY+'/currency',STORY+'/cash_horizon'])
    for i,(label,key)in enumerate((('Aportes brutos','gross_contributions'),('Cobros brutos','gross_distributions'),('Resultado de caja','net_cash_profit'),('Equity Multiple','equity_multiple'))):
        text(28+i*184,476,label,8,178,True)
        text(28+i*184,457,compact(None if s is None else s[key]),12,178,True,[STORY+'/'+key])
    text(28,440,'FLUJOS POR CONCEPTO',8,232,True)
    if s is None:
        text(28,419,'Cifras actuales pendientes por fuentes/calculo.')
    else:
        for i,g in enumerate(groups):
            y=421-i*25;refs=g['result_pointers']
            text(28,y,EVENTS[g['category']]+': '+compact(g['amount']),7,232,refs=refs)
            dates='Sin movimientos declarados'if not g['event_count']else(g['first_date']+' a '+g['last_date']+' | n='+str(g['event_count']))
            text(28,y-11,dates,6.1,232,refs=refs)
    text(28,243,'Resumen por concepto; calendario completo en evidencia.',6.3,232)
    text(28,232,'Rango de fechas no implica frecuencia ni cobro unico.',6.3,232)
    text(28,215,'REFERENCIA DEL PROYECTO',8,232,True)
    norm=None if s is None else s['normalized_story'];ref=STORY+'/normalized_story'
    if norm:
        text(28,201,'Referencia '+compact(norm['reference_amount'])+' / base '+compact(norm['basis_amount']),6.8,232,refs=[ref])
        text(28,189,'A '+compact(norm['total_contributions'])+' | C '+compact(norm['total_distributions'])+' | N '+compact(norm['net_cash_profit']),6.5,232,refs=[ref])
    else:text(28,201,'Normalizacion pendiente; sin base automatica.',6.8)
    text(28,171,'CAPITAL / VALOR RETENIDO',8,232,True)
    latest=p['latest_capital_snapshot_index']
    if s is not None and latest is not None:
        stock=s['capital_snapshots'][latest];refs=[STORY+'/capital_snapshots/'+str(latest),'/capital_visibility/'+str(latest)]
        text(28,157,'Corte declarado: '+stock['as_of_date'],6.8,232,refs=refs)
        text(28,145,'Capital declarado: '+compact(stock['capital_still_invested']),6.8,232,refs=refs)
        text(28,133,'Valor retenido (no caja): '+compact(stock['retained_equity_value']),6.8,232,refs=refs)
    else:text(28,157,'Capital y valor retenido: pendientes.',6.8)
    text(280,440,'CAJA POR ANO DE LA VENTANA',8,232,True)
    text(280,428,'A aporte / C cobro / N neto / O operativo',6.5)
    if s is None:text(280,408,'Caja anual y CoC actuales pendientes.')
    for i,year in enumerate(years):
        y=411-i*22;ref=STORY+'/annual_cash_receipts/'+str(i)
        text(280,y,str(year['calendar_cash_receipt_year'])+' A '+compact(year['gross_contributions'])+' C '+compact(year['gross_distributions'])+' N '+compact(year['net_equity_cash']),6.7,232,refs=[ref])
        text(280,y-10,'O '+compact(year['operating_distributions_only'])+' | CoC (fraccion): '+compact(year['conditional_coc']),6.4,232,refs=[ref])
    text(280,133,'Ventana de caja; no ano operativo certificado.',6.3)
    text(528,440,'METRICAS / CRITERIOS',8,236,True)
    for i,m in enumerate(p['metrics']):
        y=421-i*23;mid=m['metric_id'];value=compact(m['value'])
        if mid=='IRR'and s is not None:value=annual_irr(s['annual_irr_roots'])
        text(528,y,LABELS[mid]+': '+value,6.8,236,refs=['/metrics/'+str(i),STORY+'/annual_irr_roots']if mid=='IRR'else['/metrics/'+str(i)])
        c=m['criterion'];conditions='P/F: Pendiente'
        if c['source_ref']is not None and c['unit']is not None and all(c[k]['operator']is not None and c[k]['threshold']is not None for k in ('pass_condition','fail_condition')):
            conditions='P '+c['pass_condition']['operator']+compact(c['pass_condition']['threshold'])+' / F '+c['fail_condition']['operator']+compact(c['fail_condition']['threshold'])
        text(528,y-10,conditions,6.2,236,refs=['/metrics/'+str(i)+'/criterion'])
    risk={}if s is None else s['risk_observations']
    text(528,179,'RIESGOS DE CAJA',8,236,True)
    for i,(label,key)in enumerate((('No recuperado al corte: ','cash_shortfall_at_horizon'),('Pico equity al cierre: ','peak_cumulative_net_equity_funding_at_date_close'),('Venta / cobros (fraccion): ','sale_share_of_distributions'))):
        text(528,165-i*12,label+compact(risk.get(key)),6.6,236,refs=[STORY+'/risk_observations/'+key])
    summary=p['input_catalog_summary']
    text(28,116,'FORMATO: '+str(summary['bound'])+'/55 vinculados; '+str(summary['pending'])+' pendientes. Decision: PENDIENTE.',8,736,True,['/input_catalog_summary','/decision'])
    text(28,104,'Retorno personal pendiente. Valor retenido no es caja; deficit al corte no es perdida economica final.',6.8,736)
    text(28,93,'IRR: todas las raices/intervalos en evidencia; limites % ampliados. CoC condicionado; sin base automatica.',6.5,736)
    text(28,82,'Calendario individual, ceros y fuentes completos en results.json. Redondeo 4 decimales mitad par; no define tolerancia.',6.3,736)
    text(28,69,'Entrada SHA256: '+p['case_source_sha256'],5.8,736,refs=['/case_source_sha256'])
    text(28,58,'Resultado T98 SHA256: '+run.sha256,5.8,736)
    text(28,40,'PRUEBA SINTETICA. No usar como dictamen, aprobacion de inversion o autorizacion para Full UW.',7,736,True)
    pdf=_pdf(commands)
    manifest=dict(component='T99',engine_sha256=ENGINE_SHA256,capital_engine_sha256=CAPITAL_ENGINE_SHA256,
        capital_definition_sha256=sha(CAPITAL_DEFINITION.read_bytes()),definition_sha256=sha(DEFINITION.read_bytes()),
        pdf_engine_sha256=PDF_ENGINE_SHA256,format_engine_sha256=FORMAT_ENGINE_SHA256,input_sha256=p['case_source_sha256'],
        result_sha256=run.sha256,result_component='T98',pdf_sha256=sha(pdf),display_spans=spans,event_groups=groups,
        event_count=0 if s is None else len(s['dated_events']),annual_years=[y['calendar_cash_receipt_year']for y in years],
        all_source_events_grouped_exactly_once=True,individual_event_calendar_in_pdf=False,
        grouped_date_ranges_imply_frequency=False,annual_rows_omitted=0,page_count_by_construction=1,
        capital_visibility=p['capital_visibility'],latest_capital_state=p['latest_capital_state'],
        underlying_financial_result_changed=False,new_financial_policy=False,personal_return_verified=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(manifest);return V1Report(pdf,value,digest(value))


def render_long_horizon_report(raw,run):
    if type(run)is not CapitalCheckedRun or assemble_capital_checked_output(raw)!=run:
        raise ValidationError('T99 page requires exact complete sources and current T98 view replay')
    return _render_verified(run)
