"""Nine-block Letter summary, from a source-replayed package only.

Presentation is independent of criteria adoption. Missing analyses are visible,
never replaced by zero. Historical references cannot authorize a real verdict.
"""
from copy import deepcopy
from decimal import Decimal,localcontext,ROUND_HALF_UP
from fractions import Fraction as Q
from io import BytesIO
from pathlib import Path
import json
from xml.sax.saxutils import escape
from worksheet_frontiers_D275 import fraction,rational,digest
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import read_package,verify_package,publish_current_pdf,read_current_revision,require_pdf_destination
from worksheet_return_summary_D273 import ledger_summary

SCHEMA='miniuw.synthetic-nine-block-decision-page.v1'

def amount(v,digits=2):
 if v is None:return 'PENDING'
 try:
  v=fraction(v)
  with localcontext() as ctx:
   ctx.prec=1500;value=(Decimal(v.numerator)/Decimal(v.denominator)).quantize(Decimal(10)**-digits,rounding=ROUND_HALF_UP)
  return format(value,f',.{digits}f').replace(',','X').replace('.',',').replace('X','.')
 except (ValueError,TypeError,ZeroDivisionError):return 'PENDING'

def ratio(a,b):
 try:
  denominator=fraction(b)
  return rational(fraction(a)/denominator) if denominator>0 else None
 except (ValueError,TypeError,ZeroDivisionError):return None

def report_view(result,case,analysis,roles):
 base=case['baseline_case'] if case.get('schema')=='miniuw.synthetic-native-rental-inputs.v36' else case
 inputs=base['rent_inputs'];data=dict(schema=SCHEMA,project=inputs['deal_id'],address=inputs.get('project_address'),revision=result['revision_review'].get('current_revision') or result['revision_review'].get('designated_revision') or result['revision_review'].get('revision') or result['revision_review'].get('reference_revision'),
  case_sha256=result['case_sha256'],decision='PENDING',scenario={},metrics={},analyses=analysis,roles=roles,
  criteria_adopted=False,personal_return='PENDING · términos de reparto por confirmar',source_results_sha256=sha(__import__('miniuw_worksheet_v1').encoded(result)))
 for s in ('Base','Downside'):
  v=result['scenarios'][s];e=result['screening'].get('metric_evidence_by_scenario',{}).get(s,{})
  defs=e.get('candidate_definitions',{});mapping=result['native_mapping_review']['scenarios'][s]['rows']
  coverage={state:sum(r.get('state')==state for r in mapping) for state in sorted({r.get('state') for r in mapping})}
  stories={}
  for route,route_view in [('with_refinance',v),('without_refinance',v.get('horizon_without_refinance',{}))]:
   c=route_view.get('cash_per_usd_10');summary=ledger_summary(c,v.get('project_calendar',{}).get('equity_dates'),inputs.get('irr_certificate')) if c is not None else None
   stories[route]=dict(cash=c,summary=summary,blockers=route_view.get('blockers',[]))
  cost=e.get('cost_basis',{});closing=v.get('construction_refinance',{});loan=v.get('permanent_loan',{});fund=v.get('construction_financing',{})
  eq=fund.get('equity_funding_through_refinance');post=v.get('post_refinance_coc',{})
  def value(name):return defs.get(name,{}).get('value')
  data['metrics'][s]=dict(YoC=value('YoC'),spread=value('spread'),DSCR=ratio(v.get('capacity',{}).get('bank_noi'),loan.get('annual_sizing_service')),
   debt_yield=ratio(v.get('capacity',{}).get('bank_noi'),loan.get('requested_principal')),
   LTC=ratio(fund.get('construction_principal_payoff'),fund.get('eligible_direct_hard')),
   LTV=ratio(loan.get('requested_principal'),v.get('valuation_and_sale',{}).get('refinance_value')),
   occupancy=value('breakeven_occupancy'),equity_TDC=ratio(eq,cost.get('tdc')),CoC=post.get('annual_proof',{}).get('value'),equity_recovered=ratio(closing.get('net_equity_distribution'),eq))
  units=sum(g['units'] for g in inputs['groups'].values());nrsf=sum(g['units']*fraction(g['rentable_sf_per_unit']) for g in inputs['groups'].values())
  gsf=None
  if v.get('development_costs',{}).get('vertical_basis')=='$/GSF':gsf=v['development_costs']['vertical_quantity']
  data['scenario'][s]=dict(coverage=coverage,stories=stories,calendar=v.get('project_calendar',{}),units=units,nrsf=rational(nrsf),gsf=gsf,
   commercial_sf=v.get('construction_budget',{}).get('commercial_area_sf'),tdc=cost.get('tdc'),equity=eq,
   construction_debt=fund.get('construction_principal_payoff'),permanent_debt=loan.get('requested_principal'),
   declared_max_ltc=fund.get('ltc'),declared_max_ltv=loan.get('maximum_ltv'),declared_min_dscr=loan.get('minimum_dscr'),blockers=v.get('blockers',[]))
 return data


