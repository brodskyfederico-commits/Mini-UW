import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_exit_output import assemble_current_exit_output,verify_current_exit_output,required_exit_sources
from evidence_currency_test_support import costed_case,exit_registry,raw,AS_OF

def f(q):return F(int(q['numerator']),int(q['denominator']))


class CurrentExitOutputTests(unittest.TestCase):
    def setUp(self):self.args,self.base=costed_case();self.registry=exit_registry(self.args)
    def values(self,at=AS_OF):
        source=raw(self.registry);run=evaluate_evidence_currency(source,at)
        return self.args,self.base,source,run,at
    def run_case(self,at=AS_OF):return assemble_current_exit_output(*self.values(at))

    def test_all_bindings_current_exposes_project_story_with_original_math(self):
        p=self.run_case().payload;s=p['current_project_return_summary']
        self.assertEqual(p['state'],'current_synthetic_output_at_declared_time')
        self.assertEqual(f(s['net_cash_profit']),F('288.9197'))
        self.assertEqual(s['equity_level'],'aggregate_project_equity');self.assertIsNone(s['personal_investor_return'])
        self.assertEqual(len(s['dated_events']),5);self.assertIsNotNone(s['risk_observations'])
        self.assertTrue(s['upstream_story_blockers']);self.assertEqual(s['decision'],'PENDING')

    def test_expiry_withdraws_current_summary_preserves_history(self):
        saved=self.base.payload_json;current=self.run_case();expired=self.run_case('2027-08-01T00:00:00Z')
        self.assertIsNotNone(current.payload['current_project_return_summary'])
        self.assertIsNone(expired.payload['current_project_return_summary'])
        self.assertEqual(expired.payload['state'],'PENDING');self.assertEqual(self.base.payload_json,saved)
        self.assertEqual(current.payload['base_costed_run_sha256'],expired.payload['base_costed_run_sha256'])

    def test_every_leaf_binding_and_alias_required(self):
        expected=required_exit_sources(self.args)
        self.assertEqual(len(expected),21)
        hashes=[r['source_sha256']for r in expected];self.assertLess(len(set(hashes)),len(hashes))
        self.registry['requirements']=self.registry['requirements'][:-1]
        self.registry['evidence']=self.registry['evidence'][:-1]
        p=self.run_case().payload;self.assertIn('complete_exit_source_binding_inventory_mismatch',p['blockers'])
        self.assertIsNone(p['current_project_return_summary'])

    def test_wrong_hash_or_locator_in_coherent_registry_still_blocked(self):
        original=copy.deepcopy(self.registry)
        for key,value in [('source_sha256','0'*64),('source_locator','/different')]:
            self.registry=copy.deepcopy(original)
            self.registry['requirements'][0][key]=value;self.registry['evidence'][0][key]=value
            p=self.run_case().payload
            self.assertIn('complete_exit_source_binding_inventory_mismatch',p['blockers'])

    def test_extra_binding_and_context_do_not_unlock(self):
        extra=copy.deepcopy(self.registry['requirements'][0]);extra['requirement_id']='extra'
        proof=copy.deepcopy(self.registry['evidence'][0]);proof.update(requirement_id='extra',evidence_id='extra')
        self.registry['requirements'].append(extra);self.registry['evidence'].append(proof)
        self.assertIsNone(self.run_case().payload['current_project_return_summary'])
        self.registry=exit_registry(self.args);self.registry['context']['run_id']+='-other'
        self.assertIn('evidence_and_exit_context_mismatch',self.run_case().payload['blockers'])

    def test_row_order_has_no_semantic_effect(self):
        before=self.run_case().payload
        self.registry['requirements'].reverse();self.registry['evidence'].reverse()
        after=self.run_case().payload
        self.assertEqual(before['current_project_return_summary'],after['current_project_return_summary'])
        self.assertEqual(before['state'],after['state'])

    def test_estimate_pending_review_or_replaced_source_blocks(self):
        original=copy.deepcopy(self.registry)
        for key,value in [('value_status','estimate'),('review_status','pending'),('superseded_by_sha256','f'*64)]:
            self.registry=copy.deepcopy(original);self.registry['evidence'][0][key]=value
            p=self.run_case().payload;self.assertIsNone(p['current_project_return_summary']);self.assertTrue(p['evidence_blockers'])

    def test_renewal_changes_registry_and_result_without_altering_math(self):
        at='2027-08-01T00:00:00Z';before=self.run_case(at)
        for e in self.registry['evidence']:
            e['evidence_id']+='-renewed';e['valid_until']='2027-09-01T00:00:00Z';e['basis_ref']+='-explicit-revision'
        after=self.run_case(at)
        self.assertIsNone(before.payload['current_project_return_summary']);self.assertIsNotNone(after.payload['current_project_return_summary'])
        self.assertNotEqual(before.payload['registry_source_sha256'],after.payload['registry_source_sha256'])
        self.assertEqual(before.payload['base_costed_run_sha256'],after.payload['base_costed_run_sha256'])

    def test_current_evidence_cannot_hide_bank_blocker(self):
        self.args,self.base=costed_case(False);self.registry=exit_registry(self.args)
        p=self.run_case().payload
        self.assertIsNone(p['current_project_return_summary']);self.assertTrue(p['calculation_blockers'])
        self.assertIn('refinance_capacity_or_selection_blocked',p['calculation_blockers'])

    def test_wrong_time_replayed_result_is_rejected(self):
        args,base,source,run,at=self.values()
        with self.assertRaises(ValidationError):assemble_current_exit_output(args,base,source,run,'2027-08-01T00:00:00Z')

    def test_rehashed_registry_and_base_result_forgeries_rejected(self):
        args,base,source,run,at=self.values()
        for family in ['registry','base']:
            target=run if family=='registry'else base;p=target.payload;p['state']='forged';text=canonical(p)
            fake=replace(target,payload_json=text,sha256=digest(text))
            with self.assertRaises(ValidationError):assemble_current_exit_output(args,fake if family=='base'else base,source,fake if family=='registry'else run,at)

    def test_full_report_replay_rejects_hash_updated_forgery(self):
        report=self.run_case();self.assertEqual(verify_current_exit_output(*self.values(),report),report)
        p=report.payload;p['current_project_return_summary']['equity_multiple']={'numerator':'9','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):verify_current_exit_output(*self.values(),replace(report,payload_json=text,sha256=digest(text)))

    def test_no_live_clock_financial_publication_or_real_authority(self):
        p=self.run_case().payload
        for key in ['all_external_document_sources_authenticated','professional_review_authenticated','live_expiry_monitor_enabled','financial_publication_authorized','real_decisions_enabled','production_authorized']:
            self.assertIs(p[key],False)
        self.assertEqual(p['decision'],'PENDING')


if __name__=='__main__':unittest.main()
