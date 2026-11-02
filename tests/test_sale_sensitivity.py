import copy
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.sale_sensitivity import (compare_sale_receipts, parse_sale_sensitivity,
    verify_sale_sensitivity, SaleSensitivityRun)
from miniuw_foundation.operating_noi import ArithmeticBudgetError, _bounded

ROOT = Path(__file__).resolve().parents[1]


def f(value):
    return F(int(value['numerator']), int(value['denominator']))


class SaleSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT/'templates/synthetic-investor-returns.json').read_bytes()
        self.base = json.loads(self.raw)
        self.spec = json.loads((ROOT/'templates/synthetic-sale-receipt-sensitivity.json').read_bytes())
        self.run = produce_investor_returns(self.raw)

    def rebind(self):
        self.raw = canonical(self.base).encode()
        self.run = produce_investor_returns(self.raw)
        self.spec.update(base_source_sha256=hashlib.sha256(self.raw).hexdigest(),
            base_run_sha256=self.run.sha256, context=copy.deepcopy(self.base['context']))

    def report(self):
        return compare_sale_receipts(self.raw, self.run, canonical(self.spec).encode())

    def test_independent_cash_and_multiple_recomputation(self):
        p = self.report().payload
        self.assertTrue(p['all_declared_cases_computable'])
        self.assertEqual(f(p['conditional_cash_recovery_net_sale_receipt_floor']), 300)
        self.assertTrue(p['EM_ge_one_equivalence_defined'])
        for row, receipt in zip(p['cases'], [0, 300, 600]):
            out = row['outputs']; m = out['cash_metrics']
            self.assertEqual(f(m['gross_contributions']), 1000)
            self.assertEqual(f(m['gross_distributions']), 700+receipt)
            self.assertEqual(f(m['net_cash_profit']), receipt-300)
            self.assertEqual(f(out['equity_multiple']), F(700+receipt, 1000))
            self.assertEqual(f(out['net_cash_profit_change_from_base']), receipt-900)

    def test_break_even_case_exactly_recovers_cash_without_pass(self):
        row = self.report().payload['cases'][1]
        self.assertEqual(f(row['outputs']['equity_multiple']), 1)
        self.assertEqual(f(row['outputs']['cash_metrics']['net_cash_profit']), 0)
        self.assertEqual(row['decision'], 'PENDING')
        root = row['outputs']['annual_irr_roots'][0]
        if root['exact_annual_rate'] is not None:
            self.assertEqual(f(root['exact_annual_rate']), 0)
        else:
            self.assertLessEqual(f(root['annual_rate_interval']['lower']), 0)
            self.assertGreaterEqual(f(root['annual_rate_interval']['upper']), 0)

    def test_target_is_one_of_multiple_sales_not_all_sales(self):
        extra = dict(self.base['events'][-1], event_id='earlier-sale', amount=q(F(150)), date='2028-01-01')
        self.base['events'].append(extra); self.rebind()
        p = self.report().payload
        self.assertEqual(f(p['conditional_cash_recovery_net_sale_receipt_floor']), 150)
        m = p['cases'][0]['outputs']['cash_metrics']
        self.assertEqual(f(m['net_sale_distribution']), 150)
        self.assertEqual(f(m['gross_distributions']), 850)

    def test_already_recovered_floor_zero_does_not_imply_em_exactly_one(self):
        self.base['events'][1]['amount'] = q(F(1500)); self.rebind()
        p = self.report().payload
        self.assertEqual(f(p['conditional_cash_recovery_net_sale_receipt_floor']), 0)
        self.assertGreater(f(p['cases'][0]['outputs']['equity_multiple']), 1)

    def test_zero_contributions_does_not_invent_em(self):
        self.base['events'][0]['amount'] = q(F(0)); self.rebind()
        p = self.report().payload
        self.assertFalse(p['EM_ge_one_equivalence_defined'])
        self.assertEqual(f(p['conditional_cash_recovery_net_sale_receipt_floor']), 0)
        self.assertIsNone(p['cases'][0]['outputs']['equity_multiple'])
        self.assertTrue(p['cases'][0]['outputs']['upstream_story_blockers'])

    def test_missing_case_preserved_with_valid_siblings(self):
        self.spec['cases'][1]['net_sale_distribution'] = None
        p = self.report().payload
        self.assertFalse(p['all_declared_cases_computable'])
        self.assertEqual([r['state'] for r in p['cases']], ['computed_synthetic', 'blocked', 'computed_synthetic'])
        self.assertIsNone(p['cases'][1]['compiled_investor_json'])
        self.assertIsNone(p['cases'][1]['outputs'])
        self.assertIsNone(p['cases'][1]['case_claim']['net_sale_distribution'])

    def test_negative_receipt_not_clipped_or_converted_to_contribution(self):
        self.spec['cases'][0]['net_sale_distribution'] = q(F(-1))
        row = self.report().payload['cases'][0]
        self.assertEqual(row['state'], 'blocked')
        self.assertIsNone(row['outputs'])
        self.assertEqual(f(row['case_claim']['net_sale_distribution']), -1)

    def test_currency_date_and_source_must_be_explicit_and_match(self):
        original = copy.deepcopy(self.spec)
        for key, value in [('currency', None), ('currency', 'EUR'), ('date', None),
                           ('date', '2028-01-01'), ('source_ref', None)]:
            with self.subTest(key=key, value=value):
                self.spec = copy.deepcopy(original); self.spec['cases'][0][key] = value
                row = self.report().payload['cases'][0]
                self.assertEqual(row['state'], 'blocked'); self.assertIsNone(row['outputs'])

    def test_global_context_hash_and_assumption_failures_block_all(self):
        original = copy.deepcopy(self.spec)
        for key, value in [('base_source_sha256', '0'*64), ('base_run_sha256', '0'*64),
                           ('frozen_cash_assumption_ref', None), ('case_inventory_declared_complete', False)]:
            with self.subTest(key=key):
                self.spec = copy.deepcopy(original); self.spec[key] = value
                p = self.report().payload
                self.assertTrue(p['blockers']); self.assertFalse(p['all_declared_cases_computable'])
                self.assertTrue(all(r['outputs'] is None for r in p['cases']))
        self.spec = copy.deepcopy(original); self.spec['context']['scenario_id'] += '-wrong'
        self.assertIn('context_mismatch', self.report().payload['blockers'])

    def test_unknown_or_wrong_kind_target_blocks(self):
        for target in ['unknown', 'initial', 'op1']:
            self.spec['target_event_id'] = target
            p = self.report().payload
            self.assertIn('target_not_an_explicit_net_sale_distribution', p['blockers'])
            self.assertIsNone(p['conditional_cash_recovery_net_sale_receipt_floor'])

    def test_base_cash_blocker_not_repaired_by_replacing_sale(self):
        self.base['events'][-1]['amount'] = None; self.rebind()
        p = self.report().payload
        self.assertIn('base_cash_metrics_blocked', p['blockers'])
        self.assertTrue(all(r['outputs'] is None for r in p['cases']))

    def test_frozen_other_events_stocks_dates_and_original_unchanged(self):
        before = copy.deepcopy(self.base); raw = self.raw; saved_run = self.run.payload_json
        for row in self.report().payload['cases']:
            compiled = json.loads(row['compiled_investor_json'])
            changed = [(i, k) for i, event in enumerate(before['events']) for k in event
                       if event[k] != compiled['events'][i][k]]
            self.assertEqual(changed, [(4, 'amount'), (4, 'source_ref')])
            for key in ['capital_snapshots', 'annual_cash_bases', 'grid', 'normalization', 'irr_parameters']:
                self.assertEqual(compiled[key], before[key])
        self.assertEqual(self.raw, raw); self.assertEqual(self.base, before)
        self.assertEqual(self.run.payload_json, saved_run)

    def test_case_identifiers_distinct_from_base(self):
        for key in ['scenario_id', 'run_id']:
            self.spec['cases'][0][key] = self.base['context'][key]
            self.assertEqual(self.report().payload['cases'][0]['state'], 'blocked')

    def test_duplicate_ids_and_bounded_inventory_rejected(self):
        original = copy.deepcopy(self.spec)
        for key in ['case_id', 'scenario_id', 'run_id']:
            self.spec = copy.deepcopy(original); self.spec['cases'][1][key] = self.spec['cases'][0][key]
            with self.assertRaises(ValidationError): self.report()
        self.spec = copy.deepcopy(original); self.spec['cases'] = []
        with self.assertRaises(ValidationError): self.report()
        self.spec['cases'] = [original['cases'][0]]*13
        with self.assertRaises(ValidationError): self.report()

    def test_strict_shape_literal_numbers_and_duplicate_json_keys(self):
        for raw in [b'{"schema":1,"schema":2}', b'NaN', b'[]', b'\xff', b' '*131073]:
            with self.assertRaises(ValidationError): parse_sale_sensitivity(raw)
        self.spec['cases'][0]['net_sale_distribution'] = 12.5
        with self.assertRaises(ValidationError): self.report()
        self.spec['cases'][0]['net_sale_distribution'] = q(F(0)); self.spec['exit_cap'] = 'invented'
        with self.assertRaises(ValidationError): self.report()

    def test_rehashed_base_forgery_and_stale_source_rejected(self):
        bad = self.run.payload; bad['gross_distributions'] = q(F(99999)); text = canonical(bad)
        with self.assertRaises(ValidationError):
            compare_sale_receipts(self.raw, replace(self.run, payload_json=text, sha256=digest(text)), canonical(self.spec).encode())
        changed = copy.deepcopy(self.base); changed['events'][0]['amount'] = q(F(2))
        with self.assertRaises(ValidationError):
            compare_sale_receipts(canonical(changed).encode(), self.run, canonical(self.spec).encode())

    def test_result_replay_rejects_updated_hash_forgery(self):
        run = self.report(); spec_raw = canonical(self.spec).encode()
        self.assertEqual(verify_sale_sensitivity(self.raw, self.run, spec_raw, run), run)
        bad = run.payload; bad['cases'][0]['outputs']['equity_multiple'] = q(F(9)); text = canonical(bad)
        with self.assertRaises(ValidationError):
            verify_sale_sensitivity(self.raw, self.run, spec_raw, SaleSensitivityRun(text, digest(text)))
        with self.assertRaises(ValidationError):
            verify_sale_sensitivity(self.raw, self.run, spec_raw, replace(run, sha256='0'*64))

    def test_changed_spec_invalidates_saved_report(self):
        run = self.report(); self.spec['cases'][0]['net_sale_distribution'] = q(F(1))
        with self.assertRaises(ValidationError):
            verify_sale_sensitivity(self.raw, self.run, canonical(self.spec).encode(), run)

    def test_global_arithmetic_budget_failure_no_partial_threshold(self):
        with patch('miniuw_foundation.sale_sensitivity._bounded', side_effect=ArithmeticBudgetError):
            p = self.report().payload
        self.assertIsNone(p['conditional_cash_recovery_net_sale_receipt_floor'])
        self.assertIn('sensitivity_exact_arithmetic_budget_exceeded', p['blockers'])
        self.assertTrue(all(r['outputs'] is None for r in p['cases']))

    def test_case_arithmetic_budget_failure_removes_partial_output(self):
        calls = []
        def limit(value):
            calls.append(value)
            if len(calls) == 3: raise ArithmeticBudgetError()
            return _bounded(value)
        with patch('miniuw_foundation.sale_sensitivity._bounded', side_effect=limit):
            p = self.report().payload
        self.assertEqual(p['cases'][0]['state'], 'blocked')
        self.assertIsNone(p['cases'][0]['outputs']); self.assertIsNone(p['cases'][0]['compiled_investor_json'])
        self.assertEqual(p['cases'][1]['state'], 'computed_synthetic')

    def test_zero_sale_recomputes_irr_not_copies_base_rate(self):
        roots = self.report().payload['cases'][0]['outputs']['annual_irr_roots']
        self.assertNotEqual(roots, self.run.payload['annual_irr_roots'])
        interval = roots[0]['annual_rate_interval']
        self.assertLess(f(interval['upper']), 0)

    def test_multiple_irr_roots_retained_without_selected_rate(self):
        # -100, +230, -132 has roots 10% and 20%; target zero sale kept explicit.
        self.base['events'] = [dict(event_id=eid, date=day, kind=kind, category=category,
            amount=q(F(amount)), currency='USD', source_ref='SYNTHETIC-multiple-IRR') for eid, day, kind, category, amount in [
            ('initial', '2027-01-01', 'contribution', 'initial_capital', 100),
            ('positive', '2028-01-01', 'distribution', 'other_distribution', 230),
            ('negative', '2029-01-01', 'contribution', 'additional_capital', 132),
            ('sale', '2029-01-01', 'distribution', 'net_sale_distribution', 0)]]
        self.rebind(); out = self.report().payload['cases'][0]['outputs']
        self.assertEqual(out['periodic_irr']['distinct_positive_discount_roots'], 2)
        self.assertEqual(len(out['annual_irr_roots']), 2); self.assertIsNone(out['selected_IRR'])
        self.assertIn('IRR_requires_unique_complete_root_or_explicit_resolution', out['upstream_story_blockers'])

    def test_isolated_analysis_never_claims_full_scenario_or_investor_return(self):
        p = self.report().payload
        self.assertEqual(p['decision'], 'PENDING')
        for key in ['project_scenario_recomputed', 'bank_capacity_checked', 'cash_and_closing_producer_link_preserved',
                    'original_source_modified', 'downside_policy_adopted', 'risk_analysis_completed',
                    'real_decisions_enabled', 'production_authorized']:
            self.assertIs(p[key], False)
        for key in ['gross_sale_price_break_even', 'exit_cap_break_even', 'personal_investor_return', 'final_economic_capital_loss']:
            self.assertIsNone(p[key])


if __name__ == '__main__':
    unittest.main()
