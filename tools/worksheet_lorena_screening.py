"""Compare a current synthetic worksheet's calculated metrics with D230."""

from datetime import date
from fractions import Fraction
from hashlib import sha256
import json

from check_worksheet_return_metrics_D167 import quarterly_cash
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.irr_interval_output import condition_relation
from miniuw_foundation.lorena_screening import BASES, CASE_SCHEMA, RLV, SCENARIOS, encode, prepare_configuration, rehearse
from miniuw_worksheet_v1 import TECHNICAL_SCHEMAS, _audit_package, read_current_revision, read_package
from worksheet_definition_screening_D193 import ECONOMIC, PRICE_BASIS, SPREAD, YOC
from worksheet_local_sources_D127 import synthetic_id
from worksheet_performance_policy_D184 import AFTER_RESERVES, BEFORE_RESERVES, price_screen
from worksheet_revision_D128 import audit_revision


def amount(value):
    return _fraction(value, 1300)


def point(value):
    value = rational(value)
    return dict(lower=value, upper=value, lower_closed=True, upper_closed=True)


def refinance_values(view, cash, calendar):
    closing = view.get("construction_refinance", {})
    funding = view.get("construction_financing", {})
    scale = amount(cash["scale_factor"])
    cutoff = calendar["stabilization_date"]
    by_date = [r for r in funding.get("cash_by_date", []) if r["date"] <= cutoff]
    pre_stab = sum((amount(r["equity_contribution"]) for r in by_date), Fraction())
    events = cash["events"]
    initial_funding = sum((amount(e["amount"]) for e in events if e["category"] in
                           ("initial_capital", "additional_capital") and e["date"] <= cutoff), Fraction())
    if not by_date or scale <= 0 or pre_stab <= 0 or pre_stab * scale != initial_funding:
        return {}, None
    values = {}
    if (closing.get("date") == calendar["refinance_date"] and calendar["refinance_date"] >= cutoff
            and closing.get("blockers") == []):
        for metric, field, category in (
            ("equity_recovered", "net_equity_distribution", "net_refinance_distribution"),
            ("equity_cash_in", "projected_cash_in_required", "refinance_cash_in"),
        ):
            observed = amount(closing.get(field))
            dated = sum((amount(e["amount"]) for e in events if e["category"] == category
                         and e["date"] == closing["date"]), Fraction())
            if observed is not None and observed >= 0 and observed * scale == dated:
                values[metric] = observed / pre_stab
    return values, pre_stab


def full_annual_coc(view, calendar):
    coc = view.get("post_refinance_coc", {})
    if (coc.get("blockers") != [] or coc.get("noi_basis") != AFTER_RESERVES
            or coc.get("window_start") != calendar["refinance_date"] or not coc.get("window_end")):
        return None
    start, end = (date.fromisoformat(coc[key]) for key in ("window_start", "window_end"))
    if ((end.year - start.year, end.month, end.day) != (1, start.month, start.day)
            or coc["window_end"] > calendar["sale_date"]):
        return None
    noi, service, equity = (amount(coc.get(key)) for key in ("period_noi", "scheduled_debt_service", "equity_still_invested"))
    if None in (noi, service, equity) or equity <= 0 or service < 0:
        return None
    value = (noi - service) / equity
    return value if value == amount(coc.get("value")) else None


