"""T99 local package and source-first recovery for the exhaustive one-page summary."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import os,shutil,tempfile

from .drafts import ValidationError,canonical,digest
from .expense_cash_detail import _json,_exact
from .capital_checked_output import (CapitalCheckedRun,assemble_capital_checked_output,
    _from_verified_parent,ENGINE_SHA256 as CAPITAL_ENGINE_SHA256,DEFINITION as CAPITAL_DEFINITION)
from .long_horizon_report import (_render_verified,ENGINE_SHA256 as RENDER_ENGINE_SHA256,DEFINITION)
from .policy_renewal_artifacts import (export_policy_renewal_bundle,recover_policy_renewal_bundle,
    review_text,ENGINE_SHA256 as PARENT_ENGINE_SHA256,MAX_BUNDLE_BYTES as PARENT_MAX_BUNDLE_BYTES)
from .scheduled_expense_case import sha,utf8
from .scheduled_expense_artifacts import read_artifacts,MAX_ARTIFACT_BYTES,ENGINE_SHA256 as INVENTORY_ENGINE_SHA256
from .v1_report import V1Report

ENGINE_SHA256=sha(Path(__file__).read_bytes())
MAX_BUNDLE_BYTES=MAX_ARTIFACT_BYTES
BUNDLE_SCHEMA='miniuw.synthetic-v1-long-horizon-output-bundle.v1'
PACKAGE_SCHEMA='miniuw.synthetic-v1-long-horizon-output-package.v1'

def encoded(value):
    return (canonical(value)+'\n').encode('utf-8')

def versions():
    return dict(engine_sha256=ENGINE_SHA256,render_engine_sha256=RENDER_ENGINE_SHA256,
        capital_engine_sha256=CAPITAL_ENGINE_SHA256,parent_bundle_engine_sha256=PARENT_ENGINE_SHA256,
        inventory_engine_sha256=INVENTORY_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        capital_definition_sha256=sha(CAPITAL_DEFINITION.read_bytes()))

def _envelope(parent_bundle,run,report):
    return dict(schema=BUNDLE_SCHEMA,**versions(),parent_bundle_utf8=parent_bundle.decode('utf-8'),
        result=dict(payload_json=run.payload_json,sha256=run.sha256),
        report_manifest_utf8=report.manifest_json,pdf_sha256=sha(report.pdf_bytes))


def _bundle(parent_bundle,run,report):
    result=encoded(_envelope(parent_bundle,run,report))
    if len(result)>MAX_BUNDLE_BYTES:
        raise ValidationError('long-horizon output bundle byte budget exceeded')
    return result


def export_long_horizon_bundle(raw,run,report=None):
    if type(run) is not CapitalCheckedRun or assemble_capital_checked_output(raw)!=run:
        raise ValidationError('long-horizon output must reproduce from exact sources')
    actual=_render_verified(run)
    if report is not None and (type(report) is not V1Report or actual!=report):
        raise ValidationError('long-horizon report differs from exact rendering')
    parent=export_policy_renewal_bundle(raw,run.parent_run)
    return _bundle(parent,run,actual)


@dataclass(frozen=True)
class RecoveredLongOutput:
    case_raw:bytes
    run:CapitalCheckedRun
    report:V1Report


def recover_long_horizon_bundle(raw):
    p=_json(raw,MAX_BUNDLE_BYTES)
    _exact(p,{'schema',*versions(),'parent_bundle_utf8','result','report_manifest_utf8','pdf_sha256'})
    if p['schema']!=BUNDLE_SCHEMA or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('compatible capital source, visibility and renderer versions required')
    parent_raw=utf8(p['parent_bundle_utf8'],PARENT_MAX_BUNDLE_BYTES)
    utf8(p['report_manifest_utf8'],1024*1024)
    parent=recover_policy_renewal_bundle(parent_raw)
    source=_json(parent_raw,PARENT_MAX_BUNDLE_BYTES)['case_utf8'].encode('utf-8')
    run=_from_verified_parent(parent)
    report=_render_verified(run)
    if p!=_envelope(parent_raw,run,report):
        raise ValidationError('long-horizon bundle differs from source-first financial/visibility/PDF replay')
    return RecoveredLongOutput(source,run,report)


def build_long_horizon_artifacts(raw):
    from pypdf import PdfReader
    run=assemble_capital_checked_output(raw)
    report=_render_verified(run)
    parent=export_policy_renewal_bundle(raw,run.parent_run)
    bundle=_bundle(parent,run,report)
    reader=PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1 or tuple(float(v) for v in reader.pages[0].mediabox)!=(0.0,0.0,792.0,612.0):
        raise ValidationError('one landscape exhaustive-summary page required')
    text=reader.pages[0].extract_text()
    if any(row['text'] not in text for row in report.manifest['display_spans']):
        raise ValidationError('long-horizon PDF display span missing')
    audit=dict(component='T99',status='passed_deterministic_technical_check',input_sha256=sha(raw),
        run_sha256=run.sha256,parent_financial_run_sha256=run.parent_run.sha256,
        pdf_sha256=sha(report.pdf_bytes),manifest_sha256=report.manifest_sha256,bundle_sha256=sha(bundle),
        page_count=1,capital_visibility_replayed=True,all_events_grouped=True,annual_rows_omitted=0,new_financial_calculations=False,
        independent_financial_audit=False,financial_publication_authorized=False,decision='PENDING')
    review=review_text(run.parent_run)+('CAPITAL: DECLARACIONES SEPARADAS DE CIFRAS ACTUALES\n'+
        canonical(dict(visibility=run.payload['capital_visibility'],latest=run.payload['latest_capital_state']))+'\n').encode('utf-8')
    contents={'case.json':raw,'results.json':(run.payload_json+'\n').encode(),
        'execution-evidence.json':bundle,'MiniUW_v1_Resumen.pdf':report.pdf_bytes,
        'report-manifest.json':(report.manifest_json+'\n').encode(),'audit.json':encoded(audit),'schedule-review.txt':review}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in contents.values()):
        raise ValidationError('long-horizon artifact write byte budget exceeded')
    contents['package.json']=encoded(dict(schema=PACKAGE_SCHEMA,**versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v)) for k,v in sorted(contents.items())],decision='PENDING',
        independent_financial_audit=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False))
    return contents,run


def audit_long_horizon_directory(directory):
    contents=read_artifacts(directory);p=_json(contents['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','decision','independent_financial_audit',
        'financial_publication_authorized','deployment_enabled','real_decisions_enabled'})
    if p['schema']!=PACKAGE_SCHEMA or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('compatible long-horizon artifact package versions required')
    names=set(contents)-{'package.json'}
    if (type(p['files']) is not list or len(p['files'])!=7
        or any(type(r) is not dict or set(r)!={'path','bytes','sha256'} for r in p['files'])
        or {r['path'] for r in p['files'] if type(r['path']) is str}!=names):
        raise ValidationError('safe exact long-horizon artifact inventory required')
    for row in p['files']:
        value=contents[row['path']]
        if type(row['bytes']) is not int or len(value)!=row['bytes'] or sha(value)!=row['sha256']:
            raise ValidationError('long-horizon artifact byte/hash mismatch')
    expected,run=build_long_horizon_artifacts(contents['case.json'])
    if contents!=expected:
        raise ValidationError('long-horizon artifacts differ from full financial/visibility/report replay')
    return dict(component='T99',status='passed_deterministic_technical_check',files_verified=8,
        page_count=1,run_sha256=run.sha256,latest_capital_state=run.payload['latest_capital_state'],
        decision='PENDING',independent_financial_audit=False,financial_publication_authorized=False)


def write_long_horizon_artifacts(raw,directory):
    contents,run=build_long_horizon_artifacts(raw);target=Path(directory).absolute()
    if target.exists() or target.is_symlink():
        if read_artifacts(target)!=contents:
            raise ValidationError('different or incomplete long-horizon output exists; choose new directory')
        return dict(status='identical_existing_verified',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.miniuw-long-',dir=target.parent))
    try:
        for name,value in contents.items():
            with (temporary/name).open('xb') as handle:
                handle.write(value);handle.flush();os.fsync(handle.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_long_horizon_output_written',output=str(target),run_sha256=run.sha256,
                page_count=1,decision='PENDING')
