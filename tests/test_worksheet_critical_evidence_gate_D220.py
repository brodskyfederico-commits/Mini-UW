"""D219 gates the integral case, downstream outputs and PDF delivery."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import miniuw_worksheet_v1 as worksheet
from audit_worksheet_critical_evidence_D219 import REFERENCE
from check_worksheet_florida_tax_D203 import settings_for_tax
from check_worksheet_technical_acceptance_D200 import source_files
from worksheet_intake_D198 import assemble, prepare, register

DSCR = "Downside:permanent:minimum_dscr"
AREA = "Compartido:GBA"


class WorksheetCriticalEvidenceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = TemporaryDirectory(prefix="miniuw-d220-")
        cls.addClassCleanup(temp.cleanup)
        cls.root = Path(temp.name)
        cls.sources = source_files(cls.root / "sources")
        cls.settings = settings_for_tax() | {"schema": worksheet.WORKBOOK_CRITICAL_EVIDENCE_SCHEMA}
        cls.control_path = cls.root / "control"
        cls.receipt, cls.control = cls.make_package("control")
        cls.control_revision = cls.designate(cls.control_path, "current")
        cls.document_review = deepcopy(cls.control["local_review"])
        del cls.document_review["financial_bindings"]

    @classmethod
    def make_package(cls, name, settings=None):
        directory = cls.root / name
        receipt = assemble(cls.settings if settings is None else settings,
                           register(cls.sources, f"SYNTHETIC-D220-{name}"), cls.sources, directory)
        return receipt, json.loads((directory / "results.json").read_bytes())

    @classmethod
    def designate(cls, package, name):
        out = cls.root / f"{name}.json"
        out.write_bytes((package / worksheet.CURRENT_REVISION_FILE).read_bytes())
        return out

    def reading(self, edit):
        def review(case, plan_raw, *, evidence_raw, evidence_milestone):
            self.assertEqual((plan_raw, evidence_raw, evidence_milestone),
                             (self.sources["plan_raw"], self.sources["evidence_raw"], "D162"))
            document_review = deepcopy(self.document_review)
            edit(document_review)
            return document_review
        return patch("worksheet_documented_finance_D147.review_documents", side_effect=review)

    @staticmethod
    def remove_dscr_locator(review):
        del review["bots"]["B08"]["bank_pdf_by_scenario"]["Downside"]["locators"]["C72"]

    def assert_pending_view(self, model, scope, field, *, reason="falso_verde"):
        view = model["scenarios"][scope]
        self.assertEqual(view["state"], "PENDING")
        self.assertIsNone(view["cash_per_usd_10"])
        self.assertIsNone(view["capacity"])
        self.assertEqual(view["noi_by_period"], {})
        self.assertNotIn("valuation_and_sale", view)
        self.assertIn(f"B12:D219:{reason}:{field}", view["blockers"])
        self.assertEqual(model["screening"]["simulation_result"], "PENDING")
        for row in model["screening"]["comparisons"]:
            if row["scenario_id"] == scope:
                self.assertNotIn(row["state"], ("PASS_CONDITION", "FAIL_CONDITION"))
        for variants in model["alternative_evaluation"]["slots"].values():
            self.assertIsNone(variants[scope]["cash_per_usd_10"])

    def test_normal_entry_point_replays_and_delivers_with_48_supported_green_fields(self):
        self.assertEqual(self.receipt["critical_evidence"],
            {"status": "PASSED", "counts": {"VERIFIED_GREEN": 48, "FALSE_GREEN": 0, "PENDING": 0},
             "affected_scenarios": []})
        case = json.loads((self.control_path / "case.json").read_bytes())
        reference = worksheet.sha(REFERENCE.read_bytes())
        self.assertEqual(case["critical_evidence_reference_sha256"], reference)
        self.assertEqual(self.control["critical_evidence_review"]["reference_sha256"], reference)
        self.assertEqual(self.control["profile"], worksheet.WORKBOOK_CRITICAL_EVIDENCE_PROFILE)
        with self.reading(lambda _: None):
            _, previous = self.make_package("historical-v32", settings_for_tax())
        self.assertEqual(self.control["scenarios"], previous["scenarios"])
        audit = worksheet.verify_package(self.control_path, current_revision_raw=self.control_revision.read_bytes())
        self.assertEqual((audit["audit_bot"], audit["vigencia"], audit["critical_evidence"]["status"]),
                         ("B16", "VIGENTE", "PASSED"))
        output = self.root / "shipment.pdf"
        command = [sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "deliver", str(self.control_path),
                   "--current-revision", str(self.control_revision), "--output", str(output)]
        receipt = json.loads(subprocess.check_output(command))
        self.assertEqual((receipt["status"], receipt["decision"]), ("delivered_synthetic_pdf", "PENDING"))
        page, = PdfReader(output).pages
        text = page.extract_text()
        for literal in ("D220", "USD 10", "Base | Aporte extra", "Downside | Aporte extra"):
            self.assertIn(literal, text)

    def test_unsupported_downside_green_withholds_only_downside_and_blocks_delivery(self):
        with self.reading(self.remove_dscr_locator):
            _, legacy = self.make_package("v32-uncaught", settings_for_tax())
            self.assertTrue(legacy["scenarios"]["Downside"]["cash_per_usd_10"]["events"])
            receipt, model = self.make_package("downside-fault")
            path = self.root / "downside-fault"
            current = self.designate(path, "downside-current")
            result = worksheet.verify_package(path, current_revision_raw=current.read_bytes())
            self.assertEqual(result["critical_evidence"], receipt["critical_evidence"])
            self.assertEqual(result["vigencia"], "VIGENTE")
            self.assertEqual(result["critical_evidence"]["affected_scenarios"], ["Downside"])
            with self.assertRaisesRegex(ValueError, f"Cotejo D219 PENDING: {DSCR}"):
                worksheet.deliver_package(path, self.root / "downside-denied.pdf", current)
        self.assertFalse((self.root / "downside-denied.pdf").exists())
        self.assert_pending_view(model, "Downside", DSCR)
        self.assertEqual(model["scenarios"]["Base"], self.control["scenarios"]["Base"])
        self.assertEqual(model["decision"], "PENDING")
        row = model["critical_evidence_review"]["fields"][DSCR]
        self.assertEqual(row["status"], "FALSE_GREEN")
        self.assertTrue(any(issue["bot"] == "B08" and issue["reason"] == "sin_respaldo" for issue in row["issues"]))
        page, = PdfReader(path / "MiniUW_Resumen.pdf").pages
        self.assertIn("Downside | Caja PENDING: respaldo documental D219 pendiente", page.extract_text())
        self.assertIn("Base | Aporte extra", page.extract_text())

    def test_shared_wrong_plan_citation_blocks_both_scenarios(self):
        def change_plan(review):
            review["bots"]["B06"]["locator"] = "p. 4 / A101 / Gross building area"
        with self.reading(change_plan):
            _, model = self.make_package("shared-fault")
        self.assertEqual(model["critical_evidence_review"]["affected_scenarios"], ["Base", "Downside"])
        self.assertEqual(model["critical_evidence_review"]["fields"][AREA]["status"], "FALSE_GREEN")
        for scope in ("Base", "Downside"):
            self.assert_pending_view(model, scope, AREA)

    def test_older_or_altered_reference_cannot_bypass_the_gate(self):
        settings = settings_for_tax()
        registr = register(self.sources, "SYNTHETIC-D220-reference-test")
        old_case, old_revision = prepare(settings, registr)
        new_case, new_revision = prepare(self.settings, registr)
        self.assertNotEqual(old_revision, new_revision)
        altered = json.loads(new_case)
        altered["critical_evidence_reference_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "inventario D219"):
            worksheet.build_results(worksheet.encoded(altered), current_revision_raw=new_revision, **self.sources)
        with self.reading(lambda _: None):
            model, _ = worksheet.build_results(new_case, current_revision_raw=old_revision, **self.sources)
        self.assertEqual(model["critical_evidence_review"]["status"], "PENDING")
        self.assertFalse(model["critical_evidence_review"]["current_revision_verified"])
        self.assertTrue(all(view["cash_per_usd_10"] is None for view in model["scenarios"].values()))
        self.assertEqual(json.loads(old_case)["schema"], worksheet.WORKBOOK_FLORIDA_TAX_SCHEMA)
