"""Declared trial-input isolation and signed measured-metric ranking. No financial engine."""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_calendar_ledger as vocabulary
ROOT=Path(__file__).resolve().parents[1]

def signature(q):
    return (tuple(sorted(q['dimensions'].items())),q['unit_id'],q['currency'],q['measurement_role'],q['basis'],q['period_ref'])

def value(q):
    return F(q['value']['numerator'],q['value']['denominator'])

def evaluate(data):
    vocabulary.schema_check('sensitivity-ranking',data)
    baseline=vocabulary.unique(data['baseline_bindings'],'field_id');drivers=vocabulary.unique(data['drivers'],'driver_id');trials=vocabulary.unique(data['trials'],'trial_id')
    if set(trials)!=set(data['expected_trial_ids']):raise ValueError('trial inventory incomplete/unknown')
    for driver in drivers.values():
        if not set(driver['permitted_target_field_ids'])<=set(baseline):raise ValueError('driver targets unknown baseline field')
    issues=[];single=[];joint=[];base=data['baseline_metric']
    if base['state']!='known':issues.append({'cause':'baseline metric unresolved','original_claim':deepcopy(base)})
    for id,trial in trials.items():
        expected=dict(data['context'],scenario_id=id)
        if trial['context']!=expected:raise ValueError('trial context mismatch')
        if trial['metric_definition_ref']!=data['metric_definition_ref']:raise ValueError('ranking metric definition changed')
        selected=set(trial['driver_ids'])
        if not selected<=set(drivers):raise ValueError('unknown configured driver')
        if (trial['experiment_kind']=='single_driver' and len(selected)!=1) or (trial['experiment_kind']=='joint' and len(selected)<2):raise ValueError('experiment kind/driver count mismatch')
        permitted=set().union(*(set(drivers[d]['permitted_target_field_ids']) for d in selected));target=set(trial['target_field_ids']);unchanged=set(trial['unchanged_field_ids'])
        if not target<=permitted or target&unchanged or target|unchanged!=set(baseline):raise ValueError('explicit target/unchanged partition invalid')
        bindings=vocabulary.unique(trial['input_bindings'],'field_id')
        if set(bindings)!=set(baseline):raise ValueError('missing trial input cannot inherit Base')
        local=[]
        for field in baseline:
            before=baseline[field]['quantity'];after=bindings[field]['quantity']
            if field in unchanged and before!=after:raise ValueError('undeclared input/provenance change in single/joint trial')
            for origin,q in [('baseline',before),('trial',after)]:
                if q['state']!='known':local.append({'cause':'input unresolved','field_id':field,'origin':origin,'original_claim':deepcopy(q)})
            if before['state']=='known' and after['state']=='known' and signature(before)!=signature(after):raise ValueError('shock changes unit/base/period without explicit conversion contract')
        metric=trial['metric_value'];delta=None
        if metric['state']!='known':local.append({'cause':'trial metric unresolved','original_claim':deepcopy(metric)})
        if base['state']=='known' and metric['state']=='known':
            if signature(base)!=signature(metric):raise ValueError('ranking metrics not comparable')
            if not local:delta=value(metric)-value(base)
        if local:issues.append({'trial_id':id,'causes':local})
        row={'trial_id':id,'driver_ids':list(trial['driver_ids']),'signed_delta':None if delta is None else str(delta),'original_metric':deepcopy(metric),'state':'measured_relation_reference' if delta is not None else 'unresolved'}
        (single if trial['experiment_kind']=='single_driver' else joint).append(row)
    if not single:issues.append({'cause':'no single-driver experiments; no individual-driver ranking'})
    ranking=[]
    complete=not issues and all(r['signed_delta'] is not None for r in single)
    if complete:
        distinct=sorted({F(r['signed_delta']) for r in single},reverse=data['ranking_direction']=='larger_signed_delta_first')
        ranking=[{'dense_rank':i+1,'signed_delta':str(delta),'trial_ids':sorted(r['trial_id'] for r in single if F(r['signed_delta'])==delta)} for i,delta in enumerate(distinct)]
    return {'state':'complete_declared_ranking_reference' if complete else 'pending_reference','decision':'PENDING','publication_authorized':False,'ranking':ranking,'single_driver_diagnostics':single,'joint_diagnostics':joint,'issues':issues,'all_single_trials_tied':bool(ranking) and len(ranking)==1,'financial_reexecution_verified':False,'joint_result_inferred_from_singles':False}

