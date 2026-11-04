"""T102 source-first review evidence, candidate PDF and strict seven-file packet."""
from dataclasses import dataclass
from pathlib import Path
import os,shutil,tempfile

from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha,utf8
from .scheduled_expense_artifacts import MAX_ARTIFACT_BYTES
from .v1_report import V1Report
from .irr_interval_artifacts import (export_irr_interval_bundle,recover_irr_interval_bundle,
    ENGINE_SHA256 as PARENT_ENGINE_SHA256,MAX_BUNDLE_BYTES as PARENT_MAX_BUNDLE_BYTES)
from .irr_interval_output import _render_verified,ENGINE_SHA256 as PARENT_CASE_ENGINE_SHA256,DEFINITION as PARENT_DEFINITION
from .irr_revision_review import (IRRRevisionReviewRun,compare_irr_revisions,_from_verified_pair,review_text,
    ENGINE_SHA256 as REVIEW_ENGINE_SHA256,DIFF_ENGINE_SHA256,DEFINITION)

ENGINE_SHA256=sha(Path(__file__).read_bytes())
MAX_BUNDLE_BYTES=MAX_ARTIFACT_BYTES
FILES={'comparison-spec.json','reference-evidence.json','candidate-evidence.json','revision-review.json',
    'revision-review.txt','candidate-MiniUW_v1_Resumen.pdf','package.json'}


def encoded(p):return (canonical(p)+'\n').encode()


def versions():
    return dict(engine_sha256=ENGINE_SHA256,review_engine_sha256=REVIEW_ENGINE_SHA256,
        diff_engine_sha256=DIFF_ENGINE_SHA256,parent_bundle_engine_sha256=PARENT_ENGINE_SHA256,
        parent_case_engine_sha256=PARENT_CASE_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        parent_definition_sha256=sha(PARENT_DEFINITION.read_bytes()))


def _envelope(reference_bundle,candidate_bundle,spec_raw,run,report):
    return dict(schema='miniuw.synthetic-IRR-review-bundle.v1',**versions(),
        reference_bundle_utf8=reference_bundle.decode(),candidate_bundle_utf8=candidate_bundle.decode(),
        spec_utf8=spec_raw.decode(),result=dict(payload_json=run.payload_json,sha256=run.sha256),
        review_text_sha256=sha(review_text(run)),candidate_pdf_sha256=sha(report.pdf_bytes))


def export_review_bundle(reference_raw,candidate_raw,spec_raw,run):
    if type(run)is not IRRRevisionReviewRun or compare_irr_revisions(reference_raw,candidate_raw,spec_raw)!=run:
        raise ValidationError('review must reproduce from both complete sources and exact specification')
    rb=export_irr_interval_bundle(reference_raw,run.reference_run);cb=export_irr_interval_bundle(candidate_raw,run.candidate_run)
    report=_render_verified(run.candidate_run);bundle=encoded(_envelope(rb,cb,spec_raw,run,report))
    if len(bundle)>MAX_BUNDLE_BYTES:raise ValidationError('review bundle byte budget exceeded')
    return bundle


@dataclass(frozen=True)
class RecoveredReview:
    reference_raw:bytes
    candidate_raw:bytes
    spec_raw:bytes
    run:IRRRevisionReviewRun
    candidate_report:V1Report


def recover_review_bundle(raw):
    p=_json(raw,MAX_BUNDLE_BYTES)
    _exact(p,{'schema',*versions(),'reference_bundle_utf8','candidate_bundle_utf8','spec_utf8','result','review_text_sha256','candidate_pdf_sha256'})
    if p['schema']!='miniuw.synthetic-IRR-review-bundle.v1'or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('exact compatible review and parent source versions required')
    rb=utf8(p['reference_bundle_utf8'],PARENT_MAX_BUNDLE_BYTES);cb=utf8(p['candidate_bundle_utf8'],PARENT_MAX_BUNDLE_BYTES)
    spec=utf8(p['spec_utf8'],65536);before=recover_irr_interval_bundle(rb);after=recover_irr_interval_bundle(cb)
    run=_from_verified_pair(before.case_raw,after.case_raw,spec,before.run,after.run)
    if p!=_envelope(rb,cb,spec,run,after.report):raise ValidationError('review bundle differs from exact two-source/result/PDF replay')
    return RecoveredReview(before.case_raw,after.case_raw,spec,run,after.report)


