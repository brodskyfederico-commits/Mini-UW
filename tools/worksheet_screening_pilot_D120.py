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
from miniuw_worksheet_v1 import WORKBOOK_CAPACITY_SCHEMA, encoded
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


def run_screening(case, scenarios, context, *, extended=False, interval_irr=False, case_sha256=None):
    revision = case.get("criteria_revision")
    require(revision is None or isinstance(revision, str) and re.fullmatch(r"SYNTHETIC-[A-Za-z0-9_-]{1,80}", revision),
            "Use an explicit synthetic criteria revision")
    metrics = METRICS
    values = [row for name in SCENARIOS for row in metric_values(name, scenarios[name])]
    provenance = {}
    if extended:
        from worksheet_reference_metrics_D121 import REFERENCE_METRICS, reference_records
        catalog = {key: value for key, value in REFERENCE_METRICS.items() if key != "IRR" or not interval_irr}
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
        run_hash = sha(encoded(result))
    require(result["decision"] == "PENDING" and not result["criteria_adopted"] and not result["production_authorized"],
            "The synthetic screening acquired decision authority")
    return result | provenance | dict(run_sha256=run_hash,
                         criteria_source_blockers=[] if revision else ["criteria_revision_missing"])


def read_scenario(spec, raw, expected):
    if raw is None:
        blocker = "workbook_missing"
    elif expected is None:
        blocker = "workbook_hash_missing"
    elif sha(raw) != expected:
        blocker = "workbook_hash_mismatch"
    else:
        result, _ = build_intake_case(spec, sha(encoded(spec)), raw, capacity_first=True)
        return result | {"expected_workbook_sha256": expected, "source_blockers": []}
    return dict(state="PENDING", cash_per_usd_10=None, expected_workbook_sha256=expected,
                received_workbook_sha256=None if raw is None else sha(raw), source_blockers=[blocker])


def render_pilot(scenarios, screening, *, extended=False, interval_irr=False):
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
    if extended:
        from worksheet_reference_metrics_D121 import REFERENCE_LABELS
        labels = labels | REFERENCE_LABELS
    for metric, label in labels.items():
        if interval_irr and metric == "IRR":
            from worksheet_irr_D122 import display_enclosure
            parts = [f"{name} {display_enclosure(result['annual_enclosure'])} ({states[metric, name]})"
                     for name, result in screening["irr_by_scenario"].items()]
            lines.append((f"{label} | " + " | ".join(parts), False))
        else:
            lines.append((f"{label} | Base {states[metric, 'Base']} | Downside {states[metric, 'Downside']}", False))
    if screening["simulation_result"] == "PENDING":
        lines.append(("Consultá los datos o reglas pendientes en el expediente.", False))
    lines.append(("Capital agregado del proyecto. Decisión de inversión PENDING.", False))
    if interval_irr:
        lines.append(("Cuatro métricas calculadas y seis referencias sintéticas declaradas.", False))
    elif extended:
        lines.append(("Tres métricas del libro de caja y siete referencias sintéticas declaradas.", False))
    milestone = "D122" if interval_irr else "D121" if extended else "D120"
    return render_page(f"{milestone} | Piloto sintético de Base y Downside", lines, 15 if extended else 18,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Planilla, retorno y simulación de decisión")


def build_pilot(case, case_sha256, workbooks, *, extended=False, interval_irr=False):
    required = {"schema", "worksheet_case", "workbook_sha256"}
    optional = {"criteria_revision", "aggregation_rule", "rules"}
    if extended:
        optional.add("reference_metrics")
    if interval_irr:
        optional.add("irr_policy")
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
    scenarios = {name: read_scenario(spec, workbooks[name], hashes.get(name)) for name in SCENARIOS}
    screening = run_screening(case, scenarios, json.loads(origin_raw)["scenario_context"],
                              extended=extended, interval_irr=interval_irr, case_sha256=case_sha256)
    pdf = render_pilot(scenarios, screening, extended=extended, interval_irr=interval_irr)
    simulation = screening["simulation_result"]
    return dict(profile=PROFILE, scope="synthetic_aggregate_equity", decision="PENDING",
                state="PENDING" if simulation == "PENDING" else "computed_synthetic_pilot",
                simulation_result=simulation, case_sha256=case_sha256, scenarios=scenarios,
                screening=screening, pdf_sha256=sha(pdf), page_count=1,
                personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False), pdf
