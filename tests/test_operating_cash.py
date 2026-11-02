import copy,hashlib,json,tempfile,unittest
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash,parse_operating_cash,definition_sources
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def num(n):return q(F(n))
def f(q):return F(int(q['numerator']),int(q['denominator']))


class OperatingCashTests(unittest.TestCase):
    def setUp(self):
        self.noi_raw=(R/'templates/synthetic-operating-noi.json').read_bytes();self.noi=produce_operating_noi(self.noi_raw)
        self.spec=json.loads((R/'templates/synthetic-operating-cash.json').read_bytes())
    def run_case(self,p=None,nr=None,n=None):return reconcile_operating_cash(self.noi_raw if nr is None else nr,self.noi if n is None else n,raw(self.spec if p is None else p))
    def test_independent_accrual_cash_and_allocation_identities(self):
        p=self.run_case().payload
        self.assertEqual(f(p['computed_noi']),1000);self.assertEqual(f(p['expected_operating_receipts']),1450-10-(200-100)+(150-100))
        self.assertEqual(f(p['expected_operating_payments']),250+200-5-(130-100)+(60-40))
        self.assertEqual(f(p['net_operating_cash']),955);self.assertEqual(f(p['free_cash_before_proposed_distribution']),50+955+20-200-100-5-50-10-150)
        self.assertEqual(f(p['exportable_operating_distribution']),100);self.assertEqual(f(p['expected_closing_free_cash']),410);self.assertEqual(f(p['expected_closing_restricted_cash']),230)
        for key in ['receipts_claim_residual','payments_claim_residual','free_cash_claim_residual','restricted_cash_claim_residual','total_cash_conservation_residual']:self.assertEqual(f(p[key]),0)
    def test_unchanged_noi_can_have_different_cash_and_distribution_not_noi(self):
        before=self.run_case().payload;self.spec['working_balances']['receivables']['closing']['value']=num(250)
        self.spec['amounts']['operating_receipts_claim']['value']=num(1340);self.spec['amounts']['closing_free_cash_claim']['value']=num(360)
        after=self.run_case().payload;self.assertEqual(before['computed_noi'],after['computed_noi']);self.assertEqual(f(after['net_operating_cash']),905)
        self.assertEqual(f(after['exportable_operating_distribution']),100);self.assertNotEqual(after['computed_noi'],after['exportable_operating_distribution'])
    def test_signed_noncash_adjustments_are_not_clamped(self):
        self.spec['amounts']['noncash_revenue']['value']=num(-10);self.spec['amounts']['operating_receipts_claim']['value']=num(1410)
        self.spec['amounts']['closing_free_cash_claim']['value']=num(430);p=self.run_case().payload
        self.assertEqual(p['state'],'reconciled_synthetic_plan');self.assertEqual(f(p['expected_operating_receipts']),1410)
    def test_missing_adjustment_is_not_explicit_zero(self):
        self.spec['amounts']['noncash_revenue']['value']=None;p=self.run_case().payload
        self.assertEqual(p['state'],'blocked');self.assertIsNone(p['expected_operating_receipts']);self.assertIsNone(p['exportable_operating_distribution'])
    def test_wrong_cash_claim_blocks_even_with_other_balanced_numbers(self):
        self.spec['amounts']['operating_receipts_claim']['value']=num(1391);self.spec['amounts']['closing_free_cash_claim']['value']=num(411)
        p=self.run_case().payload;self.assertEqual(f(p['receipts_claim_residual']),1);self.assertIn('operating_receipts_claim_mismatch',p['blockers']);self.assertIsNone(p['exportable_operating_distribution'])
    def test_offsetting_stock_claim_errors_not_hidden_by_total_conservation(self):
        self.spec['amounts']['closing_free_cash_claim']['value']=num(420);self.spec['amounts']['closing_restricted_cash_claim']['value']=num(220)
        p=self.run_case().payload;self.assertEqual(f(p['total_cash_conservation_residual']),0)
        self.assertEqual(f(p['free_cash_claim_residual']),10);self.assertEqual(f(p['restricted_cash_claim_residual']),-10);self.assertEqual(p['state'],'blocked')
    def test_missing_allocation_preserves_reconciled_operating_cash_only(self):
        self.spec['amounts']['debt_principal_payment']['value']=None;p=self.run_case().payload
        self.assertEqual(p['accrual_cash_state'],'computed_synthetic');self.assertEqual(f(p['net_operating_cash']),955);self.assertIsNone(p['exportable_operating_distribution'])
    def test_distribution_larger_than_free_cash_is_blocked_without_cut_or_new_equity(self):
        self.spec['amounts']['planned_operating_distribution']['value']=num(600);p=self.run_case().payload
        self.assertEqual(f(p['expected_closing_free_cash']),-90);self.assertIsNone(p['exportable_operating_distribution'])
        self.assertIn('negative_free_cash_no_automatic_funding_or_distribution_cut',p['blockers']);self.assertEqual(self.spec['amounts']['equity_contribution']['value'],num(0))
    def test_restricted_cash_cannot_fund_distribution_without_explicit_release(self):
        # Total cash is positive, but the free cash account would be overdrawn.
        self.spec['amounts']['reserve_deposit']['value']=num(700);self.spec['amounts']['closing_restricted_cash_claim']['value']=num(780)
        p=self.run_case().payload;self.assertEqual(f(p['expected_closing_free_cash']),-140);self.assertEqual(p['state'],'blocked')
    def test_reserve_release_cannot_create_negative_restricted_cash(self):
        self.spec['amounts']['reserve_release']['value']=num(300);self.spec['amounts']['closing_free_cash_claim']['value']=num(690)
        p=self.run_case().payload;self.assertEqual(f(p['expected_closing_restricted_cash']),-50);self.assertIsNone(p['exportable_equity_contribution'])
    def test_explicit_equity_contribution_changes_free_cash_not_operating_cash(self):
        self.spec['amounts']['equity_contribution']['value']=num(200);self.spec['amounts']['closing_free_cash_claim']['value']=num(610)
        p=self.run_case().payload;self.assertEqual(f(p['net_operating_cash']),955);self.assertEqual(f(p['exportable_equity_contribution']),200);self.assertEqual(f(p['expected_closing_free_cash']),610)
    def test_all_missing_scope_and_basis_claims_block_without_financial_adoption(self):
        for field,value in [('scope_inventory_declared_complete',None),('scope_inventory_declared_complete',False),('period_basis_ref',None),('classification_basis_ref',None),('distribution_basis_ref',None)]:
            p=copy.deepcopy(self.spec);p[field]=value;out=self.run_case(p).payload;self.assertEqual(out['state'],'blocked');self.assertIsNone(out['exportable_operating_distribution'])
    def test_each_amount_metadata_guard(self):
        for field,value in [('currency','EUR'),('period_ref','OTHER'),('source_ref',None),('value',num(-1))]:
            p=copy.deepcopy(self.spec);p['amounts']['debt_fee_payment'][field]=value;self.assertEqual(self.run_case(p).payload['state'],'blocked')
    def test_working_balances_require_gross_nonnegative_and_exact_cutoff(self):
        for field,value in [('value',None),('value',num(-1)),('currency','EUR'),('period_ref',self.spec['period_ref']),('source_ref',None)]:
            p=copy.deepcopy(self.spec);p['working_balances']['receivables']['opening'][field]=value;self.assertIsNone(self.run_case(p).payload['expected_operating_receipts'])
    def test_source_run_context_period_and_currency_binding_guards(self):
        for field,value in [('noi_source_sha256','0'*64),('noi_run_sha256','0'*64),('period_ref','OTHER'),('currency','EUR')]:
            p=copy.deepcopy(self.spec);p[field]=value;self.assertEqual(self.run_case(p).payload['state'],'blocked')
        self.spec['context']['run_id']='SYNTHETIC-other-run';self.assertIn('producer_context_mismatch',self.run_case().payload['blockers'])
    def test_upstream_blocker_not_erased_by_available_income(self):
        nr=json.loads(self.noi_raw);nr['tax_coefficient']['value']=None;nr=raw(nr);n=produce_operating_noi(nr)
        self.spec.update(noi_source_sha256=hashlib.sha256(nr).hexdigest(),noi_run_sha256=n.sha256)
        p=self.run_case(nr=nr,n=n).payload;self.assertTrue(p['noi_blockers']);self.assertIsNone(p['expected_operating_receipts']);self.assertEqual(p['decision'],'PENDING')
    def test_rehashed_fake_noi_rejected_before_consumption(self):
        p=self.noi.payload;p['noi']=num(9999);enc=canonical(p);fake=replace(self.noi,payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):self.run_case(n=fake)
    def test_negative_computed_receipts_need_other_profile(self):
        self.spec['working_balances']['receivables']['closing']['value']=num(2000);p=self.run_case().payload
        self.assertLess(f(p['expected_operating_receipts']),0);self.assertIn('negative_computed_gross_cash_requires_separate_profile',p['blockers']);self.assertIsNone(p['exportable_operating_distribution'])
    def test_dates_are_half_open_and_schema_is_strict(self):
        for field,value in [('cash_date',self.spec['end_date']),('start_date',self.spec['end_date']),('cash_date','2027-02-30'),('profile','automatic_distribution')]:
            p=copy.deepcopy(self.spec);p[field]=value
            with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.spec);del p['working_balances']['payables']
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.spec);p['amounts']['debt_fee_payment']['value']=5.0
        with self.assertRaises(ValidationError):self.run_case(p)
    def test_payload_and_inputs_immutable_and_source_definitions_exact(self):
        before=raw(self.spec);r=self.run_case();p=r.payload;p['net_operating_cash']=num(9999)
        self.assertEqual(f(r.payload['net_operating_cash']),955);self.assertEqual(raw(self.spec),before);self.assertEqual(r.sha256,digest(r.payload_json))
        for ref in definition_sources():self.assertEqual(ref['sha256'],hashlib.sha256((R/ref['path']).read_bytes()).hexdigest())
    def test_reopened_archive_preserves_sources_runs_and_retry(self):
        s=raw(self.spec);r=self.run_case()
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'cash.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_operating_cash(self.noi_raw,self.noi,s,r);self.assertEqual(key,a.save_operating_cash(self.noi_raw,self.noi,s,r))
            with EvidenceArchive(path)as a:
                b=a.load_operating_cash(key);self.assertEqual(b.run,r);self.assertEqual(a.get_operating_cash_spec(b.payload['spec_source_sha256']),s);self.assertEqual(a.get_operating_noi_source(b.payload['noi_source_sha256']),self.noi_raw)
    def test_archive_rollback_forgery_compatibility_and_missing_source(self):
        s=raw(self.spec);r=self.run_case();p=r.payload;p['exportable_operating_distribution']=num(999);enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_operating_cash(self.noi_raw,self.noi,s,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_operating_cash(self.noi_raw,self.noi,s,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_operating_cash(self.noi_raw,self.noi,s,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_operating_cash(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_operating_cash(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',hashlib.sha256(s).hexdigest()))
            with self.assertRaises(MissingEvidence):a.load_operating_cash(key)
    def test_no_actual_payment_debt_schedule_distribution_or_financial_approval(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for k in ['multi_period_continuity_verified','intraperiod_liquidity_verified','cash_projection_actuality_verified','debt_cash_schedule_verified','distribution_authorized','tax_policy_adopted','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[k])

    def test_exact_arithmetic_budget_failure_never_exports_partial_cash(self):
        denominators=[2**845,3**535,5**365,7**301]
        for family in ['receivables','advance_income']:
            for cutoff in ['opening','closing']:
                self.spec['working_balances'][family][cutoff]['value']=q(F(1,denominators.pop(0)))
        self.spec['amounts']['noncash_revenue']['value']=q(F(1,23**187))
        p=self.run_case().payload;self.assertIn('exact_cash_arithmetic_budget_exceeded',p['blockers'])
        self.assertEqual(p['accrual_cash_state'],'blocked');self.assertIsNone(p['exportable_operating_distribution'])
