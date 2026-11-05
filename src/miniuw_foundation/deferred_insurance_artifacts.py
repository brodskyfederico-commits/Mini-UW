"""T106 source-first internal nominal settlement plan; no automatic closing integration."""
from pathlib import Path
import os,shutil,tempfile
from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha
from .deferred_insurance_settlement import reconcile_deferred_insurance_settlement,ENGINE_SHA256 as PLAN_ENGINE_SHA256,DEFINITION

ENGINE_SHA256=sha(Path(__file__).read_bytes())
FILES={'settlement-source.json','settlement-results.json','package.json'}
MAX_FILE_BYTES=4*1024*1024
encoded=lambda p:(canonical(p)+'\n').encode()


def versions():return dict(engine_sha256=ENGINE_SHA256,plan_engine_sha256=PLAN_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()))


def _contents(raw,run):
    values={'settlement-source.json':raw,'settlement-results.json':(run.payload_json+'\n').encode()}
    if any(len(v)>MAX_FILE_BYTES for v in values.values()):raise ValidationError('nominal settlement artifact byte budget exceeded')
    values['package.json']=encoded(dict(schema='miniuw.synthetic-deferred-insurance-package.v1',**versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(values.items())],
        full_case_financial_integration_completed=False,new_external_PDF_created=False,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING'))
    return values


def build_deferred_insurance_artifacts(raw):
    run=reconcile_deferred_insurance_settlement(raw)
    return _contents(raw,run),run


def read_deferred_insurance_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular nominal settlement directory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=FILES or any(p.is_symlink()or not p.is_file()or p.stat().st_size>MAX_FILE_BYTES for p in paths):raise ValidationError('exact three bounded regular settlement files required')
    return {p.name:p.read_bytes()for p in paths}


def recover_deferred_insurance_directory(directory):
    values=read_deferred_insurance_artifacts(directory);p=_json(values['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','full_case_financial_integration_completed','new_external_PDF_created',
        'financial_publication_authorized','deployment_enabled','real_decisions_enabled','decision'})
    if p['schema']!='miniuw.synthetic-deferred-insurance-package.v1'or any(p[k]!=v for k,v in versions().items()):raise ValidationError('exact compatible settlement versions required')
    if(type(p['files'])is not list or len(p['files'])!=2 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])
        or {r['path']for r in p['files']if type(r['path'])is str}!=FILES-{'package.json'}):raise ValidationError('safe exact settlement inventory required')
    for row in p['files']:
        raw=values[row['path']]
        if type(row['bytes'])is not int or len(raw)!=row['bytes']or sha(raw)!=row['sha256']:raise ValidationError('settlement bytes/hash mismatch')
    run=reconcile_deferred_insurance_settlement(values['settlement-source.json'])
    if values!=_contents(values['settlement-source.json'],run):raise ValidationError('settlement package differs from complete source-first replay')
    return run


def audit_deferred_insurance_directory(directory):
    run=recover_deferred_insurance_directory(directory)
    return dict(component='T106',status='passed_source_first_nominal_settlement_recovery',files_verified=3,run_sha256=run.sha256,
        plan_state=run.payload['state'],integration_state=run.payload['integration_state'],decision='PENDING')


def write_deferred_insurance_artifacts(raw,directory):
    values,run=build_deferred_insurance_artifacts(raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_deferred_insurance_artifacts(target)!=values:raise ValidationError('different or incomplete settlement exists; choose another directory')
        return dict(status='identical_existing_verified',run_sha256=run.sha256,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-insurance-settlement-',dir=target.parent))
    try:
        for name,value in values.items():
            with(temporary/name).open('xb')as f:f.write(value);f.flush();os.fsync(f.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_nominal_settlement_plan_written',output=str(target),run_sha256=run.sha256,
        integration_state=run.payload['integration_state'],decision='PENDING')
