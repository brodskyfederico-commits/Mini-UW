"""Reproduce the first synthetic pilot and compare its equity multiple in a separate screening rehearsal."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_unified_worksheet_D48 import expected_events
from miniuw_worksheet_v1 import build_package, encoded, verify_package
from miniuw_foundation.screening import AGGREGATION, SCHEMA, simulate_screening
from miniuw_foundation.scheduled_expense_case import sha
from pilot_workbook_D49 import workbook_bytes

FIXTURE = "templates/synthetic-first-pilot-D49.json"
WORKBOOK = "docs/review/MiniUW_Planilla_Cotejo_D49.xlsx"


def rehearsal():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = json.loads(raw)
    case_raw = local_file(ROOT, fixture["case_path"]).read_bytes()
    require(fixture["schema"] == "miniuw.synthetic-first-pilot.v1" and sha(case_raw) == fixture["case_sha256"]
            and fixture["metric_id"] == "equity_multiple", "Pilot fixture or case differs")
    case = json.loads(case_raw)
    require(case["profile"] == "without_refinance" and case["archive_case"] == "matched", "Unexpected pilot profile")

    events = sorted(expected_events("matched"))
    contributions = sum(value for _, kind, _, value in events if kind == "contribution")
    receipts = sum(value for _, kind, _, value in events if kind == "distribution")
    multiple = Fraction(receipts, contributions)
    packages = {}
    rows = []
    for probe in fixture["cases"]:
        archive_case = probe["archive_case"]
        if archive_case not in packages:
            candidate = case_raw if archive_case == case["archive_case"] else encoded(case | {"archive_case": archive_case})
            packages[archive_case] = build_package(candidate)
        _, result = packages[archive_case]
        project = result["project"]
        value = None if project is None else project["equity_multiple"]
        if value is not None:
            require(amount(value) == multiple
                    and amount(project["gross_contributions"]) == contributions
                    and amount(project["gross_distributions"]) == receipts, "Pilot disagrees with the independent ledger")
        context = result["context"]
        identity = dict(metric_id=fixture["metric_id"], scenario_id=context["scenario_id"],
                        definition_ref="SYNTHETIC-D49-dated-gross-cash-multiple-v1",
                        unit="multiple", currency=None, quantity_kind="scalar",
                        period_ref="SYNTHETIC-D49:2026-10-01/2027-07-01",
                        applicability="applicable", applicability_evidence_ref=None)
        comparison = dict(schema=SCHEMA, case_id=f"SYNTHETIC-D49-{probe['id']}", context=context,
                          criteria_revision=fixture["criteria_revision"], criteria_status="synthetic_fixture_only",
                          required_metrics=[fixture["metric_id"]], required_scenarios=[context["scenario_id"]],
                          metric_values=[identity | {"value": value}],
                          criteria=[identity | {k: probe[k] for k in ("pass_condition", "fail_condition")}],
                          aggregation_rule=AGGREGATION, hypothetical_band_policy=None)
        run = simulate_screening(encoded(comparison))
        screen = run.payload
        blockers = screen["simulation_blockers"]
        expected_blocker = probe["expected_blocker"]
        require(screen["comparisons"][0]["state"] == probe["expected_state"]
                and (not blockers if expected_blocker is None
                     else any(value.rsplit(":", 1)[-1] == expected_blocker for value in blockers)),
                f"Pilot screening reason differs: {probe['id']}")
        require(screen["simulation_result"] == probe["expected"] and screen["decision"] == result["decision"] == "PENDING"
                and screen["criteria_adopted"] is screen["production_authorized"] is False
                and result["real_decisions_enabled"] is result["deployment_enabled"] is False,
                f"Pilot screening differs: {probe['id']}")
        rows.append(dict(id=probe["id"], archive_case=archive_case, input=comparison, expected=probe["expected"],
                         simulation=screen["simulation_result"], operational_decision=screen["decision"],
                         blockers=screen["simulation_blockers"], screening_sha256=run.sha256,
                         project_case_sha256=result["provenance"]["case_sha256"], pdf_sha256=result["pdf_sha256"]))
    require(len(rows) == 6 and {r["simulation"] for r in rows} == {"PASS", "FAIL", "PENDING"}, "Pilot outcome inventory differs")
    evidence = dict(schema="miniuw.synthetic-first-pilot-evidence.v1", decision="PENDING",
                    fixture_sha256=sha(raw), criteria_adopted=False, deployment_enabled=False,
                    independent_reference=dict(events=[(date, kind, category, str(value))
                                                       for date, kind, category, value in events],
                                               contributions=str(contributions), receipts=str(receipts),
                                               equity_multiple=str(multiple)),
                    cases=rows)
    return packages["matched"][0], evidence


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for the audited synthetic pilot.")
    args = parser.parse_args()
    try:
        package, evidence = rehearsal()
        workbook = workbook_bytes(evidence)
        require(workbook == local_file(ROOT, WORKBOOK).read_bytes(), "Published workbook differs from the pilot rehearsal")
        if args.output is not None:
            target = args.output
            require(not target.exists() and not target.is_symlink() and target.parent.is_dir(), "Use a new pilot output directory")
            with TemporaryDirectory(dir=target.parent, prefix=".miniuw-pilot-") as temp:
                staged = Path(temp) / "piloto"
                case_dir = staged / "expediente"
                case_dir.mkdir(parents=True)
                for name, content in package.items():
                    (case_dir / name).write_bytes(content)
                verify_package(case_dir)
                (staged / "MiniUW_Planilla_Cotejo_D49.xlsx").write_bytes(workbook)
                (staged / "ensayo_pass_fail.json").write_bytes(encoded(evidence))
                staged.rename(target)
        rows = evidence["cases"]
        print(json.dumps(dict(status="passed", decision=evidence["decision"], cases=len(rows),
                              simulated={value: sum(row["simulation"] == value for row in rows)
                                         for value in ("PASS", "FAIL", "PENDING")},
                              workbook_sha256=sha(workbook)), ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
