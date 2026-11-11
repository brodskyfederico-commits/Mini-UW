"""Audit the pilot's economic occupancy, annual service and USD 10 cash."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_screening_pilot_D120 import BOOKS, audit, check_cash_and_metrics, condition, replace_rule
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_occupancy_D125 import METRIC_ID, occupancy_evidence
from worksheet_screening_pilot_D120 import run_screening


CASE = ROOT / "templates/synthetic-workbook-screening-pilot-D125.json"
SERVICE = 12 * 150 * Fraction(1, 100) / (1 - Fraction(101, 100) ** -3)
INPUTS = {"Base": (1000, 200, 50, Fraction(1, 10)), "Downside": (900, 250, 30, Fraction(3, 25))}


def verify(temp, saved_output):
    raw = CASE.read_bytes()
    case = json.loads(raw)
    primary, page = audit(CASE, BOOKS["Base"], BOOKS["Downside"], saved_output or temp / "primary")
    check_cash_and_metrics(primary)
    screening = primary["screening"]
    scenarios = primary["scenarios"]
    evidence = screening["occupancy_by_scenario"]
    require(primary["simulation_result"] == "FAIL" and len(screening["comparisons"]) == 20
            and len(screening["reference_metric_sources"]) == 4
            and "Base 87,32% (FAIL) | Downside 103,94% (FAIL, inviable)" in page,
            "The annual service did not produce the expected occupancy comparisons")
    for name, (rent, costs, tax, coefficient) in INPUTS.items():
        row = evidence[name]
        debt = scenarios[name]["annual_sizing_service"]
        crossing = (costs + SERVICE + max(tax, coefficient * SERVICE)) / rent
        require(amount(debt["amount"]) == SERVICE and amount(debt["regular_payment"]) * 12 == SERVICE
                and row["annual_sizing_service"] == debt and row["case_sha256"] == sha(raw)
                and row["debt_pointer"] == f"/scenarios/{name}/annual_sizing_service"
                and amount(row["algebraic_crossing"]) == crossing
                and all(point["covers_debt_service"] == (amount(point["occupancy"]) >= crossing)
                        for point in row["evaluated_points"]),
                f"{name} did not use the same verified loan or rent and cost inputs")
    require(evidence["Downside"]["minimum_occupancy"] is None
            and evidence["Downside"]["state"] == "infeasible_within_domain"
            and not any(point["covers_debt_service"] for point in evidence["Downside"]["evaluated_points"]),
            "A crossing above full occupancy was treated as feasible")

    def screen(spec):
        return run_screening(spec, scenarios, scenarios["Base"]["context"], extended=True, interval_irr=True,
                             yield_metrics=True, case_sha256=sha(encoded(spec)))

    stronger_rent = deepcopy(case)
    for name, rent in (("Base", 1100), ("Downside", 1200)):
        stronger_rent["occupancy_inputs"][name]["profile"]["rent_at_full_occupancy"] = rational(Fraction(rent))
    for metric, minimum in (("YoC", Fraction(3, 44)), ("spread", Fraction(-1850, 11))):
        stronger_rent = replace_rule(stronger_rent, metric, "Downside", pass_condition=condition(">=", minimum),
                                     fail_condition=condition("<", minimum))
    stronger_rent["criteria_revision"] = "SYNTHETIC-D125-compatible-r2"
    complete = screen(stronger_rent)
    require(complete["simulation_result"] == "PASS"
            and all(amount(row["minimum_occupancy"]) <= Fraction(17, 20) for row in complete["occupancy_by_scenario"].values()),
            "An independently feasible occupancy profile did not pass the supplied criteria")

    missing = deepcopy(case)
    missing["occupancy_inputs"]["Downside"]["profile"].pop("rent_at_full_occupancy")
    pending_case = temp / "missing-rent.json"
    pending_case.write_bytes(encoded(missing))
    pending, page = audit(pending_case, BOOKS["Base"], BOOKS["Downside"], temp / "pending")
    require(pending["simulation_result"] == "PENDING" and pending["scenarios"] == scenarios
            and "Downside PENDING" in page
            and "missing_or_outside_profile:rent_at_full_occupancy"
            in pending["screening"]["occupancy_by_scenario"]["Downside"]["blockers"],
            "A missing rent supplied an occupancy or discarded valid cash")
    for condition_value in (None, condition(">", Fraction(11, 10))):
        pending = screen(replace_rule(case, METRIC_ID, "Downside", fail_condition=condition_value))
        require(pending["simulation_result"] == "PENDING"
                and "breakeven_occupancy:Downside:fail_condition_rule_missing_or_unsupported" in pending["simulation_blockers"],
                "An absent or out-of-domain rule supplied a decision")

    group = case["occupancy_inputs"]["Downside"]
    operating = case["yield_inputs"]["Downside"]["stabilized_noi"]
    result = occupancy_evidence(group, operating, "Downside", scenarios["Downside"] | {"annual_sizing_service": None})
    require(result["algebraic_crossing"] is None and result["blockers"] == ["compatible_annual_debt_service_unavailable"],
            "Missing verified annual service supplied a zero or default")
    return dict(status="passed", decision="PENDING", metrics=10, calculated_metrics=8, full_workbook_cases=2,
                simulated=dict(PASS=1, FAIL=1, PENDING=1), page_count=1, pdf_sha256=primary["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited primary fixture.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d125-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
