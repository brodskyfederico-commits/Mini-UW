"""Run the synthetic pilot from both workbook sources through USD 10 cash and screening."""
from fractions import Fraction
import json
import re

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_scenario_pilot_D51 import METRICS, MISSING
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.expense_cash_detail import _exact
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.screening import SCHEMA, simulate_screening
from miniuw_worksheet_v1 import (WORKBOOK_CAPACITY_SCHEMA, WORKBOOK_CURRENT_CHAIN_SCHEMAS, WORKBOOK_FUNDING_PILOT_SCHEMAS,
                                 WORKBOOK_LOCAL_CHAIN_SCHEMAS, WORKBOOK_MIXED_CHAIN_SCHEMA, WORKBOOK_OPERATING_PILOT_SCHEMAS,
                                 WORKBOOK_OVERLAY_CHAIN_SCHEMA, WORKBOOK_PLAN_CHAIN_SCHEMA, WORKBOOK_PLAN_SET_CHAIN_SCHEMA,
                                 WORKBOOK_RETURN_PILOT_SCHEMAS,
                                 WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA, WORKBOOK_SCAN_CHAIN_SCHEMA, encoded)
from worksheet_intake_case_D117 import SOURCE_FIXTURE, build_intake_case
from worksheet_plan_refinance_D109 import LABELS, SCENARIOS
from worksheet_sale_rate_grid_D84 import money


PROFILE = "synthetic_workbook_screening_pilot"
CASE_ID = "SYNTHETIC-D120-workbook-pilot"
METRIC_LABELS = {"equity_multiple": "Múltiplo", "equity_recovered": "Equity recuperado",
                 "equity_cash_in": "Aporte al refinanciar"}
RESULT_LABELS = {"PASS_CONDITION": "PASS", "FAIL_CONDITION": "FAIL", "BAND": "PENDING",
                 "PENDING": "PENDING", "CONFLICT": "PENDING"}
SOURCE_LABELS = {"workbook_missing": "Falta la planilla del escenario.",
                 "workbook_hash_missing": "Falta vincular la planilla al caso.",
                 "workbook_hash_mismatch": "La planilla no coincide con la fuente declarada."}


def metric_values(name, scenario):
    cash = scenario.get("cash_per_usd_10")
    if cash is None:
        return []
    events = cash["events"]
    categories = ("net_refinance_distribution", "refinance_cash_in")
    refi_dates = {event["date"] for event in events if event["category"] in categories}
    require(len(refi_dates) == 1 and amount(cash["reference_amount"]) == 10
            and amount(cash["total_contributions"]) > 0 and amount(cash["scale_factor"]) > 0,
            "A verified refinance date and initial USD 10 basis are required")
    refi_date, = refi_dates
    by_category = {category: sum((amount(event["amount"]) for event in events if event["category"] == category),
                                 Fraction()) for category in categories}
    values = {
        "equity_multiple": amount(cash["total_distributions"]) / amount(cash["total_contributions"]),
        "equity_recovered": by_category["net_refinance_distribution"] / 10,
        "equity_cash_in": by_category["refinance_cash_in"] / amount(cash["scale_factor"]),
    }
    window = f"{events[0]['date']}/{events[-1]['date']}"
    return [
        dict(metric_id=metric, scenario_id=name, definition_ref=f"SYNTHETIC-D51-{definition}",
             unit=unit, quantity_kind=kind, currency=currency,
             period_ref=window if metric == "equity_multiple" else refi_date,
             applicability="applicable", applicability_evidence_ref=None, value=rational(values[metric]))
        for metric, (unit, kind, currency, definition) in METRICS.items()
    ]


