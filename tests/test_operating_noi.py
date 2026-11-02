from dataclasses import replace
from pathlib import Path
from fractions import Fraction
from unittest.mock import patch
import copy,hashlib,json,tempfile,unittest
from miniuw_foundation import ValidationError
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.operating_noi import parse_operating_noi,produce_operating_noi
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence

R=Path(__file__).resolve().parents[1]
def raw(p):return json.dumps(p).encode()
def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}
def f(p):return None if p is None else Fraction(int(p['numerator']),int(p['denominator']))


class OperatingNoiTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((R/'templates/synthetic-operating-noi.json').read_bytes())
    def run_case(self,p=None):return produce_operating_noi(raw(self.p if p is None else p))

    def test_declared_income_and_expenses_produce_exact_proxy_noi(self):
        p=self.run_case().payload
        self.assertEqual(f(p['income_total']),1450);self.assertEqual(f(p['expenses_excluding_tax']),250)
        self.assertEqual(f(p['operating_before_tax']),1200);self.assertEqual(f(p['noi']),1000);self.assertEqual(f(p['property_tax']),200)
        self.assertEqual(p['tax_branch'],'proxy');self.assertEqual(f(p['equation_residual']),0)

    def test_comparable_floor_branch_and_boundary_tie(self):
        for floor,noi,tax,branch in [(300,900,300,'floor'),(200,1000,200,'tie')]:
            p=copy.deepcopy(self.p);p['tax_floor']['value']=q(floor);r=self.run_case(p).payload
            self.assertEqual((f(r['noi']),f(r['property_tax']),r['tax_branch']),(noi,tax,branch))

    def test_negative_noi_is_preserved_not_clipped_or_classified_fail(self):
        p=copy.deepcopy(self.p);p['income_rows']=p['income_rows'][:1];p['income_rows'][0]['value']=q(0);p['expense_rows'][0]['value']=q(100);p['tax_floor']['value']=q(20)
        r=self.run_case(p).payload;self.assertEqual(f(r['noi']),-120);self.assertEqual(f(r['property_tax']),20);self.assertEqual(r['decision'],'PENDING')

    def test_explicit_zero_coefficient_and_floor_differ_from_missing(self):
        p=copy.deepcopy(self.p);p['tax_coefficient']['value']=q(0);p['tax_floor']['value']=q(0)
        r=self.run_case(p).payload;self.assertEqual(f(r['noi']),1200);self.assertEqual(f(r['property_tax']),0)
        p['tax_coefficient']['value']=None;r=self.run_case(p).payload
        self.assertEqual(f(r['operating_before_tax']),1200);self.assertIsNone(r['noi']);self.assertIn('/tax_coefficient:coefficient_missing',r['blockers'])

    def test_missing_comparable_does_not_default_to_zero(self):
        p=copy.deepcopy(self.p);p['tax_floor']['value']=None;r=self.run_case(p).payload
        self.assertIsNone(r['noi']);self.assertIn('/tax_floor:amount_missing',r['blockers'])

    def test_negative_floor_or_coefficient_is_outside_this_profile(self):
        for field in ['tax_floor','tax_coefficient']:
            p=copy.deepcopy(self.p);p[field]['value']=q(-1);r=self.run_case(p).payload
            self.assertIsNone(r['noi']);self.assertTrue(any('nonnegative_profile_domain'in x for x in r['blockers']))

    def test_original_equation_is_satisfied_over_signed_and_boundary_grid(self):
        for A in [-10,0,12,50]:
            for floor in [0,3,6]:
                for k in [Fraction(0),Fraction(1,4),Fraction(2)]:
                    p=copy.deepcopy(self.p);p['income_rows']=p['income_rows'][:1];p['income_rows'][0]['value']=q(A);p['expense_rows'][0]['value']=q(0)
                    p['tax_floor']['value']=q(floor);p['tax_coefficient']['value']=q(k.numerator,k.denominator);r=self.run_case(p).payload
                    N,T=f(r['noi']),f(r['property_tax']);self.assertEqual(N,A-max(Fraction(floor),k*N));self.assertEqual(T,A-N)

    def test_currency_and_period_mismatches_block_affected_totals(self):
        for field,value in [('currency','EUR'),('period_ref','other-period')]:
            p=copy.deepcopy(self.p);p['income_rows'][0][field]=value;r=self.run_case(p).payload
            self.assertIsNone(r['income_total']);self.assertIsNone(r['noi']);self.assertTrue(any(field+'_missing_or_mismatch'in x for x in r['blockers']))

    def test_cash_basis_and_unsupported_units_are_not_silently_normalized(self):
        for field,value in [('basis','cash_paid'),('unit','dollars_per_month')]:
            p=copy.deepcopy(self.p);p['expense_rows'][0][field]=value;r=self.run_case(p).payload
            self.assertIsNone(r['expenses_excluding_tax']);self.assertIsNone(r['noi'])
        p=copy.deepcopy(self.p);p['tax_coefficient']['unit']='bps';self.assertIsNone(self.run_case(p).payload['noi'])

    def test_empty_inventory_and_blank_row_do_not_imply_zero(self):
        for family in ['income_rows','expense_rows']:
            p=copy.deepcopy(self.p);p[family]=[];r=self.run_case(p).payload
            self.assertIsNone(r['noi']);self.assertIn('/'+family+':inventory_empty_not_assumed_zero',r['blockers'])
        p=copy.deepcopy(self.p);p['income_rows'][0]['value']=None;self.assertIsNone(self.run_case(p).payload['income_total'])

    def test_duplicate_item_ids_rejected_but_equal_amounts_retained(self):
        p=copy.deepcopy(self.p);p['expense_rows'][0]['item_id']=p['income_rows'][0]['item_id']
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.p);p['income_rows'][0]['value']=q(250);self.assertEqual(f(self.run_case(p).payload['income_total']),500)

    def test_missing_source_binding_and_global_metadata_remain_pending(self):
        p=copy.deepcopy(self.p);p['income_rows'][0]['source_ref']=None;r=self.run_case(p).payload
        self.assertIn('/income_rows/0:declared_source_ref_missing',r['blockers'])
        for key in ['currency','period_ref']:
            p=copy.deepcopy(self.p);p[key]=None;self.assertIsNone(self.run_case(p).payload['noi'])

    def test_non_synthetic_context_and_unsupported_tax_assumptions_rejected(self):
        p=copy.deepcopy(self.p);p['context']['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case(p)
        for key,value in [('coefficient_fixed',False),('additional_tax_adjustments',True),('same_period_accrual',None)]:
            p=copy.deepcopy(self.p);p['modelling_assumptions'][key]=value
            with self.assertRaises(ValidationError):self.run_case(p)

    def test_ambiguous_float_extra_fields_and_duplicate_json_keys_rejected(self):
        p=copy.deepcopy(self.p);p['income_rows'][0]['value']=1.2
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.p);p['tax_exemption_approved']=True
        with self.assertRaises(ValidationError):self.run_case(p)
        with self.assertRaises(ValidationError):parse_operating_noi(b'{"schema":"a","schema":"b"}')

    def test_arithmetic_budget_blocks_large_coprime_accumulation(self):
        p=copy.deepcopy(self.p);p['income_rows']=[]
        # Consecutive large denominator powers are individually bounded, but exceed the exact-sum budget.
        for i in range(1,25):
            row=copy.deepcopy(self.p['income_rows'][0]);row['item_id']='SYNTHETIC-budget-'+str(i);row['value']=q(1,10**250+i);p['income_rows'].append(row)
        r=self.run_case(p).payload;self.assertIsNone(r['noi']);self.assertIn('exact_arithmetic_budget_or_residual_guard',r['blockers'])

    def test_lineage_source_hash_and_definitions_bind_output_without_authority_claim(self):
        r=self.run_case();p=r.payload;self.assertEqual(p['source_sha256'],hashlib.sha256(raw(self.p)).hexdigest())
        self.assertEqual(len(p['lineage']),5);self.assertEqual(len(p['definition_sources']),3)
        self.assertTrue(all(x['sha256']for x in p['definition_sources']))
        for key in ['economic_scope_independently_verified','calendar_period_verified','source_authority_verified','tax_law_verified','tax_policy_adopted','financial_inputs_verified','cash_paid_or_distributed_verified','financial_module_closed','production_authorized']:
            self.assertFalse(p[key])

    def test_input_and_payload_copy_are_isolated(self):
        original=copy.deepcopy(self.p);r=self.run_case();p=r.payload;p['noi']=q(0)
        self.assertEqual(original,self.p);self.assertEqual(f(r.payload['noi']),1000)

    def test_exact_source_representation_changes_evidence_without_changing_math(self):
        a=self.run_case();p=copy.deepcopy(self.p);p['tax_coefficient']['value']=q(2,10);b=self.run_case(p)
        self.assertNotEqual(a.sha256,b.sha256);self.assertEqual(a.payload['noi'],b.payload['noi'])

    def test_reopened_archive_replays_exact_source_and_result(self):
        run=self.run_case();src=raw(self.p)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'noi.sqlite3'
            with EvidenceArchive(path)as archive:
                key=archive.save_operating_noi(src,run);self.assertEqual(key,archive.save_operating_noi(src,run))
            with EvidenceArchive(path)as archive:
                bundle=archive.load_operating_noi(key);self.assertEqual(bundle.run,run);self.assertEqual(archive.get_operating_noi_source(bundle.payload['source_sha256']),src)

    def test_forgery_and_local_capture_rollback(self):
        run=self.run_case();p=run.payload;p['noi']=q(9999);encoded=canonical(p);forged=replace(run,payload_json=encoded,sha256=digest(encoded))
        with EvidenceArchive(':memory:')as archive:
            with self.assertRaises(ValidationError):archive.save_operating_noi(raw(self.p),forged)
            with patch.object(archive,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):archive.save_operating_noi(raw(self.p),run)
            self.assertEqual(archive._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=archive.save_operating_noi(raw(self.p),run);body=json.loads(archive.read_bundle_bytes(key));body['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with archive._transaction():bad=archive._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):archive.load_operating_noi(bad)

    def test_missing_evidence_and_incompatible_code_versions(self):
        run=self.run_case()
        with EvidenceArchive(':memory:')as archive:
            key=archive.save_operating_noi(raw(self.p),run);body=json.loads(archive.read_bundle_bytes(key));body['versions'][0]='0'*64
            with archive._transaction():bad=archive._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):archive.load_operating_noi(bad)
            archive._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',run.payload['source_sha256']))
            with self.assertRaises(MissingEvidence):archive.load_operating_noi(key)