def base_rlv(view, evidence, metrics, pre_stab, settings, configuration):
    """Use D230 thresholds and check the remaining Base criteria at the proposed limit."""
    if (settings.get("basis") != PRICE_BASIS or not synthetic_id(settings.get("source_ref"))
            or settings.get("binding_yields") not in (["YoC"], ["spread"])):
        return None, "rlv_price_grid_or_binding_yield_unconfirmed"
    yield_metric, = settings["binding_yields"]
    required = set(BASES) - {RLV}
    if not required <= metrics.keys():
        return None, "rlv_requires_all_base_metric_inputs"
    cash, calendar = view["cash_per_usd_10"], view["project_calendar"]
    closing, coc = view["construction_refinance"], view["post_refinance_coc"]
    scale = amount(cash["scale_factor"])
    development, cost = view["development_costs"], evidence["cost_basis"]
    details = evidence["candidate_definitions"]
    spread = details["spread"]
    tdc, debt, applied = (amount(value) for value in (cost["tdc"], cost["components"]["loan_draw"], cost["applied_equity"]))
    equity_left = amount(coc["equity_still_invested"])
    payout, cash_in = (amount(closing[key]) for key in ("net_equity_distribution", "projected_cash_in_required"))
    flows = quarterly_cash(cash, calendar["equity_dates"])
    price, asking, closing_rate = (amount(development.get(key)) for key in
                                  ("evaluated_purchase_price", "worksheet_asking", "closing_fraction"))
    if (None in (tdc, debt, applied, price, asking, closing_rate) or asking < 0 or flows is None
            or applied != pre_stab or equity_left != pre_stab - payout + cash_in
            or not synthetic_id(development.get("purchase_source_ref")) or not development.get("cell_sources", {}).get("C33")):
        return None, "rlv_equity_cash_timing_or_purchase_basis_unconfirmed"
    specs = {entry["metric_id"]: entry for entry in configuration["metrics"]}
    rules = {}
    for key, metric in (("yield_or_spread", yield_metric), ("annual_irr", "IRR"),
                        ("equity_multiple", "equity_multiple"), ("equity_to_tdc", "equity_TDC")):
        pc, fc = (specs[metric][name] for name in ("pass_base", "fail_base"))
        rules[key] = (pc["operator"], amount(pc["threshold"]), fc["operator"], amount(fc["threshold"]))
    noi_uw = amount(details["YoC"]["noi_after_reserve"])
    noi_before = amount(details["YoC"]["noi_before_reserve"])
    cap, cap_basis = amount(spread["cap"]), spread["cap_noi_basis"]
    source = dict(price=price, asking=asking, closing_rate=closing_rate, tdc=tdc, applied_equity=applied, debt=debt,
                  contributions=amount(cash["total_contributions"]) / scale,
                  distributions=amount(cash["total_distributions"]) / scale,
                  net_flows=[value / scale for value in flows.values()],
                  cap=cap if yield_metric == "spread" else None, cap_noi_basis=cap_basis,
                  noi_before=noi_before, noi_uw=noi_uw)
    try:
        answer = price_screen(source, rules, settings["grid"], require_both_neighbors=True, annual_hurdles=True)
    except (TypeError, KeyError, ValueError) as error:
        return None, str(error)
    if answer["pass_price"] is None or answer["pass_price"] <= 0:
        return None, answer["blocker"] or "nonpositive_rlv_premium_undefined"
    boundary = answer["pass_boundary"]
    delta = boundary["at"]["delta_tdc"]
    candidate_equity, candidate_remaining = pre_stab + delta, equity_left + delta
    if candidate_equity <= 0 or candidate_remaining <= 0:
        return None, "rlv_boundary_equity_outside_supported_domain"
    # The upper neighbor fails a monotone price criterion. The lower boundary
    # must also meet every applicable Base criterion outside that solver.
    candidate = {
        "YoC": noi_uw / (tdc + delta),
        "spread": ((noi_before if cap_basis == BEFORE_RESERVES else noi_uw) / (tdc + delta) - cap) * 10_000,
        "equity_recovered": payout / candidate_equity,
        "equity_cash_in": cash_in / candidate_equity,
        "breakeven_occupancy": metrics["breakeven_occupancy"],
        "post_refi_CoC": metrics["post_refi_CoC"] * equity_left / candidate_remaining,
    }
    for metric, value in candidate.items():
        criterion = specs[metric]["pass_base"]
        if condition_relation(point(value), criterion["threshold"], criterion["operator"]) != "every":
            return None, f"rlv_boundary_does_not_meet:{metric}"
    low = asking / boundary["above"]["price"] - 1
    high = asking / answer["pass_price"] - 1
    return dict(lower=rational(low), upper=rational(high), lower_closed=low == high, upper_closed=True), None


