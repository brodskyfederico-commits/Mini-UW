"""Exercise reception, validation, calculation, screening, PDF and replay."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_intake_case_D117 import changed_cells, workbook_with_numeric_cell
from check_worksheet_screening_pilot_D120 import BOOKS, audit, check_cash_and_metrics, condition, replace_rule
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_final_metrics_D126 import ASKING, COC
from worksheet_screening_pilot_D120 import run_screening


CASE = ROOT / "templates/synthetic-workbook-screening-pilot-D126.json"


def audit_variant(case, temp, name, *, downside=BOOKS["Downside"]):
    case_path = temp / f"{name}.json"
    case_path.write_bytes(encoded(case))
    return audit(case_path, BOOKS["Base"], downside, temp / name)


def verify(temp, saved_output):
    case_raw = CASE.read_bytes()
    case = json.loads(case_raw)
    output = saved_output or temp / "primary"
    primary, page = audit(CASE, BOOKS["Base"], BOOKS["Downside"], output)
    check_cash_and_metrics(primary)
    screening = primary["screening"]
    scenarios = primary["scenarios"]
    evidence = screening["final_metrics_by_scenario"]
    stages = primary["pipeline"]["stages"]
    require(len(screening["comparisons"]) == 20 and len(screening["required_metrics"]) == 10
            and screening["reference_metric_sources"] == []
            and primary["simulation_result"] == "FAIL"
            and [(row["dot"], row["bots"]) for row in stages]
            == [("D01", ["B01", "B02"]), ("D02", ["B04"]), ("D05", ["B12", "B13", "B14"]), ("D06", ["B15"])]
            and primary["pipeline"]["case_sha256"] == sha(case_raw)
            and stages[0]["source_ready"] == {"Base": True, "Downside": True}
            and stages[1]["pending_cells"] == {"Base": [], "Downside": []}
            and stages[2]["comparison_count"] == 20 and stages[2]["decision"] == "PENDING"
            and stages[3]["pdf_sha256"] == primary["pdf_sha256"]
            and "CoC pos-refi del tramo | Base 10,00% (PASS) | Downside 10,00% (PASS)" in page
            and "Asking / precio soportado | Base 0,82x (PASS) | Downside 1,40x (FAIL)" in page,
            "The complete pilot lost a calculated metric, stage, rule or one-page result")
    for name, maximum in (("Base", 426), ("Downside", 250)):
        metrics = evidence[name]["metrics"]
        coc, asking = metrics[COC], metrics[ASKING]
        require(amount(coc["value"]) == Fraction(1, 10) and amount(coc["operating_receipts"]) == 100
                and amount(coc["capital_base"]) == 1000 and coc["operating_event_ids"] == ["op-after"]
                and coc["period_ref"] == "2027-04-01/2027-07-01" and not coc["annualized"]
                and amount(asking["supported_price"]) == maximum and amount(asking["asking"]) == 350
                and amount(asking["value"]) == Fraction(350, maximum)
                and asking["evaluated_prices"] == 701 and asking["feasible_prices"] == maximum + 1
                and asking["boundary"]["next_grid_price"] == maximum + 1,
                f"{name} included the wrong receipt or missed the exact maximum on the price grid")
        bounds, objectives = asking["boundary"], asking["objectives"]
        require(all(amount(bounds["at_maximum"][key]) >= amount(rule["threshold"]) for key, rule in objectives.items())
                and any(amount(bounds["at_next"][key]) < amount(rule["threshold"]) for key, rule in objectives.items()),
                f"{name} failed to distinguish the maximum from its successor")

    compatible = deepcopy(case)
    for name, rent in (("Base", 1100), ("Downside", 1200)):
        compatible["occupancy_inputs"][name]["profile"]["rent_at_full_occupancy"] = rational(Fraction(rent))
    for metric, floor in (("YoC", Fraction(3, 44)), ("spread", Fraction(-1850, 11))):
        compatible = replace_rule(compatible, metric, "Downside", pass_condition=condition(">=", floor),
                                  fail_condition=condition("<", floor))
    compatible["criteria_revision"] = "SYNTHETIC-D126-compatible-r2"
    passed, _ = audit_variant(compatible, temp, "pass")
    require(passed["simulation_result"] == "PASS" and passed["scenarios"] == scenarios
            and amount(passed["screening"]["final_metrics_by_scenario"]["Downside"]["metrics"][ASKING]["supported_price"]) == 350,
            "A criterion revision did not reprice support independently of actual scenario cash")

    incomplete = deepcopy(case)
    incomplete["return_inputs"]["Downside"].pop("coc_basis")
    incomplete["return_inputs"]["Base"]["pricing"].pop("asking")
    pending, _ = audit_variant(incomplete, temp, "pending")
    metrics = pending["screening"]["final_metrics_by_scenario"]
    require(pending["simulation_result"] == "PENDING" and pending["scenarios"] == scenarios
            and metrics["Downside"]["metrics"][COC]["value"] is None
            and metrics["Base"]["metrics"][ASKING]["value"] is None
            and amount(metrics["Base"]["metrics"][ASKING]["supported_price"]) == 426,
            "A missing capital basis or asking leaked a comparison or changed verified cash")

    missing_rule = replace_rule(case, "YoC", "Downside", pass_condition=None)
    pending_rule = run_screening(missing_rule, scenarios, scenarios["Base"]["context"], extended=True, interval_irr=True,
                                 yield_metrics=True, case_sha256=sha(encoded(missing_rule)))
    require(pending_rule["simulation_result"] == "PENDING"
            and pending_rule["final_metrics_by_scenario"]["Downside"]["metrics"][ASKING]["blockers"]
            == ["compatible_YoC_and_equity_multiple_minimum_rules_required"],
            "Missing price objective supplied an implicit rule")
    book = BOOKS["Downside"].read_bytes()
    missing_dscr = workbook_with_numeric_cell(book, "C72")
    require(changed_cells(book, missing_dscr) == {"C72"}, "The workbook probe edited another cell")
    blocked_book = temp / "missing-dscr.xlsx"
    blocked_book.write_bytes(missing_dscr)
    blocked_case = case | {"workbook_sha256": case["workbook_sha256"] | {"Downside": sha(missing_dscr)}}
    blocked, blocked_page = audit_variant(blocked_case, temp, "blocked-intake", downside=blocked_book)
    blocked_stages = blocked["pipeline"]["stages"]
    require(blocked["simulation_result"] == "PENDING" and blocked["scenarios"]["Base"] == scenarios["Base"]
            and blocked_stages[0]["source_ready"] == {"Base": True, "Downside": True}
            and blocked_stages[1]["pending_cells"] == {"Base": [], "Downside": ["Inputs!C72"]}
            and blocked_stages[2]["cash_ready"] == {"Base": True, "Downside": False}
            and "Downside | Retorno por USD 10 PENDING" in blocked_page,
            "An incomplete worksheet passed validation or discarded the available scenario")
    verified = call("audit", output)
    require(verified.get("audit_bot") == "B16", "Verified package did not report the deterministic auditor")
    altered = temp / "altered"
    copytree(output, altered)
    primary["pipeline"]["stages"][-1]["pages"] = 2
    rewritten = encoded(primary)
    (altered / "results.json").write_bytes(rewritten)
    manifest_path = altered / "package.json"
    manifest = json.loads(manifest_path.read_bytes())
    row, = (row for row in manifest["files"] if row["path"] == "results.json")
    row.update(bytes=len(rewritten), sha256=sha(rewritten))
    manifest_path.write_bytes(encoded(manifest))
    call("audit", altered, blocked=True)
    return dict(status="passed", decision="PENDING", metrics=10, calculated_metrics=10, full_workbook_cases=4,
                simulated=dict(PASS=1, FAIL=1, PENDING=2), page_count=1,
                pdf_sha256=primary["pdf_sha256"], rehashed_stage_tamper_rejected=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited primary fixture.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d126-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
