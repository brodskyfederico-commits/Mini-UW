"""Verify staged draws, construction interest, closing payoff and dated equity per USD 10."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_project_calendar_D145 import case_for as calendar_case, workbook_values as calendar_values
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_CONSTRUCTION_FINANCING_SCHEMA, encoded
from plan_return_D107 import DATES
from worksheet_construction_financing_D146 import LIFECYCLE, POLICY, RULES
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-construction-financing-D146.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D146.json"
BOOKS = {name: ROOT / f"templates/synthetic-construction-financing-{name.lower()}-D146.xlsx" for name in SCENARIOS}
CELLS = ("C51", "C52", "C53")


def workbook_values(name, catalog):
    values = ("0.60", "0.08", "0.01") if name == "Base" else ("0.50", "0.10", "0.015")
    return calendar_values(name, catalog) | {cell: {"value": value} for cell, value in zip(CELLS, values, strict=True)}


def case_for(books, catalog):
    case = calendar_case(books, catalog)
    case.update(schema=WORKBOOK_CONSTRUCTION_FINANCING_SCHEMA, criteria_revision="SYNTHETIC-D146-criteria-r1")
    case["local_sources"]["revision"] = "SYNTHETIC-D146-input-r1"
    for rule in case["rules"]:
        rule["period_ref"] = LIFECYCLE
    case["rent_inputs"]["construction_financing"] = dict(
        policy=POLICY, policy_ref="SYNTHETIC-D146-draw-interest-fee-and-payoff-terms", rules=RULES.copy(),
        scenarios={name: dict(source_ref=f"SYNTHETIC-D146-{name}-term-sheet", currency="USD",
                              maximum_commitment=rational(cap), requested_invoice_fraction=rational(Fraction(1, 4)),
                              available_per_draw_checkpoint=rational(limit), maturity_date=maturity)
                   for name, cap, limit, maturity in (("Base", 1600000, 350000, "2028-12-30"),
                                                       ("Downside", 1250000, 380000, "2029-06-30"))})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    require(all(BOOKS[name].read_bytes() == raw for name, raw in originals.items()), "Fixture drift")
    result = run(CASE, BOOKS, CURRENT, output)
    require(result["simulation_result"] == "FAIL" and not result["revision_review"]["blockers"], "Expected synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL", "Debt flows did not replay")
    views = result["scenarios"]
    expected = {
        "Base": dict(commitment=1524000, fee=15240, draw=317500, project_uses=4130700, interest=57150,
                     dated_interest=[0, 6350, 12700, 12700, 12700, 12700],
                     dates=("2027-09-30", "2028-09-30", "2028-12-30"),
                     equity=[2400000, 0, 1117290, 12700, 12700, 12700, 12700],
                     operating=Fraction("450539.10"), forward=Fraction("480891.60")),
        "Downside": dict(commitment=1250000, fee=18750, draw=343000, project_uses=4929792, interest=102900,
                         dated_interest=[0, 8575, 8575, 17150, 17150, 17150, 17150, 17150],
                         dates=("2027-12-30", "2029-03-30", "2029-06-30"),
                         equity=[2400000, 182946, 8575, 1688171, 17150, 17150, 17150, 17150, 17150],
                         operating=286236, forward=317346),
    }
    for name, check in expected.items():
        view = views[name]
        funding, closing = view["construction_financing"], view["construction_refinance"]
        debt, cash = funding["debt_run"], view["cash_per_usd_10"]
        finish, refi, sale = check["dates"]
        require(set(funding["cell_sources"]) == set(CELLS) and amount(funding["commitment"]) == check["commitment"]
                and amount(funding["origination_fee"]) == check["fee"], "LTC or opening fee did not reach funding")
        require([(row["start_date"], amount(row["draw_at_start"])) for row in debt["periods"] if amount(row["draw_at_start"])]
                == [(DATES[1], check["draw"]), (finish, check["draw"])]
                and [amount(row["interest_due_at_end"]) for row in debt["periods"]] == check["dated_interest"],
                "Draw timing or interest exposure changed")
        draws = 2 * check["draw"]
        total_equity = sum(check["equity"])
        require([amount(debt["totals"][key]) for key in ("gross_draws", "interest_due", "principal_repaid", "terminal_principal")]
                == [draws, check["interest"], draws, 0]
                and amount(funding["free_cash_at_refinance"]) == 0
                and total_equity + draws == check["project_uses"] + check["fee"] + check["interest"],
                "Sources, uses and repayment do not reconcile")
        cash_by_day = funding["cash_by_date"]
        require([amount(row["equity_contribution"]) for row in cash_by_day] == check["equity"]
                and amount(cash_by_day[0]["origination_fee_paid"]) == check["fee"]
                and events(cash, "contribution") == [(row["date"], value * NORMALIZER)
                    for row, value in zip(cash_by_day, check["equity"], strict=True) if value]
                and cash["basis_event_ids"] == ["initial"] and amount(cash["total_contributions"]) == total_equity * NORMALIZER,
                "Dated contributions or the original USD 10 basis changed")
        gross = (check["operating"] + check["forward"] * Fraction(95, 9) - 45500 - draws) * NORMALIZER
        receipts = events(cash, "distribution")
        require(closing["date"] == refi and amount(closing["prior_principal_paid"]) == draws
                and amount(closing["net_equity_distribution"]) == 1372000 - draws
                and view["dated_debt_service"]["date"] == sale and [day for day, _ in receipts] == [refi, sale, sale]
                and receipts[0][1] == (1372000 - draws) * NORMALIZER and amount(cash["total_distributions"]) == gross
                and amount(cash["unrecovered_after_sale"]) == max(0, total_equity * NORMALIZER - gross),
                "Loan proceeds or payoff were omitted or counted twice in the return")

    def variant(name, edits=None, patch=None, *, stale=False):
        books = originals.copy()
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
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D146-{name}")))
        return run(case_path, paths, revision, temp / name)

    def terms(case):
        return case["rent_inputs"]["construction_financing"]["scenarios"]["Downside"]

    downside = views["Downside"]["cash_per_usd_10"]
    earlier = variant("earlier-completion", {"C46": {"value": "6"}})["scenarios"]["Downside"]
    earlier_debt = earlier["construction_financing"]["debt_run"]
    require(earlier_debt["periods"][2]["start_date"] == "2027-09-30" and amount(earlier_debt["periods"][2]["draw_at_start"]) == 343000
            and amount(earlier_debt["totals"]["interest_due"]) == 111475
            and amount(earlier["cash_per_usd_10"]["total_contributions"]) - amount(downside["total_contributions"]) == 8575 * NORMALIZER
            and events(earlier["cash_per_usd_10"], "distribution") == events(downside, "distribution"),
            "A C46 change did not recalculate the interest and equity")
    for cell, reduction in (("C52", 102900), ("C53", 18750)):
        alternate = variant(f"zero-{cell}", {cell: {"value": "0"}})["scenarios"]["Downside"]["cash_per_usd_10"]
        require(amount(downside["total_contributions"]) - amount(alternate["total_contributions"]) == reduction * NORMALIZER
                and events(alternate, "distribution") == events(downside, "distribution"), f"Explicit zero {cell} did not reach equity")
    unlevered = variant("zero-construction-debt", {cell: {"value": "0"} for cell in CELLS},
                       lambda case: terms(case).update(requested_invoice_fraction=rational(0)))["scenarios"]["Downside"]
    require(amount(unlevered["construction_refinance"]["prior_principal_paid"]) == 0
            and amount(unlevered["cash_per_usd_10"]["total_contributions"]) == 4929792 * NORMALIZER
            and amount(unlevered["cash_per_usd_10"]["total_distributions"]) - amount(downside["total_distributions"]) == 686000 * NORMALIZER,
            "An explicitly zero construction facility did not reproduce the equity-funded case")

    def pending(name, reason=None, *, keep_cash=False, **kwargs):
        output = variant(name, **kwargs)
        view = output["scenarios"]["Downside"]
        require(output["simulation_result"] == "PENDING" and (view["cash_per_usd_10"] is not None) == keep_cash
                and (reason is None or any(reason in blocker for blocker in view["blockers"])),
                f"Unresolved financing or criterion released {name}")
        return output

    missing = pending("missing-rate", "construction_financing_field_unconfirmed_or_out_of_range:C52", edits={"C52": "missing"})
    require(missing["scenarios"]["Base"] == views["Base"], "Downside financing gap withdrew Base cash")
    pending("missing-fee", "construction_financing_field_unconfirmed_or_out_of_range:C53", edits={"C53": "missing"})
    pending("low-ltc", "cumulative_gross_draws_exceed_nonrevolving_commitment", edits={"C51": {"value": "0.20"}})
    pending("short-maturity", "schedule_past_maturity_no_extension_inferred", edits={"C47": {"value": "12"}})
    pending("unavailable-draw", "draw_exceeds_declared_available_new_draw",
            patch=lambda case: terms(case).update(available_per_draw_checkpoint=rational(300000)))
    pending("missing-term", "construction_bank_limit_or_draw_share_unconfirmed", patch=lambda case: terms(case).pop("maximum_commitment"))
    pending("payoff-shortfall", "cash_in_required_but_projected_equity_funding_assumption_missing",
            patch=lambda case: case["rent_inputs"].update(requested_principal=rational(600000)))
    capacity = pending("refi-over-capacity", "selected_principal_exceeds_declared_bank_capacity",
                       patch=lambda case: case["rent_inputs"].update(requested_principal=rational(3000000)))
    require(capacity["scenarios"]["Downside"]["construction_refinance"]["net_equity_distribution"] is None,
            "A blocked capacity released the estimated refinance distribution")
    pending("missing-criterion", keep_cash=True, patch=lambda case: case["rules"].pop())
    stale = pending("stale-revision", keep_cash=True, edits={"C52": {"value": "0.09"}}, stale=True)
    require(stale["revision_review"]["blockers"], "Changed interest left the previous revision current")
    return dict(status="passed", decision="PENDING", full_workbook_cases=15, pending_cases=10, worksheet_cells=3,
                pdf_sha256=result["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d146-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
