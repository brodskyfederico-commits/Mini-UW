"""Read-only hypothetical allocations, exact gross reconciliation and IRR certificate."""
from fractions import Fraction as F
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError,canonical
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_case_output import assemble_worksheet_case
from miniuw_foundation.cash_participation import _from_verified_parent
from miniuw_foundation.cash_participation_artifacts import (audit_cash_participation_directory,read_cash_participation_artifacts,
    recover_cash_participation_bundle,export_cash_participation_bundle)

EXAMPLE=ROOT/'docs/review/miniuw-v1-cash-participation-example'
RECORD=ROOT/'docs/review/cash-participation-validation-T104.json'


def require(value,message):
    if not value:raise ValidationError(message)


def independent_IRR_certificate(row,frequency):
    # Single-sign-change sparse cash case: bracket plus Descartes bound proves uniqueness.
    flows=[_fraction(v['net'],1300)for v in row['dated_net_flows']]
    signs=[1 if value>0 else-1 for value in flows if value]
    require(sum(a!=b for a,b in zip(signs,signs[1:]))==1,'positive-share fixture must have one coefficient sign change')
    result=row['periodic_IRR'];require(result['status']=='complete_synthetic'and result['distinct_positive_discount_roots']==1,'fixture IRR did not complete uniquely')
    root=result['roots'][0];polynomial=lambda x:sum((c*x**i for i,c in enumerate(flows)),F(0))
    if root['exact_discount_factor']is not None:
        x=F(root['exact_discount_factor']);require(x>0 and polynomial(x)==0,'independent exact root fails')
        require(_fraction(row['annual_IRR_roots'][0]['exact_annual_rate'],1300)==x**(-frequency)-1,'independent exact annual transformation fails')
    else:
        interval=root['discount_factor_interval'];a,b=F(interval['lower']),F(interval['upper'])
        require(0<a<b and polynomial(a)<0<polynomial(b),'independent root bracket signs fail')
        annual=row['annual_IRR_roots'][0]['annual_rate_interval']
        require(_fraction(annual['lower'],1300)==b**(-frequency)-1 and _fraction(annual['upper'],1300)==a**(-frequency)-1,
            'independent annual discount transformation fails')
        require(annual['lower_closed']==interval['upper_closed']and annual['upper_closed']==interval['lower_closed'],'annual endpoint closures differ')
    require(result['coefficient_bit_limit']==4096 and result['operation_budget']==200000 and row['selected_IRR']is None,'IRR budgets or point selection changed')


