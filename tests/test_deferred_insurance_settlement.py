from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.expense_schedule import produce_expense_schedule
from miniuw_foundation.deferred_insurance_settlement import reconcile_deferred_insurance_settlement,verify_deferred_insurance_settlement,parse_deferred_insurance_settlement
from miniuw_foundation.deferred_insurance_artifacts import (build_deferred_insurance_artifacts,write_deferred_insurance_artifacts,
    read_deferred_insurance_artifacts,recover_deferred_insurance_directory,audit_deferred_insurance_directory,versions)

ROOT=Path(__file__).resolve().parents[1];q=lambda value:rational(F(value));encoded=lambda p:(canonical(p)+'\n').encode()
def source(label):return(ROOT/('templates/insurance-settlement-'+label+'-T106.json')).read_bytes()
def run(label='deferred',change=None):
    p=json.loads(source(label))
    if change:change(p)
    return reconcile_deferred_insurance_settlement(encoded(p))


class DeferredInsuranceSettlementTests(unittest.TestCase):
    def test_control_preserves_original_T90_expense_and_nominal_due_amounts(self):
        original=(ROOT/'templates/synthetic-insurance-schedule.json').read_bytes();prior=produce_expense_schedule(original).payload
        p=run('control').payload;self.assertEqual(p['totals']['allocated_expense'],prior['totals']['expense'])
        self.assertEqual(p['totals']['nominal_installments'],prior['totals']['installments']);self.assertEqual(p['totals']['planned_payments'],q(20))
        self.assertEqual([r['allocated_expense']for r in p['allocations']],[r['allocated_expense']for r in prior['allocations']])
        self.assertEqual(p['totals']['nominal_not_settled_before_cut'],q(0));self.assertEqual(p['integration_state'],'PENDING_FINANCIAL_INTEGRATION')
        self.assertEqual(original,(ROOT/'templates/synthetic-insurance-schedule.json').read_bytes())

    def test_deferred_cash_tail_is_visible_and_requires_another_terminal_source(self):
        p=run().payload;t=p['totals']
        self.assertEqual(t['allocated_expense'],q(20));self.assertEqual(t['cash_by_cut_bucket'],dict(before_cut=q(15),on_cut=q(0),after_cut=q(5)))
        self.assertEqual(t['nominal_not_settled_before_cut'],q(5));self.assertTrue(p['terminal_settlement_source_required'])
        self.assertEqual(p['integration_state'],'PENDING_TERMINAL_SETTLEMENT_SOURCE');self.assertFalse(p['case_or_cash_or_return_modified'])
        self.assertFalse(p['full_case_financial_integration_completed']);self.assertFalse(p['nominal_tail_is_approved_legal_liability']);self.assertEqual(p['decision'],'PENDING')

    def test_late_payment_and_future_due_are_distinct_with_same_cash_tail(self):
        late=run('late').payload['totals'];future=run().payload['totals']
        self.assertEqual(late['cash_by_cut_bucket'],future['cash_by_cut_bucket']);self.assertEqual(late['nominal_not_settled_before_cut'],q(5))
        self.assertEqual(late['due_before_cut_not_settled'],q(5));self.assertEqual(late['not_due_before_cut_not_prepaid'],q(0))
        self.assertEqual(future['due_before_cut_not_settled'],q(0));self.assertEqual(future['not_due_before_cut_not_prepaid'],q(5))
        self.assertEqual(late['due_by_cut_bucket']['after_cut'],q(0));self.assertEqual(future['due_by_cut_bucket']['after_cut'],q(5))

    def test_future_due_can_be_prepaid_without_inventing_an_outstanding_balance(self):
        p=run('prepaid').payload;t=p['totals']
        self.assertEqual(t['due_by_cut_bucket']['after_cut'],q(5));self.assertEqual(t['cash_by_cut_bucket']['after_cut'],q(0))
        self.assertEqual(t['cash_by_cut_bucket']['before_cut'],q(20));self.assertEqual(t['nominal_not_settled_before_cut'],q(0))
        self.assertFalse(p['terminal_settlement_source_required']);self.assertFalse(p['penalties_or_prepayment_rights_verified'])

    def test_events_on_cut_are_outside_previous_cash_and_never_counted_twice(self):
        p=run('on-cut').payload;t=p['totals']
        self.assertEqual(t['due_by_cut_bucket'],dict(before_cut=q(15),on_cut=q(5),after_cut=q(0)))
        self.assertEqual(t['cash_by_cut_bucket'],dict(before_cut=q(15),on_cut=q(5),after_cut=q(0)))
        self.assertEqual(t['nominal_not_settled_before_cut'],q(5));self.assertFalse(p['cutoff_includes_same_date_events'])
        self.assertEqual(p['planned_payments'][-1]['time_bucket'],'on_cut')

    def test_split_payments_keep_explicit_linkage_and_order_independent_totals(self):
        p=run('late').payload;due=p['due_installments'][1]
        self.assertEqual(due['payment_indices'],[1,2]);self.assertEqual(due['planned_total'],q(15));self.assertEqual(due['planned_before_cut'],q(10))
        self.assertEqual(due['nominal_not_settled_before_cut'],q(5))
        changed=run('late',lambda p:p['planned_payments'].reverse()).payload
        self.assertEqual(changed['totals'],p['totals'])
        for i,row in enumerate(changed['planned_payments']):self.assertEqual(row['source_pointer'],'/planned_payments/'+str(i))

    def test_known_zero_preserves_rows_and_differs_from_missing_even_with_empty_inventories(self):
        p=run('zero').payload;self.assertEqual(p['totals']['allocated_expense'],q(0));self.assertEqual(len(p['due_installments']),1);self.assertEqual(len(p['planned_payments']),1)
        self.assertEqual(p['planned_payments'][0]['amount'],q(0));self.assertFalse(p['terminal_settlement_source_required'])
        empty=run('zero',lambda p:(p.update(due_installments=[]),p.update(planned_payments=[]))).payload
        self.assertEqual(empty['totals']['planned_payments'],q(0))
        missing=run('zero',lambda p:p['allocations'][0].update(fraction=None)).payload
        self.assertIsNone(missing['totals']);self.assertIsNone(missing['terminal_settlement_source_required'])

    def test_required_missing_data_and_sources_withhold_every_derived_amount(self):
        changes=[lambda p:p.update(total_cost=None),lambda p:p['allocations'][0].update(fraction=None),lambda p:p['due_installments'][0].update(amount=None),
            lambda p:p['planned_payments'][0].update(amount=None),lambda p:p.update(source_ref=None),lambda p:p.update(allocation_basis_ref=None),
            lambda p:p.update(settlement_basis_ref=None),lambda p:p.update(payment_inventory_declared_complete=None),
            lambda p:p.update(installment_inventory_declared_complete=False),lambda p:p.update(period_inventory_declared_complete=None),
            lambda p:p['planned_payments'][0].update(source_ref=None)]
        for change in changes:
            p=run(change=change).payload;self.assertEqual(p['state'],'PENDING');self.assertIsNone(p['totals']);self.assertIsNone(p['terminal_settlement_source_required'])
            self.assertTrue(all(r['allocated_expense']is None for r in p['allocations']))
            self.assertTrue(all(r['planned_total']is None and r['planned_before_cut']is None and r['nominal_not_settled_before_cut']is None for r in p['due_installments']))

    def test_global_total_cannot_hide_overpayment_underpayment_or_omitted_plan(self):
        def compensate(p):p['planned_payments'][0]['amount']=q(4);p['planned_payments'][1]['amount']=q(11)
        for change in(compensate,lambda p:p.update(planned_payments=[]),lambda p:p['due_installments'][0].update(amount=q(6)),
            lambda p:p['planned_payments'][0].update(installment_id='SYNTHETIC-unknown'),lambda p:p['planned_payments'][0].update(amount=q(-1))):
            p=run(change=change).payload;self.assertIsNone(p['totals']);self.assertTrue(p['blockers'])
        self.assertTrue(any('this_installment'in s for s in run(change=compensate).payload['blockers']))

    def test_opening_dates_other_cuts_gaps_and_overlap_require_other_profiles(self):
        changes=[lambda p:p['planned_payments'][0].update(payment_date='2026-12-01'),lambda p:p['due_installments'][0].update(due_date='2026-12-01'),
            lambda p:p.update(cutoff_date='2027-08-01'),lambda p:p['allocations'][1].update(start_date='2027-04-02'),
            lambda p:p['allocations'][1].update(start_date='2027-03-31'),lambda p:p['allocations'].reverse()]
        for change in changes:self.assertIsNone(run(change=change).payload['totals'])

    def test_fractions_are_supplied_not_inferred_from_days_and_schema_stays_strict(self):
        def quarter(p):
            p['allocation_basis_ref']='SYNTHETIC-explicit-quarter-three-quarter-no-daycount';p['allocations'][0]['fraction']=q(F(1,4));p['allocations'][1]['fraction']=q(F(3,4))
        self.assertEqual([r['allocated_expense']for r in run(change=quarter).payload['allocations']],[q(5),q(15)])
        for change in(lambda p:p.update(kind='property_tax'),lambda p:p.update(extra=True),lambda p:p['due_installments'].append(copy.deepcopy(p['due_installments'][0])),
            lambda p:p['planned_payments'].append(copy.deepcopy(p['planned_payments'][0])),lambda p:p['assumptions'].update(refunds_credits_interest_fees=True),lambda p:p['planned_payments'][0].update(amount=0.5)):
            p=json.loads(source('deferred'));change(p)
            with self.assertRaises(ValidationError):parse_deferred_insurance_settlement(encoded(p))
        with self.assertRaises(ValidationError):parse_deferred_insurance_settlement(source('deferred').replace(b'"kind":',b'"kind":null,"kind":',1))

    def test_real_fraction_arithmetic_excess_withholds_all_computations_and_preserves_source(self):
        p=json.loads(source('deferred'));seed=p['allocations'][0];dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01','2027-05-01','2027-06-01','2027-07-01']
        p['allocations']=[dict(seed,period_ref='SYNTHETIC-budget-'+str(i),start_date=dates[i],end_date=dates[i+1],fraction=q(F(1,2**800+2*i+1)))for i in range(6)]
        raw=encoded(p);before=raw;p=reconcile_deferred_insurance_settlement(raw).payload
        self.assertIn('exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['totals']);self.assertEqual(p['source'],json.loads(before));self.assertIsNone(p['terminal_settlement_source_required'])

    def test_rehashed_result_and_other_source_bytes_cannot_be_verified(self):
        raw=source('deferred');result=reconcile_deferred_insurance_settlement(raw);p=result.payload;p['totals']['nominal_not_settled_before_cut']=q(0);text=canonical(p);fake=replace(result,payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):verify_deferred_insurance_settlement(raw,fake)
        with self.assertRaises(ValidationError):verify_deferred_insurance_settlement(raw+b'\n',result)
        changed=reconcile_deferred_insurance_settlement(raw+b'\n');self.assertEqual(changed.payload['totals'],result.payload['totals']);self.assertNotEqual(changed.sha256,result.sha256)

    def test_three_file_recovery_reproduces_current_and_blocked_plans_without_PDF(self):
        for label in('deferred','missing'):
            values,result=build_deferred_insurance_artifacts(source(label));self.assertEqual(len(values),3);self.assertFalse(any(k.endswith('.pdf')for k in values))
            with tempfile.TemporaryDirectory()as td:
                root=Path(td)
                for k,v in values.items():(root/k).write_bytes(v)
                self.assertEqual(recover_deferred_insurance_directory(root),result);self.assertEqual(audit_deferred_insurance_directory(root)['files_verified'],3)
        self.assertIsNone(run('missing').payload['totals'])

    def test_incompatible_versions_and_rehashed_or_unsafe_packets_are_rejected(self):
        values,_=build_deferred_insurance_artifacts(source('deferred'))
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for k,v in values.items():(root/k).write_bytes(v)
            for key in versions():
                restore();p=json.loads(values['package.json']);p[key]='0'*64;(root/'package.json').write_bytes(encoded(p))
                with self.assertRaises(ValidationError):recover_deferred_insurance_directory(root)
            restore();(root/'settlement-results.json').write_bytes(b'{}');p=json.loads(values['package.json']);row=next(r for r in p['files']if r['path']=='settlement-results.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):recover_deferred_insurance_directory(root)
            restore();p=json.loads(values['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):recover_deferred_insurance_directory(root)

    def test_retry_no_overwrite_extra_symlink_size_and_failed_rename_cleanup(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);target=root/'out';write_deferred_insurance_artifacts(source('deferred'),target);before=read_deferred_insurance_artifacts(target)
            self.assertEqual(write_deferred_insurance_artifacts(source('deferred'),target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_deferred_insurance_artifacts(source('late'),target)
            self.assertEqual(before,read_deferred_insurance_artifacts(target));(target/'extra').write_bytes(b'x')
            with self.assertRaises(ValidationError):read_deferred_insurance_artifacts(target)
            (target/'extra').unlink();(target/'settlement-results.json').unlink();(target/'settlement-results.json').symlink_to(target/'settlement-source.json')
            with self.assertRaises(ValidationError):read_deferred_insurance_artifacts(target)
        with patch('miniuw_foundation.deferred_insurance_artifacts.MAX_FILE_BYTES',10):
            with self.assertRaises(ValidationError):build_deferred_insurance_artifacts(source('deferred'))
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep';keep.write_bytes(b'x')
            with patch('miniuw_foundation.deferred_insurance_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_deferred_insurance_artifacts(source('deferred'),root/'out')
            self.assertEqual(list(root.iterdir()),[keep])


if __name__=='__main__':unittest.main()
