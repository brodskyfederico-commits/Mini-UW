"""T08 exact arithmetic and evidence tests, without financial policy acceptance."""
from dataclasses import asdict, replace
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from miniuw_foundation import DraftStore, ValidationError
from miniuw_foundation.archive import EvidenceArchive, archive_and_import, CorruptArchive, MissingEvidence, UnsupportedArchive
from miniuw_foundation.calculations import (Operand, CalculationNode, CalculationGraph,
    calculate_synthetic, observe_calculation_freshness, graph_from_record)
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.intake import SCHEMA
from miniuw_foundation.normalization import NumericProfile, normalize_synthetic
from test_foundation import seed, claim


def inp(slot):return Operand(kind='input',ref=slot)
def out(node):return Operand(kind='node',ref=node)
def node(identity, operation, *operands):
    return CalculationNode(node_id=identity,definition_revision='fixture-v1',operation=operation,operands=tuple(operands))
def graph(*nodes):
    return CalculationGraph(graph_id='SYNTHETIC-arithmetic',definition_revision='fixture-v1',nodes=tuple(nodes))


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:');self.addCleanup(self.store.close)
        self.archive=EvidenceArchive(':memory:');self.addCleanup(self.archive.close)
        blank=self.store.create('initial',seed())
        self.a,self.factor,self.c,self.zero,self.unused=list(blank.payload['input_claims'])[:5]
        self.counter=0
        self.snapshot,self.profiles,self.numeric=self.case()

    def case(self, row_changes=None, profile_changes=None):
        self.counter+=1;identity='draft-'+str(self.counter)
        self.store.create(identity,seed())
        rows=[];profiles=[]
        for i,(slot,literal) in enumerate([(self.a,'10.1'),(self.factor,'0.2'),(self.c,'2.2'),(self.zero,'0')]):
            row={'claim_id':'claim-'+str(i),'slot_kind':'input','slot_id':slot,'literal':literal,
                'unit_literal':'fraction' if i==1 else 'currency/month',
                'currency_literal':None if i==1 else 'USD','period_literal':None if i==1 else 'SYNTHETIC-month-1',
                'definition_ref':'SYNTHETIC-definition-v1'}
            row.update((row_changes or {}).get(slot,{}));rows.append(row)
            values={'profile_id':'SYNTHETIC-profile-'+slot,'definition_revision':'fixture-v1',
                'slot_id':slot,'source_definition_ref':row['definition_ref'],'decimal_mark':'.',
                'notation':'decimal','trim_outer_whitespace':False,'source_unit_literal':row['unit_literal'],
                'target_unit':row['unit_literal'],'quantity_kind':'scalar' if i==1 else 'money_per_period',
                'currency_literal':row['currency_literal'],'period_literal':row['period_literal']}
            values.update((profile_changes or {}).get(slot,{}));profiles.append(NumericProfile(**values))
        raw=json.dumps({'schema':SCHEMA,'claims':rows}).encode()
        snapshot=archive_and_import(self.archive,self.store,identity,expected_revision=0,operation_id='seed',raw=raw).snapshot
        profiles=tuple(profiles)
        return snapshot,profiles,normalize_synthetic(snapshot,profiles)

    def run_graph(self,g,case=None):
        snapshot,profiles,numeric=case or (self.snapshot,self.profiles,self.numeric)
        return calculate_synthetic(snapshot,profiles,numeric,g)

    def rational(self,run,key):
        value=run.payload['results'][key]['rational']
        return None if value is None else Fraction(int(value['numerator']),int(value['denominator']))

    def test_exact_sum_and_difference_preserve_quantity(self):
        g=graph(node('sum','sum',inp(self.a),inp(self.c)),node('difference','difference',inp(self.a),inp(self.c)))
        run=self.run_graph(g)
        self.assertEqual(self.rational(run,'sum'),Fraction(123,10))
        self.assertEqual(self.rational(run,'difference'),Fraction(79,10))
        self.assertEqual(run.payload['results']['sum']['quantity'],
            {'kind':'money_per_period','unit':'currency/month','currency':'USD','period':'SYNTHETIC-month-1'})

    def test_scale_and_ratio_exact_with_declared_fraction(self):
        g=graph(node('scale','scale',inp(self.a),inp(self.factor)),node('ratio','ratio',inp(self.a),inp(self.c)))
        run=self.run_graph(g)
        self.assertEqual(self.rational(run,'scale'),Fraction(101,50))
        self.assertEqual(self.rational(run,'ratio'),Fraction(101,22))
        self.assertEqual(run.payload['results']['ratio']['quantity']['unit'],'fraction')
        self.assertIsNone(run.payload['results']['ratio']['quantity']['currency'])

    def test_multistep_graph_topological_execution_and_lineage(self):
        g=graph(node('ratio','ratio',out('difference'),inp(self.a)),
            node('difference','difference',inp(self.a),out('scaled')),
            node('scaled','scale',inp(self.a),inp(self.factor)))
        run=self.run_graph(g)
        self.assertEqual(self.rational(run,'ratio'),Fraction(4,5))
        self.assertEqual(run.payload['results']['difference']['lineage'][1]['fingerprint'],run.payload['results']['scaled']['fingerprint'])

    def test_zero_denominator_blocks_descendants_but_not_independent_branch(self):
        g=graph(node('bad','ratio',inp(self.a),inp(self.zero)),node('child','identity',out('bad')),
            node('independent','identity',inp(self.c)))
        run=self.run_graph(g)
        self.assertIsNone(self.rational(run,'bad'))
        self.assertIn('division_by_zero_unresolved',run.payload['results']['bad']['blockers'])
        self.assertEqual(run.payload['results']['child']['state'],'blocked')
        self.assertEqual(self.rational(run,'independent'),Fraction(11,5))
        self.assertEqual(run.payload['decision'],'PENDING')

    def test_signed_values_and_zero_are_not_domain_policy(self):
        case=self.case({self.a:{'literal':'0'},self.c:{'literal':'-2.2'}})
        g=graph(node('ratio','ratio',inp(self.a),inp(self.c)),node('difference','difference',inp(self.a),inp(self.c)))
        run=self.run_graph(g,case)
        self.assertEqual(self.rational(run,'ratio'),0)
        self.assertEqual(self.rational(run,'difference'),Fraction(11,5))

    def test_currency_mismatch_blocked_even_when_both_numbers_decode(self):
        case=self.case({self.c:{'currency_literal':'EUR'}})
        self.assertEqual(case[2].payload['results'][self.c]['state'],'decoded_synthetic')
        run=self.run_graph(graph(node('sum','sum',inp(self.a),inp(self.c))),case)
        self.assertIn('incompatible_quantity_unit_currency_or_period',run.payload['results']['sum']['blockers'])

    def test_period_and_unit_mismatches_are_not_converted(self):
        g=graph(node('sum','sum',inp(self.a),inp(self.c)))
        for changes in [{self.c:{'period_literal':'SYNTHETIC-month-2'}},{self.c:{'unit_literal':'currency/year'}}]:
            run=self.run_graph(g,self.case(changes))
            self.assertEqual(run.payload['results']['sum']['state'],'blocked')

    def test_quantity_kind_mismatch_is_not_ignored(self):
        case=self.case(profile_changes={self.c:{'quantity_kind':'money'}})
        run=self.run_graph(graph(node('sum','sum',inp(self.a),inp(self.c))),case)
        self.assertEqual(run.payload['results']['sum']['state'],'blocked')

    def test_scalar_decimal_is_not_implicitly_a_fraction_scale(self):
        case=self.case({self.factor:{'unit_literal':'decimal'}})
        run=self.run_graph(graph(node('scale','scale',inp(self.a),inp(self.factor))),case)
        self.assertIn('scale_requires_explicit_dimensionless_fraction',run.payload['results']['scale']['blockers'])

    def test_missing_input_blocks_without_zero_default(self):
        run=self.run_graph(graph(node('missing','identity',inp(self.a))),self.case({self.a:{'literal':None}}))
        self.assertIsNone(self.rational(run,'missing'))
        self.assertIn('input_blocked:'+self.a,run.payload['results']['missing']['blockers'])

    def test_conflicting_claims_remain_blocked(self):
        newer=self.store.append(self.snapshot.draft_id,expected_revision=1,operation_id='conflict',claims=[
            claim('conflict','10.2',self.a,unit_literal='currency/month',currency_literal='USD',
                period_literal='SYNTHETIC-month-1',definition_ref='SYNTHETIC-definition-v1')]).snapshot
        numeric=normalize_synthetic(newer,self.profiles)
        run=self.run_graph(graph(node('value','identity',inp(self.a))),(newer,self.profiles,numeric))
        self.assertEqual(run.payload['results']['value']['state'],'blocked')

    def test_graph_input_requires_explicit_profile(self):
        profiles=tuple(p for p in self.profiles if p.slot_id!=self.a)
        numeric=normalize_synthetic(self.snapshot,profiles)
        with self.assertRaises(ValidationError):calculate_synthetic(self.snapshot,profiles,numeric,graph(node('value','identity',inp(self.a))))

    def test_numeric_run_from_other_snapshot_or_forged_number_rejected(self):
        g=graph(node('value','identity',inp(self.a)))
        other=self.case()
        with self.assertRaises(ValidationError):calculate_synthetic(other[0],other[1],self.numeric,g)
        payload=self.numeric.payload;payload['results'][self.a]['rational']['numerator']='99'
        encoded=canonical(payload);forged=replace(self.numeric,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):calculate_synthetic(self.snapshot,self.profiles,forged,g)

    def test_graph_order_and_record_roundtrip_are_deterministic(self):
        g=graph(node('a','identity',inp(self.a)),node('b','identity',inp(self.c)))
        reordered=replace(g,nodes=tuple(reversed(g.nodes)))
        self.assertEqual(self.run_graph(g),self.run_graph(reordered))
        self.assertEqual(graph_from_record(g.record()).sha256,g.sha256)
        with self.assertRaises(ValidationError):graph_from_record(dict(g.record(),approved=True))

    def test_cycles_unknown_nodes_and_duplicate_ids_rejected(self):
        for nodes in [(node('a','identity',out('a')),),
            (node('a','identity',out('b')),node('b','identity',out('a'))),
            (node('a','identity',out('unknown')),),
            (node('same','identity',inp(self.a)),node('same','identity',inp(self.c)))]:
            with self.assertRaises(ValidationError):graph(*nodes)

    def test_unsupported_operation_constants_empty_sum_and_wrong_arity_rejected(self):
        for operation,operands in [('formula',(inp(self.a),)),('sum',()),('ratio',(inp(self.a),))]:
            with self.assertRaises(ValidationError):node('bad',operation,*operands)
        with self.assertRaises(ValidationError):Operand(kind='constant',ref='12')
        with self.assertRaises(ValidationError):CalculationGraph(graph_id='financial-policy',definition_revision='v1',nodes=(node('x','identity',inp(self.a)),))

    def test_result_is_immutable_pending_and_does_not_change_store_or_criteria(self):
        g=graph(node('value','identity',inp(self.a)));run=self.run_graph(g)
        copy=run.payload;copy['results']['value']['rational']['numerator']='999'
        self.assertEqual(self.rational(run,'value'),Fraction(101,10))
        self.assertEqual(self.store.get(self.snapshot.draft_id),self.snapshot)
        self.assertTrue(all(not v for v in self.snapshot.payload['criterion_claims'].values()))
        self.assertFalse(run.payload['financially_validated']);self.assertFalse(run.payload['run_ready'])
        self.assertFalse(run.payload['production_authorized']);self.assertEqual(run.payload['decision'],'PENDING')

    def test_profile_change_invalidates_affected_branch_and_descendants(self):
        g=graph(node('a','identity',inp(self.a)),node('c','identity',inp(self.c)),node('total','sum',out('a'),out('c')))
        run=self.run_graph(g)
        profiles=tuple(replace(p,definition_revision='fixture-v2') if p.slot_id==self.a else p for p in self.profiles)
        numeric=normalize_synthetic(self.snapshot,profiles)
        report=observe_calculation_freshness(run,self.snapshot,profiles,numeric,g)
        self.assertEqual(report['affected_nodes'],['a','total']);self.assertEqual(report['unchanged_nodes'],['c'])
        self.assertFalse(report['entire_run_current']);self.assertFalse(report['publication_authorized'])

    def test_unreferenced_snapshot_change_does_not_make_old_run_current(self):
        g=graph(node('a','identity',inp(self.a)));run=self.run_graph(g)
        newer=self.store.append(self.snapshot.draft_id,expected_revision=1,operation_id='unrelated',
            claims=[claim('unrelated','text',self.unused)]).snapshot
        report=observe_calculation_freshness(run,newer,self.profiles,normalize_synthetic(newer,self.profiles),g)
        self.assertEqual(report['affected_nodes'],[]);self.assertFalse(report['entire_run_current'])

    def test_node_definition_and_graph_shape_change_are_tracked(self):
        g=graph(node('a','identity',inp(self.a)),node('c','identity',inp(self.c)),node('total','sum',out('a'),out('c')))
        run=self.run_graph(g)
        changed=replace(g,nodes=tuple(replace(n,definition_revision='v2') if n.node_id=='a' else n for n in g.nodes))
        report=observe_calculation_freshness(run,self.snapshot,self.profiles,self.numeric,changed)
        self.assertEqual(report['affected_nodes'],['a','total'])
        expanded=replace(g,nodes=g.nodes+(node('added','identity',inp(self.a)),))
        report=observe_calculation_freshness(run,self.snapshot,self.profiles,self.numeric,expanded)
        self.assertEqual(report['added_nodes'],['added']);self.assertFalse(report['entire_run_current'])

    def test_computational_bit_bound_blocks_without_rounding_or_explosion(self):
        case=self.case({self.factor:{'literal':'9'*200}})
        g=graph(node('square','scale',inp(self.factor),inp(self.factor)),
            node('fourth','scale',out('square'),out('square')),
            node('eighth','scale',out('fourth'),out('fourth')),node('child','identity',out('eighth')))
        run=self.run_graph(g,case)
        self.assertEqual(run.payload['results']['fourth']['state'],'computed_synthetic')
        self.assertIn('technical_rational_size_bound',run.payload['results']['eighth']['blockers'])
        self.assertEqual(run.payload['results']['child']['state'],'blocked')
        self.assertIsNone(self.rational(run,'eighth'))

    def test_archive_reopen_replays_full_input_profile_graph_chain(self):
        g=graph(node('scale','scale',inp(self.a),inp(self.factor)));run=self.run_graph(g)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'archive.sqlite3'
            with EvidenceArchive(path) as archive:
                for sha in {c['source_sha256'] for records in self.snapshot.payload['input_claims'].values() for c in records}:
                    archive.put_source(self.archive.get_source(sha))
                key=archive.save_calculation(self.snapshot,self.profiles,self.numeric,g,run)
                self.assertEqual(key,archive.save_calculation(self.snapshot,self.profiles,self.numeric,g,run))
            with EvidenceArchive(path) as archive:
                restored=archive.load_calculation(key)
                self.assertEqual(restored.snapshot,self.snapshot);self.assertEqual(restored.normalization,self.numeric)
                self.assertEqual(restored.graph.sha256,g.sha256);self.assertEqual(restored.run,run)

    def test_archive_rejects_forged_result_with_recomputed_hash(self):
        g=graph(node('value','identity',inp(self.a)));run=self.run_graph(g)
        payload=run.payload;payload['results']['value']['rational']['numerator']='99'
        encoded=canonical(payload);forged=replace(run,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):self.archive.save_calculation(self.snapshot,self.profiles,self.numeric,g,forged)
        sha=self.archive.save_calculation(self.snapshot,self.profiles,self.numeric,g,run)
        bundle=json.loads(self.archive.read_bundle_bytes(sha));bundle['run']=asdict(forged)
        with self.archive._transaction():altered=self.archive._put('bundle',canonical(bundle).encode())
        with self.assertRaises(CorruptArchive):self.archive.load_calculation(altered)

    def test_missing_source_or_commit_failure_does_not_create_false_evidence(self):
        g=graph(node('value','identity',inp(self.a)));run=self.run_graph(g)
        with EvidenceArchive(':memory:') as empty:
            with self.assertRaises(MissingEvidence):empty.save_calculation(self.snapshot,self.profiles,self.numeric,g,run)
        with patch.object(self.archive,'_commit',side_effect=RuntimeError('pre-commit fault')):
            with self.assertRaises(RuntimeError):self.archive.save_calculation(self.snapshot,self.profiles,self.numeric,g,run)
        self.assertEqual(self.archive._connection.execute("SELECT COUNT(*) FROM objects WHERE kind='bundle'").fetchone()[0],0)
        self.archive.load_calculation(self.archive.save_calculation(self.snapshot,self.profiles,self.numeric,g,run))

    def test_calculator_or_decoder_mismatch_blocks_replay_but_preserves_bytes(self):
        g=graph(node('value','identity',inp(self.a)));run=self.run_graph(g)
        sha=self.archive.save_calculation(self.snapshot,self.profiles,self.numeric,g,run)
        for field in ['calculator_sha256','normalizer_sha256']:
            payload=json.loads(self.archive.read_bundle_bytes(sha));payload[field]='0'*64
            with self.archive._transaction():altered=self.archive._put('bundle',canonical(payload).encode())
            with self.assertRaises(UnsupportedArchive):self.archive.load_calculation(altered)
            self.assertTrue(self.archive.read_bundle_bytes(altered))

if __name__=='__main__':unittest.main()
