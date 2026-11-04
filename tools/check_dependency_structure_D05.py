"""D05 read-only data dependency map and observed synthetic change-impact check."""
from pathlib import Path
import argparse,ast,copy,csv,hashlib,io,json,sys
from check_reference_package import local_file,require,PackageError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
DIRECTORY='docs/current-structure/'
SNAPSHOT=DIRECTORY+'MiniUW_Dependencias_D05.json'
CSV=DIRECTORY+'MiniUW_Dependencias_D05.csv'
RECORD=DIRECTORY+'D05-structural-validation.json'
CASES=['templates/miniuw-v1-policy-renewal-case.json','templates/miniuw-v1-policy-renewal-twelve-case.json']
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canonical=lambda p:json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def source_function(root,module,symbol):
    path='src/miniuw_foundation/'+module+'.py';raw=local_file(root,path).read_bytes();tree=ast.parse(raw)
    node=next((n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name==symbol),None)
    require(node is not None,'declared producer function missing')
    return dict(path=path,sha256=sha(raw),symbol=symbol,line=node.lineno)


def unpack(raw):
    p=json.loads(raw);scheduled_raw=p['scheduled_case_utf8'].encode();scheduled=json.loads(scheduled_raw);base_raw=scheduled['base_case_utf8'].encode();base=json.loads(base_raw)
    return p,scheduled,base,scheduled_raw,base_raw


def resolve_pointer(value,pointer):
    require(type(pointer)is str and(pointer==''or pointer.startswith('/')),'explicit JSON Pointer required')
    for key in pointer.split('/')[1:]:
        key=key.replace('~1','/').replace('~0','~')
        try:value=value[int(key)]if isinstance(value,list)else value[key]
        except (KeyError,IndexError,ValueError,TypeError)as error:raise PackageError('dependency source locator not resolved')from error
    return value


def located_value(raw,location):
    def get(chain,pointer,mode):
        nested=raw
        for step in chain:
            selected=resolve_pointer(json.loads(nested),step)
            require(type(selected)is str,'embedded JSON source must be explicit UTF-8 text')
            nested=selected.encode('utf-8')
        if mode=='exact_embedded_UTF8_bytes'and pointer=='':return nested.decode('utf-8')
        return resolve_pointer(json.loads(nested),pointer)
    if location.get('selection_shape'):
        selected=[get(s['embedded_json_pointers'],s['final_pointer'],'canonical_JSON_subtree')for s in location['selections']]
        return dict(zip([s['selected_key']for s in location['selections']],selected))if location['selection_shape']=='object'else selected
    return get(location['embedded_json_pointers'],location['final_pointer'],location['value_mode'])


def topology(nodes):
    ids=[n['node_id']for n in nodes];require(len(ids)==len(set(ids)),'duplicate dependency node')
    by={n['node_id']:n for n in nodes};seen=set();active=set();order=[]
    def visit(nid):
        require(nid in by,'unknown dependency endpoint')
        require(nid not in active,'dependency cycle')
        if nid in seen:return
        active.add(nid)
        for parent in by[nid]['data_dependencies']:visit(parent)
        active.remove(nid);seen.add(nid);order.append(nid)
    for nid in ids:visit(nid)
    return order


