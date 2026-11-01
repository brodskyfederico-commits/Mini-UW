"""Explicit periodic/annualized interval-to-condition reference; never a deal PASS/FAIL."""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_calendar_ledger as vocabulary
import validate_investor_return_bridge as bridge
ROOT=Path(__file__).resolve().parents[1]

def interval_relation(lo,hi,lc,uc,threshold,op):
    if any(type(v) not in (int,F) for v in [lo,hi,threshold]) or type(lc) is not bool or type(uc) is not bool:raise ValueError('exact rational bounds and explicit closures required')
    if lo>hi or (lo==hi and not (lc and uc)):raise ValueError('empty interval')
    if op=='>=':
        return True if lo>=threshold else False if hi<threshold or (hi==threshold and not uc) else None
    if op=='>':
        return True if lo>threshold or (lo==threshold and not lc) else False if hi<=threshold else None
    if op=='<=':
        return True if hi<=threshold else False if lo>threshold or (lo==threshold and not lc) else None
    if op=='<':
        return True if hi<threshold or (hi==threshold and not uc) else False if lo>=threshold else None
    raise ValueError('explicit supported operator required')

def compound(lo,hi,lc,uc,periods_per_year):
    if type(periods_per_year) is not int or periods_per_year<=0 or lo<=-1 or hi<=-1:raise ValueError('explicit positive exponent and r > -1 required')
    return ((1+lo)**periods_per_year-1,(1+hi)**periods_per_year-1,lc,uc)

def evaluate(data):
    vocabulary.schema_check('return-metric-bridge',data)
    c=data['criterion'];spec=data['metric_contract'];source=data['investor_return_bridge']
    if c['context']!=data['context'] or source['context']!=data['context']:raise ValueError('comparison context mismatch')
    if spec['metric_id']!=c['metric_id'] or spec['definition_ref']!=c['metric_definition_ref']:raise ValueError('metric/definition mismatch')
    base={'decision':'PENDING','publication_authorized':False,'condition_role':c['condition_role'],'condition_satisfied':None,'metric_frequency':spec['frequency']}
    if c['applicability']!='applicable':return dict(base,state='pending_reference',reason='criterion applicability requires separate treatment',original_criterion=deepcopy(c))
    q=c['threshold']
    if q['state']!='known':return dict(base,state='pending_reference',reason='threshold unresolved',original_threshold=deepcopy(q))
    if q['dimensions']!={'money':0,'area':0,'unit':0,'space':0,'time':0} or q['measurement_role']!='ratio' or q['currency'] is not None:raise ValueError('effective-return criterion needs dimensionless ratio, not money/rate-per-time')
    if (q['unit_id'],q['basis'],q['period_ref'])!=(spec['unit_id'],spec['basis'],spec['period_ref']):raise ValueError('criterion unit/basis/horizon mismatch')
    t=F(q['value']['numerator'],q['value']['denominator']);z=bridge.build(source)
    if z['state']=='blocked':return dict(base,state='pending_reference',reason='underlying ledger blocked',source_reference=z)
    roots=z['periodic_irr']
    if roots['status']!='complete_reference':return dict(base,state='pending_reference',reason='root isolation indeterminate/incomplete',source_reference=z)
    if roots['distinct_positive_discount_roots']!=1:return dict(base,state='pending_reference',reason='no unique admissible root; no selection policy applied',source_reference=z)
    item=roots['roots'][0]
    if item['exact_periodic_rate'] is not None:lo=hi=F(item['exact_periodic_rate']);lc=uc=True
    else:
        i=item['periodic_rate_interval'];lo=F(i['lower']);hi=F(i['upper']);lc=i['lower_closed'];uc=i['upper_closed']
    if spec['frequency']=='annual':
        m=spec['periods_per_year'];rule=spec['annualization_rule_ref'];grid=source['return_grid']
        if m is None or not rule:return dict(base,state='pending_reference',reason='annualization frequency/rule missing')
        if grid['spacing']!='calendar_months_same_day':return dict(base,state='pending_reference',reason='day-grid annualization needs separate explicit year convention')
        if grid['step']*m!=12:raise ValueError('annualization exponent inconsistent with explicit calendar-month step')
        lo,hi,lc,uc=compound(lo,hi,lc,uc,m)
    elif spec['periods_per_year'] is not None or spec['annualization_rule_ref'] is not None:raise ValueError('periodic metric cannot silently consume annualization configuration')
    relation=interval_relation(lo,hi,lc,uc,t,c['operator'])
    return dict(base,state='condition_relation_reference' if relation is not None else 'pending_refinement',condition_satisfied=relation,reason='all values in interval have same criterion relation' if relation is not None else 'threshold intersects current enclosure; refine or retain pending',compared_interval={'lower':str(lo),'upper':str(hi),'lower_closed':lc,'upper_closed':uc},threshold=str(t),operator=c['operator'],source_reference=z)

