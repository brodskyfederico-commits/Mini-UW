"""Replay mixed RGB and grayscale financial evidence and verify its blocking controls."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import events
from check_worksheet_construction_pdf_D157 import BOOKS, ORDER, PLAN, pages, run_package
from check_worksheet_evidence_oriented_D159 import (
    CASE as PRIOR, CURRENT as PRIOR_CURRENT, PRIOR_SCAN as UPRIGHT, SCAN as PRIOR_SCAN, oriented_bundle,
)
from check_worksheet_evidence_scan_D158 import variant_bundle
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, WORKBOOK_COLOR_EVIDENCE_SCHEMA, build_results, encoded
from worksheet_evidence_scan_D158 import COLOR_PROFILE
from worksheet_plan_scan_D131 import full_page_image
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-evidence-color-D160.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D160.json"
SCAN = ROOT / "templates/synthetic-color-evidence-D160.pdf"
COLOR_ROLES = {"construction_downside", "gc", "base"}
def color_sample(gray):
    shift = min(gray, (255 - gray) // 2)
    return bytes((gray + 2 * shift, gray - shift, gray - (11 * shift + 57) // 114))


PALETTE = tuple(color_sample(gray) for gray in range(256))
LOW_CONFIDENCE_PALETTE = tuple(bytes((dark * (255 - gray) + light * gray + 127) // 255
                                     for dark, light in zip((8, 38, 92), (255, 250, 235), strict=True))
                               for gray in range(256))


def tinted_bundle(raw, *, unsupported=None, palette=PALETTE):
    writer = PdfWriter(clone_from=PdfReader(BytesIO(raw), strict=True))
    writer.add_metadata({"/Title": "Mini-UW D160 synthetic mixed RGB and grayscale financial scans"})
    for role, page in zip(ORDER, writer.pages, strict=True):
        if role not in COLOR_ROLES:
            continue
        pgm = full_page_image(page, allow_text_layer=True, allowed_rotation=page.rotation, allow_crop_box=True)
        pixels = pgm.split(b"\n", 3)[3]
        resources = page["/Resources"]["/XObject"].get_object()
        name, = resources
        original = resources[name]
        replacement = DecodedStreamObject()
        replacement.update({key: value for key, value in original.items() if key not in ("/Filter", "/ColorSpace", "/Length")})
        if role == unsupported:
            replacement[NameObject("/ColorSpace")] = NameObject("/DeviceCMYK")
            replacement.set_data(b"".join(bytes((0, 0, 0, 255 - value)) for value in pixels))
        else:
            replacement[NameObject("/ColorSpace")] = NameObject("/DeviceRGB")
            replacement.set_data(b"".join(map(palette.__getitem__, pixels)))
        resources[name] = writer._add_object(replacement.flate_encode())
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def case_for(raw):
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_COLOR_EVIDENCE_SCHEMA
    case["local_sources"]["evidence_pdf"].update(profile=COLOR_PROFILE, sha256=sha(raw))
    return case


def verify(temp, output):
    raw = SCAN.read_bytes()
    original = PRIOR_SCAN.read_bytes()
    case = case_for(raw)
    require(raw == tinted_bundle(original) and CASE.read_bytes() == encoded(case), "Fixture drift")
    run_package(PRIOR, PRIOR_CURRENT, PRIOR_SCAN, temp / "D159")
    previous = json.loads((temp / "D159/results.json").read_bytes())
    status = run_package(CASE, CURRENT, SCAN, output)
    result = json.loads((output / "results.json").read_bytes())
    require(result["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["real_decisions_enabled"] and not result["deployment_enabled"]
            and not result["local_review"]["blockers"] and not result["revision_review"]["blockers"],
            "The synthetic color evidence did not reach the calculation")
    budget = result["local_review"]["bots"]["B08"]
    financial = (budget["gc_pdf"], *budget["bank_pdf_by_scenario"].values(), *budget["construction_pdf_by_scenario"].values())
    original_pages = PdfReader(BytesIO(original), strict=True).pages
    for reading in financial:
        page = original_pages[reading["page"] - 1]
        role = ORDER[reading["page"] - 1]
        pgm = full_page_image(page, allowed_rotation=page.rotation, allow_crop_box=True)
        _, dimensions, maximum, pixels = pgm.split(b"\n", 3)
        if role in COLOR_ROLES:
            raw_color = b"P6\n" + dimensions + b"\n" + maximum + b"\n" + b"".join(map(PALETTE.__getitem__, pixels))
            palette_gray = bytes(round((299 * r + 587 * g + 114 * b) / 1000) for r, g, b in PALETTE)
            expected_gray = b"P5\n" + dimensions + b"\n" + maximum + b"\n" + pixels.translate(palette_gray)
            require(reading["source_color_space"] == "/DeviceRGB" and reading["source_raster_sha256"] == sha(raw_color)
                    and reading["grayscale_input_sha256"] == sha(expected_gray)
                    and reading["source_raster_sha256"] != reading["grayscale_input_sha256"], "RGB conversion lost provenance")
        else:
            require(reading["source_color_space"] == "/DeviceGray" and reading["source_raster_sha256"] == sha(pgm)
                    and reading["grayscale_input_sha256"] == sha(pgm), "Grayscale image was changed")
        require(reading["ocr_region_basis"] == "cropped_rotation_normalized_pixels" and reading["ocr"]["cited_lines"],
                "The visible geometry or citations were lost")
    for name, scenario in result["scenarios"].items():
        before = previous["scenarios"][name]
        quote = scenario["document_financial_binding"]["gc_quote"]
        require(quote["source_color_space"] == "/DeviceRGB" and quote["source_raster_sha256"] == budget["gc_pdf"]["source_raster_sha256"]
                and scenario["capacity"]["maximum_principal_capacity"] == before["capacity"]["maximum_principal_capacity"],
                "The quote lost RGB provenance or changed capacity")
        for kind in ("contribution", "distribution"):
            require(events(scenario["cash_per_usd_10"], kind) == events(before["cash_per_usd_10"], kind),
                    "A change of color altered financial cash")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and (output / EVIDENCE_FILE).read_bytes() == raw and audit["pdf_sha256"] == status["pdf_sha256"],
            "The original mixed PDF did not replay")
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()
    upright = UPRIGHT.read_bytes()
    expected = pages(case)

    def pending(bundle):
        changed = case_for(bundle)
        revision = encoded(snapshot_for_case(changed, "SYNTHETIC-D160-variant"))
        view, _ = build_results(encoded(changed), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                current_revision_raw=revision, plan_raw=plan, evidence_raw=bundle)
        require(view["decision"] == view["simulation_result"] == "PENDING", "A bad color scan released a decision")
        return view

    clipped = pending(tinted_bundle(oriented_bundle(upright, crop=("gc", (16, 18, 1177, 1060)))))
    quote = clipped["local_review"]["bots"]["B08"]["gc_pdf"]
    require(quote["source_color_space"] == "/DeviceRGB" and quote["blockers"] == ["evidence_scan_crop_hides_or_changes_required_rows"]
            and all(row["cash_per_usd_10"] is None for row in clipped["scenarios"].values()), "RGB crop hid digits without a block")
    changed_lines = [line.replace("0.10", "0.11") if line.startswith("C52 | ") else line
                     for line in expected["construction_downside"]]
    conflict = pending(tinted_bundle(oriented_bundle(upright, overlay=("construction_downside", changed_lines))))
    loan = conflict["local_review"]["bots"]["B08"]["construction_pdf_by_scenario"]["Downside"]
    require(loan["source_color_space"] == "/DeviceRGB" and loan["blockers"] == ["evidence_scan_and_text_disagree"]
            and [amount(loan["readings"][kind]["document"]["annual_interest"]) for kind in ("ocr", "text")]
                == [Fraction("0.10"), Fraction("0.11")]
            and conflict["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and conflict["scenarios"]["Base"]["cash_per_usd_10"] is not None, "The text overlay overrode an RGB loan")
    missing_index = expected["construction_downside"].index("C52 | annual_nominal_fraction | 0.10")
    missing = pending(tinted_bundle(oriented_bundle(variant_bundle(upright, blank=("construction_downside", missing_index)))))
    loan = missing["local_review"]["bots"]["B08"]["construction_pdf_by_scenario"]["Downside"]
    require(loan["blockers"] == ["construction_pdf_convention_or_inventory_unconfirmed"]
            and missing["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and missing["scenarios"]["Base"]["cash_per_usd_10"] is not None, "Missing RGB loan field was supplied")
    with_text = oriented_bundle(upright, overlay=("construction_downside", expected["construction_downside"]))
    unsupported = pending(tinted_bundle(with_text, unsupported="construction_downside"))
    require("B08:Downside:evidence_financial_scan_required_or_layout_unsupported" in unsupported["local_review"]["blockers"]
            and unsupported["scenarios"]["Downside"]["cash_per_usd_10"] is None
            and unsupported["scenarios"]["Base"]["cash_per_usd_10"] is not None, "A text overlay substituted unsupported color evidence")
    weak = pending(tinted_bundle(original, palette=LOW_CONFIDENCE_PALETTE))
    require("B08:gc_budget:evidence_scan_ocr_confidence_below_declared_minimum" in weak["local_review"]["blockers"]
            and all(row["cash_per_usd_10"] is None for row in weak["scenarios"].values()),
            "Color distortion escaped the OCR confidence gate")
    return dict(status="passed", decision="PENDING", evidence_pages=6, scanned_pages=5, rgb_pages=3, pending_cases=5,
                page_count=1, pdf_sha256=result["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d160-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