def fixture():
    ctx=deepcopy(vocabulary.CTX);ctx['scenario_id']='sensitivity-aggregate'
    def q(n):return vocabulary.money(n,'period_total','SYNTHETIC-RANKING-PERIOD')
    inputs=[{'field_id':'rent','quantity':q(10)},{'field_id':'expense','quantity':q(5)}]
    drivers=[{'driver_id':id,'permitted_target_field_ids':[field],'definition_ref':'SYNTHETIC-DRIVER-DEFINITION'} for id,field in [('rent','rent'),('expense','expense'),('zero','rent')]]
    trials=[]
    for id,kind,ds,changes,measured in [('rent-trial','single_driver',['rent'],{'rent':12},110),('expense-trial','single_driver',['expense'],{'expense':6},90),('zero-trial','single_driver',['zero'],{'rent':10},100),('joint-trial','joint',['rent','expense'],{'rent':12,'expense':6},120)]:
        bindings=deepcopy(inputs)
        for b in bindings:
            if b['field_id'] in changes:b['quantity']=q(changes[b['field_id']])
        trials.append({'trial_id':id,'context':dict(ctx,scenario_id=id),'experiment_kind':kind,'driver_ids':ds,'target_field_ids':list(changes),'unchanged_field_ids':[b['field_id'] for b in inputs if b['field_id'] not in changes],'input_bindings':bindings,'metric_definition_ref':'SYNTHETIC-METRIC-v1','metric_value':q(measured),'experiment_evidence_ref':'SYNTHETIC-MEASUREMENTS-NOT-CALCULATED-PRODUCT'})
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':ctx,'metric_id':'SYNTHETIC-SIGNED-METRIC','metric_definition_ref':'SYNTHETIC-METRIC-v1','ranking_direction':'larger_signed_delta_first','tie_policy':'shared_dense_ranks','ranking_rule_ref':'SYNTHETIC-NOT-AUTHENTICATED-RANKING-RULE','baseline_bindings':inputs,'baseline_metric':q(100),'drivers':drivers,'expected_trial_ids':[t['trial_id'] for t in trials],'trials':trials}

