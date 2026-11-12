"""Test the D105 plan revision through capacity, refinance, and USD 10 equity cash."""
from argparse import ArgumentParser
from fractions import Fraction
from math import floor
import json

from check_operating_replay_D20 import ROOT, local_file, require
from miniuw_foundation import closing_cash
from miniuw_foundation.debt_closing import DatedLoanEvidence, reconcile_debt_closing
from miniuw_foundation.debt_service import _fraction, produce_debt_service, rational
from miniuw_foundation.refinance_capacity import RefinanceInputs, size_refinance
from miniuw_foundation.scheduled_expense_case import sha
from plan_impact_D106 import RENT_BASES, vertical_alternatives
from plan_return_D107 import (
    ASSUMPTIONS, DATES, FORWARD_PERIOD, INITIAL, OPERATING_PERIOD, SALE_COST_RATE, SALE_DATE,
    bind_closing, build_noi, encode, equity_source_from_cost, reconcile_year, sale_source, template, value_at_exit,
)
from plan_schedule_D105 import FIXTURE_A, FIXTURE_B, compare_schedules


SOURCE = "SYNTHETIC-D108"
REFI_DATE = DATES[-2]
REQUEST = 1400000
FEE = Fraction(1, 50)
REFI_CAP = Fraction(1, 10)
LTV = Fraction(13, 20)
DSCR = Fraction(5, 4)
BANK_LOSS_ADD = Fraction(1, 20)
QUARTERLY_RATE = Fraction(1, 80)
AMORTIZATION = 40
PAYMENT_DATES = (
    SALE_DATE, "2028-09-30", "2028-12-30", "2029-03-30", "2029-06-30",
    "2029-09-30", "2029-12-30", "2030-03-30",
)
BANK_PERIOD = f"{SOURCE}-bank-annual"
VALUE_PERIOD = f"{SOURCE}-refinance-valuation-annual"


def loan_evidence(context, principal, *, refi_date=REFI_DATE, payment_dates=PAYMENT_DATES):
    terms = template("synthetic-project-sale-loan")
    terms.update(context=context, loan_id=f"{SOURCE}-permanent-loan", principal=rational(principal),
                 periodic_rate=rational(QUARTERLY_RATE), origination_date=refi_date,
                 payments_per_year=4, amortization_payments=AMORTIZATION, maturity_payment=len(payment_dates),
                 payment_dates=list(payment_dates), annual_equivalent_ref=BANK_PERIOD,
                 rate_interval_ref=f"{SOURCE}/quarterly-fixed-rate")
    raw = encode(terms)
    return DatedLoanEvidence(loan_raw=raw, windows=(), run=produce_debt_service(raw, ()))


def refi_closing(context, loan, principal, *, refi_date=REFI_DATE, construction_financing=None):
    source = template("synthetic-capacity-tie-closing")
    source.update(context=context, closing_date=refi_date, kind="refinance",
                  classification_basis_ref=f"{SOURCE}/gross-draw-and-explicit-refinance-fee",
                  equity_residual_basis_ref=f"{SOURCE}/distribute-only-net-proceeds",
                  equity_funding_assumption_ref=None, old_debts=[], valuation_claim=None)
    values = {"gross_proceeds": principal, "closing_costs_paid": principal * FEE}
    for key, row in source["amounts"].items():
        row.update(value=rational(values.get(key, 0)), as_of_date=refi_date, source_ref=f"{SOURCE}/refi/{key}")
    if construction_financing is not None:
        funding = construction_financing
        require(funding["payoff_date"] == refi_date, "construction_payoff_date_must_match_refinance")
        proof_ref = f"sha256:{funding['debt_run_sha256']}"
        source["amounts"]["opening_free_cash"].update(
            value=funding["free_cash_at_refinance"], source_ref=f"sha256:{sha(encode(funding))}#/free_cash_at_refinance")
        if _fraction(funding["construction_principal_payoff"]):
            old_debt = dict(loan_id=funding["debt_run"]["loan_id"])
            for category in closing_cash.DUE:
                for role, basis in (("due", "debt_obligation_before_closing"), ("paid", "cash_flow_at_closing")):
                    old_debt[f"{category}_{role}"] = dict(
                        value=funding["construction_principal_payoff"] if category == "principal" else rational(0),
                        currency="USD", as_of_date=refi_date, basis=basis,
                        source_ref=f"{proof_ref}#/totals/principal_repaid" if category == "principal"
                        else f"{funding['policy_ref']}/no-unpaid-interest-or-other-payoff-fees")
            source["old_debts"].append(old_debt)
    source["new_loan"] = dict(loan_id=loan.run.payload["loan_id"], principal_after_closing=dict(
        value=rational(principal), currency="USD", as_of_date=refi_date, basis="debt_principal_after_closing",
        source_ref=f"{loan.run.sha256}#/principal_at_origination"))
    raw = encode(source)
    return raw, closing_cash.produce_closing_cash(raw)


