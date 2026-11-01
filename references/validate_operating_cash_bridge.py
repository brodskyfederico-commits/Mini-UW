"""Declared accrued-operation-to-cash identity with explicit working balances. Synthetic only."""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_calendar_ledger as ledger
ROOT=Path(__file__).resolve().parents[1]

def reconcile(data):
    ledger.schema_check('operating-cash-bridge',data);l=data['event_ledger']
    if data['context']!=l['context']:raise ValueError('operating/ledger context mismatch')
    z=ledger.reconcile(l);issues=[]
    common={'decision':'PENDING','publication_authorized':False}
    if z['state']=='blocked':return dict(common,state='blocked',ledger_reference=z,issues=deepcopy(z['issues']),periods=[])
    periods=[p['period_id'] for p in l['calendar']['periods']];records=ledger.unique(data['period_records'],'period_ref')
    if set(records)!=set(periods):raise ValueError('every calendar period needs explicit M2 and balance records')
    signature=None
    for account in l['accounts']:
        if account['account_class']!='external_counterparty':_,signature=ledger.quantity(account['opening_balance'],'stock','OPENING:'+periods[0],signature)
    def amount(q,role,pid,where):
        if q['state']!='known':issues.append({'cause':'operating bridge amount unresolved','location':where,'original_claim':deepcopy(q)});return None
        return ledger.quantity(q,role,pid,signature)[0]
    def lit(v):return None if v is None else str(v)
    result=[];previous={}
    for pid in periods:
        record=records[pid];m=record['m2_result']
        if m['context']!=data['context']:raise ValueError('M2 result context mismatch')
        local_start=len(issues)
        if m['status']!='candidate_complete':issues.append({'cause':'M2 source not structurally complete','period_ref':pid,'status':m['status'],'pending_causes':deepcopy(m['pending_causes'])})
        vals={k:amount(q,'period_total',pid,pid+'.'+k) for k,q in m['outputs'].items()}
        balances={};deltas={}
        for bucket,pair in record['working_balances'].items():
            a=amount(pair['opening'],'stock','OPENING:'+pid,pid+'.'+bucket+'.opening');b=amount(pair['closing'],'stock','CLOSING:'+pid,pid+'.'+bucket+'.closing')
            if any(v is not None and v<0 for v in [a,b]):raise ValueError('gross working-balance buckets cannot encode credit balances; separate treatment required')
            if bucket in previous:
                prior=previous[bucket]
                if prior is None or a is None:issues.append({'cause':'balance continuity unresolved','bucket':bucket,'period_ref':pid})
                elif prior!=a:issues.append({'cause':'working-balance discontinuity','bucket':bucket,'period_ref':pid,'prior_close':str(prior),'next_open':str(a),'residual':str(a-prior)})
            previous[bucket]=b;balances[bucket]=(a,b);deltas[bucket]=None if a is None or b is None else b-a
        nr=amount(record['noncash_revenue'],'period_total',pid,pid+'.noncash_revenue');ne=amount(record['noncash_expense'],'period_total',pid,pid+'.noncash_expense')
        receipts=sum((ledger.quantity(e['amount'],'period_total',pid,signature)[0] for e in l['cash_events'] if e['period_ref']==pid and e['kind']=='operating_receipt'),F(0))
        payments=sum((ledger.quantity(e['amount'],'period_total',pid,signature)[0] for e in l['cash_events'] if e['period_ref']==pid and e['kind']=='operating_payment'),F(0))
        defined=all(v is not None for v in [*vals.values(),*deltas.values(),nr,ne])
        expected_r=expected_p=noi_residual=None
        if defined:
            expected_r=vals['effective_income']-nr-deltas['receivables']+deltas['deferred_revenue']
            expected_p=vals['operating_expenses']+vals['property_tax']-ne-deltas['payables']+deltas['prepaid_expenses']
            noi_residual=vals['noi']-(vals['effective_income']-vals['operating_expenses']-vals['property_tax'])
            for name,residual in [('NOI definition',noi_residual),('cash receipts',receipts-expected_r),('cash payments',payments-expected_p)]:
                if residual:issues.append({'cause':'operating/cash discrepancy','comparison':name,'period_ref':pid,'residual':str(residual)})
        result.append({'period_ref':pid,'state':'blocked' if len(issues)>local_start else 'internally_reconciled_reference','claimed_noi':lit(vals['noi']),'noi_definition_residual':lit(noi_residual),'expected_receipts':lit(expected_r),'ledger_receipts':str(receipts),'expected_payments':lit(expected_p),'ledger_payments':str(payments),'net_operating_cash':str(receipts-payments),'working_balance_deltas':{k:lit(v) for k,v in deltas.items()}})
    return dict(common,state='blocked' if issues else 'internally_reconciled_reference',ledger_reference=z,issues=issues,periods=result)

