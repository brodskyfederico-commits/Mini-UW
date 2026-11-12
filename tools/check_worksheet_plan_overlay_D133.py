"""Exercise two observations from one sheet, using the raster beneath its PDF text."""
from argparse import ArgumentParser
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_pdf_D130 import PLAN as TEXT_PLAN, run_case
from check_worksheet_plan_scan_D131 import CONFLICT, MISSING, PLAN as SCAN_PLAN
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_plan_scan_D131 import full_page_image
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-overlay-chain-D133.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D133.json"
PLAN = ROOT / "templates/synthetic-overlay-plan-D133.pdf"


def overlay_pdf(background, area="1,000.00", *, visible=False):
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW synthetic plan with PDF text overlay D133"})
    writer.add_page(PdfReader(TEXT_PLAN, strict=True).pages[0])
    page = writer.add_page(PdfReader(background, strict=True).pages[1])
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page["/Resources"][NameObject("/Font")] = DictionaryObject({NameObject("/F1"): writer._add_object(font)})
    lines = [(462, "SYNTHETIC MINI-UW PLAN"), (438, "PLAN REF SYNTHETIC-PLAN-01-R1"), (420, "SHEET A601")]
    if area is not None:
        lines.append((255, f"Declared GBA: {area} m2"))
    rendering_mode = 0 if visible else 3
    overlay = f"BT\n/F1 11 Tf\n{rendering_mode} Tr\n" + "".join(f"1 0 0 1 60 {y} Tm\n({line}) Tj\n" for y, line in lines)
    content = DecodedStreamObject()
    content.set_data(page.get_contents().get_data() + b"\n" + (overlay + "ET\n").encode())
    page.replace_contents(content)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    bots = matching["local_review"]["bots"]
    observations = bots["B06"]["observations"]
    original_image = sha(full_page_image(PdfReader(SCAN_PLAN, strict=True).pages[1]))
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"]
            and bots["B03"]["documents"]["plan_pdf"]["kind"] == "synthetic_pdf_with_text_overlay"
            and (bots["B06"]["sheet"], bots["B06"]["page"], bots["B06"]["extraction_method"]) == ("A601", 2, "text_and_ocr")
            and all(amount(row["value"]) == 1000 and row["page"] == 2 for row in observations.values())
            and observations["ocr"]["ocr_input_sha256"] == original_image
            and len(observations["ocr"]["ocr"]["cited_lines"]) == 4
            and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
            "The overlaid text and underlying raster did not supply separately cited observations")
    audited = call("audit", output, "--current-revision", CURRENT)
    require(audited["vigencia"] == "VIGENTE" and audited["audit_bot"] == "B16"
            and audited["simulation_result"] == "FAIL", "The overlay could not replay from source")

    def pending_variant(name, raw, blocker):
        plan = temp / f"{name}.pdf"
        plan.write_bytes(raw)
        spec = deepcopy(case)
        spec["local_sources"]["plan_pdf"]["sha256"] = sha(raw)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(spec))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(spec, f"SYNTHETIC-D133-{name}")))
        result = run_case(case_path, temp / name, reference, plan)
        readings = result["local_review"]["bots"]
        require(result["simulation_result"] == "PENDING" and result["scenarios"] == matching["scenarios"]
                and readings["B06"]["blockers"] == [blocker] and "value" not in readings["B06"]
                and readings["B07"]["blockers"] == ["both_plan_readings_required"]
                and readings["B09"]["state"] == "PENDING",
                "An incomplete overlay changed cash or supplied a reconciled value")
        return readings["B06"]["observations"]

    native_changed = pending_variant("conflicting-text", overlay_pdf(SCAN_PLAN, "1,050.00", visible=True),
                                     "overlay_observations_conflict")
    require(amount(native_changed["text"]["value"]) == 1050 and amount(native_changed["ocr"]["value"]) == 1000
            and native_changed["ocr"]["ocr_input_sha256"] == original_image,
            "Changing the overlaid text influenced OCR of the original image")
    raster_changed = pending_variant("conflicting-image", overlay_pdf(CONFLICT), "overlay_observations_conflict")
    require(amount(raster_changed["text"]["value"]) == 1000 and amount(raster_changed["ocr"]["value"]) == 1050,
            "The image disagreement was overwritten with the text")
    native_missing = pending_variant("missing-text-area", overlay_pdf(SCAN_PLAN, None), "overlay_both_observations_required")
    require(native_missing["text"]["blockers"] == ["explicit_area_missing_or_ambiguous"]
            and amount(native_missing["ocr"]["value"]) == 1000, "The OCR result filled in a missing text value")
    raster_missing = pending_variant("missing-image-area", overlay_pdf(MISSING), "overlay_both_observations_required")
    require(raster_missing["ocr"]["blockers"] == ["explicit_area_missing_or_ambiguous"]
            and amount(raster_missing["text"]["value"]) == 1000, "The text filled in a missing OCR value")
    with patch.dict(os.environ, {"TESSDATA_PREFIX": str(temp / "missing-runtime")}):
        unavailable = pending_variant("missing-runtime", PLAN.read_bytes(), "overlay_both_observations_required")
    require(unavailable["ocr"]["blockers"] == ["scan_ocr_runtime_missing"]
            and amount(unavailable["text"]["value"]) == 1000, "Missing OCR discarded the text observation")
    return dict(status="passed", decision="PENDING", full_workbook_cases=6, pending_cases=5,
                overlaid_text_cannot_change_ocr_input=True, both_conflict_directions_preserved=True,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited matching overlay case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d133-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
