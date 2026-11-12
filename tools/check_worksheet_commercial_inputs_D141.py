"""Verify the C16–C21 commercial bridge and its effect on dated equity cash."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_rental_inputs_D140 import case_for as residential_case, run, workbook_values as residential_values
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_COMMERCIAL_INPUTS_SCHEMA, encoded
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_commercial_inputs_D141 import POLICY
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-commercial-inputs-D141.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D141.json"
BOOKS = {name: ROOT / f"templates/synthetic-commercial-{name.lower()}-D141.xlsx" for name in SCENARIOS}
CELLS = tuple(f"C{i}" for i in range(16, 22))
NUMBERS = {"Base": ("28", "32", "26", "0.10", "0.05", "8"),
           "Downside": ("24", "28", "22", "0.25", "0.15", "14")}


def workbook_values(name, catalog):
    return residential_values(name, catalog) | {
        cell: {"value": value} for cell, value in zip(CELLS, NUMBERS[name], strict=True)}


def case_for(books, catalog):
    case = residential_case(books, catalog)
    case["schema"] = WORKBOOK_COMMERCIAL_INPUTS_SCHEMA
    case["local_sources"]["revision"] = "SYNTHETIC-D141-input-r1"
    case["rent_inputs"]["commercial"] = dict(policy=POLICY, source_ref="SYNTHETIC-D141-inventory",
        tco_date="2027-07-01", tco_source_ref="SYNTHETIC-D141-tco",
        uses={name: dict(applies=True, rentable_sf=rational(area), source_ref=f"SYNTHETIC-D141-plan-{name}")
              for name, area in (("retail", 1200), ("restaurant", 800), ("office", 1000))})
    return case


def received(view):
    return amount(view["cash_per_usd_10"]["total_distributions"])


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
    require(audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "PASS", "Audit could not replay commercial cash")
    periods = (OPERATING_PERIOD, BANK_PERIOD, VALUE_PERIOD, FORWARD_PERIOD)
    for name, months, gross, vac, cost in (("Base", (4, 12, 12, 12), 85200, Fraction(1, 10), Fraction(1, 20)),
                                          ("Downside", (0, 7, 7, 10), 73200, Fraction(1, 4), Fraction(3, 20))):
        view = matching[name]
        require(set(view["commercial_terms"]["cell_sources"]) == set(CELLS), "Missing commercial cell lineage")
        for period, count in zip(periods, months, strict=True):
            row = view["noi_by_period"][period]["commercial"]
            recognized = Fraction(gross * count, 12)
            require(row["recognized_months"] == count and
                    [amount(row[key]) for key in ("gross", "vacancy", "non_recoverable", "net")] ==
                    [recognized, recognized * vac, recognized * (1 - vac) * cost, recognized * (1 - vac) * (1 - cost)],
                    "Commercial lease timing or deduction differs")

    def variant(name, edits=None, patch=None, *, inactive=False):
        books = originals.copy()
        if edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        if inactive:
            books = {scenario: native_workbook(cells | dict.fromkeys(CELLS, "missing"))
                     for scenario, cells in values.items()}
        case = case_for(books, catalog)
        if inactive:
            for use in case["rent_inputs"]["commercial"]["uses"].values():
                use.update(applies=False, rentable_sf=rational(0))
            for review in case["native_mapping"]["scenarios"].values():
                for cell in CELLS:
                    field = f"INPUT_{cell}"
                    review["confirmed_fields"].remove(field)
                    review["not_applicable_fields"].append(field)
        if patch:
            patch(case)
        case_path, revision = (temp / f"{name}-{suffix}.json" for suffix in ("case", "revision"))
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, raw in books.items():
            paths[scenario].write_bytes(raw)
        case_path.write_bytes(encoded(case))
        revision.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D141-{name}")))
        return run(case_path, paths, revision, temp / name)

    baseline = variant("explicit-no-commercial-use", inactive=True)["scenarios"]
    for name, operating, forward, noi in (("Base", 24282, 72846, Fraction("423765.60")),
                                         ("Downside", 0, Fraction("38887.50"), 290961)):
        require(amount(baseline[name]["noi_by_period"][OPERATING_PERIOD]["noi"]) == noi
                and amount(matching[name]["noi_by_period"][OPERATING_PERIOD]["noi"]) == noi + operating,
                "Commercial NOI did not bridge from the residential case")
        expected = (operating + forward * Fraction(95, 9)) / 240000
        require(received(matching[name]) - received(baseline[name]) == expected,
                "The new commercial income did not reconcile to dated cash")

    earlier = variant("lease-start-no-delay", {"C21": {"value": "0"}})["scenarios"]["Downside"]
    require(earlier["noi_by_period"][OPERATING_PERIOD]["commercial"]["recognized_months"] == 12
            and received(earlier) - received(matching["Downside"]) ==
            (46665 + Fraction("7777.50") * Fraction(95, 9)) / 240000, "C21 did not move cash")
    free = variant("zero-non-recoverable", {"C20": {"value": "0"}})["scenarios"]["Downside"]
    require(amount(free["noi_by_period"][FORWARD_PERIOD]["commercial"]["non_recoverable"]) == 0
            and received(free) > received(matching["Downside"]), "Explicit zero in C20 was not respected")

    def pending(name, *, keep_cash=False, **kwargs):
        item = variant(name, **kwargs)
        require(item["simulation_result"] == "PENDING"
                and (item["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                "An unresolved commercial input or rule released a result")
        return item

    missing = pending("delay-unconfirmed", patch=lambda case: case["native_mapping"]["scenarios"]["Downside"]
                      ["confirmed_fields"].remove("INPUT_C21"))
    require(missing["scenarios"]["Base"] == matching["Base"]
            and missing["scenarios"]["Downside"]["blockers"] == ["commercial_vacancy_cost_or_delay_unconfirmed:C19-C21"],
            "A missing commercial field withdrew unrelated cash")
    pending("area-missing", patch=lambda case: case["rent_inputs"]["commercial"]["uses"]["retail"].pop("rentable_sf"))
    pending("tco-missing", patch=lambda case: case["rent_inputs"]["commercial"].pop("tco_date"))
    pending("criterion-missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    return dict(status="passed", decision="PENDING", full_workbook_cases=8, pending_cases=4, worksheet_cells=6,
                pdf_sha256=result["pdf_sha256"], page_count=1, earlier_cash=earlier["cash_per_usd_10"]["total_distributions"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d141-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
