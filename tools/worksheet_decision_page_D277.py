"""D277 presentation version. D275 renderer and archived profiles stay intact."""
from io import BytesIO
from pathlib import Path
from fractions import Fraction as Q
from xml.sax.saxutils import escape
import json
from worksheet_decision_page_D275 import report_view as previous_view,amount,certified_irr_display,ratio
from worksheet_cash_attribution_D277 import reconcile_case
from worksheet_frontiers_D275 import fraction as F,rational as R,digest,DRIVERS
from miniuw_worksheet_v1 import read_package,verify_package,publish_current_pdf,read_current_revision,require_pdf_destination
from miniuw_foundation.scheduled_expense_case import sha
SCHEMA='miniuw.synthetic-nine-block-decision-page.D277.v1'
METRICS=[('YoC','YoC · NOI_uw','percent','6,50 / 5,75 %'),('spread','Spread · bps','money','100 / 50'),('equity_recovered','Recupero neto refi','percent','60 / 40 %'),('cash_in','Cash-in / equity','percent','5 / 10 %'),('occupancy','Equilibrio económico','percent','85 / 90 %'),('CoC','CoC posrefi anual','percent','6 / 4 %'),('asking_supported','Pedido/soportado - 1','percent','0 / — %'),('equity_TDC','Equity / TDC','percent','35 / 40 %'),('IRR','TIR anual','irr','15 / 12 %'),('EM','Múltiplo','multiple','1,75 / 1,50x')]


def report_view(result,case,analysis,roles):
 data=previous_view(result,case,analysis,roles);data['schema']=SCHEMA;attr=reconcile_case(result)
 for s in ('Base','Downside'):
  data['scenario'][s]['attribution']=attr['scenarios'][s];a=attr['scenarios'][s]['with_refinance'];metrics=data['metrics'][s];obs=result['computed_metrics'][s]
  metrics.update(equity_recovered=a.get('equity_recovered_net'),cash_in=a.get('cash_in_over_equity'),asking_supported=None,IRR=obs.get('IRR',{}).get('value'),EM=obs.get('equity_multiple',{}).get('value'))
 return data


