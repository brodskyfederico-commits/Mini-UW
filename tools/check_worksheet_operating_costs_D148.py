"""Replay worksheet operating costs through documented NOI, loan capacity and USD 10 cash."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_documented_finance_D147 import (
    BOOKS as DOC_BOOKS, CASE as DOC_CASE, CURRENT as DOC_CURRENT, PLAN, case_for as documented_case,
    workbook_values as documented_values,
)
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_OPERATING_COSTS_SCHEMA, encoded
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_operating_costs_D148 import POLICY, RULES
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-operating-costs-D148.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D148.json"
BOOKS = {name: ROOT / f"templates/synthetic-operating-costs-{name.lower()}-D148.xlsx" for name in SCENARIOS}
CELLS = ("C57", "C58", "C59")


def workbook_values(name, catalog):
    rates = ("1300", "0.05", "300") if name == "Base" else ("1600", "0.06", "550")
    return documented_values(name, catalog) | {cell: {"value": rate} for cell, rate in zip(CELLS, rates, strict=True)}


def case_for(books, catalog, plan):
    case = documented_case(books, catalog, plan)
    case["schema"] = WORKBOOK_OPERATING_COSTS_SCHEMA
    case["local_sources"]["finance_binding"]["source_ref"] = "SYNTHETIC-D148-GBA-and-GC-scope"
    inputs = case["rent_inputs"]
    inputs["policy"].update(source_ref="SYNTHETIC-D148-effective-residential-rent-and-other-egi",
                            other_income_basis="explicit_eligible_units_included_in_residential_management")
    expenses = inputs["annual_expenses"]
    del expenses["unit_opex"], expenses["management"]
    expenses["source_ref"] = "SYNTHETIC-D148-separate-fixed-building-costs-and-tax"
    inputs["operating_costs"] = dict(policy=POLICY, source_ref="SYNTHETIC-D148-cost-coverage-and-allocation", currency="USD",
        rules=RULES.copy(), scenarios={name: dict(controllable_units=26, insured_units=26,
             controllable_units_ref=f"SYNTHETIC-D148-{name}-controllable-units",
             insurance_coverage_ref=f"SYNTHETIC-D148-{name}-insured-unit-schedule") for name in SCENARIOS})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    raw = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items()) and
            CASE.read_bytes() == encoded(case_for(originals, catalog, raw)), "Fixture drift")
    baseline = run(DOC_CASE, DOC_BOOKS, DOC_CURRENT, temp / "D147", plan=PLAN)
    matching = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"], "Expected current documents and synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL",
            "Operating costs did not replay from the saved documents")
    for name, total, utility, insurance, fee_rate, op_noi, bank_noi, forward_noi in (
            ("Base", 33800, 15720, 7800, Fraction("0.05"), Fraction("439839.10"), Fraction("445795.60"), Fraction("470191.60")),
            ("Downside", 41600, 20280, 14300, Fraction("0.06"), Fraction("262452.20"), Fraction("272231.72"), Fraction("293562.20"))):
        view = matching["scenarios"][name]
        for period, noi in ((OPERATING_PERIOD, op_noi), (BANK_PERIOD, bank_noi), (VALUE_PERIOD, forward_noi), (FORWARD_PERIOD, forward_noi)):
            row = view["noi_by_period"][period]
            costs = row["operating_costs"]
            egi = amount(row["effective_rent"]) + amount(row["other_income"])
            require(set(costs["cell_sources"]) == set(CELLS)
                    and [amount(costs[key]) for key in ("controllable_total", "utilities_in_controllable", "controllable_excluding_utilities",
                                                       "insurance_total", "management_eligible_egi", "management_fee")]
                    == [total, utility, total - utility, insurance, egi, egi * fee_rate]
                    and amount(row["operating_expenses_excluding_tax"]) == total + insurance + egi * fee_rate + 10800
                    and amount(row["noi"]) == noi, "Cost scope, residential EGI or NOI differs")
        cash = view["cash_per_usd_10"]
        previous = baseline["scenarios"][name]["cash_per_usd_10"]
        old_draw = amount(view["construction_refinance"]["prior_principal_paid"])
        gross = (op_noi + forward_noi * Fraction(95, 9) - 45500 - old_draw) * NORMALIZER
        require(events(cash, "contribution") == events(previous, "contribution")
                and events(cash, "distribution")[0] == events(previous, "distribution")[0]
                and amount(view["capacity"]["bank_noi"]) == bank_noi
                and amount(cash["total_distributions"]) == gross
                and amount(cash["unrecovered_after_sale"]) == max(0, amount(cash["total_contributions"]) - gross),
                "Dated cash or bank NOI did not use the verified costs")

    def variant(name, edits=None, patch=None, *, stale=False):
        books = originals.copy()
        if edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        case = case_for(books, catalog, raw)
        if patch:
            patch(case)
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, source in books.items():
            paths[scenario].write_bytes(source)
        case_path, revision = (temp / f"{name}-{suffix}.json" for suffix in ("case", "revision"))
        case_path.write_bytes(encoded(case))
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D148-{name}")))
        return run(case_path, paths, revision, temp / name, plan=PLAN)

    old = matching["scenarios"]["Downside"]
    for cell, value, expected_decrease in (("C57", "1700", 2600), ("C58", "0", Fraction("-20782.80")), ("C59", "650", 2600)):
        view = variant(f"changed-{cell}", {cell: {"value": value}})["scenarios"]["Downside"]
        require(amount(old["noi_by_period"][OPERATING_PERIOD]["noi"]) - amount(view["noi_by_period"][OPERATING_PERIOD]["noi"]) == expected_decrease
                and amount(old["cash_per_usd_10"]["total_distributions"]) - amount(view["cash_per_usd_10"]["total_distributions"])
                == expected_decrease * Fraction(104, 9) * NORMALIZER, f"Incorrect cash sensitivity from {cell}")
    utility = variant("utility-within-budget", {"C25": {"value": "55"}})["scenarios"]["Downside"]
    costs = utility["noi_by_period"][OPERATING_PERIOD]["operating_costs"]
    require(amount(costs["utilities_in_controllable"]) == 20760 and amount(costs["controllable_excluding_utilities"]) == 20840
            and events(utility["cash_per_usd_10"], "distribution") == events(old["cash_per_usd_10"], "distribution"),
            "Utilities were charged a second time or erased")

    def pending(name, reason, *, keep_cash=False, **kwargs):
        output = variant(name, **kwargs)
        require(output["simulation_result"] == "PENDING"
                and any(reason in blocker for blocker in output["screening"]["simulation_blockers"])
                and (output["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                f"Missing gate or wrong cash availability for {name}")
        return output

    missing = pending("missing-fee-rate", "operating_expense_rate_unconfirmed_or_negative:C58", edits={"C58": "missing"})
    require(missing["scenarios"]["Base"] == matching["scenarios"]["Base"], "Downside rate gap withdrew Base cash")
    pending("missing-insured-units", "insured_unit_inventory_unconfirmed:C59",
            patch=lambda case: case["rent_inputs"]["operating_costs"]["scenarios"]["Downside"].pop("insured_units"))
    pending("undefined-cost-scope", "operating_expense_scope_unconfirmed:C57-C59",
            patch=lambda case: case["rent_inputs"]["operating_costs"]["rules"].pop("controllable"))
    pending("utilities-over-budget", "utilities_exceed_controllable_budget:C57", edits={"C57": {"value": "700"}})
    pending("capacity-reduced", "selected_principal_exceeds_declared_bank_capacity",
            patch=lambda case: case["rent_inputs"].update(requested_principal=rational(1800000)))
    pending("criterion-missing", "criterion_record_missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    pending("stale-operating-costs", "workbooks_fingerprint_mismatch", keep_cash=True, edits={"C59": {"value": "650"}}, stale=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=12, pending_cases=7, worksheet_cells=3,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d148-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
