"""Replay JPEG-compressed financial scans through OCR and discrepancy gates."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, EncodedStreamObject, NameObject, NumberObject, RectangleObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import events
from check_worksheet_construction_pdf_D157 import BOOKS, ORDER, PLAN, pages, run_package
from check_worksheet_evidence_color_D160 import CASE as PRIOR, CURRENT as PRIOR_CURRENT, SCAN as PRIOR_SCAN, PALETTE
from check_worksheet_evidence_oriented_D159 import MARGIN, PRIOR_SCAN as UPRIGHT, oriented_bundle
from check_worksheet_evidence_scan_D158 import variant_bundle
from check_worksheet_plan_overlay_D133 import add_text_overlay
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_JPEG_EVIDENCE_SCHEMA, build_results, encoded
from worksheet_evidence_jpeg_D161 import PROFILE
from worksheet_plan_scan_D131 import full_page_image
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-evidence-jpeg-D161.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D161.json"
SCAN = ROOT / "templates/synthetic-jpeg-evidence-D161.pdf"
DECODER = {"pillow_version": "13.0.0", "libjpeg_turbo_version": "3.2.0"}
JPEG_ROLES = {"gc": ("RGB", 97), "base": ("RGB", 97), "construction_base": ("L", 100)}


def jpeg_bundle(upright, *, overlay=None, truncated=None, progressive_roles=()):
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Mini-UW D161 synthetic JPEG-compressed financial evidence"})
    originals = PdfReader(BytesIO(upright), strict=True).pages
    flate = PdfReader(BytesIO(oriented_bundle(upright)), strict=True).pages
    for index, role in enumerate(ORDER):
        if role not in JPEG_ROLES:
            writer.add_page(flate[index])
            continue
        mode, quality = JPEG_ROLES[role]
        _, dimensions, _, pixels = full_page_image(originals[index]).split(b"\n", 3)
        width, height = map(int, dimensions.split())
        page = writer.add_blank_page(width=width, height=height)
        left, top, right, bottom = MARGIN
        page.cropbox = RectangleObject((left, height - bottom, right, height - top))
        if mode == "RGB":
            pixels = b"".join(map(PALETTE.__getitem__, pixels))
        source = Image.frombytes(mode, (width, height), pixels)
        buffer = BytesIO()
        source.save(buffer, "JPEG", quality=quality, subsampling=0, optimize=True,
                    progressive=role in progressive_roles)
        compressed = buffer.getvalue()
        stream = EncodedStreamObject()
        stream._data = compressed[:-32] if role == truncated else compressed
        stream.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                       NameObject("/Width"): NumberObject(width), NameObject("/Height"): NumberObject(height),
                       NameObject("/ColorSpace"): NameObject("/DeviceRGB" if mode == "RGB" else "/DeviceGray"),
                       NameObject("/BitsPerComponent"): NumberObject(8), NameObject("/Filter"): NameObject("/DCTDecode")})
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/XObject"): DictionaryObject({NameObject("/I"): writer._add_object(stream)})})
        paint = DecodedStreamObject()
        paint.set_data(f"q\n{width} 0 0 {height} 0 0 cm\n/I Do\nQ\n".encode())
        page[NameObject("/Contents")] = writer._add_object(paint)
        if overlay and role == overlay[0]:
            add_text_overlay(writer, page, [(height - 40 - 22 * offset, line) for offset, line in enumerate(overlay[1])])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def case_for(raw):
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_JPEG_EVIDENCE_SCHEMA
    case["local_sources"]["evidence_pdf"].update(profile=PROFILE, sha256=sha(raw), jpeg_decoder=DECODER.copy())
    return case


def verify(temp, output):
    upright = UPRIGHT.read_bytes()
    raw = SCAN.read_bytes()
    case = case_for(raw)
    require(raw == jpeg_bundle(upright) and encoded(case) == CASE.read_bytes(), "JPEG fixture drift")
    run_package(PRIOR, PRIOR_CURRENT, PRIOR_SCAN, temp / "D160")
    prior = json.loads((temp / "D160/results.json").read_bytes())
    status = run_package(CASE, CURRENT, SCAN, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["real_decisions_enabled"] and not result["deployment_enabled"]
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"],
            "Valid JPEGs did not reach the synthetic calculation")
    bots = result["local_review"]["bots"]
    require(bots["B03"]["documents"]["evidence_pdf"]["jpeg_decoder"] == DECODER, "Decoder runtime was not recorded")
    budget = bots["B08"]
    readings = (budget["gc_pdf"], *budget["bank_pdf_by_scenario"].values(), *budget["construction_pdf_by_scenario"].values())
    pdf = PdfReader(SCAN, strict=True)
    for reading in readings:
        index = reading["page"] - 1
        role = ORDER[index]
        if role in JPEG_ROLES:
            page = pdf.pages[index]
            require(not (page.extract_text() or "").strip(), "A JPEG fixture contains a text layer")
            image = page["/Resources"]["/XObject"]["/I"]
            jpeg = image.get_data()
            with Image.open(BytesIO(jpeg), formats=("JPEG",)) as decoded:
                header = b"P6" if decoded.mode == "RGB" else b"P5"
                raster = header + f"\n{decoded.width} {decoded.height}\n255\n".encode() + decoded.tobytes()
            require(reading["source_image_filter"] == "/DCTDecode" and reading["source_jpeg_sha256"] == sha(jpeg)
                    and reading["source_raster_sha256"] == sha(raster) != reading["source_jpeg_sha256"],
                    "JPEG stream provenance did not match the decoded raster")
        else:
            require(reading["source_image_filter"] == "/FlateDecode" and "source_jpeg_sha256" not in reading,
                    "A Flate page was relabeled as JPEG")
        require(reading["extraction_method"] == "ocr" and reading["ocr"]["cited_lines"], "Financial evidence bypassed OCR")
    for name, scenario in result["scenarios"].items():
        before = prior["scenarios"][name]
        quote = scenario["document_financial_binding"]["gc_quote"]
        require(quote["source_jpeg_sha256"] == budget["gc_pdf"]["source_jpeg_sha256"]
                and scenario["capacity"]["maximum_principal_capacity"] == before["capacity"]["maximum_principal_capacity"],
                "JPEG evidence failed to reach the quote or changed the bank capacity")
        for kind in ("contribution", "distribution"):
            require(events(scenario["cash_per_usd_10"], kind) == events(before["cash_per_usd_10"], kind),
                    "JPEG compression changed verified cash")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and (output / EVIDENCE_FILE).read_bytes() == raw and audit["pdf_sha256"] == status["pdf_sha256"],
            "B16 did not reproduce the JPEG evidence")
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()
    expected = pages(case)

    def pending(bundle, *, decoder=None):
        changed = case_for(bundle)
        if decoder is not None:
            changed["local_sources"]["evidence_pdf"]["jpeg_decoder"] = decoder
        snapshot = encoded(snapshot_for_case(changed, "SYNTHETIC-D161-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=snapshot, plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == view["simulation_result"] == "PENDING", "A bad JPEG released a decision")
        return view

    missing_index = expected["construction_base"].index("C52 | annual_nominal_fraction | 0.08")
    missing = pending(jpeg_bundle(variant_bundle(upright, blank=("construction_base", missing_index))))
    missing_loan = missing["local_review"]["bots"]["B08"]["construction_pdf_by_scenario"]["Base"]
    require(missing_loan["source_image_filter"] == "/DCTDecode" and missing_loan["blockers"]
            and not any(row["text"].startswith("C52 | ") for row in missing_loan["ocr"]["cited_lines"])
            and missing["scenarios"]["Base"]["cash_per_usd_10"] is None
            and missing["scenarios"]["Downside"]["cash_per_usd_10"] is not None, "Missing JPEG loan field was supplied")
    changed_lines = [line.replace("0.05", "0.06") if line.startswith("C69 | ") else line for line in expected["base"]]
    conflict = pending(jpeg_bundle(upright, overlay=("base", changed_lines)))
    loan = conflict["local_review"]["bots"]["B08"]["bank_pdf_by_scenario"]["Base"]
    require(loan["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(loan["readings"][method]["document"]["annual_nominal_rate"]) for method in ("ocr", "text")]
                == [Fraction("0.05"), Fraction("0.06")]
            and conflict["scenarios"]["Base"]["cash_per_usd_10"] is None
            and conflict["scenarios"]["Downside"]["cash_per_usd_10"] is not None, "Text overrode a conflicting JPEG")
    changed_quote = [line.replace("2340000", "2340001") if line.startswith("Vertical Base | ") else line
                     for line in expected["gc"]]
    gc_conflict = pending(jpeg_bundle(upright, overlay=("gc", changed_quote)))
    quote = gc_conflict["local_review"]["bots"]["B08"]["gc_pdf"]
    require(quote["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(quote["readings"][method]["document"]["budget_by_scenario"]["Base"]["value"])
                 for method in ("ocr", "text")] == [2340000, 2340001]
            and all(row["cash_per_usd_10"] is None for row in gc_conflict["scenarios"].values()),
            "A conflicting JPEG quote supplied a budget")
    truncated = pending(jpeg_bundle(upright, overlay=("base", expected["base"]), truncated="base"))
    require("B08:Base:evidence_financial_scan_required_or_layout_unsupported" in truncated["local_review"]["blockers"]
            and truncated["scenarios"]["Base"]["cash_per_usd_10"] is None, "The text layer replaced truncated JPEG bytes")
    mismatch = pending(raw, decoder=DECODER | {"libjpeg_turbo_version": "unverified"})
    require("B03:evidence_jpeg_decoder_mismatch" in mismatch["local_review"]["blockers"]
            and all(row["cash_per_usd_10"] is None for row in mismatch["scenarios"].values()), "A different decoder passed")
    return dict(status="passed", decision="PENDING", evidence_pages=6, scanned_pages=5, jpeg_pages=3, pending_cases=5,
                page_count=1, pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d161-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
