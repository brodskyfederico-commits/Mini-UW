"""Compute the two remaining pilot ratios under explicit synthetic scopes."""
from fractions import Fraction
from operator import ge, gt

from check_operating_replay_D20 import amount, require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.screening import _overlap
from miniuw_worksheet_v1 import encoded


COC = "post_refi_CoC"
ASKING = "asking_relative_to_supported_price"
COC_BASIS = "SYNTHETIC-D126-post-refinance-observed-cash-over-declared-capital"
PRICE_BASIS = "SYNTHETIC-D126-only-acquisition-cost-and-initial-equity-change"
METRICS = {
    COC: ("fraction", "scalar", None, COC_BASIS),
    ASKING: ("multiple", "scalar", None, "SYNTHETIC-D126-asking-over-finite-two-target-price-grid"),
}
PRICE_TARGETS = ("YoC", "equity_multiple")
MINIMUM_OPERATORS = {">": gt, ">=": ge}


def post_refinance_coc(cash, basis, capital_bases):
    result = dict(value=None, period_ref=None, operating_receipts=None, capital_base=None,
                  operating_event_ids=[], annualized=False)
    if basis != COC_BASIS:
        return result | {"blockers": ["explicit_post_refinance_cash_basis_missing_or_unsupported"]}
    events = cash["events"]
    dates = {row["date"] for row in events if row["category"] in ("net_refinance_distribution", "refinance_cash_in")}
    exits = {row["date"] for row in events if row["category"] == "net_sale_distribution"}
    if len(dates) != 1 or len(exits) != 1:
        return result | {"blockers": ["verified_refinance_and_sale_window_required"]}
    start, = dates
    end, = exits
    result["period_ref"] = f"{start}/{end}"
    if start >= end or start[:4] != end[:4]:
        return result | {"blockers": ["single_calendar_year_post_refinance_window_required"]}
    base = _fraction(capital_bases.get(start[:4]))
    if base is None or base <= 0:
        return result | {"blockers": ["positive_declared_pilot_capital_base_required"]}
    operating = [row for row in events if row["category"] == "operating_distribution" and start < row["date"] <= end]
    receipts = sum((amount(row["amount"]) for row in operating), Fraction()) / amount(cash["scale_factor"])
    return result | dict(value=rational(receipts / base), operating_receipts=rational(receipts), capital_base=rational(base),
                         operating_event_ids=[row["event_id"] for row in operating], blockers=[])


def minimum_targets(case, name, values):
    targets = {}
    rules = case.get("rules")
    if not isinstance(rules, list):
        return None
    for metric in PRICE_TARGETS:
        matches = [row for row in rules if isinstance(row, dict)
                   and (row.get("scenario_id"), row.get("metric_id")) == (name, metric)]
        value = values.get((name, metric))
        if len(matches) != 1 or value is None or not case.get("criteria_revision"):
            return None
        rule, = matches
        if any(rule.get(field) is None or rule[field] != value[field] for field in ("definition_ref", "unit", "period_ref")):
            return None
        passing, failing = rule.get("pass_condition"), rule.get("fail_condition")
        if not isinstance(passing, dict) or not isinstance(failing, dict):
            return None
        operator, threshold = passing.get("operator"), _fraction(passing.get("threshold"))
        if (operator not in (">", ">=") or threshold is None or threshold <= 0 or failing.get("operator") not in ("<", "<=")
                or _fraction(failing.get("threshold")) is None or _overlap(passing, failing)):
            return None
        targets[metric] = (operator, threshold)
    return targets


