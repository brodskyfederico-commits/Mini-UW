"""Reproduce the D181 pilot and exercise the proposed SRC-02/SRC-03 rules."""
from argparse import ArgumentParser
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from check_operating_replay_D20 import require
from check_worksheet_integrated_screening_D181 import CASE, CURRENT, check_oracle
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded, verify_package, write_package
from plan_refinance_D108 import VALUE_PERIOD
from worksheet_performance_policy_D184 import AFTER_RESERVES, BEFORE_RESERVES, equilibrium, performance, price_screen


def performance_checks(scenarios, screening):
    evidence = {}
    for name, view in scenarios.items():
        reserve = view["replacement_reserve"]
        calendar = view["project_calendar"]
        annual = view["noi_by_period"][VALUE_PERIOD]
        factors = list(map(amount, annual["growth"]["expense_month_factors"]))
        cost = amount(screening["metric_evidence_by_scenario"][name]["cost_basis"]["tdc"])
        unit_reserve = amount(reserve["annual_rate"]) * reserve["eligible_units"]
        # D181's refinance-to-sale window covers the first three monthly factors.
        require(len(factors) == 12 and annual["growth"]["window_start"] == calendar["noi_window_starts"][VALUE_PERIOD]
                and calendar["equity_dates"][-2:] == [calendar["refinance_date"], calendar["sale_date"]],
                "The reference window no longer supports the proposed reserve allocation")
        annual_reserve = unit_reserve * sum(factors) / 12
        tranche_reserve = unit_reserve * sum(factors[:3]) / 12
        coc = view["post_refinance_coc"]
        noi = amount(annual["noi"])
        cap = Fraction(7, 100)  # Independent synthetic cap input, with an explicitly declared basis per probe.
        common = dict(noi=noi, reserve=annual_reserve, cost=cost, cap=cap,
                      post_refi_noi=amount(coc["period_noi"]), post_refi_reserve=tranche_reserve,
                      service=amount(coc["scheduled_debt_service"]), equity=amount(coc["equity_still_invested"]))
        trial = {basis: performance(cap_basis=basis, **common) for basis in (AFTER_RESERVES, BEFORE_RESERVES, None)}
        after, before, missing = (trial[key] for key in (AFTER_RESERVES, BEFORE_RESERVES, None))
        require(after["yoc"] == before["yoc"] == missing["yoc"] == (noi - annual_reserve) / cost,
                "The comparable cap changed the reported YoC")
        require(after["spread_bps"] == (after["yoc"] - cap) * 10_000
                and before["spread_bps"] - after["spread_bps"] == annual_reserve * 10_000 / cost,
                "Spread compared incompatible reserve bases")
        require(missing["spread_bps"] is None and missing["spread_state"] == "PENDING", "Unknown cap basis yielded a spread")
        require(after["coc"] == amount(coc["value"]) - tranche_reserve / amount(coc["equity_still_invested"]),
                "CoC did not use the reserve of the refinance-to-sale window")
        evidence[name] = dict(noi_uw=after["noi_uw"], yoc=after["yoc"], coc=after["coc"], coc_annualized=False,
                              reserve_annual=annual_reserve, reserve_post_refi=tranche_reserve,
                              spread_by_basis={"after_reserves": after, "before_reserves": before, "basis_missing": missing},
                              sources=dict(reserve_cell=reserve["cell_source"], growth_cell=view["growth_terms"]["cell_sources"]["C76"],
                                           period=annual["growth"]["window_start"] + "/" + annual["growth"]["window_end_exclusive"],
                                           refi_to_sale=[calendar["refinance_date"], calendar["sale_date"]],
                                           noi_sha256=annual["noi_assembly_sha256"], cash_sha256=sha(
                                               encoded(view["cash_per_usd_10"]))),
                              cash_per_usd_10=view["cash_per_usd_10"],
                              bank_capacity_sha256=view["capacity"]["capacity_run_sha256"],
                              bank_noi=view["capacity"]["bank_noi"], refi_value=view["valuation_and_sale"]["refinance_value"],
                              gross_sale=view["gross_sale"])
    return evidence


