"""Exercise opt-in operating sensitivities without silently replacing the base case."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from test_worksheet_sensitivities import change
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, encoded, read_package, verify_package
from worksheet_annual_coc import quantity as amount
from worksheet_intake_D198 import assemble, register
from worksheet_sensitivities_D253 import EXTENDED_SCHEMA, bind_change, evaluate_scenario
from plan_return_D107 import FORWARD_PERIOD


class OperatingSensitivityBindingTests(TestCase):
    def test_missing_and_explicit_zero_for_each_new_numeric_driver(self):
        units = {cell: "USD_per_unit_per_month" for cell in ("C8", "C9", "C10", "C11")}
        units.update({cell: "USD_per_rentable_sf_per_year" for cell in ("C16", "C17", "C18")})
        units.update({cell: "fraction" for cell in ("C14", "C15", "C19")})
        units["C76"] = "annual_effective_growth_fraction"
        for cell, unit in units.items():
            rows = {f"INPUT_{cell}": dict(value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(1))}
            request = change(cell, "replace_absolute", unit, 0)
            with self.subTest(cell=cell):
                self.assertEqual(amount(bind_change(request, rows, "book", "case", units=units)["resulting_value"]), 0)
                for blank in (None, "", " "):
                    with self.assertRaises((ValueError, TypeError)):
                        bind_change(request | dict(value=blank), rows, "book", "case", units=units)
                    missing = deepcopy(rows)
                    missing[f"INPUT_{cell}"]["value"] = blank
                    with self.assertRaises((ValueError, TypeError)):
                        bind_change(request, missing, "book", "case", units=units)
                    review = dict(rows=[dict(field_id="INPUT_C7", value="PER UNIT"),
                                        rows[f"INPUT_{cell}"] | dict(field_id=f"INPUT_{cell}")], workbook_sha256="book")
                    evaluation = evaluate_scenario(dict(changes=[request | dict(value=blank)]), "Base", review,
                                                   dict(cash_per_usd_10={}),
                                                   lambda *args: self.fail("blank reached the engine"),
                                                   [], "case", extended=True)
                    self.assertIsNone(evaluation["combined"]["cash_per_usd_10"])
                    self.assertEqual(evaluation["state"], "PENDING")
                if unit.startswith("USD_"):
                    with self.assertRaisesRegex(ValueError, "requires_fraction"):
                        bind_change(change(cell, "basis_point_change", "bps", 1), rows, "book", "case", units=units)

    def test_sf_rent_basis_is_bound_and_wrong_units_block_before_calculation(self):
        rows = [dict(field_id="INPUT_C7", value="PER SF"),
                dict(field_id="INPUT_C8", value_cell="Inputs!C8", state="CONFIRMED_SYNTHETIC", value=rational(2))]
        review = dict(rows=rows, workbook_sha256="book")
        trial = dict(changes=[change("C8", "replace_absolute", "USD_per_unit_per_month", 3)])
        result = evaluate_scenario(trial, "Base", review, dict(cash_per_usd_10={}),
                                   lambda *args: self.fail("invalid units reached the engine"), [], "case", extended=True)
        self.assertEqual(result["individual"]["C8"]["blockers"], ["sensitivity_change_unit_mismatch"])
        result = bind_change(trial["changes"][0] | dict(unit="USD_per_rentable_sf_per_month"),
                             {"INPUT_C8": rows[1]}, "book", "case", units={"C8": "USD_per_rentable_sf_per_month"})
        self.assertEqual(result["resulting_unit"], "USD_per_rentable_sf_per_month")


class OperatingSensitivityIntegrationTests(TestCase):
    def test_operating_changes_replay_dated_cash_and_evidence_blocks(self):
        with TemporaryDirectory(prefix="miniuw-d254-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            settings = settings_for_acceptance()
            registration = register(sources, "SYNTHETIC-D254-operating")
            assemble(settings, registration, sources, root / "origin")
            original = json.loads((root / "origin/results.json").read_bytes())
            changes = [change(cell, "relative_change", "fraction_of_baseline", Fraction(-1, 100))
                       for cell in ("C8", "C9", "C10", "C11", "C16", "C17", "C18")]
            changes += [change(cell, "basis_point_change", "bps", 1) for cell in ("C14", "C15", "C19", "C76")]
            settings["rent_inputs"]["sensitivities"] = dict(schema=EXTENDED_SCHEMA, scenarios={
                "Base": dict(changes=changes),
                "Downside": dict(changes=[change("C8", "relative_change", "fraction_of_baseline", -1),
                                          change("C76", "replace_absolute", "annual_effective_growth_fraction", Fraction(1, 2))])})
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root / "variants")
            saved = read_package(root / "variants")
            result = json.loads(saved["results.json"])
            self.assertEqual(settings, unchanged)
            self.assertEqual(result["scenarios"], original["scenarios"])
            self.assertEqual(result["decision"], "PENDING")
            evaluation = result["sensitivity_evaluation"]
            self.assertEqual(evaluation["schema"], EXTENDED_SCHEMA)
            base, downside = (evaluation["scenarios"][name] for name in ("Base", "Downside"))
            self.assertEqual(set(base["individual"]), {row["target_cell"] for row in changes})
            self.assertEqual(base["state"], "computed_synthetic", base)
            self.assertEqual(downside["state"], "PENDING")
            self.assertIn("B08:market_assumption_outside_evidence:C8", downside["individual"]["C8"]["blockers"])
            self.assertIn("selected_principal_exceeds_declared_bank_capacity", downside["individual"]["C76"]["blockers"])
            self.assertIsNone(downside["combined"]["cash_per_usd_10"])
            self.assertEqual(downside["rank_by_signed_net_cash_delta"], [])
            origin = original["scenarios"]["Base"]
            for cell, observation in base["individual"].items():
                binding, = observation["bindings"]
                if cell in {"C16", "C17", "C18", "C19"}:
                    provenance = observation["commercial_terms"]["cell_sources"]
                elif cell == "C76":
                    provenance = observation["growth_terms"]["cell_sources"]
                else:
                    provenance = observation["cell_sources"]
                self.assertEqual(provenance[cell], f"sha256:{sha(encoded(binding))}#/resulting_value")
                self.assertNotEqual(observation["noi_by_period"], origin["noi_by_period"], cell)
                self.assertLess(amount(observation["forward_noi"]), amount(origin["noi_by_period"][FORWARD_PERIOD]["noi"]), cell)
                self.assertNotEqual(observation["cash_per_usd_10"], origin["cash_per_usd_10"], cell)
            combined = base["combined"]
            cash = combined["cash_per_usd_10"]
            self.assertEqual(amount(cash["events"][0]["amount"]), 10)
            totals = {kind: sum(amount(event["amount"]) for event in cash["events"] if event["kind"] == kind)
                      for kind in ("contribution", "distribution")}
            self.assertEqual(amount(cash["total_contributions"]), totals["contribution"])
            self.assertEqual(amount(cash["total_distributions"]), totals["distribution"])
            self.assertEqual(amount(cash["unrecovered_after_sale"]), max(0, totals["contribution"]-totals["distribution"]))
            self.assertEqual(amount(combined["delta_net_cash_per_usd_10"]),
                             totals["distribution"]-totals["contribution"]
                             - amount(origin["cash_per_usd_10"]["total_distributions"])
                             + amount(origin["cash_per_usd_10"]["total_contributions"]))
            self.assertNotEqual(amount(combined["delta_net_cash_per_usd_10"]),
                                sum(amount(item["delta_net_cash_per_usd_10"]) for item in base["individual"].values()))
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")