def fixture():
    b=bridge.positive_fixture();ctx=deepcopy(b['context']);q={'state':'known','value':{'numerator':1,'denominator':10},'dimensions':{'money':0,'area':0,'unit':0,'space':0,'time':0},'unit_id':'SYNTHETIC-EFFECTIVE-RETURN','currency':None,'measurement_role':'ratio','basis':'SYNTHETIC-PROJECT-EQUITY-PERIODIC','period_ref':'SYNTHETIC-HORIZON','sources':[vocabulary.src()]}
    c={'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':deepcopy(ctx),'criterion_id':'SYNTHETIC-ONLY','metric_id':'SYNTHETIC-IRR','metric_definition_ref':'SYNTHETIC-METRIC-DEFINITION','condition_role':'pass_condition','operator':'>=','threshold':q,'applicability':'applicable','applicability_reason':None,'applicability_rule_ref':None,'aggregation_rule_ref':None,'sources':[vocabulary.src()]}
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':ctx,'investor_return_bridge':b,'criterion':c,'metric_contract':{'metric_id':c['metric_id'],'definition_ref':c['metric_definition_ref'],'unit_id':q['unit_id'],'basis':q['basis'],'period_ref':q['period_ref'],'frequency':'periodic','periods_per_year':None,'annualization_rule_ref':None}}

