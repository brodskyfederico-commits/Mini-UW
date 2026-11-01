"""Draft schema and quantity-exchange reference, not an underwriting engine."""
from pathlib import Path
from fractions import Fraction
from copy import deepcopy
import json
from jsonschema import Draft202012Validator,RefResolver,ValidationError
ROOT=Path(__file__).resolve().parents[1]
SCHEMAS={}
for p in (ROOT/'schemas').glob('*.schema.json'):
 d=json.loads(p.read_text());Draft202012Validator.check_schema(d);SCHEMAS[d['$id']]=d
INDEX={x['module']:x for x in json.loads((ROOT/'schemas/interface-index.json').read_text())['interfaces']}

def deny_network(uri):raise ValueError('Network reference forbidden: '+uri)
def validator(mod):
 schema=SCHEMAS['urn:miniuw:candidate:'+mod+':0.1']
 return Draft202012Validator(schema,resolver=RefResolver.from_schema(schema,store=SCHEMAS,handlers={'http':deny_network,'https':deny_network}))
def rational(q):
 v=q['value']
 if type(v['numerator']) is not int or type(v['denominator']) is not int or v['denominator']<=0:raise ValueError('exact integer rational required')
 return Fraction(v['numerator'],v['denominator'])
def validate_semantics(record):
 validator(record['module']).validate(record)
 mod=record['module'];outputs=record['outputs']
 if mod=='M9':
  if outputs['decision'] in ['PASS','FAIL'] and not outputs['aggregation_rule_ref']:raise ValueError('rule absent')
  if outputs['decision'] in ['PASS','FAIL'] and any(x['result'] in ['band','conflict','not_evaluable'] or not x['criterion_ref'] for x in outputs['comparisons']):raise ValueError('comparison incomplete')
  if outputs['decision'] in ['PASS','FAIL'] and not outputs['comparisons']:raise ValueError('empty comparison set')
  if outputs['decision'] in ['PASS','FAIL'] and all(x['result']=='not_applicable' for x in outputs['comparisons']):raise ValueError('no applicable comparison')
  return
 for name,spec in INDEX[mod]['port_signatures'].items():
  q=outputs[name]
  if q['state']=='known':
   rational(q)
   if q['dimensions']!=spec['dimensions'] or q['measurement_role']!=spec['measurement_role']:raise ValueError('port dimensions or role')
   if spec['required_basis_if_known'] and q['basis']!=spec['required_basis_if_known']:raise ValueError('physical basis mismatch')
  if record['status']=='candidate_complete' and q['state'] not in ['known','not_applicable']:raise ValueError('incomplete port')
  if record['status']=='not_applicable' and q['state']!='not_applicable':raise ValueError('applicability inconsistent')

def source():return {'source_id':'SYNTHETIC-REF','locator':'declared fixture only','claim_kind':'synthetic_reference','verification_status':'synthetic_only'}
def known(spec,value=Fraction(0)):
 money=spec['dimensions']['money']!=0
 return {'state':'known','value':{'numerator':value.numerator,'denominator':value.denominator},'dimensions':spec['dimensions'].copy(),'unit_id':'SYNTHETIC-DECLARED-UNIT','currency':'SYNTHETIC-CURRENCY' if money else None,'measurement_role':spec['measurement_role'],'basis':spec['required_basis_if_known'] or 'synthetic_project','period_ref':'EXPLICIT-SYNTHETIC-PERIOD','sources':[source()]}
def context():return {'deal_id':'SYNTHETIC-DEAL','scenario_id':'base','run_id':'run-1','input_revision':'revision-1','definition_set_revision':'definitions-1'}
def fixture(mod):
 outputs={name:known(spec) for name,spec in INDEX[mod]['port_signatures'].items()}
 if mod=='M8':outputs['bound_kind']='indeterminate'
 if mod=='M9':outputs={'decision':'PENDING','aggregation_rule_ref':None,'comparisons':[]}
 return {'schema_version':'0.1-candidate','purpose':'design_or_synthetic_reference','module':mod,'context':context(),'status':'candidate_complete','pending_causes':[],'outputs':outputs,'authorization':'not_granted'}
