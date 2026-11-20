"""Explicit scenario contracts, source completeness and cross-family transformations."""
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_worksheet_scenario_program_D268 import (settings, drivers, make_packet, sources_for,
    reference_taxes, independently_verify)
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import encoded, build_results, CURRENT_REVISION_FILE, PLAN_FILE, EVIDENCE_FILE, WORKBOOK_FILE, DOWNSIDE_WORKBOOK_FILE
from worksheet_intake_D198 import prepare, register
from worksheet_scenario_program_D268 import (DRIVERS, driver_terms, transformed, check_variant,
    leaf_changes, packet_hash, cash_deltas)
from worksheet_variant_evidence_D268 import reference_issues, inputs_digest, fiscal_cash
from worksheet_horizon_fiscal_D267 import horizon_calendar
from check_worksheet_horizon_fiscal_D267 import source_cells, value


class ScenarioCashComparisonTests(TestCase):
    def test_gross_deltas_keep_missing_or_incompatible_routes_pending(self):
        def cash(contributions, receipts, unrec, basis=100):
            return dict(basis_amount=rational(basis), reference_amount=rational(10),
                total_contributions=rational(contributions), total_distributions=rational(receipts),
                unrecovered_after_sale=rational(unrec))
        def record(value):
            return dict(cash={name: {route: dict(cash_per_usd_10=deepcopy(value))
                for route in ("with_refi", "without_refi")} for name in ("Base", "Downside")})
        records = dict(baseline=record(cash(12, 15, 0)), trial=record(cash(14, 11, 3)))
        deltas = cash_deltas(records)
        self.assertEqual(deltas["trial"]["Base"]["with_refi"]["deltas"],
                         dict(total_contributions=rational(2), total_distributions=rational(-4), unrecovered_after_sale=rational(3)))
        records["trial"]["cash"]["Downside"]["with_refi"]["cash_per_usd_10"] = None
        records["trial"]["cash"]["Base"]["without_refi"]["cash_per_usd_10"]["basis_amount"] = rational(200)
        deltas = cash_deltas(records)
        self.assertIsNone(deltas["trial"]["Downside"]["with_refi"]["deltas"])
        self.assertEqual(deltas["trial"]["Base"]["without_refi"]["state"], "PENDING")


