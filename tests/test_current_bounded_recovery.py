import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.current_bounded_recovery import required_bounded_recovery_sources,assemble_current_bounded_recovery,verify_current_bounded_recovery
from piecewise_recovery_test_support import build_case,recovery_spec,raw
from evidence_currency_test_support import registry,AS_OF

def f(q):return F(int(q['numerator']),int(q['denominator']))


class CurrentBoundedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.args,self.base=build_case();self.spec=recovery_spec(self.base);self.rebind()
    def rebind(self):
        self.sr=raw(self.spec);self.recovery=analyze_bounded_sale_recovery(self.args,self.base,self.sr)
        self.p=registry(self.args[4].payload['context'],required_bounded_recovery_sources(self.args,self.sr))
    def values(self,at=AS_OF):
        rr=raw(self.p);run=evaluate_evidence_currency(rr,at)
        return self.args,self.base,self.sr,self.recovery,rr,run,at
    def run_case(self,at=AS_OF):return assemble_current_bounded_recovery(*self.values(at))

    def test_current_domain_and_full_23_binding_inventory(self):
        p=self.run_case().payload;a=p['current_recovery_analysis']
        self.assertEqual(p['state'],'current_synthetic_piecewise_recovery_at_declared_time')
        self.assertEqual(len(p['required_source_bindings']),23)
        self.assertEqual(f(a['recovering_price_intervals'][0]['lower']),F('116.0803'))
        self.assertEqual(p['decision'],'PENDING')

    def test_22_old_bindings_do_not_cover_new_domain_spec(self):
        self.p['requirements']=[r for r in self.p['requirements']if r['requirement_id']!='/recovery/piecewise_spec']
        self.p['evidence']=[r for r in self.p['evidence']if r['requirement_id']!='/recovery/piecewise_spec']
        p=self.run_case().payload;self.assertIsNone(p['current_recovery_analysis'])
        self.assertIn('complete_piecewise_recovery_source_inventory_mismatch',p['blockers'])

    def test_only_domain_expiry_withdraws_current_analysis_not_history(self):
        saved=self.recovery.payload_json
        next(r for r in self.p['evidence']if r['requirement_id']=='/recovery/piecewise_spec')['valid_until']=AS_OF
        p=self.run_case().payload;self.assertIsNone(p['current_recovery_analysis'])
        self.assertEqual(self.recovery.payload_json,saved);self.assertTrue(p['historical_analysis_preserved'])

    def test_changed_domain_or_budget_needs_new_evidence_binding(self):
        old=copy.deepcopy(self.p)
        self.spec['segment_budget']=128;self.sr=raw(self.spec);self.recovery=analyze_bounded_sale_recovery(self.args,self.base,self.sr)
        self.p=old
        self.assertIn('complete_piecewise_recovery_source_inventory_mismatch',self.run_case().payload['blockers'])

    def test_pending_estimated_or_superseded_domain_blocks(self):
        original=copy.deepcopy(self.p)
        for key,value in [('review_status','pending'),('value_status','estimate'),('superseded_by_sha256','a'*64)]:
            self.p=copy.deepcopy(original)
            next(r for r in self.p['evidence']if r['requirement_id']=='/recovery/piecewise_spec')[key]=value
            self.assertIsNone(self.run_case().payload['current_recovery_analysis'])

    def test_bank_failure_and_budget_failure_remain_visible(self):
        self.args,self.base=build_case(compatible=False);self.spec=recovery_spec(self.base);self.rebind()
        p=self.run_case().payload;self.assertIsNone(p['current_recovery_analysis'])
        self.assertIn('refinance_capacity_or_selection_blocked',p['underlying_calculation_blockers'])
        self.args,self.base=build_case();self.spec=recovery_spec(self.base,budget=2);self.rebind()
        p=self.run_case().payload;self.assertIn('piecewise_segment_budget_exceeded',p['recovery_blockers'])

    def test_empty_solution_still_exposed_as_conditional_analysis(self):
        self.args,self.base=build_case(extra_uses=F('383.9197'))
        self.spec=recovery_spec(self.base,upper=450);self.rebind()
        p=self.run_case().payload
        self.assertIsNotNone(p['current_recovery_analysis'])
        self.assertEqual(p['current_recovery_analysis']['recovering_price_intervals'],[])
        self.assertEqual(p['decision'],'PENDING')

    def test_same_time_full_report_replay_and_updated_hash_forgeries(self):
        report=self.run_case();self.assertEqual(verify_current_bounded_recovery(*self.values(),report),report)
        p=report.payload;p['current_recovery_analysis']['recovering_price_intervals']=[];text=canonical(p)
        with self.assertRaises(ValidationError):verify_current_bounded_recovery(*self.values(),replace(report,payload_json=text,sha256=digest(text)))
        values=list(self.values());p=self.recovery.payload;p['state']='forged';text=canonical(p)
        values[3]=replace(self.recovery,payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):assemble_current_bounded_recovery(*values)

    def test_context_source_hash_and_row_order_guards(self):
        before=self.run_case().payload['current_recovery_analysis'];self.p['requirements'].reverse();self.p['evidence'].reverse()
        self.assertEqual(self.run_case().payload['current_recovery_analysis'],before)
        self.p['context']['run_id']+='-other'
        self.assertIn('registry_and_recovery_context_mismatch',self.run_case().payload['blockers'])

    def test_old_time_registry_cannot_be_reused(self):
        values=list(self.values());values[-1]='2027-08-01T00:00:00Z'
        with self.assertRaises(ValidationError):assemble_current_bounded_recovery(*values)

    def test_no_financial_domain_approval_or_personal_return(self):
        p=self.run_case().payload
        for key in ['professional_review_authenticated','cost_profile_financially_valid_over_domain','funding_availability_verified_over_domain','financial_publication_authorized','live_expiry_monitor_enabled','investment_criterion_adopted','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return'])


if __name__=='__main__':unittest.main()
