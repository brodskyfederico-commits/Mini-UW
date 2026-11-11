"""Audit all ten synthetic pilot metrics and test incomplete or stale claims."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_screening_pilot_D120 import BOOKS, audit, check_cash_and_metrics, condition, replace_rule
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_screening_pilot_D120 import run_screening


CASE = ROOT / "templates/synthetic-workbook-screening-pilot-D121.json"
EXPECTED_REFERENCES = {
    "YoC": (Fraction("0.10"), Fraction("0.08")),
    "spread": (200, -50),
    "breakeven_occupancy": (Fraction("0.65"), Fraction("0.80")),
    "post_refi_CoC": (Fraction("0.09"), Fraction("0.07")),
    "equity_TDC": (Fraction("0.40"), Fraction("0.45")),
    "IRR": (Fraction("0.827793"), Fraction("0.263647")),
    "asking_relative_to_supported_price": (Fraction("0.90"), Fraction("0.97")),
}


def indexed(records):
    return {(record["scenario_id"], record["metric_id"]): record for record in records}


def verify(temp, saved_output):
    case_raw = CASE.read_bytes()
    case = json.loads(case_raw)
    base, downside = BOOKS["Base"], BOOKS["Downside"]
    passed, page = audit(CASE, base, downside, saved_output or temp / "pass")
    check_cash_and_metrics(passed)
    screening = passed["screening"]
    comparisons = indexed(screening["comparisons"])
    sources = indexed(screening["reference_metric_sources"])
    require(passed["simulation_result"] == "PASS" and "Simulación PASS/FAIL  |  PASS" in page
            and "siete referencias sintéticas declaradas" in page
            and len(screening["comparisons"]) == len(comparisons) == 20
            and len(screening["reference_metric_sources"]) == len(sources) == 14
            and all(row["state"] == "PASS_CONDITION" for row in comparisons.values()),
            "The complete inventory did not pass all twenty comparisons")
    for metric, expected_values in EXPECTED_REFERENCES.items():
        for name, expected in zip(BOOKS, expected_values):
            source = sources[name, metric]
            require(amount(comparisons[name, metric]["metric_record"]["value"]) == expected
                    and source["origin"] == "supplied_synthetic_reference"
                    and source["case_sha256"] == sha(case_raw)
                    and source["workbook_sha256"] == sha(BOOKS[name].read_bytes())
                    and source["claim_pointer"] == f"/reference_metrics/{name}/claims/{metric}"
                    and not source["blockers"],
                    f"{name} {metric} lost its declared value or provenance")

    threshold = Fraction("0.09")
    stricter = replace_rule(case, "YoC", "Downside", pass_condition=condition(">=", threshold),
                            fail_condition=condition("<", threshold))
    stricter["criteria_revision"] = "SYNTHETIC-D121-stricter-yoc-r2"
    stricter_path = temp / "stricter.json"
    stricter_path.write_bytes(encoded(stricter))
    failed, failed_page = audit(stricter_path, base, downside, temp / "fail")
    failed_checks = indexed(failed["screening"]["comparisons"])
    require(failed["simulation_result"] == "FAIL" and "Simulación PASS/FAIL  |  FAIL" in failed_page
            and failed["scenarios"] == passed["scenarios"]
            and [key for key, row in failed_checks.items() if row["state"] == "FAIL_CONDITION"] == [("Downside", "YoC")],
            "The Downside criterion change did not isolate the FAIL from the cash")

    incomplete = deepcopy(stricter)
    incomplete["criteria_revision"] = "SYNTHETIC-D121-missing-inputs-r3"
    incomplete["reference_metrics"]["Downside"]["claims"]["IRR"]["value"] = None
    incomplete["rules"] = [rule for rule in incomplete["rules"]
                           if (rule["scenario_id"], rule["metric_id"]) != ("Downside", "post_refi_CoC")]
    incomplete_path = temp / "incomplete.json"
    incomplete_path.write_bytes(encoded(incomplete))
    pending, pending_page = audit(incomplete_path, base, downside, temp / "pending")
    pending_screening = pending["screening"]
    pending_checks = indexed(pending_screening["comparisons"])
    require(pending["simulation_result"] == "PENDING" and "Simulación PASS/FAIL  |  PENDING" in pending_page
            and pending["scenarios"] == passed["scenarios"]
            and pending_checks["Downside", "YoC"]["state"] == "FAIL_CONDITION"
            and "IRR:Downside:metric_value_missing" in pending_screening["simulation_blockers"]
            and "post_refi_CoC:Downside:criterion_record_missing" in pending_screening["simulation_blockers"]
            and indexed(pending_screening["reference_metric_sources"])["Downside", "IRR"]["blockers"]
            == ["reference_value_missing"],
            "A known failure overrode a missing value or rule, or blocked valid cash")

    stale = deepcopy(case)
    stale["reference_metrics"]["Downside"]["workbook_sha256"] = sha(base.read_bytes())
    stale["reference_metrics"]["Base"]["claims"]["spread"]["unit"] = "fraction"
    scenarios = passed["scenarios"]
    stale_screening = run_screening(stale, scenarios, scenarios["Base"]["context"], extended=True,
                                    case_sha256=sha(encoded(stale)))
    stale_sources = indexed(stale_screening["reference_metric_sources"])
    stale_checks = indexed(stale_screening["comparisons"])
    require(stale_screening["simulation_result"] == "PENDING"
            and all(stale_sources["Downside", metric]["blockers"]
                    == ["reference_workbook_revision_mismatch_or_missing"]
                    and stale_checks["Downside", metric]["metric_record"]["value"] is None
                    for metric in EXPECTED_REFERENCES)
            and stale_sources["Base", "spread"]["blockers"] == ["reference_definition_or_unit_missing_or_incompatible"]
            and stale_checks["Base", "spread"]["metric_record"]["value"] is None,
            "A stale workbook revision or incompatible unit acquired a verified value")
    return dict(status="passed", metrics=10, comparisons=20, calculated_values=6,
                declared_synthetic_values=14, full_workbook_cases=3, stale_workbook_and_unit_blocked=True,
                simulated=dict(PASS=1, FAIL=1, PENDING=1), decision="PENDING", page_count=1,
                pdf_sha256=passed["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited PASS package.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d121-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
