from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,tempfile,unittest
from miniuw_foundation import ValidationError
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_dscr import OperatingDscrBinding,calculate_operating_dscr
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence

R=Path(__file__).resolve().parents[1]
def raw(p):return json.dumps(p).encode()
def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}


class OperatingDscrTests(unittest.TestCase):
    def setUp(self):
        self.noi=(R/'templates/synthetic-operating-noi.json').read_bytes();self.loan=(R/'templates/synthetic-operating-dscr-loan.json').read_bytes()
        self.nr=produce_operating_noi(self.noi);self.dr=produce_debt_service(self.loan,());self.binding=OperatingDscrBinding(**json.loads((R/'templates/synthetic-operating-dscr-binding.json').read_bytes()))
    def run_case(self,binding=None,noi=None,loan=None):
        n=self.noi if noi is None else noi;l=self.loan if loan is None else loan
        return calculate_operating_dscr(n,produce_operating_noi(n),l,(),produce_debt_service(l,()),binding or self.binding)
    def rebind(self,noi,loan):
        nr=produce_operating_noi(noi);dr=produce_debt_service(loan,())
        return replace(self.binding,noi_source_sha256=hashlib.sha256(noi).hexdigest(),loan_source_sha256=hashlib.sha256(loan).hexdigest(),noi_run_sha256=nr.sha256,debt_run_sha256=dr.sha256)

    def test_exact_ratio_consumes_computed_noi_and_regular_annual_service(self):
        p=self.run_case().payload;self.assertEqual(p['computed_noi'],q(1000));self.assertEqual(p['annual_service_equivalent'],q(1200));self.assertEqual(p['rational'],q(5,6));self.assertEqual(p['state'],'computed_synthetic')
        self.assertIn('not_dated_cash_or_balloon',p['interpretation_label'])

    def test_negative_computed_noi_produces_signed_ratio_without_fail(self):
        p=json.loads(self.noi);p['income_rows']=p['income_rows'][:1];p['income_rows'][0]['value']=q(0);p['expense_rows'][0]['value']=q(100);p['tax_floor']['value']=q(20);n=raw(p)
        r=self.run_case(self.rebind(n,self.loan),noi=n).payload;self.assertEqual(r['rational'],q(-1,10));self.assertEqual(r['decision'],'PENDING')

    def test_missing_tax_parameter_blocks_noi_and_downstream_ratio(self):
        p=json.loads(self.noi);p['tax_coefficient']['value']=None;n=raw(p)
        r=self.run_case(self.rebind(n,self.loan),noi=n).payload;self.assertIsNone(r['rational']);self.assertIn('computed_noi_unavailable',r['blockers']);self.assertIn('/tax_coefficient:coefficient_missing',r['noi_blockers'])

    def test_forged_noi_or_debt_result_is_rejected_even_with_new_hash(self):
        for family in ['noi','debt']:
            original=self.nr if family=='noi'else self.dr;p=original.payload
            if family=='noi':p['noi']=q(9999)
            else:p['annual_sizing']['amount']=q(1)
            encoded=canonical(p);forged=replace(original,payload_json=encoded,sha256=digest(encoded))
            with self.assertRaises(ValidationError):calculate_operating_dscr(self.noi,forged if family=='noi'else self.nr,self.loan,(),forged if family=='debt'else self.dr,self.binding)

    def test_all_source_and_run_identity_bindings_are_checked(self):
        for field in ['noi_source_sha256','loan_source_sha256','noi_run_sha256','debt_run_sha256']:
            r=self.run_case(replace(self.binding,**{field:'0'*64})).payload
            self.assertIsNone(r['rational']);self.assertIn(field+'_mismatch',r['blockers'])

    def test_cross_deal_or_run_context_is_not_mixed(self):
        p=json.loads(self.loan);p['context']['run_id']='SYNTHETIC-other-run';l=raw(p)
        r=self.run_case(self.rebind(self.noi,l),loan=l).payload;self.assertIn('producer_context_mismatch',r['blockers']);self.assertIsNone(r['rational'])

    def test_currency_mismatch_stays_blocked_without_conversion(self):
        p=json.loads(self.loan);p['currency']='EUR';l=raw(p)
        r=self.run_case(self.rebind(self.noi,l),loan=l).payload;self.assertIn('producer_currency_mismatch',r['blockers']);self.assertIsNone(r['rational'])

    def test_period_references_and_annual_basis_are_explicit(self):
        for field,value in [('noi_period_ref','other'),('annual_equivalent_ref','other'),('declared_annual_noi_basis_ref',None)]:
            r=self.run_case(replace(self.binding,**{field:value})).payload;self.assertIsNone(r['rational']);self.assertTrue(r['blockers'])

    def test_matching_named_binding_does_not_hide_actual_service_period_mismatch(self):
        p=json.loads(self.loan);p['annual_equivalent_ref']='SYNTHETIC-other-year';l=raw(p)
        b=replace(self.rebind(self.noi,l),annual_equivalent_ref='SYNTHETIC-other-year')
        r=self.run_case(b,loan=l).payload;self.assertIn('noi_and_annual_equivalent_period_mismatch',r['blockers'])

    def test_missing_or_nonpositive_service_never_divides_or_fails_economically(self):
        for value in [None,q(0),q(-1)]:
            p=json.loads(self.loan);p['principal']=value;l=raw(p)
            r=self.run_case(self.rebind(self.noi,l),loan=l).payload;self.assertIsNone(r['rational']);self.assertTrue(any('service'in x for x in r['blockers']));self.assertEqual(r['decision'],'PENDING')

    def test_profile_and_hash_shape_are_validated_without_accepting_dated_profile(self):
        with self.assertRaises(ValidationError):replace(self.binding,profile_id='dated_contractual_due')
        with self.assertRaises(ValidationError):replace(self.binding,noi_source_sha256='not-a-hash')
        with self.assertRaises(ValidationError):replace(self.binding,definition_revision='')

    def test_no_bank_minimum_adoption_or_cash_paid_claim(self):
        p=self.run_case().payload
        for key in ['annual_noi_basis_financially_verified','tax_policy_adopted','loan_terms_financially_verified','cash_paid_verified','bank_dscr_minimum_applied','investment_criterion_applied','financially_validated','production_authorized']:
            self.assertFalse(p[key])
        self.assertEqual(p['decision'],'PENDING');self.assertTrue(p['producer_arithmetic_replayed'])

    def test_reopened_archive_replays_both_producers_and_exact_bridge(self):
        run=self.run_case()
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'bridge.sqlite3'
            with EvidenceArchive(path)as a:
                key=a.save_operating_dscr(self.noi,self.nr,self.loan,(),self.dr,self.binding,run)
                self.assertEqual(key,a.save_operating_dscr(self.noi,self.nr,self.loan,(),self.dr,self.binding,run))
            with EvidenceArchive(path)as a:
                bundle=a.load_operating_dscr(key);self.assertEqual(bundle.run,run)
                self.assertEqual(a.get_operating_noi_source(bundle.payload['noi_source_sha256']),self.noi);self.assertEqual(a.get_loan_source(bundle.payload['loan_source_sha256']),self.loan)

    def test_forged_bridge_and_atomic_capture_failure(self):
        run=self.run_case();p=run.payload;p['rational']=q(9999);encoded=canonical(p);forged=replace(run,payload_json=encoded,sha256=digest(encoded))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_operating_dscr(self.noi,self.nr,self.loan,(),self.dr,self.binding,forged)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_operating_dscr(self.noi,self.nr,self.loan,(),self.dr,self.binding,run)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_operating_dscr(self.noi,self.nr,self.loan,(),self.dr,self.binding,run);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_operating_dscr(bad)

    def test_missing_evidence_and_incompatible_versions_are_explicit(self):
        run=self.run_case()
        with EvidenceArchive(':memory:')as a:
            key=a.save_operating_dscr(self.noi,self.nr,self.loan,(),self.dr,self.binding,run);body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_operating_dscr(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',run.payload['noi_source_sha256']))
            with self.assertRaises(MissingEvidence):a.load_operating_dscr(key)
