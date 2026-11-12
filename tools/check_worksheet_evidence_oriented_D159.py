"""Replay rotated and cropped financial scans without accepting hidden evidence."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import events
from check_worksheet_construction_pdf_D157 import BOOKS, ORDER, PLAN, pages, run_package
from check_worksheet_evidence_scan_D158 import CASE as PRIOR, CURRENT as PRIOR_CURRENT, SCAN as PRIOR_SCAN, add_scan
from check_worksheet_plan_overlay_D133 import add_text_overlay
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_ORIENTED_EVIDENCE_SCHEMA, build_results, encoded
from worksheet_evidence_scan_D158 import ORIENTED_PROFILE
from worksheet_plan_overlay_D133 import rotate_scan
from worksheet_plan_scan_D131 import full_page_image
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-evidence-oriented-D159.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D159.json"
SCAN = ROOT / "templates/synthetic-oriented-evidence-D159.pdf"
ANGLES = {"construction_downside": 270, "downside": 180, "gc": 90, "construction_base": 180, "base": 270}
MARGIN = (16, 18, 1800, 1060)


def pdf_crop_box(region, rotation, width, height):
    x0, y0, x1, y1 = region
    if rotation == 90:
        x0, y0, x1, y1 = y0, height - x1, y1, height - x0
    elif rotation == 180:
        x0, y0, x1, y1 = width - x1, height - y1, width - x0, height - y0
    elif rotation == 270:
        x0, y0, x1, y1 = width - y1, x0, width - y0, x1
    return RectangleObject((x0, height - y1, x1, height - y0))


def oriented_bundle(raw, *, crop=None, overlay=None, no_crop=None):
    reader = PdfReader(BytesIO(raw), strict=True)
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW D159 synthetic rotated and cropped financial scans"})
    for role, original in zip(ORDER, reader.pages, strict=True):
        if role == "official":
            writer.add_page(original)
            continue
        angle = ANGLES[role]
        stored = rotate_scan(full_page_image(original), 360 - angle)
        _, dimensions, _, pixels = stored.split(b"\n", 3)
        width, height = map(int, dimensions.split())
        page = add_scan(writer, width, height, pixels, page_size=(width, height))
        page.rotate(angle)
        if role != no_crop:
            region = crop[1] if crop is not None and role == crop[0] else MARGIN
            page.cropbox = pdf_crop_box(region, angle, width, height)
        if overlay and role == overlay[0]:
            add_text_overlay(writer, page, [(560 - 22 * index, line) for index, line in enumerate(overlay[1])])
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def case_for(raw):
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_ORIENTED_EVIDENCE_SCHEMA
    case["local_sources"]["evidence_pdf"].update(profile=ORIENTED_PROFILE, sha256=sha(raw))
    return case


def verify(temp, output):
    original = PRIOR_SCAN.read_bytes()
    raw = oriented_bundle(original)
    case = case_for(raw)
    require(SCAN.read_bytes() == raw and CASE.read_bytes() == encoded(case), "Fixture drift")
    run_package(PRIOR, PRIOR_CURRENT, PRIOR_SCAN, temp / "D158")
    prior = json.loads((temp / "D158/results.json").read_bytes())
    status = run_package(CASE, CURRENT, SCAN, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["real_decisions_enabled"] and not result["deployment_enabled"]
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"],
            "Visible financial evidence failed the synthetic gate")
    budget = result["local_review"]["bots"]["B08"]
    readings = [budget["gc_pdf"], *budget["bank_pdf_by_scenario"].values(), *budget["construction_pdf_by_scenario"].values()]
    upright = PdfReader(BytesIO(original), strict=True)
    for reading in readings:
        page = reading["page"]
        require(reading["page_rotation_clockwise"] == ANGLES[ORDER[page - 1]]
                and reading["crop_region_in_oriented_scan"] == list(MARGIN)
                and reading["full_oriented_scan_sha256"] == sha(full_page_image(upright.pages[page - 1]))
                and reading["ocr_region_basis"] == "cropped_rotation_normalized_pixels"
                and reading["raw_image_sha256"] != reading["full_oriented_scan_sha256"] != reading["ocr_input_sha256"],
                "Rotation, crop and cited image were not independently recorded")
    for name, view in result["scenarios"].items():
        quote = view["document_financial_binding"]["gc_quote"]
        require(quote["page_rotation_clockwise"] == 90 and quote["crop_region_in_oriented_scan"] == list(MARGIN)
                and quote["ocr_region_basis"] == "cropped_rotation_normalized_pixels"
                and view["capacity"]["maximum_principal_capacity"] == prior["scenarios"][name]["capacity"]["maximum_principal_capacity"],
                "GC geometry was lost or valid evidence changed capacity")
        for kind in ("contribution", "distribution"):
            require(events(view["cash_per_usd_10"], kind) == events(prior["scenarios"][name]["cash_per_usd_10"], kind),
                    "Valid crop changed dated cash")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and (output / EVIDENCE_FILE).read_bytes() == raw and audit["pdf_sha256"] == status["pdf_sha256"],
            "B16 did not replay the original evidence")
    workbooks = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()

    def variant(bundle, *, pending=True):
        changed = case_for(bundle)
        snapshot = encoded(snapshot_for_case(changed, "SYNTHETIC-D159-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=workbooks["Base"], downside_workbook_raw=workbooks["Downside"],
                                current_revision_raw=snapshot, plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == "PENDING" and view["simulation_result"] == ("PENDING" if pending else "FAIL"),
                "Wrong decision for the crop variant")
        return view

    lines = pages(case)
    matched = variant(oriented_bundle(original, overlay=("base", lines["base"]), no_crop="construction_base"), pending=False)
    matched_budget = matched["local_review"]["bots"]["B08"]
    require(matched_budget["bank_pdf_by_scenario"]["Base"]["extraction_method"] == "text_and_ocr"
            and matched_budget["construction_pdf_by_scenario"]["Base"]["ocr_region_basis"] == "rotation_normalized_pixels",
            "Matching overlay or uncropped rotation failed")
    hidden = variant(oriented_bundle(original, crop=("downside", (16, 18, 1800, 445)),
                                      overlay=("downside", lines["downside"])))
    bank = hidden["local_review"]["bots"]["B08"]["bank_pdf_by_scenario"]["Downside"]
    require(bank["blockers"] == ["evidence_scan_crop_hides_or_changes_required_rows"] and "document" not in bank
            and not any(row["text"].startswith("C72 | ") for row in bank["ocr"]["cited_lines"])
            and hidden["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and hidden["scenarios"]["Base"]["cash_per_usd_10"] is not None, "A hidden C72 was supplied by full OCR or overlay")
    clipped = variant(oriented_bundle(original, crop=("gc", (16, 18, 1177, 1060))))
    gc = clipped["local_review"]["bots"]["B08"]["gc_pdf"]
    require(gc["blockers"] == ["evidence_scan_crop_hides_or_changes_required_rows"] and "document" not in gc
            and all(row["cash_per_usd_10"] is None for row in clipped["scenarios"].values()), "A clipped quote reached financing")
    alternate = [line.replace("0.05", "0.06") if line.startswith("C69 | ") else line for line in lines["base"]]
    disagrees = variant(oriented_bundle(original, overlay=("base", alternate)))
    reading = disagrees["local_review"]["bots"]["B08"]["bank_pdf_by_scenario"]["Base"]
    require(reading["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(reading["readings"][method]["document"]["annual_nominal_rate"]) for method in ("ocr", "text")]
                == [Fraction("0.05"), Fraction("0.06")]
            and disagrees["scenarios"]["Base"]["cash_per_usd_10"] is None
            and disagrees["scenarios"]["Downside"]["cash_per_usd_10"] is not None, "A crop suppressed a text/OCR discrepancy")
    no_identity = variant(oriented_bundle(original, crop=("construction_downside", (16, 80, 1800, 1060)),
                                           overlay=("construction_downside", lines["construction_downside"])))
    inventory = no_identity["local_review"]["bots"]["B03"]["documents"]["evidence_pdf"]
    require(inventory["blockers"] == ["evidence_scan_page_role_missing_or_disagrees_with_text"]
            and inventory["page_reading"]["ocr_role"] is None
            and inventory["page_reading"]["text_role"] == "construction_Downside", "Text supplied the hidden OCR page identity")
    unsupported = variant(oriented_bundle(original, crop=("construction_downside", (16.5, 18, 1800, 1060))))
    require("B03:evidence_scan_crop_box_unsupported" in unsupported["local_review"]["blockers"],
            "Subpixel crop coordinates were rounded")
    return dict(status="passed", decision="PENDING", evidence_pages=6, scanned_pages=5, pending_cases=5,
                page_count=1, pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d159-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
