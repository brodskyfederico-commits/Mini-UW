"""Explicit synthetic event groups, debt windows/caps and maturity. No inferred bank rules."""
from fractions import Fraction as F
from datetime import date
from copy import deepcopy
from pathlib import Path
import json
from jsonschema import ValidationError
import validate_calendar_ledger as ledger
import validate_settlement_bridge as closing
ROOT=Path(__file__).resolve().parents[1]

def reconcile(data):
    ledger.schema_check('financing-timeline',data);l=data['event_ledger']
    if l['context']!=data['context']:raise ValueError('timeline context mismatch')
    result=ledger.reconcile(l);common={'decision':'PENDING','publication_authorized':False,'contract_authority_verified':False}
    if result['state']=='blocked':return dict(common,state='blocked',ledger_reference=result,issues=deepcopy(result['issues']))
    if data['timeline_state']!='documented_claim':return dict(common,state='blocked',ledger_reference=result,issues=[{'cause':'chronology unresolved','source_state':data['timeline_state'],'original_timeline':deepcopy(data['timeline'])}])
    if data['assessment_date'] is None:return dict(common,state='blocked',ledger_reference=result,issues=[{'cause':'assessment date missing','original_claim':None}])
    c=l['calendar'];pids=[p['period_id'] for p in c['periods']];asof=date.fromisoformat(data['assessment_date'])
    if ledger.assign(c,data['assessment_date'])!=pids[-1]:raise ValueError('assessment must lie in last covered period')
    groups=ledger.unique(data['timeline'],'action_id');seq=ledger.unique(data['timeline'],'sequence')
    if set(seq)!=set(range(len(seq))):raise ValueError('explicit consecutive sequence from zero required')
    families={'cash':ledger.unique(l['cash_events'],'event_id'),'debt':ledger.unique(l['debt_events'],'event_id'),'obligation':ledger.unique(l['obligation_events'],'event_id')}
    memberships={k:{} for k in families};last=None
    for i in range(len(seq)):
        group=seq[i];when=date.fromisoformat(group['iso_date']);pid=ledger.assign(c,group['iso_date'])
        if when>asof or (last is not None and when<last):raise ValueError('timeline reversed or beyond assessment')
        last=when
        if not any(group[k+'_event_ids'] for k in families):raise ValueError('empty atomic event group')
        for family,events in families.items():
            for id in group[family+'_event_ids']:
                if id not in events or id in memberships[family]:raise ValueError('unknown/duplicated timeline event')
                if events[id]['period_ref']!=pid:raise ValueError('event/group period mismatch')
                memberships[family][id]=group['action_id']
    for family,events in families.items():
        if set(memberships[family])!=set(events):raise ValueError('timeline must explicitly bind every recorded event')
    dates=ledger.unique(l['date_bindings'],'date_ref')
    for id,e in families['cash'].items():
        if dates[e['date_ref']]['iso_date']!=groups[memberships['cash'][id]]['iso_date']:raise ValueError('cash/action date mismatch')
    for id,e in families['debt'].items():
        if e['cash_event_ref'] is not None:
            if e['cash_event_ref'] not in memberships['cash']:raise ValueError('unknown cash counterpart')
            if memberships['debt'][id]!=memberships['cash'][e['cash_event_ref']]:raise ValueError('cash/principal counterparts must be atomic')
    for id,e in families['obligation'].items():
        for family,key in [('cash','cash_event_ref'),('debt','debt_event_ref')]:
            if e[key] is not None:
                if e[key] not in memberships[family]:raise ValueError('unknown obligation counterpart')
                if memberships['obligation'][id]!=memberships[family][e[key]]:raise ValueError('obligation counterpart must be atomic')
    accounts=ledger.unique(l['accounts'],'account_id');loans=ledger.unique(l['debts'],'debt_id');obligations=ledger.unique(l['obligations'],'obligation_id');terms=ledger.unique(data['loan_terms'],'debt_id')
    if set(terms)!=set(loans):raise ValueError('all and only recorded loans need explicit term records')
    permissions=ledger.unique(data['restricted_action_permissions'],'cash_event_id')
    required_permissions={id for id,e in families['cash'].items() if e['kind'] in ['restricted_transfer','reserve_release']}
    if set(permissions)!=required_permissions:raise ValueError('restriction claims missing/duplicated/unknown')
    signature=None;cash={};principal={};due={};issues=[];valid_terms={};cumulative={};maturity_results={}
    for id,a in accounts.items():
        if a['account_class']!='external_counterparty':cash[id],signature=ledger.quantity(a['opening_balance'],'stock','OPENING:'+pids[0],signature)
    def money(q,role,period):return ledger.quantity(q,role,period,signature)[0]
    for id,a in loans.items():principal[id]=money(a['opening_principal'],'stock','OPENING:'+pids[0])
    for id,o in obligations.items():due[id]=money(o['opening_due'],'stock','OPENING:'+pids[0])
    for id,t in terms.items():
        unresolved=t['terms_state']!='documented_claim' or not t['evidence_ref'] or any(t[k] is None for k in ['draw_start_date','draw_end_date','draw_start_boundary','draw_end_boundary','maturity_date','maturity_cutoff','capacity_basis']) or t['capacity']['state']!='known'
        if unresolved:issues.append({'cause':'loan terms unresolved','debt_id':id,'original_claim':deepcopy(t)});continue
        start=date.fromisoformat(t['draw_start_date']);end=date.fromisoformat(t['draw_end_date']);mat=date.fromisoformat(t['maturity_date'])
        if start>end or end>mat:raise ValueError('draw window inverted or extends past declared maturity')
        cap=money(t['capacity'],'stock','FACILITY:'+id)
        if cap<0:raise ValueError('negative facility capacity')
        if t['capacity_basis']=='cumulative_cash_draws':
            q=t['prior_cash_draws']
            if q is None or q['state']!='known':issues.append({'cause':'prior cumulative draws unresolved','debt_id':id,'original_claim':deepcopy(q)});continue
            prior=money(q,'stock','PRIOR-CASH-DRAWS:'+id)
            if prior<0:raise ValueError('negative prior cumulative draws')
            cumulative[id]=prior
        else:
            if t['prior_cash_draws'] is not None:raise ValueError('unused prior-draws claim for outstanding-principal basis')
            cumulative[id]=F(0)
        valid_terms[id]=(t,start,end,mat,cap)
    for id,p in permissions.items():
        e=families['cash'][id]
        if p['state']!='documented_claim' or not p['rule_ref'] or not p['evidence_ref']:issues.append({'cause':'restriction claim unresolved','cash_event_id':id,'original_claim':deepcopy(p)})
        elif p['rule_ref']!=e['restriction_rule_ref']:raise ValueError('restriction rule reference mismatch')
    def capacity_check(point):
        for id,(t,_,_,_,cap) in valid_terms.items():
            used=principal[id] if t['capacity_basis']=='maximum_outstanding_principal' else cumulative[id]
            if used>cap:issues.append({'cause':'declared capacity exceeded','debt_id':id,'point':point,'basis':t['capacity_basis'],'used':str(used),'limit':str(cap),'excess':str(used-cap)})
    def maturity_check(when,at_assessment=False):
        for id,(t,_,_,mat,_) in valid_terms.items():
            reached=(when>=mat if t['maturity_cutoff']=='exclusive_start_of_date' or at_assessment else when>mat)
            if not reached or id in maturity_results:continue
            unpaid=sum((v for oid,v in due.items() if obligations[oid]['debt_id']==id),F(0))
            maturity_results[id]={'maturity_date':str(mat),'cutoff':t['maturity_cutoff'],'principal':str(principal[id]),'recorded_unpaid_obligations':str(unpaid),'state':'recorded_balances_zero_at_declared_cutoff' if principal[id]==0 and unpaid==0 else 'unresolved_at_declared_cutoff'}
            if principal[id]!=0 or unpaid!=0:issues.append({'cause':'recorded obligations not cleared at maturity','debt_id':id,**maturity_results[id]})
    capacity_check('OPENING');snapshots=[]
    for i in range(len(seq)):
        group=seq[i];when=date.fromisoformat(group['iso_date']);pid=ledger.assign(c,group['iso_date']);maturity_check(when)
        for eid in group['cash_event_ids']:
            e=families['cash'][eid];v=money(e['amount'],'period_total',pid)
            if e['from_account'] in cash:cash[e['from_account']]-=v
            if e['to_account'] in cash:cash[e['to_account']]+=v
            touches_restricted=any(accounts[e[k]]['account_class']=='restricted_project_cash' for k in ['from_account','to_account'])
            if touches_restricted and e['kind'] not in ['restricted_transfer','reserve_release']:issues.append({'cause':'direct restricted-cash use needs separate explicit treatment','cash_event_id':eid})
        for eid in group['debt_event_ids']:
            e=families['debt'][eid];v=money(e['principal_effect'],'period_total',pid);id=e['debt_id'];principal[id]+=v
            if e['kind']=='cash_draw' and id in valid_terms:
                t,start,end,mat,_=valid_terms[id];cumulative[id]+=v
                allowed=(when>=start if t['draw_start_boundary']=='inclusive' else when>start) and (when<=end if t['draw_end_boundary']=='inclusive' else when<end)
                matured=when>mat or (when==mat and t['maturity_cutoff']=='exclusive_start_of_date')
                if not allowed or matured:issues.append({'cause':'draw outside declared date permissions','debt_id':id,'action_id':group['action_id'],'iso_date':str(when)})
        for eid in group['obligation_event_ids']:
            e=families['obligation'][eid];due[e['obligation_id']]+=money(e['due_effect'],'period_total',pid)
        for id,(t,_,_,mat,_) in valid_terms.items():
            expired=when>mat or (when==mat and t['maturity_cutoff']=='exclusive_start_of_date')
            unpaid=sum((v for oid,v in due.items() if obligations[oid]['debt_id']==id),F(0))
            if expired and (principal[id]>0 or unpaid>0):issues.append({'cause':'balance recorded after declared maturity','debt_id':id,'action_id':group['action_id'],'principal':str(principal[id]),'recorded_unpaid_obligations':str(unpaid)})
        for kind,values in [('cash',cash),('principal',principal),('unpaid_obligation',due)]:
            for id,v in values.items():
                if v<0:issues.append({'cause':'negative balance in explicit sequence','balance_kind':kind,'id':id,'action_id':group['action_id'],'amount':str(v)})
        capacity_check(group['action_id']);snapshots.append({'action_id':group['action_id'],'iso_date':group['iso_date'],'sequence':i,'cash':{k:str(v) for k,v in cash.items()},'principal':{k:str(v) for k,v in principal.items()},'due':{k:str(v) for k,v in due.items()}})
    maturity_check(asof,at_assessment=True)
    for id,(_,_,_,mat,_) in valid_terms.items():
        if id not in maturity_results:maturity_results[id]={'state':'not_reached_within_assessed_horizon','maturity_date':str(mat)}
    assert {k:str(v) for k,v in cash.items()}==result['cash'] and {k:str(v) for k,v in principal.items()}==result['debt'] and {k:str(v) for k,v in due.items()}==result['due']
    return dict(common,state='blocked' if issues else 'internally_reconciled_reference',ledger_reference=result,issues=issues,action_snapshots=snapshots,maturity_diagnostics=maturity_results,capacity_claims={id:{'basis':t['capacity_basis'],'limit':str(cap),'used_at_assessment':str(principal[id] if t['capacity_basis']=='maximum_outstanding_principal' else cumulative[id]),'unused_at_assessment':str(cap-(principal[id] if t['capacity_basis']=='maximum_outstanding_principal' else cumulative[id]))} for id,(t,_,_,_,cap) in valid_terms.items()})

