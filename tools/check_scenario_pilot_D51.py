"""Replay an explicit multi-metric Base and Downside screening rehearsal."""
from argparse import ArgumentParser
from collections import Counter
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from check_first_pilot_D49 import rehearsal as sale_rehearsal
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_refinance_pilot_D50 import FIXTURE as REFI_FIXTURE, WORKBOOK as PREVIOUS, rehearsal as refi_rehearsal
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.debt_service import rational
from miniuw_foundation.screening import AGGREGATION, SCHEMA, simulate_screening
from miniuw_foundation.scheduled_expense_case import sha
from pilot_workbook_D49 import workbook_bytes


FIXTURE = "templates/synthetic-multi-scenario-pilot-D51.json"
WORKBOOK = "docs/review/MiniUW_Planilla_Cotejo_D51.xlsx"
METRICS = {
    "equity_multiple": ("multiple", "scalar", None, "gross-dated-cash-window"),
    "equity_recovered": ("fraction", "scalar", None, "net-refi-cash-over-initial-equity"),
    "equity_cash_in": ("USD", "money", "USD", "gross-additional-contribution-at-refinance"),
}
MISSING = {"operator": None, "threshold": None}


def scenario_values(files, independent):
    result = json.loads(files["results.json"])
    story = result["project"]
    categories = story["cash_by_category"]
    initial = amount(categories["initial_capital"])
    actual = {
        "equity_multiple": amount(story["equity_multiple"]),
        "equity_recovered": amount(categories["net_refinance_distribution"]) / initial,
        "equity_cash_in": amount(categories["refinance_cash_in"]),
    }
    reference = Counter()
    for _, _, category, value in independent["events"]:
        reference[category] += Fraction(value)
    expected = {
        "equity_multiple": Fraction(independent["equity_multiple"]),
        "equity_recovered": reference["net_refinance_distribution"] / reference["initial_capital"],
        "equity_cash_in": reference["refinance_cash_in"],
    }
    require(actual == expected and result["decision"] == "PENDING"
            and result["deployment_enabled"] is result["real_decisions_enabled"] is False,
            "Scenario metrics differ from independently dated cash")
    return result, actual


def screen_input(fixture, probe, sources):
    values, criteria = [], []
    action = probe["action"]
    require(action in (None, "missing_value", "missing_rule", "missing_scenario", "unit_mismatch"),
            "Unknown synthetic fault probe")
    for scenario, (result, amounts) in sources.items():
        if scenario == "Downside" and action == "missing_scenario":
            continue
        for metric, (unit, kind, currency, definition) in METRICS.items():
            story = result["project"]
            horizon = story["cash_horizon"]
            period = (f"{horizon['start']}/{horizon['end']}" if metric == "equity_multiple"
                      else result["refinance"]["date"])
            identity = dict(metric_id=metric, scenario_id=scenario, definition_ref=f"SYNTHETIC-D51-{definition}",
                            unit=unit, quantity_kind=kind, currency=currency, period_ref=period,
                            applicability="applicable", applicability_evidence_ref=None)
            record = identity | {"value": rational(amounts[metric])}
            rule = identity | probe["overrides"].get(metric, fixture["criteria"][metric])
            if scenario == "Downside" and metric == "equity_cash_in":
                if action == "missing_value":
                    record["value"] = None
                elif action == "missing_rule":
                    rule["fail_condition"] = MISSING
                elif action == "unit_mismatch":
                    record["unit"] = "fraction"
            values.append(record)
            criteria.append(rule)
    return dict(schema=SCHEMA, context=sources["Base"][0]["context"], case_id=f"SYNTHETIC-D51-{probe['id']}",
                criteria_revision=f"SYNTHETIC-D51-{probe['id']}-v1", criteria_status="synthetic_fixture_only",
                required_metrics=list(METRICS), required_scenarios=list(sources), metric_values=values, criteria=criteria,
                aggregation_rule=AGGREGATION, hypothetical_band_policy=None)


