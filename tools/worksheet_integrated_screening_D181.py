"""Compare calculated metrics against the current synthetic workbook criteria."""
from collections import defaultdict
from datetime import date
from fractions import Fraction

from check_reference_package import PackageError
from check_scenario_pilot_D51 import METRICS as CASH_METRICS
from check_worksheet_refinance_D45 import render_page
from check_worksheet_return_metrics_D167 import KINDS, verify_irr
from functools import partial
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.irr_interval_output import ENGINE_SHA256, _compare, condition_relation
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.screening import AGGREGATION, SCHEMA, simulate_screening
from miniuw_worksheet_v1 import encoded
from plan_refinance_D108 import VALUE_PERIOD
from worksheet_formula_review_D173 import COC_BASIS
from worksheet_irr_D122 import IRR_METRIC, display_enclosure
from worksheet_local_sources_D127 import number, object_or_empty, synthetic_id
from worksheet_occupancy_D125 import DEFINITION as OCCUPANCY_DEFINITION
from worksheet_reference_metrics_D121 import REFERENCE_LABELS
from worksheet_sale_rate_grid_D84 import money
from worksheet_screening_pilot_D120 import METRIC_LABELS, RESULT_LABELS, criterion_records, metric_values


TDC_SCOPE = "project_uses_lease_up_origination_and_cash_interest_before_refinance"
amount = partial(_fraction, max_digits=1300)
CAP_BASIS = "synthetic_stabilized_comparable_cap"
METRICS = {
    **{key: (unit, kind, currency, f"SYNTHETIC-D51-{definition}")
       for key, (unit, kind, currency, definition) in CASH_METRICS.items()},
    "YoC": ("fraction", "scalar", None, "SYNTHETIC-D181-stabilized-forward-noi-over-reconciled-tdc"),
    "spread": ("bps", "scalar", None, "SYNTHETIC-D181-yoc-less-matched-comparable-cap"),
    "equity_TDC": ("fraction", "scalar", None, "SYNTHETIC-D181-applied-pre-refi-equity-over-reconciled-tdc"),
    "post_refi_CoC": ("fraction", "scalar", None, f"SYNTHETIC-D173-{COC_BASIS}"),
    "breakeven_occupancy": ("fraction", "scalar", None, OCCUPANCY_DEFINITION),
    "asking_relative_to_supported_price": ("multiple", "scalar", None, "SYNTHETIC-D181-house-rlv-definition-pending"),
    "IRR": IRR_METRIC,
}
LABELS = METRIC_LABELS | REFERENCE_LABELS | {"asking_relative_to_supported_price": "Precio pedido / RLV",
                                             "equity_recovered": "Equity recuperado en refi",
                                             "equity_cash_in": "Aporte en refi"}


def cost_basis(view, scope):
    calendar = view["project_calendar"]
    funding = view["construction_financing"]
    rows = funding["cash_by_date"]
    parts = {key: sum((amount(row[key]) for row in rows), Fraction())
             for key in ("project_uses", "origination_fee_paid", "interest_paid", "loan_draw")}
    tdc = parts["project_uses"] + parts["origination_fee_paid"] + parts["interest_paid"]
    applied = amount(funding["equity_funding_through_refinance"]) - amount(funding["free_cash_at_refinance"])
    budget = amount(view["construction_budget"]["total_development_cost"]) + amount(calendar["lease_up_funding"])
    evidence = dict(scope=scope, components={key: rational(value) for key, value in parts.items()},
                    tdc_source="/construction_financing/cash_by_date",
                    funding_source="/construction_financing/equity_funding_through_refinance",
                    cutoff=funding["payoff_date"])
    if (scope.get("basis") != TDC_SCOPE or not synthetic_id(scope.get("source_ref"))
            or funding["payoff_date"] != calendar["refinance_date"] or tdc <= 0 or applied < 0
            or parts["project_uses"] != budget or tdc != applied + parts["loan_draw"]):
        return evidence | dict(tdc=None, applied_equity=None, blockers=["complete_pre_refinance_tdc_unconfirmed"])
    return evidence | dict(tdc=rational(tdc), applied_equity=rational(applied), blockers=[])


