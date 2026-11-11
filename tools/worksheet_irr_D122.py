"""Compute and compare a synthetic annual IRR enclosure from audited cash."""
from datetime import date
from fractions import Fraction
from math import ceil, floor

from check_operating_replay_D20 import amount
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.irr_checked_output import _current_annual_roots
from miniuw_foundation.irr_interval_output import ENGINE_SHA256 as INTERVAL_ENGINE_SHA256
from miniuw_foundation.irr_interval_output import VALUE_DEFINITION, _annual_enclosure, _compare
from miniuw_foundation.primitive_periodic_returns import isolate_primitive_periodic_returns
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded


IRR_POLICY = "SYNTHETIC-D122-month-start-grid-v1"
IRR_METRIC = ("fraction", "scalar", None, VALUE_DEFINITION)


def annual_evidence(cash, policy):
    result = dict(policy=policy, period_ref=None, cash_pointer=None, cash_sha256=None,
                  dated_net_flows=[], periodic_result=None, annual_enclosure=None, blockers=[])
    if cash is None:
        return result | {"blockers": ["current_scenario_cash_unavailable"]}
    result.update(cash_pointer="cash_per_usd_10", cash_sha256=sha(encoded(cash)))
    if policy != IRR_POLICY:
        return result | {"blockers": ["explicit_synthetic_monthly_IRR_policy_missing_or_unsupported"]}

    events = cash["events"]
    if not events:
        return result | {"blockers": ["current_scenario_cash_unavailable"]}
    dates = [date.fromisoformat(event["date"]) for event in events]
    first, last = min(dates), max(dates)
    period_ref = f"{first.isoformat()}/{last.isoformat()}"
    month_indices = [day.year * 12 + day.month - 1 for day in dates]
    first_month = min(month_indices)
    count = max(month_indices) - first_month + 1
    if any(day.day != 1 for day in dates) or count > 65:
        return result | {"period_ref": period_ref, "blockers": ["cash_dates_outside_supported_month_start_grid"]}

    flows = [Fraction()] * count
    for event, month in zip(events, month_indices, strict=True):
        value = amount(event["amount"])
        flows[month - first_month] += -value if event["kind"] == "contribution" else value
    net = []
    for offset, value in enumerate(flows):
        year, zero_based_month = divmod(first_month + offset, 12)
        net.append(dict(date=date(year, zero_based_month + 1, 1).isoformat(), net=rational(value)))
    roots = isolate_primitive_periodic_returns(flows, Fraction(1, 100_000_000), 128, 50_000)
    annual, _, annual_blockers = _current_annual_roots(roots, 12, 1)
    enclosure, blockers = _annual_enclosure(dict(periodic_irr=roots, annual_irr_roots=annual),
                                           dict(annualization_blockers=annual_blockers))
    return result | dict(period_ref=period_ref, dated_net_flows=net, periodic_result=roots,
                         annual_enclosure=enclosure, blockers=sorted(set(blockers + annual_blockers)))


def combine_irr(screening, rules, scenarios, policy, case_sha256):
    evidence = {}
    comparisons = list(screening["comparisons"])
    global_blockers = list(screening["simulation_blockers"])
    pending_review = list(screening["pending_review_metrics"])
    indexed = {rule["scenario_id"]: (index, rule) for index, rule in rules}
    for name, scenario in scenarios.items():
        result = annual_evidence(scenario["cash_per_usd_10"], policy)
        criterion_index, criterion = indexed.get(name, (None, None))
        criterion_path = None if criterion_index is None else f"/rules/{criterion_index}"
        if criterion is None:
            state, relations, blockers = "PENDING", {}, ["criterion_record_missing"]
        else:
            state, relations, blockers = _compare(result["annual_enclosure"], criterion | {"source_ref": criterion_path},
                                                  result["period_ref"])
        blockers = sorted(set(blockers + result["blockers"]))
        global_blockers.extend(f"IRR:{name}:{blocker}" for blocker in blockers)
        result |= dict(case_sha256=case_sha256, criterion_pointer=criterion_path, comparison_state=state,
                       condition_relations=relations, comparison_blockers=blockers)
        evidence[name] = result
        metric_path = f"/screening/irr_by_scenario/{name}/annual_enclosure"
        comparisons.append(dict(metric_id="IRR", scenario_id=name, state=state, blockers=blockers,
                                metric_locator=metric_path, criterion_locator=criterion_path, criterion_record=criterion,
                                metric_record=dict(definition_ref=VALUE_DEFINITION, unit="fraction",
                                                   period_ref=result["period_ref"], annual_enclosure=result["annual_enclosure"])))
        if state == "BAND":
            pending_review.append(dict(metric_id="IRR", scenario_id=name, metric_locator=metric_path,
                                       criterion_locator=criterion_path))

    simulation = "PENDING"
    if not global_blockers:
        simulation = "FAIL" if any(row["state"] == "FAIL_CONDITION" for row in comparisons) else "PASS"
    return screening | dict(component="D122", interval_engine_sha256=INTERVAL_ENGINE_SHA256,
                            required_metrics=[*screening["required_metrics"], "IRR"], comparisons=comparisons,
                            irr_by_scenario=evidence, simulation_result=simulation,
                            simulation_blockers=sorted(set(global_blockers)), pending_review_metrics=pending_review,
                            professional_review_needed_for_band=bool(pending_review))


def display_enclosure(interval):
    if interval is None:
        return "PENDING"
    lower = floor(_fraction(interval["lower"], 1300) * 10_000)
    upper = ceil(_fraction(interval["upper"], 1300) * 10_000)
    return " a ".join(f"{'-' if value < 0 else ''}{abs(value) // 100},{abs(value) % 100:02d}%"
                      for value in (lower, upper))