def criterion_records(rules, metrics):
    require(isinstance(rules, list) and len(rules) <= len(SCENARIOS) * len(metrics),
            "A bounded explicit criterion inventory is required")
    records = []
    fields = {"scenario_id", "metric_id", "definition_ref", "unit", "period_ref", "pass_condition", "fail_condition"}
    for rule in rules:
        require(isinstance(rule, dict) and {"scenario_id", "metric_id"} <= rule.keys() <= fields
                and rule["scenario_id"] in SCENARIOS and rule["metric_id"] in metrics,
                "Expected a supported scenario and investment metric")
        _, kind, currency, _ = metrics[rule["metric_id"]]
        record = {key: rule.get(key) for key in fields - {"pass_condition", "fail_condition"}}
        for name in ("pass_condition", "fail_condition"):
            condition = rule.get(name)
            require(condition is None or isinstance(condition, dict) and condition.keys() <= MISSING.keys(),
                    "Use explicit operator and threshold fields")
            record[name] = MISSING | (condition or {})
        records.append(record | dict(quantity_kind=kind, currency=currency,
                                     applicability="applicable", applicability_evidence_ref=None))
    return records


def run_screening(case, scenarios, context, *, extended=False, interval_irr=False, yield_metrics=False, case_sha256=None):
    revision = case.get("criteria_revision")
    require(revision is None or isinstance(revision, str) and re.fullmatch(r"SYNTHETIC-[A-Za-z0-9_-]{1,80}", revision),
            "Use an explicit synthetic criteria revision")
    metrics = METRICS
    values = [row for name in SCENARIOS for row in metric_values(name, scenarios[name])]
    provenance = {}
    computed_yield = {}
    computed_equity = None
    computed_occupancy = None
    computed_returns = None
    schema = case.get("schema")
    if extended:
        from worksheet_reference_metrics_D121 import REFERENCE_METRICS, reference_records
        catalog = {key: value for key, value in REFERENCE_METRICS.items() if key != "IRR" or not interval_irr}
        if yield_metrics:
            from worksheet_yoc_spread_D123 import CALCULATED_METRICS, yield_records
            catalog = {key: value for key, value in catalog.items() if key not in CALCULATED_METRICS}
            metrics = metrics | CALCULATED_METRICS
            derived, computed_yield = yield_records(case.get("yield_inputs"), scenarios, case_sha256)
            values.extend(derived)
            if schema in WORKBOOK_FUNDING_PILOT_SCHEMAS:
                from worksheet_equity_tdc_D124 import METRIC, METRIC_ID, equity_records
                del catalog[METRIC_ID]
                metrics = metrics | {METRIC_ID: METRIC}
                derived, computed_equity = equity_records(case.get("funding_inputs"), computed_yield, case_sha256)
                values.extend(derived)
            if schema in WORKBOOK_OPERATING_PILOT_SCHEMAS:
                from worksheet_occupancy_D125 import METRIC, METRIC_ID, occupancy_records
                del catalog[METRIC_ID]
                metrics = metrics | {METRIC_ID: METRIC}
                derived, computed_occupancy = occupancy_records(case.get("occupancy_inputs"),
                                    case.get("yield_inputs") or {}, scenarios, case_sha256)
                values.extend(derived)
            if schema in WORKBOOK_RETURN_PILOT_SCHEMAS:
                from worksheet_final_metrics_D126 import METRICS as FINAL_METRICS, final_metric_records
                catalog = {key: value for key, value in catalog.items() if key not in FINAL_METRICS}
                metrics = metrics | FINAL_METRICS
                derived, computed_returns = final_metric_records(case, scenarios, computed_yield, values, case_sha256)
                values.extend(derived)
        metrics = metrics | catalog
        references, sources = reference_records(case.get("reference_metrics"), scenarios, case_sha256, metrics=catalog)
        values.extend(references)
        provenance = {"reference_metric_sources": sources}
    supplied = case.get("rules") or []
    if interval_irr:
        from worksheet_irr_D122 import IRR_METRIC, combine_irr
        rules = criterion_records(supplied, metrics | {"IRR": IRR_METRIC})
        irr_rules = [(index, row) for index, row in enumerate(rules) if row["metric_id"] == "IRR"]
        require(len({row["scenario_id"] for _, row in irr_rules}) == len(irr_rules), "Duplicate IRR criterion")
        rules = [row for row in rules if row["metric_id"] != "IRR"]
    else:
        rules = criterion_records(supplied, metrics)
    if computed_occupancy is not None:
        from worksheet_occupancy_D125 import METRIC_ID, validate_occupancy_conditions
        for row in rules:
            if row["metric_id"] == METRIC_ID:
                validate_occupancy_conditions(row)
    source = dict(schema=SCHEMA, context=context, case_id=CASE_ID,
                  criteria_revision=revision or "SYNTHETIC-unbound-criteria",
                  criteria_status="synthetic_fixture_only", required_metrics=list(metrics),
                  required_scenarios=list(SCENARIOS),
                  metric_values=values,
                  criteria=rules if revision else [], aggregation_rule=case.get("aggregation_rule"),
                  hypothetical_band_policy=None)
    run = simulate_screening(encoded(source))
    result = run.payload
    run_hash = run.sha256
    if interval_irr:
        result = combine_irr(result, irr_rules if revision else [], scenarios, case.get("irr_policy"), case_sha256)
        result["scalar_run_sha256"] = run_hash
        if yield_metrics:
            result.update(component="D123", yield_by_scenario=computed_yield)
        if computed_equity is not None:
            result.update(component="D124", equity_tdc_by_scenario=computed_equity)
        if computed_occupancy is not None:
            result.update(component="D125", occupancy_by_scenario=computed_occupancy)
        if computed_returns is not None:
            result.update(component="D126", final_metrics_by_scenario=computed_returns)
        run_hash = sha(encoded(result))
    require(result["decision"] == "PENDING" and not result["criteria_adopted"] and not result["production_authorized"],
            "The synthetic screening acquired decision authority")
    return result | provenance | dict(run_sha256=run_hash,
                         criteria_source_blockers=[] if revision else ["criteria_revision_missing"])


