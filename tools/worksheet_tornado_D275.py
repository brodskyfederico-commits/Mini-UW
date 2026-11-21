"""Symmetric, explicitly declared sensitivities from audited source-level runs.

IRR changes remain intervals: no midpoint or convenient root is selected.
Overlapping impact enclosures share an unresolved rank instead of false order.
"""
from worksheet_frontiers_D275 import DRIVERS,fraction,rational,pending

SCHEMA='miniuw.synthetic-six-driver-tornado.v1'


def enclosure(raw):
 if not isinstance(raw,dict):raise ValueError('Falta intervalo certificado de TIR')
 a,b=fraction(raw.get('lower')),fraction(raw.get('upper'))
 if a>b:raise ValueError('Intervalo de TIR invertido')
 return a,b

def delta_enclosure(current,baseline):
 a,b=enclosure(current);lo,hi=enclosure(baseline)
 return dict(lower=rational(a-hi),upper=rational(b-lo))

def impact_interval(values):
 bounds=[enclosure(v) for v in values]
 lower=max(min(abs(a),abs(b)) if a*b>0 else 0 for a,b in bounds)
 upper=max(max(abs(a),abs(b)) for a,b in bounds)
 return dict(lower=rational(lower),upper=rational(upper))

def ranked(rows):
 complete=[r for r in rows if r['state']=='CALCULATED']
 for row in complete:
  a,b=enclosure(row['irr_impact'])
  row['rank_min']=1+sum(enclosure(other['irr_impact'])[0]>b for other in complete if other is not row)
  row['rank_max']=len(complete)-sum(enclosure(other['irr_impact'])[1]<a for other in complete if other is not row)
  row['ranking_basis']='Intervalo del impacto absoluto máximo de los dos shocks; sin elegir una raíz o punto medio'
 return sorted(rows,key=lambda r:(r.get('rank_min',len(rows)+1),r['driver']))

def tornado(config,evaluator):
 if not isinstance(config,dict) or config.get('schema')!=SCHEMA or set(config.get('drivers',{}))!=set(DRIVERS):
  raise ValueError('Se requieren seis shocks simétricos explícitos, sin defaults')
 result={}
 for scenario in ('Base','Downside'):
  result[scenario]={}
  for route in ('with_refinance','without_refinance'):
   rows=[]
   for driver,decl in config['drivers'].items():
    row=dict(driver=driver,state='PENDING',shocks=[])
    try:
     magnitude=fraction(decl.get('magnitude'))
     if magnitude<=0 or decl.get('unit')!=DRIVERS[driver]['unit'] or not isinstance(decl.get('source_ref'),str) or not decl['source_ref'].strip():
      raise ValueError('Shock, unidad o fuente sin confirmar')
     if driver=='lease_up' and magnitude.denominator!=1:raise ValueError('Lease-up requiere meses enteros')
     base=evaluator(driver,0,scenario,route)
     if base.get('state')!='VERIFIED':raise ValueError('Falta caja base auditada')
     base_irr=base.get('irr_annual');enclosure(base_irr);em=fraction(base.get('equity_multiple'))
     for movement in (-magnitude,magnitude):
      observation=evaluator(driver,movement,scenario,route)
      if observation.get('state')!='VERIFIED' or any(observation.get(k)!='PASSED' for k in ('b12','b16','independent_check')):
       row['shocks'].append(dict(movement=rational(movement),state='PENDING',reason=observation.get('reason','Corrida bloqueada')))
       continue
      try:
       irr=delta_enclosure(observation.get('irr_annual'),base_irr)
       delta=fraction(observation.get('equity_multiple'))-em
       row['shocks'].append(dict(state='CALCULATED',movement=rational(movement),delta_irr_annual=irr,
        delta_equity_multiple=rational(delta),case_sha256=observation['case_sha256'],results_sha256=observation['results_sha256'],cash_sha256=observation.get('cash_sha256')))
      except (ValueError,KeyError,TypeError) as error:row['shocks'].append(dict(movement=rational(movement),state='PENDING',reason=str(error)))
     if len(row['shocks'])==2 and all(v['state']=='CALCULATED' for v in row['shocks']):
      row.update(state='CALCULATED',irr_impact=impact_interval([v['delta_irr_annual'] for v in row['shocks']]))
     else:row['reason']='Un shock no tiene caja o TIR certificada; permanece visible'
    except (ValueError,TypeError,KeyError) as error:row['reason']=str(error)
    rows.append(row)
   result[scenario][route]=ranked(rows)
 return dict(schema=SCHEMA,tornado=result,criteria_adopted=False,real_decision='PENDING',deployment_enabled=False)
