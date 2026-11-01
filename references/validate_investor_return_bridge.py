"""Explicit aggregate project-equity ledger/grid/returns reference. No investment policy."""
from fractions import Fraction as F
from datetime import date,timedelta
from copy import deepcopy
from pathlib import Path
import json
from jsonschema import ValidationError
import validate_calendar_ledger as ledger
import validate_periodic_irr_isolation as irr
ROOT=Path(__file__).resolve().parents[1]

def build(data):
    ledger.schema_check('investor-return-bridge',data)
    l=data['event_ledger']
    if data['context']!=l['context']:raise ValueError('mixed return/ledger context')
    reconciled=ledger.reconcile(l)
    common={'decision':'PENDING','publication_authorized':False,'annualized':False,'equity_level':'aggregate project equity only'}
    if reconciled['state']=='blocked':return dict(common,state='blocked',ledger_reference=reconciled,issues=deepcopy(reconciled['issues']),equity_multiple=None,periodic_irr=None)
    grid=data['return_grid'];points=ledger.unique(grid['points'],'point_id');indices=ledger.unique(grid['points'],'index')
    if set(indices)!=set(range(len(points))):raise ValueError('return indices must include every integer from zero without compression')
    first=date.fromisoformat(indices[0]['iso_date'])
    for i,p in indices.items():
        current=date.fromisoformat(p['iso_date'])
        if grid['spacing']=='fixed_days':expected=first+timedelta(days=grid['step']*i)
        else:
            month=first.year*12+first.month-1+grid['step']*i
            try:expected=date(month//12,month%12+1,first.day)
            except ValueError:raise ValueError('month-end/leap adjustment needs separate explicit convention')
        if current!=expected:raise ValueError('declared regular spacing does not match dates')
        if ledger.assign(l['calendar'],p['iso_date'])!=p['period_ref']:raise ValueError('return point calendar/period mismatch')
    events={e['event_id']:e for e in l['cash_events'] if e['kind'] in ['equity_contribution','equity_distribution']}
    bindings=ledger.unique(data['equity_event_bindings'],'event_id')
    if set(bindings)!=set(events):raise ValueError('all and only recorded equity events need one explicit timing binding')
    dates=ledger.unique(l['date_bindings'],'date_ref');rows={i:{'point_id':p['point_id'],'index':i,'iso_date':p['iso_date'],'period_ref':p['period_ref'],'contributions':F(0),'distributions':F(0),'contribution_event_ids':[],'distribution_event_ids':[]} for i,p in indices.items()}
    for eid,event in events.items():
        binding=bindings[eid]
        if binding['point_id'] not in points:raise ValueError('unknown return point')
        point=points[binding['point_id']];event_date=dates[event['date_ref']]['iso_date']
        if binding['timing_mode']=='exact_event_date' and event_date!=point['iso_date']:raise ValueError('event date not exact return-grid date')
        if binding['timing_mode']=='explicit_bucket_assignment' and event['period_ref']!=point['period_ref']:raise ValueError('bucket requires explicit same-calendar-period allocation; cross-period treatment unsupported')
        value,_=ledger.quantity(event['amount'],'period_total',event['period_ref'])
        row=rows[point['index']]
        if event['kind']=='equity_contribution':row['contributions']+=value;row['contribution_event_ids'].append(eid)
        else:row['distributions']+=value;row['distribution_event_ids'].append(eid)
    ordered=[rows[i] for i in range(len(rows))]
    contributions=sum((p['contributions'] for p in ordered),F(0));distributions=sum((p['distributions'] for p in ordered),F(0))
    assert contributions==F(reconciled['gross_equity_contributions']) and distributions==F(reconciled['gross_equity_distributions'])
    net=[p['distributions']-p['contributions'] for p in ordered]
    params=data['irr_parameters'];width=params['max_periodic_rate_interval_width'];root_result=irr.isolate_periodic(net,F(width['numerator'],width['denominator']),params['split_budget'])
    out=[]
    for p,n in zip(ordered,net):
        out.append(dict(p,contributions=str(p['contributions']),distributions=str(p['distributions']),net=str(n)))
    return dict(common,state='internally_reconciled_reference',ledger_reference=reconciled,periods=out,gross_contributions=str(contributions),gross_distributions=str(distributions),net_vector=[str(n) for n in net],equity_multiple=None if contributions==0 else str(distributions/contributions),equity_multiple_state='undefined_zero_contributions' if contributions==0 else 'defined_reference',periodic_irr=root_result,issues=[])

def fixture():
    l=ledger.fixture()
    points=[{'point_id':'R0','index':0,'iso_date':'2028-02-15','period_ref':'P1'},{'point_id':'R1','index':1,'iso_date':'2028-03-15','period_ref':'P2'}]
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':deepcopy(l['context']),'event_ledger':l,'return_grid':{'spacing':'calendar_months_same_day','step':1,'timing_rule_ref':'SYNTHETIC-MIDMONTH-GRID-NO-HOUSE-POLICY','points':points},'equity_event_bindings':[{'event_id':eid,'point_id':point,'timing_mode':'exact_event_date','timing_evidence_ref':'SYNTHETIC-EXPLICIT-TIMING'} for eid,point in [('A1','R0'),('A2','R1'),('DIST','R1')]],'irr_parameters':{'max_periodic_rate_interval_width':{'numerator':1,'denominator':100000},'split_budget':500}}

def positive_fixture(with_gap=False):
    x=fixture();l=x['event_ledger'];end='P3' if with_gap else 'P2'
    if with_gap:
        l['calendar']['periods'].append({'period_id':'P3','start_date':'2028-04-01','end_date':'2028-05-01'})
        l['date_bindings'].append({'date_ref':'DATE-P3','iso_date':'2028-04-15'})
        x['return_grid']['points'].append({'point_id':'R2','index':2,'iso_date':'2028-04-15','period_ref':'P3'})
    l.update(debts=[],debt_events=[],obligations=[],obligation_events=[],closing_debt_claims=[],closing_due_claims=[])
    l['cash_events']=[ledger.cash_event('START','equity_contribution','investor','free',10,'P1'),ledger.cash_event('EARN','operating_receipt','tenant','free',2,end),ledger.cash_event('END','equity_distribution','free','investor',12,end)]
    l['closing_cash_claims']=[{'account_id':a,'amount':ledger.money(0,'stock','CLOSING:'+end)} for a in ['free','restricted']]
    x['equity_event_bindings']=[{'event_id':eid,'point_id':pid,'timing_mode':'exact_event_date','timing_evidence_ref':'SYNTHETIC-TIMING'} for eid,pid in [('START','R0'),('END','R2' if with_gap else 'R1')]]
    return x

def main():
    checks=[]
    def ok(name,condition):
        assert condition,name;checks.append(name)
    def reject(name,mutate):
        x=fixture();mutate(x)
        try:build(x)
        except (ValidationError,ValueError):checks.append(name)
        else:raise AssertionError(name)
    b=fixture();before=deepcopy(b);z=build(b)
    ok('ledger_gross_flows_reconcile',z['gross_contributions']=='15' and z['gross_distributions']=='5' and z['equity_multiple']=='1/3')
    ok('simultaneous_gross_not_cancelled_for_multiple',z['periods'][1]['contributions']=='5' and z['periods'][1]['distributions']=='5' and z['net_vector']==['-10','0'])
    ok('bank_reserve_and_operating_flows_not_equity',sum(len(p['contribution_event_ids'])+len(p['distribution_event_ids']) for p in z['periods'])==3)
    ok('no_root_does_not_mean_deal_fail',z['periodic_irr']['root_classification']=='no_admissible_root' and z['decision']=='PENDING')
    ok('original_ledger_unmodified',before==b)
    ok('project_cash_not_automatically_distributed',z['ledger_reference']['cash']['restricted']=='2' and z['gross_distributions']=='5')
    x=fixture();x['event_ledger']['cash_events'].extend([ledger.cash_event('EXTRA-A','equity_contribution','investor','free',5,'P2'),ledger.cash_event('EXTRA-D','equity_distribution','free','investor',5,'P2')]);x['equity_event_bindings'].extend([{'event_id':eid,'point_id':'R1','timing_mode':'exact_event_date','timing_evidence_ref':'SYNTHETIC-GROSS-EVENT'} for eid in ['EXTRA-A','EXTRA-D']]);other=build(x)
    ok('same_net_distinct_gross_multiple',other['net_vector']==z['net_vector'] and other['equity_multiple']=='1/2' and other['equity_multiple']!=z['equity_multiple'])
    z=build(positive_fixture());root=z['periodic_irr']['roots'][0]
    ok('ledger_to_positive_periodic_irr',z['net_vector']==['-10','12'] and z['equity_multiple']=='6/5' and z['periodic_irr']['distinct_positive_discount_roots']==1)
    ok('known_return_inside_isolated_interval',root['exact_periodic_rate']=='1/5' if root['exact_periodic_rate'] is not None else F(root['periodic_rate_interval']['lower'])<=F(1,5)<F(root['periodic_rate_interval']['upper']))
    z=build(positive_fixture(True));root=z['periodic_irr']['roots'][0];a=root['discount_factor_interval']
    ok('empty_intermediate_point_preserved',z['net_vector']==['-10','0','12'] and len(z['periods'])==3 and z['periods'][1]['contribution_event_ids']==[])
    ok('zero_period_not_compressed_into_one_period_return',F(a['lower'])**2<F(5,6)<=F(a['upper'])**2)
    ok('monthly_grid_not_assumed_equal_actual_day_count',(date(2028,3,15)-date(2028,2,15)).days!=(date(2028,4,15)-date(2028,3,15)).days)
    x=positive_fixture();x['return_grid'].update(spacing='fixed_days',step=29);z=build(x)
    ok('explicit_fixed_day_grid_supported',z['periodic_irr']['distinct_positive_discount_roots']==1)
    x=fixture();x['return_grid']['points'][0]['iso_date']='2028-02-20';x['return_grid']['points'][1]['iso_date']='2028-03-20'
    for item in x['equity_event_bindings']:item['timing_mode']='explicit_bucket_assignment'
    ok('documented_same_period_bucket_supported',build(x)['gross_contributions']=='15')
    x=positive_fixture();x['irr_parameters']['split_budget']=0;z=build(x)
    ok('irr_incomplete_preserved_despite_balanced_ledger',z['state']=='internally_reconciled_reference' and z['periodic_irr']['status']=='incomplete_reference' and z['decision']=='PENDING')
    x=fixture();x['event_ledger']['closing_cash_claims'][0]['amount']=ledger.money(1,'stock','CLOSING:P2');z=build(x)
    ok('closing_discrepancy_blocks_return_calculation',z['state']=='blocked' and z['periodic_irr'] is None and z['equity_multiple'] is None and z['issues'][0]['residual']=='1')
    x=positive_fixture();l=x['event_ledger'];l['cash_events']=[ledger.cash_event('EARN','operating_receipt','tenant','free',12,'P2'),ledger.cash_event('END','equity_distribution','free','investor',12,'P2')];x['equity_event_bindings']=x['equity_event_bindings'][1:];z=build(x)
    ok('zero_contributions_multiple_undefined',z['equity_multiple'] is None and z['equity_multiple_state']=='undefined_zero_contributions')
    x=positive_fixture();x['event_ledger']['cash_events']=[];x['equity_event_bindings']=[];z=build(x)
    ok('all_zero_net_is_indeterminate',z['periodic_irr']['status']=='indeterminate' and z['net_vector']==['0','0'])
    mutations=[
        ('mixed_context',lambda x:x['context'].update(run_id='OTHER')),
        ('duplicate_return_point',lambda x:x['return_grid']['points'].append(deepcopy(x['return_grid']['points'][0]))),
        ('duplicate_return_index',lambda x:x['return_grid']['points'][1].update(index=0)),
        ('missing_zero_index',lambda x:x['return_grid']['points'][0].update(index=2)),
        ('skipped_return_index',lambda x:x['return_grid']['points'][1].update(index=3)),
        ('irregular_month_grid',lambda x:x['return_grid']['points'][1].update(iso_date='2028-03-16')),
        ('month_end_not_clamped',lambda x:(x['return_grid']['points'][0].update(iso_date='2028-02-29'),x['return_grid']['points'][1].update(iso_date='2028-03-28'))),
        ('wrong_fixed_day_spacing',lambda x:x['return_grid'].update(spacing='fixed_days',step=30)),
        ('wrong_point_period',lambda x:x['return_grid']['points'][1].update(period_ref='P1')),
        ('unbound_equity_event',lambda x:x['equity_event_bindings'].pop()),
        ('no_base_fallback_when_bindings_empty',lambda x:x.update(equity_event_bindings=[])),
        ('duplicate_equity_binding',lambda x:x['equity_event_bindings'].append(deepcopy(x['equity_event_bindings'][0]))),
        ('bank_draw_not_investor_contribution',lambda x:x['equity_event_bindings'].append({'event_id':'DRAW','point_id':'R0','timing_mode':'exact_event_date','timing_evidence_ref':'SYNTHETIC'})),
        ('unknown_point_binding',lambda x:x['equity_event_bindings'][0].update(point_id='ABSENT')),
        ('no_implicit_timing_policy',lambda x:x['return_grid'].pop('timing_rule_ref')),
        ('no_implicit_event_assignment',lambda x:x['equity_event_bindings'][0].pop('timing_mode')),
        ('empty_timing_evidence',lambda x:x['equity_event_bindings'][0].update(timing_evidence_ref='')),
        ('cross_period_bucket_unsupported',lambda x:x['equity_event_bindings'][0].update(point_id='R1',timing_mode='explicit_bucket_assignment')),
        ('exact_date_mismatch',lambda x:x['equity_event_bindings'][0].update(point_id='R1')),
        ('negative_cash_event',lambda x:x['event_ledger']['cash_events'][0]['amount']['value'].update(numerator=-1)),
        ('missing_equity_not_zero',lambda x:x['event_ledger']['cash_events'][0].update(amount={'state':'missing','causes':[{'field_id':'equity','cause_kind':'missing','reason':'Not supplied'}]})),
        ('currency_mismatch',lambda x:x['event_ledger']['cash_events'][0]['amount'].update(currency='OTHER')),
        ('no_default_irr_parameters',lambda x:x.pop('irr_parameters')),
        ('invalid_rate_width',lambda x:x['irr_parameters']['max_periodic_rate_interval_width'].update(denominator=0)),
        ('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(ledger.STORE),'synthetic_examples':{'existing_ledger':build(fixture()),'positive_return_with_zero_period':build(positive_fixture(True))},'scope':'Explicit synthetic aggregate-equity event/grid/gross-multiple/periodic-root bridge only. Not ledger completeness, real-deal economics, terminal valuation, LP/JV waterfall, automatic timing/annualization, XIRR, root-selection policy, expert review or production.'}
    (ROOT/'references/fixtures/investor-return-bridge-synthetic.json').write_text(json.dumps(fixture(),indent=2)+'\n')
    (ROOT/'references/investor-return-bridge-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
