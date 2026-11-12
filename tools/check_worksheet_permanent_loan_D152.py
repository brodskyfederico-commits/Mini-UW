"""Verify C69–C72 through the permanent loan, refinance gates and USD 10 cash."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_exit_pricing_D151 import (
    BOOKS as SALE_BOOKS, CASE as SALE_CASE, CURRENT as SALE_CURRENT, PLAN, case_for as sale_case, workbook_values as sale_values,
)
from check_worksheet_replacement_reserve_D149 import flow
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_PERMANENT_LOAN_SCHEMA, encoded
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_permanent_loan_D152 import POLICY, RULES
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-permanent-loan-D152.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D152.json"
BOOKS = {name: ROOT / f"templates/synthetic-permanent-loan-{name.lower()}-D152.xlsx" for name in SCENARIOS}
CELLS = ("C69", "C70", "C71", "C72")


def workbook_values(name, catalog):
    values = ("0.05", "20", "0.65", "1.25") if name == "Base" else ("0.065", "11", "0.65", "1.30")
    return sale_values(name, catalog) | {cell: {"value": value} for cell, value in zip(CELLS, values, strict=True)}


def case_for(books, catalog, plan):
    case = sale_case(books, catalog, plan)
    case["schema"] = WORKBOOK_PERMANENT_LOAN_SCHEMA
    case["rent_inputs"]["permanent_loan"] = dict(policy=POLICY, source_ref="SYNTHETIC-D152-quarterly-loan-and-sizing-rules",
        rules=RULES.copy(), currency="USD", scenarios={name: dict(terms_ref=f"SYNTHETIC-D152-{name}-term-sheet",
            maturity_payments=8, maturity_ref=f"SYNTHETIC-D152-{name}-separate-two-year-maturity",
            other_limits_declared_complete=True, other_limits_ref=f"SYNTHETIC-D152-{name}-ltv-and-dscr-inventory")
            for name in SCENARIOS})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    plan = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items()) and
            CASE.read_bytes() == encoded(case_for(originals, catalog, plan)), "Fixture drift")
    baseline = run(SALE_CASE, SALE_BOOKS, SALE_CURRENT, temp / "D151", plan=PLAN)
    matching = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"], "Expected current documents and synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL",
            "Permanent loan could not replay from saved sources")
    for name, annual, years, dscr, binding, refi, sale, maturity in (
            ("Base", "0.05", 20, "1.25", "LTV", "2028-09-30", "2028-12-30", "2030-09-30"),
            ("Downside", "0.065", 11, "1.30", "DSCR", "2029-03-30", "2029-06-30", "2031-03-30")):
        view, previous = matching["scenarios"][name], baseline["scenarios"][name]
        loan, cap = view["permanent_loan"], view["capacity"]
        principal = 1400000
        rate = Fraction(annual) / 4
        unit = rate / (1 - (1 + rate) ** (-4 * years))
        installment = principal * unit
        interest = principal * rate
        payoff = principal - (installment - interest)
        first, last = loan["projected_schedule"][0], loan["projected_schedule"][-1]
        require(set(loan["cell_sources"]) == set(CELLS) and amount(loan["periodic_rate"]) == rate
                and loan["amortization_payments"] == 4 * years and loan["maturity_payments"] == 8
                and [loan["origination_date"], first["date"], last["date"], loan["maturity_date"]] == [refi, sale, maturity, maturity]
                and loan["payment_dates"] == view["project_calendar"]["payment_dates"]
                and amount(first["scheduled_service_due"]) == installment == amount(loan["regular_payment_due"])
                and amount(first["interest_due"]) == interest and amount(first["principal_due"]) == installment - interest
                and amount(first["closing_balance"]) == payoff and amount(first["balloon_due"]) == 0
                and amount(last["balloon_due"]) == amount(last["closing_balance"]) > 0
                and amount(view["debt_principal_paid_at_sale"]) == payoff, "C69/C70, maturity and payoff did not reconcile")
        ltv_limit = amount(view["valuation_and_sale"]["refinance_value"]) * Fraction(13, 20)
        dscr_limit = amount(cap["bank_noi"]) / (Fraction(dscr) * 4 * unit)
        require(cap["binding_limit_ids"] == [binding] and amount(cap["selected_principal"]) == principal
                and amount(loan["annual_sizing_service"]) == installment * 4
                and amount(cap["capacity_limits"]["LTV"]) == ltv_limit and amount(cap["capacity_limits"]["DSCR"]) == dscr_limit
                and amount(cap["maximum_principal_capacity"]) == min(ltv_limit, dscr_limit), "C71/C72 did not feed independent bank limits")
        cash, prior = view["cash_per_usd_10"], previous["cash_per_usd_10"]
        op_delta = (amount(previous["dated_debt_service"]["scheduled_service_due"]) - installment) * NORMALIZER
        sale_delta = (amount(previous["debt_principal_paid_at_sale"]) - payoff) * NORMALIZER
        total = amount(prior["total_distributions"]) + op_delta + sale_delta
        require(events(cash, "contribution") == events(prior, "contribution")
                and flow(cash, "net_refinance_distribution") == flow(prior, "net_refinance_distribution")
                and flow(cash, "operating_distribution") - flow(prior, "operating_distribution") == op_delta
                and flow(cash, "net_sale_distribution") - flow(prior, "net_sale_distribution") == sale_delta
                and amount(cash["total_distributions"]) == total
                and amount(cash["unrecovered_after_sale"]) == max(0, amount(cash["total_contributions"]) - total),
                "A dated payment, sizing equivalent or payoff was counted incorrectly in cash")

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
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D152-{name}")))
        return run(case_path, paths, revision, temp / name, plan=PLAN)

    def loan_terms(case):
        return case["rent_inputs"]["permanent_loan"]["scenarios"]["Downside"]

    old = matching["scenarios"]["Downside"]
    old_cash = old["cash_per_usd_10"]
    zero = variant("zero-rate", {"C69": {"value": "0"}})["scenarios"]["Downside"]
    require(amount(zero["dated_debt_service"]["interest_due"]) == 0
            and amount(zero["permanent_loan"]["regular_payment_due"]) == Fraction(1400000, 44)
            and amount(zero["cash_per_usd_10"]["total_distributions"]) - amount(old_cash["total_distributions"]) == 22750 * NORMALIZER,
            "Explicit zero C69 did not reach the principal-only schedule")
    longer = variant("longer-amortization", {"C70": {"value": "12"}})["scenarios"]["Downside"]
    require(longer["permanent_loan"]["amortization_payments"] == 48
            and longer["permanent_loan"]["maturity_date"] == old["permanent_loan"]["maturity_date"]
            and amount(longer["permanent_loan"]["regular_payment_due"]) < amount(old["permanent_loan"]["regular_payment_due"])
            and longer["capacity"]["binding_limit_ids"] == ["LTV"]
            and longer["cash_per_usd_10"]["total_distributions"] == old_cash["total_distributions"],
            "C70 did not reprice the schedule or changed the distinct maturity")
    for cell, value in (("C71", "0.64"), ("C72", "1.25")):
        alternate = variant(f"limit-switch-{cell}", {cell: {"value": value}})["scenarios"]["Downside"]
        require(alternate["capacity"]["binding_limit_ids"] == ["LTV"]
                and events(alternate["cash_per_usd_10"], "distribution") == events(old_cash, "distribution"),
                f"{cell} did not change the limit independently of the fixed selected principal")
    exact = amount(old["valuation_and_sale"]["refinance_value"]) * Fraction(16, 25)
    equality = variant("at-capacity", {"C71": {"value": "0.64"}}, patch=lambda case: case["rent_inputs"].update(
        requested_principal=rational(exact)))["scenarios"]["Downside"]
    require(amount(equality["capacity"]["selected_principal"]) == amount(equality["capacity"]["maximum_principal_capacity"]) == exact
            and equality["cash_per_usd_10"] is not None, "A loan equal to the limit was blocked")
    maturity = variant("longer-maturity", patch=lambda case: loan_terms(case).update(maturity_payments=12))["scenarios"]["Downside"]
    require(maturity["permanent_loan"]["maturity_date"] == "2032-03-30"
            and len(maturity["project_calendar"]["payment_dates"]) == 12
            and maturity["permanent_loan"]["regular_payment_due"] == old["permanent_loan"]["regular_payment_due"],
            "The separate maturity did not update the calendar or changed amortization")

    def pending(name, reason, *, keep_cash=False, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and any(reason in blocker for blocker in result["screening"]["simulation_blockers"])
                and (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                f"Missing gate or wrong cash availability for {name}")
        return result

    for cell in CELLS:
        missing = pending(f"missing-{cell}", f"permanent_loan_input_unconfirmed_or_negative:{cell}", edits={cell: "missing"})
        require(missing["scenarios"]["Base"] == matching["scenarios"]["Base"], "Downside loan gap withdrew Base cash")
    pending("missing-maturity", "permanent_loan_terms_or_limit_inventory_unconfirmed:C69-C72",
            patch=lambda case: loan_terms(case).pop("maturity_payments"))
    pending("unsupported-frequency", "permanent_loan_rate_or_schedule_policy_unconfirmed:C69-C72",
            patch=lambda case: case["rent_inputs"]["permanent_loan"]["rules"].update(payments_per_year=12))
    for cell, value, binding in (("C71", "0.63", "LTV"), ("C72", "1.34", "DSCR")):
        blocked = pending(f"over-{binding}", "selected_principal_exceeds_declared_bank_capacity", edits={cell: {"value": value}})
        view = blocked["scenarios"]["Downside"]
        require(view["capacity"]["binding_limit_ids"] == [binding]
                and view["construction_refinance"]["net_equity_distribution"] is None, "Capacity released a refinance receipt")
    pending("criterion-missing", "criterion_record_missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    pending("stale-amortization", "workbooks_fingerprint_mismatch", keep_cash=True, edits={"C70": {"value": "12"}}, stale=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=17, pending_cases=10, worksheet_cells=4,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d152-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