def read_scenario(spec, raw, expected, *, include_sizing_service=False, include_capital_bases=False):
    if raw is None:
        blocker = "workbook_missing"
    elif expected is None:
        blocker = "workbook_hash_missing"
    elif sha(raw) != expected:
        blocker = "workbook_hash_mismatch"
    else:
        result, _ = build_intake_case(spec, sha(encoded(spec)), raw, capacity_first=True,
                                      include_sizing_service=include_sizing_service, include_capital_bases=include_capital_bases)
        return result | {"expected_workbook_sha256": expected, "source_blockers": []}
    return dict(state="PENDING", cash_per_usd_10=None, expected_workbook_sha256=expected,
                received_workbook_sha256=None if raw is None else sha(raw), source_blockers=[blocker])


def render_pilot(scenarios, screening, *, extended=False, interval_irr=False, yield_metrics=False,
                 local_milestone=None):
    lines = [(f"Simulación PASS/FAIL  |  {screening['simulation_result']}", True)]
    for name, scenario in scenarios.items():
        cash = scenario["cash_per_usd_10"]
        if cash is None:
            lines.append((f"{name} | Retorno por USD 10 PENDING", True))
            source = scenario["source_blockers"]
            pending = [row["cell"] for row in scenario.get("preflight", {}).get("checklist", []) if row["action"]]
            if source:
                lines.append((SOURCE_LABELS[source[0]], False))
            elif pending:
                cells = ", ".join(pending[:5])
                lines.append((f"Revisá {cells}. Ver detalle en el expediente.", False))
            else:
                lines.append(("Capacidad o cálculo pendiente. Ver motivo en el expediente.", False))
            continue
        lines.append((f"{name} | Cobro total USD {money(cash['total_distributions'])} por USD 10 iniciales.", True))
        for event in cash["events"]:
            if amount(event["amount"]):
                label = LABELS.get(event["category"], "Aporte al refinanciar")
                lines.append((f"{event['date']} | {label} USD {money(event['amount'])}", False))
        lines.append((f"Aportado USD {money(cash['total_contributions'])} | "
                      f"Saldo sin recuperar USD {money(cash['unrecovered_after_sale'])}.", False))
    states = {(r["metric_id"], r["scenario_id"]): RESULT_LABELS[r["state"]] for r in screening["comparisons"]}
    lines.append(("REGLAS SINTÉTICAS POR MÉTRICA", True))
    labels = METRIC_LABELS
    computed_equity = screening.get("equity_tdc_by_scenario")
    computed_occupancy = screening.get("occupancy_by_scenario")
    computed_returns = screening.get("final_metrics_by_scenario")
    ratios = {}
    if yield_metrics:
        ratios = {metric: {name: row["values"][metric] for name, row in screening["yield_by_scenario"].items()}
                  for metric in ("YoC", "spread")}
    if computed_equity is not None:
        ratios["equity_TDC"] = {name: row["equity_to_tdc"] for name, row in computed_equity.items()}
    if computed_occupancy is not None:
        ratios["breakeven_occupancy"] = {name: row["algebraic_crossing"] for name, row in computed_occupancy.items()}
    if computed_returns is not None:
        from worksheet_final_metrics_D126 import ASKING, COC
        for metric in (ASKING, COC):
            ratios[metric] = {name: row["metrics"][metric]["value"] for name, row in computed_returns.items()}
    if extended:
        from worksheet_reference_metrics_D121 import REFERENCE_LABELS
        labels = labels | REFERENCE_LABELS
    if computed_returns is not None:
        labels = labels | {COC: "CoC pos-refi del tramo"}
    for metric, label in labels.items():
        if interval_irr and metric == "IRR":
            from worksheet_irr_D122 import display_enclosure
            parts = [f"{name} {display_enclosure(result['annual_enclosure'])} ({states[metric, name]})"
                     for name, result in screening["irr_by_scenario"].items()]
            lines.append((f"{label} | " + " | ".join(parts), False))
        elif metric in ratios:
            from worksheet_yoc_spread_D123 import display_yield
            parts = []
            for name, value in ratios[metric].items():
                display = display_yield(metric, value)
                if value is not None:
                    impossible = metric == "breakeven_occupancy" and computed_occupancy[name]["state"] == "infeasible_within_domain"
                    suffix = ", inviable" if impossible else ""
                    display += f" ({states[metric, name]}{suffix})"
                parts.append(f"{name} {display}")
            lines.append((f"{label} | " + " | ".join(parts), False))
        else:
            lines.append((f"{label} | Base {states[metric, 'Base']} | Downside {states[metric, 'Downside']}", False))
    if screening["simulation_result"] == "PENDING":
        lines.append(("Consultá los datos o reglas pendientes en el expediente.", False))
    lines.append(("Capital agregado del proyecto. Decisión de inversión PENDING.", False))
    milestone = "D120"
    if computed_returns is not None:
        milestone = local_milestone or "D126"
        lines.append(("Diez métricas calculadas bajo las definiciones del piloto sintético.", False))
    elif computed_occupancy is not None:
        milestone = "D125"
        lines.append(("Ocho métricas calculadas y dos referencias sintéticas declaradas.", False))
    elif computed_equity is not None:
        milestone = "D124"
        lines.append(("Siete métricas calculadas y tres referencias sintéticas declaradas.", False))
    elif yield_metrics:
        milestone = "D123"
        lines.append(("Seis métricas calculadas y cuatro referencias sintéticas declaradas.", False))
    elif interval_irr:
        milestone = "D122"
        lines.append(("Cuatro métricas calculadas y seis referencias sintéticas declaradas.", False))
    elif extended:
        milestone = "D121"
        lines.append(("Tres métricas del libro de caja y siete referencias sintéticas declaradas.", False))
    return render_page(f"{milestone} | Piloto sintético de Base y Downside", lines, 15 if extended else 18,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Planilla, retorno y simulación de decisión")


def pilot_pipeline(case_sha256, scenarios, screening, pdf, local_review=None, version_suite=None):
    """Record the deterministic contracts exercised by the workbook pilot."""
    source_ready = {name: not row["source_blockers"] for name, row in scenarios.items()}
    input_blockers = {name: [item["cell"] for item in row.get("preflight", {}).get("checklist", []) if item["action"]]
                      for name, row in scenarios.items()}
    cash_ready = {name: row["cash_per_usd_10"] is not None for name, row in scenarios.items()}
    stages = [
        dict(dot="D01", bots=["B01", "B02"], source_ready=source_ready),
        dict(dot="D02", bots=["B04"], pending_cells=input_blockers),
        dict(dot="D05", bots=["B12", "B13", "B14"], cash_ready=cash_ready,
             comparison_count=len(screening["comparisons"]), simulation=screening["simulation_result"],
             decision=screening["decision"], blockers=screening["simulation_blockers"]),
        dict(dot="D06", bots=["B15"], pdf_sha256=sha(pdf), pages=1),
    ]
    if local_review is not None:
        bots = local_review["bots"]
        stages[0]["bots"].append("B03")
        stages[0]["classification"] = bots["B03"]["state"]
        stages[2]["bots"].insert(0, "B08")
        stages[2]["gate"] = "PENDING" if screening["simulation_result"] == "PENDING" else "checked_synthetic"
        stages[2:2] = [
            dict(dot="D03", bots=["B05", "B06", "B07", "B09"], reconciliation=bots["B09"]["state"]),
            dict(dot="D04", bots=["B10", "B11"], local_snapshot=bots["B11"]["state"]),
        ]
        stages.append(dict(dot="D07", bots=["B16", "B17"], audit_command="audit", version_suite=version_suite))
    return dict(case_sha256=case_sha256, stages=stages)


def build_pilot(case, case_sha256, workbooks, *, extended=False, interval_irr=False, yield_metrics=False,
                current_revision_raw=None, plan_raw=None):
    required = {"schema", "worksheet_case", "workbook_sha256"}
    optional = {"criteria_revision", "aggregation_rule", "rules"}
    if extended:
        optional.add("reference_metrics")
    if interval_irr:
        optional.add("irr_policy")
    if yield_metrics:
        optional.add("yield_inputs")
    schema = case.get("schema")
    if schema in WORKBOOK_FUNDING_PILOT_SCHEMAS:
        optional.add("funding_inputs")
    if schema in WORKBOOK_OPERATING_PILOT_SCHEMAS:
        optional.add("occupancy_inputs")
    if schema in WORKBOOK_RETURN_PILOT_SCHEMAS:
        optional.add("return_inputs")
    if schema in WORKBOOK_LOCAL_CHAIN_SCHEMAS:
        optional.add("local_sources")
    require(required <= case.keys() <= required | optional,
            "An explicit pilot workbook case and source hashes are required")
    spec = case["worksheet_case"]
    _exact(spec, {"schema", "source_fixture_sha256", "monthly_discount_rate"})
    origin_raw = local_file(ROOT, SOURCE_FIXTURE).read_bytes()
    require(spec["schema"] == WORKBOOK_CAPACITY_SCHEMA and spec["source_fixture_sha256"] == sha(origin_raw),
            "The pilot requires the same synthetic workbook and capacity profile")
    hashes = case["workbook_sha256"]
    require(isinstance(hashes, dict) and hashes.keys() <= set(SCENARIOS)
            and all(value is None or isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                    for value in hashes.values()), "Use explicit worksheet SHA-256 values or missing entries")
    scenarios = {name: read_scenario(spec, workbooks[name], hashes.get(name),
                                   include_sizing_service=schema in WORKBOOK_OPERATING_PILOT_SCHEMAS,
                                   include_capital_bases=schema in WORKBOOK_RETURN_PILOT_SCHEMAS)
                 for name in SCENARIOS}
    screening = run_screening(case, scenarios, json.loads(origin_raw)["scenario_context"],
                              extended=extended, interval_irr=interval_irr, yield_metrics=yield_metrics,
                              case_sha256=case_sha256)
    local_review = None
    revision_review = None
    local_milestone = None
    version_suite = None
    if schema in WORKBOOK_LOCAL_CHAIN_SCHEMAS:
        from worksheet_local_sources_D127 import object_or_empty, review_local_sources
        local_milestone, version_suite = "D127", "check_worksheet_local_chain_D127.py"
        local_sources = case.get("local_sources")
        pdf_plan = None
        if schema == WORKBOOK_PLAN_CHAIN_SCHEMA:
            from worksheet_plan_pdf_D130 import read_plan
            pdf_plan = read_plan(plan_raw, object_or_empty(local_sources).get("plan_pdf"))
        elif schema == WORKBOOK_SCAN_CHAIN_SCHEMA:
            from worksheet_plan_scan_D131 import read_scanned_plan
            pdf_plan = read_scanned_plan(plan_raw, object_or_empty(local_sources).get("plan_pdf"))
        elif schema == WORKBOOK_MIXED_CHAIN_SCHEMA:
            from worksheet_plan_mixed_D132 import read_mixed_plan
            pdf_plan = read_mixed_plan(plan_raw, object_or_empty(local_sources).get("plan_pdf"))
        elif schema in (WORKBOOK_OVERLAY_CHAIN_SCHEMA, WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA):
            from worksheet_plan_overlay_D133 import read_overlay_plan
            pdf_plan = read_overlay_plan(plan_raw, object_or_empty(local_sources).get("plan_pdf"),
                                         require_rotation=schema == WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA)
        elif schema == WORKBOOK_PLAN_SET_CHAIN_SCHEMA:
            from worksheet_plan_set_D135 import read_plan_set
            pdf_plan = read_plan_set(plan_raw, object_or_empty(local_sources).get("plan_pdf"))
        local_review = review_local_sources(local_sources, hashes, pdf_plan=pdf_plan)
        screening["worksheet_simulation_result"] = screening["simulation_result"]
        screening["worksheet_run_sha256"] = screening.pop("run_sha256")
        blockers = local_review["blockers"]
        evidence = {"screening": screening, "local_review": local_review}
        if schema in WORKBOOK_CURRENT_CHAIN_SCHEMAS:
            from worksheet_revision_D128 import review_revision
            revision_review = review_revision(case, current_revision_raw)
            local_milestone, version_suite = "D128", "check_worksheet_current_chain_D128.py"
            evidence["revision_review"] = revision_review
            blockers = blockers + [f"B12:{reason}" for reason in revision_review["blockers"]]
        if schema == WORKBOOK_PLAN_CHAIN_SCHEMA:
            local_milestone, version_suite = "D130", "check_worksheet_plan_pdf_D130.py"
        elif schema == WORKBOOK_SCAN_CHAIN_SCHEMA:
            local_milestone, version_suite = "D131", "check_worksheet_plan_scan_D131.py"
        elif schema == WORKBOOK_MIXED_CHAIN_SCHEMA:
            local_milestone, version_suite = "D132", "check_worksheet_plan_mixed_D132.py"
        elif schema == WORKBOOK_OVERLAY_CHAIN_SCHEMA:
            local_milestone, version_suite = "D133", "check_worksheet_plan_overlay_D133.py"
        elif schema == WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA:
            local_milestone, version_suite = "D134", "check_worksheet_plan_rotation_D134.py"
        elif schema == WORKBOOK_PLAN_SET_CHAIN_SCHEMA:
            local_milestone, version_suite = "D135", "check_worksheet_plan_set_D135.py"
        if blockers:
            screening["simulation_result"] = "PENDING"
            screening["simulation_blockers"] = sorted(set(screening["simulation_blockers"] + blockers))
        screening["run_sha256"] = sha(encoded(evidence))
    pdf = render_pilot(scenarios, screening, extended=extended, interval_irr=interval_irr,
                       yield_metrics=yield_metrics, local_milestone=local_milestone)
    simulation = screening["simulation_result"]
    pipeline = {}
    if schema in WORKBOOK_RETURN_PILOT_SCHEMAS:
        pipeline["pipeline"] = pilot_pipeline(case_sha256, scenarios, screening, pdf, local_review, version_suite)
    if local_review is not None:
        pipeline["local_review"] = local_review
    if revision_review is not None:
        pipeline["revision_review"] = revision_review
    return dict(profile=PROFILE, scope="synthetic_aggregate_equity", decision="PENDING",
                state="PENDING" if simulation == "PENDING" else "computed_synthetic_pilot",
                simulation_result=simulation, case_sha256=case_sha256, scenarios=scenarios,
                screening=screening, pdf_sha256=sha(pdf), page_count=1,
                personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False) | pipeline, pdf
