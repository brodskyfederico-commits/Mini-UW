"""Replay synthetic scans and hold ambiguous or unavailable OCR PENDING."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_pdf_D130 import PLAN as TEXT_PLAN, run_case
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_plan_scan_D131 import read_scanned_plan
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-scan-chain-D131.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D131.json"
PLAN = ROOT / "templates/synthetic-scanned-plan-D131.pdf"
MISSING = ROOT / "templates/synthetic-scanned-plan-missing-area-D131.pdf"
CONFLICT = ROOT / "templates/synthetic-scanned-plan-conflict-D131.pdf"


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    spec = case["local_sources"]["plan_pdf"]
    for scan in (PLAN, MISSING, CONFLICT):
        pages = PdfReader(scan, strict=True).pages
        require(len(pages) == 2 and all(not (page.extract_text() or "").strip() for page in pages),
                "A scan fixture contains a PDF text layer")
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    bots = matching["local_review"]["bots"]
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"]
            and bots["B03"]["documents"]["plan_pdf"]["kind"] == "synthetic_scanned_pdf_plan"
            and bots["B03"]["documents"]["plan_pdf"]["ocr"]["language_sha256"] == spec["ocr"]["language_sha256"]
            and (bots["B05"]["sheet"], bots["B05"]["page"], amount(bots["B05"]["value"])) == ("A101", 1, 1000)
            and (bots["B06"]["sheet"], bots["B06"]["page"], amount(bots["B06"]["value"])) == ("A601", 2, 1000)
            and all(len(bots[key]["ocr"]["cited_lines"]) == 4
                    and all(len(line["pixel_region"]) == 4 for line in bots[key]["ocr"]["cited_lines"])
                    for key in ("B05", "B06"))
            and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
            "OCR lost a declared value, its page citations or the GC comparison")
    audited = call("audit", output, "--current-revision", CURRENT)
    require(audited["vigencia"] == "VIGENTE" and audited["audit_bot"] == "B16"
            and audited["simulation_result"] == "FAIL", "The OCR result could not replay from the source scan")

    def pending_variant(name, scan, *, minimum=None):
        variant = deepcopy(case)
        binding = variant["local_sources"]["plan_pdf"]
        binding["sha256"] = sha(scan.read_bytes())
        if minimum is not None:
            binding["ocr"]["minimum_word_confidence"] = minimum
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(variant))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(variant, f"SYNTHETIC-D131-{name}")))
        result = run_case(case_path, temp / name, reference, scan)
        require(result["simulation_result"] == "PENDING"
                and result["screening"]["worksheet_simulation_result"] == "FAIL"
                and result["scenarios"] == matching["scenarios"],
                "An unverified scan released a verdict or changed independent cash")
        return result["local_review"]["bots"]

    missing = pending_variant("missing-area", MISSING)
    require(missing["B05"]["state"] == "checked_synthetic"
            and missing["B06"]["blockers"] == ["explicit_area_missing_or_ambiguous"]
            and missing["B07"]["blockers"] == ["both_plan_readings_required"],
            "An omitted area was filled from another sheet")
    conflict = pending_variant("conflict", CONFLICT)
    require(conflict["B07"]["blockers"] == ["plan_readings_conflict"]
            and [amount(row["value"]) for row in conflict["B07"]["readings"]] == [1000, 1050]
            and conflict["B09"]["state"] == "PENDING", "A discrepancy lost an OCR observation")
    uncertain = pending_variant("below-confidence", PLAN, minimum=100)
    require(all(uncertain[key]["blockers"] == ["scan_ocr_confidence_below_declared_minimum_or_ambiguous"]
                and "value" not in uncertain[key] and amount(uncertain[key]["ocr"]["observed_value"]) == 1000
                for key in ("B05", "B06")),
            "Low confidence supplied a verified area or lost its observation")
    with patch.dict(os.environ, {"TESSDATA_PREFIX": str(temp / "missing-runtime")}):
        no_runtime = pending_variant("missing-runtime", PLAN)
    require(no_runtime["B03"]["documents"]["plan_pdf"]["blockers"] == ["scan_ocr_runtime_missing"],
            "Missing OCR dependencies produced a verified reading")

    vector = TEXT_PLAN.read_bytes()
    require(read_scanned_plan(vector, spec | {"sha256": sha(vector)})["document"]["blockers"]
            == ["scan_image_layout_unsupported"], "The scan profile used a PDF text layer")
    wrong_data = spec | {"ocr": spec["ocr"] | {"language_sha256": "0" * 64}}
    require(read_scanned_plan(PLAN.read_bytes(), wrong_data)["document"]["blockers"] == ["scan_ocr_runtime_mismatch"],
            "Unpinned language data produced a verified reading")
    return dict(status="passed", decision="PENDING", full_workbook_cases=5, pending_cases=4,
                scans_have_no_text_layer=True, confidence_and_pixel_citations_preserved=True,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited matching scan case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d131-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
