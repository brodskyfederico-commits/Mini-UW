"""Cross-check the defined independent design deliverables; not financial/product acceptance."""
from pathlib import Path
from collections import Counter
from io import StringIO
import csv,hashlib,json,re
from urllib.parse import unquote
from pypdf import PdfReader
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
REPORT='references/structure-closeout-validation.json'

def validate(root=ROOT):
    checks=[]
    def check(name,condition):
        if not condition:raise ValueError('structure check failed: '+name)
        checks.append(name)
    def read(path):return json.loads((root/path).read_text())
    reg=read('docs/structural-integration-register.json');pending=read('docs/final-dependency-register.json');closeout=read('docs/independent-structure-closeout.json');ready=read('docs/package-readiness.json')
    modules={m['id']:m for m in reg['modules']};check('all_nine_modules_unique',len(modules)==len(reg['modules'])==9 and set(modules)=={'M'+str(i) for i in range(1,10)})
    contracts={c['id']:c for c in reg['contracts']};check('all_84_contracts_unique',len(contracts)==len(reg['contracts'])==84)
    check('contract_counts_match_independent_readiness',dict(Counter(c['module'] for c in contracts.values()))==ready['module_contracts'])
    coverage=read('docs/coverage-matrix.json')['rows'];rows={r['id']:r for r in coverage}
    check('all_398_coverage_rows_unique_and_financially_open',len(coverage)==len(rows)==398 and not any(r['cobertura_financiera_extremo_a_extremo'] for r in coverage))
    sources=read('docs/source-register.json');hashes={s['sha256'] for s in sources}
    check('all_original_source_bytes_preserved',len(sources)==19 and len(hashes)==16 and all(hashlib.sha256((root/s['backup_path']).read_bytes()).hexdigest()==s['sha256'] for s in sources))
    found=[]
    for m in modules.values():
        lines=(root/m['candidate_document']).read_text().splitlines();actual=[match[1] for line in lines if (match:=re.match(r'^\| ('+m['id']+r'-\d{2}) \|',line))]
        if actual!=m['contract_ids']:raise ValueError('candidate contract table/index mismatch')
        for id in actual:
            c=contracts[id];r=rows[id]
            if c['module']!=m['id'] or c['candidate_document']!=m['candidate_document'] or not lines[c['candidate_line']-1].startswith('| '+id+' |'):raise ValueError('contract locator mismatch')
            cells=[part.strip() for part in lines[c['candidate_line']-1].strip().strip('|').split('|')]
            if c['summary']!=cells[1] or c['candidate_details']!=cells[2:] or c['coverage_state']!=r['estado']:raise ValueError('contract definition/state differs from source candidate table')
            if (c['original_document'],c['original_sha256'],c['original_locator'])!=(r['documento'],r['sha256_documento'],r['ubicacion_exacta']) or c['original_sha256'] not in hashes or c['financially_closed']:raise ValueError('contract/source crosswalk mismatch')
        found+=actual
    check('candidate_tables_locators_sources_and_matrix_agree',set(found)==set(contracts) and len(found)==84)
    with (root/'docs/coverage-matrix.csv').open(encoding='utf-8-sig',newline='') as handle:csvrows=list(csv.DictReader(handle))
    check('csv_json_coverage_export_identical',len(csvrows)==398 and all({k:('' if v is None else str(v)) for k,v in a.items()}==b for a,b in zip(coverage,csvrows)))
    required_fields=['requisito_o_variable','documento','ubicacion_exacta','definicion_documentada','definicion_vigente','modulo_o_calculo_afectado','evidencia_validacion','estado','pendientes']
    check('every_coverage_row_retains_definition_location_evidence_and_pending',all(all(str(row[k]).strip() for k in required_fields) for row in coverage))
    schemas={}
    for p in sorted((root/'schemas').glob('*.schema.json')):
        s=json.loads(p.read_text());Draft202012Validator.check_schema(s)
        if s['$id'] in schemas:raise ValueError('duplicate schema ID')
        schemas[s['$id']]=s
    check('all_33_schema_files_registered',set(reg['schemas'])=={str(p.relative_to(root)) for p in (root/'schemas').glob('*.schema.json')} and len(schemas)==33)
    refs=[]
    def walk(node,document):
        if isinstance(node,dict):
            for key,val in node.items():
                if key=='$ref':
                    base,_,fragment=val.partition('#');target=schemas[base] if base else document
                    if fragment:
                        if not fragment.startswith('/'):raise ValueError('unsupported schema anchor')
                        for part in unquote(fragment)[1:].split('/'):
                            key=part.replace('~1','/').replace('~0','~');target=target[int(key)] if isinstance(target,list) else target[key]
                    refs.append(val)
                else:walk(val,document)
        elif isinstance(node,list):
            for val in node:walk(val,document)
    for s in schemas.values():walk(s,s)
    check('all_local_schema_reference_targets_resolve',bool(refs))
    ports={p['id']:p for p in reg['aggregate_port_routes']};expected=set()
    for m in modules.values():
        actual=list(read(m['schema'])['properties']['outputs']['properties']);expected.update(m['id']+'.'+p for p in actual)
        if actual!=m['aggregate_output_ports']:raise ValueError('module output index mismatch')
    check('all_33_aggregate_outputs_have_routes',len(ports)==len(reg['aggregate_port_routes'])==33 and set(ports)==expected)
    terminals={'external_one_page_report_design','internal_audit_design'}
    check('all_route_consumers_and_contract_links_exist',all(p['consumers'] and set(p['consumers'])<=set(modules)|terminals and set(p['contract_ids'])<=set(contracts) for p in ports.values()))
    check('no_implicit_cast_or_executable_wiring_claim',all(not p['implicit_conversion_allowed'] and not p['machine_executable_wiring'] and p['consumer_rule'] and len(p['transport_requirements'])==4 for p in ports.values()))
    execution=read('docs/module-execution-design.json');loops=reg['control_loops_and_secondary_passes']
    check('financial_cycles_and_secondary_passes_reconciled',execution['control_loops_and_secondary_passes']==loops and {c['id'] for c in loops}=={'LOOP-FINANCE','PASS-BREAKEVEN','LOOP-SCENARIO-PRICE','PASS-CRITERIA'})
    check('baseline_stages_retain_nine_module_interfaces',{s['module'] for s in execution['stages']}==set(modules) and all((root/s['emits']).is_file() for s in execution['stages']) and not execution['production_execution'])
    annual=read('references/refinance-capacity-bridge-validation.json')['synthetic_example']
    check('annual_equivalent_to_dated_cash_gap_explicit',not annual['dated_annual_service_computed'] and 'no alimenta caja M7' in ports['M6.annual_debt_service']['consumer_rule'])
    roots=read('references/periodic-irr-isolation-validation.json')['examples']['two']
    check('multiple_root_evidence_not_collapsed_to_single_export',roots['distinct_positive_discount_roots']==2 and 'nunca exportar primera raíz' in ports['M7.irr']['consumer_rule'])
    dispositions={r['coverage_id']:r for r in pending['coverage_row_dispositions']}
    check('every_coverage_pending_has_exact_final_disposition',len(dispositions)==len(pending['coverage_row_dispositions'])==398 and set(dispositions)==set(rows) and all(d['source_state_unchanged']==rows[id]['estado'] and d['pending_text_unchanged']==rows[id]['pendientes'] and not d['financial_closure_claimed'] for id,d in dispositions.items()))
    feedback=read('docs/professional-feedback-register.json');topics={t['id']:t for t in pending['questions_and_review_topics']}
    check('all_35_review_topics_indexed_without_fabricated_answers',len(topics)==35 and set(topics)=={x['id'] for x in feedback['items']} and all(not t['professional_response_received'] for t in topics.values()) and not feedback['feedback_received'] and all(x['response'] is None and not x['adopted_as_policy'] for x in feedback['items']))
    check('user_pending_and_output_directions_do_not_wait_for_new_lorena_choice',topics['REVIEW-Q01']['status']=='current_user_direction_effective' and topics['REVIEW-Q20']['status']=='current_user_external_output_direction_effective' and not pending['contact_authorized'])
    cases=read('docs/acceptance-case-contracts.json')['cases']
    check('all_36_acceptance_setups_still_not_product_certified',len(cases)==len({c['id'] for c in cases})==36 and all(c['independent_or_product_evidence'] is None and 'not executed' in c['status'] for c in cases))
    check('implementation_and_deferred_recovery_boundaries_explicit',len(pending['future_implementation'])==len({x['id'] for x in pending['future_implementation']})==9 and all(x['status']=='future_phase_not_implemented' for x in pending['future_implementation']) and {x['id'] for x in pending['additional_boundaries']}=={'EXT-DEAL','EXT-POLICY','EXT-RECOVERY','EXT-FULL-UW'})
    inputs=read('docs/input-contract-map.json')['fields'];template=read('templates/project-draft-empty.json');slots=template['project_inputs']+template['financing_inputs']+template['requested_alternatives']
    check('55_original_inputs_match_template_and_matrix_without_values',len(inputs)==len(slots)==55 and {x['id'] for x in inputs}=={x['field_id'] for x in slots} and all(x['id'] in rows and x['source_value'] is None and x['source_attribution'] is None for x in inputs) and all(x['value'] is None for x in slots))
    check('criteria_policy_and_parameter_slots_remain_blank',len(template['investment_criteria'])==10 and all(x['threshold'] is None for x in template['investment_criteria']) and all(v is None for v in template['expert_policy_choices'].values()) and all(v is None for v in template['technical_parameters'].values()) and not template['run_ready'])
    check('all_financial_release_gates_remain_open',not ready['full_model_complete'] and not ready['production_ready'] and not any(m['cerrado'] for m in read('docs/module-closure.json')['modules']) and not closeout['financial_model_complete'] and not closeout['production_authorized'])
    check('unchanged_R02_review_cut_preserved',hashlib.sha256((root/'docs/review/MiniUW_Estructura_para_Revision_Profesional_R02.pdf').read_bytes()).hexdigest()==feedback['review_snapshot_sha256']==closeout['R02_sha256'])
    proof=read('docs/review/integral-spec-I01-validation.json');pdf_path=root/proof['document'];pdf=PdfReader(pdf_path);pdf_text='\n'.join(p.extract_text() or '' for p in pdf.pages)
    check('integral_pdf_hash_pages_and_all_contracts_match',proof['status']=='passed' and proof['sha256']==hashlib.sha256(pdf_path.read_bytes()).hexdigest() and proof['pages']==len(pdf.pages) and all(c in pdf_text for c in contracts) and not proof['text_bounds_violations'])
    master=(root/'docs/Especificacion_Integral_Armado_I01.md').read_text()
    check('master_spec_covers_all_modules_contracts_deliverables',all(c in master for c in contracts) and all(d['id'] in master and d['id'] in pdf_text for d in closeout['deliverables']) and all(t in master and t in pdf_text for t in topics) and all(c['id'] in master and c['id'] in pdf_text for c in cases) and bool(pdf.outline) and 'una sola página' in master)
    for link in re.findall(r'\[[^]]+\]\(([^)]+)\)',master):
        if not link.startswith(('https://','http://')) and not (root/'docs'/link.split('#')[0]).is_file():raise ValueError('missing integral-spec local link')
    check('all_eight_design_deliverables_have_existing_evidence',len(closeout['deliverables'])==8 and {d['id'] for d in closeout['deliverables']}=={'D0'+str(i) for i in range(1,9)} and all(p==REPORT or (root/p).is_file() for d in closeout['deliverables'] for p in d['evidence_paths']))
    registry=read('docs/reference-runner-map.json')['references'];expected_reports={r['path']:r['count'] for r in ready['reference_results']}
    check('all_26_reference_scripts_and_results_registered',len(registry)==26 and {r['script'] for r in registry}=={str(p.relative_to(root)) for p in (root/'references').glob('validate_*.py')} and {r['report'] for r in registry}==set(expected_reports))
    check('25_prior_scoped_results_retained_without_product_relabel',all(read(p)['status']=='passed' and read(p)['total']==count for p,count in expected_reports.items() if p!=REPORT))
    return {'status':'passed','total':len(checks),'checks':checks,'modules':9,'contracts':84,'aggregate_ports':33,'schema_documents':33,'resolved_schema_references':len(refs),'coverage_rows':398,'review_topics':35,'future_acceptance_specs':36,'closeout_deliverables':8,'integral_pdf_pages':len(pdf.pages),'independent_design_deliverables_consistent':True,'full_financial_integration_certified':False,'scope':'Cross-file consistency/content-presence and retained scoped evidence for the eight independent design deliverables only. Not authentication, independent financial validation, actual executable wiring, professional approval, product acceptance or production. Remote publication closure requires its external exact-commit/CI receipt.'}

if __name__=='__main__':
    result=validate();(ROOT/REPORT).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','total','contracts','aggregate_ports','resolved_schema_references','integral_pdf_pages']}))
