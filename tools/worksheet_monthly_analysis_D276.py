"""Source-replayed analytical overlay; never accept a table of claimed results."""
from pathlib import Path
from hashlib import sha256
import json
from fractions import Fraction as Q
from worksheet_frontiers_D275 import fraction as F,rational as R,digest,DRIVERS,FRONTIERS
from worksheet_monthly_experiments_D276 import experiments,price_analysis,RANGES
from worksheet_tornado_D275 import enclosure,delta_enclosure,impact_interval,ranked
from worksheet_intake_D198 import read_source_directory
from worksheet_monthly_native_D276 import SCHEMA as CASE_SCHEMA
from miniuw_worksheet_v1 import read_package,verify_package,CURRENT_REVISION_FILE
from check_monthly_oracle_D276 import verify
from check_worksheet_scenario_program_D268 import source_cells

SCHEMA='miniuw.synthetic-monthly-review-analysis-request.v1'


def request(case_raw,sources):
 return dict(schema=SCHEMA,case_sha256=sha256(case_raw).hexdigest(),sources_sha256={k:sha256(v).hexdigest() for k,v in sources.items() if isinstance(v,bytes)},include_stress=True,usage='synthetic_mathematical_review_only')


def validate_request(raw,case_raw,sources):
 if raw!=request(case_raw,sources):raise ValueError('La solicitud de análisis no coincide con fuentes, alcance o revisión; no se aceptan tablas manuales')


def bounded_grid(points,upper,step,unit):
 result=dict(unit=unit,source_ref='SYNTHETIC-D276-declared-mathematical-grid',value=None,monotonicity='finite_declared_grid_only')
 if points[0][1] is not None and points[0][1]<0:return result|dict(state='BASELINE_BREACHED',value=R(0),reason='La observación inicial ya cruza esta frontera')
 if any(m is None for _,m in points):return result|dict(state='PENDING',reason='Algún punto carece de caja o capacidad; no es un cero')
 if any(b[1]>a[1] for a,b in zip(points,points[1:])):return result|dict(state='PENDING',reason='No monotonía en la grilla; no se elige una frontera')
 index=next((k for k,(_,margin) in enumerate(points) if margin<0),None)
 if index is None:return result|dict(state='BEYOND_SEARCH_RANGE',lower_bound=R(upper),reason='No cruza dentro del rango declarado')
 return result|dict(state='BOUNDED',safe_movement=R(points[index-1][0]),breached_movement=R(points[index][0]),safe_margin=R(points[index-1][1]),breached_margin=R(points[index][1]),resolution=R(step))


def views(spec,sources,result,raw):
 matrix={};tornado={}
 for s in ('Base','Downside'):
  matrix[s]={};tornado[s]={};v=result['scenarios'][s];_,cell=source_cells(sources,s);base=result['monthly_contracts'][s]
  for route in ('with_refinance','without_refinance'):
   matrix[s][route]={};t_rows=[]
   for driver,record in raw['experiments'][s][route].items():
    series={f:[] for f in FRONTIERS};key='with_refinance' if route=='with_refinance' else 'horizon_without_refinance';baseline_calls=F(v[key]['cash_per_usd_10']['total_contributions']);direct=F(base['budget']['direct_hard']);vertical=F(v['development_costs']['vertical_cost'])
    for row in record['adverse']:
     x=F(row['movement']);cash_ok=row['state']=='CALCULATED';capacity=row.get('capacity');principal=F(v['construction_financing']['terminal_principal'])*(1+(vertical/direct*x if driver=='vertical_cost' else 0));rate=F(base['construction']['annual_rate'])+(x/10000 if driver=='interest' else 0);annual=None if capacity is None else F(capacity['annual_service']) if route=='with_refinance' else principal*rate
     margins={'F1':None if not cash_ok else F(row['equity_multiple'])-1,'F2':None if annual is None or annual<=0 else F(capacity['bank_noi'])/annual-1,'F3':None,'F4':None if not cash_ok else baseline_calls-F(row['total_contributions'])}
     if capacity is not None and route=='with_refinance':margins['F3']=F(capacity['maximum_principal_capacity'])-principal-F(base['permanent']['requested_principal'])*F(base['refinance']['cost_fraction'])-F(base['refinance']['reserve_amount'])
     for f in FRONTIERS:series[f].append((x,margins[f]))
    matrix[s][route][driver]={f:bounded_grid(points,F(record['range_upper']),F(record['resolution']),record['unit']) for f,points in series.items()}
    if route=='without_refinance':matrix[s][route][driver]['F3']=dict(state='N/A',value=None,reason='No aplica refinanciación a esta estrategia')
    t=dict(driver=driver,state='PENDING',reason='Un shock carece de caja / TIR certificada',shocks=[]);adverse=record['adverse'][1];favorable=record['favorable'][0];baseline=record['adverse'][0]
    try:
     baseline_irr=baseline['irr_annual']['annual_enclosure'];enclosure(baseline_irr)
     for r in (favorable,adverse):
      if r['state']!='CALCULATED':raise ValueError('Shock bloqueado; no reemplazar por cero')
      interval=delta_enclosure(r['irr_annual']['annual_enclosure'],baseline_irr);t['shocks'].append(dict(movement=r['movement'],delta_irr_annual=interval,delta_equity_multiple=R(F(r['equity_multiple'])-F(baseline['equity_multiple']))))
     t.update(state='CALCULATED',reason=None,irr_impact=impact_interval([r['delta_irr_annual'] for r in t['shocks']]))
    except (ValueError,KeyError,TypeError):pass
    t_rows.append(t)
   tornado[s][route]=ranked(t_rows)
 return matrix,dict(tornado=tornado)


def replay(path,package):
 files=read_package(package);case=json.loads(files['case.json'])
 if case.get('schema')!=CASE_SCHEMA:raise ValueError('El análisis mensual requiere el perfil v37; no reinterpreta otros perfiles')
 sources=read_source_directory(Path(package),include_reference=True);raw=json.loads(Path(path).read_bytes());validate_request(raw,files['case.json'],sources)
 audit=verify_package(Path(package),current_revision_raw=files[CURRENT_REVISION_FILE]);result=json.loads(files['results.json'])
 if audit['vigencia']!='VIGENTE' or result['critical_evidence_review']['status']!='PASSED':raise ValueError('Fuente o revisión no verificadas; análisis PENDING')
 proof=verify(case,sources,result);stress=experiments(case,sources,result);price=price_analysis(case,sources,result,proof);matrix,tornado=views(case,sources,result,stress)
 return dict(state='MONTHLY_MATH_SOURCE_REPLAYED',baseline_results_sha256=sha256(files['results.json']).hexdigest(),case_sha256=sha256(files['case.json']).hexdigest(),breakeven_matrix=matrix,price_grid={s:price[s]['with_refinance'] for s in price},price_all_routes=price,tornado=tornado,recovery_grid=stress,independent_check=proof['checks'],scope='Synthetic mathematical stress, baseline OCR audited; no hypothetical bank terms authenticated',criteria_adopted=False,decision='PENDING',deployment_enabled=False)
