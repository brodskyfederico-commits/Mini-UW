"""T43 exact explicitly classified fixed/percent-of-gross sale cost inventory."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational
from .investor_returns import _date
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T43-T44.md'


def parse_sale_costs(raw):
    if type(raw)is not bytes or not raw or len(raw)>131072:raise ValidationError('bounded explicit sale cost source required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid sale cost JSON')from error
    keys={'schema','context','currency','sale_date','gross_price','inventory_declared_complete','inventory_basis_ref','nonoverlap_basis_ref','costs'}
    if type(p)is not dict or set(p)!=keys or p['schema']!='miniuw.synthetic-fixed-and-gross-percent-sale-costs.v1':raise ValidationError('exact fixed/percent gross price profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    nonempty(p['currency'],'currency');_date(p['sale_date'])
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('explicit inventory declaration required')
    for key in ['inventory_basis_ref','nonoverlap_basis_ref']:
        if p[key]is not None:nonempty(p[key],key)
    claim=p['gross_price']
    if type(claim)is not dict or set(claim)!={'value','currency','as_of_date','basis','source_ref'}:raise ValidationError('exact projected gross price claim required')
    _fraction(claim['value'])
    for key in ['currency','basis','source_ref']:
        if claim[key]is not None:nonempty(claim[key],key)
    if claim['as_of_date']is not None:_date(claim['as_of_date'])
    if type(p['costs'])is not list or len(p['costs'])>64:raise ValidationError('bounded explicit cost inventory required')
    seen=set()
    for row in p['costs']:
        keys={'cost_id','classification','kind','applicability','applicability_basis_ref','value','unit','currency','as_of_date','source_ref'}
        if type(row)is not dict or set(row)!=keys:raise ValidationError('exact cost classification and amount metadata required')
        nonempty(row['cost_id'],'cost_id')
        if row['cost_id']in seen:raise ValidationError('duplicate cost identity')
        seen.add(row['cost_id'])
        if row['classification']not in ['transaction_cost','tax','other']or row['kind']not in ['fixed','percent_of_gross']:raise ValidationError('unsupported cost classification/profile')
        if row['applicability']not in ['included','not_applicable','unresolved']:raise ValidationError('explicit applicability status required')
        _fraction(row['value'])
        for key in ['unit','currency','source_ref','applicability_basis_ref']:
            if row[key]is not None:nonempty(row[key],key)
        if row['as_of_date']is not None:_date(row['as_of_date'])
    return p


@dataclass(frozen=True)
class SaleCostsRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def produce_sale_costs(raw):
    from fractions import Fraction
    p=parse_sale_costs(raw);blockers=[];rows=[];total=None
    if p['inventory_declared_complete']is not True or p['inventory_basis_ref']is None:blockers.append('cost_inventory_not_explicitly_complete_with_basis')
    if p['nonoverlap_basis_ref']is None:blockers.append('nonoverlap_basis_missing')
    claim=p['gross_price'];price=_fraction(claim['value'])
    price_bad=[]
    if price is None or price<0:price_bad.append('gross_price_missing_or_negative')
    if claim['currency']!=p['currency']or claim['as_of_date']!=p['sale_date']or claim['basis']!='projected_gross_sale_price'or claim['source_ref']is None:price_bad.append('gross_price_metadata_missing_or_mismatch')
    blockers.extend(price_bad)
    try:
        subtotal=Fraction(0)
        for row in p['costs']:
            issues=[];value=_fraction(row['value']);amount=None
            if row['currency']!=p['currency']or row['as_of_date']!=p['sale_date']or row['source_ref']is None or row['applicability_basis_ref']is None:issues.append('cost_metadata_or_applicability_basis_missing_or_mismatch')
            expected='currency'if row['kind']=='fixed'else'fraction_of_gross_price'
            if row['unit']!=expected:issues.append('cost_unit_missing_or_mismatch')
            if row['applicability']=='unresolved':issues.append('cost_applicability_unresolved')
            elif row['applicability']=='not_applicable':
                if value is not None:issues.append('not_applicable_cost_must_not_carry_an_amount')
            else:
                if value is None or value<0:issues.append('included_cost_missing_or_negative')
                if not issues and not price_bad:
                    amount=_bounded(value if row['kind']=='fixed'else _bounded(price*value))
                    subtotal=_bounded(subtotal+amount)
            blockers.extend(row['cost_id']+':'+x for x in issues)
            rows.append(dict(claim=row,computed_cost=None if amount is None else rational(amount),
                excluded_by_explicit_applicability=row['applicability']=='not_applicable'and not issues,blockers=issues))
        if not blockers:total=rational(subtotal)
    except ArithmeticBudgetError:
        blockers.append('sale_cost_exact_arithmetic_budget_exceeded');total=None;rows=[]
    payload={'component':'T43','purpose':'conditional_synthetic_fixed_and_gross_percent_sale_costs',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256(raw).hexdigest(),'context':p['context'],'currency':p['currency'],
        'sale_date':p['sale_date'],'gross_price':claim,'cost_rows':rows,'total_closing_cost':total,
        'state':'computed_synthetic_sale_costs'if total is not None else'blocked','blockers':sorted(set(blockers)),
        'cost_inventory_financially_verified':False,'cost_nonoverlap_financially_verified':False,
        'tax_rule_verified':False,'tax_policy_adopted':False,'costs_paid_verified':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(payload);return SaleCostsRun(encoded,digest(encoded))
