"""Independent boundary equations, missingness and audit gate invariants."""
from fractions import Fraction as Q
from unittest import TestCase
from copy import deepcopy
from worksheet_frontiers_D275 import search,fraction,rational,DRIVERS,matrix


def config(driver='exit_cap'):
 return dict(driver=driver,unit=DRIVERS[driver]['unit'],upper=rational(100),step=rational(1),monotonic_probes=10,maximum_evaluations=30,source_ref='SYNTHETIC-boundary-test')
def adapter(margin):
 def run(d,x,s,r):return dict(state='VERIFIED',b12='PASSED',b16='PASSED',independent_check='PASSED',
  case_sha256='a'*64,results_sha256='b'*64,sources_sha256='c'*64,margins={k:rational(margin(x)) for k in ('F1','F2','F3','F4')})
 return run

def run(c,fn):return search(c,fn,scenario='Base',route='with_refinance',frontier='F1')

class FrontierTests(TestCase):
 def test_exact_affine_crossing_and_equality_safe(self):
  x=run(config(),adapter(lambda x:Q(71,2)-x));self.assertEqual(x['state'],'BOUNDED')
  self.assertEqual(fraction(x['safe_movement']),35);self.assertEqual(fraction(x['breached_movement']),36)
  self.assertEqual(x['decision'],'PENDING')
 def test_exact_zero_at_boundary_not_a_blank(self):
  x=run(config(),adapter(lambda x:35-x));self.assertEqual(fraction(x['safe_margin']),0);self.assertEqual(fraction(x['breached_movement']),36)
 def test_non_monotone_is_not_a_selected_crossing(self):
  x=run(config(),adapter(lambda x:50-x if x<50 else x-80));self.assertEqual(x['state'],'PENDING');self.assertEqual(x['monotonicity'],'failed')
 def test_evidence_missing_blocks_instead_of_zero(self):
  fn=adapter(lambda x:50-x)
  def missing(d,x,s,r):return fn(d,x,s,r) if x!=50 else dict(state='PENDING',reason='Falta cita')
  x=run(config(),missing);self.assertEqual(x['state'],'PENDING');self.assertIsNone(x['value'])
 def test_independent_or_b12_b16_missing_blocks(self):
  for gate in ['b12','b16','independent_check','case_sha256','results_sha256','sources_sha256']:
   fn=adapter(lambda x:50-x)
   def fault(d,x,s,r):
    a=fn(d,x,s,r);a.pop(gate);return a
   self.assertEqual(run(config(),fault)['state'],'PENDING',gate)
 def test_beyond_search_is_not_zero_or_infinity(self):
  x=run(config(),adapter(lambda x:101-x));self.assertEqual(x['state'],'BEYOND_SEARCH_RANGE');self.assertIsNone(x['value']);self.assertEqual(fraction(x['lower_bound']),100)
 def test_original_breach_is_explicit_zero_movement(self):
  x=run(config(),adapter(lambda x:-1-x));self.assertEqual(x['state'],'BASELINE_BREACHED');self.assertEqual(fraction(x['value']),0)
 def test_invalid_or_missing_ranges_do_not_get_defaults(self):
  for val in [None,'',False,0,-1]:
   c=config();c['upper']=val;self.assertEqual(run(c,adapter(lambda x:50-x))['state'],'PENDING')
 def test_bounded_budget_remains_pending(self):
  c=config();c['maximum_evaluations']=3;self.assertEqual(run(c,adapter(lambda x:50-x))['state'],'PENDING')
 def test_month_granularity_requires_whole_months(self):
  c=config('lease_up');c['step']=rational(Q(1,2));self.assertEqual(run(c,adapter(lambda x:50-x))['state'],'PENDING')
 def test_exact_fraction_resolution(self):
  c=config('residential_rent');c.update(upper=rational(1),step=rational(Q(1,1000)),maximum_evaluations=40)
  x=run(c,adapter(lambda x:Q(1,3)-x));self.assertEqual(fraction(x['safe_movement']),Q(333,1000));self.assertEqual(fraction(x['breached_movement']),Q(334,1000))
 def test_matrix_requires_all_six_declared_drivers(self):
  with self.assertRaises(ValueError):matrix(dict(schema='miniuw.synthetic-mathematical-frontiers.v1',drivers={}),adapter(lambda x:1-x))
 def test_input_not_mutated(self):
  c=config();old=deepcopy(c);run(c,adapter(lambda x:50-x));self.assertEqual(c,old)

class RouteApplicabilityTests(TestCase):
 def test_refi_frontier_is_explicitly_not_applicable_without_refi(self):
  def forbidden(*args):raise AssertionError('No debe pedir una corrida de refi para esta ruta')
  a=search(config(),forbidden,scenario='Base',route='without_refinance',frontier='F3');self.assertEqual(a['state'],'N/A');self.assertIsNone(a['value'])

class NumericSafetyTests(TestCase):
 def test_bounded_scientific_literals_and_booleans(self):
  self.assertEqual(fraction('1e-3'),Q(1,1000))
  for value in ['1e999999999','1e1301',dict(numerator=True,denominator='1'),dict(numerator='0',denominator=False)]:
   with self.assertRaises(ValueError):fraction(value)

class InitialBreachTests(TestCase):
 def test_known_initial_breach_does_not_depend_on_unavailable_future_stress(self):
  def fn(d,x,s,r):return adapter(lambda y:-1)(d,x,s,r) if x==0 else dict(state='PENDING',reason='Capacidad del estrés no respaldada')
  a=run(config(),fn);self.assertEqual(a['state'],'BASELINE_BREACHED');self.assertEqual(fraction(a['value']),0);self.assertEqual(len(a['observed_points']),1)