def extract_sources(raw):
    outer,parent,base,parent_raw,base_raw=unpack(raw);r=base['recipe'];values={};locators={}
    def add(nid,label,value,chain,pointer,mode='canonical_JSON_subtree'):
        value_bytes=value.encode()if mode=='exact_embedded_UTF8_bytes'else canonical(value).encode()
        values[nid]=dict(label=label,source_sha256=sha(value_bytes),value=value,mode=mode)
        locators[nid]=dict(embedded_json_pointers=chain,final_pointer=pointer,value_mode=mode)
    chain=['/scheduled_case_utf8','/base_case_utf8']
    for key in r:
        if key!='operating_periods':add('input:recipe/'+key,key,r[key],chain,'/recipe/'+key)
    for i,p in enumerate(r['operating_periods']):
        for key in ('noi_source','cash_source','expense_detail','rental_calendar'):
            add('input:period/'+str(i)+'/'+key,p['cash_source']['period_ref']+' / '+key,p[key],chain,'/recipe/operating_periods/'+str(i)+'/'+key)
    add('input:eligibility','Catálogo55 y escenarios',dict(original_inputs=base['original_inputs'],required_scenarios=base['required_scenarios'],scenario_id=base['context']['scenario_id']),chain,'',mode='canonical_JSON_subtree')
    add('input:identity','Identidad y revisión v1',{k:base[k]for k in ('schema','profile','case_id','case_revision','title','context')},chain,'')
    add('input:criteria','Diez criterios expresos',base['criteria'],chain,'/criteria')
    add('input:base_registry','Vigencia base',base['source_registry'],chain,'/source_registry')
    add('input:asof','Instantes UTC declarados',[base['as_of_UTC'],parent['as_of_UTC'],outer['as_of_UTC']],[],'')
    def selections(nid,shape,items):
        locators[nid].update(selection_shape=shape,selections=[dict(selected_key=key,embedded_json_pointers=steps,final_pointer=pointer)for key,steps,pointer in items])
    selections('input:eligibility','object',[(key,chain,'/'+key)for key in ('original_inputs','required_scenarios')]+[('scenario_id',chain,'/context/scenario_id')])
    selections('input:identity','object',[(key,chain,'/'+key)for key in ('schema','profile','case_id','case_revision','title','context')])
    selections('input:asof','array',[(str(i),steps,'/as_of_UTC')for i,steps in enumerate((chain,['/scheduled_case_utf8'],[]))])
    add('input:scheduled_binding','Mapa de cuotas a pagos',parent['binding_utf8'],['/scheduled_case_utf8'],'/binding_utf8','exact_embedded_UTF8_bytes')
    add('input:scheduled_registry','Vigencia de gastos',parent['registry_utf8'],['/scheduled_case_utf8'],'/registry_utf8','exact_embedded_UTF8_bytes')
    add('input:policy_registry','Vigencia de pólizas',outer['registry_utf8'],[],'/registry_utf8','exact_embedded_UTF8_bytes')
    add('input:base_bytes','Bytes exactos del expediente base',base_raw.decode(),['/scheduled_case_utf8'],'/base_case_utf8','exact_embedded_UTF8_bytes')
    add('input:scheduled_bytes','Bytes exactos del expediente de gastos',parent_raw.decode(),[],'/scheduled_case_utf8','exact_embedded_UTF8_bytes')
    add('input:outer_bytes','Bytes exactos de la revisión completa',raw.decode(),[],'','exact_embedded_UTF8_bytes')
    for i,s in enumerate(parent['schedule_sources_utf8']):
        p=json.loads(s);add('input:schedule/'+p['schedule_id'],p['kind']+' / '+p['schedule_id'],s,['/scheduled_case_utf8'],'/schedule_sources_utf8/'+str(i),'exact_embedded_UTF8_bytes')
    for i,s in enumerate(outer['policy_books_utf8']):
        p=json.loads(s);add('input:policy/'+p['schedule_id'],'Pólizas / '+p['schedule_id'],s,[],'/policy_books_utf8/'+str(i),'exact_embedded_UTF8_bytes')
    for nid,value in values.items():require(located_value(raw,locators[nid])==value['value'],'dependency locator does not reproduce the declared source value: '+nid)
    return values,locators


