"""Verify a shuffled financial evidence PDF whose five scans are progressive JPEGs."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from PIL import Image
from pypdf import PdfReader, PdfWriter

from check_operating_replay_D20 import amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_pdf_D157 import BOOKS, ORDER, PLAN, pages, run_package
from check_worksheet_evidence_jpeg_D161 import JPEG_ROLES, UPRIGHT, jpeg_bundle
from check_worksheet_evidence_oriented_D159 import ANGLES, MARGIN, pdf_crop_box
from check_worksheet_evidence_progressive_crop_D163 import (
    CASE as PRIOR, CURRENT as PRIOR_CURRENT, SCAN as PRIOR_SCAN, case_for, same_cash,
)
from check_worksheet_plan_overlay_D133 import add_text_overlay
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, build_results, encoded
from worksheet_evidence_pdf_D156 import CONSTRUCTION_HEADERS, HEADERS
from worksheet_revision_D128 import snapshot_for_case


SHUFFLED = ("base", "gc", "construction_base", "official", "downside", "construction_downside")
SCAN_ENCODINGS = JPEG_ROLES | {"construction_downside": ("L", 98), "downside": ("L", 100)}
ROLES = HEADERS | CONSTRUCTION_HEADERS


def shuffled_pdf():
    raw = jpeg_bundle(UPRIGHT.read_bytes(), progressive_roles=SCAN_ENCODINGS, oriented=True,
                      rgb_quality=98, jpeg_roles=SCAN_ENCODINGS)
    reader = PdfReader(BytesIO(raw), strict=True)
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW D164 synthetic shuffled progressive financial evidence"})
    for role in SHUFFLED:
        writer.add_page(reader.pages[ORDER.index(role)])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def variant_pdf(raw, role, *, drop=False, replace_with=None, crop=None, overlay=None):
    writer = PdfWriter(clone_from=BytesIO(raw))
    index = SHUFFLED.index(role)
    if replace_with is not None:
        writer.insert_page(writer.pages[SHUFFLED.index(replace_with)], index=index)
        index += 1
    if drop or replace_with is not None:
        writer.remove_page(index)
    else:
        page = writer.pages[index]
        if crop is not None:
            page.cropbox = pdf_crop_box(crop, ANGLES[role], int(page.mediabox.width), int(page.mediabox.height))
        if overlay is not None:
            add_text_overlay(writer, page, [(560 - 22 * i, line) for i, line in enumerate(overlay)])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def verify(temp, output):
    raw = shuffled_pdf()
    case = case_for(raw)
    evidence = temp / EVIDENCE_FILE
    evidence.write_bytes(raw)
    case_file = temp / "case.json"
    case_file.write_bytes(encoded(case))
    revision = temp / "current_revision.json"
    revision.write_bytes(encoded(snapshot_for_case(case, "SYNTHETIC-D164-current")))
    status = run_package(case_file, revision, evidence, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"]
            and not result["deployment_enabled"] and not result["real_decisions_enabled"],
            "Shuffled progressive pages did not reach the synthetic calculation")

    run_package(PRIOR, PRIOR_CURRENT, PRIOR_SCAN, temp / "D163")
    prior = json.loads((temp / "D163/results.json").read_bytes())
    for scenario in ("Base", "Downside"):
        same_cash(result, prior, scenario)
    expected = pages(case)
    page_roles = {ROLES[expected[role][0]]: i for i, role in enumerate(SHUFFLED, 1)}
    bots = result["local_review"]["bots"]
    require(bots["B03"]["documents"]["evidence_pdf"]["page_roles"] == page_roles, "B03 used the wrong page order")
    budget = bots["B08"]
    readings = {"gc": budget["gc_pdf"]}
    for scenario in ("Base", "Downside"):
        readings[scenario.lower()] = budget["bank_pdf_by_scenario"][scenario]
        readings[f"construction_{scenario.lower()}"] = budget["construction_pdf_by_scenario"][scenario]
    pdf = PdfReader(BytesIO(raw), strict=True)
    for role, reading in readings.items():
        index = SHUFFLED.index(role)
        page = pdf.pages[index]
        image = page["/Resources"]["/XObject"]["/I"].get_data()
        with Image.open(BytesIO(image), formats=("JPEG",)) as decoded:
            require(decoded.info.get("progressive") and decoded.mode == SCAN_ENCODINGS[role][0],
                    f"{role} did not have a progressive JPEG")
        require(reading["page"] == index + 1 and reading["page_rotation_clockwise"] == page.rotation == ANGLES[role]
                and reading["crop_region_in_oriented_scan"] == list(MARGIN)
                and reading["ocr_region_basis"] == "cropped_rotation_normalized_pixels"
                and reading["source_image_filter"] == "/DCTDecode" and reading["source_jpeg_sha256"] == sha(image)
                and reading["jpeg_encoding"] == "progressive" and reading["extraction_method"] == "ocr"
                and not (page.extract_text() or "").strip()
                and reading["ocr"]["cited_lines"][0]["text"] == expected[role][0],
                f"{role} lost the physical page, geometry or OCR citation")
    audit = call("audit", output, "--current-revision", revision)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and audit["pdf_sha256"] == status["pdf_sha256"] and (output / EVIDENCE_FILE).read_bytes() == raw,
            "B16 could not replay the shuffled progressive PDF")

    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()

    def pending(role, **changes):
        bundle = variant_pdf(raw, role, **changes)
        changed = case_for(bundle)
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=encoded(snapshot_for_case(changed, "SYNTHETIC-D164-variant")),
                                plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == view["simulation_result"] == "PENDING", "Unresolved pages released a decision")
        return view, view["local_review"]["bots"]

    missing, bots = pending("construction_base", drop=True)
    require(bots["B08"]["construction_pdf_by_scenario"]["Base"]["blockers"] == ["evidence_page_role_missing"]
            and missing["scenarios"]["Base"]["cash_per_usd_10"] is None, "Missing construction evidence reached Base")
    same_cash(missing, prior, "Downside")

    hidden, bots = pending("downside", crop=(16, 18, 1800, 445), overlay=expected["downside"])
    bank = bots["B08"]["bank_pdf_by_scenario"]["Downside"]
    require(bank["blockers"] == ["evidence_scan_crop_hides_or_changes_required_rows"]
            and not any(row["text"].startswith("C72 | ") for row in bank["ocr"]["cited_lines"])
            and hidden["scenarios"]["Downside"]["cash_per_usd_10"] is None, "Text supplied hidden Downside C72")
    same_cash(hidden, prior, "Base")

    lines = [line.replace("0.10", "0.11") if line.startswith("C52 | ") else line
             for line in expected["construction_downside"]]
    conflict, bots = pending("construction_downside", overlay=lines)
    loan = bots["B08"]["construction_pdf_by_scenario"]["Downside"]
    require(loan["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(loan["readings"][method]["document"]["annual_interest"]) for method in ("ocr", "text")]
                == [Fraction("0.10"), Fraction("0.11")]
            and conflict["scenarios"]["Downside"]["cash_per_usd_10"] is None, "Conflicting construction terms reached Downside")
    same_cash(conflict, prior, "Base")

    lines = [line.replace("2340000", "2340001") if line.startswith("Vertical Base | ") else line
             for line in expected["gc"]]
    conflict, bots = pending("gc", overlay=lines)
    quote = bots["B08"]["gc_pdf"]
    require(quote["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(quote["readings"][method]["document"]["budget_by_scenario"]["Base"]["value"])
                 for method in ("ocr", "text")] == [2340000, 2340001]
            and all(row["cash_per_usd_10"] is None for row in conflict["scenarios"].values()),
            "Conflicting quote supplied a budget")

    duplicate, bots = pending("base", replace_with="downside")
    inventory = bots["B03"]["documents"]["evidence_pdf"]
    require(inventory["blockers"] == ["evidence_page_role_duplicate"] and inventory["role"] == "bank_Downside"
            and all(row["cash_per_usd_10"] is None for row in duplicate["scenarios"].values()),
            "Duplicate Downside evidence was assigned to Base")
    return dict(status="passed", decision="PENDING", page_count=len(PdfReader(output / "MiniUW_Resumen.pdf").pages),
                evidence_pages=len(SHUFFLED), page_roles=page_roles, progressive_pages=len(readings), pending_cases=5,
                evidence_sha256=sha(raw), pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d164-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
