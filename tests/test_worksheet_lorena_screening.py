"""Use the Mini-UW metric producers and the same dated ledger across D230 verdicts."""

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from unittest import TestCase
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_worksheet_return_metrics_D167 import verify_irr
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.lorena_screening import RLV, encode, prepare_configuration, rehearse
from plan_return_D107 import template
from test_lorena_screening import RECIPE, SOURCE
from worksheet_definition_screening_D193 import ECONOMIC, PRICE_BASIS, SPREAD, YOC
from worksheet_formula_review_D173 import COC_BASIS, post_refi_coc
from worksheet_lorena_screening import calculated_case
from worksheet_performance_policy_D184 import AFTER_RESERVES, equilibrium, performance


DATES = [f"{year}-{month:02d}-30" for year in (2027, 2028) for month in (3, 6, 9, 12)]
DEAL = "SYNTHETIC-D231-calculated-metrics"


def investor_inputs(name, payout, operating, sale):
    raw = template("synthetic-closing-investor-slots")
    raw.update(context=dict(deal_id=DEAL, scenario_id=name, run_id=DEAL, definition_set_revision=DEAL),
               grid=dict(spacing="calendar_months_same_day", step_months=3, dates=DATES, timing_basis_ref=DEAL),
               annual_cash_bases=[], capital_snapshots=[])
    raw["irr_parameters"]["periods_per_year"] = 4
    raw["normalization"] = dict(reference_amount=rational(10), contribution_event_ids=["initial"], basis_ref=DEAL)
    rows = (
        ("initial", DATES[0], "contribution", "initial_capital", 250),
        ("construction", DATES[1], "contribution", "additional_capital", 50),
        ("refinance", DATES[3], "distribution", "net_refinance_distribution", payout),
        ("operating", DATES[7], "distribution", "operating_distribution", operating),
        ("sale", DATES[7], "distribution", "net_sale_distribution", sale),
    )
    raw["events"] = [dict(event_id=id_, date=day, kind=kind, category=category, amount=rational(value), currency="USD",
                          source_ref=f"{DEAL}/{name}/{id_}") for id_, day, kind, category, value in rows]
    return raw


