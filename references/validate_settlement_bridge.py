"""Explicit gross-cash full-payoff closing reference; not banking/legal policy or real deal."""
from fractions import Fraction as F
from pathlib import Path
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_calendar_ledger as ledger
ROOT=Path(__file__).resolve().parents[1]
ROLES=['proceeds','principal_payoff','interest_payoff','fee_payoff','closing_cost','reserve_release','new_reserve','equity_contribution','equity_distribution','other_source','other_use']

def reconcile(data):
    ledger.schema_check('settlement-bridge',data);l=data['event_ledger']
    if data['context']!=l['context']:raise ValueError('mixed closing context')
    common={'decision':'PENDING','publication_authorized':False,'valuation_is_cash':False}
    if data['representation']!='explicit_gross_cash_movements':return dict(common,state='blocked',issues=[{'cause':'net/withheld statement requires explicit counterpart contract; no gross cash invented'}])
    if data['payoff_profile']!='all_preexisting_debts_closed':return dict(common,state='blocked',issues=[{'cause':'partial payoff needs separate declared treatment'}])
    if data['obligation_inventory_state']!='declared_complete':return dict(common,state='blocked',issues=[{'cause':'obligation inventory unresolved'}])
    z=ledger.reconcile(l)
    if z['state']=='blocked':return dict(common,state='blocked',ledger_reference=z,issues=deepcopy(z['issues']))
    pid=data['closing_period_ref'];pids=[p['period_id'] for p in l['calendar']['periods']]
    if pid!=pids[-1]:raise ValueError('closing must be last explicitly included period in this reduced reference')
    dates=ledger.unique(l['date_bindings'],'date_ref')
    if data['closing_date_ref'] not in dates:raise ValueError('closing date missing')
    when=dates[data['closing_date_ref']]['iso_date']
    if ledger.assign(l['calendar'],when)!=pid:raise ValueError('closing date/period mismatch')
    events={e['event_id']:e for e in l['cash_events'] if e['period_ref']==pid}
    if any(dates[e['date_ref']]['iso_date']!=when for e in events.values()):raise ValueError('mixed dates in closing period require finer event ordering contract')
    classifications=ledger.unique(data['cash_classifications'],'cash_event_id')
    if set(classifications)!=set(events):raise ValueError('every closing-period cash event needs exactly one explicit role')
    accounts=ledger.unique(l['accounts'],'account_id');debts=ledger.unique(l['debts'],'debt_id');old=set(data['debt_ids_to_close']);new=data['new_debt_id']
    if data['kind']=='refinance':
        if new not in debts or new in old:raise ValueError('distinct new loan required')
    elif new is not None:raise ValueError('sale is not a new-loan cash source in this profile')
    if old!=set(debts)-({new} if new else set()):raise ValueError('old debt inventory omitted or unknown')
    signature=None;opening={}
    for id,a in accounts.items():
        if a['account_class']=='external_counterparty':continue
        value,signature=ledger.quantity(a['opening_balance'],'stock','OPENING:'+pids[0],signature);opening[id]=value
    def amount(q,role,period):return ledger.quantity(q,role,period,signature)[0]
    if data['valuation_claim'] is not None:
        q=data['valuation_claim']
        if q['state']=='known':amount(q,'stock','VALUATION:'+when)
    sums={r:F(0) for r in ROLES};issues=[]
    for eid,c in classifications.items():
        e=events[eid];r=c['role'];fr=accounts[e['from_account']]['account_class'];to=accounts[e['to_account']]['account_class']
        external_in=fr=='external_counterparty' and to=='free_project_cash';external_out=fr=='free_project_cash' and to=='external_counterparty'
        kinds={'proceeds':'loan_cash_draw' if data['kind']=='refinance' else 'sale_receipt','principal_payoff':'principal_payment','interest_payoff':'interest_payment','fee_payoff':'fee_payment','closing_cost':'other_documented' if data['kind']=='refinance' else 'sale_cost','reserve_release':'reserve_release','new_reserve':'restricted_transfer','equity_contribution':'equity_contribution','equity_distribution':'equity_distribution','other_source':'other_documented','other_use':'other_documented'}
        if e['kind']!=kinds[r]:raise ValueError('closing role/event kind mismatch')
        if r in ['proceeds','equity_contribution','other_source'] and not external_in:raise ValueError('closing source must enter free project cash')
        if r in ['principal_payoff','interest_payoff','fee_payoff','closing_cost','equity_distribution','other_use'] and not external_out:raise ValueError('closing use must leave free project cash')
        if r=='proceeds' and new is not None and e['related_debt_ref']!=new:raise ValueError('proceeds from wrong loan')
        if r in ['principal_payoff','interest_payoff','fee_payoff'] and e['related_debt_ref'] not in old:raise ValueError('payoff is not for declared old loan')
        sums[r]+=amount(e['amount'],'period_total',pid)
    claims=[]
    for r in ROLES:
        q=data['role_claims'][r]
        if q['state']!='known':issues.append({'cause':'settlement claim unresolved','role':r,'original_claim':deepcopy(q)});claims.append({'role':r,'claimed':None,'ledger':str(sums[r]),'residual':None});continue
        v=amount(q,'period_total',pid)
        if v<0:raise ValueError('gross statement claim must be nonnegative')
        residual=v-sums[r];claims.append({'role':r,'claimed':str(v),'ledger':str(sums[r]),'residual':str(residual)})
        if residual:issues.append({'cause':'statement/ledger discrepancy','role':r,'claimed':str(v),'ledger':str(sums[r]),'residual':str(residual)})
    if new:
        if amount(debts[new]['opening_principal'],'stock','OPENING:'+pids[0])!=0 or any(e['debt_id']==new and e['period_ref']!=pid for e in l['debt_events']):raise ValueError('new loan must open at this closing in this profile')
        if F(z['debt'][new])!=sums['proceeds']:issues.append({'cause':'new principal has noncash adjustments needing separate treatment','cash_proceeds':str(sums['proceeds']),'principal':z['debt'][new]})
    for id in old:
        if F(z['debt'][id])!=0:issues.append({'cause':'old principal remains outstanding','debt_id':id,'amount':z['debt'][id]})
    for e in l['debt_events']:
        if e['period_ref']==pid and e['debt_id'] in old and e['kind']=='documented_principal_adjustment':
            issues.append({'cause':'old principal adjustment needs separate discharge/capitalization treatment','event_id':e['event_id']})
    old_obligations={o['obligation_id'] for o in l['obligations'] if o['debt_id'] in old}
    for e in l['obligation_events']:
        if e['period_ref']==pid and e['obligation_id'] in old_obligations and e['kind']=='documented_adjustment':
            issues.append({'cause':'old obligation adjustment is not proof of payment','event_id':e['event_id']})
    for o in l['obligations']:
        if o['debt_id'] in old and F(z['due'][o['obligation_id']])!=0:issues.append({'cause':'old obligation remains outstanding','obligation_id':o['obligation_id'],'amount':z['due'][o['obligation_id']]})
    # Reconstruct free cash entering the closing period from all earlier recorded periods.
    for e in l['cash_events']:
        if pids.index(e['period_ref'])>=pids.index(pid):continue
        v=amount(e['amount'],'period_total',e['period_ref'])
        if e['from_account'] in opening:opening[e['from_account']]-=v
        if e['to_account'] in opening:opening[e['to_account']]+=v
    free_before=sum((v for id,v in opening.items() if accounts[id]['account_class']=='free_project_cash'),F(0))
    free_after=sum((F(v) for id,v in z['cash'].items() if accounts[id]['account_class']=='free_project_cash'),F(0))
    sources=free_before+sum(sums[r] for r in ['proceeds','reserve_release','equity_contribution','other_source'])
    uses=sum(sums[r] for r in ['principal_payoff','interest_payoff','fee_payoff','closing_cost','new_reserve','equity_distribution','other_use'])
    assert sources-uses==free_after
    return dict(common,state='blocked' if issues else 'internally_reconciled_reference',statement_reconciliation=claims,ledger_reference=z,issues=issues,free_cash_before=str(free_before),sources_including_free_cash=str(sources),cash_uses=str(uses),retained_free_cash=str(free_after),distribution_recorded=str(sums['equity_distribution']),new_restricted_cash=str(sums['new_reserve']),valuation_claim=deepcopy(data['valuation_claim']),obligation_completeness='declared, not independently verified')

