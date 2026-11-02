"""Exact syntactic number decoding; these are not financial acceptance tests."""
from dataclasses import asdict, replace
from fractions import Fraction
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from miniuw_foundation import DraftStore, ValidationError
from miniuw_foundation.archive import (EvidenceArchive, archive_and_import,
    CorruptArchive, MissingEvidence, UnsupportedArchive)
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.intake import SCHEMA
from miniuw_foundation.normalization import (NumericProfile, normalize_synthetic,
    observe_normalization_freshness)
from miniuw_foundation.inputsheet import parse_synthetic_input_sheet
from inputsheet_fixture import native_workbook
from test_foundation import seed, claim


def profile(slot, **changes):
    values=dict(profile_id='SYNTHETIC-numeric-profile',definition_revision='fixture-v1',
        slot_id=slot,source_definition_ref='SYNTHETIC-definition-v1',decimal_mark='.',
        notation='decimal',trim_outer_whitespace=False,source_unit_literal='decimal',
        target_unit='decimal',quantity_kind='scalar',currency_literal=None,period_literal=None)
    values.update(changes)
    return NumericProfile(**values)


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:');self.addCleanup(self.store.close)
        self.archive=EvidenceArchive(':memory:');self.addCleanup(self.archive.close)
        self.blank=self.store.create('draft',seed())
        self.slot,self.other=list(self.blank.payload['input_claims'])[:2]
        self.spec=profile(self.slot)

    def record(self,identity='number',literal='0.1',**changes):
        return claim(identity,literal,self.slot,unit_literal='decimal',
            definition_ref='SYNTHETIC-definition-v1',**changes)

    def snapshot(self,records):
        # Use actual source bytes so archive replay can verify every record.
        payload=[{k:v for k,v in r.record().items() if k not in {'source_sha256','locator','claim_kind'}} for r in records]
        raw=json.dumps({'schema':SCHEMA,'claims':payload},ensure_ascii=False).encode()
        return archive_and_import(self.archive,self.store,'draft',expected_revision=0,
            operation_id='fixture',raw=raw).snapshot

    def result(self,snapshot,spec=None):
        return normalize_synthetic(snapshot,(spec or self.spec,)).payload['results'][self.slot]

    def rational(self,result):
        return Fraction(int(result['rational']['numerator']),int(result['rational']['denominator']))

    def test_decimal_exact_without_binary_rounding(self):
        result=self.result(self.snapshot([self.record(literal='0.10000000000000000001')]))
        self.assertEqual(self.rational(result),Fraction(10000000000000000001,10**20))
        self.assertEqual(result['state'],'decoded_synthetic')
        self.assertEqual(result['source_claims'][0]['literal'],'0.10000000000000000001')

    def test_comma_decimal_only_when_explicit(self):
        snapshot=self.snapshot([self.record(literal='0,0525')])
        self.assertEqual(self.result(snapshot)['state'],'blocked')
        decoded=self.result(snapshot,replace(self.spec,decimal_mark=','))
        self.assertEqual(self.rational(decoded),Fraction(21,400))

    def test_percent_suffix_exact_division_by_100(self):
        snapshot=self.snapshot([claim('percent','5%',self.slot,unit_literal='%',definition_ref='SYNTHETIC-definition-v1')])
        spec=replace(self.spec,source_unit_literal='%',target_unit='fraction',notation='percent_suffix')
        self.assertEqual(self.rational(self.result(snapshot,spec)),Fraction(1,20))
        self.assertEqual(self.store.get('draft'),snapshot)

    def test_zero_remains_zero_not_missing(self):
        result=self.result(self.snapshot([self.record(literal='-0.000')]))
        self.assertEqual(self.rational(result),0)
        self.assertEqual(result['source_claims'][0]['literal'],'-0.000')

    def test_blank_null_and_missing_never_default_to_zero(self):
        self.assertIsNone(self.result(self.blank)['rational'])
        snapshot=self.snapshot([self.record('null',None),self.record('empty','')])
        result=self.result(snapshot)
        self.assertEqual(result['state'],'blocked');self.assertIsNone(result['rational'])
        self.assertIn('missing_literal',result['blockers'])

    def test_blank_and_present_sources_require_explicit_resolution(self):
        result=self.result(self.snapshot([self.record('present','0'),self.record('blank',None)]))
        self.assertIn('blank_and_present_claims_require_resolution',result['blockers'])
        self.assertIsNone(result['rational'])

    def test_conflicting_even_equivalent_representations_not_auto_reconciled(self):
        result=self.result(self.snapshot([self.record('a','0.10'),self.record('b','0.1')]))
        self.assertIn('unresolved_source_conflict',result['blockers'])
        self.assertEqual(len(result['source_claims']),2)

    def test_matching_claims_retained_without_authenticating_them(self):
        result=self.result(self.snapshot([self.record('a'),self.record('b')]))
        self.assertEqual(self.rational(result),Fraction(1,10))
        self.assertEqual(len(result['source_claims']),2)
        self.assertFalse(result['financially_validated'])

    def test_whitespace_policy_is_explicit(self):
        snapshot=self.snapshot([self.record(literal=' 0.10 ')])
        self.assertEqual(self.result(snapshot)['state'],'blocked')
        self.assertEqual(self.rational(self.result(snapshot,replace(self.spec,trim_outer_whitespace=True))),Fraction(1,10))

    def test_grouping_nonfinite_exponent_formula_and_nonnumeric_are_blocked(self):
        for literal in ['1,234.56','1 000','NaN','Infinity','1e2','=1+1','1/2','1_000','5%']:
            with self.subTest(literal=literal):
                store=DraftStore(':memory:')
                try:
                    store.create('x',seed())
                    snapshot=store.append('x',expected_revision=0,operation_id='x',claims=[self.record(literal=literal)]).snapshot
                    self.assertEqual(self.result(snapshot)['state'],'blocked')
                finally:store.close()

    def test_percent_requires_suffix_and_contract_no_implicit_percent(self):
        snapshot=self.snapshot([claim('percent','5',self.slot,unit_literal='%',definition_ref='SYNTHETIC-definition-v1')])
        spec=replace(self.spec,source_unit_literal='%',target_unit='fraction',notation='percent_suffix')
        self.assertIn('explicit_percent_suffix_missing',self.result(snapshot,spec)['blockers'])
        identity=replace(self.spec,source_unit_literal='%',target_unit='%')
        self.assertEqual(self.rational(self.result(snapshot,identity)),5)

    def test_currency_symbol_does_not_supply_missing_currency(self):
        snapshot=self.snapshot([claim('money','1250',self.slot,unit_literal='$',definition_ref='SYNTHETIC-definition-v1')])
        spec=replace(self.spec,quantity_kind='money',currency_literal='USD',source_unit_literal='$',target_unit='$')
        result=self.result(snapshot,spec)
        self.assertIn('source_currency_literal_mismatch_or_missing',result['blockers'])
        self.assertIsNone(result['rational'])

    def test_periodic_money_requires_exact_source_currency_and_period(self):
        snapshot=self.snapshot([claim('money','1250.50',self.slot,unit_literal='USD/month',
            currency_literal='USD',period_literal='SYNTHETIC-period:month-1',definition_ref='SYNTHETIC-definition-v1')])
        spec=replace(self.spec,quantity_kind='money_per_period',currency_literal='USD',
            period_literal='SYNTHETIC-period:month-1',source_unit_literal='USD/month',target_unit='USD/month')
        self.assertEqual(self.rational(self.result(snapshot,spec)),Fraction(2501,2))
        for changed in [replace(spec,currency_literal='EUR'),replace(spec,period_literal='SYNTHETIC-period:month-2')]:
            self.assertEqual(self.result(snapshot,changed)['state'],'blocked')

    def test_unit_and_definition_identity_mismatch_blocked(self):
        snapshot=self.snapshot([self.record()])
        for spec in [replace(self.spec,source_unit_literal='fraction',target_unit='fraction'),
                     replace(self.spec,source_definition_ref='other-definition')]:
            self.assertEqual(self.result(snapshot,spec)['state'],'blocked')

    def test_no_inferred_unit_conversion_or_missing_profile_metadata(self):
        for changes in [dict(target_unit='annual'),dict(quantity_kind='money'),
            dict(quantity_kind='money_per_period',currency_literal='USD'),
            dict(decimal_mark='auto'),dict(profile_id='approved-policy'),
            dict(notation='scientific'),dict(trim_outer_whitespace=None)]:
            with self.assertRaises(ValidationError):replace(self.spec,**changes)

    def test_unknown_slot_criterion_and_duplicate_profiles_rejected(self):
        for profiles in [(replace(self.spec,slot_id='unknown'),),(self.spec,self.spec),
            (replace(self.spec,slot_id='YoC'),),[],()]:
            with self.assertRaises(ValidationError):normalize_synthetic(self.blank,profiles)

    def test_source_snapshot_and_run_are_immutable_and_pending(self):
        snapshot=self.snapshot([self.record()]);run=normalize_synthetic(snapshot,(self.spec,))
        copy=run.payload;copy['results'][self.slot]['rational']['numerator']='999'
        self.assertEqual(self.rational(run.payload['results'][self.slot]),Fraction(1,10))
        self.assertEqual(self.store.get('draft'),snapshot)
        self.assertFalse(run.payload['financially_normalized']);self.assertFalse(run.payload['run_ready'])
        self.assertFalse(run.payload['production_authorized']);self.assertEqual(run.payload['decision'],'PENDING')
        self.assertTrue(all(not v for v in snapshot.payload['criterion_claims'].values()))

    def test_freshness_observation_invalidates_source_or_profile_change(self):
        snapshot=self.snapshot([self.record()]);run=normalize_synthetic(snapshot,(self.spec,))
        self.assertTrue(observe_normalization_freshness(run,snapshot,(self.spec,))['entire_run_current'])
        self.assertFalse(observe_normalization_freshness(run,snapshot,(replace(self.spec,definition_revision='v2'),))['entire_run_current'])
        newer=self.store.append('draft',expected_revision=1,operation_id='unrelated',
            claims=[claim('unrelated','text',self.other)]).snapshot
        report=observe_normalization_freshness(run,newer,(self.spec,))
        self.assertFalse(report['entire_run_current']);self.assertFalse(report['publication_authorized'])

    def test_native_sheet_missing_currency_remains_blocked(self):
        raw=native_workbook({'C8':{'value':'1250'}})
        snapshot=archive_and_import(self.archive,self.store,'draft',expected_revision=0,operation_id='native',raw=raw).snapshot
        spec=profile('INPUT_C8',quantity_kind='money',source_unit_literal='$',target_unit='$',
            currency_literal='USD',source_definition_ref='input-sheet-layout-v1')
        result=normalize_synthetic(snapshot,(spec,)).payload['results']['INPUT_C8']
        self.assertEqual(result['state'],'blocked')
        self.assertIsNone(result['rational'])

    def test_archive_reopen_recovers_profiles_sources_and_exact_rational(self):
        snapshot=self.snapshot([self.record()]);run=normalize_synthetic(snapshot,(self.spec,))
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'archive.sqlite3'
            with EvidenceArchive(path) as archive:
                for c in snapshot.slot('input',self.slot)['claims']:
                    archive.put_source(self.archive.get_source(c['source_sha256']))
                sha=archive.save_normalization(snapshot,(self.spec,),run)
                self.assertEqual(sha,archive.save_normalization(snapshot,(self.spec,),run))
            with EvidenceArchive(path) as archive:
                restored=archive.load_normalization(sha)
                self.assertEqual(restored.snapshot,snapshot);self.assertEqual(restored.profiles,(self.spec,))
                self.assertEqual(restored.run,run)

    def test_archive_rejects_forged_rational_even_with_updated_hash(self):
        snapshot=self.snapshot([self.record()]);run=normalize_synthetic(snapshot,(self.spec,))
        payload=run.payload;payload['results'][self.slot]['rational']['numerator']='99'
        encoded=canonical(payload);forged=replace(run,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):self.archive.save_normalization(snapshot,(self.spec,),forged)
        sha=self.archive.save_normalization(snapshot,(self.spec,),run)
        bundle=json.loads(self.archive.read_bundle_bytes(sha));bundle['run']=asdict(forged)
        with self.archive._transaction():tampered=self.archive._put('bundle',canonical(bundle).encode())
        with self.assertRaises(CorruptArchive):self.archive.load_normalization(tampered)

    def test_archive_missing_source_blocks_normalization_capture(self):
        snapshot=self.store.append('draft',expected_revision=0,operation_id='declared-only',claims=[self.record()]).snapshot
        with self.assertRaises(MissingEvidence):self.archive.save_normalization(snapshot,(self.spec,),normalize_synthetic(snapshot,(self.spec,)))

    def test_archive_rollback_before_commit_leaves_no_bundle(self):
        snapshot=self.snapshot([self.record()]);run=normalize_synthetic(snapshot,(self.spec,))
        with patch.object(self.archive,'_commit',side_effect=RuntimeError('pre-commit fault')):
            with self.assertRaises(RuntimeError):self.archive.save_normalization(snapshot,(self.spec,),run)
        self.assertEqual(self.archive._connection.execute("SELECT COUNT(*) FROM objects WHERE kind='bundle'").fetchone()[0],0)
        self.archive.load_normalization(self.archive.save_normalization(snapshot,(self.spec,),run))

    def test_changed_decoder_version_blocks_replay_but_bytes_retrievable(self):
        snapshot=self.snapshot([self.record()]);run=normalize_synthetic(snapshot,(self.spec,))
        sha=self.archive.save_normalization(snapshot,(self.spec,),run)
        payload=json.loads(self.archive.read_bundle_bytes(sha));payload['normalizer_sha256']='0'*64
        with self.archive._transaction():changed=self.archive._put('bundle',canonical(payload).encode())
        with self.assertRaises(UnsupportedArchive):self.archive.load_normalization(changed)
        self.assertTrue(self.archive.read_bundle_bytes(changed))

    def test_source_or_run_corruption_is_not_accepted(self):
        snapshot=self.snapshot([self.record()]);run=normalize_synthetic(snapshot,(self.spec,))
        with self.assertRaises(ValidationError):normalize_synthetic(replace(snapshot,sha256='0'*64),(self.spec,))
        with self.assertRaises(ValidationError):observe_normalization_freshness(replace(run,sha256='0'*64),snapshot,(self.spec,))

    def test_profile_declaration_order_does_not_change_output(self):
        snapshot=self.store.append('draft',expected_revision=0,operation_id='fixture',claims=[self.record(),
            claim('b','2',self.other,unit_literal='decimal',definition_ref='SYNTHETIC-definition-v1')]).snapshot
        other=replace(self.spec,profile_id='SYNTHETIC-other',slot_id=self.other)
        self.assertEqual(normalize_synthetic(snapshot,(self.spec,other)),normalize_synthetic(snapshot,(other,self.spec)))

if __name__=='__main__':unittest.main()
