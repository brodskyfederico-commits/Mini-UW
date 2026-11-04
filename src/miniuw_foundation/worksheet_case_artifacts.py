"""T103 source-first workbook/case transport and exact nine-file local output."""
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO
import base64,binascii,os,shutil,tempfile
from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha,utf8
from .intake import MAX_BYTES
from .v1_report import V1Report
from .scheduled_expense_artifacts import MAX_ARTIFACT_BYTES
from .irr_interval_artifacts import export_irr_interval_bundle,recover_irr_interval_bundle,ENGINE_SHA256 as PARENT_ENGINE_SHA256
from .worksheet_case_output import (WorksheetCaseRun,assemble_worksheet_case,_from_verified_parent,_render_verified,
    ENGINE_SHA256 as CASE_ENGINE_SHA256,DEFINITION,READER,WORKBOOK_READER,LAYOUT,NUMERIC_ENGINE_SHA256)

ENGINE_SHA256=sha(Path(__file__).read_bytes())
FILES={'case.json','Inputs.xlsx','binding.json','results.json','execution-evidence.json',
    'MiniUW_v1_Resumen.pdf','report-manifest.json','audit.json','package.json'}
encoded=lambda p:(canonical(p)+'\n').encode()


def versions():
    return dict(engine_sha256=ENGINE_SHA256,case_engine_sha256=CASE_ENGINE_SHA256,parent_bundle_engine_sha256=PARENT_ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),worksheet_reader_sha256=sha(READER.read_bytes()),
        workbook_reader_sha256=sha(WORKBOOK_READER.read_bytes()),worksheet_layout_sha256=sha(LAYOUT.read_bytes()),
        numeric_decoder_sha256=NUMERIC_ENGINE_SHA256)


def _envelope(parent,workbook,binding,run,report):
    return dict(schema='miniuw.synthetic-worksheet-case-bundle.v1',**versions(),parent_bundle_utf8=parent.decode(),
        workbook_base64=base64.b64encode(workbook).decode(),binding_utf8=binding.decode(),
        result=dict(payload_json=run.payload_json,sha256=run.sha256),report_manifest_utf8=report.manifest_json,
        pdf_sha256=sha(report.pdf_bytes))


def _bundle(parent,workbook,binding,run,report):
    raw=encoded(_envelope(parent,workbook,binding,run,report))
    if len(raw)>MAX_ARTIFACT_BYTES:raise ValidationError('worksheet bundle byte budget exceeded')
    return raw


def export_worksheet_case_bundle(case_raw,workbook_raw,binding_raw,run):
    if type(run)is not WorksheetCaseRun or assemble_worksheet_case(case_raw,workbook_raw,binding_raw)!=run:
        raise ValidationError('worksheet run differs from complete source replay')
    parent=export_irr_interval_bundle(case_raw,run.parent_run)
    return _bundle(parent,workbook_raw,binding_raw,run,_render_verified(run))


@dataclass(frozen=True)
class RecoveredWorksheetCase:
    case_raw:bytes
    workbook_raw:bytes
    binding_raw:bytes
    run:WorksheetCaseRun
    report:V1Report


