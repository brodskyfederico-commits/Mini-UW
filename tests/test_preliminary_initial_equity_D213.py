"""Replay a corrected acquisition quote through the D206 pilot and USD 10 output."""
from collections import Counter
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_worksheet_preliminary_pdf_D206 import (
    DEAL, FIXTURES, INDEX, SECOND, bundle_pages, pdf_bundle, write_sources,
)
from check_worksheet_preliminary_pilot_D205 import fixture as structured_sources
from check_worksheet_preliminary_stages_D188 import workbook
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_worksheet_v1 import encoded
from reconcile_worksheet_D179 import exact
from worksheet_preliminary_pilot_D205 import paths, pilot_audit, pilot_current, pilot_run

SCENARIO = "Downside"
OLD_PRICE, NEW_PRICE = 100_000, 140_000
CLOSING_RATE = Q("0.05")


def inventory(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes()
            for p in directory.rglob("*") if p.is_file()}


def register(files, replacements):
    revised = files | replacements
    index = json.loads(files[INDEX])
    for name, raw in replacements.items():
        index["sha256"][name] = sha256(raw).hexdigest()
    return revised | {INDEX: encoded(index)}


class PreliminaryInitialEquityTests(unittest.TestCase):
    def test_purchase_revision_rescales_every_gross_cash_event(self):
        names = paths(DEAL, SCENARIO, pdf=True)
        published = inventory(FIXTURES)
        sheets = bundle_pages(DEAL, SCENARIO, structured_sources())
        quote = sheets["acquisition_and_costs"]
        old_row = f"Inputs | C32 | {OLD_PRICE}"
        self.assertIn(old_row, quote)
        self.assertIn("Inputs | C33 | 0.05", quote)

        def revised_sources(price):
            book = workbook(SCENARIO, {"C32": {"value": str(price)}})
            before = inspect_synthetic_input_sheet(published[names["Inputs"]]).cells
            after = inspect_synthetic_input_sheet(book).cells
            self.assertEqual([cell for cell in before if before[cell] != after[cell]], ["C32"])
            rows = [f"Inputs | C32 | {price}" if row == old_row else row for row in quote]
            pdf = pdf_bundle(sheets | {"acquisition_and_costs": rows})
            return book, pdf

        with TemporaryDirectory(prefix="miniuw-d213-") as temp:
            root = Path(temp)

            def replay(label, files):
                src, dst = root / f"{label}-sources", root / label
                write_sources(files, src)
                model = pilot_run(src, dst)
                self.assertEqual(pilot_audit(dst), model)
                self.assertEqual(model["decision"], "PENDING")
                self.assertFalse(model["real_decisions_enabled"])
                self.assertFalse(model["deployment_enabled"])
                self.assertFalse(model["full_uw_eligible"])
                return model, dst

            original, original_package = replay("original", published)
            original_package_bytes = inventory(original_package)
            self.assertEqual([row["deal_id"] for row in original["ranking"]], [DEAL, SECOND])
            before = original["deals"][DEAL]["scenarios"][SCENARIO]
            book, pdf = revised_sources(NEW_PRICE)
            zero_book, zero_pdf = revised_sources(0)
            for label, inputs, issue in (
                ("workbook-only", {names["Inputs"]: book}, "acquisition_and_costs · C32 difiere"),
                ("pdf-only", {names["Evidence"]: pdf}, "acquisition_and_costs · C32 difiere"),
                ("zero-basis", {names["Inputs"]: zero_book, names["Evidence"]: zero_pdf}, "aporte inicial"),
            ):
                with self.subTest(label=label):
                    changed, _ = replay(label, register(published, inputs))
                    self.assertEqual(changed["state"], "PENDING")
                    view = changed["deals"][DEAL]["scenarios"][SCENARIO]
                    self.assertIsNone(view["cash"])
                    self.assertTrue(any(issue in message for message in view["blockers"]), view["blockers"])
                    self.assertEqual([row["deal_id"] for row in changed["ranking"]], [SECOND])
                    self.assertEqual(changed["deals"][DEAL]["scenarios"]["Base"],
                                     original["deals"][DEAL]["scenarios"]["Base"])
                    self.assertEqual(changed["deals"][SECOND], original["deals"][SECOND])

            revised, new_package = replay("revised", register(published, {names["Inputs"]: book, names["Evidence"]: pdf}))
            self.assertEqual(revised["state"], "PRELIMINAR")
            self.assertNotEqual(revised["case_sha256"], original["case_sha256"])
            view = revised["deals"][DEAL]["scenarios"][SCENARIO]
            self.assertEqual(view["blockers"], [])
            self.assertEqual(view["financing"], before["financing"])
            self.assertEqual(view["florida_property_tax"], before["florida_property_tax"])
            self.assertEqual(revised["deals"][DEAL]["scenarios"]["Base"], original["deals"][DEAL]["scenarios"]["Base"])
            self.assertEqual(revised["deals"][SECOND], original["deals"][SECOND])
            locator = view["evidence"]["Evidence"]["pages"]["acquisition_and_costs"]
            self.assertEqual(locator["page"], 4)
            self.assertGreater(locator["locators"]["Inputs/C32"], 5)
            self.assertTrue(view["cell_sources"]["C32"].endswith("#Inputs!C32"))

            old_cash, new_cash = before["cash"], view["cash"]
            old_basis, new_basis = [price * (1 + CLOSING_RATE) for price in (OLD_PRICE, NEW_PRICE)]
            self.assertEqual(exact(old_cash["basis_amount"]), old_basis)
            self.assertEqual(exact(new_cash["basis_amount"]), new_basis)
            old_scale, new_scale = 10 / old_basis, 10 / new_basis
            self.assertEqual(exact(new_cash["scale_factor"]), new_scale)
            kinds = Counter()
            for old, new in zip(old_cash["events"], new_cash["events"], strict=True):
                fields = ("date", "kind", "category")
                self.assertEqual(tuple(new[k] for k in fields), tuple(old[k] for k in fields))
                kinds[new["category"]] += 1
                gross = exact(old["amount"]) / old_scale
                if old["category"] == "initial_capital":
                    self.assertEqual(gross, old_basis)
                    self.assertEqual(exact(new["amount"]), 10)
                    self.assertTrue(new["source_ref"].endswith("#Inputs!C32:C33"))
                else:
                    self.assertEqual(exact(new["amount"]), gross * new_scale)
            self.assertEqual(kinds, {"initial_capital": 1, "additional_capital": 3, "refinance_cash_in": 1,
                                     "net_refinance_distribution": 1, "operating_distribution": 4,
                                     "net_sale_distribution": 1})
            contributions = 10 + (exact(old_cash["total_contributions"]) - 10) * new_scale / old_scale
            distributions = exact(old_cash["total_distributions"]) * new_scale / old_scale
            self.assertEqual(exact(new_cash["total_contributions"]), contributions)
            self.assertEqual(exact(new_cash["total_distributions"]), distributions)
            self.assertEqual(exact(new_cash["unrecovered_after_sale"]), contributions - distributions)
            self.assertEqual(exact(new_cash["equity_multiple"]), distributions / contributions)
            self.assertEqual([row["deal_id"] for row in revised["ranking"]], [SECOND, DEAL])
            self.assertEqual(exact(revised["ranking"][1]["downside_equity_multiple"]), distributions / contributions)

            page, = PdfReader(new_package / "MiniUW_Resumen.pdf").pages
            rendered = page.extract_text()
            for label in ("Dictamen formal PENDING", "Aporte extra 5,72", "Cobro total 6,47",
                          "Sin recuperar 9,25", "2028-12-30"):
                self.assertIn(label, rendered)
            self.assertEqual(inventory(original_package), original_package_bytes)
            self.assertEqual(pilot_audit(original_package), original)
            self.assertEqual(inventory(FIXTURES), published)

            revised_sources_dir = root / "revised-sources"
            current = pilot_current(new_package, revised_sources_dir)
            self.assertEqual(current["vigencia"], "VIGENTE")
            self.assertEqual(current["ranking"], revised["ranking"])
            self.assertEqual(current["pdf_sha256"], revised["pdf_sha256"])
            self.assertEqual(current["current_case_sha256"], current["archived_case_sha256"])
            self.assertEqual(current["blockers"], [])
            self.assertEqual(current["decision"], "PENDING")
            stale = pilot_current(original_package, revised_sources_dir)
            self.assertEqual(stale["current_case_sha256"], current["current_case_sha256"])
            self.assertEqual(stale["archived_case_sha256"], original["case_sha256"])
            self.assertEqual(stale["blockers"], ["El inventario vigente difiere de la revisión archivada"])

            for package, sources_dir in ((original_package, revised_sources_dir),
                                         (new_package, new_package / "sources"),
                                         (new_package, root / "missing-current-sources")):
                blocked = pilot_current(package, sources_dir)
                self.assertEqual((blocked["state"], blocked["decision"], blocked["vigencia"]),
                                 ("PENDING", "PENDING", "PENDING"))
                self.assertEqual(blocked["ranking"], [])
                self.assertIsNone(blocked["pdf_sha256"])
                self.assertTrue(blocked["blockers"])

            workbook_path = revised_sources_dir / names["Inputs"]
            workbook_path.unlink()
            blocked = pilot_current(new_package, revised_sources_dir)
            self.assertEqual(blocked["ranking"], [])
            self.assertIsNone(blocked["pdf_sha256"])
            self.assertEqual(blocked["blockers"], [f"{names['Inputs']} · falta en la revisión vigente"])
            workbook_path.write_bytes(book + b" ")
            blocked = pilot_current(new_package, revised_sources_dir)
            self.assertEqual(blocked["vigencia"], "PENDING")
            self.assertEqual(blocked["blockers"], [f"{names['Inputs']} · huella distinta en la revisión vigente"])
            workbook_path.write_bytes(book)
            self.assertEqual(pilot_current(new_package, revised_sources_dir), current)

            command = [sys.executable, str(ROOT / "tools/worksheet_preliminary_pilot_D205.py"), "audit"]
            audited = subprocess.check_output([*command, str(original_package), "--current-source",
                                               str(revised_sources_dir)])
            self.assertEqual(json.loads(audited), stale)
            archived = subprocess.check_output([*command, str(original_package)])
            self.assertEqual(json.loads(archived)["ranking"], original["ranking"])
            self.assertEqual(inventory(original_package), original_package_bytes)
