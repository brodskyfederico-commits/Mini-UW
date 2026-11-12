"""Verify the documented C61–C62 tax branches and dated equity effects."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_budget_D144 import NORMALIZER, events
from check_worksheet_replacement_reserve_D149 import (
    BOOKS as RESERVE_BOOKS, CASE as RESERVE_CASE, CURRENT as RESERVE_CURRENT, PLAN, case_for as reserve_case,
    workbook_values as reserve_values, flow,
)
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import WORKBOOK_PROPERTY_TAX_SCHEMA, encoded
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_property_tax_D150 import CAP_UNIT, POLICY, RATE_UNIT, RULES
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-property-tax-D150.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D150.json"
BOOKS = {name: ROOT / f"templates/synthetic-property-tax-{name.lower()}-D150.xlsx" for name in SCENARIOS}


def workbook_values(name, catalog):
    assessment, comparable = ("0.80", "1900") if name == "Base" else ("0.90", "1300")
    return reserve_values(name, catalog) | {"C61": {"value": assessment}, "C62": {"value": comparable}}


def case_for(books, catalog, plan):
    case = reserve_case(books, catalog, plan)
    case["schema"] = WORKBOOK_PROPERTY_TAX_SCHEMA
    rent = case["rent_inputs"]
    del rent["annual_expenses"]["property_tax"]
    rent["annual_expenses"]["source_ref"] = "SYNTHETIC-D150-fixed-non-tax-costs"
    rent["property_tax"] = dict(policy=POLICY, source_ref="SYNTHETIC-D150-annual-tax-bases", rules=RULES.copy(), currency="USD",
        scenarios={name: dict(comparable_units=26, comparable_source_ref=f"SYNTHETIC-D150-{name}-whole-asset-comps",
                              assessment_source_ref=f"SYNTHETIC-D150-{name}-assessed-market-ratio",
                              assessed_tax_rate=dict(value=rational(rate), unit=RATE_UNIT, source_ref=f"SYNTHETIC-D150-{name}-annual-rate"),
                              market_proxy_cap=dict(value=rational(cap), unit=CAP_UNIT, source_ref=f"SYNTHETIC-D150-{name}-tax-proxy-cap"))
                   for name, rate, cap in (("Base", Fraction("0.015"), Fraction("0.10")), ("Downside", Fraction("0.02"), Fraction("0.09")))})
    return case


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    plan = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items()) and
            CASE.read_bytes() == encoded(case_for(originals, catalog, plan)), "Fixture drift")
    baseline = run(RESERVE_CASE, RESERVE_BOOKS, RESERVE_CURRENT, temp / "D149", plan=PLAN)
    matching = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"], "Expected current documents and synthetic FAIL")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL",
            "The tax model could not replay from the saved sources")
    for name, floor, k, pre_tax, branches in (
            ("Base", 49400, Fraction(3, 25), ("451839.10", "457795.60", "482191.60", "482191.60"), ("floor", "floor", "proxy", "proxy")),
            ("Downside", 33800, Fraction(1, 5), ("274452.20", "284231.72", "305562.20", "305562.20"), ("proxy",) * 4)):
        view, previous = matching["scenarios"][name], baseline["scenarios"][name]
        tax_by_period = {}
        for period, before, branch in zip((OPERATING_PERIOD, BANK_PERIOD, VALUE_PERIOD, FORWARD_PERIOD), pre_tax, branches, strict=True):
            before = Fraction(before)
            row = view["noi_by_period"][period]
            evidence = row["property_tax"]
            noi = before - floor if branch == "floor" else before / (1 + k)
            tax = before - noi
            tax_by_period[period] = tax
            require(set(evidence["cell_sources"]) == {"C61", "C62"} and evidence["branch"] == branch
                    and [amount(evidence[key]) for key in ("floor", "coefficient", "operating_before_tax", "annual_tax", "equation_residual")]
                    == [floor, k, before, tax, 0] and tax == max(floor, k * noi) and amount(row["noi"]) == noi,
                    "The payable tax or exact NOI branch differs")
        cash, prior = view["cash_per_usd_10"], previous["cash_per_usd_10"]
        op_delta = (tax_by_period[OPERATING_PERIOD] - 12000) * NORMALIZER
        sale_delta = (tax_by_period[FORWARD_PERIOD] - 12000) * Fraction(95, 9) * NORMALIZER
        total = amount(prior["total_distributions"]) - op_delta - sale_delta
        require(events(cash, "contribution") == events(prior, "contribution")
                and flow(cash, "net_refinance_distribution") == flow(prior, "net_refinance_distribution")
                and flow(prior, "operating_distribution") - flow(cash, "operating_distribution") == op_delta
                and flow(prior, "net_sale_distribution") - flow(cash, "net_sale_distribution") == sale_delta
                and amount(cash["total_distributions"]) == total
                and amount(cash["unrecovered_after_sale"]) == max(0, amount(cash["total_contributions"]) - total)
                and view["capacity"]["bank_noi"] == view["noi_by_period"][BANK_PERIOD]["noi"],
                "NOI was not reflected once in operating cash, bank sizing and sale")

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
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D150-{name}")))
        return run(case_path, paths, revision, temp / name, plan=PLAN)

    def tax_terms(case):
        return case["rent_inputs"]["property_tax"]["scenarios"]["Downside"]

    old = matching["scenarios"]["Downside"]
    for name, edits, branch, expected in (
            ("zero-assessment", {"C61": {"value": "0"}}, "floor", 33800),
            ("zero-comparable", {"C62": {"value": "0"}}, "proxy", Fraction("274452.20") / 6),
            ("higher-comparable", {"C62": {"value": "2000"}}, "floor", 52000),
            ("both-zero", {"C61": {"value": "0"}, "C62": {"value": "0"}}, "tie", 0)):
        view = variant(name, edits)["scenarios"]["Downside"]
        result = view["noi_by_period"][OPERATING_PERIOD]["property_tax"]
        delta = amount(old["noi_by_period"][OPERATING_PERIOD]["property_tax"]["annual_tax"]) - expected
        require(result["branch"] == branch and amount(result["annual_tax"]) == expected
                and flow(view["cash_per_usd_10"], "operating_distribution") - flow(old["cash_per_usd_10"], "operating_distribution")
                == delta * NORMALIZER, f"C61/C62 did not re-evaluate {name}")

    def pending(name, reason, *, keep_cash=False, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and any(reason in blocker for blocker in result["screening"]["simulation_blockers"])
                and (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                f"Missing gate or wrong cash availability for {name}")
        return result

    missing = pending("missing-ratio", "property_tax_assessment_ratio_unconfirmed_or_out_of_range:C61", edits={"C61": "missing"})
    require(missing["scenarios"]["Base"] == matching["scenarios"]["Base"], "Downside tax gap withdrew Base cash")
    pending("missing-comparable", "property_tax_comparable_rate_unconfirmed_or_negative:C62", edits={"C62": "missing"})
    pending("missing-comparable-units", "property_tax_comparable_units_or_scope_unconfirmed:C62",
            patch=lambda case: tax_terms(case).pop("comparable_units"))
    pending("missing-tax-rate", "property_tax_rate_or_unit_unconfirmed:C61", patch=lambda case: tax_terms(case).pop("assessed_tax_rate"))
    pending("ambiguous-rate-unit", "property_tax_rate_or_unit_unconfirmed:C61",
            patch=lambda case: tax_terms(case)["assessed_tax_rate"].update(unit="undeclared_millage"))
    pending("zero-proxy-cap", "property_tax_market_proxy_cap_unconfirmed:C61",
            patch=lambda case: tax_terms(case)["market_proxy_cap"].update(value=rational(0)))
    pending("capacity-reduced", "selected_principal_exceeds_declared_bank_capacity",
            patch=lambda case: case["rent_inputs"].update(requested_principal=rational(1550000)))
    pending("missing-investment-criterion", "criterion_record_missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    pending("stale-assessment", "workbooks_fingerprint_mismatch", keep_cash=True, edits={"C61": {"value": "0.85"}}, stale=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=14, pending_cases=9, worksheet_cells=2,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d150-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
