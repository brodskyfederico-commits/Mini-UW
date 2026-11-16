"""Verify the four-route page against an independent reading of the audited ledger."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pypdf import PdfReader

from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import encode
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, read_package
from test_worksheet_annual_holding import ROUTE, source_files
from test_worksheet_annual_sale_without_refi import SALE, settings_with_sale
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import annual_cash, deliver_annual_comparison, render_page
from worksheet_intake_D198 import assemble, register
from worksheet_sale_rate_grid_D84 import money


class WorksheetAnnualComparisonTests(TestCase):
    def test_one_page_reconciles_all_four_paths_and_blocks_a_changed_revision(self):
        with TemporaryDirectory(prefix="miniuw-annual-comparison-") as directory:
            root = Path(directory)
            package, current, pdf = root / "expediente", root / "actual.json", root / "comparativo.pdf"
            sources = source_files(root / "sources")
            assemble(settings_with_sale(), register(sources, "SYNTHETIC-D238-four-routes"), sources, package)
            files = read_package(package)
            current.write_bytes(files[CURRENT_REVISION_FILE])
            receipt = deliver_annual_comparison(package, pdf, current, (ROUTE, SALE))
            model = json.loads(files["results.json"])
            self.assertEqual(receipt["decision"], "PENDING")
            self.assertEqual(receipt["source_results_sha256"], sha256(files["results.json"]).hexdigest())
            self.assertEqual(receipt["pdf_sha256"], sha256(pdf.read_bytes()).hexdigest())
            self.assertEqual(receipt["page_count"], 1)
            page, = PdfReader(pdf).pages
            report = {" ".join(line.split()) for line in page.extract_text().splitlines()}
            self.assertIn("Cobro total | 16,92 | 17,08 | 4,94 | 5,22", report)
            self.assertIn("Aportes adicionales | 4,87 | 4,87 | 8,32 | 8,23", report)
            self.assertIn("Saldo sin recuperar | 0,00 | 0,00 | 13,38 | 13,01", report)
            self.assertIn("Ensayo sintético | 1101 real, retorno histórico y retorno personal PENDING", report)
            labels = {"construction": "Aporte inicial/obra", "refinance": "Refinanciación",
                      "operation": "Operación", "sale": "Venta neta"}
            directory_ledger = {}
            count = 0
            for index, (name, variant, label) in enumerate(
                    (name, variant, route) for name in ("Base", "Downside")
                    for variant, route in (("Con refi", ROUTE), ("Sin refi", SALE))):
                original = model["calendar_checks"][name][label]["cash_per_usd_10"]
                disclosed = receipt["scenarios"][name][variant]
                self.assertEqual(disclosed["cash_per_usd_10"], original)
                self.assertEqual(disclosed["cash_sha256"], sha256(encode(original)).hexdigest())
                for item in original["events"]:
                    count += 1
                    key = f"{item['date']} {labels[item['stage']]}"
                    cells = directory_ledger.setdefault(key, ["—"] * 4)
                    self.assertEqual(cells[index], "—")
                    cells[index] = f"{money(item['contribution'])} / {money(item['receipt'])}"
            self.assertEqual(count, 52)
            for key, cells in directory_ledger.items():
                self.assertIn(" | ".join([key, *cells]), report)

            changed = deepcopy(model)
            changed["calendar_checks"]["Base"][SALE]["sale"]["gross"] = rational(1)
            with self.assertRaisesRegex(ValueError, "Comparación PENDING para Base"):
                annual_cash(changed, (ROUTE, SALE))
            changed = deepcopy(model)
            changed["calendar_checks"]["Downside"][SALE] = {"state": "PENDING", "blocker": "construction_loan_matures_before_sale"}
            with self.assertRaisesRegex(ValueError, "construction_loan_matures_before_sale"):
                annual_cash(changed, (ROUTE, SALE))

            def render_then_change(*args):
                payload = render_page(*args)
                current.write_bytes(files[CURRENT_REVISION_FILE] + b"\n")
                return payload

            stale = root / "stale.pdf"
            with patch("worksheet_annual_comparison._audit_package", return_value=(files, model)):
                with patch("worksheet_annual_comparison.render_page", side_effect=render_then_change):
                    with self.assertRaisesRegex(ValueError, "La revisión vigente cambió durante la entrega"):
                        deliver_annual_comparison(package, stale, current, (ROUTE, SALE))
            self.assertFalse(stale.exists())
            self.assertEqual(read_package(package), files)