def main():
    checks=[]
    def ok(name,condition):
        assert condition,name;checks.append(name)
    def reject(name,mutation):
        x=fixture();mutation(x)
        try:evaluate(x)
        except (ValueError,ValidationError):checks.append(name)
        else:raise AssertionError(name)
    # Exhaustive small rational endpoint/closure truth tables, independent by explicit
    # witness points representing endpoints and every threshold-separated interior region.
    operations={'>=':lambda v,t:v>=t,'>':lambda v,t:v>t,'<=':lambda v,t:v<=t,'<':lambda v,t:v<t}
    n=0
    for lo,hi in [(F(-1,2),F(0)),(F(0),F(1,2)),(F(1,5),F(1,5))]:
        for lc in [False,True]:
            for uc in [False,True]:
                if lo==hi and not(lc and uc):continue
                for t in [lo-1,lo,(lo+hi)/2,hi,hi+1]:
                    cuts=sorted({lo,hi,t} & {v for v in [lo,hi,t] if lo<=v<=hi})
                    witnesses=[v for v in cuts if (v>lo or lc) and (v<hi or uc)]
                    witnesses += [(a+b)/2 for a,b in zip(cuts,cuts[1:]) if a<b]
                    for op,fn in operations.items():
                        results={fn(v,t) for v in witnesses};expected=next(iter(results)) if len(results)==1 else None
                        assert interval_relation(lo,hi,lc,uc,t,op)==expected;n+=1
    ok('all_endpoint_and_open_closed_truth_tables',n==180)
    b=fixture();old=deepcopy(b);z=evaluate(b)
    ok('linked_periodic_condition_true_without_deal_pass',z['condition_satisfied'] is True and z['decision']=='PENDING' and not z['publication_authorized'])
    ok('source_inputs_unchanged',old==b)
    x=fixture();x['criterion']['threshold']['value']={'numerator':3,'denominator':10};z=evaluate(x)
    ok('condition_false_not_whole_deal_fail',z['condition_satisfied'] is False and z['decision']=='PENDING')
    x=fixture();root=z['source_reference']['periodic_irr']['roots'][0];i=root['periodic_rate_interval'];mid=(F(i['lower'])+F(i['upper']))/2;x['criterion']['threshold']['value']={'numerator':mid.numerator,'denominator':mid.denominator};z=evaluate(x)
    ok('intersected_interval_remains_pending_no_midpoint_guess',z['state']=='pending_refinement' and z['condition_satisfied'] is None)
    x=fixture();x['metric_contract'].update(frequency='annual',periods_per_year=12,annualization_rule_ref='SYNTHETIC-EXPLICIT-COMPOUNDING');x['metric_contract']['basis']='SYNTHETIC-PROJECT-EQUITY-ANNUAL';x['criterion']['threshold']['basis']=x['metric_contract']['basis'];z=evaluate(x)
    ok('explicit_monthly_to_annual_compounding',z['condition_satisfied'] is True and F(z['compared_interval']['lower'])<=(F(6,5)**12-1)<F(z['compared_interval']['upper']))
    ok('annualization_is_not_rate_times_twelve',F(6,5)**12-1!=F(1,5)*12)
    x=fixture();x['metric_contract']['frequency']='annual';z=evaluate(x)
    ok('missing_annualization_convention_pending',z['state']=='pending_reference' and z['condition_satisfied'] is None)
    x=fixture();x['investor_return_bridge']['return_grid'].update(spacing='fixed_days',step=29);x['metric_contract'].update(frequency='annual',periods_per_year=12,annualization_rule_ref='SYNTHETIC');z=evaluate(x)
    ok('day_grid_does_not_invent_365_year',z['state']=='pending_reference' and 'year convention' in z['reason'])
    x=fixture();x['investor_return_bridge']['irr_parameters']['split_budget']=0;z=evaluate(x)
    ok('incomplete_isolation_cannot_compare',z['state']=='pending_reference' and z['condition_satisfied'] is None)
    x=fixture();x['investor_return_bridge']=bridge.fixture();z=evaluate(x)
    ok('no_root_is_not_false_condition',z['state']=='pending_reference' and z['condition_satisfied'] is None)
    x=fixture();b2=bridge.positive_fixture(True);l=b2['event_ledger'];l['cash_events']=[vocabulary.cash_event('A0','equity_contribution','investor','free',100,'P1'),vocabulary.cash_event('USE0','operating_payment','free','vendor',100,'P1'),vocabulary.cash_event('EARN1','operating_receipt','tenant','free',230,'P2'),vocabulary.cash_event('D1','equity_distribution','free','investor',230,'P2'),vocabulary.cash_event('A2','equity_contribution','investor','free',132,'P3'),vocabulary.cash_event('USE2','operating_payment','free','vendor',132,'P3')];b2['equity_event_bindings']=[{'event_id':eid,'point_id':pid,'timing_mode':'exact_event_date','timing_evidence_ref':'SYNTHETIC-MULTIPLE-ROOTS'} for eid,pid in [('A0','R0'),('D1','R1'),('A2','R2')]];x['investor_return_bridge']=b2;z=evaluate(x)
    ok('multiple_ledger_irr_roots_do_not_choose_favorable_rate',z['state']=='pending_reference' and z['condition_satisfied'] is None and z['source_reference']['periodic_irr']['distinct_positive_discount_roots']==2)
    x=fixture();x['criterion']['threshold']={'state':'missing','causes':[{'field_id':'threshold','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('missing_threshold_preserves_cause',z['original_threshold']['causes'][0]['reason']=='Not supplied' and z['condition_satisfied'] is None)
    x=fixture();x['criterion']['applicability']='unresolved';z=evaluate(x)
    ok('unknown_applicability_not_silent_exclusion',z['state']=='pending_reference' and 'original_criterion' in z)
    for op,t,expected in [('>=',F(1,5),True),('>',F(1,5),False),('<=',F(1,5),True),('<',F(1,5),False)]:
        ok('exact_equal_'+op,interval_relation(F(1,5),F(1,5),True,True,t,op) is expected)
    lo,hi,lc,uc=compound(F(-1,10),F(1,10),False,True,12)
    ok('monotonic_annualization_preserves_closures_and_negative_rates',lo==F(9,10)**12-1 and hi==F(11,10)**12-1 and not lc and uc)
    mutations=[('metric_definition_mismatch',lambda x:x['metric_contract'].update(definition_ref='OTHER')),('metric_id_mismatch',lambda x:x['metric_contract'].update(metric_id='OTHER')),('context_mismatch',lambda x:x['criterion']['context'].update(run_id='OTHER')),('unit_mismatch',lambda x:x['criterion']['threshold'].update(unit_id='OTHER')),('basis_mismatch',lambda x:x['criterion']['threshold'].update(basis='OTHER')),('horizon_mismatch',lambda x:x['criterion']['threshold'].update(period_ref='OTHER')),('not_dimensionless',lambda x:x['criterion']['threshold']['dimensions'].update(time=-1)),('monetary_threshold_not_return',lambda x:x['criterion']['threshold'].update(currency='SYNTHETIC-MONEY')),('wrong_measurement_role',lambda x:x['criterion']['threshold'].update(measurement_role='unit_rate')),('wrong_annualization_exponent',lambda x:x['metric_contract'].update(frequency='annual',periods_per_year=2,annualization_rule_ref='SYNTHETIC')),('no_unused_annualization_config',lambda x:x['metric_contract'].update(periods_per_year=12)),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    report={'status':'passed','total':len(checks),'checks':checks,'endpoint_truth_table_cases':n,'schemas_checked':len(vocabulary.STORE),'synthetic_example':evaluate(b),'scope':'Synthetic ledger-to-IRR interval/condition and declared calendar-month compounding only. Not root-selection/aggregation policy, threshold authority, actual frequency approval, XIRR, financial audit, publication or real-deal PASS/FAIL.'}
    (ROOT/'references/return-metric-bridge-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'endpoint_truth_table_cases':n}))

if __name__=='__main__':main()
