"""Synthetic graph behavior and T01-to-T02 integration; no UW acceptance claims."""
from dataclasses import replace
import unittest

from miniuw_foundation import DraftStore, ValidationError
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.execution import (
    Execution, Graph, Node, SlotRef, execute_synthetic, observe_freshness)
from miniuw_foundation.intake import SCHEMA, import_synthetic_claims
from test_foundation import claim, seed


def node(identity, *, slots=(), deps=(), op='text_length', revision='fixture-definition-v1'):
    return Node(node_id=identity, operation=op, definition_revision=revision,
        dependencies=deps, slots=slots)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.store = DraftStore(':memory:')
        self.addCleanup(self.store.close)
        self.blank = self.store.create('draft', seed())
        self.a, self.b, self.unused = list(self.blank.payload['input_claims'])[:3]
        self.criterion = next(iter(self.blank.payload['criterion_claims']))
        self.graph = Graph((
            node('total', deps=('len-a','len-b'), op='integer_sum'),
            node('len-b', slots=(SlotRef(kind='input',slot_id=self.b),)),
            node('len-a', slots=(SlotRef(kind='input',slot_id=self.a),))))
        self.filled = self.store.append('draft',expected_revision=0,operation_id='seed',
            claims=[claim('a','abc',self.a),claim('b','xy',self.b)]).snapshot

    def run_graph(self, snapshot=None, graph=None):
        return execute_synthetic(snapshot or self.filled, graph or self.graph)

    def test_out_of_order_graph_executes_topologically(self):
        execution = self.run_graph()
        results = execution.payload['results']
        self.assertEqual(results['len-a']['value'],3)
        self.assertEqual(results['len-b']['value'],2)
        self.assertEqual(results['total']['value'],5)
        self.assertEqual(results['total']['state'],'computed_synthetic')
        self.assertEqual(results['total']['upstream_fingerprints']['len-a'],results['len-a']['fingerprint'])

    def test_missing_blocks_downstream_without_zero_or_fail(self):
        results = self.run_graph(self.blank).payload['results']
        self.assertEqual(results['len-a']['state'],'blocked')
        self.assertIsNone(results['total']['value'])
        self.assertEqual(results['total']['blockers'],['upstream_blocked:len-a','upstream_blocked:len-b'])
        self.assertEqual(self.run_graph(self.blank).payload['decision'],'PENDING')

    def test_conflicting_source_blocks_only_affected_branch(self):
        snapshot = self.store.append('draft',expected_revision=1,operation_id='conflict',
            claims=[claim('a2','different',self.a)]).snapshot
        results = self.run_graph(snapshot).payload['results']
        self.assertEqual(results['len-a']['state'],'blocked')
        self.assertEqual(results['len-b']['state'],'computed_synthetic')
        self.assertIn('conflicting_claims',results['len-a']['blockers'][0])
        self.assertEqual(results['total']['state'],'blocked')

    def test_zero_is_a_literal_not_missing_and_formula_is_not_executed(self):
        other = self.store.create('other',seed())
        snapshot = self.store.append('other',expected_revision=0,operation_id='literal',
            claims=[claim('zero','0',self.a),claim('formula','=1+1',self.b)]).snapshot
        graph = Graph((node('zero',slots=(SlotRef(kind='input',slot_id=self.a),)),
            node('formula',slots=(SlotRef(kind='input',slot_id=self.b),),op='literal_echo')))
        results = self.run_graph(snapshot,graph).payload['results']
        self.assertEqual(results['zero']['value'],1)
        self.assertEqual(results['formula']['value'],'=1+1')

    def test_current_observation_does_not_authorize_publication(self):
        report = observe_freshness(self.run_graph(),self.filled,self.graph)
        self.assertTrue(report['entire_run_current'])
        self.assertTrue(report['observation_only'])
        self.assertFalse(report['publication_authorized'])
        self.assertEqual(report['decision'],'PENDING')

    def test_changed_source_invalidates_descendants_not_independent_branch(self):
        execution = self.run_graph()
        updated = self.store.append('draft',expected_revision=1,operation_id='matching-source',
            claims=[claim('a-new-source','abc',self.a,source_sha256='b'*64)]).snapshot
        report = observe_freshness(execution,updated,self.graph)
        self.assertEqual(report['affected_nodes'],['len-a','total'])
        self.assertEqual(report['unchanged_nodes'],['len-b'])
        self.assertFalse(report['entire_run_current'])
        self.assertEqual(self.run_graph(updated).payload['results']['total']['value'],5)

    def test_unreferenced_change_keeps_branch_keys_but_old_run_is_not_current(self):
        execution = self.run_graph()
        updated = self.store.append('draft',expected_revision=1,operation_id='unreferenced',
            claims=[claim('c','unused',self.unused)]).snapshot
        report = observe_freshness(execution,updated,self.graph)
        self.assertEqual(report['affected_nodes'],[])
        self.assertFalse(report['source_snapshot_current'])
        self.assertFalse(report['entire_run_current'])

    def test_definition_change_invalidates_node_and_descendants(self):
        changed = Graph(tuple(replace(n,definition_revision='v2') if n.node_id=='len-a' else n for n in self.graph.nodes))
        report = observe_freshness(self.run_graph(),self.filled,changed)
        self.assertEqual(report['affected_nodes'],['len-a','total'])
        self.assertFalse(report['graph_current'])

    def test_operation_change_invalidates_even_with_same_definition_label(self):
        changed = Graph(tuple(replace(n,operation='literal_echo') if n.node_id=='len-a' else n for n in self.graph.nodes))
        report = observe_freshness(self.run_graph(),self.filled,changed)
        self.assertEqual(report['affected_nodes'],['len-a','total'])
        self.assertEqual(self.run_graph(graph=changed).payload['results']['total']['state'],'blocked')

    def test_changed_topology_invalidates_dependent_node(self):
        changed = Graph(tuple(replace(n,dependencies=('len-a',)) if n.node_id=='total' else n for n in self.graph.nodes))
        report = observe_freshness(self.run_graph(),self.filled,changed)
        self.assertEqual(report['affected_nodes'],['total'])
        self.assertEqual(self.run_graph(graph=changed).payload['results']['total']['value'],3)

    def test_added_and_removed_nodes_are_explicit(self):
        expanded = Graph(self.graph.nodes + (node('extra',slots=(SlotRef(kind='input',slot_id=self.a),)),))
        report = observe_freshness(self.run_graph(),self.filled,expanded)
        self.assertEqual(report['added_nodes'],['extra'])
        report = observe_freshness(self.run_graph(graph=expanded),self.filled,self.graph)
        self.assertEqual(report['removed_nodes'],['extra'])
        self.assertFalse(report['entire_run_current'])

    def test_declaration_order_has_no_effect(self):
        reordered = Graph(tuple(reversed(self.graph.nodes)))
        self.assertEqual(reordered.sha256,self.graph.sha256)
        self.assertEqual(self.run_graph(graph=reordered).sha256,self.run_graph().sha256)

    def test_scenario_run_definition_and_deal_context_are_isolated(self):
        original = self.run_graph()
        for key, value in [('scenario_id','scenario-2'),('run_id','run-2'),
                           ('definition_set_revision','definitions-2'),('deal_id','SYNTHETIC-other')]:
            payload = self.filled.payload
            payload['context'][key] = value
            encoded = canonical(payload)
            snapshot = replace(self.filled,payload_json=encoded,sha256=digest(encoded))
            report = observe_freshness(original,snapshot,self.graph)
            self.assertEqual(report['affected_nodes'],['len-a','len-b','total'])
            self.assertFalse(report['entire_run_current'])

    def test_run_snapshot_and_source_snapshot_do_not_mutate_each_other(self):
        run = self.run_graph()
        copy = run.payload
        copy['results']['total']['value']=999
        self.assertEqual(run.payload['results']['total']['value'],5)
        self.assertEqual(self.store.get('draft').sha256,self.filled.sha256)
        self.assertEqual(run.payload['source']['sha256'],self.filled.sha256)
        self.assertEqual(run.payload['source']['revision'],1)

    def test_type_mismatch_blocks_and_propagates(self):
        graph = Graph(self.graph.nodes+(node('bad-length',deps=('total',)),
            node('downstream',deps=('bad-length',),op='literal_echo')))
        results = self.run_graph(graph=graph).payload['results']
        self.assertEqual(results['bad-length']['blockers'],['synthetic_operation_type_mismatch'])
        self.assertEqual(results['downstream']['state'],'blocked')

    def test_cycles_unknown_dependencies_and_duplicate_nodes_rejected(self):
        for nodes in [(node('self',deps=('self',)),),
                      (node('a',deps=('b',)),node('b',deps=('a',))),
                      (node('a',deps=('unknown',)),),
                      (node('a',deps=('a',)),node('a',deps=('a',)))]:
            with self.assertRaises(ValidationError):Graph(nodes)

    def test_invalid_operation_arity_mutable_configuration_rejected(self):
        for kwargs in [dict(op='financial_formula',deps=('x',)),dict(),
                       dict(slots=[SlotRef(kind='input',slot_id=self.a)]),
                       dict(deps=('x','x'))]:
            with self.assertRaises(ValidationError):node('bad',**kwargs)
        with self.assertRaises(ValidationError):Graph([])

    def test_unknown_slot_is_configuration_error_not_filled_default(self):
        graph = Graph((node('unknown',slots=(SlotRef(kind='input',slot_id='unknown'),)),))
        with self.assertRaises(ValidationError):self.run_graph(graph=graph)

    def test_criteria_are_empty_until_explicit_synthetic_fixture_no_adoption(self):
        graph = Graph((node('criterion',slots=(SlotRef(kind='criterion',slot_id=self.criterion),),op='literal_echo'),))
        self.assertEqual(self.run_graph(graph=graph).payload['results']['criterion']['state'],'blocked')
        snapshot = self.store.append('draft',expected_revision=1,operation_id='criterion',
            claims=[claim('criterion','synthetic text',self.criterion,kind='criterion')]).snapshot
        run = self.run_graph(snapshot,graph)
        self.assertEqual(run.payload['results']['criterion']['value'],'synthetic text')
        self.assertFalse(run.payload['financially_normalized'])
        self.assertEqual(run.payload['decision'],'PENDING')

    def test_corrupted_source_execution_and_changed_guards_rejected(self):
        with self.assertRaises(ValidationError):self.run_graph(replace(self.filled,sha256='0'*64))
        run = self.run_graph()
        with self.assertRaises(ValidationError):observe_freshness(replace(run,sha256='0'*64),self.filled,self.graph)
        payload=run.payload
        payload['decision']='PASS'
        encoded=canonical(payload)
        with self.assertRaises(ValidationError):observe_freshness(Execution(encoded,digest(encoded)),self.filled,self.graph)

    def test_intake_store_execution_end_to_end_preserves_source_pointer(self):
        import json
        raw_record = claim('a-new','abc',self.a).record()
        record={k:v for k,v in raw_record.items() if k not in {'source_sha256','locator','claim_kind'}}
        raw=json.dumps({'schema':SCHEMA,'claims':[record]}).encode()
        snapshot=import_synthetic_claims(self.store,'draft',expected_revision=1,operation_id='file',raw=raw).snapshot
        run=self.run_graph(snapshot)
        provenance=run.payload['results']['len-a']['source_slots'][0]['claims'][-1]
        import hashlib
        self.assertEqual(provenance['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(provenance['locator'],'/claims/0/literal')
        self.assertEqual(run.payload['results']['total']['value'],5)

if __name__=='__main__':unittest.main()
