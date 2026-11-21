from copy import deepcopy
from unittest import TestCase
from worksheet_criteria_plug_D275 import SCHEMA,UNITS,apply,validated,FINANCIAL_KEYS
from miniuw_foundation.lorena_screening import BASES,RLV
from worksheet_frontiers_D275 import digest

def config(strict=False):
 return dict(schema=SCHEMA,usage='synthetic_plug_test_only',criteria_adopted=False,revision='SYNTHETIC-STRICT' if strict else 'SYNTHETIC-LENIENT',valid_from='2027-01-01',valid_until='2027-12-31',house_rlv_definition=None,rules=[dict(scenario=s,metric_id=m,unit=UNITS[m],basis=b,period_ref='SYNTHETIC-window',source_ref='SYNTHETIC-rule-'+m,applicability='applicable',fail_scope='explicit_condition',pass_={'operator':'>=','threshold':'2' if strict else '0'},fail={'operator':'<','threshold':'2' if strict else '0'}) for s in ('Base','Downside') for m,b in BASES.items()])
def configuration(strict=False):
 c=config(strict)
 for r in c['rules']:r['pass']=r.pop('pass_')
 return c

def snapshot():
 return dict(scenarios=dict(gross_dated_cash='UNCHANGED_SYNTHETIC'),return_summary=dict(initial=10),computed_metrics={s:{m:dict(value='1',unit=UNITS[m],basis=b,period_ref='SYNTHETIC-window') for m,b in BASES.items()} for s in ('Base','Downside')},breakeven_matrix={'synthetic_boundary':'unchanged'},price_grid={'fixed_debt':'unchanged'},tornado={'declared_shocks':'unchanged'})

class CriteriaPlugTests(TestCase):
 def test_no_strict_lenient_configs_change_any_financial_bytes(self):
  s=snapshot();outputs=[apply(s,c,'2027-06-01') for c in (None,configuration(True),configuration(False))]
  fingerprints={o['financial_snapshot_sha256'] for o in outputs};self.assertEqual(len(fingerprints),1)
  self.assertTrue(all(r['state']=='PENDING' for r in outputs[0]['criteria_comparisons']))
  self.assertTrue(all(r['state']=='FAIL_SIMULATED' for r in outputs[1]['criteria_comparisons']))
  self.assertTrue(all(r['state']=='PASS_SIMULATED' for r in outputs[2]['criteria_comparisons']))
  self.assertTrue(all(o['decision']=='PENDING' and not o['criteria_adopted'] for o in outputs))
 def test_invalid_unit_basis_scenario_operator_and_dates_block(self):
  for field,val in [('unit','USD'),('basis','wrong'),('scenario','Other')]:
   c=configuration();c['rules'][0][field]=val;a=apply(snapshot(),c,'2027-06-01');self.assertTrue(all(r['state']=='PENDING' for r in a['criteria_comparisons']))
  c=configuration();c['rules'][0]['pass']['operator']='==';self.assertTrue(all(r['state']=='PENDING' for r in apply(snapshot(),c,'2027-06-01')['criteria_comparisons']))
  self.assertTrue(all(r['state']=='PENDING' for r in apply(snapshot(),configuration(),'2028-01-01')['criteria_comparisons']))
 def test_blank_observation_not_zero_and_valid_zero_respected(self):
  for blank in [None,'',False]:
   s=snapshot();s['computed_metrics']['Base']['YoC']['value']=blank
   row=next(v for v in apply(s,configuration(),'2027-06-01')['criteria_comparisons'] if v['scenario']=='Base' and v['metric_id']=='YoC');self.assertEqual(row['state'],'PENDING')
  s=snapshot();s['computed_metrics']['Base']['YoC']['value']='0';row=next(v for v in apply(s,configuration(),'2027-06-01')['criteria_comparisons'] if v['scenario']=='Base' and v['metric_id']=='YoC');self.assertEqual(row['state'],'PASS_SIMULATED')
 def test_missing_criterion_never_drops_a_metric(self):
  c=configuration();c['rules'].pop();a=apply(snapshot(),c,'2027-06-01');self.assertEqual(len(a['criteria_comparisons']),20);self.assertTrue(all(v['state']=='PENDING' for v in a['criteria_comparisons']))
 def test_actual_house_rlv_stays_pending_without_definition(self):
  self.assertEqual(apply(snapshot(),configuration(),'2027-06-01')['house_rlv']['state'],'PENDING')
 def test_house_rlv_is_explicit_exception_to_numeric_invariance(self):
  c=configuration();c['house_rlv_definition']=dict(all_applicable_criteria_jointly=True)
  def solver(financial,criteria):return dict(state='SYNTHETIC_ONLY',value=42,reason='ficticio')
  a=apply(snapshot(),c,'2027-06-01',house_rlv_solver=solver);self.assertEqual(a['house_rlv']['value'],42);self.assertEqual(a['financial_snapshot_sha256'],apply(snapshot(),None,'2027-06-01')['financial_snapshot_sha256'])
 def test_rlv_does_not_exclude_YoC_or_spread(self):
  c=configuration();c['house_rlv_definition']=dict(all_applicable_criteria_jointly=False);a=apply(snapshot(),c,'2027-06-01');self.assertEqual(a['house_rlv']['state'],'PENDING')
 def test_source_and_criteria_not_mutated(self):
  s=snapshot();c=configuration();old=deepcopy((s,c));apply(s,c,'2027-06-01');self.assertEqual((s,c),old)
 def test_overlapping_conditions_never_select_favorable_state(self):
  c=configuration();c['rules'][0]['fail']=dict(operator='>',threshold='0');a=apply(snapshot(),c,'2027-06-01');self.assertEqual(a['criteria_comparisons'][0]['state'],'PENDING')
 def test_unresolved_interval_and_intermediate_band_remain_pending(self):
  s=snapshot();s['computed_metrics']['Base']['YoC']['value']=dict(lower='-1',upper='1');a=apply(s,configuration(),'2027-06-01');self.assertEqual(a['criteria_comparisons'][0]['state'],'PENDING')
