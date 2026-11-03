from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import copy
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from expense_lifecycle_demo_support import raw, q, refresh_detail, make_lifecycle, make_manifest, make_registry, AT
from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.expense_checked_lifecycle import (
    assemble_expense_checked_lifecycle, export_expense_checked_bundle, recover_expense_checked_bundle,
    parse_expense_lifecycle_manifest,
)
from miniuw_foundation.current_expense_lifecycle import assemble_current_expense_lifecycle, required_expense_lifecycle_sources
from miniuw_foundation.staged_lifecycle_bundle import recover_staged_lifecycle_bundle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency


class ExpenseCheckedLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lr = (ROOT/'templates/synthetic-expense-lifecycle-base.json').read_bytes()
        cls.manifest = json.loads((ROOT/'templates/synthetic-expense-lifecycle-manifest.json').read_bytes())
        cls.bundle = (ROOT/'templates/synthetic-expense-checked-lifecycle-bundle.json').read_bytes()
        cls.base = recover_staged_lifecycle_bundle(cls.lr)

    def run_case(self, p=None):
        return assemble_expense_checked_lifecycle(self.lr, raw(self.manifest if p is None else p))

    def test_full_history_return_and_independent_cash_identity(self):
        run = self.run_case()
        p = run.investor_run.payload
        self.assertEqual(run.payload['state'], 'compiled_synthetic_expense_checked_lifecycle')
        for k, v in [('gross_contributions', 1400), ('gross_distributions', 840), ('net_cash_profit', -560)]: self.assertEqual(p[k], q(v))
        self.assertEqual(p['equity_multiple'], q(F(3, 5)))
        self.assertEqual(p['normalized_story']['total_distributions'], q(6))
        self.assertEqual(p['cash_by_category']['operating_distribution'], q(200))
        self.assertEqual(p['cash_by_category']['net_sale_distribution'], q(640))
        self.assertEqual(1400+250+150+400, 1000+10+50+30+100+100+40+10+20+840)

    def test_no_second_expense_payment_or_equity_and_all_prior_sources_preserved(self):
        run = self.run_case()
        self.assertEqual(run.compiled_raw, self.base.run.compiled_raw)
        self.assertEqual(run.investor_run, self.base.run.investor_run)
        self.assertEqual(run.payload['cash_risk_run'], self.base.run.payload['cash_risk_run'])
        self.assertFalse(run.payload['additional_expense_payment_or_equity_generated'])
        self.assertEqual(run.investor_run.payload['cash_by_category']['net_refinance_distribution'], q(0))
        self.assertTrue(run.investor_run.payload['annual_irr_roots'])
        self.assertIsNone(run.investor_run.payload['selected_IRR'])
        self.assertEqual(len(run.investor_run.payload['events']), 8)

    def test_all_items_match_period_end_to_next_opening(self):
        p = self.run_case().payload
        self.assertEqual(len(p['item_continuity_checks']), 3)
        self.assertTrue(all(all(c[k] for k in ('same_economic_item', 'payables_match', 'prepaid_match')) for c in p['item_continuity_checks']))
        details = [json.loads(r['detail_run']['payload_json']) for r in p['periods']]
        self.assertEqual([d['totals']['expense_amount'] for d in details], [q(15), q(15)])
        self.assertEqual([d['totals']['cash_payments'] for d in details], [q(10), q(20)])
        self.assertEqual(details[0]['totals']['closing_payables'], details[1]['totals']['opening_payables'])

    def test_aggregate_balance_continuity_cannot_hide_changed_item_debt(self):
        def change(d):
            a, b = d['items'][:2]
            a['closing_payables'] = q(0)
            b['closing_payables'] = q(5)
            a['payments'][0]['amount'] = q(10)
            b['payments'][0]['amount'] = q(0)
        manifest = refresh_detail(self.lr, self.manifest, 0, change)
        self.assertEqual(json.loads(manifest['periods'][0]['detail_run']['payload_json'])['state'], 'matched_synthetic_expense_cash_detail')
        run = self.run_case(manifest)
        self.assertTrue(any('item_working_balance_discontinuity' in b for b in run.payload['blockers']))
        self.assertIsNone(run.compiled_raw)
        self.assertIsNone(run.investor_run)
        self.assertIsNotNone(self.base.run.investor_run)

    def test_reclassification_or_changed_item_inventory_requires_revision(self):
        for mutate in (lambda d:d['items'][0].update(kind='other_operating_expense'), lambda d:d['items'][0].update(item_id='SYNTHETIC-replacement')):
            manifest = refresh_detail(self.lr, self.manifest, 1, mutate)
            self.assertEqual(json.loads(manifest['periods'][1]['detail_run']['payload_json'])['state'], 'matched_synthetic_expense_cash_detail')
            self.assertEqual(self.run_case(manifest).payload['state'], 'blocked')

    def test_missing_extra_reordered_or_unknown_period_cannot_be_skipped(self):
        for mutate in (lambda m:m['periods'].pop(), lambda m:m['periods'].clear(), lambda m:m['periods'].reverse(), lambda m:m['periods'][0].update(period_ref='SYNTHETIC-unknown')):
            p = copy.deepcopy(self.manifest)
            mutate(p)
            run = self.run_case(p)
            self.assertIn('exact_ordered_operating_period_inventory_required', run.payload['blockers'])
            self.assertIsNone(run.compiled_raw)

    def test_per_period_expense_blocker_withdraws_full_return(self):
        manifest = refresh_detail(self.lr, self.manifest, 0, lambda d:d['items'][0]['payments'][0].update(amount=q(6)))
        p = self.run_case(manifest).payload
        self.assertIn('SYNTHETIC-hold-1:expense_detail_blocked', p['blockers'])
        self.assertIsNone(p['investor_run'])
        self.assertIsNone(p['cash_risk_run'])

    def test_payment_id_or_source_cannot_be_reused_across_periods(self):
        first = json.loads(self.manifest['periods'][0]['detail_source_utf8'])['items'][0]['payments'][0]
        for field in ('payment_id', 'source_ref'):
            p = refresh_detail(self.lr, self.manifest, 1, lambda d:d['items'][0]['payments'][0].update({field:first[field]}))
            self.assertEqual(json.loads(p['periods'][1]['detail_run']['payload_json'])['state'], 'matched_synthetic_expense_cash_detail')
            self.assertIn('SYNTHETIC-hold-2:payment_identity_or_source_reused_across_periods', self.run_case(p).payload['blockers'])

    def test_manifest_source_context_currency_and_basis_guards(self):
        for field, value in [('lifecycle_bundle_sha256', '0'*64), ('currency', 'EUR'), ('inventory_declared_complete', None), ('continuity_basis_ref', None), ('item_inventory_basis_ref', None)]:
            p = copy.deepcopy(self.manifest)
            p[field] = value
            self.assertIsNone(self.run_case(p).investor_run)
        p = copy.deepcopy(self.manifest)
        p['context']['run_id'] = 'SYNTHETIC-other'
        self.assertIsNone(self.run_case(p).investor_run)
        # Same mathematical bundle, different exact transport bytes still needs a new binding.
        self.assertIn('lifecycle_bundle_identity_mismatch', assemble_expense_checked_lifecycle(self.lr+b'\n', raw(self.manifest)).payload['blockers'])

    def test_rehashed_detail_proof_cannot_be_grafted(self):
        p = copy.deepcopy(self.manifest)
        d = json.loads(p['periods'][0]['detail_run']['payload_json'])
        d['totals']['cash_payments'] = q(999)
        encoded = canonical(d)
        p['periods'][0]['detail_run'] = dict(payload_json=encoded, sha256=digest(encoded))
        with self.assertRaises(ValidationError): self.run_case(p)
        p = copy.deepcopy(self.manifest)
        p['periods'][0]['detail_source_utf8'] += '\n'
        with self.assertRaises(ValidationError): self.run_case(p)

    def test_upstream_debt_blocker_survives_valid_expense_details_and_recovery(self):
        lr = make_lifecycle(terms_change=lambda t:t.update(principal=q(201)))
        m = raw(make_manifest(lr))
        run = assemble_expense_checked_lifecycle(lr, m)
        self.assertIn('underlying_staged_lifecycle_blocked', run.payload['blockers'])
        self.assertTrue(all(not r['blockers'] for r in run.payload['periods']))
        self.assertIsNone(run.compiled_raw)
        self.assertEqual(recover_expense_checked_bundle(export_expense_checked_bundle(lr, m, run)).run, run)

    def test_strict_manifest_and_source_budget(self):
        for mutate in (lambda p:p.update(schema='other'), lambda p:p.update(extra=True), lambda p:p.update(inventory_declared_complete=1), lambda p:p['context'].update(deal_id='live'), lambda p:p['periods'].append(copy.deepcopy(p['periods'][0])), lambda p:p['periods'][0].update(detail_source_utf8=None), lambda p:p.update(periods=p['periods']*65)):
            p = copy.deepcopy(self.manifest)
            mutate(p)
            with self.assertRaises(ValidationError): self.run_case(p)
        p = copy.deepcopy(self.manifest)
        p['periods'][0]['detail_source_utf8'] = '\ud800'
        with self.assertRaises(ValidationError): parse_expense_lifecycle_manifest(json.dumps(p, ensure_ascii=True).encode())
        for src in (b'{}', b'{"schema":1,"schema":2}', b'NaN', b'\xff', b' '*8_388_609):
            with self.assertRaises(ValidationError): parse_expense_lifecycle_manifest(src)

    def test_exact_deterministic_recovery_and_immutable_proof(self):
        run = self.run_case()
        bundle = export_expense_checked_bundle(self.lr, raw(self.manifest), run)
        self.assertEqual(bundle, self.bundle)
        recovered = recover_expense_checked_bundle(bundle)
        self.assertEqual(recovered.run, run)
        self.assertEqual(recovered.lifecycle_raw, self.lr)
        self.assertEqual(recovered.manifest_raw, raw(self.manifest))
        p = run.payload
        p['periods'].clear()
        self.assertEqual(len(run.payload['periods']), 2)

    def test_blocked_manifest_recovery_preserves_all_reasons(self):
        m = copy.deepcopy(self.manifest)
        m['continuity_basis_ref'] = None
        run = self.run_case(m)
        b = export_expense_checked_bundle(self.lr, raw(m), run)
        self.assertEqual(recover_expense_checked_bundle(b).run, run)
        self.assertIsNone(run.investor_run)
        self.assertEqual(run.payload['decision'], 'PENDING')
        self.assertIsNone(run.payload['personal_investor_return'])
        self.assertFalse(run.payload['production_authorized'])

    def test_rehashed_result_source_and_version_forgery_rejected(self):
        run = self.run_case()
        p = run.payload
        p['decision'] = 'PASS'
        encoded = canonical(p)
        fake = replace(run, payload_json=encoded, sha256=digest(encoded))
        with self.assertRaises(ValidationError): export_expense_checked_bundle(self.lr, raw(self.manifest), fake)
        for mutate in (lambda b:b.update(expected_run=dict(payload_json=encoded, sha256=digest(encoded))), lambda b:b['versions'].update(T76='0'*64), lambda b:b.update(lifecycle_source_utf8=b['lifecycle_source_utf8']+'\n'), lambda b:b.pop('manifest_source_utf8')):
            body = json.loads(self.bundle)
            mutate(body)
            with self.assertRaises(ValidationError): recover_expense_checked_bundle(raw(body))
        body = json.loads(self.bundle)
        m = json.loads(body['manifest_source_utf8'])
        m['continuity_basis_ref'] = None
        body['manifest_source_utf8'] = raw(m).decode()
        with self.assertRaises(ValidationError): recover_expense_checked_bundle(raw(body))


class CurrentExpenseLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = (ROOT/'templates/synthetic-expense-checked-lifecycle-bundle.json').read_bytes()
        cls.registry = json.loads((ROOT/'templates/synthetic-expense-lifecycle-evidence.json').read_bytes())

    def current(self, p=None, at=AT):
        rr = raw(self.registry if p is None else p)
        return assemble_current_expense_lifecycle(self.bundle, rr, evaluate_evidence_currency(rr, at), at)

    def test_full_source_current_story_and_expense_table_preserve_negative_return(self):
        run = self.current()
        p = run.payload
        self.assertEqual(len(p['required_source_bindings']), 26)
        s = p['current_project_return_story']
        self.assertEqual(s['gross_distributions'], q(840))
        self.assertEqual(s['net_cash_profit'], q(-560))
        self.assertEqual([r['totals']['cash_payments'] for r in p['current_expense_period_totals']], [q(10), q(20)])
        self.assertIn('Puente de gastos y pagos', p['markdown'])
        self.assertIn('-560.0000', p['markdown'])
        self.assertEqual(p['decision'], 'PENDING')
        self.assertIsNone(s['personal_investor_return'])
        self.assertIsNone(s['selected_IRR'])

    def test_expired_detail_manifest_original_loan_or_transport_withdraw_all_numbers(self):
        for path in ('/expense/manifest', '/expense/periods/0/detail', '/expense/periods/1/detail', '/construction/loans/0', '/transition/phase_contract', '/transport/expense_checked_bundle', '/investor/source'):
            p = copy.deepcopy(self.registry)
            next(e for e in p['evidence'] if e['requirement_id'] == path)['valid_until'] = AT
            result = self.current(p).payload
            self.assertIsNone(result['current_project_return_story'])
            self.assertIsNone(result['current_expense_period_totals'])
            self.assertNotIn('-560.0000', result['markdown'])
            self.assertNotIn('840.0000', result['markdown'])
            self.assertTrue(result['historical_calculation_preserved'])
        self.assertEqual(recover_expense_checked_bundle(self.bundle).run.investor_run.payload['gross_distributions'], q(840))

    def test_only_old_current_inventory_cannot_substitute_for_new_expense_sources(self):
        p = copy.deepcopy(self.registry)
        p['requirements'] = [r for r in p['requirements'] if not r['requirement_id'].startswith('/expense/') and r['requirement_id'] != '/transport/expense_checked_bundle']
        ids = {r['requirement_id'] for r in p['requirements']}
        p['evidence'] = [e for e in p['evidence'] if e['requirement_id'] in ids]
        rr = raw(p)
        proof = evaluate_evidence_currency(rr, AT)
        self.assertEqual(proof.payload['state'], 'current_synthetic_evidence')
        self.assertIn('complete_expense_lifecycle_source_inventory_mismatch', self.current(p).payload['blockers'])

    def test_rehashed_inventory_context_and_pending_review_cannot_make_current(self):
        for field, value in [('source_sha256', '0'*64), ('source_locator', '/wrong')]:
            p = copy.deepcopy(self.registry)
            p['requirements'][-1][field] = value
            p['evidence'][-1][field] = value
            self.assertIn('complete_expense_lifecycle_source_inventory_mismatch', self.current(p).payload['blockers'])
        for field, value in [('review_status', 'pending'), ('value_status', 'estimate'), ('superseded_by_sha256', '1'*64)]:
            p = copy.deepcopy(self.registry)
            p['evidence'][-1][field] = value
            self.assertIsNone(self.current(p).payload['current_project_return_story'])
        p = copy.deepcopy(self.registry)
        p['context']['run_id'] = 'SYNTHETIC-other'
        self.assertIn('expense_lifecycle_evidence_context_mismatch', self.current(p).payload['blockers'])

    def test_wrong_evaluation_time_or_rehashed_registry_proof_rejected(self):
        rr = raw(self.registry)
        run = evaluate_evidence_currency(rr, AT)
        with self.assertRaises(ValidationError): assemble_current_expense_lifecycle(self.bundle, rr, run, '2027-07-01T12:00:01Z')
        p = run.payload
        p['blockers'].append('fake')
        encoded = canonical(p)
        with self.assertRaises(ValidationError): assemble_current_expense_lifecycle(self.bundle, rr, replace(run, payload_json=encoded, sha256=digest(encoded)), AT)

    def test_fresh_sources_do_not_repair_calculation_blocker(self):
        rec = recover_expense_checked_bundle(self.bundle)
        m = json.loads(rec.manifest_raw)
        m['continuity_basis_ref'] = None
        run = assemble_expense_checked_lifecycle(rec.lifecycle_raw, raw(m))
        bundle = export_expense_checked_bundle(rec.lifecycle_raw, raw(m), run)
        rr = raw(make_registry(bundle))
        currency = evaluate_evidence_currency(rr, AT)
        self.assertEqual(currency.payload['state'], 'current_synthetic_evidence')
        p = assemble_current_expense_lifecycle(bundle, rr, currency, AT).payload
        self.assertIn('expense_lifecycle_calculation_blocked', p['blockers'])
        self.assertIsNone(p['current_project_return_story'])

    def test_current_proof_is_repeatable_isolated_and_never_real_approval(self):
        run = self.current()
        self.assertEqual(run, self.current())
        p = run.payload
        p['current_project_return_story']['gross_distributions'] = q(999)
        self.assertEqual(run.payload['current_project_return_story']['gross_distributions'], q(840))
        for key in ('live_expiry_monitor_enabled', 'real_sources_payments_or_professional_approval_authenticated', 'financial_publication_authorized', 'external_decision_pdf_produced', 'real_decisions_enabled', 'production_authorized'):
            self.assertIs(run.payload[key], False)
        rec = recover_expense_checked_bundle(self.bundle)
        self.assertEqual(len(required_expense_lifecycle_sources(rec, self.bundle)), 26)
