"""Replay a local worksheet and inject unsupported green claims by datum."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from audit_worksheet_critical_evidence_D219 import (
    BOT, REFERENCE, audit, audit_package, canonical, digest, fields, get,
)
from check_worksheet_florida_tax_D203 import settings_for_tax
from check_worksheet_technical_acceptance_D200 import source_files
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, verify_package
from worksheet_intake_D198 import assemble, register

DSCR = "Downside:permanent:minimum_dscr"
BANK = BOT + ("B08", "bank_pdf_by_scenario", "Downside")
AREA = "Compartido:GBA"


class CriticalEvidenceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = TemporaryDirectory(prefix="miniuw-d219-")
        cls.addClassCleanup(work.cleanup)
        root = Path(work.name)
        cls.package = root / "control"
        sources = source_files(root / "sources")
        registration = register(sources, "SYNTHETIC-D219-document-control")
        intake = assemble(settings_for_tax(), registration, sources, cls.package)
        if intake["source_blockers"]:
            raise AssertionError(intake["source_blockers"])
        cls.revision_path = cls.package / CURRENT_REVISION_FILE
        cls.revision = cls.revision_path.read_bytes()
        replay = verify_package(cls.package, current_revision_raw=cls.revision)
        if replay["vigencia"] != "VIGENTE" or replay["audit_bot"] != "B16":
            raise AssertionError("B16 could not replay the synthetic control")
        cls.ref = json.loads(REFERENCE.read_bytes())
        cls.results = json.loads((cls.package / "results.json").read_bytes())
        cls.documents = {n: (cls.package / n).read_bytes()
                         for n in (*cls.ref["sources"], "case.json", CURRENT_REVISION_FILE)}

    def audit(self, results=None, docs=None, revision=None):
        checked = audit(self.results if results is None else results,
                        self.documents if docs is None else docs,
                        self.revision if revision is None else revision, self.ref)
        self.assertEqual(checked["critical_fields"], 48)
        self.assertEqual(checked["decision"], "PENDING")
        return checked

    def assert_false(self, report, key, reason=None, bot=None):
        self.assertEqual(report["status"], "PENDING")
        row = report["fields"][key]
        self.assertEqual(row["status"], "FALSE_GREEN")
        if reason is not None:
            self.assertTrue(any(issue["reason"] == reason and (bot is None or issue.get("bot") == bot)
                                for issue in row["issues"]), row)

    def test_reproduced_current_package_has_no_false_green(self):
        before = canonical(self.results)
        report = audit_package(self.package, self.revision_path, self.ref)
        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(report["counts"], {"VERIFIED_GREEN": 48, "FALSE_GREEN": 0, "PENDING": 0})
        self.assertEqual(report["green_claims"], 48)
        self.assertTrue(report["current_revision_verified"])
        self.assertEqual(canonical(self.results), before)
        self.assertEqual(set(report["fields"][AREA]["bots"]), {"B03", "B05", "B06", "B07", "B08", "B09"})

    def test_every_critical_datum_detects_an_unsupported_green(self):
        for field in fields(self.ref):
            with self.subTest(datum=field.key):
                model = deepcopy(self.results)
                claim = field.claims[-1]
                target = claim.record + next(reversed(claim.expected))
                get(model, target[:-1])[target[-1]] = None
                report = self.audit(model)
                self.assert_false(report, field.key, "discrepancia", claim.bot)
                self.assertTrue(report["fields"][field.key]["locator"])
                self.assertGreaterEqual(report["counts"]["FALSE_GREEN"], 1)

    def test_catches_green_with_no_quote_observation_or_wrong_page(self):
        for part, key, value, reason in (
            ("observations", "C72", None, "sin_respaldo"),
            ("observations", "C72", ["fraction", "1.30"], "discrepancia"),
            ("locators", "C72", "Evidence.pdf p. 1 / C72", "discrepancia"),
        ):
            with self.subTest(part=part, value=value):
                model = deepcopy(self.results)
                target = get(model, BANK + (part,))
                if value is None:
                    del target[key]
                else:
                    target[key] = value
                report = self.audit(model)
                self.assert_false(report, DSCR, reason, "B08")
                self.assertEqual(report["counts"]["FALSE_GREEN"], 1)

    def test_parent_green_exposes_a_missing_reading_and_duplicate_plan_pages(self):
        model = deepcopy(self.results)
        del get(model, BOT)["B06"]
        self.assert_false(self.audit(model), AREA, "sin_respaldo", "B06")
        model = deepcopy(self.results)
        get(model, BOT + ("B03", "documents", "plan_pdf"))["duplicate_sheet_pages"] = {"A101": [4, 5]}
        self.assert_false(self.audit(model), AREA, "discrepancia", "B03")

    def test_detects_missing_or_altered_source_and_preserves_independent_fields(self):
        for content in (None, self.documents["Evidence.pdf"] + b"\n"):
            with self.subTest(altered=content is not None):
                report = self.audit(docs=self.documents | {"Evidence.pdf": content})
                self.assert_false(report, DSCR, "fuente_ausente_o_huella_distinta", "B08")
                self.assertEqual(report["counts"], {"VERIFIED_GREEN": 16, "FALSE_GREEN": 32, "PENDING": 0})
                self.assertEqual(report["fields"]["Base:market:C59"]["status"], "VERIFIED_GREEN")

    def test_old_or_incompatible_revision_cannot_support_any_green(self):
        alternate = json.loads(self.revision)
        for field, value in (("revision", "SYNTHETIC-D219-next"), ("criteria_revision", "SYNTHETIC-unknown")):
            with self.subTest(field=field):
                different = canonical(alternate | {field: value})
                report = self.audit(revision=different)
                self.assertFalse(report["current_revision_verified"])
                self.assertEqual(report["counts"]["FALSE_GREEN"], 48)
        invalid = canonical(alternate | {"criteria_revision": "SYNTHETIC-unbound"})
        spoofed = deepcopy(self.results)
        spoofed["revision_review"]["reference_sha256"] = digest(invalid)
        self.assertFalse(self.audit(spoofed, self.documents | {CURRENT_REVISION_FILE: invalid},
                                    invalid)["current_revision_verified"])

    def test_pending_and_independent_supported_claims_do_not_become_false_green(self):
        model = deepcopy(self.results)
        review = model["local_review"]
        review["state"] = "PENDING"
        review["bots"] = {bot: review["bots"][bot] for bot in ("B03", "B05")}
        model["scenarios"] = {}
        report = self.audit(model, self.documents | {"Evidence.pdf": None})
        self.assertEqual(report["status"], "PENDING")
        self.assertEqual(report["counts"], {"VERIFIED_GREEN": 0, "FALSE_GREEN": 0, "PENDING": 48})
        self.assertEqual(report["fields"][AREA]["green_bots"], ["B03", "B05"])

    def test_cli_signals_false_green_with_a_nonzero_exit_status(self):
        command = [sys.executable, str(ROOT / "tools/audit_worksheet_critical_evidence_D219.py"),
                   str(self.package), "--current-revision", str(self.revision_path)]
        accepted = subprocess.run(command, capture_output=True, check=False)
        self.assertEqual(accepted.returncode, 0, accepted.stderr.decode())
        self.assertEqual(json.loads(accepted.stdout)["counts"]["FALSE_GREEN"], 0)
        model = deepcopy(self.results)
        get(model, BANK + ("locators",))["C72"] = ""
        result_path = self.package / "results.json"
        original = result_path.read_bytes()
        try:
            result_path.write_bytes(canonical(model))
            blocked = subprocess.run(command, capture_output=True, check=False)
        finally:
            result_path.write_bytes(original)
        self.assertEqual(blocked.returncode, 2, blocked.stderr.decode())
        self.assert_false(json.loads(blocked.stdout), DSCR, "discrepancia", "B08")
