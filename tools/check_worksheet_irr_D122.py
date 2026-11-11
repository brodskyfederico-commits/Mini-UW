"""Audit cash-derived annual IRR, exact threshold comparisons and worksheet revisions."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_intake_case_D117 import changed_cells, workbook_with_numeric_cell
from check_worksheet_screening_pilot_D120 import BOOKS, EXPECTED_SALE, audit, check_cash_and_metrics, condition, replace_rule
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_irr_D122 import IRR_POLICY, annual_evidence
from worksheet_screening_pilot_D120 import run_screening


CASE = ROOT / "templates/synthetic-workbook-screening-pilot-D122.json"


def with_threshold(case, name, threshold):
    return replace_rule(case, "IRR", name, pass_condition=condition(">=", threshold),
                        fail_condition=condition("<", threshold))


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    base, downside = BOOKS["Base"], BOOKS["Downside"]
    passed, page = audit(CASE, base, downside, saved_output or temp / "pass")
    check_cash_and_metrics(passed)
    screening = passed["screening"]
    evidence = screening["irr_by_scenario"]
    scenarios = passed["scenarios"]
    require(screening["simulation_result"] == "PASS" and len(screening["comparisons"]) == 20
            and len(screening["reference_metric_sources"]) == 12
            and all(row["state"] == "PASS_CONDITION" for row in screening["comparisons"])
            and "Base 82,77% a 82,78% (PASS) | Downside 26,36% a 26,37% (PASS)" in page,
            "The calculated IRR did not join the full synthetic screening and one-page result")
    for name, sale in EXPECTED_SALE.items():
        row = evidence[name]
        flows = (-10, 0, 1, 2, 0, 1, sale)
        roots = row["periodic_result"]
        bounds = roots["roots"][0]["periodic_rate_interval"]
        monthly_lower, monthly_upper = (Fraction(bounds[key]) for key in ("lower", "upper"))
        annual_lower, annual_upper = (_fraction(row["annual_enclosure"][key], 1300) for key in ("lower", "upper"))

        def npv(rate):
            return sum(value / (1 + rate) ** index for index, value in enumerate(flows))

        require(tuple((item["date"], amount(item["net"])) for item in row["dated_net_flows"])
                == tuple((f"2027-{month:02d}-01", value) for month, value in enumerate(flows, 1))
                and roots["distinct_positive_discount_roots"] == 1 and roots["selected_rate"] is None
                and npv(monthly_lower) >= 0 > npv(monthly_upper)
                and annual_lower == (1 + monthly_lower) ** 12 - 1
                and annual_upper == (1 + monthly_upper) ** 12 - 1
                and row["cash_sha256"] == sha(encoded(scenarios[name]["cash_per_usd_10"])),
                f"{name} annual enclosure did not reproduce the independently dated cash")

    stricter = with_threshold(case, "Downside", Fraction("0.30"))
    stricter["criteria_revision"] = "SYNTHETIC-D122-stricter-irr-r2"
    stricter_path = temp / "stricter.json"
    stricter_path.write_bytes(encoded(stricter))
    failed, failed_page = audit(stricter_path, base, downside, temp / "fail")
    require(failed["simulation_result"] == "FAIL" and "Simulación PASS/FAIL  |  FAIL" in failed_page
            and failed["scenarios"] == scenarios
            and failed["screening"]["irr_by_scenario"]["Downside"]["comparison_state"] == "FAIL_CONDITION",
            "A stricter synthetic IRR rule did not fail independently of cash")

    def screen(spec):
        return run_screening(spec, scenarios, scenarios["Base"]["context"], extended=True,
                             interval_irr=True, case_sha256=sha(encoded(spec)))

    boundary = screen(with_threshold(case, "Downside", Fraction("0.263647266")))
    require(boundary["simulation_result"] == "PENDING"
            and boundary["irr_by_scenario"]["Downside"]["condition_relations"]
            == {"pass_condition": "mixed", "fail_condition": "mixed"},
            "A threshold inside the annual enclosure acquired a synthetic decision")
    missing_rule = replace_rule(case, "IRR", "Downside", fail_condition=None)
    for spec, blocker in ((case | {"irr_policy": None}, "explicit_synthetic_monthly_IRR_policy_missing_or_unsupported"),
                          (missing_rule, "fail_condition_rule_missing_or_unsupported")):
        pending = screen(spec)
        require(pending["simulation_result"] == "PENDING" and f"IRR:Downside:{blocker}" in pending["simulation_blockers"],
                "Missing calculation policy or criterion supplied an implied result")

    new_book = workbook_with_numeric_cell(downside.read_bytes(), "C67", "0.25")
    require(changed_cells(downside.read_bytes(), new_book) == {"C67"}, "The worksheet probe changed other cells")
    revised_book = temp / "revised.xlsx"
    revised_book.write_bytes(new_book)
    revised_case = temp / "revised.json"
    revised_case.write_bytes(encoded(case | {"workbook_sha256": case["workbook_sha256"] | {"Downside": sha(new_book)}}))
    revised, _ = audit(revised_case, base, revised_book, temp / "revised")
    revised_cash = revised["scenarios"]["Downside"]["cash_per_usd_10"]
    revised_irr = revised["screening"]["irr_by_scenario"]["Downside"]["annual_enclosure"]
    require(revised["simulation_result"] == "PENDING" and revised["scenarios"]["Base"] == scenarios["Base"]
            and amount(revised_cash["total_distributions"]) < amount(scenarios["Downside"]["cash_per_usd_10"]["total_distributions"])
            and _fraction(revised_irr["upper"], 1300) < _fraction(evidence["Downside"]["annual_enclosure"]["lower"], 1300)
            and all(row["state"] == "PENDING" for row in revised["screening"]["reference_metric_sources"]
                    if row["scenario_id"] == "Downside"),
            "A revised sale assumption did not recalculate IRR or withhold stale supplied references")

    off_grid = deepcopy(scenarios["Downside"]["cash_per_usd_10"])
    off_grid["events"][-1]["date"] = "2027-07-02"
    multiple = {"events": [dict(date=f"2027-0{index}-01", kind=kind, amount=rational(value))
                           for index, (kind, value) in enumerate((("contribution", 10), ("distribution", 23),
                                                                 ("contribution", Fraction("13.2"))), 1)]}
    blocked = (annual_evidence(None, IRR_POLICY), annual_evidence(off_grid, IRR_POLICY), annual_evidence(multiple, IRR_POLICY))
    for result, blocker in zip(blocked, ("current_scenario_cash_unavailable", "cash_dates_outside_supported_month_start_grid",
                                         "unique_distinct_periodic_root_required_without_selection"), strict=True):
        require(result["annual_enclosure"] is None and blocker in result["blockers"], "An ineligible ledger acquired an IRR")
    return dict(status="passed", decision="PENDING", metrics=10, calculated_metrics=4, full_workbook_cases=3,
                simulated=dict(PASS=1, FAIL=1, PENDING=1), exact_annual_enclosure=True, page_count=1,
                pdf_sha256=passed["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited PASS package.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d122-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
