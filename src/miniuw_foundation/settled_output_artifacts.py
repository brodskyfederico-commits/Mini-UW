"""T109 six-file current-source one-page package with full numerical and PDF replay."""
from pathlib import Path
from io import BytesIO
import os,shutil,tempfile
from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha
from .settled_case_artifacts import versions as parent_versions
from .current_settled_case import assemble_current_settled_case,ENGINE_SHA256 as CURRENT_ENGINE_SHA256,DEFINITION
from .settled_output_report import render_settled_output,ENGINE_SHA256 as REPORT_ENGINE_SHA256
from .evidence_currency import ENGINE_SHA256 as EVIDENCE_ENGINE_SHA256,DEFINITION_PATH as EVIDENCE_DEFINITION
from .synthetic_onepager import ENGINE_SHA256 as PDF_ENGINE_SHA256
from .v1_report import ENGINE_SHA256 as FORMAT_ENGINE_SHA256

ENGINE_SHA256=sha(Path(__file__).read_bytes())
FILES={'current-settled-source.json','current-results.json','MiniUW_Resumen.pdf','report-manifest.json','audit.json','package.json'}
MAX_FILE_BYTES=32*1024*1024
encoded=lambda p:(canonical(p)+'\n').encode()


def versions():return dict(engine_sha256=ENGINE_SHA256,current_engine_sha256=CURRENT_ENGINE_SHA256,report_engine_sha256=REPORT_ENGINE_SHA256,
    evidence_engine_sha256=EVIDENCE_ENGINE_SHA256,evidence_definition_sha256=sha(EVIDENCE_DEFINITION.read_bytes()),
    definition_sha256=sha(DEFINITION.read_bytes()),pdf_engine_sha256=PDF_ENGINE_SHA256,format_engine_sha256=FORMAT_ENGINE_SHA256,parent=parent_versions())


def validate_report(raw,run,report):
    from pypdf import PdfReader
    if render_settled_output(raw,run)!=report:raise ValidationError('settled current PDF differs from source replay')
    reader=PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1 or tuple(float(v)for v in reader.pages[0].mediabox)!= (0.0,0.0,792.0,612.0):raise ValidationError('exact single landscape page required')
    extracted=reader.pages[0].extract_text()
    for span in report.manifest['display_spans']:
        if span['text']not in extracted:raise ValidationError('settled report span missing from PDF extraction')
    return dict(component='T109-audit',status='passed_source_currentness_calculation_and_one_page_replay',page_count=1,all_display_spans_extracted=True,
        input_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),manifest_sha256=report.manifest_sha256,
        visual_independent_financial_audit_performed=False,financial_publication_authorized=False,decision='PENDING')


def _contents(raw,run,report,audit):
    values={'current-settled-source.json':raw,'current-results.json':(run.payload_json+'\n').encode(),'MiniUW_Resumen.pdf':report.pdf_bytes,
        'report-manifest.json':(report.manifest_json+'\n').encode(),'audit.json':encoded(audit)}
    if any(len(v)>MAX_FILE_BYTES for v in values.values()):raise ValidationError('current settled artifact byte budget exceeded')
    values['package.json']=encoded(dict(schema='miniuw.synthetic-current-settled-package.v1',versions=versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(values.items())],page_count=1,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING'))
    return values


def build_current_settled_artifacts(raw):
    run=assemble_current_settled_case(raw);report=render_settled_output(raw,run);audit=validate_report(raw,run,report)
    return _contents(raw,run,report,audit),run,report


def read_current_settled_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular current settled directory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=FILES or any(p.is_symlink()or not p.is_file()or p.stat().st_size>MAX_FILE_BYTES for p in paths):raise ValidationError('exact six bounded regular current settled files required')
    return {p.name:p.read_bytes()for p in paths}


def recover_current_settled_directory(directory):
    values=read_current_settled_artifacts(directory);p=_json(values['package.json'],65536)
    _exact(p,{'schema','versions','run_sha256','files','page_count','financial_publication_authorized','deployment_enabled','real_decisions_enabled','decision'})
    if p['schema']!='miniuw.synthetic-current-settled-package.v1'or p['versions']!=versions():raise ValidationError('exact compatible current settled versions required')
    if(type(p['files'])is not list or len(p['files'])!=5 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])
        or {r['path']for r in p['files']if type(r['path'])is str}!=FILES-{'package.json'}):raise ValidationError('safe exact current settled inventory required')
    for row in p['files']:
        raw=values[row['path']]
        if type(row['bytes'])is not int or len(raw)!=row['bytes']or sha(raw)!=row['sha256']:raise ValidationError('current settled bytes/hash mismatch')
    expected,run,report=build_current_settled_artifacts(values['current-settled-source.json'])
    if values!=expected:raise ValidationError('current settled output differs from complete source-first replay')
    return run,report


def audit_current_settled_directory(directory):
    run,report=recover_current_settled_directory(directory)
    return dict(component='T109',status='passed_current_settled_source_first_one_page_recovery',files_verified=6,page_count=1,
        run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),state=run.payload['state'],decision='PENDING')


def write_current_settled_artifacts(raw,directory):
    values,run,report=build_current_settled_artifacts(raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_current_settled_artifacts(target)!=values:raise ValidationError('different or incomplete current settled output exists; choose another directory')
        return dict(status='identical_existing_verified',run_sha256=run.sha256,page_count=1,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-current-settled-',dir=target.parent))
    try:
        for name,value in values.items():
            with(temporary/name).open('xb')as f:f.write(value);f.flush();os.fsync(f.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_current_settled_output_written',output=str(target),run_sha256=run.sha256,page_count=1,pdf_sha256=sha(report.pdf_bytes),decision='PENDING')
