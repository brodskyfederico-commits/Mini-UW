"""T95 source-first policy-renewal replay, verified one-page PDF and local package."""
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
import json,os,shutil,tempfile

from .drafts import ValidationError,canonical,digest
from .expense_cash_detail import _json,_exact
from .insurance_renewals import ENGINE_SHA256 as POLICY_ENGINE_SHA256,DEFINITION
from .policy_renewal_case import assemble_policy_renewal_case,PolicyRenewalCaseRun,ENGINE_SHA256 as CASE_ENGINE_SHA256
from .scheduled_expense_case import sha
from .scheduled_expense_artifacts import read_artifacts,MAX_ARTIFACT_BYTES,ENGINE_SHA256 as INVENTORY_ENGINE_SHA256
from .v1_report import _render_verified,V1Report,ENGINE_SHA256 as RENDER_ENGINE_SHA256

ENGINE_SHA256=sha(Path(__file__).read_bytes())
MAX_BUNDLE_BYTES=112*1024*1024


def encoded(p):return (canonical(p)+'\n').encode('utf-8')


def render_policy_renewal_report(raw,run):
    if type(run)is not PolicyRenewalCaseRun or assemble_policy_renewal_case(raw)!=run:raise ValidationError('policy report requires full exact source gate replay')
    base=_render_verified(run);manifest=base.manifest
    manifest.update(component='T95',policy_report_engine_sha256=ENGINE_SHA256,composition_engine_sha256=RENDER_ENGINE_SHA256,policy_gate_run_sha256=run.sha256,scope='One-page synthetic project return after complete successive insurance policy checks')
    text=canonical(manifest);return V1Report(base.pdf_bytes,text,digest(text))


def envelope(raw,run):
    return dict(schema='miniuw.synthetic-v1-policy-renewal-bundle.v1',engine_sha256=ENGINE_SHA256,case_engine_sha256=CASE_ENGINE_SHA256,policy_engine_sha256=POLICY_ENGINE_SHA256,inventory_engine_sha256=INVENTORY_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),case_utf8=raw.decode('utf-8'),result=asdict(run))


def export_policy_renewal_bundle(raw,run):
    if type(run)is not PolicyRenewalCaseRun or assemble_policy_renewal_case(raw)!=run:raise ValidationError('policy result must reproduce from exact sources')
    bundle=encoded(envelope(raw,run))
    if len(bundle)>MAX_BUNDLE_BYTES:raise ValidationError('policy renewal bundle size budget exceeded')
    return bundle


def recover_policy_renewal_bundle(raw):
    p=_json(raw,MAX_BUNDLE_BYTES);_exact(p,{'schema','engine_sha256','case_engine_sha256','policy_engine_sha256','inventory_engine_sha256','definition_sha256','case_utf8','result'})
    if p['schema']!='miniuw.synthetic-v1-policy-renewal-bundle.v1'or p['engine_sha256']!=ENGINE_SHA256 or p['case_engine_sha256']!=CASE_ENGINE_SHA256 or p['policy_engine_sha256']!=POLICY_ENGINE_SHA256 or p['inventory_engine_sha256']!=INVENTORY_ENGINE_SHA256 or p['definition_sha256']!=sha(DEFINITION.read_bytes()):raise ValidationError('compatible policy source and engine definitions required')
    if type(p['case_utf8'])is not str:raise ValidationError('exact policy case UTF-8 required')
    try:source=p['case_utf8'].encode('utf-8')
    except UnicodeError as error:raise ValidationError('valid policy source Unicode required')from error
    run=assemble_policy_renewal_case(source)
    if p!=envelope(source,run):raise ValidationError('policy bundle differs from complete replay')
    return run


