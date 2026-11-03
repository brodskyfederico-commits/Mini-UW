import json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.recovery_case_check import check_recovery_case,verify_recovery_case
from piecewise_recovery_test_support import build_case,recovery_spec,raw
from recovery_case_test_support import reprice

def f(q):return F(int(q['numerator']),int(q['denominator']))


class RecoveryCaseCheckTests(unittest.TestCase):
    def setUp(self):
        self.args,self.base=build_case();self.sr=raw(recovery_spec(self.base));self.r=analyze_bounded_sale_recovery(self.args,self.base,self.sr)
    def values(self,price=200,fee=None):return self.args,self.base,self.sr,self.r,*reprice(self.args,price,fee)
    def test_before_at_after_boundary_matches_full_cash(self):
        for price,profit in [(F('115.0803'),-1),(F('116.0803'),0),(F('117.0803'),1)]:
            p=check_recovery_case(*self.values(price)).payload
            self.assertEqual(p['state'],'matched_synthetic_full_case');self.assertEqual(f(p['comparison']['replayed_net_cash_profit']),profit)
            self.assertEqual(f(p['comparison']['cash_profit_difference']),0);self.assertEqual(p['decision'],'PENDING')
    def test_shared_breakpoints_use_all_matching_segments(self):
        for price in [500,800]:
            p=check_recovery_case(*self.values(price)).payload
            self.assertEqual(p['comparison']['matching_segment_count'],2);self.assertEqual(p['state'],'matched_synthetic_full_case')
    def test_each_regime_matches_independent_cost_and_profit(self):
        for price,cost,profit in [(200,35,F('83.9197')),(800,50,F('668.9197')),(2000,50,F('1868.9197'))]:
            p=check_recovery_case(*self.values(price)).payload['comparison']
            self.assertEqual(f(p['replayed_closing_cost']),cost);self.assertEqual(f(p['replayed_net_cash_profit']),profit)
    def test_changed_fee_even_if_replayed_valid_requires_new_curve(self):
        p=check_recovery_case(*self.values(400,F(1,10))).payload
        self.assertIn('fixed_profile_source_changed_at_argument_5',p['blockers']);self.assertIsNone(p['comparison'])
    def test_out_of_domain_not_extrapolated(self):
        p=check_recovery_case(*self.values(2001)).payload
        self.assertIn('candidate_price_outside_declared_domain',p['blockers'])
    def test_changed_funding_assumption_not_ignored(self):
        values=list(self.values());args=list(values[4]);s=json.loads(args[9]);s['equity_funding_assumption_ref']='SYNTHETIC-changed-funding'
        args[9]=raw(s);values[4]=tuple(args);values[5]=assemble_bounded_exit_sale(*values[4])
        p=check_recovery_case(*values).payload;self.assertIn('fixed_profile_source_changed_at_argument_9',p['blockers'])
    def test_different_project_and_bank_failure_stay_visible(self):
        candidate,run=build_case(compatible=False)
        p=check_recovery_case(self.args,self.base,self.sr,self.r,candidate,run).payload
        self.assertIn('candidate_guarded_return_blocked',p['blockers']);self.assertTrue(p['candidate_calculation_blockers'])
    def test_blocked_reference_curve_does_not_certify_candidate(self):
        self.args,self.base=build_case(compatible=False);self.sr=raw(recovery_spec(self.base));self.r=analyze_bounded_sale_recovery(self.args,self.base,self.sr)
        p=check_recovery_case(*self.values()).payload;self.assertIn('reference_recovery_unavailable',p['blockers'])
    def test_updated_hash_candidate_forgery_rejected(self):
        values=list(self.values());run=values[-1];p=run.payload;p['state']='forged';text=canonical(p)
        values[-1]=replace(run,payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):check_recovery_case(*values)
    def test_report_replay_and_updated_hash_forgery(self):
        values=self.values();run=check_recovery_case(*values);self.assertEqual(verify_recovery_case(*values,run),run)
        p=run.payload;p['comparison']['replayed_net_cash_profit']={'numerator':'999','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):verify_recovery_case(*values,replace(run,payload_json=text,sha256=digest(text)))
    def test_budget_fault_no_partial_comparison(self):
        values=self.values()
        with patch('miniuw_foundation.recovery_case_check._bounded',side_effect=ArithmeticBudgetError):p=check_recovery_case(*values).payload
        self.assertIsNone(p['comparison']);self.assertIn('recovery_case_exact_arithmetic_budget_exceeded',p['blockers'])
    def test_no_freshness_personal_return_or_adoption_claim(self):
        p=check_recovery_case(*self.values()).payload
        for key in ['candidate_inputs_automatically_tuned','investment_criterion_adopted','evidence_currency_checked','funding_availability_verified','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return'])


if __name__=='__main__':unittest.main()
