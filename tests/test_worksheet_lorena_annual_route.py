"""Cotejo de la ruta anual vigente contra los criterios sintéticos D230."""

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pypdf import PdfReader

from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import RLV, encode, prepare_configuration
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, read_package
from test_lorena_screening import RECIPE, SOURCE
from test_worksheet_annual_holding import ROUTE, annual_settings, reconcile, source_files
from worksheet_annual_coc import quantity as amount
from worksheet_annual_route_report import render_annual_route
from worksheet_intake_D198 import assemble, register
from worksheet_lorena_screening import rehearse_workbook
from worksheet_sale_rate_grid_D84 import money


MATCHED = "annual_hold_reconciled_noi"
NOI = {"Base": Fraction("466912.470375"), "Downside": Fraction("261099.11675")}


class AnnualLorenaRouteTests(TestCase):
    def test_current_annual_route_preserves_cash_and_requires_joint_rlv_evidence(self):
        settings = annual_settings()
        terms_by_scenario = settings["rent_inputs"]["calendar_checks"]
        for name, routes in terms_by_scenario.items():
            terms = deepcopy(routes[ROUTE])
            for when, row in terms["quarterly_noi_before_reserves"].items():
                row.update(value=rational(NOI[name] / 4), source_ref=f"SYNTHETIC-D235-{name}/{when}")
            routes[MATCHED] = terms
        configuration = encode(prepare_configuration(RECIPE, SOURCE))
        with TemporaryDirectory(prefix="miniuw-annual-criteria-") as tmp:
            root = Path(tmp)
            sources = source_files(root / "sources")
            package, revision = root / "expediente", root / "vigente.json"
            assemble(settings, register(sources, "SYNTHETIC-D235-annual-criteria"), sources, package)
            files = read_package(package)
            revision.write_bytes(files[CURRENT_REVISION_FILE])
            result = json.loads(files["results.json"])
            pdf = root / "annual.pdf"
            for label, rlv_reason in ((ROUTE, "rlv_requires_all_base_metric_inputs"), (MATCHED, "not_attainable_on_grid")):
                with self.subTest(route=label):
                    decision = rehearse_workbook(package, revision, RECIPE, SOURCE, configuration, route=label,
                                                 pdf_output=pdf if label == ROUTE else None)
                    self.assertEqual((decision["decision"], decision["simulation_result"]), ("PENDING", "PENDING"))
                    self.assertFalse(decision["criteria_adopted"])
                    self.assertFalse(decision["deployment_enabled"])
                    self.assertEqual(decision["source_results_sha256"], sha256(files["results.json"]).hexdigest())
                    self.assertEqual(decision["pdf_sha256"], result["pdf_sha256"])
                    self.assertEqual(decision["source"]["Base"]["rlv_price_search"]["blocker"], rlv_reason)
                    states = {(r["scenario"], r["metric_id"]): r["state"] for r in decision["comparisons"]}
                    self.assertEqual(states["Downside", RLV], "N/A")
                    self.assertEqual(states["Base", "IRR"], "FAIL_CONDITION")
                    self.assertEqual(states["Downside", "IRR"], "PASS_NOT_MET")
                    for name, view in result["scenarios"].items():
                        route = result["calendar_checks"][name][label]
                        expected = reconcile(route, view, terms_by_scenario[name][label])
                        evidence = decision["annual_calendar_route"]["scenarios"][name]
                        metrics = decision["observed_metrics"][name]
                        self.assertEqual(evidence["cash_per_usd_10"], expected["cash"])
                        self.assertEqual(evidence["cash_sha256"], sha256(encode(expected["cash"])).hexdigest())
                        self.assertEqual(metrics["post_refi_CoC"]["value"], expected["coc"])
                        if label == MATCHED:
                            original = result["screening"]["metric_evidence_by_scenario"][name]["candidate_definitions"]
                            self.assertEqual(amount(original["YoC"]["noi_before_reserve"]), NOI[name])
                            self.assertEqual(states[name, "breakeven_occupancy"], "PASS_CONDITION")
                        else:
                            self.assertEqual(states[name, "breakeven_occupancy"], "PENDING")
                    if label == ROUTE:
                        exported = pdf.read_bytes()
                        self.assertNotEqual(exported, files["MiniUW_Resumen.pdf"])
                        self.assertEqual(decision["annual_pdf"]["sha256"], sha256(exported).hexdigest())
                        self.assertEqual(decision["annual_pdf"]["revision_sha256"], sha256(revision.read_bytes()).hexdigest())
                        page, = PdfReader(BytesIO(exported)).pages
                        printed = page.extract_text()
                        self.assertIn("Base | Aporte extra 4,87 | Cobro total 16,92", printed)
                        self.assertIn("Downside | Aporte extra 8,32 | Cobro total 4,94", printed)
                        self.assertIn("Precio pedido / RLV | PENDING / N/A", printed)
                        self.assertIn("Dictamen real PENDING | Retorno histórico y personal PENDING", printed)
                        self.assertNotIn("Dictamen simulado", printed)
                        stages = {"construction": "Aporte inicial/obra", "refinance": "Refinanciación",
                                  "operation": "Operación", "sale": "Venta neta"}
                        schedule = {}
                        for name in ("Base", "Downside"):
                            for row in result["calendar_checks"][name][ROUTE]["cash_per_usd_10"]["events"]:
                                key = (row["date"], stages[row["stage"]])
                                schedule.setdefault(key, {})[name] = f"{money(row['contribution'])} / {money(row['receipt'])}"
                        all_lines = {" ".join(line.split()) for line in printed.splitlines()}
                        for (when, stage), flows in schedule.items():
                            base, downside = (flows.get(name, "—") for name in ("Base", "Downside"))
                            self.assertIn(f"{when} {stage} | {base} | {downside}", all_lines)
                        blocked = deepcopy(decision)
                        blocked["annual_calendar_route"]["scenarios"]["Downside"] = {"state": "PENDING"}
                        with self.assertRaisesRegex(ValueError, "Caja anual por USD 10 PENDING"):
                            render_annual_route(blocked)

            def render_then_change(receipt):
                rendered = render_annual_route(receipt)
                revision.write_bytes(files[CURRENT_REVISION_FILE] + b"\n")
                return rendered

            stale = root / "stale.pdf"
            try:
                with patch("worksheet_annual_route_report.render_annual_route", side_effect=render_then_change):
                    with self.assertRaisesRegex(ValueError, "La revisión vigente cambió durante la entrega"):
                        rehearse_workbook(package, revision, RECIPE, SOURCE, configuration, route=ROUTE, pdf_output=stale)
            finally:
                revision.write_bytes(files[CURRENT_REVISION_FILE])
            self.assertFalse(stale.exists())
            self.assertEqual(list(root.glob("*.pdf")), [pdf])
            self.assertEqual(read_package(package), files)
            self.assertEqual(revision.read_bytes(), files[CURRENT_REVISION_FILE])
