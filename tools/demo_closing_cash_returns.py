"""Conditional refinance/sale gross closing residuals into synthetic equity returns."""
from pathlib import Path
import json,tempfile
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.closing_returns import ClosingReturnBinding,assemble_closing_returns
from miniuw_foundation.archive import EvidenceArchive
import hashlib


def main():
    root=Path(__file__).resolve().parents[1];original=(root/'templates/synthetic-closing-investor-slots.json').read_bytes();current=original;stages=[]
    for kind,eid in [('refinance','refi'),('sale','sale')]:
        raw=(root/f'templates/synthetic-{kind}-closing.json').read_bytes();closing=produce_closing_cash(raw)
        binding=ClosingReturnBinding(profile_id='SYNTHETIC-CLOSING-EMPTY-EQUITY-SLOTS-v1',closing_source_sha256=hashlib.sha256(raw).hexdigest(),closing_run_sha256=closing.sha256,investor_source_sha256=hashlib.sha256(current).hexdigest(),distribution_event_id=eid,contribution_event_id=None)
        run=assemble_closing_returns(raw,closing,current,binding)
        if run.compiled_raw is None:raise ValueError('synthetic closing blocked; inspect source claims rather than inventing funding')
        stages.append((raw,closing,current,binding,run));current=run.compiled_raw
    receipts=[]
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'closings.sqlite3'
        with EvidenceArchive(path)as a:
            for raw,closing,investor,binding,run in stages:receipts.append((a.save_closing_cash(raw,closing),a.save_closing_returns(raw,closing,investor,binding,run)))
        with EvidenceArchive(path)as a:
            restored=[]
            for (cash_key,return_key),(raw,closing,investor,binding,run)in zip(receipts,stages):
                c=a.load_closing_cash(cash_key);r=a.load_closing_returns(return_key)
                assert c.run==closing and r.run==run
                assert a.get_closing_cash_source(c.payload['source_sha256'])==raw
                assert a.get_investor_returns_source(r.payload['investor_source_sha256'])==investor
                restored.append(r)
            assert restored[0].run.payload['compiled_investor_source_sha256']==restored[1].payload['investor_source_sha256']
            assert restored[-1].run.investor_run==stages[-1][-1].investor_run
    p=stages[-1][-1].investor_run.payload
    return {'purpose':'synthetic_conditional_closing_cash_to_investor_return_demo',
        'closings':[{'kind':c.payload['kind'],'date':c.payload['closing_date'],'gross_proceeds_claim':json.loads(raw)['amounts']['gross_proceeds'],
            'payoff_totals':c.payload['payoff_totals'],'projected_net_distribution':c.payload['projected_equity_distribution'],
            'projected_equity_contribution_required':c.payload['projected_equity_contribution_required'],
            'conservation_residual':c.payload['total_cash_conservation_residual'],'closing_run_sha256':c.sha256,
            'cash_bundle_sha256':keys[0],'return_bundle_sha256':keys[1]}for (raw,c,investor,binding,run),keys in zip(stages,receipts)],
        'normalized_equity_events':p['normalized_story']['events'],'normalized_total_contributions':p['normalized_story']['total_contributions'],
        'normalized_total_receipts':p['normalized_story']['total_distributions'],'normalized_cash_profit':p['normalized_story']['net_cash_profit'],
        'equity_multiple':p['equity_multiple'],'annual_irr_roots':p['annual_irr_roots'],'selected_IRR':p['selected_IRR'],
        'all_four_bundles_replayed_after_reopen':True,'intermediate_source_hash_link_verified':True,'original_investor_source_preserved':True,
        'runtime_database_retained':False,'obligations_and_proceeds_still_supplied_dated_claims':True,
        'operating_distributions_still_supplied_in_this_demo':True,'whole_project_cash_reconciled':False,
        'equity_residual_rule_adopted':False,'distribution_authorized':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