def refinance_capital(view):
    cash = view["cash_per_usd_10"]
    valuation = view["valuation_and_sale"]
    closing = view["construction_refinance"]
    coc = view["post_refinance_coc"]
    scale = amount(cash["scale_factor"])
    capital = amount(coc.get("equity_still_invested"))
    property_value, debt = amount(valuation["refinance_value"]), amount(closing["gross_proceeds"])
    retained = None if property_value is None or debt is None else (property_value - debt) * scale
    return dict(date=closing["date"], capital_still_invested=None if capital is None else rational(capital * scale),
                retained_property_equity=None if retained is None else rational(retained),
                capital_pointer="/post_refinance_coc/equity_still_invested",
                valuation_pointer="/valuation_and_sale/refinance_value",
                new_debt_pointer="/construction_refinance/gross_proceeds")


def collect_metrics(name, view, supplied):
    records = {}

    def record(metric, period, value, pointer, *blockers):
        unit, kind, currency, definition = METRICS[metric]
        records[metric] = dict(period_ref=period, definition_ref=definition, unit=unit, quantity_kind=kind,
                               currency=currency, applicability="applicable", applicability_evidence_ref=None,
                               metric_id=metric, scenario_id=name, value=value,
                               source_pointer=None if pointer is None else f"/scenarios/{name}/{pointer}",
                               blockers=list(blockers))

    record("breakeven_occupancy", None, None, None, "SRC-02_house_economic_occupancy_unconfirmed")
    record("asking_relative_to_supported_price", None, None, None, "SRC-03_house_rlv_unconfirmed")
    cash = view.get("cash_per_usd_10")
    if cash is None:
        for metric in METRICS.keys() - records.keys():
            record(metric, None, None, None, "verified_scenario_cash_unavailable")
        return records, {}, dict(annual_enclosure=None, period_ref=None, blockers=["verified_scenario_cash_unavailable"])

    calendar = view["project_calendar"]
    for row in metric_values(name, view):
        metric = row["metric_id"]
        if metric == "equity_cash_in":
            source = view["construction_refinance"]["projected_cash_in_required"]
            value = row["value"] if amount(source) is not None and amount(source) == amount(row["value"]) else None
            blockers = [] if value is not None else ["refinance_cash_in_does_not_reconcile_to_closing"]
            record(metric, row["period_ref"], value, "construction_refinance/projected_cash_in_required", *blockers)
        else:
            record(metric, row["period_ref"], row["value"], "cash_per_usd_10")

    cost = cost_basis(view, object_or_empty(supplied.get("tdc_scope")))
    tdc = amount(cost["tdc"])
    equity = amount(cost["applied_equity"])
    record("equity_TDC", cost["cutoff"], None if tdc is None else rational(equity / tdc),
           "construction_financing/cash_by_date", *cost["blockers"])

    annual = view["noi_by_period"][VALUE_PERIOD]
    start = date.fromisoformat(calendar["noi_window_starts"][VALUE_PERIOD])
    period = f"{start}/{start.replace(year=start.year + 1)}"
    noi = amount(annual["noi"])
    yield_blockers = list(cost["blockers"])
    if (noi is None or start < date.fromisoformat(calendar["stabilization_date"])
            or annual.get("commercial", {}).get("recognized_months") != 12):
        yield_blockers.append("full_stabilized_annual_noi_unconfirmed")
    yoc = None if yield_blockers else noi / tdc
    record("YoC", period, None if yoc is None else rational(yoc), f"noi_by_period/{VALUE_PERIOD}/noi", *yield_blockers)
    cap = object_or_empty(supplied.get("reference_cap"))
    cap_value = number(cap.get("value"))
    spread_blockers = []
    if (cap.get("basis") != CAP_BASIS or cap.get("period_ref") != period
            or not synthetic_id(cap.get("source_ref")) or cap_value is None or not 0 < cap_value <= 1):
        spread_blockers.append("compatible_stabilized_comparable_cap_unconfirmed")
    if yoc is None:
        spread_blockers.append("yoc_unavailable")
    spread = None if spread_blockers else rational((yoc - cap_value) * 10_000)
    record("spread", period, spread, f"noi_by_period/{VALUE_PERIOD}/noi", *spread_blockers)

    coc = view["post_refinance_coc"]
    coc_period = (f"{coc['window_start']}/{coc['window_end']}" if "holding_horizon" in view else
                  f"{calendar['refinance_date']}/{calendar['sale_date']}")
    record("post_refi_CoC", coc_period, coc["value"], "post_refinance_coc/value", *coc["blockers"])

    if "holding_horizon" in view:
        from worksheet_holding_horizon_D266 import horizon_irr
        irr = horizon_irr(cash, calendar["equity_dates"])
    else:
        irr = verify_irr(cash, calendar["equity_dates"])
    record("IRR", irr.get("period_ref"), None, "cash_per_usd_10/events", *irr["blockers"])
    evidence = dict(cost_basis=cost, noi_pointer=f"/scenarios/{name}/noi_by_period/{VALUE_PERIOD}/noi",
                    comparable_cap_pointer=f"/rent_inputs/integrated_screening/{name}/reference_cap",
                    comparable_cap=cap, refinance_capital_per_usd_10=refinance_capital(view))
    return records, evidence, irr


