from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,tempfile,unittest
from miniuw_foundation import ValidationError
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.rental_operations import produce_rental_operations
from miniuw_foundation.rental_noi import assemble_rental_noi
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence

R=Path(__file__).resolve().parents[1]
def raw(p):return json.dumps(p).encode()
def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}


class RentalNoiTests(unittest.TestCase):
    def setUp(self):
        self.source=(R/'templates/synthetic-residential-operations.json').read_bytes();self.rental=produce_rental_operations(self.source)
        self.spec=json.loads((R/'templates/synthetic-residential-noi-assembly.json').read_bytes())
    def run_case(self,p=None,source=None):
        src=self.source if source is None else source
        return assemble_rental_noi(src,produce_rental_operations(src),raw(self.spec if p is None else p))
    def rebind(self,source):
        p=copy.deepcopy(self.spec);p['rental_source_sha256']=hashlib.sha256(source).hexdigest();p['rental_run_sha256']=produce_rental_operations(source).sha256;return p

    def test_computed_rent_and_expenses_feed_exact_conditional_noi(self):
        run=self.run_case();self.assertEqual(run.payload['computed_noi'],q(8000));self.assertEqual(run.noi_run.payload['property_tax'],q(2000))
        self.assertEqual(run.noi_run.payload['operating_before_tax'],q(10000));self.assertEqual(run.payload['state'],'computed_synthetic')

    def test_derived_amounts_and_provenance_are_bound_to_rental_run(self):
        p=json.loads(self.run_case().compiled_raw)
        self.assertEqual(p['income_rows'][0]['value'],q(10800));self.assertIn(self.rental.sha256,p['income_rows'][0]['source_ref'])
        self.assertEqual([r['value']for r in p['expense_rows']],[q(540),q(120),q(140)])

    def test_required_additional_inventory_not_silently_assumed_zero(self):
        for field,value in [('additional_income_inventory_declared_complete',None),('additional_income_inventory_declared_complete',False),('additional_income_rows',[])]:
            p=copy.deepcopy(self.spec);p[field]=value;run=self.run_case(p)
            self.assertEqual(run.payload['state'],'blocked');self.assertIsNone(run.compiled_raw);self.assertIsNone(run.noi_run)

    def test_stale_source_run_or_context_block_compilation(self):
        for field in ['rental_source_sha256','rental_run_sha256']:
            p=copy.deepcopy(self.spec);p[field]='0'*64;self.assertIsNone(self.run_case(p).compiled_raw)
        p=copy.deepcopy(self.spec);p['context']['run_id']='SYNTHETIC-other';self.assertIsNone(self.run_case(p).compiled_raw)

    def test_forged_producer_cannot_be_used_as_input(self):
        p=self.rental.payload;p['residential_effective_rent']=q(9999);encoded=canonical(p);fake=replace(self.rental,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):assemble_rental_noi(self.source,fake,raw(self.spec))

    def test_upstream_missing_rent_blocks_compilation_and_preserves_causes(self):
        p=json.loads(self.source);p['residential_groups'][0]['rent']=None;src=raw(p);run=self.run_case(self.rebind(src),src)
        self.assertIn('residential_producer_blocked',run.payload['blockers']);self.assertTrue(run.payload['residential_blockers']);self.assertIsNone(run.compiled_raw)

    def test_missing_tax_keeps_pre_tax_amount_but_blocks_noi(self):
        p=copy.deepcopy(self.spec);p['tax_coefficient']['value']=None;run=self.run_case(p)
        self.assertEqual(run.noi_run.payload['operating_before_tax'],q(10000));self.assertIsNone(run.payload['computed_noi']);self.assertIn('NOI:/tax_coefficient:coefficient_missing',run.payload['blockers'])

    def test_additional_currency_or_period_mismatch_is_not_converted(self):
        for field,value in [('currency','EUR'),('period_ref','other-period')]:
            p=copy.deepcopy(self.spec);p['additional_income_rows'][0][field]=value;run=self.run_case(p)
            self.assertIsNone(run.payload['computed_noi']);self.assertTrue(any(field+'_missing_or_mismatch'in b for b in run.payload['blockers']))

    def test_literal_zero_and_missing_additional_value_differ(self):
        self.assertEqual(self.run_case().payload['computed_noi'],q(8000))
        p=copy.deepcopy(self.spec);p['additional_income_rows'][0]['value']=None;self.assertIsNone(self.run_case(p).payload['computed_noi'])

    def test_unsupported_policy_or_live_context_rejected_and_no_financial_approval(self):
        p=copy.deepcopy(self.spec);p['context']['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.spec);p['noi_modelling_assumptions']['coefficient_fixed']=False
        with self.assertRaises(ValidationError):self.run_case(p)
        run=self.run_case();self.assertEqual(run.payload['decision'],'PENDING')
        for k in ['additional_income_scope_independently_verified','tax_policy_adopted','financially_validated','production_authorized','financial_module_closed']:self.assertFalse(run.payload[k])

    def test_reopened_archive_preserves_original_spec_compiled_source_and_runs(self):
        run=self.run_case();spec=raw(self.spec)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'assembled.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_rental_noi(self.source,self.rental,spec,run);self.assertEqual(key,a.save_rental_noi(self.source,self.rental,spec,run))
            with EvidenceArchive(path)as a:
                b=a.load_rental_noi(key);self.assertEqual(b.run,run);self.assertEqual(a.get_rental_source(b.payload['rental_source_sha256']),self.source);self.assertEqual(a.get_rental_noi_spec(b.payload['spec_source_sha256']),spec)
                self.assertEqual(a.get_operating_noi_source(b.payload['compiled_noi_source_sha256']),run.compiled_raw)

    def test_archive_forgery_atomic_fault_missing_and_version_checks(self):
        run=self.run_case();spec=raw(self.spec);p=run.payload;p['computed_noi']=q(9999);encoded=canonical(p);fake=replace(run,payload_json=encoded,sha256=digest(encoded))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_rental_noi(self.source,self.rental,spec,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_rental_noi(self.source,self.rental,spec,run)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_rental_noi(self.source,self.rental,spec,run);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_rental_noi(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_rental_noi(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',run.payload['compiled_noi_source_sha256']))
            with self.assertRaises(MissingEvidence):a.load_rental_noi(key)

    def test_full_residential_to_noi_to_service_ratio_replays_both_archived_links(self):
        from miniuw_foundation.debt_service import produce_debt_service
        from miniuw_foundation.operating_dscr import OperatingDscrBinding,calculate_operating_dscr
        run=self.run_case();loan=json.loads((R/'templates/synthetic-loan-terms.json').read_bytes());loan['context']=run.payload['context'];loan['annual_equivalent_ref']=run.noi_run.payload['period_ref'];loan_raw=raw(loan);debt=produce_debt_service(loan_raw,())
        binding=OperatingDscrBinding(profile_id='SYNTHETIC-COMPUTED-NOI-ANNUAL-DSCR-v1',definition_revision='SYNTHETIC-residential-chain-v1',
            noi_source_sha256=hashlib.sha256(run.compiled_raw).hexdigest(),loan_source_sha256=hashlib.sha256(loan_raw).hexdigest(),noi_run_sha256=run.noi_run.sha256,debt_run_sha256=debt.sha256,
            currency='USD',noi_period_ref=run.noi_run.payload['period_ref'],annual_equivalent_ref=loan['annual_equivalent_ref'],declared_annual_noi_basis_ref='SYNTHETIC-explicit-regular-year-basis')
        ratio=calculate_operating_dscr(run.compiled_raw,run.noi_run,loan_raw,(),debt,binding);self.assertEqual(ratio.payload['rational'],q(20,3))
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'chain.sqlite3'
            with EvidenceArchive(path)as a:
                ak=a.save_rental_noi(self.source,self.rental,raw(self.spec),run)
                bk=a.save_operating_dscr(run.compiled_raw,run.noi_run,loan_raw,(),debt,binding,ratio)
            with EvidenceArchive(path)as a:
                assembly=a.load_rental_noi(ak);bridge=a.load_operating_dscr(bk)
                self.assertEqual(assembly.run.noi_run.sha256,bridge.payload['binding']['noi_run_sha256'])
                self.assertEqual(hashlib.sha256(assembly.run.compiled_raw).hexdigest(),bridge.payload['noi_source_sha256'])
                self.assertEqual(bridge.run,ratio)
