"""Replay scanned GC and loan evidence and exercise strict OCR discrepancy gates."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import events
from check_worksheet_construction_pdf_D157 import BOOKS, CASE as PRIOR, CURRENT as PRIOR_CURRENT, EVIDENCE as PRIOR_EVIDENCE, PLAN, ORDER, pages
from check_worksheet_construction_pdf_D157 import run_package
from check_worksheet_evidence_pdf_D156 import evidence_pdf
from check_worksheet_plan_overlay_D133 import add_text_overlay
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_SCANNED_EVIDENCE_SCHEMA, build_results, encoded
from worksheet_evidence_pdf_D156 import read_evidence_pdf
from worksheet_evidence_scan_D158 import PROFILE
from worksheet_plan_scan_D131 import full_page_image
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-evidence-scan-D158.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D158.json"
SCAN = ROOT / "templates/synthetic-scanned-evidence-D158.pdf"
REVISION = "SYNTHETIC-D158-EVIDENCE"


def case_for(raw, minimum=60):
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_SCANNED_EVIDENCE_SCHEMA
    local = case["local_sources"]
    local["revision"] = REVISION
    local["evidence_pdf"] = dict(profile=PROFILE, sha256=sha(raw),
                                 ocr=local["plan_pdf"]["ocr"] | {"minimum_word_confidence": minimum})
    return case


def add_scan(writer, width, height, pixels):
    page = writer.add_blank_page(width=792, height=612)
    image = DecodedStreamObject()
    image.set_data(pixels)
    image.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                  NameObject("/Width"): NumberObject(width), NameObject("/Height"): NumberObject(height),
                  NameObject("/ColorSpace"): NameObject("/DeviceGray"), NameObject("/BitsPerComponent"): NumberObject(8)})
    resources = DictionaryObject({NameObject("/I"): writer._add_object(image.flate_encode())})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): resources})
    stream = DecodedStreamObject()
    stream.set_data(b"q\n792 0 0 612 0 0 cm\n/I Do\nQ\n")
    page[NameObject("/Contents")] = writer._add_object(stream)
    return page


def variant_bundle(raw, *, blank=None, overlay=None, text_only=None, duplicate=None):
    reader = PdfReader(BytesIO(raw), strict=True)
    writer = PdfWriter()
    for role, page in zip(ORDER, reader.pages, strict=True):
        if blank and role == blank[0]:
            _, dims, _, pixels = full_page_image(page).split(b"\n", 3)
            width, height = map(int, dims.split())
            start, end = (35 + 52 * blank[1]) * width, (35 + 52 * (blank[1] + 1)) * width
            add_scan(writer, width, height, pixels[:start] + b"\xff" * (end - start) + pixels[end:])
        elif text_only and role == text_only[0]:
            native = evidence_pdf({role: text_only[1]}, (role,))
            writer.add_page(PdfReader(BytesIO(native), strict=True).pages[0])
        elif duplicate and role == duplicate[0]:
            writer.add_page(reader.pages[ORDER.index(duplicate[1])])
        else:
            clone = writer.add_page(page)
            if overlay and role == overlay[0]:
                add_text_overlay(writer, clone, [(560 - 22 * index, line) for index, line in enumerate(overlay[1])])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def verify(temp, output):
    raw = SCAN.read_bytes()
    case = case_for(raw)
    require(CASE.read_bytes() == encoded(case), "Scan case fixture drift")
    expected_pages = pages(case)
    pdf = PdfReader(SCAN, strict=True)
    require(len(pdf.pages) == 6 and all(not (pdf.pages[index].extract_text() or "").strip()
                                       and full_page_image(pdf.pages[index]) is not None for index in range(1, 6)),
            "A financial fixture was not a scan-only PDF page")
    run_package(PRIOR, PRIOR_CURRENT, PRIOR_EVIDENCE, temp / "D157")
    prior = json.loads((temp / "D157/results.json").read_bytes())
    status = run_package(CASE, CURRENT, SCAN, output)
    result = json.loads((output / "results.json").read_bytes())
    bots = result["local_review"]["bots"]
    require(result["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["real_decisions_enabled"] and not result["deployment_enabled"]
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"],
            "Verified OCR did not reach the synthetic calculation")
    sources = [bots["B08"]["gc_pdf"], *bots["B08"]["bank_pdf_by_scenario"].values(),
               *bots["B08"]["construction_pdf_by_scenario"].values()]
    for source in sources:
        page = source["page"]
        evidence = source["ocr"]["cited_lines"]
        require(source["extraction_method"] == "ocr" and source["ocr_input_sha256"] == sha(full_page_image(pdf.pages[page - 1]))
                and [row["text"] for row in evidence] == expected_pages[ORDER[page - 1]]
                and all(len(row["pixel_region"]) == 4 for row in evidence), "OCR citations did not reproduce the raster or fixture")
    for name, scenario in result["scenarios"].items():
        previous = prior["scenarios"][name]
        quote = scenario["document_financial_binding"]["gc_quote"]
        require(quote["page"] == 4 and quote["ocr_citation"]["text"].startswith(f"Vertical {name} | ")
                and quote["ocr_input_sha256"] == bots["B08"]["gc_pdf"]["ocr_input_sha256"]
                and scenario["permanent_loan"]["bank_document_binding"]["quote"]["extraction_method"] == "ocr"
                and scenario["construction_financing"]["bank_document_binding"]["quote"]["extraction_method"] == "ocr",
                "Scanned evidence did not propagate to the budget and debt producers")
        for kind in ("contribution", "distribution"):
            require(events(scenario["cash_per_usd_10"], kind) == events(previous["cash_per_usd_10"], kind),
                    "Identical scan and text values changed cash")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and (output / EVIDENCE_FILE).read_bytes() == raw and status["pdf_sha256"] == audit["pdf_sha256"],
            "B16 failed to replay the original scan and PDF")
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()

    def run_variant(bundle, *, patch_case=None, minimum=60, pending=True):
        changed = case_for(bundle, minimum)
        if patch_case:
            patch_case(changed)
        revision = encoded(snapshot_for_case(changed, "SYNTHETIC-D158-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=revision, plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == "PENDING" and view["simulation_result"] == ("PENDING" if pending else "FAIL"),
                "Wrong decision for scan variant")
        return view

    overlay = run_variant(variant_bundle(raw, overlay=("base", expected_pages["base"])), pending=False)
    readback = overlay["local_review"]["bots"]["B08"]["bank_pdf_by_scenario"]["Base"]
    require(readback["extraction_method"] == "text_and_ocr" and readback["text_observation"] == readback["observations"],
            "Matching overlay did not preserve both observations")
    missing_index = expected_pages["downside"].index("C72 | multiple | 1.30")
    missing = run_variant(variant_bundle(raw, blank=("downside", missing_index)))
    missing_quote = missing["local_review"]["bots"]["B08"]["bank_pdf_by_scenario"]["Downside"]
    require(missing_quote["blockers"] == ["bank_pdf_convention_or_inventory_unconfirmed"]
            and missing["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and missing["scenarios"]["Base"]["cash_per_usd_10"] is not None, "A missing scanned bank row escaped or changed Base")
    gc_lines = [line.replace("2340000", "2340001") for line in expected_pages["gc"]]
    disagreement = run_variant(variant_bundle(raw, overlay=("gc", gc_lines)))
    conflicting = disagreement["local_review"]["bots"]["B08"]["gc_pdf"]
    require(conflicting["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(conflicting["readings"][method]["document"]["budget_by_scenario"]["Base"]["value"])
                 for method in ("ocr", "text")] == [2340000, 2340001]
            and all(row["cash_per_usd_10"] is None for row in disagreement["scenarios"].values()),
            "A conflicting GC overlay overrode the raster or lost a value")
    missing_overlay = run_variant(variant_bundle(raw, overlay=("downside", expected_pages["downside"][:-1])))
    require("B08:Downside:evidence_scan_both_readings_required" in missing_overlay["local_review"]["blockers"]
            and missing_overlay["scenarios"]["Downside"]["cash_per_usd_10"] is None, "OCR filled an incomplete overlay")
    def change_maturity(changed):
        changed["rent_inputs"]["construction_financing"]["scenarios"]["Downside"]["maturity_date"] = "2029-09-30"

    maturity = run_variant(raw, patch_case=change_maturity)["scenarios"]["Downside"]
    require(maturity["cash_per_usd_10"] is None and maturity["construction_financing"]["bank_document_binding"]["fields"]
            == ["maturity_date"], "Scanned loan terms overrode the declared construction conditions")
    weak = run_variant(raw, minimum=100)
    require("B08:Base:evidence_scan_ocr_confidence_below_declared_minimum" in weak["local_review"]["blockers"]
            and all(row["cash_per_usd_10"] is None for row in weak["scenarios"].values()), "Low-confidence OCR released cash")
    vector = run_variant(variant_bundle(raw, text_only=("downside", expected_pages["downside"])))
    require("B08:Downside:evidence_financial_scan_required_or_layout_unsupported" in vector["local_review"]["blockers"]
            and vector["scenarios"]["Downside"]["cash_per_usd_10"] is None, "A native layer bypassed required OCR")
    duplicate = run_variant(variant_bundle(raw, duplicate=("downside", "base")))
    require("B03:evidence_page_role_duplicate" in duplicate["local_review"]["blockers"], "Duplicate scanned role was accepted")
    with patch.dict(os.environ, {"TESSDATA_PREFIX": str(temp / "missing-ocr")}):
        evidence, _ = read_evidence_pdf(raw, case["local_sources"]["evidence_pdf"], REVISION,
                                        case["rent_inputs"]["deal_id"], include_construction=True, scanned=True)
        require(evidence["blockers"] == ["scan_ocr_runtime_missing"], "Missing OCR runtime did not block")
    return dict(status="passed", decision="PENDING", evidence_pages=6, scanned_pages=5, pending_cases=7,
                page_count=1, pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d158-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
