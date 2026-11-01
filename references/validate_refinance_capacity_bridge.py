"""Exact reduced valuation/capacity/selected-principal/closing reference. No approval or bank defaults."""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import json
from jsonschema import ValidationError
import validate_calendar_ledger as vocabulary
import validate_settlement_bridge as settlement
ROOT=Path(__file__).resolve().parents[1]

def ratio(q,unit,basis,period):
    if q['dimensions']!={'money':0,'area':0,'unit':0,'space':0,'time':0} or q['currency'] is not None or q['measurement_role']!='ratio' or (q['unit_id'],q['basis'],q['period_ref'])!=(unit,basis,period):raise ValueError('ratio convention/unit/base/period mismatch')
    return F(q['value']['numerator'],q['value']['denominator'])

def evaluate(data):
    vocabulary.schema_check('refinance-capacity-bridge',data);source=data['settlement_bridge'];loan=data['loan_id'];issues=[]
    common={'decision':'PENDING','publication_authorized':False,'credit_approval_verified':False,'funding_availability_verified':False,'bank_terms_authority_verified':False}
    if source['context']!=data['context'] or source['kind']!='refinance' or source['new_debt_id']!=loan:raise ValueError('refinance/loan/context binding mismatch')
    closing=settlement.reconcile(source)
    if closing['state']=='blocked':return dict(common,state='pending_reference',reason='underlying closing unresolved',settlement_reference=closing,issues=deepcopy(closing['issues']))
    dates=vocabulary.unique(source['event_ledger']['date_bindings'],'date_ref');closing_date=dates[source['closing_date_ref']]['iso_date']
    if data['sizing_asof_date']!=closing_date:return dict(common,state='pending_reference',reason='valuation/sizing date bridge needs separate validity contract',issues=[{'sizing_date':data['sizing_asof_date'],'closing_date':closing_date}])
    if data['terms_state']=='conflict' and len(data['term_claims'])<2:raise ValueError('term conflict requires alternative claims')
    if data['profile']!='regular_fixed_rate_equal_payments_in_arrears' or data['terms_state']!='documented_claim' or not data['terms_evidence_ref']:
        return dict(common,state='pending_reference',reason='loan profile/terms unresolved',original_terms=deepcopy(data))
    if data['limit_inventory_state']!='declared_complete' or not data['limit_inventory_evidence_ref']:
        return dict(common,state='pending_reference',reason='capacity restriction inventory unresolved',original_limits=deepcopy(data['other_capacity_limits']))
    if data['disbursement_profile']!='full_selected_principal_cash_disbursement':return dict(common,state='pending_reference',reason='partial/net/noncash proceeds need separate explicit contract')
    if data['annual_service_convention']!='m_times_regular_payment_equivalent' or not data['annual_service_evidence_ref']:return dict(common,state='pending_reference',reason='annual sizing-service convention/evidence unresolved')
    n=data['amortization_payment_count'];m=data['payments_per_year'];k=data['maturity_after_payment_count']
    if any(v is None for v in [n,m,k]):return dict(common,state='pending_reference',reason='payment frequency/amortization/maturity count missing')
    if k>n:return dict(common,state='pending_reference',reason='maturity count outside reduced amortization profile')
    if n>data['calculation_budget_payments']:return dict(common,state='pending_reference',reason='explicit calculation budget insufficient',requested_payment_count=n,allowed_payment_count=data['calculation_budget_payments'])
    pid=source['closing_period_ref'];signature=None
    for account in source['event_ledger']['accounts']:
        if account['account_class']!='external_counterparty':_,signature=vocabulary.quantity(account['opening_balance'],'stock',account['opening_balance']['period_ref'],signature)
    def monetary(q,role,period,name):
        if q['state']!='known':issues.append({'cause':'required sizing quantity unresolved','field':name,'original_claim':deepcopy(q)});return None
        return vocabulary.quantity(q,role,period,signature)[0]
    def rvalue(name,unit,basis,period):
        q=data[name]
        if q['state']!='known':issues.append({'cause':'required sizing ratio unresolved','field':name,'original_claim':deepcopy(q)});return None
        return ratio(q,unit,basis,period)
    VNOI=monetary(data['valuation_noi'],'period_total','VALUATION-NOI-ANNUAL','valuation_noi')
    N=monetary(data['bank_underwriting_noi'],'period_total','BANK-NOI-ANNUAL','bank_underwriting_noi')
    selected=monetary(data['selected_principal'],'stock','SELECTED-PRINCIPAL:'+loan,'selected_principal')
    cap=rvalue('valuation_cap_rate','annual_cap_fraction','annual_valuation_noi_to_value','VALUATION-NOI-ANNUAL')
    ltv=rvalue('maximum_ltv','ltv_fraction','bank_maximum_loan_to_value','ASOF:'+closing_date)
    dscr=rvalue('minimum_bank_dscr','dscr_multiple','bank_minimum_debt_service_coverage','BANK-NOI-ANNUAL')
    rate=rvalue('periodic_effective_rate','periodic_effective_fraction','regular_payment_interval','PAYMENT-INTERVAL')
    other=vocabulary.unique(data['other_capacity_limits'],'limit_id');limits={}
    if set(other)&{'LTV','DSCR'}:raise ValueError('additional limit ID collides with derived constraint')
    for id,item in other.items():
        if not item['evidence_ref']:issues.append({'cause':'additional limit evidence missing','limit_id':id})
        limits[id]=monetary(item['amount'],'stock','LOAN-CAPACITY:'+loan,id)
    if issues:return dict(common,state='pending_reference',reason='required sizing inputs unresolved',issues=issues,settlement_reference=closing)
    if not(cap>0 and dscr>0 and VNOI>=0 and N>=0 and ltv>=0 and rate>=0 and selected>=0 and all(v>=0 for v in limits.values())):
        return dict(common,state='pending_reference',reason='outside declared nonnegative fixed-rate capacity profile',original_inputs=deepcopy(data))
    value=VNOI/cap
    payment_unit=F(1,n) if rate==0 else rate/(1-(1+rate)**(-n))
    annual_constant=m*payment_unit
    limits.update(LTV=value*ltv,DSCR=N/(dscr*annual_constant));capacity=min(limits.values());active=sorted(id for id,v in limits.items() if v==capacity)
    payment=selected*payment_unit;annual_service=selected*annual_constant
    balance=selected
    for _ in range(k):balance=balance*(1+rate)-payment
    closed_balance=selected*(1+rate)**k-payment*sum(((1+rate)**j for j in range(k)),F(0))
    pv=sum((payment/(1+rate)**j for j in range(1,n+1)),F(0))
    assert balance==closed_balance and pv==selected
    if selected>capacity:issues.append({'cause':'selected principal exceeds declared capacity','selected':str(selected),'capacity':str(capacity),'excess':str(selected-capacity)})
    actual=F(next(row['ledger'] for row in closing['statement_reconciliation'] if row['role']=='proceeds'))
    actual_principal=F(closing['ledger_reference']['debt'][loan])
    if actual!=selected:issues.append({'cause':'recorded proceeds do not equal explicit full-disbursement selection','selected':str(selected),'recorded_cash':str(actual),'residual':str(actual-selected)})
    if actual_principal!=selected:issues.append({'cause':'recorded principal does not equal selection','selected':str(selected),'recorded_principal':str(actual_principal),'residual':str(actual_principal-selected)})
    quote=source['valuation_claim']
    if quote is not None:
        if quote['state']!='known':issues.append({'cause':'closing valuation claim unresolved','original_claim':deepcopy(quote)})
        else:
            claimed=monetary(quote,'stock','VALUATION:'+closing_date,'closing valuation')
            if claimed!=value:issues.append({'cause':'valuation claim differs from declared NOI/cap','claimed':str(claimed),'derived':str(value),'residual':str(claimed-value)})
    return dict(common,state='internally_reconciled_reference' if not issues else 'pending_reference',issues=issues,derived_valuation=str(value),bank_underwriting_noi=str(N),capacity_limits={id:str(v) for id,v in limits.items()},capacity=str(capacity),binding_limits=active,selected_principal=str(selected),recorded_cash_proceeds=str(actual),recorded_new_principal=str(actual_principal),payment_per_regular_interval=str(payment),annualized_regular_payment_equivalent=str(annual_service),annual_service_convention=data['annual_service_convention'],dated_annual_service_computed=False,annual_debt_constant=str(annual_constant),bank_dscr=None if annual_service==0 else str(N/annual_service),bank_dscr_state='undefined_zero_service' if annual_service==0 else 'defined_reference',scheduled_principal_after_k_payments=str(balance),scheduled_payment_count_at_maturity=k,maturity_diagnostic='scheduled_residual_balloon' if balance>0 else 'fully_amortized_in_declared_schedule',settlement_reference=closing,inventory_completeness='declared only; not independently verified')

