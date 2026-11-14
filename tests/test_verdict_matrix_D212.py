"""D212 replays the verdict matrix with invented inputs and gross cash by date."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_worksheet_return_metrics_D167 import verify_irr
from check_worksheet_verdict_options_D211 import BAND, PASS_MISS, preview
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.investor_returns import CATEGORIES, produce_investor_returns
from miniuw_foundation.irr_interval_output import condition_relation
from miniuw_worksheet_v1 import encoded
from worksheet_criteria_intake_D194 import PASS_ONLY_POLICY
from worksheet_definition_screening_D193 import RLV
from worksheet_integrated_screening_D181 import compare_pass_only
from worksheet_intake_case_D117 import initial_equity_cash
from worksheet_performance_policy_D184 import price_screen

FIXTURE = Path(__file__).with_name("synthetic_verdict_matrix_D212.json")
POLICIES = ("current_rule", "base_fail_first")
OBSERVATIONS = ("equity_recovered", "equity_cash_in", "breakeven_occupancy", "post_refi_CoC")
CASH_TOTALS = ("total_contributions", "total_distributions", "unrecovered_after_sale")

BASE_RULES = {
    "spread": (">=", -125, "<", -135),
    "equity_recovered": (">=", ".10", "<", ".07"),
    "equity_cash_in": ("<=", ".05", ">", ".10"),
    "breakeven_occupancy": ("<=", ".72", ">", ".82"),
    "post_refi_CoC": (">=", ".04", "<", ".03"),
}
DOWNSIDE_RULES = {
    "spread": (">=", -325),
    "equity_recovered": (">=", ".06"),
    "equity_cash_in": ("<=", ".08"),
    "breakeven_occupancy": ("<=", ".82"),
    "post_refi_CoC": (">=", ".015"),
}


def investor_source(identifier, name, dates, events):
    rows = []
    for position, category, value in events:
        kind, = (kind for kind, categories in CATEGORIES.items() if category in categories)
        event_id = f"{position}-{category}"
        rows.append(dict(event_id=event_id, date=dates[position], kind=kind, category=category,
                         amount=rational(value), currency="USD", source_ref=f"{identifier}:{name}:{event_id}"))
    return dict(
        schema="miniuw.synthetic-investor-returns.v1",
        context=dict(deal_id=identifier, scenario_id=f"SYNTHETIC-{name}", run_id=f"{identifier}-{name}",
                     definition_set_revision="SYNTHETIC-D212-cash-v1"),
        currency="USD", equity_level="aggregate_project_equity", event_inventory_declared_complete=True,
        grid=dict(spacing="calendar_months_same_day", step_months=3, dates=dates, timing_basis_ref=identifier),
        events=rows, normalization=dict(reference_amount=rational(10),
                                        contribution_event_ids=["0-initial_capital"], basis_ref=identifier),
        capital_snapshots=[], annual_cash_bases=[],
        irr_parameters=dict(rate_domain="r_gt_minus_one_positive_discount_factor",
                            max_periodic_rate_interval_width=rational(Fraction(1, 100_000_000)),
                            split_budget=128, operation_budget=50_000, periods_per_year=4),
    )


def point(value):
    return dict(lower=value, upper=value, lower_closed=True, upper_closed=True)


def base_comparison(context, value, enclosure, rule):
    if value is None and enclosure is None:
        return dict(context, value=None, state="PENDING", blockers=["metric_value_missing"])
    passing, pass_value, failing, fail_value = rule
    bounds = enclosure if enclosure is not None else point(value)
    relations = (condition_relation(bounds, rational(Fraction(pass_value)), passing),
                 condition_relation(bounds, rational(Fraction(fail_value)), failing))
    state = {("every", "none"): "PASS_CONDITION", ("none", "every"): "FAIL_CONDITION",
             ("none", "none"): "BAND"}[relations]
    return dict(context, value=value, state=state, blockers=[])


def screen(identifier, metrics, intervals, rules, changes):
    base_rules = rules["Base"].copy()
    downside_rules = rules["Downside"].copy()
    values = deepcopy(metrics)
    if "band" in changes:
        base_rules["post_refi_CoC"] = (">=", ".06", "<", ".03")
    if "missing" in changes:
        values["Base"][RLV] = None
    if "base_fail" in changes:
        base_rules["spread"] = (">=", -100, "<", -115)
    if "downside_miss" in changes:
        downside_rules["spread"] = (">=", -300)
    if "no_downside_spread_limit" in changes:
        downside_rules["spread"] = (">=", None)
    if "no_downside_rlv_limit" in changes:
        downside_rules[RLV] = ("<=", None)
    if "tight_downside_rlv_limit" in changes:
        downside_rules[RLV] = ("<=", ".65")

    rows = []
    for name, scenario in values.items():
        for metric, value in scenario.items():
            unit = {"spread": "bps", "equity_multiple": "multiple", RLV: "multiple"}.get(metric, "fraction")
            context = dict(scenario_id=name, metric_id=metric, unit=unit, currency=None, quantity_kind="scalar",
                           period_ref=intervals[name]["period_ref"], applicability="applicable",
                           definition_ref=f"{identifier}-{metric}")
            enclosure = intervals[name]["annual_enclosure"] if metric == "IRR" else None
            if name == "Base":
                rows.append(base_comparison(context, value, enclosure, base_rules[metric]))
                continue
            operator, threshold = downside_rules[metric]
            condition = dict(operator=operator, threshold=None if threshold is None else rational(Fraction(threshold)))
            record = dict(context, value=value)
            state, _, blockers = compare_pass_only(record, dict(context, pass_condition=condition), enclosure)
            rows.append(dict(record, state=state, blockers=blockers,
                             pass_only_policy=dict(policy=PASS_ONLY_POLICY, source_ref=identifier)))
    blockers = {f"{r['scenario_id']}:{r['metric_id']}:{issue}" for r in rows for issue in r["blockers"]}
    if any(r["state"] == "BAND" for r in rows):
        blockers.add(BAND)
    return dict(comparisons=rows, simulation_blockers=sorted(blockers))


class SyntheticVerdictMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_bytes())
        cls.identifier = cls.fixture["case_id"]
        cls.dates = cls.fixture["dates"]
        cls.sources = {name: investor_source(cls.identifier, name, cls.dates, scenario["events"])
                       for name, scenario in cls.fixture["scenarios"].items()}

    def reproduce_cash(self, name):
        return produce_investor_returns(encoded(self.sources[name])).payload

    def test_consolidated_verdicts_keep_the_usd10_cash(self):
        cash, intervals, measures = {}, {}, {}
        rules = {"Base": BASE_RULES.copy(), "Downside": DOWNSIDE_RULES.copy()}
        land = self.fixture["land"]
        quarterly = (Fraction("-.05"), Fraction("-.07"))
        tdc = Fraction(land["tdc"])
        debt = Fraction(land["debt"])
        asking = Fraction(land["price"])
        for name, scenario in self.fixture["scenarios"].items():
            with self.subTest(source=name):
                story = self.reproduce_cash(name)
                self.assertEqual(story["cash_blockers"], [])
                self.assertEqual(story["decision"], "PENDING")
                self.assertFalse(story["production_authorized"])
                cash[name] = initial_equity_cash(story)
                self.assertEqual(tuple(amount(cash[name][field]) for field in CASH_TOTALS),
                                 tuple(map(Fraction, scenario["expected_cash_per_usd_10"])))
                initial = cash[name]["events"][0]
                self.assertEqual((initial["date"], initial["category"], amount(initial["amount"])),
                                 (self.dates[0], "initial_capital", 10))
                intervals[name] = verify_irr(cash[name], self.dates)
                self.assertEqual(intervals[name]["state"], "checked_synthetic")
                yoc_pass, yoc_fail, em_pass, em_fail = map(Fraction, scenario["land_bands"])
                included = dict(yield_or_spread=(">=", yoc_pass, "<", yoc_fail),
                                annual_irr=(">=", (1 + quarterly[0])**4 - 1, "<", (1 + quarterly[1])**4 - 1),
                                equity_multiple=(">=", em_pass, "<", em_fail),
                                equity_to_tdc=("<=", Fraction(".78"), ">", Fraction(".85")))
                land_input = dict(price=asking, asking=asking, closing_rate=Fraction(land["closing_rate"]),
                                  tdc=tdc, applied_equity=tdc-debt, debt=debt,
                                  contributions=amount(story["gross_contributions"]),
                                  distributions=amount(story["gross_distributions"]),
                                  net_flows=[amount(row["net"]) for row in story["dated_net_flows"]],
                                  cap=None, cap_noi_basis=None, noi_uw=Fraction(scenario["noi_uw"]),
                                  quarterly_irr_thresholds=quarterly)
                rlv = price_screen(land_input, included, land["grid"], require_both_neighbors=True)
                self.assertEqual(rlv["state"], "calculated_synthetic")
                self.assertEqual([rlv["pass_price"], rlv["before_fail"]], scenario["expected_price_limits"])
                self.assertEqual(rlv["pass_boundary"]["above"]["state"], "PENDING")
                self.assertEqual(rlv["before_fail_boundary"]["above"]["state"], "FAIL")
                yoc = land_input["noi_uw"] / tdc
                measures[name] = dict(zip(OBSERVATIONS, map(lambda x: rational(Fraction(x)), scenario["observed"]),
                                          strict=True))
                measures[name].update(YoC=rational(yoc), spread=rational((yoc - Fraction(".10")) * 10_000),
                                      IRR=None, equity_multiple=story["equity_multiple"],
                                      equity_TDC=rational((tdc-debt)/tdc))
                measures[name][RLV] = rational(rlv["asking_over_pass_price"])
                for observed, criterion in (("YoC", "yield_or_spread"), ("IRR", "annual_irr"),
                                             ("equity_multiple", "equity_multiple"), ("equity_TDC", "equity_to_tdc")):
                    rules[name][observed] = included[criterion] if name == "Base" else included[criterion][:2]
                rules[name][RLV] = (("<=", 1, ">", Fraction(rlv["before_fail"], rlv["pass_price"]))
                                    if name == "Base" else ("<=", 1))

        baseline = encoded(cash)
        counts = Counter()
        outcomes = {(scope, policy): set() for scope in ("required", "excluded") for policy in POLICIES}
        for case_id, scope, confirmed, changes, expected in self.fixture["cases"]:
            with self.subTest(case=case_id):
                screening = screen(self.identifier, measures, intervals, rules, changes)
                before = encoded(screening)
                result = preview(screening, scope, applicability_confirmed=confirmed)
                self.assertEqual(encoded(screening), before)
                self.assertEqual(len(screening["comparisons"]), 20)
                self.assertEqual([result[policy] for policy in POLICIES], expected)
                for policy in POLICIES:
                    outcomes[scope, policy].add(result[policy])
                    counts[result[policy]] += 1

                if all(state == "PASS" for state in expected):
                    active_rows = [row for row in screening["comparisons"] if not (
                        confirmed and (row["scenario_id"], row["metric_id"]) == ("Downside", RLV))]
                    self.assertEqual(len(active_rows), 19 if confirmed else 20)
                    self.assertTrue(all(row["state"] == "PASS_CONDITION" for row in active_rows))
                    self.assertEqual(result["downside_rlv"], "N/A" if confirmed else "PASS_CONDITION")
                    self.assertEqual(result["unresolved_blockers"], [])
                if expected == ["PENDING", "FAIL"]:
                    metric = RLV if "tight_downside_rlv_limit" in changes else "spread"
                    self.assertEqual(result["confirmed_downside_misses"], [f"Downside:{metric}:{PASS_MISS}"])
                    self.assertEqual(result["unresolved_blockers"], [])
                if "no_downside_rlv_limit" in changes:
                    self.assertIn(f"Downside:{RLV}:pass_condition_rule_missing_or_unsupported",
                                  result["unresolved_blockers"])
                if scope == "excluded" and not confirmed:
                    self.assertIn("Downside:RLV:applicability_unconfirmed", result["unresolved_blockers"])

                rerun = {name: self.reproduce_cash(name) for name in cash}
                self.assertTrue(all(story["decision"] == "PENDING" for story in rerun.values()))
                self.assertEqual(encoded({name: initial_equity_cash(story) for name, story in rerun.items()}),
                                 baseline)

        self.assertEqual(counts, {"PASS": 4, "FAIL": 7, "PENDING": 19})
        self.assertTrue(all(states == {"PASS", "FAIL", "PENDING"} for states in outcomes.values()))