def rehearsal():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = json.loads(raw)
    require(fixture["schema"] == "miniuw.synthetic-multi-scenario-pilot.v1"
            and fixture["refinance_fixture_sha256"] == sha(local_file(ROOT, REFI_FIXTURE).read_bytes())
            and fixture["scenarios"] == {"Base": "cash-out", "Downside": "cash-in"}
            and fixture["criteria"].keys() == METRICS.keys(), "Scenario fixture or source inventory differs")
    packages, refinance = refi_rehearsal()
    sources = {scenario: scenario_values(packages[name], refinance["independent_references"][name])
               for scenario, name in fixture["scenarios"].items()}
    require(sources["Base"][0]["context"] == sources["Downside"][0]["context"],
            "Base and Downside are not variants of the same case")
    probes = []
    for probe in fixture["probes"]:
        source = screen_input(fixture, probe, sources)
        run = simulate_screening(encoded(source))
        result = run.payload
        require(result["simulation_result"] == probe["expected"]
                and result["simulation_blockers"] == sorted(probe["blockers"])
                and result["decision"] == "PENDING" and result["criteria_adopted"] is False
                and result["production_authorized"] is False and len(result["comparisons"]) == 6,
                f"Scenario screening differs: {probe['id']}")
        if probe["id"] in ("falta_dato_con_fail", "falta_regla_con_fail"):
            require(any(row["state"] == "FAIL_CONDITION" and row["scenario_id"] == "Downside"
                        for row in result["comparisons"]), "The incomplete test lost the known failure")
        probes.append(dict(id=probe["id"], input=source, screening_sha256=run.sha256, expected=probe["expected"],
                           simulation=result["simulation_result"], decision=result["decision"],
                           comparisons=result["comparisons"], blockers=result["simulation_blockers"]))
    require(Counter(row["simulation"] for row in probes) == {"PASS": 1, "FAIL": 1, "PENDING": 6},
            "Scenario probe inventory differs")
    evidence = dict(schema="miniuw.synthetic-multi-scenario-pilot-evidence.v1", fixture_sha256=sha(raw),
                    decision="PENDING", criteria_adopted=False, deployment_enabled=False, probes=probes,
                    sources={scenario: dict(archive_case=fixture["scenarios"][scenario],
                                             results_sha256=sha(packages[fixture["scenarios"][scenario]]["results.json"]),
                                             values={key: str(value) for key, value in values.items()})
                             for scenario, (_, values) in sources.items()})
    return refinance, evidence


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for the scenario comparison and workbook.")
    args = parser.parse_args()
    try:
        refinance, evidence = rehearsal()
        _, sale = sale_rehearsal()
        require(workbook_bytes(sale, refinance) == local_file(ROOT, PREVIOUS).read_bytes(), "Prior workbook differs")
        workbook = workbook_bytes(sale, refinance, evidence)
        require(workbook == local_file(ROOT, WORKBOOK).read_bytes(), "Scenario workbook differs from its evidence")
        if args.output is not None:
            target = args.output
            require(not target.exists() and not target.is_symlink() and target.parent.is_dir(), "Use a new output directory")
            with TemporaryDirectory(dir=target.parent, prefix=".miniuw-scenario-pilot-") as temp:
                staged = Path(temp) / "piloto"
                staged.mkdir()
                (staged / Path(WORKBOOK).name).write_bytes(workbook)
                (staged / "ensayo_base_downside.json").write_bytes(encoded(evidence))
                staged.rename(target)
        print(json.dumps(dict(status="passed", decision="PENDING", probes=len(evidence["probes"]),
                              comparisons=sum(len(row["comparisons"]) for row in evidence["probes"]),
                              simulated=dict(Counter(row["simulation"] for row in evidence["probes"])),
                              workbook_sha256=sha(workbook)), ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
