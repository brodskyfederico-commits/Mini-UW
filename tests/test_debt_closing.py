import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q,DateWindow
from miniuw_foundation.debt_closing import reconcile_debt_closing,parse_debt_closing,DatedLoanEvidence
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from debt_closing_test_support import fixture,build,raw,sha,set_closing_date

def num(n):return q(F(n))
def f(q):return F(int(q['numerator']),int(q['denominator']))


class DebtClosingTests(unittest.TestCase):
    def setUp(self):self.loan,self.closing,self.spec=fixture()
    def case(self):return build(self.loan,self.closing,self.spec)
    def run_case(self):return reconcile_debt_closing(*self.case())
    def test_before_third_payment_uses_opening_balance_not_balloon_plus_principal(self):
        p=self.run_case().payload;r=p['loans'][0];self.assertEqual(p['state'],'matched_synthetic_debt_assumptions')
        self.assertEqual(f(r['computed_principal_to_close']),1200-100-100);self.assertEqual(f(r['computed_regular_interval_interest_to_close']),0)
        self.assertEqual(r['assumed_paid_regular_payment_indices'],[1,2]);self.assertEqual(f(r['scheduled_row_balloon_due']),900)
        self.assertFalse(r['balloon_added_again_to_principal']);self.assertEqual(r['principal_schedule_pointer'],'/schedule/2/opening_balance')
    def test_after_third_regular_payment_uses_remaining_balloon_once(self):
        self.spec['loans'][0]['payment_cutoff']='after_regular_payment_before_balloon'
        for suffix in ['due','paid']:self.closing['old_debts'][0]['principal_'+suffix]['value']=num(900)
        p=self.run_case().payload;r=p['loans'][0];self.assertEqual(p['state'],'matched_synthetic_debt_assumptions')
        self.assertEqual(f(r['computed_principal_to_close']),900);self.assertEqual(r['assumed_paid_regular_payment_indices'],[1,2,3]);self.assertEqual(f(r['computed_regular_interval_interest_to_close']),0)
    def test_positive_interest_cutoff_before_and_after_known_annuity_payment(self):
        # L=210, i=10%, n=2: two payments of 121; first interest 21, capital 100.
        self.loan.update(principal=num(210),periodic_rate=num(F(1,10)),amortization_payments=2,maturity_payment=2,payments_per_year=1,origination_date='2027-01-01',payment_dates=['2028-01-01','2029-01-01'])
        for mode,principal,interest,indices in [('before_regular_payment',210,21,[]),('after_regular_payment_before_balloon',110,0,[1])]:
            self.spec['loans'][0]['payment_cutoff']=mode
            for key,value in [('principal',principal),('interest',interest)]:
                for suffix in ['due','paid']:self.closing['old_debts'][0][key+'_'+suffix]['value']=num(value)
            p=self.run_case().payload;r=p['loans'][0];self.assertEqual(p['state'],'matched_synthetic_debt_assumptions')
            self.assertEqual(f(r['computed_principal_to_close']),principal);self.assertEqual(f(r['computed_regular_interval_interest_to_close']),interest);self.assertEqual(r['assumed_paid_regular_payment_indices'],indices)
    def test_full_amortization_after_last_payment_has_explicit_zero_principal(self):
        self.loan.update(amortization_payments=3)
        self.spec['loans'][0]['payment_cutoff']='after_regular_payment_before_balloon'
        for suffix in ['due','paid']:self.closing['old_debts'][0]['principal_'+suffix]['value']=num(0)
        p=self.run_case().payload;self.assertEqual(p['state'],'matched_synthetic_debt_assumptions');self.assertEqual(f(p['loans'][0]['computed_principal_to_close']),0)
    def test_origination_cutoff_is_explicit_and_no_accrual_is_assumed_only_there(self):
        set_closing_date(self.closing,self.loan['origination_date']);self.spec['loans'][0]['payment_cutoff']='at_origination_no_accrual'
        for suffix in ['due','paid']:self.closing['old_debts'][0]['principal_'+suffix]['value']=num(1200)
        p=self.run_case().payload;self.assertEqual(p['state'],'matched_synthetic_debt_assumptions');self.assertEqual(p['loans'][0]['assumed_paid_regular_payment_indices'],[])
        set_closing_date(self.closing,'2027-10-02');self.assertEqual(self.run_case().payload['state'],'blocked')
    def test_between_payment_and_after_maturity_dates_do_not_infer_stub_or_extension(self):
        for date in ['2027-12-15','2028-01-02','2030-01-01']:
            set_closing_date(self.closing,date);p=self.run_case().payload
            self.assertEqual(p['state'],'blocked');self.assertIsNone(p['loans'][0]['computed_principal_to_close']);self.assertTrue(any('no_stub_or_extension'in b for b in p['blockers']))
    def test_double_counting_balloon_and_old_unamortized_principal_is_rejected(self):
        for value in [1200,1900,900]:
            for suffix in ['due','paid']:self.closing['old_debts'][0]['principal_'+suffix]['value']=num(value)
            p=self.run_case().payload;self.assertEqual(f(p['loans'][0]['computed_principal_to_close']),1000)
            self.assertTrue(any('principal_closing_claim_differs'in b for b in p['blockers']))
    def test_interest_already_in_assumed_paid_regular_service_not_charged_again(self):
        self.loan,self.closing,self.spec=fixture('sale');self.spec['loans'][0]['payment_cutoff']='after_regular_payment_before_balloon'
        # Keep supplied pre-payment principal/interest to demonstrate discrepancy.
        p=self.run_case().payload;r=p['loans'][0];self.assertEqual(f(r['computed_regular_interval_interest_to_close']),0)
        self.assertTrue(any('interest_closing_claim_differs'in b for b in p['blockers']));self.assertTrue(any('principal_closing_claim_differs'in b for b in p['blockers']))
    def test_all_payment_and_change_assumptions_and_basis_refs_required(self):
        for key,value in [('prior_regular_service_assumed_paid',None),('prior_regular_service_assumed_paid',False),('unmodeled_debt_changes_declared_absent',False),('unmodeled_debt_changes_declared_absent',None),('payment_assumption_basis_ref',None),('cutoff_basis_ref',None),('fees_and_other_scope_basis_ref',None)]:
            spec=copy.deepcopy(self.spec);spec['loans'][0][key]=value;p=reconcile_debt_closing(*build(self.loan,self.closing,spec)).payload;self.assertEqual(p['state'],'blocked')
    def test_missing_dated_schedule_and_upstream_numeric_blockers_preserved(self):
        for key,value in [('payment_dates',None),('principal',None),('maturity_payment',None),('payment_dates',['2027-11-01'])]:
            loan=copy.deepcopy(self.loan);loan[key]=value;p=reconcile_debt_closing(*build(loan,self.closing,self.spec)).payload
            self.assertEqual(p['state'],'blocked');self.assertIsNone(p['loans'][0]['computed_principal_to_close'])
            if key=='principal':self.assertIn('principal_missing',p['loans'][0]['loan_payment_blockers'])
    def test_annual_sizing_frequency_not_used_to_infer_dated_payoff(self):
        self.loan['payments_per_year']=None;loans,cr,c,s=self.case();self.assertEqual(loans[0].run.payload['annual_sizing']['state'],'blocked')
        self.assertEqual(reconcile_debt_closing(loans,cr,c,s).payload['state'],'matched_synthetic_debt_assumptions')
    def test_fees_and_other_unknown_still_block_even_with_known_principal(self):
        self.closing['old_debts'][0]['other_due']['value']=None;p=self.run_case().payload
        self.assertEqual(f(p['loans'][0]['computed_principal_to_close']),1000);self.assertIn('closing_plan_blocked',p['blockers']);self.assertTrue(p['closing_blockers'])
    def test_stale_closing_and_loan_bindings_never_repair_sources(self):
        loans,cr,c,s=self.case()
        for key in ['closing_source_sha256','closing_run_sha256']:
            spec=json.loads(s);spec[key]='0'*64;self.assertIn(key+'_mismatch',reconcile_debt_closing(loans,cr,c,raw(spec)).payload['blockers'])
        for key in ['loan_source_sha256','loan_run_sha256']:
            spec=json.loads(s);spec['loans'][0][key]='0'*64;p=reconcile_debt_closing(loans,cr,c,raw(spec)).payload;self.assertIn(key+'_mismatch',p['loans'][0]['blockers'])
        self.assertEqual(cr,raw(self.closing))
    def test_complete_old_loan_inventory_required_in_bindings_and_evidence(self):
        loans,cr,c,s=self.case();p=reconcile_debt_closing((),cr,c,s).payload;self.assertEqual(p['state'],'blocked')
        spec=json.loads(s);spec['loans']=[];p=reconcile_debt_closing(loans,cr,c,raw(spec)).payload
        self.assertIn('cutoff_binding_inventory_does_not_match_all_old_debts',p['blockers'])
        extra=copy.deepcopy(self.loan);extra['loan_id']='SYNTHETIC-extra';extra_loans=build(extra,self.closing,self.spec)[0]
        self.assertEqual(reconcile_debt_closing(loans+extra_loans,cr,c,s).payload['state'],'blocked')
    def test_context_currency_and_live_scope_guards(self):
        for key,value in [('currency','EUR')]:
            loan=copy.deepcopy(self.loan);loan[key]=value;self.assertEqual(reconcile_debt_closing(*build(loan,self.closing,self.spec)).payload['state'],'blocked')
        self.loan['context']['run_id']='SYNTHETIC-other';self.assertEqual(self.run_case().payload['state'],'blocked')
        spec=copy.deepcopy(self.spec);spec['context']['deal_id']='real'
        with self.assertRaises(ValidationError):parse_debt_closing(raw(spec))
    def test_rehashed_forged_debt_and_closing_runs_rejected_before_comparison(self):
        loans,cr,c,s=self.case();d=loans[0].run.payload;d['schedule'][2]['opening_balance']=num(999);enc=canonical(d);fake=replace(loans[0],run=replace(loans[0].run,payload_json=enc,sha256=digest(enc)))
        with self.assertRaises(ValidationError):reconcile_debt_closing((fake,),cr,c,s)
        p=c.payload;p['exportable_equity_distribution']=num(999);enc=canonical(p)
        with self.assertRaises(ValidationError):reconcile_debt_closing(loans,cr,replace(c,payload_json=enc,sha256=digest(enc)),s)
    def test_strict_inventory_types_duplicates_transport_and_cutoff(self):
        loans,cr,c,s=self.case()
        for bad in [list(loans),loans+loans,loans*65]:
            with self.assertRaises(ValidationError):reconcile_debt_closing(bad,cr,c,s)
        huge=replace(loans[0],loan_raw=b'x'*8_388_609)
        with self.assertRaises(ValidationError):reconcile_debt_closing((huge,),cr,c,s)
        spec=json.loads(s);spec['loans'][0]['payment_cutoff']='actual_365'
        with self.assertRaises(ValidationError):parse_debt_closing(raw(spec))
        spec=json.loads(s);spec['loans'].append(spec['loans'][0])
        with self.assertRaises(ValidationError):parse_debt_closing(raw(spec))
    def test_immutable_payload_and_source_ids(self):
        loans,cr,c,s=self.case();r=reconcile_debt_closing(loans,cr,c,s);p=r.payload;p['loans'].clear()
        self.assertEqual(len(r.payload['loans']),1);self.assertEqual(r.payload['spec_source_sha256'],sha(s));self.assertEqual(r.sha256,digest(r.payload_json))
    def test_reopened_archive_replays_dated_windows_and_sources(self):
        windows=(DateWindow(window_id='SYNTHETIC-horizon',start_date='2027-10-01',end_date='2028-01-02',boundary='start_inclusive_end_exclusive'),)
        loans,cr,c,s=build(self.loan,self.closing,self.spec,windows);r=reconcile_debt_closing(loans,cr,c,s)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'payoff.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_debt_closing(loans,cr,c,s,r);self.assertEqual(key,a.save_debt_closing(loans,cr,c,s,r))
            with EvidenceArchive(path)as a:
                b=a.load_debt_closing(key);self.assertEqual(b.run,r);self.assertEqual(b.payload['loans'][0]['windows'][0]['window_id'],'SYNTHETIC-horizon');self.assertEqual(a.get_debt_closing_spec(b.payload['spec_source_sha256']),s)
    def test_archive_rollback_forgery_version_missing_and_blocked_recovery(self):
        loans,cr,c,s=self.case();r=reconcile_debt_closing(loans,cr,c,s);p=r.payload;p['state']='wrong';enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_debt_closing(loans,cr,c,s,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_debt_closing(loans,cr,c,s,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_debt_closing(loans,cr,c,s,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_debt_closing(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_debt_closing(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(loans[0].loan_raw)))
            with self.assertRaises(MissingEvidence):a.load_debt_closing(key)
        r=reconcile_debt_closing((),cr,c,s)
        with EvidenceArchive(':memory:')as a:key=a.save_debt_closing((),cr,c,s,r);self.assertEqual(a.load_debt_closing(key).run,r)
    def test_no_assumed_payment_is_relabelled_as_actual_bank_evidence(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['closing_source_changed','payment_assumptions_adopted','scheduled_payment_history_actually_verified','bank_payoff_statement_verified','actual_debt_discharge_verified','whole_project_cash_reconciled','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])
