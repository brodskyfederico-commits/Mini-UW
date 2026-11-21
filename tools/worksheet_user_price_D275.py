"""Fixed-debt land-price mathematics with explicitly configured user targets.

This is a separate analytical contract, never house RLV or adopted criteria.
All other future uses, debt, receipts and their dates are explicitly held fixed.
The purchase-price change is funded at the initial contribution, including C33.
"""
from copy import deepcopy
from fractions import Fraction as Q
from worksheet_frontiers_D275 import fraction,rational,digest
from worksheet_irr_certificate_D270 import positive_inventory,annual_enclosure,ArithmeticBudget

SCHEMA='miniuw.synthetic-user-target-price-grid.v1'
MONTHLY_SCHEMA='miniuw.synthetic-monthly-user-target-price-grid.v1'
RULE='fixed_debt_and_future_gross_events_delta_land_plus_closing_funded_at_initial_date'
METRICS=('annual_irr','equity_multiple','yoc','equity_tdc')


def exact_irr(flows):
 try:
  inv=positive_inventory(flows);coeff=inv.pop('coefficients',None)
  if not inv['complete'] or inv['positive_roots']!=1:return dict(state='PENDING',annual_enclosure=None,reason='No hay una única raíz admisible probada',root_inventory=inv)
  return dict(state='CERTIFIED',annual_enclosure=annual_enclosure(coeff,inv),root_inventory=inv)
 except (ValueError,ArithmeticBudget) as error:return dict(state='PENDING',annual_enclosure=None,reason=str(error))

def compare_enclosure(low,high,condition):
 if not isinstance(condition,dict) or set(condition)!={'operator','value'}:raise ValueError('Meta del usuario incompleta')
 op=condition['operator'];target=fraction(condition['value'])
 if op=='>=':return True if low>=target else False if high<target else None
 if op=='<=':return True if high<=target else False if low>target else None
 raise ValueError('Operador no soportado en meta del usuario')

def price_point(source,price,targets):
 try:
  if source.get('schema') not in (SCHEMA,MONTHLY_SCHEMA) or source.get('rule')!=RULE or source.get('source_check')!='INDEPENDENTLY_VERIFIED':
   raise ValueError('Falta contrato de precio con cotejo independiente de fuentes')
  if not source.get('source_ref') or not isinstance(source.get('source_sha256'),str) or len(source['source_sha256'])!=64:raise ValueError('Falta huella y ubicación de fuentes')
  if not isinstance(targets,dict) or not targets or not set(targets)<=set(METRICS):raise ValueError('Faltan metas explícitas del usuario')
  p0,c33,tdc,eq,debt,noi=(fraction(source.get(k)) for k in ('purchase_price','closing_fraction','tdc','applied_equity','fixed_debt','noi_uw'))
  other_sources=fraction(source.get('fixed_other_sources')) if source.get('schema')==MONTHLY_SCHEMA else Q()
  if not 0<=c33<=1 or debt<0 or other_sources<0 or tdc<=0 or eq<0 or eq+debt+other_sources!=tdc:raise ValueError('No concilian costo, equity y deuda fija')
  price=fraction(price);change=(price-p0)*(1+c33);cost=tdc+change;applied=eq+change
  if cost<=0 or applied<0:raise ValueError('Precio fuera del dominio de costo y equity')
  events=deepcopy(source.get('gross_events'));dates=source.get('dates');initial_id=source.get('initial_event_id')
  if not isinstance(events,list) or not isinstance(dates,list) or len(dates)<2 or dates!=sorted(set(dates)) or {e.get('date') for e in events}!=set(dates):
   raise ValueError('Falta inventario fechado completo; un hueco no se rellena')
  from datetime import date
  dd=[date.fromisoformat(d) for d in dates]
  frequency=12 if source.get('schema')==MONTHLY_SCHEMA else 4;spacing=12//frequency
  if source.get('schema')==MONTHLY_SCHEMA and source.get('periods_per_year')!=12:raise ValueError('El perfil mensual requiere períodos por año explícitos')
  if any(d.day!=1 for d in dd) or [(d.year-dd[0].year)*12+d.month-dd[0].month for d in dd]!=list(range(0,spacing*len(dd),spacing)):
   raise ValueError('Se requiere malla explícita y completa según el perfil de precio')
  initial=[e for e in events if e.get('id')==initial_id]
  if len(initial)!=1 or initial[0]['date']!=dates[0] or initial[0].get('kind')!='contribution':raise ValueError('Aporte inicial de precio ausente o ambiguo')
  initial[0]['amount']=rational(fraction(initial[0]['amount'])+change)
  basis=fraction(initial[0]['amount'])
  if basis<=0:raise ValueError('El equity inicial debe seguir siendo positivo; no se cambia la base por el total aportado')
  flows={d:Q() for d in dates};calls=receipts=Q()
  ids=[e.get('id') for e in events]
  if len(ids)!=len(set(ids)) or any(not v for v in ids):raise ValueError('Movimientos ausentes o duplicados')
  for event in events:
   val=fraction(event.get('amount'))
   if val<0 or not event.get('source_ref') or event.get('kind') not in ('contribution','distribution'):raise ValueError('Movimiento bruto inválido o sin fuente')
   if event['kind']=='contribution':calls+=val;flows[event['date']]-=val
   else:receipts+=val;flows[event['date']]+=val
  if frequency==12:
   from worksheet_monthly_D275 import monthly_irr
   irr=monthly_irr(dates,[rational(v) for v in flows.values()],source['source_ref'])
  else:irr=exact_irr(list(flows.values()))
  multiple=receipts/calls
  values=dict(yoc=rational(noi/cost),equity_tdc=rational(applied/cost),equity_multiple=rational(multiple),annual_irr=irr['annual_enclosure'])
  compared={}
  for key,condition in targets.items():
   value=values[key]
   if value is None:compared[key]=None
   elif key=='annual_irr':compared[key]=compare_enclosure(fraction(value['lower']),fraction(value['upper']),condition)
   else:compared[key]=compare_enclosure(fraction(value),fraction(value),condition)
  outcome='MEETS_USER_TARGETS' if all(v is True for v in compared.values()) else 'DOES_NOT_MEET_USER_TARGETS' if any(v is False for v in compared.values()) else 'PENDING'
  scale=10/basis
  return dict(state='CALCULATED',price=rational(price),negative_price_flag=price<0,delta_tdc=rational(change),tdc=rational(cost),fixed_debt=rational(debt),applied_equity=rational(applied),
   values=values,irr=irr,targets=compared,target_status=outcome,
   gross_cash_per_usd10=[dict(id=e['id'],date=e['date'],kind=e['kind'],amount=rational(fraction(e['amount'])*scale),source_ref=e['source_ref']) for e in events],
   total_contributions_per_usd10=rational(calls*scale),total_receipts_per_usd10=rational(receipts*scale),
   source_sha256=source['source_sha256'],initial_equity=rational(basis),house_rlv=dict(state='PENDING',reason='Criterio de RLV de la casa por confirmar'))
 except (ValueError,KeyError,TypeError,ZeroDivisionError) as error:
  return dict(state='PENDING',reason=str(error),price=None,values=None,house_rlv=dict(state='PENDING',reason='Criterio por confirmar'))


