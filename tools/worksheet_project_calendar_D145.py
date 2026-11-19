"""Bind confirmed worksheet durations to the dated synthetic project cash cycle."""
from datetime import date

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _date, _fraction, rational
from plan_refinance_D108 import BANK_PERIOD, PAYMENT_DATES, VALUE_PERIOD
from plan_return_D107 import DATES, FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D145-quarterly-project-calendar"
LIFECYCLE = "SYNTHETIC-D145-purchase-through-sale"
TIMING_RULES = dict(cash_grid="quarterly_day_30", construction_origin="declared_start_on_purchase_checkpoint",
                    lease_up_origin="declared_tco_first_of_quarter", stabilized_cash_window="12_full_months_from_stabilization",
                    refinance="nine_months_from_stabilization_checkpoint", sale="twelve_months_from_stabilization_checkpoint",
                    lease_up_funding="net_shortfall_reserved_at_construction_finish", outside_window_cash="zero_net_cash")


def offset(day, months):
    year, index = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, index + 1, day.day)


def confirmed_months(rows, cell, minimum):
    row = rows[cell]
    require(row["state"] == "CONFIRMED_SYNTHETIC", f"project_duration_unconfirmed:{cell}")
    months = _fraction(row["value"])
    require(months is not None and minimum <= months <= 36 and months % 3 == 0,
            f"project_duration_outside_quarterly_profile:{cell}")
    return int(months)


def project_calendar(raw, name, review, purchase_date, *, sale_term=None, holding_horizon=None):
    if holding_horizon is not None:
        from worksheet_holding_horizon_D266 import horizon_calendar
        return horizon_calendar(raw, name, review, purchase_date, sale_term, holding_horizon)
    source = object_or_empty(raw)
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    require(source.get("policy") == POLICY and source.get("rules") == TIMING_RULES
            and synthetic_id(source.get("policy_ref")), "project_calendar_policy_unconfirmed")
    rows = {row["value_cell"].split("!")[1]: row for row in review["rows"]}
    construction = confirmed_months(rows, "C46", 3)
    lease_up = confirmed_months(rows, "C47", 0)
    require(purchase_date == DATES[0] == record.get("construction_start") and synthetic_id(record.get("start_ref")),
            "construction_start_unconfirmed:C46")
    start = date.fromisoformat(purchase_date)
    completion = offset(start, construction)
    tco_text = record.get("tco_date")
    require(isinstance(tco_text, str) and synthetic_id(record.get("tco_ref")), "lease_up_origin_unconfirmed:C47")
    tco = _date(tco_text)
    require(tco.isoformat() == tco_text and tco.day == 1 and tco.month in (1, 4, 7, 10) and completion < tco,
            "tco_conflicts_with_construction_or_quarterly_grid:C46-C47")
    tco_checkpoint = offset(tco, -1).replace(day=30)
    stabilized_start = offset(tco, lease_up)
    stabilization_checkpoint = offset(tco_checkpoint, lease_up)
    refi = offset(stabilization_checkpoint, 9)
    sale = offset(stabilization_checkpoint, 12)
    sale_evidence = {}
    if sale_term is not None:
        declared = _date(sale_term["value"])
        # This profile has one permanent-loan payment and a twelve-month
        # stabilized seller operating window.
        require(declared == sale, "declared_sale_date_outside_supported_quarterly_hold")
        sale = declared
        sale_evidence = dict(sale_source_ref=sale_term["source_ref"])
    horizon = (sale.year - start.year) * 12 + sale.month - start.month
    require(horizon <= 192, "project_calendar_horizon_outside_equity_grid")
    monthly_shortfall = _fraction(record.get("lease_up_shortfall_per_month"))
    early_hard_share = _fraction(record.get("upfront_direct_hard_share"))
    require(monthly_shortfall is not None and monthly_shortfall >= 0 and synthetic_id(record.get("lease_up_cash_ref")),
            "lease_up_cash_basis_unconfirmed:C47")
    require(early_hard_share is not None and 0 <= early_hard_share <= 1 and synthetic_id(record.get("construction_draw_ref")),
            "construction_funding_split_unconfirmed:C46")
    return dict(
        cell_sources={cell: rows[cell].get("sensitivity_value_source_ref", f"sha256:{review['workbook_sha256']}#{rows[cell]['value_cell']}") for cell in ("C46", "C47")},
        policy_ref=source["policy_ref"], rules=source["rules"],
        purchase_date=purchase_date, construction_start=purchase_date, construction_start_ref=record["start_ref"],
        upfront_date=offset(start, 3).isoformat(), construction_months=construction, construction_finish=completion.isoformat(),
        tco_date=tco_text, tco_ref=record["tco_ref"], lease_up_months=lease_up, stabilization_date=stabilized_start.isoformat(),
        refinance_date=refi.isoformat(), sale_date=sale.isoformat(), exit_forward_end=offset(sale, 12).isoformat(),
        operating_window=[stabilized_start.isoformat(), offset(stabilized_start, 12).isoformat()],
        noi_window_starts={OPERATING_PERIOD: stabilized_start.isoformat(), FORWARD_PERIOD: offset(stabilized_start, 12).isoformat(),
                           BANK_PERIOD: offset(stabilized_start, 9).isoformat(), VALUE_PERIOD: offset(stabilized_start, 9).isoformat()},
        equity_dates=[offset(start, month).isoformat() for month in range(0, horizon + 1, 3)],
        payment_dates=[offset(refi, 3 * index).isoformat() for index in range(1, len(PAYMENT_DATES) + 1)],
        lease_up_funding=rational(monthly_shortfall * lease_up), lease_up_shortfall_per_month=rational(monthly_shortfall),
        lease_up_cash_ref=record["lease_up_cash_ref"], upfront_direct_hard_share=rational(early_hard_share),
        construction_draw_ref=record["construction_draw_ref"],
    ) | sale_evidence