def review_text(run):
    p=run.payload;lines=['MINI-UW | RENOVACIONES SINTETICAS DE SEGUROS','DECISION PENDIENTE | Sin despliegue ni decisiones reales.','Resultado SHA256 '+run.sha256]
    if p['current_policy_cost_totals']is None:lines+=['CIFRAS ACTUALES RETIRADAS',canonical(p['policy_blockers'])]
    else:
        for row in p['historical_policy_runs']:
            r=json.loads(row['payload_json']);lines+=[r['schedule_id']+' | '+r['currency'],'Totales: '+canonical(r['totals']),'Polizas y asignaciones: '+canonical(r['policy_rows']),'Grupos de cuotas: '+canonical(r['installment_groups'])]
    lines+=['Fechas, primas y fracciones suministradas. Suficiencia de cobertura y condiciones contractuales sin autenticar.','No se genera otro gasto, pago o reparto. Retorno personal y validacion financiera pendientes.','Bloqueos completos: '+canonical(p['blockers'])]
    return ('\n'.join(lines)+'\n').encode()


def build_policy_renewal_artifacts(raw):
    from pypdf import PdfReader
    run=assemble_policy_renewal_case(raw);report=render_policy_renewal_report(raw,run);bundle=export_policy_renewal_bundle(raw,run);reader=PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1 or tuple(float(x)for x in reader.pages[0].mediabox)!=(0.0,0.0,792.0,612.0):raise ValidationError('one landscape policy page required')
    text=reader.pages[0].extract_text()
    if any(s['text']not in text for s in report.manifest['display_spans']):raise ValidationError('policy PDF text span missing')
    audit=dict(component='T95',status='passed_deterministic_technical_check',input_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),manifest_sha256=report.manifest_sha256,page_count=1,full_source_and_policy_gate_replay=True,display_spans_extracted=True,independent_financial_audit=False,financial_publication_authorized=False,decision='PENDING')
    contents={'case.json':raw,'results.json':(run.payload_json+'\n').encode(),'execution-evidence.json':bundle,'MiniUW_v1_Resumen.pdf':report.pdf_bytes,'report-manifest.json':(report.manifest_json+'\n').encode(),'audit.json':encoded(audit),'schedule-review.txt':review_text(run)}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in contents.values()):raise ValidationError('policy artifact write budget exceeded')
    contents['package.json']=encoded(dict(schema='miniuw.synthetic-v1-policy-renewal-output.v1',engine_sha256=ENGINE_SHA256,run_sha256=run.sha256,files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(contents.items())],decision='PENDING',independent_financial_audit=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False))
    return contents,run


def audit_policy_renewal_directory(directory):
    contents=read_artifacts(directory);p=_json(contents['package.json'],65536);_exact(p,{'schema','engine_sha256','run_sha256','files','decision','independent_financial_audit','financial_publication_authorized','deployment_enabled','real_decisions_enabled'})
    expected_names=set(contents)-{'package.json'}
    if type(p['files'])is not list or len(p['files'])!=7 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])or {r['path']for r in p['files']if type(r['path'])is str}!=expected_names:raise ValidationError('safe exact policy artifact inventory required')
    for row in p['files']:
        value=contents[row['path']]
        if type(row['bytes'])is not int or len(value)!=row['bytes']or sha(value)!=row['sha256']:raise ValidationError('policy artifact byte/hash mismatch')
    expected,run=build_policy_renewal_artifacts(contents['case.json'])
    if contents!=expected:raise ValidationError('policy artifact directory differs from full replay')
    return dict(status='passed_deterministic_technical_check',files_verified=8,page_count=1,run_sha256=run.sha256,decision='PENDING',independent_financial_audit=False)


def write_policy_renewal_artifacts(raw,directory):
    contents,run=build_policy_renewal_artifacts(raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_artifacts(target)!=contents:raise ValidationError('different or incomplete policy output exists; choose new directory')
        return dict(status='identical_existing_verified',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-policies-',dir=target.parent))
    try:
        for name,value in contents.items():
            with (temporary/name).open('xb')as handle:handle.write(value);handle.flush();os.fsync(handle.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_policy_output_written',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
