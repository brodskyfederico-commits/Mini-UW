from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import copy,json,tempfile,unittest
from miniuw_foundation import ValidationError
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.rental_operations import produce_rental_operations
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence

R=Path(__file__).resolve().parents[1]
def raw(p):return json.dumps(p).encode()
def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}


class RentalOperationsTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((R/'templates/synthetic-residential-operations.json').read_bytes())
    def run_case(self,p=None):return produce_rental_operations(raw(self.p if p is None else p))

    def test_exact_rent_losses_and_three_expense_bases(self):
        r=self.run_case().payload;self.assertEqual(r['gross_potential_total'],q(12000));self.assertEqual(r['residential_effective_rent'],q(10800))
        self.assertEqual([e['amount']for e in r['expenses']],[q(540),q(120),q(140)])
        self.assertEqual(r['operating_expenses_excluding_tax'],q(800));self.assertEqual(r['state'],'computed_synthetic')

    def test_per_unit_and_per_rentable_sf_produce_same_amount_with_explicit_area(self):
        p=copy.deepcopy(self.p);g=p['residential_groups'][0];g.update(rent_basis='per_rentable_sf_per_month',unit_rentable_sf=q(500),rent=q(1,5))
        self.assertEqual(self.run_case(p).payload['residential_effective_rent'],q(10800))
        g['unit_rentable_sf']=None;self.assertIsNone(self.run_case(p).payload['residential_effective_rent'])

    def test_concession_gross_and_after_vacancy_bases_are_distinct(self):
        for basis,expected in [('gross_potential_rent',q(9600)),('after_vacancy_rent',q(9720))]:
            p=copy.deepcopy(self.p);p['residential_groups'][0].update(concession_fraction=q(1,10),concession_basis=basis)
            self.assertEqual(self.run_case(p).payload['residential_effective_rent'],expected)

    def test_net_rent_requires_explicit_no_second_concession(self):
        p=copy.deepcopy(self.p);g=p['residential_groups'][0];g.update(rent=q(90),rent_definition='net_of_concessions',concession_basis='already_in_rent',concession_fraction=q(0))
        self.assertEqual(self.run_case(p).payload['residential_effective_rent'],q(9720))
        g['concession_fraction']=q(1,10);r=self.run_case(p).payload
        self.assertIsNone(r['residential_effective_rent']);self.assertTrue(any('net_rent_requires_explicit_zero'in b for b in r['blockers']))

    def test_declared_regular_month_conversion_not_implicit_calendar(self):
        p=copy.deepcopy(self.p);p['months_in_period']=6;r=self.run_case(p).payload
        self.assertEqual(r['residential_effective_rent'],q(5400));self.assertEqual(r['expenses'][1]['amount'],q(60));self.assertFalse(r['calendar_verified'])
        p['months_per_year']=None;self.assertEqual(self.run_case(p).payload['state'],'blocked')

    def test_zero_units_and_zero_rates_preserved(self):
        p=copy.deepcopy(self.p);p['residential_groups'][0]['units']=q(0);r=self.run_case(p).payload
        self.assertEqual(r['residential_effective_rent'],q(0));self.assertEqual(r['expenses'][0]['amount'],q(0));self.assertEqual(r['expenses'][2]['amount'],q(140))

    def test_no_clamping_of_signed_effective_result_from_declared_concession_base(self):
        p=copy.deepcopy(self.p);p['residential_groups'][0].update(loss_fraction=q(9,10),concession_fraction=q(1,5),concession_basis='gross_potential_rent')
        r=self.run_case(p).payload;self.assertEqual(r['residential_effective_rent'],q(-1200));self.assertEqual(r['decision'],'PENDING');self.assertFalse(r['rental_policy_adopted'])

    def test_missing_units_block_dependent_fee_but_preserve_independent_fixed_cost(self):
        p=copy.deepcopy(self.p);p['residential_groups'][0]['units']=None;r=self.run_case(p).payload
        self.assertIsNone(r['residential_effective_rent']);self.assertIsNone(r['expenses'][0]['amount']);self.assertEqual(r['expenses'][2]['amount'],q(140))

    def test_outside_fraction_or_integer_domains_stay_blocked(self):
        for field,value in [('units',q(3,2)),('rent',q(-1)),('loss_fraction',q(11,10)),('concession_fraction',q(-1,10))]:
            p=copy.deepcopy(self.p);p['residential_groups'][0][field]=value;self.assertEqual(self.run_case(p).payload['state'],'blocked')

    def test_currency_policy_and_source_metadata_not_assumed(self):
        for field,value in [('currency','EUR'),('policy_ref',None),('source_ref',None),('rent_basis',None)]:
            p=copy.deepcopy(self.p);p['residential_groups'][0][field]=value;r=self.run_case(p).payload
            self.assertIsNone(r['residential_effective_rent']);self.assertTrue(r['blockers'])

    def test_empty_inventories_do_not_assume_zero_or_hide_valid_rent(self):
        p=copy.deepcopy(self.p);p['expense_items']=[];r=self.run_case(p).payload
        self.assertEqual(r['residential_effective_rent'],q(10800));self.assertIsNone(r['operating_expenses_excluding_tax']);self.assertEqual(r['state'],'blocked')
        p=copy.deepcopy(self.p);p['residential_groups']=[];self.assertEqual(self.run_case(p).payload['state'],'blocked')

    def test_duplicate_identity_float_or_live_context_rejected(self):
        p=copy.deepcopy(self.p);p['residential_groups'].append(copy.deepcopy(p['residential_groups'][0]))
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.p);p['residential_groups'][0]['rent']=100.0
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.p);p['context']['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case(p)

    def test_exact_rational_budget_is_guarded(self):
        p=copy.deepcopy(self.p);p['residential_groups']=[]
        for i in range(1,25):
            g=copy.deepcopy(self.p['residential_groups'][0]);g['group_id']='SYNTHETIC-'+str(i);g['rent']=q(1,10**250+i);p['residential_groups'].append(g)
        r=self.run_case(p).payload;self.assertEqual(r['state'],'blocked');self.assertIn('exact_arithmetic_budget_exceeded',r['blockers'])

    def test_payload_and_source_are_isolated_and_unverified_flags_preserved(self):
        before=copy.deepcopy(self.p);run=self.run_case();p=run.payload;p['groups'].clear()
        self.assertEqual(before,self.p);self.assertEqual(len(run.payload['groups']),1)
        for key in ['calendar_verified','economic_scope_verified','rental_policy_adopted','cash_collected_verified','production_authorized']:self.assertFalse(run.payload[key])

    def test_reopen_archive_restores_exact_source_and_result(self):
        run=self.run_case();src=raw(self.p)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'rental.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_rental_operations(src,run);self.assertEqual(key,a.save_rental_operations(src,run))
            with EvidenceArchive(path)as a:
                b=a.load_rental_operations(key);self.assertEqual(b.run,run);self.assertEqual(a.get_rental_source(b.payload['source_sha256']),src)

    def test_forgery_rollback_missing_source_and_version_guards(self):
        run=self.run_case();p=run.payload;p['residential_effective_rent']=q(99999);encoded=canonical(p);forged=replace(run,payload_json=encoded,sha256=digest(encoded))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_rental_operations(raw(self.p),forged)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_rental_operations(raw(self.p),run)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_rental_operations(raw(self.p),run);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_rental_operations(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_rental_operations(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',run.payload['source_sha256']))
            with self.assertRaises(MissingEvidence):a.load_rental_operations(key)
