"""Replay a declared synthetic plan revision through Base and Downside equity cash."""
from argparse import ArgumentParser
from fractions import Fraction
import json

from check_operating_replay_D20 import ROOT, local_file, require
from miniuw_foundation import closing_cash, exit_value, operating_cash
from miniuw_foundation.closing_returns import ClosingReturnBinding, assemble_closing_returns
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.rental_noi import assemble_rental_noi
from miniuw_foundation.rental_operations import produce_rental_operations
from miniuw_foundation.scheduled_expense_case import sha
from plan_impact_D106 import RENT_BASES, operations_source, vertical_alternatives
from plan_schedule_D105 import FIXTURE_A, FIXTURE_B, compare_schedules


ASSUMPTIONS = {
    "Base": dict(loss=Fraction(1, 20), concession=Fraction(1, 50), cap=Fraction(9, 100)),
    "Downside": dict(loss=Fraction(1, 5), concession=Fraction(1, 20), cap=Fraction(11, 100)),
}
INITIAL = 2400000
ANNUAL_TAX = 12000
SALE_COST_RATE = Fraction(1, 20)
DATES = ("2027-03-30", "2027-06-30", "2027-09-30", "2027-12-30", "2028-03-30", "2028-06-30")
SALE_DATE = DATES[-1]
OPERATING_PERIOD = "SYNTHETIC-D107-operating-year"
FORWARD_PERIOD = "SYNTHETIC-D107-year-from-sale"
SOURCE = "SYNTHETIC-D107"


def encode(document):
    return json.dumps(document, sort_keys=True).encode()


def template(name):
    return json.loads(local_file(ROOT, f"templates/{name}.json").read_bytes())


def build_noi(comparison, revision, context, period, terms):
    rental = operations_source(comparison, revision, RENT_BASES)
    rental.update(context=context, period_ref=period, months_in_period=12)
    for group in rental["residential_groups"]:
        group.update(loss_fraction=rational(terms["loss"]), concession_fraction=rational(terms["concession"]))
    fixed = next(row for row in rental["expense_items"] if row["kind"] == "fixed_per_declared_period")
    fixed["rate"] = rational(12 * _fraction(fixed["rate"]))
    rental_raw = encode(rental)
    residential = produce_rental_operations(rental_raw)
    spec = template("synthetic-residential-noi-assembly")
    spec.update(context=context, rental_source_sha256=sha(rental_raw), rental_run_sha256=residential.sha256)
    spec["additional_income_rows"][0]["period_ref"] = period
    spec["tax_floor"].update(value=rational(ANNUAL_TAX), period_ref=period, source_ref=f"{SOURCE}/fixed-tax")
    spec["tax_coefficient"].update(value=rational(0), source_ref=f"{SOURCE}/zero-variable-tax")
    return assemble_rental_noi(rental_raw, residential, encode(spec))