def fixture():
    env=ledger.env();l=ledger.fixture();pid='P1'
    l['calendar']['periods']=l['calendar']['periods'][:1];l['date_bindings']=l['date_bindings'][:1]
    for a in l['accounts']:
        if a['account_class']!='external_counterparty':a['opening_balance']=ledger.money(0,'stock','OPENING:P1')
    l.update(debts=[],debt_events=[],obligations=[],obligation_events=[],closing_debt_claims=[],closing_due_claims=[])
    l['cash_events']=[ledger.cash_event('COLLECT','operating_receipt','tenant','free',46,pid),ledger.cash_event('PAY','operating_payment','free','vendor',20,pid),ledger.cash_event('RESERVE','restricted_transfer','free','restricted',5,pid,rule='SYNTHETIC-RESERVE'),ledger.cash_event('DIST','equity_distribution','free','investor',10,pid)]
    l['closing_cash_claims']=[{'account_id':id,'amount':ledger.money(v,'stock','CLOSING:P1')} for id,v in [('free',11),('restricted',5)]]
    m=dict(env,schema_version='0.1-candidate',module='M2',status='candidate_complete',pending_causes=[],outputs={k:ledger.money(v,'period_total',pid) for k,v in [('effective_income',50),('operating_expenses',20),('property_tax',5),('noi',25)]})
    balances={k:{'opening':ledger.money(a,'stock','OPENING:P1'),'closing':ledger.money(b,'stock','CLOSING:P1')} for k,a,b in [('receivables',3,8),('deferred_revenue',2,4),('payables',4,9),('prepaid_expenses',1,3)]}
    return dict(env,event_ledger=l,profile='explicit_accrual_cash_reconciliation',profile_evidence_ref='SYNTHETIC-DECLARED-PROFILE-NOT-APPROVED',period_records=[{'period_ref':pid,'m2_result':m,'working_balances':balances,'noncash_revenue':ledger.money(1,'period_total',pid),'noncash_expense':ledger.money(2,'period_total',pid),'adjustment_evidence_ref':'SYNTHETIC-EXPLICIT-WORKING-BALANCES'}])

