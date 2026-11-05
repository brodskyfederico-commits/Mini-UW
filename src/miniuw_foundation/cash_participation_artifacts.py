"""T104 internal cash hypothesis transport; original single-page output unchanged."""
from dataclasses import dataclass
from pathlib import Path
import os,shutil,tempfile
from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha,utf8
from .scheduled_expense_artifacts import MAX_ARTIFACT_BYTES
from .worksheet_case_artifacts import export_worksheet_case_bundle,recover_worksheet_case_bundle,ENGINE_SHA256 as PARENT_ENGINE_SHA256
from .cash_participation import (CashParticipationRun,assemble_cash_participation,_from_verified_parent,
    ENGINE_SHA256 as CASH_ENGINE_SHA256,ROOT_ENGINE_SHA256,ANNUAL_ENGINE_SHA256,DEFINITION)

ENGINE_SHA256=sha(Path(__file__).read_bytes())
FILES={'allocation-terms.json','allocation-results.json','allocation-evidence.json','package.json'}
encoded=lambda p:(canonical(p)+'\n').encode()


def versions():
    return dict(engine_sha256=ENGINE_SHA256,cash_engine_sha256=CASH_ENGINE_SHA256,parent_bundle_engine_sha256=PARENT_ENGINE_SHA256,
        root_engine_sha256=ROOT_ENGINE_SHA256,annual_engine_sha256=ANNUAL_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()))


def _envelope(parent,terms,run):
    return dict(schema='miniuw.synthetic-cash-participation-bundle.v1',**versions(),parent_bundle_utf8=parent.decode(),
        terms_utf8=terms.decode(),result=dict(payload_json=run.payload_json,sha256=run.sha256))


def _bundle(parent,terms,run):
    raw=encoded(_envelope(parent,terms,run))
    if len(raw)>MAX_ARTIFACT_BYTES:raise ValidationError('cash hypothesis bundle byte budget exceeded')
    return raw


def export_cash_participation_bundle(case_raw,workbook_raw,binding_raw,terms_raw,run):
    if type(run)is not CashParticipationRun or assemble_cash_participation(case_raw,workbook_raw,binding_raw,terms_raw)!=run:
        raise ValidationError('cash participation differs from exact four-source replay')
    parent=export_worksheet_case_bundle(case_raw,workbook_raw,binding_raw,run.parent_run)
    return _bundle(parent,terms_raw,run)


@dataclass(frozen=True)
class RecoveredCashParticipation:
    case_raw:bytes
    workbook_raw:bytes
    binding_raw:bytes
    terms_raw:bytes
    run:CashParticipationRun


def recover_cash_participation_bundle(raw):
    p=_json(raw,MAX_ARTIFACT_BYTES)
    _exact(p,{'schema',*versions(),'parent_bundle_utf8','terms_utf8','result'})
    if p['schema']!='miniuw.synthetic-cash-participation-bundle.v1'or any(p[k]!=v for k,v in versions().items()):
        raise ValidationError('exact compatible cash hypothesis source versions required')
    parent_raw=utf8(p['parent_bundle_utf8'],MAX_ARTIFACT_BYTES);terms=utf8(p['terms_utf8'],65536)
    parent=recover_worksheet_case_bundle(parent_raw);run=_from_verified_parent(terms,parent.run)
    if p!=_envelope(parent_raw,terms,run):raise ValidationError('cash participation bundle differs from complete source-first replay')
    return RecoveredCashParticipation(parent.case_raw,parent.workbook_raw,parent.binding_raw,terms,run)


def _contents(terms,run,bundle):
    values={'allocation-terms.json':terms,'allocation-results.json':(run.payload_json+'\n').encode(),'allocation-evidence.json':bundle}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in values.values()):raise ValidationError('cash hypothesis artifact byte budget exceeded')
    values['package.json']=encoded(dict(schema='miniuw.synthetic-cash-participation-package.v1',**versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(values.items())],
        new_external_PDF_created=False,allocation_terms_adopted=False,personal_investor_return_verified=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING'))
    return values


def build_cash_participation_artifacts(case_raw,workbook_raw,binding_raw,terms_raw):
    run=assemble_cash_participation(case_raw,workbook_raw,binding_raw,terms_raw)
    parent=export_worksheet_case_bundle(case_raw,workbook_raw,binding_raw,run.parent_run)
    return _contents(terms_raw,run,_bundle(parent,terms_raw,run)),run


def read_cash_participation_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular internal hypothesis directory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=FILES or any(p.is_symlink()or not p.is_file()or p.stat().st_size>MAX_ARTIFACT_BYTES for p in paths):
        raise ValidationError('exact four bounded regular internal hypothesis artifacts required')
    return {p.name:p.read_bytes()for p in paths}


def audit_cash_participation_directory(directory):
    values=read_cash_participation_artifacts(directory);p=_json(values['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','new_external_PDF_created','allocation_terms_adopted',
        'personal_investor_return_verified','financial_publication_authorized','deployment_enabled','real_decisions_enabled','decision'})
    if p['schema']!='miniuw.synthetic-cash-participation-package.v1'or any(p[k]!=v for k,v in versions().items()):raise ValidationError('compatible internal hypothesis package required')
    if(type(p['files'])is not list or len(p['files'])!=3 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])
        or {r['path']for r in p['files']if type(r['path'])is str}!=FILES-{'package.json'}):raise ValidationError('safe exact internal hypothesis inventory required')
    for row in p['files']:
        value=values[row['path']]
        if type(row['bytes'])is not int or len(value)!=row['bytes']or sha(value)!=row['sha256']:raise ValidationError('internal hypothesis artifact bytes/hash mismatch')
    recovered=recover_cash_participation_bundle(values['allocation-evidence.json'])
    if values!=_contents(recovered.terms_raw,recovered.run,values['allocation-evidence.json']):raise ValidationError('internal hypothesis packet differs from source-first replay')
    return dict(component='T104',status='passed_source_first_hypothetical_cash_replay',files_verified=4,run_sha256=recovered.run.sha256,
        allocation_state=recovered.run.payload['state'],new_external_PDF_created=False,personal_investor_return_verified=False,decision='PENDING')


def write_cash_participation_artifacts(case_raw,workbook_raw,binding_raw,terms_raw,directory):
    values,run=build_cash_participation_artifacts(case_raw,workbook_raw,binding_raw,terms_raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_cash_participation_artifacts(target)!=values:raise ValidationError('different or incomplete hypothesis exists; choose another directory')
        return dict(status='identical_existing_verified',run_sha256=run.sha256,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-cash-share-',dir=target.parent))
    try:
        for name,value in values.items():
            with(temporary/name).open('xb')as f:f.write(value);f.flush();os.fsync(f.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_internal_cash_hypothesis_written',output=str(target),run_sha256=run.sha256,
        personal_investor_return_verified=False,decision='PENDING')
