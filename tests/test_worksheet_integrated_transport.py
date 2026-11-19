"""Exact long rationals from registered XLSX/PDF intake to the audited decision."""
from copy import deepcopy
from fractions import Fraction
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

from check_worksheet_construction_pdf_D157 import ORDER, pages
from check_worksheet_evidence_pdf_D156 import evidence_pdf
from check_worksheet_evidence_jpeg_D161 import UPRIGHT, jpeg_bundle
from check_worksheet_evidence_progressive_order_D164 import SCAN_ENCODINGS, SHUFFLED
from check_worksheet_evidence_scan_D158 import add_scan
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, read_package, verify_package
from test_worksheet_exact_cash import cash_values
from worksheet_exact_cash_D263 import exact_fraction
from worksheet_integrated_transport_D264 import PROFILE, integrated_engines
from worksheet_intake_D198 import assemble, register


def numeric_cells(raw, values):
    """Write actual numeric cells; a missing value is an absent cell, never zero."""
    output = BytesIO()
    with ZipFile(BytesIO(raw)) as src, ZipFile(output, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                sheet = ET.fromstring(data)
                ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                for row in sheet.iter(ns+"row"):
                    for cell in list(row):
                        key = cell.attrib.get("r")
                        if key not in values:
                            continue
                        if values[key] is None:
                            row.remove(cell)
                        else:
                            for child in list(cell):
                                cell.remove(child)
                            cell.set("t", "n")
                            ET.SubElement(cell, ns+"v").text = values[key]
                data = ET.tostring(sheet, encoding="utf-8", xml_declaration=True)
            dst.writestr(item, data)
    return output.getvalue()


def revised_evidence(settings):
    records = pages(settings)
    for role, rate in (("base", "0.0501"), ("downside", "0.0651")):
        records[role] = [f"C69 | annual_nominal_fraction | {rate}" if line.startswith("C69 |") else line
                         for line in records[role]]
    upright = PdfWriter()
    font = ImageFont.truetype("DejaVuSansMono.ttf", size=24)
    originals = PdfReader(UPRIGHT, strict=True).pages
    for index, role in enumerate(ORDER):
        if role not in ("base", "downside"):
            upright.add_page(originals[index])
        else:
            image = Image.new("L", (1900, 1100), 255)
            draw = ImageDraw.Draw(image)
            for index, line in enumerate(records[role]):
                draw.text((36, 35+52*index), line, font=font, fill=0)
            add_scan(upright, *image.size, image.tobytes())
    buffer = BytesIO()
    upright.write(buffer)
    bundle = jpeg_bundle(buffer.getvalue(), progressive_roles=SCAN_ENCODINGS, oriented=True,
                         rgb_quality=98, jpeg_roles=SCAN_ENCODINGS)
    reader, writer = PdfReader(BytesIO(bundle), strict=True), PdfWriter()
    for role in SHUFFLED:
        writer.add_page(reader.pages[ORDER.index(role)])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class IntegratedTransportTests(TestCase):
    def test_configuration_and_source_mismatch_never_fall_back(self):
        valid = dict(profile=PROFILE, source_ref="SYNTHETIC-D264-transport")
        for raw in (None, {}, valid | dict(source_ref=""), valid | dict(extra=True)):
            with self.assertRaises(ValueError):
                integrated_engines(raw, technical=True)
        with self.assertRaises(ValueError):
            integrated_engines(valid, technical=False)
        with patch("worksheet_integrated_transport_D264.SCREENING_SHA256", "0"*64):
            with self.assertRaisesRegex(ValueError, "screening_revision_unconfirmed"):
                integrated_engines(valid, technical=True)
        _, private, descriptor = integrated_engines(valid, technical=True)
        from miniuw_foundation import screening
        self.assertIsNot(private.__globals__, vars(screening))
        self.assertIs(private.__code__, screening.simulate_screening.__code__)
        self.assertIs(private.__globals__["_fraction"], exact_fraction)
        self.assertEqual(descriptor["rounding"], "none")
        self.assertNotEqual(private.__globals__["ENGINE_SHA256"], screening.ENGINE_SHA256)

    def test_revised_numeric_xlsx_and_scanned_bank_source_reach_the_integrated_output(self):
        with TemporaryDirectory(prefix="miniuw-d264-") as temp:
            root = Path(temp)
            settings = settings_for_acceptance()
            sources = source_files(root/"sources")
            registration = register(sources, "SYNTHETIC-D264-original")
            assemble(settings, registration, sources, root/"legacy")
            original = json.loads((root/"legacy/results.json").read_bytes())
            settings["rent_inputs"]["cash_transport"] = dict(profile=PROFILE, source_ref="SYNTHETIC-D264-exact-intake")
            assemble(settings, registration, sources, root/"equivalent")
            equivalent = json.loads((root/"equivalent/results.json").read_bytes())
            for name in ("Base", "Downside"):
                self.assertEqual(cash_values(original["scenarios"][name]["cash_per_usd_10"]),
                                 cash_values(equivalent["scenarios"][name]["cash_per_usd_10"]))
            for name, rate in (("Base", "0.0501"), ("Downside", "0.0651")):
                key = "workbook_raw" if name == "Base" else "downside_workbook_raw"
                sources[key] = numeric_cells(sources[key], {"C69":rate})
            sources["evidence_raw"] = revised_evidence(settings)
            for name in ("Base", "Downside"):
                # Explicit new synthetic annex confirming the revised PDF; never relink real evidence automatically.
                settings["rent_inputs"]["bank_debt_yield"][name].update(
                    quote_source_sha256=sha(sources["evidence_raw"]), source_ref=f"SYNTHETIC-D264-{name}-revised-annex")
            registration = register(sources, "SYNTHETIC-D264-revised-sources")
            before = deepcopy(settings)
            assemble(settings, registration, sources, root/"revised")
            self.assertEqual(before, settings)
            saved = read_package(root/"revised")
            result = json.loads(saved["results.json"])
            self.assertEqual(result["decision"], "PENDING")
            self.assertFalse(result["real_decisions_enabled"])
            self.assertFalse(result["deployment_enabled"])
            self.assertFalse(result["local_review"]["blockers"], result["local_review"]["blockers"])
            for name, rate in (("Base", "0.0501"), ("Downside", "0.0651")):
                view = result["scenarios"][name]
                self.assertFalse(view["blockers"], view["blockers"])
                self.assertIsNotNone(view["cash_per_usd_10"])
                self.assertNotEqual(cash_values(view["cash_per_usd_10"]),cash_values(original["scenarios"][name]["cash_per_usd_10"]))
                quote = view["permanent_loan"]["bank_document_binding"]["quote"]
                self.assertEqual(exact_fraction(quote["document"]["annual_nominal_rate"]),Fraction(rate))
                self.assertEqual(quote["source_sha256"],sha(sources["evidence_raw"]))
                self.assertEqual(view["exact_cash_transport"]["profile"],PROFILE)
                self.assertIsNotNone(view["post_refinance_coc"]["value"])
            self.assertGreater(len(result["scenarios"]["Base"]["dated_debt_service"]["principal_due"]["numerator"]),256)
            self.assertEqual(verify_package(root/"revised", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"],"VIGENTE")
            # A broken configuration blocks both cash outputs; no silent legacy fallback.
            invalid = deepcopy(settings)
            invalid["rent_inputs"]["cash_transport"]["source_ref"] = ""
            assemble(invalid, registration, sources, root/"invalid")
            pending = json.loads((root/"invalid/results.json").read_bytes())
            for view in pending["scenarios"].values():
                self.assertIsNone(view["cash_per_usd_10"])
                self.assertIn("integrated_exact_transport_configuration_unconfirmed",view["blockers"])
