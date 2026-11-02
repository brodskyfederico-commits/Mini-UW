"""Candidate DSCR from declared synthetic amounts, not a derived/approved NOI model."""
import json
from pathlib import Path
from miniuw_foundation import ContextSeed,DraftStore
from miniuw_foundation.archive import EvidenceArchive,archive_and_import
from miniuw_foundation.normalization import NumericProfile,normalize_synthetic
from miniuw_foundation.calculations import graph_from_record,calculate_synthetic
from miniuw_foundation.scoped_profiles import DscrBinding,dispatch_scoped_profile


def main():
    root=Path(__file__).resolve().parents[1]/'templates'
    raw=(root/'synthetic-dscr-source.json').read_bytes()
    profiles=tuple(NumericProfile(**p) for p in json.loads((root/'synthetic-dscr-profiles.json').read_bytes()))
    graph=graph_from_record(json.loads((root/'synthetic-dscr-upstream-graph.json').read_bytes()))
    binding=DscrBinding(**json.loads((root/'synthetic-dscr-binding.json').read_bytes()))
    with DraftStore(':memory:') as store,EvidenceArchive(':memory:') as archive:
        store.create('dscr-demo',ContextSeed(deal_id='SYNTHETIC-dscr-demo',scenario_id='demo',run_id='dscr-demo',definition_set_revision='synthetic-declared-only'))
        snapshot=archive_and_import(archive,store,'dscr-demo',expected_revision=0,operation_id='source',raw=raw).snapshot
        numeric=normalize_synthetic(snapshot,profiles)
        upstream=calculate_synthetic(snapshot,profiles,numeric,graph)
        run=dispatch_scoped_profile(snapshot,profiles,numeric,graph,upstream,binding)
        restored=archive.load_scoped_profile(archive.save_scoped_profile(snapshot,profiles,numeric,graph,upstream,binding,run))
        return {'purpose':'synthetic_declared_dscr_only','rational':restored.run.payload['rational'],
            'output_unit':restored.run.payload['output_unit'],'interpretation':restored.run.payload['interpretation_label'],
            'definition_sources':restored.run.payload['definition_sources'],
            'exact_run_recovered':restored.run==run,'upstream_contracts_financially_verified':False,
            'criteria_with_claims':sum(bool(v) for v in snapshot.payload['criterion_claims'].values()),
            'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
