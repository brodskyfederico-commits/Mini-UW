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
from phased_rental_demo_support import raw, q, change_segment
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.phased_rental import produce_phased_rental, parse_phased_rental, DEFINITION
from miniuw_foundation.rental_calendar import next_month
from miniuw_foundation.debt_service import _date
from miniuw_foundation.operating_noi import ArithmeticBudgetError


class PhasedRentalTests(unittest.TestCase):
    def setUp(self):
        m = json.loads((ROOT/'templates/synthetic-phased-lifecycle-manifest.json').read_bytes())
        self.p = json.loads(m['periods'][0]['calendar_source_utf8'])
        self.partial = json.loads((ROOT/'templates/synthetic-partial-rental-period.json').read_bytes())

    def run_case(self, p=None):
        return produce_phased_rental(raw(self.p if p is None else p))

    def test_hand_available_exposure_and_scaled_rental_components(self):
        p = self.run_case().payload
        self.assertEqual(p['state'], 'computed_synthetic_phased_rental')
        self.assertEqual(p['totals'], dict(gross_potential_rent=q(35),vacancy_loss=q(2),concession_loss=q(5),effective_rent=q(28),available_unit_months=q(F(35,2))))
        self.assertEqual([r['amounts']['effective_rent'] for r in p['segments']], [q(0),q(5),q(8),q(15)])
        self.assertEqual([c['fraction'] for c in p['month_fraction_checks']], [q(1)]*3)

    def test_partial_month_and_unequal_date_lengths_use_supplied_fraction_only(self):
        self.assertEqual(self.run_case(self.partial).payload['totals']['effective_rent'], q(5))
        p = copy.deepcopy(self.p)
        p['segments'][0]['end_date'] = '2027-01-10'
        p['segments'][1]['start_date'] = '2027-01-10'
        self.assertEqual(self.run_case(p).payload['totals']['effective_rent'], q(28))
        self.assertFalse(self.run_case(p).payload['day_count_or_delivery_rule_generated'])

    def test_missing_fraction_even_on_zero_availability_never_becomes_zero(self):
        p = copy.deepcopy(self.p)
        p['segments'][0]['proration_fraction'] = None
        r = self.run_case(p).payload
        self.assertIsNone(r['totals'])
        self.assertTrue(any('month_fraction_missing' in b for b in r['blockers']))

    def test_full_month_fraction_sum_and_partial_upper_bound_are_exact(self):
        for weights in ((F(2,5),F(1,2)), (1,1)):
            p = copy.deepcopy(self.p)
            for row, v in zip(p['segments'], weights): row['proration_fraction'] = q(v)
            self.assertIsNone(self.run_case(p).payload['totals'])
        for v in (F(11,10), -1):
            p = copy.deepcopy(self.partial)
            p['segments'][0]['proration_fraction'] = q(v)
            self.assertIsNone(self.run_case(p).payload['totals'])

    def test_capacity_not_inferred_from_available_and_explicit_zero_preserved(self):
        for value in (None, q(-1), q(F(3,2))):
            p = copy.deepcopy(self.p)
            p['capacity'][0]['total_units'] = value
            self.assertIsNone(self.run_case(p).payload['totals'])
        p = copy.deepcopy(self.p)
        p['capacity'][0]['total_units'] = q(0)
        for i in range(len(p['segments'])): change_segment(p,i,lambda s:s['residential_groups'][0].update(units=q(0)))
        self.assertEqual(self.run_case(p).payload['totals']['effective_rent'], q(0))
        p['capacity'][0]['total_units'] = None
        self.assertIsNone(self.run_case(p).payload['totals'])

    def test_availability_cannot_exceed_capacity_be_fractional_or_unknown(self):
        for value in (q(11),q(F(1,2)),q(-1),None):
            p = copy.deepcopy(self.p)
            change_segment(p,1,lambda s:s['residential_groups'][0].update(units=value))
            self.assertIsNone(self.run_case(p).payload['totals'])
        # A separately supplied reduction is supported; no monotone delivery policy inferred.
        p = copy.deepcopy(self.p)
        change_segment(p,2,lambda s:s['residential_groups'][0].update(units=q(3)))
        self.assertEqual(self.run_case(p).payload['state'], 'computed_synthetic_phased_rental')

    def test_exact_capacity_group_area_and_rent_basis_required(self):
        for mutate in (lambda s:s['residential_groups'].clear(),lambda s:s['residential_groups'][0].update(group_id='SYNTHETIC-unknown'),lambda s:s['residential_groups'][0].update(unit_rentable_sf=q(1)),lambda s:s['residential_groups'][0].update(rent_basis='per_rentable_sf_per_month',unit_rentable_sf=q(100))):
            p=copy.deepcopy(self.p);change_segment(p,1,mutate)
            self.assertIsNone(self.run_case(p).payload['totals'])
        for field,value in [('unit_rentable_sf',q(-1)),('source_ref',None),('rent_basis',None)]:
            p=copy.deepcopy(self.p);p['capacity'][0][field]=value
            self.assertIsNone(self.run_case(p).payload['totals'])

    def test_gaps_overlaps_order_missing_or_cross_month_segments_block(self):
        for mutate in (lambda p:p['segments'].pop(0),lambda p:p['segments'].reverse(),lambda p:p['segments'][0].update(end_date='2027-01-17'),lambda p:p['segments'][1].update(end_date='2027-02-02'),lambda p:p['segments'][1].update(month_anchor='2027-01-02'),lambda p:p.update(end_date='2027-05-01'),lambda p:p['segments'].clear()):
            p=copy.deepcopy(self.p);mutate(p)
            self.assertIsNone(self.run_case(p).payload['totals'])

    def test_reference_month_metadata_expenses_and_unknown_rent_remain_guarded(self):
        for field,value in [('months_in_period',2),('months_per_year',None),('currency','EUR'),('period_ref','SYNTHETIC-other')]:
            p=copy.deepcopy(self.p);change_segment(p,1,lambda s:s.update({field:value}))
            self.assertIsNone(self.run_case(p).payload['totals'])
        for mutate in (lambda s:s['residential_groups'][0].update(rent=None),lambda s:s['expense_items'][0].update(rate=q(1)),lambda s:s['context'].update(run_id='SYNTHETIC-other')):
            p=copy.deepcopy(self.p);change_segment(p,1,mutate)
            self.assertIsNone(self.run_case(p).payload['totals'])

    def test_concession_base_and_proration_are_applied_once(self):
        values=[]
        for basis in ('after_vacancy_rent','gross_potential_rent'):
            p=copy.deepcopy(self.partial)
            change_segment(p,0,lambda s:s['residential_groups'][0].update(loss_fraction=q(F(1,2)),concession_fraction=q(F(1,2)),concession_basis=basis))
            values.append(self.run_case(p).payload['totals']['effective_rent'])
        self.assertEqual(values,[q(F(5,4)),q(0)])

    def test_negative_mathematical_result_is_preserved_without_clamping(self):
        p=copy.deepcopy(self.partial)
        change_segment(p,0,lambda s:s['residential_groups'][0].update(loss_fraction=q(F(9,10)),concession_fraction=q(F(1,5)),concession_basis='gross_potential_rent'))
        self.assertEqual(self.run_case(p).payload['totals']['effective_rent'],q(F(-1,2)))
        self.assertEqual(self.run_case(p).payload['decision'],'PENDING')

    def test_each_completeness_capacity_availability_and_proration_basis_required(self):
        for field,value in [('inventory_declared_complete',None),('capacity_basis_ref',None),('calendar_basis_ref',None),('capacity',[])]:
            p=copy.deepcopy(self.p);p[field]=value
            self.assertIsNone(self.run_case(p).payload['totals'])
        for field in ('availability_source_ref','proration_basis_ref'):
            p=copy.deepcopy(self.p);p['segments'][0][field]=None
            self.assertIsNone(self.run_case(p).payload['totals'])

    def test_injected_and_real_denominator_budget_never_export_partial_totals(self):
        with patch('miniuw_foundation.phased_rental._bounded',side_effect=ArithmeticBudgetError('fault')):
            self.assertIn('exact_phased_rental_arithmetic_budget_exceeded',self.run_case().payload['blockers'])
        p=copy.deepcopy(self.p);proto=copy.deepcopy(p['segments'][2]);p.update(end_date='2029-01-01',segments=[]);start=_date('2027-01-01')
        for i in range(24):
            end=next_month(start);row=copy.deepcopy(proto);row.update(segment_id='SYNTHETIC-small-'+str(i),start_date=start.isoformat(),end_date=end.isoformat(),month_anchor=start.isoformat(),proration_fraction=q(1))
            source=json.loads(row['rental_source_utf8']);source['period_ref']=row['segment_id'];source['residential_groups'][0].update(rent=q(F(1,10**250+i+1)),loss_fraction=q(0),concession_fraction=q(0));row['rental_source_utf8']=raw(source).decode();p['segments'].append(row);start=end
        r=self.run_case(p).payload;self.assertIn('exact_phased_rental_arithmetic_budget_exceeded',r['blockers']);self.assertIsNone(r['totals'])

    def test_strict_syntax_duplicate_inventory_and_bounded_sources(self):
        for mutate in (lambda p:p.update(extra=True),lambda p:p.update(inventory_declared_complete=1),lambda p:p['context'].update(deal_id='live'),lambda p:p['capacity'].append(copy.deepcopy(p['capacity'][0])),lambda p:p['segments'].append(copy.deepcopy(p['segments'][0])),lambda p:p['segments'][0].update(proration_fraction=0.5),lambda p:p['segments'][0].update(rental_source_utf8=None),lambda p:p.update(segments=p['segments']*241)):
            p=copy.deepcopy(self.p);mutate(p)
            with self.assertRaises(ValidationError):self.run_case(p)
        for b in (b'{}',b'{"schema":1,"schema":2}',b'NaN',b'\xff',b' '*8_388_609):
            with self.assertRaises(ValidationError):parse_phased_rental(b)
        p=copy.deepcopy(self.p);p['segments'][0]['rental_source_utf8']='\ud800'
        with self.assertRaises(ValidationError):parse_phased_rental(json.dumps(p,ensure_ascii=True).encode())

    def test_immutable_repeated_proof_and_no_real_delivery_or_contract_approval(self):
        before=raw(self.p);run=self.run_case();self.assertEqual(run,self.run_case());p=run.payload;p['segments'].clear()
        self.assertEqual(len(run.payload['segments']),4);self.assertEqual(raw(self.p),before)
        self.assertEqual(run.payload['definition_sha256'],hashlib.sha256(DEFINITION.read_bytes()).hexdigest())
        for key in ('day_count_or_delivery_rule_generated','actual_capacity_availability_or_occupancy_verified','proration_contract_authenticated','actual_collection_or_intraperiod_liquidity_verified','real_decisions_enabled','production_authorized'):
            self.assertIs(run.payload[key],False)
