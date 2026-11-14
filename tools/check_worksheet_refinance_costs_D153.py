"""Verify C73–C74 through the refinance waterfall, restricted cash and USD 10 flows."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_permanent_loan_D152 import (
    BOOKS as LOAN_BOOKS, CASE as LOAN_CASE, CURRENT as LOAN_CURRENT, PLAN, case_for as loan_case, workbook_values as loan_values,
)
from check_worksheet_replacement_reserve_D149 import flow
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_REFINANCE_COSTS_SCHEMA, encoded
from worksheet_calendar_routes_D199 import route_cash
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_refinance_costs_D153 import POLICY, RULES
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-refinance-costs-D153.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D153.json"
BOOKS = {name: ROOT / f"templates/synthetic-refinance-costs-{name.lower()}-D153.xlsx" for name in SCENARIOS}


def workbook_values(name, catalog):
    cost, reserve = ("0.025", "1800") if name == "Base" else ("0.035", "3000")
    return loan_values(name, catalog) | {"C73": {"value": cost}, "C74": {"value": reserve}}


def case_for(books, catalog, plan):
    case = loan_case(books, catalog, plan)
    case["schema"] = WORKBOOK_REFINANCE_COSTS_SCHEMA
    case["rent_inputs"]["refinance_costs"] = dict(policy=POLICY, source_ref="SYNTHETIC-D153-refinance-funding-and-reserve-rules",
        rules=RULES.copy(), currency="USD", scenarios={name: dict(cost_inventory_declared_complete=True,
            cost_inventory_ref=f"SYNTHETIC-D153-{name}-aggregate-refinance-charges",
            eligible_units=26, reserve_eligibility_ref=f"SYNTHETIC-D153-{name}-reserve-eligible-units",
            sale_release_fraction=rational(release), sale_settlement_ref=f"SYNTHETIC-D153-{name}-permanent-reserve-disposition")
            for name, release in (("Base", 1), ("Downside", Fraction(1, 2)))})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    plan = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items()) and
            CASE.read_bytes() == encoded(case_for(originals, catalog, plan)), "Fixture drift")
    baseline = run(LOAN_CASE, LOAN_BOOKS, LOAN_CURRENT, temp / "D152", plan=PLAN)
    matching = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"], "Expected current documents and synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL",
            "The refinance closing could not replay from the saved sources")
    for name, fee, deposit, release, payoff, refi_date, sale_date in (
            ("Base", 35000, 46800, 46800, 635000, "2028-09-30", "2028-12-30"),
            ("Downside", 49000, 78000, 39000, 686000, "2029-03-30", "2029-06-30")):
        view, previous = matching["scenarios"][name], baseline["scenarios"][name]
        closing, permanent, replacement = (view[key] for key in ("construction_refinance", "permanent_reserve", "replacement_reserve"))
        net = 1400000 - payoff - fee - deposit
        require(closing["date"] == permanent["funding_date"] == refi_date and permanent["sale_date"] == sale_date
                and set(closing["terms"]["cell_sources"]) == {"C73", "C74"}
                and [amount(closing[key]) for key in ("gross_proceeds", "prior_principal_paid", "closing_fee", "permanent_reserve_deposit",
                    "closing_restricted_cash", "net_equity_distribution", "closing_cash_residual", "projected_cash_in_required")]
                == [1400000, payoff, fee, deposit, deposit, net, 0, 0], "Refinance sources and uses did not reconcile")
        require(permanent["refinance_closing_sha256"] == closing["closing_run_sha256"]
                and permanent["sale_closing_sha256"] == view["source_runs"]["sale_closing_sha256"]
                and [amount(permanent[key]) for key in ("opening_at_sale", "released_at_sale", "transferred_restricted_to_buyer", "sale_cash_residual")]
                == [deposit, release, deposit - release, 0], "Refinance reserve did not carry through sale")
        for total_key, replacement_key, permanent_part in (
                ("total_restricted_before_sale", "restricted_before_sale", deposit),
                ("total_released_at_sale", "released_at_sale", release),
                ("total_restricted_transferred_to_buyer", "transferred_restricted_to_buyer", deposit - release)):
            original = previous["replacement_reserve"][replacement_key]
            require(replacement[replacement_key] == original and amount(permanent[total_key]) == amount(original) + permanent_part,
                    "C74 was combined incorrectly with C60")
        cash, prior = view["cash_per_usd_10"], previous["cash_per_usd_10"]
        expected_total = amount(prior["total_distributions"]) - (fee - 28000 + deposit - release) * NORMALIZER
        require(events(cash, "contribution") == events(prior, "contribution")
                and flow(cash, "net_refinance_distribution") == net * NORMALIZER
                and flow(cash, "operating_distribution") == flow(prior, "operating_distribution")
                and flow(cash, "net_sale_distribution") - flow(prior, "net_sale_distribution") == release * NORMALIZER
                and amount(cash["total_distributions"]) == expected_total
                and amount(cash["unrecovered_after_sale"]) == max(0, amount(cash["total_contributions"]) - expected_total),
                "Refinance cost, reserve or release was double-counted in cash")

    def variant(name, edits=None, patch=None, *, stale=False):
        books = originals.copy()
        if edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        case = case_for(books, catalog, plan)
        if patch:
            patch(case)
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, source in books.items():
            paths[scenario].write_bytes(source)
        case_path, revision = (temp / f"{name}-{suffix}.json" for suffix in ("case", "revision"))
        case_path.write_bytes(encoded(case))
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D153-{name}")))
        return run(case_path, paths, revision, temp / name, plan=PLAN)

    def closing_terms(case):
        return case["rent_inputs"]["refinance_costs"]["scenarios"]["Downside"]

    old = matching["scenarios"]["Downside"]
    old_cash = old["cash_per_usd_10"]
    zero_cost = variant("zero-fee", {"C73": {"value": "0"}})["scenarios"]["Downside"]
    require(amount(zero_cost["construction_refinance"]["closing_fee"]) == 0
            and flow(zero_cost["cash_per_usd_10"], "net_refinance_distribution") - flow(old_cash, "net_refinance_distribution") == 49000 * NORMALIZER,
            "Explicit zero C73 did not reach the closing")
    zero_reserve = variant("zero-reserve", {"C74": {"value": "0"}})["scenarios"]["Downside"]
    require(amount(zero_reserve["permanent_reserve"]["opening_at_sale"]) == 0
            and flow(zero_reserve["cash_per_usd_10"], "net_refinance_distribution") - flow(old_cash, "net_refinance_distribution") == 78000 * NORMALIZER
            and flow(old_cash, "net_sale_distribution") - flow(zero_reserve["cash_per_usd_10"], "net_sale_distribution") == 39000 * NORMALIZER,
            "Explicit zero C74 changed the wrong flows")
    fewer = variant("fewer-eligible-units", patch=lambda case: closing_terms(case).update(eligible_units=25))["scenarios"]["Downside"]
    require(amount(fewer["construction_refinance"]["permanent_reserve_deposit"]) == 75000, "C74 ignored the eligible count")
    for fraction in (0, 1):
        view = variant(f"sale-release-{fraction}", patch=lambda case: closing_terms(case).update(
            sale_release_fraction=rational(fraction)))["scenarios"]["Downside"]
        cash = view["cash_per_usd_10"]
        require(amount(view["permanent_reserve"]["released_at_sale"]) == 78000 * fraction
                and flow(cash, "net_refinance_distribution") == flow(old_cash, "net_refinance_distribution")
                and flow(cash, "net_sale_distribution") - flow(old_cash, "net_sale_distribution") == (78000 * fraction - 39000) * NORMALIZER,
                "Sale disposition did not move only the sale receipt")
    exact = variant("zero-net-refinance", {"C73": {"value": "0.01"}, "C74": {"value": "28000"}},
                    patch=lambda case: closing_terms(case).update(eligible_units=25))["scenarios"]["Downside"]
    require(amount(exact["construction_refinance"]["net_equity_distribution"]) == 0
            and flow(exact["cash_per_usd_10"], "net_refinance_distribution") == 0
            and events(exact["cash_per_usd_10"], "contribution") == events(old_cash, "contribution"),
            "A zero closing residual was treated as a missing amount or generated a contribution")

    def pending(name, reason, *, keep_cash=False, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and any(reason in blocker for blocker in result["screening"]["simulation_blockers"])
                and (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                f"Missing gate or wrong cash availability for {name}")
        return result

    for cell in ("C73", "C74"):
        missing = pending(f"missing-{cell}", f"refinance_cost_or_reserve_input_unconfirmed_or_out_of_range:{cell}", edits={cell: "missing"})
        require(missing["scenarios"]["Base"] == matching["scenarios"]["Base"], "Downside gap withdrew Base cash")
    pending("fee-basis-missing", "refinance_cost_or_reserve_scope_unconfirmed:C73-C74",
            patch=lambda case: case["rent_inputs"]["refinance_costs"]["rules"].pop("cost_basis"))
    pending("units-missing", "permanent_reserve_eligible_units_unconfirmed:C74",
            patch=lambda case: closing_terms(case).update(eligible_units=None))
    pending("disposition-missing", "refinance_cost_inventory_or_sale_disposition_unconfirmed:C73-C74",
            patch=lambda case: closing_terms(case).pop("sale_settlement_ref"))
    shortfall = pending("cash-in-required", "cash_in_required_but_projected_equity_funding_assumption_missing",
                        edits={"C74": {"value": "30000"}})["scenarios"]["Downside"]
    require(amount(shortfall["construction_refinance"]["projected_cash_in_required"]) == 115000
            and shortfall["construction_refinance"]["net_equity_distribution"] is None, "Closing invented shortfall funding")
    capacity = pending("over-capacity", "selected_principal_exceeds_declared_bank_capacity",
                       edits={"C71": {"value": "0.63"}})["scenarios"]["Downside"]
    require(capacity["construction_refinance"]["net_equity_distribution"] is None and "permanent_reserve" not in capacity,
            "A blocked draw supplied a receipt or a reserve for sale")
    sale_terms = dict(route="sell_without_refinance", source_ref="SYNTHETIC-D153-sale-only",
                      construction_tax=dict(applicability="no_incremental_tax_in_variant",
                                            source_ref="SYNTHETIC-D153-no-additional-levy"))
    separate = pending("separate-exit", "selected_principal_exceeds_declared_bank_capacity",
                       edits={"C71": {"value": "0.63"}}, patch=lambda case: case["rent_inputs"].update(
                           calendar_checks={"Downside": {"sell_without_refinance": sale_terms}}))
    candidate = route_cash(separate["scenarios"]["Downside"], sale_terms)
    control = route_cash(old, sale_terms)
    require(candidate["state"] == "calculated_synthetic" and candidate == control
            and candidate["sale"]["principal_paid"] == 686000
            and all(event["stage"] != "refinance" for event in candidate["cash_per_usd_10"]["events"]),
            "Refinance capacity rejected an independently supported sale")
    pending("criterion-missing", "criterion_record_missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    pending("stale-refinance-fee", "workbooks_fingerprint_mismatch", keep_cash=True, edits={"C73": {"value": "0.04"}}, stale=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=17, pending_cases=10, worksheet_cells=2,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d153-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
