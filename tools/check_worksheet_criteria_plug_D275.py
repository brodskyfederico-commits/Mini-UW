"""Native-source criteria plug rehearsal: none, strict and lenient, unchanged cash."""
from pathlib import Path
from argparse import ArgumentParser
from copy import deepcopy
import json
from fractions import Fraction as Q
from miniuw_worksheet_v1 import read_package,verify_package,CURRENT_REVISION_FILE,encoded
from worksheet_criteria_plug_D275 import apply,SCHEMA,UNITS,FINANCIAL_KEYS
from miniuw_foundation.lorena_screening import BASES,RLV
from worksheet_lorena_screening import calculated_case,JOINT_MAXIMUM
from worksheet_rlv_scope_D273 import FIELD,PROFILE,RULE
from worksheet_frontiers_D275 import fraction,rational,digest
from miniuw_foundation.scheduled_expense_case import sha


def joint_case(case):
 value=deepcopy(case['baseline_case'] if case.get('schema')=='miniuw.synthetic-native-rental-inputs.v36' else case)
 cfg=value['rent_inputs']['definition_screening']['Base']['rlv'];cfg['binding_yields']=['YoC','spread'];cfg.pop('yield_metric',None)
 cfg[FIELD]=dict(profile=PROFILE,rule=RULE,scenario_id='Base',metric_ids=sorted(set(BASES)-{RLV}),source_ref='SYNTHETIC-D273-user-confirmed-joint-scope-test')
 return value


def fixtures(case,strict):
 rules=[];inputs=case['rent_inputs'];revision='SYNTHETIC-D275-STRICT' if strict else 'SYNTHETIC-D275-LENIENT'
 maximum={'equity_cash_in','breakeven_occupancy','equity_TDC',RLV}
 for scenario in ('Base','Downside'):
  purchase=inputs['development']['scenarios'][scenario]['purchase_date'];sale=inputs['supplemental_scope'][scenario]['sale_date']['value']
  calendar=inputs['criterion_noi_contexts'][scenario]['YoC']['period_ref'];stable=calendar.split('/')[0]
  for metric,basis in BASES.items():
   if metric in maximum:passing,failing=('-1','-0.5') if strict else ('2','3');ops=('<=','>')
   else:
    ops=('>=','<')
    if metric=='IRR':passing,failing=('0.5','0.4') if strict else (('0.01','0') if scenario=='Base' else ('-0.99','-1'))
    elif metric=='spread':passing,failing=('10000','9000') if strict else ('-100000','-100001')
    elif metric=='equity_multiple':passing,failing=('10','9') if strict else ('0','-1')
    else:passing,failing=('1','0.9') if strict else ('-1','-2')
   period=f'{purchase}/{sale}' if metric in ('IRR','equity_multiple',RLV) else stable if metric in ('equity_TDC','equity_recovered','equity_cash_in') else calendar
   rules.append(dict(scenario=scenario,metric_id=metric,unit=UNITS[metric],basis=basis,source_ref=revision+'-'+metric,
    applicability='not_applicable' if metric==RLV else 'applicable',reason='El RLV es un slot separado, dependiente del criterio; ensayo no adoptado' if metric==RLV else None,
    period_ref=period,fail_scope='explicit_condition',**{'pass':dict(operator=ops[0],threshold=passing),'fail':dict(operator=ops[1],threshold=failing)}))
 return dict(schema=SCHEMA,usage='synthetic_plug_test_only',criteria_adopted=False,revision=revision,valid_from='2027-01-01',valid_until='2027-12-31',rules=rules,house_rlv_definition=None)


def legacy_configuration(config):
 entries=[]
 for metric in BASES:
  by_scenario={r['scenario']:r for r in config['rules'] if r['metric_id']==metric}
  record=dict(metric_id=metric,unit=UNITS[metric],basis=BASES[metric])
  for scenario,tag in [('Base','base'),('Downside','downside')]:
   for field in ('pass','fail'):
    c=by_scenario[scenario][field];record[field+'_'+tag]=dict(operator=c['operator'],threshold=rational(fraction(c['threshold'])),source_locator=by_scenario[scenario]['source_ref'])
  entries.append(record)
 return dict(revision=config['revision'],criteria_adopted=False,deployment_enabled=False,metrics=entries)