def calculated_control(base_cap="0.09", downside_cap="0.08", base_payout=180):
    result = dict(scenarios={}, screening=dict(comparisons=[], metric_evidence_by_scenario={}, irr_by_scenario={}))
    screening = result["screening"]
    case = dict(rent_inputs=dict(deal_id=DEAL, definition_screening={
        "Base": {"rlv": dict(basis=PRICE_BASIS, binding_yields=["spread"], grid=[70, 350, 10], source_ref=DEAL)}}))
    for name, cap, noi, payout, sale in (("Base", base_cap, 110, base_payout, 420),
                                         ("Downside", downside_cap, 100, 150, 350)):
        reserve, service, cost = 10, 40, 1000
        operating, equity_left = noi - reserve - service, 300 - payout
        ledger = produce_investor_returns(encode(investor_inputs(name, payout, operating, sale))).payload
        cash = ledger["normalized_story"]
        cash["unrecovered_after_sale"] = rational(max(0, -_fraction(cash["net_cash_profit"])))
        calendar = dict(purchase_date=DATES[0], stabilization_date="2027-10-01", refinance_date=DATES[3],
                        sale_date=DATES[7], equity_dates=DATES, sale_source_ref=DEAL)
        view = dict(cash_per_usd_10=cash, blockers=[], project_calendar=calendar,
                    construction_refinance=dict(date=DATES[3], blockers=[], net_equity_distribution=rational(payout),
                                                projected_cash_in_required=rational(0)),
                    construction_financing=dict(cash_by_date=[dict(date=day, equity_contribution=rational(value))
                                                               for day, value in zip(DATES[:2], (250, 50))]),
                    dated_debt_service=dict(scheduled_service_due=rational(service), date=DATES[7]),
                    permanent_loan=dict(loan_run_sha256="synthetic-annual-service-control"),
                    development_costs=dict(evaluated_purchase_price=rational(200), worksheet_asking=rational(90),
                                           closing_fraction=rational(Fraction("0.02")), purchase_source_ref=DEAL,
                                           cell_sources={"C33": f"{DEAL}/C33"}))
        terms = dict(basis=COC_BASIS, currency="USD", window_start=DATES[3], window_end=DATES[7],
                     period_noi=rational(noi - reserve), noi_source_ref=DEAL, equity_still_invested=rational(equity_left),
                     equity_source_ref=DEAL, noi_basis=AFTER_RESERVES)
        view["post_refinance_coc"] = post_refi_coc({name: terms}, name, view, require_noi_basis=True)
        result["scenarios"][name] = view
        profitability = performance(Fraction(noi), reserve, cost, Fraction(cap), AFTER_RESERVES, noi, reserve, service, equity_left)
        occupancy = equilibrium(Fraction(200), -80, 0, 0, service, reserve)["economic"]
        for metric, ref, unit, value in (("YoC", YOC, "fraction", profitability["yoc"]),
                                         ("spread", SPREAD, "bps", profitability["spread_bps"]),
                                         ("breakeven_occupancy", ECONOMIC, "fraction", occupancy)):
            screening["comparisons"].append(dict(scenario_id=name, metric_id=metric,
                                                 metric_record=dict(definition_ref=ref, unit=unit,
                                                                    period_ref="2027-10-01/2028-10-01",
                                                                    value=rational(value), blockers=[])))
        screening["metric_evidence_by_scenario"][name] = dict(
            cost_basis=dict(tdc=rational(cost), applied_equity=rational(300), blockers=[], components={"loan_draw": rational(700)}),
            candidate_definitions={"YoC": {"noi_after_reserve": rational(profitability["noi_uw"]), "noi_before_reserve": rational(noi)},
                                   "spread": {"cap": rational(Fraction(cap)), "cap_noi_basis": AFTER_RESERVES}})
        screening["irr_by_scenario"][name] = verify_irr(cash, DATES)
    return result, case


def evaluate(result, case):
    config = prepare_configuration(RECIPE, SOURCE)
    raw = encode(config)
    observed, proof = calculated_case(result, case, config, raw)
    verdict = rehearse(RECIPE, SOURCE, raw, encode(observed))
    return verdict | dict(observed=observed["metric_values"], cash_proof=proof)


