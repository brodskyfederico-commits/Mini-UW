"""Declared mathematical boundaries over audited, independently checked source runs.

No criteria are loaded. Callers supply ranges, resolution, units and a replay
adapter. An unavailable observation is never an implicit zero or a safe point.
"""
from fractions import Fraction as Q
from hashlib import sha256
import json
import re

SCHEMA = 'miniuw.synthetic-mathematical-frontiers.v1'
DRIVERS = {
 'residential_rent': {'cells':['C8','C9','C10','C11'],'unit':'relative_fraction'},
 'exit_cap': {'cells':['C67'],'unit':'bps'},
 'vertical_cost': {'cells':['C35'],'unit':'relative_fraction'},
 'interest': {'cells':['C52','C69'],'unit':'bps'},
 'lease_up': {'cells':['C47'],'unit':'months'},
 'vacancy': {'cells':['C14'],'unit':'percentage_points'},
}
FRONTIERS = ('F1','F2','F3','F4')

def fraction(raw):
 if raw is None or isinstance(raw,(bool,float)) or raw == '':
  raise ValueError('Falta un número explícito; vacío no equivale a cero')
 if isinstance(raw,dict):
  if set(raw)!={'numerator','denominator'}:raise ValueError('Número racional inválido')
  if any(isinstance(v,(bool,float)) or not isinstance(v,(str,int)) or len(str(v))>1300 for v in raw.values()):raise ValueError('Número racional inválido o fuera del límite de precisión')
  return Q(int(raw['numerator']),int(raw['denominator']))
 if isinstance(raw,str):
  v=raw.strip()
  if len(v)>1300 or not re.fullmatch(r'[+-]?(?:[0-9]+/[+-]?[0-9]+|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,4})?)',v):raise ValueError('Literal numérico inválido o fuera del límite de precisión')
  if 'e' in v.lower() and abs(int(v.lower().split('e')[1]))>1300:raise ValueError('Exponente fuera del límite de precisión')
  value=Q(v)
  if max(abs(value.numerator).bit_length(),value.denominator.bit_length())>4320:raise ValueError('Número fuera del límite de precisión')
  return value
 if isinstance(raw,(int,Q)):return Q(raw)
 raise ValueError('Número explícito inválido')

def rational(value):
 v=fraction(value);return dict(numerator=str(v.numerator),denominator=str(v.denominator))

def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def pending(reason,**kw):return dict(state='PENDING',reason=reason,value=None,**kw)