def issue(field,kind,why):return {'field_id':field,'cause_kind':kind,'reason':why}
def blocked(q):
 if q['state']=='known':return []
 if q['state']=='not_applicable':return [issue('operand','not_applicable_operand','Explicit calculation applicability is required')]
 return deepcopy(q['causes'])
def metadata(q):return {k:q[k] for k in ['dimensions','unit_id','currency','measurement_role','basis','period_ref']}
def exchange(a,b,ctx_a,ctx_b,operation):
 causes=blocked(a)+blocked(b)
 if ctx_a!=ctx_b:causes.append(issue('context','context_mismatch','Different deal/scenario/run/revision'))
 if a['state']=='known' and b['state']=='known' and metadata(a)!=metadata(b):causes.append(issue('units','unit_mismatch','Unit/currency/base/period/role differs'))
 if causes:return {'state':'blocked','causes':causes}
 va=rational(a);vb=rational(b)
 if operation=='ratio' and vb==0:return {'state':'undefined','causes':[issue('denominator','undefined','Division by documented zero')]}
 if operation not in ['sum','ratio']:raise ValueError('operator absent')
 value=va+vb if operation=='sum' else va/vb
 result=deepcopy(a);result['value']={'numerator':value.numerator,'denominator':value.denominator};result['sources']=deepcopy(a['sources']+b['sources'])
 if operation=='ratio':
  result['dimensions']={k:0 for k in a['dimensions']};result['currency']=None;result['measurement_role']='ratio';result['unit_id']='dimensionless';result['basis']='ratio_of_same_explicit_basis'
 return result

checks=[]
def ok(name,cond=True):
 assert cond,name;checks.append(name)
def reject(name,record):
 try:validate_semantics(record)
 except (ValidationError,ValueError):checks.append(name)
 else:raise AssertionError('Invalid record accepted: '+name)
for mod in INDEX:
 validate_semantics(fixture(mod));ok('valid_structural_fixture_'+mod)
for mod in INDEX:
 f=fixture(mod);f['authorization']='granted';reject('no_release_flag_'+mod,f)
 f=fixture(mod);f['context'].pop('scenario_id');reject('no_implicit_scenario_'+mod,f)
f=fixture('M2');f['outputs']['noi']['value']['denominator']=0;reject('zero_rational_denominator',f)
f=fixture('M2');f['outputs']['noi']['value']['numerator']=1.0;reject('floating_number_not_exact_rational',f)
f=fixture('M2');f['outputs']['noi']['currency']=None;reject('money_currency_missing',f)
f=fixture('M1');f['outputs']['building_gsf']['basis']='NRSF';reject('GSF_not_NRSF',f)
f=fixture('M2');f['outputs']['noi']['dimensions']['area']=1;reject('wrong_output_dimension',f)
f=fixture('M2');f['outputs']['noi']={'state':'missing','causes':[issue('NOI','missing','No inputs supplied')]};reject('candidate_complete_cannot_hide_missing',f)
f['status']='blocked';f['pending_causes']=[issue('NOI','missing','No inputs supplied')];validate_semantics(f);ok('blocked_record_preserves_reason')
f['pending_causes']=[];reject('blocked_requires_causes',f)
f=fixture('M9');f['status']='blocked';f['pending_causes']=[issue('rule','missing','Absent rule')];f['outputs']['decision']='FAIL';reject('blocked_not_FAIL',f)
f=fixture('M9');f['outputs']['decision']='PASS';reject('no_PASS_without_rule_and_comparisons',f)
f=fixture('M8');f['outputs']['bound_kind']='permitted_purchase_by_default';reject('no_invented_bound_class',f)
base=fixture('M2')['outputs']['noi'];a=deepcopy(base);b=deepcopy(base);a['value']['numerator']=7;b['value']['numerator']=3
result=exchange(a,b,context(),context(),'sum');ok('sum_same_units',rational(result)==10 and len(result['sources'])==2)
ok('zero_preserved',rational(exchange(base,b,context(),context(),'sum'))==3)
missing={'state':'missing','causes':[issue('input_A','missing','Missing source')]}
conflict={'state':'conflict','causes':[issue('input_B','conflict','Two alternative values')]}
result=exchange(missing,conflict,context(),context(),'sum');ok('all_block_causes_preserved',result['state']=='blocked' and len(result['causes'])==2 and 'value' not in result)
for key,value in [('currency','OTHER-CURRENCY'),('unit_id','OTHER-UNIT'),('period_ref','OTHER-PERIOD'),('basis','OTHER-BASE'),('measurement_role','stock')]:
 changed=deepcopy(b);changed[key]=value
 q=exchange(a,changed,context(),context(),'sum');ok('reject_mismatched_'+key,q['state']=='blocked' and 'value' not in q)
