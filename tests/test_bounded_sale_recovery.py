import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery,verify_bounded_sale_recovery,parse_bounded_recovery
from piecewise_recovery_test_support import build_case,recovery_spec,raw,sha

def f(q):return F(int(q['numerator']),int(q['denominator']))
def intervals(rows):return [(f(r['lower']),None if r['upper']is None else f(r['upper']))for r in rows]


class BoundedSaleRecoveryTests(unittest.TestCase):
    def setUp(self):self.args,self.base=build_case();self.spec=recovery_spec(self.base)
    def run_case(self):return analyze_bounded_sale_recovery(self.args,self.base,raw(self.spec))
    def reset_case(self,**kwargs):self.args,self.base=build_case(**kwargs);self.spec=recovery_spec(self.base)

    def test_independent_three_segments_and_exact_recovery(self):
        p=self.run_case().payload;a=p['analysis'];self.assertEqual(p['state'],'computed_synthetic_piecewise_recovery')
        self.assertEqual(a['segment_count'],3)
        self.assertEqual([(f(s['price_interval']['lower']),f(s['price_interval']['upper']))for s in a['segments']],[(0,500),(500,800),(800,2000)])
        self.assertEqual([f(s['cash_profit_slope'])for s in a['segments']],[1,F(19,20),1])
        self.assertEqual([f(s['cash_profit_intercept'])for s in a['segments']],[F('-116.0803'),F('-91.0803'),F('-131.0803')])
        self.assertEqual(intervals(a['recovering_price_intervals']),[(F('116.0803'),2000)])
        self.assertEqual(intervals(a['zero_cash_profit_price_intervals']),[(F('116.0803'),F('116.0803'))])

    def test_independent_direct_clamp_costs_at_boundaries_and_base(self):
        a=self.run_case().payload['analysis']
        for row in a['breakpoint_observations']:
            price=f(row['price']);cost=10+min(max(price/20,F(25)),F(40))
            self.assertEqual(f(row['total_cost']),cost)
            self.assertEqual(f(row['net_cash_profit']),price-cost-F('81.0803'))
        for segment in a['segments']:
            price=f(segment['sample_price']);direct=price-(10+min(max(price/20,F(25)),F(40)))-F('81.0803')
            self.assertEqual(f(segment['cash_profit_slope'])*price+f(segment['cash_profit_intercept']),direct)

    def test_exit_cap_inverts_true_piecewise_recovery_boundary(self):
        a=self.run_case().payload['analysis'];caps=a['recovering_exit_cap_intervals']
        self.assertEqual(intervals(caps),[(F(1,50),F(40)/F('116.0803'))])
        self.assertTrue(caps[0]['lower_closed']);self.assertTrue(caps[0]['upper_closed'])

    def test_disconnected_recovery_sets_not_collapsed_to_one_floor(self):
        self.reset_case(rate=3,minimum=0,maximum=2000,extra_cash=1000)
        a=self.run_case().payload['analysis']
        self.assertEqual(intervals(a['recovering_price_intervals']),[(0,F('908.9197')/2),(F('1091.0803'),2000)])
        self.assertEqual(len(a['zero_cash_profit_price_intervals']),2)
        caps=a['recovering_exit_cap_intervals'];self.assertEqual(len(caps),2)
        self.assertEqual(f(caps[0]['lower']),F(1,50));self.assertEqual(f(caps[0]['upper']),F(40)/F('1091.0803'))
        self.assertEqual(f(caps[1]['lower']),F(80)/F('908.9197'));self.assertIsNone(caps[1]['upper'])

    def test_flat_zero_interval_and_adjacent_recovery_merge(self):
        self.reset_case(rate=1,minimum=0,maximum=400,extra_cash=F('91.0803'))
        a=self.run_case().payload['analysis']
        self.assertEqual(intervals(a['zero_cash_profit_price_intervals']),[(0,400)])
        self.assertEqual(intervals(a['recovering_price_intervals']),[(0,2000)])

    def test_root_at_shared_breakpoint_deduplicated(self):
        self.reset_case(extra_uses=F('383.9197'))
        a=self.run_case().payload['analysis']
        self.assertEqual(intervals(a['zero_cash_profit_price_intervals']),[(500,500)])
        self.assertEqual(intervals(a['recovering_price_intervals']),[(500,2000)])

    def test_empty_recovery_domain_is_valid_not_a_calculation_failure(self):
        self.reset_case(extra_uses=F('383.9197'))
        self.spec['gross_price_domain']['upper']=q(F(450))
        p=self.run_case().payload;self.assertEqual(p['state'],'computed_synthetic_piecewise_recovery')
        self.assertEqual(p['analysis']['recovering_price_intervals'],[])
        self.assertEqual(p['analysis']['recovering_exit_cap_intervals'],[]);self.assertEqual(p['decision'],'PENDING')

    def test_isolated_recovery_point_at_local_maximum(self):
        self.reset_case(rate=2,minimum=800,maximum=2000,extra_cash=F('491.0803'))
        self.spec['gross_price_domain']['upper']=q(F(1200))
        a=self.run_case().payload['analysis']
        self.assertEqual(intervals(a['recovering_price_intervals']),[(400,400)])
        self.assertEqual(intervals(a['zero_cash_profit_price_intervals']),[(400,400)])
        self.assertEqual(intervals(a['recovering_exit_cap_intervals']),[(F(1,10),F(1,10))])

    def test_coincident_limits_deduplicate_and_zero_rate_avoids_division(self):
        self.reset_case(minimum=25,maximum=25)
        a=self.run_case().payload['analysis']
        self.assertEqual(a['segment_count'],2)
        self.assertEqual([f(s['cost_slope'])for s in a['segments']],[0,0])
        self.reset_case(rate=0,minimum=25,maximum=40)
        self.assertEqual(self.run_case().payload['analysis']['segment_count'],1)

    def test_boundary_invariant_after_full_repriced_bounded_cash_replay(self):
        from miniuw_foundation.exit_value import produce_exit_value
        before=self.run_case().payload['analysis'];args=list(self.args)
        spec=json.loads(args[3]);spec['cap_rate']['value']=q(F(1,5));args[3]=raw(spec);args[4]=produce_exit_value(args[1],args[2],args[3])
        source=json.loads(args[5]);source['gross_price']['value']=args[4].payload['candidate_value']
        source['gross_price']['source_ref']='miniuw:synthetic-exit-value:'+args[4].sha256+'#/candidate_value'
        args[5]=raw(source);args[6]=produce_sale_costs(args[5])
        bounds=json.loads(args[7]);bounds.update(cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256)
        args[7]=raw(bounds);args[8]=produce_bounded_sale_costs(args[5],args[6],args[7])
        spec=json.loads(args[9]);spec.update(exit_spec_sha256=sha(args[3]),exit_run_sha256=args[4].sha256,cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256,
            bounds_source_sha256=sha(args[7]),bounded_run_sha256=args[8].sha256);args[9]=raw(spec)
        self.args=tuple(args);self.base=assemble_bounded_exit_sale(*self.args);self.spec=recovery_spec(self.base)
        after=self.run_case().payload['analysis'];self.assertNotEqual(before['base_gross_price'],after['base_gross_price'])
        for field in ['fixed_other_cash_constant','segments','recovering_price_intervals','recovering_exit_cap_intervals','zero_cash_profit_price_intervals']:
            self.assertEqual(before[field],after[field])

    def test_unbounded_fee_and_zero_cap_profiles(self):
        self.reset_case(minimum=None,maximum=None)
        a=self.run_case().payload['analysis'];self.assertEqual(a['segment_count'],1)
        self.assertEqual(intervals(a['recovering_price_intervals']),[(F('91.0803')/F(19,20),2000)])
        self.reset_case(minimum=None,maximum=0)
        a=self.run_case().payload['analysis'];self.assertEqual(intervals(a['recovering_price_intervals']),[(F('91.0803'),2000)])

    def test_zero_noi_distinguishes_price_recovery_from_attainable_caps(self):
        self.reset_case(noi_zero=True)
        a=self.run_case().payload['analysis'];self.assertTrue(a['recovery_possible_in_price_domain']);self.assertFalse(a['recovery_possible_via_positive_exit_cap'])
        self.reset_case(noi_zero=True,extra_cash=1000)
        a=self.run_case().payload['analysis'];caps=a['recovering_exit_cap_intervals']
        self.assertEqual(f(caps[0]['lower']),0);self.assertFalse(caps[0]['lower_closed']);self.assertIsNone(caps[0]['upper'])

    def test_point_domain_supported_and_prior_valuation_not_ignored(self):
        self.spec['gross_price_domain']=dict(lower=q(F(400)),upper=q(F(400)))
        a=self.run_case().payload['analysis'];self.assertEqual(a['segment_count'],1);self.assertEqual(intervals(a['recovering_price_intervals']),[(400,400)])
        self.reset_case(retain_valuation=True)
        self.assertIn('existing_valuation_requires_separate_domain_consistency',self.run_case().payload['blockers'])
        self.spec['gross_price_domain']=dict(lower=q(F(500)),upper=q(F(500)))
        self.assertEqual(self.run_case().payload['state'],'computed_synthetic_piecewise_recovery')

    def test_segment_budget_exhaustion_never_publishes_partial_solution(self):
        self.spec['segment_budget']=2;p=self.run_case().payload
        self.assertIsNone(p['analysis']);self.assertIn('piecewise_segment_budget_exceeded',p['blockers'])
        for value in [0,130,True]:
            self.spec['segment_budget']=value
            with self.assertRaises(ValidationError):self.run_case()

    def test_missing_domain_basis_hash_or_outside_price_blocks(self):
        original=copy.deepcopy(self.spec)
        for key,value in [('base_bounded_run_sha256','0'*64),('cost_profile_domain_basis_ref',None),('other_sources_fixed_basis_ref',None)]:
            self.spec=copy.deepcopy(original);self.spec[key]=value
            self.assertIsNone(self.run_case().payload['analysis'])
        for lower,upper in [(-1,2000),(500,2000),(0,300),(500,400)]:
            self.spec=copy.deepcopy(original);self.spec['gross_price_domain']=dict(lower=q(F(lower)),upper=q(F(upper)))
            self.assertIsNone(self.run_case().payload['analysis'])

    def test_bank_blocker_and_limit_conflict_preserved(self):
        self.reset_case(compatible=False)
        p=self.run_case().payload;self.assertIsNone(p['analysis']);self.assertIn('refinance_capacity_or_selection_blocked',p['underlying_calculation_blockers'])
        self.reset_case(minimum=50,maximum=40)
        self.assertIsNone(self.run_case().payload['analysis'])

    def test_replay_rejects_rehashed_base_and_report_forgeries(self):
        p=self.base.payload;p['state']='forged';text=canonical(p)
        with self.assertRaises(ValidationError):analyze_bounded_sale_recovery(self.args,replace(self.base,payload_json=text,sha256=digest(text)),raw(self.spec))
        report=self.run_case();self.assertEqual(verify_bounded_sale_recovery(self.args,self.base,raw(self.spec),report),report)
        p=report.payload;p['analysis']['recovering_price_intervals']=[];text=canonical(p)
        with self.assertRaises(ValidationError):verify_bounded_sale_recovery(self.args,self.base,raw(self.spec),replace(report,payload_json=text,sha256=digest(text)))

    def test_changed_domain_invalidates_result_and_arithmetic_fault_blocks(self):
        report=self.run_case();self.spec['gross_price_domain']['upper']=q(F(1900))
        with self.assertRaises(ValidationError):verify_bounded_sale_recovery(self.args,self.base,raw(self.spec),report)
        with patch('miniuw_foundation.bounded_sale_recovery._bounded',side_effect=ArithmeticBudgetError):p=self.run_case().payload
        self.assertIsNone(p['analysis']);self.assertIn('piecewise_exact_arithmetic_budget_exceeded',p['blockers'])

    def test_syntax_shapes_and_budget(self):
        for value in [b'[]',b'NaN',b'\xff',b' '*65537,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_bounded_recovery(value)

    def test_no_new_ledger_criterion_or_personal_loss_claim(self):
        p=self.run_case().payload
        self.assertTrue(p['analysis']['EM_ge_one_equivalence_defined_over_domain'])
        for key in ['new_scenario_or_investor_ledger_generated','cost_profile_financially_valid_over_domain','funding_availability_verified_over_domain','investment_criterion_adopted','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return']);self.assertIsNone(p['final_economic_capital_loss'])


if __name__=='__main__':unittest.main()
