"""Reduced affine-cost/single-return price-to-condition/cash reference, not full underwriting."""
from fractions import Fraction as F
from pathlib import Path
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_calendar_ledger as vocabulary
import validate_price_grid_catalogue as grid
import validate_periodic_irr_isolation as irr_reference
ROOT=Path(__file__).resolve().parents[1]

def ratio(q,unit,basis,period):
    if q['dimensions']!={'money':0,'area':0,'unit':0,'space':0,'time':0} or q['currency'] is not None or q['measurement_role']!='ratio' or (q['unit_id'],q['basis'],q['period_ref'])!=(unit,basis,period):raise ValueError('ratio unit/base/period mismatch')
    return F(q['value']['numerator'],q['value']['denominator'])

def relation(v,t,op):return grid.relation(v-t,op)

def evaluate(data):
    vocabulary.schema_check('affine-price-support',data)
    scenarios=vocabulary.unique(data['scenarios'],'scenario_id')
    if set(scenarios)!=set(data['expected_scenario_ids']):raise ValueError('scenario inventory mismatch')
    domain=data['domain'];issues=[];signature=None;domain_values={}
    for key in ['lower','upper','anchor','increment','normalizing_price_unit']:
        q=domain[key]
        if q['state']=='known':domain_values[key],signature=vocabulary.quantity(q,'stock','PRICE-DOMAIN',signature)
    parameters={};catalogue_scenarios=[]
    for sid,s in scenarios.items():
        if s['context']!=dict(data['context'],scenario_id=sid):raise ValueError('scenario context mismatch')
        if s['assumptions_state']=='conflict' and len(s['assumption_claims'])<2:raise ValueError('assumption conflict requires alternative claims')
        local=[];p={};criteria={}
        if s['assumptions_state']!='declared_claim' or not s['profile_evidence_ref'] or not s['period_definition_ref']:local.append({'cause':'profile assumptions/evidence unresolved','original_claim':deepcopy(s)})
        for name in ['cost_intercept','cost_price_coefficient','noi_for_declared_period','terminal_equity_distribution']:
            q=s[name]
            if q['state']!='known':local.append({'cause':'profile quantity unresolved','field':name,'original_claim':deepcopy(q)});continue
            if name=='cost_price_coefficient':p[name]=ratio(q,'dimensionless_cost_multiplier','price_to_total_cost','PRICE-DOMAIN')
            else:
                role,period=('stock','PRICE-DOMAIN') if name=='cost_intercept' else ('period_total','NOI-PERIOD') if name=='noi_for_declared_period' else ('period_total','TERMINAL-RETURN-PERIOD')
                v,key=vocabulary.quantity(q,role,period,signature)
                if signature is None:signature=key
                p[name]=v
        for key,metric,basis,period in [('yoc','declared_period_noi_over_affine_cost','declared_period_noi_over_affine_total_cost','NOI-PERIOD'),('irr','single_period_project_equity_irr','one_interval_project_equity_effective_return','RETURN-INTERVAL')]:
            c=s[key+'_criterion']
            if not s['criterion_revisions'][key]:local.append({'cause':'criterion revision unresolved','metric':key,'original_claim':None})
            if c['context']!=s['context'] or c['metric_id']!=metric or c['metric_definition_ref']!=data['metric_definition_refs'][key]:raise ValueError('criterion context/metric definition mismatch')
            if c['condition_role']!='pass_condition' or c['applicability']!='applicable':local.append({'cause':'objective role/applicability needs explicit support interpretation','metric':key,'original_claim':deepcopy(c)})
            q=c['threshold']
            if q['state']!='known':local.append({'cause':'objective threshold unresolved','metric':key,'original_claim':deepcopy(q)})
            else:criteria[key]=(ratio(q,'fraction',basis,period),c['operator'])
        if len(domain_values)!=5:local.append({'cause':'domain/normalization unresolved'})
        if len(p)==4 and len(criteria)==2 and len(domain_values)==5:
            a=p['cost_intercept'];b=p['cost_price_coefficient'];N=p['noi_for_declared_period'];H=p['terminal_equity_distribution'];y=criteria['yoc'][0];r=criteria['irr'][0]
            if not(a>0 and b>0 and N>0 and H>0 and y>0 and r>-1 and a+b*domain_values['lower']>0):local.append({'cause':'outside declared positive affine/single-return profile','values':{k:str(v) for k,v in p.items()},'yoc_target':str(y),'irr_target':str(r)})
        known=not local
        if known:parameters[sid]=(p,criteria)
        if local and s['required_status']!='excluded':issues.append({'scenario_id':sid,'causes':local})
        constraints=[]
        for key in ['yoc','irr']:
            c=s[key+'_criterion'];coefficients=None
            if known:
                t,op=criteria[key];factor=t if key=='yoc' else 1+t;amount=p['noi_for_declared_period'] if key=='yoc' else p['terminal_equity_distribution']
                coefficients=[amount-factor*p['cost_intercept'],-factor*p['cost_price_coefficient']*domain_values['normalizing_price_unit']]
            constraint=grid.constraint(key,coefficients if coefficients is not None else [0],c['operator'])
            constraint['state']='defined_claim' if known else 'missing';constraint['coefficients']=None if coefficients is None else [{'numerator':v.numerator,'denominator':v.denominator} for v in coefficients]
            constraint['criterion_revision']=s['criterion_revisions'][key];constraint['normalized_relation_definition_ref']=data['profile_definition_ref']+'::'+key;constraint['evidence_ref']=s['profile_evidence_ref'];constraint['original_claims']=[{'literal':json.dumps(c,sort_keys=True),'evidence_ref':data['profile_definition_ref']}]
            constraints.append(constraint)
        catalogue_scenarios.append({'scenario_id':sid,'context':deepcopy(s['context']),'required_status':s['required_status'],'exclusion_reason':s['exclusion_reason'],'exclusion_rule_ref':s['exclusion_rule_ref'],'scenario_evidence_ref':s['scenario_evidence_ref'],'required_constraint_ids':['yoc','irr'],'constraints':constraints})
    catalogue={'purpose':data['purpose'],'authorization':data['authorization'],'context':deepcopy(data['context']),'scope_definition_ref':data['profile_definition_ref'],'domain':deepcopy(domain),'expected_scenario_ids':list(data['expected_scenario_ids']),'scenarios':catalogue_scenarios,'evaluation_budget_points':data['evaluation_budget_points']}
    result=grid.evaluate(catalogue)
    def point(price):
        rows=[]
        for sid,(p,criteria) in parameters.items():
            if scenarios[sid]['required_status']!='required':continue
            C=p['cost_intercept']+p['cost_price_coefficient']*price;N=p['noi_for_declared_period'];H=p['terminal_equity_distribution'];yoc=N/C;r=H/C-1;q=C/H
            assert C>0 and q>0 and -C+H*q==0
            rows.append({'scenario_id':sid,'cost':str(C),'noi_over_cost':str(yoc),'exact_periodic_irr':str(r),'equity_multiple':str(H/C),'gross_initial_contribution':str(C),'gross_terminal_distribution':str(H),'initial_cash_sources':str(C),'initial_cash_uses':str(C),'terminal_cash_receipt':str(H),'terminal_equity_cash_out':str(H),'linear_irr_root_certificate':{'positive_discount_factor':str(q),'polynomial_residual':'0','degree':1},'yoc_condition_satisfied':relation(yoc,*criteria['yoc']),'irr_condition_satisfied':relation(r,*criteria['irr'])})
        return rows
    quote=result['best_known_grid_candidate'];checks=None;next_check=None
    if quote is not None:
        P=F(quote);checks=point(P);assert checks and all(x['yoc_condition_satisfied'] and x['irr_condition_satisfied'] for x in checks)
        nxt=P+domain_values['increment'];upper=domain_values['upper'];inside=nxt<upper or (nxt==upper and domain['upper_closed'])
        next_check={'price':str(nxt),'state':'inside_declared_grid' if inside else 'outside_declared_domain','scenario_diagnostics':point(nxt) if inside else []}
    asking=data['asking_price'];asking_result={'state':'pending_domain' if asking['state']=='known' else 'unresolved_asking','original_claim':deepcopy(asking),'scenario_diagnostics':[]}
    if asking['state']=='known' and len(domain_values)==5:
        P,_=vocabulary.quantity(asking,'stock','PRICE-DOMAIN',signature);idx=(P-domain_values['anchor'])/domain_values['increment'];lo=domain_values['lower'];hi=domain_values['upper']
        inside=(P>lo or(P==lo and domain['lower_closed'])) and (P<hi or(P==hi and domain['upper_closed'])) and idx.denominator==1
        can_evaluate=inside and not issues and result.get('all_required_relations_resolved',False)
        asking_result={'state':'inside_declared_grid' if inside else 'outside_declared_grid','evaluation_state':'evaluated_reduced_profile' if can_evaluate else 'not_evaluated','price':str(P),'scenario_diagnostics':point(P) if can_evaluate else []}
    return {'decision':'PENDING','publication_authorized':False,'approved_rlv':False,'profile':'reduced affine cost and two explicit objectives only','catalogue_reference':result,'profile_issues':issues,'derived_catalogue_input':catalogue,'candidate_cash_return_checks':checks,'candidate_is_maximum_of_declared_grid':result.get('classification')=='maximum_attained_in_declared_grid_reference','next_grid_point_check':next_check,'asking_diagnostic':asking_result,'annualization_applied':False}

