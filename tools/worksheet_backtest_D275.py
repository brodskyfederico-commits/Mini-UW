"""Replay audited original forecasts and account for observed deviations.

Actual figures are supplied by the team, never fabricated by this harness.
A residual is displayed as 'no explicada'; an empty observation is not zero.
"""
from argparse import ArgumentParser
from pathlib import Path
from hashlib import sha256
from datetime import date
import json
from worksheet_frontiers_D275 import fraction,rational,digest
from miniuw_worksheet_v1 import read_package,verify_package,CURRENT_REVISION_FILE

SCHEMA='miniuw.closed-project-backtest.v1'
METRICS={'tdc':'USD','noi':'USD/year','debt_service':'USD/year','gross_sale':'USD',
 'contributions_per_usd10':'USD/initial_USD10','receipts_per_usd10':'USD/initial_USD10','equity_multiple':'multiple','annual_irr':'annual_fraction'}
CATEGORIES=('fuente','plazo','costo','NOI','servicio_deuda','venta','aportes','cobros')


def interval(value):
 if isinstance(value,dict) and set(value)=={'lower','upper'}:
  lo,hi=fraction(value['lower']),fraction(value['upper'])
 else:lo=hi=fraction(value)
 if lo>hi:raise ValueError('Intervalo invertido')
 return lo,hi

def compare_metric(predicted,actual,unit,explanations):
 try:
  if unit not in METRICS.values():raise ValueError('Unidad de cotejo sin confirmar')
  lo,hi=interval(predicted);a,b=interval(actual)
  difference=(a-hi,b-lo)
  if not isinstance(explanations,list):raise ValueError('Falta declaración de atribuciones; [] debe ser explícito')
  grouped={k:[fraction(0),fraction(0)] for k in CATEGORIES}
  for item in explanations:
   if item.get('category') not in CATEGORIES or not isinstance(item.get('source_ref'),str) or not item['source_ref'].strip():raise ValueError('Atribución sin categoría o respaldo')
   left,right=interval(item.get('amount'));grouped[item['category']][0]+=left;grouped[item['category']][1]+=right
  explained=(sum(v[0] for v in grouped.values()),sum(v[1] for v in grouped.values()))
  # Interval subtraction is conservative. It never asserts exact cancellation
  # of two distinct uncertain measurements simply because their bands overlap.
  residual=(difference[0]-explained[1],difference[1]-explained[0])
  return dict(state='COMPARED',unit=unit,difference=dict(lower=rational(difference[0]),upper=rational(difference[1])),
   by_category={k:dict(lower=rational(v[0]),upper=rational(v[1])) for k,v in grouped.items()},
   unexplained=dict(lower=rational(residual[0]),upper=rational(residual[1])),
   fully_explained_exactly=residual==(0,0),reason='Residual visible; las atribuciones requieren evidencia independiente, no se infiere causalidad')
 except (ValueError,KeyError,TypeError,ZeroDivisionError) as error:return dict(state='PENDING',difference=None,unexplained=None,reason=str(error))


