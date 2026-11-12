"""Replay C80–C82 through isolated alternatives and verify their dated USD 10 cash."""
from argparse import ArgumentParser
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_growth_D154 import (
    BOOKS as PRIOR_BOOKS, CASE as PRIOR_CASE, CURRENT as PRIOR_CURRENT, PLAN,
    case_for as growth_case, workbook_values as growth_values,
)
from check_worksheet_rental_inputs_D140 import run
from check_worksheet_replacement_reserve_D149 import flow
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_ALTERNATIVES_SCHEMA, encoded
from worksheet_alternatives_D155 import POLICY, SLOTS
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-alternatives-D155.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D155.json"
BOOKS = {name: ROOT / f"templates/synthetic-alternatives-{name.lower()}-D155.xlsx" for name in SCENARIOS}
DRIVERS = {
    "C80": ("C67", "Exit cap rate", "annual_cap_fraction", "0.08", "0.115"),
    "C81": ("C68", "Sale costs", "fraction_of_gross_sale_price", "0", "0"),
    "C82": ("C75", "Rent growth", "annual_effective_growth_fraction", "0.04", "-0.12"),
}


def workbook_values(name, catalog):
    index = SCENARIOS.index(name)
    return growth_values(name, catalog) | {cell: {"text": f"{driver[1]} = {driver[3 + index]}"} for cell, driver in DRIVERS.items()}