def graph_for(root,raw):
    outer,parent,base,_,_=unpack(raw);values,locators=extract_sources(raw);nodes=[]
    for nid,s in values.items():nodes.append(dict(node_id=nid,label=s['label'],kind='input_source',data_dependencies=[],source_location=locators[nid],source_function=None,observed_stage=None))
    def add(nid,label,deps,module,symbol,stage=None):
        nodes.append(dict(node_id=nid,label=label,kind='calculation_or_control',data_dependencies=deps,source_location=None,source_function=source_function(root,module,symbol),observed_stage=stage))
    recipe=lambda key:'input:recipe/'+key
    eligibility=['input:eligibility']
    add('construction_cash','Caja y deuda de obra',eligibility+[recipe(k)for k in ('construction_loans','preopening_source','construction_binding')],'construction_cash','assemble_construction_cash','construction_cash')
    add('operating_phase','Transición de la misma obligación',['construction_cash',recipe('phase_contract')],'operating_debt_phase','produce_operating_debt_phase','operating_phase')
    cash=[];noi=[];detail=[];rent=[]
    for i,p in enumerate(base['recipe']['operating_periods']):
        pid=p['cash_source']['period_ref'];prefix='input:period/'+str(i)+'/'
        n='NOI:'+pid;c='operating_cash:'+pid;d='expense_detail:'+pid;t='phased_rental:'+pid
        add(n,'NOI declarado y calculado / '+pid,eligibility+[prefix+'noi_source'],'operating_noi','produce_operating_noi',n)
        add(c,'Caja operativa / '+pid,[n,prefix+'cash_source'],'operating_cash','reconcile_operating_cash',c)
        add(d,'Devengo, pagos y saldos / '+pid,[n,c,prefix+'expense_detail'],'expense_cash_detail','reconcile_expense_cash_detail',d)
        add(t,'Renta por tramos / '+pid,eligibility+[prefix+'rental_calendar'],'phased_rental','produce_phased_rental',t)
        noi.append(n);cash.append(c);detail.append(d);rent.append(t)
    add('holding_cash','Continuidad de tenencia',noi+cash+[recipe('holding_manifest')],'holding_cash','reconcile_holding_cash','holding_cash')
    add('sale_cash','Caja de venta',eligibility+[recipe('sale')],'closing_cash','produce_closing_cash','sale_cash')
    add('sale_debt','Conciliación de deuda de venta',['operating_phase','sale_cash',recipe('sale')],'debt_closing','reconcile_debt_closing','sale_debt')
    add('hold_sale','Tenencia a venta',['holding_cash','sale_cash','sale_debt',recipe('hold_sale_binding')],'hold_sale_cash','reconcile_hold_sale_cash','hold_sale')
    add('staged_operating_window','Ventana completa obra–operación–venta',['construction_cash','operating_phase','hold_sale',cash[0],recipe('cash_boundary_binding'),recipe('window_binding')],'staged_operating_window','reconcile_staged_operating_window','staged_operating_window')
    add('lifecycle_return','Aportes y cobros hasta venta',['staged_operating_window',recipe('investor_source'),recipe('investor_binding')],'staged_lifecycle_returns','assemble_staged_lifecycle_returns','lifecycle_return')
    add('expense_checked_return','Retorno con gastos por concepto',['lifecycle_return']+detail+[recipe('expense_manifest')],'expense_checked_lifecycle','assemble_expense_checked_lifecycle','expense_checked_return')
    add('phased_rental_return','Retorno con renta conciliada',['expense_checked_return']+rent+[recipe('rental_manifest')],'phased_rental_lifecycle','assemble_phased_rental_lifecycle','phased_rental_return')
    add('source_currency','Vista base actual',['phased_rental_return','input:base_registry','input:asof','input:identity'],'current_phased_rental','assemble_current_phased_rental','source_currency')
    add('screening','Comparación de métricas y criterios',['source_currency','input:criteria','input:identity'],'screening','simulate_screening')
    schedules=[];policy=[]
    for s in parent['schedule_sources_utf8']:
        v=json.loads(s);nid='schedule:'+v['schedule_id'];add(nid,'Calendario agregado / '+v['schedule_id'],['input:schedule/'+v['schedule_id']],'expense_schedule','produce_expense_schedule');schedules.append(nid)
    add('scheduled_current','Control completo de seguros e impuestos',['source_currency','screening','input:scheduled_binding','input:scheduled_registry','input:asof','input:base_bytes']+schedules,'scheduled_expense_case','assemble_scheduled_expense_case')
    for s in outer['policy_books_utf8']:
        v=json.loads(s);nid='policy:'+v['schedule_id'];add(nid,'Renovaciones y cuotas agrupadas / '+v['schedule_id'],['schedule:'+v['schedule_id'],'input:policy/'+v['schedule_id']],'insurance_renewals','reconcile_insurance_renewals');policy.append(nid)
    add('policy_current','Control actual de pólizas y retorno',['scheduled_current','input:policy_registry','input:scheduled_bytes','input:asof']+policy,'policy_renewal_case','assemble_policy_renewal_case')
    add('report','Página y trazabilidad de salida',['policy_current','screening','input:outer_bytes'],'policy_renewal_artifacts','render_policy_renewal_report')
    topology(nodes);return nodes,values


def observations(run,report):
    p=run.payload;result={r['stage']:r['run_sha256']for r in p['stages']}
    for row in p['historical_schedule_runs']:
        v=json.loads(row['payload_json']);result['schedule:'+v['schedule_id']]=row['sha256']
    for row in p['historical_policy_runs']:
        v=json.loads(row['payload_json']);result['policy:'+v['schedule_id']]=row['sha256']
    result.update(screening=p['screening_run_sha256'],scheduled_current=p['scheduled_case_run_sha256'],policy_current=run.sha256,report=sha(report.pdf_bytes))
    return result


