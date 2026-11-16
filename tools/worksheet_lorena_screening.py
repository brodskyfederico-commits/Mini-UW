"""Compare a current synthetic worksheet's calculated metrics with D230."""

from datetime import date
from fractions import Fraction
from hashlib import sha256
import json

from check_worksheet_return_metrics_D167 import quarterly_cash
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.lorena_screening import BASES, CASE_SCHEMA, RLV, SCENARIOS, encode, prepare_configuration, rehearse
from miniuw_worksheet_v1 import (TECHNICAL_SCHEMAS, _audit_package, publish_current_pdf, read_current_revision,
                                read_package, require_delivery_evidence, require_pdf_destination)
from worksheet_definition_screening_D193 import ECONOMIC, PRICE_BASIS, SPREAD, YOC
from worksheet_annual_coc import equity_at_refinance, verify_annual_coc
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_performance_policy_D184 import AFTER_RESERVES, BEFORE_RESERVES, JOINT_MAXIMUM, JOINT_MINIMUM, price_screen
from worksheet_revision_D128 import audit_revision


def amount(value):
    return _fraction(value, 1300)


def stabilized_equity(view, cash, calendar):
    funding = view.get("construction_financing", {})
    scale = amount(cash["scale_factor"])
    cutoff = calendar["stabilization_date"]
    by_date = [r for r in funding.get("cash_by_date", []) if r["date"] <= cutoff]
    pre_stab = sum((amount(r["equity_contribution"]) for r in by_date), Fraction())
    events = cash["events"]
    initial_funding = sum((amount(e["amount"]) for e in events if e["category"] in
                           ("initial_capital", "additional_capital") and e["date"] <= cutoff), Fraction())
    if not by_date or scale <= 0 or pre_stab <= 0 or pre_stab * scale != initial_funding:
        return None
    return pre_stab


