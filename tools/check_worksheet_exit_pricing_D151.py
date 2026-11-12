"""Verify the separate C66–C68 effects through capacity, sale and dated equity cash."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_property_tax_D150 import (
    BOOKS as TAX_BOOKS, CASE as TAX_CASE, CURRENT as TAX_CURRENT, PLAN, case_for as tax_case, workbook_values as tax_values,
)
from check_worksheet_replacement_reserve_D149 import flow
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_EXIT_PRICING_SCHEMA, encoded
from plan_refinance_D108 import VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD
from worksheet_exit_pricing_D151 import POLICY, RULES, SOURCE_ROLES
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-exit-pricing-D151.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D151.json"
BOOKS = {name: ROOT / f"templates/synthetic-exit-pricing-{name.lower()}-D151.xlsx" for name in SCENARIOS}
CELLS = ("C66", "C67", "C68")


def workbook_values(name, catalog):
    values = ("0.095", "0.0875", "0.04") if name == "Base" else ("0.115", "0.105", "0.07")
    return tax_values(name, catalog) | {cell: {"value": value} for cell, value in zip(CELLS, values, strict=True)}


def case_for(books, catalog, plan):
    case = tax_case(books, catalog, plan)
    case["schema"] = WORKBOOK_EXIT_PRICING_SCHEMA
    rent = case["rent_inputs"]
    del rent["exit_cap"]
    rent["valuation_and_sale"] = dict(policy=POLICY, source_ref="SYNTHETIC-D151-separate-cap-rates-and-gross-sale-costs",
        rules=RULES.copy(), currency="USD", scenarios={name: dict(inventory_declared_complete=True,
            **{role: f"SYNTHETIC-D151-{name}-{role}" for role in SOURCE_ROLES}) for name in SCENARIOS})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    plan = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items()) and
            CASE.read_bytes() == encoded(case_for(originals, catalog, plan)), "Fixture drift")
    baseline = run(TAX_CASE, TAX_BOOKS, TAX_CURRENT, temp / "D150", plan=PLAN)
    matching = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"], "Expected current documents and synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL",
            "Sale pricing could not replay from saved sources")
    for name, refi_cap, exit_cap, cost, limit, refi_date, sale_date in (
            ("Base", "0.095", "0.0875", "0.04", "DSCR", "2028-09-30", "2028-12-30"),
            ("Downside", "0.115", "0.105", "0.07", "LTV", "2029-03-30", "2029-06-30")):
        view, previous = matching["scenarios"][name], baseline["scenarios"][name]
        pricing = view["valuation_and_sale"]
        valuation_noi = amount(previous["noi_by_period"][VALUE_PERIOD]["noi"])
        forward_noi = amount(previous["noi_by_period"][FORWARD_PERIOD]["noi"])
        value = valuation_noi / Fraction(refi_cap)
        price = forward_noi / Fraction(exit_cap)
        cost_total = price * Fraction(cost)
        require(set(pricing["cell_sources"]) == set(CELLS)
                and pricing["refinance_date"] == refi_date and pricing["sale_date"] == pricing["forward_window"]["start"] == sale_date
                and [amount(pricing[key]) for key in ("refinance_noi", "forward_noi", "refinance_value", "gross_sale_price",
                    "sale_cost", "closing_cash_residual")] == [valuation_noi, forward_noi, value, price, cost_total, 0]
                and view["capacity"]["binding_limit_ids"] == [limit]
                and amount(view["capacity"]["capacity_limits"]["LTV"]) == value * Fraction(13, 20),
                "The distinct caps did not reach their valuation or capacity")
        sale_cost_run = pricing["sale_cost_run"]
        row, = sale_cost_run["cost_rows"]
        require(sale_cost_run["gross_price"]["source_ref"] == f"miniuw:synthetic-exit-value:{view['source_runs']['exit_value_sha256']}#/candidate_value"
                and row["claim"]["source_ref"] == pricing["cell_sources"]["C68"]
                and amount(row["computed_cost"]) == cost_total
                and pricing["sale_closing_sha256"] == view["source_runs"]["sale_closing_sha256"],
                "C68 did not bind a single cost to gross price and the same closing")
        cash, prior = view["cash_per_usd_10"], previous["cash_per_usd_10"]
        sale = (price - cost_total - amount(view["debt_principal_paid_at_sale"])
                + amount(view["replacement_reserve"]["released_at_sale"])) * NORMALIZER
        total = flow(prior, "net_refinance_distribution") + flow(prior, "operating_distribution") + sale
        require(events(cash, "contribution") == events(prior, "contribution")
                and events(cash, "distribution")[:2] == events(prior, "distribution")[:2]
                and events(cash, "distribution")[-1] == (sale_date, sale)
                and amount(cash["total_distributions"]) == total
                and amount(cash["unrecovered_after_sale"]) == max(0, amount(cash["total_contributions"]) - total),
                "Valuation was counted as cash, or sale costs, reserve or payoff were misapplied")

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
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D151-{name}")))
        return run(case_path, paths, revision, temp / name, plan=PLAN)

    old = matching["scenarios"]["Downside"]
    old_pricing, old_cash = old["valuation_and_sale"], old["cash_per_usd_10"]
    lower_refi_cap = variant("refi-cap-switch", {"C66": {"value": "0.10"}})["scenarios"]["Downside"]
    require(lower_refi_cap["capacity"]["binding_limit_ids"] == ["DSCR"]
            and amount(lower_refi_cap["valuation_and_sale"]["refinance_value"]) > amount(old_pricing["refinance_value"])
            and events(lower_refi_cap["cash_per_usd_10"], "distribution") == events(old_cash, "distribution"),
            "C66 failed to change the binding bank limit or altered the fixed selected loan")
    lower_exit_cap = variant("exit-cap-reprice", {"C67": {"value": "0.09"}})["scenarios"]["Downside"]
    repriced = lower_exit_cap["valuation_and_sale"]
    price_delta = amount(repriced["gross_sale_price"]) - amount(old_pricing["gross_sale_price"])
    require(price_delta > 0 and repriced["refinance_value"] == old_pricing["refinance_value"]
            and amount(repriced["sale_cost"]) - amount(old_pricing["sale_cost"]) == price_delta * Fraction(7, 100)
            and flow(lower_exit_cap["cash_per_usd_10"], "net_sale_distribution") - flow(old_cash, "net_sale_distribution")
            == price_delta * Fraction(93, 100) * NORMALIZER, "C67 failed to reprice gross sale and cost together")
    for rate in ("0", "0.09"):
        view = variant(f"sale-cost-{rate}", {"C68": {"value": rate}})["scenarios"]["Downside"]
        pricing = view["valuation_and_sale"]
        require(pricing["gross_sale_price"] == old_pricing["gross_sale_price"]
                and amount(pricing["sale_cost"]) == amount(old_pricing["gross_sale_price"]) * Fraction(rate)
                and flow(old_cash, "net_sale_distribution") - flow(view["cash_per_usd_10"], "net_sale_distribution")
                == (amount(pricing["sale_cost"]) - amount(old_pricing["sale_cost"])) * NORMALIZER,
                "C68 did not change the sale receipt once or ignored explicit zero")

    def pending(name, reason, *, keep_cash=False, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and any(reason in blocker for blocker in result["screening"]["simulation_blockers"])
                and (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                f"Missing gate or wrong cash availability for {name}")
        return result

    def sale_terms(case):
        return case["rent_inputs"]["valuation_and_sale"]["scenarios"]["Downside"]

    missing = pending("refi-cap-missing", "valuation_or_sale_rate_unconfirmed_or_out_of_range:C66", edits={"C66": "missing"})
    require(missing["scenarios"]["Base"] == matching["scenarios"]["Base"], "Downside gap withdrew Base cash")
    pending("zero-exit-cap", "valuation_or_sale_rate_unconfirmed_or_out_of_range:C67", edits={"C67": {"value": "0"}})
    pending("sale-cost-missing", "valuation_or_sale_rate_unconfirmed_or_out_of_range:C68", edits={"C68": "missing"})
    pending("cost-inventory-incomplete", "valuation_evidence_or_sale_cost_inventory_unconfirmed:C66-C68",
            patch=lambda case: sale_terms(case).update(inventory_declared_complete=False))
    pending("duplicate-costs", "valuation_evidence_or_sale_cost_inventory_unconfirmed:C66-C68",
            patch=lambda case: sale_terms(case).update(additional_closing_cost=rational(10000)))
    pending("sale-at-value-rule-missing", "valuation_evidence_or_sale_cost_inventory_unconfirmed:C66-C68",
            patch=lambda case: sale_terms(case).pop("sale_at_value_ref"))
    pending("capacity-reduced", "selected_principal_exceeds_declared_bank_capacity", edits={"C66": {"value": "0.12"}})
    pending("sale-cash-in", "cash_in_required_but_projected_equity_funding_assumption_missing", edits={"C67": {"value": "0.40"}})
    pending("criterion-missing", "criterion_record_missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    pending("stale-sale-cost", "workbooks_fingerprint_mismatch", keep_cash=True, edits={"C68": {"value": "0.09"}}, stale=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=15, pending_cases=10, worksheet_cells=3,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d151-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
