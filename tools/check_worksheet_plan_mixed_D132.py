"""Replay mixed PDF plans with isolated text and OCR readings."""
from argparse import ArgumentParser
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os

from pypdf import PdfReader, PdfWriter

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_pdf_D130 import PLAN as TEXT_PLAN, run_case
from check_worksheet_plan_scan_D131 import CONFLICT, MISSING, PLAN as SCAN_PLAN
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_plan_mixed_D132 import read_mixed_plan
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-mixed-chain-D132.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D132.json"
PLAN = ROOT / "templates/synthetic-mixed-plan-D132.pdf"


def make_pdf(first, second, *, overlay=None):
    writer = PdfWriter()
    writer.add_page(first)
    page = writer.add_page(second)
    if overlay is not None:
        page.merge_page(overlay)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    bots = matching["local_review"]["bots"]
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"]
            and bots["B03"]["documents"]["plan_pdf"]["kind"] == "synthetic_mixed_pdf_plan"
            and (bots["B05"]["sheet"], bots["B05"]["page"], bots["B05"]["extraction_method"]) == ("A101", 1, "text")
            and (bots["B06"]["sheet"], bots["B06"]["page"], bots["B06"]["extraction_method"]) == ("A601", 2, "ocr")
            and "ocr" not in bots["B05"] and len(bots["B06"]["ocr"]["cited_lines"]) == 4
            and all(bots[name]["source_sha256"] == sha(PLAN.read_bytes()) for name in ("B05", "B06"))
            and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
            "The mixed plan lost a cited reading or its GC reconciliation")
    audited = call("audit", output, "--current-revision", CURRENT)
    require(audited["vigencia"] == "VIGENTE" and audited["audit_bot"] == "B16"
            and audited["simulation_result"] == "FAIL", "The mixed plan could not replay from source")

    def run_variant(name, raw, expected, *, routes=None):
        plan = temp / f"{name}.pdf"
        plan.write_bytes(raw)
        spec = deepcopy(case)
        binding = spec["local_sources"]["plan_pdf"]
        binding["sha256"] = sha(raw)
        if routes is not None:
            binding["page_routes"] = routes
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(spec))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(spec, f"SYNTHETIC-D132-{name}")))
        result = run_case(case_path, temp / name, reference, plan)
        require(result["simulation_result"] == expected and result["scenarios"] == matching["scenarios"],
                "The mixed reader changed independent cash or acquired an incorrect verdict")
        return result["local_review"]["bots"]

    native, scan = (PdfReader(path, strict=True).pages for path in (TEXT_PLAN, SCAN_PLAN))
    reversed_routes = {"A101": {"page": 1, "method": "ocr"}, "A601": {"page": 2, "method": "text"}}
    reversed_modes = run_variant("reversed-modes", make_pdf(scan[0], native[1]), "FAIL", routes=reversed_routes)
    require(reversed_modes["B05"]["extraction_method"] == "ocr" and reversed_modes["B06"]["extraction_method"] == "text"
            and amount(reversed_modes["B07"]["value"]) == 1000 and amount(reversed_modes["B09"]["difference"]) == 0,
            "The mode was hardwired to a particular sheet")

    missing_page = PdfReader(MISSING, strict=True).pages[1]
    missing = run_variant("missing-area", make_pdf(native[0], missing_page), "PENDING")
    require(missing["B05"]["state"] == "checked_synthetic"
            and missing["B06"]["blockers"] == ["explicit_area_missing_or_ambiguous"]
            and missing["B07"]["blockers"] == ["both_plan_readings_required"], "A missing area acquired a fallback")
    conflict_page = PdfReader(CONFLICT, strict=True).pages[1]
    conflict = run_variant("conflict", make_pdf(native[0], conflict_page), "PENDING")
    require(conflict["B07"]["blockers"] == ["plan_readings_conflict"]
            and [(row["extraction_method"], amount(row["value"])) for row in conflict["B07"]["readings"]]
            == [("text", 1000), ("ocr", 1050)]
            and conflict["B09"]["state"] == "PENDING", "A conflict lost either observation")

    overlay = run_variant("text-overlay", make_pdf(native[0], scan[1], overlay=native[1]), "PENDING")
    require(overlay["B05"]["state"] == "checked_synthetic"
            and overlay["B06"]["blockers"] == ["mixed_ocr_page_layout_unsupported"],
            "A text layer over an image was accepted as a supported source")
    with patch.dict(os.environ, {"TESSDATA_PREFIX": str(temp / "missing-runtime")}):
        runtime_missing = run_variant("missing-runtime", PLAN.read_bytes(), "PENDING")
    require(runtime_missing["B05"]["state"] == "checked_synthetic" and runtime_missing["B06"]["blockers"]
            == ["scan_ocr_runtime_missing"], "A missing OCR runtime invalidated the independent text reading")

    spec = case["local_sources"]["plan_pdf"]
    swapped = {"A101": {"page": 2, "method": "ocr"}, "A601": {"page": 1, "method": "text"}}
    wrong_sheet = read_mixed_plan(PLAN.read_bytes(), spec | {"page_routes": swapped})
    require(all(wrong_sheet[name]["blockers"] == ["mixed_sheet_identity_missing_or_ambiguous"] for name in ("B05", "B06")),
            "A page was assigned to the wrong sheet")
    return dict(status="passed", decision="PENDING", full_workbook_cases=6, pending_cases=4,
                both_mode_assignments_verified=True, conflicting_observations_preserved=True,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited mixed plan case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d132-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