def occupancy_checks():
    profile = dict(slope=Fraction(500_000), intercept=Fraction(-80_000), floor=Fraction(20_000),
                   tax_coefficient=Fraction(1, 10), debt_service=Fraction(110_000), reserve=Fraction(30_000))
    combined = equilibrium(**profile)
    require(combined["economic"] == Fraction(12, 25) and combined["physical"] is None
            and combined["physical_state"] == "PENDING" and combined["physical_blocker"] == "C14_sin_desglose",
            "A combined C14 supplied a physical occupancy")
    split = equilibrium(**profile, credit_loss=Fraction(1, 20), concessions=Fraction(1, 50))
    require(split["physical"] * Fraction(19, 20) * Fraction(49, 50) == combined["economic"],
            "Physical occupancy did not reproduce the economic realization")
    zero = equilibrium(**profile, credit_loss=Fraction(), concessions=Fraction())
    require(zero["physical"] == combined["economic"], "Explicit zero losses did not preserve occupancy")
    coefficient_branch = equilibrium(**(profile | {"floor": Fraction(10_000)}))
    require(coefficient_branch["economic"] == Fraction(117, 250)
            and coefficient_branch["tax_at_crossing"] == 14_000, "Wrong tax branch on the pre-reserve NOI basis")
    for result, trial in ((combined, profile), (coefficient_branch, profile | {"floor": Fraction(10_000)})):
        q = result["economic"]
        def covers(realization):
            income_net = trial["slope"] * realization + trial["intercept"]
            floor, coefficient = trial["floor"], trial["tax_coefficient"]
            pre_reserve_noi = min(income_net - floor, income_net / (1 + coefficient))
            return pre_reserve_noi - trial["reserve"] >= trial["debt_service"]
        require(covers(q) and not covers(q - Fraction(1, 10_000)), "The tax calculation did not reproduce the crossing")
    unattainable = equilibrium(**profile, credit_loss=Fraction(3, 5), concessions=Fraction())
    require(unattainable["physical"] == Fraction(6, 5) and unattainable["physical_state"] == "not_attainable",
            "An infeasible physical occupancy was clipped")
    return dict(c14_combined=combined, c14_split=split, explicit_zero=zero,
                coefficient_tax_branch=coefficient_branch, physical_not_attainable=unattainable)


