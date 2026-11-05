"""Read-only source-first attributed cash-risk and unchanged project-risk reconciliation."""
from fractions import Fraction as F
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError,canonical
from miniuw_foundation.debt_service import _fraction,rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.cash_participation import _from_verified_parent as allocation_from_parent
from miniuw_foundation.cash_participation_artifacts import recover_cash_participation_bundle,export_cash_participation_bundle
from miniuw_foundation.worksheet_case_output import assemble_worksheet_case
from miniuw_foundation.participant_cash_risk import analyze_participant_cash_risk,ADDITIVE,DATED
from miniuw_foundation.participant_cash_risk_artifacts import (audit_participant_cash_risk_directory,
    read_participant_cash_risk_artifacts,recover_participant_cash_risk_directory,write_participant_cash_risk_artifacts)
import tempfile

EXAMPLE=ROOT/'docs/review/miniuw-v1-participant-cash-risk-example'
RECORD=ROOT/'docs/review/participant-cash-risk-validation-T105.json'
REGISTRY=ROOT/'docs/review/participant-cash-risk-fixtures-T105.json'
encoded=lambda p:(canonical(p)+'\n').encode()


def require(value,message):
    if not value:raise ValidationError(message)


def source_variant(source,terms,verified_worksheet):
    # Offline fixture construction, not automatic runtime evidence renewal or proposal adoption.
    allocation=allocation_from_parent(terms,verified_worksheet);p=json.loads(source)
    p.update(terms_utf8=terms.decode(),result=dict(payload_json=allocation.payload_json,sha256=allocation.sha256))
    return encoded(p)


