"""Computed service and two explicit maturity views, without actual-payment claims."""
from dataclasses import replace
from pathlib import Path
import json
from miniuw_foundation import ContextSeed,DraftStore
from miniuw_foundation.archive import EvidenceArchive,archive_and_import
from miniuw_foundation.normalization import NumericProfile,normalize_synthetic
from miniuw_foundation.calculations import graph_from_record,calculate_synthetic
from miniuw_foundation.debt_service import parse_loan_terms,produce_debt_service,DateWindow
from miniuw_foundation.debt_dscr import DebtDscrBinding,calculate_debt_dscr


def main():
    root=Path(__file__).resolve().parents[1]/'templates'
    raw=(root/'synthetic-loan-terms.json').read_bytes();terms=parse_loan_terms(raw)
    windows=tuple(DateWindow(**w) for w in json.loads((root/'synthetic-loan-windows.json').read_bytes()))
    case=json.loads((root/'synthetic-debt-dscr-case.json').read_bytes())
    with DraftStore(':memory:') as store,EvidenceArchive(':memory:') as archive:
        store.create('debt-demo',ContextSeed(**terms['context']))
        snapshot=archive_and_import(archive,store,'debt-demo',expected_revision=0,operation_id='source',raw=json.dumps(case['source']).encode()).snapshot
        profiles=tuple(NumericProfile(**p) for p in case['profiles']);numeric=normalize_synthetic(snapshot,profiles)
        graph=graph_from_record(case['graph']);upstream=calculate_synthetic(snapshot,profiles,numeric,graph)
        debt=produce_debt_service(raw,windows);binding=DebtDscrBinding(**case['binding'])
        run=calculate_debt_dscr(snapshot,profiles,numeric,graph,upstream,raw,windows,debt,binding)
        gross=calculate_debt_dscr(snapshot,profiles,numeric,graph,upstream,raw,windows,debt,replace(binding,include_balloon=True))
        restored=archive.load_debt_dscr(archive.save_debt_dscr(snapshot,profiles,numeric,graph,upstream,raw,windows,debt,binding,run))
        return {'purpose':'synthetic_debt_producer_and_dscr_only','regular_payment_due':debt.payload['regular_payment_due'],
            'annual_sizing_equivalent':debt.payload['annual_sizing']['amount'],
            'maturity_window':debt.payload['dated_windows'][binding.window_id],
            'dscr_scheduled_only':run.payload['rational'],'dscr_including_balloon_due':gross.payload['rational'],
            'exact_bridge_recovered':restored.run==run,'cash_paid_verified':False,'noi_financially_verified':False,
            'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
