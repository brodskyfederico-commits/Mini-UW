"""T86 bounded one-page synthetic executive output, only from a replayed v1 run."""
from dataclasses import dataclass
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path
import hashlib
import json

from .drafts import ValidationError,canonical,digest
from .debt_service import _fraction
from .v1_case import MiniUWV1Run,run_v1_case
from .synthetic_onepager import _pdf,_pdf_string,PreviewLayoutError,ENGINE_SHA256 as PDF_UTILITY_ENGINE_SHA256

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
LABELS={'YoC':'YoC','spread':'Spread','equity_recovered':'Equity recuperado','equity_cash_in':'Equity cash-in',
        'breakeven_occupancy':'Ocupacion equilibrio','post_refi_CoC':'CoC pos-refi','equity_TDC':'Equity/TDC',
        'equity_multiple':'EM','IRR':'IRR anual','asking_relative_to_supported_price':'Asking/precio soportado'}
EVENTS={'initial_capital':'Aporte inicial','additional_capital':'Aporte adicional','operating_distribution':'Cobro operativo',
        'net_sale_distribution':'Cobro venta','net_refinance_distribution':'Cobro refi','refinance_cash_in':'Cash-in refi','other_distribution':'Otro cobro'}


def amount(value):
    if value is None:return 'Pendiente'
    f=_fraction(value,1300)
    with localcontext()as ctx:
        ctx.prec=1400
        rounded=(Decimal(f.numerator)/Decimal(f.denominator)).quantize(Decimal('.0001'),rounding=ROUND_HALF_EVEN)
    if rounded==0 and f!=0:return 'no cero (<0.0001)'
    return format(rounded,'f')


