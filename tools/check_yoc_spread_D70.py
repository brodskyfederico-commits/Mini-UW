"""Rehearse stabilized YoC and spread with exact, explicitly scoped synthetic sources."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require
from miniuw_linked_cotejo_D54 import publish
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.debt_service import _date, _fraction, rational
from miniuw_foundation.expense_cash_detail import _exact, _json
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.screening import AGGREGATION, SCHEMA, simulate_screening


FIXTURE = "templates/synthetic-yoc-spread-D70.json"
COMPONENTS = {"acquisition", "hard", "soft", "financing", "other"}
METRICS = {"YoC": ("fraction", "stabilized-noi-over-complete-tdc"),
           "spread": ("bps", "yoc-less-compatible-reference-cap")}


def source_ref(value):
    return isinstance(value, str) and value.startswith("SYNTHETIC-D70-")


def compute(scenario, period):
    _exact(scenario, {"stabilized_noi", "tdc", "cap_rate"})
    raw = encoded(scenario["stabilized_noi"])
    run = produce_operating_noi(raw)
    noi = run.payload
    tdc, cap = scenario["tdc"], scenario["cap_rate"]
    _exact(tdc, {"context", "currency", "complete", "scope_ref", "rows"})
    _exact(cap, {"context", "currency", "period_ref", "kind", "value", "source_ref"})
    blockers = {"YoC": [], "spread": []}
    if noi["period_ref"] != period or noi["noi"] is None or noi["currency"] != "USD":
        blockers["YoC"].append("compatible_stabilized_noi_unavailable")
    if (tdc["context"] != noi["context"] or tdc["currency"] != noi["currency"]
            or tdc["complete"] is not True or not source_ref(tdc["scope_ref"])):
        blockers["YoC"].append("compatible_complete_tdc_unavailable")
    require(isinstance(tdc["rows"], list) and len(tdc["rows"]) <= len(COMPONENTS), "Bounded TDC inventory required")
    components = {}
    for row in tdc["rows"]:
        _exact(row, {"component", "amount", "source_ref"})
        name, value = row["component"], _fraction(row["amount"])
        require(isinstance(name, str) and name not in components, "Duplicate or invalid TDC component")
        components[name] = value
        if value is None or value < 0 or not source_ref(row["source_ref"]):
            blockers["YoC"].append(f"tdc_component_unavailable:{name}")
    total = None
    if set(components) != COMPONENTS:
        blockers["YoC"].append("tdc_component_inventory_incomplete")
    if not blockers["YoC"]:
        total = sum(components.values())
        if total <= 0:
            blockers["YoC"].append("tdc_must_be_positive")
    yoc = None if blockers["YoC"] else amount(noi["noi"]) / total
    cap_value = _fraction(cap["value"])
    if (cap_value is None or cap_value <= 0 or cap["kind"] != "synthetic_market_cap_reference"
            or cap["context"] != noi["context"] or cap["currency"] != noi["currency"]
            or cap["period_ref"] != period or not source_ref(cap["source_ref"])):
        blockers["spread"].append("compatible_reference_cap_unavailable")
    if yoc is None:
        blockers["spread"].append("yoc_unavailable")
    spread = None if blockers["spread"] else (yoc - cap_value) * 10_000
    return dict(values={key: None if value is None else rational(value)
                        for key, value in (("YoC", yoc), ("spread", spread))},
                blockers=blockers, context=noi["context"], stabilized_noi=noi["noi"], noi_run_sha256=run.sha256,
                tdc=None if total is None else rational(total), tdc_source_sha256=sha(encoded(tdc)),
                cap_reference_sha256=sha(encoded(cap)), reference_cap=cap["value"])


def screen(sources, rules, period, variant):
    values, criteria = [], []
    _exact(rules, METRICS)
    for scenario, evidence in sources.items():
        for metric, (unit, definition) in METRICS.items():
            identity = dict(metric_id=metric, scenario_id=scenario, definition_ref=f"SYNTHETIC-D70-{definition}",
                            unit=unit, quantity_kind="scalar", currency=None, period_ref=period,
                            applicability="applicable", applicability_evidence_ref=None)
            values.append(identity | {"value": evidence["values"][metric]})
            criteria.append(identity | rules[metric])
    data = dict(schema=SCHEMA, context=sources["Base"]["context"], case_id=f"SYNTHETIC-D70-{variant}",
                criteria_revision=f"SYNTHETIC-D70-{variant}-v1", criteria_status="synthetic_fixture_only",
                required_metrics=list(METRICS), required_scenarios=list(sources), metric_values=values,
                criteria=criteria, aggregation_rule=AGGREGATION, hypothetical_band_policy=None)
    run = simulate_screening(encoded(data))
    result = run.payload
    require(result["decision"] == "PENDING" and result["production_authorized"] is False,
            "Synthetic ratios acquired an operational decision")
    return dict(result=result, screening_sha256=run.sha256)


def verify():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = _json(raw)
    _exact(fixture, {"schema", "stabilized_start", "stabilized_end", "scenarios", "criteria"})
    require(fixture["schema"] == "miniuw.synthetic-yoc-spread-rehearsal.v1", "Unsupported rehearsal schema")
    start, end = _date(fixture["stabilized_start"]), _date(fixture["stabilized_end"])
    require(start.day == end.day == 1 and start.month == end.month and end.year == start.year + 1,
            "The synthetic annual stabilized window must be explicit")
    period = f"{start}/{end}"
    _exact(fixture["scenarios"], {"Base", "Downside"})
    sources = {name: compute(scenario, period) for name, scenario in fixture["scenarios"].items()}
    base_context = sources["Base"]["context"]
    for name, row in sources.items():
        require(row["context"] == base_context | {"scenario_id": f"SYNTHETIC-D70-{name}"},
                "The two synthetic scenarios must belong to the same case and definition revision")
    expected = {"Base": (Fraction(1, 10), 200), "Downside": (Fraction(3, 44), Fraction(-1850, 11))}
    for name, reference in expected.items():
        require(tuple(amount(sources[name]["values"][metric]) for metric in METRICS) == reference,
                f"{name} differs from the independent ratio calculation")
    probes = {}
    for name, expected_decision in {"strict": "FAIL", "relaxed": "PASS", "intermediate": "PENDING"}.items():
        probes[name] = screen(sources, fixture["criteria"][name], period, name)
        require(probes[name]["result"]["simulation_result"] == expected_decision,
                f"{name} screening differs from its independent result")
    blocked = deepcopy(fixture["scenarios"]["Downside"])
    blocked["cap_rate"]["period_ref"] = "SYNTHETIC-different-period"
    mismatched = compute(blocked, period)
    require(mismatched["values"]["spread"] is None
            and mismatched["values"]["YoC"] == sources["Downside"]["values"]["YoC"],
            "Incompatible reference cap should block only spread")
    probes["cap_period_mismatch"] = screen(sources | {"Downside": mismatched},
                                           fixture["criteria"]["strict"], period, "cap_period_mismatch")
    require(probes["cap_period_mismatch"]["result"]["simulation_result"] == "PENDING",
            "The incomplete scenario was not held pending")
    blocked["tdc"]["rows"].pop()
    missing_cost = compute(blocked, period)
    require(all(v is None for v in missing_cost["values"].values()), "Incomplete TDC inventory supplied ratios")
    zero_cost = deepcopy(fixture["scenarios"]["Base"])
    for row in zero_cost["tdc"]["rows"]:
        row["amount"] = rational(Fraction(0))
    zero_tdc = compute(zero_cost, period)
    require(zero_tdc["blockers"]["YoC"] == ["tdc_must_be_positive"]
            and all(v is None for v in zero_tdc["values"].values()),
            "A zero TDC denominator supplied a ratio")
    zero_noi = deepcopy(fixture["scenarios"]["Base"])
    zero_noi["stabilized_noi"]["income_rows"][0]["value"] = zero_noi["stabilized_noi"]["expense_rows"][0]["value"]
    zero_yield = compute(zero_noi, period)
    require(not any(zero_yield["blockers"].values()) and amount(zero_yield["values"]["YoC"]) == 0
            and amount(zero_yield["values"]["spread"]) == -800, "Explicit zero NOI was treated as missing")
    return dict(status="passed", decision="PENDING", fixture_sha256=sha(raw), stabilized_period=period,
                sources=sources, probes=probes, incomplete_cost_control=missing_cost,
                zero_tdc_blocked=True, explicit_zero_noi_preserved=True, deployment_enabled=False, real_decisions_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New path for the full synthetic evidence.")
    try:
        args = parser.parse_args()
        report = verify()
        if args.output is not None:
            publish(args.output, report)
        print(json.dumps(dict(status=report["status"], decision=report["decision"],
                              scenario_values={k: v["values"] for k, v in report["sources"].items()},
                              simulations={k: v["result"]["simulation_result"] for k, v in report["probes"].items()},
                              zero_tdc_blocked=report["zero_tdc_blocked"],
                              explicit_zero_noi_preserved=report["explicit_zero_noi_preserved"]), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
