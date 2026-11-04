from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction as F
from pathlib import Path
import copy,importlib.util,json,unittest

from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.primitive_periodic_returns import isolate_primitive_periodic_returns as solve,primitive,_COUNTER
from miniuw_foundation.periodic_returns import isolate_periodic_returns as legacy
from miniuw_foundation.irr_checked_output import _annual_roots,_current_annual_roots

ROOT=Path(__file__).resolve().parents[1]


def contains(root,q):
    if root['exact_discount_factor']is not None:return F(root['exact_discount_factor'])==q
    r=root['discount_factor_interval'];return F(r['lower'])<q<=F(r['upper'])


class PrimitivePeriodicReturnTests(unittest.TestCase):
    def test_sixteen_exact_reference_cases_keep_all_roots_and_multiplicities(self):
        spec=importlib.util.spec_from_file_location('oracle',ROOT/'references/validate_periodic_irr_isolation.py')
        ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
        cases=[[-100,110],[-2,1],[-100,230,-132],[-1,2,-1],[-1,3,-3,1],
            [1,-1,1],[1,1],[1,2,3],[-1,-2,-3],[5],[0,-1,1],[-100,110,0,0],[0,0,0],
            [-2,0,1],[4,0,-4,0,1],[F(1000001,1000000),-F(2000001,1000000),1]]
        for p in cases:
            expected=ref.isolate_periodic(p,F(1,100000),200)
            actual=solve(p,F(1,100000),200,200000)
            for key in ('roots','unresolved_intervals','root_classification','distinct_positive_discount_roots'):
                self.assertEqual(actual[key],expected[key],(p,key))

    def test_factored_polynomial_retains_distinct_simple_and_repeated_roots(self):
        p=[F(1)]
        factors=[(F(1,2),1),(F(1),1),(F(2),2),(F(3),1),(F(-1),1)]
        for q,m in factors:
            for _ in range(m):
                out=[F(0)]*(len(p)+1)
                for i,c in enumerate(p):out[i]-=q*c;out[i+1]+=c
                p=out
        out=[F(0)]*(len(p)+2)
        for i,c in enumerate(p):out[i]+=c;out[i+2]+=c
        result=solve(out,F(1,100000),256,200000)
        self.assertEqual(result['status'],'complete_synthetic');self.assertEqual(result['distinct_positive_discount_roots'],4)
        for q,m in factors[:-1]:
            matched=[r for r in result['roots']if contains(r,q)];self.assertEqual(len(matched),1);self.assertEqual(matched[0]['multiplicity'],m)

    def test_sparse_sixty_five_point_root_has_independent_sign_and_uniqueness_certificate(self):
        flows=[0]*65
        for k,c in {0:-1000,56:-400,60:100,63:100,64:578}.items():flows[k]=c
        old=legacy(flows,F(1,1000000),256,200000);new=solve(flows,F(1,1000000),256,200000)
        self.assertEqual(old['root_classification'],'arithmetic_budget_exhausted')
        self.assertEqual(new['status'],'complete_synthetic');self.assertEqual(new['distinct_positive_discount_roots'],1)
        self.assertEqual(new['coefficient_bit_limit'],4096);self.assertLessEqual(new['arithmetic_operations'],200000)
        root=new['roots'][0];interval=root['discount_factor_interval'];lo,hi=F(interval['lower']),F(interval['upper'])
        evaluate=lambda x:sum(F(c)*x**k for k,c in enumerate(flows))
        self.assertGreater(lo,0);self.assertLess(evaluate(lo),0);self.assertGreaterEqual(evaluate(hi),0)
        # P(x)/x^56 has a strictly positive derivative term by term on x>0.
        for k,c in enumerate(flows):
            if c and k!=56:self.assertGreater(c*(k-56),0)
        self.assertEqual(root['multiplicity'],1);self.assertIsNone(new['selected_rate'])

    def test_global_positive_negative_and_rational_scales_preserve_roots_and_inputs(self):
        source=[F(-100),F(230),F(-132)];before=copy.deepcopy(source)
        expected=solve(source,F(1,100000),200,200000)['roots']
        for factor in (F(7),F(-3),F(13,17)):
            self.assertEqual(solve([c*factor for c in source],F(1,100000),200,200000)['roots'],expected)
        self.assertEqual(source,before)

    def test_zero_discount_factors_endpoints_and_cashless_tail_are_not_extra_rates(self):
        delayed=solve([0,0,-1,1],F(1,100000),200,200000)
        self.assertEqual(delayed['excluded_zero_discount_factor_multiplicity'],2)
        self.assertEqual(delayed['distinct_positive_discount_roots'],1);self.assertTrue(contains(delayed['roots'][0],F(1)))
        a=solve([-100,110],F(1,100000),200,200000)
        b=solve([-100,110,0,0],F(1,100000),200,200000)
        self.assertEqual(a['roots'],b['roots'])
        self.assertEqual(solve([0,0],F(1,100000),200,200000)['status'],'indeterminate')

    def test_split_and_operation_exhaustion_never_select_a_partial_or_favorable_rate(self):
        split=solve([-100,230,-132],F(1,100000),0,200000)
        self.assertEqual(split['status'],'incomplete_synthetic');self.assertEqual(split['roots'],[])
        self.assertEqual(split['unresolved_intervals'][0]['distinct_roots'],2)
        budget=solve([-100,230,-132],F(1,100000),200,1)
        self.assertEqual(budget['root_classification'],'arithmetic_budget_exhausted');self.assertEqual(budget['roots'],[])
        for r in (split,budget):self.assertIsNone(r['selected_rate']);self.assertEqual(r['decision'],'PENDING')

    def test_bit_budget_is_preserved_for_coefficients_and_denominators(self):
        for p in ([F(2**4096),1],[F(1,2**4096),1],[F(1,2**3000-1),F(1,2**3001-1),1]):
            r=solve(p,F(1,100000),200,200000)
            self.assertEqual(r['root_classification'],'arithmetic_budget_exhausted');self.assertEqual(r['roots'],[])
        self.assertEqual(solve([-1,2],F(1,100000),200,200000)['status'],'complete_synthetic')

    def test_invalid_types_and_unsupported_controls_are_rejected(self):
        for p,width,splits,budget in (([],F(1,100),2,100),([None,1],F(1,100),2,100),([True,1],F(1,100),2,100),
            ([-1,1.1],F(1,100),2,100),([-1,2],0,2,100),([-1,2],.01,2,100),([-1,2],F(1,100),True,100),
            ([-1,2],F(1,100),2049,100),([-1,2],F(1,100),2,200001),([0]*66,F(1,100),2,100)):
            with self.assertRaises(ValidationError):solve(p,width,splits,budget)

    def test_primitive_content_reduction_preserves_signs_zero_and_positive_scale(self):
        token=_COUNTER.set(dict(used=0,limit=200000))
        try:
            source=[F(-6,35),F(12,35),F(0),F(-18,35)];result=primitive(source)
            self.assertEqual(result,[F(-1),F(2),F(0),F(-3)])
            factors=[b/a for a,b in zip(source,result)if a];self.assertEqual(set(factors),{F(35,6)})
            self.assertEqual(primitive([0,0]),[F(0)])
        finally:_COUNTER.reset(token)

    def test_irrational_and_repeated_irrational_roots_keep_certified_intervals(self):
        for flows,multiplicity in (([-2,0,1],1),([4,0,-4,0,1],2)):
            r=solve(flows,F(1,1000000),256,200000);root=r['roots'][0];iv=root['discount_factor_interval']
            self.assertIsNone(root['exact_discount_factor']);self.assertEqual(root['multiplicity'],multiplicity)
            self.assertLess(F(iv['lower'])**2,2);self.assertGreaterEqual(F(iv['upper'])**2,2)
            rate=root['periodic_rate_interval'];self.assertLessEqual(F(rate['upper'])-F(rate['lower']),F(1,1000000))

    def test_concurrent_calls_and_legacy_executor_remain_independent(self):
        before=legacy([-100,110],F(1,100000),200,200000)
        requests=[([-100,110],200000),([-100,230,-132],1),([-1,2,-1],200000)]*3
        with ThreadPoolExecutor(max_workers=3)as pool:
            results=list(pool.map(lambda args:solve(args[0],F(1,100000),200,args[1]),requests))
        for args,r in zip(requests,results):self.assertEqual(r['status'],'incomplete_synthetic'if args[1]==1 else'complete_synthetic')
        self.assertEqual(legacy([-100,110],F(1,100000),200,200000),before)

    def test_annualization_requires_declared_compatible_frequency_and_preserves_overflow_pending(self):
        monthly=solve([-100,110],F(1,100000),200,200000)['roots']
        for frequency,step in ((None,1),(12,3)):
            annual,blockers=_annual_roots(monthly,frequency,step)
            self.assertEqual(annual,[]);self.assertEqual(blockers,['annualization_frequency_missing_or_inconsistent'])
        annual,blockers=_annual_roots(monthly,12,1)
        self.assertEqual(blockers,[]);self.assertTrue(annual)
        huge=[dict(exact_periodic_rate=str(F(2**500)),periodic_rate_interval=None)]
        annual,blockers=_annual_roots(huge,12,1)
        self.assertEqual(annual,[]);self.assertEqual(blockers,['IRR_annualization_arithmetic_budget_exceeded'])

    def test_one_resolved_root_does_not_hide_another_unresolved_root(self):
        partial=solve([3,-3,-1,1],F(1,1000000),2,200000)
        self.assertEqual(partial['status'],'incomplete_synthetic')
        self.assertEqual(partial['distinct_positive_discount_roots'],2);self.assertEqual(len(partial['roots']),1)
        current,attempted,blockers=_current_annual_roots(partial,12,1)
        self.assertEqual(current,[]);self.assertEqual(len(attempted),1)
        self.assertIn('IRR_incomplete_root_inventory_current_intervals_withheld',blockers)


if __name__=='__main__':unittest.main()
