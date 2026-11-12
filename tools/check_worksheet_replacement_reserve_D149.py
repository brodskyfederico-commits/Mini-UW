"""Verify that C60 moves cash through the reserve and sale exactly once."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_operating_costs_D148 import (
    BOOKS as OPEX_BOOKS, CASE as OPEX_CASE, CURRENT as OPEX_CURRENT, PLAN, case_for as opex_case,
    workbook_values as opex_values,
)
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_REPLACEMENT_RESERVE_SCHEMA, encoded
from plan_return_D107 import OPERATING_PERIOD
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_replacement_reserve_D149 import POLICY, RULES
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-replacement-reserve-D149.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D149.json"
BOOKS = {name: ROOT / f"templates/synthetic-replacement-reserve-{name.lower()}-D149.xlsx" for name in SCENARIOS}


def workbook_values(name, catalog):
    return opex_values(name, catalog) | {"C60": {"value": "1200" if name == "Base" else "2000"}}


def case_for(books, catalog, plan):
    case = opex_case(books, catalog, plan)
    case["schema"] = WORKBOOK_REPLACEMENT_RESERVE_SCHEMA
    case["rent_inputs"]["replacement_reserve"] = dict(
        policy=POLICY, source_ref="SYNTHETIC-D149-restricted-cash-policy", rules=RULES.copy(), currency="USD",
        scenarios={name: dict(eligible_units=26, eligible_units_ref=f"SYNTHETIC-D149-{name}-covered-units",
                              sale_release_fraction=rational(Fraction(1) if name == "Base" else Fraction(1, 2)),
                              sale_settlement_ref=f"SYNTHETIC-D149-{name}-restricted-cash-at-closing") for name in SCENARIOS})
    return case


def flow(cash, category):
    event, = [row for row in cash["events"] if row["category"] == category]
    return amount(event["amount"])


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    plan = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items()) and
            CASE.read_bytes() == encoded(case_for(originals, catalog, plan)), "Fixture drift")
    baseline = run(OPEX_CASE, OPEX_BOOKS, OPEX_CURRENT, temp / "D148", plan=PLAN)
    matching = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"], "Expected current documents and synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL",
            "The reserve could not replay from the saved sources")
    for name, deposit, release, sale_date in (("Base", 31200, 31200, "2028-12-30"), ("Downside", 52000, 26000, "2029-06-30")):
        view, previous = matching["scenarios"][name], baseline["scenarios"][name]
        reserve = view["replacement_reserve"]
        cash, prior = view["cash_per_usd_10"], previous["cash_per_usd_10"]
        require(reserve["cell_source"].endswith("#Inputs!C60") and reserve["deposit_date"] == reserve["sale_date"] == sale_date
                and [amount(reserve[key]) for key in ("deposit", "restricted_before_sale", "released_at_sale", "transferred_restricted_to_buyer",
                    "operating_cash_residual", "sale_cash_residual", "operating_equity_contribution")] == [deposit, deposit, release, deposit - release, 0, 0, 0]
                and reserve["operating_cash_sha256"] == view["source_runs"]["operating_cash_sha256"]
                and reserve["sale_closing_sha256"] == view["source_runs"]["sale_closing_sha256"], "Restricted cash did not reconcile")
        require({period: row["noi"] for period, row in view["noi_by_period"].items()}
                == {period: row["noi"] for period, row in previous["noi_by_period"].items()}
                and view["gross_sale"] == previous["gross_sale"] and
                view["capacity"]["maximum_principal_capacity"] == previous["capacity"]["maximum_principal_capacity"],
                "The reserve was counted as an expense or valuation uplift")
        gross = amount(prior["total_distributions"]) - (deposit - release) * NORMALIZER
        require(events(cash, "contribution") == events(prior, "contribution")
                and flow(cash, "net_refinance_distribution") == flow(prior, "net_refinance_distribution")
                and flow(prior, "operating_distribution") - flow(cash, "operating_distribution") == deposit * NORMALIZER
                and flow(cash, "net_sale_distribution") - flow(prior, "net_sale_distribution") == release * NORMALIZER
                and amount(cash["total_distributions"]) == gross
                and amount(cash["unrecovered_after_sale"]) == max(0, amount(cash["total_contributions"]) - gross),
                "The operating distribution or sale counted the reserve twice")

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
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D149-{name}")))
        return run(case_path, paths, revision, temp / name, plan=PLAN)

    def reserve_terms(case):
        return case["rent_inputs"]["replacement_reserve"]["scenarios"]["Downside"]

    prior = baseline["scenarios"]["Downside"]["cash_per_usd_10"]
    zero = variant("zero-deposit", {"C60": {"value": "0"}})["scenarios"]["Downside"]
    require(amount(zero["replacement_reserve"]["deposit"]) == 0
            and events(zero["cash_per_usd_10"], "distribution") == events(prior, "distribution"),
            "Explicit zero did not reproduce the no-reserve cash")
    for fraction in (0, 1):
        view = variant(f"release-{fraction}", patch=lambda case: reserve_terms(case).update(
            sale_release_fraction=rational(fraction)))["scenarios"]["Downside"]
        require(amount(view["replacement_reserve"]["transferred_restricted_to_buyer"]) == 52000 * (1 - fraction)
                and flow(view["cash_per_usd_10"], "net_sale_distribution") == flow(prior, "net_sale_distribution") + 52000 * fraction * NORMALIZER,
                "Explicit sale disposition was ignored")
    fewer = variant("covered-units", patch=lambda case: reserve_terms(case).update(eligible_units=25))["scenarios"]["Downside"]
    require(amount(fewer["replacement_reserve"]["deposit"]) == 50000, "C60 ignored the covered-unit inventory")
    stressed = variant("cash-shortfall", {"C60": {"value": "10000"}})["scenarios"]["Downside"]
    cash = stressed["cash_per_usd_10"]
    shortfall = 260000 * NORMALIZER - flow(prior, "operating_distribution")
    require(shortfall > 0 and flow(cash, "operating_distribution") == 0
            and events(cash, "contribution") == events(prior, "contribution") + [("2029-06-30", shortfall)]
            and amount(stressed["replacement_reserve"]["operating_equity_contribution"]) * NORMALIZER == shortfall
            and stressed["noi_by_period"][OPERATING_PERIOD]["noi"] == baseline["scenarios"]["Downside"]["noi_by_period"][OPERATING_PERIOD]["noi"],
            "An operating shortfall did not reach the dated investor contribution")

    def pending(name, reason, *, keep_cash=False, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and any(reason in blocker for blocker in result["screening"]["simulation_blockers"])
                and (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                f"Missing gate or wrong cash availability for {name}")
        return result

    missing = pending("missing-rate", "replacement_reserve_rate_unconfirmed_or_negative:C60", edits={"C60": "missing"})
    require(missing["scenarios"]["Base"] == matching["scenarios"]["Base"], "Downside reserve gap withdrew Base cash")
    pending("missing-units", "replacement_reserve_units_unconfirmed:C60", patch=lambda case: reserve_terms(case).pop("eligible_units"))
    pending("missing-sale-disposition", "replacement_reserve_sale_disposition_unconfirmed:C60",
            patch=lambda case: reserve_terms(case).pop("sale_settlement_ref"))
    pending("out-of-range-release", "replacement_reserve_sale_disposition_unconfirmed:C60",
            patch=lambda case: reserve_terms(case).update(sale_release_fraction=rational(Fraction(11, 10))))
    pending("missing-funding-policy", "replacement_reserve_policy_unconfirmed:C60",
            patch=lambda case: case["rent_inputs"]["replacement_reserve"]["rules"].pop("shortfall_funding"))
    pending("missing-investment-criterion", "criterion_record_missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    pending("stale-release-policy", "financial_sources_fingerprint_mismatch", keep_cash=True, stale=True,
            patch=lambda case: reserve_terms(case).update(sale_release_fraction=rational(Fraction(3, 4))))
    return dict(status="passed", decision="PENDING", full_workbook_cases=13, pending_cases=7, worksheet_cells=1,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d149-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