def fixture(kind='refinance'):
    ctx=deepcopy(ledger.CTX);env=ledger.env();pid='P1'
    accounts=[{'account_id':id,'account_class':cl,'opening_balance':ledger.money(v,'stock','OPENING:P1') if cl!='external_counterparty' else None} for id,cl,v in [('free','free_project_cash',2),('restricted','restricted_project_cash',4),('old_bank','external_counterparty',0),('new_bank','external_counterparty',0),('buyer','external_counterparty',0),('vendor','external_counterparty',0),('investor','external_counterparty',0)]]
    specs=[('PROCEEDS','loan_cash_draw' if kind=='refinance' else 'sale_receipt','new_bank' if kind=='refinance' else 'buyer','free',100,'NEW' if kind=='refinance' else None,None),('PRINCIPAL','principal_payment','free','old_bank',70,'OLD',None),('INTEREST','interest_payment','free','old_bank',2,'OLD',None),('FEE','fee_payment','free','old_bank',1,'OLD',None),('COST','other_documented' if kind=='refinance' else 'sale_cost','free','vendor',3,None,None),('RELEASE','reserve_release','restricted','free',4,None,'SYNTHETIC-RELEASE'),('RESERVE','restricted_transfer','free','restricted',5,None,'SYNTHETIC-RESTRICTION'),('DIST','equity_distribution','free','investor',20,None,None)]
    cash=[ledger.cash_event(id,k,fr,to,n,pid,debt,rule) for id,k,fr,to,n,debt,rule in specs]
    debt=[]
    for id,k,n,loan,link in [('OLD-REPAY','principal_repayment',-70,'OLD','PRINCIPAL')]+([('NEW-DRAW','cash_draw',100,'NEW','PROCEEDS')] if kind=='refinance' else []):
        e=ledger.debt_event(id,k,n,pid,link);e['debt_id']=loan;debt.append(e)
    obligations=[{'obligation_id':id,'debt_id':'OLD','obligation_class':cl,'opening_due':ledger.money(n,'stock','OPENING:P1')} for id,cl,n in [('OLD-I','interest',2),('OLD-F','fee',1)]]
    oe=[dict(env,event_id=id,obligation_id=oid,kind='cash_settlement',due_effect=ledger.money(-n,'period_total',pid),cash_event_ref=ref,debt_event_ref=None,calendar_ref='CAL-1',period_ref=pid,sources=[ledger.src()]) for id,oid,n,ref in [('SET-I','OLD-I',2,'INTEREST'),('SET-F','OLD-F',1,'FEE')]]
    l=dict(env,ledger_id='SYNTHETIC-CLOSING',calendar=dict(env,calendar_id='CAL-1',boundary_convention='left_closed_right_open',continuous_coverage=True,periods=[{'period_id':pid,'start_date':'2028-02-01','end_date':'2028-03-01'}],sources=[ledger.src()]),accounts=accounts,debts=[{'debt_id':id,'opening_principal':ledger.money(n,'stock','OPENING:P1')} for id,n in [('OLD',70)]+([('NEW',0)] if kind=='refinance' else [])],date_bindings=[{'date_ref':'DATE-P1','iso_date':'2028-02-15'}],cash_events=cash,debt_events=debt,obligations=obligations,obligation_events=oe,closing_cash_claims=[{'account_id':id,'amount':ledger.money(5,'stock','CLOSING:P1')} for id in ['free','restricted']],closing_debt_claims=[{'debt_id':id,'amount':ledger.money(n,'stock','CLOSING:P1')} for id,n in [('OLD',0)]+([('NEW',100)] if kind=='refinance' else [])],closing_due_claims=[{'obligation_id':o['obligation_id'],'amount':ledger.money(0,'stock','CLOSING:P1')} for o in obligations])
    roles=dict(zip([s[0] for s in specs],['proceeds','principal_payoff','interest_payoff','fee_payoff','closing_cost','reserve_release','new_reserve','equity_distribution']))
    values={r:F(0) for r in ROLES}
    for id,_,_,_,n,_,_ in specs:values[roles[id]]+=n
    return dict(env,event_ledger=l,settlement_id='SYNTHETIC-'+kind,kind=kind,closing_period_ref=pid,closing_date_ref='DATE-P1',representation='explicit_gross_cash_movements',payoff_profile='all_preexisting_debts_closed',new_debt_id='NEW' if kind=='refinance' else None,debt_ids_to_close=['OLD'],obligation_inventory_state='declared_complete',completeness_evidence_ref='SYNTHETIC-DECLARED-INVENTORY-NOT-VERIFIED',valuation_claim=ledger.money(120,'stock','VALUATION:2028-02-15'),role_claims={r:ledger.money(v,'period_total',pid) for r,v in values.items()},cash_classifications=[{'cash_event_id':id,'role':roles[id],'evidence_ref':'SYNTHETIC-EXPLICIT-CLOSING-LINE'} for id in roles])

