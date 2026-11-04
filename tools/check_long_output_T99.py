"""Read-only full source/result/report recovery and exhaustive summary checks."""
from pathlib import Path
from io import BytesIO
import argparse,json,sys
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.capital_checked_output import assemble_capital_checked_output,render_capital_checked_output
from miniuw_foundation.long_horizon_artifacts import audit_long_horizon_directory,recover_long_horizon_bundle
from miniuw_foundation.scheduled_expense_artifacts import read_artifacts
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import PreviewLayoutError

EXAMPLE=ROOT/'docs/review/miniuw-v1-long-output-example'
RECORD=ROOT/'docs/review/long-output-validation-T99.json'


def verify():
    audit=audit_long_horizon_directory(EXAMPLE);files=read_artifacts(EXAMPLE)
    recovered=recover_long_horizon_bundle(files['execution-evidence.json']);run=recovered.run;p=run.payload
    if (recovered.case_raw!=files['case.json']or (run.payload_json+'\n').encode()!=files['results.json']
        or recovered.report.pdf_bytes!=files['MiniUW_v1_Resumen.pdf']
        or (recovered.report.manifest_json+'\n').encode()!=files['report-manifest.json']):
        raise ValidationError('long-window example differs from complete portable recovery')
    m=recovered.report.manifest;s=p['current_project_return_story']
    if (s['periodic_irr']['status']!='incomplete_synthetic'
        or s['periodic_irr']['root_classification']!='arithmetic_budget_exhausted'
        or s['annual_irr_roots']or s['selected_IRR']is not None):
        raise ValidationError('long-window unresolved numerical IRR state must remain explicit')
    indices=[i for group in m['event_groups']for i in group['event_indices']]
    if sorted(indices)!=list(range(16))or len(set(indices))!=16 or m['annual_years']!=list(range(2022,2028)):
        raise ValidationError('all sixteen events and six annual rows required without omissions')
    if p['latest_capital_state']!='PENDING'or s['capital_snapshots'][-1]['capital_still_invested']is not None:
        raise ValidationError('current capital visibility guard must remain pending')
    pages=PdfReader(BytesIO(recovered.report.pdf_bytes));text=pages.pages[0].extract_text()
    if len(pages.pages)!=1 or any(row['text']not in text for row in m['display_spans']):
        raise ValidationError('one-page complete display evidence required')
    for year in (2023,2024,2025):
        if str(year)+' A 0 C 0 N 0'not in text:raise ValidationError('cashless year omitted')
    if 'Capital declarado: Pendiente'not in text or 'Capital declarado: 1000'in text:
        raise ValidationError('pending capital representation mismatch')
    generation=json.loads((ROOT/'docs/review/long-output-fixture-generation-T99.json').read_bytes())
    if len(generation['cases'])!=3:raise ValidationError('three distinct declared fixture revisions required')
    legacy=[]
    for case in generation['cases']:
        source=(ROOT/case['path']).read_bytes()
        if sha(source)!=case['sha256']:raise ValidationError('fixture bytes changed')
        if case['path'].endswith('long-window-case.json'):
            current=run
            if source!=recovered.case_raw:raise ValidationError('saved long example source differs')
        else:current=assemble_capital_checked_output(source)
        story=current.payload['current_project_return_story']
        if story is None or len(story['dated_events'])!=case['events']or len(story['annual_cash_receipts'])!=case['years']:
            raise ValidationError('declared event/year inventory does not reproduce')
        for key,expected in (('gross_contributions',1400),('gross_distributions',778),('net_cash_profit',-622)):
            if story[key]!={'numerator':str(expected),'denominator':'1'}:raise ValidationError('synthetic cash changed unexpectedly')
        try:render_capital_checked_output(source,current)
        except PreviewLayoutError as error:
            if str(error)!=case['legacy_layout_error']:raise ValidationError('legacy limitation differs')
            legacy.append(str(error))
        else:raise ValidationError('legacy before/after limitation no longer reproduced')
    if 'annual rows exceed v1 page budget'not in legacy:
        raise ValidationError('separate legacy annual-row limit must be reproduced')
    return dict(component='T99',status='passed_exhaustive_onepage_source_first_recovery',files_verified=audit['files_verified'],
        page_count=1,fixture_revisions_checked=3,grouped_event_count=16,category_rows=7,annual_rows=6,
        cashless_years_checked=[2023,2024,2025],source_event_indices_exactly_once=True,annual_rows_omitted=0,
        capital_pending_preserved=True,legacy_event_and_year_limits_reproduced=True,result_component='T98',
        long_window_IRR_status=s['periodic_irr']['status'],long_window_IRR_root_classification=s['periodic_irr']['root_classification'],
        underlying_financial_result_changed=False,source_sha256=sha(files['case.json']),run_sha256=run.sha256,
        pdf_sha256=sha(files['MiniUW_v1_Resumen.pdf']),manifest_sha256=recovered.report.manifest_sha256,
        bundle_sha256=sha(files['execution-evidence.json']),
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in
            ('src/miniuw_foundation/long_horizon_report.py','src/miniuw_foundation/long_horizon_artifacts.py',
             'src/miniuw_foundation/capital_checked_output.py','tools/long_miniuw_v1.py','tools/check_long_output_T99.py',
             'docs/technical-implementation-T99.md','docs/review/long-output-fixture-generation-T99.json')],
        financial_policy_adopted=False,personal_return_verified=False,decision='PENDING',
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record and json.loads(RECORD.read_bytes())!=result:raise ValidationError('stored long-output validation differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