def capacity_check(context, valuation, bank, loan, refi_raw, refi, principal, *, refi_date=REFI_DATE):
    inputs = RefinanceInputs(valuation_noi_raw=valuation.compiled_raw, valuation_noi_run=valuation.noi_run,
                             bank_noi_raw=bank.compiled_raw, bank_noi_run=bank.noi_run,
                             new_loan=loan, closing_raw=refi_raw, closing_run=refi)
    spec = template("synthetic-capacity-project-spec")
    spec.update(context=context, as_of_date=refi_date, valuation_noi_period_ref=VALUE_PERIOD,
                bank_noi_period_ref=BANK_PERIOD,
                valuation_noi_source_sha256=sha(valuation.compiled_raw), valuation_noi_run_sha256=valuation.noi_run.sha256,
                bank_noi_source_sha256=sha(bank.compiled_raw), bank_noi_run_sha256=bank.noi_run.sha256,
                new_loan_source_sha256=sha(loan.loan_raw), new_loan_run_sha256=loan.run.sha256,
                closing_source_sha256=sha(refi_raw), closing_run_sha256=refi.sha256)
    for key, value, period in (("cap_rate", REFI_CAP, VALUE_PERIOD), ("maximum_ltv", LTV, "SYNTHETIC-sizing-at-date"),
                               ("minimum_dscr", DSCR, BANK_PERIOD)):
        spec["parameters"][key].update(value=rational(value), period_ref=period, source_ref=f"{SOURCE}/bank/{key}")
    spec["selected_principal"].update(value=rational(principal), as_of_date=refi_date,
                                      source_ref=f"{SOURCE}/requested-gross-principal")
    return size_refinance(inputs, encode(spec))


def sale_with_payoff(context, operating, valuation, loan, payment, *, replacement_reserve=None):
    sale_date = payment["date"]
    source = sale_source(context, operating, valuation, sale_date=sale_date, replacement_reserve=replacement_reserve)
    source["classification_basis_ref"] = f"{SOURCE}/sale-after-dated-regular-payment"
    principal = _fraction(payment["closing_balance"])
    debt = {"loan_id": loan.run.payload["loan_id"]}
    for category in closing_cash.DUE:
        for role, basis in (("due", "debt_obligation_before_closing"), ("paid", "cash_flow_at_closing")):
            debt[f"{category}_{role}"] = dict(
                value=rational(principal if category == "principal" else 0),
                currency="USD", as_of_date=sale_date, basis=basis,
                source_ref=(f"{loan.run.sha256}#/schedule/0/closing_balance" if category == "principal"
                            else f"{SOURCE}/interest-in-operating-cash-and-no-other-payoff-costs"))
    source["old_debts"] = [debt]
    raw = encode(source)
    closing = closing_cash.produce_closing_cash(raw)
    spec = template("synthetic-project-sale-debt-binding")
    spec.update(context=context, closing_source_sha256=sha(raw), closing_run_sha256=closing.sha256)
    spec["loans"][0].update(loan_id=debt["loan_id"], loan_source_sha256=sha(loan.loan_raw),
                             loan_run_sha256=loan.run.sha256, payment_cutoff="after_regular_payment_before_balloon",
                             cutoff_basis_ref=f"{SOURCE}/after-payment-before-payoff-on-sale-date")
    checked = reconcile_debt_closing((loan,), raw, closing, encode(spec))
    return raw, closing, checked


