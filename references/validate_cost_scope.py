"""Declared synthetic cost-coverage reference. No scope inference or financial policy."""
from pathlib import Path
from copy import deepcopy
from fractions import Fraction as F
import json
from jsonschema import Draft202012Validator,RefResolver,ValidationError
ROOT=Path(__file__).resolve().parents[1];STORE={}
for p in (ROOT/'schemas').glob('*.schema.json'):
 d=json.loads(p.read_text());Draft202012Validator.check_schema(d);STORE[d['$id']]=d

def deny_network(uri):raise ValueError('network resolution forbidden')
def schema_check(data):
 s=STORE['urn:miniuw:candidate:cost-scope-package:0.1'];Draft202012Validator(s,resolver=RefResolver.from_schema(s,store=STORE,handlers={'http':deny_network,'https':deny_network})).validate(data)
def reconcile(data):
 schema_check(data);required=data['required_scope_ids']
 if len(required)!=len(set(required)):raise ValueError('duplicate required scope')
 seen=set();claims={x:[] for x in required};issues=[];residuals=[];signature=None
 def amount(q,location):
  nonlocal signature
  if q['state']!='known':issues.append({'cause':'amount unresolved','location':location,'source_state':q['state']});return None
  v=q['value']
  if type(v['numerator']) is not int or type(v['denominator']) is not int or v['denominator']<=0:raise ValueError('exact rational required')
  if q['dimensions']!={'money':1,'area':0,'unit':0,'space':0,'time':0} or q['measurement_role']!='stock' or not q['currency']:raise ValueError('normalized monetary cost required')
  key=(q['currency'],q['unit_id'],q['basis'],q['period_ref'])
  if signature is not None and key!=signature:raise ValueError('currency/unit/basis/period mismatch')
  signature=key;return F(v['numerator'],v['denominator'])
 for rep in data['representations']:
  id=rep['representation_id']
  if id in seen:raise ValueError('duplicate document representation')
  seen.add(id)
  if rep['context']!=data['context']:raise ValueError('mixed context')
  total=amount(rep['quoted_total'],id+'.quoted_total');local=set();allocation_values=[]
  if rep['coverage_state']!='full_explicit_mapping':issues.append({'cause':'mapping not complete','representation_id':id,'state':rep['coverage_state']})
  for a in rep['allocations']:
   scope=a['scope_id']
   if scope in local:raise ValueError('scope allocated twice inside representation')
   local.add(scope);v=amount(a['signed_cost_effect'],id+'.'+scope)
   if scope not in claims:claims[scope]=[];issues.append({'cause':'unexpected scope needs explicit treatment','scope_id':scope})
   if v is not None and ((a['effect_type']=='expense' and v<0) or (a['effect_type']=='documented_credit' and v>0)):raise ValueError('effect type/sign mismatch')
   claims[scope].append({'representation_id':id,'amount':None if v is None else str(v),'mapping_evidence_ref':a['mapping_evidence_ref']})
   allocation_values.append(v)
  allocated=sum(allocation_values,F(0)) if all(x is not None for x in allocation_values) else None
  residual=total-allocated if total is not None and allocated is not None else None
  residuals.append({'representation_id':id,'quoted':None if total is None else str(total),'allocated':None if allocated is None else str(allocated),'residual':None if residual is None else str(residual)})
  if residual is not None and residual!=0:issues.append({'cause':'unallocated quote residual','representation_id':id,'quoted':str(total),'allocated':str(allocated),'residual':str(residual)})
 values={}
 for scope,items in claims.items():
  if not items:issues.append({'cause':'required scope uncovered','scope_id':scope});values[scope]=None;continue
  amounts={x['amount'] for x in items}
  if None in amounts:values[scope]=None
  elif len(amounts)>1:issues.append({'cause':'conflicting scope claims','scope_id':scope,'claims':deepcopy(items)});values[scope]=None
  else:values[scope]=next(iter(amounts))
 total=None if issues or any(v is None for v in values.values()) else str(sum((F(v) for v in values.values()),F(0)))
 return {'state':'blocked' if total is None else 'internally_reconciled_scope_reference','scope_values':values,'canonical_scope_total':total,'quote_residuals':residuals,'scope_claims':claims,'issues':issues}

CTX={'deal_id':'SYNTHETIC-SCOPE-NO-DEAL','scenario_id':'explicit-reference','run_id':'reference-1','input_revision':'v1','definition_set_revision':'v1'}
def src():return {'source_id':'SYNTHETIC-ONLY','locator':'declared explicit scope mapping','claim_kind':'synthetic_reference','verification_status':'synthetic_only'}
def money(n):
 n=F(n);return {'state':'known','value':{'numerator':n.numerator,'denominator':n.denominator},'dimensions':{'money':1,'area':0,'unit':0,'space':0,'time':0},'unit_id':'SYNTHETIC-MONEY','currency':'SYNTHETIC-CURRENCY','measurement_role':'stock','basis':'synthetic_project','period_ref':'EXPLICIT-BUDGET-CUTOFF','sources':[src()]}
