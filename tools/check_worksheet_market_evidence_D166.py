"""Verify the market, insurance and bank gates through the integrated pilot."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_pdf_D157 import BOOKS, PLAN, pages, run_package
from check_worksheet_evidence_progressive_order_D164 import case_for, same_cash, shuffled_pdf, variant_pdf
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_MARKET_EVIDENCE_SCHEMA, build_results, encoded
from worksheet_market_evidence_D166 import SCHEMA
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-market-evidence-D166.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D166.json"


def fixture(raw):
    case = case_for(raw)
    case["schema"] = WORKBOOK_MARKET_EVIDENCE_SCHEMA
    inputs = case["rent_inputs"]
    ranges = {
        "Base": {"C8": ("1150", "1250"), "C9": ("1450", "1550"), "C10": ("1800", "1950"), "C11": ("2300", "2500"),
                 "C15": ("0", "0.025"), "C47": ("3", "4"), "C67": ("0.08", "0.095")},
        "Downside": {"C8": ("1050", "1150"), "C9": ("1300", "1400"), "C10": ("1600", "1750"), "C11": ("1900", "2100"),
                     "C15": ("0.04", "0.06"), "C47": ("5", "7"), "C67": ("0.10", "0.12")},
    }
    specs = {
        "rent": ("USD_per_unit_per_month", "gross_before_losses_and_concessions", ("C8", "C9", "C10", "C11")),
        "concessions": ("fraction", inputs["policy"]["concession_basis"], ("C15",)),
        "absorption": ("months", "tco_to_stabilization", ("C47",)),
        "exit_cap": ("annual_cap_fraction", "forward_twelve_month_noi_divided_by_exit_cap", ("C67",)),
    }
    scenarios = {}
    for name, premium in (("Base", 300), ("Downside", 550)):
        records = {}
        for role, (unit, basis, cells) in specs.items():
            records[role] = dict(unit=unit, basis=basis, ranges={
                cell: dict(minimum=rational(Fraction(ranges[name][cell][0])), maximum=rational(Fraction(ranges[name][cell][1])))
                for cell in cells})
        records["insurance"] = dict(unit="USD_per_insured_unit_per_year", basis="residential_insurance",
                                    premium_per_insured_unit=rational(Fraction(premium)), insured_units=26,
                                    coverage_ref=f"SYNTHETIC-D148-{name}-insured-unit-schedule")
        for role, record in records.items():
            record.update(scenario=name, deal_id=inputs["deal_id"], source_ref=f"SYNTHETIC-D166-{name}-{role}",
                          observed_on="2027-02-10", valid_through="2027-03-31")
        scenarios[name] = {role: dict(document=record, sha256=sha(encoded(record))) for role, record in records.items()}
    inputs["market_evidence"] = dict(schema=SCHEMA, scenarios=scenarios)
    return case


def verify(temp, output):
    raw = shuffled_pdf()
    case = fixture(raw)
    require(CASE.read_bytes() == encoded(case)
            and CURRENT.read_bytes() == encoded(snapshot_for_case(case, "SYNTHETIC-D166-current")), "Market fixture drift")
    evidence = temp / EVIDENCE_FILE
    evidence.write_bytes(raw)
    status = run_package(CASE, CURRENT, evidence, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["decision"] == "PENDING" and result["simulation_result"] == "FAIL"
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"]
            and not result["deployment_enabled"] and not result["real_decisions_enabled"],
            "Complete evidence did not reach the synthetic calculation")
    prior = case_for(raw)
    prior_file = temp / "case.json"
    prior_file.write_bytes(encoded(prior))
    revision = temp / "revision.json"
    revision.write_bytes(encoded(snapshot_for_case(prior, "SYNTHETIC-D166-before-gate")))
    run_package(prior_file, revision, evidence, temp / "previous")
    before = json.loads((temp / "previous/results.json").read_bytes())
    for name, view in result["scenarios"].items():
        same_cash(result, before, name)
        market = view["market_insurance_review"]
        require(market["state"] == "checked_synthetic" and set(market["records"]) ==
                {"rent", "absorption", "concessions", "exit_cap", "insurance"}
                and all(record["observed_sha256"] == record["declared_sha256"] for record in market["records"].values()),
                "Verified market records or provenance are absent")
        require(view["permanent_loan"]["bank_document_binding"]["quote"]["extraction_method"] == "ocr"
                and view["construction_financing"]["bank_document_binding"]["quote"]["extraction_method"] == "ocr",
                "Bank terms bypassed the document check")
    stages = {stage["dot"]: stage for stage in result["pipeline"]["stages"]}
    require(stages["D03"]["bots"] == ["B05", "B06", "B07", "B08", "B09"]
            and stages["D03"]["market_insurance_by_scenario"] == dict.fromkeys(("Base", "Downside"), "checked_synthetic")
            and "B08" not in stages["D05"]["bots"] and stages["D07"]["bots"] == ["B16"]
            and result["pipeline"]["version_tests"]["bot"] == "B17", "Runtime evidence differs from the reviewed flow")
    alternatives = result["alternative_evaluation"]["slots"]
    require(alternatives["C80"]["Base"]["state"] == "computed_synthetic"
            and alternatives["C80"]["Downside"]["state"] == "computed_synthetic", "Supported alternative was blocked")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["pdf_sha256"] == status["pdf_sha256"],
            "The saved market evidence could not be audited")

    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()

    def replay(changed, evidence_raw=raw):
        snapshot = snapshot_for_case(changed, "SYNTHETIC-D166-variant")
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=encoded(snapshot), plan_raw=plan, evidence_raw=evidence_raw)
        require(view["decision"] == "PENDING", "An unresolved case released a real decision")
        return view

    def records(changed, name):
        return changed["rent_inputs"]["market_evidence"]["scenarios"][name]

    def edit_record(changed, name, role, **changes):
        envelope = records(changed, name)[role]
        envelope["document"].update(changes)
        envelope["sha256"] = sha(encoded(envelope["document"]))

    def blocked(view, name, reason):
        other = "Downside" if name == "Base" else "Base"
        row = view["scenarios"][name]
        require(view["simulation_result"] == "PENDING" and reason in row["blockers"]
                and row["cash_per_usd_10"] is None and row["capacity"] is None and not row["noi_by_period"],
                f"{name}: the expected gate did not fire before the calculation: {reason}")
        same_cash(view, before, other)

    missing = deepcopy(case)
    del records(missing, "Base")["absorption"]
    blocked(replay(missing), "Base", "B08:market_evidence_missing:absorption")

    inconsistent = deepcopy(case)
    edit_record(inconsistent, "Downside", "insurance", premium_per_insured_unit=rational(Fraction(551)))
    edit_record(inconsistent, "Downside", "concessions", valid_through="2027-02-28")
    rent = deepcopy(records(inconsistent, "Downside")["rent"]["document"]["ranges"])
    rent["C8"]["minimum"] = rational(Fraction(1101))
    edit_record(inconsistent, "Downside", "rent", ranges=rent)
    view = replay(inconsistent)
    for reason in ("B08:insurance_quote_disagrees:C59", "B08:market_evidence_outside_validity:concessions",
                   "B08:market_assumption_outside_evidence:C8"):
        blocked(view, "Downside", reason)

    bad_unit = deepcopy(case)
    edit_record(bad_unit, "Base", "exit_cap", unit="percentage_points")
    blocked(replay(bad_unit), "Base", "B08:market_evidence_scope_mismatch:exit_cap")

    unverified = deepcopy(case)
    records(unverified, "Downside")["insurance"]["document"]["source_ref"] = "SYNTHETIC-unsigned-change"
    blocked(replay(unverified), "Downside", "B08:market_evidence_binding_unconfirmed:insurance")

    narrowed = deepcopy(case)
    edit_record(narrowed, "Base", "exit_cap", ranges={"C67": dict(minimum=rational(Fraction("0.085")),
                                                                maximum=rational(Fraction("0.095")))})
    view = replay(narrowed)
    same_cash(view, before, "Base")
    same_cash(view, before, "Downside")
    alternative = view["alternative_evaluation"]["slots"]["C80"]["Base"]
    require(view["simulation_result"] == "FAIL" and alternative["state"] == "PENDING"
            and alternative["cash_per_usd_10"] is None and "B08:market_assumption_outside_evidence:C67" in alternative["blockers"],
            "Unsupported alternative bypassed the gate or erased supported Base")

    terms = pages(case)["downside"]
    revised_lines = [line.replace("0.065", "0.066") if line.startswith("C69 | ") else line for line in terms]
    # A conflicting text reading keeps the original scan and both observations.
    bank_pdf = variant_pdf(raw, "downside", overlay=revised_lines)
    changed = deepcopy(case)
    changed["local_sources"]["evidence_pdf"]["sha256"] = sha(bank_pdf)
    blocked(replay(changed, bank_pdf), "Downside", "B08:evidence_scan_and_text_disagree")

    mismatched_terms = deepcopy(case)
    mismatched_terms["rent_inputs"]["permanent_loan"]["scenarios"]["Downside"]["maturity_payments"] = 9
    view = replay(mismatched_terms)
    blocked(view, "Downside", "B08:bank_pdf_and_worksheet_terms_disagree")
    require(view["scenarios"]["Downside"]["bank_document_binding"]["fields"] == ["maturity_payments"],
            "The bank discrepancy did not retain the conflicting field")

    return dict(status="passed", decision="PENDING", pending_cases=7,
                page_count=len(PdfReader(output / "MiniUW_Resumen.pdf").pages), pdf_sha256=status["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d166-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
