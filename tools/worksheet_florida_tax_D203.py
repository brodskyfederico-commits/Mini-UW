"""M2 annual Florida ad valorem projection for the documented synthetic profile."""
from collections import Counter
from datetime import date
from fractions import Fraction
import json

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import day, number, object_or_empty, synthetic_id
from plan_refinance_D108 import BANK_PERIOD
from plan_return_D107 import FORWARD_PERIOD
from worksheet_project_calendar_D145 import offset


PROFILE = "synthetic_documented_florida_tax"
POLICY = "SYNTHETIC-D203-FL-nonhomestead-ad-valorem"
SCOPE = "ad_valorem_with_explicit_no_exemptions_or_special_assessments"
CHANGES = {"confirmed_no_change", "ownership_or_control_reset", "qualifying_improvement_reset"}


def evidence(record, key, *, label):
    require(synthetic_id(record.get(key)), f"M2:{label}:{key}_missing")
    return record[key]


def nonnegative(record, key, *, label, maximum=None):
    value = number(record.get(key))
    require(value is not None and value >= 0 and (maximum is None or value <= maximum),
            f"M2:{label}:{key}_missing_or_invalid")
    return value


def assessed_value(record, year, previous, classification, owner, sale):
    label = f"{owner}:{year}"
    just = nonnegative(record, "just_value", label=label)
    school = nonnegative(record, "school_taxable_value", label=label, maximum=just)
    valuation_ref = evidence(record, "valuation_ref", label=label)
    event_ref = evidence(record, "event_ref", label=label)
    treatment = record.get("assessment_treatment")
    require(treatment in CHANGES, f"M2:{label}:assessment_treatment_unconfirmed")
    event = record.get("event_date")
    prior = previous
    ceiling = cap = None
    if treatment == "confirmed_no_change":
        require(event is None and prior is not None, f"M2:{label}:prior_assessment_or_event_conflict")
        cap = Fraction(5 if year >= 2027 else 10, 100)
        ceiling = prior * (1 + cap)
        non_school = min(just, ceiling)
    else:
        event_date = day(event)
        require(event_date is not None and date(year - 1, 1, 1) <= event_date < date(year, 1, 1),
                f"M2:{label}:reset_date_outside_prior_roll")
        require(treatment != "qualifying_improvement_reset" or classification == "art_VII_4h",
                f"M2:{label}:qualifying_improvement_classification_unconfirmed")
        if owner == "buyer":
            require(treatment == "ownership_or_control_reset" and event_date == sale,
                    f"M2:{label}:buyer_reset_does_not_match_sale")
        non_school = just
    return dict(tax_year=year, owner=owner, assessment_treatment=treatment, event_date=event,
                event_ref=event_ref, valuation_ref=valuation_ref, prior_non_school_assessed=prior,
                just_value=just, school_taxable_value=school, non_school_assessed_value=non_school,
                cap=cap, assessment_ceiling=ceiling)


def month_weights(start, months):
    return Counter(offset(start, month).year for month in range(months))


