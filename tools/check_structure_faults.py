from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util,json,shutil
R=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('closeout',R/'references/validate_structure_closeout.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
cases=[('omitted_contract','docs/structural-integration-register.json',lambda x:x['contracts'].pop()),('wrong_module_port_index','docs/structural-integration-register.json',lambda x:x['modules'][5]['aggregate_output_ports'].pop()),('missing_pending_disposition','docs/final-dependency-register.json',lambda x:x['coverage_row_dispositions'].pop()),('user_direction_reopened_as_external_choice','docs/final-dependency-register.json',lambda x:next(t for t in x['questions_and_review_topics'] if t['requirement_id']=='Q01').update(status='awaiting_lorena_choice')),('financial_release_flag','docs/package-readiness.json',lambda x:x.update(production_ready=True)),('unresolved_schema_target','schemas/M1.schema.json',lambda x:x['properties']['context'].update({'$ref':'urn:miniuw:missing-schema'})),('criterion_value_inserted','templates/project-draft-empty.json',lambda x:x['investment_criteria'][0].update(threshold=1)),('wrong_contract_locator','docs/structural-integration-register.json',lambda x:x['contracts'][0].update(candidate_line=1))]
rejected=[]
with TemporaryDirectory(prefix='miniuw-closeout-faults-') as td:
    root=Path(td)/'package';shutil.copytree(R,root,ignore=shutil.ignore_patterns('.git','__pycache__'))
    module.validate(root)
    for name,path,mutate in cases:
        p=root/path;before=p.read_bytes();data=json.loads(before);mutate(data);p.write_text(json.dumps(data))
        try:module.validate(root)
        except (ValueError,KeyError):rejected.append(name)
        else:raise AssertionError('fault accepted: '+name)
        finally:p.write_bytes(before)
    module.validate(root)
assert len(rejected)==8
proof={'status':'passed','faults_rejected':rejected,'total':8,'source_package_mutated':False,'scope':'Deliberate disposable-copy structural defects rejected; not financial model fault injection or independent audit.'}
print(json.dumps(proof,indent=2))
