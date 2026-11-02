"""Source -> exact decoding -> typed arithmetic -> archived replay, in memory."""
import json
from pathlib import Path
from miniuw_foundation import ContextSeed, DraftStore
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.normalization import NumericProfile, normalize_synthetic
from miniuw_foundation.calculations import calculate_synthetic, graph_from_record


def main():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'templates/synthetic-normalization-source.json').read_bytes()
    profiles=tuple(NumericProfile(**p) for p in json.loads((root/'templates/synthetic-normalization-profiles.json').read_bytes()))
    graph=graph_from_record(json.loads((root/'templates/synthetic-calculation-graph.json').read_bytes()))
    with DraftStore(':memory:') as store, EvidenceArchive(':memory:') as archive:
        store.create('arithmetic-demo',ContextSeed(deal_id='SYNTHETIC-arithmetic-demo',scenario_id='demo',
            run_id='arithmetic-demo',definition_set_revision='synthetic-only-unadopted'))
        snapshot=archive_and_import(archive,store,'arithmetic-demo',expected_revision=0,
            operation_id='fixture',raw=raw).snapshot
        numeric=normalize_synthetic(snapshot,profiles)
        run=calculate_synthetic(snapshot,profiles,numeric,graph)
        restored=archive.load_calculation(archive.save_calculation(snapshot,profiles,numeric,graph,run))
        return {'purpose':'typed_synthetic_arithmetic_only',
            'results':{key:{'state':record['state'],'rational':record['rational'],
                'quantity':record['quantity'],'blockers':record['blockers']}
                for key,record in restored.run.payload['results'].items()},
            'exact_run_recovered':restored.run==run,
            'criteria_with_claims':sum(bool(v) for v in snapshot.payload['criterion_claims'].values()),
            'decision':run.payload['decision'],'financially_validated':False,'production_authorized':False}


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
