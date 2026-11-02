"""T09 declared-upstream DSCR profile; no certification of NOI or credit decisions."""
from dataclasses import asdict, replace
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from miniuw_foundation import DraftStore, ValidationError
from miniuw_foundation.archive import EvidenceArchive, archive_and_import, MissingEvidence, CorruptArchive, UnsupportedArchive
from miniuw_foundation.calculations import CalculationGraph,CalculationNode,Operand,calculate_synthetic
from miniuw_foundation.normalization import NumericProfile,normalize_synthetic
from miniuw_foundation.scoped_profiles import PROFILE_ID,DscrBinding,dispatch_scoped_profile,definition_sources
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.intake import SCHEMA
from test_foundation import seed


class ScopedProfileTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:');self.addCleanup(self.store.close)
        self.archive=EvidenceArchive(':memory:');self.addCleanup(self.archive.close)
        self.store.create('initial',seed());self.counter=0
        self.default=self.case()

    def case(self,noi='1250',service='1000',unit='currency/declared-period',currency='USD',period='SYNTHETIC-period-1',changes=None):
        self.counter+=1;identity='profile-'+str(self.counter);blank=self.store.create(identity,seed())
        slots=list(blank.payload['input_claims'])[1:3];rows=[];profiles=[];nodes=[]
        for i,(role,literal) in enumerate([('declared_noi',noi),('declared_service',service)]):
            row={'claim_id':'fixture-'+role,'slot_kind':'input','slot_id':slots[i],'literal':literal,
                'unit_literal':unit,'currency_literal':currency,'period_literal':period,
                'definition_ref':'SYNTHETIC-provided-'+role+'-v1'}
            row.update((changes or {}).get(role,{}));rows.append(row)
            profiles.append(NumericProfile(profile_id='SYNTHETIC-'+role,definition_revision='fixture-v1',
                slot_id=slots[i],source_definition_ref=row['definition_ref'],decimal_mark='.',notation='decimal',
                trim_outer_whitespace=False,source_unit_literal=row['unit_literal'],target_unit=row['unit_literal'],
                quantity_kind='money_per_period',currency_literal=row['currency_literal'],period_literal=row['period_literal']))
            nodes.append(CalculationNode(node_id=role,definition_revision='SYNTHETIC-provided-'+role+'-v1',
                operation='identity',operands=(Operand(kind='input',ref=slots[i]),)))
        raw=json.dumps({'schema':SCHEMA,'claims':rows}).encode()
        snapshot=archive_and_import(self.archive,self.store,identity,expected_revision=0,operation_id='source',raw=raw).snapshot
        profiles=tuple(profiles);numeric=normalize_synthetic(snapshot,profiles)
        graph=CalculationGraph(graph_id='SYNTHETIC-provided-amounts',definition_revision='fixture-v1',nodes=tuple(nodes))
        upstream=calculate_synthetic(snapshot,profiles,numeric,graph)
        binding=DscrBinding(profile_id=PROFILE_ID,definition_revision='candidate-dscr-v1',noi_node='declared_noi',
            debt_service_node='declared_service',noi_producer_revision=nodes[0].definition_revision,
            debt_service_producer_revision=nodes[1].definition_revision,noi_basis_ref='SYNTHETIC-declared-NOI-basis',
            service_basis_ref='SYNTHETIC-declared-service-basis',service_basis='declared_dated_period',
            expected_unit=unit,currency=currency,period_ref=period)
        return snapshot,profiles,numeric,graph,upstream,binding

    def run_case(self,case=None):return dispatch_scoped_profile(*(case or self.default))

    def number(self,run):
        value=run.payload['rational']
        return None if value is None else Fraction(int(value['numerator']),int(value['denominator']))

    def test_documented_ratio_compiles_and_replays_exactly(self):
        run=self.run_case()
        self.assertEqual(self.number(run),Fraction(5,4))
        self.assertEqual(run.payload['state'],'computed_synthetic')
        self.assertIsNotNone(run.payload['compiled_calculation'])
        self.assertEqual(run.payload['interpretation_label'],'synthetic_dscr_for_declared_dated_period')

    def test_definition_evidence_has_exact_document_hashes_and_locations(self):
        root=Path(__file__).resolve().parents[1]
        import hashlib
        evidence=definition_sources()
        self.assertEqual(evidence[0]['line'],41)
        for reference in evidence:
            self.assertEqual(hashlib.sha256((root/reference['path']).read_bytes()).hexdigest(),reference['sha256'])
        self.assertEqual(self.run_case().payload['definition_sources'],evidence)

    def test_service_zero_is_unresolved_even_with_zero_noi(self):
        for noi in ['0','100']:
            run=self.run_case(self.case(noi=noi,service='0'))
            self.assertEqual(run.payload['state'],'blocked');self.assertIsNone(self.number(run))
            self.assertIn('positive_debt_service_required_for_this_profile',run.payload['blockers'])
            self.assertEqual(run.payload['decision'],'PENDING')

    def test_negative_service_not_treated_as_valid_debt_service(self):
        run=self.run_case(self.case(service='-1000'))
        self.assertIsNone(self.number(run));self.assertEqual(run.payload['state'],'blocked')

    def test_negative_and_zero_noi_preserve_arithmetic_without_fail(self):
        for literal,expected in [('0',Fraction(0)),('-500',Fraction(-1,2))]:
            run=self.run_case(self.case(noi=literal))
            self.assertEqual(self.number(run),expected)
            self.assertEqual(run.payload['decision'],'PENDING')

    def test_missing_upstream_amount_stays_blocked_without_default(self):
        run=self.run_case(self.case(service=None))
        self.assertIn('debt_service_upstream_blocked',run.payload['blockers'])
        self.assertIsNone(run.payload['compiled_calculation'])
        self.assertIsNone(self.number(run))

    def test_period_currency_and_unit_mismatches_are_not_equated(self):
        for change in [{'period_literal':'SYNTHETIC-period-2'},{'currency_literal':'EUR'},{'unit_literal':'currency/other-period'}]:
            run=self.run_case(self.case(changes={'declared_service':change}))
            self.assertIn('debt_service_quantity_unit_currency_or_period_mismatch',run.payload['blockers'])
            self.assertEqual(run.payload['state'],'blocked')

    def test_principal_stock_not_substituted_for_periodic_service(self):
        case=list(self.default)
        profiles=tuple(replace(p,quantity_kind='money') if p.slot_id==case[1][1].slot_id else p for p in case[1])
        case[1]=profiles;case[2]=normalize_synthetic(case[0],profiles)
        case[4]=calculate_synthetic(case[0],profiles,case[2],case[3])
        self.assertIn('debt_service_quantity_unit_currency_or_period_mismatch',self.run_case(case).payload['blockers'])

    def test_changed_producer_revision_is_not_silently_accepted(self):
        case=list(self.default);case[-1]=replace(case[-1],noi_producer_revision='different-revision')
        self.assertIn('noi_producer_revision_mismatch',self.run_case(case).payload['blockers'])

    def test_basis_references_are_retained_without_authenticating_them(self):
        run=self.run_case();binding=self.default[-1]
        self.assertEqual(run.payload['binding']['noi_basis_ref'],binding.noi_basis_ref)
        self.assertFalse(run.payload['upstream_contracts_financially_verified'])
        self.assertTrue(run.payload['producer_role_claims_only'])
        self.assertFalse(run.payload['policy_adopted']);self.assertFalse(run.payload['financially_validated'])

    def test_annual_sizing_equivalent_is_distinct_and_requires_explicit_unit(self):
        case=list(self.case(unit='currency/annual-sizing-equivalent',period='SYNTHETIC-annual-equivalent-1'))
        case[-1]=replace(case[-1],service_basis='regular_annual_sizing_equivalent')
        run=self.run_case(case)
        self.assertEqual(self.number(run),Fraction(5,4))
        self.assertEqual(run.payload['interpretation_label'],'synthetic_sizing_dscr_equivalent')
        with self.assertRaises(ValidationError):replace(self.default[-1],service_basis='regular_annual_sizing_equivalent')

    def test_unknown_profile_basis_identical_roles_and_missing_bindings_rejected(self):
        for changes in [dict(profile_id='generic-ratio'),dict(service_basis='automatic'),
            dict(debt_service_node='declared_noi'),dict(noi_basis_ref='')]:
            with self.assertRaises(ValidationError):replace(self.default[-1],**changes)
        case=list(self.default);case[-1]=replace(case[-1],noi_node='unknown')
        with self.assertRaises(ValidationError):self.run_case(case)

    def test_forged_or_cross_snapshot_upstream_calculation_rejected(self):
        case=list(self.default);payload=case[4].payload
        payload['results']['declared_noi']['rational']['numerator']='999'
        encoded=canonical(payload);case[4]=replace(case[4],payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):self.run_case(case)
        case=list(self.case());case[4]=self.default[4]
        with self.assertRaises(ValidationError):self.run_case(case)

    def test_result_copy_does_not_mutate_evidence_inputs_or_criteria(self):
        run=self.run_case();copy=run.payload;copy['rational']['numerator']='999'
        self.assertEqual(self.number(run),Fraction(5,4))
        self.assertEqual(self.store.get(self.default[0].draft_id),self.default[0])
        self.assertTrue(all(not v for v in self.default[0].payload['criterion_claims'].values()))
        self.assertFalse(run.payload['run_ready']);self.assertFalse(run.payload['production_authorized'])
        self.assertEqual(run.payload['decision'],'PENDING')

    def test_archived_profile_reopens_and_reproduces_complete_chain(self):
        case=self.default;run=self.run_case()
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'scoped.sqlite3'
            with EvidenceArchive(path) as archive:
                for claims in case[0].payload['input_claims'].values():
                    for c in claims:archive.put_source(self.archive.get_source(c['source_sha256']))
                sha=archive.save_scoped_profile(*case,run)
                self.assertEqual(sha,archive.save_scoped_profile(*case,run))
            with EvidenceArchive(path) as archive:
                restored=archive.load_scoped_profile(sha)
                self.assertEqual(restored.run,run);self.assertEqual(restored.upstream,case[4])
                self.assertEqual(restored.snapshot,case[0]);self.assertEqual(restored.binding,case[-1])

    def test_altered_ratio_with_recomputed_hash_fails_replay(self):
        case=self.default;run=self.run_case();payload=run.payload;payload['rational']['numerator']='99'
        encoded=canonical(payload);forged=replace(run,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):self.archive.save_scoped_profile(*case,forged)
        sha=self.archive.save_scoped_profile(*case,run)
        bundle=json.loads(self.archive.read_bundle_bytes(sha));bundle['run']=asdict(forged)
        with self.archive._transaction():altered=self.archive._put('bundle',canonical(bundle).encode())
        with self.assertRaises(CorruptArchive):self.archive.load_scoped_profile(altered)

    def test_missing_source_and_precommit_failure_do_not_create_success(self):
        case=self.default;run=self.run_case()
        with EvidenceArchive(':memory:') as empty:
            with self.assertRaises(MissingEvidence):empty.save_scoped_profile(*case,run)
        with patch.object(self.archive,'_commit',side_effect=RuntimeError('pre-commit failure')):
            with self.assertRaises(RuntimeError):self.archive.save_scoped_profile(*case,run)
        self.assertEqual(self.archive._connection.execute("SELECT COUNT(*) FROM objects WHERE kind='bundle'").fetchone()[0],0)
        self.archive.load_scoped_profile(self.archive.save_scoped_profile(*case,run))

    def test_code_or_definition_revision_change_requires_compatible_replay(self):
        sha=self.archive.save_scoped_profile(*self.default,self.run_case())
        for field in ['profile_engine_sha256','calculator_sha256','normalizer_sha256','definition_sources']:
            bundle=json.loads(self.archive.read_bundle_bytes(sha))
            bundle[field]=[] if field=='definition_sources' else '0'*64
            with self.archive._transaction():altered=self.archive._put('bundle',canonical(bundle).encode())
            with self.assertRaises(UnsupportedArchive):self.archive.load_scoped_profile(altered)
            self.assertTrue(self.archive.read_bundle_bytes(altered))

if __name__=='__main__':unittest.main()
