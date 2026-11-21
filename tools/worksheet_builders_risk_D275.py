"""Explicit construction insurance line; never inferred from soft costs."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from worksheet_frontiers_D275 import fraction,rational,digest

SCHEMA='miniuw.synthetic-builders-risk.v1'

def proof(source,documents):
 if not isinstance(source,dict) or not isinstance(source.get('locator'),str) or not source['locator'].strip():return False
 raw=documents.get(source.get('sha256'))
 return isinstance(raw,bytes) and sha256(raw).hexdigest()==source.get('sha256')

def line(spec,documents):
 try:
  if not isinstance(spec,dict) or spec.get('schema')!=SCHEMA or spec.get('currency')!='USD' or not proof(spec.get('quote_source'),documents):
   raise ValueError('Falta cotización de builder’s risk con fuente y cita')
  quote=json.loads(documents[spec['quote_source']['sha256']])
  if quote.get('schema')!='miniuw.synthetic-builders-risk-quote.v1':raise ValueError('Cotización fuera del formato explícito soportado; requiere lectura verificada')
  keys=('currency','premium_basis','base','rate','quoted_premium','term_start','term_end','payment_date')
  if any(quote.get(k)!=spec.get(k) for k in keys):raise ValueError('La prima, base, tasa o plazo discrepa de la cotización original')
  start,end,pay=(date.fromisoformat(spec[k]) for k in ('term_start','term_end','payment_date'))
  if not start<end or pay>end:raise ValueError('Plazo o fecha de prima incompatible')
  mode=spec.get('premium_basis')
  if mode=='quoted_premium':
   if spec.get('base') is not None or spec.get('rate') is not None:raise ValueError('Bases de prima incompatibles; no mezclar prima y tasa')
   premium=fraction(spec.get('quoted_premium'))
  elif mode=='rate_times_base_for_full_declared_term':
   if spec.get('quoted_premium') is not None:raise ValueError('Prima duplicada con tasa sobre base')
   base,rate=fraction(spec.get('base')),fraction(spec.get('rate'))
   if base<0 or not 0<=rate<=1:raise ValueError('Base o tasa fuera de alcance')
   premium=base*rate
  else:raise ValueError('Falta base explícita de la prima; no se anualiza el plazo en silencio')
  if premium<0 or not isinstance(spec.get('included_in_gc'),bool) or spec.get('included_in_soft_percentage') is not False:
   raise ValueError('Falta exclusión de soft % o declaración de inclusión en GC')
  if spec['included_in_gc']:
   if not proof(spec.get('gc_inclusion_source'),documents):raise ValueError('Inclusión en GC sin respaldo; no se puede evitar doble conteo por declaración sola')
   gc=json.loads(documents[spec['gc_inclusion_source']['sha256']])
   if gc.get('schema')!='miniuw.synthetic-gc-risk-inclusion.v1' or gc.get('included') is not True or fraction(gc.get('premium'))!=premium:raise ValueError('El documento GC no confirma la inclusión de esta prima')
  return dict(schema=SCHEMA,state='CALCULATED',quoted_or_computed_premium=rational(premium),incremental_budget_cost=rational(0 if spec['included_in_gc'] else premium),
   included_in_gc=spec['included_in_gc'],included_in_soft_percentage=False,premium_basis=mode,
   base=spec.get('base'),rate=spec.get('rate'),term_start=str(start),term_end=str(end),payment_date=str(pay),
   quote_source=spec['quote_source'],gc_inclusion_source=spec.get('gc_inclusion_source'),source_spec_sha256=digest(spec),
   operating_insurance_unchanged=True,decision='PENDING')
 except (ValueError,KeyError,TypeError,AttributeError,ZeroDivisionError) as error:return dict(schema=SCHEMA,state='PENDING',incremental_budget_cost=None,reason=str(error),decision='PENDING')

def budget_extension(budget,spec,documents):
 item=line(spec,documents)
 if item['state']=='PENDING':return dict(state='PENDING',builders_risk=item,total_development_cost=None)
 try:
  base=fraction(budget.get('total_development_cost'));amount=fraction(item['incremental_budget_cost'])
  if 'builders_risk' in budget:raise ValueError('La partida de builder’s risk ya fue aplicada')
  if base<0:raise ValueError('Presupuesto base inválido')
  return deepcopy(budget)|dict(state='CALCULATED',builders_risk=item,base_total_development_cost=rational(base),
   total_development_cost=rational(base+amount),incremental_uses=[dict(date=item['payment_date'],amount=rational(amount),source_ref=item['quote_source'])])
 except (ValueError,TypeError,ZeroDivisionError) as error:return dict(state='PENDING',builders_risk=item,total_development_cost=None,reason=str(error))
