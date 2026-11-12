"""Verify a mixed progressive, sequential and Flate PDF through the financial OCR chain."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from PIL import Image
from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import events
from check_worksheet_construction_pdf_D157 import BOOKS, ORDER, PLAN, pages, run_package
from check_worksheet_evidence_jpeg_D161 import (
    CASE as PRIOR, CURRENT as PRIOR_CURRENT, DECODER, JPEG_ROLES, SCAN as PRIOR_SCAN, UPRIGHT, jpeg_bundle,
)
from check_worksheet_evidence_scan_D158 import variant_bundle
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_PROGRESSIVE_JPEG_EVIDENCE_SCHEMA, build_results, encoded
from worksheet_evidence_jpeg_D161 import PROGRESSIVE_PROFILE
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-evidence-progressive-D162.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D162.json"
SCAN = ROOT / "templates/synthetic-progressive-evidence-D162.pdf"
PROGRESSIVE = {"gc", "construction_base"}


def case_for(raw):
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_PROGRESSIVE_JPEG_EVIDENCE_SCHEMA
    case["local_sources"]["evidence_pdf"].update(profile=PROGRESSIVE_PROFILE, sha256=sha(raw))
    return case


def verify(temp, output):
    upright = UPRIGHT.read_bytes()
    raw = SCAN.read_bytes()
    case = case_for(raw)
    require(raw == jpeg_bundle(upright, progressive_roles=PROGRESSIVE) and encoded(case) == CASE.read_bytes(),
            "Progressive fixture drift")
    require(jpeg_bundle(upright) == PRIOR_SCAN.read_bytes(), "The archived sequential fixture changed")
    run_package(PRIOR, PRIOR_CURRENT, PRIOR_SCAN, temp / "D161")
    prior = json.loads((temp / "D161/results.json").read_bytes())
    status = run_package(CASE, CURRENT, SCAN, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["deployment_enabled"] and not result["real_decisions_enabled"]
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"],
            "Complete progressive evidence did not reach the calculation")
    bots = result["local_review"]["bots"]
    require(bots["B03"]["documents"]["evidence_pdf"]["jpeg_decoder"] == DECODER, "Decoder identity changed")
    budget = bots["B08"]
    reads = (budget["gc_pdf"], *budget["bank_pdf_by_scenario"].values(), *budget["construction_pdf_by_scenario"].values())
    pdf = PdfReader(SCAN, strict=True)
    for reading in reads:
        index = reading["page"] - 1
        role = ORDER[index]
        page = pdf.pages[index]
        require(not (page.extract_text() or "").strip() and reading["extraction_method"] == "ocr",
                "A financial page bypassed OCR")
        if role not in JPEG_ROLES:
            require("jpeg_encoding" not in reading and reading["source_image_filter"] == "/FlateDecode",
                    "A Flate page was classified as JPEG")
            continue
        data = page["/Resources"]["/XObject"]["/I"].get_data()
        with Image.open(BytesIO(data), formats=("JPEG",)) as image:
            progressive = bool(image.info.get("progressive"))
            require(progressive == (role in PROGRESSIVE), "The expected JPEG encoding was absent")
        require(reading["source_image_filter"] == "/DCTDecode" and reading["source_jpeg_sha256"] == sha(data)
                and reading["jpeg_encoding"] == ("progressive" if progressive else "sequential"),
                "The evidence did not preserve the JPEG encoding or bytes")
    for name, view in result["scenarios"].items():
        previous = prior["scenarios"][name]
        require(view["document_financial_binding"]["gc_quote"]["jpeg_encoding"] == "progressive"
                and view["capacity"]["maximum_principal_capacity"] == previous["capacity"]["maximum_principal_capacity"],
                "Quote provenance was lost or bank capacity changed")
        for kind in ("contribution", "distribution"):
            require(events(view["cash_per_usd_10"], kind) == events(previous["cash_per_usd_10"], kind),
                    "The JPEG encoding changed dated cash")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and (output / EVIDENCE_FILE).read_bytes() == raw and audit["pdf_sha256"] == status["pdf_sha256"],
            "B16 could not reproduce the original mixed PDF")
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()
    expected = pages(case)

    def pending(bundle, *, sequential=False):
        changed = json.loads(PRIOR.read_bytes()) if sequential else case_for(bundle)
        changed["local_sources"]["evidence_pdf"]["sha256"] = sha(bundle)
        snapshot = encoded(snapshot_for_case(changed, "SYNTHETIC-D162-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=snapshot, plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == view["simulation_result"] == "PENDING", "An unresolved progressive JPEG released a decision")
        return view

    missing_index = expected["construction_base"].index("C52 | annual_nominal_fraction | 0.08")
    blank = variant_bundle(upright, blank=("construction_base", missing_index))
    missing = pending(jpeg_bundle(blank, progressive_roles=PROGRESSIVE))
    loan = missing["local_review"]["bots"]["B08"]["construction_pdf_by_scenario"]["Base"]
    require(loan["jpeg_encoding"] == "progressive" and loan["blockers"]
            and not any(row["text"].startswith("C52 | ") for row in loan["ocr"]["cited_lines"])
            and missing["scenarios"]["Base"]["cash_per_usd_10"] is None
            and missing["scenarios"]["Downside"]["cash_per_usd_10"] is not None, "Missing progressive C52 released or changed cash")
    altered = [line.replace("2340000", "2340001") if line.startswith("Vertical Base | ") else line
               for line in expected["gc"]]
    conflict = pending(jpeg_bundle(upright, overlay=("gc", altered), progressive_roles=PROGRESSIVE))
    quote = conflict["local_review"]["bots"]["B08"]["gc_pdf"]
    require(quote["jpeg_encoding"] == "progressive" and quote["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(quote["readings"][method]["document"]["budget_by_scenario"]["Base"]["value"])
                 for method in ("ocr", "text")] == [2340000, 2340001]
            and all(row["cash_per_usd_10"] is None for row in conflict["scenarios"].values()),
            "Conflicting progressive evidence supplied a quote")
    damaged = pending(jpeg_bundle(upright, overlay=("construction_base", expected["construction_base"]),
                                  truncated="construction_base", progressive_roles=PROGRESSIVE))
    require("B08:Base:evidence_financial_scan_required_or_layout_unsupported" in damaged["local_review"]["blockers"]
            and damaged["scenarios"]["Base"]["cash_per_usd_10"] is None
            and damaged["scenarios"]["Downside"]["cash_per_usd_10"] is not None, "A truncated progressive image supplied terms")
    sequential = pending(jpeg_bundle(upright, overlay=("construction_base", expected["construction_base"]),
                                     progressive_roles={"construction_base"}), sequential=True)
    require("B08:Base:evidence_financial_scan_required_or_layout_unsupported" in sequential["local_review"]["blockers"]
            and sequential["scenarios"]["Base"]["cash_per_usd_10"] is None
            and sequential["scenarios"]["Downside"]["cash_per_usd_10"] is not None,
            "The archived sequential profile accepted a progressive page")
    return dict(status="passed", decision="PENDING", evidence_pages=6, jpeg_pages=3, progressive_pages=2,
                pending_cases=4, page_count=1, pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d162-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