def review_rules(raw, scenarios):
    """Keep the source indices and isolate unusable or ambiguous criteria."""
    if raw is None:
        return {}, {}, []
    if not isinstance(raw, list) or len(raw) > len(scenarios) * len(METRICS):
        return {}, {}, ["criterion_inventory_invalid"]

    accepted = {}
    issues = {}
    for index, entry in enumerate(raw):
        candidate = object_or_empty(entry)
        scenario, metric = candidate.get("scenario_id"), candidate.get("metric_id")
        if not isinstance(scenario, str) or not isinstance(metric, str) or scenario not in scenarios or metric not in METRICS:
            return {}, {}, [f"criterion_identity_invalid:/rules/{index}"]
        key = (scenario, metric)
        if key in accepted or key in issues:
            accepted.pop(key, None)
            issues[key] = "duplicate_scenario_metric_criterion"
            continue
        try:
            criterion, = criterion_records([candidate], METRICS)
            for field in ("definition_ref", "unit", "period_ref"):
                value = criterion[field]
                if value is not None and (not isinstance(value, str) or not value.strip()):
                    raise ValidationError("criterion metadata must be text")
            for condition in (criterion["pass_condition"], criterion["fail_condition"]):
                operator = condition["operator"]
                if operator is not None and not isinstance(operator, str):
                    raise ValidationError("criterion operator must be text")
                amount(condition["threshold"])
        except (PackageError, ValidationError):
            issues[key] = f"criterion_record_invalid:/rules/{index}"
        else:
            accepted[key] = (index, criterion)
    return accepted, issues, []


def compare_pass_only(metric, criterion, enclosure):
    """Evaluate an explicitly scoped Downside PASS without a FAIL threshold."""
    blockers = [f"{field}_missing_or_mismatch" for field in
                ("definition_ref", "unit", "period_ref", "quantity_kind", "currency", "applicability")
                if metric[field] != criterion[field] or (field != "currency" and metric[field] is None)]
    condition = criterion["pass_condition"]
    if condition["operator"] not in (">", ">=", "<", "<=") or condition["threshold"] is None:
        blockers.append("pass_condition_rule_missing_or_unsupported")
    if enclosure is None and metric["value"] is not None:
        enclosure = dict(lower=metric["value"], upper=metric["value"], lower_closed=True, upper_closed=True)
    if enclosure is None:
        blockers.append("metric_value_missing")
    if blockers:
        return "PENDING", {}, blockers
    relation = condition_relation(enclosure, condition["threshold"], condition["operator"])
    reasons = {"mixed": "IRR_enclosure_crosses_criterion_boundary",
               "none": "downside_pass_not_met_pending_review"}
    return ("PASS_CONDITION" if relation == "every" else "PENDING",
            {"pass_condition": relation}, [] if relation == "every" else [reasons[relation]])


