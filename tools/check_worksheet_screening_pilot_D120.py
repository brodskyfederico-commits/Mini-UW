"""Verify the workbook pilot through the public run/audit and exact rule checks."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_intake_case_D117 import changed_cells, workbook_with_numeric_cell
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import DOWNSIDE_WORKBOOK_FILE, WORKBOOK_FILE, encoded
from worksheet_screening_pilot_D120 import read_scenario, run_screening


CASE = ROOT / "templates/synthetic-workbook-screening-pilot-D120.json"
BOOKS = {name: ROOT / f"templates/synthetic-pilot-{name.lower()}-D120.xlsx" for name in ("Base", "Downside")}
EXPECTED_SALE = {"Base": Fraction(54056381, 6060200), "Downside": Fraction(42542001, 6060200)}


def audit(case, base, downside, output):
    created = call("run", case, "--workbook", base, "--downside-workbook", downside, "--output", output)
    verified = call("audit", output)
    result = json.loads((output / "results.json").read_bytes())
    pdf = (output / "MiniUW_Resumen.pdf").read_bytes()
    page, = PdfReader(BytesIO(pdf)).pages
    require(created["pdf_sha256"] == verified["pdf_sha256"] == result["pdf_sha256"] == sha(pdf)
            and (output / "case.json").read_bytes() == case.read_bytes()
            and (output / WORKBOOK_FILE).read_bytes() == base.read_bytes()
            and (output / DOWNSIDE_WORKBOOK_FILE).read_bytes() == downside.read_bytes()
            and result["decision"] == "PENDING" and not result["real_decisions_enabled"]
            and not result["deployment_enabled"] and result["personal_investor_return"] is None,
            "The audit lost the exact inputs or the real-decision guard")
    return result, page.extract_text()


def check_cash_and_metrics(result):
    metrics = {(row["scenario_id"], row["metric_id"]): row for row in result["screening"]["comparisons"]}
    for name, sale in EXPECTED_SALE.items():
        scenario = result["scenarios"][name]
        cash = scenario["cash_per_usd_10"]
        expected = (
            ("2027-01-01", "initial_capital", 10),
            ("2027-03-01", "operating_distribution", 1),
            ("2027-04-01", "net_refinance_distribution", 2),
            ("2027-06-01", "operating_distribution", 1),
            ("2027-07-01", "net_sale_distribution", sale),
        )
        require(cash["basis_event_ids"] == ["initial"]
                and tuple((event["date"], event["category"], amount(event["amount"]))
                          for event in cash["events"] if amount(event["amount"])) == expected
                and amount(cash["total_distributions"]) == 4 + sale
                and amount(cash["unrecovered_after_sale"]) == 0,
                f"{name} cash differs from independent dated events")
        for metric, value in {"equity_multiple": (4 + sale) / 10,
                              "equity_recovered": Fraction(1, 5), "equity_cash_in": 0}.items():
            require(amount(metrics[name, metric]["metric_record"]["value"]) == value,
                    f"{name} {metric} did not come from the verified cash")


def replace_rule(case, metric, scenario, **replacement):
    rules = [row | replacement if (row["metric_id"], row["scenario_id"]) == (metric, scenario)
             else row for row in case["rules"]]
    return case | {"rules": rules}


def condition(operator, value):
    return dict(operator=operator, threshold=rational(value))


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    base, downside = (BOOKS[name] for name in ("Base", "Downside"))
    require(changed_cells(base.read_bytes(), downside.read_bytes()) == {"C67"}
            and all(case["workbook_sha256"][name] == sha(path.read_bytes()) for name, path in BOOKS.items()),
            "The Base/Downside worksheet inventory changed")
    passed, page = audit(CASE, base, downside, saved_output or temp / "pass")
    check_cash_and_metrics(passed)
    require(passed["simulation_result"] == "PASS" and "Simulación PASS/FAIL  |  PASS" in page
            and all(row["state"] == "PASS_CONDITION" for row in passed["screening"]["comparisons"]),
            "The completed pilot did not produce a synthetic PASS")

    fail_case = replace_rule(case, "equity_multiple", "Downside", pass_condition=condition(">=", Fraction(6, 5)),
                             fail_condition=condition("<", Fraction(6, 5)))
    fail_case |= {"criteria_revision": "SYNTHETIC-D120-fail-r2"}
    fail_path = temp / "fail.json"
    fail_path.write_bytes(encoded(fail_case))
    failed, failed_page = audit(fail_path, base, downside, temp / "fail")
    require(failed["simulation_result"] == "FAIL" and "Simulación PASS/FAIL  |  FAIL" in failed_page
            and failed["scenarios"] == passed["scenarios"]
            and any(row["state"] == "FAIL_CONDITION" and row["scenario_id"] == "Downside"
                    and row["metric_id"] == "equity_multiple" for row in failed["screening"]["comparisons"]),
            "A criterion change did not isolate the FAIL from the unchanged cash")

    missing_raw = workbook_with_numeric_cell(downside.read_bytes(), "C72")
    require(changed_cells(downside.read_bytes(), missing_raw) == {"C72"}, "The missing-data probe changed other inputs")
    missing_workbook = temp / "missing-dscr.xlsx"
    missing_workbook.write_bytes(missing_raw)
    missing_case = temp / "missing-dscr.json"
    missing_case.write_bytes(encoded(case | {"workbook_sha256": case["workbook_sha256"] | {"Downside": sha(missing_raw)}}))
    pending, pending_page = audit(missing_case, base, missing_workbook, temp / "missing-dscr")
    require(pending["simulation_result"] == "PENDING" and "Revisá Inputs!C72." in pending_page
            and pending["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and pending["scenarios"]["Base"] == passed["scenarios"]["Base"],
            "The missing input leaked a result or withdrew the available scenario")

    scenarios = passed["scenarios"]
    context = scenarios["Base"]["context"]
    missing_rule = replace_rule(fail_case, "equity_cash_in", "Downside", fail_condition=None)
    missing = run_screening(missing_rule, scenarios, context)
    require(missing["simulation_result"] == "PENDING"
            and "equity_cash_in:Downside:fail_condition_rule_missing_or_unsupported" in missing["simulation_blockers"]
            and any(row["state"] == "FAIL_CONDITION" for row in missing["comparisons"]),
            "A known failure overrode a missing rule")
    band = replace_rule(case, "equity_multiple", "Downside", pass_condition=condition(">=", Fraction(6, 5)))
    pending_band = run_screening(band, scenarios, context)
    require(pending_band["simulation_result"] == "PENDING"
            and "intermediate_band_pending_professional_review" in pending_band["simulation_blockers"],
            "The intermediate band did not stay PENDING")
    require(run_screening(case | {"aggregation_rule": None}, scenarios, context)["simulation_result"] == "PENDING",
            "The pilot supplied a missing aggregation rule")
    swapped = read_scenario(case["worksheet_case"], base.read_bytes(), case["workbook_sha256"]["Downside"])
    absent = read_scenario(case["worksheet_case"], None, case["workbook_sha256"]["Downside"])
    for row, reason in ((swapped, "workbook_hash_mismatch"), (absent, "workbook_missing")):
        require(row["state"] == "PENDING" and row["source_blockers"] == [reason] and row["cash_per_usd_10"] is None
                and run_screening(case, scenarios | {"Downside": row}, context)["simulation_result"] == "PENDING",
                "A missing or swapped source acquired cash or a decision")

    (temp / "fail" / DOWNSIDE_WORKBOOK_FILE).write_bytes(base.read_bytes())
    call("audit", temp / "fail", blocked=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=3,
                rule_and_source_probes=5, simulated=dict(PASS=1, FAIL=1, PENDING=1), page_count=1,
                tampered_workbook_rejected=True, pdf_sha256=passed["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the verified complete pilot package.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d120-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
