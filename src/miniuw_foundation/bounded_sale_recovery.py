"""T51 exact piecewise cash recovery under explicitly bounded per-item charges."""
from dataclasses import dataclass
from pathlib import Path
from fractions import Fraction
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError
from .bounded_exit_sale import BoundedExitSaleRun,assemble_bounded_exit_sale
from .sale_recovery import _solve,_caps,_interval,ENGINE_SHA256 as AFFINE_HELPER_SHA256

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T51-T52.md'


def parse_bounded_recovery(raw):
    if type(raw)is not bytes or not raw or len(raw)>65536:raise ValidationError('bounded explicit piecewise recovery specification required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid piecewise recovery JSON')from error
    keys={'schema','base_bounded_run_sha256','gross_price_domain','cost_profile_domain_basis_ref','other_sources_fixed_basis_ref','segment_budget'}
    if type(p)is not dict or set(p)!=keys or p['schema']!='miniuw.synthetic-piecewise-bounded-sale-recovery.v1':raise ValidationError('exact piecewise recovery profile required')
    if type(p['base_bounded_run_sha256'])is not str or not re.fullmatch('[a-f0-9]{64}',p['base_bounded_run_sha256']):raise ValidationError('exact bounded-exit result hash required')
    for key in ['cost_profile_domain_basis_ref','other_sources_fixed_basis_ref']:
        if p[key]is not None:nonempty(p[key],key)
    domain=p['gross_price_domain']
    if type(domain)is not dict or set(domain)!={'lower','upper'}:raise ValidationError('explicit finite closed price domain required')
    for value in domain.values():_fraction(value)
    if type(p['segment_budget'])is not int or not 1<=p['segment_budget']<=129:raise ValidationError('explicit segment budget 1..129 required')
    return p


def _cost_terms(rows):
    terms=[]
    for row in rows:
        claim=row['source_cost_claim'];value=_fraction(claim['value']);rule=row['rule']
        a=value if claim['kind']=='percent_of_gross'else Fraction(0)
        b=value if claim['kind']=='fixed'else Fraction(0)
        limits={key:_fraction(rule[key]['value'])for key in ['minimum','maximum']if rule[key]['enabled']}
        terms.append((row['cost_id'],a,b,limits))
    return terms


def _at(terms,price):
    total=Fraction(0)
    for _,a,b,limits in terms:
        value=_bounded(_bounded(a*price)+b)
        if 'minimum'in limits:value=max(value,limits['minimum'])
        if 'maximum'in limits:value=min(value,limits['maximum'])
        total=_bounded(total+value)
    return total


def _formula(terms,sample):
    slope=intercept=Fraction(0);regimes=[]
    for cid,a,b,limits in terms:
        value=_bounded(_bounded(a*sample)+b);regime='original_formula'
        if 'minimum'in limits and 'maximum'in limits and limits['minimum']==limits['maximum']:
            a,b,regime=Fraction(0),limits['minimum'],'minimum_and_maximum'
        elif 'minimum'in limits and value<limits['minimum']:a,b,regime=Fraction(0),limits['minimum'],'minimum'
        elif 'maximum'in limits and value>limits['maximum']:a,b,regime=Fraction(0),limits['maximum'],'maximum'
        slope=_bounded(slope+a);intercept=_bounded(intercept+b)
        regimes.append(dict(cost_id=cid,regime_at_sample=regime))
    return slope,intercept,regimes


def _merge(intervals):
    merged=[]
    for lower,upper in sorted(intervals):
        if merged and lower<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],upper))
        else:merged.append((lower,upper))
    return merged