def verify():
    audit=audit_participant_cash_risk_directory(EXAMPLE);files=read_participant_cash_risk_artifacts(EXAMPLE)
    source=files['allocation-evidence.json'];main=recover_participant_cash_risk_directory(EXAMPLE)
    require(files['participant-cash-risk.json']==(main.payload_json+'\n').encode(),'saved risk differs from source-first recovery')
    fixture=json.loads(REGISTRY.read_bytes())
    original=(ROOT/fixture['source_evidence']).read_bytes()
    require(source==original and sha(original)==fixture['source_evidence_sha256'],'original T104 evidence was altered or nested again')
    base=recover_cash_participation_bundle(source);project=base.run.parent_run.payload['current_project_return_story']['risk_observations']
    require([r['label']for r in fixture['cases']]==['quarter','third','zero','missing'],'four existing terms revisions required')
    observations=[]
    for case in fixture['cases']:
        terms=(ROOT/case['terms_path']).read_bytes();require(sha(terms)==case['terms_sha256'],'declared existing T104 terms changed')
        raw=source if terms==base.terms_raw else source_variant(source,terms,base.run.parent_run)
        run=main if raw==source else analyze_participant_cash_risk(raw);p=run.payload
        require(p['state']==case['state'],'declared risk state differs')
        for key in('original_cash_and_IRR_changed','allocation_terms_adopted','candidate_or_fraction_selected',
            'sale_exclusion_is_recomputed_scenario','capital_still_invested_derived_from_cash',
            'actual_funding_or_reinvestment_availability_verified','actual_intraday_order_verified','independent_downside_verified',
            'full_risk_analysis_completed','financial_publication_authorized','new_external_PDF_created','deployment_enabled','real_decisions_enabled'):
            require(p[key]is False,'observations became a decision, available funding or authority: '+key)
        require(p['decision']=='PENDING'and p['verified_personal_investor_return']is None,'actual personal return inferred')
        if p['participants']is None:
            require(case['expected']is None and p['reconciliation']is None and p['blockers']==['current_participant_cash_unavailable'], 'missing allocation restored project risk as participant fallback')
            expected=None
        else:
            require(len(p['participants'])==len(case['expected']),'participant inventory differs')
            expected=[]
            for index,(row,wanted)in enumerate(zip(p['participants'],case['expected'])):
                m=row['metrics']
                for key,amount in wanted.items():require(m[key]==amount,'independent exact risk amount differs: '+key)
                require(row['source_participant_pointer']=='/participants/'+str(index),'participant source locator differs')
                participant=run.parent_run.payload['participants'][index]
                require(row['currency']==participant['currency']and row['cash_horizon']==participant['cash_horizon'],'explicit cash currency/window lost')
                events=participant['dated_events']
                require(sorted(i for date in row['dated_observations']for i in date['event_indices'])==list(range(len(events))), 'zero/gross event indices omitted or duplicated')
                for date in row['dated_observations']:
                    require(date['event_ids']==[events[i]['event_id']for i in date['event_indices']], 'event ID/index linkage differs')
                    require(all(events[i]['date']==date['date']for i in date['event_indices']),'source event date was shifted')
                require(all(row[k]is None for k in('capital_still_invested','retained_equity_value','conditional_CoC','final_economic_capital_loss',
                    'verified_personal_investor_return','actual_capital_available')),'cash observation became an unavailable stock or actual funding value')
                expected.append({key:m[key]for key in wanted})
            reconciliation=p['reconciliation'];require(reconciliation['project_metrics']==project,'unchanged T37 project observation differs')
            for key in ADDITIVE:
                require(sum((_fraction(row['metrics'][key],1300)for row in p['participants']),F(0))==_fraction(project[key],1300),'project risk cash conservation fails')
            require(reconciliation['sale_ratios_summed']is False,'percentage risks were summed')
            for index,date in enumerate(reconciliation['dated_checks']):
                for key in DATED:require(date['allocated'][key]==rational(sum((_fraction(row['dated_observations'][index][key],1300)for row in p['participants']),F(0))), 'dated risk bounds do not reconcile')
        observations.append(dict(label=case['label'],terms_sha256=sha(terms),source_evidence_sha256=sha(raw),risk_run_sha256=run.sha256,
            state=p['state'],blockers=p['blockers'],observations=expected))
    # A valid attribution of a worksheet-blocked source cannot restore current money after recovery.
    book=(ROOT/'templates/worksheet-case-zero-conflict-T103.xlsx').read_bytes();binding=(ROOT/'templates/worksheet-case-zero-conflict-T103.json').read_bytes()
    worksheet=assemble_worksheet_case(base.case_raw,book,binding);terms=json.loads(base.terms_raw)
    terms.update(source_hashes=worksheet.payload['worksheet_reconciliation']['source_hashes'],worksheet_run_sha256=worksheet.sha256)
    traw=encoded(terms);allocation=allocation_from_parent(traw,worksheet)
    blocked_source=export_cash_participation_bundle(base.case_raw,book,binding,traw,allocation)
    with tempfile.TemporaryDirectory()as td:
        path=Path(td)/'risk';write_participant_cash_risk_artifacts(blocked_source,path);blocked=recover_participant_cash_risk_directory(path)
        require(blocked.payload['participants']is None and blocked.payload['reconciliation']is None and
            blocked.parent_run.parent_run.payload['current_project_return_story']is None,'blocked allocation recovered historical cash as current risk')
    paths=('src/miniuw_foundation/participant_cash_risk.py','src/miniuw_foundation/participant_cash_risk_artifacts.py',
        'src/miniuw_foundation/cash_risk.py','src/miniuw_foundation/cash_participation.py','src/miniuw_foundation/cash_participation_artifacts.py',
        'tools/participant_cash_risk_miniuw_v1.py','tools/check_participant_cash_risk_T105.py',
        'docs/technical-implementation-T105.md','docs/technical-implementation-T37.md','docs/review/participant-cash-risk-fixtures-T105.json')
    return dict(component='T105',status='passed_source_first_participant_risk_and_project_cash_reconciliation',files_verified=audit['files_verified'],
        fixture_revisions_checked=4,observations=observations,risk_run_sha256=main.sha256,source_allocation_run_sha256=main.parent_run.sha256,
        original_allocation_evidence_bytes_preserved=True,original_allocation_evidence_nested_again=False,
        original_one_page_PDF_sha256=sha((ROOT/'docs/review/miniuw-v1-worksheet-case-example/MiniUW_v1_Resumen.pdf').read_bytes()),
        new_external_PDF_created=False,blocked_source_directory_recovery_verified=True,ratios_summed=False,
        observed_peak_is_actual_funding_available=False,capital_or_final_economic_loss_derived=False,
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in paths],
        original_semantic_mappings_pending=54,actual_personal_return_verified=False,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored participant risk verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
