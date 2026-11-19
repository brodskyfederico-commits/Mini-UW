"""Keep C60 restricted cash distinct from NOI, debt and gross investor movements."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import test_worksheet_expense_sensitivities as expense_tests
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files, verify_periods
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, MAX_INTEGRATED_PILOT_BYTES, read_package, verify_package, encoded
from plan_return_D107 import OPERATING_PERIOD
from worksheet_annual_coc import quantity as amount
from worksheet_intake_D198 import assemble, register
from worksheet_replacement_reserve_D149 import declared_reserve
from worksheet_sensitivities_D253 import RESERVE_SCHEMA, bind_change, evaluate_scenario


UNIT = "USD_per_eligible_unit_per_year"


def request(inputs):
    result = expense_tests.request(inputs)
    result["schema"] = RESERVE_SCHEMA
    for name in ("Base", "Downside"):
        case = result["scenarios"][name]
        case["changes"].append(expense_tests.change("C60", "relative_change", "fraction_of_baseline", Fraction(1, 100)))
        case["expense_support"]["individual"]["C60"] = dict(source_ref=f"SYNTHETIC-D259-{name}-reserve-rate")
    return result


def flow(cash, event_id):
    row, = [row for row in cash["events"] if row["event_id"] == event_id]
    return amount(row["amount"])


class ReserveSensitivityBindingTests(TestCase):
    def test_missing_reserve_is_pending_explicit_zero_survives_and_v6_stays_closed(self):
        row = dict(field_id="INPUT_C60", value_cell="Inputs!C60", state="CONFIRMED_SYNTHETIC", value=rational(1200))
        zero = expense_tests.change("C60", "replace_absolute", UNIT, 0)
        self.assertEqual(amount(bind_change(zero, {"INPUT_C60": row}, "book", "case", units={"C60": UNIT})["resulting_value"]), 0)
        review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
        for blank in (None, "", " "):
            with self.assertRaises((ValueError, TypeError)):
                bind_change(zero, {"INPUT_C60": row | dict(value=blank)}, "book", "case", units={"C60": UNIT})
            spec = dict(changes=[zero | dict(value=blank)], expense_support=dict(individual={"C60": {}}, combined={}))
            result = evaluate_scenario(spec, "Base", review, dict(cash_per_usd_10={}),
                lambda *args, **kw: self.fail("missing reserve reached the engine"), [], "case", extended=True,
                budget=True, expense=True, reserve=True, scenario_inputs={})
            self.assertEqual(result["state"], "PENDING")
            self.assertIsNone(result["combined"]["cash_per_usd_10"])
        spec = dict(changes=[zero], expense_support=dict(individual={"C60": {}}, combined={}))
        rejected = evaluate_scenario(spec, "Base", review, {}, lambda *args, **kw: self.fail("v6 accepted C60"),
                                     [], "case", extended=True, budget=True, expense=True)
        self.assertEqual(rejected["blockers"], ["sensitivity_driver_inventory_invalid"])

    def test_sale_disposition_and_eligible_units_cannot_default_from_missing(self):
        source = settings_for_acceptance()["rent_inputs"]["replacement_reserve"]
        review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C60", value_cell="Inputs!C60", state="CONFIRMED_SYNTHETIC", value=rational(1200))])
        for key in ("sale_release_fraction", "sale_settlement_ref", "eligible_units", "eligible_units_ref"):
            missing = deepcopy(source)
            missing["scenarios"]["Base"].pop(key)
            with self.assertRaises(ValueError):
                declared_reserve(missing, "Base", review, dict(units=dict(units=26)))
        zero_units = deepcopy(source)
        zero_units["scenarios"]["Base"]["eligible_units"] = 0
        self.assertEqual(amount(declared_reserve(zero_units, "Base", review, dict(units=dict(units=26)))["deposit"]), 0)


class ReserveSensitivityIntegrationTests(TestCase):
    def check_cash_and_reserve(self, view):
        verify_periods(view)
        reserve, cash = view["replacement_reserve"], view["cash_per_usd_10"]
        self.assertEqual(amount(reserve["deposit"]), amount(reserve["annual_rate"])*reserve["eligible_units"])
        self.assertEqual(reserve["deposit"], reserve["restricted_before_sale"])
        self.assertEqual(amount(reserve["released_at_sale"])+amount(reserve["transferred_restricted_to_buyer"]), amount(reserve["deposit"]))
        self.assertEqual(amount(reserve["released_at_sale"]), amount(reserve["deposit"])*amount(reserve["sale_release_fraction"]))
        self.assertEqual(amount(reserve["operating_cash_residual"]), 0)
        self.assertEqual(amount(reserve["sale_cash_residual"]), 0)
        self.assertEqual(reserve["sale_date"], view["project_calendar"]["sale_date"])
        self.assertEqual(amount(view["operating_noi_after_reserve"]["value"]),
                         amount(view["noi_by_period"][OPERATING_PERIOD]["noi"])-amount(reserve["deposit"]))
        contributions, receipts = [sum(amount(row["amount"]) for row in cash["events"] if row["kind"] == kind)
                                   for kind in ("contribution", "distribution")]
        self.assertEqual(amount(cash["events"][0]["amount"]), 10)
        self.assertEqual(amount(cash["total_contributions"]), contributions)
        self.assertEqual(amount(cash["total_distributions"]), receipts)
        self.assertEqual(amount(cash["unrecovered_after_sale"]), max(0, contributions-receipts))

    def test_reserve_and_expenses_replay_release_transfer_and_funding_without_double_counting(self):
        with TemporaryDirectory(prefix="miniuw-d259-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            registration = register(sources, "SYNTHETIC-D259-reserve")
            settings = settings_for_acceptance()
            assemble(settings, registration, sources, root / "origin")
            original = json.loads((root / "origin/results.json").read_bytes())
            settings["rent_inputs"]["sensitivities"] = request(settings["rent_inputs"])
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root / "variants")
            saved = read_package(root / "variants")
            self.assertLessEqual(len(saved["case.json"]), MAX_INTEGRATED_PILOT_BYTES)
            model = json.loads(saved["results.json"])
            self.assertEqual(settings, unchanged)
            self.assertEqual(model["scenarios"], original["scenarios"])
            self.assertEqual(model["decision"], "PENDING")
            sensitivity = model["sensitivity_evaluation"]
            self.assertEqual(sensitivity["state"], "computed_synthetic", {
                name: {cell: row["blockers"] for cell, row in case.get("individual", {}).items()}
                for name, case in sensitivity["scenarios"].items()})
            for name in ("Base", "Downside"):
                baseline = original["scenarios"][name]
                case = sensitivity["scenarios"][name]
                for view in [*case["individual"].values(), case["combined"]]:
                    self.check_cash_and_reserve(view)
                    opex_view = view | dict(bindings=[binding for binding in view["bindings"] if binding["change"]["target_cell"] != "C60"])
                    expense_tests.ExpenseSensitivityIntegrationTests.check_expenses(self, opex_view, baseline, settings["rent_inputs"], name)
                    self.assertEqual(view["construction_financing"], baseline["construction_financing"])
                reserve_only = case["individual"]["C60"]
                old_cash, cash = baseline["cash_per_usd_10"], reserve_only["cash_per_usd_10"]
                old, reserve = baseline["replacement_reserve"], reserve_only["replacement_reserve"]
                delta = amount(reserve["deposit"])-amount(old["deposit"])
                scale, release = amount(cash["scale_factor"]), amount(reserve["sale_release_fraction"])
                self.assertGreater(delta, 0)
                self.assertEqual({p: r["noi"] for p, r in reserve_only["noi_by_period"].items()}, {p: r["noi"] for p, r in baseline["noi_by_period"].items()})
                self.assertEqual(reserve_only["capacity"]["maximum_principal_capacity"], baseline["capacity"]["maximum_principal_capacity"])
                self.assertEqual(reserve_only["gross_sale"], baseline["gross_sale"])
                self.assertEqual(flow(cash, "operating")-flow(old_cash, "operating"), -delta*scale)
                self.assertEqual(flow(cash, "sale")-flow(old_cash, "sale"), delta*release*scale)
                self.assertEqual(amount(cash["total_distributions"])-amount(old_cash["total_distributions"]), -delta*(1-release)*scale)
                binding, = reserve_only["bindings"]
                self.assertEqual(reserve["cell_source"], f"sha256:{sha(encoded(binding))}#/resulting_value")
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            missing = deepcopy(settings)
            missing["rent_inputs"]["replacement_reserve"]["scenarios"]["Base"]["sale_release_fraction"] = None
            missing["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["changes"][-1]["value"] = None
            assemble(missing, registration, sources, root / "missing-support")
            rejected = json.loads((root / "missing-support/results.json").read_bytes())
            self.assertIsNone(rejected["scenarios"]["Base"]["cash_per_usd_10"])
            self.assertIn("replacement_reserve_sale_disposition_unconfirmed:C60", rejected["scenarios"]["Base"]["blockers"])
            downside = rejected["sensitivity_evaluation"]["scenarios"]["Downside"]
            self.assertEqual(downside["individual"]["C60"]["state"], "PENDING")
            self.assertIsNone(downside["combined"]["cash_per_usd_10"])
            self.assertEqual(downside["rank_by_signed_net_cash_delta"], [])

            stressed = deepcopy(settings)
            for name, value in (("Base", 100_000), ("Downside", 0)):
                stressed["rent_inputs"]["sensitivities"]["scenarios"][name]["changes"][-1] = expense_tests.change("C60", "replace_absolute", UNIT, value)
            assemble(stressed, registration, sources, root / "funding-and-zero")
            final = json.loads((root / "funding-and-zero/results.json").read_bytes())["sensitivity_evaluation"]
            large = final["scenarios"]["Base"]["individual"]["C60"]
            self.check_cash_and_reserve(large)
            extra = amount(large["replacement_reserve"]["operating_equity_contribution"])
            self.assertGreater(extra, 0)
            self.assertEqual(flow(large["cash_per_usd_10"], "operating-funding"), extra*amount(large["cash_per_usd_10"]["scale_factor"]))
            self.assertEqual(flow(large["cash_per_usd_10"], "operating"), 0)
            self.assertEqual(large["cash_per_usd_10"]["net_cash_profit"], original["scenarios"]["Base"]["cash_per_usd_10"]["net_cash_profit"])
            zero = final["scenarios"]["Downside"]["combined"]
            self.check_cash_and_reserve(zero)
            for key in ("deposit", "restricted_before_sale", "released_at_sale", "transferred_restricted_to_buyer"):
                self.assertEqual(amount(zero["replacement_reserve"][key]), 0)
