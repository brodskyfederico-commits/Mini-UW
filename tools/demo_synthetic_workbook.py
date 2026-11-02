"""Inspect/recover a synthetic workbook; a supplied formula cache stays inactive."""
import json
from pathlib import Path
from miniuw_foundation import ContextSeed, DraftStore
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic
from miniuw_foundation.workbooks import inspect_synthetic_xlsx, parse_synthetic_xlsx


def main():
    raw=(Path(__file__).resolve().parents[1]/'templates/synthetic-workbook-example.xlsx').read_bytes()
    inspection=inspect_synthetic_xlsx(raw);claims=parse_synthetic_xlsx(raw)
    with DraftStore(':memory:') as store, EvidenceArchive(':memory:') as archive:
        store.create('xlsx-demo',ContextSeed(deal_id='SYNTHETIC-xlsx-demo',scenario_id='demo',
            run_id='xlsx-demo',definition_set_revision='synthetic-only'))
        snapshot=archive_and_import(archive,store,'xlsx-demo',expected_revision=0,
            operation_id='workbook',raw=raw).snapshot
        graph=Graph(tuple(Node(node_id='cell-'+str(i),operation='literal_echo',
            definition_revision='fixture-v1',dependencies=(),
            slots=(SlotRef(kind=c.slot_kind,slot_id=c.slot_id),)) for i,c in enumerate(claims)))
        execution=execute_synthetic(snapshot,graph)
        bundle=archive.load_execution(archive.save_execution(snapshot,graph,execution))
        return {'purpose':'synthetic_workbook_demo_only',
            'exact_source_bytes_recovered':archive.get_source(inspection.source_sha256)==raw,
            'D3_text':bundle.execution.payload['results']['cell-0']['value'],
            'D4_formula':inspection.cells['D4']['formula'],
            'D4_supplied_cache':inspection.cells['D4']['cached_value'],
            'D4_input_literal':claims[1].literal,
            'D4_execution_state':bundle.execution.payload['results']['cell-1']['state'],
            'decision':bundle.execution.payload['decision'],'production_authorized':False}


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
