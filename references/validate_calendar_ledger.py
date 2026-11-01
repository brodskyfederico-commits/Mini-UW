"""Explicit-calendar and period-aggregate ledger reference; no underwriting or bank conventions."""
from pathlib import Path
from fractions import Fraction as F
from datetime import date
from copy import deepcopy
import json
from jsonschema import Draft202012Validator,RefResolver,FormatChecker,ValidationError
ROOT=Path(__file__).resolve().parents[1]
STORE={}
for p in (ROOT/'schemas').glob('*.schema.json'):
 d=json.loads(p.read_text());Draft202012Validator.check_schema(d);STORE[d['$id']]=d

def no_network(uri):raise ValueError('network resolution forbidden')
def schema_check(name,data):
 s=STORE['urn:miniuw:candidate:'+name+':0.1']
 Draft202012Validator(s,resolver=RefResolver.from_schema(s,store=STORE,handlers={'http':no_network,'https':no_network}),format_checker=FormatChecker()).validate(data)
def unique(items,key):
 result={}
 for item in items:
  if item[key] in result:raise ValueError('duplicate '+key)
  result[item[key]]=item
 return result

def calendar(c):
 schema_check('calendar',c);unique(c['periods'],'period_id');last=None
 for p in c['periods']:
  a=date.fromisoformat(p['start_date']);b=date.fromisoformat(p['end_date'])
  if a>=b:raise ValueError('empty/inverted period')
  if last is not None and (a<last or (c['continuous_coverage'] and a!=last)):raise ValueError('overlap, wrong order or required gap')
  last=b
 return c

def assign(c,when):
 calendar(c);d=date.fromisoformat(when);matches=[]
 for p in c['periods']:
  a=date.fromisoformat(p['start_date']);b=date.fromisoformat(p['end_date'])
  eligible=a<=d<b if c['boundary_convention']=='left_closed_right_open' else a<d<=b
  if eligible:matches.append(p['period_id'])
 if len(matches)!=1:raise ValueError('date outside uniquely assigned periods')
 return matches[0]

def explicit_actual_day_fraction(start,end,denominator):
 if type(denominator) is not int or denominator<=0:raise ValueError('explicit positive denominator required')
 a=date.fromisoformat(start);b=date.fromisoformat(end)
 if b<a:raise ValueError('inverted dates')
 return F((b-a).days,denominator)

def quantity(q,role,period,signature=None):
 if q['state']!='known':raise ValueError('unresolved amount')
 if type(q['value']['numerator']) is not int or type(q['value']['denominator']) is not int or q['value']['denominator']<=0:raise ValueError('exact rational required')
 if q['dimensions']!={'money':1,'area':0,'unit':0,'space':0,'time':0} or q['measurement_role']!=role or q['period_ref']!=period:raise ValueError('money role/dimension/period mismatch')
 key=(q['currency'],q['unit_id'],q['basis'])
 if not q['currency'] or (signature is not None and signature!=key):raise ValueError('currency/unit/basis mismatch')
 return F(q['value']['numerator'],q['value']['denominator']),key