def main():
    checks=[]
    def ok(name,c):
        assert c,name;checks.append(name)
    def reject(name,mutate):
        x=fixture();mutate(x)
        try:evaluate(x)
        except (ValueError,ValidationError):checks.append(name)
        else:raise AssertionError(name)
    b=fixture();old=deepcopy(b);z=evaluate(b)
    ok('signed_direction_preserved_not_absolute_delta',[r['signed_delta'] for r in z['ranking']]==['10','0','-10'])
    ok('joint_result_not_ranked_as_individual',all('joint-trial' not in r['trial_ids'] for r in z['ranking']) and z['joint_diagnostics'][0]['signed_delta']=='20')
    ok('joint_result_not_sum_of_individual_changes',F(z['joint_diagnostics'][0]['signed_delta'])!=sum(F(r['signed_delta']) for r in z['single_driver_diagnostics']))
    ok('no_financial_reexecution_or_decision_claim',z['decision']=='PENDING' and not z['financial_reexecution_verified'] and not z['publication_authorized'] and not z['joint_result_inferred_from_singles'])
    ok('original_packets_unchanged',b==old)
    x=fixture();x['ranking_direction']='smaller_signed_delta_first';z=evaluate(x)
    ok('opposite_direction_requires_explicit_rule',[r['signed_delta'] for r in z['ranking']]==['-10','0','10'])
    x=fixture();x['trials'][1]['metric_value']=deepcopy(x['trials'][0]['metric_value']);z=evaluate(x)
    ok('ties_share_dense_rank_without_arbitrary_top_driver',z['ranking'][0]['trial_ids']==['expense-trial','rent-trial'] and z['ranking'][1]['dense_rank']==2)
    x=fixture()
    for t in x['trials']:t['metric_value']=deepcopy(x['baseline_metric'])
    z=evaluate(x);ok('all_zero_changes_keep_metric_and_full_tie',z['all_single_trials_tied'] and len(z['ranking'])==1 and len(z['ranking'][0]['trial_ids'])==3 and z['ranking'][0]['signed_delta']=='0')
    x=fixture();x['trials'][0]['metric_value']={'state':'missing','causes':[{'field_id':'trial metric','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('missing_trial_not_dropped_from_ranking',z['state']=='pending_reference' and z['ranking']==[] and len(z['single_driver_diagnostics'])==3 and z['issues'][0]['causes'][0]['original_claim']['causes'][0]['reason']=='Not supplied')
    x=fixture();x['baseline_metric']={'state':'missing','causes':[{'field_id':'baseline','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('missing_baseline_not_assumed_zero',z['state']=='pending_reference' and z['ranking']==[] and all(r['signed_delta'] is None for r in z['single_driver_diagnostics']))
    x=fixture();x['trials'][0]['input_bindings'][0]['quantity']={'state':'missing','causes':[{'field_id':'rent','cause_kind':'missing','reason':'No shock supplied'}]};z=evaluate(x)
    ok('known_metric_does_not_erase_unknown_shocked_input',z['state']=='pending_reference' and z['single_driver_diagnostics'][0]['signed_delta'] is None)
    x=fixture();x['trials']=x['trials'][-1:];x['expected_trial_ids']=['joint-trial'];z=evaluate(x)
    ok('joint_only_cannot_generate_individual_ranking',z['state']=='pending_reference' and z['ranking']==[])
    mutations=[('trial_context_mismatch',lambda x:x['trials'][0]['context'].update(run_id='OTHER')),('trial_scenario_context_not_base_fallback',lambda x:x['trials'][0]['context'].update(scenario_id='Base')),('metric_definition_mismatch',lambda x:x['trials'][0].update(metric_definition_ref='OTHER')),('metric_currency_mismatch',lambda x:x['trials'][0]['metric_value'].update(currency='OTHER')),('metric_period_mismatch',lambda x:x['trials'][0]['metric_value'].update(period_ref='OTHER')),('metric_basis_mismatch',lambda x:x['trials'][0]['metric_value'].update(basis='OTHER')),('unknown_driver',lambda x:x['trials'][0].update(driver_ids=['UNKNOWN'])),('single_driver_cannot_hide_two_drivers',lambda x:x['trials'][0].update(driver_ids=['rent','expense'])),('joint_needs_multiple_drivers',lambda x:x['trials'][-1].update(driver_ids=['rent'])),('target_outside_driver_definition',lambda x:x['trials'][0].update(target_field_ids=['expense'],unchanged_field_ids=['rent'])),('unchanged_input_altered',lambda x:x['trials'][0]['input_bindings'][1]['quantity']['value'].update(numerator=99)),('missing_unchanged_binding_not_inherited',lambda x:x['trials'][0]['input_bindings'].pop()),('duplicate_input_binding',lambda x:x['trials'][0]['input_bindings'].append(deepcopy(x['trials'][0]['input_bindings'][0]))),('target_unchanged_overlap',lambda x:x['trials'][0]['unchanged_field_ids'].append('rent')),('unclassified_input_field',lambda x:x['trials'][0].update(unchanged_field_ids=[])),('shock_unit_changed',lambda x:x['trials'][0]['input_bindings'][0]['quantity'].update(unit_id='OTHER')),('missing_trial_record',lambda x:x['trials'].pop()),('duplicate_trial_id',lambda x:x['trials'].append(deepcopy(x['trials'][0]))),('no_default_direction',lambda x:x.pop('ranking_direction')),('no_empty_evidence',lambda x:x['trials'][0].update(experiment_evidence_ref='')),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(vocabulary.STORE),'synthetic_example':evaluate(b),'scope':'Declared synthetic numeric-input preservation, compatible measured-metric signed deltas, explicit direction/ties and separation of joint experiments only. Not actual perturbation generation, financial recomputation, authenticated ranking policy, causal/probabilistic inference, real-deal screening, independent audit or production.'}
    (ROOT/'references/sensitivity-ranking-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'references/fixtures/sensitivity-ranking-synthetic.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
