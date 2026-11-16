"""Reconcile an annual sale retaining construction debt from workbook to PDF."""

from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pypdf import PdfReader

from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import RLV, encode, prepare_configuration
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, read_package
from test_lorena_screening import RECIPE, SOURCE
from test_worksheet_annual_holding import ROUTE, annual_settings, source_files
from worksheet_annual_coc import quantity as amount
from worksheet_calendar_routes_D199 import route_cash
from worksheet_intake_D198 import assemble, register
from worksheet_lorena_screening import rehearse_workbook


SALE = "annual_hold_without_refinance"
RATES = {"Base": Fraction("0.02"), "Downside": Fraction("0.025")}


def settings_with_sale():
    settings = annual_settings()
    for name, routes in settings["rent_inputs"]["calendar_checks"].items():
        inherited = routes[ROUTE]
        terms = {k: deepcopy(inherited[k]) for k in (
            "quarterly_noi_before_reserves", "delayed_forward_noi", "construction_tax")}
        source = f"SYNTHETIC-D237-{name}-construction-hold"
        dates = terms["quarterly_noi_before_reserves"]
        terms.update(route="sell_without_refinance", source_ref=source,
                     construction_hold=dict(source_ref=source, principal_basis="unchanged_until_sale",
                         interest_fractions={d: dict(value=rational(RATES[name]), source_ref=f"{source}/{d}") for d in dates},
                         maturity_extension=dict(date=max(dates), fee_usd=rational(0), source_ref=f"{source}/extension")))
        routes[SALE] = terms
    return settings


def verify(root):
    settings = settings_with_sale()
    sources = source_files(root / "sources")
    package, revision, pdf = root / "expediente", root / "vigente.json", root / "MiniUW_D237_Sin_Refi.pdf"
    assemble(settings, register(sources, "SYNTHETIC-D237-annual-sale"), sources, package)
    saved = read_package(package)
    revision.write_bytes(saved[CURRENT_REVISION_FILE])
    config = encode(prepare_configuration(RECIPE, SOURCE))
    receipt = rehearse_workbook(package, revision, RECIPE, SOURCE, config, route=SALE, pdf_output=pdf)
    assert receipt["decision"] == receipt["simulation_result"] == "PENDING"
    assert not receipt["criteria_adopted"] and not receipt["deployment_enabled"]
    assert receipt["annual_pdf"]["sha256"] == sha256(pdf.read_bytes()).hexdigest()
    page, = PdfReader(pdf).pages
    text = page.extract_text()
    assert "CoC pos-refi | N/A / N/A" in text and text.count("Refinanciación N/A") == 2
    assert "Dictamen real PENDING" in text and "Dictamen simulado" not in text
    assert read_package(package) == saved

    model = json.loads(saved["results.json"])
    states = {(row["scenario"], row["metric_id"]): row["state"] for row in receipt["comparisons"]}
    for name, view in model["scenarios"].items():
        sale = model["calendar_checks"][name][SALE]
        financed = model["calendar_checks"][name][ROUTE]
        terms = settings["rent_inputs"]["calendar_checks"][name][SALE]
        payoff = amount(view["construction_financing"]["construction_principal_payoff"])
        expected_service = RATES[name] * payoff
        reserve = view.get("replacement_reserve_for_sale_only", view["replacement_reserve"])
        deposit = amount(reserve["deposit"])
        released = deposit * amount(reserve["sale_release_fraction"])
        schedule = sale["debt"]["schedule"]
        assert sale["sale"]["date"] == financed["sale"]["date"] == schedule[-1]["date"]
        assert len(schedule) == 4 and amount(sale["sale"]["principal_paid"]) == payoff
        assert all(amount(r["opening"]) == amount(r["closing"]) == payoff
                   and amount(r["service"]) == amount(r["interest"]) == expected_service
                   and amount(r["principal"]) == 0 for r in schedule)
        rows = sale["cash_by_period"]
        construction = [r for r in rows if r["stage"] == "construction"]
        assert construction == [r for r in financed["cash_by_period"] if r["stage"] == "construction"]
        scale = 10 / amount(construction[0]["contribution"])
        assert len([r for r in rows if r["stage"] == "operation"]) == 4
        annual = sum(amount(r["value"]) for r in terms["quarterly_noi_before_reserves"].values())
        operating = [r for r in rows if r["stage"] == "operation"]
        assert sum(amount(r["distribution"]) - amount(r["contribution"]) for r in operating) == annual - deposit - 4 * expected_service
        assert amount(rows[-1]["distribution"]) == (amount(rows[-1]["opening_free"])
            + amount(sale["sale"]["gross"]) - amount(sale["sale"]["cost"]) - payoff + released)
        evidence = receipt["annual_calendar_route"]["scenarios"][name]
        assert evidence["annual_without_refi"] == sale["annual_without_refi"]
        cash = evidence["cash_per_usd_10"]
        assert cash == sale["cash_per_usd_10"] and all(r["stage"] != "refinance" for r in cash["events"])
        received = scale * sum(amount(r["distribution"]) for r in rows)
        contributed = scale * sum(amount(r["contribution"]) for r in rows)
        assert amount(cash["received"]) == received and amount(cash["additional"]) == contributed - 10
        assert amount(cash["unrecovered"]) == max(0, contributed - received)
        assert all(states[name, m] == "N/A" for m in ("equity_recovered", "equity_cash_in", "post_refi_CoC"))
        assert "IRR" in receipt["observed_metrics"][name]
        assert amount(receipt["observed_metrics"][name]["equity_multiple"]["value"]) == received / contributed

        independent = {k: v for k, v in view.items() if k not in (
            "permanent_loan", "construction_refinance", "capacity", "cash_per_usd_10")}
        independent["project_calendar"] = {k: v for k, v in view["project_calendar"].items() if k != "refinance_date"}
        assert json.loads(json.dumps(route_cash(independent, terms), default=rational)) == sale
        bad = deepcopy(terms)
        bad["construction_hold"].pop("maturity_extension")
        assert route_cash(independent, bad)["blocker"] == "construction_loan_matures_before_sale"
        bad = deepcopy(terms)
        next(iter(bad["quarterly_noi_before_reserves"].values()))["value"] = None
        assert route_cash(independent, bad)["blocker"] == "four_documented_noi_quarters_without_refinancing_required"
        bad = deepcopy(terms)
        quarter = next(iter(bad["construction_hold"]["interest_fractions"].values()))
        quarter["value"] = None
        assert route_cash(independent, bad)["blocker"] == "documented_construction_hold_interest_required"
        quarter["value"] = rational(0)
        assert route_cash(independent, bad)["debt"]["schedule"][0]["interest"] == 0
        bad["construction_hold"]["maturity_extension"]["fee_usd"] = rational(1)
        assert route_cash(independent, bad)["blocker"] == "construction_extension_requires_documented_maturity_and_zero_fee"
    assert states["Base", RLV] == "PENDING" and states["Downside", RLV] == "N/A"
    assert receipt["source"]["Base"]["rlv_price_search"]["blocker"] == "rlv_criteria_without_refinance_unconfirmed"
    (root / "recibo.json").write_bytes(encode(receipt))
    return receipt


class AnnualSaleWithoutRefinanceTests(TestCase):
    def test_annual_sale_with_existing_debt_does_not_require_permanent_loan(self):
        with TemporaryDirectory(prefix="miniuw-annual-sale-") as tmp:
            self.assertEqual(verify(Path(tmp))["decision"], "PENDING")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    receipt = verify(args.output)
    print(json.dumps(receipt["annual_pdf"]))