def reconcile(ledger):
 schema_check('event-ledger',ledger);c=calendar(ledger['calendar'])
 if c['context']!=ledger['context']:raise ValueError('calendar context mismatch')
 accounts=unique(ledger['accounts'],'account_id');debts=unique(ledger['debts'],'debt_id')
 cash=unique(ledger['cash_events'],'event_id');debt_events=unique(ledger['debt_events'],'event_id');bindings=unique(ledger['date_bindings'],'date_ref')
 obligations=unique(ledger['obligations'],'obligation_id');obligation_events=unique(ledger['obligation_events'],'event_id')
 pids=[p['period_id'] for p in c['periods']];signature=None;balances={};principal={}
 for id,a in accounts.items():
  if a['account_class']=='external_counterparty':
   if a['opening_balance'] is not None:raise ValueError('external cash not consolidated')
   continue
  if a['opening_balance'] is None:raise ValueError('opening cash missing')
  v,key=quantity(a['opening_balance'],'stock','OPENING:'+pids[0],signature)
  if v<0:raise ValueError('overdraft requires another explicit contract')
  signature=key;balances[id]=v
 if not balances:raise ValueError('no project cash account')
 for id,d in debts.items():
  v,_=quantity(d['opening_principal'],'stock','OPENING:'+pids[0],signature)
  if v<0:raise ValueError('negative initial principal unsupported')
  principal[id]=v
 amounts={};effects={};linked={};gross_A=F(0);gross_D=F(0)
 for id,e in cash.items():
  if e['context']!=ledger['context'] or e['calendar_ref']!=c['calendar_id']:raise ValueError('event context/calendar mismatch')
  if e['from_account'] not in accounts or e['to_account'] not in accounts or e['from_account']==e['to_account']:raise ValueError('cash accounts unknown/equal')
  if e['date_ref'] not in bindings:raise ValueError('date reference missing')
  if assign(c,bindings[e['date_ref']]['iso_date'])!=e['period_ref']:raise ValueError('event date/period mismatch')
  amount,_=quantity(e['amount'],'period_total',e['period_ref'],signature)
  if amount<0:raise ValueError('cash amounts must remain gross')
  amounts[id]=amount
  f=e['from_account'] in balances;t=e['to_account'] in balances
  if not(f or t):raise ValueError('event has no project cash side')
  kind=e['kind']
  if kind in ['equity_contribution','loan_cash_draw','operating_receipt','sale_receipt'] and (f or not t):raise ValueError('receipt direction mismatch')
  if kind in ['equity_distribution','principal_payment','interest_payment','fee_payment','operating_payment','development_payment','sale_cost'] and (not f or t):raise ValueError('payment direction mismatch')
  if kind=='equity_contribution':gross_A+=amount
  if kind=='equity_distribution':gross_D+=amount
  if kind in ['restricted_transfer','reserve_release']:
   if not(f and t) or not e['restriction_rule_ref']:raise ValueError('restriction transfer lacks rule/accounts')
   fc=accounts[e['from_account']]['account_class'];tc=accounts[e['to_account']]['account_class']
   if (kind=='restricted_transfer' and (fc!='free_project_cash' or tc!='restricted_project_cash')) or (kind=='reserve_release' and (fc!='restricted_project_cash' or tc!='free_project_cash')):raise ValueError('restriction direction mismatch')
 for id,e in debt_events.items():
  if e['context']!=ledger['context'] or e['calendar_ref']!=c['calendar_id'] or e['period_ref'] not in pids or e['debt_id'] not in principal:raise ValueError('debt context/period/loan mismatch')
  effect,_=quantity(e['principal_effect'],'period_total',e['period_ref'],signature);effects[id]=effect
  if e['kind'] in ['cash_draw','principal_repayment']:
   ref=e['cash_event_ref']
   if ref not in cash or ref in linked:raise ValueError('cash link absent/reused')
   ce=cash[ref];expected='loan_cash_draw' if e['kind']=='cash_draw' else 'principal_payment';sign=1 if e['kind']=='cash_draw' else -1
   if ce['kind']!=expected or ce['related_debt_ref']!=e['debt_id'] or ce['period_ref']!=e['period_ref'] or effect!=sign*amounts[ref]:raise ValueError('cash/principal link mismatch')
   linked[ref]=id
 for id,e in cash.items():
  if e['kind'] in ['loan_cash_draw','principal_payment'] and id not in linked:raise ValueError('orphan loan cash event')
 due={};due_effects={};due_cash={};due_cap={}
 for id,o in obligations.items():
  if o['debt_id'] not in principal:raise ValueError('obligation loan missing')
  v,_=quantity(o['opening_due'],'stock','OPENING:'+pids[0],signature)
  if v<0:raise ValueError('negative opening due needs explicit receivable structure')
  due[id]=v
 for id,e in obligation_events.items():
  if e['context']!=ledger['context'] or e['calendar_ref']!=c['calendar_id'] or e['period_ref'] not in pids or e['obligation_id'] not in due:raise ValueError('obligation context/period/id mismatch')
  value,_=quantity(e['due_effect'],'period_total',e['period_ref'],signature);due_effects[id]=value;ob=obligations[e['obligation_id']]
  if e['kind']=='cash_settlement':
   link=e['cash_event_ref']
   if link not in cash or link in due_cash:raise ValueError('obligation cash link missing/reused')
   ce=cash[link];expected={'interest':'interest_payment','fee':'fee_payment','other_documented':'other_documented'}[ob['obligation_class']]
   if ce['kind']!=expected or ce['related_debt_ref']!=ob['debt_id'] or ce['period_ref']!=e['period_ref'] or value!=-amounts[link]:raise ValueError('obligation cash mismatch')
   due_cash[link]=id
  elif e['kind']=='capitalization':
   link=e['debt_event_ref']
   if link not in debt_events or link in due_cap:raise ValueError('obligation capitalization link missing/reused')
   de=debt_events[link];expected='capitalized_interest' if ob['obligation_class']=='interest' else 'documented_principal_adjustment'
   if de['kind']!=expected or de['debt_id']!=ob['debt_id'] or de['period_ref']!=e['period_ref'] or value!=-effects[link]:raise ValueError('obligation principal counterpart mismatch')
   due_cap[link]=id
 for id,e in debt_events.items():
  if e['kind']=='capitalized_interest' and id not in due_cap:raise ValueError('capitalization has no payable counterpart')
 for id,e in cash.items():
  if e['kind'] in ['interest_payment','fee_payment'] and id not in due_cash:raise ValueError('orphan interest/fee cash settlement')
 period_results=[]
 for pid in pids:
  before=sum(balances.values());external_in=F(0);external_out=F(0);before_debt=sum(principal.values());effect_total=F(0)
  for id,e in cash.items():
   if e['period_ref']!=pid:continue
   v=amounts[id];f=e['from_account'];t=e['to_account']
   if f in balances:balances[f]-=v
   if t in balances:balances[t]+=v
   if f not in balances:external_in+=v
   if t not in balances:external_out+=v
  for id,e in debt_events.items():
   if e['period_ref']==pid:principal[e['debt_id']]+=effects[id];effect_total+=effects[id]
  for id,e in obligation_events.items():
   if e['period_ref']==pid:due[e['obligation_id']]+=due_effects[id]
  if any(v<0 for v in balances.values()) or any(v<0 for v in principal.values()) or any(v<0 for v in due.values()):raise ValueError('negative end-period balance needs explicit financing/receivable structure')
  if sum(balances.values())!=before+external_in-external_out or sum(principal.values())!=before_debt+effect_total:raise AssertionError('ledger identity failed')
  period_results.append({'period_id':pid,'external_in':str(external_in),'external_out':str(external_out),'cash_total':str(sum(balances.values())),'principal_total':str(sum(principal.values())),'due_total':str(sum(due.values()))})
 claims_cash=unique(ledger['closing_cash_claims'],'account_id');claims_debt=unique(ledger['closing_debt_claims'],'debt_id');claims_due=unique(ledger['closing_due_claims'],'obligation_id');issues=[]
 if set(claims_cash)!=set(balances) or set(claims_debt)!=set(principal) or set(claims_due)!=set(due):raise ValueError('closing claims incomplete/unknown')
 for kind,claims,derived in [('cash',claims_cash,balances),('debt',claims_debt,principal),('due',claims_due,due)]:
  for id,v in derived.items():
   q=claims[id]['amount']
   if q['state']!='known':issues.append({'kind':kind,'id':id,'cause':'closing amount unresolved'});continue
   claimed,_=quantity(q,'stock','CLOSING:'+pids[-1],signature)
   if claimed!=v:issues.append({'kind':kind,'id':id,'claimed':str(claimed),'derived':str(v),'residual':str(claimed-v)})
 return {'state':'blocked' if issues else 'internally_reconciled_reference','periods':period_results,'cash':{k:str(v) for k,v in balances.items()},'debt':{k:str(v) for k,v in principal.items()},'due':{k:str(v) for k,v in due.items()},'recorded_principal_plus_due':str(sum(principal.values())+sum(due.values())),'gross_equity_contributions':str(gross_A),'gross_equity_distributions':str(gross_D),'issues':issues}