def return_summary(run):
    story=run.payload['current_project_return_story']
    fields=('equity_level','currency','cash_horizon','gross_contributions','gross_distributions','net_cash_profit','equity_multiple','cash_by_category','personal_investor_return','selected_IRR','upstream_story_blockers')
    return dict(source_pointer='/current_project_return_story',values={key:story[key]for key in fields},normalized_values={key:story['normalized_story'][key]for key in ('reference_amount','basis_amount','total_contributions','total_distributions','net_cash_profit')})


def fingerprints(nodes,values):
    by={n['node_id']:n for n in nodes};result={}
    for nid in topology(nodes):
        n=by[nid];result[nid]=sha(canonical(dict(node_id=nid,source_function=n['source_function'],input_hash=values[nid]['source_sha256']if nid in values else None,upstream=[(p,result[p])for p in n['data_dependencies']])).encode())
    return result


def flat_csv(snapshot):
    s=io.StringIO(newline='');fields=['node_id','label','kind','data_dependencies','producer','source_locator','observed_stage'];writer=csv.DictWriter(s,fieldnames=fields);writer.writeheader()
    for n in snapshot['nodes']:
        f=n['source_function'];writer.writerow(dict(node_id=n['node_id'],label=n['label'],kind=n['kind'],data_dependencies='; '.join(n['data_dependencies']),producer=''if f is None else f['path']+':'+str(f['line'])+'::'+f['symbol'],source_locator=''if n['source_location']is None else canonical(n['source_location']),observed_stage=n['observed_stage']or''))
    return s.getvalue().encode()


def build_snapshot(root=ROOT):
    from miniuw_foundation.policy_renewal_case import assemble_policy_renewal_case
    from miniuw_foundation.policy_renewal_artifacts import render_policy_renewal_report
    from miniuw_foundation.v1_revision import differences
    raws=[local_file(root,p).read_bytes()for p in CASES];graph,values_a=graph_for(root,raws[0]);other,values_b=graph_for(root,raws[1]);require(graph==other,'same supported dependency graph required for demo')
    runs=[assemble_policy_renewal_case(raw)for raw in raws];reports=[render_policy_renewal_report(raw,run)for raw,run in zip(raws,runs)]
    require(all(r.payload['current_project_return_story']is not None for r in runs),'both declared synthetic demo projections must be current')
    actual=[observations(r,p)for r,p in zip(runs,reports)];fp_a=fingerprints(graph,values_a);fp_b=fingerprints(graph,values_b)
    changed_inputs=[nid for nid in values_a if values_a[nid]['source_sha256']!=values_b[nid]['source_sha256']];affected=[n['node_id']for n in graph if n['kind']!='input_source'and fp_a[n['node_id']]!=fp_b[n['node_id']]]
    observed_changed=[nid for nid in actual[0]if actual[0][nid]!=actual[1].get(nid)];observed_stable=[nid for nid in actual[0]if actual[0][nid]==actual[1].get(nid)]
    require(set(observed_changed)<=set(affected),'observed changed producer absent from declared data dependency impact')
    require('construction_cash'not in affected and 'operating_phase'not in affected,'insurance demo must preserve construction source dependencies')
    require(all(nid not in affected for nid in actual[0]if nid.startswith('phased_rental:')),'unchanged rental source data must remain independent')
    changes=[]
    for nid in changed_inputs:
        if nid.endswith('_bytes'):continue
        a,b=values_a[nid],values_b[nid];av=json.loads(a['value'])if a['mode']=='exact_embedded_UTF8_bytes'else a['value'];bv=json.loads(b['value'])if b['mode']=='exact_embedded_UTF8_bytes'else b['value']
        changes.append(dict(input_node=nid,reference_source_sha256=a['source_sha256'],candidate_source_sha256=b['source_sha256'],logical_changes=differences(av,bv)))
    sources={n['source_function']['path']:n['source_function']['sha256']for n in graph if n['source_function']is not None}
    for path in ('src/miniuw_foundation/v1_projection.py','src/miniuw_foundation/v1_case.py','tools/check_dependency_structure_D05.py'):
        sources[path]=sha(local_file(root,path).read_bytes())
    return dict(snapshot_id='D05',scope='Conservative data dependency map for the supplied T95 profile; structural review, not an incremental executor or financial acceptance',technical_baseline='T95',registered_technical_unit_tests=1351,nodes=graph,source_versions=[dict(path=p,sha256=h)for p,h in sorted(sources.items())],cases=[dict(path=p,sha256=sha(raw),run_sha256=run.sha256,decision=run.payload['decision'],observed_return_summary=return_summary(run),observed_producers=obs,producer_dependency_fingerprints=fp)for p,raw,run,obs,fp in zip(CASES,raws,runs,actual,[fp_a,fp_b])],demonstration=dict(changed_input_nodes=changed_inputs,logical_input_changes=changes,data_dependency_affected_nodes=affected,observed_changed_producers=observed_changed,observed_stable_producers=observed_stable,all_observed_changes_reached=True,unmapped_original_field_count=54,monetary_values_not_inferred=True),all_55_original_fields_financially_mapped=False,financial_model_complete=False,professional_review_authenticated=False,independent_financial_audit=False,real_decisions_enabled=False,deployment_enabled=False)


