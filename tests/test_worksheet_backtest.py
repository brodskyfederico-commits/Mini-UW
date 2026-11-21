from unittest import TestCase
from copy import deepcopy
from worksheet_backtest_D275 import compare_metric,compare_case,SCHEMA,METRICS
from worksheet_frontiers_D275 import fraction


def fixture():return dict(schema=SCHEMA,project_id='SYNTHETIC-CLOSED',population='synthetic_test',input_as_of='2020-01-01',observed_as_of='2026-01-01',original_inputs_sha256='a'*64,audited_results_sha256='b'*64,observed_source_sha256='c'*64,measurements=[dict(scenario=s,route=r,metric=m,unit=u,predicted='10',actual='12',actual_source_ref='SYNTHETIC-closed-ledger',explanations=[dict(category='costo',amount='2',source_ref='SYNTHETIC-verified-cost-delta')]) for s in ('Base','Downside') for r in ('with_refinance','without_refinance') for m,u in METRICS.items()],expected_calendar_milestones=['sale'],calendar_comparisons=[dict(milestone='sale',predicted_date='2025-01-01',actual_date='2025-02-01')])

class BacktestTests(TestCase):
 def test_known_synthetic_difference_fully_accounted_for_in_all_routes(self):
  x=compare_case(fixture());self.assertEqual(x['state'],'COMPARED');self.assertTrue(x['all_numeric_differences_exactly_explained']);self.assertEqual(x['calendar'][0]['difference_days'],31)
 def test_unexplained_residual_visible_instead_of_forced_zero(self):
  a=compare_metric('10','13','USD',[dict(category='costo',amount='2',source_ref='SYNTHETIC-cost')]);self.assertEqual(fraction(a['unexplained']['lower']),1);self.assertFalse(a['fully_explained_exactly'])
 def test_missing_actual_does_not_become_zero(self):
  for v in [None,'',False]:self.assertEqual(compare_metric('10',v,'USD',[])['state'],'PENDING')
 def test_zero_observation_respected(self):
  a=compare_metric('10','0','USD',[]);self.assertEqual(fraction(a['difference']['lower']),-10)
 def test_uncertain_irr_difference_remains_an_interval(self):
  a=compare_metric(dict(lower='0.14',upper='0.15'),dict(lower='0.12',upper='0.13'),'annual_fraction',[])
  self.assertEqual(fraction(a['difference']['lower']),fraction('-0.03'));self.assertEqual(fraction(a['difference']['upper']),fraction('-0.01'))
 def test_missing_measurements_keep_overall_pending(self):
  s=fixture();s['measurements'].pop();a=compare_case(s);self.assertEqual(a['state'],'PENDING');self.assertEqual(len(a['missing_measurements']),1)
 def test_invalid_units_and_unsupported_attribution_not_accepted(self):
  self.assertEqual(compare_metric('10','12','SF',[])['state'],'PENDING');self.assertEqual(compare_metric('10','12','USD',[dict(category='inventada',amount='2',source_ref='X')])['state'],'PENDING')
 def test_no_historical_reality_certification_from_synthetic_data(self):
  a=compare_case(fixture());self.assertFalse(a['real_validation_completed']);self.assertEqual(a['real_decision'],'PENDING')
 def test_duplicate_and_missing_original_hash_rejected(self):
  s=fixture();s['measurements'].append(s['measurements'][0])
  with self.assertRaises(ValueError):compare_case(s)
  s=fixture();s['original_inputs_sha256']=None
  with self.assertRaises(ValueError):compare_case(s)
 def test_forecast_inputs_are_not_mutated(self):
  a=fixture();old=deepcopy(a);compare_case(a);self.assertEqual(a,old)

class ObservationBindingTests(TestCase):
 def test_a_declared_hash_does_not_substitute_for_an_actual_source(self):
  from worksheet_backtest_D275 import run
  with self.assertRaisesRegex(ValueError,'respaldo observado'):run(fixture(),None,b'wrong source bytes')

class RealHistoryScopeTests(TestCase):
 def test_real_history_does_not_require_inventing_the_unexecuted_strategy(self):
  s=fixture();s.update(population='closed_real_project',observed_strategy='with_refinance');s['measurements']=[r for r in s['measurements'] if r['route']=='with_refinance'];a=compare_case(s);self.assertEqual(a['state'],'COMPARED');self.assertEqual(len(a['comparisons']),16);self.assertEqual(len(a['not_observed_alternatives']),2)
 def test_same_actual_history_required_for_base_and_downside(self):
  s=fixture();s.update(population='closed_real_project',observed_strategy='with_refinance');s['measurements']=[r for r in s['measurements'] if r['route']=='with_refinance'];s['measurements'][-1]['actual']='13'
  with self.assertRaisesRegex(ValueError,'misma historia'):compare_case(s)
 def test_counterfactual_real_cash_is_not_accepted(self):
  s=fixture();s.update(population='closed_real_project',observed_strategy='with_refinance')
  with self.assertRaisesRegex(ValueError,'no ejecutada'):compare_case(s)

class CalendarCompletenessTests(TestCase):
 def test_missing_calendar_does_not_become_zero_delay(self):
  s=fixture();s.pop('expected_calendar_milestones');a=compare_case(s);self.assertEqual(a['state'],'PENDING');self.assertIsNone(a['calendar'][0]['difference_days'])
