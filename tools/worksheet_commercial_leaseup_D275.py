"""Per-space commercial lease-up, distinct cash, capex and NOI bases.

This opt-in monthly calculation requires explicit space inventories and terms.
It does not interpret an unreconciled real plan as a verified rent-roll.
"""
from datetime import date
from fractions import Fraction as Q
from worksheet_monthly_D275 import month
from worksheet_frontiers_D275 import fraction,rational,digest

SCHEMA='miniuw.synthetic-commercial-leaseup.v1'
BASES=('contractual_net','collected_net')


def schedule(spec):
 try:
  if not isinstance(spec,dict) or spec.get('schema')!=SCHEMA or spec.get('currency')!='USD' or spec.get('inventory_complete') is not True or not spec.get('source_ref'):
   raise ValueError('Falta inventario comercial completo, moneda o fuente')
  if spec.get('area_reconciliation')!='RECONCILED':raise ValueError('Área comercial pendiente o discrepante: bloquear dependientes')
  if spec.get('owner_cost_scope')!='commercial_only_excluding_M2_property_tax_insurance_and_residential':raise ValueError('Alcance de gastos no evita doble conteo con M2')
  start,end=(date.fromisoformat(spec[k]) for k in ('start','end'))
  if not start<end or start.day!=1 or end.day!=1:raise ValueError('Ventana comercial mensual inválida')
  n=(end.year-start.year)*12+end.month-start.month
  spaces=spec.get('spaces')
  if not isinstance(spaces,list) or len(spaces)>1000:raise ValueError('Falta inventario de locales; vacío no equivale a área cero')
  area=fraction(spec.get('reconciled_area_sf'))
  if area<0 or sum((fraction(v.get('area_sf')) for v in spaces),Q())!=area:raise ValueError('Inventario por local no concilia con el plano')
  ids=[v.get('id') for v in spaces]
  if len(set(ids))!=len(ids) or any(not isinstance(v,str) or not v for v in ids):raise ValueError('Local ausente o duplicado')
  rows=[];capex=[];term_records=[]
  for space in spaces:
   if not space.get('source_ref'):raise ValueError('Local sin términos documentados')
   sf,rent,collection,recovery=(fraction(space.get(k)) for k in ('area_sf','annual_rent_per_sf','collection_loss_fraction','recovery_fraction'))
   mode=space.get('owner_cost_mode','fixed_per_month')
   if mode=='fixed_per_month':owner=fraction(space.get('owner_cost_per_month'));owner_fraction=None
   elif mode=='legacy_C20_collected_rent_fraction':
    if space.get('owner_cost_per_month') is not None or recovery!=0:raise ValueError('C20 porcentual no se mezcla con gasto fijo o recuperos')
    owner_fraction=fraction(space.get('owner_cost_fraction'));owner=Q()
    if not 0<=owner_fraction<=1:raise ValueError('Falta fracción C20 explícita')
   else:raise ValueError('Modo de gasto comercial sin confirmar')
   if sf<=0 or min(rent,collection,owner,recovery)<0 or collection>1 or recovery>1:raise ValueError('Renta, área, pérdidas o recuperos inválidos')
   lease,expiry=(date.fromisoformat(space[k]) for k in ('lease_start','lease_end'))
   if lease.day!=1 or expiry.day!=1 or not lease<expiry:raise ValueError('Fechas de contrato comercial inválidas')
   free=space.get('free_rent_months');waive=space.get('recoveries_waived_during_free_rent')
   if type(free) is not int or free<0 or not isinstance(waive,bool):raise ValueError('Free rent o regla de recuperos sin confirmar')
   bases=space.get('noi_bases')
   if not isinstance(bases,dict) or set(bases)!={'bank','refinance_valuation','sale_valuation'} or any(v not in BASES for v in bases.values()):raise ValueError('Falta base de NOI bancario o valoración comercial')
   steps=space.get('rent_steps')
   if not isinstance(steps,list):raise ValueError('Escalones de renta sin declarar; [] debe ser explícito')
   parsed=[]
   for step in steps:
    d=date.fromisoformat(step['effective_date']);change=fraction(step.get('relative_increase'))
    if d.day!=1 or not lease<=d<expiry or change<=-1 or not step.get('source_ref'):raise ValueError('Escalón de renta inválido o sin fuente')
    parsed.append((d,change))
   if [d for d,v in parsed]!=sorted(set(d for d,v in parsed)):raise ValueError('Escalones duplicados o fuera de orden')
   events=space.get('ti_lc_events');event_keys=set()
   if not isinstance(events,list):raise ValueError('TI/LC sin calendario explícito')
   for event in events:
    when=date.fromisoformat(event['date']);amount=fraction(event.get('amount'));location=event.get('budget_location')
    if amount<0 or not start<=when<end or event.get('kind') not in ('TI','LC') or location not in ('M3','operating_capex') or not event.get('source_ref'):
     raise ValueError('TI/LC sin alcance, fuente o fecha dentro de la corrida')
    identity=(event['date'],event['kind'],event['source_ref'])
    if identity in event_keys:raise ValueError('TI/LC duplicado en un mismo local y fuente')
    event_keys.add(identity)
    capex.append(dict(space_id=space['id'],date=str(when),kind=event['kind'],budget_location=location,amount=rational(amount),source_ref=event['source_ref']))
   term_records.append((space,sf,rent,collection,owner,recovery,lease,expiry,free,waive,bases,parsed,mode,owner_fraction))
  for i in range(n):
   when=month(start,i);potential=rent_cash=recoveries=expenses=Q();income={b:Q() for b in ('bank','refinance_valuation','sale_valuation')};detail=[]
   for space,sf,rent,loss,owner,recovery,lease,expiry,free,waive,bases,steps,mode,owner_fraction in term_records:
    occupied=lease<=when<expiry;age=(when.year-lease.year)*12+when.month-lease.month;factor=Q(1)
    for effective,change in steps:
     if when>=effective:factor*=1+change
    base=sf*rent/12*factor if occupied else Q();free_now=occupied and age<free
    contractual=Q() if free_now else base;actual_owner=owner if mode=='fixed_per_month' else contractual*(1-loss)*owner_fraction;recover=actual_owner*recovery if occupied and not (free_now and waive) else Q()
    cash=(contractual+recover)*(1-loss);net_contract=contractual+recover-actual_owner;net_cash=cash-actual_owner
    potential+=base;rent_cash+=contractual*(1-loss);recoveries+=recover*(1-loss);expenses+=actual_owner
    for b in income:income[b]+=net_contract if bases[b]=='contractual_net' else net_cash
    detail.append(dict(space_id=space['id'],occupied=occupied,free_rent=free_now,rent=rational(contractual),recoveries=rational(recover),owner_cost=rational(actual_owner),cash_net=rational(net_cash),source_ref=space['source_ref']))
   operating_capex=sum((fraction(e['amount']) for e in capex if e['budget_location']=='operating_capex' and date.fromisoformat(e['date']).replace(day=1)==when),Q())
   rows.append(dict(start=str(when),end=str(month(start,i+1)),contractual_potential_rent=rational(potential),collected_rent=rational(rent_cash),collected_recoveries=rational(recoveries),owner_expenses=rational(expenses),
    operating_noi=rational(rent_cash+recoveries-expenses),cash_after_commercial_capex=rational(rent_cash+recoveries-expenses-operating_capex),operating_capex=rational(operating_capex),
    noi_by_basis={k:rational(v) for k,v in income.items()},spaces=detail))
  m3=sum((fraction(e['amount']) for e in capex if e['budget_location']=='M3'),Q())
  return dict(schema=SCHEMA,state='CALCULATED',monthly=rows,m3_ti_lc=rational(m3),capex_events=capex,reconciled_area_sf=rational(area),source_spec_sha256=digest(spec),
   no_cap_assumed=True,decision='PENDING',deployment_enabled=False)
 except (ValueError,KeyError,TypeError,AttributeError,ZeroDivisionError) as error:return dict(schema=SCHEMA,state='PENDING',reason=str(error),monthly=None,m3_ti_lc=None,decision='PENDING')


def combine_residential_noi(residential,commercial):
 if commercial.get('state')!='CALCULATED':return dict(state='PENDING',reason='Comercial sin conciliar o con términos faltantes',monthly=None)
 try:
  if not isinstance(residential,list) or len(residential)!=len(commercial['monthly']):raise ValueError('Falta un mes residencial o comercial')
  rows=[]
  for r,c in zip(residential,commercial['monthly'],strict=True):
   if r['start']!=c['start'] or r['end']!=c['end']:raise ValueError('Ventanas residencial y comercial incompatibles')
   rows.append(dict(start=r['start'],end=r['end'],residential_noi=r['noi'],commercial_noi=c['operating_noi'],
    total_operating_noi=rational(fraction(r['noi'])+fraction(c['operating_noi']))))
  return dict(state='CALCULATED',monthly=rows)
 except (ValueError,KeyError,TypeError):return dict(state='PENDING',monthly=None,reason='NOI residencial o período sin confirmar')
