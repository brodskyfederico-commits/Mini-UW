"""Audit staged PRELIMINAR with M2 tax in lending, operating cash and exit."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from check_reference_package import require
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_preliminary_stages_D188 import BOOKS, CASE, DEAL, SCENARIOS
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import PRELIMINARY_FLORIDA_TAX_SCHEMA, build_results, encoded, verify_package
from reconcile_worksheet_D179 import exact
from worksheet_florida_tax_D203 import POLICY, SCOPE


FIXTURE = CASE.with_name("synthetic-preliminary-florida-tax-D204.json")


def fixture():
    case = json.loads(CASE.read_bytes())
    case["schema"] = PRELIMINARY_FLORIDA_TAX_SCHEMA
    fiscal = {}
    for name in SCENARIOS:
        seller_2028 = dict(just_value=rational(285_000 if name == "Base" else 265_000),
                           school_taxable_value=rational(285_000 if name == "Base" else 265_000),
                           assessment_treatment="confirmed_no_change" if name == "Base" else "qualifying_improvement_reset",
                           event_date=None if name == "Base" else "2027-09-29",
                           valuation_ref=f"SYNTHETIC-D204-{name}-2028-just-value",
                           event_ref=f"SYNTHETIC-D204-{name}-2028-event")
        buyer_value = 330_000 if name == "Base" else 285_000
        fiscal[name] = dict(
            classification="art_VII_4h", classification_ref=f"SYNTHETIC-D204-{name}-property-classification",
            scope=SCOPE, scope_ref=f"SYNTHETIC-D204-{name}-assessments-in-scope",
            source_ref=f"SYNTHETIC-D204-{name}-fiscal-assumptions",
            owner="Equipo sintético LOI", as_of=case["as_of"],
            opening_assessment=dict(tax_year=2027, non_school_assessed_value=rational(180_000),
                                    source_ref=f"SYNTHETIC-D204-{name}-2027-roll"),
            rolls=dict(seller={"2028": seller_2028},
                       buyer={"2029": dict(just_value=rational(buyer_value), school_taxable_value=rational(buyer_value),
                                           assessment_treatment="ownership_or_control_reset", event_date=case["dates"][-1],
                                           valuation_ref=f"SYNTHETIC-D204-{name}-2029-buyer-value",
                                           event_ref=f"SYNTHETIC-D204-{name}-sale-projection")},
                       millage={str(year): dict(school_mills=rational(4), non_school_mills=rational(9),
                                               source_ref=f"SYNTHETIC-D204-{name}-{year}-millage")
                                for year in (2028, 2029)}))
    case["florida_property_tax"] = dict(policy=POLICY, scenarios=fiscal)
    return case


def normalized(view):
    return [(row["date"], row["category"], exact(row["amount"])) for row in view["cash"]["events"]]


def verify_portfolio(model, case):
    require(model["state"] == "PRELIMINAR" and model["decision"] == model["simulation_result"] == "PENDING"
            and not model["deployment_enabled"] and not model["real_decisions_enabled"] and not model["full_uw_eligible"],
            "PRELIMINAR changed the decision or deployment gate")
    pair = model["deals"][DEAL]["scenarios"]
    checks = {}
    dates = case["dates"]
    for name, school, non_school, buyer, prior_bank, prior_sizing, prior_operating, prior_sale in (
        ("Base", 285_000, 189_000, 330_000, Q("35622.8"), Q(37196), Q(6799), Q(273562)),
        ("Downside", 265_000, 265_000, 285_000, Q("24321.98"), Q("25659.2"), Q("4414.8"), Q("88947.8")),
    ):
        # Independent reconstruction from the accepted D188 dated cash and declared fiscal figures.
        view = pair[name]
        finance = view["financing"]
        seller_tax = Q(school * 4 + non_school * 9, 1000)
        buyer_tax = Q(buyer * 13, 1000)
        old_tax = Q(2000)
        cap = Q(1, 10) if name == "Base" else Q(16, 100)
        sale_cost = Q(5, 100) if name == "Base" else Q(6, 100)
        require(exact(finance["bank_noi"]) == prior_bank + old_tax - seller_tax
                and exact(finance["refinance_value"]) == (prior_sizing + old_tax - seller_tax) / Q("0.16"),
                f"{name}: M2 tax did not reach lender and valuation NOI")
        tax = view["florida_property_tax"]
        require(exact(tax["refinance"]["total"]) == seller_tax and exact(tax["sale"]["total"]) == buyer_tax
                and all(exact(tax[when]["total"]) == seller_tax / 4 for when in dates[4:]),
                f"{name}: annual or quarterly fiscal trace differs")
        cap_roll = tax["refinance"]["rolls"][0]
        buyer_roll = tax["sale"]["rolls"][0]
        require(exact(cap_roll["non_school_assessed_value"]) == non_school
                and exact(cap_roll["school_taxable_value"]) == school
                and buyer_roll["cap"] is None and buyer_roll["owner"] == "buyer"
                and exact(buyer_roll["non_school_assessed_value"]) == buyer,
                f"{name}: assessment basis differs")
        events = normalized(view)
        operating = prior_operating + (old_tax - seller_tax) / 4
        sale = prior_sale + (old_tax - buyer_tax) / cap * (1 - sale_cost)
        require([(date, value) for date, kind, value in events if kind == "operating_distribution"] ==
                [(date, operating / 10500) for date in dates[4:]]
                and events[-1] == (dates[-1], "net_sale_distribution", sale / 10500),
                f"{name}: operating or sale cash per USD 10 differs")
        cash = view["cash"]
        checks[name] = dict(additional=round(float(exact(cash["total_contributions"]) - 10), 2),
                            received=round(float(exact(cash["total_distributions"])), 2),
                            unrecovered=round(float(exact(cash["unrecovered_after_sale"])), 2),
                            seller_tax=rational(seller_tax), buyer_tax=rational(buyer_tax),
                            dated_cash=cash["events"])
    require(model["ranking"] == [dict(deal_id=DEAL, position=1, downside_equity_multiple=pair["Downside"]["cash"]["equity_multiple"])],
            "Ranking did not use the recomputed Downside cash")
    return checks


def verify(output):
    case = fixture()
    require(FIXTURE.read_bytes() == encoded(case), "Published fiscal fixture drift")
    subprocess.run([sys.executable, str(CASE.parents[1] / "tools/miniuw_worksheet_v1.py"), "run", str(FIXTURE),
                    "--workbook", str(BOOKS["Base"]), "--downside-workbook", str(BOOKS["Downside"]),
                    "--output", str(output)], check=True, capture_output=True)
    audited = verify_package(output)
    model = json.loads((output / "results.json").read_bytes())
    report = (output / "MiniUW_Resumen.pdf").read_bytes()
    require(audited["state"] == "PRELIMINAR" and audited["pdf_sha256"] == model["pdf_sha256"]
            and "Dictamen formal PENDING" in pdf_text(report), "Source-first replay or one-page report differs")
    checks = verify_portfolio(model, case)
    sources = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes())
    baseline = model["deals"][DEAL]["scenarios"]

    def probe(label, path, value=None, *, blocker):
        revised = deepcopy(case)
        if not path:
            revised.pop("florida_property_tax")
        else:
            target = revised["florida_property_tax"]["scenarios"]["Downside"]
            for part in path[:-1]:
                target = target[part]
            if value is None:
                target.pop(path[-1])
            else:
                target[path[-1]] = value
        pending, pdf = build_results(encoded(revised), **sources)
        pair = pending["deals"][DEAL]["scenarios"]
        require(pending["state"] == pending["decision"] == "PENDING" and not pending["ranking"]
                and pair["Downside"]["cash"] is None and blocker in pair["Downside"]["blockers"][0]
                and (pair["Base"] == baseline["Base"] if path else pair["Base"]["cash"] is None)
                and "Fuera del ranking" in pdf_text(pdf), f"{label}: unexpected decision, cash or ranking")
        restored, restored_pdf = build_results(encoded(case), **sources)
        require(restored == model and restored_pdf == report, f"{label}: restored evidence did not replay")
        return pair["Downside"]["blockers"][0]

    probes = {
        "missing_tax_submission": probe("fiscal", (), blocker="M2"),
        "missing_millage": probe("millage", ("rolls", "millage", "2028", "non_school_mills"),
                                 blocker="M2:millage:2028:non_school_mills"),
        "undated_reset": probe("reset", ("rolls", "seller", "2028", "event_date"), blocker="M2:seller:2028:reset_date"),
        "missing_buyer_valuation": probe("buyer", ("rolls", "buyer", "2029", "just_value"), blocker="M2:buyer:2029:just_value"),
        "future_evidence": probe("future", ("as_of",), "2027-02-02", blocker="M2"),
        "tax_breaks_capacity": probe("capacity", ("rolls", "millage", "2028", "non_school_mills"),
                                    rational(30), blocker="supera capacidad"),
    }
    from check_worksheet_preliminary_stages_D188 import workbook
    without_proxy = deepcopy(case)
    blank = workbook("Downside", {"C62": {}})
    from miniuw_foundation.scheduled_expense_case import sha
    without_proxy["scenarios"]["Downside"]["workbook_sha256"] = sha(blank)
    no_proxy, _ = build_results(encoded(without_proxy), **(sources | {"downside_workbook_raw": blank}))
    require(no_proxy["state"] == "PRELIMINAR"
            and normalized(no_proxy["deals"][DEAL]["scenarios"]["Downside"]) == normalized(baseline["Downside"]),
            "Blank legacy C62 changed the M2 projection")
    zero = deepcopy(case)
    zero["florida_property_tax"]["scenarios"]["Downside"]["rolls"]["millage"]["2028"]["non_school_mills"] = rational(0)
    zero_model, _ = build_results(encoded(zero), **sources)
    zero_view = zero_model["deals"][DEAL]["scenarios"]["Downside"]
    require(zero_model["state"] == "PRELIMINAR" and exact(zero_view["florida_property_tax"]["refinance"]["non_school_tax"]) == 0
            and exact(zero_view["florida_property_tax"]["refinance"]["school_tax"]) == 1060,
            "Explicit zero for non-school millage was treated as missing or affected school tax")
    prior, _ = build_results(CASE.read_bytes(), **sources)
    require(prior["state"] == "PRELIMINAR" and all(
        exact(prior["deals"][DEAL]["scenarios"][name]["cash"]["total_distributions"]) == total
        for name, total in (("Base", Q(328558, 10500)), ("Downside", Q(106607, 10500)))),
        "Archived D188 comparison changed")
    return dict(status="passed", decision="PENDING", ranking=model["ranking"], scenarios=checks, probes=probes,
                explicit_zero_millage_verified=True, blank_legacy_C62_verified=True,
                pdf_sha256=model["pdf_sha256"], deployment_enabled=False, real_decisions_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d204-") as temp:
        print(json.dumps(verify(args.output or Path(temp) / "case"), ensure_ascii=False, sort_keys=True))
