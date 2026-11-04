"""Read-only original-layout sheet/case and blocked-source recovery checks."""
from io import BytesIO
from pathlib import Path
import argparse,json,sys
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError,canonical
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_case_output import assemble_worksheet_case,_from_verified_parent
from miniuw_foundation.worksheet_case_artifacts import (audit_worksheet_case_directory,read_worksheet_case_artifacts,
    recover_worksheet_case_bundle,export_worksheet_case_bundle)

EXAMPLE=ROOT/'docs/review/miniuw-v1-worksheet-case-example'
RECORD=ROOT/'docs/review/worksheet-case-validation-T103.json'


def require(value,message):
    if not value:raise ValidationError(message)


def verify():
    audit=audit_worksheet_case_directory(EXAMPLE);files=read_worksheet_case_artifacts(EXAMPLE)
    recovered=recover_worksheet_case_bundle(files['execution-evidence.json']);run=recovered.run;p=run.payload
    require((recovered.case_raw,recovered.workbook_raw,recovered.binding_raw)==tuple(files[k]for k in('case.json','Inputs.xlsx','binding.json')),
        'exact sheet/case/binding bytes differ after recovery')
    require((run.payload_json+'\n').encode()==files['results.json']and recovered.report.pdf_bytes==files['MiniUW_v1_Resumen.pdf'],
        'current result or PDF differs from source-first recovery')
    parent=run.parent_run.payload
    for key in('current_project_return_story','original_inputs','metrics','IRR_interval_comparison','input_catalog_summary','capital_visibility'):
        require(p[key]==parent[key],'matched worksheet changed financial source or semantic coverage: '+key)
    require(p['input_catalog_summary']==dict(total=55,bound=1,pending=54),'unresolved semantic mapping was promoted')
    generation=json.loads((ROOT/'docs/review/worksheet-fixture-generation-T103.json').read_bytes())
    require(sha((ROOT/generation['original_workbook']).read_bytes())==generation['original_sha256'],'original workbook changed')
    require([r['label']for r in generation['cases']]==['matched','zero-conflict','formula','other-case'],'four explicit sheet fixtures required')
    expected={'matched':dict(MATCHED_REPRESENTATION=1,MISSING_BOTH=54),
        'zero-conflict':dict(MATCHED_REPRESENTATION=1,MISSING_BOTH=53,CONFLICT=1),
        'formula':dict(MISSING_BOTH=54,PENDING=1),'other-case':dict(MATCHED_REPRESENTATION=1,MISSING_BOTH=54)}
    observations=[]
    for row in generation['cases']:
        args=tuple((ROOT/row[k]).read_bytes()for k in('case','workbook','binding'))
        require(all(sha(value)==row[key+'_sha256']for key,value in zip(('case','workbook','binding'),args)),'declared input bytes changed')
        require(args[0]==recovered.case_raw,'fixture replaced its economic source')
        current=run if row['label']=='matched'else _from_verified_parent(*args,run.parent_run)
        view=current.payload;check=view['worksheet_reconciliation'];items=check['rows']
        require(len(items)==55 and check['counts']==expected[row['label']]==row['counts'],'independent field inventory differs')
        require(view['worksheet_gate_open']==row['worksheet_gate_open']and
            (view['current_project_return_story']is not None)==row['current_story_available'],'declared gate did not reproduce')
        require(view['decision']=='PENDING'and not view['worksheet_values_adopted']and not view['case_or_recipe_automatically_updated']and
            not view['current_figures_are_parent_fallback'],'sheet adopted data or restored a fallback')
        require([r['field_id']for r in items]==[r['field_id']for r in parent['original_inputs']], 'field order/identity changed')
        for index,item in enumerate(items):
            require(item['worksheet_locator']=='xlsx:sheet:Inputs:cell:'+item['cell']and
                item['case_pointer'].endswith('/original_inputs/'+str(index)+'/value')and not item['financial_semantics_verified'],
                'cell locator or unresolved financial meaning changed')
        if row['label']=='zero-conflict':
            item=next(r for r in items if r['field_id']=='INPUT_C8')
            require(_fraction(item['decoded_representation'])==0 and item['case_value']is None and item['state']=='CONFLICT',
                'explicit zero became missing or silently replaced case value')
        elif row['label']=='formula':
            item=next(r for r in items if r['field_id']=='INPUT_C7')
            require(item['worksheet_cell']['formula']=='1+1'and item['worksheet_cell']['cached_value']=='2'and
                item['decoded_representation']is None and item['state']=='PENDING','formula/cache was adopted')
        elif row['label']=='other-case':require('worksheet_metadata_mismatch:B3'in check['blockers'],'cross-case sheet was accepted')
        if not view['worksheet_gate_open']:
            require(view['current_project_return_story']is None and view['IRR_interval_comparison']['enclosure']is None and
                all(m['value']is None for m in view['metrics']),'blocked sheet kept current money/IRR/metric values')
        observations.append(dict(label=row['label'],case_sha256=sha(args[0]),workbook_sha256=sha(args[1]),binding_sha256=sha(args[2]),
            run_sha256=current.sha256,worksheet_gate_open=view['worksheet_gate_open'],counts=check['counts'],
            blockers=check['blockers'],current_story_available=view['current_project_return_story']is not None))
    # Independent supplied expired financial source: matching sheet cannot revive it.
    expired=(ROOT/'templates/miniuw-v1-review-expired-candidate.json').read_bytes()
    binding=json.loads(recovered.binding_raw);binding.update(case_sha256=sha(expired),case_revision=53)
    br=(canonical(binding)+'\n').encode();blocked=assemble_worksheet_case(expired,recovered.workbook_raw,br)
    restored=recover_worksheet_case_bundle(export_worksheet_case_bundle(expired,recovered.workbook_raw,br,blocked))
    require(restored.run==blocked and blocked.payload['worksheet_gate_open']and blocked.payload['current_project_return_story']is None,
        'matching sheet revived financially expired output')
    pages=PdfReader(BytesIO(recovered.report.pdf_bytes));text=pages.pages[0].extract_text()
    require(len(pages.pages)==1 and 'Hoja cotejada'in text and 'Decision: PENDIENTE'in text and run.sha256 in text and
        sha(recovered.workbook_raw)in text and sha(recovered.case_raw)in text,'one-page sheet/case/current identity missing')
    paths=('src/miniuw_foundation/worksheet_case_output.py','src/miniuw_foundation/worksheet_case_artifacts.py',
        'src/miniuw_foundation/inputsheet.py','src/miniuw_foundation/workbooks.py','src/miniuw_foundation/normalization.py',
        'src/miniuw_foundation/data/input-sheet-layout-v1.json','src/miniuw_foundation/irr_interval_output.py',
        'tools/worksheet_case_miniuw_v1.py','tools/check_worksheet_case_T103.py','docs/technical-implementation-T103.md',
        'docs/review/worksheet-fixture-generation-T103.json')
    return dict(component='T103',status='passed_source_first_worksheet_case_and_expired_financial_recovery',
        files_verified=audit['files_verified'],page_count=1,fixture_sheets_checked=4,field_rows_checked=55,observations=observations,
        run_sha256=run.sha256,pdf_sha256=sha(recovered.report.pdf_bytes),manifest_sha256=recovered.report.manifest_sha256,
        expired_source_sha256=sha(expired),expired_run_sha256=blocked.sha256,expired_financial_source_not_revived=True,
        parent_financial_output_unchanged_when_matched=True,original_semantic_mappings_pending=54,
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in paths],
        worksheet_values_adopted=False,financial_field_mapping_completed=False,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored worksheet verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
