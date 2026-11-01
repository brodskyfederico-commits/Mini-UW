"""Explicit synthetic cost-to-period-to-cash links; no financial or accrual policy."""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_cost_scope as costs
import validate_calendar_ledger as ledger
ROOT=Path(__file__).resolve().parents[1]

def reconcile(data):
    ledger.schema_check('budget-payment-bridge',data)
    c=data['cost_package'];l=data['event_ledger'];ctx=data['context']
    if c['context']!=ctx or l['context']!=ctx:raise ValueError('mixed bridge context')
    cost_result=costs.reconcile(c);cash_result=ledger.reconcile(l)
    issues=[]
    if cost_result['state']=='blocked':issues.append({'cause':'budget unresolved','details':deepcopy(cost_result['issues'])})
    if cash_result['state']=='blocked':issues.append({'cause':'ledger unresolved','details':deepcopy(cash_result['issues'])})
    # All original claims and unlinked ledger records remain in the input; no rewriting.
    signature=None
    for rep in c['representations']:
        if rep['quoted_total']['state']=='known':
            _,signature=ledger.quantity(rep['quoted_total'],'stock',rep['quoted_total']['period_ref']);break
    if signature is None:raise ValueError('no explicit budget unit context')
    first_period=l['calendar']['periods'][0]['period_id']
    for account in l['accounts']:
        if account['account_class']!='external_counterparty':
            ledger.quantity(account['opening_balance'],'stock','OPENING:'+first_period,signature)
    def amount(q,period,where):
        if q['state']!='known':
            issues.append({'cause':'amount unresolved','location':where,'original_claim':deepcopy(q)})
            return None
        v,_=ledger.quantity(q,'period_total',period,signature)
        if v<0:raise ValueError('signed payment/credit requires separate treatment')
        return v
    def total(values):return sum(values,F(0)) if all(v is not None for v in values) else None
    def literal(v):return None if v is None else str(v)
    pids={p['period_id'] for p in l['calendar']['periods']}
    schedules=ledger.unique(data['schedule_allocations'],'allocation_id')
    links=ledger.unique(data['payment_allocations'],'link_id')
    events=ledger.unique(l['cash_events'],'event_id')
    development={id:e for id,e in events.items() if e['kind']=='development_payment'}
    by_scope={s:[] for s in c['required_scope_ids']};sv={};paid_by_schedule={id:[] for id in schedules};paid_by_event={id:[] for id in development};pairs=set()
    for id,s in schedules.items():
        if s['scope_id'] not in by_scope:raise ValueError('unknown economic scope')
        if s['period_ref'] not in pids:raise ValueError('unknown schedule period')
        sv[id]=amount(s['amount'],s['period_ref'],id);by_scope[s['scope_id']].append(sv[id])
    for id,link in links.items():
        eid=link['cash_event_id'];sid=link['schedule_allocation_id']
        if eid not in development or sid not in schedules:raise ValueError('orphan or non-development cash link')
        if (eid,sid) in pairs:raise ValueError('duplicate cash/schedule pair')
        pairs.add((eid,sid));v=amount(link['amount'],development[eid]['period_ref'],id)
        paid_by_event[eid].append(v);paid_by_schedule[sid].append(v)
    scope_rows=[]
    for scope,values in by_scope.items():
        budget=cost_result['scope_values'][scope];budget=None if budget is None else F(budget)
        scheduled=total(values) if values else None
        residual=budget-scheduled if budget is not None and scheduled is not None else None
        if not values:issues.append({'cause':'scope has no explicit schedule allocation','scope_id':scope})
        if budget is not None and budget<0:issues.append({'cause':'documented credit timing requires separate treatment','scope_id':scope})
        if residual is not None and residual!=0:issues.append({'cause':'budget schedule discrepancy','scope_id':scope,'residual':str(residual)})
        scope_rows.append({'scope_id':scope,'budget':literal(budget),'scheduled':literal(scheduled),'residual':literal(residual)})
    cash_rows=[]
    for eid,event in development.items():
        claimed=amount(event['amount'],event['period_ref'],eid);allocated=total(paid_by_event[eid]) if paid_by_event[eid] else None
        residual=claimed-allocated if claimed is not None and allocated is not None else None
        if not paid_by_event[eid]:issues.append({'cause':'development cash unmapped','event_id':eid})
        if residual is not None and residual!=0:issues.append({'cause':'cash allocation discrepancy','event_id':eid,'residual':str(residual)})
        cash_rows.append({'event_id':eid,'cash':literal(claimed),'allocated':literal(allocated),'residual':literal(residual)})
    schedule_rows=[]
    for sid,s in schedules.items():
        paid=total(paid_by_schedule[sid]);remaining=sv[sid]-paid if sv[sid] is not None and paid is not None else None
        if remaining is not None and remaining<0:issues.append({'cause':'payment exceeds linked scheduled amount; explicit treatment required','allocation_id':sid,'residual':str(remaining)})
        schedule_rows.append({'allocation_id':sid,'scheduled_period':s['period_ref'],'scheduled':literal(sv[sid]),'linked_cash':literal(paid),'not_cash_linked':literal(remaining)})
    return {'state':'blocked' if issues else 'internally_reconciled_reference','scope_reconciliation':scope_rows,'cash_reconciliation':cash_rows,'schedule_reconciliation':schedule_rows,'cost_reference':cost_result,'ledger_reference':cash_result,'issues':issues,'decision':'PENDING','publication_authorized':False}

