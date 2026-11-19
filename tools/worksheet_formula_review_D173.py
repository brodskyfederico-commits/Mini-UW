"""Require explicit buyer-tax and post-refinance cash-on-cash scopes."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import check, number, object_or_empty, synthetic_id


PROFILE = "synthetic_documented_buyer_tax_and_return"
BUYER_BASIS = "buyer_tax_for_exact_forward_window"
COC_BASIS = "period_noi_less_scheduled_debt_service_over_equity_still_invested_at_refinance"


def forward_buyer_tax(raw, name, calendar):
    record = object_or_empty(object_or_empty(raw).get(name))
    dates = (calendar["sale_date"], calendar["exit_forward_end"])
    require(record.keys() == {"basis", "currency", "window_start", "window_end", "school_tax", "non_school_tax", "source_ref"}
            and record["basis"] == BUYER_BASIS and record["currency"] == "USD"
            and (record["window_start"], record["window_end"]) == dates and synthetic_id(record["source_ref"]),
            "buyer_forward_property_tax_source_or_window_unconfirmed")
    school, non_school = (number(record[key]) for key in ("school_tax", "non_school_tax"))
    require(school is not None and non_school is not None and school >= 0 and non_school >= 0,
            "buyer_forward_property_tax_components_unconfirmed")
    return record | dict(total=rational(school + non_school), source_sha256=sha(encoded(record)))


def post_refi_coc(raw, name, view, *, require_noi_basis=False, property_tax=None):
    result = dict(definition=COC_BASIS, value=None, annualized=False)
    calendar = view.get("project_calendar")
    if calendar is None or view.get("cash_per_usd_10") is None:
        return check("verified_cash_and_refinance_dates_required", **result)
    start, end = calendar["refinance_date"], calendar["sale_date"]
    result.update(window_start=start, window_end=end)
    record = object_or_empty(object_or_empty(raw).get(name))
    fields = {"basis", "currency", "window_start", "window_end", "period_noi",
              "noi_source_ref", "equity_still_invested", "equity_source_ref"}
    if require_noi_basis:
        from worksheet_performance_policy_D184 import AFTER_RESERVES
        fields.add("noi_basis")
        if record.get("noi_basis") != AFTER_RESERVES:
            return check("post_refi_reserve_adjusted_noi_basis_unconfirmed", **result)
        result["noi_basis"] = AFTER_RESERVES
    if property_tax is not None:
        fields.remove("period_noi")
        fields.add("period_noi_before_property_tax")
    if (record.keys() != fields
            or record["basis"] != COC_BASIS or record["currency"] != "USD"
            or (record["window_start"], record["window_end"]) != (start, end)
            or not all(synthetic_id(record[key]) for key in ("noi_source_ref", "equity_source_ref"))):
        return check("post_refi_noi_and_equity_evidence_or_window_unconfirmed", **result)
    if property_tax is None:
        noi = number(record["period_noi"])
    else:
        before_tax = number(record["period_noi_before_property_tax"])
        noi = None if before_tax is None else before_tax - number(property_tax["total"])
        result["property_tax"] = property_tax
    equity = number(record["equity_still_invested"])
    debt = view["dated_debt_service"]
    try:
        service = _fraction(debt["scheduled_service_due"], 1300)
    except (ValueError, TypeError):
        service = None
    result.update(period_noi=record["period_noi"] if property_tax is None else (None if noi is None else rational(noi)),
                  equity_still_invested=record["equity_still_invested"],
                  scheduled_debt_service=debt["scheduled_service_due"], debt_payment_date=debt["date"],
                  debt_source_ref=view["permanent_loan"]["loan_run_sha256"],
                  source_sha256=sha(encoded(record)), source=record)
    if noi is None or equity is None or equity <= 0 or service is None or service < 0 or debt["date"] != end:
        return check("post_refi_noi_debt_service_or_positive_remaining_equity_unconfirmed", **result)
    return check(**(result | dict(value=rational((noi - service) / equity))))
