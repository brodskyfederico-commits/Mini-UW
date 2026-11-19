"""Connect C66-C68 without treating appraised value or capacity as investor cash."""
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
from worksheet_exit_pricing_D151 import declared_valuation_terms
from worksheet_intake_D198 import assemble, register
from worksheet_sensitivities_D253 import PRICING_SCHEMA, PRICING_UNITS, bind_change, evaluate_scenario, evaluate_trial


def change(cell, operation, unit, value):
    return base_change(cell, operation, unit, value) | dict(source_ref=f"SYNTHETIC-D261-explicit-{cell}")


def request():
    return dict(schema=PRICING_SCHEMA, scenarios={name: dict(changes=[
        change(cell, "basis_point_change", "bps", 1) for cell in PRICING_UNITS
    ]) for name in ("Base", "Downside")})


def event(cash, event_id):
    row, = [row for row in cash["events"] if row["event_id"] == event_id]
    return amount(row["amount"])


def financial_events(cash):
    return [{k: row[k] for k in ("event_id", "kind", "date", "amount")} for row in cash["events"]]


class PricingSensitivityBindingTests(TestCase):
    def test_blank_values_missing_sources_wrong_units_and_old_inventory_block(self):
        for cell, unit in PRICING_UNITS.items():
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(Fraction(1, 10)))
            zero = change(cell, "replace_absolute", unit, 0)
            # Numeric zero reaches the domain validator; it is never a substitute for a blank.
            self.assertEqual(amount(bind_change(zero, {row["field_id"]: row}, "book", "case", units=PRICING_UNITS)["resulting_value"]), 0)
            review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
            for blank in (None, "", " "):
                with self.assertRaises((ValueError, TypeError)):
                    bind_change(zero, {row["field_id"]: row | dict(value=blank)}, "book", "case", units=PRICING_UNITS)
                result = evaluate_scenario(dict(changes=[zero | dict(value=blank)]), "Base", review,
                    dict(cash_per_usd_10={}), lambda *a, **k: self.fail("blank reached calculation"), [], "case",
                    extended=True, pricing=True)
                self.assertEqual(result["state"], "PENDING")
                self.assertIsNone(result["combined"]["cash_per_usd_10"])
            for invalid in (zero | dict(unit="monthly_fraction"), zero | dict(source_ref=None)):
                with self.assertRaises(ValueError):
                    bind_change(invalid, {row["field_id"]: row}, "book", "case", units=PRICING_UNITS)
        spec = dict(changes=[change("C66", "replace_absolute", PRICING_UNITS["C66"], Fraction(1, 10))])
        legacy = evaluate_scenario(spec, "Base", review, {}, lambda *a, **k: self.fail("v8 accepted C66"),
                                   [], "case", extended=True, tax=True)
        self.assertEqual(legacy["blockers"], ["sensitivity_driver_inventory_invalid"])

    def test_valuation_scope_cost_inventory_and_zero_cap_cannot_default(self):
        raw = settings_for_acceptance()["rent_inputs"]["valuation_and_sale"]
        review = dict(workbook_sha256="book", rows=[dict(field_id=f"INPUT_{c}", value_cell=f"Inputs!{c}",
            state="CONFIRMED_SYNTHETIC", value=rational(v)) for c, v in (("C66", Fraction(1, 10)), ("C67", Fraction(1, 10)), ("C68", 0))])
        self.assertEqual(amount(declared_valuation_terms(raw, "Base", review)["sale_cost_fraction"]), 0)
        for key in ("refinance_cap_ref", "exit_cap_ref", "sale_at_value_ref", "sale_cost_inventory_ref", "nonoverlap_ref", "inventory_declared_complete"):
            invalid = deepcopy(raw)
            invalid["scenarios"]["Base"].pop(key)
            with self.assertRaises(ValueError):
                declared_valuation_terms(invalid, "Base", review)
        for cell, value in (("C66", 0), ("C67", 0), ("C66", -1), ("C68", -1), ("C68", Fraction(101, 100))):
            invalid = deepcopy(review)
            next(r for r in invalid["rows"] if r["field_id"] == f"INPUT_{cell}")["value"] = rational(value)
            with self.assertRaisesRegex(ValueError, "out_of_range"):
                declared_valuation_terms(raw, "Base", invalid)

    def test_pricing_must_reach_the_documented_valuation_basis(self):
        row = dict(field_id="INPUT_C66", value_cell="Inputs!C66", state="CONFIRMED_SYNTHETIC", value=rational(Fraction(1, 10)))
        binding = bind_change(change("C66", "basis_point_change", "bps", 1), {row["field_id"]: row}, "book", "case", units=PRICING_UNITS)
        for refs in ({}, {"C66": "sha256:stale-book#Inputs!C66"}):
            trial = dict(blockers=[], cash_per_usd_10={}, capacity={}, valuation_and_sale=dict(cell_sources=refs))
            result = evaluate_trial("Base", dict(rows=[row]), [binding], {}, lambda *a, **k: trial,
                                    extended=True, pricing=True)
            self.assertEqual(result["blockers"], ["sensitivity_valuation_basis_not_connected:C66-C68"])
            self.assertIsNone(result["cash_per_usd_10"])


