"""Exercise the documented Base, Downside and Policy 17 verdicts with fictional observations."""

from fractions import Fraction
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from xml.etree import ElementTree
from zipfile import ZipFile
import json

from miniuw_foundation.debt_service import rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.lorena_screening import CASE_SCHEMA, RLV, encode, prepare_configuration, rehearse
from miniuw_foundation.threshold_rehearsal import NS


ROOT = Path(__file__).resolve().parents[1]
RECIPE = (ROOT / "templates/lorena-screening-D230.json").read_bytes()
SOURCE = (ROOT / json.loads(RECIPE)["source"]["path"]).read_bytes()


def fixture(config_raw, label):
    config = json.loads(config_raw)
    values = {}
    for scenario in ("Base", "Downside"):
        values[scenario] = {
            spec["metric_id"]: dict(unit=spec["unit"], basis=spec["basis"], value=rule["threshold"])
            for spec in config["metrics"]
            if (rule := spec["pass_base" if scenario == "Base" else "pass_downside"]) is not None
        }
    return dict(schema=CASE_SCHEMA, deal_id=f"SYNTHETIC-D230-{label}", criteria_revision=config["revision"],
                criteria_sha256=sha256(config_raw).hexdigest(),
                scope={scenario: dict(refinance_in_scope=True, equity_remains_after_refi=True) for scenario in values},
                irr_in_scope=True, material_gaps=[], metric_values=values)


def set_value(case, scenario, metric, amount):
    case["metric_values"][scenario][metric]["value"] = rational(Fraction(amount))


class LorenaScreeningTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = prepare_configuration(RECIPE, SOURCE)
        cls.raw = encode(cls.config)

    def verdict(self, case, expected, reason):
        result = rehearse(RECIPE, SOURCE, self.raw, encode(case))
        self.assertEqual((result["simulation_result"], result["reason"]), (expected, reason))
        self.assertEqual(result["decision"], "PENDING")
        self.assertFalse(result["criteria_adopted"])
        self.assertFalse(result["deployment_enabled"])
        return result

    def test_versioned_source_preserves_exact_units_and_missing_conditions(self):
        metrics = {m["metric_id"]: m for m in self.config["metrics"]}
        fields = ("pass_base", "pass_downside", "fail_base")
        self.assertEqual(sum(m[field] is not None for m in metrics.values() for field in fields), 29)
        self.assertTrue(all(m["fail_downside"] is None for m in metrics.values()))
        self.assertIsNone(metrics[RLV]["pass_downside"])
        self.assertEqual(metrics["spread"]["fail_base"]["threshold"], rational(Fraction(0)))
        self.assertEqual(metrics["spread"]["pass_base"]["threshold"], rational(Fraction(100)))
        self.assertEqual(metrics["spread"]["unit"], "bps")
        self.assertEqual(metrics["YoC"]["pass_base"]["operator"], ">=")
        self.assertEqual(metrics["equity_TDC"]["fail_base"]["operator"], ">")
        self.assertEqual(metrics["equity_cash_in"]["unit"], "fraction")
        with ZipFile(BytesIO(SOURCE)) as archive:
            document = ElementTree.fromstring(archive.read("word/document.xml"))
        source = self.config["source"]
        for key, prefix in (("verdict_policy_locator", "17. Verdict Rules Policy"),
                            ("scenario_policy_locator", "33. Scenario Override and Application Policy")):
            index = int(source[key].rsplit("[", 1)[1][:-1])
            paragraph = document.findall(".//w:p", NS)[index]
            self.assertTrue("".join(node.text or "" for node in paragraph.findall(".//w:t", NS)).startswith(prefix))
        date = document.findall(".//w:tbl", NS)[0].findall("w:tr/w:tc", NS)[3]
        self.assertEqual("".join(node.text or "" for node in date.findall(".//w:t", NS)), source["date_literal"])

    def test_all_applicable_passes_at_inclusive_boundaries(self):
        result = self.verdict(fixture(self.raw, "pass"), "PASS", "ALL_APPLICABLE_BASE_AND_DOWNSIDE_PASS")
        self.assertEqual(sum(row["state"] == "PASS_CONDITION" for row in result["comparisons"]), 19)
        self.assertEqual([row["reason"] for row in result["comparisons"] if row["state"] == "N/A"],
                         ["base_only_rlv_policy_13"])

    def test_downside_missing_its_pass_target_is_hold_economics(self):
        case = fixture(self.raw, "downside-hold")
        set_value(case, "Downside", "spread", -100)
        result = self.verdict(case, "HOLD", "ECONOMICS_NOT_SUPPORTED")
        self.assertEqual([r["state"] for r in result["comparisons"]
                          if (r["scenario"], r["metric_id"]) == ("Downside", "spread")], ["PASS_NOT_MET"])

    def test_base_fail_is_strict_on_both_sides_and_rlv_uses_premium(self):
        for metric, boundary, strict_fail in (("YoC", "0.0525", "0.0524"), ("equity_TDC", "0.45", "0.4501"),
                                              (RLV, "0.15", "0.1501"), ("spread", "0", "-0.01")):
            with self.subTest(metric=metric):
                case = fixture(self.raw, "base-threshold")
                set_value(case, "Base", metric, boundary)
                self.verdict(case, "HOLD", "ECONOMICS_NOT_SUPPORTED")
                set_value(case, "Base", metric, strict_fail)
                self.verdict(case, "FAIL", "BASE_FAIL_THRESHOLD_BREACHED")

    def test_missing_document_or_observation_is_hold_dd(self):
        case = fixture(self.raw, "hold-dd")
        case["material_gaps"].append("SYNTHETIC-missing-cost-evidence")
        del case["metric_values"]["Downside"]["YoC"]
        result = self.verdict(case, "HOLD", "MORE_DD_REQUIRED")
        self.assertEqual(result["material_gaps"], ["Downside:YoC:metric_value_missing", "SYNTHETIC-missing-cost-evidence"])

    def test_verified_fail_with_independent_material_gap_remains_pending(self):
        case = fixture(self.raw, "mixed")
        set_value(case, "Base", "YoC", "0.05")
        del case["metric_values"]["Downside"]["spread"]
        result = self.verdict(case, "PENDING", "material_gaps_with_verified_base_fail_precedence_unconfirmed")
        self.assertTrue(any(r["state"] == "FAIL_CONDITION" for r in result["comparisons"]))

    def test_unit_or_basis_mismatch_cannot_trigger_pass_or_fail(self):
        case = fixture(self.raw, "cash-in-units")
        case["metric_values"]["Base"]["equity_cash_in"]["unit"] = "USD"
        case["metric_values"]["Downside"]["post_refi_CoC"]["basis"] = "unannualized_period_coc"
        result = self.verdict(case, "HOLD", "MORE_DD_REQUIRED")
        self.assertEqual(len(result["material_gaps"]), 2)

    def test_explicit_scope_handles_no_refinance_and_irrelevant_irr(self):
        case = fixture(self.raw, "no-refi")
        case["irr_in_scope"] = False
        case["scope"]["Downside"] = dict(refinance_in_scope=False, equity_remains_after_refi=None)
        result = self.verdict(case, "PASS", "ALL_APPLICABLE_BASE_AND_DOWNSIDE_PASS")
        self.assertEqual(sum(r["state"] == "N/A" for r in result["comparisons"]), 8)
        case["scope"]["Downside"]["refinance_in_scope"] = None
        self.verdict(case, "HOLD", "MORE_DD_REQUIRED")

    def test_irr_enclosure_crossing_inclusive_boundary_requires_due_diligence(self):
        case = fixture(self.raw, "irr-enclosure")
        case["metric_values"]["Base"]["IRR"]["value"] = dict(
            lower=rational(Fraction("0.149")), upper=rational(Fraction("0.151")), lower_closed=True, upper_closed=True)
        result = self.verdict(case, "HOLD", "MORE_DD_REQUIRED")
        self.assertEqual(result["material_gaps"], ["Base:IRR:irr_interval_crosses_criterion"])

    def test_changed_docx_criteria_revision_or_hash_blocks(self):
        with self.assertRaises(ValidationError):
            prepare_configuration(RECIPE, SOURCE + b"changed")
        case = fixture(self.raw, "mismatched-revision")
        with self.assertRaises(ValidationError):
            rehearse(RECIPE, SOURCE, self.raw + b" ", encode(case))
        for field in ("criteria_revision", "criteria_sha256"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                rehearse(RECIPE, SOURCE, self.raw, encode(case | {field: "stale"}))

    def test_non_synthetic_identity_and_upside_inputs_are_rejected(self):
        case = fixture(self.raw, "out-of-scope")
        with self.assertRaises(ValidationError):
            rehearse(RECIPE, SOURCE, self.raw, encode(case | {"deal_id": "1101"}))
        case["metric_values"]["Upside"] = case["metric_values"]["Base"]
        with self.assertRaises(ValidationError):
            rehearse(RECIPE, SOURCE, self.raw, encode(case))
