"""Verify construction-budget shocks through dated debt and initial USD 10 equity."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from test_worksheet_sensitivities import change as declared_change
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, encoded, read_package, verify_package
from plan_return_D107 import FORWARD_PERIOD
from worksheet_annual_coc import quantity as amount
from worksheet_intake_D198 import assemble, register
from worksheet_sensitivities_D253 import BUDGET_SCHEMA, bind_change, evaluate_scenario


UNITS = dict(C37="USD_per_parking_space", C38="USD_total", C39="fraction", C40="fraction",
             C41="USD_per_rentable_sf", C42="fraction")


def change(cell, operation, unit, value):
    return declared_change(cell, operation, unit, value) | dict(source_ref=f"SYNTHETIC-D255-explicit-{cell}")


def changes(name):
    costs = [change(cell, "relative_change", "fraction_of_baseline", Fraction(1, 100)) for cell in ("C37", "C38", "C41")]
    costs += [change("C40", "basis_point_change", "bps", 10)]
    costs += ([change("C39", "basis_point_change", "bps", 10), change("C42", "percentage_point_change", "percentage_points", 1)]
              if name == "Base" else [change(cell, "replace_absolute", "fraction", 0) for cell in ("C39", "C42")])
    return costs + [change("C9", "relative_change", "fraction_of_baseline", Fraction(-1, 1000))]


def amounts_by_date(cash):
    return {row["date"]: sum(amount(item["amount"]) for item in cash["events"]
                             if item["kind"] == "contribution" and item["date"] == row["date"])
            for row in cash["events"] if row["kind"] == "contribution"}


class BudgetSensitivityBindingTests(TestCase):
    def test_all_six_fields_keep_blanks_pending_and_preserve_explicit_zero(self):
        for cell, unit in UNITS.items():
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(1))
            request = change(cell, "replace_absolute", unit, 0)
            review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
            with self.subTest(cell=cell):
                self.assertEqual(amount(bind_change(request, {row["field_id"]: row}, "book", "case", units=UNITS)["resulting_value"]), 0)
                invalid = [request | dict(value=value) for value in (None, "", " ")]
                invalid += [{key: value for key, value in request.items() if key != missing} for missing in ("value", "source_ref")]
                for variant in invalid:
                    output = evaluate_scenario(dict(changes=[variant]), "Base", review, dict(cash_per_usd_10={}),
                                               lambda *args: self.fail("unconfirmed input reached the motor"),
                                               [], "case", extended=True, budget=True)
                    self.assertEqual(output["state"], "PENDING")
                    self.assertIsNone(output["combined"]["cash_per_usd_10"])
                    self.assertEqual(output["rank_by_signed_net_cash_delta"], [])
                for blank in (None, "", " "):
                    with self.assertRaises((ValueError, TypeError)):
                        bind_change(request, {row["field_id"]: row | dict(value=blank)}, "book", "case", units=UNITS)
                with self.assertRaisesRegex(ValueError, "baseline_cell_unconfirmed"):
                    bind_change(request, {row["field_id"]: row | dict(state="NOT_APPLICABLE", value=None)}, "book", "case", units=UNITS)

    def test_prior_contracts_reject_budget_drivers_and_currency_rejects_rate_units(self):
        review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT")])
        for extended in (False, True):
            result = evaluate_scenario(dict(changes=[change("C37", "replace_absolute", UNITS["C37"], 0)]),
                                       "Base", review, {}, lambda *args: self.fail("old schema accepted a new field"),
                                       [], "case", extended=extended)
            self.assertEqual(result["blockers"], ["sensitivity_driver_inventory_invalid"])
        for cell in ("C37", "C38", "C41"):
            row = dict(value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(1))
            with self.assertRaisesRegex(ValueError, "requires_fraction"):
                bind_change(change(cell, "basis_point_change", "bps", 1), {f"INPUT_{cell}": row}, "book", "case", units=UNITS)


class BudgetSensitivityIntegrationTests(TestCase):
    def check_finance(self, variant):
        cash, funding, budget = (variant[key] for key in ("cash_per_usd_10", "construction_financing", "construction_budget"))
        scale = amount(cash["scale_factor"])
        self.assertEqual(amount(cash["events"][0]["amount"]), 10)
        for row in funding["cash_by_date"]:
            self.assertEqual(sum(amount(row[key]) for key in ("opening_free_cash", "loan_draw", "equity_contribution")),
                             sum(amount(row[key]) for key in ("project_uses", "interest_paid", "origination_fee_paid", "closing_free_cash")))
        self.assertEqual(sum(amount(row["project_uses"]) for row in funding["cash_by_date"]),
                         amount(budget["total_development_cost"])+amount(variant["project_calendar"]["lease_up_funding"]))
        self.assertEqual(amount(funding["commitment"]), min(amount(funding["eligible_direct_hard"])*amount(funding["ltc"]),
                                                           amount(funding["contractual_limit"])))
        periods = funding["debt_run"]["periods"]
        for row in periods:
            self.assertEqual(amount(row["closing_principal"]), amount(row["opening_principal"])+amount(row["draw_at_start"])-amount(row["principal_repayment_at_end"]))
            self.assertEqual(amount(row["interest_due_at_end"]),
                             (amount(row["opening_principal"])+amount(row["draw_at_start"]))*amount(funding["annual_interest"])/4)
        self.assertEqual(funding["construction_principal_payoff"], funding["debt_run"]["totals"]["principal_repaid"])
        closing = variant["construction_refinance"]
        self.assertEqual(closing["prior_principal_paid"], funding["construction_principal_payoff"])
        self.assertEqual(sum(amount(closing[key]) for key in ("gross_proceeds", "opening_free_cash", "projected_cash_in_required")),
                         sum(amount(closing[key]) for key in ("prior_principal_paid", "closing_fee", "closing_restricted_cash", "net_equity_distribution")))
        contributions, receipts = [sum(amount(row["amount"]) for row in cash["events"] if row["kind"] == kind)
                                   for kind in ("contribution", "distribution")]
        self.assertEqual(amount(cash["total_contributions"]), contributions)
        self.assertEqual(amount(cash["total_distributions"]), receipts)
        self.assertEqual(amount(cash["unrecovered_after_sale"]), max(0, contributions-receipts))
        self.assertEqual(sum(amount(row["equity_contribution"]) for row in funding["cash_by_date"])*scale, contributions)

    def check_budget(self, variant):
        budget = variant["construction_budget"]
        inputs = {cell: amount(next(entry for entry in variant["bindings"] if entry["change"]["target_cell"] == cell)["resulting_value"])
                  for cell in UNITS if any(entry["change"]["target_cell"] == cell for entry in variant["bindings"])}
        get = lambda cell, key: inputs[cell] if cell in inputs else amount(budget[key])
        parking = get("C37", "parking_rate")*budget["parking_spaces"]
        direct = amount(variant["development_costs"]["vertical_cost"])+parking+get("C38", "site_cost")
        contingency = direct*get("C39", "contingency_rate")
        hard = direct+contingency
        soft = hard*get("C40", "soft_rate")
        ti = get("C41", "ti_lc_rate")*amount(budget["commercial_area_sf"])
        land = sum(amount(variant["development_costs"][key]) for key in ("evaluated_purchase_price", "land_closing_cost"))
        self.assertEqual(amount(budget["total_development_cost"]), land+hard+soft+ti)
        self.assertEqual(amount(budget["upfront_soft"]), soft*get("C42", "upfront_soft_share"))
        self.assertEqual(amount(budget["remaining_soft"])+amount(budget["upfront_soft"]), soft)
        for binding in variant["bindings"]:
            cell = binding["change"]["target_cell"]
            if cell in UNITS:
                self.assertEqual(budget["cell_sources"][cell], f"sha256:{sha(encoded(binding))}#/resulting_value")

    def test_budget_and_rent_shocks_recalculate_equity_debt_and_joint_cash(self):
        with TemporaryDirectory(prefix="miniuw-d255-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            registration = register(sources, "SYNTHETIC-D255-budget")
            settings = settings_for_acceptance()
            assemble(settings, registration, sources, root / "origin")
            original = json.loads((root / "origin/results.json").read_bytes())
            settings["rent_inputs"]["sensitivities"] = dict(schema=BUDGET_SCHEMA,
                scenarios={name: dict(changes=changes(name)) for name in ("Base", "Downside")})
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root / "variants")
            saved = read_package(root / "variants")
            result = json.loads(saved["results.json"])
            self.assertEqual(settings, unchanged)
            self.assertEqual(result["scenarios"], original["scenarios"])
            self.assertEqual(result["decision"], "PENDING")
            sensitivity = result["sensitivity_evaluation"]
            self.assertEqual(sensitivity["schema"], BUDGET_SCHEMA)
            self.assertEqual(sensitivity["state"], "computed_synthetic")
            for name in ("Base", "Downside"):
                scenario = sensitivity["scenarios"][name]
                baseline = original["scenarios"][name]
                for cell, variant in scenario["individual"].items():
                    self.assertEqual(variant["state"], "computed_synthetic", (name, cell, variant["blockers"]))
                    self.check_budget(variant)
                    self.check_finance(variant)
                    if cell in UNITS:
                        self.assertEqual(amount(variant["forward_noi"]), amount(baseline["noi_by_period"][FORWARD_PERIOD]["noi"]))
                    if cell == "C42":
                        for key in ("total_contributions", "total_distributions"):
                            self.assertEqual(variant["cash_per_usd_10"][key], baseline["cash_per_usd_10"][key])
                        actual = {row["date"]: row for row in variant["construction_financing"]["cash_by_date"]}
                        prior = {row["date"]: row for row in baseline["construction_financing"]["cash_by_date"]}
                        upfront, finish = (variant["project_calendar"][key] for key in ("upfront_date", "construction_finish"))
                        shifted = amount(variant["construction_budget"]["upfront_soft"])-amount(baseline["construction_budget"]["upfront_soft"])
                        self.assertNotEqual(shifted, 0)
                        self.assertEqual(amount(actual[upfront]["project_uses"])-amount(prior[upfront]["project_uses"]), shifted)
                        self.assertEqual(amount(actual[finish]["project_uses"])-amount(prior[finish]["project_uses"]), -shifted)
                        if name == "Base":
                            # The initial cash buffer covers this earlier invoice without another capital call.
                            self.assertEqual(amounts_by_date(variant["cash_per_usd_10"]), amounts_by_date(baseline["cash_per_usd_10"]))
                            self.assertEqual(amount(actual[upfront]["closing_free_cash"])-amount(prior[upfront]["closing_free_cash"]), -shifted)
                        else:
                            self.assertNotEqual(amounts_by_date(variant["cash_per_usd_10"]), amounts_by_date(baseline["cash_per_usd_10"]))
                combined = scenario["combined"]
                self.check_budget(combined)
                self.check_finance(combined)
                self.assertNotEqual(amount(combined["delta_net_cash_per_usd_10"]),
                                    sum(amount(row["delta_net_cash_per_usd_10"]) for row in scenario["individual"].values()))
            downside = sensitivity["scenarios"]["Downside"]["combined"]["construction_budget"]
            self.assertEqual(amount(downside["contingency_reserve"]), 0)
            self.assertEqual(amount(downside["upfront_soft"]), 0)
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            blocked = deepcopy(settings)
            blocked["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["changes"] = [
                change("C37", "replace_absolute", "USD_per_parking_space", 1_000_000),
                change("C40", "basis_point_change", "bps", 10)]
            assemble(blocked, registration, sources, root / "blocked")
            blocked_result = json.loads((root / "blocked/results.json").read_bytes())
            downside = blocked_result["sensitivity_evaluation"]["scenarios"]["Downside"]
            self.assertEqual(downside["state"], "PENDING")
            self.assertIsNone(downside["individual"]["C37"]["cash_per_usd_10"])
            self.assertEqual(downside["individual"]["C40"]["state"], "computed_synthetic")
            self.assertTrue(downside["individual"]["C37"]["construction_financing"]["blockers"])
            self.assertEqual(downside["rank_by_signed_net_cash_delta"], [])
            self.assertIsNone(downside["combined"]["cash_per_usd_10"])
            self.assertEqual(blocked_result["scenarios"], original["scenarios"])
