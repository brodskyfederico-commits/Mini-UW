"""Verify type-specific utility expenses, NOI and their impact on equity cash."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_commercial_inputs_D141 import case_for as commercial_case, received, workbook_values as commercial_values
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_UTILITY_INPUTS_SCHEMA, encoded
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_revision_D128 import snapshot_for_case
from worksheet_utility_inputs_D142 import GROUPS, POLICY


CASE = ROOT / "templates/synthetic-workbook-utility-inputs-D142.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D142.json"
BOOKS = {name: ROOT / f"templates/synthetic-utilities-{name.lower()}-D142.xlsx" for name in SCENARIOS}
RATES = {"Base": ("35", "45", "60", "75"), "Downside": ("45", "60", "75", "95")}
UNIT_COUNTS = {"studio": 4, "1BR": 12, "2BR": 8, "3BR": 2}
BASE_NOI = {"Base": Fraction("448047.60"), "Downside": Fraction(290961)}


def workbook_values(name, catalog):
    return commercial_values(name, catalog) | {
        cell: {"value": rate} for cell, rate in zip(GROUPS, RATES[name], strict=True)}


def case_for(books, catalog):
    case = commercial_case(books, catalog)
    case["schema"] = WORKBOOK_UTILITY_INPUTS_SCHEMA
    case["local_sources"]["revision"] = "SYNTHETIC-D142-input-r1"
    case["rent_inputs"]["utilities"] = dict(policy=POLICY, base_expenses_exclude_utilities=True,
        expense_scope_ref="SYNTHETIC-D142-budget-utilities-separate",
        eligible_units={name: {group: dict(applies=True, count=count, source_ref=f"SYNTHETIC-D142-{name}-{group}")
                               for group, count in UNIT_COUNTS.items()} for name in SCENARIOS})
    return case


def verify(temp, saved_output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    require(all(BOOKS[name].read_bytes() == raw for name, raw in originals.items()), "Fixture drift")
    output = saved_output or temp / "matching"
    result = run(CASE, BOOKS, CURRENT, output)
    require(result["simulation_result"] == "PASS" and not result["revision_review"]["blockers"], "Synthetic rules did not clear")
    matching = result["scenarios"]
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "PASS", "Audit could not replay utility expenses")

    def variant(name, edits=None, patch=None, *, zero=False):
        books = originals.copy()
        if zero:
            books = {scenario: native_workbook(cells | {cell: {"value": "0"} for cell in GROUPS})
                     for scenario, cells in values.items()}
        elif edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        case = case_for(books, catalog)
        if patch:
            patch(case)
        case_path, revision = (temp / f"{name}-{suffix}.json" for suffix in ("case", "revision"))
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, raw in books.items():
            paths[scenario].write_bytes(raw)
        case_path.write_bytes(encoded(case))
        revision.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D142-{name}")))
        return run(case_path, paths, revision, temp / name)

    baseline = variant("zero-utilities", zero=True)["scenarios"]
    for name, expected in (("Base", [1680, 6480, 5760, 1800]), ("Downside", [2160, 8640, 7200, 2280])):
        view = matching[name]
        total = sum(expected)
        for period in (OPERATING_PERIOD, BANK_PERIOD, VALUE_PERIOD, FORWARD_PERIOD):
            row, reference = view["noi_by_period"][period], baseline[name]["noi_by_period"][period]
            require([amount(item["annual_expense"]) for item in row["utilities"]["rows"]] == expected
                    and [item["cell"] for item in row["utilities"]["rows"]] == list(GROUPS)
                    and amount(row["utilities"]["annual_total"]) == total
                    and amount(row["operating_expenses_excluding_tax"]) - amount(reference["operating_expenses_excluding_tax"]) == total
                    and amount(reference["noi"]) - amount(row["noi"]) == total
                    and row["effective_rent"] == reference["effective_rent"], "Utility costs did not reach NOI once")
        require(amount(baseline[name]["noi_by_period"][OPERATING_PERIOD]["noi"]) == BASE_NOI[name]
                and received(baseline[name]) - received(view) == Fraction(total, 240000) * Fraction(104, 9),
                "Utility expenses did not reconcile to the dated cash after operating expenses and sale")
        actual = {e["event_id"]: amount(e["amount"]) for e in view["cash_per_usd_10"]["events"]}
        prior = {e["event_id"]: amount(e["amount"]) for e in baseline[name]["cash_per_usd_10"]["events"]}
        require(prior["operating"] - actual["operating"] == Fraction(total, 240000)
                and prior["sale"] - actual["sale"] == Fraction(total, 240000) * Fraction(95, 9)
                and all(actual[k] == prior[k] for k in actual if k not in ("operating", "sale")),
                "Utility costs affected the wrong dated events")

    more = variant("one-bedroom-increase", {"C26": {"value": "70"}})["scenarios"]["Downside"]
    require(received(matching["Downside"]) - received(more) == Fraction(1440, 240000) * Fraction(104, 9),
            "The C26 change did not use the 12 eligible one-bedroom units")

    def inactive(case):
        eligibility = case["rent_inputs"]["utilities"]["eligible_units"]["Downside"]["3BR"]
        eligibility.update(applies=False, count=0)
        review = case["native_mapping"]["scenarios"]["Downside"]
        review["confirmed_fields"].remove("INPUT_C28")
        review["not_applicable_fields"].append("INPUT_C28")

    absent = variant("explicitly-not-applicable", {"C28": "missing"}, inactive)
    last = absent["scenarios"]["Downside"]["noi_by_period"][OPERATING_PERIOD]["utilities"]["rows"][-1]
    require(absent["simulation_result"] == "PASS" and not last["applies"] and amount(last["annual_expense"]) == 0,
            "Documented non-applicability was lost")

    def pending(name, reason=None, *, keep_cash=False, **kwargs):
        item = variant(name, **kwargs)
        view = item["scenarios"]["Downside"]
        require(item["simulation_result"] == "PENDING" and (view["cash_per_usd_10"] is not None) == keep_cash
                and (reason is None or reason in view["blockers"]), "A missing utility confirmation or criterion released a result")
        return item

    unconfirmed = pending("rate-unconfirmed", "utility_rate_unconfirmed:C27",
                          patch=lambda case: case["native_mapping"]["scenarios"]["Downside"]["confirmed_fields"].remove("INPUT_C27"))
    require(unconfirmed["scenarios"]["Base"] == matching["Base"], "Missing C27 withdrew unrelated cash")
    pending("eligible-count-missing", "utility_eligible_units_unconfirmed:C28",
            patch=lambda case: case["rent_inputs"]["utilities"]["eligible_units"]["Downside"]["3BR"].pop("count"))
    pending("scope-overlaps-base", "utility_treatment_or_base_expense_scope_unconfirmed",
            patch=lambda case: case["rent_inputs"]["utilities"].update(base_expenses_exclude_utilities=False))
    pending("criterion-missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    return dict(status="passed", decision="PENDING", full_workbook_cases=8, pending_cases=4, worksheet_cells=4,
                pdf_sha256=result["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d142-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
