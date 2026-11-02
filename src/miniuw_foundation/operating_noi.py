"""T19 conditional synthetic accrued NOI; no tax-law or policy adoption."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-operating-noi.v1'
PROFILE='SYNTHETIC-M2-MAX-TAX-v1'
MONEY_KEYS={'value','currency','period_ref','unit','basis','source_ref'}
ASSUMPTIONS={'same_period_accrual':True,'tax_model':'max_floor_or_fixed_coefficient_times_noi',
    'coefficient_fixed':True,'additional_tax_adjustments':False,'rounding':'none_exact'}
MAX_BITS=4096


class ArithmeticBudgetError(ValidationError):pass


def _bounded(value):
    if value.numerator.bit_length()>MAX_BITS or value.denominator.bit_length()>MAX_BITS:raise ArithmeticBudgetError('exact arithmetic budget exceeded')
    return value


def parse_operating_noi(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded synthetic NOI source required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid NOI source JSON')from error
    if type(p)is not dict or set(p)!={'schema','profile_id','context','currency','period_ref','income_rows','expense_rows','tax_floor','tax_coefficient','modelling_assumptions'}or p['schema']!=SCHEMA or p['profile_id']!=PROFILE:
        raise ValidationError('exact supported synthetic NOI profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    if type(p['modelling_assumptions'])is not dict or set(p['modelling_assumptions'])!=set(ASSUMPTIONS):raise ValidationError('explicit profile assumptions required')
    for k,v in ASSUMPTIONS.items():
        if type(p['modelling_assumptions'][k])is not type(v)or p['modelling_assumptions'][k]!=v:raise ValidationError('unsupported NOI profile assumption: '+k)
    for k in ['currency','period_ref']:
        if p[k]is not None:nonempty(p[k],k)
    seen=set()
    for family in ['income_rows','expense_rows']:
        if type(p[family])is not list or len(p[family])>64:raise ValidationError('bounded explicit operating row inventory required')
        for row in p[family]:
            if type(row)is not dict or set(row)!=MONEY_KEYS|{'item_id'}:raise ValidationError('exact operating amount metadata required')
            nonempty(row['item_id'],'item_id')
            if row['item_id']in seen:raise ValidationError('operating item identity duplicated across inventories')
            seen.add(row['item_id']);_fraction(row['value'])
            for k in MONEY_KEYS-{'value'}:
                if row[k]is not None:nonempty(row[k],k)
    floor=p['tax_floor']
    if type(floor)is not dict or set(floor)!=MONEY_KEYS:raise ValidationError('exact tax-floor amount required')
    _fraction(floor['value'])
    for k in MONEY_KEYS-{'value'}:
        if floor[k]is not None:nonempty(floor[k],k)
    coefficient=p['tax_coefficient']
    if type(coefficient)is not dict or set(coefficient)!={'value','unit','source_ref'}:raise ValidationError('exact fixed-coefficient record required')
    _fraction(coefficient['value'])
    for k in ['unit','source_ref']:
        if coefficient[k]is not None:nonempty(coefficient[k],k)
    return p


def definition_sources():
    path='docs/model-operations-contract.md';raw=(Path(__file__).resolve().parents[2]/path).read_bytes();lines=raw.decode().splitlines();refs=[]
    for marker in ['| M2-06 |','`N = A − max(F, k N)`','`N = min(A−F, A/(1+k)); T = A−N = max(F, k N)`']:
        hits=[i+1 for i,l in enumerate(lines)if l.startswith(marker)]
        if len(hits)!=1:raise ValidationError('NOI definition locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return refs


@dataclass(frozen=True)
class OperatingNoiRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def produce_operating_noi(raw):
    p=parse_operating_noi(raw);refs=definition_sources();blockers=[];lineage=[]
    def amount(row,locator):
        issues=[]
        for field in ['currency','period_ref']:
            if p[field]is None or row[field]is None or row[field]!=p[field]:issues.append(field+'_missing_or_mismatch')
        if row['unit']!='currency_per_declared_period':issues.append('amount_unit_missing_or_mismatch')
        if row['basis']!='accrual':issues.append('accrual_basis_missing_or_mismatch')
        if row['source_ref']is None:issues.append('declared_source_ref_missing')
        value=_fraction(row['value'])
        if value is None:issues.append('amount_missing')
        blockers.extend(locator+':'+reason for reason in issues)
        lineage.append({'locator':locator,'item_id':row.get('item_id'),'source_ref':row['source_ref'],'declared_value':row['value'],'blockers':issues})
        return None if issues else value
    totals={};before=None;noi=None;tax=None;branch=None;residual=None
    try:
        for family in ['income_rows','expense_rows']:
            values=[amount(row,'/'+family+'/'+str(i))for i,row in enumerate(p[family])]
            if not values:blockers.append('/'+family+':inventory_empty_not_assumed_zero')
            total=Fraction(0)
            for value in values:
                if value is not None:total=_bounded(total+value)
            totals[family]=None if not values or any(v is None for v in values)else total
        if all(totals.get(f)is not None for f in ['income_rows','expense_rows']):before=_bounded(totals['income_rows']-totals['expense_rows'])
        floor=amount(p['tax_floor'],'/tax_floor');coefficient=p['tax_coefficient'];k=_fraction(coefficient['value']);k_issues=[]
        if k is None:k_issues.append('coefficient_missing')
        elif k<0:k_issues.append('fixed_coefficient_outside_nonnegative_profile_domain')
        if coefficient['unit']!='scalar':k_issues.append('coefficient_unit_missing_or_mismatch')
        if coefficient['source_ref']is None:k_issues.append('declared_source_ref_missing')
        blockers.extend('/tax_coefficient:'+reason for reason in k_issues)
        lineage.append({'locator':'/tax_coefficient','source_ref':coefficient['source_ref'],'declared_value':coefficient['value'],'blockers':k_issues})
        if floor is not None and floor<0:blockers.append('/tax_floor:outside_nonnegative_profile_domain')
        if not blockers:
            floor_branch=_bounded(before-floor);proxy_branch=_bounded(before/_bounded(1+k))
            noi=min(floor_branch,proxy_branch);tax=_bounded(before-noi)
            branch='tie'if floor_branch==proxy_branch else('floor'if floor_branch<proxy_branch else'proxy')
            residual=_bounded(noi-(before-max(floor,_bounded(k*noi))))
            if residual!=0:raise ArithmeticBudgetError('profile equation residual is nonzero')
    except ArithmeticBudgetError:
        blockers.append('exact_arithmetic_budget_or_residual_guard');noi=tax=residual=None;branch=None
    q=lambda x:None if x is None else rational(x)
    payload={'component':'T19','purpose':'conditional_synthetic_operating_profile','engine_sha256':ENGINE_SHA256,
        'source_sha256':hashlib.sha256(raw).hexdigest(),'definition_sources':refs,'profile_id':PROFILE,'context':p['context'],
        'currency':p['currency'],'period_ref':p['period_ref'],'quantity_kind':'money_per_period','basis':'accrual',
        'income_total':q(totals.get('income_rows')),'expenses_excluding_tax':q(totals.get('expense_rows')),
        'operating_before_tax':q(before),'property_tax':q(tax),'noi':q(noi),'tax_branch':branch,'equation_residual':q(residual),
        'lineage':lineage,'blockers':sorted(set(blockers)),'calculation_status':'computed_synthetic_profile'if noi is not None else'PENDING',
        'economic_scope_independently_verified':False,'calendar_period_verified':False,'source_authority_verified':False,
        'tax_law_verified':False,'tax_policy_adopted':False,'financial_inputs_verified':False,'cash_paid_or_distributed_verified':False,
        'decision':'PENDING','run_ready':False,'review_authenticated':False,'production_authorized':False,'financial_module_closed':False}
    encoded=canonical(payload);return OperatingNoiRun(encoded,digest(encoded))
