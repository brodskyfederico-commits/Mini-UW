"""Replay and independently reconcile the v32 Florida tax and USD 10 cash cases."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_reference_package import require
from check_worksheet_definition_screening_D193 import approvals_unchanged
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_technical_acceptance_D200 import cash_summary, settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, WORKBOOK_FLORIDA_TAX_SCHEMA, encoded, read_package, verify_package
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from reconcile_worksheet_D179 import exact
from worksheet_documented_finance_D147 import review_documents
from worksheet_florida_tax_D203 import POLICY, SCOPE
from worksheet_intake_D198 import assemble, prepare, register


ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "templates/synthetic-florida-tax-settings-D203.json"


def roll(value, *, treatment="confirmed_no_change", when=None):
    return dict(just_value=rational(value), school_taxable_value=rational(value), assessment_treatment=treatment,
                event_date=when, valuation_ref="SYNTHETIC-D203-roll-valuation", event_ref="SYNTHETIC-D203-event-record")


def settings_for_tax():
    settings = settings_for_acceptance()
    settings["schema"] = WORKBOOK_FLORIDA_TAX_SCHEMA
    inputs = settings["rent_inputs"]
    # D199's separate calendar experiment includes its own pre-opening levy.
    # These M2 runs only measure the ad valorem changes in the main lifecycle.
    for key in ("calendar_checks", "property_tax", "buyer_forward_property_tax"):
        inputs.pop(key)
    rate = dict(school_mills=rational(4), non_school_mills=rational(9),
                source_ref="SYNTHETIC-D203-separated-certified-millage-example")
    seller = {
        "Base": {"2027": roll(2_000_000), "2028": roll(2_500_000), "2029": roll(2_800_000)},
        "Downside": {"2027": roll(2_000_000),
                     "2028": roll(3_000_000, treatment="qualifying_improvement_reset", when="2027-12-31"),
                     "2029": roll(3_200_000), "2030": roll(3_300_000)},
    }
    scenarios = {}
    for name, year, buyer_value in (("Base", 2029, 3_500_000), ("Downside", 2030, 3_300_000)):
        sale_date = inputs["supplemental_scope"][name]["sale_date"]["value"]
        coc = inputs["post_refinance_coc"][name]
        # Explicit synthetic NOI before property tax and after reserves for the post-refi quarter.
        coc.pop("period_noi")
        coc["period_noi_before_property_tax"] = rational(118_000 if name == "Base" else 76_000)
        coc["noi_source_ref"] = f"SYNTHETIC-D203-{name}-post-refi-before-property-tax"
        scenarios[name] = dict(
            classification="art_VII_4h", classification_ref=f"SYNTHETIC-D203-{name}-parcel-classification",
            scope=SCOPE, scope_ref=f"SYNTHETIC-D203-{name}-taxability-inventory",
            source_ref=f"SYNTHETIC-D203-{name}-dated-rolls",
            opening_assessment=dict(tax_year=2026, non_school_assessed_value=rational(1_500_000),
                                    source_ref=f"SYNTHETIC-D203-{name}-2026-opening-roll"),
            rolls=dict(seller=seller[name],
                       buyer={str(year): roll(buyer_value, treatment="ownership_or_control_reset", when=sale_date)},
                       millage={str(roll_year): rate.copy() for roll_year in range(2027, year + 1)}))
    inputs["florida_property_tax"] = dict(policy=POLICY, scenarios=scenarios)
    return settings


def cash_by_event(view):
    return {row["event_id"]: (row["date"], exact(row["amount"])) for row in view["cash_per_usd_10"]["events"]}


def check_calculated(model, historic, name):
    view = model["scenarios"][name]
    require(view["cash_per_usd_10"] is not None, f"{name} calculation blocked: {view['blockers']}")
    periods = view["noi_by_period"]
    # Independent calendar arithmetic from the fixture values. Seller sizing
    # windows keep the seller basis, while forward exit crosses into buyer reset.
    if name == "Base":
        seller_2028 = Q(2_500_000 * 4 + 1_653_750 * 9, 1000)
        seller_2029 = Q(2_800_000 * 4, 1000) + Q(1_653_750) * Q(105, 100) * Q(9, 1000)
        operating = seller_2028
        sizing = (seller_2028 + 3 * seller_2029) / 4
        exit_tax = Q(3_500_000 * 13, 1000)
        coc_tax = seller_2028 / 4
        treatment = "confirmed_no_change"
        expected_assessed = 1_653_750
    else:
        seller_2028 = Q(3_000_000 * 13, 1000)
        seller_2029 = Q(3_200_000 * 4 + 3_150_000 * 9, 1000)
        seller_2030 = Q(3_300_000 * 13, 1000)
        operating = (seller_2028 + seller_2029) / 2
        sizing = (3 * seller_2029 + seller_2030) / 4
        exit_tax = (seller_2029 + seller_2030) / 2
        coc_tax = seller_2029 / 4
        treatment = "qualifying_improvement_reset"
        expected_assessed = 3_000_000
    expected = {OPERATING_PERIOD: operating, BANK_PERIOD: sizing, VALUE_PERIOD: sizing, FORWARD_PERIOD: exit_tax}
    for period, tax in expected.items():
        details = periods[period]
        prior = historic["noi_by_period"][period]
        key = "buyer_property_tax" if period == FORWARD_PERIOD else "property_tax"
        value = details[key]
        old_tax = exact(prior[key]["total" if period == FORWARD_PERIOD else "annual_tax"])
        require(exact(value["total"]) == tax == exact(value["school_tax"]) + exact(value["non_school_tax"])
                and exact(details["noi"]) == exact(prior["noi"]) + old_tax - tax,
                f"{name} {period}: tax or NOI does not reconcile")
    op_roll = periods[OPERATING_PERIOD]["property_tax"]["rolls"][0]
    require(op_roll["assessment_treatment"] == treatment and exact(op_roll["non_school_assessed_value"]) == expected_assessed,
            f"{name}: cap or improvement reset was lost")
    buyer_roll = periods[FORWARD_PERIOD]["buyer_property_tax"]["rolls"][-1]
    require(buyer_roll["assessment_treatment"] == "ownership_or_control_reset" and buyer_roll["cap"] is None
            and buyer_roll["non_school_assessed_value"] == buyer_roll["just_value"], f"{name}: buyer inherited seller cap")
    coc = view["post_refinance_coc"]
    require(exact(view["post_refinance_tax"]["total"]) == coc_tax
            and exact(coc["period_noi"]) == exact(coc["source"]["period_noi_before_property_tax"]) - coc_tax
            and exact(coc["value"]) == (exact(coc["period_noi"]) - exact(coc["scheduled_debt_service"]))
            / exact(coc["equity_still_invested"]), f"{name}: CoC omitted tax")
    require(exact(view["capacity"]["bank_noi"]) == exact(periods[BANK_PERIOD]["noi"]), "Bank sizing used a different NOI")
    sale = view["valuation_and_sale"]
    require(exact(sale["refinance_value"]) == exact(periods[VALUE_PERIOD]["noi"]) / exact(sale["refinance_cap"])
            and exact(view["gross_sale"]) == exact(periods[FORWARD_PERIOD]["noi"]) / exact(sale["exit_cap"]),
            "Refinance or exit valuation omitted tax")
    events, prior_events = cash_by_event(view), cash_by_event(historic)
    scale = exact(view["cash_per_usd_10"]["scale_factor"])
    op_difference = exact(periods[OPERATING_PERIOD]["noi"]) - exact(historic["noi_by_period"][OPERATING_PERIOD]["noi"])
    sale_difference = exact(view["gross_sale"]) - exact(historic["gross_sale"])
    require(all(events[key] == prior_events[key] for key in events.keys() - {"operating", "sale"})
            and events["operating"][1] - prior_events["operating"][1] == scale * op_difference
            and events["sale"][1] - prior_events["sale"][1] == scale * sale_difference * (1 - exact(sale["sale_cost_fraction"])),
            "Cash changes do not reconcile to the tax change")
    return dict(cash_per_usd_10=cash_summary(view["cash_per_usd_10"]), prior_cash_per_usd_10=cash_summary(historic["cash_per_usd_10"]),
                taxes={key: rational(tax) for key, tax in expected.items()},
                seller_first_operating_roll=op_roll, buyer_reset_roll=buyer_roll,
                capacity=rational(exact(view["capacity"]["maximum_principal_capacity"])),
                gross_sale=view["gross_sale"], delta_receipts_per_usd_10=rational(
                    exact(view["cash_per_usd_10"]["total_distributions"]) -
                    exact(historic["cash_per_usd_10"]["total_distributions"])))


def verify(output):
    output.mkdir(exist_ok=True)
    sources = source_files(output / "sources")
    fiscal = settings_for_tax()
    require(SETTINGS.read_bytes() == encoded(fiscal), "Published settings drift")
    legacy = settings_for_acceptance()
    registration = register(sources, "SYNTHETIC-D203-FL")
    case_raw, _ = prepare(fiscal, registration)
    document_case = json.loads(case_raw)
    docs = review_documents(document_case, sources["plan_raw"], evidence_raw=sources["evidence_raw"], evidence_milestone="D162")

    def reuse_documents(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(all(candidate[key] == document_case[key] for key in ("workbook_sha256", "local_sources"))
                and plan_raw == sources["plan_raw"] and evidence_raw == sources["evidence_raw"]
                and evidence_milestone == "D162", "Fiscal-only test changed underlying finance documents")
        return deepcopy(docs)

    def run(settings, label):
        path = output / label
        assemble(settings, registration, sources, path)
        saved = read_package(path)
        model = json.loads(saved["results.json"])
        approvals_unchanged(model)
        audit = verify_package(path, current_revision_raw=saved[CURRENT_REVISION_FILE])
        require(audit["audit_bot"] == "B16" and audit["page_count"] == 1, "Output did not replay as a one-page case")
        return model, audit, saved["MiniUW_Resumen.pdf"]

    model, audit, report = run(fiscal, "florida")
    require(audit["vigencia"] == "VIGENTE" and "D203" in pdf_text(report), "Florida evidence did not replay")
    with patch("worksheet_documented_finance_D147.review_documents", reuse_documents):
        previous, _, prior_report = run(legacy, "prior-method")
        require(prior_report == (ROOT / "docs/review/MiniUW_Informe_USD10_D200.pdf").read_bytes(),
                "Archived D200 PDF changed")
        checks = {name: check_calculated(model, view, name) for name, view in previous["scenarios"].items()}
        missing = [
            ("missing-opening", ("opening_assessment", "non_school_assessed_value"),
             "M2:prior_roll:non_school_assessed_value_missing_or_invalid"),
            ("missing-millage", ("rolls", "millage", "2029", "non_school_mills"),
             "M2:millage:2029:non_school_mills_missing_or_invalid"),
            ("missing-reset-evidence", ("rolls", "seller", "2028", "event_ref"),
             "M2:seller:2028:event_ref_missing"),
            ("missing-buyer-appraisal", ("rolls", "buyer", "2030", "just_value"),
             "M2:buyer:2030:just_value_missing_or_invalid"),
        ]
        variants = {}
        for label, path, blocker in missing:
            config = deepcopy(fiscal)
            parent = config["rent_inputs"]["florida_property_tax"]["scenarios"]["Downside"]
            for key in path[:-1]:
                parent = parent[key]
            parent.pop(path[-1])
            blocked, verification, pdf = run(config, label)
            require(blocked["scenarios"]["Downside"]["cash_per_usd_10"] is None
                    and blocked["scenarios"]["Downside"]["blockers"] == [blocker]
                    and blocked["scenarios"]["Base"]["cash_per_usd_10"] == model["scenarios"]["Base"]["cash_per_usd_10"]
                    and verification["vigencia"] == verification["simulation_result"] == "PENDING"
                    and "Downside | Caja PENDING: evidencia fiscal M2" in pdf_text(pdf), f"{label}: missing evidence was used")
            variants[label] = blocker

    from worksheet_florida_tax_D203 import assessed_value
    record = roll(2_000_000)
    for year, expected in ((2026, 1_650_000), (2027, 1_575_000)):
        require(assessed_value(record, year, Q(1_500_000), "art_VII_4h", "seller", None)["non_school_assessed_value"]
                == expected, "Cap effective-date boundary failed")
    require(assessed_value(roll(900_000), 2027, Q(1_500_000), "art_VII_4h", "seller", None)["non_school_assessed_value"]
            == 900_000, "Assessment exceeded just value")
    return dict(status="passed", decision="PENDING", deployment_enabled=False, real_decisions_enabled=False,
                observed_simulation=audit["simulation_result"], scenarios=checks, missing_evidence=variants,
                pdf_sha256=sha256(report).hexdigest())


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d203-") as temporary:
        print(json.dumps(verify(args.output or Path(temporary)), ensure_ascii=False, sort_keys=True))