def verify():
    audit=audit_cash_participation_directory(EXAMPLE);files=read_cash_participation_artifacts(EXAMPLE)
    recovered=recover_cash_participation_bundle(files['allocation-evidence.json']);run=recovered.run;parent=run.parent_run;story=parent.payload['current_project_return_story']
    require(files['allocation-terms.json']==recovered.terms_raw and files['allocation-results.json']==(run.payload_json+'\n').encode(),'saved allocation source/result differs')
    generation=json.loads((ROOT/'docs/review/cash-participation-fixture-generation-T104.json').read_bytes())
    require(sha((ROOT/generation['parent_evidence']).read_bytes())==generation['parent_evidence_sha256'],'original T103 proof changed')
    require([r['label']for r in generation['cases']]==['quarter','third','zero','missing'],'four explicit allocation terms required')
    observations=[];certificates=0
    for record in generation['cases']:
        raw=(ROOT/record['path']).read_bytes();require(sha(raw)==record['sha256'],'declared allocation terms changed')
        current=run if raw==recovered.terms_raw else _from_verified_parent(raw,parent);p=current.payload
        require(p['state']==record['state']and p['blockers']==record['blockers'],'declared hypothetical state differs')
        for key in('allocation_terms_adopted','personal_investor_return_verified','source_or_contract_authority_authenticated',
            'participant_or_fraction_selected','parent_case_or_worksheet_modified','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):
            require(p[key]is False,'hypothesis became an authority or automatic action: '+key)
        require(p['decision']=='PENDING'and p['verified_personal_investor_return']is None,'hypothesis became verified personal return')
        if p['participants']is None:
            require(record['label']=='missing'and p['reconciliation']is None,'unexpected partial allocation')
            rows=None
        else:
            rows=[]
            for row,declared in zip(p['participants'],record['participants']):
                summary={k:row[k]for k in('participant_id','gross_contributions','gross_distributions','net_cash_profit','equity_multiple')}
                require(summary=={k:declared[k]for k in summary},'declared exact hypothetical cash differs')
                require(row['periodic_IRR']['status']==declared['IRR_status'],'declared IRR status differs')
                f=_fraction(row['share_fraction'])
                for index,(event,source)in enumerate(zip(row['dated_events'],story['dated_events'])):
                    require(event['event_id']==source['event_id']and event['date']==source['date']and event['kind']==source['kind']and
                        event['category']==source['category']and _fraction(event['amount'],1300)==_fraction(source['amount'],1300)*f,
                        'independent full gross-event allocation identity fails')
                    require(event['project_event_pointer'].endswith('/dated_events/'+str(index)),'event provenance locator differs')
                require(len(row['dated_events'])==len(story['dated_events']),'gross or zero events omitted')
                require([y['calendar_cash_receipt_year']for y in row['annual_cash']]==[y['calendar_cash_receipt_year']for y in story['annual_cash_receipts']], 'cash years omitted')
                require(all(row[k]is None for k in('capital_still_invested','retained_equity_value','conditional_CoC','verified_personal_investor_return','selected_IRR')),'unsupported capital or personal value invented')
                if f>0:independent_IRR_certificate(row,parent.payload['irr_recalculation']['parameters']['periods_per_year']);certificates+=1
                else:require(row['equity_multiple']is None and row['periodic_IRR']['root_classification']=='identically_zero_net_polynomial'and not row['annual_IRR_roots'],'zero fraction became a defined return')
                rows.append(summary)
            require(p['reconciliation']['totals']=={k:story[k]for k in('gross_contributions','gross_distributions','net_cash_profit')},'aggregate allocations do not conserve gross project cash')
            if record['label']=='quarter':
                first=p['participants'][0]
                require([_fraction(first[k])for k in('gross_contributions','gross_distributions','net_cash_profit')]==[F(350),F(389,2),F(-311,2)],'independent quarter cash amounts differ')
                require(_fraction(first['cash_by_category']['initial_capital'])==250 and _fraction(first['cash_by_category']['additional_capital'])==100 and
                    _fraction(first['cash_by_category']['operating_distribution'])==50 and _fraction(first['cash_by_category']['net_sale_distribution'])==F(289,2),'independent initial/additional/operation/sale detail differs')
        observations.append(dict(label=record['label'],terms_sha256=sha(raw),run_sha256=current.sha256,state=p['state'],blockers=p['blockers'],participants=rows))
    # Matching allocation terms never restore a worksheet-blocked current view.
    book=(ROOT/'templates/worksheet-case-zero-conflict-T103.xlsx').read_bytes();binding=(ROOT/'templates/worksheet-case-zero-conflict-T103.json').read_bytes()
    blocked_parent=assemble_worksheet_case(recovered.case_raw,book,binding);terms=json.loads(recovered.terms_raw)
    terms.update(source_hashes=blocked_parent.payload['worksheet_reconciliation']['source_hashes'],worksheet_run_sha256=blocked_parent.sha256)
    terms_raw=(canonical(terms)+'\n').encode();blocked=_from_verified_parent(terms_raw,blocked_parent)
    restored=recover_cash_participation_bundle(export_cash_participation_bundle(recovered.case_raw,book,binding,terms_raw,blocked))
    require(restored.run==blocked and blocked.payload['participants']is None and blocked.payload['blockers']==['current_project_cash_unavailable'], 'blocked cash recovered through a historical fallback')
    paths=('src/miniuw_foundation/cash_participation.py','src/miniuw_foundation/cash_participation_artifacts.py',
        'src/miniuw_foundation/primitive_periodic_returns.py','src/miniuw_foundation/irr_checked_output.py',
        'src/miniuw_foundation/worksheet_case_output.py','src/miniuw_foundation/worksheet_case_artifacts.py',
        'tools/cash_participation_miniuw_v1.py','tools/check_cash_participation_T104.py','docs/technical-implementation-T104.md',
        'docs/review/cash-participation-fixture-generation-T104.json')
    return dict(component='T104',status='passed_source_first_hypothetical_cash_and_independent_IRR_certificates',files_verified=audit['files_verified'],
        fixture_terms_checked=4,independent_positive_share_IRR_certificates=certificates,observations=observations,
        run_sha256=run.sha256,parent_worksheet_run_sha256=parent.sha256,blocked_source_portable_recovery_verified=True,
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in paths],
        original_one_page_PDF_sha256=sha((ROOT/'docs/review/miniuw-v1-worksheet-case-example/MiniUW_v1_Resumen.pdf').read_bytes()),
        new_external_PDF_created=False,original_semantic_mappings_pending=54,allocation_terms_adopted=False,
        personal_investor_return_verified=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored hypothetical allocation verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
