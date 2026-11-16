"""Verify the four-route page against an independent reading of the audited ledger."""

from copy import deepcopy
from datetime import date
from fractions import Fraction
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
from worksheet_annual_crossover_construction import construction_at_cut, construction_recovery, reprice_route
from worksheet_annual_crossover_sale_price import sale_prices
from worksheet_annual_discount_crossover import crossover_by_scenario, shown_rate
from worksheet_downside_construction_sale import CUTS, downside_combinations
from worksheet_downside_fixed_sale_construction import SALE_PRICES, downside_fixed_price_cuts
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

            cross = crossover_by_scenario(annual_cash(model, (ROUTE, SALE)))
            for name, row in cross.items():
                self.assertEqual(shown_rate(row), {"Base": "0,6532%", "Downside": "1,7903%"}[name])
                origin = date.fromisoformat(row["purchase_date"])

                def pv(variant, rate):
                    events = receipt["scenarios"][name][variant]["cash_per_usd_10"]["events"]
                    total = Fraction()
                    for event in events:
                        when = date.fromisoformat(event["date"])
                        offset = 12 * (when.year - origin.year) + when.month - origin.month
                        total += (amount(event["receipt"]) - amount(event["contribution"])) / (1 + rate) ** offset
                    return total

                lower, upper = (amount(row[key]) for key in ("monthly_rate_lower", "monthly_rate_upper"))
                self.assertLessEqual(upper - lower, Fraction(1, 10**10))
                self.assertLess(pv("Con refi", lower), pv("Sin refi", lower))
                self.assertGreaterEqual(pv("Con refi", upper), pv("Sin refi", upper))
                self.assertEqual(pv("Con refi", Fraction()) - pv("Sin refi", Fraction()),
                                 amount(row["net_nominal_with_refi"]) - amount(row["net_nominal_without_refi"]))
                self.assertEqual(pv("Sin refi", (lower + upper) / 2), amount(row["npv_at_midpoint_without_refi"]))

            prices = sale_prices(model, annual_cash(model, (ROUTE, SALE)), (ROUTE, SALE))
            expected = {"Base": Fraction("4749316.96"), "Downside": Fraction("8919058.39")}
            for name, row in prices.items():
                origin = date.fromisoformat(row["cross"]["purchase_date"])
                for variant, label in (("Con refi", ROUTE), ("Sin refi", SALE)):
                    path = row["paths"][variant]
                    self.assertEqual(amount(path["minimum_gross_at_cents"]), expected[name])
                    self.assertLess(amount(path["below_terminal_upper"]), 0)
                    self.assertGreaterEqual(amount(path["minimum_terminal_lower"]), 0)
                    route = model["calendar_checks"][name][label]
                    source = route["cash_by_period"][0]
                    sale = date.fromisoformat(route["sale"]["date"])
                    terminal_month = (sale.year - origin.year) * 12 + sale.month - origin.month
                    nominal_gross = amount(route["sale"]["gross"])
                    commission = amount(model["scenarios"][name]["valuation_and_sale"]["sale_cost_fraction"])
                    for endpoint in ("monthly_rate_lower", "monthly_rate_upper"):
                        rate = amount(row["cross"][endpoint])
                        upfront = amount(source["contribution"])
                        future_cash = Fraction()
                        for event in route["cash_per_usd_10"]["events"]:
                            when = date.fromisoformat(event["date"])
                            elapsed = (sale.year - when.year) * 12 + sale.month - when.month
                            self.assertLessEqual(elapsed, terminal_month)
                            future_cash += (amount(event["receipt"]) - amount(event["contribution"])) * (1 + rate) ** elapsed
                        reach = future_cash + (expected[name] - nominal_gross) * (1 - commission) * 10 / upfront
                        self.assertLess(reach - Fraction(1, 100) * (1 - commission) * 10 / upfront, 0)
                        self.assertGreaterEqual(reach, 0)

            inputs = json.loads(files["case.json"])["rent_inputs"]
            cuts = construction_recovery(model, inputs, annual_cash(model, (ROUTE, SALE)), (ROUTE, SALE))
            expected_cuts = {"Con refi": Fraction("125513.82"), "Sin refi": Fraction("125487.65")}
            for name, row in cuts.items():
                rate = sum(amount(row["cross"][key]) for key in ("monthly_rate_lower", "monthly_rate_upper")) / 2
                origin = date.fromisoformat(row["cross"]["purchase_date"])
                for caption, label in (("Con refi", ROUTE), ("Sin refi", SALE)):
                    path = row["paths"][caption]
                    if name == "Base":
                        cut = amount(path["direct_cut"])
                        self.assertEqual(cut, expected_cuts[caption])
                        self.assertGreaterEqual(amount(path["tested_terminal_bounds"]["lower"]), 0)
                        _, funding = construction_at_cut(model, inputs, name, cut - Fraction(1, 100))
                        replay = reprice_route(model["scenarios"][name], inputs["calendar_checks"][name][label],
                                              model["calendar_checks"][name][label], funding)
                        net = Fraction()
                        for event in replay["cash_per_usd_10"]["events"]:
                            when = date.fromisoformat(event["date"])
                            elapsed = 12 * (when.year - origin.year) + when.month - origin.month
                            net += (amount(event["receipt"]) - amount(event["contribution"])) / (1 + rate) ** elapsed
                        self.assertLess(net, 0)
                    else:
                        self.assertIsNone(path["direct_cut"])
                        self.assertEqual(amount(path["tested_direct_cost"]), 0)
                        self.assertLess(amount(path["tested_terminal_bounds"]["upper"]), 0)

            combinations = downside_combinations(model, inputs, annual_cash(model, (ROUTE, SALE)), (ROUTE, SALE))
            expected_pairs = (
                ("8919058.39", "8919058.39"), ("7426692.33", "7450445.38"), ("5967646.91", "6015153.02"),
                ("4582547.40", "4696913.53"), ("3407011.14", "3726831.21"),
            )
            for ratio, row, pair in zip(CUTS, combinations["rows"], expected_pairs, strict=True):
                self.assertEqual(amount(row["cut_ratio"]), ratio)
                self.assertEqual(amount(row["tested_direct_cost"]), Fraction(2744000) * (1 - ratio))
                for caption, expected_price in zip(("Con refi", "Sin refi"), pair, strict=True):
                    path = row["paths"][caption]
                    price = path["price"]
                    self.assertEqual(amount(price["minimum_gross_at_cents"]), Fraction(expected_price))
                    self.assertLess(amount(price["below_terminal_upper"]), 0)
                    self.assertGreaterEqual(amount(price["minimum_terminal_lower"]), 0)
                    cash = path["dated_cash_at_original_price"]
                    self.assertEqual(amount(path["total_received_per_10_at_minimum"]),
                                     amount(cash["received"]) + amount(price["net_sale_increase_per_10"]))

            fixed = downside_fixed_price_cuts(model, inputs, annual_cash(model, (ROUTE, SALE)), (ROUTE, SALE))
            minimums = (("2397953.38", "2550826.92"), ("1826958.96", "1857193.81"), ("1356788.54", "1379242.41"))
            self.assertEqual(fixed["cross"], combinations["cross"])
            for row, price, reductions in zip(fixed["rows"], SALE_PRICES, minimums, strict=True):
                self.assertEqual(amount(row["gross_sale"]), price)
                for caption, expected in zip(("Con refi", "Sin refi"), reductions, strict=True):
                    trial = row["paths"][caption]
                    self.assertEqual(amount(trial["minimum_direct_cut"]), Fraction(expected))
                    self.assertEqual(amount(trial["tested_direct_cost"]), 2744000 - Fraction(expected))
                    self.assertLess(amount(trial["one_cent_less_terminal_upper"]), 0)
                    self.assertGreaterEqual(amount(trial["tested_terminal_bounds"]["lower"]), 0)
                    self.assertEqual(trial["original_cash_sha256"], receipt["scenarios"]["Downside"][caption]["cash_sha256"])

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
