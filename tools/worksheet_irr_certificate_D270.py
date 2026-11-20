"""Opt-in exact positive-discount root certificates; no financial assumption.

Descartes' rule is applied after exact changes of variable on (0,1) and
(1,infinity). A zero/one variation count certifies the number of roots there.
Unproved or multiple-root cases never select a rate.
"""
from fractions import Fraction as Q
from math import comb, isqrt
from pathlib import Path

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import synthetic_id


PROFILE = "miniuw.synthetic-positive-discount-irr-certificate.v1"
RULES = dict(domain="strictly_positive_periodic_discount_factor",
    grid="documented_complete_quarters_four_per_year",
    inventory="Descartes_on_0_1_and_1_infinity_plus_exact_endpoint_1",
    selection="only_one_proven_admissible_root",
    unproved="existing_complete_inventory_or_PENDING_never_guess",
    bisection_steps=68, expanding_bracket_steps=32,
    maximum_degree=64, maximum_input_bits=4096,
    maximum_certificate_bits=8192, maximum_evaluation_bits=32768)
_RULES_BYTES = encoded(RULES)
_LOADED_SHA256 = sha(Path(__file__).read_bytes())


class ArithmeticBudget(ValueError):
    pass


def implementation_sha256():
    return _LOADED_SHA256


def bounded(value, limit):
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > limit:
        raise ArithmeticBudget("IRR_certificate_arithmetic_budget_exhausted")
    return value


def variations(values):
    signs = [value > 0 for value in values if value]
    return sum(a != b for a,b in zip(signs, signs[1:]))


def evaluate(coefficients, point):
    result = Q()
    for coefficient in reversed(coefficients):
        result = bounded(result*point+coefficient, RULES["maximum_evaluation_bits"])
    return result


def positive_inventory(values):
    require(isinstance(values, (list,tuple)) and 1 <= len(values) <= RULES["maximum_degree"]+1
            and all(type(value) is int or isinstance(value,Q) for value in values),
            "IRR_certificate_explicit_rational_polynomial_required")
    coefficients = [bounded(Q(value), RULES["maximum_input_bits"]) for value in values]
    digest = sha(encoded([rational(value) for value in coefficients]))
    if not any(coefficients):
        return dict(state="PENDING", complete=False, positive_roots=None,
                    classification="identically_zero_infinite_roots", polynomial_sha256=digest)
    # Factors x are outside the strictly positive domain; terminal zeros do not
    # change the polynomial. Neither operation fills missing cash observations.
    removed = 0
    while coefficients[0] == 0:
        coefficients.pop(0); removed += 1
    while len(coefficients)>1 and coefficients[-1] == 0: coefficients.pop()
    degree = len(coefficients)-1
    left,right = [],[]
    for j in range(degree+1):
        first,last = Q(),Q()
        for i in range(j+1):
            first = bounded(first+coefficients[i]*comb(degree-i,j-i), RULES["maximum_certificate_bits"])
        for i in range(j,degree+1):
            last = bounded(last+coefficients[i]*comb(i,j), RULES["maximum_certificate_bits"])
        left.append(first); right.append(last)
    vl,vr = variations(left),variations(right)
    endpoint = evaluate(coefficients,Q(1)) == 0
    complete = vl <= 1 and vr <= 1
    count = vl+vr+int(endpoint) if complete else None
    return dict(state="complete_exact_inventory" if complete else "PENDING", complete=complete,
        positive_roots=count, classification="certified_positive_domain" if complete else "variation_bound_not_exact",
        degree=degree, zero_discount_factors_removed=removed, polynomial_sha256=digest,
        left_variations=vl, right_variations=vr, root_at_one=endpoint,
        left_transform="(1+t)^n P(t/(1+t))", right_transform="P(1+t)",
        coefficients=coefficients)


def annual_enclosure(coefficients, certificate):
    require(certificate["complete"] and certificate["positive_roots"] == 1,
            "IRR_certificate_unique_root_required")
    if certificate["root_at_one"]:
        return dict(lower=rational(0), upper=rational(0), lower_closed=True, upper_closed=True)
    low,high = (Q(0),Q(1)) if certificate["left_variations"] == 1 else (Q(1),Q(2))
    f_low,f_high = evaluate(coefficients,low),evaluate(coefficients,high)
    for _ in range(RULES["expanding_bracket_steps"]):
        if f_high == 0 or f_low*f_high < 0: break
        require(certificate["right_variations"] == 1, "IRR_certificate_bracket_not_proven")
        high *= 2; f_high = evaluate(coefficients,high)
    else: raise ArithmeticBudget("IRR_certificate_expanding_bracket_budget_exhausted")
    if f_high == 0:
        rate=high**-4-1
        return dict(lower=rational(rate),upper=rational(rate),lower_closed=True,upper_closed=True)
    require(f_low != 0 and f_low*f_high < 0, "IRR_certificate_strict_bracket_required")
    for _ in range(RULES["bisection_steps"]):
        middle=(low+high)/2; found=evaluate(coefficients,middle)
        if found == 0:
            rate=middle**-4-1
            return dict(lower=rational(rate),upper=rational(rate),lower_closed=True,upper_closed=True)
        if (found>0)==(f_low>0): low,f_low=middle,found
        else: high,f_high=middle,found
    require(low>0 and f_low*f_high<0, "IRR_certificate_finite_bracket_not_resolved")
    return dict(lower=rational(high**-4-1),upper=rational(low**-4-1),lower_closed=True,upper_closed=True)


