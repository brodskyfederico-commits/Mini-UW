"""Offline explicit-slot and content-digest reference; no engine, authentication or database."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
from jsonschema import ValidationError
import validate_calendar_ledger as vocabulary
ROOT=Path(__file__).resolve().parents[1]

def canonical(value):
    def check(v):
        if v is None or type(v) in (str,int,bool):return
        if type(v) is list:
            for item in v:check(item)
            return
        if type(v) is dict and all(type(k) is str for k in v):
            for item in v.values():check(item)
            return
        raise ValueError('Only explicit JSON strings, integers, booleans, null, lists and objects; no float/nonfinite substitution')
    check(value)
    # This is the declared Python reference serialization, not a universal canonical-JSON standard.
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

def digest(value):return hashlib.sha256(canonical(value)).hexdigest()

def seal(artifact):
    d=deepcopy(artifact);d.pop('content_sha256',None);d['content_sha256']=digest(d);return d

def inspect(data):
    vocabulary.schema_check('calculation-lineage',data);canonical(data)
    artifacts=vocabulary.unique(data['artifacts'],'artifact_id')
    contracts=vocabulary.unique(data['calculation_contracts'],'result_artifact_id')
    scenarios=set(data['declared_scenarios']);graph={id:[] for id in artifacts}
    for id,a in artifacts.items():
        if seal(a)['content_sha256']!=a['content_sha256']:raise ValueError('artifact content digest mismatch: '+id)
        scope=a['scope']
        if scope['sharing']=='scenario_private':
            if scope['scenario_id'] not in scenarios:raise ValueError('private scenario undeclared')
        elif scope['scenario_id'] is not None or a['kind'] not in ['source_literal','definition']:
            raise ValueError('shared source/definition needs explicit scope; criteria/normalized values are scenario-specific')
        if a['kind']=='derived_candidate' and id not in contracts:raise ValueError('derived artifact missing calculation contract')
    def dependency(result,id,kind,permission):
        if id not in artifacts:raise ValueError('unknown dependency '+id)
        a=artifacts[id]
        if a['kind']!=kind:raise ValueError('dependency kind mismatch')
        scope=a['scope'];target=artifacts[result]['scope']
        if permission=='same_scenario':
            if scope['sharing']!='scenario_private' or scope['scenario_id']!=target['scenario_id']:raise ValueError('cross-scenario fallback forbidden')
        elif scope['sharing']!='explicit_shared_deal':raise ValueError('shared slot requires explicitly shared artifact')
        graph[result].append(id)
    for result,contract in contracts.items():
        if result not in artifacts or artifacts[result]['kind']!='derived_candidate':raise ValueError('contract result is not derived artifact')
        definition=contract['definition_artifact_id']
        if definition not in artifacts:raise ValueError('missing definition')
        permission='explicit_shared_deal' if artifacts[definition]['scope']['sharing']=='explicit_shared_deal' else 'same_scenario'
        dependency(result,definition,'definition',permission)
        vocabulary.unique(contract['slots'],'slot_id')
        for slot in contract['slots']:
            dependency(result,slot['artifact_id'],slot['expected_kind'],slot['sharing_permission'])
    active=set();done=set()
    def visit(id):
        if id in active:raise ValueError('cycle requires a separately defined unresolved financial block')
        if id in done:return
        active.add(id)
        for dep in graph[id]:visit(dep)
        active.remove(id);done.add(id)
    for id in graph:visit(id)
    return artifacts,contracts,graph

def freeze(data,target):
    artifacts,contracts,graph=inspect(data)
    if target not in contracts:raise ValueError('target requires calculation contract')
    closure=set()
    def visit(id):
        if id in closure:return
        closure.add(id)
        for dep in graph[id]:visit(dep)
    visit(target)
    records=[];blockers=[]
    for id in sorted(closure):
        a=artifacts[id];records.append({'artifact_id':id,'revision':a['revision'],'content_sha256':a['content_sha256'],'contract_sha256':digest(contracts[id]) if id in contracts else None})
        if a['availability']!='known':blockers.append({'artifact_id':id,'availability':a['availability'],'original_payload':deepcopy(a['payload'])})
    receipt={'context':deepcopy(data['context']),'target':target,'closure':records,'blockers':blockers,'state':'blocked' if blockers else 'content_bound_reference','authorization':'not_granted','decision':'PENDING'}
    receipt['receipt_sha256']=digest(receipt)
    return receipt

def compare(receipt,current):
    body=deepcopy(receipt);claimed=body.pop('receipt_sha256',None)
    if digest(body)!=claimed:raise ValueError('receipt altered')
    fresh=freeze(current,receipt['target'])
    if fresh['receipt_sha256']!=claimed:return {'state':'stale_reference','decision':'PENDING','publication_authorized':False,'fresh_blockers':fresh['blockers']}
    return {'state':'blocked' if fresh['blockers'] else 'current_reference','decision':'PENDING','publication_authorized':False,'fresh_blockers':fresh['blockers']}

def artifact(id,kind,payload,scenario='base',availability='known'):
    return seal({'artifact_id':id,'revision':'v1','kind':kind,'scope':{'sharing':'explicit_shared_deal' if scenario is None else 'scenario_private','scenario_id':scenario},'availability':availability,'payload':payload})

def fixture():
    artifacts=[artifact('source','source_literal',{'literal':'SYNTHETIC ONLY; not financial evidence'},None),artifact('formula','definition',{'expression':'synthetic f(x); definition only, not executed'},None)]
    contracts=[]
    for s in ['base','down']:
        artifacts.extend([artifact(s+'.input','normalized_input',{'value':{'numerator':0,'denominator':1}},s),artifact(s+'.criterion','criterion',{'literal':'SYNTHETIC EXPLICIT CRITERION; never a deal default'},s),artifact(s+'.cash','derived_candidate',{'reference':'SYNTHETIC CASH PLACEHOLDER'},s),artifact(s+'.compare','derived_candidate',{'reference':'SYNTHETIC COMPARISON PLACEHOLDER'},s)])
        contracts.extend([{'result_artifact_id':s+'.cash','definition_artifact_id':'formula','slots':[{'slot_id':'input','artifact_id':s+'.input','expected_kind':'normalized_input','sharing_permission':'same_scenario'},{'slot_id':'source','artifact_id':'source','expected_kind':'source_literal','sharing_permission':'explicit_shared_deal'}]},{'result_artifact_id':s+'.compare','definition_artifact_id':'formula','slots':[{'slot_id':'cash','artifact_id':s+'.cash','expected_kind':'derived_candidate','sharing_permission':'same_scenario'},{'slot_id':'criterion','artifact_id':s+'.criterion','expected_kind':'criterion','sharing_permission':'same_scenario'}]}])
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':{'deal_id':'SYNTHETIC-LINEAGE-NO-DEAL','scenario_id':'explicit-multi-scenario-reference','run_id':'reference-1','input_revision':'capture-1','definition_set_revision':'definitions-1'},'declared_scenarios':['base','down'],'artifacts':artifacts,'calculation_contracts':contracts}

def main():
    checks=[]
    def ok(name,condition):
        assert condition,name;checks.append(name)
    def find(x,id):return next(a for a in x['artifacts'] if a['artifact_id']==id)
    def alter(x,id,fn):
        a=find(x,id);fn(a);x['artifacts'][x['artifacts'].index(a)]=seal(a)
    def reject(name,mutation):
        x=fixture();mutation(x)
        try:freeze(x,'base.compare')
        except (ValueError,ValidationError):checks.append(name)
        else:raise AssertionError(name)
    b=fixture();before=deepcopy(b);receipt=freeze(b,'base.compare')
    ok('same_content_is_current_only_as_reference',compare(receipt,b)['state']=='current_reference')
    ok('transitive_input_and_source_are_bound',{'base.input','source','base.cash','base.criterion','base.compare','formula'}=={a['artifact_id'] for a in receipt['closure']})
    ok('explicit_zero_is_not_missing',not receipt['blockers'])
    ok('original_records_not_mutated',b==before)
    ok('current_is_never_pass_or_publication',compare(receipt,b)['decision']=='PENDING' and not compare(receipt,b)['publication_authorized'])
    x=fixture();alter(x,'base.input',lambda a:a['payload'].update(value={'numerator':1,'denominator':1}))
    ok('changed_bytes_same_revision_stale',find(x,'base.input')['revision']=='v1' and compare(receipt,x)['state']=='stale_reference')
    x=fixture();alter(x,'formula',lambda a:a['payload'].update(expression='DIFFERENT SYNTHETIC DEFINITION'))
    ok('changed_formula_same_revision_stale',compare(receipt,x)['state']=='stale_reference')
    x=fixture();alter(x,'base.criterion',lambda a:a['payload'].update(literal='DIFFERENT SYNTHETIC CRITERION'))
    ok('criterion_invalidates_comparison',compare(receipt,x)['state']=='stale_reference')
    ok('criterion_preserves_declared_independent_cash',compare(freeze(b,'base.cash'),x)['state']=='current_reference')
    x=fixture();alter(x,'down.criterion',lambda a:a['payload'].update(literal='OTHER DOWN CRITERION'))
    ok('unrelated_scenario_does_not_rewrite_base_closure',compare(receipt,x)['state']=='current_reference')
    x=fixture();alter(x,'source',lambda a:a['payload'].update(literal='UPDATED SHARED SOURCE'))
    ok('shared_source_invalidates_both_explicit_dependents',all(compare(freeze(b,s+'.cash'),x)['state']=='stale_reference' for s in ['base','down']))
    x=fixture();x['calculation_contracts'][1]['slots']=x['calculation_contracts'][1]['slots'][:1]
    ok('removed_dependency_changes_contract_digest',compare(receipt,x)['state']=='stale_reference')
    x=fixture();alter(x,'base.input',lambda a:a.update(availability='missing',payload={'cause':'No supplied literal'}));z=freeze(x,'base.compare')
    ok('missing_input_blocks_known_result',z['state']=='blocked' and z['blockers'][0]['original_payload']['cause']=='No supplied literal')
    ok('unchanged_blocked_receipt_remains_blocked',compare(z,x)['state']=='blocked')
    x=fixture();claims=[{'literal':'A','source':'SYNTHETIC-A'},{'literal':'B','source':'SYNTHETIC-B'}];alter(x,'base.input',lambda a:a.update(availability='conflict',payload={'claims':claims}));z=freeze(x,'base.compare')
    ok('conflict_claims_survive_without_winner',z['blockers'][0]['original_payload']['claims']==claims and z['state']=='blocked')
    for state in ['invalid','undefined','not_applicable']:
        x=fixture();alter(x,'base.input',lambda a:a.update(availability=state,payload={'reason':'Synthetic unresolved treatment'}));z=freeze(x,'base.compare')
        ok(state+'_does_not_become_zero_or_silent_exclusion',z['state']=='blocked' and z['blockers'][0]['availability']==state)
    x=fixture();alter(x,'formula',lambda a:a.update(availability='missing',payload={'reason':'Rule not supplied'}));z=freeze(x,'base.compare')
    ok('missing_definition_blocks',z['state']=='blocked' and z['blockers'][0]['artifact_id']=='formula')
    x=fixture();x['artifacts'].reverse()
    ok('registry_order_does_not_change_closure',freeze(x,'base.compare')['receipt_sha256']==receipt['receipt_sha256'])
    ok('json_object_key_order_not_value_change',digest({'a':0,'b':1})==digest({'b':1,'a':0}))
    ok('list_order_preserved',digest({'list':[0,1]})!=digest({'list':[1,0]}))
    for field in ['deal_id','run_id','input_revision','definition_set_revision','scenario_id']:
        x=fixture();x['context'][field]='OTHER'
        ok('capture_context_change_'+field,compare(receipt,x)['state']=='stale_reference')
    mutations=[
        ('artifact_changed_without_resealing',lambda x:find(x,'base.input')['payload'].update(unrecorded=1)),
        ('duplicate_artifact_id',lambda x:x['artifacts'].append(deepcopy(x['artifacts'][0]))),
        ('duplicate_contract_result',lambda x:x['calculation_contracts'].append(deepcopy(x['calculation_contracts'][0]))),
        ('duplicate_slot_id',lambda x:x['calculation_contracts'][0]['slots'].append(deepcopy(x['calculation_contracts'][0]['slots'][0]))),
        ('unknown_dependency',lambda x:x['calculation_contracts'][0]['slots'][0].update(artifact_id='ABSENT')),
        ('wrong_dependency_kind',lambda x:x['calculation_contracts'][0]['slots'][0].update(expected_kind='criterion')),
        ('down_cannot_fallback_to_base_input',lambda x:x['calculation_contracts'][2]['slots'][0].update(artifact_id='base.input')),
        ('shared_source_not_implicit_private_input',lambda x:x['calculation_contracts'][0]['slots'][1].update(sharing_permission='same_scenario')),
        ('private_input_not_claimed_shared',lambda x:x['calculation_contracts'][0]['slots'][0].update(sharing_permission='explicit_shared_deal')),
        ('criterion_not_shared_default',lambda x:alter(x,'base.criterion',lambda a:a.update(scope={'sharing':'explicit_shared_deal','scenario_id':None}))),
        ('private_scenario_must_be_declared',lambda x:alter(x,'base.input',lambda a:a['scope'].update(scenario_id='UNKNOWN'))),
        ('shared_scope_has_no_private_scenario',lambda x:alter(x,'source',lambda a:a['scope'].update(scenario_id='base'))),
        ('definition_cannot_be_input',lambda x:x['calculation_contracts'][0].update(definition_artifact_id='base.input')),
        ('unknown_definition',lambda x:x['calculation_contracts'][0].update(definition_artifact_id='MISSING')),
        ('derived_artifact_needs_contract',lambda x:x['calculation_contracts'].pop()),
        ('leaf_cannot_get_result_contract',lambda x:x['calculation_contracts'][0].update(result_artifact_id='base.input')),
        ('unresolved_cycle_not_solved_by_digest',lambda x:x['calculation_contracts'][0]['slots'].append({'slot_id':'cycle','artifact_id':'base.compare','expected_kind':'derived_candidate','sharing_permission':'same_scenario'})),
        ('floating_payload_not_silently_rounded',lambda x:alter(x,'base.input',lambda a:a['payload'].update(value=0.1))),
        ('nonfinite_payload_rejected',lambda x:alter(x,'base.input',lambda a:a['payload'].update(value=float('nan')))),
        ('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:
        try:reject(name,mutate)
        except ValueError:
            # Canonical-content rejection may occur while the test attempts resealing.
            if name not in ['floating_payload_not_silently_rounded','nonfinite_payload_rejected']:raise
            checks.append(name)
    tampered=deepcopy(receipt);tampered['closure'][0]['revision']='ALTERED'
    try:compare(tampered,b)
    except ValueError:checks.append('altered_receipt_rejected')
    else:raise AssertionError('altered receipt accepted')
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(vocabulary.STORE),'synthetic_receipt':receipt,'scope':'Explicit synthetic dependency slots, local deterministic JSON digests, transitive content freshness and blocker preservation only. Not completeness of actual economic dependencies, recomputation of outputs, external-file validation, authentication, persistent immutability, concurrency/atomic publication or production.'}
    (ROOT/'references/fixtures/calculation-lineage-synthetic.json').write_text(json.dumps(b,indent=2)+'\n')
    (ROOT/'references/calculation-lineage-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
