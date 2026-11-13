"""Verify financial OCR when progressive JPEGs are both rotated and cropped."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from PIL import Image
from pypdf import PdfReader, PdfWriter

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import events
from check_worksheet_construction_pdf_D157 import BOOKS, ORDER, PLAN, pages, run_package
from check_worksheet_evidence_jpeg_D161 import JPEG_ROLES, UPRIGHT, jpeg_bundle
from check_worksheet_evidence_oriented_D159 import ANGLES, MARGIN, pdf_crop_box
from check_worksheet_evidence_progressive_D162 import (
    CASE as PRIOR, CURRENT as PRIOR_CURRENT, SCAN as PRIOR_SCAN, PROGRESSIVE, case_for,
)
from check_worksheet_plan_overlay_D133 import add_text_overlay
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, build_results, encoded
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-evidence-progressive-crop-D163.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D163.json"
SCAN = ROOT / "templates/synthetic-progressive-crop-evidence-D163.pdf"


def variant_pdf(raw, role, *, crop=None, overlay=None):
    """Keep the original JPEG bytes and vary its PDF crop or text overlay."""
    writer = PdfWriter(clone_from=BytesIO(raw))
    page = writer.pages[ORDER.index(role)]
    if crop is not None:
        page.cropbox = pdf_crop_box(crop, ANGLES[role], int(page.mediabox.width), int(page.mediabox.height))
    if overlay is not None:
        add_text_overlay(writer, page, [(560 - 22 * index, line) for index, line in enumerate(overlay)])
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def same_cash(result, baseline, scenario):
    actual = result["scenarios"][scenario]
    previous = baseline["scenarios"][scenario]
    require(actual["capacity"]["maximum_principal_capacity"] == previous["capacity"]["maximum_principal_capacity"],
            f"{scenario} refinance capacity changed")
    for kind in ("contribution", "distribution"):
        require(events(actual["cash_per_usd_10"], kind) == events(previous["cash_per_usd_10"], kind),
                f"{scenario} dated {kind} changed")


def verify(temp, output):
    upright = UPRIGHT.read_bytes()
    raw = SCAN.read_bytes()
    case = case_for(raw)
    require(raw == jpeg_bundle(upright, progressive_roles=JPEG_ROLES, oriented=True, rgb_quality=98)
            and encoded(case) == CASE.read_bytes(), "Rotated progressive fixture drift")
    require(jpeg_bundle(upright, progressive_roles=PROGRESSIVE) == PRIOR_SCAN.read_bytes(),
            "The D162 archive changed")
    run_package(PRIOR, PRIOR_CURRENT, PRIOR_SCAN, temp / "D162")
    prior = json.loads((temp / "D162/results.json").read_bytes())
    status = run_package(CASE, CURRENT, SCAN, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["simulation_result"] == prior["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["deployment_enabled"] and not result["real_decisions_enabled"]
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"],
            "Visible rotated progressive evidence failed the synthetic gate")

    budget = result["local_review"]["bots"]["B08"]
    readings = {"gc": budget["gc_pdf"], "base": budget["bank_pdf_by_scenario"]["Base"],
                "construction_base": budget["construction_pdf_by_scenario"]["Base"]}
    pdf = PdfReader(SCAN, strict=True)
    for role, reading in readings.items():
        page = pdf.pages[ORDER.index(role)]
        image = page["/Resources"]["/XObject"]["/I"].get_data()
        with Image.open(BytesIO(image), formats=("JPEG",)) as decoded:
            require(decoded.info.get("progressive") and decoded.mode == JPEG_ROLES[role][0],
                    f"{role} was not encoded in the expected progressive format")
        require(not (page.extract_text() or "").strip() and reading["extraction_method"] == "ocr"
                and reading["source_image_filter"] == "/DCTDecode" and reading["jpeg_encoding"] == "progressive"
                and reading["source_jpeg_sha256"] == sha(image)
                and reading["page_rotation_clockwise"] == page.rotation == ANGLES[role]
                and reading["crop_region_in_oriented_scan"] == list(MARGIN)
                and reading["ocr_region_basis"] == "cropped_rotation_normalized_pixels"
                and reading["full_oriented_scan_sha256"] != reading["ocr_input_sha256"]
                and reading["ocr"]["cited_lines"], f"{role} did not preserve OCR geometry and provenance")
    for scenario in ("Base", "Downside"):
        same_cash(result, prior, scenario)
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and (output / EVIDENCE_FILE).read_bytes() == raw and audit["pdf_sha256"] == status["pdf_sha256"],
            "B16 did not reproduce the original rotated progressive PDF")

    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()
    expected = pages(case)

    def review(bundle, *, pending=True):
        changed = case_for(bundle)
        snapshot = encoded(snapshot_for_case(changed, "SYNTHETIC-D163-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=snapshot, plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == "PENDING" and view["simulation_result"] == ("PENDING" if pending else "FAIL"),
                "Unexpected decision after changing visible progressive evidence")
        return view, view["local_review"]["bots"]["B08"]

    def variant(role, *, pending=True, **changes):
        return review(variant_pdf(raw, role, **changes), pending=pending)

    matched, matched_budget = variant("base", pending=False, overlay=expected["base"])
    require(matched_budget["bank_pdf_by_scenario"]["Base"]["extraction_method"] == "text_and_ocr",
            "A matching overlay did not reconcile")
    for scenario in ("Base", "Downside"):
        same_cash(matched, prior, scenario)

    hidden, hidden_budget = variant("base", crop=(16, 18, 1800, 445), overlay=expected["base"])
    bank = hidden_budget["bank_pdf_by_scenario"]["Base"]
    require(bank["blockers"] == ["evidence_scan_crop_hides_or_changes_required_rows"]
            and bank["jpeg_encoding"] == "progressive" and "document" not in bank
            and not any(row["text"].startswith("C72 | ") for row in bank["ocr"]["cited_lines"])
            and hidden["scenarios"]["Base"]["cash_per_usd_10"] is None,
            "Hidden C72 reached the calculation from cropped pixels or overlay")
    same_cash(hidden, prior, "Downside")

    clipped, clipped_budget = variant("gc", crop=(16, 18, 1177, 1060), overlay=expected["gc"])
    quote = clipped_budget["gc_pdf"]
    require(quote["blockers"] == ["evidence_scan_crop_hides_or_changes_required_rows"] and "document" not in quote
            and quote["jpeg_encoding"] == "progressive"
            and all(row["cash_per_usd_10"] is None for row in clipped["scenarios"].values()),
            "A clipped quote reached financing")

    bank_lines = [line.replace("0.05", "0.06") if line.startswith("C69 | ") else line for line in expected["base"]]
    conflict, conflict_budget = variant("base", overlay=bank_lines)
    bank = conflict_budget["bank_pdf_by_scenario"]["Base"]
    require(bank["blockers"] == ["evidence_scan_and_text_disagree"] and bank["jpeg_encoding"] == "progressive"
            and [amount(bank["readings"][method]["document"]["annual_nominal_rate"]) for method in ("ocr", "text")]
                == [Fraction("0.05"), Fraction("0.06")]
            and conflict["scenarios"]["Base"]["cash_per_usd_10"] is None, "Conflicting bank terms supplied a rate")
    same_cash(conflict, prior, "Downside")

    quote_lines = [line.replace("2340000", "2340001") if line.startswith("Vertical Base | ") else line
                   for line in expected["gc"]]
    conflict, conflict_budget = variant("gc", overlay=quote_lines)
    quote = conflict_budget["gc_pdf"]
    require(quote["blockers"] == ["evidence_scan_and_text_disagree"] and quote["jpeg_encoding"] == "progressive"
            and [amount(quote["readings"][method]["document"]["budget_by_scenario"]["Base"]["value"])
                 for method in ("ocr", "text")] == [2340000, 2340001]
            and all(row["cash_per_usd_10"] is None for row in conflict["scenarios"].values()),
            "A conflicting quote supplied a budget")
    low_quality, _ = review(jpeg_bundle(upright, progressive_roles=JPEG_ROLES, oriented=True))
    require("B08:gc_budget:evidence_scan_ocr_confidence_below_declared_minimum" in low_quality["local_review"]["blockers"]
            and "B08:Base:evidence_scan_ocr_confidence_below_declared_minimum" in low_quality["local_review"]["blockers"]
            and all(row["cash_per_usd_10"] is None for row in low_quality["scenarios"].values()),
            "Low-confidence progressive JPEG released cash")

    return dict(status="passed", decision="PENDING", evidence_pages=6, progressive_pages=len(readings),
                rotation_angles=sorted(ANGLES[role] for role in readings), pending_cases=5,
                page_count=len(PdfReader(output / "MiniUW_Resumen.pdf").pages), pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d163-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