for key in context():
 changed=context();changed[key]='DIFFERENT'
 q=exchange(a,b,context(),changed,'sum');ok('reject_mixed_'+key,q['state']=='blocked' and 'value' not in q)
q=exchange(a,base,context(),context(),'ratio');ok('division_by_explicit_zero_undefined',q['state']=='undefined' and 'value' not in q)
q=exchange(a,b,context(),context(),'ratio');ok('ratio_same_basis',rational(q)==Fraction(7,3) and q['currency'] is None)
na={'state':'not_applicable','reason':'Synthetic rule only','rule_ref':'SYNTHETIC-RULE','sources':[source()]}
q=exchange(a,na,context(),context(),'sum');ok('NA_not_numeric_zero',q['state']=='blocked' and q['causes'][0]['cause_kind']=='not_applicable_operand')

# Validate the additional record families without interpreting a contract as a review approval.
def record_validator(name):
 schema=SCHEMAS['urn:miniuw:candidate:'+name+':0.1']
 return Draft202012Validator(schema,resolver=RefResolver.from_schema(schema,store=SCHEMAS,handlers={'http':deny_network,'https':deny_network}))
def validate_record(name,record):
 record_validator(name).validate(record)
 def values(node):
  if isinstance(node,dict):
   if node.get('state')=='known' and 'value' in node:rational(node)
   for v in node.values():values(v)
  elif isinstance(node,list):
   for v in node:values(v)
 values(record)
 if name=='cash-event' and record['from_account']==record['to_account']:raise ValueError('same cash account')
 if name=='scenario':
  ids=[x['field_id'] for x in record['input_bindings']]
  if len(ids)!=len(set(ids)):raise ValueError('duplicate field binding')
 if name=='execution-snapshot':
  ids=[x['source_id'] for x in record['source_revisions']]
  if len(ids)!=len(set(ids)):raise ValueError('duplicate source revision binding')
def expect_bad_record(label,name,record):
 try:validate_record(name,record)
 except (ValueError,ValidationError):checks.append(label)
 else:raise AssertionError('Invalid record accepted: '+label)
def common_record():return {'context':context(),'purpose':'design_or_synthetic_reference','authorization':'not_granted'}
money=deepcopy(a)
cost=dict(common_record(),cost_id='SYNTHETIC-COST',economic_scope_id='SCOPE-1',amount=money,classification='vertical',inclusion_status='unresolved',parent_contract_ref=None,basis_ref=None,contingency_base_ref=None,sources=[source()])
cash=dict(common_record(),event_id='CASH-1',kind='equity_contribution',from_account='synthetic_investor',to_account='synthetic_project',amount=money,calendar_ref='SYNTHETIC-CALENDAR',period_ref='PERIOD-1',date_ref=None,restriction_rule_ref=None,related_debt_ref=None,sources=[source()])
debt=dict(common_record(),event_id='DEBT-1',debt_id='SYNTHETIC-LOAN',kind='capitalized_interest',principal_effect=money,cash_event_ref=None,calendar_ref='SYNTHETIC-CALENDAR',period_ref='PERIOD-1',sources=[source()])
criterion=dict(common_record(),criterion_id='SYNTHETIC-CRITERION',metric_id='SYNTHETIC-METRIC',metric_definition_ref='SYNTHETIC-DEFINITION',condition_role='pass_condition',operator='>=',threshold={'state':'missing','causes':[issue('threshold','missing','No Lorena input supplied')]},applicability='unresolved',applicability_reason=None,applicability_rule_ref=None,aggregation_rule_ref=None,sources=[source()])
scenario=dict(common_record(),scenario_id='base',required_status='unresolved',exclusion_rule_ref=None,inherit_unspecified=False,input_bindings=[],criteria_refs=[],transformations=[],required_rule_refs=[])
snapshot=dict(common_record(),snapshot_id='SNAPSHOT-1',source_revisions=[{'source_id':'SYNTHETIC-SOURCE','revision':'v1'}],module_definition_revisions={'M'+str(i):'candidate-v1' for i in range(1,10)},scenario_refs=[],criteria_refs=[],rule_refs=[],completeness='pending',pending_causes=[issue('criteria','missing','No complete run authorized')])
for name,record in [('cost-line',cost),('cash-event',cash),('debt-event',debt),('criterion',criterion),('scenario',scenario),('execution-snapshot',snapshot)]:
 validate_record(name,record);ok('valid_pending_or_synthetic_record_'+name)