def run_scenario(comparison, revision, scenario, principal=REQUEST):
    result = dict(state="PENDING", capacity=None, cash_per_usd_10=None)
    groups = {row["group_id"] for row in comparison["fields"] if row["field"] == "unit_count"}
    if groups != RENT_BASES.keys():
        return result | dict(blockers=["synthetic_rent_terms_missing_for_declared_group_inventory"])
    cost = vertical_alternatives(comparison, revision)["units"]
    if cost is None or cost < INITIAL:
        return result | dict(blockers=["construction_budget_unavailable_for_equity_profile"])
    context = dict(deal_id=comparison["deal_id"], scenario_id=f"SYNTHETIC-{scenario}",
                   run_id=f"{SOURCE}-{revision}", definition_set_revision=f"{SOURCE}-v1")
    terms = ASSUMPTIONS[scenario]
    plan_hash = comparison[f"{'reference' if revision == 'before' else 'candidate'}_sha256"]

    def noi_for(period):
        inputs = terms | {"loss": terms["loss"] + BANK_LOSS_ADD} if period == BANK_PERIOD else terms
        return build_noi(comparison, revision, context, period, inputs)

    return financed_cash(context, cost, f"{plan_hash}/declared-plan-and-D106-vertical-basis", principal, terms["cap"], noi_for)


