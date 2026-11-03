from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import copy
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from rental_lifecycle_demo_support import raw, q, refresh_calendar, change_month, make_registry, AT
from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.rental_checked_lifecycle import assemble_rental_checked_lifecycle, export_rental_checked_bundle, recover_rental_checked_bundle, parse_rental_lifecycle_manifest
from miniuw_foundation.current_rental_lifecycle import assemble_current_rental_lifecycle, required_rental_lifecycle_sources
from miniuw_foundation.expense_checked_lifecycle import recover_expense_checked_bundle, assemble_expense_checked_lifecycle, export_expense_checked_bundle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency


class RentalCheckedLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.er = (ROOT/'templates/synthetic-rental-expense-base.json').read_bytes()
        cls.manifest = json.loads((ROOT/'templates/synthetic-rental-lifecycle-manifest.json').read_bytes())
        cls.bundle = (ROOT/'templates/synthetic-rental-checked-lifecycle-bundle.json').read_bytes()

    def run_case(self, p=None):
        return assemble_rental_checked_lifecycle(self.er, raw(self.manifest if p is None else p))

    def test_full_cash_return_hand_totals_from_monthly_rent(self):
        run = self.run_case()
        p = run.investor_run.payload
        for k, v in [('gross_contributions', 1400), ('gross_distributions', 775), ('net_cash_profit', -625)]: self.assertEqual(p[k], q(v))
        self.assertEqual(p['equity_multiple'], q(F(31,56)))
        self.assertEqual(p['normalized_story']['total_distributions'], q(F(155,28)))
        self.assertEqual(p['cash_by_category']['operating_distribution'], q(200))
        self.assertEqual(p['cash_by_category']['net_sale_distribution'], q(575))
        self.assertEqual([json.loads(r['calendar_run']['payload_json'])['totals']['effective_rent'] for r in run.payload['periods']], [q(25), q(60)])
        self.assertEqual(1400+250+85+400, 1000+10+50+30+100+100+40+10+20+775)

    def test_exact_existing_ledger_reused_without_second_rent_or_expense(self):
        run = self.run_case()
        old = recover_expense_checked_bundle(self.er).run
        self.assertEqual(run.compiled_raw, old.compiled_raw)
        self.assertEqual(run.investor_run, old.investor_run)
        self.assertEqual(run.payload['cash_risk_run'], old.payload['cash_risk_run'])
        self.assertFalse(run.payload['rental_income_counted_as_additional_equity_receipt'])
        self.assertFalse(run.payload['new_funding_or_distribution_generated'])
        self.assertIsNone(run.payload['personal_investor_return'])
        self.assertIsNone(run.investor_run.payload['selected_IRR'])
        self.assertTrue(run.investor_run.payload['annual_irr_roots'])

    def test_valid_changed_monthly_rent_cannot_patch_existing_NOI_or_return(self):
        m = refresh_calendar(self.manifest, 0, lambda c:change_month(c, 2, lambda s:s['residential_groups'][0].update(rent=q(3))))
        self.assertEqual(json.loads(m['periods'][0]['calendar_run']['payload_json'])['state'], 'computed_synthetic_monthly_rental_calendar')
        run = self.run_case(m)
        self.assertIn('SYNTHETIC-hold-1:rental_income_does_not_equal_exact_NOI_row', run.payload['blockers'])
        self.assertIsNone(run.investor_run)
        self.assertEqual(recover_expense_checked_bundle(self.er).run.investor_run.payload['gross_distributions'], q(775))

    def test_missing_month_or_period_cannot_be_ignored(self):
        m = refresh_calendar(self.manifest, 0, lambda c:c['months'].pop(0))
        self.assertIn('SYNTHETIC-hold-1:monthly_rental_calendar_blocked', self.run_case(m).payload['blockers'])
        for mutate in (lambda p:p['periods'].pop(), lambda p:p['periods'].clear(), lambda p:p['periods'].reverse(), lambda p:p['periods'][0].update(period_ref='SYNTHETIC-unknown')):
            p = copy.deepcopy(self.manifest)
            mutate(p)
            self.assertIn('exact_ordered_rental_period_inventory_required', self.run_case(p).payload['blockers'])
            self.assertIsNone(self.run_case(p).compiled_raw)

    def test_same_rent_total_does_not_allow_changed_physical_inventory(self):
        def change(c):
            for i in range(3): change_month(c, i, lambda s:s['residential_groups'][0].update(units=q(20), rent=q(1)))
        m = refresh_calendar(self.manifest, 1, change)
        r = json.loads(m['periods'][1]['calendar_run']['payload_json'])
        self.assertEqual(r['state'], 'computed_synthetic_monthly_rental_calendar')
        self.assertEqual(r['totals']['effective_rent'], q(60))
        self.assertIn('SYNTHETIC-hold-2:physical_group_or_rental_income_identity_changed_between_periods', self.run_case(m).payload['blockers'])

    def test_exact_income_target_and_explicit_other_zero_inventory(self):
        for field, value in [('rental_income_item_id', 'SYNTHETIC-absent'), ('other_zero_income_item_ids', [])]:
            p = copy.deepcopy(self.manifest)
            p['periods'][0][field] = value
            self.assertIsNone(self.run_case(p).investor_run)
        p = copy.deepcopy(self.manifest)
        row = p['periods'][0]
        row['rental_income_item_id'], row['other_zero_income_item_ids'] = row['other_zero_income_item_ids'][0], [row['rental_income_item_id']]
        self.assertIn('SYNTHETIC-hold-1:nonresidential_income_requires_other_profile', self.run_case(p).payload['blockers'])

    def test_source_context_currency_scope_and_date_binding_guards(self):
        for field, value in [('expense_bundle_sha256', '0'*64), ('currency', 'EUR'), ('inventory_declared_complete', None), ('rental_scope_and_no_overlap_basis_ref', None), ('period_recognition_basis_ref', None)]:
            p = copy.deepcopy(self.manifest)
            p[field] = value
            self.assertIsNone(self.run_case(p).investor_run)
        for field in ('noi_source_sha256', 'cash_source_sha256'):
            p = copy.deepcopy(self.manifest)
            p['periods'][0][field] = '0'*64
            self.assertIsNone(self.run_case(p).investor_run)
        m = refresh_calendar(self.manifest, 0, lambda c:c.update(start_date='2027-01-02'))
        self.assertIn('SYNTHETIC-hold-1:start_date_mismatch', self.run_case(m).payload['blockers'])
        p = copy.deepcopy(self.manifest)
        p['context']['run_id'] = 'SYNTHETIC-other'
        self.assertIsNone(self.run_case(p).investor_run)

    def test_expense_blocker_survives_correct_monthly_rental_and_recovery(self):
        rec = recover_expense_checked_bundle(self.er)
        m = json.loads(rec.manifest_raw)
        m['continuity_basis_ref'] = None
        mr = raw(m)
        er = export_expense_checked_bundle(rec.lifecycle_raw, mr, assemble_expense_checked_lifecycle(rec.lifecycle_raw, mr))
        p = copy.deepcopy(self.manifest)
        import hashlib
        p['expense_bundle_sha256'] = hashlib.sha256(er).hexdigest()
        mr = raw(p)
        run = assemble_rental_checked_lifecycle(er, mr)
        self.assertIn('expense_checked_lifecycle_blocked', run.payload['blockers'])
        self.assertTrue(all(not e['blockers'] for e in run.payload['periods']))
        self.assertIsNone(run.investor_run)
        self.assertEqual(recover_rental_checked_bundle(export_rental_checked_bundle(er, mr, run)).run, run)

    def test_rehashed_calendar_proof_and_changed_exact_source_are_rejected(self):
        p = copy.deepcopy(self.manifest)
        r = json.loads(p['periods'][0]['calendar_run']['payload_json'])
        r['totals']['effective_rent'] = q(999)
        encoded = canonical(r)
        p['periods'][0]['calendar_run'] = dict(payload_json=encoded, sha256=digest(encoded))
        with self.assertRaises(ValidationError): self.run_case(p)
        p = copy.deepcopy(self.manifest)
        p['periods'][0]['calendar_source_utf8'] += '\n'
        with self.assertRaises(ValidationError): self.run_case(p)

    def test_portable_deterministic_replay_and_forged_result_source_versions(self):
        run = self.run_case()
        self.assertEqual(export_rental_checked_bundle(self.er, raw(self.manifest), run), self.bundle)
        rec = recover_rental_checked_bundle(self.bundle)
        self.assertEqual(rec.run, run)
        self.assertEqual(rec.expense_raw, self.er)
        body = run.payload
        body['decision'] = 'PASS'
        encoded = canonical(body)
        fake = replace(run, payload_json=encoded, sha256=digest(encoded))
        with self.assertRaises(ValidationError): export_rental_checked_bundle(self.er, raw(self.manifest), fake)
        for mutate in (lambda p:p.update(expected_run=dict(payload_json=encoded, sha256=digest(encoded))), lambda p:p['versions'].update(T79='0'*64), lambda p:p.update(expense_bundle_utf8=p['expense_bundle_utf8']+'\n'), lambda p:p.pop('rental_manifest_utf8')):
            p = json.loads(self.bundle)
            mutate(p)
            with self.assertRaises(ValidationError): recover_rental_checked_bundle(raw(p))
        p = json.loads(self.bundle)
        m = json.loads(p['rental_manifest_utf8'])
        m['period_recognition_basis_ref'] = None
        p['rental_manifest_utf8'] = raw(m).decode()
        with self.assertRaises(ValidationError): recover_rental_checked_bundle(raw(p))

    def test_strict_manifest_and_immutable_pending_scope(self):
        for mutate in (lambda p:p.update(extra=True), lambda p:p.update(inventory_declared_complete=1), lambda p:p['context'].update(deal_id='live'), lambda p:p['periods'].append(copy.deepcopy(p['periods'][0])), lambda p:p['periods'][0].update(calendar_source_utf8=None), lambda p:p['periods'][0]['other_zero_income_item_ids'].append(p['periods'][0]['other_zero_income_item_ids'][0])):
            p = copy.deepcopy(self.manifest)
            mutate(p)
            with self.assertRaises(ValidationError): self.run_case(p)
        for b in (b'{}', b'{"schema":1,"schema":2}', b'NaN', b'\xff', b' '*8_388_609):
            with self.assertRaises(ValidationError): parse_rental_lifecycle_manifest(b)
        run = self.run_case()
        p = run.payload
        p['periods'].clear()
        self.assertEqual(len(run.payload['periods']), 2)
        self.assertEqual(run.payload['decision'], 'PENDING')
        self.assertFalse(run.payload['production_authorized'])


class CurrentRentalLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = (ROOT/'templates/synthetic-rental-checked-lifecycle-bundle.json').read_bytes()
        cls.registry = json.loads((ROOT/'templates/synthetic-rental-lifecycle-evidence.json').read_bytes())

    def current(self, p=None):
        rr = raw(self.registry if p is None else p)
        return assemble_current_rental_lifecycle(self.bundle, rr, evaluate_evidence_currency(rr, AT), AT)

    def test_complete_current_return_months_and_existing_expense_bridge(self):
        r = self.current().payload
        self.assertEqual(len(r['required_source_bindings']), 36)
        self.assertEqual(r['current_project_return_story']['gross_distributions'], q(775))
        self.assertEqual(r['current_project_return_story']['net_cash_profit'], q(-625))
        self.assertEqual([m['amounts']['effective_rent'] for m in r['current_rental_months']], [q(v) for v in [0,10,15,20,20,20]])
        self.assertEqual([e['totals']['cash_payments'] for e in r['current_expense_period_totals']], [q(10),q(20)])
        self.assertIn('Renta mensual declarada', r['markdown'])
        self.assertIn('-625.0000', r['markdown'])
        self.assertEqual(r['decision'], 'PENDING')

    def test_expired_month_calendar_old_expense_or_loan_withdraws_all_current_numbers(self):
        for path in ('/rental/periods/0/months/0', '/rental/periods/1/months/2', '/rental/periods/0/calendar', '/rental/manifest', '/expense/periods/0/detail', '/construction/loans/0', '/transport/rental_checked_bundle'):
            p = copy.deepcopy(self.registry)
            next(e for e in p['evidence'] if e['requirement_id'] == path)['valid_until'] = AT
            r = self.current(p).payload
            for k in ('current_project_return_story', 'current_rental_months', 'current_expense_period_totals'): self.assertIsNone(r[k])
            self.assertNotIn('-625.0000', r['markdown'])
            self.assertNotIn('775.0000', r['markdown'])
            self.assertTrue(r['historical_calculation_preserved'])
        self.assertEqual(recover_rental_checked_bundle(self.bundle).run.investor_run.payload['gross_distributions'], q(775))

    def test_current_old_inventory_cannot_replace_missing_monthly_source(self):
        p = copy.deepcopy(self.registry)
        path = '/rental/periods/0/months/0'
        p['requirements'] = [r for r in p['requirements'] if r['requirement_id'] != path]
        p['evidence'] = [e for e in p['evidence'] if e['requirement_id'] != path]
        self.assertEqual(evaluate_evidence_currency(raw(p), AT).payload['state'], 'current_synthetic_evidence')
        self.assertIn('complete_rental_lifecycle_source_inventory_mismatch', self.current(p).payload['blockers'])

    def test_altered_hash_locator_and_context_cannot_make_view_current(self):
        for field, value in [('source_sha256','0'*64), ('source_locator','/wrong')]:
            p = copy.deepcopy(self.registry)
            p['requirements'][-1][field] = value
            p['evidence'][-1][field] = value
            self.assertIn('complete_rental_lifecycle_source_inventory_mismatch', self.current(p).payload['blockers'])
        p = copy.deepcopy(self.registry)
        p['context']['run_id'] = 'SYNTHETIC-other'
        self.assertIsNone(self.current(p).payload['current_project_return_story'])

    def test_pending_estimated_superseded_month_remains_pending(self):
        for field, value in [('review_status','pending'), ('value_status','estimate'), ('superseded_by_sha256','1'*64)]:
            p = copy.deepcopy(self.registry)
            p['evidence'][-1][field] = value
            self.assertIsNone(self.current(p).payload['current_rental_months'])

    def test_current_evidence_cannot_repair_incompatible_rental_NOI(self):
        rec = recover_rental_checked_bundle(self.bundle)
        m = refresh_calendar(json.loads(rec.manifest_raw), 0, lambda c:change_month(c, 2, lambda s:s['residential_groups'][0].update(rent=q(3))))
        mr = raw(m)
        run = assemble_rental_checked_lifecycle(rec.expense_raw, mr)
        b = export_rental_checked_bundle(rec.expense_raw, mr, run)
        rr = raw(make_registry(b))
        currency = evaluate_evidence_currency(rr, AT)
        self.assertEqual(currency.payload['state'], 'current_synthetic_evidence')
        r = assemble_current_rental_lifecycle(b, rr, currency, AT).payload
        self.assertIn('rental_lifecycle_calculation_blocked', r['blockers'])
        self.assertIsNone(r['current_project_return_story'])

    def test_exact_time_forged_registry_and_immutable_unverified_flags(self):
        rr = raw(self.registry)
        currency = evaluate_evidence_currency(rr, AT)
        with self.assertRaises(ValidationError): assemble_current_rental_lifecycle(self.bundle, rr, currency, '2027-07-01T12:00:01Z')
        p = currency.payload
        p['blockers'].append('forged')
        encoded = canonical(p)
        with self.assertRaises(ValidationError): assemble_current_rental_lifecycle(self.bundle, rr, replace(currency,payload_json=encoded,sha256=digest(encoded)), AT)
        run = self.current()
        self.assertEqual(run, self.current())
        p = run.payload
        p['current_rental_months'].clear()
        self.assertEqual(len(run.payload['current_rental_months']), 6)
        for k in ('live_expiry_monitor_enabled', 'actual_rental_contract_collection_or_review_authenticated', 'financial_publication_authorized', 'external_decision_pdf_produced', 'real_decisions_enabled', 'production_authorized'):
            self.assertIs(run.payload[k], False)
        self.assertEqual(len(required_rental_lifecycle_sources(recover_rental_checked_bundle(self.bundle), self.bundle)), 36)
