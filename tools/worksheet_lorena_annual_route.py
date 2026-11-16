"""Connect the audited D234 calendar route to the worksheet criteria adapter."""

from fractions import Fraction
from hashlib import sha256

from check_worksheet_return_metrics_D167 import quarterly_cash, verify_irr
from miniuw_foundation.debt_service import rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.lorena_screening import SCENARIOS, encode
from reconcile_worksheet_D179 import annual_irr_interval
from worksheet_annual_coc import quantity as amount
from worksheet_definition_screening_D193 import ECONOMIC, SPREAD, YOC
from worksheet_local_sources_D127 import day, object_or_empty, synthetic_id
from worksheet_performance_policy_D184 import AFTER_RESERVES, BEFORE_RESERVES, equilibrium
from worksheet_project_calendar_D145 import offset


def route_cash_story(route, scale):
    events = []
    for index, row in enumerate(route["cash_per_usd_10"]["events"]):
        contribution, receipt = (amount(row[k]) for k in ("contribution", "receipt"))
        if None in (contribution, receipt) or min(contribution, receipt) < 0:
            raise ValidationError("annual route cash event is missing or invalid")
        if contribution:
            category = "initial_capital" if index == 0 else "additional_capital"
            events.append(dict(date=row["date"], category=category, amount=row["contribution"], kind="contribution"))
        if receipt:
            category = {"refinance": "net_refinance_distribution", "operation": "operating_distribution",
                        "sale": "net_sale_distribution"}[row["stage"]]
            events.append(dict(date=row["date"], category=category, amount=row["receipt"], kind="distribution"))
    contributions = sum((amount(row["amount"]) for row in events if row["kind"] == "contribution"), Fraction())
    distributions = sum((amount(row["amount"]) for row in events if row["kind"] == "distribution"), Fraction())
    cash = route["cash_per_usd_10"]
    if (not events or events[0]["category"] != "initial_capital" or amount(events[0]["amount"]) != 10
            or contributions != 10 + amount(cash["additional"]) or distributions != amount(cash["received"])
            or max(Fraction(), contributions - distributions) != amount(cash["unrecovered"])):
        raise ValidationError("annual route USD 10 ledger does not reconcile")
    return dict(reference_amount=rational(10), scale_factor=scale, events=events,
                total_contributions=rational(contributions), total_distributions=rational(distributions))


def route_annual_irr(cash, dates):
    flows = quarterly_cash(cash, dates)
    if flows is not None:
        values = [value for value in flows.values() if value]
        signs = [value > 0 for value in values]
        if signs and not signs[0] and signs[-1] and signs == sorted(signs):
            try:
                low, high = annual_irr_interval(list(flows.values()))
            except ValueError:
                pass
            else:
                return dict(state="checked_synthetic", period_ref=f"{dates[0]}/{dates[-1]}",
                            annual_enclosure=dict(lower=rational(low), upper=rational(high),
                                                  lower_closed=True, upper_closed=True), blockers=[])
    return verify_irr(cash, dates)


def route_metric_evidence(name, route, annual, evidence, refi_date, tdc, debt):
    records = []
    details = evidence.get("candidate_definitions", {})
    required = {"YoC": YOC, "spread": SPREAD, "breakeven_occupancy": ECONOMIC}
    units = {"YoC": "fraction", "spread": "bps", "breakeven_occupancy": "fraction"}
    noi_after = amount(annual.get("noi_after_reserves"))
    noi_before = sum((amount(r["value"]) for r in route["debt"]["quarterly_noi_source"].values()), Fraction())
    period_start = offset(day(refi_date).replace(day=1), 1)
    period = f"{period_start}/{offset(period_start,12)}"
    comparable = evidence.get("comparable_cap", {})
    cap_evidence = details.get("spread", {})
    cap, cap_basis = amount(cap_evidence.get("cap")), cap_evidence.get("cap_noi_basis")
    reserve, service = None if noi_after is None else noi_before - noi_after, amount(annual.get("scheduled_debt_service"))
    comparison_basis = (cap_basis in (BEFORE_RESERVES, AFTER_RESERVES) and comparable.get("period_ref") == period
                        and cap_evidence.get("comparison_noi_context", {}).get("matched", True))
    values = {
        "YoC": (None, "annual_reserve_adjusted_noi_unconfirmed") if noi_after is None else (noi_after/tdc, None),
        "spread": (None, "annual_comparable_cap_basis_or_window_unconfirmed"),
        "breakeven_occupancy": (None, "annual_operating_curve_does_not_reconcile_to_route_noi"),
    }
    if noi_after is not None and 0 < (cap or 0) <= 1 and comparison_basis and synthetic_id(comparable.get("source_ref")):
        spread_noi = noi_before if cap_basis == BEFORE_RESERVES else noi_after
        values["spread"] = ((spread_noi / tdc - cap) * 10_000, None)
    occupancy = details.get("breakeven_occupancy", {})
    yoc = details.get("YoC", {})
    if (occupancy.get("definition") == ECONOMIC and occupancy.get("period") == period
            and occupancy.get("value") is not None and service is not None and reserve is not None and reserve >= 0
            and occupancy.get("comparison_noi_context", {}).get("matched", True)
            and noi_before == amount(yoc.get("noi_before_reserve"))):
        inputs = {key: amount(value) for key, value in occupancy["inputs"].items()}
        values["breakeven_occupancy"] = (
            equilibrium(**(inputs | {"debt_service": service, "reserve": reserve}))["economic"], None)
    for metric, (value, reason) in values.items():
        records.append(dict(scenario_id=name, metric_id=metric,
                            metric_record=dict(value=None if value is None else rational(value), definition_ref=required[metric],
                                               unit=units[metric], period_ref=period, blockers=[reason] if reason else [])))
    cost = dict(tdc=rational(tdc), applied_equity=rational(tdc-debt), components={"loan_draw": rational(debt)}, blockers=[])
    support = dict(cost_basis=cost, candidate_definitions={
        "YoC": dict(noi_before_reserve=rational(noi_before), noi_after_reserve=annual.get("noi_after_reserves")),
        "spread": dict(cap=cap_evidence.get("cap"), cap_noi_basis=cap_basis),
    })
    return records, support