def supported_price(case, name, pricing, cash, budget, values):
    result = dict(value=None, period_ref=cash["events"][0]["date"], asking=None, supported_price=None, grid=None,
                  evaluated_prices=0, feasible_prices=0, objectives=None, boundary=None)
    if not isinstance(pricing, dict) or not pricing.keys() <= {"basis", "as_of", "asking", "lower", "upper", "step"}:
        return result | {"blockers": ["explicit_price_grid_missing_or_invalid"]}
    if pricing.get("basis") != PRICE_BASIS or pricing.get("as_of") != result["period_ref"]:
        return result | {"blockers": ["compatible_price_reflow_basis_required"]}
    low, high, step = (pricing.get(key) for key in ("lower", "upper", "step"))
    if (any(type(value) is not int for value in (low, high, step)) or not 0 <= low <= high <= 10**9
            or step <= 0 or (high - low) % step or (high - low) // step > 1000):
        return result | {"blockers": ["explicit_bounded_integer_USD_grid_required"]}
    if budget["tdc"] is None or budget["stabilized_noi"] is None:
        return result | {"blockers": ["current_complete_TDC_and_stabilized_NOI_required"]}
    source = case["yield_inputs"][name]["tdc"]
    acquisition, = (amount(row["amount"]) for row in source["rows"] if row["component"] == "acquisition")
    if sha(encoded(source)) != budget["tdc_source_sha256"]:
        return result | {"blockers": ["price_TDC_source_revision_mismatch"]}
    targets = minimum_targets(case, name, values)
    if targets is None:
        return result | {"blockers": ["compatible_YoC_and_equity_multiple_minimum_rules_required"]}
    factor = amount(cash["scale_factor"])
    initial = amount(cash["reference_amount"]) / factor
    tdc, noi = amount(budget["tdc"]), amount(budget["stabilized_noi"])
    contributions = amount(cash["total_contributions"]) / factor
    distributions = amount(cash["total_distributions"]) / factor
    if initial + low - acquisition <= 0 or tdc + low - acquisition <= 0:
        return result | {"blockers": ["positive_cost_and_initial_equity_required_across_grid"]}

    def outcome(price):
        delta = price - acquisition
        return {"YoC": noi / (tdc + delta), "equity_multiple": distributions / (contributions + delta)}

    grid = range(low, high + 1, step)
    feasible = []
    for price in grid:
        projected = outcome(price)
        if all(MINIMUM_OPERATORS[operator](projected[metric], threshold)
               for metric, (operator, threshold) in targets.items()):
            feasible.append(price)
    result.update(grid=dict(lower=low, upper=high, step=step), evaluated_prices=len(grid), feasible_prices=len(feasible),
                  objectives={metric: dict(operator=op, threshold=rational(value)) for metric, (op, value) in targets.items()})
    if not feasible:
        return result | {"blockers": ["no_supported_price_on_declared_grid"]}
    maximum = max(feasible)
    next_price = maximum + step
    result.update(supported_price=rational(Fraction(maximum)),
                  boundary=dict(at_maximum={metric: rational(value) for metric, value in outcome(maximum).items()},
                                next_grid_price=next_price if next_price <= high else None,
                                at_next={metric: rational(value) for metric, value in outcome(next_price).items()}
                                if next_price <= high else None))
    asking = _fraction(pricing.get("asking"))
    if asking is None or asking < 0 or maximum <= 0:
        return result | {"blockers": ["asking_or_positive_supported_price_unavailable"]}
    return result | dict(asking=rational(asking), value=rational(asking / maximum), blockers=[])


def final_metric_records(case, scenarios, budgets, metric_values, case_sha256):
    inventory = case.get("return_inputs")
    inventory = {} if inventory is None else inventory
    require(isinstance(inventory, dict) and inventory.keys() <= scenarios.keys(),
            "Return metric inputs must identify explicit pilot scenarios")
    current = {(row["scenario_id"], row["metric_id"]): row for row in metric_values}
    values, evidence = [], {}
    for name, scenario in scenarios.items():
        group, cash = inventory.get(name), scenario["cash_per_usd_10"]
        if (cash is None or not isinstance(group, dict) or not group.keys() <= {"workbook_sha256", "coc_basis", "pricing"}
                or group.get("workbook_sha256") != scenario["preflight"]["workbook_sha256"]):
            rows = {key: dict(value=None, period_ref=None, blockers=["current_return_source_or_binding_unavailable"]) for key in METRICS}
        else:
            rows = {
                COC: post_refinance_coc(cash, group.get("coc_basis"), scenario.get("calendar_capital_bases") or {}),
                ASKING: supported_price(case, name, group.get("pricing"), cash, budgets[name], current),
            }
        evidence[name] = dict(case_sha256=case_sha256, source_pointer=f"/return_inputs/{name}", metrics=rows,
                              cash_sha256=None if cash is None else sha(encoded(cash)))
        for metric, (unit, kind, currency, definition) in METRICS.items():
            row = rows[metric]
            values.append(dict(metric_id=metric, scenario_id=name, definition_ref=definition, unit=unit,
                               quantity_kind=kind, currency=currency, period_ref=row["period_ref"],
                               applicability="applicable", applicability_evidence_ref=None, value=row["value"]))
    return values, evidence
