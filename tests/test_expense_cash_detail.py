import copy
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.operating_noi import produce_operating_noi, ArithmeticBudgetError
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.expense_cash_detail import (
    reconcile_expense_cash_detail, parse_expense_cash_detail,
    export_expense_cash_bundle, recover_expense_cash_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
q = lambda n: rational(F(n))
raw = lambda p: canonical(p).encode('utf-8')


class ExpenseCashDetailTests(unittest.TestCase):
    def setUp(self):
        self.nr = (ROOT/'templates/synthetic-expense-detail-noi.json').read_bytes()
        self.cr = (ROOT/'templates/synthetic-expense-detail-cash.json').read_bytes()
        self.detail = json.loads((ROOT/'templates/synthetic-expense-cash-detail.json').read_bytes())
        self.n = produce_operating_noi(self.nr)
        self.c = reconcile_operating_cash(self.nr, self.n, self.cr)

    def run_case(self, detail=None):
        return reconcile_expense_cash_detail(self.nr, self.n, self.cr, self.c, raw(self.detail if detail is None else detail))

    def rebind_cash(self, p):
        self.cr = raw(p)
        self.c = reconcile_operating_cash(self.nr, self.n, self.cr)
        self.detail.update(cash_source_sha256=hashlib.sha256(self.cr).hexdigest(), cash_run_sha256=self.c.sha256)

    def bundle(self, run=None):
        return export_expense_cash_bundle(self.nr, self.n, self.cr, self.c, raw(self.detail), self.run_case() if run is None else run)

    def test_independent_item_and_aggregate_hand_identities(self):
        p = self.run_case().payload
        self.assertEqual(p['state'], 'matched_synthetic_expense_cash_detail')
        self.assertEqual([r['cash_payments'] for r in p['items']], [q(120+60-40), q(130+20-30), q(200+80-100)])
        self.assertEqual(p['totals'], dict(expense_amount=q(450), cash_payments=q(440), opening_payables=q(100), closing_payables=q(130), opening_prepaid=q(40), closing_prepaid=q(60)))
        self.assertTrue(all(r['cash_identity_residual'] == q(0) for r in p['items']))
        self.assertEqual(self.c.payload['computed_noi'], q(1000))
        self.assertEqual(self.c.payload['exportable_operating_distribution'], q(100))
        self.assertEqual(self.c.payload['expected_closing_free_cash'], q(405))

    def test_more_prepaid_cash_does_not_change_NOI_or_invent_distribution(self):
        before = self.run_case().payload
        self.detail['items'][0]['closing_prepaid'] = q(120)
        self.detail['items'][0]['payments'][0]['amount'] = q(200)
        c = json.loads(self.cr)
        c['working_balances']['prepaid_expenses']['closing']['value'] = q(120)
        c['amounts']['operating_payments_claim']['value'] = q(500)
        c['amounts']['closing_free_cash_claim']['value'] = q(345)
        self.rebind_cash(c)
        after = self.run_case().payload
        self.assertEqual(after['state'], before['state'])
        self.assertEqual(after['totals']['expense_amount'], before['totals']['expense_amount'])
        self.assertEqual(after['totals']['cash_payments'], q(500))
        self.assertEqual(self.c.payload['computed_noi'], q(1000))
        self.assertEqual(self.c.payload['exportable_operating_distribution'], q(100))
        self.assertEqual(self.c.payload['expected_closing_free_cash'], q(345))

    def test_offsetting_item_errors_cannot_hide_in_matching_total(self):
        self.detail['items'][0]['payments'][0]['amount'] = q(141)
        self.detail['items'][2]['payments'][0]['amount'] = q(179)
        p = self.run_case().payload
        self.assertEqual(p['state'], 'blocked')
        self.assertEqual([r['cash_identity_residual'] for r in p['items']], [q(1), q(0), q(-1)])
        self.assertIsNone(p['totals'])

    def test_explicit_zero_payment_and_unpaid_accrual_are_distinct(self):
        r = self.detail['items'][0]
        r.update(opening_prepaid=q(0), closing_prepaid=q(0), closing_payables=q(120), payments=[])
        c = json.loads(self.cr)
        c['working_balances']['prepaid_expenses']['opening']['value'] = q(0)
        c['working_balances']['prepaid_expenses']['closing']['value'] = q(0)
        c['working_balances']['payables']['closing']['value'] = q(250)
        c['amounts']['operating_payments_claim']['value'] = q(300)
        c['amounts']['closing_free_cash_claim']['value'] = q(545)
        self.rebind_cash(c)
        p = self.run_case().payload
        self.assertEqual(p['state'], 'matched_synthetic_expense_cash_detail')
        self.assertEqual(p['items'][0]['cash_payments'], q(0))
        r['payments_inventory_declared_complete'] = False
        self.assertEqual(self.run_case().payload['state'], 'blocked')

    def test_missing_or_extra_item_cannot_claim_complete_inventory(self):
        for mutate in (lambda p:p['items'].pop(), lambda p:p['items'].clear(), lambda p:p['items'][0].update(noi_pointer='/expense_rows/99')):
            p = copy.deepcopy(self.detail)
            mutate(p)
            self.assertIn('exact_all_NOI_expenses_and_tax_inventory_required', self.run_case(p).payload['blockers'])

    def test_duplicate_target_and_tax_misclassification_are_blocked(self):
        for field, value in [('noi_pointer', '/expense_rows/1'), ('kind', 'property_tax')]:
            p = copy.deepcopy(self.detail)
            p['items'][0][field] = value
            self.assertEqual(self.run_case(p).payload['state'], 'blocked')
        self.detail['items'][2]['kind'] = 'other_operating_expense'
        self.assertEqual(self.run_case().payload['state'], 'blocked')

    def test_each_expense_must_match_NOI_not_just_payment_identity(self):
        self.detail['items'][0].update(expense_amount=q(121), closing_prepaid=q(59))
        p = self.run_case().payload
        self.assertEqual(p['items'][0]['cash_identity_residual'], q(0))
        self.assertIn('SYNTHETIC-insurance:expense_differs_from_exact_NOI_item', p['blockers'])

    def test_balanced_item_stocks_must_match_aggregate_cash_stocks(self):
        self.detail['items'][0].update(opening_payables=q(1), closing_payables=q(1))
        p = self.run_case().payload
        self.assertEqual(p['items'][0]['cash_identity_residual'], q(0))
        self.assertIn('opening_payables_differs_from_aggregate_cash_plan', p['blockers'])
        self.assertIsNone(p['totals'])

    def test_null_negative_values_and_missing_basis_never_become_zero(self):
        for field, value in [('expense_amount', None), ('opening_prepaid', None), ('closing_payables', q(-1)), ('source_ref', None), ('settlement_basis_ref', None), ('payments_inventory_declared_complete', None), ('kind', 'unknown')]:
            p = copy.deepcopy(self.detail)
            p['items'][0][field] = value
            self.assertEqual(self.run_case(p).payload['state'], 'blocked')
        for value in (None, q(-1)):
            p = copy.deepcopy(self.detail)
            p['items'][0]['payments'][0]['amount'] = value
            self.assertIsNone(self.run_case(p).payload['items'][0]['cash_payments'])

    def test_complete_source_context_period_currency_and_date_binding(self):
        for field, value in [('noi_source_sha256', '0'*64), ('noi_run_sha256', '0'*64), ('cash_source_sha256', '0'*64), ('cash_run_sha256', '0'*64), ('currency', 'EUR'), ('period_ref', 'OTHER'), ('start_date', '2027-01-02'), ('end_date', '2028-01-02'), ('classification_basis_ref', None), ('inventory_declared_complete', None)]:
            p = copy.deepcopy(self.detail)
            p[field] = value
            self.assertEqual(self.run_case(p).payload['state'], 'blocked')
        p = copy.deepcopy(self.detail)
        p['context']['run_id'] = 'SYNTHETIC-other'
        self.assertEqual(self.run_case(p).payload['state'], 'blocked')
        for field, value in [('currency', None), ('period_ref', 'OTHER')]:
            p = copy.deepcopy(self.detail)
            p['items'][0][field] = value
            self.assertEqual(self.run_case(p).payload['state'], 'blocked')

    def test_payment_boundaries_sources_and_duplicate_identities(self):
        for date in ('2026-12-31', '2028-01-01'):
            p = copy.deepcopy(self.detail)
            p['items'][0]['payments'][0]['date'] = date
            self.assertEqual(self.run_case(p).payload['state'], 'blocked')
        p = copy.deepcopy(self.detail)
        p['items'][1]['payments'][0]['source_ref'] = p['items'][0]['payments'][0]['source_ref']
        self.assertIn('SYNTHETIC-other:payment_source_reused_no_split_profile', self.run_case(p).payload['blockers'])
        p['items'][0]['payments'][0]['source_ref'] = None
        self.assertEqual(self.run_case(p).payload['state'], 'blocked')
        p = copy.deepcopy(self.detail)
        p['items'][1]['payments'][0]['payment_id'] = p['items'][0]['payments'][0]['payment_id']
        with self.assertRaises(ValidationError): self.run_case(p)

    def test_strict_syntax_inventory_bounds_and_synthetic_only_context(self):
        for mutate in (lambda p:p.update(extra=True), lambda p:p['items'][0].update(expense_amount=120.0), lambda p:p['context'].update(deal_id='real-deal'), lambda p:p['assumptions'].update(noncash_expenses=0), lambda p:p['items'].append(copy.deepcopy(p['items'][0])), lambda p:p['items'][0]['payments'][0].update(date='2027-02-30'), lambda p:p.update(items=p['items']*66)):
            p = copy.deepcopy(self.detail)
            mutate(p)
            with self.assertRaises(ValidationError): self.run_case(p)
        for src in (b'{}', b'{"schema":1,"schema":2}', b'NaN', b'\xff', b' '*1_048_577):
            with self.assertRaises(ValidationError): parse_expense_cash_detail(src)

    def test_noncash_expense_needs_another_explicit_profile(self):
        c = json.loads(self.cr)
        c['amounts']['noncash_expense']['value'] = q(5)
        c['amounts']['operating_payments_claim']['value'] = q(435)
        c['amounts']['closing_free_cash_claim']['value'] = q(410)
        self.rebind_cash(c)
        self.assertEqual(self.c.payload['state'], 'reconciled_synthetic_plan')
        self.assertIn('noncash_expense_outside_reduced_profile', self.run_case().payload['blockers'])

    def test_underlying_cash_failure_is_not_repaired_by_matching_items(self):
        c = json.loads(self.cr)
        c['amounts']['closing_free_cash_claim']['value'] = q(999)
        self.rebind_cash(c)
        p = self.run_case().payload
        self.assertIn('upstream_NOI_or_cash_blocked', p['blockers'])
        self.assertTrue(p['upstream_cash_blockers'])
        self.assertIsNone(p['totals'])

    def test_rehashed_NOI_or_cash_proof_forgery_is_rejected(self):
        for which, field in [('noi', 'noi'), ('cash', 'expected_operating_payments')]:
            value = self.n if which == 'noi' else self.c
            p = value.payload
            p[field] = q(9999)
            encoded = canonical(p)
            fake = replace(value, payload_json=encoded, sha256=digest(encoded))
            with self.assertRaises(ValidationError):
                reconcile_expense_cash_detail(self.nr, fake if which == 'noi' else self.n, self.cr, fake if which == 'cash' else self.c, raw(self.detail))

    def test_arithmetic_budget_never_exports_partial_totals(self):
        with patch('miniuw_foundation.expense_cash_detail._bounded', side_effect=ArithmeticBudgetError('fault')):
            p = self.run_case().payload
        self.assertIn('exact_arithmetic_budget_exceeded', p['blockers'])
        self.assertIsNone(p['totals'])
        row = self.detail['items'][0]
        row['payments'] = [dict(payment_id='SYNTHETIC-'+str(i), date='2027-01-01', amount=q(F(1, 10**250+i)), source_ref='SYNTHETIC-unique-'+str(i)) for i in range(1, 24)]
        self.assertIn('exact_arithmetic_budget_exceeded', self.run_case().payload['blockers'])

    def test_immutable_payload_exact_sources_and_recovery_are_deterministic(self):
        before = raw(self.detail)
        run = self.run_case()
        p = run.payload
        p['items'].clear()
        self.assertEqual(len(run.payload['items']), 3)
        self.assertEqual(raw(self.detail), before)
        bundle = self.bundle(run)
        self.assertEqual(bundle, self.bundle())
        self.assertEqual(recover_expense_cash_bundle(bundle), run)
        sources = json.loads(bundle)['sources']
        self.assertEqual(sources['noi']['utf8'].encode(), self.nr)
        self.assertEqual(sources['cash']['utf8'].encode(), self.cr)

    def test_blocked_recovery_preserves_reasons_and_never_approves(self):
        self.detail['items'][0]['expense_amount'] = None
        run = self.run_case()
        self.assertEqual(recover_expense_cash_bundle(self.bundle(run)), run)
        self.assertEqual(run.payload['decision'], 'PENDING')
        for field in ('new_expense_or_payment_generated', 'bank_payment_history_verified', 'tax_or_insurance_policy_adopted', 'intraperiod_liquidity_verified', 'current_source_authority_verified', 'real_decisions_enabled', 'production_authorized'):
            self.assertIs(run.payload[field], False)

    def test_rehashed_result_and_changed_rehashed_source_cannot_forge_recovery(self):
        run = self.run_case()
        p = run.payload
        p['totals']['cash_payments'] = q(999)
        encoded = canonical(p)
        fake = replace(run, payload_json=encoded, sha256=digest(encoded))
        with self.assertRaises(ValidationError): self.bundle(fake)
        body = json.loads(self.bundle())
        body['result'] = dict(payload_json=encoded, sha256=digest(encoded))
        with self.assertRaises(ValidationError): recover_expense_cash_bundle(raw(body))
        body = json.loads(self.bundle())
        detail = json.loads(body['sources']['detail']['utf8'])
        detail['items'][0]['payments'][0]['amount'] = q(999)
        changed = raw(detail)
        body['sources']['detail'] = dict(utf8=changed.decode(), sha256=hashlib.sha256(changed).hexdigest())
        with self.assertRaises(ValidationError): recover_expense_cash_bundle(raw(body))

    def test_recovery_versions_missing_sources_and_source_hash_guards(self):
        for mutate in (lambda p:p.update(engine_sha256='0'*64), lambda p:p.update(definition_sha256='0'*64), lambda p:p['sources'].pop('cash'), lambda p:p['sources']['cash'].update(sha256='0'*64), lambda p:p['sources']['cash'].update(utf8=None), lambda p:p['result'].update(sha256='0'*64)):
            p = json.loads(self.bundle())
            mutate(p)
            with self.assertRaises(ValidationError): recover_expense_cash_bundle(raw(p))
        with self.assertRaises(ValidationError): recover_expense_cash_bundle(b' '*4_194_305)