CTX={'deal_id':'SYNTHETIC-LEDGER-NO-DEAL','scenario_id':'explicit-reference','run_id':'reference-1','input_revision':'v1','definition_set_revision':'v1'}
def src():return {'source_id':'SYNTHETIC-ONLY','locator':'fixture declaration','claim_kind':'synthetic_reference','verification_status':'synthetic_only'}
def money(v,role,period):
 v=F(v);return {'state':'known','value':{'numerator':v.numerator,'denominator':v.denominator},'dimensions':{'money':1,'area':0,'unit':0,'space':0,'time':0},'unit_id':'SYNTHETIC-MONEY','currency':'SYNTHETIC-CURRENCY','measurement_role':role,'basis':'synthetic_project','period_ref':period,'sources':[src()]}
def env():return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':deepcopy(CTX)}
def cash_event(id,kind,fr,to,value,pid,debt=None,rule=None):return dict(env(),event_id=id,kind=kind,from_account=fr,to_account=to,amount=money(value,'period_total',pid),calendar_ref='CAL-1',period_ref=pid,date_ref='DATE-'+pid,restriction_rule_ref=rule,related_debt_ref=debt,sources=[src()])
def debt_event(id,kind,value,pid,link=None):return dict(env(),event_id=id,debt_id='LOAN-1',kind=kind,principal_effect=money(value,'period_total',pid),cash_event_ref=link,calendar_ref='CAL-1',period_ref=pid,sources=[src()])
def fixture():
 cal=dict(env(),calendar_id='CAL-1',boundary_convention='left_closed_right_open',continuous_coverage=True,periods=[{'period_id':'P1','start_date':'2028-02-01','end_date':'2028-03-01'},{'period_id':'P2','start_date':'2028-03-01','end_date':'2028-04-01'}],sources=[src()])
 cash=[cash_event('A1','equity_contribution','investor','free',10,'P1'),cash_event('DRAW','loan_cash_draw','bank','free',20,'P1','LOAN-1'),cash_event('COST','development_payment','free','vendor',25,'P1'),cash_event('RESERVE','restricted_transfer','free','restricted',3,'P1',rule='SYNTHETIC-RESTRICTION'),cash_event('PAY1','principal_payment','free','bank',2,'P1','LOAN-1'),cash_event('A2','equity_contribution','investor','free',5,'P2'),cash_event('INCOME','operating_receipt','tenant','free',4,'P2'),cash_event('RELEASE','reserve_release','restricted','free',1,'P2',rule='SYNTHETIC-RELEASE'),cash_event('INTEREST','interest_payment','free','bank',1,'P2','LOAN-1'),cash_event('DIST','equity_distribution','free','investor',5,'P2'),cash_event('PAY2','principal_payment','free','bank',4,'P2','LOAN-1')]
 de=[debt_event('D1','cash_draw',20,'P1','DRAW'),debt_event('CAP','capitalized_interest',2,'P1'),debt_event('D2','principal_repayment',-2,'P1','PAY1'),debt_event('D3','principal_repayment',-4,'P2','PAY2')]
 accounts=[{'account_id':id,'account_class':kind,'opening_balance':money(0,'stock','OPENING:P1') if kind!='external_counterparty' else None} for id,kind in [('free','free_project_cash'),('restricted','restricted_project_cash'),('investor','external_counterparty'),('bank','external_counterparty'),('vendor','external_counterparty'),('tenant','external_counterparty')]]
 ob=[{'obligation_id':'INTEREST-DUE','debt_id':'LOAN-1','obligation_class':'interest','opening_due':money(0,'stock','OPENING:P1')},{'obligation_id':'FEE-DUE','debt_id':'LOAN-1','obligation_class':'fee','opening_due':money(0,'stock','OPENING:P1')}]
 def oe(id,oid,kind,v,pid,cashref=None,debtref=None):return dict(env(),event_id=id,obligation_id=oid,kind=kind,due_effect=money(v,'period_total',pid),cash_event_ref=cashref,debt_event_ref=debtref,calendar_ref='CAL-1',period_ref=pid,sources=[src()])
 obe=[oe('I1','INTEREST-DUE','accrual',2,'P1'),oe('I2','INTEREST-DUE','capitalization',-2,'P1',debtref='CAP'),oe('I3','INTEREST-DUE','accrual',1,'P2'),oe('I4','INTEREST-DUE','cash_settlement',-1,'P2',cashref='INTEREST'),oe('F1','FEE-DUE','accrual',1,'P2')]
 return dict(env(),ledger_id='SYNTHETIC-LEDGER-01',calendar=cal,accounts=accounts,debts=[{'debt_id':'LOAN-1','opening_principal':money(0,'stock','OPENING:P1')}],date_bindings=[{'date_ref':'DATE-P1','iso_date':'2028-02-15'},{'date_ref':'DATE-P2','iso_date':'2028-03-15'}],cash_events=cash,debt_events=de,closing_cash_claims=[{'account_id':'free','amount':money(0,'stock','CLOSING:P2')},{'account_id':'restricted','amount':money(2,'stock','CLOSING:P2')}],closing_debt_claims=[{'debt_id':'LOAN-1','amount':money(16,'stock','CLOSING:P2')}],obligations=ob,obligation_events=obe,closing_due_claims=[{'obligation_id':'INTEREST-DUE','amount':money(0,'stock','CLOSING:P2')},{'obligation_id':'FEE-DUE','amount':money(1,'stock','CLOSING:P2')}])

