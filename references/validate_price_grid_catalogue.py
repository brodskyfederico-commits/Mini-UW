"""Exact finite-grid enumeration of declared normalized-polynomial conditions; no financial engine."""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_calendar_ledger as vocabulary
ROOT=Path(__file__).resolve().parents[1]

def relation(value,op):
    if op=='>=':return value>=0
    if op=='>':return value>0
    if op=='<=':return value<=0
    if op=='<':return value<0
    raise ValueError('explicit operator required')

def evaluate(data):
    vocabulary.schema_check('price-grid-catalogue',data)
    common={'decision':'PENDING','publication_authorized':False,'financial_model_certified':False,'global_continuous_optimum_claimed':False}
    domain=data['domain'];signature=None;values={};issues=[]
    for key in ['lower','upper','anchor','increment','normalizing_price_unit']:
        q=domain[key]
        if q['state']!='known':issues.append({'cause':'price domain unresolved','field':key,'original_claim':deepcopy(q)});continue
        v,signature=vocabulary.quantity(q,'stock','PRICE-DOMAIN',signature);values[key]=v
    if issues:return dict(common,classification='indeterminate_reference',issues=issues,points=[],domain_grid_point_count=None,best_known_grid_candidate=None)
    lower=values['lower'];upper=values['upper'];step=values['increment'];anchor=values['anchor'];scale=values['normalizing_price_unit']
    if lower>upper or step<=0 or scale<=0:raise ValueError('ordered finite bounds, positive increment and normalization required')
    a=(lower-anchor)/step;b=(upper-anchor)/step
    first=-((-a.numerator)//a.denominator);last=b.numerator//b.denominator
    if not domain['lower_closed'] and anchor+first*step==lower:first+=1
    if not domain['upper_closed'] and anchor+last*step==upper:last-=1
    n=max(0,last-first+1)
    scenarios=vocabulary.unique(data['scenarios'],'scenario_id')
    if set(scenarios)!=set(data['expected_scenario_ids']):raise ValueError('scenario inventory missing/unknown')
    required=[];unresolved_inventory=False;unresolved_constraints=False
    def defined(c):return c['state']=='defined_claim' and c['operator'] is not None and c['coefficients'] is not None and all(c[k] for k in ['criterion_revision','normalized_relation_definition_ref','evidence_ref'])
    for sid,s in scenarios.items():
        expected=dict(data['context'],scenario_id=sid)
        if s['context']!=expected:raise ValueError('scenario deal/run/revision/context mismatch')
        constraints=vocabulary.unique(s['constraints'],'constraint_id')
        if set(constraints)!=set(s['required_constraint_ids']):raise ValueError('constraint inventory missing/unknown')
        for constraint in constraints.values():
            if constraint['state']=='conflict' and len(constraint['original_claims'])<2:raise ValueError('conflict must preserve alternate claims')
        if s['required_status']=='excluded':
            if not all(s[k] for k in ['exclusion_reason','exclusion_rule_ref','scenario_evidence_ref']):raise ValueError('exclusion requires explicit reason/rule/evidence')
            continue
        if s['required_status']!='required' or not s['scenario_evidence_ref']:
            unresolved_inventory=True;issues.append({'cause':'scenario requirement/evidence unresolved','scenario_id':sid,'original_claim':deepcopy(s)})
        for c in constraints.values():
            if not defined(c):
                unresolved_constraints=True;issues.append({'cause':'required relation unresolved','scenario_id':sid,'constraint_id':c['constraint_id'],'original_claim':deepcopy(c)})
        required.append(s)
    if not required:unresolved_inventory=True;issues.append({'cause':'no required scenarios; no vacuous support classification'})
    points=[];best=None;unknown=unresolved_constraints
    for offset in range(min(n,data['evaluation_budget_points'])):
        index=first+offset;price=anchor+index*step;x=price/scale;point_unknown=unresolved_inventory;conditions=[]
        for scenario in required:
            for c in scenario['constraints']:
                known=defined(c)
                if not known:
                    point_unknown=True;conditions.append({'scenario_id':scenario['scenario_id'],'constraint_id':c['constraint_id'],'state':'unresolved','condition_satisfied':None,'original_claim':deepcopy(c)});continue
                polynomial=F(0)
                for coefficient in reversed(c['coefficients']):polynomial=polynomial*x+F(coefficient['numerator'],coefficient['denominator'])
                conditions.append({'scenario_id':scenario['scenario_id'],'constraint_id':c['constraint_id'],'state':'evaluated_declared_relation','polynomial_value':str(polynomial),'operator':c['operator'],'condition_satisfied':relation(polynomial,c['operator']),'criterion_revision':c['criterion_revision']})
        known_true=not point_unknown and bool(conditions) and all(c['condition_satisfied'] is True for c in conditions)
        state='indeterminate' if point_unknown else 'all_declared_conditions_satisfied' if known_true else 'declared_condition_not_satisfied'
        points.append({'grid_index':index,'price':str(price),'normalized_price':str(x),'state':state,'conditions':conditions})
        if known_true:best=price
        unknown|=point_unknown
    incomplete=len(points)!=n
    if incomplete or unknown or unresolved_inventory:classification='indeterminate_reference'
    elif best is None:classification='empty_declared_grid_reference'
    else:classification='maximum_attained_in_declared_grid_reference'
    return dict(common,classification=classification,issues=issues,domain_grid_point_count=n,evaluated_grid_point_count=len(points),unvisited_grid_point_count=n-len(points),complete_declared_domain_coverage=not incomplete,all_required_relations_resolved=not (unknown or unresolved_inventory),best_known_grid_candidate=None if best is None else str(best),maximum_price=None if classification!='maximum_attained_in_declared_grid_reference' else str(best),points=points,currency=signature[0],unit_id=signature[1],price_basis=signature[2],scope='Only the explicitly supplied normalized-polynomial relations and finite grid; no derived real-deal model or RLV approval.')

def constraint(id,coefficients,op='>='):
    return {'constraint_id':id,'state':'defined_claim','criterion_revision':'SYNTHETIC-CRITERIA-v1','normalized_relation_definition_ref':'SYNTHETIC-POLYNOMIAL-NOT-REAL-MODEL','operator':op,'coefficients':[{'numerator':F(c).numerator,'denominator':F(c).denominator} for c in coefficients],'evidence_ref':'SYNTHETIC-ONLY','original_claims':[]}

def money(n):return vocabulary.money(n,'stock','PRICE-DOMAIN')

def fixture():
    ctx=deepcopy(vocabulary.CTX);ctx['scenario_id']='explicit-grid-aggregate'
    scenarios=[]
    for sid,c in [('Base',constraint('nonmonotone',[3,-4,1])),('Downside',constraint('upper-limit',[-2,1],'<='))]:
        scenarios.append({'scenario_id':sid,'context':dict(ctx,scenario_id=sid),'required_status':'required','exclusion_reason':None,'exclusion_rule_ref':None,'scenario_evidence_ref':'SYNTHETIC-EXPLICIT-SCENARIO','required_constraint_ids':[c['constraint_id']],'constraints':[c]})
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':ctx,'scope_definition_ref':'SYNTHETIC-FINITE-CATALOGUE-NOT-RLV','domain':{'kind':'finite_uniform_grid','lower':money(0),'upper':money(4),'lower_closed':True,'upper_closed':True,'anchor':money(0),'increment':money(1),'normalizing_price_unit':money(1),'domain_evidence_ref':'SYNTHETIC-NOT-APPROVED-QUOTE-GRID'},'expected_scenario_ids':['Base','Downside'],'scenarios':scenarios,'evaluation_budget_points':10}

def main():
    checks=[]
    def ok(name,c):
        assert c,name;checks.append(name)
    def reject(name,mutate):
        x=fixture();mutate(x)
        try:evaluate(x)
        except (ValueError,ValidationError):checks.append(name)
        else:raise AssertionError(name)
    b=fixture();before=deepcopy(b);z=evaluate(b)
    ok('required_scenario_intersection_over_full_grid',z['maximum_price']=='1' and z['domain_grid_point_count']==5 and z['complete_declared_domain_coverage'])
    ok('base_alone_not_used_for_downside',z['points'][3]['conditions'][0]['condition_satisfied'] is True and z['points'][3]['conditions'][1]['condition_satisfied'] is False)
    ok('no_scenario_or_criterion_mutation',b==before)
    ok('maximum_not_underwriting_pass_or_continuous_optimum',z['decision']=='PENDING' and not z['publication_authorized'] and not z['financial_model_certified'] and not z['global_continuous_optimum_claimed'])
    x=fixture();x['scenarios'][1].update(required_status='excluded',exclusion_reason='SYNTHETIC-SCOPE-ONLY',exclusion_rule_ref='SYNTHETIC-RULE');z=evaluate(x)
    ok('nonmonotone_grid_does_not_stop_at_first_frontier',z['maximum_price']=='4' and [p['price'] for p in z['points'] if p['state']=='all_declared_conditions_satisfied']==['0','1','3','4'])
    x=fixture();x['evaluation_budget_points']=2;z=evaluate(x)
    ok('partial_search_keeps_candidate_without_maximum_claim',z['classification']=='indeterminate_reference' and z['best_known_grid_candidate']=='1' and z['maximum_price'] is None and z['unvisited_grid_point_count']==3)
    x=fixture();x['evaluation_budget_points']=0;z=evaluate(x)
    ok('zero_work_budget_not_empty_feasible_set_proof',z['classification']=='indeterminate_reference' and z['points']==[] and z['unvisited_grid_point_count']==5)
    x=fixture();c=x['scenarios'][1]['constraints'][0];c.update(state='missing',coefficients=None,operator=None,criterion_revision=None);z=evaluate(x)
    ok('missing_downside_not_inherited_from_base',z['classification']=='indeterminate_reference' and all(p['state']=='indeterminate' for p in z['points']) and z['points'][0]['conditions'][1]['original_claim']['coefficients'] is None)
    x=fixture();c=x['scenarios'][1]['constraints'][0];c.update(state='conflict',coefficients=None,original_claims=[{'literal':'A','evidence_ref':'SYNTHETIC-A'},{'literal':'B','evidence_ref':'SYNTHETIC-B'}]);z=evaluate(x)
    ok('conflict_alternatives_preserved',z['classification']=='indeterminate_reference' and len(z['points'][0]['conditions'][1]['original_claim']['original_claims'])==2)
    x=fixture();x['scenarios'][0]['constraints'][0]=constraint('nonmonotone',[-1]);x['scenarios'][1]['constraints'][0].update(state='undefined',coefficients=None);z=evaluate(x)
    ok('known_failed_relation_does_not_erase_required_unknown',z['points'][0]['state']=='indeterminate' and z['classification']=='indeterminate_reference')
    x=fixture();x['scenarios'][0]['constraints'][0]=constraint('nonmonotone',[-1]);z=evaluate(x)
    ok('empty_set_only_after_complete_declared_evaluation',z['classification']=='empty_declared_grid_reference' and z['complete_declared_domain_coverage'] and z['all_required_relations_resolved'])
    x=fixture();x['domain'].update(lower=money(0),upper=money(1),increment=money(F(1,2)),lower_closed=False,upper_closed=False);z=evaluate(x)
    ok('open_grid_endpoints_not_admitted',z['domain_grid_point_count']==1 and z['maximum_price']=='1/2')
    x=fixture();x['domain'].update(lower=money(0),upper=money(1),anchor=money(F(1,4)),increment=money(F(1,2)));z=evaluate(x)
    ok('explicit_nonzero_grid_anchor_retained',[p['price'] for p in z['points']]==['1/4','3/4'])
    x=fixture();x['domain'].update(lower=money(0),upper=money(0));z=evaluate(x)
    ok('singleton_closed_domain_keeps_explicit_zero',z['domain_grid_point_count']==1 and z['maximum_price']=='0')
    x=fixture();x['domain'].update(lower=money(0),upper=money(0),upper_closed=False);z=evaluate(x)
    ok('open_singleton_has_no_grid_points',z['domain_grid_point_count']==0 and z['classification']=='empty_declared_grid_reference')
    x=fixture();x['domain'].update(lower=money(-2),upper=money(0));z=evaluate(x)
    ok('negative_domain_not_silently_clamped',[p['price'] for p in z['points']]==['-2','-1','0'])
    x=fixture();x['domain']['upper']=money(10**30);x['evaluation_budget_points']=1;z=evaluate(x)
    ok('huge_grid_count_without_materializing_entire_domain',z['domain_grid_point_count']==10**30+1 and len(z['points'])==1 and z['classification']=='indeterminate_reference')
    x=fixture();x['domain']['lower']={'state':'missing','causes':[{'field_id':'lower bound','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('unknown_domain_not_replaced_by_zero',z['domain_grid_point_count'] is None and z['issues'][0]['original_claim']['causes'][0]['reason']=='Not supplied')
    x=fixture();x['domain']['normalizing_price_unit']=money(2);z=evaluate(x)
    ok('dimensionless_polynomial_uses_explicit_price_scale',z['points'][1]['normalized_price']=='1/2')
    x=fixture();x['scenarios'][1]['required_status']='unresolved';z=evaluate(x)
    ok('scenario_applicability_unknown_blocks_bound',z['classification']=='indeterminate_reference' and z['maximum_price'] is None)
    x=fixture()
    for s in x['scenarios']:s.update(required_status='excluded',exclusion_reason='SYNTHETIC',exclusion_rule_ref='SYNTHETIC')
    z=evaluate(x);ok('all_excluded_not_vacuous_support',z['classification']=='indeterminate_reference' and z['best_known_grid_candidate'] is None)
    x=fixture();x['scenarios'][1]['constraints'][0]['criterion_revision']=None;z=evaluate(x)
    ok('missing_criterion_revision_cannot_use_latest',z['classification']=='indeterminate_reference')
    x=fixture();x['domain'].update(lower=money(0),upper=money(0),upper_closed=False);x['scenarios'][1]['constraints'][0].update(state='missing',coefficients=None);z=evaluate(x)
    ok('empty_grid_does_not_claim_required_relation_resolved',z['domain_grid_point_count']==0 and not z['all_required_relations_resolved'] and z['classification']=='indeterminate_reference')
    grid_cases=0
    for lower in [F(-1,2),F(0),F(1,2)]:
        for upper in [F(1,2),F(1),F(3,2)]:
            for anchor in [F(-1,4),F(0),F(1,4)]:
                for step in [F(1,4),F(1,2),F(1)]:
                    for lc,uc in [(False,False),(False,True),(True,False),(True,True)]:
                        x=fixture();x['domain'].update(lower=money(lower),upper=money(upper),anchor=money(anchor),increment=money(step),lower_closed=lc,upper_closed=uc)
                        for s in x['scenarios']:s['constraints'][0]=constraint(s['required_constraint_ids'][0],[1])
                        oracle=[anchor+k*step for k in range(-20,21) if (anchor+k*step>lower or (lc and anchor+k*step==lower)) and (anchor+k*step<upper or (uc and anchor+k*step==upper))]
                        z=evaluate(x);assert [F(p['price']) for p in z['points']]==oracle
                        assert z['maximum_price']==(str(max(oracle)) if oracle else None)
                        grid_cases+=1
    ok('grid_endpoints_and_negative_indices_match_independent_enumeration',grid_cases==324)
    mutations=[('context_mismatch',lambda x:x['scenarios'][1]['context'].update(run_id='OTHER')),('wrong_scenario_context',lambda x:x['scenarios'][1]['context'].update(scenario_id='Base')),('missing_required_scenario',lambda x:x['scenarios'].pop()),('duplicate_scenario',lambda x:x['scenarios'].append(deepcopy(x['scenarios'][0]))),('missing_constraint',lambda x:x['scenarios'][0]['constraints'].clear()),('wrong_constraint_id',lambda x:x['scenarios'][0]['constraints'][0].update(constraint_id='OTHER')),('duplicate_constraint',lambda x:x['scenarios'][0]['constraints'].append(deepcopy(x['scenarios'][0]['constraints'][0]))),('no_empty_required_constraint_inventory',lambda x:x['scenarios'][0].update(required_constraint_ids=[])),('no_empty_scenario_inventory',lambda x:x.update(expected_scenario_ids=[])),('unsupported_continuous_domain',lambda x:x['domain'].update(kind='continuous_interval')),('zero_increment',lambda x:x['domain'].update(increment=money(0))),('negative_increment',lambda x:x['domain'].update(increment=money(-1))),('zero_normalization',lambda x:x['domain'].update(normalizing_price_unit=money(0))),('reversed_bounds',lambda x:x['domain'].update(lower=money(5))),('wrong_currency',lambda x:x['domain']['increment'].update(currency='OTHER')),('wrong_unit',lambda x:x['domain']['upper'].update(unit_id='OTHER')),('wrong_basis',lambda x:x['domain']['upper'].update(basis='OTHER')),('wrong_domain_cutoff',lambda x:x['domain']['upper'].update(period_ref='OTHER')),('no_unjustified_exclusion',lambda x:x['scenarios'][1].update(required_status='excluded')),('conflict_needs_alternate_claims',lambda x:x['scenarios'][0]['constraints'][0].update(state='conflict')),('zero_coefficient_denominator',lambda x:x['scenarios'][0]['constraints'][0]['coefficients'][0].update(denominator=0)),('floating_coefficient',lambda x:x['scenarios'][0]['constraints'][0]['coefficients'][0].update(numerator=0.5)),('negative_work_budget',lambda x:x.update(evaluation_budget_points=-1)),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    # Exact endpoint truth tables for each operator at zero; no display rounding.
    for op,expected in [('>=',True),('>',False),('<=',True),('<',False)]:ok('explicit_equality_'+op,relation(F(0),op) is expected)
    report={'status':'passed','total':len(checks),'checks':checks,'enumerated_grid_property_cases':grid_cases,'schemas_checked':len(vocabulary.STORE),'synthetic_example':evaluate(b),'scope':'Exact finite uniform grid enumeration/intersection of explicitly supplied scenario-specific normalized-polynomial claims only. Not actual financial dependency recalculation, authenticated criteria/exclusions, continuous/global price optimization, approved RLV, economic feasibility, independent audit or production.'}
    (ROOT/'references/price-grid-catalogue-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'references/fixtures/price-grid-catalogue-synthetic.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
