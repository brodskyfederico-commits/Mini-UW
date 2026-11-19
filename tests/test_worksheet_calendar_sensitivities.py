"""Replay C46/C47 changes with explicit support for dates and unchanged bank contracts."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import test_worksheet_budget_sensitivities as budget_tests
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, encoded, read_package, verify_package
from worksheet_annual_coc import quantity as amount
from worksheet_calendar_support_D256 import support_inventory, supported_inputs
from worksheet_intake_D198 import assemble, register
from worksheet_sensitivities_D253 import CALENDAR_SCHEMA, bind_change, evaluate_scenario

change = budget_tests.change


EXPECTED = {
    "Base": {
        "C46": ("2027-12-30", "2028-01-01", "2028-04-01", "2028-12-30", "2029-03-30", 8, "2030-03-30"),
        "C47": ("2027-09-30", "2027-10-01", "2027-10-01", "2028-06-30", "2028-09-30", 8, "2029-09-30"),
        "combined": ("2027-12-30", "2028-01-01", "2028-01-01", "2028-09-30", "2028-12-30", 8, "2029-12-30"),
    },
    "Downside": {
        "C46": ("2027-09-30", "2028-01-01", "2028-07-01", "2029-03-30", "2029-06-30", 8, "2030-06-30"),
        "C47": ("2027-12-30", "2028-01-01", "2028-10-01", "2029-06-30", "2029-09-30", 8, "2030-09-30"),
        "combined": ("2027-09-30", "2028-01-01", "2028-10-01", "2029-06-30", "2029-09-30", 8, "2030-09-30"),
    },
}


def support(name, mode):
    _, tco, _, _, sale, count, tax_end = EXPECTED[name][mode]
    source = f"SYNTHETIC-D256-{name}-{mode}"
    result = dict(source_ref=source)
    if name == "Base" and mode in ("C46", "combined"):
        result["tco_date"] = dict(value=tco, source_ref="SYNTHETIC-D256-Base-independent-revised-TCO")
    if name == "Downside" and mode == "C46":
        return result
    result["sale_date"] = dict(value=sale, source_ref=source+"-sale")
    result["maturity_payments"] = dict(value=count, source_ref=source+"-remaining-contractual-payments")
    result["buyer_forward_property_tax"] = dict(basis="buyer_tax_for_exact_forward_window", currency="USD",
        window_start=sale, window_end=tax_end, school_tax=rational(30_000 if name == "Base" else 25_000),
        non_school_tax=rational(45_000), source_ref=source+"-declared-buyer-tax-window")
    return result


def request():
    return dict(schema=CALENDAR_SCHEMA, scenarios={name: dict(
        changes=[change("C46", "month_change", "months", 3 if name == "Base" else -3),
                 change("C47", "month_change", "months", -3 if name == "Base" else 3)],
        calendar_support=dict(individual={cell: support(name, cell) for cell in ("C46", "C47")},
                              combined=support(name, "combined"))) for name in ("Base", "Downside")})


def settings_for_calendar():
    settings = settings_for_acceptance()
    # This separate synthetic market record explicitly covers the trial durations; no runtime range is expanded.
    for name in ("Base", "Downside"):
        record = settings["rent_inputs"]["market_evidence"]["scenarios"][name]["absorption"]
        record["document"].update(source_ref=f"SYNTHETIC-D256-{name}-declared-absorption-range", ranges={
            "C47": dict(minimum=rational(0), maximum=rational(12))})
        record["sha256"] = sha(encoded(record["document"]))
    return settings


class CalendarSensitivityBindingTests(TestCase):
    def test_missing_months_never_become_zero_and_non_month_units_block(self):
        for cell, baseline in (("C46", 6), ("C47", 3)):
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(baseline))
            zero = change(cell, "replace_absolute", "months", 0)
            self.assertEqual(amount(bind_change(zero, {row["field_id"]: row}, "book", "case", units={cell: "months"})["resulting_value"]), 0)
            for value in (None, "", " "):
                with self.assertRaises((ValueError, TypeError)):
                    bind_change(zero | dict(value=value), {row["field_id"]: row}, "book", "case", units={cell: "months"})
                with self.assertRaises((ValueError, TypeError)):
                    bind_change(zero, {row["field_id"]: row | dict(value=value)}, "book", "case", units={cell: "months"})
            for operation, unit, value in (("relative_change", "fraction_of_baseline", 1),
                                            ("basis_point_change", "bps", 1), ("month_change", "months", Fraction(1, 2))):
                with self.assertRaisesRegex(ValueError, "explicit_whole_months"):
                    bind_change(change(cell, operation, unit, value), {row["field_id"]: row}, "book", "case", units={cell: "months"})
            review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
            spec = dict(changes=[zero | dict(value=None)], calendar_support=dict(
                individual={cell: dict(source_ref="SYNTHETIC-D256-single")}, combined=dict(source_ref="SYNTHETIC-D256-joint")))
            result = evaluate_scenario(spec, "Base", review, dict(cash_per_usd_10={}),
                lambda *args, **kw: self.fail("missing months reached the engine"), [], "case", extended=True,
                budget=True, calendar=True, scenario_inputs={})
            self.assertEqual(result["state"], "PENDING")
            self.assertIsNone(result["combined"]["cash_per_usd_10"])

    def test_support_cannot_change_unrelated_parameters_or_implicitly_move_tco(self):
        settings = settings_for_calendar()
        original = deepcopy(settings["rent_inputs"])
        updated, binding = supported_inputs(original, "Base", support("Base", "C46"))
        self.assertEqual(settings["rent_inputs"], original)
        self.assertNotEqual(updated["project_calendar"], original["project_calendar"])
        for key in ("construction_financing", "operating_costs", "market_evidence"):
            self.assertEqual(updated[key], original[key])
        self.assertEqual(binding["origin_inputs_sha256"], sha(encoded(original)))
        for bad in (dict(source_ref=None), dict(source_ref="SYNTHETIC-D256", requested_principal=rational(1)),
                    dict(source_ref="SYNTHETIC-D256", sale_date=dict(value=None, source_ref="SYNTHETIC-D256"))):
            with self.assertRaises((ValueError, TypeError)):
                supported_inputs(original, "Base", bad)
        inventory = request()["scenarios"]["Base"]["calendar_support"]
        invalid = deepcopy(inventory)
        invalid["combined"].pop("tco_date")
        with self.assertRaisesRegex(ValueError, "combined_tco_differs"):
            support_inventory(invalid, ("C46", "C47"))


class CalendarSensitivityIntegrationTests(TestCase):
    def test_individual_and_joint_dates_interest_and_cash_replay_with_pending_controls(self):
        with TemporaryDirectory(prefix="miniuw-d256-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            registration = register(sources, "SYNTHETIC-D256-calendar")
            settings = settings_for_calendar()
            assemble(settings, registration, sources, root / "origin")
            original = json.loads((root / "origin/results.json").read_bytes())
            settings["rent_inputs"]["sensitivities"] = request()
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root / "variants")
            saved = read_package(root / "variants")
            model = json.loads(saved["results.json"])
            self.assertEqual(settings, unchanged)
            self.assertEqual(model["scenarios"], original["scenarios"])
            self.assertEqual(model["decision"], "PENDING")
            result = model["sensitivity_evaluation"]
            self.assertEqual(result["state"], "computed_synthetic", {
                name: {key: row.get("blockers") for key, row in record.get("individual", {}).items()}
                for name, record in result["scenarios"].items()})
            for name in ("Base", "Downside"):
                baseline = original["scenarios"][name]
                observations = result["scenarios"][name]["individual"] | dict(combined=result["scenarios"][name]["combined"])
                for mode, variant in observations.items():
                    expected = EXPECTED[name][mode]
                    calendar = variant["project_calendar"]
                    self.assertEqual(tuple(calendar[key] for key in ("construction_finish", "tco_date", "stabilization_date", "refinance_date", "sale_date")), expected[:5])
                    budget_tests.BudgetSensitivityIntegrationTests.check_finance(self, variant)
                    self.assertEqual(variant["permanent_loan"]["maturity_date"], {
                        "Base": {"C46": "2030-12-30", "C47": "2030-06-30", "combined": "2030-09-30"},
                        "Downside": {"C46": "2031-03-30", "C47": "2031-06-30", "combined": "2031-06-30"},
                    }[name][mode])
                    self.assertEqual(variant["permanent_loan"]["maturity_payments"], expected[5])
                    self.assertEqual(variant["permanent_loan"]["origination_date"], expected[3])
                    self.assertEqual(variant["permanent_loan"]["bank_document_binding"]["blockers"], [])
                    self.assertEqual(variant["cash_per_usd_10"]["scale_factor"], baseline["cash_per_usd_10"]["scale_factor"])
                    for row in variant["cash_per_usd_10"]["events"]:
                        if row["category"] == "net_refinance_distribution":
                            self.assertEqual(row["date"], expected[3])
                        if row["category"] in ("operating_distribution", "net_sale_distribution"):
                            self.assertEqual(row["date"], expected[4])
                    loan = variant["construction_financing"]
                    prior = baseline["construction_financing"]
                    self.assertNotEqual(loan["debt_run"]["totals"]["interest_due"], prior["debt_run"]["totals"]["interest_due"])
                    self.assertEqual(variant["date_comparison"]["sale_date"], dict(original=baseline["project_calendar"]["sale_date"], variant=expected[4]))
                    for binding in variant["bindings"]:
                        cell = binding["change"]["target_cell"]
                        self.assertEqual(calendar["cell_sources"][cell], f"sha256:{sha(encoded(binding))}#/resulting_value")
                if name == "Base":
                    self.assertEqual(amount(observations["combined"]["project_calendar"]["lease_up_funding"]), 0)
                    self.assertEqual(observations["combined"]["project_calendar"]["sale_date"], baseline["project_calendar"]["sale_date"])
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            # Retain the source contracts and show why removing support cannot release current cash.
            invalid = deepcopy(settings)
            invalid["rent_inputs"]["sensitivities"]["scenarios"]["Downside"]["calendar_support"]["individual"]["C47"].pop("sale_date")
            invalid["rent_inputs"]["sensitivities"]["scenarios"]["Base"]["calendar_support"]["individual"]["C47"].pop("buyer_forward_property_tax")
            assemble(invalid, registration, sources, root / "missing-support")
            rejected = json.loads((root / "missing-support/results.json").read_bytes())["sensitivity_evaluation"]
            for name, reason in (("Downside", "declared_sale_date_outside_supported_quarterly_hold"),
                                 ("Base", "buyer_forward_property_tax_source_or_window_unconfirmed")):
                trial = rejected["scenarios"][name]["individual"]["C47"]
                self.assertEqual(trial["state"], "PENDING")
                self.assertIn(reason, trial["blockers"])
                self.assertIsNone(trial["cash_per_usd_10"])
                self.assertEqual(rejected["scenarios"][name]["rank_by_signed_net_cash_delta"], [])

            expired = deepcopy(settings)
            scopes = expired["rent_inputs"]["sensitivities"]["scenarios"]
            scopes["Base"]["calendar_support"]["individual"]["C46"]["maturity_payments"]["value"] = 7
            scopes["Downside"]["changes"][1] = change("C47", "month_change", "months", 6)
            late = support("Downside", "C47")
            late["sale_date"]["value"] = "2029-12-30"
            late["maturity_payments"]["value"] = 8
            late["buyer_forward_property_tax"].update(window_start="2029-12-30", window_end="2030-12-30")
            scopes["Downside"]["calendar_support"] = dict(individual={"C46": support("Downside", "C46"), "C47": late},
                                                          combined=late | dict(source_ref="SYNTHETIC-D256-combined-expiry"))
            assemble(expired, registration, sources, root / "bank-controls")
            blocked = json.loads((root / "bank-controls/results.json").read_bytes())["sensitivity_evaluation"]
            self.assertIn("B08:bank_pdf_and_worksheet_terms_disagree", blocked["scenarios"]["Base"]["individual"]["C46"]["blockers"])
            for mode, trial in (blocked["scenarios"]["Downside"]["individual"] | dict(combined=blocked["scenarios"]["Downside"]["combined"])).items():
                if mode == "C46":
                    continue
                self.assertEqual(trial["state"], "PENDING")
                self.assertIsNone(trial["cash_per_usd_10"])
                self.assertTrue(any("maturity" in reason for reason in trial["blockers"]), trial["blockers"])
