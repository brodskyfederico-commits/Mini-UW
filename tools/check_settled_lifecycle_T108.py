"""Independent cash/event/IRR certificates for the settled full synthetic path."""
from pathlib import Path
from fractions import Fraction as F
import argparse,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.debt_service import rational,_fraction
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.settled_case import assemble_settled_case,source_window
from miniuw_foundation.expense_checked_lifecycle import recover_expense_checked_bundle
from miniuw_foundation.hold_sale_cash import reconcile_hold_sale_cash
from miniuw_foundation.drafts import canonical
from miniuw_foundation.settled_case_artifacts import audit_settled_case_directory,read_settled_case_artifacts,recover_settled_case_directory,write_settled_case_artifacts

EXAMPLE=ROOT/'docs/review/miniuw-v1-settled-lifecycle-example'
RECORD=ROOT/'docs/review/settled-lifecycle-validation-T108.json'
q=lambda v:rational(F(v))


def require(value,message):
    if not value:raise ValidationError(message)


def certificate(story):
    # Source-specific independent uniqueness certificate: one sign variation and strict rational sign bracket.
    flows=[_fraction(row['net'],1300)for row in story['dated_net_flows']];nonzero=[v for v in flows if v]
    variations=sum((a>0)!=(b>0)for a,b in zip(nonzero,nonzero[1:]));root=story['periodic_irr'];require(variations==1,'control cash polynomial must have one coefficient sign variation')
    require(root['status']=='complete_synthetic'and root['distinct_positive_discount_roots']==1 and len(root['roots'])==1,'complete sole positive discount root required')
    row=root['roots'][0];interval=row['discount_factor_interval'];lo,hi=F(interval['lower']),F(interval['upper'])
    def polynomial(x):
        value=F(0)
        for coefficient in reversed(flows):value=value*x+coefficient
        return value
    require(0<lo<hi and polynomial(lo)<0<polynomial(hi),'independent rational cash polynomial bracket fails')
    rates=row['periodic_rate_interval'];a,b=F(rates['lower']),F(rates['upper'])
    require(a==1/hi-1 and b==1/lo-1 and b-a<=F(root['requested_rate_interval_width']),'discount/rate transformation or width differs')
    annual=story['annual_irr_roots'];require(len(annual)==1 and annual[0]['exact_annual_rate']is None,'conditional annual enclosure required')
    bounds=annual[0]['annual_rate_interval'];require(_fraction(bounds['lower'],1300)==(1+a)**12-1 and _fraction(bounds['upper'],1300)==(1+b)**12-1,'independent supplied monthly annual transformation fails')
    require(story['selected_IRR']is None and root['selected_rate']is None and root['coefficient_bit_limit']==4096 and root['operation_budget']==200000,'root selection or numerical budget changed')
    return dict(coefficient_sign_variations=variations,strict_exact_rational_bracket=True,unique_positive_discount_root_certified=True,annual_frequency=12,point_rate_selected=False)