def reconcile_year(assembly, context, *, debt_payment=None, debt_source_ref=None):
    noi = assembly.noi_run.payload
    income = _fraction(noi["income_total"])
    costs = _fraction(noi["expenses_excluding_tax"]) + _fraction(noi["property_tax"])

    def claim(value, period=OPERATING_PERIOD, source_ref=f"{SOURCE}/all-operating-accruals-settled-by-sale"):
        return dict(value=rational(value), currency="USD", period_ref=period,
                    source_ref=source_ref)

    debt = {} if debt_payment is None else {
        "debt_principal_payment": _fraction(debt_payment["principal_due"]),
        "debt_interest_payment": _fraction(debt_payment["interest_due"]),
    }
    available = income - costs - sum(debt.values())
    claims = {
        "operating_receipts_claim": income,
        "operating_payments_claim": costs,
        "planned_operating_distribution": max(0, available),
        "equity_contribution": max(0, -available),
    }
    spec = template("synthetic-operating-cash")
    spec.update(
        context=context, period_ref=OPERATING_PERIOD, start_date="2027-07-01", end_date="2028-07-01",
        cash_date=SALE_DATE, noi_source_sha256=sha(assembly.compiled_raw), noi_run_sha256=assembly.noi_run.sha256,
        period_basis_ref=f"{SOURCE}/one-year-accrual-and-cash",
        distribution_basis_ref=f"{SOURCE}/distribute-surplus-or-fund-shortfall-from-equity",
        classification_basis_ref=f"{SOURCE}/all-equity-no-unsettled-cash-items",
        working_balances={name: dict(opening=claim(0, "OPENING:" + OPERATING_PERIOD),
                                     closing=claim(0, "CLOSING:" + OPERATING_PERIOD))
                          for name in operating_cash.WORKING},
        amounts={key: claim(claims.get(key, 0)) for key in
                 operating_cash.FLOWS + operating_cash.ADJUSTMENTS + operating_cash.CLAIMS}
        | {key: claim(0, prefix + OPERATING_PERIOD) for key, prefix in operating_cash.STOCKS.items()},
    )
    if debt:
        require(debt_source_ref and debt_payment["date"] == SALE_DATE,
                "Dated debt evidence must match the operating payment date")
        spec["classification_basis_ref"] = f"{SOURCE}/operating-cash-with-dated-debt-service"
        spec["amounts"].update({key: claim(value, source_ref=debt_source_ref) for key, value in debt.items()})
    return operating_cash.reconcile_operating_cash(assembly.compiled_raw, assembly.noi_run, encode(spec))


def value_at_exit(forward, context, cap):
    spec = dict(schema="miniuw.synthetic-exit-value.v1", context=context, currency="USD",
                valuation_date=SALE_DATE, noi_source_sha256=sha(forward.compiled_raw),
                noi_run_sha256=forward.noi_run.sha256, valuation_basis_ref=f"{SOURCE}/explicit-sale-at-value",
                forward_window=dict(start=SALE_DATE, end="2029-06-30", period_ref=FORWARD_PERIOD,
                                    basis_ref=f"{SOURCE}/same-terms-forward-12-months"),
                cap_rate=dict(value=rational(cap), unit="annual_cap_fraction", period_ref=FORWARD_PERIOD,
                              source_ref=f"{SOURCE}/scenario-cap"))
    return exit_value.produce_exit_value(forward.compiled_raw, forward.noi_run, encode(spec))


def sale_source(context, operating, valuation):
    def claim(value, basis, source_ref):
        return dict(value=rational(value), currency="USD", as_of_date=SALE_DATE, basis=basis, source_ref=source_ref)

    price = _fraction(valuation.payload["candidate_value"])
    proceeds = {
        "gross_proceeds": (price, f"{valuation.sha256}#/candidate_value"),
        "closing_costs_paid": (price * SALE_COST_RATE, f"{SOURCE}/sale-cost-fraction-of-price"),
    }
    amounts = {}
    for key in closing_cash.CASH_FIELDS:
        value, source_ref = proceeds.get(key, (0, f"{SOURCE}/explicit-zero"))
        amounts[key] = claim(value, "cash_flow_at_closing", source_ref)
    free_cash = _fraction(operating.payload["expected_closing_free_cash"])
    restricted_cash = _fraction(operating.payload["expected_closing_restricted_cash"])
    balances = {"opening_free_cash": free_cash, "opening_restricted_cash": restricted_cash,
                "retained_free_cash": 0, "closing_restricted_cash_claim": 0}
    amounts.update({key: claim(balances[key], basis, f"{operating.sha256}/D107-sale-balances")
                    for key, basis in closing_cash.STOCK_FIELDS.items()})
    return dict(schema=closing_cash.SCHEMA, profile="SYNTHETIC-RESIDUAL-AFTER-EXPLICIT-RETENTION-v1",
                  context=context, currency="USD", closing_date=SALE_DATE, kind="sale",
                  representation="explicit_gross_cash_movements", debt_inventory_declared_complete=True,
                  classification_basis_ref=f"{SOURCE}/sale-without-debt",
                  equity_residual_basis_ref=f"{SOURCE}/distribute-sale-residual",
                  equity_funding_assumption_ref=None, amounts=amounts, old_debts=[], new_loan=None,
                  valuation_claim=None)


