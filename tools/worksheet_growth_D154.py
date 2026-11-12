"""Project declared annual growth over the dated windows of the synthetic worksheet."""
from datetime import date
from fractions import Fraction

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_project_calendar_D145 import offset


POLICY = "SYNTHETIC-D154-annual-growth-from-stabilization"
RULES = dict(
    convention="annual_effective_compounded_at_stabilization_anniversaries",
    window_weighting="twelve_full_months_each_at_its_applicable_annual_factor",
    rent_scope="residential_and_recognized_commercial_base_rent",
    expense_scope="fixed_opex_controllable_including_utilities_and_insurance",
    other_income="c13_flat",
    percentage_fees="recalculate_from_their_own_projected_bases",
    property_tax="recalculate_assessment_branch_keep_documented_comparable_floor",
    pre_stabilization="no_escalation",
    reserves_and_debt="retain_independent_terms",
)
GROWING_COSTS = ("controllable_total", "utilities_in_controllable", "controllable_excluding_utilities", "insurance_total")


def declared_growth(raw, scenario, review, calendar):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("rules") == RULES
            and synthetic_id(source.get("source_ref")), "growth_scope_or_convention_unconfirmed:C75-C76")
    scenarios = object_or_empty(source.get("scenarios"))
    record = object_or_empty(scenarios.get(scenario))
    require(record.keys() == {"scope_ref"} and synthetic_id(record["scope_ref"]),
            "scenario_growth_scope_unconfirmed:C75-C76")
    rows = {row["field_id"]: row for row in review["rows"]}
    rates, refs = {}, {}
    for cell, name in (("C75", "rent_growth"), ("C76", "expense_growth")):
        row = rows[f"INPUT_{cell}"]
        value = _fraction(row["value"])
        require(row["state"] == "CONFIRMED_SYNTHETIC" and value is not None and value > -1,
                f"growth_rate_unconfirmed_or_outside_positive_factor_profile:{cell}")
        rates[name] = rational(value)
        refs[cell] = row.get("alternative_value_source_ref", f"sha256:{review['workbook_sha256']}#{row['value_cell']}")
    return dict(policy_ref=source["source_ref"], scenario_scope_ref=record["scope_ref"], rules=source["rules"],
                cell_sources=refs, anchor=calendar["stabilization_date"], **rates)


def project_window(terms, window_start):
    anchor, start = (date.fromisoformat(value) for value in (terms["anchor"], window_start))
    require(anchor.day == start.day == 1 and start >= anchor, "growth_window_outside_stabilized_month_grid")
    months_since_anchor = (start.year - anchor.year) * 12 + start.month - anchor.month
    years = [(months_since_anchor + index) // 12 for index in range(12)]
    rent_monthly = [(1 + _fraction(terms["rent_growth"])) ** year for year in years]
    expense_monthly = [(1 + _fraction(terms["expense_growth"])) ** year for year in years]
    return terms | dict(window_start=window_start, window_end_exclusive=offset(start, 12).isoformat(),
                        completed_anniversaries_by_month=years, rent_month_factors=[rational(x) for x in rent_monthly],
                        expense_month_factors=[rational(x) for x in expense_monthly],
                        rent_factor=rational(sum(rent_monthly) / 12),
                        expense_factor=rational(sum(expense_monthly) / 12))


def projected_expense_terms(terms, projection):
    factor = _fraction(projection["expense_factor"])
    expenses = terms["expenses"] | {"fixed_opex": rational(_fraction(terms["expenses"]["fixed_opex"]) * factor)}
    costs = terms["operating_costs"]
    costs = costs | {key: rational(_fraction(costs[key]) * factor) for key in GROWING_COSTS}
    utilities = terms["utility_evidence"]
    rows = []
    for row in utilities["rows"]:
        rate = _fraction(row["monthly_rate"])
        rows.append(row | dict(monthly_rate=None if rate is None else rational(rate * factor),
                               annual_expense=rational(_fraction(row["annual_expense"]) * factor)))
    utilities = utilities | dict(rows=rows, annual_total=costs["utilities_in_controllable"])
    utility_items = [row | dict(rate=rational(_fraction(row["rate"]) * factor)) for row in terms["utility_expenses"]]
    return terms | dict(expenses=expenses, operating_costs=costs, utility_evidence=utilities, utility_expenses=utility_items)