bad=deepcopy(cash);bad['amount']['value']['numerator']=-1;expect_bad_record('gross_cash_cannot_encode_negative_net','cash-event',bad)
bad=deepcopy(cash);bad['to_account']=bad['from_account'];expect_bad_record('cash_same_account_rejected','cash-event',bad)
bad=deepcopy(debt);bad['kind']='cash_draw';expect_bad_record('cash_draw_requires_cash_event_reference','debt-event',bad)
bad=deepcopy(debt);bad['cash_event_ref']='FICTITIOUS-CASH';expect_bad_record('pure_capitalization_not_fake_cash_draw','debt-event',bad)
bad=deepcopy(criterion);bad['applicability']='excluded';expect_bad_record('criterion_exclusion_requires_reason_rule','criterion',bad)
bad=deepcopy(scenario);bad['inherit_unspecified']=True;expect_bad_record('scenario_no_implicit_inheritance','scenario',bad)
bad=deepcopy(scenario);bad['required_status']='excluded';expect_bad_record('scenario_exclusion_requires_rule','scenario',bad)
bad=deepcopy(scenario);bad['input_bindings']=[{'field_id':'X','source_value_ref':'A','source_revision':'1'},{'field_id':'X','source_value_ref':'B','source_revision':'2'}];expect_bad_record('active_field_binding_conflict_rejected','scenario',bad)
bad=deepcopy(snapshot);bad['source_revisions'].append({'source_id':'SYNTHETIC-SOURCE','revision':'v2'});expect_bad_record('mixed_revision_same_source_rejected','execution-snapshot',bad)
bad=deepcopy(snapshot);bad['pending_causes']=[];expect_bad_record('pending_snapshot_requires_reason','execution-snapshot',bad)
conf=fixture('M2');conf['status']='blocked';conf['pending_causes']=[issue('noi','conflict','Two explicit claims')]
claim_q={'state':'conflict','causes':deepcopy(conf['pending_causes']),'claims':[{'literal':'5','unit_literal':'declared synthetic unit','source':source()},{'literal':'6','unit_literal':'declared synthetic unit','source':source()}]}
conf['outputs']['noi']=deepcopy(claim_q);validate_semantics(conf);ok('conflict_keeps_two_literal_claims')
bad=deepcopy(conf);bad['outputs']['noi'].pop('claims');reject('conflict_cannot_discard_alternatives',bad)
before=deepcopy(claim_q);result=exchange(a,claim_q,context(),context(),'sum');ok('blocked_arithmetic_keeps_original_claims',result['state']=='blocked' and claim_q==before)
na_comparison={'metric_id':'SYNTHETIC-METRIC','criterion_ref':None,'result':'not_applicable','applicability_reason':None,'applicability_rule_ref':None}
bad=fixture('M9');bad['outputs']['comparisons']=[na_comparison];reject('NA_comparison_requires_reason_rule',bad)
bad=fixture('M9');bad['outputs']={'decision':'PASS','aggregation_rule_ref':'SYNTHETIC-RULE','comparisons':[dict(na_comparison,criterion_ref='SYNTHETIC-REF',applicability_reason='synthetic exclusion',applicability_rule_ref='synthetic rule')]};reject('no_vacuous_PASS_from_all_NA',bad)

report={'status':'passed','validator':'jsonschema Draft202012Validator (installed version 4.10.3); local references only','schemas_checked':len(SCHEMAS),'checks':checks,'total':len(checks),'scope':'Candidate interface shapes and isolated arithmetic/block propagation. No financial defaults, full dependency/model integration, expert approval, authenticated identity or production release.'}
Path(__file__).with_name('interface-contracts-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