def screen_integrated(case, views, blockers, *, definition_screening=False, criteria_review=None,
                      technical_acceptance=False, scalar_engine=None):
    inputs = object_or_empty(object_or_empty(case.get("rent_inputs")).get("integrated_screening"))
    collections = {name: collect_metrics(name, view, object_or_empty(inputs.get(name)))
                   for name, view in views.items()}
    revision = case.get("criteria_revision")
    current_rules = synthetic_id(revision) and not any(reason.startswith("B12:") for reason in blockers)
    workbook_rows = {}
    rule_path = "/rules" if criteria_review is None else "/screening/criteria_workbook/rules"
    raw_rules = case.get("rules")
    if criteria_review is not None:
        workbook_rows = {(row["scenario_id"], row["metric_id"]): row for row in criteria_review["rows"]}
        raw_rules = criteria_review["rules"]
        blockers = [*blockers, *criteria_review["blockers"]]
        current_rules = current_rules and not criteria_review["blockers"]
    rules, rule_issues, inventory_issues = review_rules(raw_rules if current_rules else None, views)
    if definition_screening:
        from worksheet_definition_screening_D193 import RLV, extend, land_band_rules
        source = object_or_empty(object_or_empty(case.get("rent_inputs")).get("definition_screening"))
        noi_contract = object_or_empty(case["rent_inputs"].get("criterion_noi_contexts"))
        for name, (records, evidence, irr) in collections.items():
            criteria = {key: entry for (scenario, key), entry in rules.items() if scenario == name}
            updated, trace = extend(views[name], object_or_empty(source.get(name)), object_or_empty(inputs.get(name)),
                                    criteria, records, evidence, irr, noi_contexts=(
                                        object_or_empty(noi_contract.get(name)) if technical_acceptance else None))
            if criteria_review is not None:
                rlv_trace = trace["candidate_definitions"][RLV]
                locators = rlv_trace.get("criterion_locators", {})
                for key, locator in locators.items():
                    locators[key] = f"{rule_path}/{locator.rsplit('/', 1)[-1]}"
            collections[name] = (updated, trace, irr)
    records = {(name, metric): data[0][metric] for name, data in collections.items() for metric in METRICS}
    if definition_screening:
        for name, (_, trace, _) in collections.items():
            key = (name, RLV)
            if key not in rules:
                continue
            _, criterion = rules[key]
            boundary = trace["candidate_definitions"][RLV].get("fail_boundary_multiple")
            if (boundary is not None and criteria_review is not None and name in criteria_review["derived_rlv"]):
                criterion["fail_condition"] = land_band_rules(boundary)["FAIL"]
            actual = {"PASS": criterion["pass_condition"], "FAIL": criterion["fail_condition"]}
            expected = land_band_rules(boundary)
            if workbook_rows.get(key, {}).get("pass_only_policy"):
                expected["FAIL"] = dict(operator=None, threshold=None)
            if boundary is not None and actual != expected:
                # The price band is defined by the joint price search. An
                # inconsistent manual ratio threshold must not override it.
                rules.pop(key)
                rule_issues[key] = "SRC-03_ratio_rule_does_not_match_computed_price_band"
    values = [{key: value for key, value in row.items() if key not in {"source_pointer", "blockers"}}
              for (_, metric), row in records.items() if metric != "IRR"]
    rule_inventory = [criterion for _, criterion in rules.values()]
    aggregation = case.get("aggregation_rule")
    component = "D193" if definition_screening else "D181"
    case_id = f"SYNTHETIC-{component}"
    calculate_screening = simulate_screening if scalar_engine is None else scalar_engine
    scalar_result = calculate_screening(encoded(dict(
        schema=SCHEMA, context=dict(deal_id=f"{case_id}-screening", scenario_id="SYNTHETIC-pair",
                                    run_id=case_id, definition_set_revision=f"{case_id}-integrated"),
        case_id=case_id, criteria_revision=revision if synthetic_id(revision) else "SYNTHETIC-unconfirmed",
        criteria_status="synthetic_fixture_only", required_metrics=[m for m in METRICS if m != "IRR"],
        required_scenarios=list(views), metric_values=values, criteria=[row for row in rule_inventory if row["metric_id"] != "IRR"],
        aggregation_rule=aggregation if aggregation == AGGREGATION else None, hypothetical_band_policy=None,
    ))).payload
    comparisons = scalar_result["comparisons"]
    for name, (_, _, irr) in collections.items():
        index, criterion = rules.get((name, "IRR"), (None, None))
        source = None if index is None else f"{rule_path}/{index}"
        state, relations, reasons = ("PENDING", {}, ["criterion_record_missing"]) if criterion is None else _compare(
            irr["annual_enclosure"], criterion | dict(source_ref=source), irr.get("period_ref"))
        comparisons.append(dict(metric_id="IRR", scenario_id=name, state=state, blockers=reasons,
                                criterion_record=criterion, metric_record=records[name, "IRR"] |
                                dict(annual_enclosure=irr["annual_enclosure"]), condition_relations=relations))

    all_blockers = set(blockers) | set(inventory_issues)
    if aggregation != AGGREGATION:
        all_blockers.add("aggregation_rule_missing_or_unconfirmed")
    review = []
    for row in comparisons:
        key = (row["scenario_id"], row["metric_id"])
        metric = records[key]
        index, _ = rules.get(key, (None, None))
        row["criterion_locator"] = None if index is None else f"{rule_path}/{index}"
        row["metric_locator"] = metric["source_pointer"]
        issues = [rule_issues[key]] if key in rule_issues else []
        if key in workbook_rows:
            workbook_row = workbook_rows[key]
            row["criteria_workbook_cells"] = workbook_row["conditions"]
            issues.extend(workbook_row["blockers"])
            if index is not None and "pass_only_policy" in workbook_row:
                row["pass_only_policy"] = workbook_row["pass_only_policy"]
                enclosure = row["metric_record"].get("annual_enclosure")
                row["state"], row["condition_relations"], row["blockers"] = compare_pass_only(
                    metric, rules[key][1], enclosure)
        row["blockers"] = sorted(set(row["blockers"] + metric["blockers"] + issues))
        all_blockers.update(f"{key[0]}:{key[1]}:{reason}" for reason in row["blockers"])
        if row["state"] == "BAND":
            all_blockers.add("intermediate_band_pending_professional_review")
            review.append({key: row[key] for key in ("metric_id", "scenario_id", "metric_locator", "criterion_locator")})
    simulation = "PENDING" if all_blockers else ("FAIL" if any(
        row["state"] == "FAIL_CONDITION" for row in comparisons) else "PASS")
    result = scalar_result | dict(component=component, required_metrics=list(METRICS), comparisons=comparisons,
                                input_case_rule_source="/rules", input_case_sha256=sha(encoded(case)),
                                current_criteria_confirmed=current_rules, interval_engine_sha256=ENGINE_SHA256,
                                metric_evidence_by_scenario={name: row[1] for name, row in collections.items()},
                                irr_by_scenario={name: row[2] for name, row in collections.items()},
                                professional_review_needed_for_band=bool(review), pending_review_metrics=review,
                                simulation_result=simulation, simulation_blockers=sorted(all_blockers))
    if criteria_review is not None:
        compiled = [dict(rule) for rule in raw_rules]
        for index, criterion in rules.values():
            compiled[index].update(pass_condition=criterion["pass_condition"], fail_condition=criterion["fail_condition"])
        result.update(input_case_rule_source="Criterios_Lorena.xlsx",
                      criteria_workbook=criteria_review | {"rules": compiled})
    return result