def verify():
    audit=audit_settled_case_directory(EXAMPLE);files=read_settled_case_artifacts(EXAMPLE);saved=recover_settled_case_directory(EXAMPLE)
    require(files['settled-case-results.json']==(saved.payload_json+'\n').encode(),'saved full-path result differs from source-first recovery')
    fixtures=json.loads((ROOT/'docs/review/settled-lifecycle-fixtures-T108.json').read_bytes());control_raw=(ROOT/fixtures['original_direct_control']).read_bytes()
    require(sha(control_raw)==fixtures['original_direct_control_sha256'],'original direct control changed');control=recover_expense_checked_bundle(control_raw).run.investor_run.payload
    require([r['label']for r in fixtures['cases']]==['retained','distributed','missing-stock','wrong-payment'],'four explicit complete/blocked source cases required')
    cases=[];certificates=[];known={}
    for row in fixtures['cases']:
        raw=(ROOT/row['path']).read_bytes();require(sha(raw)==row['sha256'],'settled source bytes changed');run=assemble_settled_case(raw);p=run.payload;s=p['project_return_story']
        require(run.sha256==row['run_sha256']and p['state']==row['state'],'declared full-path run did not reproduce')
        for key in('accounting_stocks_inferred','extra_expense_payment_or_equity_generated','phase_principal_counted_as_new_equity','all_model_profiles_or_financial_validation_complete',
            'current_source_authority_verified','one_page_for_this_new_profile_integrated','capital_or_CoC_definitions_adopted','new_external_PDF_created','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):
            require(p[key]is False,'cash proof became authority or another economic movement: '+key)
        require(p['decision']=='PENDING'and p['personal_investor_return']is None,'real decision or personal allocation invented')
        if row['label']in('retained','distributed'):
            retained=row['label']=='retained';require(s is not None and p['full_supplied_synthetic_cash_path_connected'],'full source path did not compile')
            expected=dict(gross_contributions=q(1400),gross_distributions=q(840),net_cash_profit=q(-560),equity_multiple=q(F(3,5)))
            require(all(s[k]==v for k,v in expected.items()),'independent gross equity/multiple oracle differs')
            expected_net=[-1000,-400,0,0,0,100,0,0,100 if retained else 105,640 if retained else 635]
            require([r['net']for r in s['dated_net_flows']]==[q(v)for v in expected_net],'independent exhaustive dated cash oracle differs')
            require(len(s['events'])==8 and sum(e['amount']==q(0)for e in s['events'])==3,'gross zero events omitted')
            require(s['normalized_story']['total_contributions']==q(10)and s['normalized_story']['total_distributions']==q(6)and s['normalized_story']['net_cash_profit']==q(-4),'explicit total-contribution normalization differs')
            require(all(r['conditional_coc']is None for r in s['annual_cash_receipts']),'annual denominator was invented')
            require(p['operating_totals']['closing_free_cash_claim']==q(275 if retained else 270)and p['settlement_summary']['settlement_cash']==q(5),'working balance or terminal cash oracle differs')
            h=p['holding_sale_totals'];require(h['operating_payments']==q(25)and h['closing_other_uses']==q(5)and h['debt_principal']==q(200)and h['equity_distributions']==q(840),'independent operating/payment/debt totals differ')
            monetary=dict(capital_expenditure=40,closing_costs=20,closing_other_sources=0,closing_other_uses=5,debt_fees=10,debt_interest=0,debt_other=0,
                debt_principal=200,equity_contributions=0,equity_distributions=840,nonfinancing_other_cash_receipt=0,opening_free_cash=590,opening_restricted_cash=0,
                operating_payments=25,operating_receipts=150,other_cash_payment=0,reserve_deposits=100,reserve_releases=100,sale_proceeds=400,terminal_free_cash=0,terminal_restricted_cash=0)
            require(h=={k:q(v)for k,v in monetary.items()},'independent exhaustive gross cash inventory differs')
            # Independent whole-window cash: opening590 + receipts150 + sale400 = payments25 + capex40 + settlement5 + closing20 + principal200 + fees10 + distributions840.
            require(590+150+400==25+40+5+20+200+10+840 and p['cash_conservation_residual']==q(0),'independent full-window conservation fails')
            if retained:
                require(all(s[k]==control[k]for k in(*expected,'dated_net_flows')),'retained settlement changed direct T77 source-control cash return')
                wa,_=source_window(json.loads(raw));ha=wa[3];old=json.loads(ha[4]);old.pop('boundary_source_sha256');old.update(schema='miniuw.synthetic-hold-sale-cash.v1',profile='SYNTHETIC-OPERATING-HOLD-TERMINAL-SALE-NO-REFINANCE-v1')
                guard=reconcile_hold_sale_cash(*ha[:4],canonical(old).encode()).payload
                require('payables:terminal_working_balance_requires_settlement_profile'in guard['blockers']and guard['exportable_equity_movements']is None,'old zero-terminal profile was silently relaxed')
            certificates.append(dict(label=row['label'],**certificate(s)));known[row['label']]=s
        else:
            require(s is None and not p['full_supplied_synthetic_cash_path_connected'],'blocked source restored a whole-case return')
            require(all(p[k]is None for k in('settlement_summary','operating_totals','holding_sale_totals','cash_conservation_residual','compiled_investor_json','irr_evidence','cash_risk_run')),'partial current money survived a required-source blocker')
        cases.append(dict(label=row['label'],source_sha256=sha(raw),run_sha256=run.sha256,state=p['state'],blockers=p['blockers'],gross_contributions=None if s is None else s['gross_contributions'],gross_distributions=None if s is None else s['gross_distributions']))
    require(known['retained']['periodic_irr']['roots']!=known['distributed']['periodic_irr']['roots'],'different supplied dated flows reused old roots')
    with tempfile.TemporaryDirectory()as td:
        missing=next(r for r in fixtures['cases']if r['label']=='missing-stock');root=Path(td)/'blocked';write_settled_case_artifacts((ROOT/missing['path']).read_bytes(),root)
        require(recover_settled_case_directory(root).payload['project_return_story']is None,'blocked directory recovery restored old return')
    paths=('src/miniuw_foundation/settled_case.py','src/miniuw_foundation/settled_expense_boundary.py','src/miniuw_foundation/settled_hold_sale.py',
        'src/miniuw_foundation/settled_operating_window.py','src/miniuw_foundation/settled_lifecycle_returns.py','src/miniuw_foundation/settled_case_artifacts.py',
        'tools/check_settled_lifecycle_T108.py','tools/settled_miniuw_v1.py','docs/technical-implementation-T108.md','docs/review/settled-lifecycle-fixtures-T108.json')
    return dict(component='T108',status='passed_full_source_path_and_independent_cash_and_IRR_certificates',files_verified=audit['files_verified'],source_cases_checked=4,
        cases=cases,independent_IRR_certificates=certificates,run_sha256=saved.sha256,original_direct_control_cash_preserved=True,
        old_zero_terminal_profile_preserved=True,blocked_source_first_directory_recovery_verified=True,
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in paths],
        complete_supplied_synthetic_cash_path_connected=True,all_model_profiles_or_financial_acceptance_completed=False,
        current_source_authority_verified=False,one_page_for_this_new_profile_integrated=False,original_semantic_mappings_pending=54,
        actual_personal_return_verified=False,new_external_PDF_created=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored full-path verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
