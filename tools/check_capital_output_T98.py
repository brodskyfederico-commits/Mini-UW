"""Read-only T98 source-first recovery and unresolved-capital regression check."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from io import BytesIO
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.capital_checked_output import audit_capital_checked_directory,recover_capital_checked_bundle
from miniuw_foundation.investor_onepage import render_investor_onepage
from miniuw_foundation.scheduled_expense_artifacts import read_artifacts

EXAMPLE=ROOT/'docs/review/miniuw-v1-capital-checked-example'
RECORD=ROOT/'docs/review/capital-output-validation-T98.json'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def verify():
    audit=audit_capital_checked_directory(EXAMPLE);files=read_artifacts(EXAMPLE)
    recovered=recover_capital_checked_bundle(files['execution-evidence.json']);p=recovered.run.payload
    if (recovered.case_raw!=files['case.json'] or (recovered.run.payload_json+'\n').encode()!=files['results.json']
        or recovered.report.pdf_bytes!=files['MiniUW_v1_Resumen.pdf']
        or (recovered.report.manifest_json+'\n').encode()!=files['report-manifest.json']):
        raise ValidationError('capital example differs from portable result/report recovery')
    story=p['current_project_return_story'];latest=p['latest_capital_snapshot_index']
    if story is None or latest!=1 or p['latest_capital_state']!='PENDING':
        raise ValidationError('unresolved latest-cut demonstration required')
    if any(story['capital_snapshots'][latest][key]is not None for key in
        ('capital_still_invested','retained_equity_value','normalized_capital_still_invested','normalized_retained_equity_value')):
        raise ValidationError('unresolved stock current values leaked')
    if p['capital_source_claims'][latest]['capital_still_invested']!={'numerator':'1000','denominator':'1'}:
        raise ValidationError('original declaration not preserved')
    for key in ('gross_contributions','gross_distributions','net_cash_profit','equity_multiple','annual_irr_roots','annual_cash_receipts'):
        if story[key]!=recovered.run.parent_run.payload['current_project_return_story'][key]:
            raise ValidationError('unrelated financial result changed')
    before=render_investor_onepage(recovered.case_raw,recovered.run.parent_run)
    before_text=PdfReader(BytesIO(before.pdf_bytes)).pages[0].extract_text()
    after=PdfReader(BytesIO(recovered.report.pdf_bytes));after_text=after.pages[0].extract_text()
    if not all(value in before_text for value in ('capital 1000.0000','Equity retenido (no caja): 900.0000')):
        raise ValidationError('legacy reproduction differs from scoped before/after case')
    if not all(value in after_text for value in ('Corte 2027-06-01: capital Pendiente','Equity retenido (no caja): Pendiente')):
        raise ValidationError('current pending capital labels missing')
    if any(value in after_text for value in ('capital 1000.0000','capital 1300.0000','Equity retenido (no caja): 900.0000')):
        raise ValidationError('raw or older capital leaked into current PDF')
    generation=json.loads((ROOT/'docs/review/capital-fixture-generation-T98.json').read_bytes())
    if len(generation['cases'])!=5:raise ValidationError('five explicit synthetic fixture revisions required')
    for case in generation['cases']:
        raw=(ROOT/case['case']).read_bytes()
        if sha(raw)!=case['sha256']:raise ValidationError('capital fixture bytes differ')
        outer=json.loads(raw);parent=json.loads(outer['scheduled_case_utf8']);base=json.loads(parent['base_case_utf8'])
        if base['recipe']['investor_source']['capital_snapshots']!=case['source_claims']:
            raise ValidationError('fixture declared capital differs')
    return dict(component='T98',status='passed_source_first_capital_visibility_and_package_replay',
        files_verified=audit['files_verified'],page_count=len(after.pages),fixture_revisions_checked=5,
        latest_capital_state=p['latest_capital_state'],original_claims_preserved=True,
        pending_current_stock_values_withheld=True,older_cut_not_substituted=True,
        underlying_financial_results_preserved=True,legacy_difference_reproduced=True,
        source_sha256=sha(files['case.json']),run_sha256=recovered.run.sha256,
        parent_financial_run_sha256=recovered.run.parent_run.sha256,
        pdf_sha256=sha(recovered.report.pdf_bytes),manifest_sha256=recovered.report.manifest_sha256,
        bundle_sha256=sha(files['execution-evidence.json']),
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in
            ('src/miniuw_foundation/capital_checked_output.py','tools/capital_miniuw_v1.py',
             'tools/check_capital_output_T98.py','docs/technical-implementation-T98.md',
             'docs/review/capital-fixture-generation-T98.json')],
        capital_definition_adopted=False,capital_value_derived=False,personal_return_verified=False,
        decision='PENDING',independent_financial_audit=False,deployment_enabled=False,real_decisions_enabled=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record and json.loads(RECORD.read_bytes())!=result:
            raise ValidationError('stored capital visibility verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
