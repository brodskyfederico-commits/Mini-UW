import copy
from dataclasses import replace
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from miniuw_foundation.cash_risk import summarize_cash_risk, verify_cash_risk, CashRiskRun
from miniuw_foundation.drafts import canonical, digest, ValidationError
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.operating_noi import ArithmeticBudgetError

ROOT = Path(__file__).resolve().parents[1]


def f(value):
    return F(int(value['numerator']), int(value['denominator']))


class CashRiskTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT / 'templates/synthetic-investor-returns.json').read_bytes())

    def run_case(self):
        raw = canonical(self.case).encode()
        upstream = produce_investor_returns(raw)
        return summarize_cash_risk(raw, upstream).payload

    def ledger(self, events):
        self.case['events'] = [dict(event_id=str(i), date=self.case['grid']['dates'][date],
            kind=kind, category=category, amount=q(F(amount)), currency='USD',
            source_ref='SYNTHETIC-test-ledger')
            for i, (date, kind, category, amount) in enumerate(events)]

    def test_independent_base_totals_and_sale_share(self):
        p = self.run_case(); m = p['metrics']
        self.assertEqual([f(m[k]) for k in ['gross_contributions', 'gross_distributions',
            'net_cash_profit', 'cash_shortfall_at_horizon', 'cash_surplus_at_horizon']],
            [1000, 1600, 600, 0, 600])
        self.assertEqual(f(m['sale_share_of_distributions']), F(9, 16))
        self.assertEqual(f(m['receipts_excluding_sale_distributions']), 700)
        self.assertEqual(f(m['cash_shortfall_excluding_sale_receipts']), 300)
        self.assertFalse(p['sale_exclusion_is_a_recomputed_scenario'])

    def test_cash_shortfall_is_not_final_loss_with_retained_asset(self):
        self.case['events'][-1]['amount'] = q(F(0))
        p = self.run_case()
        self.assertEqual(f(p['metrics']['cash_shortfall_at_horizon']), 300)
        self.assertEqual(f(p['metrics']['net_cash_profit']), -300)
        self.assertIsNone(p['final_economic_capital_loss'])
        self.assertEqual(p['final_economic_capital_loss_state'], 'PENDING')

    def test_sale_event_does_not_certify_economic_close(self):
        self.case['events'][-1]['amount'] = q(F(100))
        p = self.run_case()
        self.assertEqual(f(p['metrics']['cash_shortfall_at_horizon']), 200)
        self.assertIsNone(p['final_economic_capital_loss'])

    def test_initial_peak_and_zero_grid_rows_preserved(self):
        self.case['events'] = self.case['events'][:1]
        p = self.run_case(); m = p['metrics']
        self.assertEqual(f(m['peak_cumulative_net_equity_funding_at_date_close']), 1000)
        self.assertEqual(f(m['possible_intraday_peak_upper_bound']), 1000)
        self.assertEqual(len(p['dated_funding_observations']), 3)
        self.assertEqual(f(p['dated_funding_observations'][1]['gross_distributions']), 0)

    def test_same_date_gross_flows_preserve_intraday_uncertainty(self):
        self.ledger([(0, 'contribution', 'initial_capital', 100),
            (1, 'contribution', 'additional_capital', 80),
            (1, 'distribution', 'net_refinance_distribution', 100),
            (2, 'distribution', 'net_sale_distribution', 100)])
        p = self.run_case(); m = p['metrics']
        self.assertEqual(f(m['peak_cumulative_net_equity_funding_at_date_close']), 100)
        self.assertEqual(f(m['possible_intraday_peak_upper_bound']), 180)
        self.assertEqual(f(m['gross_contributions']), 180)
        self.assertEqual(f(m['gross_distributions']), 200)

    def test_bounds_match_exhaustive_within_date_event_orders(self):
        events = [(0, 'contribution', 'initial_capital', 100),
            (1, 'contribution', 'additional_capital', 80),
            (1, 'contribution', 'refinance_cash_in', 60),
            (1, 'distribution', 'net_refinance_distribution', 50),
            (1, 'distribution', 'other_distribution', 140),
            (2, 'distribution', 'net_sale_distribution', 100)]
        self.ledger(events)
        peaks = []
        for permutation in itertools.permutations([80, 60, -50, -140]):
            balance = peak = 100
            for cash in permutation + (-100,):
                balance += cash
                peak = max(peak, balance)
            peaks.append(peak)
        m = self.run_case()['metrics']
        self.assertEqual(f(m['peak_cumulative_net_equity_funding_at_date_close']), min(peaks))
        self.assertEqual(f(m['possible_intraday_peak_upper_bound']), max(peaks))

    def test_row_order_is_not_intraday_order(self):
        before = self.run_case()
        self.case['events'].reverse()
        after = self.run_case()
        self.assertEqual(before['metrics'], after['metrics'])
        self.assertEqual(before['dated_funding_observations'], after['dated_funding_observations'])
        self.assertNotEqual(before['investor_source_sha256'], after['investor_source_sha256'])

    def test_recycled_cash_does_not_reset_signed_balance(self):
        self.ledger([(0, 'contribution', 'initial_capital', 100),
            (1, 'distribution', 'other_distribution', 300),
            (2, 'contribution', 'additional_capital', 150)])
        p = self.run_case(); m = p['metrics']
        self.assertEqual(f(m['peak_cumulative_net_equity_funding_at_date_close']), 100)
        self.assertEqual(f(m['possible_intraday_peak_upper_bound']), 100)
        self.assertEqual(f(p['dated_funding_observations'][-1]['cumulative_contributions_less_distributions']), -50)

    def test_exact_rational_not_float(self):
        self.case['events'][-1]['amount'] = q(F(1, 3))
        m = self.run_case()['metrics']
        self.assertEqual(f(m['sale_share_of_distributions']), F(1, 2101))
        self.assertEqual(f(m['cash_shortfall_at_horizon']), F(899, 3))

    def test_zero_distributions_undefined_sale_share_not_zero(self):
        for event in self.case['events']:
            if event['kind'] == 'distribution': event['amount'] = q(F(0))
        m = self.run_case()['metrics']
        self.assertIsNone(m['sale_share_of_distributions'])
        self.assertEqual(m['sale_share_state'], 'undefined_zero_distributions')
        self.assertEqual(f(m['cash_shortfall_at_horizon']), 1000)

    def test_zero_sale_with_positive_receipts_is_known_zero(self):
        self.case['events'][-1]['amount'] = q(F(0))
        m = self.run_case()['metrics']
        self.assertEqual(f(m['sale_share_of_distributions']), 0)
        self.assertEqual(m['sale_share_state'], 'computed_synthetic')

    def test_additional_capital_and_refinance_cash_in_stay_separate(self):
        for i, (category, amount) in enumerate([('additional_capital', 50), ('refinance_cash_in', 120)]):
            self.case['events'].append(dict(event_id='new'+str(i), date='2028-01-01', kind='contribution',
                category=category, amount=q(F(amount)), currency='USD', source_ref='SYNTHETIC-extra'))
        m = self.run_case()['metrics']
        self.assertEqual(f(m['additional_capital_contributions']), 50)
        self.assertEqual(f(m['refinance_cash_in_contributions']), 120)
        self.assertEqual(f(m['gross_contributions']), 1170)

    def test_missing_cash_metadata_blocks_without_partial_metrics(self):
        baseline = copy.deepcopy(self.case)
        for field, value in [('amount', None), ('currency', 'EUR'), ('date', '2028-02-01'), ('source_ref', None)]:
            with self.subTest(field=field):
                self.case = copy.deepcopy(baseline)
                self.case['events'][1][field] = value
                p = self.run_case()
                self.assertEqual(p['state'], 'blocked')
                self.assertIsNone(p['metrics'])
                self.assertEqual(p['dated_funding_observations'], [])

    def test_invalid_date_is_rejected_at_source_boundary(self):
        self.case['events'][1]['date'] = None
        with self.assertRaises(ValidationError):
            self.run_case()

    def test_incomplete_inventory_blocks(self):
        self.case['event_inventory_declared_complete'] = False
        self.assertEqual(self.run_case()['state'], 'blocked')

    def test_story_missing_stock_and_coc_does_not_erase_known_cash(self):
        self.case['capital_snapshots'] = []
        self.case['annual_cash_bases'] = []
        p = self.run_case()
        self.assertEqual(p['state'], 'computed_synthetic')
        self.assertTrue(p['upstream_story_blockers'])
        self.assertEqual(p['decision'], 'PENDING')

    def test_retained_equity_never_reduces_cash_shortfall(self):
        self.case['events'][-1]['amount'] = q(F(0))
        before = self.run_case()['metrics']
        self.case['capital_snapshots'][0]['retained_equity_value'] = q(F(9999999))
        self.assertEqual(self.run_case()['metrics'], before)

    def test_no_personal_allocation_or_financing_authority(self):
        p = self.run_case()
        self.assertEqual(p['equity_level'], 'aggregate_project_equity')
        self.assertIsNone(p['personal_investor_return'])
        self.assertEqual(p['personal_investor_return_state'], 'PENDING')
        for key in ['LP_allocation_applied', 'financing_compatibility_checked', 'risk_analysis_completed',
                    'capital_still_invested_derived_from_net_cash', 'production_authorized', 'real_decisions_enabled']:
            self.assertIs(p[key], False)

    def test_source_result_replay_rejects_stale_and_rehashed_forgery(self):
        raw = canonical(self.case).encode(); run = produce_investor_returns(raw)
        fake = run.payload; fake['gross_distributions'] = q(F(9999))
        encoded = canonical(fake)
        with self.assertRaises(ValidationError): summarize_cash_risk(raw, replace(run, payload_json=encoded, sha256=digest(encoded)))
        self.case['context']['run_id'] += '-revision'
        with self.assertRaises(ValidationError): summarize_cash_risk(canonical(self.case).encode(), run)

    def test_type_and_digest_checked(self):
        raw = canonical(self.case).encode(); run = produce_investor_returns(raw)
        for value in [run.payload, replace(run, sha256='0'*64)]:
            with self.assertRaises(ValidationError): summarize_cash_risk(raw, value)

    def test_risk_replay_rejects_rehashed_forgery_and_roundtrips(self):
        raw = canonical(self.case).encode(); upstream = produce_investor_returns(raw)
        run = summarize_cash_risk(raw, upstream)
        recovered = CashRiskRun(**json.loads(json.dumps({'payload_json': run.payload_json, 'sha256': run.sha256})))
        self.assertEqual(verify_cash_risk(raw, upstream, recovered), run)
        fake = run.payload; fake['metrics']['possible_intraday_peak_upper_bound'] = q(F(1))
        encoded = canonical(fake)
        with self.assertRaises(ValidationError): verify_cash_risk(raw, upstream, CashRiskRun(encoded, digest(encoded)))

    def test_arithmetic_budget_fault_fails_closed(self):
        raw = canonical(self.case).encode(); upstream = produce_investor_returns(raw)
        with patch('miniuw_foundation.cash_risk._bounded', side_effect=ArithmeticBudgetError):
            p = summarize_cash_risk(raw, upstream).payload
        self.assertEqual(p['state'], 'blocked'); self.assertIsNone(p['metrics'])
        self.assertEqual(p['dated_funding_observations'], [])
        self.assertIn('cash_risk_exact_arithmetic_budget_exceeded', p['cash_blockers'])

    def test_inputs_and_payload_are_immutable(self):
        raw = canonical(self.case).encode(); upstream = produce_investor_returns(raw)
        saved = upstream.payload_json
        run = summarize_cash_risk(raw, upstream)
        run.payload['metrics']['gross_distributions'] = None
        self.assertEqual(upstream.payload_json, saved)
        self.assertEqual(f(run.payload['metrics']['gross_distributions']), 1600)


if __name__ == '__main__':
    unittest.main()
