"""T105 three internal files reuse unchanged T104 evidence instead of nesting it."""
from pathlib import Path
import os,shutil,tempfile
from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha
from .scheduled_expense_artifacts import MAX_ARTIFACT_BYTES
from .participant_cash_risk import (analyze_participant_cash_risk,ENGINE_SHA256 as RISK_ENGINE_SHA256,
    SOURCE_ENGINE_SHA256,PROJECT_RISK_ENGINE_SHA256,PROJECT_RISK_DEFINITION,DEFINITION)

ENGINE_SHA256=sha(Path(__file__).read_bytes())
FILES={'allocation-evidence.json','participant-cash-risk.json','package.json'}
encoded=lambda p:(canonical(p)+'\n').encode()


def versions():
    return dict(engine_sha256=ENGINE_SHA256,risk_engine_sha256=RISK_ENGINE_SHA256,source_engine_sha256=SOURCE_ENGINE_SHA256,
        project_risk_engine_sha256=PROJECT_RISK_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        project_risk_definition_sha256=sha(PROJECT_RISK_DEFINITION.read_bytes()))


def _contents(source,run):
    values={'allocation-evidence.json':source,'participant-cash-risk.json':(run.payload_json+'\n').encode()}
    if any(len(v)>MAX_ARTIFACT_BYTES for v in values.values()):raise ValidationError('participant risk artifact byte budget exceeded')
    values['package.json']=encoded(dict(schema='miniuw.synthetic-participant-cash-risk-package.v1',**versions(),risk_run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(values.items())],
        original_allocation_evidence_nested_again=False,new_external_PDF_created=False,
        verified_personal_investor_return=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING'))
    return values


def build_participant_cash_risk_artifacts(source_raw):
    run=analyze_participant_cash_risk(source_raw)
    return _contents(source_raw,run),run


def read_participant_cash_risk_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular internal risk directory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=FILES or any(p.is_symlink()or not p.is_file()or p.stat().st_size>MAX_ARTIFACT_BYTES for p in paths):raise ValidationError('exact three bounded regular risk artifacts required')
    return {p.name:p.read_bytes()for p in paths}


def recover_participant_cash_risk_directory(directory):
    values=read_participant_cash_risk_artifacts(directory);p=_json(values['package.json'],65536)
    _exact(p,{'schema',*versions(),'risk_run_sha256','files','original_allocation_evidence_nested_again','new_external_PDF_created',
        'verified_personal_investor_return','financial_publication_authorized','deployment_enabled','real_decisions_enabled','decision'})
    if p['schema']!='miniuw.synthetic-participant-cash-risk-package.v1'or any(p[k]!=v for k,v in versions().items()):raise ValidationError('exact compatible risk package versions required')
    if(type(p['files'])is not list or len(p['files'])!=2 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])
        or {r['path']for r in p['files']if type(r['path'])is str}!=FILES-{'package.json'}):raise ValidationError('safe exact internal risk inventory required')
    for row in p['files']:
        value=values[row['path']]
        if type(row['bytes'])is not int or len(value)!=row['bytes']or sha(value)!=row['sha256']:raise ValidationError('internal risk artifact bytes/hash mismatch')
    run=analyze_participant_cash_risk(values['allocation-evidence.json'])
    if values!=_contents(values['allocation-evidence.json'],run):raise ValidationError('risk package differs from full source-first reconstruction')
    return run


def audit_participant_cash_risk_directory(directory):
    run=recover_participant_cash_risk_directory(directory)
    return dict(component='T105',status='passed_source_first_participant_cash_risk_recovery',files_verified=3,
        risk_run_sha256=run.sha256,state=run.payload['state'],new_external_PDF_created=False,decision='PENDING')


def write_participant_cash_risk_artifacts(source_raw,directory):
    values,run=build_participant_cash_risk_artifacts(source_raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_participant_cash_risk_artifacts(target)!=values:raise ValidationError('different or incomplete risk output exists; choose another directory')
        return dict(status='identical_existing_verified',risk_run_sha256=run.sha256,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-participant-risk-',dir=target.parent))
    try:
        for name,value in values.items():
            with(temporary/name).open('xb')as f:f.write(value);f.flush();os.fsync(f.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_participant_cash_risk_written',output=str(target),risk_run_sha256=run.sha256,decision='PENDING')