checks=[]
def ok(name,condition):
 assert condition,name;checks.append(name)
def reject(name,x):
 try:reconcile(x)
 except (ValueError,ValidationError):checks.append(name)
 else:raise AssertionError('invalid ledger accepted: '+name)
base=fixture();before=deepcopy(base);result=reconcile(base)
ok('exact_closing_cash_and_principal',result['state']=='internally_reconciled_reference' and result['cash']=={'free':'0','restricted':'2'} and result['debt']=={'LOAN-1':'16'})
ok('gross_equity_not_bank_or_reserve_flows',result['gross_equity_contributions']=='15' and result['gross_equity_distributions']=='5')
ok('internal_reserves_cancel_in_total',result['periods'][0]['cash_total']=='3' and result['periods'][1]['cash_total']=='2')
ok('input_ledger_not_mutated',base==before)
ok('leap_year_actual_days',explicit_actual_day_fraction('2028-02-01','2028-03-01',360)==F(29,360))
ok('nonleap_actual_days',explicit_actual_day_fraction('2027-02-01','2027-03-01',365)==F(28,365))
ok('explicit_zero_duration',explicit_actual_day_fraction('2028-02-01','2028-02-01',360)==0)
ok('boundary_left_configuration',assign(base['calendar'],'2028-03-01')=='P2')
right=deepcopy(base['calendar']);right['boundary_convention']='left_open_right_closed';ok('boundary_right_configuration',assign(right,'2028-03-01')=='P1')
mutations=[
('duplicate_cash_id',lambda x:x['cash_events'].append(deepcopy(x['cash_events'][0]))),
('duplicate_debt_id',lambda x:x['debt_events'].append(deepcopy(x['debt_events'][0]))),
('duplicate_account',lambda x:x['accounts'].append(deepcopy(x['accounts'][0]))),
('duplicate_date_binding',lambda x:x['date_bindings'].append(deepcopy(x['date_bindings'][0]))),
('duplicate_principal_cash_link',lambda x:x['debt_events'].append(dict(deepcopy(x['debt_events'][0]),event_id='NEW-ID'))),
('orphan_draw_cash',lambda x:x['debt_events'].pop(0)),
('debt_link_amount_disagrees',lambda x:x['debt_events'][0]['principal_effect']['value'].update(numerator=19)),
('debt_wrong_sign',lambda x:x['debt_events'][2]['principal_effect']['value'].update(numerator=2)),
('wrong_related_loan',lambda x:x['cash_events'][1].update(related_debt_ref='OTHER-LOAN')),
('cash_context_mixed',lambda x:x['cash_events'][0]['context'].update(scenario_id='OTHER')),
('debt_context_mixed',lambda x:x['debt_events'][0]['context'].update(run_id='OTHER')),
('wrong_currency',lambda x:x['cash_events'][0]['amount'].update(currency='OTHER')),
('wrong_unit',lambda x:x['cash_events'][0]['amount'].update(unit_id='OTHER')),
('wrong_basis',lambda x:x['cash_events'][0]['amount'].update(basis='OTHER')),
('wrong_amount_period',lambda x:x['cash_events'][0]['amount'].update(period_ref='P2')),
('date_period_disagrees',lambda x:x['date_bindings'][0].update(iso_date='2028-03-01')),
('unbound_date_ref',lambda x:x['cash_events'][0].update(date_ref='MISSING')),
('invalid_calendar_date',lambda x:x['date_bindings'][0].update(iso_date='2028-02-30')),
('overlapping_periods',lambda x:x['calendar']['periods'][1].update(start_date='2028-02-29')),
('gap_in_continuous_calendar',lambda x:x['calendar']['periods'][1].update(start_date='2028-03-02')),
('period_id_duplicate',lambda x:x['calendar']['periods'][1].update(period_id='P1')),
('no_boundary_default',lambda x:x['calendar'].pop('boundary_convention')),
('opening_balance_missing',lambda x:x['accounts'][0].update(opening_balance=None)),
('closing_claims_incomplete',lambda x:x['closing_cash_claims'].pop()),
('restriction_without_rule',lambda x:x['cash_events'][3].update(restriction_rule_ref=None)),
('capitalization_fake_cash',lambda x:x['debt_events'][1].update(cash_event_ref='DRAW')),
('negative_gross_cash',lambda x:x['cash_events'][0]['amount']['value'].update(numerator=-10)),
('same_cash_account',lambda x:x['cash_events'][0].update(from_account='free')),
('missing_amount_state',lambda x:x['cash_events'][0].update(amount={'state':'missing','causes':[{'field_id':'A1','cause_kind':'missing','reason':'No supplied amount'}]})),
('end_period_shortfall_not_invented_equity',lambda x:x['cash_events'][0]['amount']['value'].update(numerator=9))]
for name,mutate in mutations:
 x=fixture();mutate(x);reject(name,x)