def configuration(raw):
    require(isinstance(raw,dict) and set(raw)=={"profile","rules","source_ref","algorithm_sha256"}
            and raw["profile"]==PROFILE and encoded(raw["rules"])==_RULES_BYTES and encoded(RULES)==_RULES_BYTES
            and synthetic_id(raw["source_ref"]) and raw["algorithm_sha256"]==implementation_sha256()
            and sha(Path(__file__).read_bytes())==implementation_sha256(),
            "IRR_certificate_definition_or_revision_unconfirmed")
    return raw


def pending(reason,dates):
    from worksheet_local_sources_D127 import day
    period = None
    if (isinstance(dates,(list,tuple)) and len(dates)>=2 and isinstance(dates[0],str)
            and isinstance(dates[-1],str) and day(dates[0]) is not None and day(dates[-1]) is not None):
        period=f"{dates[0]}/{dates[-1]}"
    return dict(state="PENDING",annual_enclosure=None,blockers=[reason],
                period_ref=period)


def verify_cash(cash, dates, config):
    try:
        configuration(config)
        require(isinstance(cash,dict) and isinstance(dates,list) and len(dates)>=2,
                "IRR_certificate_verified_cash_and_dates_required")
        events=cash.get("events")
        require(isinstance(events,list) and events and {e.get("date") for e in events if isinstance(e,dict)}==set(dates),
                "IRR_certificate_missing_cash_date_not_zero")
        for event in events:
            amount=_fraction(event.get("amount"),1300)
            require(event.get("kind") in {"contribution","distribution"} and event.get("currency")=="USD"
                    and amount is not None and amount>=0, "IRR_certificate_missing_or_invalid_gross_cash")
        from check_worksheet_return_metrics_D167 import quarterly_cash
        flows=quarterly_cash(cash,dates)
        require(flows is not None,"IRR_certificate_cash_outside_declared_quarterly_grid")
        certificate=positive_inventory(list(flows.values()))
        coefficients=certificate.pop("coefficients",None)
        provenance=dict(method=PROFILE,cash_sha256=sha(encoded(cash)),period_ref=f"{dates[0]}/{dates[-1]}",
            step_months=3,periods_per_year=4,method_source_sha256=implementation_sha256(),
            definition=config,complete_root_inventory=certificate)
        if not certificate["complete"]:
            if certificate["classification"]=="identically_zero_infinite_roots":
                return pending("IRR_identically_zero_no_unique_rate",dates)|provenance
            # Existing isolation may certify a case for which this sufficient
            # Descartes condition is inconclusive. It still cannot pick a root
            # from an incomplete or multiple inventory.
            from worksheet_lorena_annual_route import route_annual_irr
            fallback=route_annual_irr(cash,dates)
            return fallback|dict(certificate_attempt=certificate,numerical_extension=config)
        if certificate["positive_roots"]!=1:
            reason="IRR_no_admissible_positive_discount_root" if certificate["positive_roots"]==0 else "IRR_multiple_admissible_roots_no_selection"
            return pending(reason,dates)|provenance
        enclosure=annual_enclosure(coefficients,certificate)
        discounts=[]
        for key in ("upper","lower"):
            factor=_fraction(enclosure[key],1300)+1
            numerator,denominator=isqrt(isqrt(factor.denominator)),isqrt(isqrt(factor.numerator))
            require(numerator**4==factor.denominator and denominator**4==factor.numerator,
                    "IRR_certificate_annualization_does_not_reconcile")
            discounts.append(Q(numerator,denominator))
        left,right=(evaluate(coefficients,point) for point in discounts)
        require(left*right<=0,"IRR_certificate_endpoint_sign_check_failed")
        check=dict(lower_discount=rational(discounts[0]),upper_discount=rational(discounts[1]),
                   lower_npv_sign=(left>0)-(left<0),upper_npv_sign=(right>0)-(right<0))
        return dict(state="checked_synthetic",annual_enclosure=enclosure,blockers=[],endpoint_check=check)|provenance
    except (ValueError,TypeError,KeyError,AttributeError,ZeroDivisionError) as error:
        return pending(str(error),dates)


def solver(raw):
    """Explicit invalid configuration remains PENDING, without an old-method default."""
    return lambda cash,dates:verify_cash(cash,dates,raw)