class PricingSensitivityIntegrationTests(TestCase):
    def check_pricing_and_cash(self, trial, baseline):
        verify_periods(trial)
        pricing = trial["valuation_and_sale"]
        selected = {b["change"]["target_cell"]: b for b in trial["bindings"]}
        original_pricing = baseline["valuation_and_sale"]
        rates = {c: amount(selected[c]["resulting_value"]) if c in selected else amount(original_pricing[k])
                 for c, k in (("C66", "refinance_cap"), ("C67", "exit_cap"), ("C68", "sale_cost_fraction"))}
        self.assertEqual(trial["noi_by_period"], baseline["noi_by_period"])
        refi_value = amount(baseline["noi_by_period"][VALUE_PERIOD]["noi"])/rates["C66"]
        gross_sale = amount(baseline["noi_by_period"][FORWARD_PERIOD]["noi"])/rates["C67"]
        fixed = amount(original_pricing["fixed_sale_cost"]["value"])
        costs = gross_sale*rates["C68"]+fixed
        self.assertEqual(amount(pricing["refinance_value"]), refi_value)
        self.assertEqual(amount(pricing["gross_sale_price"]), gross_sale)
        self.assertEqual(amount(pricing["sale_cost"]), costs)
        capacity = trial["capacity"]
        limits = {k: amount(v) for k, v in capacity["capacity_limits"].items()}
        self.assertEqual(limits["LTV"], refi_value*amount(trial["permanent_loan"]["maximum_ltv"]))
        self.assertEqual(amount(capacity["maximum_principal_capacity"]), min(limits.values()))
        self.assertEqual(set(capacity["binding_limit_ids"]), {k for k, v in limits.items() if v == min(limits.values())})
        for key in ("DSCR", "DEBT_YIELD"):
            self.assertEqual(capacity["capacity_limits"][key], baseline["capacity"]["capacity_limits"][key])
        self.assertEqual(capacity["selected_principal"], baseline["capacity"]["selected_principal"])
        self.assertEqual(trial["construction_financing"], baseline["construction_financing"])
        self.assertEqual(trial["project_calendar"], baseline["project_calendar"])
        cash, old_cash = trial["cash_per_usd_10"], baseline["cash_per_usd_10"]
        self.assertEqual(cash["scale_factor"], old_cash["scale_factor"])
        self.assertEqual(event(cash, "initial"), 10)
        self.assertEqual(cash["total_contributions"], old_cash["total_contributions"])
        self.assertEqual(event(cash, "refinance"), event(old_cash, "refinance"))
        self.assertEqual(event(cash, "operating"), event(old_cash, "operating"))
        delta = (gross_sale-costs-amount(original_pricing["gross_sale_price"])+amount(original_pricing["sale_cost"]))*amount(cash["scale_factor"])
        self.assertEqual(event(cash, "sale")-event(old_cash, "sale"), delta)
        self.assertEqual(amount(cash["total_distributions"])-amount(old_cash["total_distributions"]), delta)
        for kind, total in (("contribution", "total_contributions"), ("distribution", "total_distributions")):
            self.assertEqual(sum(amount(e["amount"]) for e in cash["events"] if e["kind"] == kind), amount(cash[total]))
        self.assertEqual(amount(cash["unrecovered_after_sale"]), max(0, amount(cash["total_contributions"])-amount(cash["total_distributions"])))
        self.assertEqual(amount(pricing["closing_cash_residual"]), 0)
        for cell, binding in selected.items():
            self.assertEqual(pricing["cell_sources"][cell], f"sha256:{sha(encoded(binding))}#/resulting_value")
        if "C67" in selected:
            evidence = trial["market_insurance_review"]["records"]["exit_cap"]
            self.assertEqual(evidence["blockers"], [])
            self.assertEqual(evidence["comparisons"]["C67"]["value_source"], pricing["cell_sources"]["C67"])
        percent, fixed_row = pricing["sale_cost_run"]["cost_rows"]
        self.assertEqual(amount(percent["computed_cost"]), gross_sale*rates["C68"])
        self.assertEqual(percent["claim"]["source_ref"], pricing["cell_sources"]["C68"])
        self.assertEqual(amount(fixed_row["computed_cost"]), fixed)

    def test_individual_and_joint_pricing_capacity_missing_and_zero(self):
        with TemporaryDirectory(prefix="miniuw-d261-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            registration = register(sources, "SYNTHETIC-D261-pricing")
            settings = settings_for_acceptance()
            assemble(settings, registration, sources, root / "origin")
            original = json.loads((root / "origin/results.json").read_bytes())
            settings["rent_inputs"]["sensitivities"] = request()
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root / "variants")
            saved = read_package(root / "variants")
            self.assertLessEqual(len(saved["case.json"]), MAX_INTEGRATED_PILOT_BYTES)
            model = json.loads(saved["results.json"])
            self.assertEqual(settings, unchanged)
            self.assertEqual(model["scenarios"], original["scenarios"])
            self.assertEqual(model["decision"], "PENDING")
            self.assertFalse(model["deployment_enabled"])
            self.assertFalse(model["real_decisions_enabled"])
            evaluation = model["sensitivity_evaluation"]
            self.assertEqual(evaluation["state"], "computed_synthetic", evaluation)
            for name, case in evaluation["scenarios"].items():
                baseline = original["scenarios"][name]
                for trial in [*case["individual"].values(), case["combined"]]:
                    self.check_pricing_and_cash(trial, baseline)
                self.assertEqual(financial_events(case["individual"]["C66"]["cash_per_usd_10"]), financial_events(baseline["cash_per_usd_10"]))
                isolated_delta = sum(amount(t["delta_net_cash_per_usd_10"]) for t in case["individual"].values())
                self.assertNotEqual(amount(case["combined"]["delta_net_cash_per_usd_10"]), isolated_delta)
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            controls = deepcopy(settings)
            cases = controls["rent_inputs"]["sensitivities"]["scenarios"]
            cases["Base"]["changes"][0] = change("C66", "replace_absolute", PRICING_UNITS["C66"], Fraction(5, 100))
            cases["Downside"]["changes"][0] = change("C66", "replace_absolute", PRICING_UNITS["C66"], Fraction(12, 100))
            cases["Downside"]["changes"][1] = change("C67", "replace_absolute", PRICING_UNITS["C67"], Fraction(20, 100))
            assemble(controls, registration, sources, root / "capacity-and-evidence")
            controlled = json.loads((root / "capacity-and-evidence/results.json").read_bytes())["sensitivity_evaluation"]
            base = controlled["scenarios"]["Base"]["individual"]["C66"]
            self.check_pricing_and_cash(base, original["scenarios"]["Base"])
            self.assertEqual(original["scenarios"]["Base"]["capacity"]["binding_limit_ids"], ["LTV"])
            self.assertEqual(base["capacity"]["binding_limit_ids"], ["DEBT_YIELD"])
            downside = controlled["scenarios"]["Downside"]
            self.assertIn("selected_principal_exceeds_declared_bank_capacity", downside["individual"]["C66"]["blockers"])
            self.assertLess(amount(downside["individual"]["C66"]["capacity"]["maximum_principal_capacity"]), amount(downside["individual"]["C66"]["capacity"]["selected_principal"]))
            self.assertIn("B08:market_assumption_outside_evidence:C67", downside["individual"]["C67"]["blockers"])
            self.assertEqual(downside["individual"]["C68"]["state"], "computed_synthetic")
            self.assertIsNone(downside["combined"]["cash_per_usd_10"])
            self.assertEqual(downside["rank_by_signed_net_cash_delta"], [])

            missing = deepcopy(settings)
            missing["rent_inputs"]["valuation_and_sale"]["scenarios"]["Base"].pop("sale_cost_inventory_ref")
            missing["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["changes"][0]["value"] = None
            assemble(missing, registration, sources, root / "missing-support")
            rejected = json.loads((root / "missing-support/results.json").read_bytes())
            self.assertIsNone(rejected["scenarios"]["Base"]["cash_per_usd_10"])
            self.assertIn("valuation_evidence_or_sale_cost_inventory_unconfirmed:C66-C68", rejected["scenarios"]["Base"]["blockers"])
            pending = rejected["sensitivity_evaluation"]["scenarios"]["Downside"]
            self.assertIsNone(pending["individual"]["C66"]["cash_per_usd_10"])
            self.assertEqual(pending["individual"]["C67"]["state"], "computed_synthetic")
            self.assertEqual(pending["individual"]["C68"]["state"], "computed_synthetic")
            self.assertIsNone(pending["combined"]["cash_per_usd_10"])
            self.assertEqual(pending["rank_by_signed_net_cash_delta"], [])

            zeros = deepcopy(settings)
            for name, cell in (("Base", "C66"), ("Downside", "C67")):
                changes = zeros["rent_inputs"]["sensitivities"]["scenarios"][name]["changes"]
                i = list(PRICING_UNITS).index(cell)
                changes[i] = change(cell, "replace_absolute", PRICING_UNITS[cell], 0)
                changes[2] = change("C68", "replace_absolute", PRICING_UNITS["C68"], 0)
            assemble(zeros, registration, sources, root / "zero-controls")
            zero = json.loads((root / "zero-controls/results.json").read_bytes())["sensitivity_evaluation"]
            for name, cell in (("Base", "C66"), ("Downside", "C67")):
                case = zero["scenarios"][name]
                self.assertIsNone(case["individual"][cell]["cash_per_usd_10"])
                self.assertIsNone(case["combined"]["cash_per_usd_10"])
                self.assertEqual(case["rank_by_signed_net_cash_delta"], [])
                cost = case["individual"]["C68"]
                self.check_pricing_and_cash(cost, original["scenarios"][name])
                self.assertEqual(amount(cost["valuation_and_sale"]["sale_cost_fraction"]), 0)
                self.assertEqual(cost["valuation_and_sale"]["sale_cost"], cost["valuation_and_sale"]["fixed_sale_cost"]["value"])