def main():
    checks=[]
    def ok(name,c):
        assert c,name;checks.append(name)
    def reject(name,mutate):
        x=fixture();mutate(x)
        try:reconcile(x)
        except (ValueError,ValidationError):checks.append(name)
        else:raise AssertionError(name)
    b=fixture();old=deepcopy(b);z=reconcile(b)
    ok('refi_gross_cash_sources_uses_retained_reconcile',z['state']=='internally_reconciled_reference' and z['sources_including_free_cash']=='106' and z['cash_uses']=='101' and z['retained_free_cash']=='5')
    ok('valuation_not_cash_proceeds_or_distribution',z['valuation_claim']['value']['numerator']==120 and z['distribution_recorded']=='20' and not z['valuation_is_cash'])
    ok('released_and_new_reserves_are_not_gross_equity',z['new_restricted_cash']=='5' and z['ledger_reference']['cash']['restricted']=='5' and z['ledger_reference']['gross_equity_distributions']=='20')
    ok('principal_interest_fee_settled_separately',z['ledger_reference']['debt']['OLD']=='0' and all(v=='0' for v in z['ledger_reference']['due'].values()))
    ok('new_debt_not_equity_recovery',z['ledger_reference']['debt']['NEW']=='100' and z['ledger_reference']['gross_equity_contributions']=='0')
    ok('no_automatic_distribution_of_retained_cash',z['retained_free_cash']=='5' and z['distribution_recorded']=='20')
    ok('source_records_unchanged',b==old)
    ok('balanced_statement_not_pass_or_publish',z['decision']=='PENDING' and not z['publication_authorized'])
    s=reconcile(fixture('sale'));ok('sale_uses_actual_receipt_not_valuation',s['state']=='internally_reconciled_reference' and s['sources_including_free_cash']=='106' and s['ledger_reference']['debt']=={'OLD':'0'})
    x=fixture();x['valuation_claim']=None;ok('valuation_absence_does_not_invent_cash',reconcile(x)['retained_free_cash']=='5')
    x=fixture();x['role_claims']['closing_cost']=ledger.money(4,'period_total','P1');z=reconcile(x);ok('statement_discrepancy_retained_not_adjusted',z['state']=='blocked' and any(i.get('residual')=='1' for i in z['issues']))
    x=fixture();x['role_claims']['other_use']={'state':'missing','causes':[{'field_id':'other closing uses','cause_kind':'missing','reason':'Not supplied'}]};z=reconcile(x);ok('missing_other_use_not_assumed_zero',z['state']=='blocked' and z['issues'][0]['original_claim']['causes'][0]['reason']=='Not supplied')
    for field,value,label in [('representation','net_receipt_with_withholdings','net_statement_no_fabricated_gross_cash'),('payoff_profile','partial_or_unresolved','partial_payoff_not_silently_closed'),('obligation_inventory_state','unresolved','unknown_obligations_not_closed')]:
        x=fixture();x[field]=value;z=reconcile(x);ok(label,z['state']=='blocked' and 'sources_including_free_cash' not in z)
    x=fixture();x['event_ledger']['closing_cash_claims'][0]['amount']=ledger.money(6,'stock','CLOSING:P1');z=reconcile(x);ok('ledger_discrepancy_blocks_statement',z['state']=='blocked' and z['issues'][0]['residual']=='1')
    x=fixture();l=x['event_ledger'];next(e for e in l['cash_events'] if e['event_id']=='PRINCIPAL')['amount']=ledger.money(69,'period_total','P1');l['debt_events'][0]['principal_effect']=ledger.money(-69,'period_total','P1');l['closing_debt_claims'][0]['amount']=ledger.money(1,'stock','CLOSING:P1');l['closing_cash_claims'][0]['amount']=ledger.money(6,'stock','CLOSING:P1');x['role_claims']['principal_payoff']=ledger.money(69,'period_total','P1');z=reconcile(x);ok('balanced_cash_does_not_prove_old_principal_paid_off',z['state']=='blocked' and any(i['cause']=='old principal remains outstanding' for i in z['issues']))
    x=fixture();l=x['event_ledger'];l['cash_events']=[e for e in l['cash_events'] if e['event_id']!='FEE'];l['obligation_events']=[e for e in l['obligation_events'] if e['event_id']!='SET-F'];l['closing_due_claims'][1]['amount']=ledger.money(1,'stock','CLOSING:P1');l['closing_cash_claims'][0]['amount']=ledger.money(6,'stock','CLOSING:P1');x['cash_classifications']=[c for c in x['cash_classifications'] if c['cash_event_id']!='FEE'];x['role_claims']['fee_payoff']=ledger.money(0,'period_total','P1');z=reconcile(x);ok('unpaid_fee_blocks_full_payoff_despite_zero_principal',z['state']=='blocked' and any(i['cause']=='old obligation remains outstanding' for i in z['issues']))
    x=fixture();l=x['event_ledger'];l['cash_events']=[e for e in l['cash_events'] if e['event_id']!='INTEREST'];next(e for e in l['cash_events'] if e['event_id']=='PRINCIPAL')['amount']=ledger.money(72,'period_total','P1');l['debt_events'][0]['principal_effect']=ledger.money(-72,'period_total','P1');cap=ledger.debt_event('OLD-CAP','capitalized_interest',2,'P1');cap['debt_id']='OLD';l['debt_events'].append(cap);oe=next(e for e in l['obligation_events'] if e['event_id']=='SET-I');oe.update(kind='capitalization',cash_event_ref=None,debt_event_ref='OLD-CAP');x['cash_classifications']=[c for c in x['cash_classifications'] if c['cash_event_id']!='INTEREST'];x['role_claims']['principal_payoff']=ledger.money(72,'period_total','P1');x['role_claims']['interest_payoff']=ledger.money(0,'period_total','P1');z=reconcile(x);ok('capitalized_interest_paid_once_inside_principal',z['state']=='internally_reconciled_reference' and z['cash_uses']=='101' and z['ledger_reference']['due']['OLD-I']=='0')
    x=fixture();l=x['event_ledger'];l['cash_events']=[e for e in l['cash_events'] if e['event_id']!='FEE'];oe=next(e for e in l['obligation_events'] if e['event_id']=='SET-F');oe.update(kind='documented_adjustment',cash_event_ref=None);l['closing_cash_claims'][0]['amount']=ledger.money(6,'stock','CLOSING:P1');x['cash_classifications']=[c for c in x['cash_classifications'] if c['cash_event_id']!='FEE'];x['role_claims']['fee_payoff']=ledger.money(0,'period_total','P1');z=reconcile(x);ok('documented_fee_adjustment_does_not_prove_cash_payment',z['state']=='blocked' and z['ledger_reference']['due']['OLD-F']=='0' and any(i['cause']=='old obligation adjustment is not proof of payment' for i in z['issues']))
    x=fixture();l=x['event_ledger'];l['calendar']['periods'].insert(0,{'period_id':'P0','start_date':'2028-01-01','end_date':'2028-02-01'});l['date_bindings'].append({'date_ref':'DATE-P0','iso_date':'2028-01-15'})
    for q in [a['opening_balance'] for a in l['accounts'] if a['opening_balance'] is not None]+[d['opening_principal'] for d in l['debts']]+[o['opening_due'] for o in l['obligations']]:q['period_ref']='OPENING:P0'
    l['cash_events'].append(ledger.cash_event('PRIOR','operating_receipt','buyer','free',3,'P0'));l['closing_cash_claims'][0]['amount']=ledger.money(8,'stock','CLOSING:P1');z=reconcile(x);ok('prior_period_cash_not_duplicated_or_ignored',z['state']=='internally_reconciled_reference' and z['free_cash_before']=='5' and z['retained_free_cash']=='8' and z['sources_including_free_cash']=='109')
    x=fixture();l=x['event_ledger'];e=ledger.debt_event('NEW-ADJUST','documented_principal_adjustment',1,'P1');e['debt_id']='NEW';l['debt_events'].append(e);l['closing_debt_claims'][1]['amount']=ledger.money(101,'stock','CLOSING:P1');z=reconcile(x);ok('new_noncash_principal_not_assumed_loan_cash',z['state']=='blocked' and any(i['cause'].startswith('new principal has') for i in z['issues']))
    x=fixture();l=x['event_ledger'];next(e for e in l['cash_events'] if e['event_id']=='PRINCIPAL')['amount']=ledger.money(68,'period_total','P1');l['debt_events'][0]['principal_effect']=ledger.money(-68,'period_total','P1');e=ledger.debt_event('OLD-ADJUST','documented_principal_adjustment',-2,'P1');e['debt_id']='OLD';l['debt_events'].append(e);l['closing_cash_claims'][0]['amount']=ledger.money(7,'stock','CLOSING:P1');x['role_claims']['principal_payoff']=ledger.money(68,'period_total','P1');z=reconcile(x);ok('old_principal_adjustment_not_cash_payoff_proof',z['state']=='blocked' and z['ledger_reference']['debt']['OLD']=='0' and any(i['cause'].startswith('old principal adjustment') for i in z['issues']))
    x=fixture();l=x['event_ledger'];l['cash_events'][0]['amount']=ledger.money(50,'period_total','P1');l['debt_events'][1]['principal_effect']=ledger.money(50,'period_total','P1');l['closing_debt_claims'][1]['amount']=ledger.money(50,'stock','CLOSING:P1');l['cash_events'].append(ledger.cash_event('CASH-IN','equity_contribution','investor','free',50,'P1'));x['cash_classifications'].append({'cash_event_id':'CASH-IN','role':'equity_contribution','evidence_ref':'SYNTHETIC-EXPLICIT-CONTRIBUTION'});x['role_claims']['proceeds']=ledger.money(50,'period_total','P1');x['role_claims']['equity_contribution']=ledger.money(50,'period_total','P1');z=reconcile(x);ok('explicit_contribution_and_distribution_not_netted',z['state']=='internally_reconciled_reference' and z['ledger_reference']['gross_equity_contributions']=='50' and z['distribution_recorded']=='20')
    x=fixture();x['event_ledger']['date_bindings'].append({'date_ref':'OTHER-DATE','iso_date':'2028-02-16'});next(e for e in x['event_ledger']['cash_events'] if e['event_id']=='COST')['date_ref']='OTHER-DATE'
    try:reconcile(x)
    except ValueError:checks.append('mixed_dates_not_assumed_same_closing')
    else:raise AssertionError('mixed closing dates accepted')
    mutations=[('context_mismatch',lambda x:x['context'].update(run_id='OTHER')),('cash_event_omitted',lambda x:x['cash_classifications'].pop()),('duplicate_cash_role',lambda x:x['cash_classifications'].append(deepcopy(x['cash_classifications'][0]))),('unknown_cash_role_ref',lambda x:x['cash_classifications'][0].update(cash_event_id='ABSENT')),('reserve_release_not_proceeds',lambda x:next(c for c in x['cash_classifications'] if c['cash_event_id']=='RELEASE').update(role='proceeds')),('bank_loan_not_equity_contribution',lambda x:x['cash_classifications'][0].update(role='equity_contribution')),('debt_not_omitted',lambda x:x.update(debt_ids_to_close=[])),('new_and_old_loan_not_same',lambda x:x.update(new_debt_id='OLD')),('unknown_new_loan',lambda x:x.update(new_debt_id='ABSENT')),('wrong_closing_period',lambda x:x.update(closing_period_ref='ABSENT')),('missing_closing_date',lambda x:x.update(closing_date_ref='ABSENT')),('no_implicit_zero_role_claim',lambda x:x['role_claims'].pop('other_source')),('no_empty_completeness_evidence',lambda x:x.update(completeness_evidence_ref='')),('wrong_statement_currency',lambda x:x['role_claims']['proceeds'].update(currency='OTHER')),('wrong_statement_period',lambda x:x['role_claims']['proceeds'].update(period_ref='P2')),('valuation_wrong_cutoff',lambda x:x['valuation_claim'].update(period_ref='P1')),('negative_gross_claim',lambda x:x['role_claims']['other_use']['value'].update(numerator=-1)),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(ledger.STORE),'synthetic_examples':{'refinance':reconcile(fixture()),'sale':reconcile(fixture('sale'))},'scope':'Explicit synthetic last-period gross-cash full-payoff settlement/ledger reconciliation only. Not actual obligation completeness, valuation/sizing approval, escrow/net-withheld counterpart inference, intraday order, distribution entitlement, tax/legal policy, independent audit or production.'}
    (ROOT/'references/settlement-bridge-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'references/fixtures/settlement-bridge-synthetic.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