def compare_case(spec):
 if not isinstance(spec,dict) or spec.get('schema')!=SCHEMA or not spec.get('project_id') or spec.get('population') not in ('synthetic_test','closed_real_project'):
  raise ValueError('Falta identificación y naturaleza del backtest')
 try:original=date.fromisoformat(spec['input_as_of']);closed=date.fromisoformat(spec['observed_as_of'])
 except (ValueError,KeyError,TypeError):raise ValueError('Faltan fechas de información original y observada') from None
 if original>closed:raise ValueError('Información observada anterior al corte original')
 for key in ('original_inputs_sha256','audited_results_sha256','observed_source_sha256'):
  value=spec.get(key)
  if not isinstance(value,str) or len(value)!=64 or any(x not in '0123456789abcdef' for x in value):raise ValueError('Falta huella del expediente original u observado')
 records=spec.get('measurements')
 if not isinstance(records,list) or not records:raise ValueError('No hay mediciones observadas; no se fabrica un backtest')
 seen=set();rows=[]
 for row in records:
  identity=(row.get('scenario'),row.get('route'),row.get('metric'))
  if identity in seen or identity[0] not in ('Base','Downside') or identity[1] not in ('with_refinance','without_refinance') or identity[2] not in METRICS:
   raise ValueError('Métrica, escenario o ruta inválidos / duplicados')
  seen.add(identity)
  if row.get('unit')!=METRICS[identity[2]]:value=dict(state='PENDING',reason='Unidad incompatible',difference=None,unexplained=None)
  elif not row.get('actual_source_ref'):value=dict(state='PENDING',reason='Observación real sin ubicación de fuente',difference=None,unexplained=None)
  else:value=compare_metric(row.get('predicted'),row.get('actual'),row['unit'],row.get('explanations'))
  rows.append(dict(scenario=identity[0],route=identity[1],metric=identity[2],actual_source_ref=row.get('actual_source_ref'),**value))
 routes=('with_refinance','without_refinance');not_observed=[]
 if spec['population']=='closed_real_project':
  strategy=spec.get('observed_strategy')
  if strategy not in routes:raise ValueError('Falta declarar la estrategia histórica realmente ejecutada')
  # One closed project has one observed history, not a different actual
  # outcome for each ex-ante Base/Downside forecast or unexecuted strategy.
  if any(r!=strategy for s,r,m in seen):raise ValueError('No se cargan resultados reales de una alternativa no ejecutada')
  for metric in METRICS:
   observations=[r.get('actual') for r in records if r.get('metric')==metric]
   if observations and any(v!=observations[0] for v in observations[1:]):raise ValueError('Base y Downside deben cotejarse con la misma historia observada')
  routes=(strategy,)
  not_observed=[dict(scenario=s,route=r,state='N/A',reason='Alternativa no ejecutada; no se inventa un retorno histórico contrafáctico') for s in ('Base','Downside') for r in ('with_refinance','without_refinance') if r!=strategy]
 required={(s,r,m) for s in ('Base','Downside') for r in routes for m in METRICS}
 missing=sorted(required-seen)
 calendar=[]
 inventory=spec.get('expected_calendar_milestones')
 records_calendar=spec.get('calendar_comparisons')
 if not isinstance(inventory,list) or not inventory or len(inventory)!=len(set(inventory)) or not isinstance(records_calendar,list):
  calendar.append(dict(milestone=None,state='PENDING',difference_days=None,reason='Falta inventario explícito de hitos a cotejar'))
  records_calendar=[]
 else:
  seen_calendar=[r.get('milestone') for r in records_calendar]
  if len(seen_calendar)!=len(set(seen_calendar)) or set(seen_calendar)!=set(inventory):calendar.append(dict(milestone=None,state='PENDING',difference_days=None,reason='Hitos ausentes o duplicados'))
 for row in records_calendar:
  try:delta=(date.fromisoformat(row['actual_date'])-date.fromisoformat(row['predicted_date'])).days;value=dict(state='COMPARED',difference_days=delta)
  except (ValueError,KeyError,TypeError):value=dict(state='PENDING',difference_days=None)
  calendar.append(dict(milestone=row.get('milestone'),**value))
 return dict(schema=SCHEMA,project_id=spec['project_id'],population=spec['population'],input_as_of=spec['input_as_of'],observed_as_of=spec['observed_as_of'],
  comparisons=rows,not_observed_alternatives=not_observed,missing_measurements=[dict(scenario=s,route=r,metric=m) for s,r,m in missing],calendar=calendar,
  state='COMPARED' if not missing and all(v['state']=='COMPARED' for v in rows) and calendar and all(v['state']=='COMPARED' for v in calendar) else 'PENDING',
  all_numeric_differences_exactly_explained=not missing and all(v.get('fully_explained_exactly',False) for v in rows),
  source_spec_sha256=digest(spec),real_validation_completed=False,real_decision='PENDING',deployment_enabled=False)