def financed_cash(context, cost, construction_source_ref, principal, exit_cap, noi_for, *, construction_draws=None,
                  calendar=None, construction_financing=None, replacement_reserve=None):
    result = dict(state="PENDING", capacity=None, cash_per_usd_10=None)
    refi_date = REFI_DATE if calendar is None else calendar["refinance_date"]
    sale_date = SALE_DATE if calendar is None else calendar["sale_date"]
    valuation = noi_for(VALUE_PERIOD)
    bank = noi_for(BANK_PERIOD)
    for assembly in (valuation, bank):
        if assembly.payload["blockers"]:
            return result | dict(blockers=assembly.payload["blockers"] + assembly.payload["residential_blockers"])
    loan = loan_evidence(context, principal, refi_date=refi_date,
                         payment_dates=PAYMENT_DATES if calendar is None else calendar["payment_dates"])
    refi_raw, refi = refi_closing(context, loan, principal, refi_date=refi_date,
                                 construction_financing=construction_financing)
    if construction_financing is not None:
        closing = refi.payload
        result["construction_refinance"] = dict(
            date=refi_date, gross_proceeds=rational(principal), closing_fee=rational(principal * FEE),
            prior_principal_paid=closing["payoff_totals"]["principal"],
            net_equity_distribution=closing["exportable_equity_distribution"], blockers=closing["blockers"],
            closing_source_sha256=sha(refi_raw), closing_run_sha256=refi.sha256)
    cap_run = capacity_check(context, valuation, bank, loan, refi_raw, refi, principal, refi_date=refi_date)
    cap = cap_run.payload
    result["capacity"] = {key: cap[key] for key in (
        "valuation_noi", "bank_noi", "selected_principal", "maximum_principal_capacity", "binding_limit_ids",
        "capacity_limits", "capacity_state", "state", "as_of_date", "input_bindings",
    )} | {"capacity_run_sha256": cap_run.sha256}
    if cap["state"] != "compatible_synthetic_refinance_capacity":
        if construction_financing is not None:
            result["construction_refinance"]["net_equity_distribution"] = None
            return result | dict(blockers=sorted(set(cap["blockers"] + closing["blockers"])))
        return result | dict(blockers=cap["blockers"])

    operating_noi = noi_for(OPERATING_PERIOD)
    forward_noi = noi_for(FORWARD_PERIOD)
    for assembly in (operating_noi, forward_noi):
        if assembly.payload["blockers"]:
            return result | dict(blockers=assembly.payload["blockers"] + assembly.payload["residential_blockers"])
    payment = loan.run.payload["schedule"][0]
    require(payment["date"] == sale_date and _fraction(payment["balloon_due"]) == 0,
            "The synthetic period requires one scheduled payment on sale day before payoff")
    operating_dates = {} if calendar is None else dict(operating_window=calendar["operating_window"], cash_date=sale_date)
    operating = reconcile_year(operating_noi, context, debt_payment=payment,
                               debt_source_ref=f"{loan.run.sha256}#/schedule/0", replacement_reserve=replacement_reserve,
                               **operating_dates)
    if operating.payload["blockers"]:
        return result | dict(blockers=operating.payload["blockers"])
    exit_dates = {} if calendar is None else dict(sale_date=sale_date, forward_end=calendar["exit_forward_end"])
    exit_run = value_at_exit(forward_noi, context, exit_cap, **exit_dates)
    if exit_run.payload["blockers"]:
        return result | dict(blockers=exit_run.payload["blockers"])
    sale_raw, sale, debt_check = sale_with_payoff(context, operating, exit_run, loan, payment, replacement_reserve=replacement_reserve)
    if debt_check.payload["blockers"]:
        return result | dict(blockers=debt_check.payload["blockers"] + debt_check.payload["closing_blockers"])
    if replacement_reserve is not None:
        operating_cash = operating.payload
        sale_cash = sale.payload
        closing_claims = json.loads(sale_raw)["amounts"]
        result["replacement_reserve"] = replacement_reserve | dict(
            deposit_date=operating_cash["cash_date"], sale_date=sale_cash["closing_date"],
            restricted_before_sale=operating_cash["expected_closing_restricted_cash"],
            operating_equity_contribution=operating_cash["exportable_equity_contribution"],
            released_at_sale=closing_claims["reserve_release"]["value"],
            transferred_restricted_to_buyer=sale_cash["expected_closing_restricted_cash"],
            operating_cash_residual=operating_cash["total_cash_conservation_residual"],
            sale_cash_residual=sale_cash["total_cash_conservation_residual"],
            operating_cash_sha256=operating.sha256, sale_closing_sha256=sale.sha256)

    equity_grid = {} if calendar is None else dict(equity_dates=calendar["equity_dates"], timing_basis_ref=calendar["policy_ref"])
    ledger = equity_source_from_cost(context, cost, construction_source_ref, operating, construction_draws=construction_draws,
                                    **equity_grid)
    ledger["events"].insert(len(ledger["events"]) - 3, dict(
        event_id="refinance", date=refi_date, kind="distribution", category="net_refinance_distribution",
        amount=None, currency="USD", source_ref=None))
    refi_bound = bind_closing(encode(ledger), refi_raw, refi, "refinance")
    if refi_bound.compiled_raw is None:
        return result | dict(blockers=refi_bound.payload["blockers"] + refi_bound.payload["closing_blockers"])
    sale_bound = bind_closing(refi_bound.compiled_raw, sale_raw, sale, "sale")
    if sale_bound.investor_run is None:
        return result | dict(blockers=sale_bound.payload["blockers"] + sale_bound.payload["closing_blockers"])
    cash = sale_bound.investor_run.payload
    story = cash["normalized_story"]
    if cash["cash_metrics_state"] != "computed_synthetic" or story["events"] is None:
        return result | dict(blockers=cash["cash_blockers"] + cash["story_blockers"])
    return result | dict(
        state="computed_synthetic", blockers=[], vertical_cost=rational(cost), gross_sale=exit_run.payload["candidate_value"],
        dated_debt_service=payment, debt_principal_paid_at_sale=sale.payload["payoff_totals"]["principal"],
        cash_per_usd_10=story | dict(unrecovered_after_sale=rational(max(0, -_fraction(story["net_cash_profit"])))),
        source_runs=dict(operating_cash_sha256=operating.sha256, exit_value_sha256=exit_run.sha256,
                         sale_closing_sha256=sale.sha256, debt_check_sha256=debt_check.sha256,
                         equity_returns_sha256=sale_bound.investor_run.sha256),
    )


def build_report(before, after):
    comparison = compare_schedules(before, after)
    return dict(status="compared", decision="PENDING", scope="synthetic_aggregate_equity",
                personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False,
                plan_comparison=comparison,
                scenarios={name: {side: run_scenario(comparison, side, name) for side in ("before", "after")}
                           for name in ASSUMPTIONS})