def rep(id,total,allocs):return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':deepcopy(CTX),'representation_id':id,'quoted_total':money(total),'coverage_state':'full_explicit_mapping','allocations':[{'scope_id':scope,'signed_cost_effect':money(n),'effect_type':'expense' if n>=0 else 'documented_credit','mapping_evidence_ref':'SYNTHETIC-EXPLICIT-MAP'} for scope,n in allocs],'sources':[src()]}
def fixture():return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':deepcopy(CTX),'package_id':'SYNTHETIC-SCOPE-01','required_scope_ids':['vertical','parking','site','soft'],'representations':[rep('GC-total',30,[('vertical',20),('parking',5),('site',5)]),rep('Parking-support',5,[('parking',5)]),rep('Soft-quote',7,[('soft',7)])]}
def main():
    checks=[]
    def ok(name,condition):
     assert condition,name;checks.append(name)
    def reject(name,x):
     try:reconcile(x)
     except (ValidationError,ValueError):checks.append(name)
     else:raise AssertionError('invalid package accepted: '+name)
    base=fixture();before=deepcopy(base);z=reconcile(base)
    ok('duplicate_representation_not_added_twice',z['canonical_scope_total']=='37' and sum(F(r['quoted_total']['value']['numerator'],r['quoted_total']['value']['denominator']) for r in base['representations'])==42)
    ok('supporting_claims_preserved',len(z['scope_claims']['parking'])==2)
    ok('same_amount_distinct_scopes_not_collapsed',z['scope_values']['parking']=='5' and z['scope_values']['site']=='5')
    ok('original_claims_not_mutated',base==before)
    x=fixture();x['representations'][1]=rep('Parking-support',6,[('parking',6)]);old=deepcopy(x);z=reconcile(x)
    ok('conflict_retains_all_without_source_choice',z['state']=='blocked' and z['canonical_scope_total'] is None and {c['amount'] for c in z['scope_claims']['parking']}=={'5','6'} and x==old)
    x=fixture();x['required_scope_ids'].append('owner-unpriced');z=reconcile(x);ok('required_exclusion_not_zero',z['state']=='blocked' and z['scope_values']['owner-unpriced'] is None)
    x=fixture();x['representations'][0]['allocations'].pop();z=reconcile(x);ok('quote_residual_not_assigned_by_estimate',z['state']=='blocked' and z['quote_residuals'][0]['residual']=='5' and z['scope_values']['site'] is None)
    x=fixture();x['representations'][0]['coverage_state']='partial_mapping';z=reconcile(x);ok('partial_mapping_blocks_even_if_sum_matches',z['state']=='blocked' and z['quote_residuals'][0]['residual']=='0')
    x=fixture();x['representations'][1]['allocations'][0]['signed_cost_effect']={'state':'missing','causes':[{'field_id':'parking','cause_kind':'missing','reason':'No supplied amount'}]};z=reconcile(x);ok('known_source_not_silent_override_for_missing_claim',z['state']=='blocked' and z['scope_values']['parking'] is None)
    x=fixture();x['required_scope_ids'].append('credit');x['representations'].append(rep('Credit',-2,[('credit',-2)]));z=reconcile(x);ok('documented_credit_retains_sign',z['canonical_scope_total']=='35')
    x=fixture();x['required_scope_ids'].append('explicit-zero');x['representations'].append(rep('Zero',0,[('explicit-zero',0)]));z=reconcile(x);ok('explicit_zero_is_known_not_missing',z['canonical_scope_total']=='37' and z['scope_values']['explicit-zero']=='0')
    x=fixture();x['required_scope_ids'].append('land');x['representations'].append(rep('Land',5,[('land',5)]));z=reconcile(x);ok('equal_price_additional_scope_added',z['canonical_scope_total']=='42')
    x=fixture();x['representations'].append(rep('Unexpected',1,[('extra',1)]));z=reconcile(x);ok('unexpected_scope_needs_treatment',z['state']=='blocked')
    mutations=[('representation_id_duplicate',lambda x:x['representations'].append(deepcopy(x['representations'][0]))),('required_scope_duplicate',lambda x:x['required_scope_ids'].append('vertical')),('duplicate_scope_inside_quote',lambda x:x['representations'][0]['allocations'].append(deepcopy(x['representations'][0]['allocations'][0]))),('no_scope_list_default',lambda x:x.pop('required_scope_ids')),('no_empty_scope_completeness',lambda x:x.update(required_scope_ids=[])),('missing_mapping_evidence',lambda x:x['representations'][0]['allocations'][0].update(mapping_evidence_ref='')),('context_mixed',lambda x:x['representations'][0]['context'].update(run_id='OTHER')),('wrong_currency',lambda x:x['representations'][1]['quoted_total'].update(currency='OTHER')),('wrong_unit',lambda x:x['representations'][1]['quoted_total'].update(unit_id='OTHER')),('wrong_base',lambda x:x['representations'][1]['quoted_total'].update(basis='OTHER')),('wrong_period',lambda x:x['representations'][1]['quoted_total'].update(period_ref='OTHER')),('price_per_area_not_total',lambda x:x['representations'][1]['quoted_total']['dimensions'].update(area=-1)),('wrong_measurement_role',lambda x:x['representations'][1]['quoted_total'].update(measurement_role='unit_rate')),('missing_currency',lambda x:x['representations'][1]['quoted_total'].update(currency=None)),('negative_expense_without_credit_class',lambda x:x['representations'][1]['allocations'][0]['signed_cost_effect']['value'].update(numerator=-5)),('bad_exact_denominator',lambda x:x['representations'][1]['quoted_total']['value'].update(denominator=0))]
    for name,mutate in mutations:
     x=fixture();mutate(x);reject(name,x)
    fixtures=ROOT/'references/fixtures';fixtures.mkdir(exist_ok=True);(fixtures/'cost-scope-synthetic.json').write_text(json.dumps(base,indent=2)+'\n')
    report={'status':'passed','arithmetic':'exact rational','schemas_checked':len(STORE),'checks':checks,'total':len(checks),'synthetic_example':reconcile(base),'scope':'Declared synthetic economic-scope allocation and document-claim consistency only; no inferred inclusions, source authority, actual construction completeness, expert policy, TDC financing or production.'}
    Path(__file__).with_name('cost-scope-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__ == "__main__":
    main()
