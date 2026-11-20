"""AMI arithmetic, explicit zero, complete windows and integration safeguards."""
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import encoded, read_case_source, MAX_REGULATED_RENT_BYTES
from worksheet_regulated_rent_D269 import PROFILE, RULES, SCHEMA, UNITS, configuration, project_window
from check_worksheet_regulated_rent_D269 import run, independently_verify, reference_window, value


class RegulatedRentContractTests(TestCase):
    def fixture(self):
        groups = {group: dict(units=3 if group == "studio" else 0) for group in ("studio", "1BR", "2BR", "3BR")}
        allocations = {group: dict(regulated_units=1 if group == "studio" else 0,
            market_units=2 if group == "studio" else 0, source_ref="SYNTHETIC-D269-allocation") for group in groups}
        windows = {}
        for year in (2028, 2029):
            limits = {group: dict(applicability="not_applicable", source_ref="SYNTHETIC-D269-NA") for group in groups}
            limits["studio"] = dict(applicability="applicable", source_ref="SYNTHETIC-D269-limit",
                imputed_household_size=1, household_basis_ref="SYNTHETIC-D269-imputed-size",
                **{key:dict(value=rational(number), unit=UNITS[key], source_ref="SYNTHETIC-D269-"+key)
                   for key,number in dict(annual_AMI_income=60_000, income_limit_fraction=Q(4,5),
                       rent_income_share=Q(3,10), utility_allowance_monthly=100).items()})
            windows[f"{year}-01-01"] = dict(source_ref="SYNTHETIC-D269-window", evidence_kind="synthetic_forecast",
                valid_from=f"{year}-01-01", valid_until_exclusive=f"{year+1}-01-01", limits=limits)
        scenario = dict(source_ref="SYNTHETIC-D269-scenario", leaseup_assumption_ref="SYNTHETIC-D269-net-leaseup-budget",
                        allocations=allocations, windows=windows)
        raw = dict(profile=PROFILE, currency="USD", rules=RULES, source_ref="SYNTHETIC-D269-contract",
                   scenarios={name:deepcopy(scenario) for name in ("Base", "Downside")})
        calendar = dict(stabilization_date="2028-01-01", holding_months=12)
        values = {key:rational(1500 if key == "C8" else 0) for key in ("C8", "C9", "C10", "C11")}
        growth = dict(window_start="2028-01-01", window_end_exclusive="2029-01-01", rent_factor=rational(1))
        return raw, groups, calendar, values, growth

    def projected(self, raw, groups, calendar, values, growth, **kwargs):
        return project_window(raw, "Base", groups, calendar, values, growth,
                              rent_basis=kwargs.get("rent_basis", "per_unit_per_month"))

    def test_known_AMI_cap_allowance_and_mixed_units_reconcile_without_expense_deduction(self):
        proof = self.projected(*self.fixture())
        studio = proof["groups"]["studio"]
        self.assertEqual(value(studio["gross_regulated_cap"]), 1200)
        self.assertEqual(value(studio["net_regulated_cap"]), 1100)
        self.assertEqual(value(studio["charged_regulated_rent"]), 1100)
        self.assertEqual(value(studio["effective_per_unit_monthly_rent"]), Q(4100, 3))
        self.assertEqual(value(proof["annual_gross_potential"]), 49_200)
        self.assertFalse(proof["owner_utility_expenses_modified"])
        self.assertFalse(proof["real_eligibility_confirmed"])
        self.assertIsNone(proof["groups"]["1BR"]["net_regulated_cap"])

    def test_market_growth_is_capped_each_year_and_not_applied_twice(self):
        raw, groups, calendar, values, growth = self.fixture()
        growth.update(window_start="2029-01-01", window_end_exclusive="2030-01-01", rent_factor=rational(Q(6,5)))
        proof = self.projected(raw, groups, calendar, values, growth)
        self.assertEqual(value(proof["groups"]["studio"]["market_rent"]), 1800)
        self.assertEqual(value(proof["groups"]["studio"]["charged_regulated_rent"]), 1100)
        self.assertEqual(value(proof["annual_gross_potential"]), 56_400)
        self.assertNotEqual(value(proof["annual_gross_potential"]), Q(49_200)*Q(6,5))

    def test_all_missing_numeric_limits_are_rejected_while_explicit_zero_is_preserved(self):
        original = self.fixture()
        for key in ("annual_AMI_income", "income_limit_fraction", "rent_income_share", "utility_allowance_monthly"):
            for blank in (None, "", " ", False):
                with self.subTest(field=key, blank=repr(blank)):
                    raw, *rest = deepcopy(original)
                    raw["scenarios"]["Base"]["windows"]["2028-01-01"]["limits"]["studio"][key]["value"] = blank
                    with self.assertRaises(ValueError): self.projected(raw, *rest)
        raw, *rest = deepcopy(original)
        limit = raw["scenarios"]["Base"]["windows"]["2028-01-01"]["limits"]["studio"]
        limit["annual_AMI_income"]["value"] = rational(0)
        limit["utility_allowance_monthly"]["value"] = rational(0)
        proof = self.projected(raw, *rest)
        self.assertEqual(value(proof["groups"]["studio"]["charged_regulated_rent"]), 0)
        self.assertEqual(value(proof["annual_gross_potential"]), 36_000)

    def test_negative_net_cap_is_pending_and_never_clipped_to_zero(self):
        raw, *rest = self.fixture()
        raw["scenarios"]["Base"]["windows"]["2028-01-01"]["limits"]["studio"]["utility_allowance_monthly"]["value"] = rational(1300)
        with self.assertRaisesRegex(ValueError, "negative_net_cap"):
            self.projected(raw, *rest)

    def test_missing_future_year_group_source_validity_or_unit_reconciliation_blocks(self):
        for fault in ("window", "group", "source", "validity", "units", "household", "leaseup", "money_unit", "currency"):
            with self.subTest(fault=fault):
                raw, *rest = self.fixture(); source = raw["scenarios"]["Base"]
                window = source["windows"]["2028-01-01"]
                if fault == "window": del source["windows"]["2029-01-01"]
                elif fault == "group": del window["limits"]["studio"]
                elif fault == "source": window["limits"]["studio"]["annual_AMI_income"]["source_ref"] = ""
                elif fault == "validity": window["valid_until_exclusive"] = "2028-12-31"
                elif fault == "units": source["allocations"]["studio"]["market_units"] = 3
                elif fault == "household": window["limits"]["studio"]["imputed_household_size"] = 0
                elif fault == "leaseup": source["leaseup_assumption_ref"] = ""
                elif fault == "money_unit": window["limits"]["studio"]["annual_AMI_income"]["unit"] = "USD_per_month"
                else: raw["currency"] = "EUR"
                with self.assertRaises(ValueError): self.projected(raw, *rest)

    def test_lower_documented_market_rent_wins_and_unknown_PER_SF_conversion_is_rejected(self):
        raw, groups, calendar, values, growth = self.fixture()
        values["C8"] = rational(900)
        proof = self.projected(raw, groups, calendar, values, growth)
        self.assertEqual(value(proof["groups"]["studio"]["charged_regulated_rent"]), 900)
        self.assertEqual(value(proof["annual_gross_potential"]), 32_400)
        with self.assertRaisesRegex(ValueError, "per_unit_basis"):
            self.projected(raw, groups, calendar, values, growth, rent_basis="per_rentable_sf_per_month")

    def test_source_size_extension_is_scoped_to_new_schema_and_bounded(self):
        raw = encoded(dict(schema=SCHEMA, padding="x"*100_000))
        self.assertEqual(read_case_source(raw)["schema"], SCHEMA)
        with self.assertRaises(ValueError): read_case_source(encoded(dict(schema="miniuw.synthetic-native-rental-inputs.v33", padding="x"*100_000)))
        with self.assertRaises(ValueError): read_case_source(encoded(dict(schema=SCHEMA, padding="x"*MAX_REGULATED_RENT_BYTES)))


class RegulatedRentIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(prefix="miniuw-d269-integration-"); cls.addClassCleanup(cls.temp.cleanup)
        cls.spec, cls.sources, cls.result, cls.saved = run(Path(cls.temp.name) / "regulated")

    def test_full_chain_verifies_130_facts_and_all_four_cash_routes_against_independent_sources(self):
        self.assertEqual(self.result["critical_evidence_review"]["counts"], dict(VERIFIED_GREEN=130, FALSE_GREEN=0, PENDING=0))
        checked = independently_verify(self.spec, self.sources, self.result)
        self.assertEqual({name:len(data["verified_routes"]) for name,data in checked.items()}, dict(Base=2, Downside=2))
        self.assertEqual(self.result["decision"], "PENDING")
        self.assertFalse(self.result["real_decisions_enabled"])

    def test_false_green_in_one_AMI_group_blocks_only_its_scenario_cash(self):
        from worksheet_critical_evidence_D220 import withhold_unverified_cash
        from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, WORKBOOK_FILE, DOWNSIDE_WORKBOOK_FILE, PLAN_FILE, EVIDENCE_FILE
        reference = json.loads(self.sources["independent_reference_raw"])
        first = next(iter(reference["regulated_rents"]["Base"]["windows"].values()))
        first["groups"]["studio"]["net_regulated_cap"] = rational(0)
        documents = {name:self.saved[name] for name in ("case.json", CURRENT_REVISION_FILE, WORKBOOK_FILE, DOWNSIDE_WORKBOOK_FILE, PLAN_FILE, EVIDENCE_FILE)}
        views, audit = withhold_unverified_cash(deepcopy(self.result["scenarios"]), self.result["local_review"],
            self.result["revision_review"], self.result["case_sha256"], encoded(reference), documents)
        self.assertEqual(audit["affected_scenarios"], ["Base"])
        self.assertIsNone(views["Base"]["cash_per_usd_10"])
        self.assertIsNotNone(views["Downside"]["cash_per_usd_10"])
        self.assertGreater(audit["counts"]["FALSE_GREEN"], 0)

    def test_omitting_forward_cap_from_inventory_cannot_create_a_green(self):
        from worksheet_variant_evidence_D268 import reference_issues
        ref = json.loads(self.sources["independent_reference_raw"])
        last = max(ref["regulated_rents"]["Downside"]["windows"])
        del ref["regulated_rents"]["Downside"]["windows"][last]
        self.assertTrue(reference_issues(encoded(ref), json.loads(self.saved["case.json"])))

