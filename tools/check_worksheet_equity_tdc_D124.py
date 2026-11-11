"""Audit equity applied to the current TDC and its independent USD 10 cash ledger."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_equity_tdc_D71 import FIXTURE
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_screening_pilot_D120 import BOOKS, audit, check_cash_and_metrics, condition, replace_rule
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_equity_tdc_D124 import METRIC_ID, funding_evidence
from worksheet_screening_pilot_D120 import run_screening


CASE = ROOT / "templates/synthetic-workbook-screening-pilot-D124.json"
EXPECTED = {"Base": (400, 1000, Fraction(2, 5)), "Downside": (500, 1100, Fraction(5, 11))}


def check_variant(case, temp, label):
    path = temp / f"{label}.json"
    path.write_bytes(encoded(case))
    return audit(path, BOOKS["Base"], BOOKS["Downside"], temp / label)


def verify(temp, saved_output):
    case_raw = CASE.read_bytes()
    case = json.loads(case_raw)
    primary, page = audit(CASE, BOOKS["Base"], BOOKS["Downside"], saved_output or temp / "primary")
    check_cash_and_metrics(primary)
    scenarios = primary["scenarios"]
    screening = primary["screening"]
    budgets = screening["yield_by_scenario"]
    evidence = screening["equity_tdc_by_scenario"]
    comparisons = {(row["scenario_id"], row["metric_id"]): row for row in screening["comparisons"]}
    require(primary["simulation_result"] == "FAIL" and "Simulación PASS/FAIL  |  FAIL" in page
            and "Equity / TDC | Base 40,00% (PASS) | Downside 45,45% (PASS)" in page
            and len(comparisons) == len(screening["comparisons"]) == 20
            and len(screening["reference_metric_sources"]) == 6
            and {key for key, row in comparisons.items() if row["state"] == "FAIL_CONDITION"}
            == {("Downside", "YoC"), ("Downside", "spread")},
            "The applied equity metric or the other existing criteria were lost")
    origin = json.loads((ROOT / FIXTURE).read_bytes())["scenarios"]
    for name, (equity, tdc, ratio) in EXPECTED.items():
        row, budget = evidence[name], budgets[name]
        raw = case["funding_inputs"][name]["funding"]
        require(raw == origin[name] | {"context": budget["context"]}
                and amount(row["applied_funding"]["equity_paid"]) == equity
                and amount(row["applied_funding"]["debt_drawn"]) == 600
                and amount(row["debt_commitment"]) == 750
                and amount(row["tdc"]) == tdc and row["tdc"] == budget["tdc"]
                and row["tdc_source_sha256"] == budget["tdc_source_sha256"]
                and row["case_sha256"] == sha(case_raw)
                and row["funding_source_sha256"] == sha(encoded(raw))
                and row["workbook_sha256"] == sha(BOOKS[name].read_bytes())
                and row["cutoff"] == "2026-12-31"
                and row["source_pointer"] == f"/funding_inputs/{name}"
                and amount(row["equity_to_tdc"]) == ratio
                and amount(comparisons[name, METRIC_ID]["metric_record"]["value"]) == ratio,
                f"{name} did not use the dated applied equity and the same verified TDC")

    compatible = case
    for metric, threshold in (("YoC", Fraction(3, 44)), ("spread", Fraction(-1850, 11))):
        compatible = replace_rule(compatible, metric, "Downside", pass_condition=condition(">=", threshold),
                                  fail_condition=condition("<", threshold))
    compatible["criteria_revision"] = "SYNTHETIC-D124-compatible-r2"
    passed, _ = check_variant(compatible, temp, "pass")
    require(passed["simulation_result"] == "PASS" and passed["scenarios"] == scenarios,
            "The compatible synthetic criteria changed the available cash or missed PASS")

    limit = Fraction(45, 100)
    stricter = replace_rule(compatible, METRIC_ID, "Downside", pass_condition=condition("<=", limit),
                            fail_condition=condition(">", limit))
    stricter["criteria_revision"] = "SYNTHETIC-D124-stricter-equity-r3"
    failed, _ = check_variant(stricter, temp, "equity-fail")
    require(failed["simulation_result"] == "FAIL" and failed["scenarios"] == scenarios
            and {(row["scenario_id"], row["metric_id"]) for row in failed["screening"]["comparisons"]
                 if row["state"] == "FAIL_CONDITION"} == {("Downside", METRIC_ID)},
            "The stricter equity rule failed to isolate the effect on the simulation")

    no_equity = deepcopy(case)
    sources = no_equity["funding_inputs"]["Downside"]["funding"]["sources"]
    sources.remove(next(row for row in sources if row["kind"] == "equity_paid"))
    pending, pending_page = check_variant(no_equity, temp, "missing-equity")
    down = pending["screening"]["equity_tdc_by_scenario"]["Downside"]
    require(pending["simulation_result"] == "PENDING" and pending["scenarios"] == scenarios
            and "Equity / TDC | Base 40,00% (PASS) | Downside PENDING" in pending_page
            and down["equity_to_tdc"] is None and down["tdc"] == budgets["Downside"]["tdc"]
            and "explicit_debt_and_equity_amounts_required" in down["blockers"],
            "The pilot supplied a ratio without equity or discarded independent cash")

    missing_rule = replace_rule(case, METRIC_ID, "Downside", fail_condition=None)
    result = run_screening(missing_rule, scenarios, scenarios["Base"]["context"], extended=True, interval_irr=True,
                           yield_metrics=True, case_sha256=sha(encoded(missing_rule)))
    require(result["simulation_result"] == "PENDING"
            and "equity_TDC:Downside:fail_condition_rule_missing_or_unsupported" in result["simulation_blockers"],
            "A missing equity criterion supplied an implicit rule")

    funding, budget = case["funding_inputs"]["Base"], budgets["Base"]
    changed = deepcopy(funding)
    changed["funding"]["debt_commitment"] = rational(Fraction(900))
    require(funding_evidence(changed, budget)["equity_to_tdc"] == evidence["Base"]["equity_to_tdc"],
            "Unused commitment changed the ratio")
    changed["funding"]["sources"][0]["amount"] = rational(Fraction(601))
    for source, tdc, blocker in (
        (changed, budget, "applied_funding_does_not_reconcile_to_tdc"),
        (funding | {"tdc_source_sha256": budgets["Downside"]["tdc_source_sha256"]}, budget,
         "funding_tdc_revision_mismatch_or_missing"),
        (funding, budget | {"tdc": None}, "positive_complete_pilot_tdc_required"),
    ):
        result = funding_evidence(source, tdc)
        require(result["equity_to_tdc"] is None and blocker in result["blockers"],
                "Missing, stale or unreconciled funding acquired a ratio")
    return dict(status="passed", decision="PENDING", metrics=10, calculated_metrics=7, full_workbook_cases=4,
                simulated=dict(PASS=1, FAIL=2, PENDING=1), page_count=1, pdf_sha256=primary["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited primary fixture.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d124-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
