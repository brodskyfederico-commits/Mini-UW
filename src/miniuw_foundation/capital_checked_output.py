"""T98 capital visibility from existing T23 blockers, with source-first output."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import copy
import os
import shutil
import tempfile

from .drafts import ValidationError,canonical,digest
from .expense_cash_detail import _json,_exact
from .policy_renewal_case import assemble_policy_renewal_case,PolicyRenewalCaseRun
from .policy_renewal_artifacts import (export_policy_renewal_bundle,
    recover_policy_renewal_bundle,review_text,ENGINE_SHA256 as PARENT_ENGINE_SHA256,
    MAX_BUNDLE_BYTES as PARENT_MAX_BUNDLE_BYTES)
from .investor_onepage import _compose_verified,ENGINE_SHA256 as COMPOSITION_ENGINE_SHA256,DEFINITION as COMPOSITION_DEFINITION
from .scheduled_expense_case import sha,utf8
from .scheduled_expense_artifacts import read_artifacts,MAX_ARTIFACT_BYTES,ENGINE_SHA256 as INVENTORY_ENGINE_SHA256
from .v1_report import V1Report,amount,_render_verified as _base_current_view_page,ENGINE_SHA256 as BASE_RENDER_ENGINE_SHA256

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T98.md'
MAX_BUNDLE_BYTES=MAX_ARTIFACT_BYTES
BUNDLE_SCHEMA='miniuw.synthetic-v1-capital-checked-output-bundle.v1'
PACKAGE_SCHEMA='miniuw.synthetic-v1-capital-checked-output-package.v1'
STOCK='/current_project_return_story/capital_snapshots'


def encoded(value):
    return (canonical(value)+'\n').encode('utf-8')


@dataclass(frozen=True)
class CapitalCheckedRun:
    payload_json:str
    sha256:str
    parent_run:PolicyRenewalCaseRun

    @property
    def payload(self):
        return _json(self.payload_json.encode(),48*1024*1024)


def _from_verified_parent(parent):
    p=parent.payload
    story=p['current_project_return_story']
    claims=[] if story is None else copy.deepcopy(story['capital_snapshots'])
    visibility=[]
    if story is not None:
        for index,row in enumerate(story['capital_snapshots']):
            prefix='snapshot:'+row['as_of_date']+':'
            blockers=[b for b in story['upstream_story_blockers'] if b.startswith(prefix)]
            if blockers:
                # T23 already classified this shared stock record as unresolved.
                for key in ('capital_still_invested','retained_equity_value',
                            'normalized_capital_still_invested','normalized_retained_equity_value'):
                    row[key]=None
            visibility.append(dict(source_index=index,as_of_date=row['as_of_date'],
                state='PENDING' if blockers else 'declared_synthetic_not_derived',blockers=blockers,
                source_claim_pointer='/capital_source_claims/'+str(index),
                current_view_pointer=STOCK+'/'+str(index)))
    latest=None if not visibility else max(range(len(visibility)),key=lambda i:visibility[i]['as_of_date'])
    capital_blockers=([b for row in visibility for b in row['blockers']] if visibility
                      else ['current_projection_withheld' if story is None else 'capital_stock_sources_missing'])
    p['blockers']['capital']=capital_blockers
    p.update(component='T98',purpose='synthetic_capital_checked_investor_output',engine_sha256=ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),parent_financial_run_sha256=parent.sha256,
        capital_source_claims=claims,capital_visibility=visibility,
        latest_capital_snapshot_index=latest,latest_capital_state=(visibility[latest]['state'] if latest is not None else 'PENDING'),
        capital_values_derived=False,retained_equity_counted_as_cash=False,older_valid_snapshot_substituted=False,
        underlying_financial_pipeline_changed=False,financial_policy_adopted=False,
        state='current_synthetic_capital_checked_output' if story is not None else 'PENDING',
        independent_financial_audit=False,professional_review_authenticated=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    text=canonical(p)
    return CapitalCheckedRun(text,digest(text),parent)


def assemble_capital_checked_output(raw):
    return _from_verified_parent(assemble_policy_renewal_case(raw))


def _render_verified(raw,run):
    # Called only with a run assembled/recovered from fully verified sources.
    # Render the checked view directly; unresolved raw claims never enter layout.
    parent=_base_current_view_page(run)
    manifest=parent.manifest
    p=run.payload;story=p['current_project_return_story'];latest=p['latest_capital_snapshot_index']
    rows=[r for r in manifest['display_spans'] if r['result_pointers']==[STOCK]]
    if story is not None and latest is not None:
        if len(rows)!=2:
            raise ValidationError('compatible two-span capital record required')
        stock=story['capital_snapshots'][latest]
        for row in rows:
            if row['text'].startswith('Corte '):
                key='capital_still_invested'
                label='capital ' if stock[key] is None else 'capital declarado '
                row['text']='Corte '+stock['as_of_date']+': '+label+amount(stock[key])
            elif row['text'].startswith('Equity retenido (no caja):'):
                key='retained_equity_value'
                label='Equity retenido (no caja): ' if stock[key] is None else 'Equity retenido declarado (no caja): '
                row['text']=label+amount(stock[key])
            else:
                raise ValidationError('compatible capital span label required')
            row['result_pointers']=[STOCK+'/'+str(latest)+'/'+key,STOCK+'/'+str(latest)+'/as_of_date',
                '/capital_visibility/'+str(latest),'/capital_source_claims/'+str(latest)]
    for row in manifest['display_spans']:
        if row['text'].startswith('Resultado SHA256: '):
            row['text']='Resultado SHA256: '+run.sha256
        elif row['text'].startswith('Bloqueos: '):
            row['text']+=' | capital '+str(len(p['blockers']['capital']))
    text=canonical(manifest)
    proxy=V1Report(parent.pdf_bytes,text,digest(text))
    composed=_compose_verified(run,proxy)
    m=composed.manifest
    m.update(component='T98',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        composition_engine_sha256=COMPOSITION_ENGINE_SHA256,
        base_current_view_manifest_sha256=parent.manifest_sha256,
        base_current_view_engine_sha256=BASE_RENDER_ENGINE_SHA256,
        parent_financial_run_sha256=run.parent_run.sha256,capital_visibility=p['capital_visibility'],
        latest_capital_state=p['latest_capital_state'],capital_stock_derived=False,
        older_valid_snapshot_substituted=False,new_financial_calculations=False,
        independent_financial_audit=False,financial_publication_authorized=False,decision='PENDING')
    text=canonical(m)
    return V1Report(composed.pdf_bytes,text,digest(text))


def render_capital_checked_output(raw,run):
    if type(run) is not CapitalCheckedRun or assemble_capital_checked_output(raw)!=run:
        raise ValidationError('capital report requires exact complete source/visibility replay')
    return _render_verified(raw,run)


def versions():
    return dict(engine_sha256=ENGINE_SHA256,composition_engine_sha256=COMPOSITION_ENGINE_SHA256,
        base_view_engine_sha256=BASE_RENDER_ENGINE_SHA256,
        parent_bundle_engine_sha256=PARENT_ENGINE_SHA256,inventory_engine_sha256=INVENTORY_ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),composition_definition_sha256=sha(COMPOSITION_DEFINITION.read_bytes()))


def _envelope(parent_bundle,run,report):
    return dict(schema=BUNDLE_SCHEMA,**versions(),parent_bundle_utf8=parent_bundle.decode('utf-8'),
        result=dict(payload_json=run.payload_json,sha256=run.sha256),
        report_manifest_utf8=report.manifest_json,pdf_sha256=sha(report.pdf_bytes))


def _bundle(parent_bundle,run,report):
    result=encoded(_envelope(parent_bundle,run,report))
    if len(result)>MAX_BUNDLE_BYTES:
        raise ValidationError('capital output bundle byte budget exceeded')
    return result


def export_capital_checked_bundle(raw,run,report=None):
    if type(run) is not CapitalCheckedRun or assemble_capital_checked_output(raw)!=run:
        raise ValidationError('capital output must reproduce from exact sources')
    actual=_render_verified(raw,run)
    if report is not None and (type(report) is not V1Report or actual!=report):
        raise ValidationError('capital report differs from exact rendering')
    parent=export_policy_renewal_bundle(raw,run.parent_run)
    return _bundle(parent,run,actual)


@dataclass(frozen=True)
class RecoveredCapitalOutput:
    case_raw:bytes
    run:CapitalCheckedRun
    report:V1Report


def recover_capital_checked_bundle(raw):
    p=_json(raw,MAX_BUNDLE_BYTES)
    _exact(p,{'schema',*versions(),'parent_bundle_utf8','result','report_manifest_utf8','pdf_sha256'})
    if p['schema']!=BUNDLE_SCHEMA or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('compatible capital source, visibility and renderer versions required')
    parent_raw=utf8(p['parent_bundle_utf8'],PARENT_MAX_BUNDLE_BYTES)
    utf8(p['report_manifest_utf8'],1024*1024)
    parent=recover_policy_renewal_bundle(parent_raw)
    source=_json(parent_raw,PARENT_MAX_BUNDLE_BYTES)['case_utf8'].encode('utf-8')
    run=_from_verified_parent(parent)
    report=_render_verified(source,run)
    if p!=_envelope(parent_raw,run,report):
        raise ValidationError('capital bundle differs from source-first financial/visibility/PDF replay')
    return RecoveredCapitalOutput(source,run,report)


def build_capital_checked_artifacts(raw):
    from pypdf import PdfReader
    run=assemble_capital_checked_output(raw)
    report=_render_verified(raw,run)
    parent=export_policy_renewal_bundle(raw,run.parent_run)
    bundle=_bundle(parent,run,report)
    reader=PdfReader(BytesIO(report.pdf_bytes))
    if len(reader.pages)!=1 or tuple(float(v) for v in reader.pages[0].mediabox)!=(0.0,0.0,792.0,612.0):
        raise ValidationError('one landscape capital-checked page required')
    text=reader.pages[0].extract_text()
    if any(row['text'] not in text for row in report.manifest['display_spans']):
        raise ValidationError('capital PDF display span missing')
    audit=dict(component='T98',status='passed_deterministic_technical_check',input_sha256=sha(raw),
        run_sha256=run.sha256,parent_financial_run_sha256=run.parent_run.sha256,
        pdf_sha256=sha(report.pdf_bytes),manifest_sha256=report.manifest_sha256,bundle_sha256=sha(bundle),
        page_count=1,capital_visibility_replayed=True,new_financial_calculations=False,
        independent_financial_audit=False,financial_publication_authorized=False,decision='PENDING')
    review=review_text(run.parent_run)+('CAPITAL: DECLARACIONES SEPARADAS DE CIFRAS ACTUALES\n'+
        canonical(dict(visibility=run.payload['capital_visibility'],latest=run.payload['latest_capital_state']))+'\n').encode('utf-8')
    contents={'case.json':raw,'results.json':(run.payload_json+'\n').encode(),
        'execution-evidence.json':bundle,'MiniUW_v1_Resumen.pdf':report.pdf_bytes,
        'report-manifest.json':(report.manifest_json+'\n').encode(),'audit.json':encoded(audit),'schedule-review.txt':review}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in contents.values()):
        raise ValidationError('capital artifact write byte budget exceeded')
    contents['package.json']=encoded(dict(schema=PACKAGE_SCHEMA,**versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v)) for k,v in sorted(contents.items())],decision='PENDING',
        independent_financial_audit=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False))
    return contents,run


def audit_capital_checked_directory(directory):
    contents=read_artifacts(directory);p=_json(contents['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','decision','independent_financial_audit',
        'financial_publication_authorized','deployment_enabled','real_decisions_enabled'})
    if p['schema']!=PACKAGE_SCHEMA or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('compatible capital artifact package versions required')
    names=set(contents)-{'package.json'}
    if (type(p['files']) is not list or len(p['files'])!=7
        or any(type(r) is not dict or set(r)!={'path','bytes','sha256'} for r in p['files'])
        or {r['path'] for r in p['files'] if type(r['path']) is str}!=names):
        raise ValidationError('safe exact capital artifact inventory required')
    for row in p['files']:
        value=contents[row['path']]
        if type(row['bytes']) is not int or len(value)!=row['bytes'] or sha(value)!=row['sha256']:
            raise ValidationError('capital artifact byte/hash mismatch')
    expected,run=build_capital_checked_artifacts(contents['case.json'])
    if contents!=expected:
        raise ValidationError('capital artifacts differ from full financial/visibility/report replay')
    return dict(component='T98',status='passed_deterministic_technical_check',files_verified=8,
        page_count=1,run_sha256=run.sha256,latest_capital_state=run.payload['latest_capital_state'],
        decision='PENDING',independent_financial_audit=False,financial_publication_authorized=False)


def write_capital_checked_artifacts(raw,directory):
    contents,run=build_capital_checked_artifacts(raw);target=Path(directory).absolute()
    if target.exists() or target.is_symlink():
        if read_artifacts(target)!=contents:
            raise ValidationError('different or incomplete capital output exists; choose new directory')
        return dict(status='identical_existing_verified',output=str(target),run_sha256=run.sha256,page_count=1,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.miniuw-capital-',dir=target.parent))
    try:
        for name,value in contents.items():
            with (temporary/name).open('xb') as handle:
                handle.write(value);handle.flush();os.fsync(handle.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_capital_output_written',output=str(target),run_sha256=run.sha256,
                page_count=1,decision='PENDING')
