"""Three declared operating years, including a zero year, into investor returns."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,tempfile
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence,reconcile_holding_cash
from miniuw_foundation.holding_returns import HoldingEventSlot,HoldingReturnBinding,assemble_holding_returns
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1];periods=[]
    for index in [1,2,3]:
        nr=(root/f'templates/synthetic-holding-noi-{index}.json').read_bytes();sr=(root/f'templates/synthetic-holding-period-{index}.json').read_bytes()
        noi=produce_operating_noi(nr);cash=reconcile_operating_cash(nr,noi,sr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash))
    periods=tuple(periods);manifest=(root/'templates/synthetic-holding-manifest.json').read_bytes()
    investor=(root/'templates/synthetic-holding-investor-slots.json').read_bytes();holding=reconcile_holding_cash(periods,manifest)
    slots=tuple(HoldingEventSlot(period_ref=row['period_ref'],distribution_event_id=eid,contribution_event_id=None)for row,eid in zip(json.loads(manifest)['periods'],['op1','op-zero','op3']))
    binding=HoldingReturnBinding(profile_id='SYNTHETIC-HOLDING-EMPTY-EQUITY-SLOTS-v1',manifest_source_sha256=hashlib.sha256(manifest).hexdigest(),holding_run_sha256=holding.sha256,investor_source_sha256=hashlib.sha256(investor).hexdigest(),slots=slots)
    assembled=assemble_holding_returns(periods,manifest,holding,investor,binding)
    if assembled.compiled_raw is None:raise ValueError('synthetic holding return blocked; inspect original evidence rather than repairing values')
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'holding.sqlite3'
        with EvidenceArchive(path)as a:
            first=a.save_holding_cash(periods,manifest,holding);second=a.save_holding_returns(periods,manifest,holding,investor,binding,assembled)
        with EvidenceArchive(path)as a:
            cash=a.load_holding_cash(first);returns=a.load_holding_returns(second)
            assert cash.run==holding and returns.run==assembled and a.get_holding_periods(first)==periods
            assert cash.run.sha256==returns.payload['holding_run']['sha256']
            assert a.get_investor_returns_source(returns.payload['investor_source_sha256'])==investor
    p=holding.payload;r=assembled.investor_run.payload
    return {'purpose':'synthetic_three_period_operating_continuity_and_investor_returns','context':p['context'],
        'declared_horizon':{'start':p['start_date'],'end':p['end_date']},'periods':p['periods'],
        'continuity_checks':len(p['continuity_checks']),'all_twelve_continuity_checks_equal':all(c['equal_exact_value']for c in p['continuity_checks']),
        'totals':p['totals'],'cash_conservation_residual':p['cash_conservation_residual'],
        'operating_movements':p['exportable_equity_movements'],'normalized_equity_events':r['normalized_story']['events'],
        'dated_net_flows':r['dated_net_flows'],'normalized_total_contributions':r['normalized_story']['total_contributions'],
        'normalized_total_receipts':r['normalized_story']['total_distributions'],'normalized_cash_profit':r['normalized_story']['net_cash_profit'],
        'equity_multiple':r['equity_multiple'],'annual_irr_roots':r['annual_irr_roots'],'selected_IRR':r['selected_IRR'],
        'unreconciled_events_outside_operating_binding':assembled.payload['events_outside_this_operating_binding'],
        'binding':asdict(binding),'holding_run_sha256':holding.sha256,'investor_run_sha256':assembled.investor_run.sha256,
        'holding_bundle_sha256':first,'return_bundle_sha256':second,'both_bundles_replayed_after_reopen':True,
        'all_period_sources_recovered_byte_exactly':True,'original_investor_source_preserved':True,
        'zero_period_included_not_compressed':True,'runtime_database_retained':False,
        'refinance_and_sale_still_supplied':True,'whole_project_cash_reconciled':False,
        'distribution_authorized':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