def _contents(spec,rb,cb,run,report):
    values={'comparison-spec.json':spec,'reference-evidence.json':rb,'candidate-evidence.json':cb,
        'revision-review.json':(run.payload_json+'\n').encode(),'revision-review.txt':review_text(run),
        'candidate-MiniUW_v1_Resumen.pdf':report.pdf_bytes}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in values.values()):raise ValidationError('review artifact byte budget exceeded')
    values['package.json']=encoded(dict(schema='miniuw.synthetic-IRR-review-package.v1',**versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(values.items())],candidate_adopted=False,
        review_authenticated=False,decision='PENDING',deployment_enabled=False,real_decisions_enabled=False))
    return values


def build_review_artifacts(reference_raw,candidate_raw,spec_raw):
    run=compare_irr_revisions(reference_raw,candidate_raw,spec_raw)
    rb=export_irr_interval_bundle(reference_raw,run.reference_run);cb=export_irr_interval_bundle(candidate_raw,run.candidate_run)
    return _contents(spec_raw,rb,cb,run,_render_verified(run.candidate_run)),run


def read_review_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular review directory required')
    entries=list(root.iterdir())
    if {p.name for p in entries}!=FILES or any(p.is_symlink()or not p.is_file()for p in entries):
        raise ValidationError('exact seven regular review artifacts required')
    if any(p.stat().st_size>MAX_ARTIFACT_BYTES for p in entries):raise ValidationError('review read byte budget exceeded')
    return {p.name:p.read_bytes()for p in entries}


def audit_review_directory(directory):
    contents=read_review_artifacts(directory);p=_json(contents['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','candidate_adopted','review_authenticated','decision','deployment_enabled','real_decisions_enabled'})
    if p['schema']!='miniuw.synthetic-IRR-review-package.v1'or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('compatible review package versions required')
    names=FILES-{'package.json'}
    if(type(p['files'])is not list or len(p['files'])!=6
        or any(type(row)is not dict or set(row)!={'path','bytes','sha256'}for row in p['files'])
        or {row['path']for row in p['files']if type(row['path'])is str}!=names):
        raise ValidationError('safe exact review inventory required')
    for row in p['files']:
        value=contents[row['path']]
        if type(row['bytes'])is not int or len(value)!=row['bytes']or sha(value)!=row['sha256']:
            raise ValidationError('review artifact byte/hash mismatch')
    rb,cb=contents['reference-evidence.json'],contents['candidate-evidence.json'];before=recover_irr_interval_bundle(rb);after=recover_irr_interval_bundle(cb)
    spec=contents['comparison-spec.json'];run=_from_verified_pair(before.case_raw,after.case_raw,spec,before.run,after.run)
    if contents!=_contents(spec,rb,cb,run,after.report):raise ValidationError('review files differ from full two-source comparison replay')
    return dict(component='T102',status='passed_deterministic_review_replay',files_verified=7,candidate_PDF_pages=1,
        run_sha256=run.sha256,state=run.payload['state'],candidate_adopted=False,decision='PENDING')


def write_review_artifacts(reference_raw,candidate_raw,spec_raw,directory):
    contents,run=build_review_artifacts(reference_raw,candidate_raw,spec_raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_review_artifacts(target)!=contents:raise ValidationError('different or incomplete review exists; choose new directory')
        return dict(status='identical_existing_verified',output=str(target),run_sha256=run.sha256,candidate_adopted=False,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-review-',dir=target.parent))
    try:
        for name,value in contents.items():
            with(temporary/name).open('xb')as handle:handle.write(value);handle.flush();os.fsync(handle.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_candidate_review_written',output=str(target),run_sha256=run.sha256,candidate_adopted=False,decision='PENDING')
