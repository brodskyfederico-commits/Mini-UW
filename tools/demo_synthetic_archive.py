"""Disposable local archive/recovery demo; no persistent files or real decisions."""
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from miniuw_foundation import ContextSeed, DraftStore
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic, observe_freshness
from miniuw_foundation.intake import SCHEMA


def main():
    with TemporaryDirectory(prefix='miniuw-synthetic-archive-') as temporary:
        path=Path(temporary)/'evidence.sqlite3'
        with DraftStore(':memory:') as store, EvidenceArchive(path) as archive:
            context=ContextSeed(deal_id='SYNTHETIC-archive-demo',scenario_id='demo',
                run_id='archive-demo',definition_set_revision='synthetic-text-v1')
            initial=store.create('demo',context)
            slot=next(iter(initial.payload['input_claims']))
            record={'claim_id':'demo-claim','slot_kind':'input','slot_id':slot,
                'literal':'abc','unit_literal':None,'currency_literal':None,
                'period_literal':None,'definition_ref':'synthetic-text-v1'}
            raw=json.dumps({'schema':SCHEMA,'claims':[record]}).encode()
            snapshot=archive_and_import(archive,store,'demo',expected_revision=0,
                operation_id='fixture',raw=raw).snapshot
            graph=Graph((Node(node_id='length',operation='text_length',
                definition_revision='text-v1',dependencies=(),
                slots=(SlotRef(kind='input',slot_id=slot),)),))
            execution=execute_synthetic(snapshot,graph)
            sha=archive.save_execution(snapshot,graph,execution)
            restored_path=Path(temporary)/'restored.sqlite3'
            with sqlite3.connect(restored_path) as target:
                archive._connection.backup(target)
        # Both original store connections are closed; recover from another file.
        with EvidenceArchive(restored_path) as restored:
            bundle=restored.load_execution(sha)
            return {'purpose':'synthetic_archive_recovery_demo_only',
                'bundle_sha256':sha,
                'source_bytes_recovered':restored.get_source(hashlib.sha256(raw).hexdigest())==raw,
                'snapshot_sha256_matches':bundle.snapshot.sha256==snapshot.sha256,
                'execution_sha256_matches':bundle.execution.sha256==execution.sha256,
                'reproduced_text_length':bundle.execution.payload['results']['length']['value'],
                'decision':bundle.execution.payload['decision'],
                'production_authorized':False,'temporary_archive_removed_after_demo':True}


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