def recover_worksheet_case_bundle(raw):
    p=_json(raw,MAX_ARTIFACT_BYTES)
    _exact(p,{'schema',*versions(),'parent_bundle_utf8','workbook_base64','binding_utf8','result','report_manifest_utf8','pdf_sha256'})
    if p['schema']!='miniuw.synthetic-worksheet-case-bundle.v1'or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('exact compatible workbook/case source versions required')
    value=p['workbook_base64']
    if type(value)is not str or len(value)>4*((MAX_BYTES+2)//3):raise ValidationError('bounded base64 workbook required')
    try:workbook=base64.b64decode(value,validate=True)
    except(ValueError,binascii.Error)as error:raise ValidationError('invalid workbook base64')from error
    if len(workbook)>MAX_BYTES:raise ValidationError('workbook byte budget exceeded')
    parent_raw=utf8(p['parent_bundle_utf8'],MAX_ARTIFACT_BYTES);binding=utf8(p['binding_utf8'],65536)
    parent=recover_irr_interval_bundle(parent_raw)
    run=_from_verified_parent(parent.case_raw,workbook,binding,parent.run);report=_render_verified(run)
    if p!=_envelope(parent_raw,workbook,binding,run,report):raise ValidationError('workbook/case bundle differs from full replay')
    return RecoveredWorksheetCase(parent.case_raw,workbook,binding,run,report)


def _contents(case,workbook,binding,run,report,bundle):
    from pypdf import PdfReader
    reader=PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1:raise ValidationError('one worksheet-gated page required')
    text=reader.pages[0].extract_text()
    if any(row['text']not in text for row in report.manifest['display_spans']):raise ValidationError('complete worksheet-gated page text required')
    audit=dict(component='T103',status='passed_deterministic_worksheet_case_check',run_sha256=run.sha256,
        worksheet_gate_open=run.payload['worksheet_gate_open'],current_story_available=run.payload['current_project_return_story']is not None,
        bundle_sha256=sha(bundle),pdf_sha256=sha(report.pdf_bytes),page_count=1,
        independent_financial_audit=False,financial_publication_authorized=False,decision='PENDING')
    contents={'case.json':case,'Inputs.xlsx':workbook,'binding.json':binding,'results.json':(run.payload_json+'\n').encode(),
        'execution-evidence.json':bundle,'MiniUW_v1_Resumen.pdf':report.pdf_bytes,
        'report-manifest.json':(report.manifest_json+'\n').encode(),'audit.json':encoded(audit)}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in contents.values()):raise ValidationError('worksheet artifact byte budget exceeded')
    contents['package.json']=encoded(dict(schema='miniuw.synthetic-worksheet-case-package.v1',**versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(contents.items())],
        worksheet_values_adopted=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING'))
    return contents


def build_worksheet_case_artifacts(case_raw,workbook_raw,binding_raw):
    run=assemble_worksheet_case(case_raw,workbook_raw,binding_raw);report=_render_verified(run)
    parent=export_irr_interval_bundle(case_raw,run.parent_run);bundle=_bundle(parent,workbook_raw,binding_raw,run,report)
    return _contents(case_raw,workbook_raw,binding_raw,run,report,bundle),run


def read_worksheet_case_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular worksheet output directory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=FILES or any(p.is_symlink()or not p.is_file()or p.stat().st_size>MAX_ARTIFACT_BYTES for p in paths):
        raise ValidationError('exact nine bounded regular worksheet artifacts required')
    return {p.name:p.read_bytes()for p in paths}


def audit_worksheet_case_directory(directory):
    values=read_worksheet_case_artifacts(directory);p=_json(values['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','worksheet_values_adopted','financial_publication_authorized','deployment_enabled','real_decisions_enabled','decision'})
    if p['schema']!='miniuw.synthetic-worksheet-case-package.v1'or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('compatible worksheet artifact versions required')
    if(type(p['files'])is not list or len(p['files'])!=8 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])
        or {r['path']for r in p['files']if type(r['path'])is str}!=FILES-{'package.json'}):raise ValidationError('safe exact worksheet inventory required')
    for row in p['files']:
        raw=values[row['path']]
        if type(row['bytes'])is not int or row['bytes']!=len(raw)or row['sha256']!=sha(raw):raise ValidationError('worksheet artifact bytes/hash mismatch')
    recovered=recover_worksheet_case_bundle(values['execution-evidence.json'])
    expected=_contents(recovered.case_raw,recovered.workbook_raw,recovered.binding_raw,recovered.run,recovered.report,values['execution-evidence.json'])
    if values!=expected:raise ValidationError('worksheet packet differs from source-first replay')
    return dict(component='T103',status='passed_source_first_worksheet_case_replay',files_verified=9,page_count=1,
        run_sha256=recovered.run.sha256,worksheet_gate_open=recovered.run.payload['worksheet_gate_open'],decision='PENDING')


def write_worksheet_case_artifacts(case_raw,workbook_raw,binding_raw,directory):
    values,run=build_worksheet_case_artifacts(case_raw,workbook_raw,binding_raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_worksheet_case_artifacts(target)!=values:raise ValidationError('different or incomplete worksheet output exists; choose another directory')
        return dict(status='identical_existing_verified',run_sha256=run.sha256,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-worksheet-',dir=target.parent))
    try:
        for name,value in values.items():
            with(temporary/name).open('xb')as f:f.write(value);f.flush();os.fsync(f.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_worksheet_case_written',output=str(target),run_sha256=run.sha256,decision='PENDING')