def refinance_values(view, cash, calendar):
    closing = view.get("construction_refinance", {})
    pre_stab = stabilized_equity(view, cash, calendar)
    if pre_stab is None:
        return {}, None
    scale = amount(cash["scale_factor"])
    cutoff = calendar["stabilization_date"]
    values = {}
    if (closing.get("date") == calendar["refinance_date"] and calendar["refinance_date"] >= cutoff
            and closing.get("blockers") == []):
        for metric, field, category in (
            ("equity_recovered", "net_equity_distribution", "net_refinance_distribution"),
            ("equity_cash_in", "projected_cash_in_required", "refinance_cash_in"),
        ):
            observed = amount(closing.get(field))
            dated = sum((amount(e["amount"]) for e in cash["events"] if e["category"] == category
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


def base_rlv(view, evidence, metrics, pre_stab, equity_left, settings, configuration):
    """Find the largest grid price that satisfies all non-RLV Base criteria."""
    def pending(reason):
        return None, dict(state="PENDING", blocker=reason)

    if (settings.get("basis") != PRICE_BASIS or not synthetic_id(settings.get("source_ref"))
            or settings.get("binding_yields") not in (["YoC"], ["spread"])):
        return pending("rlv_price_grid_or_binding_yield_unconfirmed")
    required = set(BASES) - {RLV}
    if not required <= metrics.keys():
        return pending("rlv_requires_all_base_metric_inputs")
    cash, calendar = view["cash_per_usd_10"], view["project_calendar"]
    closing = view["construction_refinance"]
    scale = amount(cash["scale_factor"])
    development, cost = view["development_costs"], evidence["cost_basis"]
    details = evidence["candidate_definitions"]
    spread = details["spread"]
    tdc, debt, applied = (amount(value) for value in (cost["tdc"], cost["components"]["loan_draw"], cost["applied_equity"]))
    payout, cash_in = (amount(closing[key]) for key in ("net_equity_distribution", "projected_cash_in_required"))
    flows = quarterly_cash(cash, calendar["equity_dates"])
    price, asking, closing_rate = (amount(development.get(key)) for key in
                                  ("evaluated_purchase_price", "worksheet_asking", "closing_fraction"))
    if (None in (tdc, debt, applied, price, asking, closing_rate) or asking < 0 or flows is None
            or equity_left != equity_at_refinance(view, cash, calendar["refinance_date"])
            or not synthetic_id(development.get("purchase_source_ref")) or not development.get("cell_sources", {}).get("C33")):
        return pending("rlv_equity_cash_timing_or_purchase_basis_unconfirmed")
    specs = {entry["metric_id"]: entry for entry in configuration["metrics"]}
    rules = {}
    metric_names = {metric: metric for metric in (*JOINT_MINIMUM, *JOINT_MAXIMUM, "equity_multiple")}
    metric_names.update(annual_irr="IRR", equity_to_tdc="equity_TDC")
    for key, metric in metric_names.items():
        pc, fc = (specs[metric][name] for name in ("pass_base", "fail_base"))
        rules[key] = (pc["operator"], amount(pc["threshold"]), fc["operator"], amount(fc["threshold"]))
    noi_uw = amount(details["YoC"]["noi_after_reserve"])
    noi_before = amount(details["YoC"]["noi_before_reserve"])
    cap, cap_basis = amount(spread["cap"]), spread["cap_noi_basis"]
    if None in (noi_uw, noi_before, cap) or cap_basis not in (AFTER_RESERVES, BEFORE_RESERVES):
        return pending("rlv_compatible_yield_and_spread_inputs_required")
    source = dict(price=price, asking=asking, closing_rate=closing_rate, tdc=tdc, applied_equity=applied, debt=debt,
                  contributions=amount(cash["total_contributions"]) / scale,
                  distributions=amount(cash["total_distributions"]) / scale,
                  net_flows=[value / scale for value in flows.values()], cap=None, cap_noi_basis=None, noi_uw=noi_uw)
    joint = dict(equity_remaining=equity_left, equity_through_stabilization=pre_stab,
                 spread_noi=noi_before if cap_basis == BEFORE_RESERVES else noi_uw,
                 comparable_cap=cap, refi_payout=payout, refi_cash_in=cash_in,
                 breakeven_occupancy=metrics["breakeven_occupancy"], available_annual_cash=metrics["post_refi_CoC"] * equity_left)
    try:
        answer = price_screen(source, rules, settings["grid"], require_both_neighbors=True, annual_hurdles=True, joint_base=joint)
    except (TypeError, KeyError, ValueError) as error:
        return pending(str(error))
    boundary = answer.get("pass_boundary")
    lower = answer["pass_price"]
    if lower is None:
        return pending(boundary["state"] if boundary else answer["blocker"])
    upper = boundary["above"]["price"]
    stopped = sorted(metric_names[key] for key, state in boundary["above"]["comparisons"].items() if state != "PASS")
    proof = dict(state="bounded_synthetic", price_lower=lower, price_upper_exclusive=upper,
                 binding_metrics=stopped, negative_limit=upper <= 0,
                 blocker="nonpositive_rlv_premium_undefined" if lower <= 0 else None)
    if lower <= 0:
        return None, proof
    low, high = asking / upper - 1, asking / lower - 1
    return dict(lower=rational(low), upper=rational(high), lower_closed=low == high, upper_closed=True), proof


def calculated_case(result, case, configuration, configuration_raw):
    scenarios = result["scenarios"]
    screening = result["screening"]
    comparisons = {(r["scenario_id"], r["metric_id"]): r["metric_record"] for r in screening["comparisons"]}
    evidence = screening["metric_evidence_by_scenario"]
    metrics, scope, gaps = {}, {}, []
    proof = {}
    by_id = {spec["metric_id"]: spec for spec in configuration["metrics"]}
    annual_inputs = case["rent_inputs"].get("annual_post_refi_coc")
    for name in SCENARIOS:
        view = scenarios[name]
        cash, dates = view.get("cash_per_usd_10"), view.get("project_calendar", {})
        refi = view.get("refinance_in_scope", True)
        scope[name] = dict(refinance_in_scope=refi, equity_remains_after_refi=None)
        metrics[name] = {}
        proof[name] = dict(window=None, equity_through_stabilization=None, cash_sha256=None)
        if cash is None or amount(cash.get("reference_amount")) != 10 or view.get("blockers"):
            gaps.append(f"{name}:verified_project_cash_unavailable")
            continue
        proof[name]["cash_sha256"] = sha256(encode(cash)).hexdigest()
        values, pre_stab = refinance_values(view, cash, dates) if refi else ({}, stabilized_equity(view, cash, dates))
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
        retained = coc = None
        if not refi:
            coc_blocker = None
        elif annual_inputs is None:
            retained = amount(view.get("post_refinance_coc", {}).get("equity_still_invested"))
            coc = full_annual_coc(view, dates)
            coc_blocker = "verified_full_annual_window_required"
        else:
            annual_proof = verify_annual_coc(view, object_or_empty(annual_inputs).get(name))
            proof[name]["annual_post_refi_coc"] = annual_proof
            retained = amount(annual_proof.get("equity_remaining"))
            coc = amount(annual_proof["value"])
            coc_blocker = annual_proof["blocker"]
        if retained is not None and retained >= 0:
            scope[name]["equity_remains_after_refi"] = retained > 0
        if coc is not None:
            values["post_refi_CoC"] = coc
        elif refi and (retained is None or retained > 0):
            gaps.append(f"{name}:post_refi_CoC:{coc_blocker}")
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
            if refi:
                rlv, search = base_rlv(view, evidence[name], values, pre_stab, retained, settings, configuration)
            else:
                rlv, search = None, dict(state="PENDING", blocker="rlv_criteria_without_refinance_unconfirmed")
            proof[name]["rlv_price_search"] = search
            if rlv is not None:
                values[RLV] = rlv
            else:
                gaps.append(f"{name}:RLV:{search['blocker']}")
        metrics[name] = {metric: dict(basis=BASES[metric], unit=by_id[metric]["unit"],
                                      value=value if isinstance(value, dict) else rational(value))
                         for metric, value in values.items()}
    observed = dict(schema=CASE_SCHEMA, deal_id=case["rent_inputs"]["deal_id"], criteria_revision=configuration["revision"],
                    criteria_sha256=sha256(configuration_raw).hexdigest(), irr_in_scope=True,
                    scope=scope, material_gaps=gaps, metric_values=metrics)
    return observed, proof


def rehearse_workbook(directory, current_revision, recipe, source, configuration_raw, *, route=None, pdf_output=None):
    if pdf_output is not None:
        if route is None:
            raise ValidationError("Seleccioná una ruta anual para exportar su PDF")
        require_pdf_destination(directory, pdf_output, current_revision)
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
    annual_summary = {}
    if route is None:
        observed, proof = calculated_case(result, case, configuration, configuration_raw)
    else:
        from worksheet_lorena_annual_route import project_annual_route

        projected, routes, gaps = project_annual_route(result, route)
        # The selected calendar route already reconciled its own annual proof.
        # A CoC attachment for the primary route has a different cash ledger.
        inputs = {key: value for key, value in case["rent_inputs"].items() if key != "annual_post_refi_coc"}
        observed, proof = calculated_case(projected, case | {"rent_inputs": inputs}, configuration, configuration_raw)
        observed["material_gaps"].extend(gaps)
        annual_summary = dict(annual_calendar_route=dict(label=route, scenarios=routes))
    verdict = rehearse(recipe, source, configuration_raw, encode(observed))
    if read_package(directory) != files or read_current_revision(current_revision, directory) != revision:
        raise ValidationError("worksheet or designated revision changed during comparison")
    receipt = verdict | dict(observed_metrics=observed["metric_values"], source=proof,
                             source_results_sha256=sha256(files["results.json"]).hexdigest(),
                             pdf_sha256=result["pdf_sha256"], current_revision=audit["current_revision"]) | annual_summary
    if pdf_output is not None:
        from worksheet_annual_route_report import render_annual_route

        require_delivery_evidence(result)
        pdf = render_annual_route(receipt)
        publish_current_pdf(directory, files, current_revision, revision, pdf_output, pdf)
        receipt["annual_pdf"] = dict(page_count=1, sha256=sha256(pdf).hexdigest(),
                                    revision_sha256=sha256(revision).hexdigest())
    return receipt
