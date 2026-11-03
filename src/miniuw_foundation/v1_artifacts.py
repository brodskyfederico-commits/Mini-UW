"""T86 local atomic synthetic artifacts and deterministic (not financial) audit."""
from io import BytesIO
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile

from .drafts import ValidationError,canonical
from .v1_case import run_v1_case
from .v1_report import render_v1_report
from .v1_contracts import load_contracts

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FILES={'case.json','results.json','execution-evidence.json','MiniUW_v1_Resumen.pdf','report-manifest.json','audit.json','bot-execution.json','package.json'}


def encoded(p):return (canonical(p)+'\n').encode('utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()


def technical_audit(case_raw,run,report):
    from pypdf import PdfReader
    expected=run_v1_case(case_raw)
    if expected!=run:raise ValidationError('v1 results do not reproduce')
    # Public renderer replays sources, so an updated-hash result cannot bypass the check.
    expected_report=render_v1_report(case_raw,expected)
    if expected_report!=report:raise ValidationError('v1 report or manifest differs from reproduced results')
    reader=PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1 or tuple(float(n)for n in reader.pages[0].mediabox)!=(0.0,0.0,792.0,612.0):
        raise ValidationError('exactly one landscape executive page required')
    extracted=reader.pages[0].extract_text()
    for span in report.manifest['display_spans']:
        if span['text']not in extracted:raise ValidationError('rendered source span missing in PDF text')
    return dict(component='T86',status='passed_deterministic_technical_check',engine_sha256=ENGINE_SHA256,
                input_sha256=sha(case_raw),results_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),
                manifest_sha256=report.manifest_sha256,page_count=1,source_replay=True,all_display_spans_extracted=True,
                independent_financial_audit=False,professional_review_authenticated=False,financial_publication_authorized=False,decision='PENDING')


def build_artifacts(case_raw):
    run=run_v1_case(case_raw);report=render_v1_report(case_raw,run);audit=technical_audit(case_raw,run,report)
    contracts,contracts_sha=load_contracts();p=run.payload;trace=[]
    for bot in contracts['bots']:
        bid=bot['bot_id'];status='not_executed_contract_pending'
        if bid in ('B01','B02'):status='completed_synthetic'
        elif bid=='B04':status='indexed_with_pending_fields'
        elif bid=='B12':status='decision_blocked_pending'
        elif bid=='B13':status='computed_supported_synthetic_profile'if p['current_project_return_story']is not None else'blocked_or_stale'
        elif bid=='B14':status='simulation_only_decision_pending'
        elif bid=='B15':status='one_page_generated'
        elif bid=='B16':status='deterministic_technical_check_only'
        elif bid=='B17':status='not_executed_per_case_release_CI_required'
        trace.append(dict(bot_id=bid,dot_id=bot['dot_id'],status=status,case_source_sha256=p['case_source_sha256'],
                          contract_status=bot['status'],external_actions_performed=False))
    bundle=run.execution_bundle
    if bundle is None:bundle=encoded(dict(schema='miniuw.v1-blocked-execution-evidence.v1',input_sha256=sha(case_raw),blockers=p['blockers']['projection'],producer_outputs_not_generated=True))
    contents={'case.json':case_raw,'results.json':encoded(p),'execution-evidence.json':bundle,'MiniUW_v1_Resumen.pdf':report.pdf_bytes,
              'report-manifest.json':(report.manifest_json+'\n').encode(),'audit.json':encoded(audit),
              'bot-execution.json':encoded(dict(component='T87',contracts_sha256=contracts_sha,bot_runs=trace,agents_deployed=False,independent_financial_audit=False))}
    package=dict(schema='miniuw.synthetic-v1-output-package.v1',input_sha256=sha(case_raw),run_sha256=run.sha256,
                 files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(contents.items())],
                 decision='PENDING',financial_publication_authorized=False,real_decisions_enabled=False,deployment_enabled=False)
    contents['package.json']=encoded(package)
    return contents,run,report


def audit_directory(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir()or {p.name for p in root.iterdir()}!=FILES or any(p.is_symlink()or not p.is_file()for p in root.iterdir()):
        raise ValidationError('exact regular output artifact inventory required')
    package=json.loads((root/'package.json').read_bytes())
    if package.get('schema')!='miniuw.synthetic-v1-output-package.v1' or len(package.get('files',[]))!=7 or {r.get('path')for r in package['files']}!=FILES-{'package.json'}:
        raise ValidationError('exact package path inventory required')
    for row in package['files']:
        raw=(root/row['path']).read_bytes()
        if len(raw)!=row['bytes']or sha(raw)!=row['sha256']:raise ValidationError('artifact byte/hash mismatch')
    contents,run,report=build_artifacts((root/'case.json').read_bytes())
    if any((root/name).read_bytes()!=value for name,value in contents.items()):raise ValidationError('artifact package does not fully reproduce')
    return dict(status='passed_deterministic_technical_check',files_verified=len(contents),page_count=1,input_sha256=run.payload['case_source_sha256'],run_sha256=run.sha256,
                independent_financial_audit=False,decision='PENDING')


def write_case_artifacts(case_raw,directory):
    contents,run,report=build_artifacts(case_raw)
    target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if target.is_symlink()or not target.is_dir()or {p.name for p in target.iterdir()}!=FILES or any(p.is_symlink()for p in target.iterdir())or any((target/k).read_bytes()!=v for k,v in contents.items()):
            raise ValidationError('output exists with different or incomplete artifacts; choose a new run directory')
        return dict(status='identical_existing_verified',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.miniuw-v1-',dir=target.parent))
    try:
        for name,value in contents.items():
            with (temporary/name).open('xb')as handle:
                handle.write(value);handle.flush();os.fsync(handle.fileno())
        # Rename of a complete local directory; no external/production publication.
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_output_written',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
