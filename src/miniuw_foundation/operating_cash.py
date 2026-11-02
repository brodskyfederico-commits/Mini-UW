"""T25 explicit synthetic accrued NOI -> cash reconciliation -> proposed allocation.

One declared period only. Neither a due schedule nor a positive residual authorizes
payment/distribution. All cash amounts and allocation choices remain source claims.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational
from .operating_noi import OperatingNoiRun,produce_operating_noi,_bounded,ArithmeticBudgetError
from .investor_returns import _date

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-operating-cash.v1'
WORKING=('receivables','advance_income','payables','prepaid_expenses')
STOCKS={'opening_free_cash':'OPENING:','opening_restricted_cash':'OPENING:',
    'closing_free_cash_claim':'CLOSING:','closing_restricted_cash_claim':'CLOSING:'}
FLOWS=('debt_principal_payment','debt_interest_payment','debt_fee_payment','capital_expenditure',
    'other_cash_payment','nonfinancing_other_cash_receipt','reserve_deposit','reserve_release',
    'equity_contribution','planned_operating_distribution')
ADJUSTMENTS=('noncash_revenue','noncash_expense')
CLAIMS=('operating_receipts_claim','operating_payments_claim')


def parse_operating_cash(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded explicit synthetic cash specification required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid operating cash JSON')from error
    keys={'schema','context','currency','period_ref','start_date','end_date','cash_date','period_basis_ref',
        'noi_source_sha256','noi_run_sha256','scope_inventory_declared_complete','distribution_basis_ref','classification_basis_ref',
        'profile','working_balances','amounts'}
    if type(p)is not dict or set(p)!=keys or p['schema']!=SCHEMA or p['profile']!='explicit_accrual_cash_and_planned_allocation_operations_only':raise ValidationError('exact supported operating cash profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    for k in ['currency','period_ref']:nonempty(p[k],k)
    for k in ['period_basis_ref','distribution_basis_ref','classification_basis_ref']:
        if p[k]is not None:nonempty(p[k],k)
    for k in ['noi_source_sha256','noi_run_sha256']:
        if type(p[k])is not str or not re.fullmatch('[a-f0-9]{64}',p[k]):raise ValidationError('exact producer/source hashes required')
    if p['scope_inventory_declared_complete']is not None and type(p['scope_inventory_declared_complete'])is not bool:raise ValidationError('explicit inventory declaration or null required')
    start,end,cash=(_date(p[k])for k in ['start_date','end_date','cash_date'])
    if not start<=cash<end:raise ValidationError('cash date must lie in explicit half-open period')
    def amount(row):
        if type(row)is not dict or set(row)!={'value','currency','period_ref','source_ref'}:raise ValidationError('exact amount metadata required')
        _fraction(row['value'])
        for k in ['currency','period_ref','source_ref']:
            if row[k]is not None:nonempty(row[k],k)
    if type(p['working_balances'])is not dict or set(p['working_balances'])!=set(WORKING):raise ValidationError('all four explicit working-balance families required')
    for pair in p['working_balances'].values():
        if type(pair)is not dict or set(pair)!={'opening','closing'}:raise ValidationError('explicit opening/closing working balances required')
        for row in pair.values():amount(row)
    if type(p['amounts'])is not dict or set(p['amounts'])!=set(STOCKS)|set(FLOWS)|set(ADJUSTMENTS)|set(CLAIMS):raise ValidationError('all cash claims/uses including zero required')
    for row in p['amounts'].values():amount(row)
    return p


def definition_sources():
    path='docs/operating-settlement-bridges.md';raw=(Path(__file__).resolve().parents[2]/path).read_bytes();lines=raw.decode().splitlines();refs=[]
    for marker in ['## Operación devengada y caja','## Estado de cierre y ledger']:
        hits=[i+1 for i,line in enumerate(lines)if line.startswith(marker)]
        if len(hits)!=1:raise ValidationError('cash definition locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return refs


@dataclass(frozen=True)
class OperatingCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_operating_cash(noi_raw,noi_run,spec_raw):
    if type(noi_run)is not OperatingNoiRun or produce_operating_noi(noi_raw)!=noi_run:raise ValidationError('NOI source/run must reproduce before cash consumption')
    s=parse_operating_cash(spec_raw);n=noi_run.payload;refs=definition_sources();upstream=[];accrual=[];allocation=[];lineage=[]
    for key,actual in [('noi_source_sha256',n['source_sha256']),('noi_run_sha256',noi_run.sha256)]:
        if s[key]!=actual:upstream.append(key+'_mismatch')
    if n['context']!=s['context']:upstream.append('producer_context_mismatch')
    if n['currency']!=s['currency']:upstream.append('producer_currency_mismatch')
    if n['period_ref']!=s['period_ref']:upstream.append('producer_period_mismatch')
    if s['period_basis_ref']is None:upstream.append('period_basis_missing')
    if s['classification_basis_ref']is None:upstream.append('cash_classification_and_no_overlap_basis_missing')
    if s['scope_inventory_declared_complete']is not True:upstream.append('cash_scope_inventory_not_declared_complete')
    if n['calculation_status']!='computed_synthetic_profile':upstream.append('computed_noi_unavailable')
    def amount(row,locator,period,issues,signed=False):
        bad=[];v=_fraction(row['value'])
        if v is None:bad.append('amount_missing')
        elif v<0 and not signed:bad.append('negative_gross_amount_unsupported')
        if row['currency']!=s['currency']:bad.append('currency_missing_or_mismatch')
        if row['period_ref']!=period:bad.append('period_or_cutoff_missing_or_mismatch')
        if row['source_ref']is None:bad.append('source_reference_missing')
        issues.extend(locator+':'+b for b in bad);lineage.append({'locator':locator,'source_ref':row['source_ref'],'declared_value':row['value'],'blockers':bad})
        return None if bad else v
    receipts=payments=net=available=close_free=close_restricted=distribution=contribution=None
    receipts_residual=payments_residual=free_residual=restricted_residual=conservation=None;deltas={};vals={}
    try:
        for family in WORKING:
            pair=s['working_balances'][family];v={}
            for cutoff,prefix in [('opening','OPENING:'),('closing','CLOSING:')]:
                v[cutoff]=amount(pair[cutoff],'/working_balances/'+family+'/'+cutoff,prefix+s['period_ref'],accrual)
            deltas[family]=None if None in v.values()else _bounded(v['closing']-v['opening'])
        for key in ADJUSTMENTS+CLAIMS:
            vals[key]=amount(s['amounts'][key],'/amounts/'+key,s['period_ref'],accrual,signed=key in ADJUSTMENTS)
        if not upstream and not accrual:
            income=_fraction(n['income_total'],1300);expenses=_fraction(n['expenses_excluding_tax'],1300);tax=_fraction(n['property_tax'],1300)
            receipts=_bounded(income-vals['noncash_revenue']-deltas['receivables']+deltas['advance_income'])
            payments=_bounded(expenses+tax-vals['noncash_expense']-deltas['payables']+deltas['prepaid_expenses'])
            net=_bounded(receipts-payments)
            receipts_residual=_bounded(vals['operating_receipts_claim']-receipts);payments_residual=_bounded(vals['operating_payments_claim']-payments)
            if receipts<0 or payments<0:accrual.append('negative_computed_gross_cash_requires_separate_profile')
            if receipts_residual!=0:accrual.append('operating_receipts_claim_mismatch')
            if payments_residual!=0:accrual.append('operating_payments_claim_mismatch')
        for key,prefix in STOCKS.items():vals[key]=amount(s['amounts'][key],'/amounts/'+key,prefix+s['period_ref'],allocation)
        for key in FLOWS:vals[key]=amount(s['amounts'][key],'/amounts/'+key,s['period_ref'],allocation)
        if s['distribution_basis_ref']is None:allocation.append('distribution_basis_missing')
        if not upstream and not accrual and not allocation:
            debt=_bounded(vals['debt_principal_payment']+vals['debt_interest_payment']+vals['debt_fee_payment'])
            available=_bounded(vals['opening_free_cash']+net+vals['nonfinancing_other_cash_receipt']+vals['reserve_release']+vals['equity_contribution']-debt-vals['capital_expenditure']-vals['other_cash_payment']-vals['reserve_deposit'])
            close_free=_bounded(available-vals['planned_operating_distribution'])
            close_restricted=_bounded(vals['opening_restricted_cash']+vals['reserve_deposit']-vals['reserve_release'])
            free_residual=_bounded(vals['closing_free_cash_claim']-close_free);restricted_residual=_bounded(vals['closing_restricted_cash_claim']-close_restricted)
            conservation=_bounded(vals['opening_free_cash']+vals['opening_restricted_cash']+receipts+vals['nonfinancing_other_cash_receipt']+vals['equity_contribution']-payments-debt-vals['capital_expenditure']-vals['other_cash_payment']-vals['planned_operating_distribution']-vals['closing_free_cash_claim']-vals['closing_restricted_cash_claim'])
            if close_free<0:allocation.append('negative_free_cash_no_automatic_funding_or_distribution_cut')
            if close_restricted<0:allocation.append('negative_restricted_cash_no_automatic_release_funding')
            if free_residual!=0:allocation.append('closing_free_cash_claim_mismatch')
            if restricted_residual!=0:allocation.append('closing_restricted_cash_claim_mismatch')
            if conservation!=0:allocation.append('total_cash_conservation_mismatch')
            if not allocation:distribution=vals['planned_operating_distribution'];contribution=vals['equity_contribution']
    except ArithmeticBudgetError:
        allocation.append('exact_cash_arithmetic_budget_exceeded');distribution=contribution=available=close_free=close_restricted=None
    blockers=sorted(set(upstream+accrual+allocation));q=lambda v:None if v is None else rational(v)
    payload={'component':'T25','purpose':'synthetic_single_period_operating_cash_and_proposed_allocation','engine_sha256':ENGINE_SHA256,
        'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'noi_source_sha256':n['source_sha256'],'noi_run_sha256':noi_run.sha256,
        'definition_sources':refs,'context':s['context'],'currency':s['currency'],'period_ref':s['period_ref'],
        'start_date':s['start_date'],'end_date':s['end_date'],'cash_date':s['cash_date'],'computed_noi':n['noi'],
        'working_balance_changes':{k:q(v)for k,v in deltas.items()},'expected_operating_receipts':q(receipts),'expected_operating_payments':q(payments),'net_operating_cash':q(net),
        'receipts_claim_residual':q(receipts_residual),'payments_claim_residual':q(payments_residual),
        'free_cash_before_proposed_distribution':q(available),'expected_closing_free_cash':q(close_free),'expected_closing_restricted_cash':q(close_restricted),
        'free_cash_claim_residual':q(free_residual),'restricted_cash_claim_residual':q(restricted_residual),'total_cash_conservation_residual':q(conservation),
        'exportable_operating_distribution':q(distribution),'exportable_equity_contribution':q(contribution),
        'accrual_cash_state':'computed_synthetic'if all(v is not None for v in [receipts,payments,net]) and not upstream and not accrual else'blocked',
        'state':'reconciled_synthetic_plan'if distribution is not None and not blockers else'blocked',
        'blockers':blockers,'noi_blockers':n['blockers'],'lineage':lineage,'producer_arithmetic_replayed':True,
        'period_scope_only':True,'multi_period_continuity_verified':False,'intraperiod_liquidity_verified':False,
        'cash_projection_actuality_verified':False,'debt_cash_schedule_verified':False,'distribution_authorized':False,
        'tax_policy_adopted':False,'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(payload);return OperatingCashRun(encoded,digest(encoded))
