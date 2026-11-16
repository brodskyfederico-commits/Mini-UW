"""Calculate Policy 12 CoC from a complete, dated synthetic post-refinance year."""

from fractions import Fraction
from hashlib import sha256

from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import day, object_or_empty, synthetic_id
from worksheet_performance_policy_D184 import AFTER_RESERVES
from worksheet_project_calendar_D145 import offset


SCHEMA = "miniuw.synthetic-post-refi-noi-quarters.v1"


def quantity(value):
    try:
        return _fraction(value, 1300)
    except ValidationError:
        return None


def pending(reason):
    return dict(state="PENDING", value=None, blocker=reason)


def equity_at_refinance(view, cash, refi):
    """Reconcile the actual net refi cash first, then determine equity still invested."""
    scale = quantity(cash.get("scale_factor"))
    if scale is None or scale <= 0 or quantity(cash.get("reference_amount")) != 10:
        return None
    closing = object_or_empty(view.get("construction_refinance"))
    payout, cash_in = (quantity(closing.get(k)) for k in ("net_equity_distribution", "projected_cash_in_required"))
    if closing.get("date") != refi or closing.get("blockers") != [] or None in (payout, cash_in) or min(payout, cash_in) < 0:
        return None
    flows = {category: Fraction() for category in ("initial_capital", "additional_capital", "refinance_cash_in",
                                                  "net_refinance_distribution")}
    for row in cash["events"]:
        category = row["category"]
        if category in ("refinance_cash_in", "net_refinance_distribution") and row["date"] != refi:
            return None
        if category not in flows or row["date"] > refi:
            continue
        value = quantity(row.get("amount"))
        if value is None or value < 0:
            return None
        flows[category] += value / scale
    if (flows["refinance_cash_in"], flows["net_refinance_distribution"]) != (cash_in, payout):
        return None
    contributed = sum(flows[k] for k in ("initial_capital", "additional_capital", "refinance_cash_in"))
    if contributed <= 0:
        return None
    return contributed - payout


def verify_annual_coc(view, evidence):
    """Use four dated NOI windows and the same four payments as the current loan."""
    calendar = object_or_empty(view.get("project_calendar"))
    refi, sale_date = day(calendar.get("refinance_date")), day(calendar.get("sale_date"))
    cash = view.get("cash_per_usd_10")
    if refi is None or sale_date is None or cash is None:
        return pending("verified_cash_and_refinance_dates_required")
    try:
        boundaries = [offset(refi, months).isoformat() for months in range(0, 13, 3)]
    except ValueError:
        return pending("verified_quarterly_anniversary_grid_required")
    if sale_date.isoformat() < boundaries[-1] or any(row["category"] == "net_sale_distribution" and
            row["date"] < boundaries[-1] for row in cash["events"]):
        return pending("sale_precedes_first_complete_post_refi_year")

    inventory = object_or_empty(evidence)
    periods = inventory.get("quarters")
    if (set(inventory) != {"schema", "noi_basis", "source_ref", "quarters"} or inventory.get("schema") != SCHEMA
            or inventory.get("noi_basis") != AFTER_RESERVES or not synthetic_id(inventory.get("source_ref"))
            or not isinstance(periods, list) or len(periods) != 4):
        return pending("four_documented_reserve_adjusted_noi_quarters_required")

    loan = object_or_empty(view.get("permanent_loan"))
    schedule = loan.get("projected_schedule")
    debt_sha = loan.get("loan_run_sha256")
    if (loan.get("quote_state") != "computed_synthetic" or loan.get("origination_date") != boundaries[0]
            or loan.get("payments_per_year") != 4 or not isinstance(schedule, list) or len(schedule) < 4
            or not isinstance(debt_sha, str) or len(debt_sha) != 64 or any(c not in "0123456789abcdef" for c in debt_sha)
            or any(day(object_or_empty(r).get("date")) is None for r in schedule)):
        return pending("quarterly_permanent_debt_schedule_unconfirmed")
    payments = [r for r in schedule if boundaries[0] < r["date"] <= boundaries[-1]]
    if [r["date"] for r in payments] != boundaries[1:]:
        return pending("permanent_debt_payment_dates_do_not_match_noi")

    rows, total_noi, total_service = [], Fraction(), Fraction()
    for index, (row, payment) in enumerate(zip(periods, payments, strict=True)):
        start, end = boundaries[index:index+2]
        period = object_or_empty(row)
        noi = quantity(period.get("noi_after_reserves"))
        if (set(period) != {"start", "end", "noi_after_reserves", "source_ref"} or (period["start"], period["end"]) != (start, end)
                or noi is None or not synthetic_id(period["source_ref"])):
            return pending("noi_quarter_missing_or_incompatible:" + end)
        service, interest, capital, balloon = (quantity(payment.get(k)) for k in
            ("scheduled_service_due", "interest_due", "principal_due", "balloon_due"))
        if (None in (service, interest, capital, balloon) or min(interest, capital) < 0 or balloon != 0
                or service != interest + capital):
            return pending("scheduled_service_missing_or_incompatible:" + end)
        total_noi += noi
        total_service += service
        rows.append(period | dict(scheduled_service=rational(service), available_cash=rational(noi - service)))

    retained = equity_at_refinance(view, cash, boundaries[0])
    if retained is None or retained < 0:
        return pending("equity_remaining_after_refinance_unconfirmed")
    proof = dict(window_start=boundaries[0], window_end=boundaries[-1], quarters=rows,
                 noi_after_reserves=rational(total_noi), scheduled_debt_service=rational(total_service),
                 cash_available=rational(total_noi-total_service), equity_remaining=rational(retained),
                 evidence_sha256=sha256(encoded(inventory)).hexdigest(), loan_run_sha256=debt_sha)
    if retained == 0:
        return proof | dict(state="N/A", blocker=None, value=None)
    return proof | dict(state="calculated_synthetic", blocker=None, value=rational((total_noi-total_service)/retained))
