"""Read-only rent/policy/settlement, full cash, IRR and one-page recovery oracles."""
from pathlib import Path
from fractions import Fraction as F
from io import BytesIO
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.debt_service import rational
from miniuw_foundation.phased_settled_output import assemble_phased_settled_output,required_sources
from miniuw_foundation.current_settled_case import assemble_current_settled_case
from miniuw_foundation.phased_settled_report import render_phased_settled_output
from miniuw_foundation.phased_settled_artifacts import recover_phased_settled_directory,validate_report
from miniuw_foundation.expense_checked_lifecycle import recover_expense_checked_bundle
from check_settled_lifecycle_T108 import certificate

RECORD=ROOT/'docs/review/phased-settled-validation-T110.json'
q=lambda n:rational(F(n))


def require(condition,message):
    if not condition:raise ValidationError(message)


def verify():
    fixtures=json.loads((ROOT/'docs/review/phased-settled-fixtures-T110.json').read_bytes());cases=[];certificates=[]
    require([r['label']for r in fixtures['cases']]==['current','twelve','blocked','expired','parent-expired'],'five explicit source hypotheses required')
    old=recover_expense_checked_bundle((ROOT/'templates/synthetic-phased-expense-base.json').read_bytes()).run.investor_run.payload
    for row in fixtures['cases']:
        raw=(ROOT/row['path']).read_bytes();source=json.loads(raw);run=assemble_phased_settled_output(raw);p=run.payload
        report=render_phased_settled_output(raw,run);audit=validate_report(raw,run,report);m=report.manifest
        require(sha(raw)==row['source_sha256']and run.sha256==row['run_sha256']and sha(report.pdf_bytes)==row['pdf_sha256']and p['state']==row['state'],'saved source/result/PDF did not reproduce')
        require(p['required_sources']==required_sources(raw)and p['source_requirements_checked']==47,'complete parent/rental/book/definition source inventory differs')
        for key in ('financial_model_complete','financial_publication_authorized','source_authority_verified','professional_review_authenticated','deployment_enabled','real_decisions_enabled','original_sheet_adapter_for_this_profile_implemented','rent_or_policy_counted_as_additional_equity_cash','nominal_due_treated_as_payment'):require(p[key]is False,'synthetic source evidence became cash/authority: '+key)
        require(p['decision']=='PENDING'and p['personal_investor_return']is None and all(r['threshold']is None and r['state']=='PENDING'for r in p['criterion_slots']),'decision or personal policy invented')
        if row['label']in('current','twelve'):
            twelve=row['label']=='twelve';s=p['current_project_return_story'];parent=assemble_current_settled_case(source['current_settled_source_utf8'].encode()).payload
            for key in ('current_project_return_story','current_settlement_summary','current_operating_totals','current_holding_sale_totals','current_nominal_insurance_totals','current_risk_observations','current_irr_evidence','current_compiled_investor_json'):require(p[key]==parent[key],'rent/policy binding altered parent money: '+key)
            expected=dict(gross_contributions=q(1400),gross_distributions=q(776 if twelve else 778),net_cash_profit=q(-624 if twelve else -622),equity_multiple=q(F(97,175)if twelve else F(389,700)))
            require(all(s[k]==v for k,v in expected.items()),'independent gross-equity oracle differs')
            require([r['net']for r in s['dated_net_flows']]==[q(v)for v in [-1000,-400,0,0,0,100,0,0,100,576 if twelve else 578]],'full dated cash including zeros differs')
            require(p['current_rental_totals']==dict(effective_rent=q(88),period_count=2)and p['current_policy_totals']['premiums']==q(22 if twelve else 20),'phased rent/policy premium oracle differs')
            require(p['current_policy_totals']['expense_by_period']=={'SYNTHETIC-hold-1':q(10),'SYNTHETIC-hold-2':q(12 if twelve else 10)},'per-period premium accrual differs')
            require(p['current_operating_totals']['closing_free_cash_claim']==q(211 if twelve else 213)and p['current_settlement_summary']['before_payables']==q(5)and p['current_settlement_summary']['settlement_cash']==q(5)and p['current_settlement_summary']['after_payables']==q(0),'independent retained cash/accounting/settlement oracle differs')
            require(s['normalized_story']['total_contributions']==q(10)and s['normalized_story']['total_distributions']==q(F(194,35)if twelve else F(389,70)),'total-contribution normalization differs')
            if not twelve:
                for key in ('gross_contributions','gross_distributions','net_cash_profit','equity_multiple'):require(s[key]==old[key],'settled phased control differs from preserved T83 cash')
            require(m['annual_years']==[2026,2027]and sorted(i for g in m['event_groups']for i in g['event_indices'])==list(range(8))and sum(g['zero_event_count']for g in m['event_groups'])==3,'zero/gross/annual event omitted or duplicated')
            certificates.append(dict(label=row['label'],**certificate(s)))
        else:
            require(all(v is None for k,v in p.items()if k.startswith('current_')),'a blocked source retained current cash/rent/policy results')
            require(m['all_current_money_withheld']and m['event_groups']==[]and m['annual_years']==[],'blocked PDF retained historical money')
        if row['label']in('current','blocked','expired'):
            recovered,rr=recover_phased_settled_directory(ROOT/('docs/review/miniuw-v1-phased-settled-'+row['label']+'-example'));require(recovered==run and rr==report,'six-file packet differs from source-first recovery')
        reader=PdfReader(BytesIO(report.pdf_bytes));require(len(reader.pages)==1,'exactly one external page required')
        require(all(span['text']in reader.pages[0].extract_text()for span in m['display_spans']),'PDF source span missing')
        cases.append(dict(label=row['label'],source_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),state=p['state'],sources=47,display_spans=len(m['display_spans']),all_current_money_withheld=m['all_current_money_withheld'],audit_status=audit['status']))
    paths=['src/miniuw_foundation/'+n+'.py'for n in ('nominal_policy_book','phased_settled_output','phased_settled_report','phased_settled_artifacts')]+['tools/phased_settled_miniuw_v1.py','tools/check_phased_settled_T110.py','tests/test_phased_settled_output.py','docs/technical-implementation-T110.md','docs/review/phased-settled-fixtures-T110.json']
    return dict(component='T110',status='passed_phased_rent_nominal_policy_full_settled_cash_currentness_one_page_and_recovery',source_cases_checked=5,saved_output_directories_checked=3,files_per_packet=6,source_requirements_per_case=47,PDF_pages_per_output=1,cases=cases,independent_IRR_certificates=certificates,
        original_phased_control_equity_preserved=True,no_new_cash_from_rent_policy_or_nominal_due=True,all_current_money_withheld_on_any_blocker=True,source_versions=[dict(path=p,sha256=sha((ROOT/p).read_bytes()))for p in paths],original_semantic_mappings_pending=54,financial_model_complete=False,source_authority_verified=False,professional_review_authenticated=False,personal_return_verified=False,visual_independent_financial_audit_performed=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored T110 validation differs')
        print(json.dumps(result,indent=2))
    except(ValueError,OSError,TypeError,KeyError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
