import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.closing_returns import ClosingReturnBinding,assemble_closing_returns
from miniuw_foundation.debt_closing import reconcile_debt_closing
from miniuw_foundation.debt_closing_returns import DebtClosingReturnBinding,assemble_debt_checked_returns,binding_from_record
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from debt_closing_test_support import fixture,build,raw,sha,R

def f(q):return F(int(q['numerator']),int(q['denominator']))
def num(n):return q(F(n))


class DebtCheckedReturnsTests(unittest.TestCase):
    def setUp(self):self.loan,self.closing,self.spec=fixture();self.investor=json.loads((R/'templates/synthetic-closing-investor-slots.json').read_bytes())
    def case(self):
        loans,cr,c,s=build(self.loan,self.closing,self.spec);r=reconcile_debt_closing(loans,cr,c,s);i=raw(self.investor)
        inner=ClosingReturnBinding(profile_id='SYNTHETIC-CLOSING-EMPTY-EQUITY-SLOTS-v1',closing_source_sha256=sha(cr),closing_run_sha256=c.sha256,investor_source_sha256=sha(i),distribution_event_id='refi'if c.payload['kind']=='refinance'else'sale',contribution_event_id=None)
        b=DebtClosingReturnBinding(profile_id='SYNTHETIC-DEBT-CHECKED-CLOSING-RETURN-v1',reconciliation_spec_sha256=sha(s),reconciliation_run_sha256=r.sha256,closing_return_binding=inner)
        return loans,cr,c,s,r,i,b
    def run_case(self):return assemble_debt_checked_returns(*self.case())
    def test_matched_debt_unlocks_only_the_explicit_synthetic_closing_path(self):
        loans,cr,c,s,r,i,b=self.case();result=assemble_debt_checked_returns(loans,cr,c,s,r,i,b)
        self.assertEqual(result.payload['state'],'compiled_synthetic');self.assertEqual(f(next(e for e in json.loads(result.compiled_raw)['events']if e['event_id']=='refi')['amount']),550)
        legacy=assemble_closing_returns(cr,c,i,b.closing_return_binding);self.assertEqual(result.closing_return_run,legacy);self.assertEqual(result.compiled_raw,legacy.compiled_raw)
    def test_arithmetically_balanced_closing_still_blocked_if_debt_claim_differs(self):
        for suffix in ['due','paid']:self.closing['old_debts'][0]['principal_'+suffix]['value']=num(1200)
        loans,cr,c,s,r,i,b=self.case();self.assertEqual(c.payload['state'],'computed_synthetic_closing')
        self.assertEqual(assemble_closing_returns(cr,c,i,b.closing_return_binding).payload['state'],'compiled_synthetic')
        result=assemble_debt_checked_returns(loans,cr,c,s,r,i,b);self.assertIsNone(result.compiled_raw);self.assertIsNone(result.closing_return_run);self.assertIn('dated_debt_closing_reconciliation_blocked',result.payload['blockers'])
    def test_missing_paid_history_assumption_does_not_become_implied_approval(self):
        self.spec['loans'][0]['prior_regular_service_assumed_paid']=None;r=self.run_case()
        self.assertEqual(r.payload['state'],'blocked');self.assertIsNone(r.compiled_raw);self.assertTrue(r.payload['debt_reconciliation_blockers'])
    def test_two_dated_debt_checked_closings_recalculate_investor_return(self):
        first=self.run_case();self.loan,self.closing,self.spec=fixture('sale');self.investor=json.loads(first.compiled_raw)
        second=self.run_case();p=second.investor_run.payload;self.assertEqual(f(p['gross_distributions']),1650);self.assertEqual(f(p['net_cash_profit']),650)
        self.assertEqual(f(p['equity_multiple']),F(33,20));self.assertEqual(f(p['normalized_story']['total_distributions']),F(33,2))
        self.assertEqual(f(p['normalized_story']['net_cash_profit']),F(13,2));self.assertEqual(p['decision'],'PENDING')
    def test_other_missing_return_data_remains_pending_after_debt_matching(self):
        r=self.run_case();self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(r.investor_run.payload['cash_metrics_state'],'blocked');self.assertEqual(r.investor_run.payload['decision'],'PENDING')
    def test_stale_reconciliation_source_or_run_hash_blocks(self):
        loans,cr,c,s,r,i,b=self.case()
        for key in ['reconciliation_spec_sha256','reconciliation_run_sha256']:
            result=assemble_debt_checked_returns(loans,cr,c,s,r,i,replace(b,**{key:'0'*64}));self.assertIsNone(result.compiled_raw);self.assertIn(key+'_mismatch',result.payload['blockers'])
    def test_nested_closing_binding_guards_are_retained(self):
        loans,cr,c,s,r,i,b=self.case();bad=replace(b,closing_return_binding=replace(b.closing_return_binding,investor_source_sha256='0'*64))
        result=assemble_debt_checked_returns(loans,cr,c,s,r,i,bad);self.assertIsNone(result.compiled_raw);self.assertIn('investor_source_sha256_mismatch',result.payload['blockers'])
        self.investor['events'][1]['amount']=num(500);self.assertIsNone(self.run_case().compiled_raw)
    def test_rehashed_reconciliation_cannot_override_a_mismatched_loan(self):
        for suffix in ['due','paid']:self.closing['old_debts'][0]['principal_'+suffix]['value']=num(1200)
        loans,cr,c,s,r,i,b=self.case();p=r.payload;p['state']='matched_synthetic_debt_assumptions';p['blockers']=[];enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):assemble_debt_checked_returns(loans,cr,c,s,fake,i,replace(b,reconciliation_run_sha256=fake.sha256))
    def test_complete_source_chain_replayed_even_if_nested_target_is_invalid(self):
        loans,cr,c,s,r,i,b=self.case();p=loans[0].run.payload;p['schedule'][2]['opening_balance']=num(999);enc=canonical(p);forged=replace(loans[0],run=replace(loans[0].run,payload_json=enc,sha256=digest(enc)))
        bad=replace(b,closing_return_binding=replace(b.closing_return_binding,distribution_event_id='missing'))
        with self.assertRaises(ValidationError):assemble_debt_checked_returns((forged,),cr,c,s,r,i,bad)
    def test_strict_typed_binding_and_live_investor_source_rejected_when_debt_blocked(self):
        loans,cr,c,s,r,i,b=self.case()
        with self.assertRaises(ValidationError):replace(b,profile_id='approved_payoff')
        with self.assertRaises(ValidationError):replace(b,closing_return_binding={})
        self.spec['loans'][0]['prior_regular_service_assumed_paid']=None;self.investor['context']['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case()
    def test_immutable_sources_payload_and_binding_roundtrip(self):
        loans,cr,c,s,r,i,b=self.case();result=assemble_debt_checked_returns(loans,cr,c,s,r,i,b);p=result.payload;p['closing_return_run']=None
        self.assertIsNotNone(result.compiled_raw);self.assertEqual(binding_from_record(result.payload['binding']),b);self.assertEqual(result.sha256,digest(result.payload_json));self.assertEqual(i,raw(self.investor))
    def test_reopened_archive_replays_comparison_then_compilation(self):
        loans,cr,c,s,r,i,b=self.case();result=assemble_debt_checked_returns(loans,cr,c,s,r,i,b)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'returns.sqlite3'
            with EvidenceArchive(path)as a:
                comparison=a.save_debt_closing(loans,cr,c,s,r);compiled=a.save_debt_checked_returns(loans,cr,c,s,r,i,b,result)
                self.assertEqual(compiled,a.save_debt_checked_returns(loans,cr,c,s,r,i,b,result))
            with EvidenceArchive(path)as a:
                recovered=a.load_debt_checked_returns(compiled);self.assertEqual(recovered.run,result);self.assertEqual(recovered.run.investor_run,result.investor_run)
                self.assertEqual(a.load_debt_closing(comparison).run.sha256,recovered.payload['reconciliation_run']['sha256'])
                self.assertEqual(a.get_investor_returns_source(recovered.payload['investor_source_sha256']),i);self.assertEqual(a.get_investor_returns_source(recovered.payload['compiled_source_sha256']),result.compiled_raw)
    def test_archive_rollback_forgery_version_and_missing_loan(self):
        loans,cr,c,s,r,i,b=self.case();result=assemble_debt_checked_returns(loans,cr,c,s,r,i,b);p=result.payload;p['blockers']=['invented'];enc=canonical(p);fake=replace(result,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_debt_checked_returns(loans,cr,c,s,r,i,b,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_debt_checked_returns(loans,cr,c,s,r,i,b,result)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_debt_checked_returns(loans,cr,c,s,r,i,b,result);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_debt_checked_returns(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_debt_checked_returns(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(loans[0].loan_raw)))
            with self.assertRaises(MissingEvidence):a.load_debt_checked_returns(key)
    def test_blocked_comparison_bundle_recovers_without_any_compilation(self):
        self.spec['loans'][0]['prior_regular_service_assumed_paid']=None;loans,cr,c,s,r,i,b=self.case();result=assemble_debt_checked_returns(loans,cr,c,s,r,i,b)
        with EvidenceArchive(':memory:')as a:
            key=a.save_debt_checked_returns(loans,cr,c,s,r,i,b,result);recovered=a.load_debt_checked_returns(key);self.assertEqual(recovered.run,result);self.assertIsNone(recovered.run.compiled_raw)
    def test_no_real_bank_evidence_or_complete_model_claimed(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['original_source_overwritten','scheduled_payment_history_actually_verified','bank_payoff_statement_verified','whole_project_cash_reconciled','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])
