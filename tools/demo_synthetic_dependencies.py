"""Reproducible T01/T02 demonstration; temporary memory store, no files changed."""
import json
from miniuw_foundation import ContextSeed, DraftStore, RawClaim
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic, observe_freshness


def main():
    context = ContextSeed(deal_id='SYNTHETIC-dependency-demo', scenario_id='explicit-demo',
        run_id='demo-run', definition_set_revision='text-fixture-v1')
    with DraftStore(':memory:') as store:
        initial = store.create('demo', context)
        first, second = list(initial.payload['input_claims'])[:2]
        def fixture(identity, slot, literal, source):
            return RawClaim(claim_id=identity,slot_kind='input',slot_id=slot,
                literal=literal,unit_literal=None,currency_literal=None,
                period_literal=None,source_sha256=source*64,
                locator='demo:'+identity,definition_ref='text-fixture-v1')
        filled = store.append('demo',expected_revision=0,operation_id='seed',
            claims=[fixture('first',first,'abc','a'),fixture('second',second,'xy','a')]).snapshot
        graph = Graph((
            Node(node_id='length-a',operation='text_length',definition_revision='text-v1',
                dependencies=(),slots=(SlotRef(kind='input',slot_id=first),)),
            Node(node_id='length-b',operation='text_length',definition_revision='text-v1',
                dependencies=(),slots=(SlotRef(kind='input',slot_id=second),)),
            Node(node_id='total-length',operation='integer_sum',definition_revision='text-v1',
                dependencies=('length-a','length-b'),slots=())))
        execution = execute_synthetic(filled,graph)
        updated = store.append('demo',expected_revision=1,operation_id='new-source',
            claims=[fixture('first-new-source',first,'abc','b')]).snapshot
        return {'purpose':'synthetic_text_dependency_demo_only',
            'text_lengths':{key:value['value'] for key,value in execution.payload['results'].items()},
            'original_revision':filled.revision,'observed_revision':updated.revision,
            'freshness':observe_freshness(execution,updated,graph),
            'decision':execution.payload['decision'],
            'production_authorized':False,'financial_engine_implemented':False}


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
