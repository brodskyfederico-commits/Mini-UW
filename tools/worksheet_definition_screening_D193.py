"""Produce candidate SRC-02 and SRC-03 values from the audited project view."""
from datetime import date
from fractions import Fraction
import json

from check_worksheet_return_metrics_D167 import quarterly_cash
from miniuw_foundation.debt_service import _fraction as amount, rational
from plan_refinance_D108 import VALUE_PERIOD
from worksheet_local_sources_D127 import number, object_or_empty, synthetic_id
from worksheet_performance_policy_D184 import AFTER_RESERVES, BEFORE_RESERVES, equilibrium, price_screen


OCCUPANCY = "breakeven_occupancy"
RLV = "asking_relative_to_supported_price"
YOC = "SYNTHETIC-D193-reserve-adjusted-YoC"
SPREAD = "SYNTHETIC-D193-spread-aligned-to-cap-NOI"
ECONOMIC = "SYNTHETIC-D193-economic-occupancy-after-reserves"
PHYSICAL = "SYNTHETIC-D193-physical-occupancy-after-reserves"
PRICE = "SYNTHETIC-D193-asking-over-fixed-debt-grid-RLV-band"
PRICE_BASIS = "fixed_debt_with_C33"
RATE_BASIS = "nominal_annual_fixed_convertible_quarterly"


def land_band_rules(fail_boundary):
    """Compare asking/RLV against the two fixed-debt search boundaries."""
    return {
        "PASS": dict(operator="<=", threshold=rational(Fraction(1))),
        "FAIL": dict(operator=">", threshold=fail_boundary),
    }


def pending(reason, **evidence):
    return dict(state="PENDING", blocker=reason, **evidence)


def annual_inputs(view):
    annual = view["noi_by_period"][VALUE_PERIOD]
    start = date.fromisoformat(annual["growth"]["window_start"])
    end = date.fromisoformat(annual["growth"]["window_end_exclusive"])
    reserve = view["replacement_reserve"]
    factors = annual["growth"]["expense_month_factors"]
    if len(factors) != 12 or end != start.replace(year=start.year + 1):
        return None
    totals = amount(reserve["annual_rate"]) * reserve["eligible_units"] * sum(map(amount, factors)) / 12
    return annual, totals, f"{start}/{end}"


def occupancy(view, annual, reserve, period, policy):
    if not synthetic_id(policy.get("source_ref")) or policy.get("definition") not in (ECONOMIC, PHYSICAL):
        return pending("SRC-02_occupancy_basis_missing")
    loan = view["permanent_loan"]
    if (loan["rules"]["rate"] != RATE_BASIS or loan["maturity_date"] < period.split("/")[1]
            or annual["commercial"]["recognized_months"] != 12):
        return pending("SRC-02_annual_stabilized_debt_service_unconfirmed")
    costs = annual["operating_costs"]
    gross, effective = (amount(annual[field]) for field in ("gross_rent", "effective_rent"))
    management_rate = amount(costs["management_rate"])
    slope = gross * (1 - management_rate)
    tax = annual["property_tax"]
    effective_fixed = amount(annual["operating_expenses_excluding_tax"]) - effective * management_rate
    intercept = amount(annual["other_income"]) + amount(annual["commercial"]["net"]) - effective_fixed
    if (slope <= 0 or gross <= 0 or not 0 <= management_rate < 1
            or slope * (effective / gross) + intercept != amount(tax["operating_before_tax"])):
        return pending("SRC-02_annual_revenue_cost_basis_does_not_reconcile")
    inputs = dict(slope=slope, intercept=intercept, floor=amount(tax["floor"]),
                  tax_coefficient=amount(tax["coefficient"]), debt_service=amount(loan["annual_sizing_service"]),
                  reserve=reserve)
    breakdown = object_or_empty(policy.get("physical_breakdown"))
    physical_vacancy, credit_loss, concessions = (number(breakdown.get(key))
                                                     for key in ("physical_vacancy", "credit_loss", "concessions"))
    split_issue = None
    if not (synthetic_id(breakdown.get("source_ref")) and
            all(x is not None and 0 <= x < 1 for x in (physical_vacancy, credit_loss, concessions))):
        split_issue = "C14_sin_desglose"
    elif gross * (1 - physical_vacancy) * (1 - credit_loss) * (1 - concessions) != effective:
        split_issue = "SRC-02_physical_breakdown_does_not_reconcile"
    if split_issue:
        credit_loss = concessions = None
    result = equilibrium(**inputs, credit_loss=credit_loss, concessions=concessions)
    if split_issue:
        result["physical_blocker"] = split_issue
    mode = "physical" if policy["definition"] == PHYSICAL else "economic"
    return dict(state="PENDING" if result[mode] is None else result[f"{mode}_state"],
                blocker=result["physical_blocker"] if result[mode] is None else None,
                definition=policy["definition"], period=period, source_ref=policy["source_ref"],
                calculation=result, inputs=inputs, value=result[mode],
                supporting_sources=dict(noi_sha256=annual["noi_assembly_sha256"], debt_sha256=loan["loan_run_sha256"],
                                        reserve=view["replacement_reserve"]["cell_source"],
                                        C14=view["cell_sources"]["C14"], physical_breakdown=breakdown))