def percent(value):
    return money(rational(amount(value) * 100)) + "%"


def display_metric(row, cash, *, delivery_report=False):
    metric = row["metric_id"]
    if delivery_report and metric == "asking_relative_to_supported_price":
        return "PENDING"
    record = row["metric_record"] or {}
    if metric == "IRR":
        value = display_enclosure(record.get("annual_enclosure"))
    elif record.get("value") is None:
        value = "—"
    elif record["unit"] == "fraction":
        value = percent(record["value"])
    elif record["unit"] == "USD":
        value = "USD " + money(rational(amount(record["value"]) * amount(cash["scale_factor"])))
    else:
        value = money(record["value"]) + {"multiple": "×", "bps": " pb"}[record["unit"]]
    if delivery_report:
        return "PENDING" if value == "—" else value
    return f"{value} [{RESULT_LABELS[row['state']]}]"


def render_integrated(views, screening, *, technical_acceptance=False, florida_tax=False, critical_evidence=False,
                      delivery_report=False):
    verdict = "Decisión real PENDING | Retorno personal LP/GP PENDING"
    if not delivery_report:
        verdict = f"Dictamen simulado {screening['simulation_result']} | {verdict}"
    lines = [(verdict, True),
             ("Equity agregado del proyecto antes de impuestos personales. Importes en USD por USD 10 iniciales.", False)]
    dated = defaultdict(dict)
    for name, view in views.items():
        cash = view.get("cash_per_usd_10")
        if cash is None:
            capacity = object_or_empty(view.get("capacity"))
            reason = ("préstamo por encima de la capacidad o términos bancarios pendientes"
                      if capacity.get("capacity_state") == "blocked" else "entradas o fuentes sin confirmar")
            if florida_tax and any(blocker.startswith("M2:") for blocker in view["blockers"]):
                reason = "evidencia fiscal M2 faltante o incompatible"
            if critical_evidence and any(blocker.startswith("B12:D219:") for blocker in view["blockers"]):
                reason = "respaldo documental D219 pendiente"
            lines.append((f"{name} | Caja PENDING: {reason}", True))
            continue
        events = cash["events"]
        for event in events:
            key = (event["date"], event["category"])
            dated[key][name] = dated[key].get(name, Fraction()) + amount(event["amount"])
        closing = view["construction_refinance"]
        cash_in = amount(closing["projected_cash_in_required"])
        if cash_in is not None:
            dated[closing["date"], "refinance_cash_in"][name] = cash_in * amount(cash["scale_factor"])
        contributed, received = (amount(cash[key]) for key in ("total_contributions", "total_distributions"))
        sale = sum((amount(e["amount"]) for e in events if e["category"] == "net_sale_distribution"), Fraction())
        dependency = "—" if received == 0 else percent(rational(sale / received))
        sale_needed = max(Fraction(), contributed - (received - sale))
        snapshot = screening["metric_evidence_by_scenario"][name]["refinance_capital_per_usd_10"]
        capital, retained = (money(snapshot[key]) if snapshot[key] is not None else "PENDING"
                             for key in ("capital_still_invested", "retained_property_equity"))
        lines.extend([
            (f"{name} | Aporte extra {money(rational(contributed - 10))} | Total aportado {money(cash['total_contributions'])}"
             f" | Cobro total {money(cash['total_distributions'])}", True),
            (f"Resultado neto {money(cash['net_cash_profit'])} | Sin recuperar {money(cash['unrecovered_after_sale'])}"
             f" | {dependency} de los cobros vienen de la venta", False),
            (f"Cobro neto de venta mínimo para recuperar lo aportado: {money(rational(sale_needed))} a valor nominal", False),
            (f"Al {snapshot['date']} | Capital remanente {capital} | Valor retenido en el inmueble {retained} (sin cobro)", False),
        ])
    if dated:
        lines.append(("Calendario de aportes y cobros  ·  Base / Downside", True))
        for (day, category), by_name in sorted(dated.items(), key=lambda item: (item[0][0], list(KINDS).index(item[0][1]))):
            cells = " / ".join(money(rational(by_name[name])) if name in by_name else "—" for name in views)
            lines.append((f"{day}  {KINDS[category]}  ·  {cells}", False))

    metrics_label = "Métricas calculadas" if delivery_report else "Métricas del dictamen"
    lines.append((f"{metrics_label}  ·  Base / Downside  ·  CoC del tramo posrefi, sin anualizar", True))
    by_key = {(row["metric_id"], row["scenario_id"]): row for row in screening["comparisons"]}
    for metric in METRICS:
        cells = " / ".join(display_metric(by_key[metric, name], view["cash_per_usd_10"], delivery_report=delivery_report)
                           for name, view in views.items())
        lines.append((f"{LABELS[metric]}  ·  {cells}", False))
    definition_screening = any("candidate_definitions" in item
                               for item in screening["metric_evidence_by_scenario"].values())
    if delivery_report:
        lines.append(("Criterios de inversión reales PENDING. Los umbrales de ensayo están en el expediente.", False))
    elif definition_screening:
        def land_boundaries(name):
            details = screening["metric_evidence_by_scenario"][name]["candidate_definitions"]
            price = details["asking_relative_to_supported_price"].get("calculation", {})
            values = (price.get("pass_price"), price.get("before_fail"))
            return " / ".join("PENDING" if value is None else str(value) for value in values)

        lines.append((f"RLV / último antes de FAIL (USD proyecto) | Base {land_boundaries('Base')} | Downside {land_boundaries('Downside')}", True))
        if any(row["state"] in {"PENDING", "CONFLICT", "BAND"} and row["metric_id"] in
               {"breakeven_occupancy", "asking_relative_to_supported_price"} for row in screening["comparisons"]):
            lines.append(("SRC-02/SRC-03: revisar bases, datos, criterios y límites del expediente.", False))
        lines.append(("Ocupación y RLV de ensayo. Aprobación de definiciones reales PENDING.", False))
    else:
        lines.append(("Pendientes de definición: ocupación económica (SRC-02) y RLV de la casa (SRC-03).", False))
    if not screening["current_criteria_confirmed"]:
        lines.append(("PENDING por vigencia: revisar la revisión de fuentes y criterios del expediente.", True))
    elif any(row["state"] in {"PENDING", "CONFLICT"} and row["metric_id"] not in
             {"breakeven_occupancy", "asking_relative_to_supported_price"} for row in screening["comparisons"]):
        lines.append(("Hay datos o criterios adicionales PENDING. El expediente detalla cada métrica y el motivo.", True))
    if not delivery_report and screening["professional_review_needed_for_band"]:
        lines.append(("PENDING por banda: una comparación requiere revisión profesional.", True))
    lines.append(("— indica que no hay evento para esa fecha o falta un valor. 0,00 indica un cero documentado o redondeado.", False))
    label = "D193 | Base y Downside" if definition_screening else "D181 | Base y Downside"
    if technical_acceptance:
        label = "D200 | Base y Downside"
    if florida_tax:
        label = "D203 | Base y Downside"
    if critical_evidence:
        label = "D220 | Base y Downside"
    subtitle = "Simulación sintética | Aportes, cobros, riesgos y métricas" if delivery_report else (
        "Piloto sintético | Aportes, cobros, riesgos y métricas del dictamen")
    return render_page(label, lines, 9 if definition_screening else 10,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       subtitle)
