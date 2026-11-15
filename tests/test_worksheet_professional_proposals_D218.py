"""Exercise two professional proposals without changing the worksheet policy."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_lorena_criteria_D192 import change_cells
from check_worksheet_definition_screening_D193 import approvals_unchanged, detail, rows
from check_worksheet_lorena_screening_D194 import fixture
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from check_worksheet_verdict_options_D211 import BAND
from miniuw_foundation.irr_interval_output import condition_relation
from miniuw_worksheet_v1 import build_results, encoded, verify_package, write_package
from worksheet_criteria_intake_D194 import PASS_ONLY_POLICY
from worksheet_definition_screening_D193 import OCCUPANCY, RLV
from worksheet_documented_finance_D147 import review_documents
from worksheet_revision_D128 import snapshot_for_case

REVISION = "SYNTHETIC-D218-professional-proposals"
BASE_FAIL = {"E11": "<= 20 %", "F11": "> 30 %"}
DOWNSIDE_RLV = ("Downside", RLV)
UNCONFIRMED = f"Downside:{RLV}:applicability_unconfirmed"


def row_blockers(row):
    scope = f"{row['scenario_id']}:{row['metric_id']}"
    return {f"{scope}:{issue}" for issue in row["blockers"]}


def verified_failure(row):
    if row["state"] != "FAIL_CONDITION" or row["blockers"] or not all(
        row.get(ref) for ref in ("metric_locator", "criterion_locator")
    ):
        return False
    metric, criterion = row["metric_record"], row["criterion_record"]
    if not metric or not criterion or any(
        metric[field] != criterion[field]
        for field in ("definition_ref", "unit", "period_ref", "quantity_kind", "currency", "applicability")
    ):
        return False
    bounds = metric.get("annual_enclosure")
    if bounds is None:
        if metric["value"] is None:
            return False
        bounds = dict(lower=metric["value"], upper=metric["value"], lower_closed=True, upper_closed=True)
    passing, failing = (criterion[name] for name in ("pass_condition", "fail_condition"))
    return (condition_relation(bounds, passing["threshold"], passing["operator"]) == "none"
            and condition_relation(bounds, failing["threshold"], failing["operator"]) == "every")


def preview(model, *, downside_override=False, applicability_confirmed=False):
    """Compare the proposals inside the synthetic tests and retain all applicable findings."""
    screening = model["screening"]
    comparisons = rows(model)
    global_blockers = set(screening["simulation_blockers"])
    for row in comparisons.values():
        global_blockers.difference_update(row_blockers(row))
    global_blockers.discard(BAND)  # Rebuilt from active rows to preserve other bands.
    if not screening["current_criteria_confirmed"] or model["revision_review"]["state"] != "matched_synthetic_revision":
        global_blockers.add("revision_not_verified")
    active = comparisons.copy()
    rlv = comparisons[DOWNSIDE_RLV]
    pending = set()
    if downside_override and not applicability_confirmed:
        pending.add(UNCONFIRMED)
        rlv_state = "PENDING"
    elif downside_override:
        rlv_state = rlv["state"]
    else:
        del active[DOWNSIDE_RLV]
        rlv_state = "N/A"
    failures = []
    for key, row in active.items():
        pending.update(row_blockers(row))
        if row["state"] == "BAND":
            pending.add(f"{key[0]}:{key[1]}:{BAND}")
        elif row["state"] == "FAIL_CONDITION" and verified_failure(row):
            failures.append({field: row[field] for field in
                             ("scenario_id", "metric_id", "metric_locator", "criterion_locator")})
        elif row["state"] != "PASS_CONDITION" and not row["blockers"]:
            pending.add(f"{key[0]}:{key[1]}:comparison_unresolved")

    verdict = "PENDING"
    if not global_blockers:
        if failures:
            verdict = "FAIL"
        elif not pending:
            verdict = "PASS"
    return dict(simulation=verdict, pending=sorted(pending | global_blockers),
                verified_failures=failures, downside_rlv=rlv_state,
                downside_rlv_information=detail(model, *DOWNSIDE_RLV).get("calculation"),
                decision=model["decision"], policy_adopted=False)


class ProfessionalProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template, cls.edits, cls.case, _ = fixture()
        policy = dict(policy=PASS_ONLY_POLICY, source_ref="SYNTHETIC-D218-pass-only")
        cls.case["criteria_revision"] = REVISION
        cls.case["criteria_workbook"]["downside_pass_only"] = dict.fromkeys((OCCUPANCY, RLV), policy)
        cls.edits.update(B18=REVISION, H11="Sin FAIL", H13="Sin FAIL")
        case, book, revision = cls.inputs({})
        cls.revision = revision
        cls.source = dict(workbook_raw=BOOKS["Base"].read_bytes(),
                          downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                          plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())
        with TemporaryDirectory(prefix="miniuw-d218-") as temp:
            package = Path(temp) / "control"
            write_package(encoded(case), package, criteria_raw=book,
                                        current_revision_raw=revision, **cls.source)
            audit = verify_package(package, current_revision_raw=revision)
            if audit["vigencia"] != "VIGENTE" or audit["audit_bot"] != "B16":
                raise AssertionError("B16 did not reproduce the control")
            cls.control = json.loads((package / "results.json").read_bytes())
        approvals_unchanged(cls.control)
        cls.checked = review_documents(case, cls.source["plan_raw"],
                                       evidence_raw=cls.source["evidence_raw"], evidence_milestone="D162")

    @classmethod
    def inputs(cls, edits):
        case = deepcopy(cls.case)
        book = change_cells(cls.template, cls.edits | edits)
        case["criteria_workbook"]["sha256"] = sha256(book).hexdigest()
        return case, book, encoded(snapshot_for_case(case, REVISION))

    def probe(self, edits, actual, *, stale=False):
        case, book, revision = self.inputs(edits)

        def reuse(candidate, plan_raw, *, evidence_raw, evidence_milestone):
            for field in ("local_sources", "workbook_sha256", "downside_workbook_sha256"):
                self.assertEqual(candidate.get(field), self.case.get(field))
            self.assertEqual((plan_raw, evidence_raw, evidence_milestone),
                             (self.source["plan_raw"], self.source["evidence_raw"], "D162"))
            return deepcopy(self.checked)

        with patch("worksheet_documented_finance_D147.review_documents", reuse):
            model, _ = build_results(encoded(case), criteria_raw=book,
                                     current_revision_raw=self.revision if stale else revision, **self.source)
        approvals_unchanged(model)
        self.assertEqual(model["simulation_result"], actual)
        for name, scenario in self.control["scenarios"].items():
            if not stale:
                self.assertEqual(model["scenarios"][name]["cash_per_usd_10"],
                                 scenario["cash_per_usd_10"])
        return model

    def candidate(self, model, expected, **kwargs):
        original = encoded(model)
        result = preview(model, **kwargs)
        self.assertEqual(encoded(model), original)
        self.assertEqual(result["simulation"], expected)
        self.assertEqual(result["decision"], "PENDING")
        self.assertFalse(result["policy_adopted"])
        return result

    def test_default_na_keeps_the_supported_downside_price_informative(self):
        result = self.candidate(self.control, "PASS")
        self.assertEqual(result["downside_rlv"], "N/A")
        self.assertGreater(result["downside_rlv_information"]["pass_price"], 0)
        self.assertEqual(self.control["simulation_result"], "PASS")

    def test_default_na_does_not_require_a_downside_rlv_threshold(self):
        model = self.probe({"G13": ""}, "PENDING")
        self.assertEqual(self.candidate(model, "PASS")["pending"], [])
        required = self.candidate(model, "PENDING", downside_override=True, applicability_confirmed=True)
        self.assertTrue(any(item.startswith(f"Downside:{RLV}:") for item in required["pending"]))
        unsupported = self.candidate(self.control, "PENDING", downside_override=True)
        self.assertIn(UNCONFIRMED, unsupported["pending"])
        confirmed = self.candidate(self.control, "PASS", downside_override=True, applicability_confirmed=True)
        self.assertEqual(confirmed["downside_rlv"], "PASS_CONDITION")

    def test_default_na_keeps_base_rlv_and_other_required_metrics(self):
        for cell, prefix in (("E13", f"Base:{RLV}:"), ("G11", f"Downside:{OCCUPANCY}:")):
            with self.subTest(cell=cell):
                result = self.candidate(self.probe({"G13": "", cell: ""}, "PENDING"), "PENDING")
                self.assertTrue(any(item.startswith(prefix) for item in result["pending"]))

    def test_verified_fail_wins_with_unrelated_missing_criterion_or_pass_miss(self):
        for other in ({"G11": ""}, {"G11": "<= 60 %"}, {"E16": ""}, {"G13": "", "G11": ""}):
            with self.subTest(other=other):
                model = self.probe(BASE_FAIL | other, "PENDING")
                result = self.candidate(model, "FAIL")
                self.assertEqual([(r["scenario_id"], r["metric_id"]) for r in result["verified_failures"]],
                                 [("Base", OCCUPANCY)])
                self.assertTrue(result["pending"])
                self.assertFalse(any(item.startswith(f"Downside:{RLV}:") for item in result["pending"]))

    def test_no_fail_from_a_missing_threshold_on_the_failing_metric_or_a_band(self):
        for edits in (BASE_FAIL | {"F11": "", "G11": ""}, {"E11": "<= 25 %"}, {"G11": "<= 60 %"}):
            with self.subTest(edits=edits):
                result = self.candidate(self.probe(edits, "PENDING"), "PENDING")
                self.assertEqual(result["verified_failures"], [])
                self.assertTrue(result["pending"])

    def test_verified_fail_preserves_an_unrelated_missing_metric_or_band(self):
        original = self.probe(BASE_FAIL, "FAIL")
        for state, reason in (("PENDING", "metric_value_missing"), ("BAND", None)):
            with self.subTest(state=state):
                model = deepcopy(original)
                row = rows(model)["Base", "equity_multiple"]
                row["state"] = state
                if reason:
                    row["metric_record"]["value"] = None
                    row["blockers"] = [reason]
                    model["screening"]["simulation_blockers"].extend(row_blockers(row))
                else:
                    model["screening"]["simulation_blockers"].append(BAND)
                result = self.candidate(model, "FAIL")
                self.assertTrue(any(item.startswith("Base:equity_multiple:") for item in result["pending"]))

    def test_stale_revision_and_case_wide_blockers_keep_pending(self):
        stale = self.probe(BASE_FAIL | {"G11": ""}, "PENDING", stale=True)
        self.assertIn("revision_not_verified", self.candidate(stale, "PENDING")["pending"])
        model = self.probe(BASE_FAIL | {"G11": ""}, "PENDING")
        for blocker in ("B03:source_missing", "B12:criteria_revision_unconfirmed"):
            with self.subTest(blocker=blocker):
                damaged = deepcopy(model)
                damaged["screening"]["simulation_blockers"].append(blocker)
                self.assertIn(blocker, self.candidate(damaged, "PENDING")["pending"])

    def test_fail_requires_a_current_value_matching_the_threshold_and_both_locators(self):
        model = self.probe(BASE_FAIL | {"G11": ""}, "PENDING")
        for change in ("metric_locator", "criterion_locator", "value", "period"):
            with self.subTest(change=change):
                damaged = deepcopy(model)
                row = rows(damaged)["Base", OCCUPANCY]
                if change == "value":
                    row["metric_record"]["value"] = row["criterion_record"]["fail_condition"]["threshold"]
                elif change == "period":
                    row["metric_record"]["period_ref"] = "SYNTHETIC-other-period"
                else:
                    row[change] = None
                self.assertEqual(self.candidate(damaged, "PENDING")["verified_failures"], [])
