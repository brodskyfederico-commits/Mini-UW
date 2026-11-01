"""Check the candidate package; run synthetic references only in a temporary copy."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

class PackageError(ValueError):pass

def require(condition,message):
    if not condition:raise PackageError(message)

def local_file(root,path):
    p=Path(path)
    require(not p.is_absolute() and '..' not in p.parts and bool(p.parts),'unsafe inventory path')
    resolved=root/p
    require(not any(x.is_symlink() for x in [resolved,*resolved.parents] if x!=root.parent),'symlink not a package file')
    require(resolved.is_file() and resolved.resolve().is_relative_to(root.resolve()),'missing or external inventory file')
    return resolved

def inventory(root):
    return {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts and '__pycache__' not in p.relative_to(root).parts}

def verify_package(root):
    def read(path):return json.loads(local_file(root,path).read_text())
    manifest=read('BACKUP_MANIFEST.json');seen=set()
    for row in manifest['files']:
        path=row['path'];require(path not in seen,'duplicate inventory path');seen.add(path)
        data=local_file(root,path).read_bytes()
        require(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'inventory byte/hash mismatch')
    require(inventory(root)==seen|{'BACKUP_MANIFEST.json'},'unlisted or missing package files')
    originals=set()
    for record in read('docs/source-register.json'):
        data=local_file(root,record['backup_path']).read_bytes();h=hashlib.sha256(data).hexdigest();require(h==record['sha256'],'original changed');originals.add(h)
    readiness=read('docs/package-readiness.json');require(not readiness['production_ready'] and not readiness['full_model_complete'],'current-phase release guard changed')
    require(not any(m['cerrado'] for m in read('docs/module-closure.json')['modules']),'current-phase module guard changed')
    template=read('templates/project-draft-empty.json');require(template['run_ready'] is False and template['authorization']=='not_granted','empty template release guard changed')
    slots=template['project_inputs']+template['financing_inputs']+template['requested_alternatives']
    require(len(slots)==55 and all(s['value'] is None and s['state']=='missing' for s in slots),'original input slots populated')
    require(len(template['investment_criteria'])==10 and all(c['threshold'] is None and c['state']=='missing' for c in template['investment_criteria']),'real criterion slots populated')
    require(all(v is None for v in template['expert_policy_choices'].values()) and all(v is None for v in template['technical_parameters'].values()),'expert/technical choices populated')
    feedback=read('docs/professional-feedback-register.json');require(not feedback['feedback_received'],'current-phase feedback state changed')
    require(hashlib.sha256(local_file(root,'docs/review/MiniUW_Estructura_para_Revision_Profesional_R02.pdf').read_bytes()).hexdigest()==feedback['review_snapshot_sha256'],'review snapshot changed')
    coverage=read('docs/coverage-matrix.json')['rows'];require(len(coverage)==readiness['coverage_rows']==398 and len({x['id'] for x in coverage})==398,'coverage IDs/count drift')
    require(not any(x['cobertura_financiera_extremo_a_extremo'] for x in coverage),'financial closure claim unsupported in this phase')
    registry=read('docs/reference-runner-map.json')['references']
    require(len(registry)==len({x['script'] for x in registry})==len(readiness['reference_results']),'reference registry incomplete/duplicated')
    require({x['script'] for x in registry}=={p.relative_to(root).as_posix() for p in (root/'references').glob('validate_*.py')},'unregistered reference script')
    require({x['report'] for x in registry}=={x['path'] for x in readiness['reference_results']},'reference result registry mismatch')
    return {'files_checked':len(seen)+1,'unique_originals_checked':len(originals),'coverage_rows':len(coverage),'references':registry}

def run(root=ROOT):
    verified=verify_package(root);readiness=json.loads((root/'docs/package-readiness.json').read_text());expected={x['path']:x['count'] for x in readiness['reference_results']}
    results=[]
    with TemporaryDirectory(prefix='miniuw-reference-check-') as td:
        copy=Path(td)/'package';shutil.copytree(root,copy,ignore=shutil.ignore_patterns('.git','__pycache__'))
        env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
        # Inherit the caller's installed libraries, including an explicitly supplied absolute PYTHONPATH.
        for item in verified.pop('references'):
            p=subprocess.run([sys.executable,str(copy/item['script'])],cwd=copy,env=env,text=True,capture_output=True,timeout=90)
            require(p.returncode==0,'reference process failed: '+item['script'])
            report=json.loads((copy/item['report']).read_text());require(report['status']=='passed' and report['total']==expected[item['report']],'reference outcome/count drift: '+item['script'])
            results.append({'script':item['script'],'status':'passed','count':report['total']})
        # Writers are limited to declared generated fixtures/reports in the temporary copy.
        for path in inventory(root)-{'BACKUP_MANIFEST.json'}:
            if path.startswith('references/') and (path.endswith('-validation.json') or path.startswith('references/fixtures/') or path=='references/dependency-graph-reference.json'):continue
            require((root/path).read_bytes()==(copy/path).read_bytes(),'reference changed non-generated package file')
    require(verify_package(root)['files_checked']==verified['files_checked'],'source package changed during check')
    return dict(verified,status='passed',reference_suites=len(results),results=results,production_ready=False,scope='Package integrity and scoped synthetic references only; no independent financial audit, deal decision or production release.')

if __name__=='__main__':
    try:print(json.dumps(run(),indent=2))
    except (PackageError,subprocess.TimeoutExpired) as e:
        print(json.dumps({'status':'failed','reason':str(e),'production_ready':False}));sys.exit(1)
