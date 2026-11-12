"""Verify a rotated A601 within an unordered synthetic plan set."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_pdf_D130 import run_case
from check_worksheet_plan_rotation_D134 import rotated_pdf
from check_worksheet_plan_set_D135 import CASE as UPRIGHT_CASE, PLAN as UPRIGHT_PLAN, plan_set
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_ROTATED_PLAN_SET_CHAIN_SCHEMA, encoded
from worksheet_plan_scan_D131 import full_page_image
from worksheet_plan_set_D135 import ROTATED_PROFILE
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-rotated-sheet-set-D136.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D136.json"
PLAN = ROOT / "templates/synthetic-rotated-sheet-set-D136.pdf"


def plan_with_rotation(rotation, *, source=None, move_summary=False, conflict=False, omit_text=False):
    upright = PdfReader(BytesIO(source if source is not None else UPRIGHT_PLAN.read_bytes()), strict=True)
    rotated = PdfReader(BytesIO(rotated_pdf(rotation, conflicting_text=conflict)), strict=True)
    summary = rotated.pages[1]
    pages = list(upright.pages)
    for index, page in enumerate(pages):
        if "SHEET A601" in (page.extract_text() or "").splitlines():
            pages[index] = summary
            break
    if move_summary:
        pages[1], pages[2] = pages[2], pages[1]
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW synthetic unordered sheet set with rotated A601 D136"})
    for page in pages:
        copied = writer.add_page(page)
        if omit_text and page is summary:
            contents = DecodedStreamObject()
            contents.set_data(page.get_contents().get_data().split(b"BT", 1)[0])
            copied.replace_contents(contents)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def case_for(raw, rotation):
    case = json.loads(UPRIGHT_CASE.read_bytes())
    case["schema"] = WORKBOOK_ROTATED_PLAN_SET_CHAIN_SCHEMA
    case["local_sources"]["plan_pdf"].update(sha256=sha(raw), sheet_set_profile=ROTATED_PROFILE,
                                               a601_rotation_clockwise=rotation)
    return case


def verify(temp, saved_output):
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    upright = PdfReader(UPRIGHT_PLAN, strict=True)
    digest = sha(full_page_image(upright.pages[1], allow_text_layer=True))
    primary = PdfReader(PLAN, strict=True)
    require(len(primary.pages) == 4 and all(primary.pages[i].get_contents().get_data()
            == upright.pages[i].get_contents().get_data() for i in (0, 2, 3)), "The fixture changed other sheets")

    def verify_match(result, plan, rotation, page):
        bots = result["local_review"]["bots"]
        summary = bots["B06"]
        observations = summary["observations"]
        ocr = observations["ocr"]
        stored = PdfReader(plan, strict=True).pages[page - 1]
        image = full_page_image(stored, allow_text_layer=True, allowed_rotation=rotation)
        inventory = bots["B03"]["documents"]["plan_pdf"]["sheet_inventory"]
        require(result["simulation_result"] == "FAIL" and result["scenarios"] == matching["scenarios"]
                and not result["revision_review"]["blockers"] and not result["local_review"]["blockers"]
                and inventory[page - 1]["sheet"] == "A601" and summary["candidate_pages"] == [page]
                and summary["declared_page_rotation"] == summary["observed_page_rotation"] == rotation
                and summary["extraction_method"] == "text_and_ocr"
                and all(row["page"] == page and amount(row["value"]) == 1000 for row in observations.values())
                and ocr["raw_image_sha256"] == sha(image) != digest and ocr["ocr_input_sha256"] == digest
                and ocr["ocr_region_basis"] == "rotation_normalized_pixels"
                and bots["B05"]["candidate_pages"] == [4] and amount(bots["B07"]["value"]) == 1000
                and amount(bots["B09"]["difference"]) == 0, "Rotation or page order changed the evidence or cash")

    verify_match(matching, PLAN, 90, 2)
    audited = call("audit", output, "--current-revision", CURRENT)
    require(audited["audit_bot"] == "B16" and audited["vigencia"] == "VIGENTE"
            and audited["simulation_result"] == "FAIL", "Audit could not replay the rotated plan")

    def variant(name, raw, rotation=90):
        plan = temp / f"{name}.pdf"
        plan.write_bytes(raw)
        case = case_for(raw, rotation)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(case))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D136-{name}")))
        return run_case(case_path, temp / name, reference, plan), plan

    for rotation, page in ((180, 2), (270, 3)):
        result, plan = variant(f"rotation-{rotation}", plan_with_rotation(rotation, move_summary=page == 3), rotation)
        verify_match(result, plan, rotation, page)

    def pending(name, raw, rotation=90):
        result, _ = variant(name, raw, rotation)
        bots = result["local_review"]["bots"]
        require(result["simulation_result"] == "PENDING" and result["scenarios"] == matching["scenarios"]
                and not result["revision_review"]["blockers"]
                and bots["B07"]["state"] == bots["B09"]["state"] == "PENDING"
                and "value" not in bots["B07"], "An unresolved plan released a verdict or changed cash")
        return bots

    for sheet, bot, expected_pages in (("A101", "B05", [4, 5]), ("A601", "B06", [2, 5])):
        missing = pending(f"missing-{sheet}", plan_with_rotation(90, source=plan_set(omit=sheet)))[bot]
        require(missing["blockers"] == ["required_sheet_missing"] and missing["candidate_pages"] == [],
                "A missing sheet was filled from another page")
        duplicate = pending(f"duplicate-{sheet}", plan_with_rotation(90, source=plan_set(duplicate=sheet)))
        require(duplicate[bot]["blockers"] == ["required_sheet_duplicated"]
                and duplicate[bot]["candidate_pages"] == expected_pages, "A duplicate was discarded after rotation")
        if sheet == "A601":
            rows = duplicate["B03"]["documents"]["plan_pdf"]["sheet_inventory"]
            require([rows[i - 1]["observations"]["ocr"]["page_rotation_clockwise"] for i in expected_pages] == [90, 0],
                    "The upright duplicate was not checked against the rotated copy")

    layers = pending("area-conflict", plan_with_rotation(90, conflict=True))["B06"]
    require(layers["blockers"] == ["required_sheet_area_observations_conflict"]
            and amount(layers["observations"]["text"]["value"]) == 1050
            and amount(layers["observations"]["ocr"]["value"]) == 1000
            and layers["observations"]["ocr"]["ocr_input_sha256"] == digest, "The visible layer influenced OCR")
    between = pending("area-between-sheets", plan_with_rotation(90, source=plan_set(conflict="between-sheets")))["B07"]
    require(between["blockers"] == ["plan_readings_conflict"]
            and [amount(row["value"]) for row in between["readings"]] == [1050, 1000], "A sheet discrepancy was discarded")
    mismatch = pending("rotation-mismatch", PLAN.read_bytes(), 270)["B06"]
    require(mismatch["blockers"] == ["required_sheet_page_rotation_mismatch"]
            and mismatch["observed_page_rotation"] == 90 and mismatch["declared_page_rotation"] == 270,
            "A different rotation satisfied the declared setting")
    image_only = pending("text-layer-missing", plan_with_rotation(90, omit_text=True))["B06"]
    require(image_only["blockers"] == ["rotated_sheet_text_and_ocr_required"]
            and amount(image_only["observations"]["ocr"]["value"]) == 1000, "A601 passed from OCR alone")
    return dict(status="passed", decision="PENDING", full_workbook_cases=11, pending_cases=8,
                rotations_verified=[90, 180, 270], required_sheet_pages={"A101": 4, "A601": 2},
                rotated_and_upright_duplicate_detected=True, identical_ocr_raster=True,
                plan_page_count=4, pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited four-page case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d136-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
