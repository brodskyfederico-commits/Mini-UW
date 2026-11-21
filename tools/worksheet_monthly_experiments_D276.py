"""Explicit mathematical counterfactuals over the frozen synthetic source case.

Upstream XLSX/PDF extraction is audited once for the baseline. Each counterfactual
changes literal worksheet observations and specified dependent calendars; its
cash is reconciled by a separate literal-source oracle. This does not assert that
an unchanged bank PDF offers the shocked rate, authorize a loan, widen market
comparable evidence or constitute a fresh bot/OCR validation of hypothetical
terms. Native deal intake never consumes this analytical profile.
"""
from pathlib import Path
from copy import deepcopy
from datetime import date
from fractions import Fraction as Q
import json
from hashlib import sha256
from worksheet_frontiers_D275 import fraction as F,rational as R,digest,DRIVERS
from worksheet_monthly_D275 import month
from worksheet_monthly_integration_D276 import integrate
from worksheet_florida_tax_D203 import window_taxes
from worksheet_monthly_native_D276 import documents_for
from worksheet_user_price_D275 import grid,MONTHLY_SCHEMA,RULE
from check_monthly_native_D276 import set_numeric_cells
from check_monthly_oracle_D276 import verify
from check_worksheet_scenario_program_D268 import source_cells,decimal

SCHEMA='miniuw.synthetic-monthly-mathematical-experiments.v1'
RANGES={'residential_rent':('0.50','0.05'),'exit_cap':('500','50'),'vertical_cost':('0.50','0.05'),'interest':('500','50'),'lease_up':('24','2'),'vacancy':('30','3')}


