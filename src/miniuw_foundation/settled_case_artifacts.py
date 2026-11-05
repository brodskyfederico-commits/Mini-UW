"""T108 bounded source/result/manifest, full local replay and no external PDF."""
from pathlib import Path
import os,shutil,tempfile
from .drafts import ValidationError,canonical
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha
from .settled_case import assemble_settled_case,DEFINITION
from .construction_bundle import versions as construction_versions

ROOT=Path(__file__).resolve().parents[2]
FILES={'settled-case-source.json','settled-case-results.json','package.json'}
MAX_FILE_BYTES=32*1024*1024
MODULES=('settled_case_artifacts','settled_case','settled_expense_boundary','settled_hold_sale','settled_operating_window','settled_lifecycle_returns',
    'operating_debt_phase','operating_noi','operating_cash','holding_cash','closing_cash','debt_closing','debt_service','project_cash',
    'expense_cash_detail','deferred_insurance_settlement','insurance_terminal_closing','investor_returns','periodic_returns',
    'primitive_periodic_returns','irr_checked_output','cash_risk','lifecycle_bundle','expense_checked_lifecycle')
encoded=lambda p:(canonical(p)+'\n').encode()


def versions():return dict(modules={m:sha((ROOT/'src/miniuw_foundation'/str(m+'.py')).read_bytes())for m in MODULES},
    construction=construction_versions(),definition_sha256=sha(DEFINITION.read_bytes()))


def _contents(raw,run):
    values={'settled-case-source.json':raw,'settled-case-results.json':(run.payload_json+'\n').encode()}
    if any(len(v)>MAX_FILE_BYTES for v in values.values()):raise ValidationError('settled case artifact byte budget exceeded')
    values['package.json']=encoded(dict(schema='miniuw.synthetic-settled-lifecycle-package.v1',versions=versions(),run_sha256=run.sha256,
        files=[dict(path=k,bytes=len(v),sha256=sha(v))for k,v in sorted(values.items())],
        financial_publication_authorized=False,new_external_PDF_created=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING'))
    return values


def build_settled_case_artifacts(raw):
    run=assemble_settled_case(raw);return _contents(raw,run),run


def read_settled_case_artifacts(directory):
    root=Path(directory)
    if root.is_symlink()or not root.is_dir():raise ValidationError('regular settled case directory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=FILES or any(p.is_symlink()or not p.is_file()or p.stat().st_size>MAX_FILE_BYTES for p in paths):raise ValidationError('exact three bounded regular settled case files required')
    return {p.name:p.read_bytes()for p in paths}


def recover_settled_case_directory(directory):
    values=read_settled_case_artifacts(directory);p=_json(values['package.json'],65536)
    _exact(p,{'schema','versions','run_sha256','files','financial_publication_authorized','new_external_PDF_created','deployment_enabled','real_decisions_enabled','decision'})
    if p['schema']!='miniuw.synthetic-settled-lifecycle-package.v1'or p['versions']!=versions():raise ValidationError('exact compatible settled case versions required')
    if(type(p['files'])is not list or len(p['files'])!=2 or any(type(r)is not dict or set(r)!={'path','bytes','sha256'}for r in p['files'])
        or {r['path']for r in p['files']if type(r['path'])is str}!=FILES-{'package.json'}):raise ValidationError('safe exact settled case inventory required')
    for row in p['files']:
        raw=values[row['path']]
        if type(row['bytes'])is not int or len(raw)!=row['bytes']or sha(raw)!=row['sha256']:raise ValidationError('settled case bytes/hash mismatch')
    run=assemble_settled_case(values['settled-case-source.json'])
    if values!=_contents(values['settled-case-source.json'],run):raise ValidationError('settled case package differs from complete source-first replay')
    return run


def audit_settled_case_directory(directory):
    run=recover_settled_case_directory(directory)
    return dict(component='T108',status='passed_source_first_settled_lifecycle_recovery',files_verified=3,run_sha256=run.sha256,
        state=run.payload['state'],full_supplied_synthetic_cash_path_connected=run.payload['full_supplied_synthetic_cash_path_connected'],decision='PENDING')


def write_settled_case_artifacts(raw,directory):
    values,run=build_settled_case_artifacts(raw);target=Path(directory).absolute()
    if target.exists()or target.is_symlink():
        if read_settled_case_artifacts(target)!=values:raise ValidationError('different or incomplete settled case exists; choose another directory')
        return dict(status='identical_existing_verified',run_sha256=run.sha256,decision='PENDING')
    target.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.miniuw-settled-case-',dir=target.parent))
    try:
        for name,value in values.items():
            with(temporary/name).open('xb')as f:f.write(value);f.flush();os.fsync(f.fileno())
        os.rename(temporary,target)
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise
    return dict(status='synthetic_settled_lifecycle_written',output=str(target),run_sha256=run.sha256,state=run.payload['state'],decision='PENDING')