x=fixture();x['closing_debt_claims'][0]['amount']['value']['numerator']=17;old=deepcopy(x);z=reconcile(x)
ok('closing_discrepancy_retains_both_values',z['state']=='blocked' and z['issues'][0]['claimed']=='17' and z['issues'][0]['derived']=='16' and z['issues'][0]['residual']=='1' and x==old)
x=fixture();x['closing_cash_claims'][0]['amount']={'state':'missing','causes':[{'field_id':'closing','cause_kind':'missing','reason':'Missing statement'}]};z=reconcile(x);ok('missing_closing_never_becomes_zero',z['state']=='blocked' and z['issues'][0]['cause']=='closing amount unresolved')
# Equal amounts with distinct source events remain distinct; split contribution is not deduplicated.
x=fixture();x['cash_events'][0]['amount']['value']['numerator']=5;x['cash_events'].insert(1,dict(deepcopy(x['cash_events'][0]),event_id='A1-SPLIT'))
z=reconcile(x);ok('same_amount_different_events_preserved',z['state']=='internally_reconciled_reference' and z['gross_equity_contributions']=='15')

ok('accrual_payment_capitalization_separate',result['due']=={'INTEREST-DUE':'0','FEE-DUE':'1'} and result['recorded_principal_plus_due']=='17' and result['debt']['LOAN-1']=='16')
extra_mutations=[
('duplicate_obligation_event',lambda x:x['obligation_events'].append(deepcopy(x['obligation_events'][0]))),
('orphan_capitalization',lambda x:x['obligation_events'].pop(1)),
('orphan_interest_payment',lambda x:x['obligation_events'].pop(3)),
('capitalization_counterpart_wrong_amount',lambda x:x['obligation_events'][1]['due_effect']['value'].update(numerator=-1)),
('obligation_cash_link_reused',lambda x:x['obligation_events'].append(dict(deepcopy(x['obligation_events'][3]),event_id='EXTRA-I4'))),
('obligation_cap_link_reused',lambda x:x['obligation_events'].append(dict(deepcopy(x['obligation_events'][1]),event_id='EXTRA-I2'))),
('obligation_context_mixed',lambda x:x['obligation_events'][0]['context'].update(scenario_id='OTHER')),
('opening_due_missing',lambda x:x['obligations'][0].update(opening_due={'state':'missing','causes':[{'field_id':'opening_due','cause_kind':'missing','reason':'No supplied amount'}]})),
('closing_due_claims_missing',lambda x:x['closing_due_claims'].pop()),
('invalid_calendar_zero_length',lambda x:x['calendar']['periods'][0].update(end_date='2028-02-01')),
('event_outside_calendar',lambda x:x['date_bindings'][0].update(iso_date='2028-01-31'))]
for name,mutate in extra_mutations:
 x=fixture();mutate(x);reject(name,x)