def counterfactual(base,sources,result,driver,movement,*,only_scenario=None):
 if driver not in DRIVERS:raise ValueError('Driver no declarado')
 x=F(movement);spec=deepcopy(base);i=spec['rent_inputs'];new_sources=dict(sources);contracts={}
 for name,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
  if only_scenario is not None and name!=only_scenario:continue
  _,old=source_cells(sources,name);edits={}
  for cell in DRIVERS[driver]['cells']:
   value=old(cell)*(1-x) if driver=='residential_rent' else old(cell)*(1+x) if driver=='vertical_cost' else old(cell)+x/({'bps':10000,'months':1,'percentage_points':100}[DRIVERS[driver]['unit']]);edits[cell]=decimal(value)
  new_sources[arg]=set_numeric_cells(sources[arg],edits);_,cell=source_cells(new_sources,name)
  if not (cell('C35')>=0 and cell('C52')>=0 and cell('C69')>=0 and 0<cell('C67')<=1 and 0<=cell('C14') and cell('C14')+cell('C15')<=1 and cell('C47').denominator==1 and 0<=cell('C47')<=36):raise ValueError('Movimiento fuera del dominio físico / financiero; no se recorta a cero')
  contract=deepcopy(result['monthly_contracts'][name]);original_stable=date.fromisoformat(contract['stabilization_date']);start=date.fromisoformat(contract['purchase_date']);finish=date.fromisoformat(contract['construction_finish']);stable=month(finish,int(cell('C47')));sale=month(stable,60);pre=int(cell('C46')+cell('C47'));cfg=i['monthly_integration']['scenarios'][name]
  contract['stabilization_date']=str(stable);contract['sale_date']=str(sale);i['supplemental_scope'][name]['sale_date']['value']=str(sale)
  for buyer in i['florida_property_tax']['scenarios'][name]['rolls']['buyer'].values():buyer['event_date']=str(sale)
  commercial=cfg['commercial'];commercial['end']=str(month(sale,12))
  shift=int(cell('C47')-old('C47'))
  for space in commercial['spaces']:
   space['lease_start']=str(month(date.fromisoformat(space['lease_start']),shift));space['lease_end']=commercial['end']
   for step in space['rent_steps']:step['effective_date']=str(month(date.fromisoformat(step['effective_date']),shift))
  contract['commercial']=deepcopy(commercial)
  calendar=i['project_calendar']['scenarios'][name];budget_cfg=i['construction_budget']['scenarios'][name];units=sum(g['units'] for g in i['groups'].values());vertical=cell('C35')*units;direct=vertical+cell('C37')*budget_cfg['parking']['spaces']+cell('C38');cont=direct*cell('C39');soft=(direct+cont)*cell('C40');contract['budget'].update(direct_hard=R(direct),contingency=R(cont),soft=R(soft),residential_leaseup=R(F(calendar['lease_up_shortfall_per_month'])*cell('C47')))
  old_direct=F(result['monthly_contracts'][name]['budget']['direct_hard']);old_soft=F(result['monthly_contracts'][name]['budget']['soft']);events=[deepcopy(e) for p in contract['construction']['periods'] for e in p['events']]
  construction=contract['construction'];construction.update(stabilization=str(stable),annual_rate=R(cell('C52')),eligible_total=R(direct),periods=[dict(start=str(month(start,k)),end=str(month(start,k+1)),inventory_complete=True,source_ref='SYNTHETIC-D276-hypothetical-calendar',events=[]) for k in range(pre)])
  for event in events:
   if event['id'].startswith(('hard-invoice-','hard-draw-')):
    event['amount']=R(F(event['amount'])*direct/old_direct)
    if event['kind']=='draw':event['eligible_invoice']=R(F(event['eligible_invoice'])*direct/old_direct)
   elif event['id'].startswith('soft-'):event['amount']=R(F(event['amount'])*soft/old_soft)
   elif event['id']=='contingency':event['amount']=R(cont)
   elif event['id']=='residential-leaseup-prefund':event['amount']=contract['budget']['residential_leaseup']
   d=date.fromisoformat(event['date']);index=(d.year-start.year)*12+d.month-start.month
   if d==stable:index=pre-1
   if not 0<=index<pre:raise ValueError('Evento queda fuera de obra; no se cambia su fecha silenciosamente')
   construction['periods'][index]['events'].append(event)
  dates=[month(start,k) for k in range(pre+72)];tax=window_taxes(i['florida_property_tax'],name,sale,{str(d):(d,1,d>=sale) for d in dates});factor=1+F(i['stabilized_tax_stress']['scenarios'][name]['relative_change']);contract['monthly_taxes']=[dict(start=str(d),amount=R(F(tax[str(d)]['total'])*(factor if d>=stable else 1)),source_ref='sha256:'+tax[str(d)]['source_sha256']) for d in dates]
  baseline_rows={r['start']:r for r in result['monthly_contracts'][name]['residential_monthly']};residential=[];gross=sum(old('C'+str(k))*i['groups'][g]['units']*(F(i['groups'][g]['rentable_sf_per_unit']) if source_cells(sources,name)[0]['C7']['literal']=='PER SF' else 1)*12 for k,g in zip(range(8,12),('studio','1BR','2BR','3BR')));bank_loss=F(i['supplemental_scope'][name]['bank_vacancy_addition']['value'])
  for d in dates:
   if d<stable:vals={role:R(0) for role in ('operating_before_tax','bank_before_tax','refinance_before_tax','sale_before_tax')}
   else:
    age=(d.year-stable.year)*12+d.month-stable.month;row=baseline_rows[str(month(original_stable,age))];year=age//12;vals={}
    for role in ('operating_before_tax','bank_before_tax','refinance_before_tax','sale_before_tax'):
     delta=Q()
     if driver=='residential_rent':delta=-x*gross*(1+cell('C75'))**year*(1-old('C14')-old('C15')-(bank_loss if role=='bank_before_tax' else 0))*(1-cell('C58'))/12
     elif driver=='vacancy':delta=-x/100*gross*(1+cell('C75'))**year*(1-cell('C58'))/12
     vals[role]=R(F(row[role])+delta)
   residential.append(dict(start=str(d),source_ref='SYNTHETIC-D276-explicit-counterfactual-'+driver,**vals))
  contract['residential_monthly']=residential;contract['sale_cap']=R(cell('C67'));contract['permanent']['annual_nominal_rate']=R(cell('C69'));contract['source_inputs_sha256']=digest(dict(original=result['monthly_contracts'][name]['source_inputs_sha256'],driver=driver,movement=R(x)))
  cfg['commercial']=deepcopy(contract['commercial']);contracts[name]=contract
 return spec,new_sources,contracts