def tax_inputs(raw, name, calendar):
    """Bind seller and buyer rolls to the exact NOI windows for one scenario."""
    spec = object_or_empty(raw)
    require(spec.get("policy") == POLICY, "M2:florida_tax_policy_missing")
    record = object_or_empty(object_or_empty(spec.get("scenarios")).get(name))
    label = "florida_tax"
    classification = record.get("classification")
    require(classification in ("art_VII_4g", "art_VII_4h") and record.get("scope") == SCOPE,
            "M2:classification_or_tax_scope_unconfirmed")
    classification_ref = evidence(record, "classification_ref", label=label)
    scope_ref = evidence(record, "scope_ref", label=label)
    submission_ref = evidence(record, "source_ref", label=label)
    rolls = object_or_empty(record.get("rolls"))
    rates = object_or_empty(rolls.get("millage"))
    seller = object_or_empty(rolls.get("seller"))
    buyer = object_or_empty(rolls.get("buyer"))
    previous = object_or_empty(record.get("opening_assessment"))
    seed_year = previous.get("tax_year")
    sale = day(calendar["sale_date"])
    reset_year = sale.year + 1
    require(type(seed_year) is int and 2000 <= seed_year < reset_year, "M2:prior_assessment_year_missing_or_invalid")
    seed = nonnegative(previous, "non_school_assessed_value", label="prior_roll")
    seed_ref = evidence(previous, "source_ref", label="prior_roll")
    starts = {period: day(value) for period, value in calendar["noi_window_starts"].items()}
    weights = {period: month_weights(start, 12) for period, start in starts.items()}
    min_seller = min(year for period, years in weights.items() for year in years
                     if period != FORWARD_PERIOD or year < reset_year)
    max_seller = max(year for period, years in weights.items() for year in years
                     if period != FORWARD_PERIOD or year < reset_year)
    max_buyer = max(weights[FORWARD_PERIOD])
    require(seed_year < min_seller and max(max_seller, max_buyer) - seed_year <= 20,
            "M2:prior_assessment_outside_supported_roll_range")

    levy = {}
    for year in range(min_seller, max(max_seller, max_buyer) + 1):
        item = object_or_empty(rates.get(str(year)))
        rate_label = f"millage:{year}"
        source_ref = evidence(item, "source_ref", label=rate_label)
        levy[year] = (nonnegative(item, "school_mills", label=rate_label, maximum=1000),
                      nonnegative(item, "non_school_mills", label=rate_label, maximum=1000), source_ref)

    seller_rows = {}
    for year in range(seed_year + 1, max_seller + 1):
        assessed = assessed_value(object_or_empty(seller.get(str(year))), year, seed, classification, "seller", sale)
        seed = assessed["non_school_assessed_value"]
        seller_rows[year] = assessed
    # In this sale profile the forward year contains exactly one post-sale January 1.
    require(max_buyer == reset_year, "M2:buyer_forward_window_outside_supported_roll_range")
    buyer_row = assessed_value(object_or_empty(buyer.get(str(reset_year))), reset_year, None, classification, "buyer", sale)

    def window_tax(start, months, *, forward=False):
        parts = []
        for year, count in month_weights(start, months).items():
            row = buyer_row if forward and year >= reset_year else seller_rows[year]
            school_mills, non_school_mills, rate_ref = levy[year]
            school = row["school_taxable_value"] * school_mills * count / 12_000
            non_school = row["non_school_assessed_value"] * non_school_mills * count / 12_000
            parts.append(row | dict(months=count, school_mills=school_mills, non_school_mills=non_school_mills,
                                    millage_ref=rate_ref, school_tax=school, non_school_tax=non_school))
        school = sum(row["school_tax"] for row in parts)
        non_school = sum(row["non_school_tax"] for row in parts)
        trace = dict(basis=POLICY, classification=classification, classification_ref=classification_ref,
                     scope_ref=scope_ref, source_ref=submission_ref, opening_assessment_ref=seed_ref,
                     window_start=start.isoformat(), window_end_exclusive=offset(start, months).isoformat(),
                     school_tax=school, non_school_tax=non_school, total=school + non_school, rolls=parts)
        return json.loads(json.dumps(trace, default=rational))

    taxes = {period: window_tax(start, 12, forward=period == FORWARD_PERIOD) for period, start in starts.items()}
    for tax in taxes.values():
        tax["source_sha256"] = sha(encoded(tax))
    start = day(calendar["noi_window_starts"][BANK_PERIOD])
    end = starts[FORWARD_PERIOD]
    months = (end.year - start.year) * 12 + end.month - start.month
    require(months > 0, "M2:post_refinance_tax_window_unconfirmed")
    post_refi = window_tax(start, months)
    post_refi["source_sha256"] = sha(encoded(post_refi))
    return taxes, post_refi