def search(config,evaluator,*,scenario,route,frontier):
 """Find the first sampled crossing, then test both bracket neighbours.

 The declared lattice is finite. Sampling cannot prove global monotonicity of
 an arbitrary financial model; the output states exactly what was checked.
 Every point comes from the adapter's source run, B12/B16 and independent check.
 """
 trace={}
 def result(state,**kw):
  return dict(schema=SCHEMA,state=state,scenario=scenario,route=route,frontier=frontier,
   mathematical_boundary_not_investment_criterion=True,decision='PENDING',
   unit=config.get('unit'),source_ref=config.get('source_ref'),
   observed_points=list(trace.values()),**kw)
 try:
  driver=config['driver'];decl=DRIVERS[driver]
  if config['unit']!=decl['unit'] or not isinstance(config.get('source_ref'),str) or not config['source_ref'].strip():
   raise ValueError('Falta unidad o fuente explícita del rango')
  stop,step=fraction(config['upper']),fraction(config['step'])
  samples=config['monotonic_probes'];budget=config['maximum_evaluations']
  if stop<=0 or step<=0 or stop/step!=int(stop/step) or type(samples) is not int or samples<2 or type(budget) is not int or not 3<=budget<=512:
   raise ValueError('Rango, resolución o presupuesto de búsqueda inválido')
  if driver=='lease_up' and (stop.denominator!=1 or step.denominator!=1):raise ValueError('El retraso requiere meses enteros')
  if scenario not in ('Base','Downside') or route not in ('with_refinance','without_refinance') or frontier not in FRONTIERS:raise ValueError('Ámbito de frontera inválido')
  if frontier=='F3' and route=='without_refinance':return result('N/A',value=None,reason='La frontera de refinanciación no aplica a la ruta sin refi',monotonicity='not_applicable')
  n=int(stop/step)
  def point(index):
   x=index*step;k=str(x)
   if k in trace:return fraction(trace[k]['margin'])
   if len(trace)>=budget:raise ValueError('Se agotó el presupuesto explícito de búsqueda')
   raw=evaluator(driver,x,scenario,route)
   if not isinstance(raw,dict) or raw.get('state')!='VERIFIED' or raw.get('b12')!='PASSED' or raw.get('b16')!='PASSED' or raw.get('independent_check')!='PASSED':
    trace[k]=dict(movement=rational(x),state='PENDING',reason=raw.get('reason','Falta corrida auditada') if isinstance(raw,dict) else 'Falta corrida auditada')
    raise ValueError('Punto bloqueado por evidencia, cálculo o cotejo independiente')
   if not all(isinstance(raw.get(f),str) and len(raw[f])==64 and all(c in '0123456789abcdef' for c in raw[f]) for f in ('case_sha256','results_sha256','sources_sha256')):
    raise ValueError('Faltan huellas de la corrida y sus fuentes')
   margins=raw['margins'];value=fraction(margins.get(frontier))
   trace[k]=dict(movement=rational(x),state='VERIFIED',margin=rational(value),
    case_sha256=raw['case_sha256'],results_sha256=raw['results_sha256'],sources_sha256=raw['sources_sha256'],
    cash_sha256=raw.get('cash_sha256'),independent_reference_sha256=raw.get('independent_reference_sha256'))
   return value
  if point(0)<0:return result('BASELINE_BREACHED',value=rational(0),reason='El caso original ya cruza la frontera matemática',monotonicity='not_required_for_observed_initial_breach')
  # Explicitly probe the whole declared domain before assuming a direction.
  indices=sorted({0,n,*[round(Q(i*n,samples)) for i in range(1,samples)]})
  for i in indices:point(i)
  def monotone():
   vals=sorted((fraction(k),fraction(v['margin'])) for k,v in trace.items() if v['state']=='VERIFIED')
   return all(b[1]<=a[1] for a,b in zip(vals,vals[1:]))
  if not monotone():return result('PENDING',reason='No monotonía en los puntos auditados; no se elige una frontera',value=None,search_range=[rational(0),rational(stop)],monotonicity='failed')
  if point(n)>=0:return result('BEYOND_SEARCH_RANGE',value=None,lower_bound=rational(stop),reason='No se alcanza la frontera dentro del rango declarado',monotonicity='sampled_only')
  low,high=0,n
  while high-low>1:
   m=(low+high)//2
   if point(m)>=0:low=m
   else:high=m
  # Neighbours are an explicit resolution, not a hidden financial tolerance.
  for i in {max(0,low-1),low,high,min(n,high+1)}:point(i)
  if not monotone():return result('PENDING',reason='La sonda de vecinos contradice la monotonía',value=None,monotonicity='failed')
  return result('BOUNDED',value=None,safe_movement=rational(low*step),breached_movement=rational(high*step),
   safe_margin=rational(point(low)),breached_margin=rational(point(high)),resolution=rational(step),
   monotonicity='verified_at_declared_probes_and_bracket_neighbours_only',
   first_representable_breach=rational(high*step),range_upper=rational(stop))
 except (ValueError,KeyError,TypeError,ZeroDivisionError) as err:
  return result('PENDING',reason=str(err),value=None,monotonicity='not_established')

def matrix(configuration,evaluator):
 if not isinstance(configuration,dict) or configuration.get('schema')!=SCHEMA or set(configuration.get('drivers',{}))!=set(DRIVERS):
  raise ValueError('Se requieren los seis drivers con rangos explícitos; no se cargan defaults')
 return dict(schema=SCHEMA,decision='PENDING',criteria_adopted=False,deployment_enabled=False,
  breakeven_matrix={s:{r:{d:{f:search(v|dict(driver=d),evaluator,scenario=s,route=r,frontier=f)
   for f in FRONTIERS} for d,v in configuration['drivers'].items()} for r in ('with_refinance','without_refinance')} for s in ('Base','Downside')})
