"""Accept the explicit sensitivity workflow through assembly and source replay."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, encoded, read_package, verify_package, write_package
from worksheet_annual_coc import quantity as amount
from worksheet_intake_D198 import assemble, prepare, register
from worksheet_sensitivities_D253 import SCHEMA


def change(cell, operation, unit, value):
    return dict(target_cell=cell, operation=operation, unit=unit, value=rational(Fraction(value)),
                source_ref=f"SYNTHETIC-D253-declared-{cell}")


def settings_with_shocks():
    settings = settings_for_acceptance()
    settings["rent_inputs"]["sensitivities"] = dict(schema=SCHEMA, scenarios={
        "Base": dict(changes=[
            change("C67", "basis_point_change", "bps", 50),
            change("C68", "replace_absolute", "fraction_of_gross_sale_price", 0),
            change("C75", "relative_change", "fraction_of_baseline", Fraction(-1, 3)),
        ]),
        "Downside": dict(changes=[
            change("C67", "basis_point_change", "bps", 200),
            change("C68", "replace_absolute", "fraction_of_gross_sale_price", 0),
            change("C75", "percentage_point_change", "percentage_points", "-11.5"),
        ]),
    })
    return settings


def sale_receipt(cash):
    receipt, = [event for event in cash["events"] if event["category"] == "net_sale_distribution"]
    return amount(receipt["amount"])


class WorksheetSensitivitiesTests(TestCase):
    def test_combined_shocks_replay_cash_and_keep_unconfirmed_changes_visible(self):
        with TemporaryDirectory(prefix="miniuw-d253-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            settings = settings_with_shocks()
            before = deepcopy(settings)
            inputs = settings_for_acceptance()
            origin = root / "origin"
            registration = register(sources, "SYNTHETIC-D253-baseline")
            assemble(inputs, registration, sources, origin)
            saved_origin = read_package(origin)
            baseline = json.loads(saved_origin["results.json"])
            destination = root / "variants"
            case_registration = register(sources, "SYNTHETIC-D253-shocks")
            assemble(settings, case_registration, sources, destination)
            self.assertEqual(settings, before)
            saved = read_package(destination)
            model = json.loads(saved["results.json"])
            self.assertEqual(read_package(origin), saved_origin)
            self.assertNotIn("sensitivity_evaluation", baseline)
            self.assertEqual(model["scenarios"], baseline["scenarios"])
            screening = [dict(result["screening"]) for result in (model, baseline)]
            for contract, result in zip(screening, (model, baseline)):
                self.assertEqual(contract.pop("input_case_sha256"), result["case_sha256"])
            self.assertEqual(*screening)
            self.assertEqual(model["decision"], "PENDING")

            sensitivity = model["sensitivity_evaluation"]
            self.assertEqual(sensitivity["decision"], "PENDING")
            self.assertEqual(sensitivity["revision_sha256"], sha(saved[CURRENT_REVISION_FILE]))
            self.assertEqual(sensitivity["request_sha256"], sha(encoded(settings["rent_inputs"]["sensitivities"])))
            self.assertEqual(sensitivity["state"], "PENDING")
            base, downside = (sensitivity["scenarios"][name] for name in ("Base", "Downside"))
            self.assertEqual(base["state"], "computed_synthetic")
            self.assertEqual(downside["state"], "PENDING")

            for cell, result in base["individual"].items():
                self.assertEqual(result["state"], "computed_synthetic")
                binding, = result["bindings"]
                expected = {"C67": "0.0925", "C68": "0", "C75": "0.02"}[cell]
                self.assertEqual(amount(binding["resulting_value"]), Fraction(expected))
                self.assertTrue(binding["base_cell_ref"].endswith(f"#Inputs!{cell}"))
                driver_record = result["valuation_and_sale"].get("cell_sources", {})
                if cell in driver_record:
                    self.assertEqual(driver_record[cell], f"sha256:{sha(encoded(binding))}#/resulting_value")
            combined = base["combined"]
            self.assertEqual(len(combined["bindings"]), 3)
            cash = combined["cash_per_usd_10"]
            initial = cash["events"][0]
            self.assertEqual(amount(initial["amount"]), 10)
            ledger = {kind: sum(amount(row["amount"]) for row in cash["events"] if row["kind"] == kind)
                      for kind in ("contribution", "distribution")}
            self.assertEqual((ledger["contribution"], ledger["distribution"]),
                             (amount(cash["total_contributions"]), amount(cash["total_distributions"])))
            self.assertEqual(amount(cash["unrecovered_after_sale"]), max(0, ledger["contribution"]-ledger["distribution"]))
            pricing = combined["valuation_and_sale"]
            original = baseline["scenarios"]["Base"]
            old_price = original["valuation_and_sale"]
            original_cash = original["cash_per_usd_10"]
            new_price = amount(combined["forward_noi"]) / Fraction("0.0925")
            self.assertEqual(amount(pricing["gross_sale_price"]), new_price)
            self.assertEqual(sale_receipt(cash) - sale_receipt(original_cash),
                             (new_price - amount(old_price["gross_sale_price"]) + amount(old_price["sale_cost"])
                              - amount(pricing["sale_cost"])) * amount(cash["scale_factor"]))
            individual = [amount(row["delta_net_cash_per_usd_10"]) for row in base["individual"].values()]
            self.assertNotEqual(amount(combined["delta_net_cash_per_usd_10"]), sum(individual))
            self.assertEqual([amount(group["delta_net_cash_per_usd_10"])
                              for group in base["rank_by_signed_net_cash_delta"]], sorted(individual))
            self.assertEqual(downside["individual"]["C68"]["state"], "computed_synthetic")
            self.assertIn("B08:market_assumption_outside_evidence:C67", downside["individual"]["C67"]["blockers"])
            self.assertIn("selected_principal_exceeds_declared_bank_capacity", downside["individual"]["C75"]["blockers"])
            self.assertIsNone(downside["combined"]["cash_per_usd_10"])
            self.assertEqual(downside["rank_by_signed_net_cash_delta"], [])
            self.assertEqual(verify_package(destination, current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            invalid_settings = deepcopy(settings)
            invalid_settings["rent_inputs"]["sensitivities"]["scenarios"]["Base"]["changes"][0]["unit"] = "fraction"
            invalid_path = root / "invalid"
            assemble(invalid_settings, case_registration, sources, invalid_path)
            invalid = json.loads((invalid_path / "results.json").read_bytes())["sensitivity_evaluation"]["scenarios"]["Base"]
            self.assertEqual(invalid["individual"]["C67"]["blockers"], ["sensitivity_change_unit_mismatch"])
            self.assertEqual(invalid["combined"]["blockers"], ["sensitivity_combination_has_unconfirmed_inputs"])
            self.assertEqual(invalid["individual"]["C68"]["state"], "computed_synthetic")
            raw, _ = prepare(invalid_settings, case_registration)
            stale_path = root / "stale"
            write_package(raw, stale_path, current_revision_raw=saved[CURRENT_REVISION_FILE], **sources)
            stale = json.loads((stale_path / "results.json").read_bytes())["sensitivity_evaluation"]
            for scenario in stale["scenarios"].values():
                self.assertIsNone(scenario["cash_per_usd_10"])
                self.assertIn("financial_sources_fingerprint_mismatch", scenario["blockers"])
