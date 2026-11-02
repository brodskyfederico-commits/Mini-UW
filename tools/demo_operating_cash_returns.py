"""Replay NOI -> one-period cash plan -> explicitly bound investor distribution."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,tempfile
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.operating_returns import OperatingReturnBinding,assemble_operating_returns
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1]
    noi_raw=(root/'templates/synthetic-operating-noi.json').read_bytes()
    spec_raw=(root/'templates/synthetic-operating-cash.json').read_bytes()
    investor_raw=(root/'templates/synthetic-operating-investor-slots.json').read_bytes()
    noi=produce_operating_noi(noi_raw);cash=reconcile_operating_cash(noi_raw,noi,spec_raw)
    binding=OperatingReturnBinding(profile_id='SYNTHETIC-EMPTY-OPERATING-EQUITY-SLOTS-v1',
        investor_source_sha256=hashlib.sha256(investor_raw).hexdigest(),cash_spec_sha256=hashlib.sha256(spec_raw).hexdigest(),
        cash_run_sha256=cash.sha256,distribution_event_id='op1',contribution_event_id=None)
    assembled=assemble_operating_returns(noi_raw,noi,spec_raw,cash,investor_raw,binding)
    if assembled.compiled_raw is None:raise ValueError('synthetic cash/return assembly blocked; inspect source rather than inventing amounts')
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'operating-cash.sqlite3'
        with EvidenceArchive(path)as a:
            first=a.save_operating_cash(noi_raw,noi,spec_raw,cash)
            second=a.save_operating_returns(noi_raw,noi,spec_raw,cash,investor_raw,binding,assembled)
        with EvidenceArchive(path)as a:
            recovered_cash=a.load_operating_cash(first);recovered_assembly=a.load_operating_returns(second)
            assert recovered_cash.run==cash and recovered_assembly.run==assembled
            assert recovered_cash.run.sha256==recovered_assembly.payload['cash_run']['sha256']
            assert recovered_assembly.run.investor_run==assembled.investor_run
            assert a.get_investor_returns_source(recovered_assembly.payload['investor_source_sha256'])==investor_raw
    p=cash.payload;returns=assembled.investor_run.payload
    return {'purpose':'synthetic_NOI_cash_allocation_investor_return_chain','context':p['context'],'cash_date':p['cash_date'],
        'NOI':p['computed_noi'],'operating_receipts':p['expected_operating_receipts'],'operating_payments':p['expected_operating_payments'],
        'net_operating_cash':p['net_operating_cash'],'cash_before_distribution':p['free_cash_before_proposed_distribution'],
        'planned_operating_distribution':p['exportable_operating_distribution'],'closing_free_cash':p['expected_closing_free_cash'],
        'closing_restricted_cash':p['expected_closing_restricted_cash'],'cash_conservation_residual':p['total_cash_conservation_residual'],
        'normalized_investor_events':returns['normalized_story']['events'],'normalized_cash_profit':returns['normalized_story']['net_cash_profit'],
        'equity_multiple':returns['equity_multiple'],'annual_irr_roots':returns['annual_irr_roots'],'binding':asdict(binding),
        'cash_source_sha256':p['spec_source_sha256'],'cash_run_sha256':cash.sha256,'compiled_investor_source_sha256':assembled.payload['compiled_investor_source_sha256'],
        'investor_return_run_sha256':assembled.investor_run.sha256,'cash_bundle_sha256':first,'assembly_bundle_sha256':second,
        'both_bundles_replayed_after_reopen':True,'NOI_cash_event_return_chain_replayed':True,'original_source_preserved':True,
        'only_first_operating_distribution_connected_to_cash_producer':True,
        'refinance_sale_and_second_operating_distribution_still_supplied':True,'runtime_database_retained':False,
        'multi_period_cash_continuity_verified':False,'debt_paid_or_distribution_authorized':False,
        'financially_validated':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
