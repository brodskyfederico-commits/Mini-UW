"""Verify C46–C47 through construction funding, stabilization, refinance and sale."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import case_for as budget_case, events, NORMALIZER
from check_worksheet_construction_budget_D144 import workbook_values as budget_values
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_PROJECT_CALENDAR_SCHEMA, encoded
from plan_return_D107 import DATES, FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_project_calendar_D145 import LIFECYCLE, POLICY, TIMING_RULES
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-project-calendar-D145.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D145.json"
BOOKS = {name: ROOT / f"templates/synthetic-project-calendar-{name.lower()}-D145.xlsx" for name in SCENARIOS}


def workbook_values(name, catalog):
    construction, lease_up = ("6", "3") if name == "Base" else ("9", "6")
    return budget_values(name, catalog) | {"C46": {"value": construction}, "C47": {"value": lease_up}}


def case_for(books, catalog):
    case = budget_case(books, catalog)
    case.update(schema=WORKBOOK_PROJECT_CALENDAR_SCHEMA, criteria_revision="SYNTHETIC-D145-criteria-r1")
    case["local_sources"]["revision"] = "SYNTHETIC-D145-input-r1"
    for rule in case["rules"]:
        rule["period_ref"] = LIFECYCLE
    rent = case["rent_inputs"]
    del rent["construction_budget"]["schedule"], rent["commercial"]["tco_date"], rent["commercial"]["tco_source_ref"]
    rent["project_calendar"] = dict(
        policy=POLICY, policy_ref="SYNTHETIC-D145-explicit-horizons", rules=TIMING_RULES.copy(),
        scenarios={name: dict(construction_start=DATES[0], start_ref=f"SYNTHETIC-D145-{name}-construction-start",
                              tco_date=tco, tco_ref=f"SYNTHETIC-D145-{name}-independent-tco",
                              upfront_direct_hard_share=rational(Fraction(1, 2)),
                              construction_draw_ref=f"SYNTHETIC-D145-{name}-cash-payment-milestones",
                              lease_up_shortfall_per_month=rational(shortfall),
                              lease_up_cash_ref=f"SYNTHETIC-D145-{name}-net-lease-up-shortfall")
                   for name, tco, shortfall in (("Base", "2027-10-01", 10000), ("Downside", "2028-01-01", 20000))})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    original = {name: native_workbook(cells) for name, cells in values.items()}
    require(all(BOOKS[name].read_bytes() == raw for name, raw in original.items()), "Fixture drift")
    result = run(CASE, BOOKS, CURRENT, output)
    require(result["simulation_result"] == "FAIL" and not result["revision_review"]["blockers"], "Expected synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL", "D145 did not replay from its sources")
    matching = result["scenarios"]
    for name, finish, tco, stable, refi, sale, early, late, lease_up, commercial_months, operating, forward, total in (
            ("Base", "2027-09-30", "2027-10-01", "2028-01-01", "2028-09-30", "2028-12-30",
             72010, 1628690, 30000, 7, Fraction("450539.10"), Fraction("480891.60"), 4130700),
            ("Downside", "2027-12-30", "2028-01-01", "2028-07-01", "2029-03-30", "2029-06-30",
             507196, 1902596, 120000, 4, 286236, 317346, 4929792)):
        view = matching[name]
        calendar = view["project_calendar"]
        cash = view["cash_per_usd_10"]
        require(set(calendar["cell_sources"]) == {"C46", "C47"} and
                [calendar[key] for key in ("construction_finish", "tco_date", "stabilization_date", "refinance_date", "sale_date")]
                == [finish, tco, stable, refi, sale], "Calendar dates did not reconcile")
        require(view["capacity"]["as_of_date"] == refi and view["dated_debt_service"]["date"] == sale
                and calendar["payment_dates"][0] == sale, "Closing and debt service must use the revised dates")
        require(view["noi_by_period"][OPERATING_PERIOD]["commercial"]["recognized_months"] == commercial_months
                and amount(view["noi_by_period"][OPERATING_PERIOD]["noi"]) == operating
                and amount(view["noi_by_period"][FORWARD_PERIOD]["noi"]) == forward, "NOI windows were not recalculated")
        gross = (operating + forward * Fraction(95, 9) - 45500) * NORMALIZER
        require(events(cash, "contribution") == [(DATES[0], 10), (DATES[1], early * NORMALIZER),
                                                 (finish, late * NORMALIZER), (finish, lease_up * NORMALIZER)]
                and cash["basis_event_ids"] == ["initial"] and amount(cash["total_contributions"]) == total * NORMALIZER,
                "Dated funding did not match the calendar and USD 10 basis")
        receipts = events(cash, "distribution")
        require([day for day, _ in receipts] == [refi, sale, sale] and receipts[0][1] == 1372000 * NORMALIZER
                and sum(value for _, value in receipts) == gross == amount(cash["total_distributions"])
                and amount(cash["unrecovered_after_sale"]) == max(0, total * NORMALIZER - gross),
                "Receipt amounts, dates or unrecovered cash differ")

    def variant(name, edits=None, patch=None, *, stale=False):
        books = original.copy()
        if edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        case = case_for(books, catalog)
        if patch:
            patch(case)
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, raw in books.items():
            paths[scenario].write_bytes(raw)
        case_path, revision = (temp / f"{name}-{suffix}.json" for suffix in ("case", "revision"))
        case_path.write_bytes(encoded(case))
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D145-{name}")))
        return run(case_path, paths, revision, temp / name)

    old_cash = matching["Downside"]["cash_per_usd_10"]
    shorter = variant("earlier-work-end", {"C46": {"value": "3"}})["scenarios"]["Downside"]
    require(shorter["project_calendar"]["construction_finish"] == "2027-06-30"
            and shorter["project_calendar"]["tco_date"] == "2028-01-01"
            and events(shorter["cash_per_usd_10"], "contribution") == [(day if i < 2 else DATES[1], value)
                for i, (day, value) in enumerate(events(old_cash, "contribution"))]
            and events(shorter["cash_per_usd_10"], "distribution") == events(old_cash, "distribution"),
            "C46 did not move the remaining construction draw without substituting a new TCO")
    immediate = variant("explicit-zero-lease-up", {"C47": {"value": "0"}})["scenarios"]["Downside"]
    calendar, cash = immediate["project_calendar"], immediate["cash_per_usd_10"]
    require(calendar["stabilization_date"] == calendar["tco_date"] == "2028-01-01"
            and [day for day, _ in events(cash, "distribution")] == ["2028-09-30", "2028-12-30", "2028-12-30"]
            and amount(old_cash["total_contributions"]) - amount(cash["total_contributions"]) == 120000 * NORMALIZER
            and amount(cash["total_distributions"]) != amount(old_cash["total_distributions"]),
            "C47 zero did not move the stabilized period and remove lease-up funding")

    def pending(name, reason=None, *, keep_cash=False, **kwargs):
        alternate = variant(name, **kwargs)
        view = alternate["scenarios"]["Downside"]
        require(alternate["simulation_result"] == "PENDING" and (view["cash_per_usd_10"] is not None) == keep_cash
                and (reason is None or reason in view["blockers"]), f"Unresolved calendar or criterion released {name}")
        return alternate

    def change_timing(case, name):
        return case["rent_inputs"]["project_calendar"]["scenarios"][name]

    missing = pending("construction-months-missing", "project_duration_unconfirmed:C46", edits={"C46": "missing"})
    require(missing["scenarios"]["Base"] == matching["Base"], "Downside data gap withdrew Base cash")
    pending("lease-up-months-missing", "project_duration_unconfirmed:C47", edits={"C47": "missing"})
    pending("off-quarter-duration", "project_duration_outside_quarterly_profile:C47", edits={"C47": {"value": "4"}})
    pending("work-after-tco", "tco_conflicts_with_construction_or_quarterly_grid:C46-C47", edits={"C46": {"value": "12"}})
    pending("tco-missing", "lease_up_origin_unconfirmed:C47", patch=lambda case: change_timing(case, "Downside").pop("tco_date"))
    pending("start-missing", "construction_start_unconfirmed:C46", patch=lambda case: change_timing(case, "Downside").pop("start_ref"))
    pending("cash-basis-missing", "lease_up_cash_basis_unconfirmed:C47",
            patch=lambda case: change_timing(case, "Downside").pop("lease_up_shortfall_per_month"))
    pending("criterion-missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    stale = pending("earlier-work-stale-revision", keep_cash=True, edits={"C46": {"value": "6"}}, stale=True)
    require(stale["revision_review"]["blockers"], "A changed construction date retained the prior revision")
    blocked = pending("refi-capacity", patch=lambda case: case["rent_inputs"].update(requested_principal=rational(3000000)))
    view = blocked["scenarios"]["Downside"]
    require(view["capacity"] is not None and view["capacity"]["as_of_date"] == "2029-03-30"
            and amount(view["capacity"]["selected_principal"]) > amount(view["capacity"]["maximum_principal_capacity"]),
            "Capacity gate did not follow the derived refinance date")
    return dict(status="passed", decision="PENDING", full_workbook_cases=13, pending_cases=10, worksheet_cells=2,
                pdf_sha256=result["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d145-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
