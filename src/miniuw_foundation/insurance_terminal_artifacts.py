"""T107 strict local five-file replay of nominal plan, closing and binding."""
from pathlib import Path
import os,shutil,tempfile
from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha
from .insurance_terminal_closing import reconcile_insurance_terminal_closing,ENGINE_SHA256 as BINDING_ENGINE_SHA256,DEFINITION
from .deferred_insurance_settlement import ENGINE_SHA256 as PLAN_ENGINE_SHA256,DEFINITION as PLAN_DEFINITION
from .closing_cash import ENGINE_SHA256 as CLOSING_ENGINE_SHA256,definition_sources

ENGINE_SHA256=sha(Path(__file__).read_bytes())
SOURCES=('plan-source.json','closing-source.json','binding-source.json')
FILES={*SOURCES,'terminal-results.json','package.json'}
MAX_FILE_BYTES=4*1024*1024
encoded=lambda p:(canonical(p)+'\n').encode()


def versions():return dict(engine_sha256=ENGINE_SHA256,binding_engine_sha256=BINDING_ENGINE_SHA256,plan_engine_sha256=PLAN_ENGINE_SHA256,
    plan_definition_sha256=sha(PLAN_DEFINITION.read_bytes()),closing_engine_sha256=CLOSING_ENGINE_SHA256,
    closing_definition_sources=definition_sources(),definition_sha256=sha(DEFINITION.read_bytes()))


def _contents(plan_raw,closing_raw,binding_raw,run):
    values=dict(zip(SOURCES,(plan_raw,closing_raw,binding_raw)));values['terminal-results.json']=(run.payload_json+'\n').encode()
    if any(len(v)>MAX_FILE_BYTES for v in values.values()):raise ValidationError('terminal insurance artifact byte budget exceeded')
    values['package.json']=encoded(dict(schema='miniuw.synthetic-insurance-terminal-package.v1',**versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(values.items())],
        full_operating_sale_return_integration_completed=False,new_external_PDF_created=False,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING'))
    return values


def build_insurance_terminal_artifacts(plan_raw,closing_raw,binding_raw):
    run=reconcile_insurance_terminal_closing(plan_raw,closing_raw,binding_raw)
    return _contents(plan_raw,closing_raw,binding_raw,run),run


def read_insurance_terminal_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular insurance terminal directory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=FILES or any(p.is_symlink()or not p.is_file()or p.stat().st_size>MAX_FILE_BYTES for p in paths):raise ValidationError('exact five bounded regular terminal files required')
    return {p.name:p.read_bytes()for p in paths}


def recover_insurance_terminal_directory(directory):
    values=read_insurance_terminal_artifacts(directory);p=_json(values['package.json'],65536)
    _exact(p,{'schema',*versions(),'run_sha256','files','full_operating_sale_return_integration_completed','new_external_PDF_created',
        'financial_publication_authorized','deployment_enabled','real_decisions_enabled','decision'})
    if p['schema']!='miniuw.synthetic-insurance-terminal-package.v1'or any(p[k]!=v for k,v in versions().items()):raise ValidationError('exact compatible insurance terminal versions required')
    if(type(p['files'])is not list or len(p['files'])!=4 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])
        or {r['path']for r in p['files']if type(r['path'])is str}!=FILES-{'package.json'}):raise ValidationError('safe exact insurance terminal inventory required')
    for row in p['files']:
        raw=values[row['path']]
        if type(row['bytes'])is not int or len(raw)!=row['bytes']or sha(raw)!=row['sha256']:raise ValidationError('insurance terminal bytes/hash mismatch')
    args=[values[k]for k in SOURCES];run=reconcile_insurance_terminal_closing(*args)
    if values!=_contents(*args,run):raise ValidationError('insurance terminal package differs from complete source-first replay')
    return run


def audit_insurance_terminal_directory(directory):
    run=recover_insurance_terminal_directory(directory)
    return dict(component='T107',status='passed_three_source_insurance_terminal_recovery',files_verified=5,run_sha256=run.sha256,
        binding_state=run.payload['state'],full_operating_sale_return_integration_completed=False,decision='PENDING')


def write_insurance_terminal_artifacts(plan_raw,closing_raw,binding_raw,directory):
    values,run=build_insurance_terminal_artifacts(plan_raw,closing_raw,binding_raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_insurance_terminal_artifacts(target)!=values:raise ValidationError('different or incomplete terminal package exists; choose another directory')
        return dict(status='identical_existing_verified',run_sha256=run.sha256,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-insurance-terminal-',dir=target.parent))
    try:
        for name,value in values.items():
            with(temporary/name).open('xb')as f:f.write(value);f.flush();os.fsync(f.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_insurance_terminal_written',output=str(target),run_sha256=run.sha256,binding_state=run.payload['state'],decision='PENDING')
