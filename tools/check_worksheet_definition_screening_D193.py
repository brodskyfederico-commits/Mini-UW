"""Replay B13–B16 for SRC-02 and SRC-03 using the document-backed synthetic pilot."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_worksheet_formula_review_D173 import pdf_text
from check_lorena_criteria_D192 import change_cells
from check_worksheet_integrated_screening_D181 import CASE as HISTORICAL, CURRENT as HISTORICAL_REVISION
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from check_worksheet_performance_policy_D184 import occupancy_checks, price_checks
from check_reference_package import require
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_worksheet_v1 import build_results, encoded, verify_package, write_package
from preview_lorena_criteria_D192 import preview
from worksheet_definition_screening_D193 import OCCUPANCY, PHYSICAL, RLV
from worksheet_documented_finance_D147 import review_documents
from worksheet_revision_D128 import snapshot_for_case


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "templates/synthetic-workbook-definition-screening-D193.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D193.json"
CRITERIA = ROOT / "templates/MiniUW_Criterios_PASS_FAIL_Lorena.xlsx"
LIMITS = {"Base": (3_200_000, 7_350_000), "Downside": (2_720_000, 4_140_000)}
ASKING = {"Base": 1_100_000, "Downside": 1_300_000}


def rows(result):
    return {(row["scenario_id"], row["metric_id"]): row for row in result["screening"]["comparisons"]}


def detail(result, name, metric):
    return result["screening"]["metric_evidence_by_scenario"][name]["candidate_definitions"][metric]


def approvals_unchanged(result):
    require(result["decision"] == "PENDING" and result["personal_investor_return"] is None
            and not result["real_decisions_enabled"] and not result["deployment_enabled"], "A real gate opened")


def verify(output):
    case_raw = CASE.read_bytes()
    case = json.loads(case_raw)
    revision = CURRENT.read_bytes()
    require(revision == encoded(snapshot_for_case(case, "SYNTHETIC-D193-current")), "Fixture revision drift")
    source = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())
    write_package(case_raw, output, current_revision_raw=revision, **source)
    verified = verify_package(output, current_revision_raw=revision)
    require(verified["vigencia"] == "VIGENTE" and verified["audit_bot"] == "B16", "B16 failed to replay from sources")
    model = json.loads((output / "results.json").read_bytes())
    report = (output / "MiniUW_Resumen.pdf").read_bytes()
    page = pdf_text(report)
    require(model["simulation_result"] == "PASS" and all(row["state"] == "PASS_CONDITION" for row in rows(model).values())
            and len(rows(model)) == 20 and "Dictamen simulado PASS" in page and "Decisión real PENDING" in page
            and "18,06" in page and "6,08" in page and "3200000" in page and "2720000" in page, "D193 report drift")
    approvals_unchanged(model)
    blank_preview = preview(CRITERIA.read_bytes(), model)
    require(blank_preview["decision"] == "PENDING" and all(row["state"] == "PENDING"
            for row in blank_preview["comparisons"]), "Blank Lorena criteria inherited synthetic rules")

    lorena = change_cells(CRITERIA.read_bytes(), {"E13": "<= 1 x", "F13": "> 1,2 x", "E11": "<= 75 %", "F11": "> 90 %"})
    preview_rows = {(row["scenario"], row["metric"]): row for row in preview(lorena, model)["comparisons"]}
    require(preview_rows["Base", OCCUPANCY]["state"] == "PASS_CONDITION"
            and preview_rows["Base", RLV]["state"] == "PENDING"
            and "SRC-03_ratio_rule_does_not_match_computed_price_band" in preview_rows["Base", RLV]["blockers"],
            "The criteria preview overrode a computed price boundary")

    documents = review_documents(case, source["plan_raw"], evidence_raw=source["evidence_raw"], evidence_milestone="D162")

    def cached(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(candidate["local_sources"] == case["local_sources"] and candidate["workbook_sha256"] == case["workbook_sha256"]
                and plan_raw == source["plan_raw"] and evidence_raw == source["evidence_raw"] and evidence_milestone == "D162",
                "A definition-only variant changed an audited document")
        return deepcopy(documents)

    with patch("worksheet_documented_finance_D147.review_documents", cached):
        historical, historical_pdf = build_results(HISTORICAL.read_bytes(), current_revision_raw=HISTORICAL_REVISION.read_bytes(), **source)
        require(historical_pdf == (ROOT / "docs/review/MiniUW_Informe_USD10_D181.pdf").read_bytes(),
                "D181 PDF changed after enabling v30")
        for name in ("Base", "Downside"):
            require(historical["scenarios"][name] == model["scenarios"][name], "A candidate definition changed project cash or debt")

        def run(edit, expected, *, older_revision=False):
            updated = deepcopy(case)
            edit(updated)
            current = revision if older_revision else encoded(snapshot_for_case(updated, "SYNTHETIC-D193-probe"))
            result, raw_pdf = build_results(encoded(updated), current_revision_raw=current, **source)
            approvals_unchanged(result)
            require(result["simulation_result"] == expected and f"Dictamen simulado {expected}" in pdf_text(raw_pdf),
                    "Simulation did not reach the expected state")
            for name, scenario in result["scenarios"].items():
                require(scenario["cash_per_usd_10"] == model["scenarios"][name]["cash_per_usd_10"],
                        "A criteria or definition change altered cash")
            return result

        def rule(updated, name, metric):
            return next(row for row in updated["rules"] if row["scenario_id"] == name and row["metric_id"] == metric)

        def set_limit(updated, name, metric, condition, threshold):
            rule(updated, name, metric)[condition]["threshold"] = rational(threshold)

        def configs(updated, name):
            return updated["rent_inputs"]["definition_screening"][name]

        def block_occupancy(updated):
            configs(updated, "Base")["occupancy"]["definition"] = PHYSICAL
            rule(updated, "Base", OCCUPANCY)["definition_ref"] = PHYSICAL

        physical = run(block_occupancy, "PENDING")
        require(detail(physical, "Base", OCCUPANCY)["blocker"] == "C14_sin_desglose"
                and rows(physical)["Downside", OCCUPANCY]["state"] == "PASS_CONDITION",
                "Missing physical components affected the other scenario")

        def supply_physical(updated):
            block_occupancy(updated)
            # The declared split reproduces Base's 93% effective realization.
            configs(updated, "Base")["occupancy"]["physical_breakdown"] = dict(
                source_ref="SYNTHETIC-D193-reconciled-split", physical_vacancy=rational(Fraction(1, 20)),
                credit_loss=rational(Fraction()), concessions=rational(Fraction(2, 95)))

        split = run(supply_physical, "PASS")
        require(amount(detail(split, "Base", OCCUPANCY)["value"]) * Fraction(93, 95)
                == amount(detail(model, "Base", OCCUPANCY)["value"]), "Physical occupancy differs from the split")

        def conflict_physical(updated):
            supply_physical(updated)
            configs(updated, "Base")["occupancy"]["physical_breakdown"]["concessions"] = rational(Fraction())

        conflicting = run(conflict_physical, "PENDING")
        require(detail(conflicting, "Base", OCCUPANCY)["blocker"] == "SRC-02_physical_breakdown_does_not_reconcile",
                "An inconsistent split produced a physical result")

        def occupancy_fail(updated):
            set_limit(updated, "Base", OCCUPANCY, "pass_condition", Fraction(1, 5))
            set_limit(updated, "Base", OCCUPANCY, "fail_condition", Fraction(3, 10))

        failed_occupancy = run(occupancy_fail, "FAIL")
        require(rows(failed_occupancy)["Base", OCCUPANCY]["state"] == "FAIL_CONDITION", "Ocupación did not drive FAIL")

        def land_rule_conflict(updated):
            set_limit(updated, "Downside", RLV, "fail_condition", Fraction(6, 5))

        conflict = run(land_rule_conflict, "PENDING")
        require("SRC-03_ratio_rule_does_not_match_computed_price_band" in rows(conflict)["Downside", RLV]["blockers"],
                "A manual threshold overrode the joint land price boundary")

        def land_band(updated):
            set_limit(updated, "Base", "equity_TDC", "pass_condition", Fraction(83, 100))
            set_limit(updated, "Base", "equity_TDC", "fail_condition", Fraction(85, 100))
            set_limit(updated, "Base", RLV, "fail_condition", Fraction(1_120_000, 640_000))

        band = run(land_band, "PENDING")
        require(rows(band)["Base", RLV]["state"] == "BAND"
                and detail(band, "Base", RLV)["calculation"]["before_fail"] == 1_120_000,
                "Asking between the two RLV boundaries did not stay PENDING")

        def limit_grid(updated):
            configs(updated, "Base")["rlv"]["grid"] = [-500_000, 3_500_000, 10_000]

        unbounded = run(limit_grid, "PENDING")
        land = detail(unbounded, "Base", RLV)
        require(land["blocker"] == "upper_bound_unresolved" and land["value"] is None
                and land["calculation"]["pass_price"] == LIMITS["Base"][0] and land["calculation"]["before_fail"] is None,
                "Incomplete RLV boundaries supplied a ratio")

        def make_unattainable(updated):
            set_limit(updated, "Base", "YoC", "pass_condition", Fraction(1))
            set_limit(updated, "Base", "YoC", "fail_condition", Fraction(9, 10))

        impossible = run(make_unattainable, "PENDING")
        land = detail(impossible, "Base", RLV)
        require(land["calculation"]["pass_price"] is None and land["blocker"] == "not_attainable_on_grid",
                "An unattainable RLV turned into zero")

        def missing_criterion(updated):
            updated["rules"].remove(rule(updated, "Base", "equity_TDC"))

        incomplete = run(missing_criterion, "PENDING")
        require(detail(incomplete, "Base", RLV)["blocker"] == "SRC-03_incompatible_or_missing_criterion:equity_TDC",
                "RLV assumed an absent criterion")
        stale = run(occupancy_fail, "PENDING", older_revision=True)
        require(not stale["screening"]["current_criteria_confirmed"]
                and all(row["criterion_locator"] is None for row in rows(stale).values()), "A stale criterion was compared")

    scenarios = {}
    for name, view in model["scenarios"].items():
        occ = detail(model, name, OCCUPANCY)
        eq = amount(occ["value"])
        inputs = occ["inputs"]
        slope, intercept = (amount(inputs[key]) for key in ("slope", "intercept"))
        floor, coefficient = (amount(inputs[key]) for key in ("floor", "tax_coefficient"))
        service, reserve = (amount(inputs[key]) for key in ("debt_service", "reserve"))

        def after_reserve(realized):
            net = slope * realized + intercept
            return min(net - floor, net / (1 + coefficient)) - reserve

        require(after_reserve(eq) == service and after_reserve(eq - Fraction(1, 10_000)) < service,
                "Independent check of break-even failed")
        land = detail(model, name, RLV)
        calculation = land["calculation"]
        passing, before_fail = LIMITS[name]
        require((calculation["pass_price"], calculation["before_fail"]) == (passing, before_fail)
                and amount(land["value"]) == Fraction(ASKING[name], passing)
                and calculation["pass_boundary"]["at"]["state"] == "PASS"
                and calculation["pass_boundary"]["above"]["state"] != "PASS"
                and calculation["before_fail_boundary"]["above"]["state"] == "FAIL", "Joint price boundaries did not reproduce")
        for boundary in ("pass_boundary", "before_fail_boundary"):
            point = calculation[boundary]["at"]
            source_price = amount(land["inputs"]["price"])
            c33 = amount(land["inputs"]["closing_rate"])
            require(amount(point["delta_tdc"]) == (point["price"] - source_price) * (1 + c33)
                    and point["debt"] == land["inputs"]["debt"], "Debt or C33 moved at the RLV boundary")
        cash = view["cash_per_usd_10"]
        scenarios[name] = dict(occupancy_percent=f"{float(eq * 100):.2f}", pass_price=passing, before_fail=before_fail,
                               ratio=f"{float(amount(land['value'])):.4f}", cash_per_usd_10={
                                   k: f"{float(amount(cash[k])):.2f}" for k in
                                   ("total_contributions", "total_distributions", "unrecovered_after_sale")
                               })
    occupancy_checks()
    price_checks()
    return dict(status="passed", decision="PENDING", simulation_result=model["simulation_result"],
                financial_definitions="candidate_synthetic", scenarios=scenarios, comparisons=20, variants=10,
                d184_edge_checks_replayed=True, older_pdf_reproduced=True, source_first_replayed=True,
                pdf_sha256=model["pdf_sha256"], pdf_pages=1, real_decisions_enabled=False, deployment_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d193-") as temporary:
        result = verify(args.output or Path(temporary) / "Expediente")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
