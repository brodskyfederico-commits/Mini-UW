"""Verify C57-C59 through expense bases, NOI, refi capacity and USD 10 cash."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import test_worksheet_budget_sensitivities as budget_tests
from test_worksheet_sensitivities import change as base_change
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, MAX_INTEGRATED_PILOT_BYTES, encoded, read_package, verify_package
from worksheet_annual_coc import quantity as amount
from worksheet_expense_support_D258 import supported_inputs
from worksheet_intake_D198 import assemble, register
from worksheet_sensitivities_D253 import EXPENSE_SCHEMA, bind_change, evaluate_scenario


UNITS = dict(C57="USD_per_residential_unit_per_year", C58="fraction_of_effective_residential_income_plus_c13",
             C59="USD_per_insured_unit_per_year")


def change(cell, operation, unit, value):
    return base_change(cell, operation, unit, value) | dict(source_ref=f"SYNTHETIC-D258-explicit-{cell}")


def support(inputs, name, label, premium=None):
    record = dict(source_ref=f"SYNTHETIC-D258-{name}-{label}-support")
    if premium is not None:
        parent = inputs["market_evidence"]["scenarios"][name]["insurance"]
        doc = deepcopy(parent["document"])
        doc.update(source_ref=f"SYNTHETIC-D258-{name}-{label}-insurance", premium_per_insured_unit=rational(Fraction(premium)))
        record["insurance"] = dict(parent_sha256=parent["sha256"], document=doc, sha256=sha(encoded(doc)))
    return record


def request(inputs):
    scenarios = {}
    for name, premium in (("Base", 303), ("Downside", Fraction("555.5"))):
        scenarios[name] = dict(changes=[
            change("C57", "relative_change", "fraction_of_baseline", Fraction(1, 100)),
            change("C58", "basis_point_change", "bps", 1),
            change("C59", "relative_change", "fraction_of_baseline", Fraction(1, 100))],
            expense_support=dict(individual={cell: support(inputs, name, cell, premium if cell == "C59" else None)
                                               for cell in UNITS}, combined=support(inputs, name, "combined", premium)))
    return dict(schema=EXPENSE_SCHEMA, scenarios=scenarios)


class ExpenseSensitivityBindingTests(TestCase):
    def test_blank_base_or_change_is_pending_and_explicit_zero_stays_numeric(self):
        for cell, unit in UNITS.items():
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(1))
            zero = change(cell, "replace_absolute", unit, 0)
            self.assertEqual(amount(bind_change(zero, {row["field_id"]: row}, "book", "case", units=UNITS)["resulting_value"]), 0)
            review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
            for value in (None, "", " "):
                with self.assertRaises((ValueError, TypeError)):
                    bind_change(zero, {row["field_id"]: row | dict(value=value)}, "book", "case", units=UNITS)
                spec = dict(changes=[zero | dict(value=value)], expense_support=dict(individual={cell: {}}, combined={}))
                result = evaluate_scenario(spec, "Base", review, dict(cash_per_usd_10={}),
                    lambda *args, **kw: self.fail("missing input reached the engine"), [], "case", extended=True,
                    budget=True, expense=True, scenario_inputs={})
                self.assertEqual(result["state"], "PENDING")
                self.assertIsNone(result["combined"]["cash_per_usd_10"])
            with self.assertRaisesRegex(ValueError, "unit_mismatch"):
                bind_change(zero | dict(unit="monthly_fraction"), {row["field_id"]: row}, "book", "case", units=UNITS)

    def test_insurance_revision_cannot_change_coverage_dates_or_other_sources(self):
        inputs = settings_for_acceptance()["rent_inputs"]
        bindings = [dict(change=dict(target_cell="C59"))]
        source = support(inputs, "Base", "unit", 303)
        before = deepcopy(inputs)
        updated, proof = supported_inputs(inputs, "Base", source, bindings)
        self.assertEqual(inputs, before)
        for key in ("operating_costs", "utilities", "construction_financing"):
            self.assertEqual(updated[key], inputs[key])
        for role in ("rent", "absorption", "exit_cap", "concessions"):
            self.assertEqual(updated["market_evidence"]["scenarios"]["Base"][role], inputs["market_evidence"]["scenarios"]["Base"][role])
        self.assertEqual(proof["insurance_revision"]["sha256"], sha(encoded(source["insurance"]["document"])))
        for field, value in (("insured_units", 0), ("coverage_ref", "SYNTHETIC-other-coverage"),
                             ("valid_through", "2030-01-01"), ("scenario", "Downside")):
            bad = deepcopy(source)
            bad["insurance"]["document"][field] = value
            bad["insurance"]["sha256"] = sha(encoded(bad["insurance"]["document"]))
            with self.assertRaisesRegex(ValueError, "coverage_or_scope_changed"):
                supported_inputs(inputs, "Base", bad, bindings)
        for bad in (source | dict(insurance=source["insurance"] | dict(parent_sha256="0"*64)),
                    source | dict(insurance=source["insurance"] | dict(sha256="0"*64)), dict(source_ref=None)):
            with self.assertRaises(ValueError):
                supported_inputs(inputs, "Base", bad, bindings)


class ExpenseSensitivityIntegrationTests(TestCase):
    def check_expenses(self, variant, baseline, inputs, name):
        selected = {cell: amount(next(entry["resulting_value"] for entry in variant["bindings"] if entry["change"]["target_cell"] == cell))
                    for cell in UNITS if any(entry["change"]["target_cell"] == cell for entry in variant["bindings"])}
        original_costs = next(iter(baseline["noi_by_period"].values()))["operating_costs"]
        rates = dict(C57=amount(original_costs["controllable_total"])/original_costs["controllable_units"],
                     C58=amount(original_costs["management_rate"]),
                     C59=amount(original_costs["insurance_total"])/original_costs["insured_units"]) | selected
        for period, row in variant["noi_by_period"].items():
            costs = row["operating_costs"]
            growth = amount(row["growth"]["expense_factor"])
            controllable = rates["C57"]*costs["controllable_units"]*growth
            insurance = rates["C59"]*costs["insured_units"]*growth
            eligible = amount(row["effective_rent"])+amount(row["other_income"])
            management = eligible*rates["C58"]
            self.assertEqual(amount(costs["controllable_total"]), controllable)
            self.assertEqual(amount(costs["controllable_excluding_utilities"])+amount(row["utilities"]["annual_total"]), controllable)
            self.assertEqual(amount(costs["insurance_total"]), insurance)
            self.assertEqual(amount(costs["management_eligible_egi"]), eligible)
            self.assertEqual(amount(costs["management_fee"]), management)
            fixed = amount(inputs["annual_expenses"]["fixed_opex"])*growth
            total = controllable+insurance+management+fixed
            self.assertEqual(amount(row["operating_expenses_excluding_tax"]), total)
            tax = amount(row["buyer_property_tax"]["total"] if "buyer_property_tax" in row else row["property_tax"]["annual_tax"])
            self.assertEqual(amount(row["noi"]), eligible+amount(row["commercial"]["net"])-total-tax)
            for binding in variant["bindings"]:
                cell = binding["change"]["target_cell"]
                self.assertEqual(costs["cell_sources"][cell], f"sha256:{sha(encoded(binding))}#/resulting_value")
        if "C59" in selected:
            quote = variant["market_insurance_review"]["records"]["insurance"]
            self.assertEqual(quote["blockers"], [])
            self.assertEqual(amount(quote["document"]["premium_per_insured_unit"]), rates["C59"])
            binding = next(entry for entry in variant["bindings"] if entry["change"]["target_cell"] == "C59")
            self.assertEqual(quote["comparison"]["value_source"], f"sha256:{sha(encoded(binding))}#/resulting_value")

    def test_individual_and_joint_expenses_noi_cash_and_pending_controls(self):
        with TemporaryDirectory(prefix="miniuw-d258-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            registration = register(sources, "SYNTHETIC-D258-expenses")
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
                cases = sensitivity["scenarios"][name]
                for variant in [*cases["individual"].values(), cases["combined"]]:
                    budget_tests.BudgetSensitivityIntegrationTests.check_finance(self, variant)
                    self.check_expenses(variant, baseline, settings["rent_inputs"], name)
                    self.assertEqual(variant["project_calendar"], baseline["project_calendar"])
                    self.assertLess(amount(variant["cash_per_usd_10"]["total_distributions"]), amount(baseline["cash_per_usd_10"]["total_distributions"]))
                    self.assertEqual(variant["cash_per_usd_10"]["total_contributions"], baseline["cash_per_usd_10"]["total_contributions"])
                    self.assertEqual(variant["construction_financing"], baseline["construction_financing"])
                for period, row in cases["combined"]["noi_by_period"].items():
                    self.assertGreater(amount(row["operating_expenses_excluding_tax"]),
                                       amount(baseline["noi_by_period"][period]["operating_expenses_excluding_tax"]))
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            missing = deepcopy(settings)
            missing["rent_inputs"]["sensitivities"]["scenarios"]["Base"]["expense_support"]["individual"]["C59"].pop("insurance")
            changed = missing["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["expense_support"]["individual"]["C59"]["insurance"]
            changed["document"]["premium_per_insured_unit"] = rational(1)
            changed["sha256"] = sha(encoded(changed["document"]))
            assemble(missing, registration, sources, root / "missing-support")
            rejected = json.loads((root / "missing-support/results.json").read_bytes())["sensitivity_evaluation"]
            for name, reason in (("Base", "expense_support_source_or_inventory_unconfirmed"),
                                 ("Downside", "B08:insurance_quote_disagrees:C59")):
                trial = rejected["scenarios"][name]["individual"]["C59"]
                self.assertEqual(trial["state"], "PENDING")
                self.assertIsNone(trial["cash_per_usd_10"])
                self.assertIn(reason, trial["blockers"])
                self.assertEqual(rejected["scenarios"][name]["rank_by_signed_net_cash_delta"], [])

            zeros = deepcopy(settings)
            zero_cases = zeros["rent_inputs"]["sensitivities"]["scenarios"]
            for name, cell in (("Base", "C58"), ("Base", "C59"), ("Downside", "C57")):
                zero_cases[name]["changes"][list(UNITS).index(cell)] = change(cell, "replace_absolute", UNITS[cell], 0)
            for label in ("C59", "combined"):
                record = support(settings["rent_inputs"], "Base", label+"-zero", 0)
                if label == "combined":
                    zero_cases["Base"]["expense_support"][label] = record
                else:
                    zero_cases["Base"]["expense_support"]["individual"][label] = record
            assemble(zeros, registration, sources, root / "zero-controls")
            zero_result = json.loads((root / "zero-controls/results.json").read_bytes())["sensitivity_evaluation"]
            for row in zero_result["scenarios"]["Base"]["combined"]["noi_by_period"].values():
                self.assertEqual(amount(row["operating_costs"]["management_fee"]), 0)
                self.assertEqual(amount(row["operating_costs"]["insurance_total"]), 0)
            for row in (zero_result["scenarios"]["Downside"]["individual"]["C57"], zero_result["scenarios"]["Downside"]["combined"]):
                self.assertEqual(row["state"], "PENDING")
                self.assertIsNone(row["cash_per_usd_10"])
                self.assertIn("utilities_exceed_controllable_budget:C57", row["blockers"])
