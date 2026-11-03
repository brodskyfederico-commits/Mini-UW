import copy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from rental_lifecycle_demo_support import raw, q, change_month
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.rental_calendar import produce_rental_calendar, parse_rental_calendar, next_month, DEFINITION
from miniuw_foundation.debt_service import _date
from miniuw_foundation.operating_noi import ArithmeticBudgetError


class RentalCalendarTests(unittest.TestCase):
    def setUp(self):
        p = json.loads((ROOT/'templates/synthetic-rental-lifecycle-manifest.json').read_bytes())
        self.p = json.loads(p['periods'][0]['calendar_source_utf8'])

    def run_case(self, p=None):
        return produce_rental_calendar(raw(self.p if p is None else p))

    def test_independent_monthly_potential_vacancy_concession_and_effective_totals(self):
        r = self.run_case().payload
        self.assertEqual(r['state'], 'computed_synthetic_monthly_rental_calendar')
        self.assertEqual(r['totals'], dict(gross_potential_rent=q(60), vacancy_loss=q(30), concession_loss=q(5), effective_rent=q(25)))
        self.assertEqual([m['amounts']['effective_rent'] for m in r['months']], [q(0), q(10), q(15)])
        self.assertEqual([m['amounts']['gross_potential_rent'] for m in r['months']], [q(20)]*3)

    def test_missing_or_reordered_month_is_not_interpolated_or_zero_filled(self):
        for mutate in (lambda p:p['months'].pop(1), lambda p:p['months'].reverse(), lambda p:p['months'].clear(), lambda p:p.update(end_date='2027-05-01')):
            p = copy.deepcopy(self.p)
            mutate(p)
            r = self.run_case(p).payload
            self.assertEqual(r['state'], 'blocked')
            self.assertIsNone(r['totals'])
            self.assertFalse(r['missing_month_or_market_assumption_generated'])

    def test_partial_overlap_and_non_first_day_periods_need_another_profile(self):
        for field, value in [('start_date', '2027-01-02'), ('end_date', '2027-01-31')]:
            p = copy.deepcopy(self.p)
            p['months'][0][field] = value
            self.assertIsNone(self.run_case(p).payload['totals'])
        self.assertEqual(next_month(_date('2027-12-01')).isoformat(), '2028-01-01')
        self.assertEqual(next_month(_date('2028-02-01')).isoformat(), '2028-03-01')

    def test_month_source_must_be_one_month_and_match_context_currency_period(self):
        for field, value in [('months_in_period', 2), ('months_per_year', None), ('currency', 'EUR'), ('period_ref', 'SYNTHETIC-wrong')]:
            p = copy.deepcopy(self.p)
            change_month(p, 0, lambda s:s.update({field:value}))
            self.assertIsNone(self.run_case(p).payload['totals'])
        p = copy.deepcopy(self.p)
        change_month(p, 0, lambda s:s['context'].update(run_id='SYNTHETIC-other'))
        self.assertIsNone(self.run_case(p).payload['totals'])

    def test_physical_group_inventory_cannot_change_silently(self):
        for field, value in [('units', q(20)), ('group_id', 'SYNTHETIC-new-group'), ('unit_rentable_sf', q(100))]:
            p = copy.deepcopy(self.p)
            change_month(p, 1, lambda s:s['residential_groups'][0].update({field:value}))
            self.assertTrue(any('physical_group_inventory_changed' in b for b in self.run_case(p).payload['blockers']))

    def test_unknown_rent_is_not_explicit_zero_or_prior_month_rent(self):
        p = copy.deepcopy(self.p)
        change_month(p, 0, lambda s:s['residential_groups'][0].update(rent=None))
        self.assertIsNone(self.run_case(p).payload['totals'])
        self.assertIsNone(self.run_case(p).payload['months'][0]['amounts'])
        change_month(p, 0, lambda s:s['residential_groups'][0].update(rent=q(0)))
        self.assertEqual(self.run_case(p).payload['totals']['effective_rent'], q(25))

    def test_concession_base_and_net_rent_never_double_count(self):
        outputs = []
        for basis in ('after_vacancy_rent', 'gross_potential_rent'):
            p = copy.deepcopy(self.p)
            change_month(p, 1, lambda s:s['residential_groups'][0].update(concession_fraction=q(F(1,2)), concession_basis=basis))
            outputs.append(self.run_case(p).payload['totals']['effective_rent'])
        self.assertEqual(outputs, [q(20), q(15)])
        p = copy.deepcopy(self.p)
        change_month(p, 2, lambda s:s['residential_groups'][0].update(rent_definition='net_of_concessions', concession_basis='already_in_rent'))
        self.assertIsNone(self.run_case(p).payload['totals'])
        change_month(p, 2, lambda s:s['residential_groups'][0].update(concession_fraction=q(0)))
        self.assertEqual(self.run_case(p).payload['totals']['effective_rent'], q(30))

    def test_nonzero_monthly_expense_is_not_silently_ignored_or_recounted(self):
        p = copy.deepcopy(self.p)
        change_month(p, 0, lambda s:s['expense_items'][0].update(rate=q(1)))
        r = self.run_case(p).payload
        self.assertTrue(any('monthly_expenses_must_be_explicit_zero_placeholders' in b for b in r['blockers']))
        self.assertIsNone(r['totals'])

    def test_missing_inventory_and_bases_withhold_all_totals(self):
        for field, value in [('inventory_declared_complete', None), ('calendar_basis_ref', None), ('group_inventory_basis_ref', None)]:
            p = copy.deepcopy(self.p)
            p[field] = value
            self.assertIsNone(self.run_case(p).payload['totals'])

    def test_negative_mathematical_rent_is_preserved_without_clamping(self):
        p = copy.deepcopy(self.p)
        for i in range(3):
            change_month(p, i, lambda s:s['residential_groups'][0].update(loss_fraction=q(F(9,10)), concession_fraction=q(F(1,5)), concession_basis='gross_potential_rent'))
        r = self.run_case(p).payload
        self.assertEqual(r['totals']['effective_rent'], q(-6))
        self.assertEqual(r['decision'], 'PENDING')
        self.assertFalse(r['loss_fraction_certifies_physical_occupancy'])

    def test_injected_and_real_denominator_growth_budget_withhold_partial_export(self):
        with patch('miniuw_foundation.rental_calendar._bounded', side_effect=ArithmeticBudgetError('fault')):
            self.assertIn('exact_monthly_aggregation_budget_exceeded', self.run_case().payload['blockers'])
        p = copy.deepcopy(self.p)
        proto = copy.deepcopy(p['months'][0])
        p.update(end_date='2029-01-01', months=[])
        start = _date('2027-01-01')
        for i in range(24):
            end = next_month(start)
            row = copy.deepcopy(proto)
            row.update(period_ref='SYNTHETIC-tiny-'+str(i), start_date=start.isoformat(), end_date=end.isoformat())
            s = json.loads(row['rental_source_utf8'])
            s['period_ref'] = row['period_ref']
            s['residential_groups'][0].update(rent=q(F(1, 10**250+i+1)), loss_fraction=q(0), concession_fraction=q(0))
            row['rental_source_utf8'] = raw(s).decode()
            p['months'].append(row)
            start = end
        r = self.run_case(p).payload
        self.assertIn('exact_monthly_aggregation_budget_exceeded', r['blockers'])
        self.assertIsNone(r['totals'])

    def test_strict_json_synthetic_context_and_bounded_inventory(self):
        for mutate in (lambda p:p.update(extra=True), lambda p:p.update(inventory_declared_complete=1), lambda p:p['context'].update(deal_id='live'), lambda p:p['months'].append(copy.deepcopy(p['months'][0])), lambda p:p.update(months=p['months']*121), lambda p:p['months'][0].update(rental_source_utf8=None), lambda p:change_month(p, 0, lambda s:s['residential_groups'][0].update(rent=2.0))):
            p = copy.deepcopy(self.p)
            mutate(p)
            with self.assertRaises(ValidationError): self.run_case(p)
        for b in (b'{}', b'{"schema":1,"schema":2}', b'NaN', b'\xff', b' '*8_388_609):
            with self.assertRaises(ValidationError): parse_rental_calendar(b)
        p = copy.deepcopy(self.p)
        p['months'][0]['rental_source_utf8'] = '\ud800'
        with self.assertRaises(ValidationError): parse_rental_calendar(json.dumps(p, ensure_ascii=True).encode())

    def test_deterministic_immutable_source_and_unverified_flags(self):
        original = raw(self.p)
        run = self.run_case()
        self.assertEqual(run, self.run_case())
        p = run.payload
        p['months'].clear()
        self.assertEqual(len(run.payload['months']), 3)
        self.assertEqual(raw(self.p), original)
        self.assertEqual(run.payload['definition_sha256'], hashlib.sha256(DEFINITION.read_bytes()).hexdigest())
        for k in ('actual_rent_lease_or_collection_verified', 'real_decisions_enabled', 'production_authorized'):
            self.assertIs(run.payload[k], False)
