"""Check delivery of the current synthetic integrated Mini-UW report."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import subprocess
import sys
import unittest

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import miniuw_worksheet_v1 as worksheet
from check_lorena_criteria_D192 import change_cells
from check_worksheet_florida_tax_D203 import settings_for_tax
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from worksheet_intake_D198 import assemble, register


class WorksheetDeliveryTests(unittest.TestCase):
    def test_only_current_audited_pdf_with_both_cash_flows_is_delivered(self):
        with TemporaryDirectory(prefix="miniuw-d216-") as temp:
            root = Path(temp)
            settings = settings_for_acceptance()
            sources = source_files(root / "sources")
            current = root / "vigente.json"
            deliverable = root / "entrega.pdf"
            command = [sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "deliver"]

            def make_package(label, case, documents=sources):
                directory = root / label
                result = assemble(case, register(documents, f"SYNTHETIC-D216-{label}"), documents, directory)
                return directory, result["simulation_result"], worksheet.read_package(directory)

            older, older_state, older_files = make_package("original", settings)
            self.assertEqual(older_state, "PASS")
            older_page, = PdfReader(BytesIO(older_files["MiniUW_Resumen.pdf"])).pages
            self.assertNotIn("[PASS]", older_page.extract_text())
            adverse = dict(sources, criteria_raw=change_cells(sources["criteria_raw"], {"G11": "<= 50 %", "H11": "> 65 %"}))
            newer, newer_state, newer_files = make_package("adverse", settings, adverse)
            self.assertEqual(newer_state, "FAIL")
            current.write_bytes(newer_files[worksheet.CURRENT_REVISION_FILE])
            baseline, revised = (json.loads(files["results.json"]) for files in (older_files, newer_files))
            self.assertEqual(baseline["scenarios"], revised["scenarios"])

            denied = subprocess.run([*command, str(older), "--current-revision", str(current),
                                     "--output", str(deliverable)], capture_output=True, check=False)
            self.assertEqual(denied.returncode, 2)
            self.assertEqual(json.loads(denied.stderr)["decision"], "PENDING")
            self.assertIn(b"archived_revision_differs_from_current", denied.stderr)
            self.assertFalse(deliverable.exists())

            receipt = json.loads(subprocess.check_output([*command, str(newer), "--current-revision", str(current),
                                                          "--output", str(deliverable)]))
            self.assertEqual(receipt["status"], "delivered_synthetic_pdf")
            self.assertEqual((receipt["decision"], receipt["simulation_result"], receipt["vigencia"]),
                             ("PENDING", "FAIL", "VIGENTE"))
            self.assertEqual(receipt["revision_sha256"], sha256(current.read_bytes()).hexdigest())
            raw = deliverable.read_bytes()
            self.assertEqual(raw, newer_files["MiniUW_Resumen.pdf"])
            self.assertEqual(receipt["pdf_sha256"], sha256(raw).hexdigest())
            page, = PdfReader(deliverable).pages
            text = page.extract_text()
            for marker in ("Decisión real PENDING", "Criterios de inversión reales PENDING", "USD 10", "18,06", "6,08",
                           "2028-12-30", "2029-06-30", "12,11"):
                self.assertIn(marker, text)
            for marker in ("Dictamen simulado", "[PASS]", "[FAIL]", "último antes de FAIL"):
                self.assertNotIn(marker, text)

            legacy_files, legacy_result = worksheet.build_package(
                newer_files["case.json"], current_revision_raw=newer_files[worksheet.CURRENT_REVISION_FILE],
                package_schema=worksheet.PACKAGE_SCHEMA, **adverse)
            self.assertEqual(legacy_result["scenarios"], revised["scenarios"])
            self.assertEqual(legacy_result["screening"], revised["screening"])
            archived = root / "archived"
            archived.mkdir()
            for name, content in legacy_files.items():
                (archived / name).write_bytes(content)
            archived_page, = PdfReader(BytesIO(legacy_files["MiniUW_Resumen.pdf"])).pages
            self.assertIn("Dictamen simulado FAIL", archived_page.extract_text())
            corrected = root / "legacy_entrega.pdf"
            legacy_receipt = worksheet.deliver_package(archived, corrected, current)
            self.assertEqual(legacy_receipt["audited_pdf_sha256"], sha256(legacy_files["MiniUW_Resumen.pdf"]).hexdigest())
            self.assertEqual(legacy_receipt["pdf_sha256"], sha256(raw).hexdigest())
            self.assertEqual(corrected.read_bytes(), raw)
            self.assertEqual(worksheet.read_package(archived), legacy_files)

            candidate = root / "bloqueado.pdf"
            existing_revision = current.read_bytes()
            with patch.object(worksheet, "read_current_revision",
                              side_effect=[existing_revision, older_files[worksheet.CURRENT_REVISION_FILE]]):
                with self.assertRaisesRegex(ValueError, "cambió durante la entrega"):
                    worksheet.deliver_package(newer, candidate, current)
            self.assertFalse(candidate.exists())
            with self.assertRaisesRegex(ValueError, "destino nuevo"):
                worksheet.deliver_package(newer, deliverable, current)
            self.assertEqual(deliverable.read_bytes(), raw)

            pdf = newer / "MiniUW_Resumen.pdf"
            pdf.write_bytes(raw + b" ")
            with self.assertRaisesRegex(ValueError, "source-first replay"):
                worksheet.deliver_package(newer, candidate, current)
            self.assertFalse(candidate.exists())
            pdf.write_bytes(raw)

            incomplete_settings = deepcopy(settings)
            incomplete_settings["native_mapping"]["scenarios"]["Downside"]["confirmed_fields"].remove("INPUT_C46")
            incomplete, state, incomplete_files = make_package("incomplete", incomplete_settings)
            self.assertEqual(state, "PENDING")
            incomplete_result = json.loads(incomplete_files["results.json"])
            self.assertIsNone(incomplete_result["scenarios"]["Downside"]["cash_per_usd_10"])
            self.assertIsNotNone(incomplete_result["scenarios"]["Base"]["cash_per_usd_10"])
            current.write_bytes(incomplete_files[worksheet.CURRENT_REVISION_FILE])
            with self.assertRaisesRegex(ValueError, "Flujos por USD 10 PENDING: Downside"):
                worksheet.deliver_package(incomplete, candidate, current)
            self.assertFalse(candidate.exists())
            self.assertEqual(worksheet.read_package(older), older_files)
            self.assertEqual(worksheet.read_package(newer), newer_files)


    def test_current_fiscal_report_preserves_cash_when_a_criterion_is_missing(self):
        with TemporaryDirectory(prefix="miniuw-d216-fiscal-") as temp:
            root = Path(temp)
            documents = source_files(root / "sources")
            documents["criteria_raw"] = change_cells(documents["criteria_raw"], {"G11": ""})
            package = root / "current"
            result = assemble(settings_for_tax(), register(documents, "SYNTHETIC-D216-fiscal"), documents, package)
            self.assertEqual(result["simulation_result"], "PENDING")
            files = worksheet.read_package(package)
            model = json.loads(files["results.json"])
            self.assertTrue(all(view["cash_per_usd_10"]["events"] for view in model["scenarios"].values()))
            current = root / "revision.json"
            current.write_bytes(files[worksheet.CURRENT_REVISION_FILE])
            report = root / "fiscal.pdf"
            receipt = worksheet.deliver_package(package, report, current)
            self.assertEqual((receipt["vigencia"], receipt["simulation_result"], receipt["decision"]),
                             ("VIGENTE", "PENDING", "PENDING"))
            self.assertEqual(report.read_bytes(), files["MiniUW_Resumen.pdf"])
            page, = PdfReader(report).pages
            for marker in ("D203", "Decisión real PENDING", "Base | Aporte extra", "Downside | Aporte extra", "USD 10"):
                self.assertIn(marker, page.extract_text())
