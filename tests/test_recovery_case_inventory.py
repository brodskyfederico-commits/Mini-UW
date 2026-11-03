import copy,json,hashlib
from dataclasses import replace
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.recovery_case_check import check_recovery_case
from miniuw_foundation.current_bounded_recovery import required_bounded_recovery_sources
from miniuw_foundation.current_bounded_exit_output import required_bounded_exit_sources
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_recovery_case import assemble_current_recovery_case
from miniuw_foundation.recovery_case_inventory import RecoveryReviewCase,assemble_recovery_case_inventory,verify_recovery_case_inventory,parse_case_inventory
from piecewise_recovery_test_support import build_case,recovery_spec,raw
from recovery_case_test_support import reprice
from evidence_currency_test_support import registry,AS_OF


class RecoveryCaseInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref,cls.base=build_case();cls.sr=raw(recovery_spec(cls.base));cls.recovery=analyze_bounded_sale_recovery(cls.ref,cls.base,cls.sr)
    def proof(self,name,price=200,expired=False,at=AS_OF,ref_revision=False):
        candidate,run=reprice(self.ref,price);args=(self.ref,self.base,self.sr,self.recovery,candidate,run);check=check_recovery_case(*args)
        rr=registry(self.ref[4].payload['context'],required_bounded_recovery_sources(self.ref,self.sr))
        if ref_revision:rr['inventory_basis_ref']+='-new-revision'
        cr=registry(candidate[4].payload['context'],required_bounded_exit_sources(candidate))
        if expired:cr['evidence'][0]['valid_until']=at
        rr=raw(rr);cr=raw(cr)
        inputs=(args,check,rr,evaluate_evidence_currency(rr,at),cr,evaluate_evidence_currency(cr,at),at)
        return RecoveryReviewCase(name,inputs,assemble_current_recovery_case(*inputs))
    def inventory(self,cases):
        return dict(schema='miniuw.synthetic-recovery-case-inventory.v1',as_of_UTC=AS_OF,
            reference_bounded_run_sha256=self.base.sha256,recovery_run_sha256=self.recovery.sha256,
            reference_registry_source_sha256=hashlib.sha256(cases[0].arguments[2]).hexdigest(),
            inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-explicit-price-case-inventory',
            cases=[dict(case_id=c.case_id,current_case_run_sha256=c.run.sha256)for c in cases])
    def test_all_cases_current_including_negative_profit_without_pass(self):
        cases=(self.proof('lower',100),self.proof('higher',200));p=assemble_recovery_case_inventory(cases,raw(self.inventory(cases))).payload
        self.assertTrue(p['all_declared_cases_current_and_matched']);self.assertEqual(len(p['case_rows']),2)
        self.assertIsNotNone(p['case_rows'][0]['current_matched_case']);self.assertEqual(p['decision'],'PENDING')
    def test_expired_case_preserved_without_zero_or_hiding_valid_sibling(self):
        cases=(self.proof('current'),self.proof('expired',expired=True));p=assemble_recovery_case_inventory(cases,raw(self.inventory(cases))).payload
        self.assertEqual(p['state'],'PENDING');self.assertIsNotNone(p['case_rows'][0]['current_matched_case'])
        self.assertIsNone(p['case_rows'][1]['current_matched_case']);self.assertTrue(p['case_rows'][1]['candidate_evidence_blockers'])
    def test_incomplete_missing_order_and_hash_inventory_block_all_views(self):
        cases=(self.proof('first'),self.proof('second',500));original=self.inventory(cases)
        for key,value in [('inventory_declared_complete',False),('inventory_basis_ref',None),('cases',original['cases'][::-1]),('cases',original['cases'][:-1]),('reference_bounded_run_sha256','0'*64)]:
            spec=copy.deepcopy(original);spec[key]=value;p=assemble_recovery_case_inventory(cases,raw(spec)).payload
            self.assertTrue(p['blockers']);self.assertTrue(all(r['current_matched_case']is None for r in p['case_rows']))
    def test_different_time_cannot_join_same_review(self):
        cases=(self.proof('first'),self.proof('later',at='2027-07-02T12:00:00Z'))
        p=assemble_recovery_case_inventory(cases,raw(self.inventory(cases))).payload
        self.assertIn('later:evaluation_time_mismatch',p['blockers'])
    def test_reference_registry_revisions_not_silently_mixed(self):
        cases=(self.proof('first'),self.proof('revised',ref_revision=True))
        p=assemble_recovery_case_inventory(cases,raw(self.inventory(cases))).payload
        self.assertIn('revised:shared_reference_evidence_revision_mismatch',p['blockers'])
    def test_case_and_report_replay_reject_updated_hash_forgery(self):
        case=self.proof('first');cases=(case,);spec=raw(self.inventory(cases));run=assemble_recovery_case_inventory(cases,spec)
        self.assertEqual(verify_recovery_case_inventory(cases,spec,run),run)
        p=run.payload;p['state']='approved';text=canonical(p)
        with self.assertRaises(ValidationError):verify_recovery_case_inventory(cases,spec,replace(run,payload_json=text,sha256=digest(text)))
        p=case.run.payload;p['state']='forged';text=canonical(p);fake=replace(case,run=replace(case.run,payload_json=text,sha256=digest(text)))
        with self.assertRaises(ValidationError):assemble_recovery_case_inventory((fake,),raw(self.inventory((fake,))))
    def test_duplicate_ids_empty_sources_and_strict_syntax(self):
        case=self.proof('first');spec=raw(self.inventory((case,)))
        with self.assertRaises(ValidationError):assemble_recovery_case_inventory((case,case),spec)
        with self.assertRaises(ValidationError):assemble_recovery_case_inventory((),spec)
        for source in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_case_inventory(source)
    def test_no_best_average_policy_or_personal_return_claim(self):
        cases=(self.proof('first'),);p=assemble_recovery_case_inventory(cases,raw(self.inventory(cases))).payload
        for key in ['best_case_selected','average_return_generated','scenarios_automatically_generated','downside_policy_adopted','professional_review_authenticated','financial_publication_authorized','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return'])


if __name__=='__main__':unittest.main()