def case_for(books, catalog, plan):
    case = growth_case(books, catalog, plan)
    case["schema"] = WORKBOOK_ALTERNATIVES_SCHEMA
    case["rent_inputs"]["alternatives"] = dict(policy=POLICY, source_ref="SYNTHETIC-D155-alternative-policy",
        scenarios={name: dict(scope_ref=f"SYNTHETIC-D155-{name}-scope",
            slots={cell: dict(target_cell=target, unit=unit, operation="replace_absolute",
                value=rational(Fraction((base, downside)[index])), source_ref=f"SYNTHETIC-D155-{name}-{cell}")
                for cell, (target, _label, unit, base, downside) in DRIVERS.items()})
            for index, name in enumerate(SCENARIOS)})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    plan = PLAN.read_bytes()
    values = {name: workbook_values(name, catalog) for name in SCENARIOS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items())
            and CASE.read_bytes() == encoded(case_for(originals, catalog, plan)), "Fixture drift")
    previous = run(PRIOR_CASE, PRIOR_BOOKS, PRIOR_CURRENT, temp / "D154", plan=PLAN)
    current = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    alternatives = current["alternative_evaluation"]
    require(current["state"] == alternatives["state"] == "PENDING" and current["simulation_result"] == previous["simulation_result"] == "FAIL"
            and alternatives["origin_case_sha256"] == current["case_sha256"]
            and alternatives["revision_sha256"] == sha(CURRENT.read_bytes()), "Alternative status changed the origin simulation")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["state"] == "PENDING",
            "Audit could not reproduce the exact alternative package")
    for index, name in enumerate(SCENARIOS):
        origin = current["scenarios"][name]
        cash = origin["cash_per_usd_10"]
        origin_prices = origin["valuation_and_sale"]
        require(events(cash, "contribution") == events(previous["scenarios"][name]["cash_per_usd_10"], "contribution")
                and events(cash, "distribution") == events(previous["scenarios"][name]["cash_per_usd_10"], "distribution"),
                "Alternative text overwrote the origin")
        for cell, pair in alternatives["slots"].items():
            entry = pair[name]
            binding = entry["binding"]
            target, label, unit, *replacements = DRIVERS[cell]
            value = Fraction(replacements[index])
            require(binding["request_literal"] == f"{label} = {replacements[index]}" and binding["target_cell"] == target
                    and binding["unit"] == unit and amount(binding["value"]) == value
                    and binding["request_ref"] == f"sha256:{sha(originals[name])}#Inputs!{cell}"
                    and binding["baseline_driver_ref"] == f"sha256:{sha(originals[name])}#Inputs!{target}",
                    "Alternative provenance or typed replacement drifted")
            candidate = entry["cash_per_usd_10"]
            if cell == "C82" and name == "Downside":
                require(entry["state"] == "PENDING" and candidate is None
                        and "selected_principal_exceeds_declared_bank_capacity" in entry["blockers"]
                        and amount(entry["capacity"]["maximum_principal_capacity"]) < 1400000,
                        "A capacity failure supplied cash or changed the origin")
                continue
            require(entry["state"] == "computed_synthetic" and not entry["blockers"]
                    and entry["baseline_cash_sha256"] == sha(encoded(cash))
                    and events(candidate, "contribution") == events(cash, "contribution")
                    and flow(candidate, "operating_distribution") == flow(cash, "operating_distribution")
                    and flow(candidate, "net_refinance_distribution") == flow(cash, "net_refinance_distribution")
                    and [date for date, _ in events(candidate, "distribution")] == [date for date, _ in events(cash, "distribution")],
                    "Alternative omitted, rescaled or re-dated shared cash")
            price = amount(origin_prices["gross_sale_price"])
            cost = amount(origin_prices["sale_cost"])
            if cell == "C80":
                require(entry["forward_noi"] == origin_prices["forward_noi"], "Exit cap changed the operating projection")
                changed_price = amount(entry["forward_noi"]) / value
                changed_cost = changed_price * amount(origin_prices["sale_cost_fraction"])
            elif cell == "C81":
                changed_price, changed_cost = price, price * value
            else:
                require(amount(entry["forward_noi"]) > amount(origin_prices["forward_noi"]), "Higher rent failed to reach exit NOI")
                changed_price = amount(entry["forward_noi"]) / amount(origin_prices["exit_cap"])
                changed_cost = changed_price * amount(origin_prices["sale_cost_fraction"])
            delta = ((changed_price - changed_cost) - (price - cost)) * NORMALIZER
            require(amount(entry["valuation_and_sale"]["gross_sale_price"]) == changed_price
                    and amount(entry["valuation_and_sale"]["sale_cost"]) == changed_cost
                    and amount(entry["delta_per_usd_10"]["total_distributions"]) == delta
                    and flow(candidate, "net_sale_distribution") - flow(cash, "net_sale_distribution") == delta,
                    "Alternative compounded with another slot or double-counted sale effects")
            source = entry["growth_terms"] if target == "C75" else entry["valuation_and_sale"]
            require(source["cell_sources"][target] == f"sha256:{sha(encoded(binding))}#/value",
                    "Projected driver did not point to the typed alternative binding")

    def variant(label, edits=None, patch=None, *, stale=False):
        books = originals.copy()
        for name, replacements in (edits or {}).items():
            books[name] = native_workbook(values[name] | replacements)
        case = case_for(books, catalog, plan)
        if patch:
            patch(case)
        paths = {name: temp / f"{label}-{name}.xlsx" for name in books}
        for name, source in books.items():
            paths[name].write_bytes(source)
        case_path, revision = (temp / f"{label}-{suffix}.json" for suffix in ("case", "revision"))
        case_path.write_bytes(encoded(case))
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D155-{label}")))
        return run(case_path, paths, revision, temp / label, plan=PLAN)

    def slots(case, name):
        return case["rent_inputs"]["alternatives"]["scenarios"][name]["slots"]

    def pending(result, cell, name, blocker):
        entry = result["alternative_evaluation"]["slots"][cell][name]
        require(entry["state"] == "PENDING" and entry["cash_per_usd_10"] is None and blocker in entry["blockers"],
                f"Wrong slot status for {cell} {name}")

    bad = variant("mismatches", {"Base": {"C80": {"text": "Exit cap rate = 0.09"},
                                         "C81": {"text": "Sale costs = 0; unsupported"},
                                         "C82": "missing"}},
                  patch=lambda case: slots(case, "Downside").pop("C80"))
    pending(bad, "C80", "Base", "alternative_literal_or_unit_mismatch")
    pending(bad, "C81", "Base", "alternative_literal_or_unit_mismatch")
    pending(bad, "C82", "Base", "alternative_request_unconfirmed")
    pending(bad, "C80", "Downside", "alternative_confirmation_missing")
    require(bad["simulation_result"] == "FAIL"
            and bad["alternative_evaluation"]["slots"]["C81"]["Downside"]
                == current["alternative_evaluation"]["slots"]["C81"]["Downside"],
            "Errors in other slots changed a valid Downside alternative or the origin decision")

    def omit(case):
        scope = case["native_mapping"]["scenarios"]["Downside"]
        scope["confirmed_fields"].remove("INPUT_C82")
        scope["not_applicable_fields"].append("INPUT_C82")
        slots(case, "Downside").pop("C82")

    omitted = variant("explicit-omission", {"Downside": {"C82": "missing"}}, patch=omit)
    require(omitted["alternative_evaluation"]["state"] == "checked_synthetic"
            and omitted["alternative_evaluation"]["slots"]["C82"]["Downside"]["state"] == "NOT_APPLICABLE",
            "An optional slot with documented omission was treated as missing")
    stale = variant("stale", patch=lambda case: slots(case, "Base")["C80"].update(
                    source_ref="SYNTHETIC-D155-revised-evidence"), stale=True)
    require(stale["simulation_result"] == "PENDING" and "financial_sources_fingerprint_mismatch" in stale["revision_review"]["blockers"],
            "An alternative change could use a prior revision")
    for cell in SLOTS:
        for name in SCENARIOS:
            pending(stale, cell, name, "alternative_origin_revision_or_documents_pending")
    return dict(status="passed", decision="PENDING", full_workbook_cases=4, alternative_slots=3,
                computed_alternatives=5, pending_capacity_alternatives=1, page_count=1, pdf_sha256=current["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d155-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