def render(data):
 from reportlab.pdfgen import canvas
 from reportlab.lib import colors
 from reportlab.lib.styles import ParagraphStyle
 from reportlab.platypus import Paragraph,Table,TableStyle
 from reportlab.lib.pagesizes import landscape,letter
 b=BytesIO();W,H=landscape(letter);c=canvas.Canvas(b,pagesize=(W,H),invariant=1);c.setTitle('Mini-UW · resultado integral D277');c.setAuthor('Mini-UW');fields=[];navy=colors.HexColor('#153348');teal=colors.HexColor('#176A69');pale=colors.HexColor('#EEF4F6');style=ParagraphStyle('cell',fontName='Helvetica',fontSize=7.1,leading=8.1,textColor=navy)
 def P(t):return Paragraph(escape(str(t)),style)
 def text(t,x,y,w):
  p=P(t);_,h=p.wrap(w,H)
  if y-h<32:raise ValueError('D277 excede una página; no ocultar contenido')
  p.drawOn(c,x,y-h);return y-h-4
 def title(t,x,y):c.setFillColor(teal);c.setFont('Helvetica-Bold',9);c.drawString(x,y-9,t);return y-17
 def table(headers,rows,x,y,widths):
  t=Table([[P(v) for v in row] for row in [headers]+rows],colWidths=widths);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),pale),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),1.1),('BOTTOMPADDING',(0,0),(-1,-1),1.1),('LINEBELOW',(0,0),(-1,-1),.2,colors.HexColor('#CBD8E0'))]));_,h=t.wrap(sum(widths),H)
  if y-h<32:raise ValueError('D277 tabla excede una página')
  t.drawOn(c,x,y-h);return y-h-5
 def value(path,v,kind='money'):
  if v is None:display='PENDING'
  elif kind=='irr':display=certified_irr_display(v)
  elif kind=='text':display=str(v)
  else:display=amount(F(v)*100 if kind=='percent' else v,2)+(' %' if kind=='percent' else 'x' if kind=='multiple' else '')
  fields.append(dict(path=path,value=v,display=display));return display
 c.setFillColor(navy);c.rect(0,H-56,W,56,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Helvetica-Bold',14);c.drawString(25,H-22,'Mini-UW · hoja integral de resultados');c.setFont('Helvetica',8);c.drawString(25,H-38,'SINTÉTICO · '+data['project']);c.drawRightString(W-25,H-22,'Dictamen: PENDING')
 b0=data['scenario']['Base'];y=text('1. Expediente · '+str(b0['units'])+' unidades · GSF '+amount(b0['gsf'])+' · NRSF '+amount(b0['nrsf'])+' · comercial '+amount(b0['commercial_sf'])+' SF. Criterios NO adoptados; retorno personal e histórico PENDING.',25,H-64,W-50);start=y;x=25;right=410;width=357
 y=title('2. Caja por USD 10 iniciales · equity agregado',x,y);cols=[(s,r) for s in ('Base','Downside') for r in ('with_refinance','without_refinance')];rows=[]
 for label,key in [('Inicial','reference_amount'),('Adicional','additional'),('Total aportado','total_contributions'),('Refi: cobro / cash-in','closing'),('Aportes posrefi','post'),('Cobros operación','operating_distribution'),('Cobro venta neta','net_sale_distribution'),('Operación: desde / hasta','operation_dates'),('Total cobrado','total_distributions'),('Depende de venta','sale_dependence'),('Sin recuperar','unrecovered_after_sale'),('Múltiplo','equity_multiple'),('TIR anual','irr'),('Primer recupero','payback')]:
  row=[label]
  for s,r in cols:
   story=data['scenario'][s]['stories'][r];cash=story['cash'];summary=story['summary'];a=data['scenario'][s]['attribution'][r];v=None;kind='money'
   if cash:
    if key=='additional':v=R(F(cash['total_contributions'])-10)
    elif key=='closing':v='N/A' if r=='without_refinance' else amount(a.get('refinance_gross_receipts'))+' / '+amount(a.get('refinance_cash_in'));kind='text'
    elif key=='operation_dates':
     dates=[e['date'] for e in cash['events'] if e['kind']=='distribution' and e['category']=='operating_distribution' and F(e['amount'])>0];v=(dates[0]+' / '+dates[-1]) if dates else 'Sin cobros';kind='text'
    elif key=='post':v=a.get('post_refinance_contributions')
    elif key in ('operating_distribution','net_sale_distribution'):
     v=R(sum((F(e['amount']) for e in cash['events'] if e['kind']=='distribution' and e['category']==key),Q()))
    elif key=='sale_dependence':v=ratio(R(sum((F(e['amount']) for e in cash['events'] if e['kind']=='distribution' and e['category']=='net_sale_distribution'),Q())),cash['total_distributions']);kind='percent'
    elif key=='irr':v=None if not summary else summary['irr_annual'].get('annual_enclosure');kind='irr'
    elif key=='payback':v=summary.get('payback_date') or 'No recuperado' if summary else None;kind='text'
    else:v=cash.get(key);kind='multiple' if key=='equity_multiple' else 'money'
   row.append(value('cash/'+s+'/'+r+'/'+key,v,kind))
  rows.append(row)
 y=table(['Concepto','Base refi','Base sin','Down refi','Down sin'],rows,x,y,[97,65,65,65,65])
 note=[]
 for s in ('Base','Downside'):
  a=data['scenario'][s]['attribution']['with_refinance']
  if a.get('post_refinance_count'):note.append(s+': '+str(a['post_refinance_count'])+' aportes '+a['post_refinance_first']+'–'+a['post_refinance_last'])
 y=text(('; '.join(note)+'. ' if note else '')+'Aportes posrefi: financiación de deuda, reservas y operación posterior; no cash-in del cierre. Múltiplo usa aportes y cobros brutos. Detalle fechado en expediente.',x,y,width)
 y=title('3. Diez métricas · referencias históricas NO VIGENTES',x,y);rows=[]
 for key,label,kind,reference in METRICS:rows.append([label,*[value('metrics/'+s+'/'+key,data['metrics'][s].get(key),kind) for s in ('Base','Downside')],reference])
 y=table(['Métrica','Base','Down','Referencia B/D'],rows,x,y,[118,68,68,103])
 y=text('Todas: criterio por confirmar. Pedido/soportado PENDING: falta RLV vigente. Equilibrio físico PENDING sin desglose de C14. Vacío nunca es cero; YoC y cap comparable deben tener la misma base de NOI.',x,y,width)
 bank=[]
 for s in ('Base','Downside'):
  m=data['metrics'][s];bank.append(s+': DSCR '+amount(m['DSCR'])+'x · LTV '+(amount(F(m['LTV'])*100) if m['LTV'] is not None else 'PENDING')+' % · DY '+(amount(F(m['debt_yield'])*100) if m['debt_yield'] is not None else 'PENDING')+' %')
 y=text('; '.join(bank),x,y,width)
 z=title('4. Fronteras matemáticas · sin adoptar umbrales',right,start);matrix=data.get('analyses',{}).get('breakeven_matrix',{});names=dict(residential_rent='Renta · %',exit_cap='Cap salida · bps',vertical_cost='Obra · %',interest='Tasa · bps',lease_up='Lease-up · meses',vacancy='Vacancia · pp');rows=[]
 def boundary(r):
  st=r.get('state');scale=100 if r.get('unit')=='relative_fraction' else 1
  def fmt(v):return amount(F(v)*scale,1)
  if st=='BASELINE_BREACHED':return 'Ya cruza'
  if st=='BEYOND_SEARCH_RANGE':return '> '+fmt(r['lower_bound'])
  if st=='BOUNDED':return fmt(r['safe_movement'])+'–'+fmt(r['breached_movement'])
  why=str(r.get('visible_reason') or r.get('reason') or 'falta análisis');why=why.replace('DEBT_YIELD','Y').replace('DSCR','D').replace('LTV','L');return 'PEND:'+why
 for driver in DRIVERS:
  row=[names[driver]]
  for s in ('Base','Downside'):
   for f in ('F1','F2','F3'):
    r=matrix.get(s,{}).get('with_refinance',{}).get(driver,{}).get(f,{});display=boundary(r);fields.append(dict(path='frontier/'+s+'/'+driver+'/'+f,value=r,display=display));row.append(display)
  rows.append(row)
 z=table(['Driver','B F1','B F2','B F3','D F1','D F2','D F3'],rows,right,z,[81]+[46]*6)
 z=text('PEND:D=DSCR, L=LTV, Y=debt yield; préstamo sobre capacidad. F1: EM 1x · F2: DSCR 1x · F3: refi cubre payoff y cierre. PENDING por capacidad mantiene préstamo fijo; no reduce deuda para fingir cumplimiento.',right,z,width)
 z=title('5. Terreno · precio pedido ±30 %',right,z);price=data.get('analyses',{}).get('price_grid',{});rows=[]
 if all(price.get(s,{}).get('price_grid') for s in ('Base','Downside')):
  for index in (0,5,10,15,20):
   row=[]
   for s in ('Base','Downside'):
    point=price[s]['price_grid'][index];v=point.get('values') or {};label=('PEDIDO ' if point.get('is_asking_price') else '')+amount(F(point['price'])/1000000,3) if point.get('price') is not None else 'PENDING';row.append(label+' / '+certified_irr_display(v.get('annual_irr')));fields.append(dict(path='price/'+s+'/'+str(index),value=point,display=row[-1]))
   rows.append(row)
  z=table(['Base: precio MUSD / TIR','Downside: precio MUSD / TIR'],rows,right,z,[178.5,178.5]);ends=[]
  for s in ('Base','Downside'):
   m=price[s]['max_price_for_targets'];display=('FUERA DE RANGO: sobre +30 %' if m.get('direction')=='above_upper' else 'FUERA DE RANGO: bajo -30 %') if m['state']=='OUTSIDE_RANGE' else 'USD '+amount(m['price']) if m.get('price') is not None else 'PENDING · '+m.get('reason','falta meta');ends.append(s+': '+display);fields.append(dict(path='price/'+s+'/maximum',value=m,display=display))
  z=text('Meta matemática TIR anual ≥15 %: '+'; '.join(ends)+'. No es RLV ni umbral vigente. Deuda y flujos futuros fijos; ΔTDC=ΔP×(1+C33).',right,z,width)
 else:z=text('PENDING · falta precio pedido documentado / análisis de la revisión; C32 es precio evaluado, no prueba del pedido.',right,z,width)
 z=title('6. Tornado · shocks declarados, no criterios',right,z);tornado=data.get('analyses',{}).get('tornado',{}).get('tornado',{});rows=[]
 for driver in DRIVERS:
  row=[names[driver]]
  for s in ('Base','Downside'):
   r=next((r for r in tornado.get(s,{}).get('with_refinance',[]) if r['driver']==driver),{})
   display=(amount(F(r['irr_impact']['lower'])*100,2)+'–'+amount(F(r['irr_impact']['upper'])*100,2)+' pp') if r.get('state')=='CALCULATED' else 'PENDING · '+str(r.get('visible_reason') or r.get('reason') or 'falta análisis');row.append(display);fields.append(dict(path='tornado/'+s+'/'+driver,value=r,display=display))
  rows.append(row)
 z=table(['Máximo |ΔTIR|','Base','Downside'],rows,right,z,[111,123,123]);z=title('7. Fuentes, usos y fechas',right,z)
 for s in ('Base','Downside'):
  v=data['scenario'][s];cal=v['calendar'];z=text(s+': TDC USD '+amount(v['tdc'])+' ('+amount(ratio(v['tdc'],v['units']))+'/unidad; '+amount(ratio(v['tdc'],v['gsf']))+'/GSF); obra/TDC '+(amount(F(ratio(v['construction_debt'],v['tdc']))*100) if ratio(v['construction_debt'],v['tdc']) is not None else 'PENDING')+' %. Compra '+cal.get('purchase_date','PENDING')+' → estable/refi '+cal.get('stabilization_date','PENDING')+' → venta '+cal.get('sale_date','PENDING')+'.',right,z,width)
 bottom=title('8. Banderas y carril humano',25,min(y,z)-2);bottom=text('Ejemplo sintético: no acredita disponibilidad de mercado ni aprobación. Custodio, criterios, revisor y aprobador por designar/acreditar. Datos, términos LP/GP y criterios reales: PENDING. Sin despliegue. Sin refi puede cobrar más al final; con refi puede cobrar antes: comparar calendario, TIR y múltiplo.',25,bottom,W-50)
 c.setFillColor(navy);c.setFont('Helvetica',7);c.drawString(25,16,'9. Revisión '+str(data.get('revision') or 'por confirmar')[:46]+' · caso '+data['case_sha256'][:12]+' · Sin dictamen real');c.drawRightString(W-25,16,'D277 · una página');c.save();return b.getvalue(),fields


def deliver(package,output,current_revision,analysis,roles):
 require_pdf_destination(package,output,current_revision);current=read_current_revision(current_revision,package);saved=read_package(package);result=json.loads(saved['results.json']);audit=verify_package(package,current_revision_raw=current)
 if audit['vigencia']!='VIGENTE' or result.get('critical_evidence_review',{}).get('status')!='PASSED':raise ValueError('PENDING: fuente o revisión; bloquear PDF')
 if analysis is None:analysis={}
 elif isinstance(analysis,(str,Path)):
  from worksheet_monthly_analysis_D277 import replay
  analysis=replay(Path(analysis),package)
  if analysis['baseline_results_sha256']!=sha(saved['results.json']):raise ValueError('Otra revisión financiera')
 else:raise ValueError('No se aceptan tablas de resultados; usar solicitud y replay de fuentes')
 view=report_view(result,json.loads(saved['case.json']),analysis,roles);pdf,fields=render(view);again,again_fields=render(report_view(result,json.loads(saved['case.json']),analysis,roles))
 if pdf!=again or fields!=again_fields:raise ValueError('PDF no reproducible')
 publish_current_pdf(package,saved,current_revision,current,output,pdf)
 return dict(schema=SCHEMA,state='DELIVERED_SYNTHETIC',current_revision_sha256=sha(current),case_sha256=sha(saved['case.json']),source_results_sha256=sha(saved['results.json']),analysis_sha256=digest(analysis),pdf_sha256=sha(pdf),view=view,rendered_fields=fields,decision='PENDING',deployment_enabled=False)
