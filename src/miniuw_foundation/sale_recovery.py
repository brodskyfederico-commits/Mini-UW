"""T45 bounded affine cash-recovery domain, never an adopted investment criterion."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError
from .costed_exit_sale import CostedExitSaleRun,assemble_costed_exit_sale

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T45.md'


def parse_sale_recovery(raw):
    if type(raw)is not bytes or not raw or len(raw)>65536:raise ValidationError('bounded explicit recovery domain required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid recovery JSON')from error
    if type(p)is not dict or set(p)!={'schema','base_costed_run_sha256','gross_price_domain','cost_profile_domain_basis_ref','other_sources_fixed_basis_ref'}or p['schema']!='miniuw.synthetic-affine-sale-cash-recovery.v1':raise ValidationError('exact affine cash recovery profile required')
    if type(p['base_costed_run_sha256'])is not str or not re.fullmatch('[a-f0-9]{64}',p['base_costed_run_sha256']):raise ValidationError('exact replayed costed-exit run hash required')
    for key in ['cost_profile_domain_basis_ref','other_sources_fixed_basis_ref']:
        if p[key]is not None:nonempty(p[key],key)
    domain=p['gross_price_domain']
    if type(domain)is not dict or set(domain)!={'lower','upper'}:raise ValidationError('explicit finite closed price domain required')
    for value in domain.values():_fraction(value)
    return p


def _interval(lower,upper,lower_closed=True,upper_closed=True):
    return {'lower':rational(lower),'upper':None if upper is None else rational(upper),
            'lower_closed':lower_closed,'upper_closed':False if upper is None else upper_closed}


def _solve(slope,intercept,lower,upper):
    if slope==0:return None if intercept<0 else (lower,upper)
    boundary=_bounded(-intercept/slope)
    if slope>0:lower=max(lower,boundary)
    else:upper=min(upper,boundary)
    return None if lower>upper else (lower,upper)


def _caps(noi,prices):
    if prices is None:return None
    lower,upper=prices
    if noi==0:return _interval(Fraction(0),None,False,False) if lower<=0<=upper else None
    if upper<=0:return None
    # P=N/c for c>0: positive N excludes P=0 even if the price interval includes it.
    return _interval(_bounded(noi/upper),None if lower==0 else _bounded(noi/lower))


@dataclass(frozen=True)
class SaleRecoveryRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def analyze_sale_recovery(arguments,base_run,spec_raw):
    spec=parse_sale_recovery(spec_raw)
    if type(arguments)is not tuple or len(arguments)!=8 or type(base_run)is not CostedExitSaleRun:
        raise ValidationError('complete immutable costed-exit argument inventory and typed result required')
    if assemble_costed_exit_sale(*arguments)!=base_run:raise ValidationError('entire costed exit must reproduce')
    e,_,_,_,v,_,cost,bridge_raw=arguments
    blockers=[];analysis=None
    if spec['base_costed_run_sha256']!=base_run.sha256:blockers.append('base_costed_run_sha256_mismatch')
    if base_run.payload['state']!='compiled_synthetic':blockers.append('guarded_base_return_unavailable')
    for key in ['cost_profile_domain_basis_ref','other_sources_fixed_basis_ref']:
        if spec[key]is None:blockers.append(key+'_missing')
    lower=_fraction(spec['gross_price_domain']['lower']);upper=_fraction(spec['gross_price_domain']['upper'])
    if lower is None or upper is None or lower<0 or upper<lower:blockers.append('valid_nonnegative_finite_closed_price_domain_required')
    price=None if v.payload['candidate_value']is None else _fraction(v.payload['candidate_value'],max_digits=1300)
    if lower is not None and upper is not None and price is not None and not lower<=price<=upper:blockers.append('base_price_outside_declared_profile_domain')
    bridge=json.loads(bridge_raw)
    sale=next((c for c in e.closings if c.closing_id==bridge['sale_node_id']),None)
    if sale is not None:
        claim=json.loads(sale.closing_raw)['valuation_claim']
        if claim is not None and not(lower==upper==price):blockers.append('existing_valuation_claim_requires_separate_domain_consistency')
    if not blockers:
        try:
            fixed=rate=Fraction(0)
            for row in cost.payload['cost_rows']:
                claim=row['claim']
                if claim['applicability']!='included':continue
                value=_fraction(claim['value'])
                if claim['kind']=='fixed':fixed=_bounded(fixed+value)
                else:rate=_bounded(rate+value)
            slope=_bounded(1-rate)
            investor=base_run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload
            profit=_fraction(investor['net_cash_profit'],max_digits=1300)
            intercept=_bounded(profit-_bounded(slope*price))
            feasible=_solve(slope,intercept,lower,upper)
            zero=None if slope==0 else _bounded(-intercept/slope)
            noi=_fraction(v.payload['forward_noi'],max_digits=1300)
            cap_domain=_caps(noi,feasible)
            sale_slot=next(s for s in e.binding.project_return_binding.slots if s.node_id==bridge['sale_node_id'])
            others=Fraction(0)
            for event in investor['events']:
                if event['kind']=='contribution'and event['event_id']!=sale_slot.contribution_event_id:
                    others=_bounded(others+_fraction(event['amount'],max_digits=1300))
            analysis={'base_gross_price':rational(price),'base_net_cash_profit':rational(profit),'fixed_forward_noi':rational(noi),
                'declared_fixed_cost':rational(fixed),'declared_gross_price_cost_fraction':rational(rate),
                'profit_slope_per_unit_gross_price':rational(slope),'profit_intercept':rational(intercept),
                'cash_profit_zero_price':None if zero is None or not lower<=zero<=upper else rational(zero),
                'cash_profit_identically_zero_over_domain':slope==0 and intercept==0,
                'recovering_price_interval':None if feasible is None else _interval(*feasible),
                'recovering_exit_cap_interval':cap_domain,
                'recovery_possible_in_declared_price_domain':feasible is not None,
                'recovery_possible_via_positive_exit_cap':cap_domain is not None,
                'non_sale_gross_contributions':rational(others),
                'EM_ge_one_equivalence_defined_over_price_domain':others>0}
        except ArithmeticBudgetError:
            blockers.append('sale_recovery_exact_arithmetic_budget_exceeded');analysis=None
    result={'component':'T45','purpose':'conditional_synthetic_affine_cash_recovery_domain',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'spec_sha256':hashlib.sha256(spec_raw).hexdigest(),'base_costed_run_sha256':base_run.sha256,
        'context':v.payload['context'],'currency':v.payload['currency'],'valuation_date':v.payload['valuation_date'],
        'forward_window':v.payload['forward_window'],'exit_cap_unit':'annual_cap_fraction',
        'gross_price_domain':spec['gross_price_domain'],'analysis':analysis,'blockers':sorted(set(blockers)),
        'state':'computed_synthetic_recovery_domain'if analysis is not None else'blocked',
        'new_scenario_or_investor_ledger_generated':False,'cost_profile_financially_valid_over_domain':False,
        'funding_availability_verified_over_domain':False,'tax_rule_verified':False,
        'investment_criterion_adopted':False,'personal_investor_return':None,'final_economic_capital_loss':None,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return SaleRecoveryRun(encoded,digest(encoded))


def verify_sale_recovery(arguments,base_run,spec_raw,report):
    if type(report)is not SaleRecoveryRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed recovery report with matching hash required')
    if analyze_sale_recovery(arguments,base_run,spec_raw)!=report:raise ValidationError('recovery report replay mismatch')
    return report
