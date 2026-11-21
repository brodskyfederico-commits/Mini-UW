"""Source-bound D277 presentation analyses: explicit asking, bounded price range.

No market data, criteria adoption, runtime debt resizing or financial defaults.
"""
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import json
from fractions import Fraction as Q
from worksheet_frontiers_D275 import fraction as F,rational as R,digest
from worksheet_monthly_analysis_D276 import views as old_views
from worksheet_monthly_experiments_D276 import experiments
from worksheet_monthly_experiments_D276 import price_analysis as legacy_price
from worksheet_user_price_D275 import grid,MONTHLY_SCHEMA,RULE
from check_monthly_oracle_D276 import verify
from check_worksheet_scenario_program_D268 import source_cells
from worksheet_intake_D198 import read_source_directory
from miniuw_worksheet_v1 import read_package,verify_package,CURRENT_REVISION_FILE
SCHEMA='miniuw.synthetic-monthly-review-analysis-request.D277.v1'
ASKING='miniuw.synthetic-asking-price-note.D277.v1'


def asking_price(note,case_raw,sources):
 if not isinstance(note,dict) or set(note)!={'schema','usage','case_sha256','workbooks','price','currency','source_ref','date','scope'}:raise ValueError('Falta nota completa del precio pedido; C32 no lo sustituye')
 if note['schema']!=ASKING or note['usage']!='synthetic_review_assumption' or note['currency']!='USD' or not note['source_ref'].startswith('SYNTHETIC-') or not note['date'] or not note['scope']:raise ValueError('Precio pedido sin ámbito / fuente sintética')
 from datetime import date
 date.fromisoformat(note['date'])
 if note['case_sha256']!=sha256(case_raw).hexdigest() or note['workbooks']!={s:sha256(sources[k]).hexdigest() for s,k in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]}:raise ValueError('Precio pedido de otra revisión')
 p=F(note['price'])
 if p<=0:raise ValueError('Precio pedido no positivo')
 return p


def request(case_raw,sources,note):
 asking_price(note,case_raw,sources)
 return dict(schema=SCHEMA,case_sha256=sha256(case_raw).hexdigest(),sources_sha256={k:sha256(v).hexdigest() for k,v in sources.items() if isinstance(v,bytes)},asking_note=note,include_stress=True,usage='synthetic_mathematical_review_only')


def reason(record):
 if record.get('reason_code')=='CAPACITY' or record.get('within_capacity') is False:
  c=record.get('capacity',{});limits=[k for k,v in c.get('limits',{}).items() if c.get('requested_principal') is not None and F(c['requested_principal'])>F(v)]
  return '/'.join(limits) or 'capacidad DSCR/LTV/DY'
 text=record.get('reason','')
 if 'monoton' in text.lower():return 'no monotonía'
 if any(v in text.lower() for v in ('raíz','tir','root')):return 'TIR sin raíz certificada'
 return text or 'faltan caja / evidencia'


def views(spec,sources,result,raw):
 matrix,tornado=old_views(spec,sources,result,raw,principal_from_rows=True)
 for s,routes in matrix.items():
  for route,drivers in routes.items():
   for driver,frontiers in drivers.items():
    records=raw['experiments'][s][route][driver]
    for f,entry in frontiers.items():
     if entry['state']=='PENDING':
      blocked=next((r for r in records['adverse'] if r['state']!='CALCULATED'),None)
      entry['visible_reason']=reason(blocked) if blocked and f in ('F1','F4') else reason(entry)
      entry['reason_detail']=None if blocked is None else deepcopy(blocked)
    row=next(v for v in tornado['tornado'][s][route] if v['driver']==driver)
    if row['state']=='PENDING':
     shocks=[records['favorable'][0],records['adverse'][1]];blocked=next((r for r in shocks if r['state']!='CALCULATED'),None)
     row['visible_reason']=reason(blocked) if blocked else 'TIR sin raíz certificada';row['reason_detail']=deepcopy(shocks)
 return matrix,tornado


def guard_fixed_construction_capacity(g,*,eligible,drawn,ltc,p0,c33):
 blocked=[]
 for point in g['price_grid']:
  if point.get('price') is None:continue
  revised=F(eligible)+(F(point['price'])-F(p0))*(1+F(c33))
  if revised<=0 or F(drawn)>revised*F(ltc):
   point.update(state='PENDING',values=None,target_status='PENDING',reason='LTC: deuda fija supera costos elegibles al nuevo precio');blocked.append(point['price'])
 if blocked:g['max_price_for_targets']=dict(state='PENDING',price=None,reason='LTC: puntos fuera de capacidad; no se extrapola la meta',blocked_prices=blocked)
 return g