def predictions(result):
 """Financial observations only; no source-derived historical criteria copied."""
 output={}
 from plan_return_D107 import OPERATING_PERIOD
 for scenario in ('Base','Downside'):
  view=result['scenarios'][scenario];evidence=result['screening']['metric_evidence_by_scenario'].get(scenario,{})
  cost=evidence.get('cost_basis',{}).get('tdc')
  noi=view.get('noi_by_period',{}).get(OPERATING_PERIOD,{}).get('noi')
  for route in ('with_refinance','without_refinance'):
   candidate=view if route=='with_refinance' else view.get('horizon_without_refinance',{})
   cash=candidate.get('cash_per_usd_10') or {}
   irr=(result['screening']['irr_by_scenario'].get(scenario,{}) if route=='with_refinance' else candidate.get('irr',{})).get('annual_enclosure')
   irr=None if irr is None else {k:irr[k] for k in ('lower','upper')}
   service=view.get('permanent_loan',{}).get('annual_sizing_service') if route=='with_refinance' else (rational(fraction(view['construction_financing']['construction_principal_payoff'])*fraction(view['construction_financing']['annual_interest'])) if view.get('construction_financing',{}).get('state')=='computed_synthetic' else None)
   output[scenario,route]=dict(tdc=cost,noi=noi,debt_service=service,gross_sale=view.get('valuation_and_sale',{}).get('gross_sale_price'),
    contributions_per_usd10=cash.get('total_contributions'),receipts_per_usd10=cash.get('total_distributions'),equity_multiple=cash.get('equity_multiple'),annual_irr=irr)
 return output


def run(spec,package,observed_raw):
 if not isinstance(observed_raw,bytes) or sha256(observed_raw).hexdigest()!=spec.get('observed_source_sha256'):raise ValueError('El respaldo observado no coincide con la huella declarada')
 observed=json.loads(observed_raw)
 if not isinstance(observed,dict) or observed.get('schema')!='miniuw.closed-project-observations.v1' or observed.get('project_id')!=spec.get('project_id') or observed.get('as_of')!=spec.get('observed_as_of'):raise ValueError('Respaldo observado fuera de proyecto o fecha')
 actual_calendar={r['milestone']:r for r in observed.get('calendar',[])}
 if len(actual_calendar)!=len(observed.get('calendar',[])):raise ValueError('Hitos observados duplicados')
 for row in spec.get('calendar_comparisons',[]):
  backed=actual_calendar.get(row.get('milestone'))
  if backed is None or backed.get('actual_date')!=row.get('actual_date') or not backed.get('source_ref'):raise ValueError('Fecha observada sin respaldo literal coincidente')
 actual={(r['scenario'],r['route'],r['metric']):r for r in observed.get('measurements',[])}
 if len(actual)!=len(observed.get('measurements',[])):raise ValueError('Mediciones observadas duplicadas')
 for row in spec['measurements']:
  backed=actual.get((row['scenario'],row['route'],row['metric']))
  if backed is None or any(backed.get(k)!=row.get(k) for k in ('actual','unit','actual_source_ref','explanations')):raise ValueError('La observación o atribución no coincide con el respaldo original')
 saved=read_package(package);audit=verify_package(package,current_revision_raw=saved[CURRENT_REVISION_FILE])
 if audit['vigencia']!='VIGENTE':raise ValueError('El pronóstico original no reproduce un expediente vigente')
 result=json.loads(saved['results.json']);current=predictions(result)
 if spec['audited_results_sha256']!=__import__('hashlib').sha256(saved['results.json']).hexdigest():raise ValueError('La huella no corresponde al pronóstico original auditado')
 raw_case=__import__('hashlib').sha256(saved['case.json']).hexdigest()
 if spec['original_inputs_sha256']!=raw_case:raise ValueError('El backtest no está enlazado al expediente de inputs original')
 copy=json.loads(json.dumps(spec))
 for row in copy['measurements']:
  value=current[row['scenario'],row['route']][row['metric']]
  if row.get('predicted')!=value:raise ValueError('El pronóstico declarado difiere del motor auditado: '+row['metric'])
 return compare_case(copy)|dict(original_case_sha256=raw_case,original_audit=audit)


def main():
 parser=ArgumentParser(description=__doc__);parser.add_argument('command',choices=['run']);parser.add_argument('spec',type=Path);parser.add_argument('--package',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--observed',type=Path,required=True);a=parser.parse_args()
 report=run(json.loads(a.spec.read_bytes()),a.package,a.observed.read_bytes());a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(state=report['state'],real_decision='PENDING')))
if __name__=='__main__':main()