def close_sale(context, operating, valuation):
    raw = encode(sale_source(context, operating, valuation))
    return raw, closing_cash.produce_closing_cash(raw)


def equity_source(context, construction, comparison, revision, operating):
    plan_hash = comparison[f"{'reference' if revision == 'before' else 'candidate'}_sha256"]
    return equity_source_from_cost(context, construction, f"{plan_hash}/declared-plan-and-D106-vertical-basis", operating)


def equity_source_from_cost(context, construction, construction_source_ref, operating, *, construction_draws=None):
    def event(identity, day, kind, category, value, source_ref):
        return dict(event_id=identity, date=day, kind=kind, category=category,
                    amount=value, currency="USD", source_ref=source_ref)

    if construction_draws is None:
        construction_draws = [dict(event_id="construction", date=DATES[1], amount=rational(construction - INITIAL),
                                   source_ref=construction_source_ref)]
    require(sum(_fraction(draw["amount"]) for draw in construction_draws) == construction - INITIAL,
            "Construction draws do not reconcile to the funding requirement")
    cash = operating.payload
    investor = template("synthetic-closing-investor-slots")
    investor.update(context=context, capital_snapshots=[], annual_cash_bases=[],
                    grid=dict(spacing="calendar_months_same_day", step_months=3, dates=list(DATES),
                              timing_basis_ref=f"{SOURCE}/quarterly-event-grid"),
                    events=[
                        event("initial", DATES[0], "contribution", "initial_capital",
                              rational(INITIAL), f"{SOURCE}/initial-equity"),
                        *(event(draw["event_id"], draw["date"], "contribution", "additional_capital", draw["amount"],
                                draw["source_ref"]) for draw in construction_draws),
                        event("operating-funding", SALE_DATE, "contribution", "additional_capital",
                              cash["exportable_equity_contribution"], f"{operating.sha256}#/exportable_equity_contribution"),
                        event("operating", SALE_DATE, "distribution", "operating_distribution",
                              cash["exportable_operating_distribution"], f"{operating.sha256}#/exportable_operating_distribution"),
                        event("sale", SALE_DATE, "distribution", "net_sale_distribution", None, None),
                    ])
    investor["irr_parameters"]["periods_per_year"] = 4
    return investor


def bind_closing(raw, closing_raw, closing, event_id):
    binding = ClosingReturnBinding(profile_id="SYNTHETIC-CLOSING-EMPTY-EQUITY-SLOTS-v1",
                                   closing_source_sha256=sha(closing_raw), closing_run_sha256=closing.sha256,
                                   investor_source_sha256=sha(raw), distribution_event_id=event_id,
                                   contribution_event_id=None)
    return assemble_closing_returns(closing_raw, closing, raw, binding)


def equity_returns(context, construction, comparison, revision, operating, closing_raw, closing):
    raw = encode(equity_source(context, construction, comparison, revision, operating))
    return bind_closing(raw, closing_raw, closing, "sale")