def price_analysis(base,sources,result,proof,asking):
 if proof.get('state')!='PASSED' or proof.get('results_sha256')!=digest(result) or proof.get('settings_sha256')!=digest(base) or proof.get('source_sha256s')!={k:sha256(v).hexdigest() for k,v in sources.items() if isinstance(v,bytes)}:raise ValueError('Falta cotejo de esta revisión')
 asking=F(asking)
 if asking<=0:raise ValueError('Falta precio pedido; no usar C32 silenciosamente')
 out={}
 for s in ('Base','Downside'):
  out[s]={};_,cell=source_cells(sources,s);v=result['scenarios'][s]
  for mode,key in [('with_refinance','with_refinance'),('without_refinance','horizon_without_refinance')]:
   cash=v[key].get('cash_per_usd_10')
   if cash is None:out[s][mode]=dict(state='PENDING',reason='Ruta sin caja por capacidad / evidencia',price_grid=[],max_price_for_targets=dict(state='PENDING',price=None));continue
   scale=F(cash['scale_factor']);fund=v['construction_financing'];other=sum((max(Q(),F(r['operating_noi'])) for r in v['commercial_leaseup']['monthly'] if r['start']<result['monthly_contracts'][s]['stabilization_date']),Q())
   source=dict(schema=MONTHLY_SCHEMA,rule=RULE,source_check='INDEPENDENTLY_VERIFIED',source_ref='SYNTHETIC-D277-fixed-debt-math-not-new-bank-terms',source_sha256=proof['results_sha256'],purchase_price=R(cell('C32')),closing_fraction=R(cell('C33')),tdc=v['tdc'],applied_equity=R(F(fund['total_contributions'])-F(fund['closing_free_cash'])),fixed_debt=fund['drawn'],fixed_other_sources=R(other),noi_uw=v['noi_uw'],gross_events=[dict(id=e['event_id'],date=e['date'],kind=e['kind'],amount=R(F(e['amount'])/scale),source_ref=e['source_ref']) for e in cash['events']],initial_event_id=cash['basis_event_ids'][0],dates=[r['date'] for r in v[key]['return_summary']['dated_cash']],periods_per_year=12)
   config=dict(schema=MONTHLY_SCHEMA,source_ref='SYNTHETIC-D277-asking-plus-minus30',lower=R(asking*Q(7,10)),upper=R(asking*Q(13,10)),step=R(asking*Q(3,100)),user_targets={'annual_irr':dict(operator='>=',value='0.15')})
   g=grid(source,config)
   if base.get('schema')=='miniuw.synthetic-native-rental-inputs.v38':g=guard_fixed_construction_capacity(g,eligible=result['monthly_contracts'][s]['construction']['eligible_total'],drawn=fund['drawn'],ltc=cell('C51'),p0=cell('C32'),c33=cell('C33'))
   for n,p in enumerate(g['price_grid']):p['is_asking_price']=n==10
   m=g['max_price_for_targets']
   if m['state'] in ('BEYOND_GRID','NO_PRICE_IN_GRID'):m.update(state='OUTSIDE_RANGE',direction='above_upper' if m['state']=='BEYOND_GRID' else 'below_lower',price=None,reason='FUERA DE RANGO ±30%; no extrapolar')
   out[s][mode]=g|dict(configuration=config,asking_price=R(asking),evaluated_price=R(cell('C32')),target_scope='15% anual hipotético; no criterio de Lorena ni RLV de la casa')
 return out


def replay(path,package):
 files=read_package(package);case=json.loads(files['case.json']);sources=read_source_directory(Path(package),include_reference=True);raw=json.loads(Path(path).read_bytes())
 if case.get('schema') not in ('miniuw.synthetic-native-rental-inputs.v37','miniuw.synthetic-native-rental-inputs.v38'):raise ValueError('Perfil de análisis no soportado')
 if raw!=request(files['case.json'],sources,raw.get('asking_note')):raise ValueError('Solicitud alterada / otra revisión; no aceptar resultados manuales')
 audit=verify_package(Path(package),current_revision_raw=files[CURRENT_REVISION_FILE]);result=json.loads(files['results.json'])
 if audit['vigencia']!='VIGENTE' or result['critical_evidence_review']['status']!='PASSED':raise ValueError('Fuentes / vigencia PENDING')
 proof=verify(case,sources,result);stress=experiments(case,sources,result);matrix,tornado=views(case,sources,result,stress);price=price_analysis(case,sources,result,proof,asking_price(raw['asking_note'],files['case.json'],sources))
 return dict(state='MONTHLY_MATH_SOURCE_REPLAYED',baseline_results_sha256=sha256(files['results.json']).hexdigest(),case_sha256=sha256(files['case.json']).hexdigest(),breakeven_matrix=matrix,price_grid={s:price[s]['with_refinance'] for s in price},price_all_routes=price,tornado=tornado,recovery_grid=stress,independent_check=proof['checks'],asking_note=raw['asking_note'],criteria_adopted=False,decision='PENDING',deployment_enabled=False)
