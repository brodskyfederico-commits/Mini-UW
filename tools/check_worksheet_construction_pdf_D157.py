"""Verify construction credit PDF evidence from B08 through T68, B13 and B16."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import events
from check_worksheet_evidence_pdf_D156 import (
    BOOKS, CURRENT as PRIOR_CURRENT, CASE as PRIOR, EVIDENCE as PRIOR_EVIDENCE, PLAN,
    evidence_pdf, pages as prior_pages,
)
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_CONSTRUCTION_PDF_SCHEMA, build_results, encoded
from worksheet_evidence_pdf_D156 import CONSTRUCTION_CONVENTIONS, CONSTRUCTION_PROFILE
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-construction-pdf-D157.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D157.json"
EVIDENCE = ROOT / "templates/synthetic-evidence-bundle-D157.pdf"
ORDER = ("official", "construction_downside", "downside", "gc", "construction_base", "base")


def pages(case):
    local = case["local_sources"]
    records = prior_pages(case)
    for name, ltc, rate, fee, limit, available, maturity in (
            ("Base", "0.60", "0.08", "0.01", "1600000", "350000", "2028-12-30"),
            ("Downside", "0.50", "0.10", "0.015", "1250000", "380000", "2029-06-30")):
        records[f"construction_{name.lower()}"] = [
            f"SYNTHETIC MINI-UW CONSTRUCTION TERMS {name.upper()}", f"Document ID | SYNTHETIC-D157-{name}-CONSTRUCTION",
            f"Revision | {local['revision']}", f"Case ID | {case['rent_inputs']['deal_id']}",
            f"C51 | fraction | {ltc}", f"C52 | annual_nominal_fraction | {rate}", f"C53 | fraction_of_commitment | {fee}",
            f"Maximum commitment | USD | {limit}", "Requested invoice share | fraction | 0.25",
            f"Available per draw | USD | {available}", f"Maturity date | {maturity}",
            *(f"{key} | {value}" for key, value in CONSTRUCTION_CONVENTIONS.items())]
    return records


def case_for(raw):
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_CONSTRUCTION_PDF_SCHEMA
    case["local_sources"]["evidence_pdf"] = dict(profile=CONSTRUCTION_PROFILE, sha256=sha(raw))
    return case


def run_package(case, revision, evidence, output):
    return call("run", case, "--workbook", BOOKS["Base"], "--downside-workbook", BOOKS["Downside"], "--plan", PLAN,
                "--evidence", evidence, "--current-revision", revision, "--output", output)


def verify(temp, output):
    source_pages = pages(json.loads(PRIOR.read_bytes()))
    raw = evidence_pdf(source_pages, ORDER)
    require(raw == EVIDENCE.read_bytes() and encoded(case_for(raw)) == CASE.read_bytes(), "Evidence fixture drift")
    run_package(PRIOR, PRIOR_CURRENT, PRIOR_EVIDENCE, temp / "D156")
    prior = json.loads((temp / "D156/results.json").read_bytes())
    status = run_package(CASE, CURRENT, EVIDENCE, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["decision"] == "PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"]
            and result["simulation_result"] == "FAIL" and not result["local_review"]["blockers"],
            "The full construction PDF failed the synthetic gate")
    for name, page in (("Base", 5), ("Downside", 2)):
        current, before = result["scenarios"][name], prior["scenarios"][name]
        funding, previous = current["construction_financing"], before["construction_financing"]
        binding = funding["bank_document_binding"]
        quote = binding["quote"]
        require(binding["state"] == "checked_synthetic" and quote["page"] == page and quote["source_sha256"] == sha(raw)
                and quote["locators"]["C52"] == f"Evidence.pdf p. {page} / C52"
                and funding["terms_source_ref"] == f"sha256:{sha(encoded(binding))}#/quote"
                and funding["debt_source"]["nonrevolving_commitment_basis_ref"] == funding["terms_source_ref"]
                and funding["debt_run_sha256"] != previous["debt_run_sha256"]
                and funding["construction_principal_payoff"] == previous["construction_principal_payoff"],
                "Construction evidence did not propagate to the debt rollforward")
        for kind in ("contribution", "distribution"):
            require(events(current["cash_per_usd_10"], kind) == events(before["cash_per_usd_10"], kind),
                    "Identical financing conditions changed the dated cash")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and (output / EVIDENCE_FILE).read_bytes() == raw
            and len(PdfReader(output / "MiniUW_Resumen.pdf").pages) == 1, "B16 replay failed")
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()

    def variant(bundle, *, patch=None, stale=False):
        changed = case_for(bundle)
        if patch:
            patch(changed)
        revision = CURRENT.read_bytes() if stale else encoded(snapshot_for_case(changed, "SYNTHETIC-D157-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=revision, plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == view["simulation_result"] == "PENDING"
                and view["scenarios"]["Base"]["cash_per_usd_10"] is not None, "A construction variant escaped or blocked Base cash")
        return view

    def edited(old, new):
        modified = source_pages.copy()
        role = "construction_downside"
        require(old in modified[role], "Fixture edit row missing")
        modified[role] = [new if row == old else row for row in modified[role]]
        return evidence_pdf(modified, ORDER)

    for row, replacement, field in (
            ("C52 | annual_nominal_fraction | 0.10", "C52 | annual_nominal_fraction | 0.11", "annual_interest"),
            ("Maturity date | 2029-06-30", "Maturity date | 2029-03-30", "maturity_date")):
        conflict = variant(edited(row, replacement))["scenarios"]["Downside"]
        require(conflict["cash_per_usd_10"] is None and conflict["construction_financing"]["bank_document_binding"]["fields"] == [field],
                "Conflicting construction terms exported cash")
    missing = variant(evidence_pdf(source_pages, tuple(role for role in ORDER if role != "construction_downside")))
    require("B08:Downside:evidence_page_role_missing" in missing["local_review"]["blockers"]
            and missing["scenarios"]["Downside"]["cash_per_usd_10"] is None, "Missing page fell back to structured terms")

    def lower_commitment(case):
        case["rent_inputs"]["construction_financing"]["scenarios"]["Downside"]["maximum_commitment"] = rational(400000)

    lowered = variant(edited("Maximum commitment | USD | 1250000", "Maximum commitment | USD | 400000"),
                      patch=lower_commitment)["scenarios"]["Downside"]
    require(lowered["construction_financing"]["bank_document_binding"]["state"] == "checked_synthetic"
            and any(reason.endswith(":cumulative_gross_draws_exceed_nonrevolving_commitment") for reason in lowered["blockers"])
            and lowered["cash_per_usd_10"] is None, "Verified lower commitment did not block the draw")
    stale = variant(evidence_pdf(source_pages, tuple(reversed(ORDER))), stale=True)
    require("plan_and_gc_documents_fingerprint_mismatch" in stale["revision_review"]["blockers"],
            "A new bundle accepted the prior revision")
    return dict(status="passed", decision="PENDING", evidence_pages=6, pending_cases=5, page_count=1, pdf_sha256=status["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d157-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
