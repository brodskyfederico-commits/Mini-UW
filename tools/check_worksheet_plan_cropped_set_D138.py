"""Verify text and OCR agreement when a rotated sheet has a PDF crop."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import zlib

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_dual_rotation_D137 import ANGLES, CASE as DUAL_CASE, PLAN as DUAL_PLAN, dual_plan, pdf_bytes
from check_worksheet_plan_pdf_D130 import run_case
from check_worksheet_plan_scan_D131 import PLAN as SCAN_PLAN
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_CROPPED_PLAN_SET_CHAIN_SCHEMA, encoded
from worksheet_plan_overlay_D133 import rotate_scan
from worksheet_plan_scan_D131 import full_page_image
from worksheet_plan_set_D135 import CROPPED_PROFILE
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-cropped-rotated-set-D138.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D138.json"
PLAN = ROOT / "templates/synthetic-cropped-rotated-set-D138.pdf"
CROP_A101 = (20, 20, 640, 320)
CROP_A601 = (20, 20, 280, 320)


def cropped_pdf(sheet, region, *, source=None):
    source = source if source is not None else DUAL_PLAN.read_bytes()
    writer = PdfWriter(clone_from=PdfReader(BytesIO(source), strict=True))
    page = writer.pages[3 if sheet == "A101" else 1]
    x0, y0, x1, y1 = region
    if sheet == "A601":
        box = (y0, x0, y1, x1)
    else:
        width, height = int(page.mediabox.width), int(page.mediabox.height)
        box = (width - y1, height - x1, width - y0, height - x0)
    page.cropbox = RectangleObject(box)
    writer.add_metadata({"/Title": "Mini-UW synthetic PDF with cropped rotated scan D138"})
    return pdf_bytes(writer)


def duplicate_area_outside_crop():
    """Copy the area line lower on the embedded A601 raster before cropping it out."""
    writer = PdfWriter(clone_from=PdfReader(DUAL_PLAN, strict=True))
    page = writer.pages[1]
    raw = full_page_image(PdfReader(SCAN_PLAN, strict=True).pages[1])
    header, dimensions, maximum, pixels = raw.split(b"\n", 3)
    width = int(dimensions.split()[0])
    changed = bytearray(pixels)
    for offset in range(70):
        source = (700 + offset) * width + 160
        target = (1100 + offset) * width + 160
        changed[target:target + 510] = pixels[source:source + 510]
    stored = rotate_scan(b"\n".join((header, dimensions, maximum, changed)), 270)
    image = page["/Resources"]["/XObject"]["/Im0"]
    image._data = zlib.compress(stored.split(b"\n", 3)[3])
    image.decoded_self = None
    return pdf_bytes(writer)


def case_for(raw):
    case = json.loads(DUAL_CASE.read_bytes())
    case["schema"] = WORKBOOK_CROPPED_PLAN_SET_CHAIN_SCHEMA
    case["local_sources"]["plan_pdf"].update(sha256=sha(raw), sheet_set_profile=CROPPED_PROFILE)
    return case


def verify(temp, saved_output):
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    baseline = PdfReader(DUAL_PLAN, strict=True)
    primary = PdfReader(PLAN, strict=True)
    require(len(primary.pages) == 4 and all(p.get_contents().get_data() == q.get_contents().get_data()
            for p, q in zip(primary.pages, baseline.pages, strict=True)), "The fixture changed the embedded page content")
    originals = PdfReader(SCAN_PLAN, strict=True)
    full_hashes = {"A101": sha(full_page_image(originals.pages[0])), "A601": sha(full_page_image(originals.pages[1]))}

    def verify_match(result, bot, sheet, region, page):
        bots = result["local_review"]["bots"]
        reading = bots[bot]
        ocr = reading["observations"]["ocr"]
        require(result["simulation_result"] == "FAIL" and result["scenarios"] == matching["scenarios"]
                and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"]
                and reading["candidate_pages"] == [page] and reading["observed_page_rotation"] == ANGLES[sheet]
                and all(amount(row["value"]) == 1000 for row in reading["observations"].values())
                and ocr["ocr_region_basis"] == "cropped_rotation_normalized_pixels"
                and ocr["crop_region_in_oriented_scan"] == [3 * point for point in region]
                and ocr["full_oriented_scan_sha256"] == full_hashes[sheet] != ocr["ocr_input_sha256"]
                and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
                "The crop changed the verified area, source provenance or cash")

    verify_match(matching, "B06", "A601", CROP_A601, 2)
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and audit["simulation_result"] == "FAIL", "Audit could not replay the cropped scan")

    def variant(name, raw):
        plan = temp / f"{name}.pdf"
        plan.write_bytes(raw)
        case = case_for(raw)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(case))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D138-{name}")))
        return run_case(case_path, temp / name, reference, plan)

    second = variant("A101-visible", cropped_pdf("A101", CROP_A101))
    verify_match(second, "B05", "A101", CROP_A101, 4)

    def pending(name, raw):
        result = variant(name, raw)
        bots = result["local_review"]["bots"]
        require(result["simulation_result"] == "PENDING" and result["scenarios"] == matching["scenarios"]
                and not result["revision_review"]["blockers"] and bots["B07"]["state"] == bots["B09"]["state"] == "PENDING"
                and "value" not in bots["B07"], "An unresolved crop released a verdict or changed cash")
        return bots

    for sheet, bot, box in (("A101", "B05", (20, 20, 640, 230)), ("A601", "B06", (20, 20, 280, 205))):
        reading = pending(f"area-hidden-{sheet}", cropped_pdf(sheet, box))[bot]
        require(reading["blockers"] == ["required_sheet_area_unverified"]
                and amount(reading["observations"]["text"]["value"]) == 1000
                and reading["observations"]["ocr"]["blockers"] == ["explicit_area_missing_or_ambiguous"]
                and "value" not in reading["observations"]["ocr"], "Hidden scan pixels supplied a value")

    partial = pending("area-line-clipped", cropped_pdf("A601", (20, 20, 280, 250)))["B06"]
    require(partial["blockers"] == ["required_sheet_area_unverified"]
            and "value" not in partial["observations"]["ocr"], "A partially clipped line was accepted")
    identity = pending("identity-hidden", cropped_pdf("A601", (20, 105, 280, 320)))["B03"]["documents"]["plan_pdf"]
    page = identity["sheet_inventory"][1]
    require(page["blockers"] == ["sheet_page_identity_unverified"] and page["observations"]["text"]["sheet"] == "A601"
            and page["observations"]["ocr"]["blockers"], "The PDF text supplied a hidden OCR identity")
    conflict = pending("cropped-layers-conflict", cropped_pdf("A101", CROP_A101, source=dual_plan(layer_conflict="A101")))["B05"]
    require(conflict["blockers"] == ["required_sheet_area_observations_conflict"]
            and amount(conflict["observations"]["text"]["value"]) == 1050
            and amount(conflict["observations"]["ocr"]["value"]) == 1000, "A crop resolved a disagreement between layers")
    duplicate = pending("duplicate-area-hidden", cropped_pdf("A601", CROP_A601, source=duplicate_area_outside_crop()))["B06"]
    require(duplicate["observations"]["ocr"]["blockers"] == ["scan_crop_hides_or_changes_required_area"]
            and amount(duplicate["observations"]["ocr"]["ocr"]["observed_value"]) == 1000,
            "A crop discarded an ambiguous area claim from the embedded scan")
    unsupported = pending("subpixel-crop", cropped_pdf("A601", (20.5, 20, 280, 320)))["B03"]["documents"]["plan_pdf"]
    require(unsupported["sheet_inventory"][1]["blockers"] == ["scan_crop_box_unsupported"],
            "A non-pixel-aligned crop was rounded silently")
    return dict(status="passed", decision="PENDING", full_workbook_cases=9, pending_cases=7,
                cropped_sheets_verified=["A101", "A601"], plan_page_count=4,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited cropped A601 case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d138-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