def annual_irr(roots):
    if not roots:return 'Pendiente'
    if len(roots)!=1:return 'Ambigua: '+str(len(roots))+' raices'
    r=roots[0]
    if r['exact_annual_rate']is not None:
        f=_fraction(r['exact_annual_rate'],1300)*100
        # Exact rate shown as outward two-decimal percentage bounds as well.
        lo=hi=f
    else:
        i=r['annual_rate_interval'];lo=_fraction(i['lower'],1300)*100;hi=_fraction(i['upper'],1300)*100
    lower=(lo*100).__floor__();upper=(hi*100).__ceil__()
    def pct(n):return ('-'if n<0 else'')+str(abs(n)//100)+'.'+str(abs(n)%100).zfill(2)
    return pct(lower)+'..'+pct(upper)+'%'


@dataclass(frozen=True)
class V1Report:
    pdf_bytes:bytes
    manifest_json:str
    manifest_sha256:str

    @property
    def manifest(self):return json.loads(self.manifest_json)


def _render_verified(run):
    p=run.payload;s=p['current_project_return_story'];commands=[];spans=[]
    def text(x,y,value,size=8,width=736,bold=False,refs=()):
        encoded=_pdf_string(value)
        if len(value)*size*.6>width or x<24 or x+width>768 or y<25 or y+size>588:
            raise PreviewLayoutError('v1 one-page layout budget exceeded; no clipping allowed')
        commands.append(f'BT /{"F2"if bold else"F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+encoded+b') Tj ET')
        spans.append(dict(text=value,x=x,y=y,font_size=size,width=width,result_pointers=list(refs)))
    commands.append(b'0.06 0.17 0.25 rg 24 524 744 64 re f 1 1 1 rg')
    text(36,566,p['title'],15,width=720,bold=True,refs=['/title'])
    text(36,546,'PENDIENTE | Mini-UW v1 - integracion sintetica',10,width=720,bold=True,refs=['/decision'])
    text(36,532,'Sin despliegue, decision real ni aprobacion profesional.',7.5,width=720)
    commands.append(b'0.06 0.17 0.25 rg')
    text(28,510,'Caso: '+p['case_id']+' | Revision: '+str(p['case_revision']),7,width=736,refs=['/case_id','/case_revision'])
    text(28,498,'Evaluacion de prueba UTC: '+p['evaluated_as_of_UTC']+' | Alcance: equity agregado del proyecto',7,width=736,refs=['/evaluated_as_of_UTC'])
    fields=[('Aportes brutos','gross_contributions'),('Cobros brutos','gross_distributions'),('Resultado de caja','net_cash_profit'),('Equity Multiple','equity_multiple')]
    for i,(label,key)in enumerate(fields):
        x=28+i*184;text(x,476,label,8,width=178,bold=True)
        text(x,457,amount(None if s is None else s[key]),12,width=178,bold=True,refs=['/current_project_return_story/'+key])
    text(28,445,'Proyeccion sintetica condicionada; formulario original y validacion financiera pendientes.',6.5,width=736)
    text(28,436,'APORTES Y COBROS CON FECHAS'+(' ('+s['currency']+')'if s else''),8.5,width=386,bold=True)
    if s is None:
        text(28,416,'Cifras actuales pendientes por fuentes/calculo.',8,width=386)
        text(28,402,'No se sustituyen por cero ni por historia vencida.',7.5,width=386)
    else:
        events=sorted(enumerate(s['dated_events']),key=lambda row:row[1]['date'])
        if len(events)>10:raise PreviewLayoutError('more than ten gross dated events exceed v1 page budget')
        for i,(j,e)in enumerate(events):
            text(28,419-i*13,e['date']+'  '+EVENTS[e['category']],7,width=258,refs=['/current_project_return_story/dated_events/'+str(j)])
            text(292,419-i*13,amount(e['amount']),7,width=122,refs=['/current_project_return_story/dated_events/'+str(j)+'/amount'])
    text(432,436,'METRICA / VALOR / CRITERIO (P/F)',8.5,width=332,bold=True)
    for i,m in enumerate(p['metrics']):
        mid=m['metric_id'];value=amount(m['value'])
        if mid=='IRR'and s is not None:value=annual_irr(s['annual_irr_roots'])
        text(432,419-i*13,LABELS[mid],6.8,width=142,refs=['/metrics/'+str(i)+'/metric_id'])
        text(575,419-i*13,value,6.6,width=96,refs=['/metrics/'+str(i)+'/value']if mid!='IRR'else['/current_project_return_story/annual_irr_roots'])
        c=m['criterion'];condition='Pendiente'
        if c['source_ref']is not None and c['unit']is not None and all(c[k]['operator']is not None and c[k]['threshold']is not None for k in ('pass_condition','fail_condition')):
            def compact(v):
                text_value=amount(v)
                return text_value.rstrip('0').rstrip('.')if '.'in text_value and text_value[-1]=='0'else text_value
            condition='P'+c['pass_condition']['operator']+compact(c['pass_condition']['threshold'])+'/F'+c['fail_condition']['operator']+compact(c['fail_condition']['threshold'])
        text(674,419-i*13,condition,6.5,width=90,refs=['/metrics/'+str(i)+'/criterion'])
    text(432,281,'IRR: limites % ampliados solo para presentacion.',6.5,width=332)
    text(432,271,'Todas las raices/intervalos exactos en results.json.',6.5,width=332)
    text(28,269,'BASE DECLARADA / REFI',8,width=386,bold=True)
    norm=None if s is None else s['normalized_story']
    if norm:
        text(28,255,'Referencia '+amount(norm['reference_amount'])+' sobre base '+amount(norm['basis_amount']),7,width=386,refs=['/current_project_return_story/normalized_story'])
        text(28,243,'Cobros '+amount(norm['total_distributions'])+' | Resultado '+amount(norm['net_cash_profit']),7,width=386,refs=['/current_project_return_story/normalized_story'])
    else:text(28,255,'Normalizacion pendiente; sin base automatica.',7,width=386)
    categories={}if s is None else s['cash_by_category']
    text(28,229,'Cobro refi: '+amount(categories.get('net_refinance_distribution'))+' | Cash-in: '+amount(categories.get('refinance_cash_in')),7,width=386,refs=['/current_project_return_story/cash_by_category'])
    text(432,252,'CAPITAL / CAJA ANUAL',8,width=332,bold=True)
    stocks=[]if s is None else s['capital_snapshots']
    if stocks:
        last=max(stocks,key=lambda r:r['as_of_date'])
        text(432,239,'Corte '+last['as_of_date']+': capital '+amount(last['capital_still_invested']),6.8,width=332,refs=['/current_project_return_story/capital_snapshots'])
        text(432,228,'Equity retenido (no caja): '+amount(last['retained_equity_value']),6.8,width=332,refs=['/current_project_return_story/capital_snapshots'])
    else:text(432,239,'Capital remanente / equity retenido: pendientes.',6.8,width=332)
    years=[]if s is None else s['annual_cash_receipts']
    if len(years)>3:raise PreviewLayoutError('annual rows exceed v1 page budget')
    for i,y in enumerate(years):
        text(432,214-i*11,str(y['calendar_cash_receipt_year'])+': operacion '+amount(y['operating_distributions_only'])+' | CoC '+amount(y['conditional_coc']),6.7,width=332,refs=['/current_project_return_story/annual_cash_receipts/'+str(i)])
    text(28,207,'RIESGOS Y ALCANCE',8,width=386,bold=True)
    risk={}if s is None else s['risk_observations']
    text(28,193,'Aportes no recuperados al corte: '+amount(risk.get('cash_shortfall_at_horizon')),7,width=386,refs=['/current_project_return_story/risk_observations/cash_shortfall_at_horizon'])
    text(28,181,'Pico de financiacion equity: '+amount(risk.get('peak_cumulative_net_equity_funding_at_date_close')),7,width=386,refs=['/current_project_return_story/risk_observations/peak_cumulative_net_equity_funding_at_date_close'])
    text(28,169,'Cobros de venta / total (fraccion): '+amount(risk.get('sale_share_of_distributions')),7,width=386,refs=['/current_project_return_story/risk_observations/sale_share_of_distributions'])
    text(28,154,'Retorno personal pendiente; no equivale a perdida economica final.',6.8,width=736)
    text(28,143,'Contratos, impuestos, entregas, cobros y liquidez intraperiodo sin acreditar.',6.8,width=736)
    summary=p['input_catalog_summary'];blockers=p['blockers']
    text(28,126,'FORMATO: '+str(summary['bound'])+'/55 vinculados; '+str(summary['pending'])+' pendientes. Decision: PENDIENTE.',8,width=736,bold=True,refs=['/input_catalog_summary','/decision'])
    text(28,113,'Bloqueos: campos '+str(len(blockers['input_catalog']))+' | calculo/fuentes '+str(len(blockers['projection']))+' | incidencias de criterio '+str(len(blockers['criteria']))+' | alcance '+str(len(blockers['financial_scope'])),7,width=736,refs=['/blockers'])
    text(28,101,'Detalle completo en results.json: campos, diez criterios, TDC/RLV/equilibrio y bases pendientes.',6.8,width=736)
    text(28,86,'Redondeo: 4 decimales mitad par; no cero pequeno se senala. No define tolerancia financiera.',6.5,width=736)
    text(28,71,'Entrada SHA256: '+p['case_source_sha256'],5.8,width=736,refs=['/case_source_sha256'])
    text(28,60,'Resultado SHA256: '+run.sha256,5.8,width=736)
    text(28,42,'PRUEBA SINTETICA. No usar como dictamen, aprobacion de inversion o autorizacion para Full UW.',7,width=736,bold=True)
    pdf=_pdf(commands)
    manifest=dict(component='T86',engine_sha256=ENGINE_SHA256,pdf_utility_engine_sha256=PDF_UTILITY_ENGINE_SHA256,
                  input_sha256=p['case_source_sha256'],result_sha256=run.sha256,pdf_sha256=hashlib.sha256(pdf).hexdigest(),
                  page_count_by_construction=1,display_spans=spans,rounding='four_decimals_half_even_presentation_only',
                  all_irr_roots_retained_in_results=True,financial_publication_authorized=False,decision='PENDING')
    encoded=canonical(manifest)
    return V1Report(pdf,encoded,digest(encoded))


def render_v1_report(case_raw,run):
    if type(run)is not MiniUWV1Run or run_v1_case(case_raw)!=run:
        raise ValidationError('v1 report requires exact complete source replay')
    return _render_verified(run)
