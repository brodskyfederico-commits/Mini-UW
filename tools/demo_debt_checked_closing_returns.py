"""Dated computed debt -> supplied closing comparison -> synthetic equity returns."""
from pathlib import Path
import json,hashlib,tempfile
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.closing_returns import ClosingReturnBinding
from miniuw_foundation.debt_closing import DatedLoanEvidence,reconcile_debt_closing
from miniuw_foundation.debt_closing_returns import DebtClosingReturnBinding,assemble_debt_checked_returns
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1];original=(root/'templates/synthetic-closing-investor-slots.json').read_bytes();current=original;stages=[]
    for kind,eid in [('refinance','refi'),('sale','sale')]:
        nr=(root/f'templates/synthetic-debt-checked-{kind}-loan.json').read_bytes()
        cr=(root/f'templates/synthetic-debt-checked-{kind}-closing.json').read_bytes()
        spec=(root/f'templates/synthetic-debt-checked-{kind}-binding.json').read_bytes()
        debt=produce_debt_service(nr,());loans=(DatedLoanEvidence(loan_raw=nr,windows=(),run=debt),);closing=produce_closing_cash(cr)
        reconciliation=reconcile_debt_closing(loans,cr,closing,spec)
        inner=ClosingReturnBinding(profile_id='SYNTHETIC-CLOSING-EMPTY-EQUITY-SLOTS-v1',closing_source_sha256=hashlib.sha256(cr).hexdigest(),closing_run_sha256=closing.sha256,investor_source_sha256=hashlib.sha256(current).hexdigest(),distribution_event_id=eid,contribution_event_id=None)
        binding=DebtClosingReturnBinding(profile_id='SYNTHETIC-DEBT-CHECKED-CLOSING-RETURN-v1',reconciliation_spec_sha256=hashlib.sha256(spec).hexdigest(),reconciliation_run_sha256=reconciliation.sha256,closing_return_binding=inner)
        result=assemble_debt_checked_returns(loans,cr,closing,spec,reconciliation,current,binding)
        if result.compiled_raw is None:raise ValueError('synthetic debt/closing mismatch; preserve evidence instead of tuning claims')
        stages.append((loans,cr,closing,spec,reconciliation,current,binding,result));current=result.compiled_raw
    keys=[]
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'checked.sqlite3'
        with EvidenceArchive(path)as a:
            for loans,cr,c,s,r,i,b,result in stages:keys.append((a.save_debt_closing(loans,cr,c,s,r),a.save_debt_checked_returns(loans,cr,c,s,r,i,b,result)))
        with EvidenceArchive(path)as a:
            recovered=[]
            for (comparison,compiled),stage in zip(keys,stages):
                loans,cr,c,s,r,i,b,result=stage;first=a.load_debt_closing(comparison);second=a.load_debt_checked_returns(compiled)
                assert first.run==r and second.run==result
                assert first.run.sha256==second.payload['reconciliation_run']['sha256']
                assert a.get_investor_returns_source(second.payload['investor_source_sha256'])==i
                recovered.append(second)
            assert recovered[0].run.closing_return_run.payload['compiled_investor_source_sha256']==recovered[1].payload['investor_source_sha256']
            assert recovered[-1].run.investor_run==stages[-1][-1].investor_run
    p=stages[-1][-1].investor_run.payload
    return {'purpose':'synthetic_dated_debt_cutoff_checked_closing_investor_return_demo',
        'closings':[{'kind':c.payload['kind'],'closing_date':c.payload['closing_date'],'loan_comparisons':r.payload['loans'],
            'projected_distribution':c.payload['projected_equity_distribution'],'debt_comparison_run_sha256':r.sha256,
            'comparison_bundle_sha256':pair[0],'return_bundle_sha256':pair[1]}for (loans,cr,c,s,r,i,b,result),pair in zip(stages,keys)],
        'normalized_equity_events':p['normalized_story']['events'],'normalized_total_receipts':p['normalized_story']['total_distributions'],
        'normalized_cash_profit':p['normalized_story']['net_cash_profit'],'equity_multiple':p['equity_multiple'],
        'annual_irr_roots':p['annual_irr_roots'],'selected_IRR':p['selected_IRR'],
        'all_four_bundles_replayed_after_reopen':True,'intermediate_investor_source_hash_link_verified':True,'original_investor_source_preserved':True,
        'runtime_database_retained':False,'prior_regular_service_paid_is_explicit_hypothesis':True,
        'fees_other_proceeds_and_operating_distributions_still_supplied':True,
        'scheduled_payment_history_actually_verified':False,'bank_payoff_statement_verified':False,
        'whole_project_cash_reconciled':False,'distribution_authorized':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
