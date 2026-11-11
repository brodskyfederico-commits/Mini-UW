"""Audit calculated YoC, spread and unchanged USD 10 cash through the worksheet pilot."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_screening_pilot_D120 import BOOKS, audit, check_cash_and_metrics, condition, replace_rule
from check_yoc_spread_D70 import FIXTURE
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_screening_pilot_D120 import run_screening
from worksheet_yoc_spread_D123 import yield_evidence


CASE = ROOT / "templates/synthetic-workbook-screening-pilot-D123.json"
EXPECTED = {
    "Base": (100, 1000, Fraction(8, 100), Fraction(1, 10), 200),
    "Downside": (75, 1100, Fraction(85, 1000), Fraction(3, 44), Fraction(-1850, 11)),
}


def verify(temp, saved_output):
    case_raw = CASE.read_bytes()
    case = json.loads(case_raw)
    base, downside = BOOKS["Base"], BOOKS["Downside"]
    failed, page = audit(CASE, base, downside, saved_output or temp / "fail")
    check_cash_and_metrics(failed)
    scenarios = failed["scenarios"]
    screening = failed["screening"]
    evidence = screening["yield_by_scenario"]
    comparisons = {(row["scenario_id"], row["metric_id"]): row for row in screening["comparisons"]}
    require(failed["simulation_result"] == "FAIL" and "Simulación PASS/FAIL  |  FAIL" in page
            and "Base 10,00% (PASS) | Downside 6,82% (FAIL)" in page
            and "Base 200,00 bps (PASS) | Downside -168,18 bps (FAIL)" in page
            and len(comparisons) == len(screening["comparisons"]) == 20
            and len(screening["reference_metric_sources"]) == 8
            and {key for key, row in comparisons.items() if row["state"] == "FAIL_CONDITION"}
            == {("Downside", "YoC"), ("Downside", "spread")},
            "The main fixture did not report the two expected failures")
    d70 = json.loads((ROOT / FIXTURE).read_bytes())["scenarios"]
    for name, expected in EXPECTED.items():
        row = evidence[name]
        raw = case["yield_inputs"][name]
        inputs = ("stabilized_noi", "tdc", "cap_rate")
        require(all(raw[key] == d70[name][key] | {"context": raw[key]["context"]} for key in inputs),
                f"{name} changed the original operating, cost or market inputs")
        fields = ("stabilized_noi", "tdc", "reference_cap")
        require(tuple(amount(row[key]) for key in fields)
                + tuple(amount(comparisons[name, metric]["metric_record"]["value"]) for metric in ("YoC", "spread"))
                == expected
                and not any(row["blockers"].values()) and row["case_sha256"] == sha(case_raw)
                and row["workbook_sha256"] == sha(BOOKS[name].read_bytes())
                and row["source_pointer"] == f"/yield_inputs/{name}",
                f"{name} did not retain its exact calculated metrics or source")

    at_threshold = case
    for metric, threshold in zip(("YoC", "spread"), EXPECTED["Downside"][-2:], strict=True):
        at_threshold = replace_rule(at_threshold, metric, "Downside", pass_condition=condition(">=", threshold),
                                    fail_condition=condition("<", threshold))
    at_threshold["criteria_revision"] = "SYNTHETIC-D123-equality-r2"
    threshold_case = temp / "threshold.json"
    threshold_case.write_bytes(encoded(at_threshold))
    passed, pass_page = audit(threshold_case, base, downside, temp / "pass")
    require(passed["simulation_result"] == "PASS" and "Simulación PASS/FAIL  |  PASS" in pass_page
            and passed["scenarios"] == scenarios
            and all(result["values"] == evidence[name]["values"]
                    for name, result in passed["screening"]["yield_by_scenario"].items()),
            "The two explicit inclusive thresholds changed cash or rejected exact equality")

    no_cap = deepcopy(case)
    no_cap["yield_inputs"]["Downside"].pop("cap_rate")
    missing_case = temp / "missing-cap.json"
    missing_case.write_bytes(encoded(no_cap))
    pending, pending_page = audit(missing_case, base, downside, temp / "pending")
    row = pending["screening"]["yield_by_scenario"]["Downside"]
    require(pending["simulation_result"] == "PENDING" and "Simulación PASS/FAIL  |  PENDING" in pending_page
            and "Spread | Base 200,00 bps (PASS) | Downside PENDING" in pending_page
            and pending["scenarios"] == scenarios
            and row["values"] == {"YoC": rational(Fraction(3, 44)), "spread": None}
            and row["blockers"] == {"YoC": [], "spread": ["compatible_reference_cap_unavailable"]},
            "A missing market cap replaced the cap, removed valid cash or let YoC force a FAIL")

    missing_rule = replace_rule(case, "spread", "Downside", fail_condition=None)
    result = run_screening(missing_rule, scenarios, scenarios["Base"]["context"], extended=True, interval_irr=True,
                           yield_metrics=True, case_sha256=sha(encoded(missing_rule)))
    require(result["simulation_result"] == "PENDING"
            and "spread:Downside:fail_condition_rule_missing_or_unsupported" in result["simulation_blockers"],
            "A missing spread criterion supplied an implicit rule")

    source = case["yield_inputs"]["Downside"]
    scenario = scenarios["Downside"]
    missing_cost = deepcopy(source)
    missing_cost["tdc"]["rows"].pop()
    missing_noi = deepcopy(source)
    missing_noi["stabilized_noi"]["income_rows"].pop()
    stale = source | {"workbook_sha256": case["workbook_sha256"]["Base"]}
    for inputs, blocker in ((missing_cost, "tdc_component_inventory_incomplete"),
                            (missing_noi, "stabilized_operating_inventory_missing_or_incompatible"),
                            (stale, "yield_workbook_revision_mismatch_or_missing")):
        result = yield_evidence(inputs, "Downside", scenario)
        require(result["values"] == {"YoC": None, "spread": None} and blocker in result["blockers"]["YoC"],
                "Incomplete or stale operating inputs acquired a computed ratio")
    cap_only = deepcopy(source)
    cap_only["cap_rate"]["value"] = rational(Fraction(1, 10))
    values = yield_evidence(cap_only, "Downside", scenario)["values"]
    require(amount(values["YoC"]) == Fraction(3, 44) and amount(values["spread"]) == Fraction(-3500, 11),
            "Changing the reference cap failed to affect only the spread")
    return dict(status="passed", decision="PENDING", metrics=10, calculated_metrics=6, full_workbook_cases=3,
                simulated=dict(PASS=1, FAIL=1, PENDING=1), page_count=1, pdf_sha256=failed["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited primary fixture.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d123-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
