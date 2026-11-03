"""T57 explicit zero-opening pre-operating cash; no interest or funding solver."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError
from .investor_returns import _date
from .holding_cash import OperatingPeriodEvidence,verify_period_evidence
from .operating_cash import WORKING

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-preopening-cash.v1'
CATEGORIES=('initial_equity_contribution','additional_equity_contribution','equity_distribution',
    'loan_draw','loan_principal_repayment','debt_interest_payment','debt_fee_payment',
    'acquisition_payment','construction_payment','soft_cost_payment','other_cash_payment',
    'other_cash_receipt','reserve_deposit','reserve_release')
LOAN_CATEGORIES={'loan_draw','loan_principal_repayment','debt_interest_payment','debt_fee_payment'}
EQUITY_CATEGORIES={'initial_equity_contribution','additional_equity_contribution','equity_distribution'}


def _object(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded immutable preopening source bytes required')
    try:return json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid preopening JSON')from error


def _claim(row):
    if type(row)is not dict or set(row)!={'value','currency','source_ref'}:raise ValidationError('exact cash amount and provenance fields required')
    _fraction(row['value'])
    for key in ['currency','source_ref']:
        if row[key]is not None:nonempty(row[key],key)


def parse_preopening_cash(raw):
    p=_object(raw)
    keys={'schema','profile','context','currency','start_date','opening_operation_date',
        'inventory_declared_complete','zero_opening_basis_ref','classification_basis_ref',
        'boundary_basis_ref','loan_ids','events','terminal_claims'}
    if type(p)is not dict or set(p)!=keys or p['schema']!=SCHEMA or p['profile']!='SYNTHETIC-ZERO-OPENING-PREOPERATING-CASH-v1':raise ValidationError('exact zero-opening preoperating cash profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    nonempty(p['currency'],'currency')
    start,end=_date(p['start_date']),_date(p['opening_operation_date'])
    if not start<end:raise ValidationError('positive explicit preopening horizon required')
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('explicit completeness declaration or null required')
    for key in ['zero_opening_basis_ref','classification_basis_ref','boundary_basis_ref']:
        if p[key]is not None:nonempty(p[key],key)
    if type(p['loan_ids'])is not list or len(p['loan_ids'])>32:raise ValidationError('bounded explicit loan inventory required, including empty')
    for loan in p['loan_ids']:nonempty(loan,'loan_id')
    if len(set(p['loan_ids']))!=len(p['loan_ids']):raise ValidationError('duplicate loan identity')
    if type(p['events'])is not list or not 1<=len(p['events'])<=256:raise ValidationError('one to 256 explicit ordered cash events required')
    seen=set();previous=None
    for event in p['events']:
        if type(event)is not dict or set(event)!={'event_id','date','category','loan_id','amount'}:raise ValidationError('exact dated gross cash event required')
        nonempty(event['event_id'],'event_id')
        if event['event_id']in seen:raise ValidationError('duplicate cash event identity')
        seen.add(event['event_id']);date=_date(event['date'])
        if not start<=date<=end or previous is not None and date<previous:raise ValidationError('events must be ordered within the declared closed horizon')
        previous=date
        if type(event['category'])is not str or event['category']not in CATEGORIES:raise ValidationError('supported explicit gross cash category required')
        if event['loan_id']is not None:nonempty(event['loan_id'],'loan_id')
        if event['category']not in LOAN_CATEGORIES and event['loan_id']is not None:raise ValidationError('non-debt event cannot carry a loan identity')
        _claim(event['amount'])
    terminal=p['terminal_claims']
    if type(terminal)is not dict or set(terminal)!={'free_cash','restricted_cash','loan_principal'}:raise ValidationError('exact closing cash and principal claims required')
    if type(terminal['loan_principal'])is not dict or set(terminal['loan_principal'])!=set(p['loan_ids']):raise ValidationError('closing principal claim for every and only declared loan required')
    for row in [terminal['free_cash'],terminal['restricted_cash'],*terminal['loan_principal'].values()]:_claim(row)
    return p


def definition_sources():
    root=Path(__file__).resolve().parents[2];result=[]
    for path,marker in [('docs/model-cash-contracts.md','## 3. Identidades de control'),('docs/model-construction-finance.md','## Identidades de deuda, caja e interés'),('docs/technical-implementation-T57.md','# T57')]:
        raw=(root/path).read_bytes();lines=[i+1 for i,line in enumerate(raw.decode().splitlines())if line.startswith(marker)]
        if len(lines)!=1:raise ValidationError('preopening definition location changed')
        result.append({'path':path,'line':lines[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return result


@dataclass(frozen=True)
class PreopeningCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_preopening_cash(raw):
    p=parse_preopening_cash(raw);blockers=[];totals=None;balances=None;checks=[];equity=None;residual=None
    if p['inventory_declared_complete']is not True:blockers.append('preopening_inventory_not_declared_complete')
    for key in ['zero_opening_basis_ref','classification_basis_ref','boundary_basis_ref']:
        if p[key]is None:blockers.append(key+'_missing')
    def value(row,locator):
        v=_fraction(row['value'])
        if v is None:blockers.append(locator+':amount_missing')
        elif v<0:blockers.append(locator+':gross_amount_negative')
        if row['currency']!=p['currency']:blockers.append(locator+':currency_mismatch')
        if row['source_ref']is None:blockers.append(locator+':source_ref_missing')
        return v
    values=[]
    for i,event in enumerate(p['events']):
        values.append(value(event['amount'],'/events/'+str(i)+'/amount'))
        if event['category']in LOAN_CATEGORIES and event['loan_id']not in p['loan_ids']:blockers.append(event['event_id']+':declared_loan_identity_missing_or_unknown')
    terminal=p['terminal_claims'];claimed={}
    for key in ['free_cash','restricted_cash']:claimed[key]=value(terminal[key],'/terminal_claims/'+key)
    for loan,row in terminal['loan_principal'].items():claimed['loan:'+loan]=value(row,'/terminal_claims/loan_principal/'+loan)
    if not blockers:
        try:
            totals={key:Fraction(0)for key in CATEGORIES};free=restricted=Fraction(0);loans={key:Fraction(0)for key in p['loan_ids']};balances=[]
            for i,(event,v)in enumerate(zip(p['events'],values)):
                category=event['category'];loan=event['loan_id'];totals[category]=_bounded(totals[category]+v)
                if category in {'initial_equity_contribution','additional_equity_contribution','loan_draw','other_cash_receipt','reserve_release'}:free=_bounded(free+v)
                else:free=_bounded(free-v)
                if category=='reserve_deposit':restricted=_bounded(restricted+v)
                elif category=='reserve_release':restricted=_bounded(restricted-v)
                elif category=='loan_draw':loans[loan]=_bounded(loans[loan]+v)
                elif category=='loan_principal_repayment':loans[loan]=_bounded(loans[loan]-v)
                if i+1==len(p['events'])or p['events'][i+1]['date']!=event['date']:
                    balances.append({'date':event['date'],'free_cash':rational(free),'restricted_cash':rational(restricted),'loan_principal':{k:rational(v)for k,v in loans.items()}})
                    for key,v in [('free_cash',free),('restricted_cash',restricted),*[(('loan:'+k),v)for k,v in loans.items()]]:
                        if v<0:blockers.append(event['date']+':'+key+':negative_date_close_balance')
            for key,actual in [('free_cash',free),('restricted_cash',restricted),*[(('loan:'+k),v)for k,v in loans.items()]]:
                equal=actual==claimed[key];checks.append({'balance':key,'computed':rational(actual),'claimed':rational(claimed[key]),'equal_exact_value':equal})
                if not equal:blockers.append(key+':terminal_claim_mismatch')
            sources=_bounded(sum((totals[k]for k in ['initial_equity_contribution','additional_equity_contribution','loan_draw','other_cash_receipt']),Fraction(0)))
            uses=_bounded(sum((totals[k]for k in CATEGORIES if k not in {'initial_equity_contribution','additional_equity_contribution','loan_draw','other_cash_receipt','reserve_deposit','reserve_release'}),Fraction(0)))
            residual=_bounded(sources-uses-free-restricted)
            if residual!=0:blockers.append('preopening_cash_conservation_mismatch')
            if not blockers:
                equity=[{'event_id':e['event_id'],'date':e['date'],'kind':'distribution'if e['category']=='equity_distribution'else'contribution',
                    'category':{'initial_equity_contribution':'initial_capital','additional_equity_contribution':'additional_capital','equity_distribution':'other_distribution'}[e['category']],
                    'amount':e['amount']['value'],'currency':p['currency'],'source_pointer':'/events/'+str(i)+'/amount','source_sha256':hashlib.sha256(raw).hexdigest()}for i,e in enumerate(p['events'])if e['category']in EQUITY_CATEGORIES]
        except ArithmeticBudgetError:
            blockers.append('preopening_exact_arithmetic_budget_exceeded');totals=None;balances=None;checks=[];equity=None;residual=None
    result={'component':'T57','purpose':'synthetic_preoperating_cash_and_declared_principal','engine_sha256':ENGINE_SHA256,
        'source_sha256':hashlib.sha256(raw).hexdigest(),'definition_sources':definition_sources(),'context':p['context'],'currency':p['currency'],
        'start_date':p['start_date'],'opening_operation_date':p['opening_operation_date'],'events':p['events'],
        'zero_opening_cash_and_principal_assumed':True,'date_close_balances':balances,'terminal_checks':checks,
        'totals':None if totals is None else{k:rational(v)for k,v in totals.items()},'cash_conservation_residual':None if residual is None else rational(residual),
        'exportable_equity_movements':equity,'blockers':sorted(set(blockers)),'state':'reconciled_synthetic_preopening_cash'if not blockers else'blocked',
        'interest_and_fees_are_supplied_cash_not_calculated':True,'capitalized_interest_or_direct_bank_payments_supported':False,
        'loan_commitment_or_availability_verified':False,'debt_schedule_and_maturity_verified':False,'intraday_order_and_liquidity_verified':False,
        'asset_cost_basis_or_complete_TDC_verified':False,'actual_cash_and_payment_history_verified':False,
        'investor_returns_connected':False,'decision':'PENDING','financial_module_closed':False,'production_authorized':False}
    encoded=canonical(result);return PreopeningCashRun(encoded,digest(encoded))


@dataclass(frozen=True)
class PreopeningOperationLinkRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def link_preopening_to_operation(raw,run,period,binding_raw):
    if type(run)is not PreopeningCashRun or reconcile_preopening_cash(raw)!=run:raise ValidationError('preopening source and result must fully reproduce')
    if type(period)is not OperatingPeriodEvidence:raise ValidationError('complete immutable operating period evidence required')
    verified=verify_period_evidence((period,));spec=next(iter(verified.values()))[1];cash=period.cash_run.payload;p=run.payload;b=_object(binding_raw)
    keys={'schema','preopening_source_sha256','preopening_run_sha256','operating_source_sha256','operating_run_sha256','boundary_basis_ref'}
    if type(b)is not dict or set(b)!=keys or b['schema']!='miniuw.synthetic-preopening-operation-link.v1':raise ValidationError('exact source-bound cash-only opening link required')
    actual={'preopening_source_sha256':hashlib.sha256(raw).hexdigest(),'preopening_run_sha256':run.sha256,'operating_source_sha256':hashlib.sha256(period.spec_raw).hexdigest(),'operating_run_sha256':period.cash_run.sha256}
    blockers=[];checks=[]
    for key,v in actual.items():
        if type(b[key])is not str or len(b[key])!=64 or any(c not in '0123456789abcdef'for c in b[key]):raise ValidationError('exact binding SHA-256 required')
        if b[key]!=v:blockers.append(key+'_mismatch')
    if b['boundary_basis_ref']is None:blockers.append('preopening_operation_boundary_basis_missing')
    else:nonempty(b['boundary_basis_ref'],'boundary_basis_ref')
    if p['state']!='reconciled_synthetic_preopening_cash':blockers.append('preopening_cash_blocked')
    if cash['state']!='reconciled_synthetic_plan':blockers.append('opening_operating_cash_blocked')
    for key in ['context','currency']:
        if p[key]!=cash[key]:blockers.append('preopening_operation_'+key+'_mismatch')
    if p['opening_operation_date']!=cash['start_date']:blockers.append('preopening_operation_boundary_date_mismatch')
    if not blockers:
        last=p['date_close_balances'][-1]
        for name in ['free_cash','restricted_cash']:
            claim=spec['amounts']['opening_'+name];equal=_fraction(last[name],1300)==_fraction(claim['value'])
            checks.append({'account':name,'preopening_terminal_amount':last[name],'operating_opening_claim':claim,'equal_exact_value':equal})
            if not equal:blockers.append(name+':opening_does_not_equal_preopening_close')
        for name in WORKING:
            # This cash-only profile cannot carry preopening accruals into operations.
            if _fraction(spec['working_balances'][name]['opening']['value'])!=0:blockers.append(name+':nonzero_opening_working_balance_requires_separate_profile')
    result={'component':'T57','purpose':'synthetic_preopening_to_operating_cash_only','engine_sha256':ENGINE_SHA256,
        'binding_source_sha256':hashlib.sha256(binding_raw).hexdigest(),'source_bindings':actual,'definition_sources':definition_sources(),
        'context':p['context'],'currency':p['currency'],'cash_boundary_checks':checks,'preopening_blockers':p['blockers'],'operating_blockers':cash['blockers'],
        'blockers':sorted(set(blockers)),'state':'matched_synthetic_cash_only'if not blockers else'blocked',
        'opening_cash_must_not_be_added_as_another_equity_contribution':True,'debt_carry_reconciliation_pending':True,
        'asset_basis_and_accrual_carry_verified':False,'whole_project_investor_returns_connected':False,
        'financial_module_closed':False,'decision':'PENDING','production_authorized':False}
    encoded=canonical(result);return PreopeningOperationLinkRun(encoded,digest(encoded))