class CalculatedLorenaScreeningTests(TestCase):
    def test_calculated_pass_hold_fail_preserve_complete_dated_ledgers(self):
        original_cash = None
        for base_cap, downside_cap, expected, reason in (
            ("0.09", "0.08", "PASS", "ALL_APPLICABLE_BASE_AND_DOWNSIDE_PASS"),
            ("0.09", "0.0875", "HOLD", "ECONOMICS_NOT_SUPPORTED"),
            ("0.1001", "0.08", "FAIL", "BASE_FAIL_THRESHOLD_BREACHED"),
        ):
            with self.subTest(verdict=expected):
                result, case = calculated_control(base_cap, downside_cap)
                original = deepcopy(result)
                verdict = evaluate(result, case)
                self.assertEqual((verdict["simulation_result"], verdict["reason"]), (expected, reason))
                self.assertEqual(verdict["decision"], "PENDING")
                self.assertEqual(result, original)
                cash = {name: view["cash_per_usd_10"] for name, view in result["scenarios"].items()}
                if original_cash is None:
                    original_cash = cash
                self.assertEqual(cash, original_cash)
                self.assertEqual(len(verdict["observed"]["Base"]), 10)
                self.assertEqual(len(verdict["observed"]["Downside"]), 9)
                self.assertEqual(verdict["observed"]["Base"]["equity_recovered"]["value"], rational(Fraction("0.60")))
                self.assertEqual(verdict["observed"]["Base"]["equity_cash_in"]["value"], rational(0))
                self.assertEqual(verdict["observed"]["Base"]["post_refi_CoC"]["value"], rational(Fraction("0.50")))

    def test_partial_coc_and_unreconciled_funding_do_not_supply_a_value(self):
        result, case = calculated_control()
        result["scenarios"]["Downside"]["post_refinance_coc"]["window_end"] = "2028-03-30"
        result["scenarios"]["Downside"]["construction_financing"]["cash_by_date"][1]["equity_contribution"] = rational(49)
        verdict = evaluate(result, case)
        self.assertEqual((verdict["simulation_result"], verdict["reason"]), ("HOLD", "MORE_DD_REQUIRED"))
        self.assertNotIn("post_refi_CoC", verdict["observed"]["Downside"])
        self.assertNotIn("equity_recovered", verdict["observed"]["Downside"])

    def test_coarse_price_grid_near_boundary_keeps_base_rlv_pending(self):
        result, case = calculated_control()
        result["scenarios"]["Base"]["development_costs"]["worksheet_asking"] = rational(205)
        verdict = evaluate(result, case)
        self.assertIn("Base:asking_relative_to_supported_price:rlv_interval_crosses_criterion", verdict["material_gaps"])
        self.assertEqual(verdict["simulation_result"], "HOLD")

    def test_refinance_recovery_can_bind_below_the_spread_limit(self):
        result, case = calculated_control(base_payout=160)
        previous = deepcopy(result)
        verdict = evaluate(result, case)
        self.assertEqual(result, previous)
        self.assertIn(RLV, verdict["observed"]["Base"])
        self.assertEqual((verdict["simulation_result"], verdict["reason"]), ("HOLD", "ECONOMICS_NOT_SUPPORTED"))
        proof = verdict["cash_proof"]["Base"]["rlv_price_search"]
        self.assertEqual((proof["price_lower"], proof["price_upper_exclusive"], proof["binding_metrics"]),
                         (160, 170, ["equity_recovered"]))

    def test_equity_to_cost_can_bind_the_rlv(self):
        result, case = calculated_control(base_cap="0.07", base_payout=240)
        verdict = evaluate(result, case)
        proof = verdict["cash_proof"]["Base"]["rlv_price_search"]
        self.assertEqual((proof["price_lower"], proof["price_upper_exclusive"], proof["binding_metrics"]),
                         (270, 280, ["equity_TDC"]))

    def test_c33_moves_the_price_limit_with_the_same_reported_cash(self):
        result, case = calculated_control(base_payout=160)
        case["rent_inputs"]["definition_screening"]["Base"]["rlv"]["grid"] = [70, 350, 1]
        positive = evaluate(result, case)["cash_proof"]["Base"]
        result["scenarios"]["Base"]["development_costs"]["closing_fraction"] = rational(0)
        zero = evaluate(result, case)["cash_proof"]["Base"]
        self.assertEqual((zero["rlv_price_search"]["price_lower"], positive["rlv_price_search"]["price_lower"]), (166, 167))
        self.assertEqual(positive["cash_sha256"], zero["cash_sha256"])

    def test_negative_price_interval_and_unattainable_grid_are_distinct(self):
        result, case = calculated_control()
        result["scenarios"]["Base"]["development_costs"]["evaluated_purchase_price"] = rational(-50)
        case["rent_inputs"]["definition_screening"]["Base"]["rlv"]["grid"] = [-150, 100, 10]
        negative = evaluate(result, case)
        first = negative["cash_proof"]["Base"]["rlv_price_search"]
        self.assertEqual((first["price_lower"], first["price_upper_exclusive"], first["negative_limit"]), (-50, -40, True))
        self.assertNotIn(RLV, negative["observed"]["Base"])
        row = next(r for r in result["screening"]["comparisons"]
                   if (r["scenario_id"], r["metric_id"]) == ("Base", "breakeven_occupancy"))
        row["metric_record"]["value"] = rational(Fraction("0.86"))
        unattainable = evaluate(result, case)
        self.assertEqual(unattainable["cash_proof"]["Base"]["rlv_price_search"],
                         dict(state="PENDING", blocker="not_attainable_on_grid"))
        self.assertNotIn(RLV, unattainable["observed"]["Base"])
