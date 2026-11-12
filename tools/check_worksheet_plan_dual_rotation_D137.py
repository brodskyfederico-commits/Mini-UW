"""Verify independent text and OCR on two rotated sheets in a synthetic PDF."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader, PdfWriter

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_overlay_D133 import add_text_overlay
from check_worksheet_plan_pdf_D130 import run_case
from check_worksheet_plan_rotation_D134 import rotated_pdf
from check_worksheet_plan_scan_D131 import CONFLICT as CONFLICT_SCAN, PLAN as SCAN_PLAN
from check_worksheet_plan_set_D135 import CASE as UPRIGHT_CASE, PLAN as UPRIGHT_PLAN, plan_set
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_DUAL_ROTATED_PLAN_SET_CHAIN_SCHEMA, encoded
from worksheet_plan_scan_D131 import full_page_image
from worksheet_plan_set_D135 import DUAL_ROTATED_PROFILE
from worksheet_revision_D128 import snapshot_for_case
from worksheet_screening_pilot_D120 import PROFILE as PILOT_PROFILE


CASE = ROOT / "templates/synthetic-workbook-dual-rotation-D137.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D137.json"
PLAN = ROOT / "templates/synthetic-dual-rotation-D137.pdf"
ANGLES = {"A101": 270, "A601": 90}
SHEETS = {"A101": "B05", "A601": "B06"}


def pdf_bytes(writer):
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def rotated_sheets(angles, *, layer_conflict=None, sheet_conflict=False, missing_text=None):
    writer = PdfWriter()
    scan = PdfReader(SCAN_PLAN, strict=True)
    summary_scan = PdfReader(CONFLICT_SCAN, strict=True) if sheet_conflict else scan
    for sheet, image in (("A101", scan.pages[0]), ("A601", summary_scan.pages[1])):
        page = writer.add_page(image)
        if sheet == missing_text:
            continue
        changed = sheet == layer_conflict
        if sheet == "A101":
            area = "Gross building area | 1050.00 | m2" if changed else "Gross building area | 1000.00 | m2"
        else:
            area = "Declared GBA: 1,050.00 m2" if changed or sheet_conflict else "Declared GBA: 1,000.00 m2"
        lines = [(462, "SYNTHETIC MINI-UW PLAN"), (438, "PLAN REF SYNTHETIC-PLAN-01-R1"),
                 (420, f"SHEET {sheet}"), (255, area)]
        add_text_overlay(writer, page, lines, visible=changed)
    raw = pdf_bytes(writer)
    for index, sheet in enumerate(SHEETS):
        raw = rotated_pdf(angles[sheet], source=raw, page_index=index)
    return PdfReader(BytesIO(raw), strict=True)


def dual_plan(angles=ANGLES, *, source=None, reorder=False, layer_conflict=None, sheet_conflict=False, missing_text=None):
    upright = PdfReader(BytesIO(source if source is not None else UPRIGHT_PLAN.read_bytes()), strict=True)
    rotated = rotated_sheets(angles, layer_conflict=layer_conflict, sheet_conflict=sheet_conflict, missing_text=missing_text)
    pages = list(upright.pages)
    for index, sheet in enumerate(SHEETS):
        for position, page in enumerate(pages):
            if f"SHEET {sheet}" in (page.extract_text() or "").splitlines():
                pages[position] = rotated.pages[index]
                break
    if reorder:
        pages = [pages[i] for i in (1, 0, 3, 2)]
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW synthetic unordered PDF with two rotated sheets D137"})
    for page in pages:
        writer.add_page(page)
    return pdf_bytes(writer)


def case_for(raw, angles):
    case = json.loads(UPRIGHT_CASE.read_bytes())
    case["schema"] = WORKBOOK_DUAL_ROTATED_PLAN_SET_CHAIN_SCHEMA
    case["local_sources"]["plan_pdf"].update(sha256=sha(raw), sheet_set_profile=DUAL_ROTATED_PROFILE,
                                               sheet_rotations_clockwise=angles)
    return case


def verify(temp, saved_output):
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    scan = PdfReader(SCAN_PLAN, strict=True)
    hashes = {sheet: sha(full_page_image(page)) for sheet, page in zip(SHEETS, scan.pages, strict=True)}
    upright = PdfReader(UPRIGHT_PLAN, strict=True)
    primary = PdfReader(PLAN, strict=True)
    require(len(primary.pages) == 4 and all(primary.pages[i].get_contents().get_data()
            == upright.pages[i].get_contents().get_data() for i in (0, 2)), "The supplementary sheets were changed")

    def verify_match(result, path, angles, pages):
        bots = result["local_review"]["bots"]
        doc = bots["B03"]["documents"]["plan_pdf"]
        require(result["profile"] == PILOT_PROFILE and result["simulation_result"] == "FAIL"
                and result["scenarios"] == matching["scenarios"]
                and not result["revision_review"]["blockers"] and not result["local_review"]["blockers"]
                and doc["sheet_rotations_clockwise"] == angles and not doc["duplicate_sheet_pages"]
                and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
                "The two orientations did not reconcile to the expected area and cash")
        reader = PdfReader(path, strict=True)
        for sheet, bot in SHEETS.items():
            row = bots[bot]
            index = pages[sheet]
            angle = angles[sheet]
            readings = row["observations"]
            ocr = readings["ocr"]
            stored = full_page_image(reader.pages[index - 1], allow_text_layer=True, allowed_rotation=angle)
            require(row["candidate_pages"] == [index] and row["extraction_method"] == "text_and_ocr"
                    and row["declared_page_rotation"] == row["observed_page_rotation"] == angle
                    and all(obs["page"] == index and amount(obs["value"]) == 1000 for obs in readings.values())
                    and ocr["raw_image_sha256"] == sha(stored) != hashes[sheet]
                    and ocr["ocr_input_sha256"] == hashes[sheet]
                    and ocr["ocr_region_basis"] == "rotation_normalized_pixels", "A reading lost its sheet or OCR provenance")

    verify_match(matching, PLAN, ANGLES, {"A101": 4, "A601": 2})
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and audit["simulation_result"] == "FAIL", "Audit could not replay the two rotated sheets")

    def variant(name, raw, angles=ANGLES):
        plan = temp / f"{name}.pdf"
        plan.write_bytes(raw)
        case = case_for(raw, angles)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(case))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D137-{name}")))
        return run_case(case_path, temp / name, reference, plan), plan

    alternate = {"A101": 90, "A601": 180}
    result, plan = variant("both-sheets-moved", dual_plan(alternate, reorder=True), alternate)
    verify_match(result, plan, alternate, {"A101": 3, "A601": 1})

    def pending(name, raw, angles=ANGLES):
        result, _ = variant(name, raw, angles)
        bots = result["local_review"]["bots"]
        require(result["simulation_result"] == "PENDING" and result["scenarios"] == matching["scenarios"]
                and not result["revision_review"]["blockers"]
                and bots["B07"]["state"] == bots["B09"]["state"] == "PENDING"
                and "value" not in bots["B07"], "An unresolved sheet released a verdict or changed cash")
        return bots

    for sheet, bot in SHEETS.items():
        absent = pending(f"missing-{sheet}", dual_plan(source=plan_set(omit=sheet)))[bot]
        require(absent["blockers"] == ["required_sheet_missing"] and not absent["candidate_pages"],
                "The plan accepted an absent sheet")
        duplicated = pending(f"duplicate-{sheet}", dual_plan(source=plan_set(duplicate=sheet)))
        candidates = [4 if sheet == "A101" else 2, 5]
        inventory = duplicated["B03"]["documents"]["plan_pdf"]["sheet_inventory"]
        require(duplicated[bot]["blockers"] == ["required_sheet_duplicated"]
                and duplicated[bot]["candidate_pages"] == candidates
                and [inventory[i - 1]["observations"]["ocr"]["page_rotation_clockwise"] for i in candidates]
                == [ANGLES[sheet], 0], "A duplicate in another orientation escaped the inventory")
        conflict = pending(f"layers-{sheet}", dual_plan(layer_conflict=sheet))[bot]
        require(conflict["blockers"] == ["required_sheet_area_observations_conflict"]
                and amount(conflict["observations"]["text"]["value"]) == 1050
                and amount(conflict["observations"]["ocr"]["value"]) == 1000
                and conflict["observations"]["ocr"]["ocr_input_sha256"] == hashes[sheet],
                "The visible overlay influenced OCR")
        image_only = pending(f"text-absent-{sheet}", dual_plan(missing_text=sheet))[bot]
        require(image_only["blockers"] == ["rotated_sheet_text_and_ocr_required"]
                and amount(image_only["observations"]["ocr"]["value"]) == 1000,
                "OCR alone satisfied the two-readings rule")

    cross_sheet = pending("cross-sheet-conflict", dual_plan(sheet_conflict=True))["B07"]
    require(cross_sheet["blockers"] == ["plan_readings_conflict"]
            and [amount(row["value"]) for row in cross_sheet["readings"]] == [1000, 1050],
            "Verified layers hid a discrepancy across sheets")
    wrong_angle = pending("wrong-angle-A101", PLAN.read_bytes(), ANGLES | {"A101": 180})["B05"]
    require(wrong_angle["blockers"] == ["required_sheet_page_rotation_mismatch"]
            and wrong_angle["declared_page_rotation"] == 180 and wrong_angle["observed_page_rotation"] == 270,
            "A different angle satisfied the declared setting")
    missing_angle = pending("angle-absent", PLAN.read_bytes(), {"A601": 90})
    require(missing_angle["B03"]["documents"]["plan_pdf"]["blockers"] == ["explicit_required_sheet_rotations_required"],
            "An angle was inferred for a sheet")
    return dict(status="passed", decision="PENDING", full_workbook_cases=13, pending_cases=11,
                verified_angle_pairs=[ANGLES, alternate], required_sheet_pages={"A101": 4, "A601": 2},
                plan_page_count=4, pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited four-page case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d137-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