def calculated_case(result, case, configuration, configuration_raw):
    scenarios = result["scenarios"]
    screening = result["screening"]
    comparisons = {(r["scenario_id"], r["metric_id"]): r["metric_record"] for r in screening["comparisons"]}
    evidence = screening["metric_evidence_by_scenario"]
    metrics, scope, gaps = {}, {}, []
    proof = {}
    by_id = {spec["metric_id"]: spec for spec in configuration["metrics"]}
    for name in SCENARIOS:
        view = scenarios[name]
        cash, dates = view.get("cash_per_usd_10"), view.get("project_calendar", {})
        retained = amount(view.get("post_refinance_coc", {}).get("equity_still_invested"))
        scope[name] = dict(refinance_in_scope=True,
                           equity_remains_after_refi=None if retained is None or retained < 0 else retained > 0)
        metrics[name] = {}
        proof[name] = dict(window=None, equity_through_stabilization=None, cash_sha256=None)
        if cash is None or amount(cash.get("reference_amount")) != 10 or view.get("blockers"):
            gaps.append(f"{name}:verified_project_cash_unavailable")
            continue
        proof[name]["cash_sha256"] = sha256(encode(cash)).hexdigest()
        values, pre_stab = refinance_values(view, cash, dates)
        proof[name]["equity_through_stabilization"] = None if pre_stab is None else rational(pre_stab)
        cost = evidence[name].get("cost_basis", {})
        tdc = amount(cost.get("tdc"))
        if cost.get("blockers") == [] and tdc is not None and tdc > 0 and pre_stab is not None:
            values["equity_TDC"] = pre_stab / tdc
        for metric, definition, unit in (("YoC", YOC, "fraction"), ("spread", SPREAD, "bps"),
                                         ("breakeven_occupancy", ECONOMIC, "fraction")):
            row = comparisons[name, metric]
            if (row["definition_ref"] == definition and row["unit"] == unit and row["period_ref"]
                    and not row.get("blockers") and row["value"] is not None):
                values[metric] = amount(row["value"])
        coc = full_annual_coc(view, dates)
        if coc is not None:
            values["post_refi_CoC"] = coc
        elif retained is None or retained > 0:
            gaps.append(f"{name}:post_refi_CoC:verified_full_annual_window_required")
        investment = amount(cash["total_contributions"])
        window = f"{dates['purchase_date']}/{dates['sale_date']}"
        proof[name]["window"] = window
        irr = screening["irr_by_scenario"][name]
        if (synthetic_id(dates.get("sale_source_ref")) and cash["events"][0]["date"] == dates["purchase_date"]
                and cash["events"][-1]["date"] == dates["sale_date"] and investment > 0):
            values["equity_multiple"] = amount(cash["total_distributions"]) / investment
            if irr["period_ref"] == window and irr.get("annual_enclosure") and not irr.get("blockers"):
                values["IRR"] = irr["annual_enclosure"]
        if name == "Base":
            settings = case["rent_inputs"]["definition_screening"][name]["rlv"]
            rlv, issue = base_rlv(view, evidence[name], values, pre_stab, settings, configuration)
            if rlv is not None:
                values[RLV] = rlv
            else:
                gaps.append(f"{name}:RLV:{issue}")
        metrics[name] = {metric: dict(basis=BASES[metric], unit=by_id[metric]["unit"],
                                      value=value if isinstance(value, dict) else rational(value))
                         for metric, value in values.items()}
    observed = dict(schema=CASE_SCHEMA, deal_id=case["rent_inputs"]["deal_id"], criteria_revision=configuration["revision"],
                    criteria_sha256=sha256(configuration_raw).hexdigest(), irr_in_scope=True,
                    scope=scope, material_gaps=gaps, metric_values=metrics)
    return observed, proof


def rehearse_workbook(directory, current_revision, recipe, source, configuration_raw):
    revision = read_current_revision(current_revision, directory)
    files, result = _audit_package(directory)
    case = json.loads(files["case.json"])
    if (case["schema"] not in TECHNICAL_SCHEMAS or result["decision"] != "PENDING"
            or result["deployment_enabled"] or result["real_decisions_enabled"]):
        raise ValidationError("current synthetic technical worksheet required")
    audit = audit_revision(result, revision)
    if audit["vigencia"] != "VIGENTE":
        raise ValidationError("stored worksheet revision is not current")
    configuration = prepare_configuration(recipe, source)
    observed, proof = calculated_case(result, case, configuration, configuration_raw)
    verdict = rehearse(recipe, source, configuration_raw, encode(observed))
    if read_package(directory) != files or read_current_revision(current_revision, directory) != revision:
        raise ValidationError("worksheet or designated revision changed during comparison")
    return verdict | dict(observed_metrics=observed["metric_values"], source=proof,
                          source_results_sha256=sha256(files["results.json"]).hexdigest(),
                          pdf_sha256=result["pdf_sha256"], current_revision=audit["current_revision"])