x=fixture();x['closing_due_claims'][1]['amount']['value']['numerator']=0;z=reconcile(x)
ok('unpaid_fee_not_hidden_in_principal',z['state']=='blocked' and z['issues'][0]['kind']=='due' and z['issues'][0]['derived']=='1' and z['debt']['LOAN-1']=='16')
x=fixture();x['calendar']['continuous_coverage']=False;x['calendar']['periods'][1]['start_date']='2028-03-02';ok('explicit_gap_allowed_without_event',reconcile(x)['state']=='internally_reconciled_reference')
x['date_bindings'][1]['iso_date']='2028-03-01';reject('event_in_gap_not_moved',x)
for name,start,end,denom in [('missing_day_denominator','2028-02-01','2028-03-01',None),('zero_day_denominator','2028-02-01','2028-03-01',0),('inverted_day_range','2028-03-01','2028-02-01',360)]:
 try:explicit_actual_day_fraction(start,end,denom)
 except ValueError:checks.append(name)
 else:raise AssertionError('Invalid day convention accepted')

fixtures=ROOT/'references/fixtures';fixtures.mkdir(exist_ok=True)
(fixtures/'calendar-ledger-synthetic.json').write_text(json.dumps(base,indent=2)+'\n')
report={'status':'passed','arithmetic':'exact rational','schemas_checked':len(STORE),'checks':checks,'total':len(checks),'synthetic_example':result,'scope':'Explicit-date period-aggregate synthetic cash/principal/declared-interest-fee/gross-equity reference. Not bank conventions, intraday liquidity proof, complete bank/legal obligations, authentic statements, independent audit or production.'}
Path(__file__).with_name('calendar-ledger-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
