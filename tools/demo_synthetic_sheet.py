"""Synthetic CSV intake -> archive -> execution -> verified recovery, in memory."""
import hashlib
import json
from pathlib import Path
from miniuw_foundation import ContextSeed, DraftStore
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic
from miniuw_foundation.sources import parse_source_claims


def main():
    raw=(Path(__file__).resolve().parents[1]/'templates/synthetic-sheet-example.csv').read_bytes()
    source_claim=parse_source_claims(raw)[0]
    with DraftStore(':memory:') as store, EvidenceArchive(':memory:') as archive:
        store.create('sheet-demo',ContextSeed(deal_id='SYNTHETIC-sheet-demo',scenario_id='demo',
            run_id='sheet-demo',definition_set_revision='text-fixture-v1'))
        snapshot=archive_and_import(archive,store,'sheet-demo',expected_revision=0,
            operation_id='sheet-fixture',raw=raw).snapshot
        graph=Graph((Node(node_id='length',operation='text_length',
            definition_revision='text-fixture-v1',dependencies=(),
            slots=(SlotRef(kind=source_claim.slot_kind,slot_id=source_claim.slot_id),)),))
        execution=execute_synthetic(snapshot,graph)
        bundle=archive.load_execution(archive.save_execution(snapshot,graph,execution))
        return {'purpose':'synthetic_csv_demo_only','source_sha256':hashlib.sha256(raw).hexdigest(),
            'source_locator':source_claim.locator,
            'exact_source_bytes_recovered':archive.get_source(source_claim.source_sha256)==raw,
            'text_length':bundle.execution.payload['results']['length']['value'],
            'decision':bundle.execution.payload['decision'],'production_authorized':False}


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
