"""T92 exact source replay, one-page scheduled-expense view and local artifacts."""
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
import json
import os
import shutil
import tempfile

from .drafts import ValidationError,canonical,digest
from .expense_cash_detail import _json,_exact
from .expense_schedule import ENGINE_SHA256 as SCHEDULE_ENGINE_SHA256,DEFINITION
from .scheduled_expense_case import assemble_scheduled_expense_case,ScheduledExpenseCaseRun,ENGINE_SHA256 as CASE_ENGINE_SHA256,sha
from .v1_report import _render_verified,V1Report,ENGINE_SHA256 as RENDER_ENGINE_SHA256

ENGINE_SHA256=sha(Path(__file__).read_bytes())
MAX_BUNDLE_BYTES=72*1024*1024
MAX_ARTIFACT_BYTES=96*1024*1024
FILES={'case.json','results.json','execution-evidence.json','MiniUW_v1_Resumen.pdf','report-manifest.json','audit.json','schedule-review.txt','package.json'}


def encoded(p):return (canonical(p)+'\n').encode('utf-8')


def render_scheduled_expense_report(raw,run):
    if type(run)is not ScheduledExpenseCaseRun or assemble_scheduled_expense_case(raw)!=run:raise ValidationError('scheduled report requires exact complete current gate replay')
    rendered=_render_verified(run);manifest=rendered.manifest
    manifest.update(component='T92',scheduled_report_engine_sha256=ENGINE_SHA256,composition_engine_sha256=RENDER_ENGINE_SHA256,schedule_gate_result_sha256=run.sha256,
                    scope='One-page synthetic full project return after insurance and tax schedule/current-source checks')
    text=canonical(manifest);return V1Report(rendered.pdf_bytes,text,digest(text))


def envelope(raw,run):
    return dict(schema='miniuw.synthetic-v1-scheduled-expense-bundle.v1',engine_sha256=ENGINE_SHA256,case_engine_sha256=CASE_ENGINE_SHA256,schedule_engine_sha256=SCHEDULE_ENGINE_SHA256,
                definition_sha256=sha(DEFINITION.read_bytes()),case_utf8=raw.decode('utf-8'),result=asdict(run))


def export_scheduled_expense_bundle(raw,run):
    if type(run)is not ScheduledExpenseCaseRun or assemble_scheduled_expense_case(raw)!=run:raise ValidationError('scheduled source result must fully reproduce')
    bundle=encoded(envelope(raw,run))
    if len(bundle)>MAX_BUNDLE_BYTES:raise ValidationError('scheduled bundle byte budget exceeded')
    return bundle


def recover_scheduled_expense_bundle(raw):
    p=_json(raw,MAX_BUNDLE_BYTES);_exact(p,{'schema','engine_sha256','case_engine_sha256','schedule_engine_sha256','definition_sha256','case_utf8','result'})
    if p['schema']!='miniuw.synthetic-v1-scheduled-expense-bundle.v1' or p['engine_sha256']!=ENGINE_SHA256 or p['case_engine_sha256']!=CASE_ENGINE_SHA256 or p['schedule_engine_sha256']!=SCHEDULE_ENGINE_SHA256 or p['definition_sha256']!=sha(DEFINITION.read_bytes()):raise ValidationError('compatible schedule sources and engine definitions required')
    if type(p['case_utf8'])is not str:raise ValidationError('exact UTF-8 scheduled case required')
    try:source=p['case_utf8'].encode('utf-8')
    except UnicodeError as error:raise ValidationError('valid source Unicode required')from error
    run=assemble_scheduled_expense_case(source)
    if p!=envelope(source,run):raise ValidationError('scheduled bundle differs from full source replay')
    return run