def structural_check(p,root=ROOT):
    require(p['snapshot_id']=='D05'and p['technical_baseline']=='T95','supported dependency snapshot required')
    require(all(p[k]is False for k in ('all_55_original_fields_financially_mapped','financial_model_complete','professional_review_authenticated','independent_financial_audit','real_decisions_enabled','deployment_enabled')),'unsupported financial mapping/release claim')
    topology(p['nodes']);sources={s['path']:s['sha256']for s in p['source_versions']};require(len(sources)==len(p['source_versions']),'unique dependency source versions required')
    for path,digest in sources.items():require(sha(local_file(root,path).read_bytes())==digest,'dependency producer/checker source hash differs')
    require([c['path']for c in p['cases']]==CASES,'exact supplied demo case inventory required')
    for case in p['cases']:
        raw=local_file(root,case['path']).read_bytes();require(sha(raw)==case['sha256'],'dependency demo case hash differs');expected,_=graph_for(root,raw);require(p['nodes']==expected,'declared dependency edges/source locations/functions differ from scoped graph')
    return True


def validate(p,expected,root=ROOT):
    structural_check(p,root);require(p==expected,'stored dependency map/observations differ from actual source replay');return True


def faults(p,expected,root=ROOT):
    cases=[]
    def trial(name,mutate):
        candidate=copy.deepcopy(p);mutate(candidate)
        try:validate(candidate,expected,root)
        except (PackageError,KeyError,ValueError,TypeError,StopIteration):cases.append(name)
        else:raise PackageError('D05 deliberate defect accepted: '+name)
    trial('missing_node',lambda x:x['nodes'].pop(0))
    trial('cycle',lambda x:next(n for n in x['nodes']if n['node_id']=='construction_cash')['data_dependencies'].append('report'))
    trial('omitted_source_dependency',lambda x:next(n for n in x['nodes']if n['node_id']=='sale_debt')['data_dependencies'].pop())
    trial('wrong_function_locator',lambda x:next(n for n in x['nodes']if n['source_function']is not None)['source_function'].update(line=1))
    trial('wrong_input_locator',lambda x:next(n for n in x['nodes']if n['source_location']is not None)['source_location'].update(final_pointer='/missing'))
    trial('unsupported_financial_closure',lambda x:x.update(financial_model_complete=True))
    trial('forged_observed_producer',lambda x:x['cases'][1]['observed_producers'].update(construction_cash='0'*64))
    require(len(cases)==7,'all dependency defects must be rejected');return cases


def record(p,rejected):
    return dict(snapshot='D05',status='passed_scoped_dependency_and_replay_check',checker_sha256=sha(Path(__file__).read_bytes()),nodes_checked=len(p['nodes']),input_nodes_checked=sum(n['kind']=='input_source'for n in p['nodes']),producer_sources_checked=len(p['source_versions']),supplied_cases_replayed=2,observed_producer_changes_checked=len(p['demonstration']['observed_changed_producers']),all_observed_changes_reached=True,negative_structural_cases_rejected=rejected,financial_validation_performed=False,independent_financial_audit=False,professional_review_authenticated=False,real_decisions_enabled=False,deployment_enabled=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-snapshot',action='store_true');parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        expected=build_snapshot()
        if args.emit_snapshot:print(json.dumps(expected,ensure_ascii=False,indent=2))
        else:
            p=json.loads(local_file(ROOT,SNAPSHOT).read_bytes());validate(p,expected);require(local_file(ROOT,CSV).read_bytes()==flat_csv(p),'D05 dependency CSV differs');result=record(p,faults(p,expected))
            if not args.emit_record:require(json.loads(local_file(ROOT,RECORD).read_bytes())==result,'stored D05 validation record differs')
            print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,StopIteration)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False),ensure_ascii=False));sys.exit(1)