def rlv(view, policies, records, evidence, criteria, before_reserve, after_reserve, cap, cap_basis):
    if not synthetic_id(policies.get("source_ref")) or policies.get("basis") != PRICE_BASIS:
        return pending("SRC-03_fixed_debt_price_basis_missing")
    yield_metric = policies.get("yield_metric")
    if yield_metric not in ("YoC", "spread"):
        return pending("SRC-03_yield_or_spread_criterion_not_designated")
    if yield_metric == "spread" and (cap is None or cap_basis not in (AFTER_RESERVES, BEFORE_RESERVES)):
        return pending("SRC-03_cap_basis_unconfirmed")
    rules = {}
    for target, key in (("yield_or_spread", yield_metric), ("annual_irr", "IRR"),
                        ("equity_multiple", "equity_multiple"), ("equity_to_tdc", "equity_TDC")):
        supplied = criteria.get(key)
        metric = records[key]
        if supplied is None or any(supplied[1][field] != metric[field] or metric[field] is None
                                   for field in ("definition_ref", "unit", "period_ref")):
            return pending(f"SRC-03_incompatible_or_missing_criterion:{key}")
        pc, fc = (supplied[1][field] for field in ("pass_condition", "fail_condition"))
        values = (pc["operator"], number(pc["threshold"]), fc["operator"], number(fc["threshold"]))
        if values[1] is None or values[3] is None:
            return pending(f"SRC-03_incomplete_criterion:{key}")
        rules[target] = values

    cash = view["cash_per_usd_10"]
    scale = amount(cash["scale_factor"])
    grid = view["project_calendar"]["equity_dates"]
    flows = quarterly_cash(cash, grid)
    cost = evidence["cost_basis"]
    development = view["development_costs"]
    grid_prices, rates = policies.get("grid"), policies.get("quarterly_irr_thresholds")
    if (not isinstance(grid_prices, list) or len(grid_prices) != 3 or
            not isinstance(rates, list) or len(rates) != 2):
        return pending("SRC-03_grid_or_quarterly_threshold_missing")
    quarterly = list(map(number, rates))
    if (flows is None or scale <= 0 or None in quarterly or cost["tdc"] is None or
            records["IRR"]["period_ref"] != f"{grid[0]}/{grid[-1]}"):
        return pending("SRC-03_cash_cost_or_quarterly_basis_unavailable")

    source = dict(
        price=amount(development["evaluated_purchase_price"]), asking=amount(development["worksheet_asking"]),
        closing_rate=amount(development["closing_fraction"]), tdc=amount(cost["tdc"]),
        applied_equity=amount(cost["applied_equity"]), debt=amount(cost["components"]["loan_draw"]),
        contributions=amount(cash["total_contributions"]) / scale, distributions=amount(cash["total_distributions"]) / scale,
        net_flows=[value / scale for value in flows.values()], cap=cap if yield_metric == "spread" else None,
        cap_noi_basis=cap_basis if yield_metric == "spread" else None, noi_before=before_reserve, noi_uw=after_reserve,
        quarterly_irr_thresholds=quarterly,
    )
    if any(source[key] is None for key in ("price", "asking", "closing_rate")) or source["asking"] < 0:
        return pending("SRC-03_asking_purchase_or_C33_missing")
    try:
        result = price_screen(source, rules, grid_prices)
    except ValueError as error:
        return pending("SRC-03_invalid_fixed_debt_profile", detail=str(error))
    ratio = result.get("asking_over_pass_price") if result["state"] == "calculated_synthetic" else None
    blocker = result["blocker"]
    if policies.get("application") != "compare_synthetic":
        ratio = None
        blocker = blocker or "SRC-03_applicability_pending"
    elif ratio is None:
        blocker = blocker or "SRC-03_nonpositive_RLV_ratio_undefined"
    return dict(state=result["state"] if ratio is not None else "PENDING", blocker=blocker,
                definition=PRICE, period=records["equity_multiple"]["period_ref"],
                source_ref=policies["source_ref"], value=ratio, calculation=result,
                fail_boundary_multiple=(Fraction(result["before_fail"], result["pass_price"])
                                        if ratio is not None else None),
                criterion_locators={key: f"/rules/{criteria[key][0]}" for key in
                                    (yield_metric, "IRR", "equity_multiple", "equity_TDC")},
                inputs=source | {"cash_dates": grid, "price_source": development["purchase_source_ref"],
                                 "C33": development["cell_sources"]["C33"]})


