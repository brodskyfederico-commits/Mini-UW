from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.periodic_returns import isolate_periodic_returns


def run(flows,width=F(1,1000000),splits=256,operations=200000):
    return isolate_periodic_returns(flows,width,splits,operations)


def rate_bounds(root):
    if root['exact_periodic_rate'] is not None:
        r=F(root['exact_periodic_rate']);return r,r
    i=root['periodic_rate_interval'];return F(i['lower']),F(i['upper'])


class PeriodicReturnsTests(unittest.TestCase):
    def assertContains(self,p,expected):
        self.assertEqual(p['status'],'complete_synthetic');self.assertEqual(len(p['roots']),1)
        lo,hi=rate_bounds(p['roots'][0]);self.assertLessEqual(lo,expected);self.assertLessEqual(expected,hi)
        self.assertLessEqual(hi-lo,F(1,1000000))

    def test_known_positive_return(self):self.assertContains(run([-100,110]),F(1,10))
    def test_known_negative_return(self):self.assertContains(run([-100,50]),F(-1,2))
    def test_zero_return(self):self.assertContains(run([-100,100]),F(0))

    def test_two_rates_preserved_without_selection(self):
        p=run([-100,230,-132]);self.assertEqual(p['distinct_positive_discount_roots'],2)
        roots=sorted(rate_bounds(r)for r in p['roots'])
        for bounds,expected in zip(roots,[F(1,10),F(1,5)]):self.assertLessEqual(bounds[0],expected);self.assertLessEqual(expected,bounds[1])
        self.assertIsNone(p['selected_rate']);self.assertEqual(p['decision'],'PENDING')

    def test_tangent_root_multiplicity_two(self):
        p=run([1,-2,1]);self.assertContains(p,F(0));self.assertEqual(p['roots'][0]['multiplicity'],2)

    def test_triple_root(self):
        p=run([-1,3,-3,1]);self.assertContains(p,F(0));self.assertEqual(p['roots'][0]['multiplicity'],3)

    def test_irrational_tangent_root_and_sign_certification(self):
        # (2q^2-1)^2; positive q=1/sqrt(2), r=sqrt(2)-1.
        p=run([1,0,-4,0,4]);self.assertEqual(len(p['roots']),1)
        lo,hi=rate_bounds(p['roots'][0]);self.assertLessEqual((1+lo)**2,2);self.assertGreaterEqual((1+hi)**2,2)
        self.assertEqual(p['roots'][0]['multiplicity'],2);self.assertLessEqual(hi-lo,F(1,1000000))

    def test_close_roots_not_merged(self):
        # q=1 and q=1000001/1000000, distinct near-zero rates.
        p=run([F(1000001,1000000),-F(2000001,1000000),1],width=F(1,10**9))
        self.assertEqual(p['status'],'complete_synthetic');self.assertEqual(len(p['roots']),2)
        roots=sorted(rate_bounds(r)for r in p['roots']);self.assertLess(roots[0][1],roots[1][0])

    def test_zero_discount_factors_excluded_and_leading_empty_period_retained(self):
        p=run([0,-100,110]);self.assertContains(p,F(1,10));self.assertEqual(p['excluded_zero_discount_factor_multiplicity'],1)

    def test_nonpositive_discount_roots_excluded(self):
        p=run([1,2,1]);self.assertEqual(p['distinct_positive_discount_roots'],0);self.assertEqual(p['roots'],[])

    def test_identically_zero_is_indeterminate(self):
        p=run([0,0,0]);self.assertEqual(p['status'],'indeterminate');self.assertIsNone(p['distinct_positive_discount_roots'])

    def test_constant_and_positive_cash_only_have_no_roots(self):
        for flows in [[1],[0,0,1],[1,1,1]]:
            p=run(flows);self.assertEqual(p['status'],'complete_synthetic');self.assertEqual(p['distinct_positive_discount_roots'],0)

    def test_split_budget_preserves_unresolved_root_count(self):
        p=run([-100,230,-132],splits=0);self.assertEqual(p['status'],'incomplete_synthetic')
        self.assertEqual(sum(i['distinct_roots']for i in p['unresolved_intervals']),2);self.assertEqual(p['roots'],[])

    def test_arithmetic_budget_blocks_without_guessing(self):
        p=run([-100,110],operations=1);self.assertEqual(p['root_classification'],'arithmetic_budget_exhausted');self.assertIsNone(p['selected_rate'])
        p=run([-(2**4097),1]);self.assertEqual(p['status'],'incomplete_synthetic')

    def test_strict_types_and_bounds(self):
        for flows in [[],[True,1],[1.0,2],[1]*66]:
            with self.assertRaises(ValidationError):run(flows)
        for width,splits,operations in [(F(0),10,100),(1.0,10,100),(F(1),True,100),(F(1),2049,100),(F(1),10,0)]:
            with self.assertRaises(ValidationError):run([-100,110],width,splits,operations)

    def test_concurrent_budgets_are_isolated_and_inputs_unchanged(self):
        flows=[-100,110]
        def work(i):return run(flows,operations=1 if i%2 else 200000)['status']
        with ThreadPoolExecutor(max_workers=4)as e:results=list(e.map(work,range(20)))
        self.assertEqual(results,['complete_synthetic'if i%2==0 else'incomplete_synthetic'for i in range(20)])
        self.assertEqual(flows,[-100,110]);self.assertContains(run(flows),F(1,10))
