from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.deferred_insurance_settlement import reconcile_deferred_insurance_settlement
from miniuw_foundation.insurance_terminal_closing import parse_insurance_terminal_binding,reconcile_insurance_terminal_closing,verify_insurance_terminal_closing
from miniuw_foundation.insurance_terminal_artifacts import (build_insurance_terminal_artifacts,write_insurance_terminal_artifacts,
    read_insurance_terminal_artifacts,recover_insurance_terminal_directory,audit_insurance_terminal_directory,versions)

ROOT=Path(__file__).resolve().parents[1];q=lambda v:rational(F(v));enc=lambda p:(canonical(p)+'\n').encode()
def sources(label='on-cut'):return tuple((ROOT/('templates/insurance-terminal-'+label+'-'+kind+'-T107.json')).read_bytes()for kind in('plan','closing','binding'))
def changed(label='on-cut',change=None,refresh=True):
    p,c,b=[json.loads(raw)for raw in sources(label)]
    if change:change(p,c,b)
    if refresh:b.update(plan_source_sha256=sha(enc(p)),closing_source_sha256=sha(enc(c)))
    return enc(p),enc(c),enc(b)
def run(label='on-cut',change=None):return reconcile_insurance_terminal_closing(*changed(label,change))


class InsuranceTerminalClosingTests(unittest.TestCase):
    def test_on_cut_insurance_is_in_closing_once_not_subtracted_again(self):
        raw=sources();before=tuple(raw);p=reconcile_insurance_terminal_closing(*raw).payload;s=p['summary'];prior=produce_closing_cash(raw[1]).payload
        self.assertEqual(s['allocated_expense'],q(20));self.assertEqual(s['planned_cash_before_cut'],q(15))
        self.assertEqual(s['bound_payment_sum'],q(5));self.assertEqual(s['nominal_after_supplied_cut_payments'],q(0))
        self.assertEqual(s['exportable_equity_distribution'],q(95));self.assertEqual(s['net_residual_after_retention'],prior['net_residual_after_retention'])
        self.assertEqual(s['total_cash_conservation_residual'],q(0));self.assertTrue(p['no_additional_deduction_applied']);self.assertEqual(raw,before)

    def test_prepaid_future_due_does_not_create_another_sale_payment(self):
        p=run('prepaid').payload;s=p['summary'];self.assertEqual(p['payment_checks'],[])
        self.assertEqual(s['planned_cash_before_cut'],q(20));self.assertEqual(s['nominal_before_cut'],q(0));self.assertEqual(s['bound_payment_sum'],q(0));self.assertEqual(s['exportable_equity_distribution'],q(100))

    def test_explicit_cash_in_and_missing_funding_assumption_are_distinct(self):
        p=run('cash-in').payload;s=p['summary'];self.assertEqual(s['exportable_equity_contribution'],q(5));self.assertEqual(s['exportable_equity_distribution'],q(0))
        self.assertEqual(s['net_residual_after_retention'],q(-5));self.assertFalse(p['funding_availability_verified'])
        p=run('funding-missing').payload;self.assertIsNone(p['summary']);self.assertIn('closing_cash_blocked',p['blockers'])

    def test_future_payment_is_not_accelerated_into_sale_even_with_matching_money(self):
        p=run('future').payload;self.assertIsNone(p['summary']);self.assertIn('after_cut_plan_payment_requires_other_profile_no_acceleration',p['blockers'])
        self.assertFalse(p['payer_or_buyer_transfer_inferred'])

    def test_split_payments_bind_each_payment_id_and_may_reorder_without_changing_cash(self):
        p=run('split').payload;self.assertEqual(len(p['payment_checks']),2);self.assertEqual(p['summary']['bound_payment_sum'],q(5))
        changed_run=run('split',lambda p,c,b:b['payments'].reverse()).payload;self.assertEqual(changed_run['summary'],p['summary'])
        self.assertEqual([r['binding_pointer']for r in changed_run['payment_checks']],['/payments/0','/payments/1'])

    def test_equal_global_total_cannot_hide_wrong_payment_or_installment(self):
        def compensate(p,c,b):b['payments'][0]['amount']=q(1);b['payments'][1]['amount']=q(4)
        for change in(compensate,lambda p,c,b:b['payments'][0].update(payment_id='SYNTHETIC-wrong'),lambda p,c,b:b['payments'][0].update(installment_id='SYNTHETIC-wrong')):
            p=run('split',change).payload;self.assertIsNone(p['summary']);self.assertTrue(p['blockers'])

    def test_wrong_other_uses_and_duplicate_deduction_withhold_current_closing_figures(self):
        for value in(4,10):
            raw=changed(change=lambda p,c,b:c['amounts']['other_cash_uses'].update(value=q(value)))
            self.assertIsNotNone(produce_closing_cash(raw[1]).payload['exportable_equity_distribution'])
            p=reconcile_insurance_terminal_closing(*raw).payload;self.assertIsNone(p['summary']);self.assertIn('bound_payment_sum_differs_from_closing_other_cash_uses',p['blockers'])

    def test_context_currency_cut_and_item_remain_exact_even_with_fresh_hashes(self):
        changes=[lambda p,c,b:c['context'].update(run_id='SYNTHETIC-another-run'),lambda p,c,b:b.update(currency='EUR'),
            lambda p,c,b:b.update(settlement_date='2027-07-02'),lambda p,c,b:b.update(economic_item_id='SYNTHETIC-other-item'),
            lambda p,c,b:b['payments'][0].update(payment_date='2027-06-30')]
        for change in changes:self.assertIsNone(run(change=change).payload['summary'])

    def test_missing_sources_inventories_dates_and_money_withhold_whole_summary(self):
        changes=[lambda p,c,b:b.update(source_ref=None),lambda p,c,b:b.update(classification_basis_ref=None),lambda p,c,b:b.update(payment_inventory_declared_complete=None),
            lambda p,c,b:b.update(settlement_date=None),lambda p,c,b:b['payments'][0].update(source_ref=None),lambda p,c,b:b['payments'][0].update(amount=None),
            lambda p,c,b:b['payments'][0].update(payment_date=None),lambda p,c,b:p['planned_payments'][0].update(amount=None),lambda p,c,b:c['amounts']['gross_proceeds'].update(value=None)]
        for change in changes:
            result=run(change=change).payload;self.assertEqual(result['state'],'PENDING');self.assertIsNone(result['summary'])

    def test_known_zero_row_is_preserved_and_cannot_be_omitted_as_empty(self):
        p=run('zero').payload;self.assertEqual(len(p['payment_checks']),1);self.assertEqual(p['summary']['bound_payment_sum'],q(0))
        self.assertEqual(p['summary']['exportable_equity_distribution'],q(100))
        for change in(lambda p,c,b:b.update(payments=[]),lambda p,c,b:b['payments'][0].update(amount=None)):
            self.assertIsNone(run('zero',change).payload['summary'])

    def test_source_bytes_identity_and_equivalent_rationals_are_both_explicit(self):
        a,b,c=sources();p=json.loads(c);p['plan_source_sha256']=sha(a+b'\n')
        self.assertIsNone(reconcile_insurance_terminal_closing(a,b,enc(p)).payload['summary'])
        self.assertIsNotNone(reconcile_insurance_terminal_closing(a+b'\n',b,enc(p)).payload['summary'])
        self.assertEqual(run(change=lambda p,c,b:b['payments'][0].update(amount={'numerator':'10','denominator':'2'})).payload['summary'],run().payload['summary'])

    def test_strict_profile_unknown_fields_duplicates_and_types_are_rejected(self):
        for change in(lambda p,c,b:b.update(extra=True),lambda p,c,b:b['payments'].append(copy.deepcopy(b['payments'][0])),
            lambda p,c,b:b['assumptions'].update(future_payments='accelerate'),lambda p,c,b:b['payments'][0].update(amount=0.5),
            lambda p,c,b:b.update(payment_inventory_declared_complete=1),lambda p,c,b:b.update(plan_source_sha256='not-a-hash')):
            with self.assertRaises(ValidationError):parse_insurance_terminal_binding(changed(change=change,refresh=False)[2])
        raw=sources()[2]
        with self.assertRaises(ValidationError):parse_insurance_terminal_binding(raw.replace(b'"schema":',b'"schema":null,"schema":',1))

    def test_actual_exact_arithmetic_excess_withholds_every_current_money_field(self):
        p,c,b=[json.loads(raw)for raw in sources()];seed=p['planned_payments'][-1]
        rows=[dict(seed,payment_id='SYNTHETIC-budget-'+str(i),amount=q(F(1,2**800+2*i+1)))for i in range(6)]
        p['planned_payments']=p['planned_payments'][:-1]+rows;b['payments']=copy.deepcopy(rows);a,d=enc(p),enc(c);b.update(plan_source_sha256=sha(a),closing_source_sha256=sha(d))
        result=reconcile_insurance_terminal_closing(a,d,enc(b)).payload;self.assertIsNone(result['summary']);self.assertIn('terminal_binding_exact_arithmetic_budget_exceeded',result['blockers'])
        self.assertEqual(result['source_hashes']['plan'],sha(a))

    def test_rehashed_result_and_other_raw_source_are_not_verified(self):
        raw=sources();result=reconcile_insurance_terminal_closing(*raw);p=result.payload;p['summary']['exportable_equity_distribution']=q(100);text=canonical(p)
        with self.assertRaises(ValidationError):verify_insurance_terminal_closing(*raw,replace(result,payload_json=text,sha256=digest(text)))
        with self.assertRaises(ValidationError):verify_insurance_terminal_closing(raw[0]+b'\n',*raw[1:],result)

    def test_five_file_recovery_preserves_valid_and_blocked_sources_without_PDF(self):
        for label in('on-cut','missing','future'):
            raw=sources(label);values,result=build_insurance_terminal_artifacts(*raw);self.assertEqual(len(values),5);self.assertFalse(any(k.endswith('.pdf')for k in values))
            with tempfile.TemporaryDirectory()as td:
                root=Path(td)
                for k,v in values.items():(root/k).write_bytes(v)
                self.assertEqual(recover_insurance_terminal_directory(root),result);self.assertEqual(audit_insurance_terminal_directory(root)['files_verified'],5)

    def test_all_versions_source_and_rehashed_output_forgery_require_full_replay(self):
        values,_=build_insurance_terminal_artifacts(*sources())
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for k,v in values.items():(root/k).write_bytes(v)
            for key in versions():
                restore();p=json.loads(values['package.json']);p[key]='0'*64;(root/'package.json').write_bytes(enc(p))
                with self.assertRaises(ValidationError):recover_insurance_terminal_directory(root)
            for name,raw in [('terminal-results.json',b'{}'),('binding-source.json',sources()[2]+b'\n')]:
                restore();p=json.loads(values['package.json']);row=next(r for r in p['files']if r['path']==name);row.update(bytes=len(raw),sha256=sha(raw));(root/name).write_bytes(raw);(root/'package.json').write_bytes(enc(p))
                with self.assertRaises(ValidationError):recover_insurance_terminal_directory(root)
            restore();p=json.loads(values['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(enc(p))
            with self.assertRaises(ValidationError):recover_insurance_terminal_directory(root)

    def test_retry_no_overwrite_safe_inventory_and_failed_rename_cleanup(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);out=root/'out';write_insurance_terminal_artifacts(*sources(),out);before=read_insurance_terminal_artifacts(out)
            self.assertEqual(write_insurance_terminal_artifacts(*sources(),out)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_insurance_terminal_artifacts(*sources('prepaid'),out)
            self.assertEqual(read_insurance_terminal_artifacts(out),before);(out/'extra').write_bytes(b'x')
            with self.assertRaises(ValidationError):read_insurance_terminal_artifacts(out)
            (out/'extra').unlink();(out/'terminal-results.json').unlink();(out/'terminal-results.json').symlink_to(out/'plan-source.json')
            with self.assertRaises(ValidationError):read_insurance_terminal_artifacts(out)
        with patch('miniuw_foundation.insurance_terminal_artifacts.MAX_FILE_BYTES',10):
            with self.assertRaises(ValidationError):build_insurance_terminal_artifacts(*sources())
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep';keep.write_bytes(b'x')
            with patch('miniuw_foundation.insurance_terminal_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_insurance_terminal_artifacts(*sources(),root/'out')
            self.assertEqual(list(root.iterdir()),[keep])

    def test_no_financial_authority_or_full_case_return_is_granted(self):
        p=run().payload;self.assertEqual(p['decision'],'PENDING')
        for key in('accounting_balances_derived','nominal_tail_is_approved_legal_liability','actual_bank_payments_verified','funding_availability_verified',
            'payer_or_buyer_transfer_inferred','source_authority_verified','full_operating_sale_return_integration_completed','personal_investor_return_verified',
            'new_external_PDF_created','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):self.assertIs(p[key],False)
        self.assertEqual(reconcile_deferred_insurance_settlement(sources()[0]).payload['totals']['nominal_not_settled_before_cut'],q(5))


if __name__=='__main__':unittest.main()