def ratio_q(n,unit,basis,period):
    n=F(n);return {'state':'known','value':{'numerator':n.numerator,'denominator':n.denominator},'dimensions':{'money':0,'area':0,'unit':0,'space':0,'time':0},'unit_id':unit,'currency':None,'measurement_role':'ratio','basis':basis,'period_ref':period,'sources':[vocabulary.src()]}

def fixture():
    s=settlement.fixture();s['valuation_claim']=vocabulary.money(200,'stock','VALUATION:2028-02-15')
    return dict(vocabulary.env(),annual_service_convention="m_times_regular_payment_equivalent",annual_service_evidence_ref="SYNTHETIC-EXPLICIT-EQUIVALENT-NOT-DATED-CASH",settlement_bridge=s,loan_id='NEW',sizing_asof_date='2028-02-15',profile='regular_fixed_rate_equal_payments_in_arrears',terms_state='documented_claim',term_claims=[],terms_evidence_ref='SYNTHETIC-NOT-AUTHENTICATED-BANK-TERMS',limit_inventory_state='declared_complete',limit_inventory_evidence_ref='SYNTHETIC-DECLARED-LIMITS-NOT-AUDITED',disbursement_profile='full_selected_principal_cash_disbursement',valuation_noi=vocabulary.money(10,'period_total','VALUATION-NOI-ANNUAL'),valuation_cap_rate=ratio_q(F(1,20),'annual_cap_fraction','annual_valuation_noi_to_value','VALUATION-NOI-ANNUAL'),bank_underwriting_noi=vocabulary.money(12,'period_total','BANK-NOI-ANNUAL'),maximum_ltv=ratio_q(F(1,2),'ltv_fraction','bank_maximum_loan_to_value','ASOF:2028-02-15'),minimum_bank_dscr=ratio_q(F(6,5),'dscr_multiple','bank_minimum_debt_service_coverage','BANK-NOI-ANNUAL'),periodic_effective_rate=ratio_q(0,'periodic_effective_fraction','regular_payment_interval','PAYMENT-INTERVAL'),amortization_payment_count=10,payments_per_year=1,maturity_after_payment_count=5,selected_principal=vocabulary.money(100,'stock','SELECTED-PRINCIPAL:NEW'),other_capacity_limits=[],calculation_budget_payments=100)

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
    ok('declared_valuation_and_two_bank_constraints_reconcile',z['state']=='internally_reconciled_reference' and z['derived_valuation']=='200' and z['capacity']=='100')
    ok('binding_ties_preserve_all_constraints',z['binding_limits']==['DSCR','LTV'])
    ok('valuation_not_cash_and_capacity_not_distribution',z['derived_valuation']=='200' and z['recorded_cash_proceeds']=='100' and z['settlement_reference']['distribution_recorded']=='20')
    ok('valuation_noi_is_separate_from_bank_noi',z['bank_underwriting_noi']=='12' and z['derived_valuation']=='200')
    ok('zero_interest_has_explicit_amortization_branch',z['payment_per_regular_interval']=='10' and z['annualized_regular_payment_equivalent']=='10' and z['bank_dscr']=='6/5')
    ok('maturity_before_amortization_preserves_balloon',z['scheduled_principal_after_k_payments']=='50' and z['maturity_diagnostic']=='scheduled_residual_balloon')
    ok('no_approval_availability_or_deal_decision',z['decision']=='PENDING' and not z['credit_approval_verified'] and not z['funding_availability_verified'] and not z['publication_authorized'])
    ok('source_claims_not_mutated',b==before)
    x=fixture();x['maximum_ltv']=ratio_q(F(3,4),'ltv_fraction','bank_maximum_loan_to_value','ASOF:2028-02-15');z=evaluate(x);ok('dscr_limit_can_bind_independently',z['binding_limits']==['DSCR'] and z['capacity_limits']['LTV']=='150')
    x=fixture();x['bank_underwriting_noi']=vocabulary.money(24,'period_total','BANK-NOI-ANNUAL');z=evaluate(x);ok('ltv_limit_can_bind_independently',z['binding_limits']==['LTV'] and z['capacity_limits']['DSCR']=='200')
    x=fixture();x['other_capacity_limits']=[{'limit_id':'DOCUMENTED-CAP','amount':vocabulary.money(90,'stock','LOAN-CAPACITY:NEW'),'evidence_ref':'SYNTHETIC-EXPLICIT-LIMIT'}];z=evaluate(x);ok('additional_limit_cannot_be_ignored',z['state']=='pending_reference' and z['binding_limits']==['DOCUMENTED-CAP'] and z['capacity']=='90' and z['selected_principal']=='100')
    x=fixture();x['selected_principal']=vocabulary.money(90,'stock','SELECTED-PRINCIPAL:NEW');z=evaluate(x);ok('selection_not_silently_replaced_by_maximum_or_actual_draw',z['state']=='pending_reference' and z['selected_principal']=='90' and z['recorded_cash_proceeds']=='100')
    x=fixture();x['bank_underwriting_noi']=vocabulary.money(30,'period_total','BANK-NOI-ANNUAL');x['maximum_ltv']=ratio_q(F(3,4),'ltv_fraction','bank_maximum_loan_to_value','ASOF:2028-02-15');z=evaluate(x);ok('selected_amount_below_capacity_remains_valid_reference',z['state']=='internally_reconciled_reference' and z['capacity']=='150' and z['selected_principal']=='100')
    x=fixture();x['settlement_bridge']['valuation_claim']=vocabulary.money(201,'stock','VALUATION:2028-02-15');z=evaluate(x);ok('valuation_discrepancy_keeps_claim_and_residual',z['state']=='pending_reference' and any(i['cause'].startswith('valuation claim differs') and i['residual']=='1' for i in z['issues']))
    x=fixture();x['bank_underwriting_noi']={'state':'missing','causes':[{'field_id':'bank NOI','cause_kind':'missing','reason':'Not supplied'}]};z=evaluate(x);ok('missing_bank_noi_not_borrowed_from_valuation_noi',z['state']=='pending_reference' and z['issues'][0]['original_claim']['causes'][0]['reason']=='Not supplied' and 'capacity' not in z)
    x=fixture();x['limit_inventory_state']='unresolved';z=evaluate(x);ok('incomplete_restriction_inventory_not_two_limit_approval',z['state']=='pending_reference' and 'capacity' not in z)
    x=fixture();x['profile']='other_or_unresolved';z=evaluate(x);ok('no_interest_only_or_floating_profile_assumed_regular',z['state']=='pending_reference' and 'payment_per_regular_interval' not in z)
    x=fixture();x['disbursement_profile']='partial_or_noncash_unresolved';z=evaluate(x);ok('no_net_proceeds_or_partial_draw_inferred',z['state']=='pending_reference' and 'capacity' not in z)
    x=fixture();x['maturity_after_payment_count']=10;z=evaluate(x);ok('complete_amortization_differs_from_balloon',z['scheduled_principal_after_k_payments']=='0' and z['maturity_diagnostic']=='fully_amortized_in_declared_schedule')
    x=fixture();x['maturity_after_payment_count']=0;z=evaluate(x);ok('zero_elapsed_payments_not_missing',z['scheduled_principal_after_k_payments']=='100' and z['scheduled_payment_count_at_maturity']==0)
    for rate in [F(1,100),F(1,10**12)]:
        x=fixture();x['periodic_effective_rate']=ratio_q(rate,'periodic_effective_fraction','regular_payment_interval','PAYMENT-INTERVAL');z=evaluate(x)
        ok('positive_exact_rate_'+str(rate),F(z['payment_per_regular_interval'])>10 and F(z['scheduled_principal_after_k_payments'])>0)
    x=fixture();x['calculation_budget_payments']=0;z=evaluate(x);ok('insufficient_budget_not_math_or_financing_failure',z['state']=='pending_reference' and z['reason']=='explicit calculation budget insufficient')
    x=fixture();x['payments_per_year']=None;z=evaluate(x);ok('payment_frequency_not_inferred_from_rate',z['state']=='pending_reference' and 'annualized_regular_payment_equivalent' not in z)
    x=fixture();x['sizing_asof_date']='2028-02-14';z=evaluate(x);ok('valuation_date_difference_needs_contract',z['state']=='pending_reference' and z['issues'][0]['sizing_date']=='2028-02-14')
    x=fixture();x['bank_underwriting_noi']=vocabulary.money(0,'period_total','BANK-NOI-ANNUAL');x['selected_principal']=vocabulary.money(0,'stock','SELECTED-PRINCIPAL:NEW');s=x['settlement_bridge'];l=s['event_ledger'];l['cash_events'][0]['amount']=vocabulary.money(0,'period_total','P1');l['debt_events'][1]['principal_effect']=vocabulary.money(0,'period_total','P1');l['closing_debt_claims'][1]['amount']=vocabulary.money(0,'stock','CLOSING:P1');l['cash_events'].append(vocabulary.cash_event('EXPLICIT-EQUITY','equity_contribution','investor','free',100,'P1'));s['cash_classifications'].append({'cash_event_id':'EXPLICIT-EQUITY','role':'equity_contribution','evidence_ref':'SYNTHETIC-EQUITY-NOT-INVENTED-BY-SOLVER'});s['role_claims']['proceeds']=vocabulary.money(0,'period_total','P1');s['role_claims']['equity_contribution']=vocabulary.money(100,'period_total','P1');z=evaluate(x)
    ok('zero_loan_and_capacity_are_known_with_explicit_other_funding',z['state']=='internally_reconciled_reference' and z['capacity']=='0' and z['selected_principal']=='0' and z['settlement_reference']['ledger_reference']['gross_equity_contributions']=='100')
    ok('zero_service_dscr_remains_undefined',z['bank_dscr'] is None and z['bank_dscr_state']=='undefined_zero_service' and z['annualized_regular_payment_equivalent']=='0')
    x=fixture();x['maximum_ltv']=ratio_q(F(6,5),'ltv_fraction','bank_maximum_loan_to_value','ASOF:2028-02-15');z=evaluate(x)
    ok('no_unsupplied_one_hundred_percent_ltv_clamp',z['capacity_limits']['LTV']=='240' and z['binding_limits']==['DSCR'] and not z['credit_approval_verified'])
    x=fixture();x['other_capacity_limits']=[{'limit_id':'DOCUMENTED-CAP','amount':vocabulary.money(100,'stock','LOAN-CAPACITY:NEW'),'evidence_ref':'SYNTHETIC'}];z=evaluate(x)
    ok('additional_equal_limit_tie_not_discarded',z['binding_limits']==['DOCUMENTED-CAP','DSCR','LTV'])
    x=fixture();x['other_capacity_limits']=[{'limit_id':'OTHER','amount':{'state':'missing','causes':[{'field_id':'other limit','cause_kind':'missing','reason':'Not supplied'}]},'evidence_ref':'SYNTHETIC'}];z=evaluate(x)
    ok('missing_additional_limit_not_treated_as_unlimited',z['state']=='pending_reference' and 'capacity' not in z and z['issues'][0]['original_claim']['causes'][0]['reason']=='Not supplied')
    x=fixture();claims=[{'literal':'fixed rate','evidence_ref':'SYNTHETIC-A'},{'literal':'floating rate','evidence_ref':'SYNTHETIC-B'}];x.update(terms_state='conflict',term_claims=claims);z=evaluate(x)
    ok('conflicting_terms_preserve_alternatives',z['state']=='pending_reference' and z['original_terms']['term_claims']==claims)
    x=fixture();x['annual_service_convention']='dated_or_unresolved';z=evaluate(x)
    ok('no_assumed_annual_sizing_service_convention',z['state']=='pending_reference' and 'annual_debt_constant' not in z)
    x=fixture();x['payments_per_year']=12;z=evaluate(x)
    ok('annualized_payment_equivalent_not_dated_partial_year_cash',z['annualized_regular_payment_equivalent']=='120' and not z['dated_annual_service_computed'] and F(z['payment_per_regular_interval'])*x['amortization_payment_count']==100)
    mutations=[('context_mismatch',lambda x:x['context'].update(run_id='OTHER')),('wrong_loan',lambda x:x.update(loan_id='OTHER')),('sale_not_refinance',lambda x:x['settlement_bridge'].update(kind='sale')),('noi_currency_mismatch',lambda x:x['valuation_noi'].update(currency='OTHER')),('bank_noi_period_mismatch',lambda x:x['bank_underwriting_noi'].update(period_ref='VALUATION-NOI-ANNUAL')),('rate_convention_mismatch',lambda x:x['periodic_effective_rate'].update(unit_id='annual_nominal_fraction')),('ltv_basis_mismatch',lambda x:x['maximum_ltv'].update(basis='investment_criterion')),('duplicate_additional_limit',lambda x:x.update(other_capacity_limits=[{'limit_id':'X','amount':vocabulary.money(100,'stock','LOAN-CAPACITY:NEW'),'evidence_ref':'SYNTHETIC'}]*2)),('reserved_limit_id',lambda x:x.update(other_capacity_limits=[{'limit_id':'LTV','amount':vocabulary.money(100,'stock','LOAN-CAPACITY:NEW'),'evidence_ref':'SYNTHETIC'}])),('conflict_needs_alternative_claims',lambda x:x.update(terms_state='conflict')),('zero_amortization_count',lambda x:x.update(amortization_payment_count=0)),('fractional_payment_count',lambda x:x.update(amortization_payment_count=F(3,2))),('no_production_authorization',lambda x:x.update(authorization='granted'))]
    for name,mutate in mutations:reject(name,mutate)
    report={'status':'passed','total':len(checks),'checks':checks,'schemas_checked':len(vocabulary.STORE),'synthetic_example':evaluate(b),'scope':'Declared synthetic annual-NOI/cap valuation, regular fixed nonnegative-rate arrears amortization, explicit capacity inventory and full selected-principal gross-closing comparison only. Not authentic bank underwriting/commitments, annual-rate conversion, dated debt service, funding/distribution rights, tax/valuation approval, complete financial integration, independent audit or production.'}
    (ROOT/'references/refinance-capacity-bridge-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'references/fixtures/refinance-capacity-bridge-synthetic.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({'status':report['status'],'total':report['total'],'schemas_checked':report['schemas_checked']}))

if __name__=='__main__':main()
