"""Verify dated C75–C76 growth from the native worksheet through NOI, closing and USD 10 cash."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_refinance_costs_D153 import (
    BOOKS as PREVIOUS_BOOKS, CASE as PREVIOUS_CASE, CURRENT as PREVIOUS_CURRENT, PLAN,
    case_for as refinance_case, workbook_values as refinance_values,
)
from check_worksheet_rental_inputs_D140 import run
from check_worksheet_replacement_reserve_D149 import flow
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_GROWTH_SCHEMA, encoded
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_commercial_inputs_D141 import commercial_income
from worksheet_growth_D154 import POLICY, RULES, project_window
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_project_calendar_D145 import offset
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-growth-D154.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D154.json"
BOOKS = {name: ROOT / f"templates/synthetic-growth-{name.lower()}-D154.xlsx" for name in SCENARIOS}
RATES = {"Base": ("0.03", "0.02"), "Downside": ("-0.005", "0.03")}
GROWING_EXPENSE_IDS = {"fixed_opex", "controllable_excluding_utilities", "insurance"}


def workbook_values(name, catalog):
    rent, expenses = RATES[name]
    return refinance_values(name, catalog) | {"C75": {"value": rent}, "C76": {"value": expenses}}


def case_for(books, catalog, plan):
    case = refinance_case(books, catalog, plan)
    case["schema"] = WORKBOOK_GROWTH_SCHEMA
    case["rent_inputs"]["growth"] = dict(policy=POLICY, rules=RULES.copy(),
        source_ref="SYNTHETIC-D154-growth-convention",
        scenarios={name: dict(scope_ref=f"SYNTHETIC-D154-{name}-growth-scope") for name in SCENARIOS})
    return case


def verify_period(projected, before, period, rent_rate, expense_rate):
    count = {OPERATING_PERIOD: 0, BANK_PERIOD: 9, VALUE_PERIOD: 9, FORWARD_PERIOD: 12}[period]
    r = 1 + rent_rate * Fraction(count, 12)
    e = 1 + expense_rate * Fraction(count, 12)
    growth = projected["growth"]
    require(growth["completed_anniversaries_by_month"] == [0] * (12 - count) + [1] * count
            and amount(growth["rent_factor"]) == r and amount(growth["expense_factor"]) == e,
            "The projected window crossed the annual boundary incorrectly")
    effective = amount(before["effective_rent"]) * r
    other = amount(before["other_income"])
    require(amount(projected["gross_rent"]) == amount(before["gross_rent"]) * r
            and amount(projected["effective_rent"]) == effective and amount(projected["other_income"]) == other,
            "C75 changed a non-rent basis or failed to reach residential rent")
    require(projected["commercial"]["recognized_months"] == before["commercial"]["recognized_months"]
            and (count == 0 or before["commercial"]["recognized_months"] == 12)
            and amount(projected["commercial"]["net"]) == amount(before["commercial"]["net"]) * r,
            "C75 changed the commercial lease start or missed its recognized rent")
    original = {item["item_id"]: amount(item["amount"]) for item in before["operating_costs"]["expense_rows"]}
    expected = {key: value * (r if key == "management" else e if key in GROWING_EXPENSE_IDS
                             or key.startswith("SYNTHETIC-utilities-") else 1) for key, value in original.items()}
    costs = projected["operating_costs"]
    require({item["item_id"]: amount(item["amount"]) for item in costs["expense_rows"]} == expected
            and amount(costs["management_eligible_egi"]) == effective + other
            and amount(costs["management_fee"]) == expected["management"] + expected["management_other_income"]
            and amount(costs["controllable_total"]) == amount(costs["controllable_excluding_utilities"])
                + amount(projected["utilities"]["annual_total"]), "Costs escalated outside their declared scope or double counted")
    pre_tax = effective + other + amount(projected["commercial"]["net"]) - sum(expected.values())
    taxes = projected["property_tax"]
    floor = amount(before["property_tax"]["floor"])
    coefficient = amount(before["property_tax"]["coefficient"])
    assessed_tax = coefficient * pre_tax / (1 + coefficient)
    tax = max(floor, assessed_tax)
    require(amount(projected["operating_expenses_excluding_tax"]) == sum(expected.values())
            and amount(taxes["floor"]) == floor and amount(taxes["annual_tax"]) == tax
            and amount(taxes["operating_before_tax"]) == pre_tax and amount(taxes["equation_residual"]) == 0
            and amount(projected["noi"]) == pre_tax - tax, "NOI or tax did not reconcile from projected components")


def verify_cash(view, previous):
    cash, prior = view["cash_per_usd_10"], previous["cash_per_usd_10"]
    pricing = view["valuation_and_sale"]
    noi = view["noi_by_period"]
    debt = view["permanent_loan"]
    bank = amount(noi[BANK_PERIOD]["noi"])
    value = amount(noi[VALUE_PERIOD]["noi"]) / amount(pricing["refinance_cap"])
    ltv = value * amount(debt["maximum_ltv"])
    dscr = bank * amount(view["capacity"]["selected_principal"]) / (amount(debt["minimum_dscr"])
                                                                    * amount(debt["annual_sizing_service"]))
    require(amount(pricing["refinance_value"]) == value and amount(view["capacity"]["maximum_principal_capacity"])
            == min(ltv, dscr), "Projected bank and valuation NOI were not used by the capacity guard")
    sale = amount(noi[FORWARD_PERIOD]["noi"]) / amount(pricing["exit_cap"])
    difference = sale - amount(previous["valuation_and_sale"]["gross_sale_price"])
    net_delta = difference * (1 - amount(pricing["sale_cost_fraction"])) * NORMALIZER
    require(amount(pricing["gross_sale_price"]) == sale and amount(pricing["sale_cost"]) == sale * amount(pricing["sale_cost_fraction"])
            and events(cash, "contribution") == events(prior, "contribution")
            and flow(cash, "net_refinance_distribution") == flow(prior, "net_refinance_distribution")
            and flow(cash, "operating_distribution") == flow(prior, "operating_distribution")
            and flow(cash, "net_sale_distribution") - flow(prior, "net_sale_distribution") == net_delta
            and amount(cash["total_distributions"]) - amount(prior["total_distributions"]) == net_delta
            and amount(cash["unrecovered_after_sale"]) == max(0, amount(cash["total_contributions"]) - amount(cash["total_distributions"]))
            and events(cash, "distribution")[-1][0] == pricing["sale_date"],
            "Forward NOI was used in the wrong cash flow or the USD 10 basis drifted")


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in SCENARIOS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    plan = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items())
            and CASE.read_bytes() == encoded(case_for(originals, catalog, plan)), "Fixture drift")
    baseline = run(PREVIOUS_CASE, PREVIOUS_BOOKS, PREVIOUS_CURRENT, temp / "D153", plan=PLAN)
    current = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    require(current["simulation_result"] == "FAIL" and not current["revision_review"]["blockers"]
            and not current["local_review"]["blockers"], "Complete synthetic growth pilot did not compute")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL",
            "Saved growth pilot failed its evidence replay")

    def compare(result, rates, names=SCENARIOS):
        for name in names:
            view, prior = result["scenarios"][name], baseline["scenarios"][name]
            rent, expense = map(Fraction, rates[name])
            require(set(view["growth_terms"]["cell_sources"]) == {"C75", "C76"}
                    and view["growth_terms"]["anchor"] == view["project_calendar"]["stabilization_date"],
                    "C75 or C76 is unbound or the growth anchor drifted")
            for period in (OPERATING_PERIOD, BANK_PERIOD, VALUE_PERIOD, FORWARD_PERIOD):
                verify_period(view["noi_by_period"][period], prior["noi_by_period"][period], period, rent, expense)
            verify_cash(view, prior)

    compare(current, RATES)

    def variant(label, edits=None, patch=None, *, stale=False):
        books = originals.copy()
        for name, replacements in (edits or {}).items():
            books[name] = native_workbook(values[name] | replacements)
        case = case_for(books, catalog, plan)
        if patch:
            patch(case)
        paths = {name: temp / f"{label}-{name}.xlsx" for name in SCENARIOS}
        for name, source in books.items():
            paths[name].write_bytes(source)
        case_path, revision = (temp / f"{label}-{suffix}.json" for suffix in ("case", "revision"))
        case_path.write_bytes(encoded(case))
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D154-{label}")))
        return run(case_path, paths, revision, temp / label, plan=PLAN)

    compare(variant("zero", {name: {"C75": {"value": "0"}, "C76": {"value": "0"}} for name in SCENARIOS}),
            {name: ("0", "0") for name in SCENARIOS})
    compare(variant("only-rents", {"Base": {"C76": {"value": "0"}}}), {"Base": ("0.03", "0")}, ("Base",))
    compare(variant("only-expenses", {"Base": {"C75": {"value": "0"}}}), {"Base": ("0", "0.02")}, ("Base",))

    def pending(label, blocker, *, keep_cash=False, **kwargs):
        result = variant(label, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and any(blocker in item for item in result["screening"]["simulation_blockers"])
                and (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                f"Wrong decision or cash availability for {label}")
        return result

    for cell in ("C75", "C76"):
        blocked = pending(f"missing-{cell}", f"growth_rate_unconfirmed_or_outside_positive_factor_profile:{cell}",
                          edits={"Downside": {cell: "missing"}})
        base = blocked["scenarios"]["Base"]
        require(base == current["scenarios"]["Base"], "A Downside growth gap withdrew Base cash")
    pending("invalid-factor", "growth_rate_unconfirmed_or_outside_positive_factor_profile:C75",
            edits={"Downside": {"C75": {"value": "-1"}}})
    pending("missing-convention", "growth_scope_or_convention_unconfirmed",
            patch=lambda case: case["rent_inputs"]["growth"]["rules"].pop("convention"))
    pending("missing-scenario-scope", "scenario_growth_scope_unconfirmed",
            patch=lambda case: case["rent_inputs"]["growth"]["scenarios"].pop("Downside"))
    capacity = pending("growth-breaks-capacity", "selected_principal_exceeds_declared_bank_capacity",
                       edits={"Downside": {"C75": {"value": "-0.12"}}})["scenarios"]["Downside"]
    require(capacity["construction_refinance"]["net_equity_distribution"] is None
            and amount(capacity["capacity"]["maximum_principal_capacity"]) < 1400000,
            "A capacity breach still exported a refinance receipt")
    pending("stale-growth", "workbooks_fingerprint_mismatch", keep_cash=True, stale=True,
            edits={"Downside": {"C76": {"value": "0.04"}}})
    pending("criterion-missing", "criterion_record_missing", keep_cash=True, patch=lambda case: case["rules"].pop())

    scope = current["scenarios"]["Base"]["growth_terms"]
    anchor = date.fromisoformat(scope["anchor"])
    later = project_window(scope, offset(anchor, 21).isoformat())
    require(amount(later["rent_factor"]) == (Fraction("1.03") * 3 + Fraction("1.03") ** 2 * 9) / 12,
            "Growth was not compounded across multiple anniversaries")
    crossing = project_window(scope, offset(anchor, 9).isoformat())
    commercial = commercial_income(dict(lease_start=offset(anchor, 11).isoformat(), vacancy=rational(0), non_recoverable=rational(0),
        uses=dict(retail=dict(area=rational(100), rate=rational(12)))), BANK_PERIOD, window_start=crossing["window_start"],
        rent_month_factors=crossing["rent_month_factors"])
    require(commercial["recognized_months"] == 10 and amount(commercial["net"]) == 100 * (1 + 9 * Fraction("1.03")),
            "Commercial growth included unleased months or weighted the wrong months")
    return dict(status="passed", decision="PENDING", full_workbook_cases=12, pending_cases=8,
                worksheet_cells=2, pdf_sha256=current["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d154-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
