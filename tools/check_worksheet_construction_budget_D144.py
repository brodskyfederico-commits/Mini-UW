"""Verify construction costs and dated contributions per initial USD 10 from two workbooks."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_development_inputs_D143 import case_for as development_case, not_applicable
from check_worksheet_development_inputs_D143 import workbook_values as development_values
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_CONSTRUCTION_BUDGET_SCHEMA, encoded
from plan_refinance_D108 import REFI_DATE
from plan_return_D107 import DATES, INITIAL, SALE_DATE
from worksheet_commercial_inputs_D141 import commercial_terms
from worksheet_construction_budget_D144 import BASES, POLICY, TIMING, construction_budget
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog, review_native_mapping
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-construction-budget-D144.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D144.json"
BOOKS = {name: ROOT / f"templates/synthetic-construction-budget-{name.lower()}-D144.xlsx" for name in SCENARIOS}
CELLS = ("C37", "C38", "C39", "C40", "C41", "C42")
NORMALIZER = Fraction(10, INITIAL)


def workbook_values(name, catalog):
    inputs = ("5000", "80000", "0.05", "0.10", "15", "0.30") if name == "Base" else (
        "6000", "100000", "0.10", "0.13", "20", "0.50")
    return development_values(name, catalog) | {cell: {"value": value} for cell, value in zip(CELLS, inputs)}


def case_for(books, catalog):
    case = development_case(books, catalog)
    case["schema"] = WORKBOOK_CONSTRUCTION_BUDGET_SCHEMA
    case["local_sources"]["revision"] = "SYNTHETIC-D144-input-r1"
    case["rent_inputs"]["construction_budget"] = dict(
        policy=POLICY, policy_ref="SYNTHETIC-D144-budget-bases", currency="USD", bases=BASES.copy(),
        schedule=dict(terms=TIMING.copy(), source_ref="SYNTHETIC-D144-two-funding-dates"),
        scenarios={name: dict(scope_source_ref=f"SYNTHETIC-D144-{name}-separate-quote-scopes",
                              parking=dict(spaces=24, source_ref=f"SYNTHETIC-D144-{name}-parking-program")) for name in SCENARIOS})
    return case


def events(cash, kind):
    return [(event["date"], amount(event["amount"])) for event in cash["events"]
            if event["kind"] == kind and amount(event["amount"]) != 0]


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    require(all(BOOKS[name].read_bytes() == raw for name, raw in originals.items()), "Fixture drift")
    result = run(CASE, BOOKS, CURRENT, output)
    require(result["simulation_result"] == "FAIL" and not result["revision_review"]["blockers"], "Expected synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL", "D144 did not replay from its sources")
    matching = result["scenarios"]
    for name, parking, site, reserve, soft, ti_lc, upfront, later, total, early, noi, forward in (
            ("Base", 120000, 80000, 127000, 266700, 45000, 80010, 186690, 4100700, 1514010,
             Fraction("432327.60"), Fraction("480891.60")),
            ("Downside", 144000, 100000, 274400, 392392, 60000, 196196, 196196, 4809792, 2213596,
             270681, Fraction("309568.50"))):
        view = matching[name]
        budget, cash = view["construction_budget"], view["cash_per_usd_10"]
        require(set(budget["cell_sources"]) == set(CELLS) and amount(budget["commercial_area_sf"]) == 3000
                and [amount(budget[key]) for key in ("parking_cost", "site_cost", "contingency_reserve", "soft_budget",
                    "ti_lc_cost", "upfront_soft", "remaining_soft", "total_development_cost")]
                == [parking, site, reserve, soft, ti_lc, upfront, later, total], "Cost scope or quantities differ")
        gross = (noi + forward * Fraction(95, 9) - 45500) * NORMALIZER
        receipts = events(cash, "distribution")
        require(events(cash, "contribution") == [(DATES[0], 10), (DATES[1], early * NORMALIZER), (DATES[2], later * NORMALIZER)]
                and cash["basis_event_ids"] == ["initial"] and amount(cash["total_contributions"]) == total * NORMALIZER
                and [day for day, _ in receipts] == [REFI_DATE, SALE_DATE, SALE_DATE]
                and receipts[0][1] == 1372000 * NORMALIZER
                and sum(value for _, value in receipts) == gross == amount(cash["total_distributions"])
                and amount(cash["unrecovered_after_sale"]) == max(0, total * NORMALIZER - gross),
                "Dated funding, receipts or recovery are inconsistent")

    def variant(name, edits=None, patch=None, *, stale=False):
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
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D144-{name}")))
        return run(case_path, paths, revision, temp / name)

    original = matching["Downside"]["cash_per_usd_10"]
    for share, expected in (("0", (2017400, 392392)), ("1", (2409792, 0))):
        alternate = variant(f"timing-{share}", {"C42": {"value": share}})["scenarios"]["Downside"]["cash_per_usd_10"]
        dated = [(DATES[0], 10)] + [(date, value * NORMALIZER) for date, value in zip(DATES[1:3], expected) if value]
        require(events(alternate, "contribution") == dated and events(alternate, "distribution") == events(original, "distribution")
                and alternate["total_contributions"] == original["total_contributions"], "C42 must move funding across dates")

    # Each price or cost basis must change the aggregate and the dated equity by the correct amount.
    for cell, increase, expected_delta in (("C37", "7000", 29832), ("C38", "110000", 12430),
                                           ("C39", "0.11", Fraction("31007.2")), ("C40", "0.14", 30184),
                                           ("C41", "21", 3000)):
        cash = variant(f"cost-{cell}", {cell: {"value": increase}})["scenarios"]["Downside"]["cash_per_usd_10"]
        require(amount(cash["total_contributions"]) - amount(original["total_contributions"]) == expected_delta * NORMALIZER
                and events(cash, "distribution") == events(original, "distribution"), f"Wrong funded cost sensitivity for {cell}")

    def no_commercial(case):
        for use in case["rent_inputs"]["commercial"]["uses"].values():
            use.update(applies=False, rentable_sf=rational(0))
        for name in SCENARIOS:
            for cell in ("C16", "C17", "C18", "C19", "C20", "C21", "C41"):
                not_applicable(case, name, f"INPUT_{cell}")

    noncommercial_cells = ("C16", "C17", "C18", "C19", "C20", "C21", "C41")
    # Both workbooks share the commercial program in this profile. Exercise the valid noncommercial budget directly.
    no_use_books = {name: native_workbook(values[name] | dict.fromkeys(noncommercial_cells, "missing")) for name in SCENARIOS}
    no_use_case = case_for(no_use_books, catalog)
    no_commercial(no_use_case)
    for name, review in review_native_mapping(no_use_case["native_mapping"], no_use_books,
                                               no_use_case["workbook_sha256"])["scenarios"].items():
        rent = no_use_case["rent_inputs"]
        terms = commercial_terms(rent["commercial"], review)
        budget = construction_budget(rent["construction_budget"], name, review, matching[name]["development_costs"], terms)
        require(amount(budget["ti_lc_cost"]) == 0 and budget["ti_lc_rate"] is None, "Explicit non-applicability did not reach TI/LC")

    def pending(name, reason, *, keep_cash=False, **kwargs):
        result = variant(name, **kwargs)
        view = result["scenarios"]["Downside"]
        require(result["simulation_result"] == "PENDING" and (view["cash_per_usd_10"] is not None) == keep_cash
                and (reason is None or reason in view["blockers"]), "Unresolved cost or criterion released a decision")
        return result

    missing = pending("ti-lc-missing", "construction_budget_field_unconfirmed:C41", edits={"C41": "missing"})
    require(missing["scenarios"]["Base"] == matching["Base"], "Downside data gap withdrew Base cash")
    pending("ti-lc-marked-inapplicable", "construction_budget_field_unconfirmed:C41", edits={"C41": "missing"},
            patch=lambda case: not_applicable(case, "Downside", "INPUT_C41"))
    pending("parking-quantity-missing", "parking_quantity_or_source_unconfirmed:C37",
            patch=lambda case: case["rent_inputs"]["construction_budget"]["scenarios"]["Downside"]["parking"].pop("spaces"))
    pending("scope-conflict", "construction_budget_scope_or_base_unconfirmed",
            patch=lambda case: case["rent_inputs"]["construction_budget"]["bases"].update(cost_scope="parking_in_vertical"))
    pending("schedule-missing", "construction_funding_schedule_unconfirmed:C42",
            patch=lambda case: case["rent_inputs"]["construction_budget"].pop("schedule"))
    pending("upfront-share-missing", "construction_budget_field_unconfirmed:C42", edits={"C42": "missing"})
    pending("upfront-share-out-of-range", "construction_budget_value_outside_profile:C42", edits={"C42": {"value": "1.01"}})
    pending("criterion-missing", None, keep_cash=True, patch=lambda case: case["rules"].pop())
    stale = pending("stale-timing", None, keep_cash=True, edits={"C42": {"value": "1"}}, stale=True)
    require(stale["revision_review"]["blockers"], "Changed funding dates did not invalidate the previous revision")
    return dict(status="passed", decision="PENDING", full_workbook_cases=17, pending_cases=9, worksheet_cells=6,
                pdf_sha256=result["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d144-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
