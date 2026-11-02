"""Exact synthetic decoding with one deliberately unresolved currency symbol."""
from pathlib import Path
import json
from miniuw_foundation import ContextSeed, DraftStore
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.normalization import NumericProfile, normalize_synthetic


def main():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'templates/synthetic-normalization-source.json').read_bytes()
    profiles=tuple(NumericProfile(**p) for p in json.loads((root/'templates/synthetic-normalization-profiles.json').read_bytes()))
    with DraftStore(':memory:') as store, EvidenceArchive(':memory:') as archive:
        store.create('decoder-demo',ContextSeed(deal_id='SYNTHETIC-decoder-demo',scenario_id='demo',
            run_id='decoder-demo',definition_set_revision='synthetic-only-unadopted'))
        snapshot=archive_and_import(archive,store,'decoder-demo',expected_revision=0,
            operation_id='decoder-source',raw=raw).snapshot
        run=normalize_synthetic(snapshot,profiles)
        restored=archive.load_normalization(archive.save_normalization(snapshot,profiles,run))
        return {'purpose':'synthetic_numeric_decoding_only',
            'results':{slot:{'state':record['state'],'rational':record['rational'],
                'target_unit':record['target_unit'],'blockers':record['blockers']}
                for slot,record in restored.run.payload['results'].items()},
            'exact_run_recovered':restored.run==run,
            'criteria_with_claims':sum(bool(v) for v in snapshot.payload['criterion_claims'].values()),
            'decision':restored.run.payload['decision'],'financially_normalized':False,
            'production_authorized':False}


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
