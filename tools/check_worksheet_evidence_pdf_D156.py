"""Verify source-first replay and isolated failure from synthetic financial and official PDF evidence."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader, PdfWriter

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_alternatives_D155 import BOOKS, CASE as PRIOR, CURRENT as PRIOR_CURRENT, PLAN
from check_worksheet_construction_budget_D144 import events
from check_worksheet_rental_inputs_D140 import run
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import _pdf, _pdf_string
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_EVIDENCE_PDF_SCHEMA, build_results, encoded
from worksheet_evidence_pdf_D156 import PROFILE, SCOPE
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-evidence-pdf-D156.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D156.json"
EVIDENCE = ROOT / "templates/synthetic-evidence-bundle-D156.pdf"
PAGE_ORDER = ("official", "downside", "gc", "base")


def pages(case):
    local = case["local_sources"]
    meta = [f"Revision | {local['revision']}", f"Case ID | {case['rent_inputs']['deal_id']}"]
    gc = ["SYNTHETIC MINI-UW GC QUOTE", "Document ID | SYNTHETIC-D156-GC", *meta,
          f"Plan REF | {local['plan_pdf']['plan_ref']}", "Area | m2 | 1000",
          f"Vertical Base | {SCOPE} | USD | 2340000", f"Vertical Downside | {SCOPE} | USD | 2500000"]
    official = ["SYNTHETIC MINI-UW OFFICIAL COPY", "Document ID | SYNTHETIC-D156-PARCEL", *meta,
                "URL | https://municipio.example.invalid/archive/parcels", "Valid from | 2026-12-20",
                "Valid through | 2027-03-31", "Record | SYNTHETIC-PARCEL-01 | floors | 4"]

    def bank(name, rate, years, dscr):
        return [f"SYNTHETIC MINI-UW BANK TERMS {name.upper()}", f"Document ID | SYNTHETIC-D156-BANK-{name}", *meta,
                "Requested principal | USD | 1400000", f"C69 | annual_nominal_fraction | {rate}",
                f"C70 | years | {years}", "C71 | fraction | 0.65", f"C72 | multiple | {dscr}",
                "Payments per year | payments/year | 4", "Maturity | payments | 8",
                "Interest basis | nominal_annual_fixed_convertible_quarterly", "Payment timing | regular_in_arrears",
                "Capacity limits | LTV+DSCR"]

    return dict(gc=gc, official=official, base=bank("Base", "0.05", 20, "1.25"),
                downside=bank("Downside", "0.065", 11, "1.30"))


def evidence_pdf(pages_by_role, order=PAGE_ORDER):
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW D156 synthetic source bundle"})
    for role in order:
        commands = [f"BT /F1 10 Tf 1 0 0 1 28 {560 - 22 * index} Tm (".encode() + _pdf_string(line) + b") Tj ET"
                    for index, line in enumerate(pages_by_role[role])]
        writer.add_page(PdfReader(BytesIO(_pdf(commands)), strict=True).pages[0])
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def case_for(raw):
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_EVIDENCE_PDF_SCHEMA
    case["local_sources"].pop("documents")
    case["local_sources"]["evidence_pdf"] = dict(profile=PROFILE, sha256=sha(raw))
    return case


def verify(temp, output):
    source_pages = pages(json.loads(PRIOR.read_bytes()))
    raw = evidence_pdf(source_pages)
    case = case_for(raw)
    require(EVIDENCE.read_bytes() == raw and CASE.read_bytes() == encoded(case), "Evidence fixture drift")
    previous = run(PRIOR, BOOKS, PRIOR_CURRENT, temp / "D155", plan=PLAN)
    status = call("run", CASE, "--workbook", BOOKS["Base"], "--downside-workbook", BOOKS["Downside"],
                  "--current-revision", CURRENT, "--plan", PLAN, "--evidence", EVIDENCE, "--output", output)
    result = json.loads((output / "results.json").read_bytes())
    bots = result["local_review"]["bots"]
    require(result["decision"] == "PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"]
            and status["simulation_result"] == result["simulation_result"] == "FAIL"
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"],
            "The full evidence package did not run under the synthetic gates")
    require(bots["B03"]["documents"]["evidence_pdf"]["page_roles"] ==
            {"official_snapshot": 1, "bank_Downside": 2, "gc_budget": 3, "bank_Base": 4}
            and bots["B11"]["value"] == 4 and bots["B11"]["document_locator"] == "Evidence.pdf p. 1 / Record"
            and bots["B11"]["document_sha256"] == sha(raw) and amount(bots["B09"]["difference"]) == 0,
            "Classification, plan reconciliation or official provenance drifted")
    for name, page in (("Base", 4), ("Downside", 2)):
        view, prior = result["scenarios"][name], previous["scenarios"][name]
        quote = view["document_financial_binding"]["gc_quote"]
        bank = view["permanent_loan"]["bank_document_binding"]["quote"]
        require(quote["source_sha256"] == bank["source_sha256"] == sha(raw)
                and quote["page"] == 3 and bank["page"] == page
                and bank["locators"]["C72"] == f"Evidence.pdf p. {page} / C72"
                and amount(quote["value"]) == amount(view["development_costs"]["vertical_cost"])
                and view["permanent_loan"]["loan_source_sha256"] != prior["permanent_loan"]["loan_source_sha256"],
                "The PDF was not bound to the budget or loan calculation")
        for kind in ("contribution", "distribution"):
            require(events(view["cash_per_usd_10"], kind) == events(prior["cash_per_usd_10"], kind),
                    "Changing representation of identical evidence changed cash")
        require(view["capacity"]["maximum_principal_capacity"] == prior["capacity"]["maximum_principal_capacity"],
                "Changing representation of identical bank terms changed capacity")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and (output / EVIDENCE_FILE).read_bytes() == raw
            and sha((output / "MiniUW_Resumen.pdf").read_bytes()) == status["pdf_sha256"], "B16 replay failed")
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()

    def variant(bundle, *, supplied=True, stale=False, patch=None):
        changed = case_for(bundle)
        if patch:
            patch(changed)
        revision = CURRENT.read_bytes() if stale else encoded(snapshot_for_case(changed, "SYNTHETIC-D156-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=revision, plan_raw=plan, evidence_raw=bundle if supplied else None)
        require(view["simulation_result"] == "PENDING" and view["decision"] == "PENDING", "Evidence failure did not gate the decision")
        return view

    def changed(role, old, new):
        modified = source_pages.copy()
        require(old in modified[role], "Unexpected original evidence row")
        modified[role] = [new if row == old else row for row in modified[role]]
        return evidence_pdf(modified)

    bank_conflict = variant(changed("downside", "C72 | multiple | 1.30", "C72 | multiple | 1.35"))
    require(bank_conflict["scenarios"]["Downside"]["bank_document_binding"]["fields"] == ["minimum_dscr"]
            and bank_conflict["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and bank_conflict["scenarios"]["Base"]["cash_per_usd_10"] is not None, "Bank mismatch changed the wrong scenario")
    gc_conflict = variant(changed("gc", f"Vertical Downside | {SCOPE} | USD | 2500000",
                                  f"Vertical Downside | {SCOPE} | USD | 2500001"))
    require("B09:model_vertical_cost_conflicts_with_gc_quote" in gc_conflict["scenarios"]["Downside"]["blockers"]
            and gc_conflict["scenarios"]["Base"]["cash_per_usd_10"] is not None, "A quote mismatch was adopted")
    expired = variant(changed("official", "Valid through | 2027-03-31", "Valid through | 2027-02-28"))
    require("B10:official_snapshot_date_missing_or_outside_validity" in expired["local_review"]["blockers"]
            and expired["scenarios"]["Base"]["cash_per_usd_10"] is not None, "Official date gate or cash isolation failed")
    missing = variant(raw, supplied=False)
    require("B03:evidence_pdf_missing" in missing["local_review"]["blockers"]
            and all(row["cash_per_usd_10"] is None for row in missing["scenarios"].values()), "Missing evidence fell back")
    duplicate = variant(evidence_pdf(source_pages, ("official", "downside", "gc", "gc")))
    require("B03:evidence_page_role_duplicate" in duplicate["local_review"]["blockers"], "Ambiguous role was accepted")
    missing_bank = variant(evidence_pdf(source_pages, ("official", "gc", "base")))
    require("B08:Downside:evidence_page_role_missing" in missing_bank["local_review"]["blockers"]
            and missing_bank["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and missing_bank["scenarios"]["Base"]["cash_per_usd_10"] is not None, "Missing bank page was not scoped")
    revised = variant(evidence_pdf(source_pages, tuple(reversed(PAGE_ORDER))), stale=True)
    require("plan_and_gc_documents_fingerprint_mismatch" in revised["revision_review"]["blockers"],
            "Reordered evidence was accepted by the previous revision")
    wrong_hash = variant(raw, patch=lambda case: case["local_sources"]["evidence_pdf"].update(sha256="0" * 64))
    require("B03:evidence_pdf_binding_unconfirmed" in wrong_hash["local_review"]["blockers"], "Wrong PDF hash was accepted")
    return dict(status="passed", decision="PENDING", evidence_pages=4, pending_cases=8, page_count=1,
                pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d156-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
