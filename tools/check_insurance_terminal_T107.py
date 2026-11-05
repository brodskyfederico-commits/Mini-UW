"""Independent known-money cut/closing oracles and complete three-source replay."""
from pathlib import Path
from fractions import Fraction as F
import argparse,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.insurance_terminal_closing import reconcile_insurance_terminal_closing
from miniuw_foundation.insurance_terminal_artifacts import (read_insurance_terminal_artifacts,recover_insurance_terminal_directory,
    audit_insurance_terminal_directory,write_insurance_terminal_artifacts)

EXAMPLE=ROOT/'docs/review/miniuw-v1-insurance-terminal-example'
RECORD=ROOT/'docs/review/insurance-terminal-validation-T107.json'
q=lambda v:rational(F(v))


def require(condition,message):
    if not condition:raise ValidationError(message)


def verify():
    audit=audit_insurance_terminal_directory(EXAMPLE);files=read_insurance_terminal_artifacts(EXAMPLE);main=recover_insurance_terminal_directory(EXAMPLE)
    require(files['terminal-results.json']==(main.payload_json+'\n').encode(),'saved terminal result differs from complete replay')
    fixture=json.loads((ROOT/'docs/review/insurance-terminal-fixtures-T107.json').read_bytes())
    require(sha((ROOT/fixture['original_control_source']).read_bytes())==fixture['original_control_source_sha256'],'original nominal plan changed')
    require([row['label']for row in fixture['cases']]==['on-cut','prepaid','cash-in','funding-missing','future','zero','missing','split'],'eight explicit source hypotheses required')
    # Independently supplied gross sale, other uses, before-cut cash, nominal tail, equity distribution/contribution and expense.
    oracle={'on-cut':(100,5,15,5,95,0,20),'prepaid':(100,0,20,0,100,0,20),'cash-in':(0,5,15,5,0,5,20),
        'zero':(100,0,0,0,100,0,0),'split':(100,5,15,5,95,0,20)}
    cases=[]
    for row in fixture['cases']:
        args=[(ROOT/row['sources'][k]['path']).read_bytes()for k in('plan','closing','binding')]
        for raw,kind in zip(args,('plan','closing','binding')):require(sha(raw)==row['sources'][kind]['sha256'],'source bytes changed')
        run=reconcile_insurance_terminal_closing(*args);p=run.payload;summary=p['summary'];source=json.loads(args[1]);base=produce_closing_cash(args[1]).payload
        require((p['state'],summary,p['blockers'])==(row['state'],row['summary'],row['blockers']),'declared terminal source plan did not reproduce')
        for key in('accounting_balances_derived','nominal_tail_is_approved_legal_liability','actual_bank_payments_verified','funding_availability_verified',
            'payer_or_buyer_transfer_inferred','source_authority_verified','full_operating_sale_return_integration_completed','personal_investor_return_verified',
            'new_external_PDF_created','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):
            require(p[key]is False,'source comparison became financial authority: '+key)
        require(p['decision']=='PENDING'and p['no_additional_deduction_applied']and p['currency']=='USD'and p['settlement_date']=='2027-07-01','scope/cut/currency/decision changed')
        if row['label']in oracle:
            gross,uses,before,tail,distribution,contribution,cost=oracle[row['label']]
            require(source['old_debts']==[]and source['new_loan']is None and source['kind']=='sale','oracle fixture debt/kind changed')
            for key,value in source['amounts'].items():
                require(value['value']==q(gross if key=='gross_proceeds'else uses if key=='other_cash_uses'else 0),'independent closing amount oracle changed')
            expected=dict(allocated_expense=q(cost),planned_cash_before_cut=q(before),nominal_before_cut=q(tail),bound_payment_sum=q(uses),
                nominal_after_supplied_cut_payments=q(0),closing_other_cash_uses=q(uses),net_residual_after_retention=q(gross-uses),
                exportable_equity_distribution=q(distribution),exportable_equity_contribution=q(contribution),total_cash_conservation_residual=q(0))
            require(summary==expected,'independent nominal/cut/equity money oracle differs')
            for key in('net_residual_after_retention','exportable_equity_distribution','exportable_equity_contribution','total_cash_conservation_residual'):
                require(summary[key]==base[key],'binding subtracted or recomputed closing cash')
            require(len(p['payment_checks'])==(2 if row['label']=='split'else 0 if row['label']=='prepaid'else 1),'complete zero/split payment index inventory changed')
        else:
            require(summary is None and p['blockers'],'blocked binding restored an isolated/historical closing result')
            if row['label']=='future':require(base['exportable_equity_distribution']==q(95),'future pending must not be caused by unrelated closing failure')
        cases.append(dict(label=row['label'],source_hashes=p['source_hashes'],run_sha256=run.sha256,state=p['state'],summary=summary,blockers=p['blockers']))
    with tempfile.TemporaryDirectory()as td:
        blocked=next(row for row in fixture['cases']if row['label']=='future');args=[(ROOT/blocked['sources'][k]['path']).read_bytes()for k in('plan','closing','binding')]
        root=Path(td)/'blocked';write_insurance_terminal_artifacts(*args,root)
        require(recover_insurance_terminal_directory(root).payload['summary']is None,'blocked three-source recovery restored financial numbers')
    paths=('src/miniuw_foundation/insurance_terminal_closing.py','src/miniuw_foundation/insurance_terminal_artifacts.py',
        'src/miniuw_foundation/deferred_insurance_settlement.py','src/miniuw_foundation/closing_cash.py','tools/insurance_terminal_miniuw_v1.py',
        'tools/check_insurance_terminal_T107.py','docs/technical-implementation-T107.md','docs/technical-implementation-T106.md',
        'docs/review/insurance-terminal-fixtures-T107.json')
    return dict(component='T107',status='passed_three_source_replay_and_independent_terminal_closing_oracles',files_verified=audit['files_verified'],
        source_hypotheses_checked=8,cases=cases,run_sha256=main.sha256,closing_cash_not_deducted_twice=True,
        future_payment_not_accelerated=True,blocked_directory_recovery_verified=True,
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in paths],
        full_operating_sale_return_integration_completed=False,accounting_balances_derived=False,actual_bank_payments_verified=False,
        actual_legal_liability_approved=False,original_semantic_mappings_pending=54,new_external_PDF_created=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored terminal source verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
