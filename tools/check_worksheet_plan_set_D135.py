"""Replay an unordered synthetic sheet set and check inventory and area blockers."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader, PdfWriter

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_overlay_D133 import CASE as OVERLAY_CASE, PLAN as OVERLAY_PLAN
from check_worksheet_plan_pdf_D130 import AREA_A, AREA_B, replace_text, run_case
from check_worksheet_plan_scan_D131 import PLAN as SCAN_PLAN
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_PLAN_SET_CHAIN_SCHEMA, encoded
from worksheet_plan_set_D135 import PROFILE
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-sheet-set-D135.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D135.json"
PLAN = ROOT / "templates/synthetic-sheet-set-D135.pdf"


def plan_set(*, omit=None, duplicate=None, conflict=None, unmarked=False):
    raw = OVERLAY_PLAN.read_bytes()
    cover = replace_text(raw, 0, b"SHEET A101", b"SHEET COVER")
    cover = replace_text(cover, 0, AREA_A, b"Synthetic drawing set index")
    detail = replace_text(raw, 0, b"SHEET A101", b"SHEET A202")
    detail = replace_text(detail, 0, AREA_A, b"Synthetic elevation detail")
    if unmarked:
        detail = replace_text(detail, 0, b"SHEET A202", b"UNTITLED DETAIL")
    summary = raw
    if conflict == "identity":
        summary = replace_text(raw, 1, b"SHEET A601", b"SHEET A602")
    elif conflict == "overlay":
        summary = replace_text(raw, 1, AREA_B, b"Declared GBA: 1,050.00 m2")
    if conflict == "between-sheets":
        raw = replace_text(raw, 0, AREA_A, b"Gross building area | 1050.00 | m2")

    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW synthetic unordered sheet set D135"})
    for sheet, data, index in (("COVER", cover, 0), ("A601", summary, 1), ("A202", detail, 0), ("A101", raw, 0)):
        if sheet != omit:
            writer.add_page(PdfReader(BytesIO(data), strict=True).pages[index])
    if duplicate == "A101":
        writer.add_page(PdfReader(SCAN_PLAN, strict=True).pages[0])
    elif duplicate == "A601":
        writer.add_page(PdfReader(BytesIO(summary), strict=True).pages[1])
    elif duplicate == "A202":
        writer.add_page(PdfReader(BytesIO(detail), strict=True).pages[0])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def case_for(raw):
    case = json.loads(OVERLAY_CASE.read_bytes())
    case["schema"] = WORKBOOK_PLAN_SET_CHAIN_SCHEMA
    specification = case["local_sources"]["plan_pdf"]
    for key in ("page_routes", "overlay_profile"):
        del specification[key]
    specification.update(sha256=sha(raw), sheet_set_profile=PROFILE)
    return case


def verify(temp, saved_output):
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    bots = matching["local_review"]["bots"]
    inventory = bots["B03"]["documents"]["plan_pdf"]["sheet_inventory"]
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"]
            and [(row["page"], row["sheet"]) for row in inventory] == [(1, "COVER"), (2, "A601"), (3, "A202"), (4, "A101")]
            and bots["B05"]["page"] == 4 and bots["B05"]["candidate_pages"] == [4]
            and bots["B06"]["page"] == 2 and bots["B06"]["candidate_pages"] == [2]
            and bots["B06"]["extraction_method"] == "text_and_ocr"
            and all(amount(row["value"]) == 1000 and row["page"] == 2 for row in bots["B06"]["observations"].values())
            and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
            "The matching PDF lost its physical citations, independent overlay readings or GC check")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and audit["simulation_result"] == "FAIL", "Source-first audit did not replay the discovered sheets")

    def pending(name, raw):
        plan = temp / f"{name}.pdf"
        plan.write_bytes(raw)
        case = case_for(raw)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(case))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D135-{name}")))
        result = run_case(case_path, temp / name, reference, plan)
        readings = result["local_review"]["bots"]
        require(result["simulation_result"] == "PENDING" and result["scenarios"] == matching["scenarios"]
                and not result["revision_review"]["blockers"]
                and readings["B07"]["state"] == "PENDING" and "value" not in readings["B07"]
                and readings["B09"]["state"] == "PENDING",
                "A sheet blocker released a verdict, changed cash or supplied a reconciled value")
        return readings

    for sheet, bot, pages in (("A101", "B05", [4, 5]), ("A601", "B06", [2, 5])):
        absent = pending(f"missing-{sheet}", plan_set(omit=sheet))[bot]
        require(absent["blockers"] == ["required_sheet_missing"] and absent["candidate_pages"] == [],
                "The reader assigned an unrelated page to a missing sheet")
        duplicated = pending(f"duplicate-{sheet}", plan_set(duplicate=sheet))
        reading = duplicated[bot]
        require(reading["blockers"] == ["required_sheet_duplicated"] and reading["candidate_pages"] == pages
                and "value" not in reading, "The reader selected one of several matching sheet identities")
        if sheet == "A101":
            fifth = duplicated["B03"]["documents"]["plan_pdf"]["sheet_inventory"][4]
            require(set(fifth["observations"]) == {"ocr"}, "The extra scanned duplicate was read as PDF text")

    disagreed = pending("area-overlay", plan_set(conflict="overlay"))["B06"]
    require(disagreed["blockers"] == ["required_sheet_area_observations_conflict"]
            and amount(disagreed["observations"]["text"]["value"]) == 1050
            and amount(disagreed["observations"]["ocr"]["value"]) == 1000, "A layer discrepancy lost either value")
    between = pending("area-between-sheets", plan_set(conflict="between-sheets"))["B07"]
    require(between["blockers"] == ["plan_readings_conflict"]
            and [amount(row["value"]) for row in between["readings"]] == [1050, 1000],
            "A cross-sheet discrepancy lost either value")
    disputed = pending("identity-overlay", plan_set(conflict="identity"))["B03"]["documents"]["plan_pdf"]
    page = disputed["sheet_inventory"][1]
    require(page["blockers"] == ["sheet_page_identities_conflict"]
            and page["observations"]["text"]["sheet"] == "A602" and page["observations"]["ocr"]["sheet"] == "A601",
            "Conflicting page identities were ignored")
    unmarked = pending("unidentified-extra-page", plan_set(unmarked=True))["B03"]["documents"]["plan_pdf"]
    require(unmarked["blockers"] == ["plan_sheet_inventory_incomplete"]
            and unmarked["sheet_inventory"][2]["blockers"] == ["sheet_page_identity_unverified"],
            "The reader skipped a page whose identity was unknown")
    extra_duplicate = pending("duplicate-extra-page", plan_set(duplicate="A202"))["B03"]["documents"]["plan_pdf"]
    require(extra_duplicate["blockers"] == ["plan_sheet_duplicates"]
            and extra_duplicate["duplicate_sheet_pages"] == {"A202": [3, 5]}, "An extra duplicate was ignored")
    return dict(status="passed", decision="PENDING", full_workbook_cases=10, pending_cases=9,
                required_sheet_pages={"A101": 4, "A601": 2}, scanned_duplicate_detected=True,
                plan_page_count=4, pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited four-page case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d135-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
