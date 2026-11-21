"""Source-level synthetic replay adapter and independent boundary acceptance.

All changes are made to worksheet literals and their synthetic documentary
backing before intake; results are never edited to manufacture a boundary.
"""
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path
from argparse import ArgumentParser

from check_worksheet_scenario_program_D268 import (settings,sources_for,make_packet,drivers,
 source_bundle,reference,independently_verify,source_cells,decimal,numeric_cells)
from check_worksheet_irr_certificate_D270 import certified_sources
from miniuw_worksheet_v1 import encoded,read_package,verify_package,CURRENT_REVISION_FILE
from worksheet_intake_D198 import register,assemble,source_inventory
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_frontiers_D275 import DRIVERS,fraction,rational,matrix

MAP={'residential_rent':['18'],'exit_cap':['31'],'vertical_cost':['22'],
     'interest':['25','26'],'lease_up':['24'],'vacancy':['20']}

class AuditedSourceRuns:
 def __init__(self,root):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=False)
  self.spec=settings();self.original=sources_for(self.spec,self.root/'seed')
  self.base,self.sources=make_packet(self.spec,self.original,'baseline',[],drivers(),self.root/'origin-source')
  self.cache={};self.initial={};self.runs=[];self.failures={}
 def replay(self,driver,movement):
  key='baseline' if movement==0 else driver+'-'+str(movement).replace('/','_').replace('-','m')
  if key in self.cache:return self.cache[key]
  records=drivers();delta=-movement if driver=='residential_rent' else movement
  for i in MAP[driver]:
   records[i]['values']={s:rational(delta) for s in ('Base','Downside')}
  spec,sources=make_packet(self.base,{k:v for k,v in self.sources.items() if k!='independent_reference_raw'},
   MAP[driver][0],[] if movement==0 else MAP[driver],records,self.root/(key+'-source'),revision='SYNTHETIC-D268-'+MAP[driver][0])
  if driver=='vertical_cost' and movement:
   # T2 changes vertical unit cost only, unlike the broader D268 hard-cost vector.
   for scenario,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
    _,cell=source_cells(self.sources,scenario)
    sources[arg]=numeric_cells(sources[arg],{k:decimal(cell(k)) for k in ('C37','C38')})
   sources['evidence_raw']=source_bundle(spec,sources)
   for rec in spec['rent_inputs']['bank_debt_yield'].values():rec['quote_source_sha256']=sha(sources['evidence_raw'])
   sources['independent_reference_raw']=encoded(reference(spec,{k:v for k,v in sources.items() if k!='independent_reference_raw'}))
  # New counterfactual test evidence, never a wider claim about the original comps.
  # The earlier negative controls retain their original ranges and stay PENDING.
  changed_support=False
  for scenario,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
   _,cell=source_cells(sources,scenario)
   role='rent' if driver=='residential_rent' else 'exit_cap' if driver=='exit_cap' else None
   if role is not None and movement:
    record=spec['rent_inputs']['market_evidence']['scenarios'][scenario][role]
    record['document']['ranges']={k:dict(minimum=rational(cell(k)),maximum=rational(cell(k))) for k in record['document']['ranges']}
    record['document']['source_ref']='SYNTHETIC-D275-explicit-counterfactual-'+role
    record['sha256']=sha(encoded(record['document']));changed_support=True
  if changed_support:
   sources['evidence_raw']=source_bundle(spec,sources)
   for rec in spec['rent_inputs']['bank_debt_yield'].values():rec['quote_source_sha256']=sha(sources['evidence_raw'])
   sources['independent_reference_raw']=encoded(reference(spec,{k:v for k,v in sources.items() if k!='independent_reference_raw'}))
  spec,sources=certified_sources(spec,sources)
  # Reject any unexpected input mutation, including accidentally stressing C51/C53.
  for scenario,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
   old,_=source_cells(self.sources,scenario);new,_=source_cells(sources,scenario)
   allowed=set(DRIVERS[driver]['cells']) if movement else set()
   assert {k for k in old if old[k]!=new[k]}<=allowed
  directory=self.root/(key+'-run');directory.mkdir()
  (directory/'settings.json').write_bytes(encoded(spec))
  for arg,name in source_inventory(sources).items():(directory/name).write_bytes(sources[arg])
  receipt=assemble(spec,register(sources,'SYNTHETIC-D275-'+key),sources,directory/'package')
  saved=read_package(directory/'package');result=json.loads(saved['results.json'])
  audit=verify_package(directory/'package',current_revision_raw=saved[CURRENT_REVISION_FILE])
  assert audit['vigencia']=='VIGENTE', 'Auditoría B16 no vigente'
  assert result['critical_evidence_review']['status']=='PASSED', 'B12: lectura o evidencia crítica no verificada; revisar runtime OCR y fuentes'
  independent=independently_verify(spec,sources,result)
  (directory/'independent-check.json').write_bytes(encoded(independent))
  entry=(spec,sources,result,dict(case_sha256=sha(saved['case.json']),results_sha256=sha(saved['results.json']),
   sources_sha256=sha(encoded({k:sha(v) for k,v in sorted(sources.items()) if v is not None})),
   independent_reference_sha256=sha(sources['independent_reference_raw'])))
  self.cache[key]=entry;self.runs.append(dict(id=key,source_directory=str(directory),**entry[-1]));print(json.dumps(dict(verified_run=key,count=len(self.runs))),flush=True)
  return entry
 def __call__(self,driver,movement,scenario,route):
  failure_key=(driver,str(movement))
  if failure_key in self.failures:return self.failures[failure_key]
  try:
   spec,sources,result,hashes=self.replay(driver,movement)
   view=result['scenarios'][scenario];_,cell=source_cells(sources,scenario)
   candidate=view if route=='with_refinance' else view['horizon_without_refinance']
   cash=candidate.get('cash_per_usd_10');capacity=view['capacity']
   bank=fraction(capacity['bank_noi']);payoff=fraction(view['construction_financing']['construction_principal_payoff'])
   annual=fraction(view['permanent_loan']['annual_sizing_service']) if route=='with_refinance' else payoff*cell('C52')
   margins={f:None for f in ('F1','F2','F3','F4')}
   if annual>0:margins['F2']=rational(bank/annual-1)
   if route=='with_refinance':
    fee=fraction(spec['rent_inputs']['requested_principal'])*cell('C73')
    reserve=cell('C74')*spec['rent_inputs']['refinance_costs']['scenarios'][scenario]['eligible_units']
    margins['F3']=rational(fraction(capacity['maximum_principal_capacity'])-payoff-fee-reserve)
   if cash is not None:
    margins['F1']=rational(fraction(cash['equity_multiple'])-1)
    if movement==0:self.initial[scenario,route]=fraction(cash['total_contributions'])
    elif (scenario,route) not in self.initial:self(driver,Q(),scenario,route)
    margins['F4']=rational(self.initial[scenario,route]-fraction(cash['total_contributions']))
   return dict(state='VERIFIED',b12='PASSED',b16='PASSED',independent_check='PASSED',margins=margins,
    cash_sha256=None if cash is None else sha(encoded(cash)),
    equity_multiple=None if cash is None else cash['equity_multiple'],
    irr_annual=(result['screening']['irr_by_scenario'][scenario] if route=='with_refinance' else candidate.get('irr',{})).get('annual_enclosure'),**hashes)
  except (ValueError,AssertionError,KeyError,TypeError,OSError) as err:
   row=dict(state='PENDING',reason='Corrida de fuentes bloqueada: '+type(err).__name__+': '+str(err));self.failures[failure_key]=row;print(json.dumps(dict(blocked_run=str(failure_key),reason=row['reason'])),flush=True);return row