def ratio_quantity(n,unit,basis,period):
    n=F(n);return {'state':'known','value':{'numerator':n.numerator,'denominator':n.denominator},'dimensions':{'money':0,'area':0,'unit':0,'space':0,'time':0},'unit_id':unit,'currency':None,'measurement_role':'ratio','basis':basis,'period_ref':period,'sources':[vocabulary.src()]}

def criterion(ctx,key,threshold):
    metric,basis,period=('declared_period_noi_over_affine_cost','declared_period_noi_over_affine_total_cost','NOI-PERIOD') if key=='yoc' else ('single_period_project_equity_irr','one_interval_project_equity_effective_return','RETURN-INTERVAL')
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':deepcopy(ctx),'criterion_id':'SYNTHETIC-'+key,'metric_id':metric,'metric_definition_ref':'SYNTHETIC-'+key+'-definition','condition_role':'pass_condition','operator':'>=','threshold':ratio_quantity(threshold,'fraction',basis,period),'applicability':'applicable','applicability_reason':None,'applicability_rule_ref':None,'aggregation_rule_ref':None,'sources':[vocabulary.src()]}

def fixture():
    source=grid.fixture();scenarios=[]
    for sid,a,b,N,H,y,r in [('Base',2,2,10,12,1,0),('Downside',4,1,10,12,1,F(1,5))]:
        ctx=dict(source['context'],scenario_id=sid)
        scenarios.append({'scenario_id':sid,'context':ctx,'required_status':'required','exclusion_reason':None,'exclusion_rule_ref':None,'scenario_evidence_ref':'SYNTHETIC-EXPLICIT-SCOPE','assumptions_state':'declared_claim','assumption_claims':[],'profile_evidence_ref':'SYNTHETIC-REDUCED-PROFILE','period_definition_ref':'SYNTHETIC-ONE-ABSTRACT-REGULAR-INTERVAL','cost_intercept':grid.money(a),'cost_price_coefficient':ratio_quantity(b,'dimensionless_cost_multiplier','price_to_total_cost','PRICE-DOMAIN'),'noi_for_declared_period':vocabulary.money(N,'period_total','NOI-PERIOD'),'terminal_equity_distribution':vocabulary.money(H,'period_total','TERMINAL-RETURN-PERIOD'),'yoc_criterion':criterion(ctx,'yoc',y),'irr_criterion':criterion(ctx,'irr',r)})
    source['domain']['upper']=grid.money(8)
    for s in scenarios:s['criterion_revisions']={'yoc':'SYNTHETIC-YOC-v1','irr':'SYNTHETIC-IRR-v1'}
    return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','context':source['context'],'profile':'affine_cost_one_initial_equity_one_terminal_distribution','profile_definition_ref':'SYNTHETIC-AFFINE-PROFILE-NOT-HOUSE-RLV','metric_definition_refs':{'yoc':'SYNTHETIC-yoc-definition','irr':'SYNTHETIC-irr-definition'},'domain':source['domain'],'asking_price':grid.money(4),'expected_scenario_ids':['Base','Downside'],'scenarios':scenarios,'evaluation_budget_points':20}

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
    ok('derived_constraints_and_grid_support_agree',z['catalogue_reference']['maximum_price']=='4' and z['candidate_is_maximum_of_declared_grid'])
    ok('cash_cost_and_return_recomputed_at_candidate',z['candidate_cash_return_checks'][0]['cost']=='10' and z['candidate_cash_return_checks'][0]['noi_over_cost']=='1' and z['candidate_cash_return_checks'][0]['exact_periodic_irr']=='1/5')
    ok('root_certificate_exact_without_tolerance_or_annualization',all(c['linear_irr_root_certificate']['polynomial_residual']=='0' for c in z['candidate_cash_return_checks']) and not z['annualization_applied'])
    ok('next_grid_point_is_checked_not_rounded_into_pass',z['next_grid_point_check']['price']=='5' and z['next_grid_point_check']['scenario_diagnostics'][0]['yoc_condition_satisfied'] is False)
    ok('asking_evaluated_as_distinct_input',z['asking_diagnostic']['state']=='inside_declared_grid' and z['asking_diagnostic']['price']=='4')
    ok('not_full_rlv_or_investment_decision',not z['approved_rlv'] and z['decision']=='PENDING' and not z['publication_authorized'])
    ok('original_profile_criteria_not_mutated',b==old)
    x=fixture();x['scenarios'][0]['yoc_criterion']['operator']='>';z=evaluate(x)
    ok('strict_objective_excludes_exact_boundary',z['catalogue_reference']['maximum_price']=='3' and z['next_grid_point_check']['scenario_diagnostics'][0]['yoc_condition_satisfied'] is False)
    x=fixture();x['domain']['upper']=grid.money(3);z=evaluate(x)
    ok('next_point_outside_domain_not_economic_failure',z['catalogue_reference']['maximum_price']=='3' and z['next_grid_point_check']['state']=='outside_declared_domain' and z['next_grid_point_check']['scenario_diagnostics']==[])
    x=fixture();x['evaluation_budget_points']=2;z=evaluate(x)
    ok('partial_search_cash_check_does_not_certify_maximum',z['candidate_cash_return_checks'] is not None and not z['candidate_is_maximum_of_declared_grid'] and z['catalogue_reference']['maximum_price'] is None)
    x=fixture();x['asking_price']={'state':'missing','causes':[{'field_id':'asking','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('asking_absent_not_zero',z['asking_diagnostic']['state']=='unresolved_asking' and z['catalogue_reference']['maximum_price']=='4')
    x=fixture();x['asking_price']=grid.money(0);z=evaluate(x)
    ok('explicit_zero_asking_preserved',z['asking_diagnostic']['price']=='0' and len(z['asking_diagnostic']['scenario_diagnostics'])==2)
    x=fixture();x['asking_price']=grid.money(F(1,2));z=evaluate(x)
    ok('off_grid_asking_not_admitted',z['asking_diagnostic']['state']=='outside_declared_grid' and z['asking_diagnostic']['scenario_diagnostics']==[])
    x=fixture();x['scenarios'][1]['noi_for_declared_period']={'state':'missing','causes':[{'field_id':'NOI','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('missing_required_scenario_parameter_blocks_price',z['catalogue_reference']['classification']=='indeterminate_reference' and z['candidate_cash_return_checks'] is None and z['profile_issues'][0]['causes'][0]['original_claim']['state']=='missing')
    x=fixture();x['scenarios'][1]['assumptions_state']='unresolved';z=evaluate(x)
    ok('formula_profile_assumptions_not_inferred',z['catalogue_reference']['classification']=='indeterminate_reference')
    x=fixture();x['scenarios'][0]['irr_criterion']['condition_role']='fail_condition';z=evaluate(x)
    ok('fail_condition_not_silently_reinterpreted_as_support_goal',z['catalogue_reference']['classification']=='indeterminate_reference')
    x=fixture();x['scenarios'][0]['yoc_criterion']['threshold']={'state':'missing','causes':[{'field_id':'threshold','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('missing_goal_not_historical_default',z['catalogue_reference']['classification']=='indeterminate_reference')
    x=fixture();x['scenarios'][0]['cost_price_coefficient']=ratio_quantity(0,'dimensionless_cost_multiplier','price_to_total_cost','PRICE-DOMAIN');z=evaluate(x)
    ok('zero_slope_is_known_but_outside_reduced_profile',z['catalogue_reference']['classification']=='indeterminate_reference' and z['profile_issues'][0]['causes'][0]['values']['cost_price_coefficient']=='0')
    x=fixture();x['domain']['lower']=grid.money(-1);z=evaluate(x)
    ok('nonpositive_cost_domain_not_called_financially_infeasible',z['catalogue_reference']['classification']=='indeterminate_reference')
    x=fixture();x['domain']['lower']={'state':'missing','causes':[{'field_id':'lower','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x)
    ok('known_asking_not_relabelled_missing_when_domain_unknown',z['asking_diagnostic']['state']=='pending_domain' and z['asking_diagnostic']['original_claim']['state']=='known')
    x=fixture();x['domain'].update(lower=grid.money(7),upper=grid.money(8));z=evaluate(x)
    ok('empty_reduced_grid_has_no_fabricated_quote',z['catalogue_reference']['classification']=='empty_declared_grid_reference' and z['candidate_cash_return_checks'] is None and z['next_grid_point_check'] is None)
    x=fixture();x['scenarios'][1].update(required_status='excluded',exclusion_reason='SYNTHETIC-SCOPE',exclusion_rule_ref='SYNTHETIC-RULE',assumptions_state='unresolved');z=evaluate(x)
    ok('explicitly_excluded_scenario_not_completed_from_base',z['catalogue_reference']['maximum_price']=='4' and z['derived_catalogue_input']['scenarios'][1]['constraints'][0]['coefficients'] is None)
    x=fixture();claims=[{'literal':'NOI fixed','evidence_ref':'SYNTHETIC-A'},{'literal':'NOI depends on price','evidence_ref':'SYNTHETIC-B'}];x['scenarios'][0].update(assumptions_state='conflict',assumption_claims=claims);z=evaluate(x)
    ok('conflicting_profile_alternatives_preserved',z['catalogue_reference']['classification']=='indeterminate_reference' and z['profile_issues'][0]['causes'][0]['original_claim']['assumption_claims']==claims)
    operators={'>=':lambda v,t:v>=t,'>':lambda v,t:v>t,'<=':lambda v,t:v<=t,'<':lambda v,t:v<t};point_cases=0
    for yop in operators:
        for rop in operators:
            x=fixture();x['scenarios'][0]['yoc_criterion']['operator']=yop;x['scenarios'][0]['irr_criterion']['operator']=rop;z=evaluate(x)
            for point_record in z['catalogue_reference']['points']:
                P=F(point_record['price'])
                for sid,intercept,slope,N,H,y,r in [('Base',2,2,10,12,F(1),F(0)),('Downside',4,1,10,12,F(1),F(1,5))]:
                    C=F(intercept)+slope*P;cs=[v for v in point_record['conditions'] if v['scenario_id']==sid]
                    assert cs[0]['condition_satisfied']==operators[yop if sid=='Base' else '>='](F(N)/C,y)
                    assert cs[1]['condition_satisfied']==operators[rop if sid=='Base' else '>='](F(H)/C-1,r)
                point_cases+=1
    ok('derived_polynomials_match_direct_ratio_comparisons_all_operators',point_cases==144)
    x=fixture();x['domain']['normalizing_price_unit']=grid.money(2);z=evaluate(x)
    ok('normalization_changes_polynomial_scale_not_economic_price',z['catalogue_reference']['maximum_price']=='4' and z['candidate_cash_return_checks'][0]['cost']=='10')
    x=fixture();x['domain'].update(anchor=grid.money(F(1,4)),increment=grid.money(F(1,2)));z=evaluate(x)
    ok('fractional_quote_and_next_increment_not_rounded',z['catalogue_reference']['maximum_price']=='15/4' and z['next_grid_point_check']['price']=='17/4' and not z['next_grid_point_check']['scenario_diagnostics'][0]['yoc_condition_satisfied'])
    for row in z['candidate_cash_return_checks']:
        C=F(row['gross_initial_contribution']);H=F(row['gross_terminal_distribution']);exact=F(row['exact_periodic_irr']);isolated=irr_reference.isolate_periodic([-C,H],F(1,1000000),200)
        assert isolated['status']=='complete_reference' and isolated['distinct_positive_discount_roots']==1
        root=isolated['roots'][0]
        assert (F(root['exact_periodic_rate'])==exact if root['exact_periodic_rate'] is not None else F(root['periodic_rate_interval']['lower'])<=exact<F(root['periodic_rate_interval']['upper']))
    ok('closed_form_return_agrees_with_general_periodic_root_isolation',len(z['candidate_cash_return_checks'])==2)
    mutations=[('scenario_context_mismatch',lambda x:x['scenarios'][0]['context'].update(run_id='OTHER')),('criterion_context_mismatch',lambda x:x['scenarios'][0]['irr_criterion']['context'].update(scenario_id='OTHER')),('metric_definition_mismatch',lambda x:x['scenarios'][0]['irr_criterion'].update(metric_definition_ref='OTHER')),('wrong_metric_id',lambda x:x['scenarios'][0]['yoc_criterion'].update(metric_id='OTHER')),('missing_required_scenario',lambda x:x['scenarios'].pop()),('duplicate_scenario',lambda x:x['scenarios'].append(deepcopy(x['scenarios'][0]))),('currency_mismatch',lambda x:x['scenarios'][0]['cost_intercept'].update(currency='OTHER')),('cost_unit_mismatch',lambda x:x['scenarios'][0]['cost_intercept'].update(unit_id='OTHER')),('noi_period_mismatch',lambda x:x['scenarios'][0]['noi_for_declared_period'].update(period_ref='OTHER')),('threshold_basis_mismatch',lambda x:x['scenarios'][0]['irr_criterion']['threshold'].update(basis='OTHER')),('coefficient_dimensions_mismatch',lambda x:x['scenarios'][0]['cost_price_coefficient']['dimensions'].update(money=1)),('asking_currency_mismatch',lambda x:x['asking_price'].update(currency='OTHER')),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    reject('assumption_conflict_requires_alternatives',lambda x:x['scenarios'][0].update(assumptions_state='conflict'))
    x=fixture();x['scenarios'][0]['criterion_revisions']['irr']=None;z=evaluate(x)
    ok('criterion_revision_not_inferred_from_input_revision',z['catalogue_reference']['classification']=='indeterminate_reference' and z['derived_catalogue_input']['scenarios'][0]['constraints'][1]['criterion_revision'] is None)
    report={'status':'passed','total':len(checks),'checks':checks,'operator_price_point_cases':point_cases,'schemas_checked':len(vocabulary.STORE),'synthetic_example':evaluate(b),'scope':'Typed declared positive affine-cost/price-independent NOI/single-initial-contribution-single-terminal-distribution profile; derived finite-grid two-objective conditions and exact candidate cash/linear-root checks only. Not full M1–M7 financial engine, approved price goals/Q3, calendar/annualization/bank/tax policy, general IRR selection, RLV, independent audit or production.'}
    (ROOT/'references/affine-price-support-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'references/fixtures/affine-price-support-synthetic.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