@dataclass(frozen=True)
class BoundedSaleRecoveryRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def analyze_bounded_sale_recovery(arguments,base_run,spec_raw):
    spec=parse_bounded_recovery(spec_raw)
    if type(arguments)is not tuple or len(arguments)!=10 or type(base_run)is not BoundedExitSaleRun:raise ValidationError('complete typed bounded-exit arguments and result required')
    if assemble_bounded_exit_sale(*arguments)!=base_run:raise ValidationError('entire bounded-exit calculation must reproduce')
    e,_,_,_,value,_,_,_,cost,bridge_raw=arguments
    p=value.payload;blockers=[];analysis=None
    if spec['base_bounded_run_sha256']!=base_run.sha256:blockers.append('base_bounded_run_sha256_mismatch')
    if base_run.payload['state']!='compiled_synthetic':blockers.append('guarded_base_return_unavailable')
    for key in ['cost_profile_domain_basis_ref','other_sources_fixed_basis_ref']:
        if spec[key]is None:blockers.append(key+'_missing')
    lower=_fraction(spec['gross_price_domain']['lower']);upper=_fraction(spec['gross_price_domain']['upper'])
    price=None if p['candidate_value']is None else _fraction(p['candidate_value'],max_digits=1300)
    if lower is None or upper is None or lower<0 or upper<lower:blockers.append('valid_nonnegative_finite_closed_domain_required')
    if lower is not None and upper is not None and price is not None and not lower<=price<=upper:blockers.append('base_price_outside_profile_domain')
    bridge=json.loads(bridge_raw);sale=next((c for c in e.closings if c.closing_id==bridge['sale_node_id']),None)
    if sale is not None and json.loads(sale.closing_raw)['valuation_claim']is not None and not(lower==upper==price):blockers.append('existing_valuation_requires_separate_domain_consistency')
    if not blockers:
        try:
            terms=_cost_terms(cost.payload['adjusted_costs']);points={lower,upper}
            for _,a,b,limits in terms:
                if a>0:
                    for limit in limits.values():
                        point=_bounded(_bounded(limit-b)/a)
                        if lower<point<upper:points.add(point)
            points=sorted(points);pairs=list(zip(points[:-1],points[1:]))if len(points)>1 else[(lower,upper)]
            if len(pairs)>spec['segment_budget']:blockers.append('piecewise_segment_budget_exceeded')
            else:
                investor=base_run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload
                gain=_fraction(investor['net_cash_profit'],max_digits=1300)
                base_cost=_fraction(cost.payload['total_closing_cost'],max_digits=1300)
                constant=_bounded(_bounded(gain-price)+base_cost)
                if _at(terms,price)!=base_cost:raise ValidationError('piecewise cost must match replayed base total')
                segments=[];recovering=[];zeros=[]
                for left,right in pairs:
                    sample=_bounded(_bounded(left+right)/2);a,b,regimes=_formula(terms,sample)
                    slope=_bounded(1-a);intercept=_bounded(constant-b)
                    for endpoint in [left,right]:
                        if _bounded(_bounded(a*endpoint)+b)!=_at(terms,endpoint):raise ValidationError('piecewise cost continuity check failed')
                    interval=_solve(slope,intercept,left,right)
                    if interval is not None:recovering.append(interval)
                    if slope==0:
                        if intercept==0:zeros.append((left,right))
                    else:
                        root=_bounded(-intercept/slope)
                        if left<=root<=right:zeros.append((root,root))
                    segments.append(dict(price_interval=_interval(left,right),segment_kind='point'if left==right else'interval',
                        sample_price=rational(sample),
                        cost_slope=rational(a),cost_intercept=rational(b),cash_profit_slope=rational(slope),cash_profit_intercept=rational(intercept),
                        cost_regimes=regimes,recovering_price_interval=None if interval is None else _interval(*interval)))
                recovering=_merge(recovering);zeros=_merge(zeros);noi=_fraction(p['forward_noi'],max_digits=1300)
                caps=[cap for interval in recovering if(cap:=_caps(noi,interval))is not None]
                caps.sort(key=lambda cap:_fraction(cap['lower'],max_digits=1300))
                slot=next(s for s in e.binding.project_return_binding.slots if s.node_id==bridge['sale_node_id'])
                other_a=Fraction(0)
                for event in investor['events']:
                    if event['kind']=='contribution'and event['event_id']!=slot.contribution_event_id:other_a=_bounded(other_a+_fraction(event['amount'],max_digits=1300))
                observations=[]
                for point in points:
                    amount=_at(terms,point);profit=_bounded(_bounded(point-amount)+constant)
                    observations.append(dict(price=rational(point),total_cost=rational(amount),net_cash_profit=rational(profit)))
                analysis=dict(base_gross_price=rational(price),base_net_cash_profit=rational(gain),base_bounded_cost=rational(base_cost),
                    fixed_other_cash_constant=rational(constant),fixed_forward_noi=rational(noi),segment_count=len(segments),
                    segments=segments,breakpoint_observations=observations,
                    recovering_price_intervals=[_interval(*interval)for interval in recovering],
                    recovering_exit_cap_intervals=caps,zero_cash_profit_price_intervals=[_interval(*interval)for interval in zeros],
                    recovery_possible_in_price_domain=bool(recovering),recovery_possible_via_positive_exit_cap=bool(caps),
                    non_sale_gross_contributions=rational(other_a),EM_ge_one_equivalence_defined_over_domain=other_a>0)
        except ArithmeticBudgetError:
            blockers.append('piecewise_exact_arithmetic_budget_exceeded');analysis=None
    result={'component':'T51','purpose':'conditional_synthetic_piecewise_bounded_cost_cash_recovery',
        'engine_sha256':ENGINE_SHA256,'affine_helper_engine_sha256':AFFINE_HELPER_SHA256,
        'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),'spec_sha256':hashlib.sha256(spec_raw).hexdigest(),
        'base_bounded_run_sha256':base_run.sha256,'context':p['context'],'currency':p['currency'],'valuation_date':p['valuation_date'],
        'forward_window':p['forward_window'],'exit_cap_unit':'annual_cap_fraction','gross_price_domain':spec['gross_price_domain'],
        'state':'computed_synthetic_piecewise_recovery'if analysis is not None else'blocked','analysis':analysis,'blockers':sorted(set(blockers)),
        'underlying_calculation_blockers':base_run.payload['blockers'],'original_cost_blockers':base_run.payload['original_cost_blockers'],
        'new_scenario_or_investor_ledger_generated':False,'cost_profile_financially_valid_over_domain':False,
        'funding_availability_verified_over_domain':False,'investment_criterion_adopted':False,
        'personal_investor_return':None,'final_economic_capital_loss':None,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return BoundedSaleRecoveryRun(encoded,digest(encoded))


def verify_bounded_sale_recovery(arguments,base_run,spec_raw,report):
    if type(report)is not BoundedSaleRecoveryRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed piecewise recovery report with matching hash required')
    if analyze_bounded_sale_recovery(arguments,base_run,spec_raw)!=report:raise ValidationError('piecewise recovery report replay mismatch')
    return report