def evaluate(base,sources,result,driver,x):
 try:
  spec,current,contracts=counterfactual(base,sources,result,driver,x)
 except ValueError:
  # A favorable bound can be outside Base's physical domain yet valid for
  # Downside. Evaluate those scopes independently instead of silently clipping
  # a value or suppressing the other scenario's valid observation.
  combined={};checks={};errors={}
  for name in ('Base','Downside'):
   try:
    spec,current,contracts=counterfactual(base,sources,result,driver,x,only_scenario=name);v=integrate(contracts[name],documents_for(spec['rent_inputs']['monthly_integration']['scenarios'][name]['documents']))
    if v['state']!='CALCULATED':raise ValueError(v.get('reason','PENDING'))
    checked=verify(spec,current,dict(scenarios={name:v},monthly_contracts=contracts),scenario_names=(name,));combined[name]=v;checks[name]=checked['checks'][name]
   except (ValueError,KeyError,AssertionError,ZeroDivisionError) as err:combined[name]=dict(state='PENDING',reason=str(err));errors[name]=str(err)
  if len(errors)==2:raise ValueError('; '.join(errors.values()))
  return dict(state='CALCULATED',scenarios=combined,independent_check=checks,scenario_blockers=errors,counterfactual_inputs_sha256=digest(dict(driver=driver,movement=R(x),base=digest(base))),cash_sha256=digest(combined),source_audit_scope='Baseline PDF/OCR only; independent mathematical scopes for valid scenarios')
 computed={name:integrate(contract,documents_for(spec['rent_inputs']['monthly_integration']['scenarios'][name]['documents'])) for name,contract in contracts.items()};snapshot=dict(scenarios=computed,monthly_contracts=contracts)
 if any(v['state']!='CALCULATED' for v in computed.values()):raise ValueError('; '.join(v.get('reason','PENDING') for v in computed.values() if v['state']!='CALCULATED'))
 independent=verify(spec,current,snapshot)
 return dict(state='CALCULATED',scenarios=computed,independent_check=independent['checks'],counterfactual_inputs_sha256=digest(spec),cash_sha256=digest({s:{r:v[k].get('cash_per_usd_10') for r,k in [('with_refinance','with_refinance'),('without_refinance','horizon_without_refinance')]} for s,v in computed.items()}),source_audit_scope='Baseline PDF/OCR only; hypothetical inputs independently reconciled, not newly quoted or adopted')


