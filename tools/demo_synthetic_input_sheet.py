"""Original 55-field layout with synthetic values, without financial decisions."""
from pathlib import Path
import json
from miniuw_foundation import ContextSeed, DraftStore
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet


def main():
    raw=(Path(__file__).resolve().parents[1]/'templates/synthetic-native-inputs-example.xlsx').read_bytes()
    with DraftStore(':memory:') as store, EvidenceArchive(':memory:') as archive:
        store.create('native-demo',ContextSeed(deal_id='SYNTHETIC-native-demo',scenario_id='demo',
            run_id='native-demo',definition_set_revision='unadopted-fixture-only'))
        snapshot=archive_and_import(archive,store,'native-demo',expected_revision=0,
            operation_id='native-file',raw=raw).snapshot
        graph=Graph(tuple(Node(node_id=field,operation='literal_echo',definition_revision='fixture-v1',
            dependencies=(),slots=(SlotRef(kind='input',slot_id=field),))
            for field in ('INPUT_C8','INPUT_C9')))
        execution=execute_synthetic(snapshot,graph)
        restored=archive.load_execution(archive.save_execution(snapshot,graph,execution))
        inspection=inspect_synthetic_input_sheet(archive.get_source(restored.payload['source_hashes'][0]))
        return {'purpose':'native_input_layout_synthetic_demo_only',
            'input_fields_with_source_claims':sum(bool(v) for v in snapshot.payload['input_claims'].values()),
            'criteria_with_claims':sum(bool(v) for v in snapshot.payload['criterion_claims'].values()),
            'C8_literal':restored.execution.payload['results']['INPUT_C8']['value'],
            'C8_unit_literal':snapshot.slot('input','INPUT_C8')['claims'][0]['unit_literal'],
            'C8_currency_inferred':False,
            'C9_formula':inspection.cells['C9']['formula'],
            'C9_cache':inspection.cells['C9']['cached_value'],
            'C9_state':restored.execution.payload['results']['INPUT_C9']['state'],
            'exact_source_recovered':archive.get_source(restored.payload['source_hashes'][0])==raw,
            'decision':restored.execution.payload['decision'],'production_authorized':False}


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