def price_checks():
    quarterly = (Fraction(1, 20), Fraction(1, 40))
    annual = [(1 + rate) ** 4 - 1 for rate in quarterly]
    rules = dict(yield_or_spread=(">=", Fraction(1, 10), "<", Fraction(2, 25)),
                 annual_irr=(">=", annual[0], "<", annual[1]),
                 equity_multiple=(">=", Fraction(5, 4), "<", Fraction(11, 10)),
                 equity_to_tdc=("<=", Fraction(2, 3), ">", Fraction(7, 10)))
    source = dict(price=100, closing_rate=Fraction(), tdc=500, applied_equity=300, debt=200,
                  contributions=320, distributions=600, net_flows=tuple(map(Fraction, (-300, -20, 0, 600))),
                  cap=None, cap_noi_basis=None, noi_before=85, noi_uw=80, asking=Fraction(180),
                  quarterly_irr_thresholds=quarterly)
    grid = (-100, 300, 1)
    zero_cost = price_screen(source, rules, grid)
    fixed = source | {"closing_rate": Fraction(1, 20)}
    with_cost = price_screen(fixed, rules, grid)
    require((zero_cost["pass_price"], with_cost["pass_price"]) == (200, 195), "C33 was ignored")
    require((zero_cost["before_fail"], with_cost["before_fail"]) == (266, 258), "FAIL boundary did not include C33")
    for result, rate in ((zero_cost, Fraction()), (with_cost, Fraction(1, 20))):
        boundary = result["pass_boundary"]
        require(boundary["below"]["state"] == boundary["at"]["state"] == "PASS"
                and boundary["above"]["state"] == "PENDING"
                and boundary["above"]["comparisons"]["equity_to_tdc"] == "PENDING"
                and all(state == "PASS" for key, state in boundary["above"]["comparisons"].items()
                        if key != "equity_to_tdc"), "Boundary did not identify the binding equity/TDC maximum")
        require(boundary["at"]["delta_tdc"] == (result["pass_price"] - source["price"]) * (1 + rate)
                and boundary["at"]["debt"] == source["debt"]
                and result["before_fail_boundary"]["above"]["state"] == "FAIL",
                "Boundary changed debt or failed to distinguish PASS from the review band")
    negative = price_screen(source, rules | {"equity_to_tdc": ("<=", Fraction(9, 20), ">", Fraction(12, 25))}, grid)
    require(negative["pass_price"] == -37 and negative["negative_pass_price"]
            and negative["asking_over_pass_price"] is None, "Negative RLV was clipped or used as a ratio")
    impossible = price_screen(source, rules | {"yield_or_spread": (">=", Fraction(1), "<", Fraction(9, 10))}, grid)
    require(impossible["state"] == "PENDING" and impossible["pass_price"] is None and impossible["before_fail"] is None
            and impossible["pass_boundary"]["state"] == "not_attainable_on_grid", "Unattainable RLV became zero")
    nonmonotone = price_screen(source | {"net_flows": tuple(map(Fraction, (-300, 100, -60, 520)))}, rules, grid)
    require(nonmonotone["blocker"] == "irr_monotonicity_unproven" and nonmonotone["pass_price"] is None,
            "Unproven TIR monotonicity produced a price")
    irr_rates = (Fraction(9, 50), Fraction(17, 100))
    irr_rules = rules | {"annual_irr": (">=", (1 + irr_rates[0]) ** 4 - 1, "<", (1 + irr_rates[1]) ** 4 - 1)}
    irr_active = price_screen(source | {"quarterly_irr_thresholds": irr_rates}, irr_rules, grid)
    boundary = irr_active["pass_boundary"]
    require(irr_active["pass_price"] == 148 and boundary["at"]["comparisons"]["annual_irr"] == "PASS"
            and boundary["above"]["comparisons"]["annual_irr"] == "PENDING", "Quarterly TIR hurdle did not bind")
    unknown = price_screen(source | {"cap": Fraction(7, 100)}, rules, grid)
    require(unknown["blocker"] == "cap_noi_basis_missing", "An unlabeled cap entered the RLV screen")
    spread_rules = rules | {"yield_or_spread": (">=", Fraction(800), "<", Fraction(700))}
    spread_after = price_screen(source | dict(cap=Fraction(7, 100), cap_noi_basis=AFTER_RESERVES), spread_rules, grid)
    spread_before = price_screen(source | dict(cap=Fraction(7, 100), cap_noi_basis=BEFORE_RESERVES), spread_rules, grid)
    require((spread_after["pass_price"], spread_before["pass_price"]) == (133, 166)
            and spread_after["yield_criterion"] == spread_before["yield_criterion"] == "spread_bps",
            "The price screen did not apply the comparable cap on its declared NOI basis")
    downside = price_screen(fixed | dict(noi_before=65, noi_uw=60, distributions=510,
                                         net_flows=tuple(map(Fraction, (-300, -20, 0, 510)))), rules, grid)
    require(downside["pass_price"] is not None and downside["pass_price"] < with_cost["pass_price"],
            "Informational Downside did not respond to lower receipts")
    return dict(base_c33_zero=zero_cost, base_c33_five_percent=with_cost, negative=negative,
                unattainable=impossible, monotonicity_blocked=nonmonotone, irr_binding=irr_active,
                cap_basis_missing=unknown, spread_after_reserves=spread_after, spread_before_reserves=spread_before,
                downside_informational=downside)


def verify(package):
    status = verify_package(package, current_revision_raw=CURRENT.read_bytes())
    require(status["vigencia"] == "VIGENTE", "The reference must replay from the D181 sources")
    result = json.loads((package / "results.json").read_bytes())
    check_oracle(result)
    require((package / "MiniUW_Resumen.pdf").read_bytes() ==
            (CASE.parents[1] / "docs/review/MiniUW_Informe_USD10_D181.pdf").read_bytes(), "Historical one-page output changed")
    return dict(status="passed", decision="PENDING", deployment_enabled=False, real_decisions_enabled=False,
                candidate_policy_status="PENDING", baseline_pdf_sha256=status["pdf_sha256"],
                performance=performance_checks(result["scenarios"], result["screening"]),
                occupancy=occupancy_checks(), fixed_debt_price=price_checks())


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d184-") as directory:
        package = args.package or Path(directory) / "D181"
        if args.package is None:
            write_package(CASE.read_bytes(), package, workbook_raw=BOOKS["Base"].read_bytes(),
                          downside_workbook_raw=BOOKS["Downside"].read_bytes(), current_revision_raw=CURRENT.read_bytes(),
                          plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())
        result = verify(package)
        print(json.dumps(result, sort_keys=True, default=rational))


if __name__ == "__main__":
    main()