def schedule_text(run):
    p=run.payload;rows=['MINI-UW | CALENDARIOS SINTETICOS DE SEGURO E IMPUESTO','DECISION PENDIENTE | Sin despliegue ni decisiones reales.','Resultado SHA256 '+run.sha256]
    if p['current_schedule_totals']is None:rows+=['CIFRAS ACTUALES RETIRADAS',canonical(p['schedule_blockers'])]
    else:
        rows+=['Importes por moneda declarada en cada calendario; fechas e importes de cuotas son suministrados.']
        for s in p['historical_schedule_runs']:
            v=json.loads(s['payload_json']);rows+=[v['schedule_id']+' | '+v['kind']+' | '+v['currency'],'Totales: '+canonical(v['totals']),'Asignaciones: '+canonical(v['allocations']),'Cuotas: '+canonical(v['installments'])]
    rows+=['La suficiencia de cobertura, autoridad fiscal, vigencia contractual, pagos bancarios y revision profesional siguen pendientes.','No se genera otro gasto, pago, reparto o financiamiento.','Bloqueos completos: '+canonical(p['blockers'])]
    return ('\n'.join(rows)+'\n').encode('utf-8')


def build_scheduled_expense_artifacts(raw):
    from pypdf import PdfReader
    run=assemble_scheduled_expense_case(raw);report=render_scheduled_expense_report(raw,run);bundle=export_scheduled_expense_bundle(raw,run)
    reader=PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1 or tuple(float(x)for x in reader.pages[0].mediabox)!=(0.0,0.0,792.0,612.0):raise ValidationError('one landscape scheduled summary page required')
    text=reader.pages[0].extract_text()
    if any(row['text']not in text for row in report.manifest['display_spans']):raise ValidationError('scheduled PDF display span missing')
    audit=dict(component='T92',status='passed_deterministic_technical_check',input_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),manifest_sha256=report.manifest_sha256,
               page_count=1,source_and_schedule_gate_replayed=True,display_spans_extracted=True,independent_financial_audit=False,professional_review_authenticated=False,decision='PENDING',financial_publication_authorized=False)
    contents={'case.json':raw,'results.json':(run.payload_json+'\n').encode(),'execution-evidence.json':bundle,'MiniUW_v1_Resumen.pdf':report.pdf_bytes,'report-manifest.json':(report.manifest_json+'\n').encode(),
              'audit.json':encoded(audit),'schedule-review.txt':schedule_text(run)}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in contents.values()):raise ValidationError('scheduled artifact write budget exceeded')
    contents['package.json']=encoded(dict(schema='miniuw.synthetic-v1-scheduled-expense-output.v1',engine_sha256=ENGINE_SHA256,run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(contents.items())],decision='PENDING',independent_financial_audit=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False))
    return contents,run


def read_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular scheduled output directory required')
    entries=list(root.iterdir())
    if {p.name for p in entries}!=FILES or any(p.is_symlink()or not p.is_file()for p in entries):raise ValidationError('exact regular scheduled artifact inventory required')
    if any(p.stat().st_size>MAX_ARTIFACT_BYTES for p in entries):raise ValidationError('scheduled artifact read budget exceeded')
    return {p.name:p.read_bytes()for p in entries}


def audit_scheduled_expense_directory(directory):
    contents=read_artifacts(directory);package=_json(contents['package.json'],65536)
    _exact(package,{'schema','engine_sha256','run_sha256','files','decision','independent_financial_audit','financial_publication_authorized','deployment_enabled','real_decisions_enabled'})
    if type(package['files'])is not list or len(package['files'])!=7 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in package['files'])or {r['path']for r in package['files']if type(r['path'])is str}!=FILES-{'package.json'}:raise ValidationError('safe exact scheduled package inventory required')
    for row in package['files']:
        value=contents[row['path']]
        if type(row['bytes'])is not int or len(value)!=row['bytes']or sha(value)!=row['sha256']:raise ValidationError('scheduled artifact bytes or hash mismatch')
    expected,run=build_scheduled_expense_artifacts(contents['case.json'])
    if expected!=contents:raise ValidationError('scheduled directory does not fully reproduce')
    return dict(status='passed_deterministic_technical_check',files_verified=8,page_count=1,run_sha256=run.sha256,decision='PENDING',independent_financial_audit=False)


def write_scheduled_expense_artifacts(raw,directory):
    contents,run=build_scheduled_expense_artifacts(raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_artifacts(target)!=contents:raise ValidationError('different or incomplete scheduled output exists; choose new directory')
        return dict(status='identical_existing_verified',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-scheduled-',dir=target.parent))
    try:
        for name,value in contents.items():
            with (temporary/name).open('xb')as handle:handle.write(value);handle.flush();os.fsync(handle.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_scheduled_output_written',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