def rehearse(result,case,analysis):
 case=joint_case(case);loose=fixtures(case,False);strict=fixtures(case,True)
 observed,proof=calculated_case(result,case,legacy_configuration(loose),encoded(legacy_configuration(loose)))
 metrics={}
 for scenario in ('Base','Downside'):
  if set(observed['metric_values'][scenario])-{RLV}!=set(BASES)-{RLV}:raise ValueError('Faltan métricas financieras del expediente para comprobar el enchufe')
  by_id={r['metric_id']:r for r in loose['rules'] if r['scenario']==scenario}
  metrics[scenario]={m:dict(record,period_ref=by_id[m]['period_ref']) for m,record in observed['metric_values'][scenario].items() if m!=RLV}
  metrics[scenario][RLV]=dict(basis=BASES[RLV],unit=UNITS[RLV],period_ref=by_id[RLV]['period_ref'],value=None)
 snapshot=dict(scenarios=deepcopy(result['scenarios']),computed_metrics=metrics,breakeven_matrix=analysis['breakeven_matrix'],price_grid=analysis['price_grid'],tornado=analysis['tornado'])
 if 'return_summary' in result:snapshot['return_summary']=deepcopy(result['return_summary'])
 before=encoded(snapshot);cut=case['rent_inputs']['as_of_UTC'][:10]
 variants={name:apply(snapshot,config,cut) for name,config in [('without_criteria',None),('strict',strict),('lenient',loose)]}
 fingerprints={r['financial_snapshot_sha256'] for r in variants.values()}
 if len(fingerprints)!=1 or encoded(snapshot)!=before:raise ValueError('El enchufe alteró la caja o las cifras independientes de criterios')
 for name,wanted in [('strict','FAIL_SIMULATED'),('lenient','PASS_SIMULATED')]:
  rows=[r for r in variants[name]['criteria_comparisons'] if r['metric_id']!=RLV]
  if len(rows)!=18 or any(r['state']!=wanted for r in rows):raise ValueError('El control ficticio no produce los estados esperados: '+name+' '+str(rows))
 def house_solver(financial,config):
  _,computed=calculated_case(result,case,legacy_configuration(config),encoded(legacy_configuration(config)))
  search=computed['Base']['rlv_price_search']
  return dict(state='SYNTHETIC_ONLY' if search['state']=='bounded_synthetic' else 'PENDING',value=search.get('price_lower'),proof=search,
   negative_price_flag=search.get('price_lower') is not None and search['price_lower']<0,all_applicable_criteria_jointly=True,criteria_adopted=False)
 with_definition=deepcopy(loose);with_definition['house_rlv_definition']=dict(all_applicable_criteria_jointly=True)
 house=apply(snapshot,with_definition,cut,house_rlv_solver=house_solver)
 if house['financial_snapshot_sha256'] not in fingerprints:raise ValueError('El RLV dependiente del criterio alteró los flujos')
 return dict(status='passed',financial_snapshot_sha256=fingerprints.pop(),case_sha256=result['case_sha256'],source_analysis_sha256=digest(analysis),
  metric_comparisons_per_fixture=20,non_RLV_compared_metrics=18,variants={k:dict(comparisons=v['criteria_comparisons'],financial_snapshot_sha256=v['financial_snapshot_sha256'],house_rlv=v['house_rlv']) for k,v in variants.items()},
  house_definition_test=house['house_rlv'],fixtures=dict(strict=strict,lenient=loose),real_decision='PENDING',criteria_adopted=False,deployment_enabled=False)


def main():
 p=ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 saved=read_package(a.package);audit=verify_package(a.package,current_revision_raw=saved[CURRENT_REVISION_FILE])
 if audit['vigencia']!='VIGENTE':raise ValueError('Expediente no vigente')
 result=json.loads(saved['results.json']);analysis=json.loads(a.analysis.read_bytes())
 if analysis.get('state')!='SOURCE_REPLAYED' or analysis.get('baseline_results_sha256')!=sha(saved['results.json']):raise ValueError('El análisis no corresponde al expediente')
 report=rehearse(result,json.loads(saved['case.json']),analysis)
 for name,fixture in report['fixtures'].items():(a.output/('criteria_fixture_'+name+'.json')).write_bytes(encoded(fixture))
 (a.output/'validation.json').write_bytes(encoded(report));print(json.dumps(dict(status='passed',financial_numbers_unchanged=True,simulated_metrics_per_fixture=18)))
if __name__=='__main__':main()
