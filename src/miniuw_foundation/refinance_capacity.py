"""T35 conditional valuation/bank capacity and selected gross refinance reconciliation."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .operating_noi import OperatingNoiRun,produce_operating_noi,_bounded,ArithmeticBudgetError
from .debt_closing import DatedLoanEvidence
from .debt_service import produce_debt_service,parse_loan_terms,_fraction,rational
from .closing_cash import ClosingCashRun,produce_closing_cash,parse_closing_cash
from .investor_returns import _date
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class RefinanceInputs:
    valuation_noi_raw:bytes
    valuation_noi_run:OperatingNoiRun
    bank_noi_raw:bytes
    bank_noi_run:OperatingNoiRun
    new_loan:DatedLoanEvidence
    closing_raw:bytes
    closing_run:ClosingCashRun
    def __post_init__(self):
        if any(type(b)is not bytes for b in [self.valuation_noi_raw,self.bank_noi_raw,self.closing_raw])or type(self.valuation_noi_run)is not OperatingNoiRun or type(self.bank_noi_run)is not OperatingNoiRun or type(self.new_loan)is not DatedLoanEvidence or type(self.closing_run)is not ClosingCashRun:raise ValidationError('immutable typed NOI/loan/closing evidence required')
        if sum(len(b)for b in [self.valuation_noi_raw,self.bank_noi_raw,self.closing_raw,self.new_loan.loan_raw])>4_194_304:raise ValidationError('refinance source transport budget exceeded')


def parse_refinance_capacity(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded explicit refinance capacity specification required')
    try:s=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid refinance capacity JSON')from error
    hashes={'valuation_noi_source_sha256','valuation_noi_run_sha256','bank_noi_source_sha256','bank_noi_run_sha256','new_loan_source_sha256','new_loan_run_sha256','closing_source_sha256','closing_run_sha256'}
    keys={'schema','profile','context','currency','as_of_date','valuation_noi_period_ref','bank_noi_period_ref','valuation_annual_basis_ref','bank_annual_basis_ref','scope_comparability_basis_ref','parameters','selected_principal','other_limits_declared_complete','other_limits_basis_ref','other_limits'}|hashes
    if type(s)is not dict or set(s)!=keys or s['schema']!='miniuw.synthetic-refinance-capacity.v1'or s['profile']!='SYNTHETIC-NOI-CAP-LTV-DSCR-FULL-DRAW-v1':raise ValidationError('exact conditional full-draw capacity profile required')
    if type(s['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**s['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    nonempty(s['currency'],'currency');_date(s['as_of_date'])
    for key in hashes:
        if type(s[key])is not str or not re.fullmatch('[a-f0-9]{64}',s[key]):raise ValidationError('exact producer/source SHA-256 required')
    for key in ['valuation_noi_period_ref','bank_noi_period_ref']:nonempty(s[key],key)
    for key in ['valuation_annual_basis_ref','bank_annual_basis_ref','scope_comparability_basis_ref','other_limits_basis_ref']:
        if s[key]is not None:nonempty(s[key],key)
    if s['other_limits_declared_complete']is not None and type(s['other_limits_declared_complete'])is not bool:raise ValidationError('explicit limit-inventory declaration or null required')
    if type(s['parameters'])is not dict or set(s['parameters'])!={'cap_rate','maximum_ltv','minimum_dscr'}:raise ValidationError('explicit cap/LTV/DSCR parameter records required')
    for row in s['parameters'].values():
        if type(row)is not dict or set(row)!={'value','unit','period_ref','source_ref'}:raise ValidationError('exact scalar parameter metadata required')
        _fraction(row['value'])
        for key in ['unit','period_ref','source_ref']:
            if row[key]is not None:nonempty(row[key],key)
    def money(row):
        if type(row)is not dict or set(row)!={'value','currency','as_of_date','basis','source_ref'}:raise ValidationError('exact dated principal/cap claim required')
        _fraction(row['value'])
        for key in ['currency','basis','source_ref']:
            if row[key]is not None:nonempty(row[key],key)
        if row['as_of_date']is not None:_date(row['as_of_date'])
    money(s['selected_principal'])
    if type(s['other_limits'])is not list or len(s['other_limits'])>64:raise ValidationError('bounded explicit other-limit inventory required')
    ids={'LTV','DSCR'}
    for row in s['other_limits']:
        if type(row)is not dict or set(row)!={'limit_id','amount'}:raise ValidationError('exact additional limit identity/amount required')
        nonempty(row['limit_id'],'limit_id')
        if row['limit_id']in ids:raise ValidationError('duplicate or reserved limit identity')
        ids.add(row['limit_id']);money(row['amount'])
    return s


def definition_sources():
    root=Path(__file__).resolve().parents[2];refs=[]
    for marker in ['## Entradas separadas','## Cuota y servicio para sizing','## Capacidades y selección','## Saldo, vencimiento y cero']:
        path='docs/refinance-capacity-bridge.md';data=(root/path).read_bytes();hits=[i+1 for i,line in enumerate(data.decode().splitlines())if line.startswith(marker)]
        if len(hits)!=1:raise ValidationError('refinance capacity locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(data).hexdigest()})
    return refs


@dataclass(frozen=True)
class RefinanceCapacityRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def size_refinance(inputs,spec_raw):
    if type(inputs)is not RefinanceInputs:raise ValidationError('typed refinance inputs required')
    v=inputs.valuation_noi_run;b=inputs.bank_noi_run;loan=inputs.new_loan;c=inputs.closing_run
    if produce_operating_noi(inputs.valuation_noi_raw)!=v or produce_operating_noi(inputs.bank_noi_raw)!=b or produce_debt_service(loan.loan_raw,loan.windows)!=loan.run or produce_closing_cash(inputs.closing_raw)!=c:raise ValidationError('every NOI/loan/closing producer must reproduce')
    s=parse_refinance_capacity(spec_raw);V=v.payload;B=b.payload;L=loan.run.payload;C=c.payload;terms=parse_loan_terms(loan.loan_raw);closing=parse_closing_cash(inputs.closing_raw)
    math=[];selection=[];lineage=[];value=K=ltv_cap=dscr_cap=capacity=selected=achieved_dscr=achieved_ltv=None;limits={};binding_limits=[];valuation_match=None
    actual={'valuation_noi_source_sha256':V['source_sha256'],'valuation_noi_run_sha256':v.sha256,'bank_noi_source_sha256':B['source_sha256'],'bank_noi_run_sha256':b.sha256,'new_loan_source_sha256':L['source_sha256'],'new_loan_run_sha256':loan.run.sha256,'closing_source_sha256':C['source_sha256'],'closing_run_sha256':c.sha256}
    for key,expected in actual.items():
        if s[key]!=expected:math.append(key+'_mismatch')
    for name,p in [('valuation',V),('bank',B),('loan',L),('closing',C)]:
        if p['context']!=s['context']:math.append(name+'_context_mismatch')
        if p['currency']!=s['currency']:math.append(name+'_currency_mismatch')
    for name,p in [('valuation',V),('bank',B)]:
        if p['period_ref']!=s[name+'_noi_period_ref']:math.append(name+'_period_mismatch')
        if p['calculation_status']!='computed_synthetic_profile':math.append(name+'_computed_noi_unavailable')
    if L['annual_sizing']['state']!='computed_synthetic':math.append('computed_annual_service_equivalent_unavailable')
    if L['annual_sizing']['period_ref']!=s['bank_noi_period_ref']:math.append('bank_noi_and_annual_equivalent_period_mismatch')
    for key in ['valuation_annual_basis_ref','bank_annual_basis_ref','scope_comparability_basis_ref']:
        if s[key]is None:math.append(key+'_missing')
    if s['other_limits_declared_complete']is not True or s['other_limits_basis_ref']is None:math.append('other_limit_inventory_not_explicitly_complete_with_basis')
    def scalar(key,unit,period,positive):
        row=s['parameters'][key];x=_fraction(row['value']);issues=[]
        if x is None or (x<=0 if positive else x<0):issues.append('value_missing_or_outside_profile_domain')
        if row['unit']!=unit or row['period_ref']!=period or row['source_ref']is None:issues.append('parameter_unit_period_or_source_mismatch')
        math.extend(key+':'+i for i in issues);lineage.append({'locator':'/parameters/'+key,'claim':row,'blockers':issues});return x if not issues else None
    def money(row,locator,basis,dest):
        x=_fraction(row['value']);issues=[]
        if x is None or x<0:issues.append('amount_missing_or_negative')
        if row['currency']!=s['currency']or row['as_of_date']!=s['as_of_date']or row['basis']!=basis or row['source_ref']is None:issues.append('currency_cutoff_basis_or_source_mismatch')
        dest.extend(locator+':'+i for i in issues);lineage.append({'locator':locator,'claim':row,'blockers':issues});return None if issues else x
    try:
        cap=scalar('cap_rate','annual_cap_fraction',s['valuation_noi_period_ref'],True);ltv=scalar('maximum_ltv','scalar','SYNTHETIC-sizing-at-date',False);dscr=scalar('minimum_dscr','x',s['bank_noi_period_ref'],True)
        N=_fraction(V['noi'],1300)if V['noi']is not None else None;bankN=_fraction(B['noi'],1300)if B['noi']is not None else None
        if N is not None and N<0:math.append('negative_valuation_noi_no_negative_property_value_inferred')
        if bankN is not None and bankN<0:math.append('negative_bank_noi_no_negative_loan_inferred')
        if N is not None and N>=0 and cap is not None:value=_bounded(N/cap)
        if value is not None and ltv is not None:ltv_cap=_bounded(ltv*value);limits['LTV']=ltv_cap
        unit=_fraction(L['payment_per_unit'],1300)if L['payment_per_unit']is not None else None
        if unit is not None and L['annual_sizing']['state']=='computed_synthetic':K=_bounded(unit*terms['payments_per_year'])
        if K is not None and K>0 and dscr is not None and bankN is not None and bankN>=0:dscr_cap=_bounded(bankN/_bounded(dscr*K));limits['DSCR']=dscr_cap
        for index,row in enumerate(s['other_limits']):
            x=money(row['amount'],'/other_limits/'+str(index)+'/amount','additional_bank_principal_limit',math)
            if x is not None:limits[row['limit_id']]=x
        if not math and len(limits)==2+len(s['other_limits']):capacity=min(limits.values());binding_limits=sorted(k for k,x in limits.items()if x==capacity)
        selected=money(s['selected_principal'],'/selected_principal','selected_new_loan_principal',selection)
        if C['kind']!='refinance':selection.append('refinance_closing_required')
        if C['closing_date']!=s['as_of_date']:selection.append('sizing_and_closing_cutoff_mismatch')
        if C['state']!='computed_synthetic_closing':selection.append('closing_plan_blocked')
        if terms['origination_date']!=s['as_of_date']:selection.append('new_loan_origination_must_match_closing')
        if closing['new_loan']is None or closing['new_loan']['loan_id']!=L['loan_id']:selection.append('new_loan_identity_mismatch')
        if selected is not None:
            if capacity is None:selection.append('complete_capacity_unavailable')
            elif selected>capacity:selection.append('selected_principal_exceeds_declared_bank_capacity')
            for name,x in [('loan_original_principal',_fraction(terms['principal'])),('gross_closing_proceeds',_fraction(closing['amounts']['gross_proceeds']['value'])),('new_closing_principal',None if closing['new_loan']is None else _fraction(closing['new_loan']['principal_after_closing']['value']))]:
                if x is None or selected!=x:selection.append(name+'_differs_from_selected_principal')
            if K is not None and selected>0 and bankN is not None:achieved_dscr=_bounded(bankN/_bounded(K*selected))
            if value is not None and value>0:achieved_ltv=_bounded(selected/value)
        claim=closing['valuation_claim']
        if claim is not None:
            claimed=money(claim,'/closing/valuation_claim','valuation_not_cash',selection)
            if claimed is not None and value is not None:
                valuation_match=claimed==value
                if not valuation_match:selection.append('closing_valuation_claim_differs_from_computed_noi_cap_value')
    except ArithmeticBudgetError:
        math.append('refinance_capacity_exact_arithmetic_budget_exceeded');capacity=None;binding_limits=[];achieved_dscr=achieved_ltv=None
    q=lambda x:None if x is None else rational(x)
    blockers=sorted(set(math+selection));p={'component':'T35','purpose':'conditional_synthetic_refinance_valuation_capacity_selection','engine_sha256':ENGINE_SHA256,'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'input_bindings':actual,'definition_sources':definition_sources(),'context':s['context'],'currency':s['currency'],'as_of_date':s['as_of_date'],
        'valuation_noi':V['noi'],'bank_noi':B['noi'],'computed_property_value':q(value),'regular_annual_sizing_constant':q(K),'capacity_limits':{k:rational(x)for k,x in limits.items()},'maximum_principal_capacity':q(capacity),'binding_limit_ids':binding_limits,'selected_principal':q(selected),'achieved_dscr_annual_sizing_only':q(achieved_dscr),'achieved_ltv':q(achieved_ltv),'achieved_dscr_undefined_reason':'zero_selected_service'if selected==0 and K is not None else None,'closing_valuation_claim_matches_calculation':valuation_match,
        'capacity_state':'computed_synthetic'if capacity is not None else'blocked','state':'compatible_synthetic_refinance_capacity'if capacity is not None and not blockers else'blocked','blockers':blockers,'capacity_blockers':sorted(set(math)),'selection_blockers':sorted(set(selection)),'valuation_noi_blockers':V['blockers'],'bank_noi_blockers':B['blockers'],'lineage':lineage,
        'bank_limits_are_supplied_not_investment_criteria':True,'annual_sizing_is_actual_dated_cash':False,'source_scope_financially_verified':False,'other_limits_completeness_verified':False,'property_appraisal_verified':False,'bank_credit_approved':False,'funds_available_verified':False,'bank_policy_adopted':False,'whole_project_cash_reconciled':False,'distribution_authorized':False,'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return RefinanceCapacityRun(encoded,digest(encoded))
