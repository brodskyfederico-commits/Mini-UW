"""Verify C61/C62, exact tax branches, capacity and gross USD 10 cash."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files, verify_periods
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, MAX_INTEGRATED_PILOT_BYTES, encoded, read_package, verify_package
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from test_worksheet_sensitivities import change as base_change
from worksheet_annual_coc import quantity as amount
from worksheet_intake_D198 import assemble, register
from worksheet_property_tax_D150 import declared_property_tax
from worksheet_sensitivities_D253 import TAX_SCHEMA, TAX_UNITS, bind_change, evaluate_scenario, evaluate_trial


def change(cell, operation, unit, value):
    return base_change(cell, operation, unit, value) | dict(source_ref=f"SYNTHETIC-D260-explicit-{cell}")


def request():
    return dict(schema=TAX_SCHEMA, scenarios={name: dict(changes=[
        change("C61", "percentage_point_change", "percentage_points", 1),
        change("C62", "relative_change", "fraction_of_baseline", Fraction(1, 100)),
    ]) for name in ("Base", "Downside")})


def event(cash, event_id):
    row, = [row for row in cash["events"] if row["event_id"] == event_id]
    return amount(row["amount"])


def cash_values(cash):
    return dict(events=[{k: row[k] for k in ("event_id", "kind", "date", "amount")} for row in cash["events"]],
                totals={k: cash[k] for k in ("total_contributions", "total_distributions", "net_cash_profit", "unrecovered_after_sale")})


class TaxSensitivityBindingTests(TestCase):
    def test_blanks_sources_units_and_legacy_inventory_never_default(self):
        for cell, unit in TAX_UNITS.items():
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(1))
            zero = change(cell, "replace_absolute", unit, 0)
            self.assertEqual(amount(bind_change(zero, {row["field_id"]: row}, "book", "case", units=TAX_UNITS)["resulting_value"]), 0)
            review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
            for blank in (None, "", " "):
                with self.assertRaises((ValueError, TypeError)):
                    bind_change(zero, {row["field_id"]: row | dict(value=blank)}, "book", "case", units=TAX_UNITS)
                spec = dict(changes=[zero | dict(value=blank)])
                result = evaluate_scenario(spec, "Base", review, dict(cash_per_usd_10={}),
                    lambda *a, **k: self.fail("missing input reached the engine"), [], "case", extended=True, tax=True)
                self.assertEqual(result["state"], "PENDING")
                self.assertIsNone(result["combined"]["cash_per_usd_10"])
            for invalid in (zero | dict(unit="undeclared_tax_unit"), zero | dict(source_ref=None)):
                with self.assertRaises(ValueError):
                    bind_change(invalid, {row["field_id"]: row}, "book", "case", units=TAX_UNITS)
            spec = dict(changes=[zero], expense_support=dict(individual={cell: {}}, combined={}))
            legacy = evaluate_scenario(spec, "Base", review, {}, lambda *a, **k: self.fail("v7 accepted tax"),
                                       [], "case", extended=True, budget=True, expense=True, reserve=True)
            self.assertEqual(legacy["blockers"], ["sensitivity_driver_inventory_invalid"])

    def test_tax_evidence_ranges_and_explicit_zero(self):
        raw = settings_for_acceptance()["rent_inputs"]["property_tax"]
        review = dict(workbook_sha256="book", rows=[dict(field_id=f"INPUT_{c}", value_cell=f"Inputs!{c}",
                      state="CONFIRMED_SYNTHETIC", value=rational(v)) for c, v in (("C61", 0), ("C62", 0))])
        groups = dict(test=dict(units=26))
        zero = declared_property_tax(raw, "Base", review, groups)
        self.assertEqual(amount(zero["floor"]), 0)
        self.assertEqual(amount(zero["coefficient"]), 0)
        for key in ("assessment_source_ref", "comparable_source_ref", "comparable_units", "assessed_tax_rate", "market_proxy_cap"):
            missing = deepcopy(raw)
            missing["scenarios"]["Base"].pop(key)
            with self.assertRaises(ValueError):
                declared_property_tax(missing, "Base", review, groups)
        for key in ("assessed_tax_rate", "market_proxy_cap"):
            for field, value in (("unit", "undeclared_millage"), ("value", None), ("source_ref", None)):
                invalid = deepcopy(raw)
                invalid["scenarios"]["Base"][key][field] = value
                with self.assertRaises(ValueError):
                    declared_property_tax(invalid, "Base", review, groups)
        for cell, value in (("C61", Fraction(101, 100)), ("C61", -1), ("C62", -1)):
            invalid = deepcopy(review)
            next(r for r in invalid["rows"] if r["field_id"] == f"INPUT_{cell}")["value"] = rational(value)
            with self.assertRaises(ValueError):
                declared_property_tax(raw, "Base", invalid, groups)

    def test_unconnected_tax_profile_or_stale_cell_reference_is_pending(self):
        row = dict(field_id="INPUT_C61", value_cell="Inputs!C61", state="CONFIRMED_SYNTHETIC", value=rational(Fraction(4, 5)))
        binding = bind_change(change("C61", "percentage_point_change", "percentage_points", 1),
                              {row["field_id"]: row}, "book", "case", units=TAX_UNITS)
        candidate = dict(blockers=[], cash_per_usd_10={}, capacity={}, noi_by_period={OPERATING_PERIOD: {}},
                         development_costs={}, construction_budget={}, construction_financing={}, construction_refinance={}, project_calendar={})
        for tax in ({}, {"cell_sources": {"C61": "sha256:old-book#Inputs!C61"}}):
            trial = deepcopy(candidate)
            trial["noi_by_period"][OPERATING_PERIOD]["property_tax"] = tax
            result = evaluate_trial("Base", dict(rows=[row]), [binding], {}, lambda *a, **k: trial,
                                    extended=True, budget=True, tax=True)
            self.assertEqual(result["blockers"], ["sensitivity_property_tax_basis_not_connected:C61-C62"])
            self.assertIsNone(result["cash_per_usd_10"])


class TaxSensitivityIntegrationTests(TestCase):
    def check_tax_and_cash(self, variant, baseline):
        verify_periods(variant)
        selected = {b["change"]["target_cell"]: b for b in variant["bindings"]}
        for period in (OPERATING_PERIOD, BANK_PERIOD, VALUE_PERIOD):
            row, original = variant["noi_by_period"][period], baseline["noi_by_period"][period]
            tax, old = row["property_tax"], original["property_tax"]
            values = {c: amount(selected[c]["resulting_value"]) if c in selected else amount(old[key])
                      for c, key in (("C61", "assessment_ratio"), ("C62", "comparable_rate"))}
            floor = values["C62"]*old["comparable_units"]
            k = values["C61"]*amount(old["assessed_tax_rate"]["value"])/amount(old["market_proxy_cap"]["value"])
            pre_tax = amount(original["property_tax"]["operating_before_tax"])
            expected_noi = min(pre_tax-floor, pre_tax/(1+k))
            self.assertEqual(amount(tax["floor"]), floor)
            self.assertEqual(amount(tax["coefficient"]), k)
            self.assertEqual(amount(row["noi"]), expected_noi)
            self.assertEqual(amount(tax["annual_tax"]), max(floor, k*expected_noi))
            self.assertEqual(amount(tax["equation_residual"]), 0)
            self.assertEqual(row["operating_expenses_excluding_tax"], original["operating_expenses_excluding_tax"])
            self.assertEqual(row["gross_rent"], original["gross_rent"])
            for cell, b in selected.items():
                self.assertEqual(tax["cell_sources"][cell], f"sha256:{sha(encoded(b))}#/resulting_value")
        self.assertEqual(variant["capacity"]["bank_noi"], variant["noi_by_period"][BANK_PERIOD]["noi"])
        self.assertEqual(variant["capacity"]["valuation_noi"], variant["noi_by_period"][VALUE_PERIOD]["noi"])
        self.assertEqual(variant["noi_by_period"][FORWARD_PERIOD], baseline["noi_by_period"][FORWARD_PERIOD])
        pricing = variant["valuation_and_sale"]
        self.assertEqual(pricing["refinance_noi"], variant["noi_by_period"][VALUE_PERIOD]["noi"])
        self.assertEqual(amount(pricing["refinance_value"]), amount(pricing["refinance_noi"])/amount(pricing["refinance_cap"]))
        for key in ("buyer_property_tax", "forward_noi", "gross_sale_price", "sale_cost", "exit_cap", "sale_date"):
            self.assertEqual(pricing[key], baseline["valuation_and_sale"][key])
        self.assertEqual(variant["gross_sale"], baseline["gross_sale"])
        self.assertEqual(variant["construction_financing"], baseline["construction_financing"])
        self.assertEqual(variant["project_calendar"], baseline["project_calendar"])
        for key in ("annual_rate", "eligible_units", "deposit", "restricted_before_sale", "released_at_sale", "transferred_restricted_to_buyer"):
            self.assertEqual(variant["replacement_reserve"][key], baseline["replacement_reserve"][key])
        old_cash, cash = baseline["cash_per_usd_10"], variant["cash_per_usd_10"]
        self.assertEqual(cash["scale_factor"], old_cash["scale_factor"])
        self.assertEqual(event(cash, "initial"), 10)
        self.assertEqual(cash["total_contributions"], old_cash["total_contributions"])
        delta_tax = amount(variant["noi_by_period"][OPERATING_PERIOD]["property_tax"]["annual_tax"])-amount(baseline["noi_by_period"][OPERATING_PERIOD]["property_tax"]["annual_tax"])
        self.assertEqual(event(cash, "operating")-event(old_cash, "operating"), -delta_tax*amount(cash["scale_factor"]))
        self.assertEqual(event(cash, "sale"), event(old_cash, "sale"))
        self.assertEqual(event(cash, "refinance"), event(old_cash, "refinance"))
        self.assertEqual(amount(cash["total_distributions"])-amount(old_cash["total_distributions"]), -delta_tax*amount(cash["scale_factor"]))
        self.assertEqual(amount(cash["unrecovered_after_sale"]), max(0, amount(cash["total_contributions"])-amount(cash["total_distributions"])))

    def test_tax_changes_individual_joint_branches_capacity_missing_and_zero(self):
        with TemporaryDirectory(prefix="miniuw-d260-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            registration = register(sources, "SYNTHETIC-D260-property-tax")
            settings = settings_for_acceptance()
            assemble(settings, registration, sources, root / "origin")
            baseline = json.loads((root / "origin/results.json").read_bytes())
            settings["rent_inputs"]["sensitivities"] = request()
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root / "variants")
            saved = read_package(root / "variants")
            self.assertLessEqual(len(saved["case.json"]), MAX_INTEGRATED_PILOT_BYTES)
            model = json.loads(saved["results.json"])
            self.assertEqual(settings, unchanged)
            self.assertEqual(model["scenarios"], baseline["scenarios"])
            self.assertEqual(model["decision"], "PENDING")
            evaluation = model["sensitivity_evaluation"]
            self.assertEqual(evaluation["state"], "computed_synthetic", evaluation)
            for name, case in evaluation["scenarios"].items():
                for view in [*case["individual"].values(), case["combined"]]:
                    self.check_tax_and_cash(view, baseline["scenarios"][name])
                self.assertEqual(len(case["rank_by_signed_net_cash_delta"]), 2)
            # A non-binding input can preserve cash without being ignored: its evidence and k/floor still change.
            for name, cell in (("Base", "C61"), ("Downside", "C62")):
                self.assertEqual(cash_values(evaluation["scenarios"][name]["individual"][cell]["cash_per_usd_10"]),
                                 cash_values(baseline["scenarios"][name]["cash_per_usd_10"]))
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            switched = deepcopy(settings)
            switched["rent_inputs"]["sensitivities"]["scenarios"]["Base"]["changes"][0] = change("C61", "replace_absolute", TAX_UNITS["C61"], 1)
            switched["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["changes"][1] = change("C62", "replace_absolute", TAX_UNITS["C62"], 1800)
            assemble(switched, registration, sources, root / "branch-switch")
            branch = json.loads((root / "branch-switch/results.json").read_bytes())["sensitivity_evaluation"]
            self.assertEqual(branch["state"], "computed_synthetic")
            for name, field, expected in (("Base", "C61", "proxy"), ("Downside", "C62", "floor")):
                trial = branch["scenarios"][name]["individual"][field]
                self.check_tax_and_cash(trial, baseline["scenarios"][name])
                self.assertEqual(trial["noi_by_period"][OPERATING_PERIOD]["property_tax"]["branch"], expected)

            zero = deepcopy(settings)
            for spec in zero["rent_inputs"]["sensitivities"]["scenarios"].values():
                spec["changes"] = [change(c, "replace_absolute", u, 0) for c, u in TAX_UNITS.items()]
            assemble(zero, registration, sources, root / "zero-controls")
            zeros = json.loads((root / "zero-controls/results.json").read_bytes())["sensitivity_evaluation"]
            self.assertEqual(zeros["state"], "computed_synthetic")
            for name, case in zeros["scenarios"].items():
                for trial in [*case["individual"].values(), case["combined"]]:
                    self.check_tax_and_cash(trial, baseline["scenarios"][name])
                for period in (OPERATING_PERIOD, BANK_PERIOD, VALUE_PERIOD):
                    tax = case["combined"]["noi_by_period"][period]["property_tax"]
                    self.assertEqual(amount(tax["annual_tax"]), 0)
                    self.assertEqual(tax["branch"], "tie")

            missing = deepcopy(settings)
            missing["rent_inputs"]["property_tax"]["scenarios"]["Base"].pop("assessment_source_ref")
            missing["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["changes"][1]["value"] = None
            assemble(missing, registration, sources, root / "missing-support")
            rejected = json.loads((root / "missing-support/results.json").read_bytes())
            self.assertIsNone(rejected["scenarios"]["Base"]["cash_per_usd_10"])
            self.assertIn("property_tax_assessment_source_unconfirmed:C61", rejected["scenarios"]["Base"]["blockers"])
            pending = rejected["sensitivity_evaluation"]["scenarios"]["Downside"]
            self.assertEqual(pending["individual"]["C61"]["state"], "computed_synthetic")
            self.assertIsNone(pending["individual"]["C62"]["cash_per_usd_10"])
            self.assertIsNone(pending["combined"]["cash_per_usd_10"])
            self.assertEqual(pending["rank_by_signed_net_cash_delta"], [])

            stressed = deepcopy(settings)
            stressed["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["changes"][1] = change("C62", "replace_absolute", TAX_UNITS["C62"], 3000)
            assemble(stressed, registration, sources, root / "capacity-block")
            blocked = json.loads((root / "capacity-block/results.json").read_bytes())["sensitivity_evaluation"]
            self.assertEqual(blocked["scenarios"]["Base"]["state"], "computed_synthetic")
            downside = blocked["scenarios"]["Downside"]
            self.assertEqual(downside["individual"]["C61"]["state"], "computed_synthetic")
            for trial in (downside["individual"]["C62"], downside["combined"]):
                self.assertIn("selected_principal_exceeds_declared_bank_capacity", trial["blockers"])
                self.assertIsNone(trial["cash_per_usd_10"])
                self.assertLess(amount(trial["capacity"]["maximum_principal_capacity"]), amount(trial["capacity"]["selected_principal"]))
            self.assertEqual(downside["rank_by_signed_net_cash_delta"], [])
