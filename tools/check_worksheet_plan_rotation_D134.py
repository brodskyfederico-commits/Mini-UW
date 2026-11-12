"""Replay rotated synthetic overlays against their original raster and source binding."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import zlib

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, NumberObject, RectangleObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_overlay_D133 import CASE as OVERLAY_CASE, PLAN as OVERLAY_PLAN
from check_worksheet_plan_pdf_D130 import run_case
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA, encoded
from worksheet_plan_overlay_D133 import ROTATED_PROFILE
from worksheet_plan_scan_D131 import full_page_image
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-rotated-overlay-D134.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D134.json"
PLAN = ROOT / "templates/synthetic-rotated-overlay-D134.pdf"


def rotated_pdf(rotation, *, conflicting_text=False):
    writer = PdfWriter(clone_from=PdfReader(OVERLAY_PLAN, strict=True))
    page = writer.pages[1]
    width, height = int(page.mediabox.width), int(page.mediabox.height)
    image = page["/Resources"]["/XObject"]["/Im0"]
    columns, rows = image["/Width"], image["/Height"]
    pixels = image.get_data()
    if rotation == 90:
        stored = b"".join(pixels[x::columns] for x in range(columns - 1, -1, -1))
        text_matrix = lambda x, y: (0, 1, -1, 0, height - y, x)
    elif rotation == 180:
        stored = pixels[::-1]
        text_matrix = lambda x, y: (-1, 0, 0, -1, width - x, height - y)
    else:
        stored = b"".join(pixels[x::columns][::-1] for x in range(columns))
        text_matrix = lambda x, y: (0, -1, 1, 0, y, width - x)
    image._data = zlib.compress(stored)
    image.decoded_self = None
    if rotation != 180:
        image[NameObject("/Width")], image[NameObject("/Height")] = NumberObject(rows), NumberObject(columns)
        page.mediabox = RectangleObject((0, 0, height, width))
        page.cropbox = RectangleObject(page.mediabox)
    page.rotate(rotation)

    data = page.get_contents().get_data()
    _, overlay = data.split(b"BT", 1)

    def transform(match):
        x, y = map(int, match.groups())
        return (" ".join(map(str, text_matrix(x, y))) + " Tm").encode()

    overlay = re.sub(rb"1 0 0 1 (\d+) (\d+) Tm", transform, overlay)
    if conflicting_text:
        overlay = overlay.replace(b"3 Tr", b"0 Tr").replace(b"1,000.00 m2", b"1,050.00 m2")
    scan_draw = f"q\n{int(page.mediabox.width)} 0 0 {int(page.mediabox.height)} 0 0 cm\n/Im0 Do\nQ\n".encode()
    contents = DecodedStreamObject()
    contents.set_data(scan_draw + b"BT" + overlay)
    page.replace_contents(contents)
    writer.add_metadata({"/Title": "Mini-UW synthetic rotated overlay D134"})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def rotated_case(raw, rotation):
    case = json.loads(OVERLAY_CASE.read_bytes())
    case["schema"] = WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA
    case["local_sources"]["plan_pdf"].update(sha256=sha(raw), overlay_profile=ROTATED_PROFILE,
                                               page_rotation_clockwise=rotation)
    return case


def verify(temp, saved_output):
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    baseline_page = PdfReader(OVERLAY_PLAN, strict=True).pages[1]
    baseline_raster = full_page_image(baseline_page, allow_text_layer=True)
    baseline_digest = sha(baseline_raster)

    def verify_matching(result, plan, rotation):
        bots = result["local_review"]["bots"]
        readings = bots["B06"]["observations"]
        ocr = readings["ocr"]
        raw_raster = full_page_image(PdfReader(plan, strict=True).pages[1], allow_text_layer=True,
                                     allowed_rotation=rotation)
        require(result["simulation_result"] == "FAIL" and not result["revision_review"]["blockers"]
                and result["scenarios"] == matching["scenarios"]
                and bots["B03"]["documents"]["plan_pdf"]["page_rotation_clockwise"] == rotation
                and ocr["observed_page_rotation"] == ocr["declared_page_rotation"] == rotation
                and ocr["raw_image_sha256"] == sha(raw_raster) != baseline_digest
                and ocr["ocr_input_sha256"] == baseline_digest
                and ocr["ocr_region_basis"] == "rotation_normalized_pixels"
                and len(ocr["ocr"]["cited_lines"]) == 4
                and all(amount(row["value"]) == 1000 and row["page"] == 2 for row in readings.values())
                and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
                "A rotation changed the raster, lost provenance or changed the checked plan or cash")

    verify_matching(matching, PLAN, 90)
    audited = call("audit", output, "--current-revision", CURRENT)
    require(audited["vigencia"] == "VIGENTE" and audited["audit_bot"] == "B16"
            and audited["simulation_result"] == "FAIL", "The rotated overlay could not replay from source")

    def variant(name, raw, rotation):
        plan = temp / f"{name}.pdf"
        plan.write_bytes(raw)
        case = rotated_case(raw, rotation)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(case))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D134-{name}")))
        return run_case(case_path, temp / name, reference, plan), plan

    for rotation in (180, 270):
        result, plan = variant(f"rotate-{rotation}", rotated_pdf(rotation), rotation)
        verify_matching(result, plan, rotation)

    mismatch, _ = variant("rotation-mismatch", PLAN.read_bytes(), 270)
    missing, _ = variant("rotation-missing", PLAN.read_bytes(), None)
    conflict, _ = variant("rotated-area-conflict", rotated_pdf(90, conflicting_text=True), 90)
    for result in (mismatch, missing, conflict):
        bots = result["local_review"]["bots"]
        require(result["simulation_result"] == "PENDING" and result["scenarios"] == matching["scenarios"]
                and "value" not in bots["B06"] and bots["B07"]["blockers"] == ["both_plan_readings_required"]
                and bots["B09"]["state"] == "PENDING", "Unresolved orientation or areas supplied a verdict")
    mismatch_ocr = mismatch["local_review"]["bots"]["B06"]["observations"]["ocr"]
    require(mismatch_ocr["blockers"] == ["overlay_page_rotation_mismatch"] and "ocr_input_sha256" not in mismatch_ocr,
            "A mismatched orientation ran OCR")
    require(missing["local_review"]["bots"]["B03"]["documents"]["plan_pdf"]["blockers"]
            == ["explicit_overlay_page_rotation_required"], "The orientation was guessed")
    disputed = conflict["local_review"]["bots"]["B06"]
    require(disputed["blockers"] == ["overlay_observations_conflict"]
            and amount(disputed["observations"]["text"]["value"]) == 1050
            and amount(disputed["observations"]["ocr"]["value"]) == 1000
            and disputed["observations"]["ocr"]["ocr_input_sha256"] == baseline_digest,
            "The visible text changed OCR of the rotated image")
    return dict(status="passed", decision="PENDING", full_workbook_cases=6, pending_cases=3,
                rotations_verified=[90, 180, 270], identical_ocr_raster=True,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited 90-degree case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d134-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