def render(data):
 from reportlab.pdfgen import canvas
 from reportlab.lib import colors
 from reportlab.lib.styles import ParagraphStyle
 from reportlab.platypus import Paragraph,Table,TableStyle
 from reportlab.lib.pagesizes import landscape,letter
 buffer=BytesIO();W,H=landscape(letter);c=canvas.Canvas(buffer,pagesize=(W,H),invariant=1,pageCompression=1)
 c.setTitle('Mini-UW · Hoja integral sintética');c.setSubject(data['project']);c.setAuthor('Mini-UW');navy=colors.HexColor('#153348');teal=colors.HexColor('#176A69');amber=colors.HexColor('#925909');pale=colors.HexColor('#EEF4F6')
 fields=[];left=25;right=410;width=357
 style=ParagraphStyle('cell',fontName='Helvetica',fontSize=7.4,leading=8.8,textColor=navy)
 def P(text):return Paragraph(text,style)
 def table(headers,rows,x,y,widths):
  t=Table([[P(escape(str(v))) for v in row] for row in [headers]+rows],colWidths=widths)
  t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),pale),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),1.7),('BOTTOMPADDING',(0,0),(-1,-1),1.7),('LINEBELOW',(0,0),(-1,-1),.2,colors.HexColor('#CBD8E0'))]))
  w,h=t.wrap(sum(widths),H)
  if y-h<30:raise ValueError('El contenido excede una página Letter; no se oculta ningún bloque')
  t.drawOn(c,x,y-h);return y-h-6
 def text(s,x,y,w):
  p=P(s);_,h=p.wrap(w,H)
  if y-h<28:raise ValueError('Texto fuera de una página')
  p.drawOn(c,x,y-h);return y-h-4
 def title(s,x,y):c.setFont('Helvetica-Bold',9);c.setFillColor(teal);c.drawString(x,y-9,s);return y-18
 def val(path,value,kind='money'):
  if value is None:display='PENDING'
  elif kind=='percent':
   try:display=amount(fraction(value)*100)+' %'
   except ValueError:display='PENDING'
  elif kind=='multiple':display=amount(value,3)+'x'
  elif kind=='text':display=str(value)
  else:display=amount(value)
  fields.append(dict(path=path,value=value,display=display));return display
 c.setFillColor(navy);c.rect(0,H-62,W,62,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Helvetica-Bold',15);c.drawString(left,H-23,'Mini-UW · hoja integral de resultados')
 c.setFont('Helvetica',8);name=data['project'];c.drawString(left,H-40,('SINTÉTICO · '+name)[:106]+('…' if len(name)>94 else ''));c.drawRightString(W-25,H-23,'Dictamen: PENDING')
 c.setFont('Helvetica',7.3);c.drawString(left,H-53,'Criterios por confirmar · sin despliegue · retorno personal PENDING sin términos de reparto')
 y=H-70
 base=data['scenario']['Base'];units=val('scenario/Base/units',base['units']);gsf=val('scenario/Base/gsf',base['gsf']);nrsf=val('scenario/Base/nrsf',base['nrsf']);com=val('scenario/Base/commercial_sf',base['commercial_sf'])
 y=text(f'1. Expediente · {units} unidades · GSF {gsf} · NRSF {nrsf} · comercial {com} SF · dirección: {escape(data.get("address") or "por confirmar")}',left,y,W-50)
 y=text('Cobertura (valores sintéticos, no respaldo real): '+ '; '.join(s+': '+', '.join(str(n)+' '+{'CONFIRMED_SYNTHETIC':'confirmados sintéticos','NOT_APPLICABLE':'no aplican','PENDING':'pendientes'}.get(k,'por revisar') for k,n in data['scenario'][s]['coverage'].items()) for s in ('Base','Downside')),left,y,W-50)
 start=y;yl=title('2. Caja por USD 10 iniciales · equity agregado',left,start)
 columns=[('Base','with_refinance'),('Base','without_refinance'),('Downside','with_refinance'),('Downside','without_refinance')];rows=[]
 for label,key in [('Inicial','reference_amount'),('Adicional','additional'),('Total aportado','total_contributions'),('Cobro refi','net_refinance_distribution'),('Cobros operación','operating_distribution'),('Cobro venta neta','net_sale_distribution'),('Total cobrado','total_distributions'),('Sin recuperar','unrecovered_after_sale'),('Múltiplo','equity_multiple'),('TIR anual','irr'),('Primer recupero','payback')]:
  row=[label]
  for s,r in columns:
   story=data['scenario'][s]['stories'][r];cash=story['cash'];summary=story['summary'];v=None;kind='money'
   if cash is not None:
    if key=='additional':v=rational(fraction(cash['total_contributions'])-10)
    elif key=='payback':v=summary.get('payback_date') if summary else None;v=v or ('No recuperado' if summary and not summary['blockers'] else 'PENDING');kind='text'
    elif key in ('net_refinance_distribution','operating_distribution','net_sale_distribution'):
     prefix={'net_refinance_distribution':'refinance-','operating_distribution':'operation-','net_sale_distribution':'sale-'}[key]
     events=[e for e in cash['events'] if (e['category']==key or e['event_id'].startswith(prefix)) and e['kind']=='distribution']
     v=rational(sum((fraction(e['amount']) for e in events),Q())) if events else None
     if key=='net_refinance_distribution' and r=='without_refinance':v='N/A';kind='text'
    elif key=='irr':
     from worksheet_irr_D122 import display_enclosure
     enclosure=None if summary is None else summary['irr_annual'].get('annual_enclosure');v=display_enclosure(enclosure) if enclosure else 'PENDING · raíz';kind='text'
    else:v=cash.get(key);kind='multiple' if key=='equity_multiple' else 'money'
   row.append(val('scenario/'+s+'/'+r+'/'+key,v,kind))
  rows.append(row)
 yl=table(['Concepto','Base refi','Base sin','Down refi','Down sin'],rows,left,yl,[93,66,66,66,66])
 yl=text('Cobros operativos trimestrales. Refi al estabilizar; venta en las fechas del calendario. Aportes y cobros por fecha: expediente y Excel de cotejo.',left,yl,width)
 yl=title('3. Métricas · referencia histórica no vigente',left,yl)
 metric_rows=[]
 for key,label,kind,reference in [('YoC','YoC (NOI_uw)','percent','6,50 / 5,75 %'),('spread','Spread compatible','money','100 / 50 bps'),('DSCR','DSCR bancario','multiple','Term sheet'),('debt_yield','Debt yield','percent','Term sheet'),('LTC','LTC efectivo','percent','Límite contractual'),('LTV','LTV efectivo','percent','Límite contractual'),('occupancy','Equilibrio económico','percent','85 / 90 %'),('equity_TDC','Equity / TDC','percent','35 / 40 %'),('CoC','CoC posrefi anual','percent','6,0 / 4,0 %'),('equity_recovered','Equity recuperado refi','percent','60 / 40 %')]:
  metric_rows.append([label,*[val('metrics/'+s+'/'+key,data['metrics'][s][key],kind) for s in ('Base','Downside')],reference,'Por confirmar'])
 yl=table(['Métrica','Base','Down','Referencia B/D','Estado'],metric_rows,left,yl,[100,48,48,83,78])
 yl=text('Equilibrio físico: PENDING si C14 no tiene desglose. YoC y cap comparables deben usar la misma base. El dato faltante no se convierte en cero.',left,yl,width)
 yr=title('4. Fronteras matemáticas · no son umbrales',right,start)
 matrix=data.get('analyses',{}).get('breakeven_matrix',{});front=[]
 def boundary(record):
  state=record.get('state')
  if state=='BEYOND_SEARCH_RANGE':return '> '+amount(record.get('lower_bound'))
  if state=='BASELINE_BREACHED':return 'Ya cruza'
  if state=='BOUNDED':return amount(record.get('safe_movement'))+'–'+amount(record.get('breached_movement'))
  return 'PENDING'
 from worksheet_frontiers_D275 import DRIVERS
 names=dict(residential_rent='Renta · fracción',exit_cap='Cap salida · bps',vertical_cost='Obra · fracción',interest='Tasa · bps',lease_up='Lease-up · meses',vacancy='Vacancia · pp')
 for driver in DRIVERS:
  row=[names[driver]]
  for s in ('Base','Downside'):
   for f in ('F1','F2','F3'):
    record=matrix.get(s,{}).get('with_refinance',{}).get(driver,{}).get(f,{})
    value=boundary(record);fields.append(dict(path='analyses/breakeven_matrix/'+s+'/with_refinance/'+driver+'/'+f,value=record,display=value));row.append(value)
  front.append(row)
 yr=table(['Driver','B F1','B F2','B F3','D F1','D F2','D F3'],front,right,yr,[102]+[42.5]*6)
 yr=text('F1: múltiplo 1x · F2: DSCR 1x · F3: refi vs payoff y cierre. Rangos y resolución explícitos en el expediente. Ya cruza: caso inicial fuera de la frontera. F4 en el anexo.',right,yr,width)
 yr=title('5. Precio del terreno · metas del usuario',right,yr)
 price=data.get('analyses',{}).get('price_grid')
 if not isinstance(price,dict) or not all('price_grid' in price.get(s,{}) for s in ('Base','Downside')):
  yr=text('Grilla: PENDING · análisis no incorporado. RLV de la casa: criterio por confirmar.',right,yr,width)
 else:
  from worksheet_irr_D122 import display_enclosure
  pr=[]
  for i in range(5):
   pair={}
   for s in ('Base','Downside'):
    points=price[s]['price_grid'];index=round(i*(len(points)-1)/4);point=points[index];values=point.get('values') or {}
    interval=values.get('annual_irr');ir='PENDING'
    if interval is not None:
     a,b=amount(fraction(interval['lower'])*100,1),amount(fraction(interval['upper'])*100,1)
     if a==b:ir=a
    pair[s]=[amount(fraction(point['price'])/1000000,3) if point.get('price') is not None else 'PENDING',ir,amount(values.get('equity_multiple'),3),amount(fraction(values['yoc'])*100) if values.get('yoc') is not None else 'PENDING',amount(fraction(values['equity_tdc'])*100) if values.get('equity_tdc') is not None else 'PENDING']
    fields.append(dict(path='analyses/price_grid/'+s+'/'+str(index),value=point,display=pair[s]))
   pr.append(['PENDING' if pair['Base'][j]==pair['Downside'][j]=='PENDING' else pair['Base'][j]+'/'+pair['Downside'][j] for j in range(5)])
  yr=table(['P ~MUSD B/D','TIR ~% B/D','EM B/D','YoC % B/D','Eq/TDC % B/D'],pr,right,yr,[68,85,60,72,72])
  maxima=[]
  for scenario in ('Base','Downside'):
   record=price[scenario].get('max_price_for_targets',{});value=record.get('price');state=record.get('state')
   display=('> USD '+amount(price[scenario].get('configuration',{}).get('upper'))) if state=='BEYOND_GRID' else ('USD '+amount(value)) if value is not None else 'PENDING'
   fields.append(dict(path='analyses/price_grid/'+scenario+'/max_price_for_targets',value=record,display=display));maxima.append(scenario+' '+display)
  yr=text('Meta de ensayo EM >= 1: '+ '; '.join(maxima)+'. Sin criterio de Lorena. TIR con raíz certificada; RLV de la casa: PENDING.',right,yr,width)
 yr=title('6. Tornado · seis drivers, shocks declarados',right,yr)
 tornado=data.get('analyses',{}).get('tornado',{}).get('tornado',{});tr=[]
 for driver in DRIVERS:
  row=[names[driver]]
  for s in ('Base','Downside'):
   records=tornado.get(s,{}).get('with_refinance',[]);record=next((v for v in records if v['driver']==driver),None)
   if record and record.get('state')=='CALCULATED':
    v=record['irr_impact'];lo=fraction(v['lower'])*10000;hi=fraction(v['upper'])*10000
    display=amount(Q(lo.numerator//lo.denominator,100))+'–'+amount(Q(-((-hi.numerator)//hi.denominator),100))+' pp'
   else:display='PENDING · visible'
   fields.append(dict(path='analyses/tornado/'+s+'/'+driver,value=record,display=display));row.append(display)
  tr.append(row)
 yr=table(['Impacto máximo |ΔTIR|','Base','Downside'],tr,right,yr,[153,102,102])
 yr=title('7. Fuentes, usos y calendario',right,yr)
 for s in ('Base','Downside'):
  v=data['scenario'][s];cal=v['calendar'];tdc=val('scenario/'+s+'/tdc',v['tdc']);eq=val('scenario/'+s+'/equity',v['equity']);debt=val('scenario/'+s+'/construction_debt',v['construction_debt']);perm=val('scenario/'+s+'/permanent_debt',v['permanent_debt']);perunit=val('scenario/'+s+'/tdc_per_unit',ratio(v['tdc'],v['units']));persf=val('scenario/'+s+'/tdc_per_gsf',ratio(v['tdc'],v['gsf']))
  yr=text(f'{s}: TDC USD {tdc} ({perunit}/unidad; {persf}/GSF) · equity USD {eq} · obra USD {debt} · permanente USD {perm}. Compra {cal.get("purchase_date","PENDING")} → fin {cal.get("construction_finish","PENDING")} → estable/refi {cal.get("stabilization_date","PENDING")} → venta {cal.get("sale_date","PENDING")}.',right,yr,width)
 bottom=min(yl,yr)-1
 bottom=title('8. Banderas y responsables',left,bottom)
 flags='; '.join(s+': '+('sin bloqueos de caja en este ensayo' if not data['scenario'][s]['blockers'] else 'PENDING · capacidad, dato o evidencia pendiente; ver expediente') for s in ('Base','Downside'))
 role_labels={'official_evidence_custodian':'custodio','criteria_owner':'criterios','financial_reviewer':'revisor','authorized_approver':'aprobador'}
 owners='; '.join(label+': '+(data.get('roles',{}).get('roles',{}).get(role,{}).get('name') or 'por designar') for role,label in role_labels.items())
 bottom=text(escape(flags)+' · Reparto / aprobación reales: PENDING. '+escape(owners)+'. Identidad y autoridad por acreditar.',left,bottom,W-50)
 c.setStrokeColor(colors.HexColor('#CBD8E0'));c.line(25,25,W-25,25);c.setFillColor(navy);c.setFont('Helvetica',7)
 c.drawString(25,14,'9. Revisión '+str(data.get('revision') or 'por confirmar')[:48]+' · caso '+data['case_sha256'][:12]+' · No es un dictamen de inversión')
 c.drawRightString(W-25,14,'Datos sintéticos · una página');c.save();return buffer.getvalue(),fields


def deliver(package,output,current_revision,analysis,roles):
 require_pdf_destination(package,output,current_revision);current=read_current_revision(current_revision,package)
 saved=read_package(package);result=json.loads(saved['results.json']);audit=verify_package(package,current_revision_raw=current)
 if audit['vigencia']!='VIGENTE' or result.get('critical_evidence_review',{}).get('status')!='PASSED':raise ValueError('PENDING: fuente no auditada o revisión anterior; bloquear PDF integral')
 if analysis is None:analysis={}
 elif isinstance(analysis,(str,Path)):
  from worksheet_analysis_replay_D275 import replay
  analysis=replay(Path(analysis))
  if analysis['baseline_results_sha256']!=sha(saved['results.json']):raise ValueError('El análisis no corresponde al mismo expediente financiero')
 else:raise ValueError('El análisis requiere expedientes fuente auditados; no se acepta una tabla de resultados sin respaldo')
 data=report_view(result,json.loads(saved['case.json']),analysis,roles);pdf,fields=render(data)
 # Rebuild the view and PDF from source-replayed results; no hand-edited number.
 again,again_fields=render(report_view(json.loads(saved['results.json']),json.loads(saved['case.json']),analysis,roles))
 if pdf!=again or fields!=again_fields:raise ValueError('El renderer no reproduce los datos del expediente')
 publish_current_pdf(package,saved,current_revision,current,output,pdf)
 return dict(schema=SCHEMA,state='DELIVERED_SYNTHETIC',current_revision_sha256=sha(current),case_sha256=sha(saved['case.json']),
  source_results_sha256=sha(saved['results.json']),analysis_sha256=digest(analysis),pdf_sha256=sha(pdf),view=data,rendered_fields=fields,
  decision='PENDING',deployment_enabled=False)