def grid(source,config):
 if not isinstance(config,dict) or config.get('schema') not in (SCHEMA,MONTHLY_SCHEMA) or config.get('schema')!=source.get('schema') or not isinstance(config.get('source_ref'),str) or not config['source_ref'].strip():raise ValueError('Falta configuración explícita de grilla')
 lo,hi,step=(fraction(config.get(k)) for k in ('lower','upper','step'))
 n=(hi-lo)/step if step>0 else -1
 if n.denominator!=1 or not 2<=n<=1000:raise ValueError('Grilla acotada no confirmada')
 points=[price_point(source,lo+i*step,config.get('user_targets')) for i in range(int(n)+1)]
 states=[p.get('target_status','PENDING') for p in points]
 monotone=not any(a=='DOES_NOT_MEET_USER_TARGETS' and b=='MEETS_USER_TARGETS' for i,a in enumerate(states) for b in states[i+1:])
 selected=[i for i,s in enumerate(states) if s=='MEETS_USER_TARGETS']
 maximum=dict(state='PENDING',price=None,reason='Ningún precio cumple las metas o hay observaciones sin resolver')
 if not monotone:maximum['reason']='No monotonía del cumplimiento en la grilla'
 elif config['schema']==MONTHLY_SCHEMA and 'PENDING' not in states and not selected:
  maximum=dict(state='NO_PRICE_IN_GRID',price=None,reason='Ningún precio de la grilla cumple; no se extrapola un precio fuera del dominio')
 elif 'PENDING' not in states and selected:
  index=selected[-1]
  if index==len(points)-1:maximum.update(state='BEYOND_GRID',reason='El límite superior aún cumple; no se afirma un máximo')
  else:maximum=dict(state='BOUNDED',price=points[index]['price'],next_price=points[index+1]['price'],resolution=rational(step),negative_price_flag=fraction(points[index]['price'])<0,
   reason='Máximo de la grilla declarada, no RLV de la casa')
 return dict(schema=config['schema'],price_grid=points,max_price_for_targets=maximum,monotone_on_complete_grid=monotone,
  house_rlv=dict(state='PENDING',reason='Criterio por confirmar'),criteria_adopted=False,real_decision='PENDING',deployment_enabled=False)
