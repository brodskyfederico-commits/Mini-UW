"""T97 source-first portable T96 investor page and exact local output package."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import os
import shutil
import tempfile

from .drafts import ValidationError, canonical
from .expense_cash_detail import _json, _exact
from .investor_onepage import render_investor_onepage, ENGINE_SHA256 as RENDER_ENGINE_SHA256, DEFINITION as RENDER_DEFINITION
from .policy_renewal_case import assemble_policy_renewal_case, PolicyRenewalCaseRun
from .policy_renewal_artifacts import (
    export_policy_renewal_bundle, recover_policy_renewal_bundle, review_text,
    ENGINE_SHA256 as PARENT_ENGINE_SHA256, MAX_BUNDLE_BYTES as PARENT_MAX_BUNDLE_BYTES,
)
from .scheduled_expense_case import sha, utf8
from .scheduled_expense_artifacts import read_artifacts, MAX_ARTIFACT_BYTES, ENGINE_SHA256 as INVENTORY_ENGINE_SHA256
from .v1_report import V1Report

ENGINE_SHA256 = sha(Path(__file__).read_bytes())
DEFINITION = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T97.md'
MAX_BUNDLE_BYTES = MAX_ARTIFACT_BYTES
BUNDLE_SCHEMA = 'miniuw.synthetic-v1-investor-output-bundle.v1'
PACKAGE_SCHEMA = 'miniuw.synthetic-v1-investor-output-package.v1'


def encoded(value):
    return (canonical(value)+'\n').encode('utf-8')


def versions():
    return dict(engine_sha256=ENGINE_SHA256, renderer_engine_sha256=RENDER_ENGINE_SHA256,
                parent_bundle_engine_sha256=PARENT_ENGINE_SHA256, inventory_engine_sha256=INVENTORY_ENGINE_SHA256,
                definition_sha256=sha(DEFINITION.read_bytes()), renderer_definition_sha256=sha(RENDER_DEFINITION.read_bytes()))


def _envelope(parent_bundle, report):
    return dict(schema=BUNDLE_SCHEMA, **versions(), parent_bundle_utf8=parent_bundle.decode('utf-8'),
                report_manifest_utf8=report.manifest_json, pdf_sha256=sha(report.pdf_bytes))


def _bounded_bundle(parent_bundle, report):
    result = encoded(_envelope(parent_bundle,report))
    if len(result)>MAX_BUNDLE_BYTES:
        raise ValidationError('investor output bundle byte budget exceeded')
    return result


def export_investor_output_bundle(raw, run, report=None):
    # The parent exporter and renderer each verify the complete exact source/run.
    parent = export_policy_renewal_bundle(raw,run)
    actual = render_investor_onepage(raw,run)
    if report is not None and (type(report) is not V1Report or report != actual):
        raise ValidationError('investor output report must reproduce from exact source')
    return _bounded_bundle(parent,actual)


@dataclass(frozen=True)
class RecoveredInvestorOutput:
    case_raw: bytes
    run: PolicyRenewalCaseRun
    report: V1Report


def recover_investor_output_bundle(raw):
    p = _json(raw,MAX_BUNDLE_BYTES)
    expected_keys = {'schema',*versions(),'parent_bundle_utf8','report_manifest_utf8','pdf_sha256'}
    _exact(p,expected_keys)
    if p['schema'] != BUNDLE_SCHEMA or any(p[key]!=value for key,value in versions().items()):
        raise ValidationError('compatible investor output source and renderer versions required')
    parent = utf8(p['parent_bundle_utf8'],PARENT_MAX_BUNDLE_BYTES)
    utf8(p['report_manifest_utf8'],1024*1024)
    run = recover_policy_renewal_bundle(parent)
    parent_payload = _json(parent,PARENT_MAX_BUNDLE_BYTES)
    source = parent_payload['case_utf8'].encode('utf-8')
    report = render_investor_onepage(source,run)
    if p != _envelope(parent,report):
        raise ValidationError('investor output bundle differs from source-first result/report replay')
    return RecoveredInvestorOutput(source,run,report)


def build_investor_output_artifacts(raw):
    from pypdf import PdfReader
    run = assemble_policy_renewal_case(raw)
    report = render_investor_onepage(raw,run)
    parent = export_policy_renewal_bundle(raw,run)
    # Both objects were produced by the guarded public APIs above.
    bundle = _bounded_bundle(parent,report)
    reader = PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1 or tuple(float(x) for x in reader.pages[0].mediabox)!=(0.0,0.0,792.0,612.0):
        raise ValidationError('one landscape investor page required')
    text = reader.pages[0].extract_text()
    if any(row['text'] not in text for row in report.manifest['display_spans']):
        raise ValidationError('investor PDF display span missing')
    audit = dict(component='T97', renderer_component='T96',status='passed_deterministic_technical_check',
                 input_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),
                 manifest_sha256=report.manifest_sha256,portable_bundle_sha256=sha(bundle),page_count=1,
                 full_source_and_policy_gate_replayed=True,display_spans_extracted=True,
                 new_financial_calculations=False,independent_financial_audit=False,
                 financial_publication_authorized=False,decision='PENDING')
    contents = {'case.json':raw,'results.json':(run.payload_json+'\n').encode('utf-8'),
                'execution-evidence.json':bundle,'MiniUW_v1_Resumen.pdf':report.pdf_bytes,
                'report-manifest.json':(report.manifest_json+'\n').encode('utf-8'),
                'audit.json':encoded(audit),'schedule-review.txt':review_text(run)}
    if any(len(value)>MAX_ARTIFACT_BYTES for value in contents.values()):
        raise ValidationError('investor artifact write byte budget exceeded')
    contents['package.json'] = encoded(dict(schema=PACKAGE_SCHEMA, **versions(),run_sha256=run.sha256,
        files=[dict(path=key,bytes=len(value),sha256=sha(value)) for key,value in sorted(contents.items())],
        decision='PENDING',independent_financial_audit=False,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False))
    return contents,run


def audit_investor_output_directory(directory):
    contents = read_artifacts(directory)
    p = _json(contents['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','decision','independent_financial_audit',
              'financial_publication_authorized','deployment_enabled','real_decisions_enabled'})
    if p['schema']!=PACKAGE_SCHEMA or any(p[key]!=value for key,value in versions().items()):
        raise ValidationError('compatible investor output package versions required')
    expected_names = set(contents)-{'package.json'}
    if (type(p['files']) is not list or len(p['files'])!=7
            or any(type(row) is not dict or set(row)!={'path','bytes','sha256'} for row in p['files'])
            or {row['path'] for row in p['files'] if type(row['path']) is str}!=expected_names):
        raise ValidationError('safe exact investor artifact inventory required')
    for row in p['files']:
        value = contents[row['path']]
        if type(row['bytes']) is not int or len(value)!=row['bytes'] or sha(value)!=row['sha256']:
            raise ValidationError('investor artifact byte/hash mismatch')
    expected,run = build_investor_output_artifacts(contents['case.json'])
    if contents != expected:
        raise ValidationError('investor output directory differs from exact source/result/report replay')
    return dict(status='passed_deterministic_technical_check',component='T97',files_verified=8,
                page_count=1,run_sha256=run.sha256,renderer_component='T96',decision='PENDING',
                independent_financial_audit=False,financial_publication_authorized=False)


def write_investor_output_artifacts(raw, directory):
    contents,run = build_investor_output_artifacts(raw)
    target = Path(directory).absolute()
    if target.exists() or target.is_symlink():
        if read_artifacts(target)!=contents:
            raise ValidationError('different or incomplete investor output exists; choose a new directory')
        return dict(status='identical_existing_verified',output=str(target),run_sha256=run.sha256,
                    page_count=1,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.miniuw-investor-',dir=target.parent))
    try:
        for name,value in contents.items():
            with (temporary/name).open('xb') as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_investor_output_written',output=str(target),run_sha256=run.sha256,
                page_count=1,decision='PENDING')