def fixture():
    c=costs.fixture();l=ledger.fixture();ctx=deepcopy(l['context'])
    c['context']=deepcopy(ctx)
    for rep in c['representations']:rep['context']=deepcopy(ctx)
    schedule=[]
    for id,scope,pid,n in [('V1','vertical','P1',15),('V2','vertical','P2',5),('PK','parking','P1',5),('SITE','site','P1',5),('SOFT','soft','P2',7)]:
        schedule.append({'allocation_id':id,'scope_id':scope,'period_ref':pid,'amount':ledger.money(n,'period_total',pid),'mapping_evidence_ref':'SYNTHETIC-EXPLICIT-BUDGET-TIME'})
    links=[{'link_id':'LINK-'+sid,'cash_event_id':'COST','schedule_allocation_id':sid,'amount':ledger.money(n,'period_total','P1'),'mapping_evidence_ref':'SYNTHETIC-EXPLICIT-CASH-ALLOCATION'} for sid,n in [('V1',15),('PK',5),('SITE',5)]]
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':ctx,'bridge_id':'SYNTHETIC-BUDGET-CASH-01','cost_package':c,'event_ledger':l,'schedule_allocations':schedule,'payment_allocations':links}

def main():
    checks=[]
    def ok(name,condition):
        assert condition,name;checks.append(name)
    def reject(name,mutate):
        x=fixture();mutate(x)
        try:reconcile(x)
        except (ValidationError,ValueError):checks.append(name)
        else:raise AssertionError(name)
    b=fixture();before=deepcopy(b);z=reconcile(b)
    ok('explicit_scope_schedule_cash_bridge_reconciles',z['state']=='internally_reconciled_reference')
    ok('supporting_parking_quote_not_second_cost',sum(F(x['budget']) for x in z['scope_reconciliation'])==37)
    ok('one_payment_can_cover_multiple_cost_scopes',z['cash_reconciliation']==[{'event_id':'COST','cash':'25','allocated':'25','residual':'0'}])
    ok('scheduled_unpaid_is_not_cash_outflow',sum(F(x['not_cash_linked']) for x in z['schedule_reconciliation'])==12 and z['ledger_reference']['cash']['free']=='0')
    ok('no_accrual_or_payable_claim_inferred',all('payable' not in x for x in z['schedule_reconciliation']))
    ok('no_real_deal_decision_or_publish',z['decision']=='PENDING' and not z['publication_authorized'])
    ok('inputs_and_original_claims_not_mutated',b==before)
    x=fixture();event=next(e for e in x['event_ledger']['cash_events'] if e['event_id']=='COST');event['amount']=ledger.money(15,'period_total','P1');other=deepcopy(event);other.update(event_id='COST2',amount=ledger.money(10,'period_total','P1'));x['event_ledger']['cash_events'].append(other);x['payment_allocations'][0]['amount']=ledger.money(5,'period_total','P1');x['payment_allocations'].append(dict(deepcopy(x['payment_allocations'][0]),link_id='SPLIT',cash_event_id='COST2',amount=ledger.money(10,'period_total','P1')));z=reconcile(x)
    ok('one_schedule_slice_can_have_several_actual_payments',z['state']=='internally_reconciled_reference' and z['schedule_reconciliation'][0]['linked_cash']=='15' and len(z['cash_reconciliation'])==2)
    x=fixture();x['schedule_allocations'][0]['amount']=ledger.money(14,'period_total','P1');z=reconcile(x)
    ok('budget_timing_residual_retained',z['state']=='blocked' and z['scope_reconciliation'][0]['residual']=='1')
    x=fixture();x['payment_allocations'].pop();z=reconcile(x)
    ok('unallocated_payment_not_invented',z['state']=='blocked' and z['cash_reconciliation'][0]['residual']=='5')
    x=fixture();x['schedule_allocations']=[s for s in x['schedule_allocations'] if s['allocation_id']!='SOFT'];z=reconcile(x)
    ok('missing_scope_schedule_not_zero',z['state']=='blocked' and z['scope_reconciliation'][-1]['scheduled'] is None)
    x=fixture();x['payment_allocations']=[];z=reconcile(x)
    ok('empty_links_do_not_certify_payment_coverage',z['state']=='blocked' and z['cash_reconciliation'][0]['allocated'] is None)
    x=fixture();x['schedule_allocations'][0]['amount']={'state':'missing','causes':[{'field_id':'timing','cause_kind':'missing','reason':'No allocation supplied'}]};z=reconcile(x)
    ok('unresolved_schedule_preserves_cause',z['state']=='blocked' and z['scope_reconciliation'][0]['scheduled'] is None and any(i.get('original_claim',{}).get('causes') for i in z['issues']))
    x=fixture();x['payment_allocations'][0]['amount']={'state':'missing','causes':[{'field_id':'link','cause_kind':'missing','reason':'No amount supplied'}]};z=reconcile(x)
    ok('unknown_link_not_zero_or_residual_assignment',z['cash_reconciliation'][0]['allocated'] is None)
    x=fixture();x['cost_package']['representations'][1]=costs.rep('Parking-support',6,[('parking',6)]);x['cost_package']['representations'][1]['context']=deepcopy(x['context']);z=reconcile(x)
    ok('source_cost_conflict_blocks_bridge',z['state']=='blocked' and z['scope_reconciliation'][1]['budget'] is None and len(z['cost_reference']['scope_claims']['parking'])==2)
    x=fixture();x['event_ledger']['closing_cash_claims'][0]['amount']=ledger.money(1,'stock','CLOSING:P2');z=reconcile(x)
    ok('underlying_ledger_discrepancy_blocks_bridge',z['state']=='blocked' and z['ledger_reference']['issues'][0]['residual']=='1')
    x=fixture();x['payment_allocations'][0]['schedule_allocation_id']='V2';z=reconcile(x)
    ok('overallocated_slice_needs_explicit_treatment',z['state']=='blocked' and any(i['cause'].startswith('payment exceeds') for i in z['issues']))
    x=fixture();x['payment_allocations'][0]['schedule_allocation_id']='V2';x['payment_allocations'][0]['amount']=ledger.money(5,'period_total','P1');x['payment_allocations'].append(dict(deepcopy(x['payment_allocations'][0]),link_id='REMAINDER',schedule_allocation_id='V1',amount=ledger.money(10,'period_total','P1')));z=reconcile(x)
    ok('different_schedule_cash_periods_require_explicit_link_not_same_month_default',z['state']=='internally_reconciled_reference' and z['schedule_reconciliation'][1]['linked_cash']=='5')
    x=fixture();x['cost_package']['required_scope_ids'].append('explicit-zero');rep=costs.rep('Zero',0,[('explicit-zero',0)]);rep['context']=deepcopy(x['context']);x['cost_package']['representations'].append(rep);x['schedule_allocations'].append({'allocation_id':'ZERO','scope_id':'explicit-zero','period_ref':'P2','amount':ledger.money(0,'period_total','P2'),'mapping_evidence_ref':'SYNTHETIC-ZERO'});z=reconcile(x)
    ok('explicit_zero_scope_retained',z['state']=='internally_reconciled_reference' and z['scope_reconciliation'][-1]['scheduled']=='0')
    x=fixture();x['cost_package']['required_scope_ids'].append('credit');rep=costs.rep('Credit',-2,[('credit',-2)]);rep['context']=deepcopy(x['context']);x['cost_package']['representations'].append(rep);z=reconcile(x)
    ok('credit_not_silently_cash_netted',z['state']=='blocked' and z['scope_reconciliation'][-1]['budget']=='-2')
    mutations=[
        ('context_mismatch',lambda x:x['event_ledger']['context'].update(run_id='OTHER')),
        ('duplicate_allocation_id',lambda x:x['schedule_allocations'].append(deepcopy(x['schedule_allocations'][0]))),
        ('duplicate_payment_link_id',lambda x:x['payment_allocations'].append(deepcopy(x['payment_allocations'][0]))),
        ('same_pair_cannot_be_double_counted',lambda x:x['payment_allocations'].append(dict(deepcopy(x['payment_allocations'][0]),link_id='DIFFERENT'))),
        ('unknown_scope',lambda x:x['schedule_allocations'][0].update(scope_id='UNKNOWN')),
        ('unknown_period',lambda x:x['schedule_allocations'][0].update(period_ref='P99')),
        ('unknown_schedule_link',lambda x:x['payment_allocations'][0].update(schedule_allocation_id='NONE')),
        ('principal_cash_not_development_cost',lambda x:x['payment_allocations'][0].update(cash_event_id='PAY1')),
        ('reserve_transfer_not_development_cost',lambda x:x['payment_allocations'][0].update(cash_event_id='RESERVE')),
        ('unknown_cash_event',lambda x:x['payment_allocations'][0].update(cash_event_id='NONE')),
        ('missing_schedule_mapping_evidence',lambda x:x['schedule_allocations'][0].update(mapping_evidence_ref='')),
        ('missing_cash_mapping_evidence',lambda x:x['payment_allocations'][0].pop('mapping_evidence_ref')),
        ('currency_mismatch',lambda x:x['schedule_allocations'][0]['amount'].update(currency='OTHER')),
        ('unit_mismatch',lambda x:x['schedule_allocations'][0]['amount'].update(unit_id='OTHER')),
        ('basis_mismatch',lambda x:x['schedule_allocations'][0]['amount'].update(basis='OTHER')),
        ('amount_period_mismatch',lambda x:x['schedule_allocations'][0]['amount'].update(period_ref='P2')),
        ('stock_not_period_allocation',lambda x:x['schedule_allocations'][0]['amount'].update(measurement_role='stock')),
        ('wrong_dimensions',lambda x:x['schedule_allocations'][0]['amount']['dimensions'].update(area=-1)),
        ('negative_payment_allocation',lambda x:x['payment_allocations'][0]['amount']['value'].update(numerator=-1)),
        ('no_implicit_production_authorization',lambda x:x.update(authorization='granted')),
        ('no_zero_denominator',lambda x:x['schedule_allocations'][0]['amount']['value'].update(denominator=0))]
    for name,mutate in mutations:reject(name,mutate)
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(ledger.STORE),'synthetic_example':reconcile(b),'scope':'Exact explicit synthetic budget-schedule-payment linkage and underlying scoped references only. Not incurred-cost accounting, payable/retention certification, schedule-curve choice, bank eligibility, complete financial integration, real deal, independent audit or production.'}
    (ROOT/'references/fixtures/budget-payment-bridge-synthetic.json').write_text(json.dumps(b,indent=2)+'\n')
    (ROOT/'references/budget-payment-bridge-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
