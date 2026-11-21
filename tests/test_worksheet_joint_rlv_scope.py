"""User decision: all applicable RLV criteria include both YoC and spread."""
from copy import deepcopy
from fractions import Fraction as Q
from pathlib import Path
import json
from unittest import TestCase

from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import BASES, RLV, encode, prepare_configuration
from test_lorena_screening import RECIPE, SOURCE
from test_worksheet_lorena_screening import calculated_control
from worksheet_lorena_screening import calculated_case
from worksheet_rlv_scope_D273 import FIELD, PROFILE, RULE, scope_issues


def declaration():
    return dict(profile=PROFILE, rule=RULE, scenario_id="Base",
                metric_ids=sorted(set(BASES)-{RLV}),
                source_ref="SYNTHETIC-D273-user-confirmed-joint-scope-test")


def inputs():
    result, case = calculated_control(base_cap="0.09", base_payout=200)
    settings = case["rent_inputs"]["definition_screening"]["Base"]["rlv"]
    settings.update(binding_yields=["YoC", "spread"], grid=[70, 350, 1])
    settings[FIELD] = declaration()
    return result, case, prepare_configuration(RECIPE, SOURCE)


def run(result, case, configuration):
    observed, proof = calculated_case(result, case, configuration, encode(configuration))
    return observed, proof["Base"]["rlv_price_search"]


class JointRLVScopeTests(TestCase):
    def test_versioned_contract_and_user_decision_preserve_every_applicable_metric(self):
        raw = json.loads((Path(__file__).resolve().parents[1]/
                         "templates/synthetic-joint-rlv-scope-D273.json").read_bytes())
        self.assertEqual(raw[FIELD], declaration())
        result, case, configuration = inputs()
        self.assertFalse(configuration["criteria_adopted"])
        before = deepcopy(result)
        _, proof = run(result, case, configuration)
        self.assertEqual(result, before)
        self.assertEqual(proof[FIELD]["metric_ids"], sorted(set(BASES)-{RLV}))
        self.assertEqual(proof["state"], "bounded_synthetic")

    def test_YoC_can_bind_even_when_spread_is_loose(self):
        result, case, configuration = inputs()
        for row in configuration["metrics"]:
            if row["metric_id"] == "YoC": row["pass_base"]["threshold"] = rational(Q("0.11"))
            if row["metric_id"] == "spread": row["pass_base"]["threshold"] = rational(0)
        observed, proof = run(result, case, configuration)
        self.assertEqual((proof["price_lower"], proof["price_upper_exclusive"]), (110, 111))
        self.assertEqual(proof["binding_metrics"], ["YoC"])
        # Independent arithmetic from the literal control: NOI_uw 100, TDC
        # 1000, land 200 and C33=.02. No producer output defines this bound.
        self.assertGreaterEqual(Q(100)/(1000+(110-200)*Q("1.02")), Q("0.11"))
        self.assertLess(Q(100)/(1000+(111-200)*Q("1.02")), Q("0.11"))
        self.assertIn(RLV, observed["metric_values"]["Base"])

    def test_spread_can_bind_even_when_YoC_is_loose(self):
        result, case, configuration = inputs()
        for row in configuration["metrics"]:
            if row["metric_id"] == "YoC": row["pass_base"]["threshold"] = rational(Q("0.06"))
            if row["metric_id"] == "spread": row["pass_base"]["threshold"] = rational(200)
        _, proof = run(result, case, configuration)
        self.assertEqual((proof["price_lower"], proof["price_upper_exclusive"]), (110, 111))
        self.assertEqual(proof["binding_metrics"], ["spread"])
        for price, passes in ((110, True), (111, False)):
            spread = (Q(100)/(1000+(price-200)*Q("1.02"))-Q("0.09"))*10000
            self.assertEqual(spread >= 200, passes)

    def test_both_yields_can_bind_together_without_changing_gross_cash(self):
        result, case, configuration = inputs()
        original = deepcopy(result)
        for row in configuration["metrics"]:
            if row["metric_id"] == "YoC": row["pass_base"]["threshold"] = rational(Q("0.11"))
            if row["metric_id"] == "spread": row["pass_base"]["threshold"] = rational(200)
        _, proof = run(result, case, configuration)
        self.assertEqual(proof["binding_metrics"], ["YoC", "spread"])
        self.assertEqual(result, original)

    def test_missing_condition_never_excludes_a_criterion_or_becomes_zero(self):
        for metric in ("YoC", "spread", "equity_multiple", "equity_TDC"):
            result, case, configuration = inputs()
            next(row for row in configuration["metrics"] if row["metric_id"] == metric)["pass_base"] = None
            _, proof = run(result, case, configuration)
            self.assertEqual(proof, dict(state="PENDING", blocker="RLV: falta confirmar una condición aplicable"))

    def test_omitted_or_duplicated_scope_and_unconfirmed_source_are_blocked(self):
        result, case, configuration = inputs()
        original = case["rent_inputs"]["definition_screening"]["Base"]["rlv"]
        for fault in ("omit", "duplicate", "source", "profile", "single"):
            settings = deepcopy(original)
            if fault == "omit": settings[FIELD]["metric_ids"].remove("YoC")
            elif fault == "duplicate": settings[FIELD]["metric_ids"].append("spread")
            elif fault == "source": settings[FIELD]["source_ref"] = ""
            elif fault == "profile": settings[FIELD]["profile"] = "unknown"
            else: settings["binding_yields"] = ["spread"]
            self.assertTrue(scope_issues(settings, configuration), fault)

    def test_new_metadata_preserves_legacy_numbers_and_does_not_rewrite_older_contracts(self):
        result, case, configuration = inputs()
        new_observed, new_proof = run(result, case, configuration)
        legacy = deepcopy(case)
        settings = legacy["rent_inputs"]["definition_screening"]["Base"]["rlv"]
        settings.pop(FIELD); settings["binding_yields"] = ["spread"]
        old_observed, old_proof = run(result, legacy, configuration)
        self.assertEqual(new_observed, old_observed)
        self.assertEqual({key:value for key,value in new_proof.items() if key != FIELD}, old_proof)
        settings["binding_yields"] = ["YoC", "spread"]
        _, unchanged_legacy = run(result, legacy, configuration)
        self.assertEqual(unchanged_legacy["state"], "PENDING")

    def test_missing_or_duplicate_configuration_metric_cannot_hide_a_constraint(self):
        _, case, configuration = inputs()
        settings = case["rent_inputs"]["definition_screening"]["Base"]["rlv"]
        for fault in ("omit", "duplicate", "bad_id"):
            bad = deepcopy(configuration)
            if fault == "omit": bad["metrics"] = [r for r in bad["metrics"] if r["metric_id"] != "spread"]
            elif fault == "duplicate": bad["metrics"].append(deepcopy(bad["metrics"][0]))
            else: bad["metrics"][0]["metric_id"] = []
            self.assertTrue(scope_issues(settings, bad), fault)