class ScenarioFixture(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(prefix="miniuw-d268-contract-")
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        cls.base = settings()
        seed = sources_for(cls.base, directory / "seed")
        cls.base, cls.sources = make_packet(cls.base, seed, "baseline", [], drivers(), directory / "baseline")
        raw, current = prepare(cls.base, register(cls.sources, "SYNTHETIC-D268-unit-contract"))
        cls.bound_case = json.loads(raw)

    def calendar(self, name):
        inputs = self.base["rent_inputs"]; _, cell = source_cells(self.sources, name)
        review = dict(workbook_sha256="a"*64, rows=[dict(value_cell="Inputs!"+key,
            state="CONFIRMED_SYNTHETIC", value=rational(cell(key))) for key in ("C46", "C47")])
        return horizon_calendar(inputs["project_calendar"], name, review,
            inputs["development"]["scenarios"][name]["purchase_date"],
            inputs["supplemental_scope"][name]["sale_date"], inputs["holding_horizon"])


class ScenarioProgramContractTests(ScenarioFixture):
    def test_all_fifteen_require_explicit_values_and_preserve_zero(self):
        for key, original in drivers().items():
            for name in ("Base", "Downside"):
                for missing in (None, "", " "):
                    with self.subTest(key=key, scenario=name, missing=repr(missing)):
                        record = deepcopy(original); record["values"][name] = missing
                        with self.assertRaises(ValueError): driver_terms(record, key)
                record = deepcopy(original); record["values"][name] = rational(0)
                self.assertEqual(driver_terms(record, key)[name], 0)
        self.assertEqual(len(DRIVERS), 15)

    def test_units_and_exceptions_do_not_supply_hidden_shocks(self):
        self.assertEqual(transformed(Q(100), Q(1, 10), "22"), 110)
        self.assertEqual(transformed(Q(5, 100), Q(100), "26"), Q(6, 100))
        self.assertEqual(transformed(Q(65, 100), Q(-1), "30"), Q(64, 100))
        self.assertEqual(transformed(Q(6), Q(3), "23"), 9)
        record = dict(applicability="excluded", source_ref="SYNTHETIC-D268-exclusion", reason="Not applicable in test")
        self.assertIsNone(driver_terms(record, "18"))
        record["reason"] = ""
        with self.assertRaisesRegex(ValueError, "exception_reason"): driver_terms(record, "18")
        wrong = deepcopy(drivers()["26"]); wrong["unit"] = "fraction"
        with self.assertRaisesRegex(ValueError, "driver_contract"): driver_terms(wrong, "26")

    def test_independent_reference_cannot_drop_bank_market_plan_or_fiscal_roles(self):
        raw = self.sources["independent_reference_raw"]
        self.assertEqual(reference_issues(raw, self.bound_case), [])
        for path in (("bank", "Downside", "permanent", "terms", "minimum_dscr"),
                     ("bank", "Base", "construction"), ("market", "Base", "rent", "cells", "C8"),
                     ("plan", "B05"), ("holding_fiscal", "Downside")):
            with self.subTest(path=path):
                ref = json.loads(raw); part = ref
                for key in path[:-1]: part = part[key]
                del part[path[-1]]
                self.assertTrue(reference_issues(encoded(ref), self.bound_case))
        for missing in (None, b"", b"{}", b"{"):
            self.assertTrue(reference_issues(missing, self.bound_case))

    def test_reference_is_bound_to_current_input_and_stress_contract(self):
        changed = deepcopy(self.bound_case)
        changed["rent_inputs"]["stabilized_tax_stress"]["scenarios"]["Base"]["relative_change"] = rational(Q(1, 20))
        self.assertTrue(reference_issues(self.sources["independent_reference_raw"], changed))
        self.assertEqual(inputs_digest(self.bound_case["rent_inputs"]), inputs_digest(self.base["rent_inputs"]))

    def test_tax_stress_is_after_assessment_once_and_preopening_is_unchanged(self):
        for name in ("Base", "Downside"):
            inputs = deepcopy(self.base["rent_inputs"])
            inputs["stabilized_tax_stress"]["scenarios"][name]["relative_change"] = rational(Q(1, 20))
            spec = deepcopy(self.base); spec["rent_inputs"] = inputs
            taxes, _, proof = fiscal_cash(inputs["florida_property_tax"], inputs["holding_tax_cash"],
                inputs["stabilized_tax_stress"], name, self.calendar(name))
            self.assertEqual(taxes, reference_taxes(spec, self.sources, name))
            baseline = reference_taxes(self.base, self.sources, name)
            for key in taxes:
                factor = Q(1) if key.startswith("preopening-") else Q(21, 20)
                self.assertEqual(value(taxes[key]["total"]), value(baseline[key]["total"]) * factor)
            self.assertEqual(proof["preopening_tax_total"], rational(Q("16631.25") if name == "Base" else Q("36131.25")))
        missing = deepcopy(inputs["stabilized_tax_stress"])
        missing["scenarios"]["Downside"]["relative_change"] = None
        with self.assertRaisesRegex(ValueError, "explicit_fraction"):
            fiscal_cash(inputs["florida_property_tax"], inputs["holding_tax_cash"], missing, "Downside", self.calendar("Downside"))

    def test_joint_changes_are_checked_against_parent_not_against_previous_variant(self):
        records = drivers()
        parent = {key: raw for key, raw in self.sources.items() if key != "independent_reference_raw"}
        spec, packet = make_packet(self.base, parent, "joint", list(DRIVERS), records, Path(self.temp.name) / "joint")
        declaration = dict(packet_sha256=packet_hash(spec, packet), settings_changes=leaf_changes(self.base, spec))
        changed = check_variant(self.base, self.sources, spec, packet, declaration, records, list(DRIVERS))
        self.assertEqual(len(changed["Base"]), 21)
        for name in ("Base", "Downside"):
            self.assertEqual(value(changed[name]["C46"]["after"])-value(changed[name]["C46"]["before"]), 3)
            self.assertEqual(value(changed[name]["C71"]["after"])-value(changed[name]["C71"]["before"]), Q(-1, 100))
        altered = deepcopy(spec)
        altered["rent_inputs"]["holding_horizon"]["scenarios"]["Base"]["initial_equity"]["value"] = rational(1)
        declared = dict(packet_sha256=packet_hash(altered, packet), settings_changes=leaf_changes(self.base, altered))
        with self.assertRaisesRegex(ValueError, "initial_basis"):
            check_variant(self.base, self.sources, altered, packet, declared, records, list(DRIVERS))
        altered = deepcopy(spec)
        altered["rent_inputs"]["project_calendar"]["scenarios"]["Base"]["lease_up_shortfall_per_month"] = rational(0)
        declared = dict(packet_sha256=packet_hash(altered, packet), settings_changes=leaf_changes(self.base, altered))
        with self.assertRaisesRegex(ValueError, "unrelated_support"):
            check_variant(self.base, self.sources, altered, packet, declared, records, list(DRIVERS))


class ScenarioProgramEvidenceTests(ScenarioFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.raw, cls.current = prepare(cls.base, register(cls.sources, "SYNTHETIC-D268-evidence-unit"))
        cls.result, cls.pdf = build_results(cls.raw, current_revision_raw=cls.current, **cls.sources)
        cls.documents = {"case.json": cls.raw, CURRENT_REVISION_FILE: cls.current,
            WORKBOOK_FILE: cls.sources["workbook_raw"], DOWNSIDE_WORKBOOK_FILE: cls.sources["downside_workbook_raw"],
            PLAN_FILE: cls.sources["plan_raw"], EVIDENCE_FILE: cls.sources["evidence_raw"]}

    def guarded(self, reference, *, result=None):
        from worksheet_critical_evidence_D220 import withhold_unverified_cash
        actual = self.result if result is None else result
        return withhold_unverified_cash(deepcopy(actual["scenarios"]), actual["local_review"],
            actual["revision_review"], actual["case_sha256"], reference, self.documents)

    def test_full_baseline_has_independent_financial_cotejo_and_116_verified_fields(self):
        self.assertEqual(self.result["critical_evidence_review"]["counts"],
                         dict(VERIFIED_GREEN=116, FALSE_GREEN=0, PENDING=0))
        self.assertEqual(set(independently_verify(self.base, self.sources, self.result)), {"Base", "Downside"})
        self.assertEqual(self.result["decision"], "PENDING")
        self.assertFalse(self.result["real_decisions_enabled"])

    def test_missing_malformed_or_truncated_inventory_withholds_both_routes(self):
        ref = json.loads(self.sources["independent_reference_raw"])
        del ref["bank"]["Downside"]["permanent"]["terms"]["minimum_dscr"]
        for raw in (None, b"{", encoded(ref)):
            with self.subTest(raw="missing" if raw is None else "malformed/truncated"):
                views, report = self.guarded(raw)
                self.assertEqual(set(report["affected_scenarios"]), {"Base", "Downside"})
                for view in views.values():
                    self.assertIsNone(view["cash_per_usd_10"])
                    self.assertNotIn("horizon_without_refinance", view)

    def test_omitted_quarter_or_fiscal_detail_error_blocks_affected_cash(self):
        for remove in (True, False):
            ref = json.loads(self.sources["independent_reference_raw"])
            window = ref["holding_fiscal"]["Downside"]["windows"]
            if remove: del window["operation-quarter-1"]
            else: window["operation-quarter-1"]["non_school_tax"] = rational(0)
            views, report = self.guarded(encoded(ref))
            self.assertEqual(report["affected_scenarios"], ["Downside"])
            self.assertIsNone(views["Downside"]["cash_per_usd_10"])
            self.assertIsNotNone(views["Base"]["cash_per_usd_10"])
            self.assertGreater(report["counts"]["FALSE_GREEN"], 0)

    def test_excess_requested_loan_is_not_resized_and_does_not_create_refi_cash(self):
        records = drivers()
        records["30"]["values"] = dict(Base=rational(0), Downside=rational(-60))
        parent = {key: raw for key, raw in self.sources.items() if key != "independent_reference_raw"}
        spec, packet = make_packet(self.base, parent, "capacity-blocked", ["30"], records,
                                   Path(self.temp.name) / "capacity-blocked")
        raw, current = prepare(spec, register(packet, "SYNTHETIC-D268-explicit-capacity-block"))
        result, _ = build_results(raw, current_revision_raw=current, **packet)
        view = result["scenarios"]["Downside"]
        self.assertIsNone(view["cash_per_usd_10"])
        self.assertTrue(view["blockers"])
        self.assertEqual(result["decision"], "PENDING")
        self.assertEqual(spec["rent_inputs"]["requested_principal"], self.base["rent_inputs"]["requested_principal"])
        self.assertIsNotNone(view.get("horizon_without_refinance", {}).get("cash_per_usd_10"))
        self.assertEqual(view["permanent_loan"]["requested_principal"], spec["rent_inputs"]["requested_principal"])
        from worksheet_variant_evidence_D268 import capacity_only_delivery
        case = json.loads(raw)
        self.assertTrue(capacity_only_delivery(case, result, "Downside"))
        for fault in ("unverified", "missing_alternative", "extra_blocker"):
            changed = deepcopy(result)
            if fault == "unverified": changed["critical_evidence_review"]["status"] = "PENDING"
            elif fault == "missing_alternative": changed["scenarios"]["Downside"]["horizon_without_refinance"]["cash_per_usd_10"] = None
            else: changed["scenarios"]["Downside"]["blockers"].append("source_missing")
            self.assertFalse(capacity_only_delivery(case, changed, "Downside"), fault)