def experiments(base,sources,result,progress=None):
 if result['critical_evidence_review']['status']!='PASSED':raise ValueError('Falta auditoría fuente del caso original')
 baseline_proof=verify(base,sources,result)
 cache={};traces=[]
 def point(driver,x):
  key=(driver,str(x))
  if key not in cache:
   try:cache[key]=evaluate(base,sources,result,driver,x)
   except (ValueError,AssertionError,KeyError,ZeroDivisionError) as err:cache[key]=dict(state='PENDING',reason=str(err))
   traces.append(dict(driver=driver,movement=R(x),**({k:v for k,v in cache[key].items() if k!='scenarios'})))
   if progress:progress(driver,str(x),cache[key]['state'])
  return cache[key]
 output={s:{r:{} for r in ('with_refinance','without_refinance')} for s in ('Base','Downside')}
 for driver,(upper,step) in RANGES.items():
  stop,spacing=F(upper),F(step);moves=[k*spacing for k in range(int(stop/spacing)+1)];adverse=[(x,point(driver,x)) for x in moves];favorable=[(-x,point(driver,-x)) for x in moves[1:]]
  for s in output:
   for route in output[s]:
    key='with_refinance' if route=='with_refinance' else 'horizon_without_refinance'
    def row(x,p):
     if p['state']!='CALCULATED':return dict(movement=R(x),state='PENDING',reason=p['reason'])
     v=p['scenarios'][s]
     if v['state']!='CALCULATED':return dict(movement=R(x),state='PENDING',reason=v.get('reason','Falta cálculo del escenario'))
     r=v[key];cash=r.get('cash_per_usd_10');record=dict(movement=R(x),state=r['state'],within_capacity=v['capacity']['within_capacity'],capacity=v['capacity'],cash_sha256=None if cash is None else digest(cash))
     if cash:record.update(capital_margin=R(F(cash['total_distributions'])-F(cash['total_contributions'])),total_contributions=cash['total_contributions'],total_receipts=cash['total_distributions'],irr_annual=r['return_summary']['irr_annual'],equity_multiple=cash['equity_multiple'])
     else:record['reason']='Préstamo supera capacidad o estrategia bloqueada; no se interpreta como pérdida cero'
     return record
    adverse_rows=[row(x,p) for x,p in adverse];favorable_rows=[row(x,p) for x,p in favorable];baseline=adverse_rows[0];first=next((a for a in adverse_rows if a['state']=='CALCULATED' and F(a['capital_margin'])<0),None);recovery=next((a for a in favorable_rows if a['state']=='CALCULATED' and F(a['capital_margin'])>=0),None)
    output[s][route][driver]=dict(unit=DRIVERS[driver]['unit'],range_upper=R(stop),resolution=R(spacing),baseline_breached=baseline.get('capital_margin') is not None and F(baseline['capital_margin'])<0,adverse=adverse_rows,favorable=favorable_rows,first_sampled_capital_breach=first,first_sampled_recovery=recovery,recovery_state='RECOVERED_ON_DECLARED_GRID' if recovery else 'NOT_RECOVERED_OR_PENDING_WITHIN_DECLARED_GRID',monotonicity='No global monotonicity asserted; every declared point is displayed')
 return dict(schema=SCHEMA,state='COMPUTED_EXPERIMENTS',baseline_results_sha256=digest(result),experiments=output,point_audits=traces,scope='Explicit synthetic mathematical counterfactuals; source audit is baseline only; not new OCR evidence, investment criteria, or actual financing',decision='PENDING',criteria_adopted=False,deployment_enabled=False)


def price_analysis(base,sources,result,proof):
 if proof.get('state')!='PASSED' or proof.get('results_sha256')!=digest(result) or proof.get('settings_sha256')!=digest(base) or proof.get('source_sha256s')!={k:sha256(v).hexdigest() for k,v in sources.items() if isinstance(v,bytes)}:raise ValueError('Falta cotejo independiente de la misma revisión para precio')
 output={}
 for scenario in ('Base','Downside'):
  output[scenario]={};_,cell=source_cells(sources,scenario);v=result['scenarios'][scenario]
  for mode,key in [('with_refinance','with_refinance'),('without_refinance','horizon_without_refinance')]:
   c=v[key]['cash_per_usd_10'];scale=F(c['scale_factor']);events=[dict(id=e['event_id'],date=e['date'],kind=e['kind'],amount=R(F(e['amount'])/scale),source_ref=e['source_ref']) for e in c['events']];fund=v['construction_financing'];free=F(fund['closing_free_cash']);other=sum((max(Q(),F(r['operating_noi'])) for r in v['commercial_leaseup']['monthly'] if r['start']<result['monthly_contracts'][scenario]['stabilization_date']),Q())
   source=dict(schema=MONTHLY_SCHEMA,rule=RULE,source_check='INDEPENDENTLY_VERIFIED',source_ref='SYNTHETIC-D276-15pct-annual-target-not-Lorena',source_sha256=proof['results_sha256'],purchase_price=R(cell('C32')),closing_fraction=R(cell('C33')),tdc=v['tdc'],applied_equity=R(F(fund['total_contributions'])-free),fixed_debt=fund['drawn'],fixed_other_sources=R(other),noi_uw=v['noi_uw'],gross_events=events,initial_event_id=c['basis_event_ids'][0],dates=[r['date'] for r in v[key]['return_summary']['dated_cash']],periods_per_year=12)
   config=dict(schema=MONTHLY_SCHEMA,source_ref='SYNTHETIC-D276-explicit-user-math-target',lower=R(200000),upper=R(3500000),step=R(100000),user_targets={'annual_irr':dict(operator='>=',value='0.15')})
   output[scenario][mode]=grid(source,config)|dict(configuration=config,target_scope='Hypothetical 15% annual IRR, never Lorena criteria or house RLV')
 return output