def run_scenario(comparison, revision, scenario, basis="units"):
    pending = dict(state="PENDING", cash_per_usd_10=None)
    groups = {row["group_id"] for row in comparison["fields"] if row["field"] == "unit_count"}
    if groups != RENT_BASES.keys():
        return pending | dict(blockers=["synthetic_rent_terms_missing_for_declared_group_inventory"])
    construction = vertical_alternatives(comparison, revision)[basis]
    if construction is None:
        return pending | dict(blockers=[f"vertical_{basis}_quantity_missing"])
    if construction < INITIAL:
        return pending | dict(blockers=["unused_initial_equity_needs_a_cash_retention_profile"])
    context = dict(deal_id=comparison["deal_id"], scenario_id=f"SYNTHETIC-{scenario}",
                   run_id=f"{SOURCE}-{revision}-{basis}", definition_set_revision=f"{SOURCE}-v1")
    terms = ASSUMPTIONS[scenario]
    historical = build_noi(comparison, revision, context, OPERATING_PERIOD, terms)
    if historical.noi_run is None or historical.payload["blockers"]:
        return pending | dict(blockers=historical.payload["blockers"] + historical.payload["residential_blockers"])
    forward = build_noi(comparison, revision, context, FORWARD_PERIOD, terms)
    if forward.noi_run is None or forward.payload["blockers"]:
        return pending | dict(blockers=forward.payload["blockers"] + forward.payload["residential_blockers"])
    operating = reconcile_year(historical, context)
    if operating.payload["state"] != "reconciled_synthetic_plan":
        return pending | dict(blockers=operating.payload["blockers"])
    valuation = value_at_exit(forward, context, terms["cap"])
    if valuation.payload["state"] != "computed_synthetic_exit_value":
        return pending | dict(blockers=valuation.payload["blockers"])
    closing_raw, closing = close_sale(context, operating, valuation)
    result = equity_returns(context, construction, comparison, revision, operating, closing_raw, closing)
    if result.investor_run is None:
        return pending | dict(blockers=result.payload["blockers"] + result.payload["closing_blockers"])
    returns = result.investor_run.payload
    if returns["cash_metrics_state"] != "computed_synthetic" or returns["normalized_story"]["events"] is None:
        return pending | dict(blockers=returns["cash_blockers"] + returns["story_blockers"])
    story = returns["normalized_story"]
    return dict(
        state="computed_synthetic", blockers=[], vertical_basis=basis, vertical_cost=rational(construction),
        operating_noi=historical.payload["computed_noi"], forward_noi=valuation.payload["forward_noi"],
        gross_sale=valuation.payload["candidate_value"], cap_rate=rational(terms["cap"]),
        cash_per_usd_10=story | dict(unrecovered_after_sale=rational(max(0, -_fraction(story["net_cash_profit"])))),
        annual_irr_roots=returns["annual_irr_roots"],
        source_runs=dict(operating_noi_sha256=historical.noi_run.sha256, forward_noi_sha256=forward.noi_run.sha256,
                         operating_cash_sha256=operating.sha256, exit_value_sha256=valuation.sha256,
                         closing_sha256=closing.sha256, equity_returns_sha256=result.investor_run.sha256),
    )


def build_report(before, after):
    comparison = compare_schedules(before, after)
    return dict(status="compared", decision="PENDING", scope="synthetic_aggregate_equity",
                financing="all_equity_no_refinance", personal_investor_return=None,
                deployment_enabled=False, real_decisions_enabled=False,
                plan_comparison=comparison,
                scenarios={name: {side: run_scenario(comparison, side, name) for side in ("before", "after")}
                           for name in ASSUMPTIONS},
                required_gsf_downside=run_scenario(comparison, "after", "Downside", "gsf"))


