import copy
from dataclasses import replace
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.recovery_case_check import check_recovery_case
from miniuw_foundation.current_bounded_recovery import required_bounded_recovery_sources
from miniuw_foundation.current_bounded_exit_output import required_bounded_exit_sources
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_recovery_case import assemble_current_recovery_case,verify_current_recovery_case
from piecewise_recovery_test_support import build_case,recovery_spec,raw
from recovery_case_test_support import reprice
from evidence_currency_test_support import registry,AS_OF


class CurrentRecoveryCaseTests(unittest.TestCase):
    def setUp(self):
        args,base=build_case();sr=raw(recovery_spec(base));r=analyze_bounded_sale_recovery(args,base,sr)
        candidate,run=reprice(args,F('116.0803'));self.check_args=(args,base,sr,r,candidate,run)
        self.check=check_recovery_case(*self.check_args)
        self.ref=registry(args[4].payload['context'],required_bounded_recovery_sources(args,sr))
        self.candidate=registry(candidate[4].payload['context'],required_bounded_exit_sources(candidate))
    def values(self):
        rr=raw(self.ref);cr=raw(self.candidate)
        return self.check_args,self.check,rr,evaluate_evidence_currency(rr,AS_OF),cr,evaluate_evidence_currency(cr,AS_OF),AS_OF
    def run_case(self):return assemble_current_recovery_case(*self.values())
    def test_both_current_expose_exact_boundary_without_pass(self):
        p=self.run_case().payload
        self.assertEqual(p['state'],'current_synthetic_matched_case_at_declared_time')
        self.assertEqual((p['reference_source_binding_count'],p['candidate_source_binding_count']),(23,22))
        self.assertEqual(p['current_matched_case']['comparison']['replayed_net_cash_profit'],{'numerator':'0','denominator':'1'})
        self.assertEqual(p['decision'],'PENDING')
    def test_only_reference_domain_expired_blocks_preserving_history(self):
        saved=self.check.payload_json
        next(e for e in self.ref['evidence']if e['requirement_id']=='/recovery/piecewise_spec')['valid_until']=AS_OF
        p=self.run_case().payload;self.assertIsNone(p['current_matched_case']);self.assertIn('reference_curve_not_current',p['blockers'])
        self.assertEqual(self.check.payload_json,saved)
    def test_only_candidate_bounds_expired_blocks(self):
        next(e for e in self.candidate['evidence']if e['requirement_id']=='/exit/cost_bounds')['valid_until']=AS_OF
        p=self.run_case().payload;self.assertIn('candidate_story_not_current',p['blockers'])
        self.assertTrue(p['candidate_evidence_blockers']);self.assertFalse(p['reference_evidence_blockers'])
    def test_missing_domain_cannot_be_covered_by_candidate_registry(self):
        self.ref['requirements']=[r for r in self.ref['requirements']if r['requirement_id']!='/recovery/piecewise_spec']
        self.ref['evidence']=[r for r in self.ref['evidence']if r['requirement_id']!='/recovery/piecewise_spec']
        self.assertIsNone(self.run_case().payload['current_matched_case'])
    def test_candidate_estimate_or_pending_review_blocks(self):
        original=copy.deepcopy(self.candidate)
        for key,value in [('value_status','estimate'),('review_status','pending'),('superseded_by_sha256','f'*64)]:
            self.candidate=copy.deepcopy(original);self.candidate['evidence'][0][key]=value
            self.assertIsNone(self.run_case().payload['current_matched_case'])
    def test_wrong_time_registry_and_rehashed_comparison_rejected(self):
        values=list(self.values());values[-1]='2027-08-01T00:00:00Z'
        with self.assertRaises(ValidationError):assemble_current_recovery_case(*values)
        values=list(self.values());p=self.check.payload;p['state']='forged';text=canonical(p)
        values[1]=replace(self.check,payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):assemble_current_recovery_case(*values)
    def test_full_report_replay_and_updated_hash_forgery(self):
        run=self.run_case();self.assertEqual(verify_current_recovery_case(*self.values(),run),run)
        p=run.payload;p['current_matched_case']['comparison']['replayed_net_cash_profit']={'numerator':'99','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):verify_current_recovery_case(*self.values(),replace(run,payload_json=text,sha256=digest(text)))
    def test_changed_candidate_fee_remains_blocked_despite_current_sources(self):
        args,base,sr,r,_,_=self.check_args;candidate,run=reprice(args,400,F(1,10));self.check_args=(args,base,sr,r,candidate,run)
        self.check=check_recovery_case(*self.check_args)
        self.candidate=registry(candidate[4].payload['context'],required_bounded_exit_sources(candidate))
        p=self.run_case().payload;self.assertIn('full_case_comparison_not_matched',p['blockers'])
        self.assertTrue(p['comparison_blockers'])
    def test_registry_context_mismatch_not_overridden(self):
        self.candidate['context']['run_id']+='-other'
        self.assertIsNone(self.run_case().payload['current_matched_case'])
    def test_no_authentication_live_clock_or_financial_release(self):
        p=self.run_case().payload
        for key in ['professional_review_authenticated','contract_or_tax_rule_verified','financial_publication_authorized','live_expiry_monitor_enabled','funding_availability_verified','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return'])


if __name__=='__main__':unittest.main()
