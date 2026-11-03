import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_bounded_exit_output import required_bounded_exit_sources,assemble_current_bounded_exit_output,verify_current_bounded_exit_output
from bounded_cost_test_support import case,raw
from evidence_currency_test_support import registry,AS_OF

def f(q):return F(int(q['numerator']),int(q['denominator']))


class CurrentBoundedExitOutputTests(unittest.TestCase):
    def setUp(self):
        self.args=case();self.base=assemble_bounded_exit_sale(*self.args)
        self.p=registry(self.args[4].payload['context'],required_bounded_exit_sources(self.args))
    def values(self,at=AS_OF):
        source=raw(self.p);run=evaluate_evidence_currency(source,at)
        return self.args,self.base,source,run,at
    def run_case(self,at=AS_OF):return assemble_current_bounded_exit_output(*self.values(at))

    def test_full_current_story_and_limit_details(self):
        p=self.run_case().payload;s=p['current_project_return_summary']
        self.assertEqual(p['state'],'current_synthetic_bounded_output_at_declared_time')
        self.assertEqual(len(p['required_source_bindings']),22)
        self.assertEqual(f(s['net_cash_profit']),F('283.9197'))
        self.assertEqual(f(s['total_bounded_closing_cost']),35)
        self.assertEqual(s['bounded_sale_cost_rows'][1]['binding_constraints'],['minimum'])
        self.assertEqual(len(s['dated_events']),5);self.assertIsNone(s['personal_investor_return'])

    def test_expiry_omits_current_story_but_preserves_historical_math(self):
        saved=self.base.payload_json
        self.assertIsNone(self.run_case('2027-08-01T00:00:00Z').payload['current_project_return_summary'])
        self.assertEqual(self.base.payload_json,saved)

    def test_missing_only_new_bounds_binding_blocks_even_if_others_current(self):
        self.p['requirements']=[r for r in self.p['requirements']if r['requirement_id']!='/exit/cost_bounds']
        self.p['evidence']=[r for r in self.p['evidence']if r['requirement_id']!='/exit/cost_bounds']
        p=self.run_case().payload;self.assertIn('complete_bounded_exit_source_inventory_mismatch',p['blockers'])
        self.assertIsNone(p['current_project_return_summary'])

    def test_coherent_registry_wrong_bound_hash_or_locator_blocks(self):
        original=copy.deepcopy(self.p)
        for key,value in [('source_sha256','0'*64),('source_locator','/wrong-bounds')]:
            self.p=copy.deepcopy(original)
            for family in ['requirements','evidence']:
                next(r for r in self.p[family]if r['requirement_id']=='/exit/cost_bounds')[key]=value
            self.assertIsNone(self.run_case().payload['current_project_return_summary'])

    def test_new_bounds_record_pending_estimate_or_superseded_blocks(self):
        original=copy.deepcopy(self.p)
        for key,value in [('review_status','pending'),('value_status','estimate'),('superseded_by_sha256','a'*64)]:
            self.p=copy.deepcopy(original)
            next(r for r in self.p['evidence']if r['requirement_id']=='/exit/cost_bounds')[key]=value
            self.assertIsNone(self.run_case().payload['current_project_return_summary'])

    def test_known_bank_failure_kept_with_current_evidence(self):
        self.args=case(False);self.base=assemble_bounded_exit_sale(*self.args)
        self.p=registry(self.args[4].payload['context'],required_bounded_exit_sources(self.args))
        p=self.run_case().payload;self.assertIsNone(p['current_project_return_summary'])
        self.assertIn('refinance_capacity_or_selection_blocked',p['calculation_blockers'])

    def test_unresolved_tax_details_visible_with_current_evidence(self):
        from miniuw_foundation.sale_costs import produce_sale_costs
        from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
        from bounded_cost_test_support import bounds_spec
        from sale_cost_test_support import sha
        args=list(self.args);source=json.loads(args[5]);tax=copy.deepcopy(source['costs'][0])
        tax.update(cost_id='tax',classification='tax',applicability='unresolved',value=None)
        source['costs'].append(tax);args[5]=raw(source);args[6]=produce_sale_costs(args[5])
        args[7]=raw(bounds_spec(args[5],args[6]));args[8]=produce_bounded_sale_costs(args[5],args[6],args[7])
        spec=json.loads(args[9]);spec.update(cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256,
            bounds_source_sha256=sha(args[7]),bounded_run_sha256=args[8].sha256);args[9]=raw(spec)
        self.args=tuple(args);self.base=assemble_bounded_exit_sale(*self.args)
        self.p=registry(self.args[4].payload['context'],required_bounded_exit_sources(self.args))
        p=self.run_case().payload
        self.assertIsNone(p['current_project_return_summary'])
        self.assertIn('tax:cost_applicability_unresolved',p['original_cost_blockers'])

    def test_registry_wrong_time_and_rehashed_forgeries_rejected(self):
        args,base,source,run,at=self.values()
        with self.assertRaises(ValidationError):assemble_current_bounded_exit_output(args,base,source,run,'2027-08-01T00:00:00Z')
        p=base.payload;p['state']='forged';text=canonical(p)
        with self.assertRaises(ValidationError):assemble_current_bounded_exit_output(args,replace(base,payload_json=text,sha256=digest(text)),source,run,at)
        p=run.payload;p['state']='forged';text=canonical(p)
        with self.assertRaises(ValidationError):assemble_current_bounded_exit_output(args,base,source,replace(run,payload_json=text,sha256=digest(text)),at)

    def test_full_report_replay_and_forgery(self):
        report=self.run_case();self.assertEqual(verify_current_bounded_exit_output(*self.values(),report),report)
        p=report.payload;p['current_project_return_summary']['net_cash_profit']={'numerator':'999','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):verify_current_bounded_exit_output(*self.values(),replace(report,payload_json=text,sha256=digest(text)))

    def test_context_and_order_guards(self):
        before=self.run_case().payload['current_project_return_summary']
        self.p['requirements'].reverse();self.p['evidence'].reverse()
        self.assertEqual(self.run_case().payload['current_project_return_summary'],before)
        self.p['context']['run_id']+='-other'
        self.assertIn('registry_and_bounded_exit_context_mismatch',self.run_case().payload['blockers'])

    def test_no_global_affine_or_real_publication_claim(self):
        p=self.run_case().payload
        for key in ['professional_review_authenticated','contract_or_tax_rule_verified','global_affine_recovery_analysis_produced','live_expiry_monitor_enabled','financial_publication_authorized','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertEqual(p['decision'],'PENDING')


if __name__=='__main__':unittest.main()