def term(id,cap,start,end,mat):
    return {'debt_id':id,'terms_state':'documented_claim','evidence_ref':'SYNTHETIC-TERMS-NOT-AUTHENTICATED','draw_start_date':start,'draw_end_date':end,'draw_start_boundary':'inclusive','draw_end_boundary':'inclusive','maturity_date':mat,'maturity_cutoff':'inclusive_end_of_date','capacity_basis':'maximum_outstanding_principal','capacity':ledger.money(cap,'stock','FACILITY:'+id),'prior_cash_draws':None}

def from_closing_fixture():
    source=closing.fixture();l=source['event_ledger'];groups=[]
    for i,e in enumerate(l['cash_events']):
        groups.append({'action_id':'ACTION-'+e['event_id'],'sequence':i,'iso_date':'2028-02-15','cash_event_ids':[e['event_id']],'debt_event_ids':[d['event_id'] for d in l['debt_events'] if d['cash_event_ref']==e['event_id']],'obligation_event_ids':[o['event_id'] for o in l['obligation_events'] if o['cash_event_ref']==e['event_id']],'atomic_group_evidence_ref':'SYNTHETIC-EXPLICIT-ORDER'})
    permissions=[{'cash_event_id':e['event_id'],'state':'documented_claim','rule_ref':e['restriction_rule_ref'],'evidence_ref':'SYNTHETIC-RESTRICTION-NOT-VERIFIED'} for e in l['cash_events'] if e['kind'] in ['restricted_transfer','reserve_release']]
    return dict(ledger.env(),event_ledger=l,assessment_date='2028-02-29',assessment_cutoff='end_of_date',timeline_state='documented_claim',timeline=groups,loan_terms=[term('OLD',70,'2028-01-01','2028-02-14','2028-02-15'),term('NEW',100,'2028-02-15','2028-02-29','2028-03-15')],restricted_action_permissions=permissions)

