"""T48 per-item declared monetary floors/caps; never infer contractual limits."""
from dataclasses import dataclass
from pathlib import Path
from fractions import Fraction
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .investor_returns import _date
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError
from .sale_costs import SaleCostsRun,produce_sale_costs

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T48-T50.md'


def parse_cost_bounds(raw):
    if type(raw)is not bytes or not raw or len(raw)>131072:raise ValidationError('bounded explicit per-item limit source required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid cost bounds JSON')from error
    if type(p)is not dict or set(p)!={'schema','profile','cost_source_sha256','cost_run_sha256','rule_inventory_declared_complete','rule_inventory_basis_ref','rules'}or p['schema']!='miniuw.synthetic-per-item-sale-cost-bounds.v1'or p['profile']!='SYNTHETIC-PER-ITEM-CLAMP-TO-EXPLICIT-MONEY-LIMITS-v1':raise ValidationError('exact explicit per-item floor/cap profile required')
    for key in ['cost_source_sha256','cost_run_sha256']:
        if type(p[key])is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):raise ValidationError('exact cost source/run hash required')
    if p['rule_inventory_declared_complete']is not None and type(p['rule_inventory_declared_complete'])is not bool:raise ValidationError('explicit rule inventory declaration required')
    if p['rule_inventory_basis_ref']is not None:nonempty(p['rule_inventory_basis_ref'],'rule_inventory_basis_ref')
    if type(p['rules'])is not list or len(p['rules'])>64:raise ValidationError('bounded explicit rules required')
    seen=set()
    for row in p['rules']:
        if type(row)is not dict or set(row)!={'cost_id','rule_basis_ref','minimum','maximum'}:raise ValidationError('exact per-cost rule required')
        nonempty(row['cost_id'],'cost_id')
        if row['cost_id']in seen:raise ValidationError('duplicate bound cost identity')
        seen.add(row['cost_id'])
        if row['rule_basis_ref']is not None:nonempty(row['rule_basis_ref'],'rule_basis_ref')
        for key in ['minimum','maximum']:
            bound=row[key]
            if type(bound)is not dict or set(bound)!={'enabled','value','currency','as_of_date','source_ref'}:raise ValidationError('exact explicit monetary limit required')
            if bound['enabled']is not None and type(bound['enabled'])is not bool:raise ValidationError('explicit enabled/disabled/unresolved bound required')
            _fraction(bound['value'])
            for k in ['currency','source_ref']:
                if bound[k]is not None:nonempty(bound[k],k)
            if bound['as_of_date']is not None:_date(bound['as_of_date'])
    return p


@dataclass(frozen=True)
class BoundedSaleCostsRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def produce_bounded_sale_costs(cost_raw,cost_run,bounds_raw):
    spec=parse_cost_bounds(bounds_raw)
    if type(cost_run)is not SaleCostsRun or produce_sale_costs(cost_raw)!=cost_run:raise ValidationError('entire original cost inventory must reproduce')
    p=cost_run.payload;blockers=[];rows=[];total=None
    if spec['cost_source_sha256']!=hashlib.sha256(cost_raw).hexdigest()or spec['cost_run_sha256']!=cost_run.sha256:blockers.append('cost_source_or_run_binding_mismatch')
    if p['state']!='computed_synthetic_sale_costs':blockers.append('original_complete_cost_inventory_blocked')
    if spec['rule_inventory_declared_complete']is not True or spec['rule_inventory_basis_ref']is None:blockers.append('rule_inventory_not_explicitly_complete_with_basis')
    included=[row for row in p['cost_rows']if row['claim']['applicability']=='included']
    rules={r['cost_id']:r for r in spec['rules']}
    if set(rules)!={r['claim']['cost_id']for r in included}:blockers.append('rules_do_not_exactly_cover_included_costs')
    try:
        subtotal=Fraction(0)
        for source_row in included:
            cid=source_row['claim']['cost_id'];rule=rules.get(cid);issues=[];limits={};adjusted=None;bindings=[]
            if rule is None:issues.append('explicit_rule_missing')
            else:
                if rule['rule_basis_ref']is None:issues.append('rule_basis_missing')
                for key in ['minimum','maximum']:
                    b=rule[key];value=_fraction(b['value'])
                    if b['currency']!=p['currency']or b['as_of_date']!=p['sale_date']or b['source_ref']is None:issues.append(key+':currency_date_or_source_missing_or_mismatch')
                    if b['enabled']is None:issues.append(key+':enabled_status_unresolved')
                    elif b['enabled']:
                        if value is None or value<0:issues.append(key+':nonnegative_limit_missing')
                        else:limits[key]=value
                    elif value is not None:issues.append(key+':disabled_limit_must_not_carry_value')
                if 'minimum'in limits and 'maximum'in limits and limits['minimum']>limits['maximum']:issues.append('minimum_exceeds_maximum')
            original=None if source_row['computed_cost']is None else _fraction(source_row['computed_cost'],max_digits=1300)
            if original is None:issues.append('original_cost_unavailable')
            if not issues:
                adjusted=original
                if 'minimum'in limits:adjusted=max(adjusted,limits['minimum'])
                if 'maximum'in limits:adjusted=min(adjusted,limits['maximum'])
                adjusted=_bounded(adjusted);subtotal=_bounded(subtotal+adjusted)
                if adjusted==original:bindings.append('original_formula')
                bindings.extend(key for key,value in limits.items()if value==adjusted)
            blockers.extend(cid+':'+i for i in issues)
            rows.append(dict(cost_id=cid,source_cost_claim=source_row['claim'],original_computed_cost=source_row['computed_cost'],rule=rule,
                bounded_cost=None if adjusted is None else rational(adjusted),binding_constraints=bindings,blockers=issues))
        if not blockers:total=rational(subtotal)
    except ArithmeticBudgetError:
        blockers.append('bounded_cost_exact_arithmetic_budget_exceeded');rows=[];total=None
    payload={'component':'T48','purpose':'synthetic_per_item_monetary_floor_cap_costs',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'cost_source_sha256':hashlib.sha256(cost_raw).hexdigest(),'cost_run_sha256':cost_run.sha256,'bounds_source_sha256':hashlib.sha256(bounds_raw).hexdigest(),
        'context':p['context'],'currency':p['currency'],'sale_date':p['sale_date'],'gross_price':p['gross_price'],
        'adjusted_costs':rows,'excluded_original_rows':[r for r in p['cost_rows']if r['claim']['applicability']!='included'],
        'total_closing_cost':total,'state':'computed_synthetic_bounded_costs'if total is not None else'blocked',
        'blockers':sorted(set(blockers)),'original_cost_blockers':p['blockers'],
        'result_is_global_affine_cost_profile':False,'contract_or_tax_rule_verified':False,'costs_paid_verified':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(payload);return BoundedSaleCostsRun(encoded,digest(encoded))