def main():
    checks=[]
    def ok(name,c):
        assert c,name;checks.append(name)
    def reject(name,mutate):
        x=fixture();mutate(x)
        try:reconcile(x)
        except (ValueError,ValidationError):checks.append(name)
        else:raise AssertionError(name)
    b=fixture();old=deepcopy(b);z=reconcile(b);p=z['periods'][0]
    ok('declared_accrual_cash_identity_reconciles',z['state']=='internally_reconciled_reference' and p['expected_receipts']=='46' and p['expected_payments']=='20')
    ok('noi_is_not_net_cash',p['claimed_noi']=='25' and p['net_operating_cash']=='26')
    ok('net_operating_cash_is_not_distribution',z['ledger_reference']['gross_equity_distributions']=='10' and p['net_operating_cash']=='26')
    ok('restricted_transfer_not_duplicate_operating_expense',p['ledger_payments']=='20' and z['ledger_reference']['cash']['restricted']=='5' and z['ledger_reference']['cash']['free']=='11')
    ok('source_claims_not_mutated',b==old)
    ok('balanced_bridge_not_decision_or_release',z['decision']=='PENDING' and not z['publication_authorized'])
    x=fixture();x['period_records'][0]['m2_result']['outputs']['noi']=ledger.money(26,'period_total','P1');z=reconcile(x);ok('noi_mismatch_not_silently_fixed',z['state']=='blocked' and z['periods'][0]['claimed_noi']=='26' and z['periods'][0]['noi_definition_residual']=='1')
    x=fixture();x['event_ledger']['cash_events'][0]['amount']=ledger.money(48,'period_total','P1');x['event_ledger']['closing_cash_claims'][0]['amount']=ledger.money(13,'stock','CLOSING:P1');z=reconcile(x);ok('balanced_ledger_does_not_override_accrual_bridge',z['state']=='blocked' and any(i.get('comparison')=='cash receipts' and i['residual']=='2' for i in z['issues']))
    x=fixture();x['period_records'][0]['noncash_expense']={'state':'missing','causes':[{'field_id':'noncash expense','cause_kind':'missing','reason':'Not supplied'}]};z=reconcile(x);ok('missing_noncash_not_zero',z['state']=='blocked' and z['periods'][0]['expected_payments'] is None and z['issues'][0]['original_claim']['causes'][0]['reason']=='Not supplied')
    x=fixture();m=x['period_records'][0]['m2_result'];m['status']='blocked';m['pending_causes']=[{'field_id':'NOI policy','cause_kind':'missing','reason':'Rule unresolved'}];z=reconcile(x);ok('known_outputs_do_not_erase_m2_blocker',z['state']=='blocked' and z['issues'][0]['pending_causes'][0]['reason']=='Rule unresolved')
    x=fixture();x['event_ledger']['closing_cash_claims'][0]['amount']=ledger.money(12,'stock','CLOSING:P1');z=reconcile(x);ok('underlying_cash_claim_mismatch_blocks',z['state']=='blocked' and z['periods']==[])
    # Add a second zero-operation period with unchanged explicit balances.
    x=fixture();l=x['event_ledger'];l['calendar']['periods'].append({'period_id':'P2','start_date':'2028-03-01','end_date':'2028-04-01'})
    for c in l['closing_cash_claims']:c['amount']['period_ref']='CLOSING:P2'
    r=deepcopy(x['period_records'][0]);r['period_ref']='P2'
    for k in r['m2_result']['outputs']:r['m2_result']['outputs'][k]=ledger.money(0,'period_total','P2')
    for pair in r['working_balances'].values():
        pair['opening']=deepcopy(pair['closing']);pair['opening']['period_ref']='OPENING:P2';pair['closing']['period_ref']='CLOSING:P2'
    r['noncash_revenue']=ledger.money(0,'period_total','P2');r['noncash_expense']=ledger.money(0,'period_total','P2');x['period_records'].append(r);z=reconcile(x)
    ok('empty_period_and_working_balance_continuity_preserved',z['state']=='internally_reconciled_reference' and len(z['periods'])==2 and z['periods'][1]['net_operating_cash']=='0')
    x['period_records'][1]['working_balances']['receivables']['opening']=ledger.money(9,'stock','OPENING:P2');z=reconcile(x);ok('working_balance_cannot_reset_between_periods',z['state']=='blocked' and any(i['cause']=='working-balance discontinuity' for i in z['issues']))
    mutations=[('context_mismatch',lambda x:x['context'].update(run_id='OTHER')),('m2_context_mismatch',lambda x:x['period_records'][0]['m2_result']['context'].update(run_id='OTHER')),('duplicate_period_record',lambda x:x['period_records'].append(deepcopy(x['period_records'][0]))),('unknown_period_record',lambda x:x['period_records'][0].update(period_ref='UNKNOWN')),('no_empty_period_records',lambda x:x.update(period_records=[])),('no_default_profile',lambda x:x.pop('profile')),('no_missing_adjustment_evidence',lambda x:x['period_records'][0].update(adjustment_evidence_ref='')),('currency_mismatch',lambda x:x['period_records'][0]['noncash_revenue'].update(currency='OTHER')),('flow_not_stock',lambda x:x['period_records'][0]['noncash_revenue'].update(measurement_role='stock')),('wrong_stock_cutoff',lambda x:x['period_records'][0]['working_balances']['receivables']['opening'].update(period_ref='P1')),('negative_gross_working_balance',lambda x:x['period_records'][0]['working_balances']['receivables']['opening']['value'].update(numerator=-1)),('no_default_zero_balance',lambda x:x['period_records'][0]['working_balances'].pop('payables')),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(ledger.STORE),'synthetic_example':reconcile(b),'scope':'Declared synthetic M2 accrued-income/expense/working-balance to recorded operating cash reconciliation only. Not approved NOI/reserve/accounting/tax definitions, authentic balance inventory, automatic cash distribution, independent audit or production.'}
    (ROOT/'references/operating-cash-bridge-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'references/fixtures/operating-cash-bridge-synthetic.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
