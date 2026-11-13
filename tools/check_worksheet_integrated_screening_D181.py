"""Verify the source-first one-page USD 10 report and integrated synthetic screening."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_operating_replay_D20 import ROOT, require
from check_worksheet_alternatives_D155 import workbook_values
from check_worksheet_blanks_and_zero_D171 import variant as workbook_variant
from check_worksheet_debt_yield_D178 import fixture as prior_fixture
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_worksheet_v1 import (WORKBOOK_INTEGRATED_SCREENING_SCHEMA, build_results, encoded, verify_package,
                                 write_package)
from worksheet_documented_finance_D147 import review_documents
from worksheet_integrated_screening_D181 import CAP_BASIS, METRICS, TDC_SCOPE, collect_metrics
from worksheet_native_mapping_D139 import mapping_catalog
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-integrated-screening-D181.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D181.json"
RECONCILIATION = ROOT / "docs/review/MiniUW_Cotejo_Independiente_D179.json"
DATES = {
    "Base": ("2028-09-30", "2028-12-30", "2028-10-01/2029-10-01"),
    "Downside": ("2029-03-30", "2029-06-30", "2029-04-01/2030-04-01"),
}
# Arbitrary, case-only comparison thresholds chosen to exercise both sides.
THRESHOLDS = {
    "equity_multiple": (">=", "<", 1),
    "equity_recovered": (">=", "<", Fraction(1, 4)),
    "equity_cash_in": ("<=", ">", 0),
    "YoC": (">=", "<", Fraction(8, 100)),
    "spread": (">=", "<", 0),
    "equity_TDC": ("<=", ">", Fraction(85, 100)),
    "post_refi_CoC": (">=", "<", Fraction(1, 20)),
    "IRR": (">=", "<", 0),
}


def fixture():
    case = prior_fixture()
    case.update(schema=WORKBOOK_INTEGRATED_SCREENING_SCHEMA, criteria_revision="SYNTHETIC-D181-investment-rules-v1",
                rules=[])
    case["rent_inputs"]["integrated_screening"] = {}
    for name, (refi, sale, annual) in DATES.items():
        case["rent_inputs"]["integrated_screening"][name] = dict(
            tdc_scope=dict(basis=TDC_SCOPE, source_ref=f"SYNTHETIC-D181-{name}-pre-refi-cost-inventory"),
            reference_cap=dict(basis=CAP_BASIS, value=rational(Fraction(7, 100)), period_ref=annual,
                               source_ref=f"SYNTHETIC-D181-{name}-comparable-cap-fixture"))
        periods = {
            "equity_multiple": f"2027-03-30/{sale}",
            "equity_recovered": refi, "equity_cash_in": refi, "equity_TDC": refi,
            "YoC": annual, "spread": annual, "post_refi_CoC": f"{refi}/{sale}", "IRR": f"2027-03-30/{sale}",
        }
        for metric, (op_pass, op_fail, threshold) in THRESHOLDS.items():
            unit, _, _, definition = METRICS[metric]
            case["rules"].append(dict(scenario_id=name, metric_id=metric, definition_ref=definition, unit=unit,
                                      period_ref=periods[metric],
                                      pass_condition=dict(operator=op_pass, threshold=rational(threshold)),
                                      fail_condition=dict(operator=op_fail, threshold=rational(threshold))))
    return case


def checks(result):
    by_key = {(row["scenario_id"], row["metric_id"]): row for row in result["screening"]["comparisons"]}
    require(len(by_key) == 20, "Every investment metric and scenario needs a disposition")
    require(result["decision"] == "PENDING" and result["simulation_result"] == "PENDING"
            and result["personal_investor_return"] is None
            and not result["real_decisions_enabled"] and not result["deployment_enabled"], "Unexpected decision")
    return by_key


def check_oracle(result):
    oracle = json.loads(RECONCILIATION.read_bytes())
    rows = checks(result)
    for name, expected in oracle["scenarios"].items():
        cash = result["scenarios"][name]["cash_per_usd_10"]
        require(amount(cash["reference_amount"]) == 10, "USD 10 initial basis changed")
        for key, source in (("total_distributions", "total_receipts"), ("total_contributions", "total_contributions"),
                            ("equity_multiple", "multiple")):
            require(abs(amount(cash[key]) - Fraction(expected[source])) <= Fraction(1, 100_000_000),
                    f"{name} {key} differs from the independent replay")
        enclosure = rows[name, "IRR"]["metric_record"]["annual_enclosure"]
        irr = Fraction(expected["irr_percent"]) / 100
        require(amount(enclosure["lower"], 1300) <= irr <= amount(enclosure["upper"], 1300),
                f"{name} independent TIR is outside the enclosure")
        expected_tdc, expected_equity, expected_noi = {
            "Base": (4_203_090, 3_568_090, Fraction(493_254_361, 1120)),
            "Downside": (5_051_442, 4_365_442, Fraction(1_210_746_467, 4800)),
        }[name]
        yoc = expected_noi / expected_tdc
        for metric, value in (("YoC", yoc), ("spread", (yoc - Fraction(7, 100)) * 10_000),
                              ("equity_TDC", Fraction(expected_equity, expected_tdc)), ("equity_cash_in", 0)):
            require(amount(rows[name, metric]["metric_record"]["value"]) == value, f"{name} {metric} changed")
        for metric in THRESHOLDS:
            expected_state = "PASS_CONDITION" if name == "Base" or metric == "equity_cash_in" else "FAIL_CONDITION"
            require(rows[name, metric]["state"] == expected_state and rows[name, metric]["criterion_locator"],
                    f"{name} {metric} did not use its fixture criterion")
        for metric in ("breakeven_occupancy", "asking_relative_to_supported_price"):
            require(rows[name, metric]["state"] == "PENDING" and rows[name, metric]["metric_record"]["value"] is None,
                    f"{name} unresolved definition received a value")
    return rows


def pending_pdf(raw, *expected, absent=()):
    report = pdf_text(raw)
    for line in ("USD 10", "Dictamen simulado PENDING", "Decisión real PENDING", *expected):
        require(line in report, f"Pending PDF lost {line}")
    require(all(line not in report for line in absent), "Pending PDF exposed unavailable cash")


def verify(output):
    case = fixture()
    snapshot = encoded(snapshot_for_case(case, "SYNTHETIC-D181-current"))
    require(CASE.read_bytes() == encoded(case) and CURRENT.read_bytes() == snapshot, "D181 fixture drift")
    plan, raw = PLAN.read_bytes(), shuffled_pdf()
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    sources = dict(workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                   plan_raw=plan, evidence_raw=raw)
    write_package(encoded(case), output, current_revision_raw=snapshot, **sources)
    status = verify_package(output, current_revision_raw=snapshot)
    require(status["vigencia"] == "VIGENTE", "The package is not on the designated revision")
    result = json.loads((output / "results.json").read_bytes())
    rows = check_oracle(result)
    pdf_raw = (output / "MiniUW_Resumen.pdf").read_bytes()
    pending_pdf(pdf_raw)
    require(pdf_raw == (ROOT / "docs/review/MiniUW_Informe_USD10_D181.pdf").read_bytes(), "Published D181 PDF changed")
    pdf = pdf_text(pdf_raw)
    for label in ("18,06", "6,08", "12,11", "TIR anual", "2028-12-30", "2029-06-30",
                  "Capital remanente 2,62", "Capital remanente 3,54", "inmueble 13,48", "inmueble 3,31",
                  "USD 0,00 [PASS] / USD 0,00 [PASS]", "SRC-02", "SRC-03", "Retorno personal LP/GP PENDING"):
        require(label in pdf, f"The one-page PDF lost {label}")

    # Probe the project-USD direction with a nonzero closing contribution.
    cash_in_view = deepcopy(result["scenarios"]["Base"])
    cash_in_view["construction_refinance"]["projected_cash_in_required"] = rational(120_000)
    cash_in_view["cash_per_usd_10"]["events"].insert(-3, dict(
        date=DATES["Base"][0], category="refinance_cash_in", kind="contribution", amount=rational(Fraction(1, 2))))
    cash_in_view["cash_per_usd_10"]["total_contributions"] = rational(Fraction(356809, 24000) + Fraction(1, 2))
    records, _, _ = collect_metrics("Base", cash_in_view, case["rent_inputs"]["integrated_screening"]["Base"])
    require(amount(records["equity_cash_in"]["value"]) == 120_000, "Nonzero cash-in did not reconcile to project USD")

    documents = review_documents(case, plan, evidence_raw=raw, evidence_milestone="D162")

    def cached_documents(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(candidate["workbook_sha256"] == case["workbook_sha256"]
                and candidate["local_sources"] == case["local_sources"]
                and plan_raw == plan and evidence_raw == raw and evidence_milestone == "D162",
                "A probe modified the audited documents or their sources")
        return deepcopy(documents)

    def probe(edit, *, stale=False, pdf_expected=(), pdf_absent=()):
        updated = deepcopy(case)
        edit(updated)
        revision = snapshot if stale else encoded(snapshot_for_case(updated, "SYNTHETIC-D181-probe"))
        with patch("worksheet_documented_finance_D147.review_documents", side_effect=cached_documents):
            payload, rendered = build_results(encoded(updated), current_revision_raw=revision, **sources)
        pending_pdf(rendered, *pdf_expected, absent=pdf_absent)
        return payload, checks(payload)

    def remove_cap(updated):
        updated["rent_inputs"]["integrated_screening"]["Downside"].pop("reference_cap")

    pending, missing = probe(remove_cap, pdf_expected=("347,81 pb [PASS] / — [PENDING]", "Cobro total 6,08"))
    require(missing["Downside", "spread"]["state"] == "PENDING" and
            missing["Downside", "YoC"] == rows["Downside", "YoC"] and missing["Base", "spread"] == rows["Base", "spread"]
            and pending["scenarios"]["Downside"]["cash_per_usd_10"] == result["scenarios"]["Downside"]["cash_per_usd_10"],
            "A missing comparable cap changed an unrelated metric or cash")

    def remove_tdc_scope(updated):
        updated["rent_inputs"]["integrated_screening"]["Base"].pop("tdc_scope")

    _, missing = probe(remove_tdc_scope, pdf_expected=("Yield on Cost  ·  — [PENDING]", "Cobro total 18,06"))
    require(all(missing["Base", metric]["state"] == "PENDING" for metric in ("YoC", "spread", "equity_TDC"))
            and missing["Downside", "YoC"] == rows["Downside", "YoC"], "A missing cost scope produced ratios")

    def remove_criterion(updated):
        rule = updated["rules"][0]
        require(rule["metric_id"] == "equity_multiple" and rule["scenario_id"] == "Base", "Probe rule moved")
        rule.pop("pass_condition")

    pending, missing = probe(remove_criterion, pdf_expected=("1,21× [PENDING] / 0,33× [FAIL]", "Cobro total 18,06"))
    require(missing["Base", "equity_multiple"]["state"] == "PENDING"
            and pending["scenarios"]["Base"]["cash_per_usd_10"] == result["scenarios"]["Base"]["cash_per_usd_10"],
            "A missing condition acquired a comparison or changed verified cash")
    _, missing = probe(lambda updated: updated.pop("rules"), pdf_expected=("1,21× [PENDING] / 0,33× [PENDING]",))
    require(all(row["state"] == "PENDING" for row in missing.values()), "An absent inventory yielded comparisons")

    def update_downside(updated):
        rule = next(row for row in updated["rules"] if (row["scenario_id"], row["metric_id"]) == ("Downside", "YoC"))
        for condition in ("pass_condition", "fail_condition"):
            rule[condition]["threshold"] = rational(Fraction(4, 100))

    changed, revised = probe(update_downside)
    require(revised["Downside", "YoC"]["state"] == "PASS_CONDITION"
            and revised["Base", "YoC"] == rows["Base", "YoC"]
            and changed["scenarios"]["Downside"]["cash_per_usd_10"] == result["scenarios"]["Downside"]["cash_per_usd_10"],
            "A criterion change affected another scenario or a cash flow")
    stale, historical = probe(update_downside, stale=True, pdf_expected=("PENDING por vigencia",))
    require("investment_rules_fingerprint_mismatch" in stale["revision_review"]["blockers"]
            and all(row["state"] == "PENDING" for row in historical.values()), "Stale criteria were compared")

    def insert_band(updated):
        updated["rules"][0]["pass_condition"]["threshold"] = rational(Fraction(5, 4))

    banded, band = probe(insert_band, pdf_expected=("PENDING por banda",))
    require(band["Base", "equity_multiple"]["state"] == "BAND"
            and banded["screening"]["professional_review_needed_for_band"], "A band failed to require professional review")

    def block_capacity(updated):
        updated["rent_inputs"]["bank_debt_yield"]["Downside"]["minimum"] = rational(Fraction(1, 2))

    blocked, comparisons = probe(block_capacity, pdf_expected=("Downside | Caja PENDING", "Cobro total 18,06"),
                                 pdf_absent=("Cobro total 6,08", "Aporte extra 8,19"))
    require(blocked["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and blocked["scenarios"]["Base"]["cash_per_usd_10"] == result["scenarios"]["Base"]["cash_per_usd_10"]
            and all(comparisons["Downside", metric]["state"] == "PENDING" for metric in METRICS),
            "Blocked capacity leaked a Downside comparison or cash flow")
    # Remove a required DSCR value in the actual versioned Downside workbook.
    values = {"Downside": workbook_values("Downside", mapping_catalog())}
    missing_cell, modified_books = workbook_variant(case, books, values, "Downside", "C72", {})
    missing_cell["rent_inputs"]["supplemental_scope"]["Downside"]["downside_scope"].update(
        downside_workbook_sha256=missing_cell["workbook_sha256"]["Downside"])
    blank_revision = encoded(snapshot_for_case(missing_cell, "SYNTHETIC-D181-missing-C72"))
    blank, blank_pdf = build_results(encoded(missing_cell), current_revision_raw=blank_revision,
                                     **(sources | {"downside_workbook_raw": modified_books["Downside"]}))
    blank_comparisons = checks(blank)
    mapping = blank["native_mapping_review"]["scenarios"]["Downside"]
    field = next(row for row in mapping["rows"] if row["field_id"] == "INPUT_C72")
    require(field["state"] == "PENDING" and field["value"] is None
            and "confirmed_field_value_missing" in field["blockers"]
            and blank["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and blank["scenarios"]["Base"]["cash_per_usd_10"] == result["scenarios"]["Base"]["cash_per_usd_10"]
            and all(blank_comparisons["Downside", metric]["state"] == "PENDING" for metric in METRICS),
            "A blank C72 produced a zero, a comparison, or a Downside cash flow")
    pending_pdf(blank_pdf, "Downside | Caja PENDING", "Cobro total 18,06",
                absent=("Cobro total 6,08", "Aporte extra 8,19"))
    return dict(status="passed", comparison_rows=len(rows), calculated_per_scenario=len(THRESHOLDS),
                probes=10, missing_workbook_cell="Downside!C72", pending_pdf_verified=True,
                published_pdf_reproduced=True, decision="PENDING", simulation_result="PENDING", page_count=1,
                pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d181-") as folder:
        print(json.dumps(verify(args.output or Path(folder) / "D181"), sort_keys=True))


if __name__ == "__main__":
    main()