def extend(view, section, supplied, criteria, records, evidence, irr):
    """Attach versioned metrics and producer evidence before B14 evaluates thresholds."""
    records = {key: value.copy() for key, value in records.items()}
    records["IRR"]["period_ref"] = irr.get("period_ref")
    records["YoC"]["definition_ref"] = YOC
    records["spread"]["definition_ref"] = SPREAD

    def apply(key, produced, default):
        records[key].update(definition_ref=produced.get("definition", default), period_ref=produced.get("period"),
                            source_pointer=f"/screening/metric_evidence_by_scenario/{records[key]['scenario_id']}/"
                                           f"candidate_definitions/{key}/value",
                            value=None if produced.get("value") is None else rational(produced["value"]),
                            blockers=[produced["blocker"]] if produced["blocker"] else [])

    details = {OCCUPANCY: pending("SRC-02_audited_annual_inputs_unavailable"),
               RLV: pending("SRC-03_audited_annual_inputs_unavailable")}
    annual_data = annual_inputs(view) if view.get("cash_per_usd_10") is not None else None
    if annual_data is None:
        for key in ("YoC", "spread"):
            records[key].update(value=None, blockers=["SRC-03_annual_performance_inputs_unavailable"])
    else:
        annual, reserve, period = annual_data
        before = amount(annual["noi"])
        after = before - reserve
        cap_record = object_or_empty(supplied.get("reference_cap"))
        cap = number(cap_record.get("value"))
        cap_basis = section.get("comparable_cap_noi_basis")
        if (not synthetic_id(cap_record.get("source_ref")) or cap_record.get("period_ref") != period
                or cap is None or not 0 < cap <= 1):
            cap = None
        cost = number(evidence["cost_basis"]["tdc"])
        for key, noi, subtraction in (("YoC", after, Fraction()),
                                      ("spread", {AFTER_RESERVES: after, BEFORE_RESERVES: before}.get(cap_basis), cap)):
            value = None if cost is None or noi is None or subtraction is None else (
                (noi / cost - subtraction) * (10_000 if key == "spread" else 1)
            )
            apply(key, dict(value=value, period=period, blocker=None if value is not None else
                            "SRC-03_tdc_or_comparable_NOI_basis_unconfirmed"), YOC if key == "YoC" else SPREAD)
            details[key] = dict(value=value, annual_reserve=reserve, noi_before_reserve=before, noi_after_reserve=after,
                                cap=cap if key == "spread" else None, cap_noi_basis=cap_basis if key == "spread" else None,
                                noi_sha256=annual["noi_assembly_sha256"])
        details[OCCUPANCY] = occupancy(view, annual, reserve, period, object_or_empty(section.get("occupancy")))
        details[RLV] = rlv(view, object_or_empty(section.get("rlv")), records, evidence, criteria,
                           before, after, cap, cap_basis)
    apply(OCCUPANCY, details[OCCUPANCY], ECONOMIC)
    apply(RLV, details[RLV], PRICE)
    details = json.loads(json.dumps(details, default=rational))
    return records, evidence | {"candidate_definitions": details}
