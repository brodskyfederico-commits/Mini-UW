"""Read-only current-source inventory, exact parent cash and one-page withdrawal checks."""
from pathlib import Path
from io import BytesIO
import argparse,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.settled_case import assemble_settled_case
from miniuw_foundation.current_settled_case import assemble_current_settled_case,required_settled_sources
from miniuw_foundation.settled_output_report import render_settled_output
from miniuw_foundation.settled_output_artifacts import (audit_current_settled_directory,read_current_settled_artifacts,
    recover_current_settled_directory,validate_report,write_current_settled_artifacts)

RECORD=ROOT/'docs/review/current-settled-validation-T109.json'


def require(condition,message):
    if not condition:raise ValidationError(message)


def verify():
    fixture=json.loads((ROOT/'docs/review/current-settled-fixtures-T109.json').read_bytes())
    require([r['label']for r in fixture['cases']]==['current','expired','blocked','distributed'],'four explicit current/expired/calc/distributed hypotheses required')
    cases=[];current=None
    for row in fixture['cases']:
        raw=(ROOT/row['path']).read_bytes();require(sha(raw)==row['source_sha256'],'current source bytes changed');source=json.loads(raw);case_raw=source['case_source_utf8'].encode()
        require(sha(case_raw)==row['case_source_sha256'],'T108 parent bytes changed');parent=assemble_settled_case(case_raw);run=assemble_current_settled_case(raw);p=run.payload
        report=render_settled_output(raw,run);audit=validate_report(raw,run,report);m=report.manifest;text=PdfReader(BytesIO(report.pdf_bytes)).pages[0].extract_text()
        require(run.sha256==row['run_sha256']and p['state']==row['state']and sha(report.pdf_bytes)==row['pdf_sha256']and audit==row['audit'],'declared current run/PDF/audit did not reproduce')
        required=required_settled_sources(case_raw);require(p['required_sources']==required and len(required)==35,'complete source inventory differs')
        paths={r['requirement_id']for r in required}
        require({'/case/source','/construction/bundle','/transition/phase_contract','/sale/cash','/sale/debt_binding','/settlement/accounting_before_after',
            '/settlement/pre_cut_payment_map','/settlement/nominal_plan','/settlement/terminal_binding','/investor/source','/investor/binding','/catalog/empty_original_inputs_criteria'}<=paths,'critical nested source omitted')
        require(len(p['criterion_slots'])==10 and all(c['threshold']is None and c['state']=='PENDING'for c in p['criterion_slots']),'original empty criteria adopted as thresholds')
        for key in('source_authority_verified','professional_review_authenticated','new_financial_values_generated','automatic_source_renewal_enabled','live_clock_or_monitor_enabled',
            'original_sheet_adapter_for_this_profile_implemented','financial_model_complete','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):
            require(p[key]is False,'synthetic currentness became authority: '+key)
        require(p['decision']=='PENDING'and p['personal_investor_return']is None,'whole deal/personal decision changed')
        if row['label']in('current','distributed'):
            require(p['current_project_return_story']==parent.payload['project_return_story']and p['current_irr_evidence']==parent.payload['irr_evidence'],'current gate modified cash, dates or roots')
            require(p['current_settlement_summary']==parent.payload['settlement_summary']and p['current_risk_observations']==json.loads(parent.payload['cash_risk_run']['payload_json'])['metrics'],'settlement or cash risk changed')
            require(m['event_count']==8 and sorted(i for g in m['event_groups']for i in g['event_indices'])==list(range(8))and sum(g['zero_event_count']for g in m['event_groups'])==3,'cash events/zeros omitted or duplicated')
            require(m['annual_years']==[2026,2027]and m['annual_rows_omitted']==0,'annual cash row omitted')
            require(all(line in text for line in ['Por 10 aportado: cobros 6','Neto escalado: -4','Gasto del seguro: 20','Pagos operativos: 15','Pago en cierre: 5','Capital declarado: Pendiente','n=4 z=3','current-results.json']),'central cash/settlement/pending stock/evidence text missing')
            if row['label']=='current':current=run
        else:
            require(p['current_project_return_story']is None and m['all_current_money_withheld'],'blocked source restored historical/isolated cash')
            require(all(p[k]is None for k in('current_settlement_summary','current_operating_totals','current_holding_sale_totals','current_risk_observations','current_irr_evidence','current_compiled_investor_json','current_nominal_insurance_totals')),'partial current money survived blocker')
            require(m['event_groups']==[]and m['annual_years']==[],'blocked page retained a calendar of old current money')
            for span in m['display_spans']:
                if any(ref.startswith('/current_')for ref in span['result_pointers']):require('pendiente'in span['text'].lower(),'blocked money span is not explicitly pending')
            if row['label']=='expired':require(any('/settlement/accounting_before_after:evidence_expired'==b for b in p['blockers']['evidence']),'exclusive terminal source expiry not exposed')
            if row['label']=='blocked':require(p['blockers']['evidence']==[]and'complete_settled_cash_path_blocked'in p['blockers']['gate'],'calculation failure incorrectly authenticated by current source declarations')
        cases.append(dict(label=row['label'],source_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),state=p['state'],source_requirements_checked=35,
            page_count=1,display_spans_checked=len(m['display_spans']),current_money_withheld=m['all_current_money_withheld'],blockers=p['blockers']))
        if row['label']in('current','expired','blocked'):
            directory=ROOT/('docs/review/miniuw-v1-current-settled-'+row['label']+'-example');packet=audit_current_settled_directory(directory)
            recovered,recovered_report=recover_current_settled_directory(directory);require(recovered==run and recovered_report==report and packet['files_verified']==6,'saved six-file current/blocked directory differs from source')
    require(current is not None,'current full source example required')
    # Also recover an independently written distributed candidate without overwriting the current directory.
    with tempfile.TemporaryDirectory()as td:
        row=fixture['cases'][-1];root=Path(td)/'candidate';write_current_settled_artifacts((ROOT/row['path']).read_bytes(),root);run,_=recover_current_settled_directory(root)
        require(run.sha256==row['run_sha256'],'candidate source-first directory recovery failed')
    paths=('src/miniuw_foundation/current_settled_case.py','src/miniuw_foundation/settled_output_report.py','src/miniuw_foundation/settled_output_artifacts.py',
        'src/miniuw_foundation/evidence_currency.py','src/miniuw_foundation/settled_case.py','tools/current_settled_miniuw_v1.py','tools/check_current_settled_T109.py',
        'docs/technical-implementation-T109.md','docs/review/current-settled-fixtures-T109.json')
    return dict(component='T109',status='passed_complete_source_gate_exact_parent_cash_one_page_and_blocked_recovery',source_cases_checked=4,saved_output_directories_checked=3,
        package_files_per_directory=6,sources_per_case=35,PDF_pages_per_output=1,cases=cases,current_run_sha256=current.sha256,
        original_T108_cash_dates_roots_and_risk_preserved=True,all_source_events_grouped_exactly_once=True,blocked_current_money_withheld=True,
        source_versions=[dict(path=p,sha256=sha((ROOT/p).read_bytes()))for p in paths],original_semantic_mappings_pending=54,
        original_sheet_adapter_for_this_profile_implemented=False,professional_review_authenticated=False,personal_return_verified=False,
        financial_model_complete=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored current settled validation differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