def configuration():
 return dict(schema='miniuw.synthetic-mathematical-frontiers.v1',usage='synthetic_test_only_no_criteria',drivers={
  driver:dict(unit=record['unit'],upper=rational(3 if driver=='lease_up' else 100 if record['unit']=='bps' else Q(1,10) if record['unit']=='relative_fraction' else 1),
   step=rational(3 if driver=='lease_up' else 100 if record['unit']=='bps' else Q(1,10) if record['unit']=='relative_fraction' else 1),
   monotonic_probes=2,maximum_evaluations=8,source_ref='SYNTHETIC-D275-declared-coarse-test-range-'+driver)
  for driver,record in DRIVERS.items()})

def main():
 parser=ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--smoke',action='store_true');parser.add_argument('--tornado',action='store_true');args=parser.parse_args()
 runs=AuditedSourceRuns(args.output/'source-runs')
 if args.smoke:
  row=runs('residential_rent',Q(), 'Base','with_refinance');assert row['state']=='VERIFIED',row
  result=dict(status='passed',smoke=row)
 else:
  config=configuration();result=matrix(config,runs);result['runs']=runs.runs
  result['configuration']=config
  if args.tornado:
   from worksheet_tornado_D275 import tornado,SCHEMA as TORNADO
   shocks=dict(schema=TORNADO,drivers={d:dict(unit=v['unit'],magnitude=v['step'],source_ref='SYNTHETIC-D275-symmetric-test-'+d) for d,v in config['drivers'].items()})
   result['tornado']=tornado(shocks,runs);result['tornado_configuration']=shocks
  result['runs']=runs.runs;result['blocked_source_runs']=[dict(driver=k[0],movement=k[1],**v) for k,v in runs.failures.items()]
 (args.output/'validation.json').write_bytes(encoded(result));print(json.dumps({'runs':len(runs.runs),'output':str(args.output)}))
if __name__=='__main__':main()