def main():
    checks=[]
    def ok(name,c):
        assert c,name;checks.append(name)
    def reject(name,mutate):
        x=from_closing_fixture();mutate(x)
        try:reconcile(x)
        except (ValueError,ValidationError):checks.append(name)
        else:raise AssertionError(name)
    b=from_closing_fixture();before=deepcopy(b);z=reconcile(b)
    ok('explicit_closing_timeline_reconciles',z['state']=='internally_reconciled_reference' and len(z['action_snapshots'])==8)
    ok('inclusive_maturity_paid_on_date',z['maturity_diagnostics']['OLD']['state']=='recorded_balances_zero_at_declared_cutoff')
    ok('future_maturity_not_certified',z['maturity_diagnostics']['NEW']['state']=='not_reached_within_assessed_horizon')
    ok('balances_equal_period_ledger',z['action_snapshots'][-1]['cash']==z['ledger_reference']['cash'] and z['action_snapshots'][-1]['principal']==z['ledger_reference']['debt'])
    ok('source_records_not_mutated',b==before)
    ok('not_authority_or_deal_approval',not z['contract_authority_verified'] and not z['publication_authorized'] and z['decision']=='PENDING')
    x=from_closing_fixture();x.update(timeline_state='unresolved',timeline=[]);z=reconcile(x)
    ok('missing_sequence_is_pending_without_inferred_order',z['state']=='blocked' and z['issues'][0]['original_timeline']==[])
    x=from_closing_fixture();x['assessment_date']=None;z=reconcile(x)
    ok('missing_assessment_date_not_selected_from_calendar',z['state']=='blocked' and z['issues'][0]['cause']=='assessment date missing')
    x=from_closing_fixture();x['loan_terms'][1]['maturity_cutoff']=None;z=reconcile(x)
    ok('missing_boundary_not_filled_inclusively',z['state']=='blocked' and z['issues'][0]['original_claim']['maturity_cutoff'] is None)
    x=from_closing_fixture();x['timeline'][0]['sequence']=1;x['timeline'][1]['sequence']=0;z=reconcile(x)
    ok('end_period_balanced_but_payment_before_receipt_blocked',z['state']=='blocked' and z['ledger_reference']['state']=='internally_reconciled_reference' and any(i['cause']=='negative balance in explicit sequence' and i['balance_kind']=='cash' for i in z['issues']))
    x=from_closing_fixture();x['loan_terms'][0]['maturity_cutoff']='exclusive_start_of_date';z=reconcile(x)
    ok('exclusive_maturity_not_repaired_by_same_day_payment',z['state']=='blocked' and z['maturity_diagnostics']['OLD']['principal']=='70')
    x=from_closing_fixture();x['loan_terms'][1]['maturity_date']='2028-02-29';z=reconcile(x)
    ok('maturity_assessed_without_action_on_maturity_date',z['state']=='blocked' and z['maturity_diagnostics']['NEW']['principal']=='100')
    x=from_closing_fixture();x['loan_terms'][1]['draw_start_boundary']='exclusive';z=reconcile(x)
    ok('draw_at_excluded_start_blocked',z['state']=='blocked' and any(i['cause']=='draw outside declared date permissions' for i in z['issues']))
    x=from_closing_fixture();x['loan_terms'][1]['draw_end_date']='2028-02-15';x['loan_terms'][1]['draw_end_boundary']='exclusive';z=reconcile(x)
    ok('draw_at_excluded_end_blocked',z['state']=='blocked' and any(i['cause']=='draw outside declared date permissions' for i in z['issues']))
    x=from_closing_fixture();x['loan_terms'][1]['capacity']=ledger.money(99,'stock','FACILITY:NEW');z=reconcile(x)
    ok('capacity_excess_not_covered_with_fictitious_loan',z['state']=='blocked' and z['capacity_claims']['NEW']['unused_at_assessment']=='-1')
    x=from_closing_fixture();x['loan_terms'][1].update(terms_state='unresolved',draw_end_date=None);z=reconcile(x)
    ok('missing_terms_preserve_claim_and_block',z['state']=='blocked' and z['issues'][0]['original_claim']['draw_end_date'] is None)
    x=from_closing_fixture();x['restricted_action_permissions'][0]['state']='unresolved';z=reconcile(x)
    ok('release_rule_label_alone_not_sufficient',z['state']=='blocked' and any(i['cause']=='restriction claim unresolved' for i in z['issues']))
    x=from_closing_fixture();x['loan_terms'][1].update(capacity_basis='cumulative_cash_draws',prior_cash_draws=None);z=reconcile(x)
    ok('cumulative_history_not_assumed_zero',z['state']=='blocked' and any(i['cause']=='prior cumulative draws unresolved' for i in z['issues']))
    x=from_closing_fixture();x['loan_terms'][1].update(capacity_basis='cumulative_cash_draws',prior_cash_draws=ledger.money(10,'stock','PRIOR-CASH-DRAWS:NEW'));z=reconcile(x)
    ok('explicit_prior_draws_count_toward_limit',z['state']=='blocked' and z['capacity_claims']['NEW']['used_at_assessment']=='110')
    x=from_closing_fixture();l=x['event_ledger'];newgroups=[]
    for eid,kind,fr,to,value,effect in [('REPAY-NEW','principal_payment','free','new_bank',20,-20),('REDRAW-NEW','loan_cash_draw','new_bank','free',20,20)]:
        ce=ledger.cash_event(eid,kind,fr,to,value,'P1','NEW');l['cash_events'].append(ce);de=ledger.debt_event('D-'+eid,'principal_repayment' if effect<0 else 'cash_draw',effect,'P1',eid);de['debt_id']='NEW';l['debt_events'].append(de);newgroups.append({'action_id':'ACTION-'+eid,'sequence':0,'iso_date':'2028-02-15','cash_event_ids':[eid],'debt_event_ids':['D-'+eid],'obligation_event_ids':[],'atomic_group_evidence_ref':'SYNTHETIC-REPAY-THEN-REDRAW'})
    x['timeline'][1:1]=newgroups
    for i,g in enumerate(x['timeline']):g['sequence']=i
    z=reconcile(x);ok('outstanding_basis_repay_then_redraw_under_explicit_cap',z['state']=='internally_reconciled_reference' and z['capacity_claims']['NEW']['used_at_assessment']=='100')
    x['loan_terms'][1].update(capacity_basis='cumulative_cash_draws',prior_cash_draws=ledger.money(0,'stock','PRIOR-CASH-DRAWS:NEW'));z=reconcile(x)
    ok('repayment_does_not_restore_cumulative_draw_capacity',z['state']=='blocked' and z['capacity_claims']['NEW']['used_at_assessment']=='120' and z['capacity_claims']['NEW']['unused_at_assessment']=='-20')
    x=from_closing_fixture();l=x['event_ledger'];next(o for o in l['obligations'] if o['obligation_id']=='OLD-I')['opening_due']=ledger.money(0,'stock','OPENING:P1');oe=dict(ledger.env(),event_id='LATE-ACCRUAL',obligation_id='OLD-I',kind='accrual',due_effect=ledger.money(2,'period_total','P1'),cash_event_ref=None,debt_event_ref=None,calendar_ref='CAL-1',period_ref='P1',sources=[ledger.src()]);l['obligation_events'].append(oe);x['timeline'].append({'action_id':'LATE-ACCRUAL-ACTION','sequence':len(x['timeline']),'iso_date':'2028-02-15','cash_event_ids':[],'debt_event_ids':[],'obligation_event_ids':['LATE-ACCRUAL'],'atomic_group_evidence_ref':'SYNTHETIC-LATE-ACCRUAL'});z=reconcile(x)
    ok('payment_before_accrual_not_hidden_by_period_netting',z['state']=='blocked' and any(i['cause']=='negative balance in explicit sequence' and i['balance_kind']=='unpaid_obligation' for i in z['issues']))
    x=from_closing_fixture();l=x['event_ledger'];e=next(e for e in l['cash_events'] if e['event_id']=='DIST');e.update(from_account='restricted',amount=ledger.money(1,'period_total','P1'));l['closing_cash_claims'][0]['amount']=ledger.money(25,'stock','CLOSING:P1');l['closing_cash_claims'][1]['amount']=ledger.money(4,'stock','CLOSING:P1');z=reconcile(x)
    ok('restricted_distribution_not_allowed_by_cash_balance_alone',z['state']=='blocked' and any(i['cause']=='direct restricted-cash use needs separate explicit treatment' for i in z['issues']))
    x=from_closing_fixture();l=x['event_ledger'];l['cash_events']=[e for e in l['cash_events'] if e['event_id']!='INTEREST'];next(e for e in l['cash_events'] if e['event_id']=='PRINCIPAL')['amount']=ledger.money(72,'period_total','P1');l['debt_events'][0]['principal_effect']=ledger.money(-72,'period_total','P1');cap=ledger.debt_event('OLD-CAP','capitalized_interest',2,'P1');cap['debt_id']='OLD';l['debt_events'].append(cap);oe=next(e for e in l['obligation_events'] if e['event_id']=='SET-I');oe.update(kind='capitalization',cash_event_ref=None,debt_event_ref='OLD-CAP');x['timeline']=[g for g in x['timeline'] if 'INTEREST' not in g['cash_event_ids']];x['timeline'].insert(1,{'action_id':'CAPITALIZE','sequence':1,'iso_date':'2028-02-15','cash_event_ids':[],'debt_event_ids':['OLD-CAP'],'obligation_event_ids':['SET-I'],'atomic_group_evidence_ref':'SYNTHETIC-CAPITALIZATION-ATOMIC'})
    for i,g in enumerate(x['timeline']):g['sequence']=i
    z=reconcile(x);ok('capitalized_interest_can_exceed_outstanding_cap_without_cash_draw',z['state']=='blocked' and z['ledger_reference']['debt']['OLD']=='0' and any(i['cause']=='declared capacity exceeded' and i['point']=='CAPITALIZE' and i['excess']=='2' for i in z['issues']))
    x=from_closing_fixture();x['loan_terms'][1]['capacity']=ledger.money(0,'stock','FACILITY:NEW');z=reconcile(x)
    ok('explicit_zero_capacity_is_known_limit',z['state']=='blocked' and z['capacity_claims']['NEW']['limit']=='0' and z['capacity_claims']['NEW']['unused_at_assessment']=='-100')
    mutations=[('context_mismatch',lambda x:x['context'].update(run_id='OTHER')),('duplicate_action_id',lambda x:x['timeline'].append(deepcopy(x['timeline'][0]))),('duplicate_sequence',lambda x:x['timeline'][1].update(sequence=0)),('missing_sequence',lambda x:x['timeline'][1].update(sequence=99)),('missing_recorded_action',lambda x:x['timeline'].pop()),('unknown_cash_action',lambda x:x['timeline'][0].update(cash_event_ids=['MISSING'])),('cash_event_in_two_actions',lambda x:x['timeline'][1].update(cash_event_ids=x['timeline'][0]['cash_event_ids'])),('date_mismatch',lambda x:x['timeline'][0].update(iso_date='2028-02-14')),('action_after_assessment',lambda x:x.update(assessment_date='2028-02-14')),('assessment_outside_calendar',lambda x:x.update(assessment_date='2028-03-01')),('missing_loan_terms',lambda x:x['loan_terms'].pop()),('duplicate_loan_terms',lambda x:x['loan_terms'].append(deepcopy(x['loan_terms'][0]))),('unknown_loan_terms',lambda x:x['loan_terms'][0].update(debt_id='OTHER')),('missing_restriction_record',lambda x:x['restricted_action_permissions'].pop()),('restriction_reference_mismatch',lambda x:x['restricted_action_permissions'][0].update(rule_ref='OTHER')),('wrong_cap_currency',lambda x:x['loan_terms'][0]['capacity'].update(currency='OTHER')),('wrong_capacity_basis_cutoff',lambda x:x['loan_terms'][0]['capacity'].update(period_ref='P1')),('inverted_window',lambda x:x['loan_terms'][0].update(draw_start_date='2028-02-16')),('draw_window_past_maturity',lambda x:x['loan_terms'][0].update(draw_end_date='2028-02-20')),('negative_capacity',lambda x:x['loan_terms'][0]['capacity']['value'].update(numerator=-1)),('unused_prior_draws_not_ignored',lambda x:x['loan_terms'][0].update(prior_cash_draws=ledger.money(1,'stock','PRIOR-CASH-DRAWS:OLD'))),('no_empty_atomic_evidence',lambda x:x['timeline'][0].update(atomic_group_evidence_ref='')),('no_two_cash_events_hide_transient_deficit',lambda x:x['timeline'][0]['cash_event_ids'].append('PRINCIPAL')),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    # Separate valid records into two actions: period ledger still balances, timeline must reject atomic split.
    x=from_closing_fixture();x['timeline'][1]['debt_event_ids']=[];x['timeline'][0]['debt_event_ids'].append('OLD-REPAY')
    try:reconcile(x)
    except ValueError:checks.append('cash_principal_pair_cannot_split_actions')
    else:raise AssertionError('split cash/principal pair accepted')
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(ledger.STORE),'synthetic_example':reconcile(b),'scope':'Explicit synthetic ordered atomic-record groups, nonnegative cash/debt/due snapshots, declared capacity/window/maturity and restriction-claim diagnostics only. Not discovered bank terms, legal interpretation, authority of documents, real intraday execution, complete commitments/covenants, solver, independent audit or production.'}
    (ROOT/'references/financing-timeline-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'references/fixtures/financing-timeline-synthetic.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