def verify(before, after, report):
    # Independent expected project amounts from the fixture quantities and terms.
    costs = (3250000, 2500000)
    expected_noi = {"Base": (Fraction("377198.4"), Fraction("257815.2")),
                    "Downside": (Fraction(296760), Fraction(201180))}
    checked = 0
    for name, pair in report["scenarios"].items():
        cap = Fraction(9 if name == "Base" else 11, 100)
        for index, side in enumerate(("before", "after")):
            row = pair[side]
            story = row["cash_per_usd_10"]
            noi = expected_noi[name][index]
            budget = costs[index]
            sale = noi / cap
            scale = Fraction(1, 240000)
            received = (noi + sale * Fraction(95, 100)) * scale
            require(row["state"] == "computed_synthetic"
                    and [_fraction(row[key]) for key in ("vertical_cost", "operating_noi", "forward_noi", "gross_sale")]
                    == [budget, noi, noi, sale], "Plan quantities did not reach budget, NOI and exit")
            require(story["basis_event_ids"] == ["initial"]
                    and _fraction(story["basis_amount"]) == 2400000
                    and _fraction(story["scale_factor"]) == scale, "The additional contribution changed the USD 10 basis")
            require([(event["event_id"], event["date"], _fraction(event["amount"])) for event in story["events"]]
                    == [("initial", DATES[0], 10), ("construction", DATES[1], (budget - INITIAL) * scale),
                        ("operating-funding", SALE_DATE, 0), ("operating", SALE_DATE, noi * scale),
                        ("sale", SALE_DATE, sale * Fraction(95, 100) * scale)],
                    "The USD 10 ledger differs from the expected cash events")
            contributed = budget * scale
            require([_fraction(story[key]) for key in ("total_contributions", "total_distributions", "net_cash_profit",
                                                       "unrecovered_after_sale", "equity_multiple")]
                    == [contributed, received, received - contributed, max(0, contributed - received),
                        received / contributed],
                    "USD 10 totals do not reconcile to the dated events")
            checked += 1

    old, current = json.loads(before), json.loads(after)
    area_only = old | dict(revision=2, groups=[old["groups"][0] |
                           {"unit_rentable_sf": current["groups"][1]["unit_rentable_sf"]}, old["groups"][1]])
    count_only = old | dict(revision=2, groups=[old["groups"][0], current["groups"][0]])
    for doc, noi, budget in ((area_only, Fraction("368716.8"), 3250000),
                             (count_only, Fraction("266296.8"), 2500000)):
        row = run_scenario(compare_schedules(before, encode(doc)), "after", "Base")
        story = row["cash_per_usd_10"]
        require((_fraction(row["operating_noi"]), _fraction(row["vertical_cost"])) == (noi, budget)
                and _fraction(story["total_distributions"]) == (noi + noi * Fraction(95, 9)) / 240000
                and _fraction(story["total_contributions"]) == Fraction(budget, 240000),
                "The isolated rentable area or unit count used the wrong calculation base")

    for field, group_index, reason in (("unit_rentable_sf", 1, "rentable_area_missing_or_outside_profile"),
                                        ("unit_count", 0, "vertical_units_quantity_missing")):
        missing = json.loads(after)
        missing["groups"][group_index][field]["value"] = None
        row = run_scenario(compare_schedules(before, encode(missing)), "after", "Downside")
        require(row["state"] == "PENDING" and row["cash_per_usd_10"] is None
                and any(reason in blocker for blocker in row["blockers"]), "A missing plan field leaked into cash")
    blocked = report["required_gsf_downside"]
    require(blocked == dict(state="PENDING", cash_per_usd_10=None, blockers=["vertical_gsf_quantity_missing"]),
            "The GSF branch ignored its required source")
    gross_only = old | dict(revision=2, building_gsf=old["building_gsf"] | {"value": rational(24000)})
    comparison = compare_schedules(before, encode(gross_only))
    gross_before, gross_after = (run_scenario(comparison, side, "Downside", "gsf")
                                 for side in ("before", "after"))
    require(_fraction(gross_before["vertical_cost"]) == 4000000
            and _fraction(gross_after["vertical_cost"]) == 3840000
            and gross_before["cash_per_usd_10"]["total_distributions"]
            == gross_after["cash_per_usd_10"]["total_distributions"]
            and _fraction(gross_before["cash_per_usd_10"]["total_contributions"])
            - _fraction(gross_after["cash_per_usd_10"]["total_contributions"]) == Fraction(2, 3),
            "A GSF-only change must reach equity funding without changing rent or sale")
    require(report["decision"] == "PENDING" and report["personal_investor_return"] is None
            and not report["deployment_enabled"] and not report["real_decisions_enabled"],
            "The synthetic replay acquired financial authority")
    return dict(status="passed", decision="PENDING", dated_cash_cases=checked,
                isolated_changes=3, missing_source_cases=3)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "report"))
    args = parser.parse_args()
    before, after = (local_file(ROOT, name).read_bytes() for name in (FIXTURE_A, FIXTURE_B))
    report = build_report(before, after)
    print(json.dumps(verify(before, after, report) if args.command == "check" else report, sort_keys=True))


if __name__ == "__main__":
    main()
