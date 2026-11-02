"""Full declared synthetic cash window, bank-schedule assumptions and investor ledger."""
from pathlib import Path
import json,hashlib,tempfile
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_closing import DatedLoanEvidence,reconcile_debt_closing
from miniuw_foundation.project_cash import CheckedClosingEvidence,reconcile_project_cash
from miniuw_foundation.project_returns import ProjectEventSlot,ProjectReturnBinding,assemble_project_returns
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1];ops=[];closings=[]
    for tag in ['pre-refi','post-refi']:
        nr=(root/f'templates/synthetic-project-{tag}-noi.json').read_bytes();sr=(root/f'templates/synthetic-project-{tag}-operation.json').read_bytes();noi=produce_operating_noi(nr);cash=reconcile_operating_cash(nr,noi,sr)
        ops.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash))
    for kind in ['refinance','sale']:
        lr=(root/f'templates/synthetic-project-{kind}-loan.json').read_bytes();cr=(root/f'templates/synthetic-project-{kind}-closing.json').read_bytes();br=(root/f'templates/synthetic-project-{kind}-debt-binding.json').read_bytes()
        debt=produce_debt_service(lr,());loans=(DatedLoanEvidence(loan_raw=lr,windows=(),run=debt),);closing=produce_closing_cash(cr);comparison=reconcile_debt_closing(loans,cr,closing,br)
        closings.append(CheckedClosingEvidence(closing_id='SYNTHETIC-project-'+kind,closing_raw=cr,closing_run=closing,loans=loans,debt_spec_raw=br,debt_run=comparison))
    ops=tuple(ops);closings=tuple(closings);manifest=(root/'templates/synthetic-project-cash-manifest.json').read_bytes();investor=(root/'templates/synthetic-project-investor-slots.json').read_bytes();cash=reconcile_project_cash(ops,closings,manifest)
    slots=tuple(ProjectEventSlot(node_id=row['node_id'],distribution_event_id=eid,contribution_event_id=None)for row,eid in zip(json.loads(manifest)['nodes'],['op-before','refi','op-after','sale']))
    binding=ProjectReturnBinding(profile_id='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1',manifest_source_sha256=hashlib.sha256(manifest).hexdigest(),project_run_sha256=cash.sha256,investor_source_sha256=hashlib.sha256(investor).hexdigest(),opening_contribution_event_ids=('initial',),slots=slots)
    result=assemble_project_returns(ops,closings,manifest,cash,investor,binding)
    if result.compiled_raw is None:raise ValueError('integrated synthetic cash mismatch; inspect original evidence rather than changing values to balance')
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'integrated.sqlite3'
        with EvidenceArchive(path)as a:cash_key=a.save_project_cash(ops,closings,manifest,cash);return_key=a.save_project_returns(ops,closings,manifest,cash,investor,binding,result)
        with EvidenceArchive(path)as a:
            c=a.load_project_cash(cash_key);r=a.load_project_returns(return_key)
            assert c.run==cash and r.run==result and c.run.sha256==r.payload['project_run']['sha256']
            assert a.get_investor_returns_source(r.payload['investor_source_sha256'])==investor
            assert a.get_investor_returns_source(r.payload['compiled_source_sha256'])==result.compiled_raw
    p=result.investor_run.payload
    return {'purpose':'synthetic_operations_refinance_operations_sale_cash_and_return_demo',
        'context':cash.payload['context'],'cash_nodes':cash.payload['nodes'],'cash_boundaries':cash.payload['cash_boundary_checks'],
        'working_balance_checks':cash.payload['working_balance_checks'],'operating_debt_checks':cash.payload['operating_debt_checks'],
        'refinance_to_sale_loan_links':cash.payload['refinance_to_sale_loan_links'],'totals':cash.payload['totals'],
        'cash_conservation_residual':cash.payload['cash_conservation_residual'],'normalized_equity_events':p['normalized_story']['events'],
        'normalized_total_contributions':p['normalized_story']['total_contributions'],'normalized_total_receipts':p['normalized_story']['total_distributions'],
        'normalized_cash_profit':p['normalized_story']['net_cash_profit'],'equity_multiple':p['equity_multiple'],'dated_net_flows':p['dated_net_flows'],
        'annual_irr_roots':p['annual_irr_roots'],'selected_IRR':p['selected_IRR'],'investor_story_blockers':p['story_blockers'],
        'cash_bundle_sha256':cash_key,'return_bundle_sha256':return_key,'both_bundles_replayed_after_reopen':True,
        'source_investor_ledger_preserved':True,'complete_declared_cash_window_reconciled':cash.payload['declared_cash_window_reconciled'],
        'runtime_database_retained':False,'whole_project_cash_reconciled':False,'whole_investor_story_complete':False,
        'opening_asset_and_construction_funding_history_verified':False,'bank_payment_history_verified':False,
        'intraperiod_liquidity_verified':False,'distribution_authorized':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
