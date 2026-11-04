"""Read-only D04 source/cell/runtime crosswalk check; no financial validation."""
from pathlib import Path
import argparse,csv,hashlib,json,sys,zipfile
import xml.etree.ElementTree as ET
from check_reference_package import local_file,require

ROOT=Path(__file__).resolve().parents[1]
DIR='docs/current-structure/'


def run(root=ROOT,verify_record=True):
    def read(path):return json.loads(local_file(root,path).read_bytes())
    digest=lambda b:hashlib.sha256(b).hexdigest()
    docpath=DIR+'MiniUW_Estructura_Vigente_D04.json';csvpath=DIR+'MiniUW_55_campos_D04.csv';p=read(docpath)
    require(p['snapshot_id']=='D04'and p['technical_components_through']=='T95','D04 snapshot identity changed')
    require(all(p[k]is False for k in ('financial_model_complete','financial_coverage_certified','professional_review_authenticated','real_decisions_enabled','deployment_enabled')),'D04 financial/deployment claim unsupported')
    source_map={s['path']:s['sha256']for s in p['sources']};require(len(source_map)==len(p['sources'])==13,'D04 source inventory changed')
    for path,expected in source_map.items():require(digest(local_file(root,path).read_bytes())==expected,'D04 source hash mismatch: '+path)
    original='sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx'
    with zipfile.ZipFile(local_file(root,original))as z:sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};cells={c.attrib['r']:c for c in sheet.findall('.//m:c',ns)}
    dictionary={r['id']:r for r in read('docs/input-dictionary.json')};mapping=read('docs/input-contract-map.json')['fields'];by_map={r['id']:(i,r)for i,r in enumerate(mapping)}
    observed_path='docs/review/miniuw-v1-policy-renewal-example/results.json';observed=read(observed_path);by_observed={r['field_id']:(i,r)for i,r in enumerate(observed['original_inputs'])}
    rows=p['input_coverage'];require(len(rows)==55 and len({r['requirement_or_variable']for r in rows})==55,'55 unique original fields required')
    require({r['requirement_or_variable']for r in rows}==set(dictionary)==set(by_map)==set(by_observed),'original field ID sets differ')
    bound=0
    for row in rows:
        fid=row['requirement_or_variable'];d=dictionary[fid];mi,m=by_map[fid];oi,o=by_observed[fid];source=row['original_source'];definition=row['definition_current'];evidence=row['validation_evidence']
        require(source['path']==original and source['sha256']==source_map[original]and source['location']==m['source_cells']and source['value_cell']=='Inputs!'+d['cell']and source['source_attribution_cell']=='Inputs!'+d['source_cell'],'source/cell locator mismatch: '+fid)
        require(row['label']==d['label']==definition['label_literal']and definition['unit_literal']==m['literal_unit']and definition['note_literal']==m['literal_note']and definition['historical_requirement']==m['historical_required'],'literal definition mismatch: '+fid)
        require(definition['proposed_value_kind']==m['proposed_value_kind']and definition['period_contract_provisional']==m['period_contract']and definition['base_contract_provisional']==m['base_contract']and definition['financial_semantics_or_ranges_approved']is False,'provisional definition changed: '+fid)
        require(row['affected_modules_proposed']==m['consumers'],'proposed module mapping mismatch: '+fid)
        e=evidence['structural_mapping'];require(e['path']=='docs/input-contract-map.json'and e['sha256']==source_map[e['path']]and e['pointer']=='/fields/'+str(mi),'mapping JSON Pointer mismatch: '+fid)
        e=evidence['runtime_observation'];require(e['path']==observed_path and e['sha256']==source_map[observed_path]and e['pointer']=='/original_inputs/'+str(oi),'runtime JSON Pointer mismatch: '+fid)
        expected=dict(example_state=o['state'],recipe_pointer=o['recipe_pointer'],unit=o['unit'],period_ref=o['period_ref'],mapping_basis_ref=o['mapping_basis_ref'],example_value=o['value'])
        require(row['runtime_mapping']==expected,'runtime observation mismatch: '+fid);is_bound=o['state']=='bound_synthetic_claim';bound+=is_bound
        require(row['state']==('bound_in_scoped_synthetic_example'if is_bound else'PENDING_runtime_semantic_mapping')and row['pending']==sorted(set(o['blockers']+['actual_deal_source_and_semantic_adoption_pending','financial_coverage_not_certified']))and evidence['original_blank_value_verified_from_workbook_XML']is True,'field coverage claim changed: '+fid)
        c=cells.get(d['cell']);require(c is None or(c.find('m:f',ns)is None and(c.find('m:v',ns)is None or not c.find('m:v',ns).text)and(c.find('m:is',ns)is None or not ''.join(c.itertext()).strip())),'original blank value changed: '+fid)
    require(bound==p['synthetic_runtime_bound_fields']==1 and 55-bound==p['synthetic_runtime_pending_fields']==54,'bound/pending counts drifted')
    csvrows=list(csv.DictReader(local_file(root,csvpath).open(encoding='utf-8',newline='')));require(len(csvrows)==55,'55 CSV field rows required')
    for a,b in zip(csvrows,rows):
        expected=dict(field_id=b['requirement_or_variable'],variable=b['label'],source_document=b['original_source']['path'],source_sha256=b['original_source']['sha256'],exact_location=b['original_source']['location'],value_cell=b['original_source']['value_cell'],current_literal_unit=b['definition_current']['unit_literal'],provisional_definition=b['definition_current']['base_contract_provisional'],proposed_consumers='; '.join(b['affected_modules_proposed']),runtime_state=b['runtime_mapping']['example_state'],runtime_recipe_pointer=b['runtime_mapping']['recipe_pointer']or'',validation_evidence=b['validation_evidence']['runtime_observation']['path']+'#'+b['validation_evidence']['runtime_observation']['pointer'],state=b['state'],pending='; '.join(b['pending']))
        require(a==expected,'complete CSV/source crosswalk mismatch')
    metrics=p['investment_metrics'];require(len(metrics)==10 and [m['metric_id']for m in metrics]==[m['metric_id']for m in observed['metrics']],'ten original metric slots required')
    for i,(m,o)in enumerate(zip(metrics,observed['metrics'])):
        require(m['value']==o['value']and m['value_state']==o['value_state']and m['definition_current']==o['definition_ref']and m['reason']==o['reason']and m['comparison_state']==o['comparison_state']and m['financial_definition_adopted']is False,'metric state mismatch')
        require(m['criterion_source_ref']is None and m['criterion_pass']==o['criterion']['pass_condition']and m['criterion_fail']==o['criterion']['fail_condition'],'fresh criterion state changed')
        e=m['validation_evidence'];require(e['path']==observed_path and e['sha256']==source_map[observed_path]and e['pointer']=='/metrics/'+str(i),'metric exact location mismatch')
    contracts=read('docs/structural-integration-register.json');roles=read('docs/miniuw-v1-dot-bot-contracts.json');closure=read('docs/module-closure.json')
    require(len(contracts['contracts'])==p['original_structure_contracts']==84 and not any(m['cerrado']for m in closure['modules']),'historical contracts or closure guards changed')
    require(p['bot_count']==len(roles['bots'])==17 and len(p['dots'])==len(roles['dots'])==7,'Dot/bot inventory mismatch')
    require(p['modules']==[dict(module_id=m['id'],label=m['name'],candidate_definition=m['candidate_document'],schema=m['schema'],contract_ids=m['contract_ids'],financial_gate_closed=False)for m in contracts['modules']],'module contract/source mapping mismatch')
    require(p['dots']==[dict(dot_id=d['dot_id'],name=d['name'],bot_ids=d['bot_ids'],status=d['status'])for d in roles['dots']],'Dot roles/status source mismatch')
    record=dict(snapshot='D04',status='passed_structural_source_and_crosswalk_check',checker_sha256=digest(Path(__file__).read_bytes()),snapshot_sha256=digest(local_file(root,docpath).read_bytes()),crosswalk_csv_sha256=digest(local_file(root,csvpath).read_bytes()),input_rows_checked=55,original_blank_workbook_cells_checked=55,observed_runtime_bound=1,observed_runtime_pending=54,metric_slots_checked=10,dots_checked=7,bot_roles_checked=17,original_contracts_preserved=84,source_hashes_checked=13,all_financial_module_gates_open=True,financial_validation_performed=False,independent_financial_audit=False,professional_review_authenticated=False,real_decisions_enabled=False,deployment_enabled=False)
    if verify_record:require(read(DIR+'D04-structural-validation.json')==record,'stored D04 validation record differs from read-only reproduction')
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:print(json.dumps(run(verify_record=not args.emit_record),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,ET.ParseError,zipfile.BadZipFile)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False),ensure_ascii=False));sys.exit(1)