def verify(report):
    expected = {
        "Base": ((Fraction("377198.4"), Fraction("354854.4")), (Fraction("257815.2"), Fraction("242083.2"))),
        "Downside": ((296760, 274416), (201180, 185448)),
    }
    costs = (3250000, 2500000)
    unit_payment = Fraction(1, 80) / (1 - Fraction(81, 80) ** -40)
    payment = 1400000 * unit_payment
    interest = Fraction(17500)
    payoff = 1400000 - (payment - interest)
    complete = blocked = 0
    for scenario, pair in report["scenarios"].items():
        for index, side in enumerate(("before", "after")):
            row = pair[side]
            annual_noi, bank_noi = expected[scenario][index]
            ltv_limit = annual_noi * Fraction(13, 2)
            dscr_limit = bank_noi / (5 * unit_payment)
            cap = row["capacity"]
            require([_fraction(cap[key]) for key in ("valuation_noi", "bank_noi", "selected_principal",
                                                     "maximum_principal_capacity")]
                    == [annual_noi, bank_noi, 1400000, min(ltv_limit, dscr_limit)]
                    and {k: _fraction(v) for k, v in cap["capacity_limits"].items()} ==
                    {"LTV": ltv_limit, "DSCR": dscr_limit} and cap["binding_limit_ids"] == ["DSCR"],
                    "Capacity differs from the independent loan and NOI calculations")
            if scenario == "Downside" and side == "after":
                require(row["state"] == "PENDING" and row["cash_per_usd_10"] is None
                        and row["blockers"] == ["selected_principal_exceeds_declared_bank_capacity"]
                        and "gross_sale" not in row and "dated_debt_service" not in row,
                        "A blocked draw emitted downstream cash or acquired replacement financing")
                blocked += 1
                continue
            cap_rate = Fraction(9 if scenario == "Base" else 11, 100)
            sale = annual_noi / cap_rate * Fraction(95, 100) - payoff
            cash = row["cash_per_usd_10"]
            scale = Fraction(1, 240000)
            expected_events = [("initial", "2027-03-30", 10),
                               ("construction", "2027-06-30", (costs[index] - 2400000) * scale),
                               ("refinance", "2028-03-30", 1372000 * scale),
                               ("operating-funding", "2028-06-30", 0),
                               ("operating", "2028-06-30", (annual_noi - payment) * scale),
                               ("sale", "2028-06-30", sale * scale)]
            require(row["state"] == "computed_synthetic"
                    and [(e["event_id"], e["date"], _fraction(e["amount"])) for e in cash["events"]] == expected_events
                    and cash["basis_event_ids"] == ["initial"]
                    and _fraction(cash["basis_amount"]) == 2400000,
                    "Dated cash or normalization differs from the independent fixture")
            received = (1372000 + annual_noi - payment + sale) * scale
            invested = costs[index] * scale
            require([_fraction(cash[key]) for key in ("total_contributions", "total_distributions", "net_cash_profit",
                                                      "unrecovered_after_sale")]
                    == [invested, received, received - invested, max(0, invested - received)]
                    and _fraction(row["debt_principal_paid_at_sale"]) == payoff,
                    "Cash totals or principal payoff do not reconcile")
            complete += 1

    comparison = report["plan_comparison"]
    ceiling = _fraction(report["scenarios"]["Downside"]["after"]["capacity"]["maximum_principal_capacity"])
    floor_cents = Fraction(floor(ceiling * 100), 100)
    for principal, state in ((floor_cents, "computed_synthetic"), (floor_cents + Fraction(1, 100), "PENDING")):
        probe = run_scenario(comparison, "after", "Downside", principal)
        require(probe["state"] == state and _fraction(probe["capacity"]["selected_principal"]) == principal
                and _fraction(probe["capacity"]["maximum_principal_capacity"]) == ceiling
                and (probe["cash_per_usd_10"] is None) == (state == "PENDING"),
                "The exact capacity boundary changed or a blocked draw was resized")
    require(report["decision"] == "PENDING" and report["personal_investor_return"] is None
            and not report["deployment_enabled"] and not report["real_decisions_enabled"],
            "The comparison acquired investment or deployment authority")
    return dict(status="passed", decision="PENDING", dated_cash_cases=complete,
                capacity_blocked_cases=blocked, cent_boundary_probes=2)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "report"))
    args = parser.parse_args()
    before, after = (local_file(ROOT, name).read_bytes() for name in (FIXTURE_A, FIXTURE_B))
    report = build_report(before, after)
    print(json.dumps(verify(report) if args.command == "check" else report, sort_keys=True))


if __name__ == "__main__":
    main()
