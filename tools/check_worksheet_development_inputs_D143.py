"""Check purchase, closing and vertical construction costs against the dated cash."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_commercial_inputs_D141 import received
from check_worksheet_rental_inputs_D140 import run
from check_worksheet_utility_inputs_D142 import case_for as utility_case, workbook_values as utility_values
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_DEVELOPMENT_INPUTS_SCHEMA, encoded
from plan_return_D107 import DATES, FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_development_inputs_D143 import POLICY
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-development-inputs-D143.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D143.json"
BOOKS = {name: ROOT / f"templates/synthetic-development-{name.lower()}-D143.xlsx" for name in SCENARIOS}
PRICES = {"Base": 1100000, "Downside": 1300000}


def workbook_values(name, catalog):
    base = name == "Base"
    return utility_values(name, catalog) | {
        "C32": {"value": str(PRICES[name])}, "C33": {"value": "0.02" if base else "0.03"},
        "C34": {"text": "$/UNIT" if base else "$/GSF"}, "C35": {"value": "90000" if base else "100"},
        "C36": "missing" if base else {"value": "25000"}}


def not_applicable(case, name, field):
    review = case["native_mapping"]["scenarios"][name]
    review["confirmed_fields"].remove(field)
    review["not_applicable_fields"].append(field)


def case_for(books, catalog):
    case = utility_case(books, catalog)
    case["schema"] = WORKBOOK_DEVELOPMENT_INPUTS_SCHEMA
    case["local_sources"]["revision"] = "SYNTHETIC-D143-input-r1"
    rent = case["rent_inputs"]
    del rent["construction_cost"], rent["cost_source_ref"]
    rent["development"] = dict(policy=POLICY, policy_ref="SYNTHETIC-D143-funded-from-equity", currency="USD",
        closing_base="evaluated_purchase_price", vertical_scope="building_excluding_parking_and_site",
        scenarios={name: dict(evaluated_purchase_price=rational(price), purchase_date=DATES[0],
                              purchase_source_ref=f"SYNTHETIC-D143-{name}-evaluated-purchase",
                              vertical_source_ref=f"SYNTHETIC-D143-{name}-vertical-quote",
                              program_source_ref="SYNTHETIC-D143-26-unit-program",
                              plan_gsf=dict(state="TBD", value=None, source_ref="SYNTHETIC-D143-plan"),
                              worksheet_gsf_source_ref="SYNTHETIC-D143-confirmed-gsf") for name, price in PRICES.items()})
    not_applicable(case, "Base", "INPUT_C36")
    return case


def verify(temp, saved_output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    require(all(BOOKS[name].read_bytes() == raw for name, raw in originals.items()), "Fixture drift")
    output = saved_output or temp / "matching"
    result = run(CASE, BOOKS, CURRENT, output)
    require(result["simulation_result"] == "FAIL" and not result["revision_review"]["blockers"], "Expected the original rule to fail")
    matching = result["scenarios"]
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL", "Audit could not replay development costs")
    for name, purchase, fees, vertical, total, noi, forward in (
            ("Base", 1100000, 22000, 2340000, 3462000, Fraction("432327.60"), Fraction("480891.60")),
            ("Downside", 1300000, 39000, 2500000, 3839000, 270681, Fraction("309568.50"))):
        view = matching[name]
        costs = view["development_costs"]
        cash = view["cash_per_usd_10"]
        expected_cash = (noi + forward * Fraction(95, 9) - 45500) / 240000
        require(set(costs["cell_sources"]) == {f"C{i}" for i in range(32, 37)}
                and [amount(costs[key]) for key in ("evaluated_purchase_price", "land_closing_cost", "vertical_cost",
                                                    "total_development_cost")] == [purchase, fees, vertical, total]
                and amount(view["noi_by_period"][OPERATING_PERIOD]["noi"]) == noi
                and amount(view["noi_by_period"][FORWARD_PERIOD]["noi"]) == forward
                and amount(cash["total_contributions"]) == Fraction(total, 240000)
                and received(view) == expected_cash
                and amount(cash["unrecovered_after_sale"]) == max(0, Fraction(total, 240000) - expected_cash),
                "Development costs did not reach contributions or preserved cash")
        contributions = [(e["date"], amount(e["amount"])) for e in cash["events"]
                         if e["kind"] == "contribution" and amount(e["amount"]) != 0]
        require(contributions == [(DATES[0], 10), (DATES[1], Fraction(total - 2400000, 240000))],
                "The additional equity changed the original USD 10 denominator")

    def variant(name, edits=None, patch=None):
        books = originals.copy()
        if edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        case = case_for(books, catalog)
        if patch:
            patch(case)
        case_path, revision = (temp / f"{name}-{suffix}.json" for suffix in ("case", "revision"))
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, raw in books.items():
            paths[scenario].write_bytes(raw)
        case_path.write_bytes(encoded(case))
        revision.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D143-{name}")))
        return run(case_path, paths, revision, temp / name)

    def declared_plan(case, mark=True):
        declaration = case["rent_inputs"]["development"]["scenarios"]["Downside"]
        declaration["plan_gsf"].update(state="declared", value=rational(25000))
        if mark:
            not_applicable(case, "Downside", "INPUT_C36")

    total = variant("vertical-total", {"C34": {"text": "TOTAL"}, "C35": {"value": "2500000"}, "C36": "missing"},
                    lambda case: not_applicable(case, "Downside", "INPUT_C36"))
    known = variant("declared-plan-gsf", {"C36": "missing"}, declared_plan)
    for alternate in (total, known):
        view = alternate["scenarios"]["Downside"]
        require(amount(view["development_costs"]["vertical_cost"]) == 2500000
                and received(view) == received(matching["Downside"])
                and view["cash_per_usd_10"]["total_contributions"] == matching["Downside"]["cash_per_usd_10"]["total_contributions"],
                "Equivalent quote bases changed cash")
    zero = variant("closing-fraction-zero", {"C33": {"value": "0"}})["scenarios"]["Downside"]
    require(amount(zero["development_costs"]["land_closing_cost"]) == 0
            and amount(zero["cash_per_usd_10"]["total_contributions"]) == Fraction(3800000, 240000),
            "Explicit zero closing cost did not reduce equity")

    def pending(name, reason=None, *, keep_cash=False, **kwargs):
        item = variant(name, **kwargs)
        view = item["scenarios"]["Downside"]
        require(item["simulation_result"] == "PENDING" and (view["cash_per_usd_10"] is not None) == keep_cash
                and (reason is None or reason in view["blockers"]), "An unresolved cost or rule released a result")
        return item

    mismatch = pending("asking-differs-from-purchase", "evaluated_purchase_price_unconfirmed_or_mismatched:C32",
                       edits={"C32": {"value": "1400000"}})
    require(mismatch["scenarios"]["Base"] == matching["Base"], "The Downside price withdrew Base cash")
    pending("required-gsf-missing", "development_field_unconfirmed:C36", edits={"C36": "missing"})
    pending("vertical-quote-unconfirmed", "development_field_unconfirmed:C35",
            patch=lambda case: case["native_mapping"]["scenarios"]["Downside"]["confirmed_fields"].remove("INPUT_C35"))
    pending("plan-gsf-conflicts-with-worksheet", "construction_gsf_source_conflict:C36",
            patch=lambda case: declared_plan(case, mark=False))
    pending("asking-missing", "development_field_unconfirmed:C32", edits={"C32": "missing"})
    pending("initial-equity-cannot-cover-acquisition", "development_costs_outside_declared_equity_schedule",
            edits={"C32": {"value": "2450000"}}, patch=lambda case: case["rent_inputs"]["development"]["scenarios"]["Downside"]
            .update(evaluated_purchase_price=rational(2450000)))
    pending("criterion-missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    return dict(status="passed", decision="PENDING", full_workbook_cases=11, pending_cases=7, worksheet_cells=5,
                pdf_sha256=result["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d143-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
