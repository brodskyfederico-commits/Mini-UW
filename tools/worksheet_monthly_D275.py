"""Explicit monthly construction accrual and certified monthly equity IRR.

Opt-in analytical contracts; no fallback day count, event, rate or amount.
Quarterly profiles remain untouched. This module does not authenticate a term
sheet or by itself replace the integrated fiscal worksheet pipeline.
"""
from datetime import date
from fractions import Fraction as Q
from math import comb
from worksheet_frontiers_D275 import fraction,rational,digest
from worksheet_irr_certificate_D270 import variations,evaluate,bounded,ArithmeticBudget

SCHEMA='miniuw.synthetic-monthly-construction.v1'
IRR_SCHEMA='miniuw.synthetic-monthly-irr-certificate.v1'

def month(d,n):
 k=d.year*12+d.month-1+n;return date(k//12,k%12+1,d.day)

def day_fraction(a,b,convention):
 if convention=='ACT/360':return Q((b-a).days,360)
 if convention=='30E/360':return Q(360*(b.year-a.year)+30*(b.month-a.month)+min(30,b.day)-min(30,a.day),360)
 raise ValueError('Convención de días ausente o no soportada; no se asume 30/360')

def construction(spec):
 try:
  if not isinstance(spec,dict) or spec.get('schema')!=SCHEMA or spec.get('currency')!='USD' or spec.get('scenario') not in ('Base','Downside'):
   raise ValueError('Falta contrato mensual con moneda y escenario')
  if spec.get('equity_policy')!='initial_then_top_up_for_sourced_uses' or spec.get('pay_interest_at_stabilization') is not True or spec.get('principal_payment_mode')!='interest_only_until_stabilization' or spec.get('other_costs_and_limits_complete') is not True or not spec.get('source_ref'):
   raise ValueError('Falta declarar política de caja, pago final o fuente')
  start,end,maturity=(date.fromisoformat(spec[k]) for k in ('start','stabilization','maturity'))
  if start.day!=1 or end.day!=1 or not start<end<=maturity:raise ValueError('Calendario mensual o vencimiento inválido')
  rate,ltc,total,maximum,fee,initial,free,opening=(fraction(spec.get(k)) for k in ('annual_rate','ltc','eligible_total','maximum_commitment','fee_fraction','initial_equity','opening_free_cash','opening_principal'))
  if min(rate,ltc,total,maximum,fee,free)<0 or ltc>1 or fee>1 or initial<=0 or free!=0 or opening!=0:raise ValueError('Términos de financiación fuera de alcance')
  convention=spec.get('day_count');day_fraction(start,end,convention)
  cadence=spec.get('interest_payment_every_months')
  if type(cadence) is not int or cadence not in (1,3):raise ValueError('Cadencia explícita de interés mensual o trimestral requerida')
  n=(end.year-start.year)*12+end.month-start.month
  periods=spec.get('periods')
  if not isinstance(periods,list) or len(periods)!=n:raise ValueError('Falta un mes; no se completa con cero')
  commitment=min(ltc*total,maximum);origination=commitment*fee
  principal=accrued=interest_total=calls=drawn=uses_total=Q();cash=[];months=[];settlements={};invoice_ids=set();eligible_invoiced=Q()
  # Opening cash and the initial contribution are explicit source values.
  free=initial;calls=initial
  cash.append(dict(event_id='monthly-initial',date=str(start),kind='contribution',amount=rational(initial),category='initial_capital',source_ref=spec['source_ref']))
  expected_sources=[]
  for i,period in enumerate(periods):
   a,b=month(start,i),month(start,i+1)
   if not isinstance(period,dict) or period.get('start')!=str(a) or period.get('end')!=str(b) or period.get('inventory_complete') is not True or not period.get('source_ref'):
    raise ValueError('Mes incompleto, fuera de orden o sin fuente')
   if not isinstance(period.get('events'),list):raise ValueError('Inventario de eventos mensual ausente')
   events=period['events'];bydate={};local_ids=[]
   for event in events:
    if not isinstance(event,dict) or event.get('kind') not in ('draw','use') or not event.get('source_ref'):raise ValueError('Evento mensual sin clase o fuente')
    when=date.fromisoformat(event['date']);value=fraction(event.get('amount'))
    if not a<=when<b or value<0:raise ValueError('Fecha o importe de evento fuera del mes')
    if not isinstance(event.get('id'),str) or not event['id']:raise ValueError('Falta ID del evento')
    local_ids.append(event['id']);bydate.setdefault(when,[]).append(event)
   expected_sources.extend(local_ids)
   if i==0:bydate.setdefault(a,[]).append(dict(id='origination-fee',kind='use',amount=rational(origination),source_ref=spec['source_ref']))
   previous=a;monthly_interest=Q();opening_principal=principal
   for when,items in sorted(bydate.items()):
    monthly_interest+=principal*rate*day_fraction(previous,when,convention);previous=when
    draw=use=Q()
    for event in items:
     val=fraction(event['amount'])
     if event['kind']=='draw':
      invoice_id=event.get('invoice_id')
      if not isinstance(invoice_id,str) or not invoice_id or invoice_id in invoice_ids:raise ValueError('Factura de draw ausente o duplicada')
      invoice_ids.add(invoice_id)
      invoice=fraction(event.get('eligible_invoice'));available=fraction(event.get('available_new_draw'));eligible_invoiced+=invoice
      if eligible_invoiced>total:raise ValueError('Facturas elegibles exceden el inventario fuente')
      if min(invoice,available)<0 or val>min(invoice*ltc,available,commitment-drawn-draw):raise ValueError('Desembolso supera elegibilidad, disponibilidad o compromiso')
      draw+=val
     else:use+=val
    principal+=draw;drawn+=draw;uses_total+=use
    row=settlements.setdefault(when,dict(draw=Q(),uses=Q(),interest=Q(),source_refs=[]))
    row['draw']+=draw;row['uses']+=use;row['source_refs'].append(period['source_ref'])
   monthly_interest+=principal*rate*day_fraction(previous,b,convention);interest_total+=monthly_interest;accrued+=monthly_interest
   pay=accrued if (i+1)%cadence==0 or i+1==n else Q()
   if pay:
    row=settlements.setdefault(b,dict(draw=Q(),uses=Q(),interest=Q(),source_refs=[]))
    row['interest']+=pay;row['source_refs'].append(period['source_ref']);accrued-=pay
   months.append(dict(start=str(a),end=str(b),opening_principal=rational(opening_principal),closing_principal=rational(principal),
    interest_accrued=rational(monthly_interest),interest_paid=rational(pay),closing_free_cash=None,unpaid_interest=rational(accrued),source_ref=period['source_ref']))
  if len(expected_sources)!=len(set(expected_sources)) or 'origination-fee' in expected_sources:raise ValueError('IDs de eventos duplicados o reservados')
  # Accrual and settlement are distinct. Aggregate ALL flows on a date before
  # asking for equity; processing a month-end payment before a same-day draw
  # would invent an intraday order and an unnecessary earlier capital call.
  free=initial;calls=initial;dated=[]
  for when,row in sorted(settlements.items()):
   before=free+row['draw']-row['uses']-row['interest'];topup=max(Q(),-before);free=before+topup;calls+=topup
   if when==start and topup:raise ValueError('El aporte inicial verificado no cubre los usos iniciales; no se redefine en silencio')
   if topup:cash.append(dict(event_id='monthly-topup-'+str(when),date=str(when),kind='contribution',amount=rational(topup),category='additional_capital',source_ref=spec['source_ref']))
   dated.append(dict(date=str(when),loan_draw=rational(row['draw']),uses=rational(row['uses']),interest_paid=rational(row['interest']),equity_contribution=rational(topup),closing_free_cash=rational(free)))
  for row in months:
   prior=[item for item in dated if item['date']<=row['end']]
   row['closing_free_cash']=prior[-1]['closing_free_cash'] if prior else rational(initial)
   row['cash_basis']='Todos los movimientos de la fecha agregados; no se supone orden intradía'
  if calls+drawn!=uses_total+interest_total+free or accrued!=0:raise ValueError('No concilian fuentes, usos, intereses y caja')
  return dict(schema=SCHEMA,state='CALCULATED',months=months,equity_events=cash,commitment=rational(commitment),drawn=rational(drawn),
   cash_by_date=dated,terminal_principal=rational(principal),interest_total=rational(interest_total),initial_equity=rational(initial),
   total_contributions=rational(calls),uses_total_including_fee=rational(uses_total),closing_free_cash=rational(free),
   source_spec_sha256=digest(spec),day_count=convention,decision='PENDING',deployment_enabled=False)
 except (ValueError,KeyError,TypeError,ZeroDivisionError) as error:return dict(schema=SCHEMA,state='PENDING',reason=str(error),months=None,equity_events=None,decision='PENDING')


def monthly_irr(dates,net_flows,source_ref):
 try:
  if not isinstance(dates,list) or not isinstance(net_flows,list) or len(dates)!=len(net_flows) or not 2<=len(dates)<=241 or not isinstance(source_ref,str) or not source_ref.strip():
   raise ValueError('Falta calendario mensual completo o fuente de flujos')
  dd=[date.fromisoformat(v) for v in dates]
  if dd!=[month(dd[0],i) for i in range(len(dd))] or any(d.day!=1 for d in dd):raise ValueError('Falta un mes observado; no se imputa cero')
  coefficients=[bounded(fraction(v),4096) for v in net_flows]
  if not any(coefficients):raise ValueError('Polinomio nulo: infinitas raíces, sin selección')
  while coefficients and coefficients[0]==0:coefficients.pop(0)
  while len(coefficients)>1 and coefficients[-1]==0:coefficients.pop()
  degree=len(coefficients)-1;left=[];right=[]
  for j in range(degree+1):
   left.append(bounded(sum((coefficients[i]*comb(degree-i,j-i) for i in range(j+1)),Q()),8192))
   right.append(bounded(sum((coefficients[i]*comb(i,j) for i in range(j,degree+1)),Q()),8192))
  vl,vr=variations(left),variations(right);at_one=evaluate(coefficients,Q(1))==0
  complete=vl<=1 and vr<=1;count=vl+vr+int(at_one) if complete else None
  inventory=dict(complete=complete,positive_roots=count,left_variations=vl,right_variations=vr,root_at_one=at_one,degree=degree)
  if not complete or count!=1:return dict(schema=IRR_SCHEMA,state='PENDING',annual_enclosure=None,root_inventory=inventory,reason='Raíz admisible única no probada')
  if at_one:low=high=Q(1)
  else:
   low,high=(Q(),Q(1)) if vl==1 else (Q(1),Q(2));fl=evaluate(coefficients,low);fh=evaluate(coefficients,high)
   for _ in range(32):
    if fh==0 or fl*fh<0:break
    high*=2;fh=evaluate(coefficients,high)
   else:raise ValueError('Presupuesto de acotación agotado')
   if fh==0:low=high
   else:
    for _ in range(72):
     mid=(low+high)/2;fm=evaluate(coefficients,mid)
     if fm==0:low=high=mid;break
     if fm*fl>0:low=mid;fl=fm
     else:high=mid;fh=fm
    if low<=0 or evaluate(coefficients,low)*evaluate(coefficients,high)>0:raise ValueError('Intervalo mensual no verificado')
  return dict(schema=IRR_SCHEMA,state='CERTIFIED',periods_per_year=12,root_inventory=inventory,
   annual_enclosure=dict(lower=rational(high**-12-1),upper=rational(low**-12-1)),
   discount_factor_enclosure=dict(lower=rational(low),upper=rational(high)),source_ref=source_ref,decision='PENDING')
 except (ValueError,KeyError,TypeError,ZeroDivisionError,ArithmeticBudget) as error:return dict(schema=IRR_SCHEMA,state='PENDING',annual_enclosure=None,reason=str(error))