def project_annual_route(result, label):
    """Build criteria inputs from the selected alternate route without mutating the workbook."""
    views, comparisons, evidence, intervals, audited, gaps = {}, [], {}, {}, {}, []
    original_evidence = result["screening"]["metric_evidence_by_scenario"]
    for name in SCENARIOS:
        view = result["scenarios"][name]
        route = object_or_empty(result.get("calendar_checks", {}).get(name, {}).get(label))
        if route.get("state") != "calculated_synthetic" or "annual_post_refi_coc" not in route:
            reason = route.get("blocker") or "audited_annual_calendar_route_missing"
            views[name] = dict(cash_per_usd_10=None, blockers=[reason])
            audited[name] = dict(state="PENDING", blocker=reason)
            gaps.append(f"{name}:{reason}")
            continue
        dated = route["cash_by_period"]
        construction = [row for row in dated if row["stage"] == "construction"]
        refinance, = [row for row in dated if row["stage"] == "refinance"]
        annual = route["annual_post_refi_coc"]
        cash = route_cash_story(route, view["cash_per_usd_10"]["scale_factor"])
        calendar = view["project_calendar"] | dict(refinance_date=refinance["date"], sale_date=route["sale"]["date"],
            sale_source_ref=route["debt"]["forward_noi_source"]["source_ref"],
            equity_dates=list(dict.fromkeys(row["date"] for row in dated)))
        tdc = sum(amount(row["uses"]) for row in construction)
        debt = sum(amount(row["sources"]) - amount(row["contribution"]) for row in construction)
        if tdc <= 0 or debt < 0 or tdc - debt != sum(amount(row["contribution"]) for row in construction) - amount(construction[-1]["closing_free"]):
            raise ValidationError("annual construction costs do not reconcile to the route debt and equity")
        views[name] = dict(blockers=[], cash_per_usd_10=cash, project_calendar=calendar,
            development_costs=view["development_costs"], construction_financing=dict(cash_by_date=[
                dict(date=row["date"], equity_contribution=row["contribution"]) for row in construction]),
            construction_refinance=dict(date=refinance["date"], blockers=[], net_equity_distribution=refinance["distribution"],
                                        projected_cash_in_required=refinance["contribution"]),
            post_refinance_coc=dict(blockers=[annual["blocker"]] if annual["blocker"] else [], noi_basis=AFTER_RESERVES,
                window_start=annual.get("window_start"), window_end=annual.get("window_end"),
                period_noi=annual.get("noi_after_reserves"), scheduled_debt_service=annual.get("scheduled_debt_service"),
                equity_still_invested=annual.get("equity_remaining"), value=annual["value"]))
        rows, support = route_metric_evidence(name, route, annual, original_evidence[name], refinance["date"], tdc, debt)
        comparisons.extend(rows)
        for row in rows:
            gaps.extend(f"{name}:{row['metric_id']}:{reason}" for reason in row["metric_record"]["blockers"])
        evidence[name] = support
        intervals[name] = route_annual_irr(cash, calendar["equity_dates"])
        if not intervals[name].get("annual_enclosure"):
            gaps.extend(f"{name}:IRR:{reason}" for reason in intervals[name]["blockers"])
        audited[name] = dict(state="calculated_synthetic", cash_per_usd_10=route["cash_per_usd_10"],
                             cash_sha256=sha256(encode(route["cash_per_usd_10"])).hexdigest(),
                             sale_date=calendar["sale_date"], annual_post_refi_coc=annual)
    projected = dict(scenarios=views, screening=dict(comparisons=comparisons, metric_evidence_by_scenario=evidence,
                                                      irr_by_scenario=intervals))
    return projected, audited, gaps
