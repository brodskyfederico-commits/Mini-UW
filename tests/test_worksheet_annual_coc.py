"""Cotejo of four synthetic quarters, the permanent loan, and the USD 10 ledger."""

from copy import deepcopy
from fractions import Fraction
from unittest import TestCase

from test_worksheet_lorena_screening import DATES, DEAL, calculated_control, evaluate
from miniuw_foundation.debt_service import _fraction, rational
from plan_refinance_D108 import loan_evidence
from worksheet_annual_coc import SCHEMA, verify_annual_coc
from worksheet_performance_policy_D184 import AFTER_RESERVES


def control():
    result, case = calculated_control()
    terms = {}
    for name, cap, net in (("Base", 880, (10, 12, 0, 38)), ("Downside", 850, (9, 11, 12, 18))):
        view = result["scenarios"][name]
        refi, first_year = DATES[3], DATES[4:]
        future = [f"2029-{month:02d}-30" for month in (3, 6, 9, 12)]
        context = dict(deal_id=DEAL, scenario_id=name, run_id=DEAL, definition_set_revision=DEAL)
        evidence = loan_evidence(context, Fraction(cap), refi_date=refi, payment_dates=first_year + future).run
        schedule = evidence.payload["schedule"]
        view["permanent_loan"] = dict(quote_state="computed_synthetic", origination_date=refi, payments_per_year=4,
                                      projected_schedule=schedule, loan_run_sha256=evidence.sha256)
        periods = []
        for start, payment, available in zip([refi, *first_year[:-1]], schedule[:4], net, strict=True):
            service = _fraction(payment["scheduled_service_due"])
            periods.append(dict(start=start, end=payment["date"], noi_after_reserves=rational(service + available),
                                source_ref=f"{DEAL}/{name}/NOI/{payment['date']}"))
        terms[name] = dict(schema=SCHEMA, noi_basis=AFTER_RESERVES, source_ref=f"{DEAL}/{name}/annual", quarters=periods)
    case["rent_inputs"]["annual_post_refi_coc"] = terms
    return result, case, terms


class WorksheetAnnualCocTests(TestCase):
    def test_dated_annual_coc_reaches_d230_with_the_same_cash(self):
        result, case, _ = control()
        snapshot = deepcopy(result)
        evaluated = evaluate(result, case)
        self.assertEqual((evaluated["simulation_result"], evaluated["decision"]), ("PASS", "PENDING"))
        self.assertEqual(result, snapshot)
        for name, expected_equity, expected_available in (("Base", 120, 60), ("Downside", 150, 50)):
            proof = evaluated["cash_proof"][name]["annual_post_refi_coc"]
            self.assertEqual(proof["equity_remaining"], rational(expected_equity))
            self.assertEqual(proof["cash_available"], rational(expected_available))
            self.assertEqual([r["end"] for r in proof["quarters"]], DATES[4:])
            self.assertEqual(evaluated["observed"][name]["post_refi_CoC"]["value"],
                             rational(Fraction(expected_available, expected_equity)))

    def test_missing_quarter_blocks_coc_and_rlv_and_preserves_cash(self):
        result, case, terms = control()
        terms["Base"]["quarters"].pop()
        snapshot = deepcopy(result)
        evaluated = evaluate(result, case)
        self.assertEqual((evaluated["simulation_result"], evaluated["decision"]), ("HOLD", "PENDING"))
        self.assertEqual(result, snapshot)
        self.assertNotIn("post_refi_CoC", evaluated["observed"]["Base"])
        self.assertNotIn("asking_relative_to_supported_price", evaluated["observed"]["Base"])
        self.assertIn("post_refi_CoC", evaluated["observed"]["Downside"])

    def test_explicit_zero_noi_differs_from_a_blank_or_an_unmatched_quarter(self):
        result, _, terms = control()
        quarter = terms["Base"]["quarters"][0]
        view = result["scenarios"]["Base"]
        quarter["noi_after_reserves"] = rational(0)
        verified = verify_annual_coc(view, terms["Base"])
        self.assertEqual(verified["state"], "calculated_synthetic")
        self.assertEqual(verified["quarters"][0]["noi_after_reserves"], rational(0))
        quarter["noi_after_reserves"] = None
        self.assertIn("noi_quarter_missing_or_incompatible", verify_annual_coc(view, terms["Base"])["blocker"])
        quarter.update(noi_after_reserves=rational(0), end=DATES[5])
        self.assertIn("noi_quarter_missing_or_incompatible", verify_annual_coc(view, terms["Base"])["blocker"])

    def test_early_sale_stops_the_annual_measure(self):
        result, _, terms = control()
        view = result["scenarios"]["Base"]
        view["project_calendar"]["sale_date"] = DATES[4]
        self.assertEqual(verify_annual_coc(view, terms["Base"])["blocker"], "sale_precedes_first_complete_post_refi_year")

    def test_debt_gap_and_refinance_cash_conflict_remain_pending(self):
        result, _, terms = control()
        view = result["scenarios"]["Base"]
        schedule = view["permanent_loan"]["projected_schedule"]
        saved = schedule[0].pop("scheduled_service_due")
        self.assertIn("scheduled_service_missing_or_incompatible", verify_annual_coc(view, terms["Base"])["blocker"])
        schedule[0]["scheduled_service_due"] = saved
        view["construction_refinance"]["net_equity_distribution"] = rational(181)
        self.assertEqual(verify_annual_coc(view, terms["Base"])["blocker"], "equity_remaining_after_refinance_unconfirmed")
        view["construction_refinance"]["net_equity_distribution"] = rational(180)
        view["cash_per_usd_10"]["events"].append(dict(category="net_refinance_distribution", date=DATES[5], amount=rational(1)))
        self.assertEqual(verify_annual_coc(view, terms["Base"])["blocker"], "equity_remaining_after_refinance_unconfirmed")
