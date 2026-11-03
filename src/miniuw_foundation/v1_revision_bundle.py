"""T89 source-first portable comparison and bounded local internal review artifacts."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile

from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .v1_revision import compare_v1_cases,V1ComparisonRun,ENGINE_SHA256 as COMPARISON_ENGINE_SHA256,DEFINITION,sha
from .v1_report import amount

ENGINE_SHA256=sha(Path(__file__).read_bytes())
MAX_BUNDLE_BYTES=48*1024*1024
MAX_ARTIFACT_BYTES=64*1024*1024
FILES={'comparison.json','comparison-evidence.json','review.txt','package.json'}


def encoded(value):return (canonical(value)+'\n').encode('utf-8')


def envelope(reference_raw,candidate_raw,spec_raw,run):
    return dict(schema='miniuw.synthetic-v1-revision-bundle.v1',engine_sha256=ENGINE_SHA256,
                comparison_engine_sha256=COMPARISON_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
                reference_utf8=reference_raw.decode('utf-8'),candidate_utf8=candidate_raw.decode('utf-8'),spec_utf8=spec_raw.decode('utf-8'),result=asdict(run))


def export_comparison_bundle(reference_raw,candidate_raw,spec_raw,run):
    if type(run)is not V1ComparisonRun or compare_v1_cases(reference_raw,candidate_raw,spec_raw)!=run:
        raise ValidationError('comparison does not reproduce from exact complete sources')
    bundle=encoded(envelope(reference_raw,candidate_raw,spec_raw,run))
    if len(bundle)>MAX_BUNDLE_BYTES:raise ValidationError('comparison bundle size budget exceeded; cannot publish unrecoverable evidence')
    return bundle


def recover_comparison_bundle(bundle_raw):
    p=_json(bundle_raw,MAX_BUNDLE_BYTES)
    _exact(p,{'schema','engine_sha256','comparison_engine_sha256','definition_sha256','reference_utf8','candidate_utf8','spec_utf8','result'})
    if p['schema']!='miniuw.synthetic-v1-revision-bundle.v1' or p['engine_sha256']!=ENGINE_SHA256 or p['comparison_engine_sha256']!=COMPARISON_ENGINE_SHA256 or p['definition_sha256']!=sha(DEFINITION.read_bytes()):
        raise ValidationError('compatible comparison source/engine/definition version required')
    if any(type(p[k])is not str for k in ('reference_utf8','candidate_utf8','spec_utf8')):raise ValidationError('exact UTF-8 case sources required')
    try:
        sources=tuple(p[k].encode('utf-8')for k in ('reference_utf8','candidate_utf8','spec_utf8'))
    except UnicodeError as error:raise ValidationError('valid source Unicode required')from error
    run=compare_v1_cases(*sources)
    if p!=envelope(*sources,run):raise ValidationError('comparison bundle differs from complete replay')
    return run


def internal_text(run):
    p=run.payload;lines=['MINI-UW v1 | COMPARACION SINTETICA INTERNA','DECISION: PENDIENTE | Sin despliegue ni decisiones reales.',
                         'Comparacion: '+p['comparison_id'],'Base declarada: '+str(p['comparison_basis_ref']),
                         'Diferencias: candidata menos referencia. No se selecciona un caso ganador.',
                         'Alcance: equity agregado del proyecto; retorno personal pendiente.']
    deltas=p['projection_deltas']
    if deltas is None:lines+=['CIFRAS COMPARATIVAS RETIRADAS. Bloqueos: '+canonical(p['comparison_blockers'])]
    else:
        lines+=['METRICA | REFERENCIA | CANDIDATA | DIFERENCIA']
        for key,label in [('gross_contributions','Aportes'),('gross_distributions','Cobros'),('net_cash_profit','Resultado de caja'),('equity_multiple','EM')]:
            lines.append(label+' | '+amount(p['reference']['current_project_return_story'][key])+' | '+amount(p['candidate']['current_project_return_story'][key])+' | '+amount(deltas[key]))
        lines.append('Eventos con fechas y diferencias: '+canonical(p['event_deltas']))
        n=p['normalization_comparison']
        lines.append('Normalizacion: '+('deltas retirados '+canonical(n['blockers'])if n['deltas']is None else canonical(n['deltas'])))
    lines+=['IRR: todas las raices e intervalos exactos en comparison.json; no se elige ni resta una tasa.',
            'ESTADOS Y BLOQUEOS POR EXPEDIENTE']
    for key in ('reference','candidate'):
        row=p[key];lines+=[key+' revision '+str(row['case_revision'])+' | entrada SHA256 '+row['case_source_sha256'],
                         'Formulario: '+canonical(row['input_catalog_summary']),'Bloqueos: '+canonical(row['blockers'])]
    lines+=['TODAS LAS DIFERENCIAS DE ENTRADA ('+str(len(p['input_changes']))+')']
    for row in p['input_changes']:lines.append(canonical(row))
    lines+=['No se atribuye causalidad aislada ni se renueva evidencia; cambios de varias fuentes se muestran juntos.',
            'Comprobacion tecnica determinista; auditoria financiera y revision profesional autenticada pendientes.',
            'Resultado SHA256 '+run.sha256]
    return ('\n'.join(lines)+'\n').encode('utf-8')


def build_comparison_artifacts(reference_raw,candidate_raw,spec_raw):
    run=compare_v1_cases(reference_raw,candidate_raw,spec_raw)
    bundle=export_comparison_bundle(reference_raw,candidate_raw,spec_raw,run)
    contents={'comparison.json':(run.payload_json+'\n').encode(),'comparison-evidence.json':bundle,'review.txt':internal_text(run)}
    if any(len(value)>MAX_ARTIFACT_BYTES for value in contents.values()):raise ValidationError('comparison artifact write budget exceeded')
    contents['package.json']=encoded(dict(schema='miniuw.synthetic-v1-revision-output-package.v1',engine_sha256=ENGINE_SHA256,comparison_run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(contents.items())],decision='PENDING',independent_financial_audit=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False))
    return contents,run


def read_artifacts(root):
    root=Path(root)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular comparison output directory required')
    entries=list(root.iterdir())
    if {p.name for p in entries}!=FILES or any(p.is_symlink()or not p.is_file()for p in entries):raise ValidationError('exact regular comparison output inventory required')
    if any(p.stat().st_size>MAX_ARTIFACT_BYTES for p in entries):raise ValidationError('comparison artifact read budget exceeded')
    return {p.name:p.read_bytes()for p in entries}


def audit_comparison_directory(directory):
    contents=read_artifacts(directory);package=_json(contents['package.json'],65536)
    _exact(package,{'schema','engine_sha256','comparison_run_sha256','files','decision','independent_financial_audit','financial_publication_authorized','deployment_enabled','real_decisions_enabled'})
    if type(package['files'])is not list or len(package['files'])!=3 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in package['files'])or {r['path']for r in package['files']if type(r['path'])is str}!=FILES-{'package.json'}:
        raise ValidationError('exact internal comparison package inventory required')
    for row in package['files']:
        value=contents[row['path']]
        if type(row['bytes'])is not int or len(value)!=row['bytes']or sha(value)!=row['sha256']:raise ValidationError('comparison artifact byte/hash mismatch')
    bundle=contents['comparison-evidence.json'];run=recover_comparison_bundle(bundle);p=_json(bundle,MAX_BUNDLE_BYTES)
    expected,_=build_comparison_artifacts(*(p[k].encode()for k in ('reference_utf8','candidate_utf8','spec_utf8')))
    if contents!=expected:raise ValidationError('comparison artifact directory differs from full replay')
    return dict(status='passed_deterministic_technical_check',files_verified=4,comparison_run_sha256=run.sha256,decision='PENDING',independent_financial_audit=False)


def write_comparison_artifacts(reference_raw,candidate_raw,spec_raw,directory):
    contents,run=build_comparison_artifacts(reference_raw,candidate_raw,spec_raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_artifacts(target)!=contents:raise ValidationError('different comparison output exists; choose a new directory')
        return dict(status='identical_existing_verified',output=str(target),comparison_run_sha256=run.sha256,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-v1-comparison-',dir=target.parent))
    try:
        for name,value in contents.items():
            with (temporary/name).open('xb')as handle:handle.write(value);handle.flush();os.fsync(handle.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_comparison_written',output=str(target),comparison_run_sha256=run.sha256,decision='PENDING')
