"""Versioned synthetic criteria plug; immutable financial snapshots.

No historical thresholds are loaded. A fixture may change comparisons, never
cash, computed metrics, frontiers, user price grid or tornado. House RLV is
explicitly criterion-dependent and is excluded from that invariant.
"""
from copy import deepcopy
from datetime import date
from worksheet_frontiers_D275 import fraction,rational,digest
from miniuw_foundation.lorena_screening import BASES,RLV

SCHEMA='miniuw.synthetic-criteria-plug.v1'
UNITS={'YoC':'annual_fraction','spread':'bps','equity_recovered':'fraction','equity_cash_in':'fraction',
 'breakeven_occupancy':'fraction','post_refi_CoC':'annual_fraction',RLV:'fraction','equity_TDC':'fraction','IRR':'annual_fraction','equity_multiple':'multiple'}
FINANCIAL_KEYS=('scenarios','return_summary','computed_metrics','breakeven_matrix','price_grid','tornado')


def validated(config,as_of):
 if config is None:return None
 if not isinstance(config,dict) or config.get('schema')!=SCHEMA or config.get('usage')!='synthetic_plug_test_only' or config.get('criteria_adopted') is not False or not isinstance(config.get('revision'),str) or not config['revision'].strip():
  raise ValueError('Falta contrato versionado de criterios ficticios; no se adoptan reglas')
 cut=date.fromisoformat(as_of)
 if not date.fromisoformat(config['valid_from'])<=cut<=date.fromisoformat(config['valid_until']):raise ValueError('Criterio fuera de vigencia')
 rows=config.get('rules')
 if not isinstance(rows,list):raise ValueError('Falta inventario de reglas por escenario')
 required={(s,m) for s in ('Base','Downside') for m in BASES};seen=set()
 for row in rows:
  identity=(row.get('scenario'),row.get('metric_id'))
  if identity not in required or identity in seen:raise ValueError('Regla fuera de inventario o duplicada')
  seen.add(identity);metric=identity[1]
  if row.get('unit')!=UNITS[metric] or row.get('basis')!=BASES[metric] or not isinstance(row.get('source_ref'),str) or not row['source_ref'].startswith('SYNTHETIC-'):
   raise ValueError('Unidad, base de NOI / cálculo o fuente incompatible')
  if row.get('applicability') not in ('applicable','not_applicable'):raise ValueError('Aplicabilidad no declarada')
  if row['applicability']=='not_applicable':
   if not row.get('reason'):raise ValueError('N/A sin motivo')
   continue
  for name in ('pass','fail'):
   condition=row.get(name)
   if condition is None:
    if name=='fail' and row.get('fail_scope')=='explicitly_not_defined':continue
    raise ValueError('Falta criterio aplicable, no se interpreta como cero')
   if not isinstance(condition,dict) or set(condition)!={'operator','threshold'} or condition['operator'] not in ('>=','>','<=','<'):
    raise ValueError('Operador del criterio no confirmado')
   fraction(condition['threshold'])
  if row.get('period_ref') is None or not isinstance(row['period_ref'],str) or not row['period_ref'].strip():raise ValueError('Ventana del criterio sin confirmar')
 if seen!=required:raise ValueError('Faltan métricas aplicables; no se omiten en silencio')
 return config


def relation(value,condition):
 if value is None:return None
 if isinstance(value,dict) and 'lower' in value:
  low,high=fraction(value['lower']),fraction(value['upper'])
  if low>high:raise ValueError('Intervalo de métrica inválido')
 else:low=high=fraction(value)
 target=fraction(condition['threshold']);op=condition['operator']
 fn={'>=':lambda a:a>=target,'>':lambda a:a>target,'<=':lambda a:a<=target,'<':lambda a:a<target}[op]
 a,b=fn(low),fn(high)
 return a if a==b else None


def apply(snapshot,config,as_of,*,house_rlv_solver=None,common_causes=None,causal_documents=None):
 # No caller-owned structure is mutated, including optional pricing/IRR records.
 financial={k:deepcopy(snapshot[k]) for k in FINANCIAL_KEYS if k in snapshot}
 output=deepcopy(snapshot);rows=[]
 try:configuration=validated(config,as_of);error=None
 except (ValueError,KeyError,TypeError,ZeroDivisionError) as err:configuration=None;error=str(err)
 rules={} if configuration is None else {(r['scenario'],r['metric_id']):r for r in configuration['rules']}
 for scenario in ('Base','Downside'):
  observations=snapshot.get('computed_metrics',{}).get(scenario,{})
  for metric in BASES:
   rule=rules.get((scenario,metric));record=observations.get(metric)
   row=dict(scenario=scenario,metric_id=metric,state='PENDING',label='criterio por confirmar',reason=error)
   try:
    if rule is None:row['reason']=error or 'Falta criterio vigente'
    elif rule['applicability']=='not_applicable':row.update(state='N/A',label='No aplica',reason=rule['reason'])
    elif not isinstance(record,dict) or record.get('value') is None:row['reason']='Falta dato calculado o definición compatible'
    elif any(record.get(k)!=rule.get(k) for k in ('basis','unit','period_ref')):row['reason']='Métrica y criterio usan bases, unidades o períodos distintos'
    else:
     passing=relation(record['value'],rule['pass']);failing=relation(record['value'],rule['fail']) if rule.get('fail') is not None else False
     if passing is True and failing is True:row['reason']='Condiciones de cumple y no cumple se superponen'
     elif passing is True:row.update(state='PASS_SIMULATED',label='cumple criterios',reason=None)
     elif failing is True:row.update(state='FAIL_SIMULATED',label='no cumple criterios',reason=None)
     else:row.update(reason='Banda intermedia o intervalo sin resolver; requiere revisión')
   except (ValueError,KeyError,TypeError,ZeroDivisionError) as err:row['reason']=str(err)
   rows.append(row)
 house=dict(state='PENDING',value=None,reason='Definición de RLV de la casa por confirmar')
 if configuration is not None and configuration.get('house_rlv_definition') is not None:
  definition=configuration['house_rlv_definition']
  if not isinstance(definition,dict) or definition.get('all_applicable_criteria_jointly') is not True:
   house['reason']='El RLV debe conservar todos los criterios aplicables, incluido YoC y spread'
  elif house_rlv_solver is None:house['reason']='Falta búsqueda conjunta verificada del RLV'
  else:house=house_rlv_solver(deepcopy(financial),deepcopy(configuration))
 output.update(criteria_comparisons=rows,criteria_revision=None if configuration is None else configuration['revision'],
  criteria_plug_schema=SCHEMA,house_rlv=house,financial_snapshot_sha256=digest(financial),criteria_adopted=False,
  decision='PENDING',historical_return='PENDING',deployment_enabled=False,
  policy_note='El estado por métrica no autentica un dictamen; precedencia con faltantes y RLV real por confirmar')
 if common_causes is not None:
  from worksheet_review_findings_D276 import findings
  output['review_findings']=findings(rows,common_causes,causal_documents,output['criteria_revision'])
 assert {k:output[k] for k in financial}==financial
 return output
