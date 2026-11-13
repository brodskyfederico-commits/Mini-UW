"""Replay the worksheet with buyer taxes, a scoped CoC, and the revised LP/GP PDF."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_pdf_D157 import run_package
from check_worksheet_gp_catch_up_D170 import PRIOR_TERMS, TERMS, render, split
from check_worksheet_market_evidence_D166 import BOOKS, CASE, CURRENT, PLAN, shuffled_pdf
from check_worksheet_return_metrics_D167 import verify as verify_d167
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_FORMULA_REVIEW_SCHEMA, build_results, encoded
from plan_return_D107 import FORWARD_PERIOD
from worksheet_documented_finance_D147 import review_documents
from worksheet_formula_review_D173 import BUYER_BASIS, COC_BASIS, PROFILE
from worksheet_revision_D128 import snapshot_for_case


FIXTURE = ROOT / "templates/synthetic-workbook-formula-review-D173.json"
REVISION = ROOT / "templates/synthetic-workbook-current-revision-D173.json"


def fixture(previous):
    case = deepcopy(previous["case"])
    case["schema"] = WORKBOOK_FORMULA_REVIEW_SCHEMA
    inputs = case["rent_inputs"]
    inputs["buyer_forward_property_tax"] = {}
    inputs["post_refinance_coc"] = {}
    for name, (school, non_school, noi, equity) in {
        "Base": (30000, 45000, 100000, 630000),
        "Downside": (25000, 45000, 60000, 850000),
    }.items():
        calendar = previous["results"]["scenarios"][name]["project_calendar"]
        inputs["buyer_forward_property_tax"][name] = dict(
            basis=BUYER_BASIS, currency="USD", window_start=calendar["sale_date"], window_end=calendar["exit_forward_end"],
            school_tax=rational(school), non_school_tax=rational(non_school), source_ref=f"SYNTHETIC-D173-{name}-buyer-tax")
        inputs["post_refinance_coc"][name] = dict(
            basis=COC_BASIS, currency="USD", window_start=calendar["refinance_date"], window_end=calendar["sale_date"],
            period_noi=rational(noi), noi_source_ref=f"SYNTHETIC-D173-{name}-post-refinance-period-noi",
            equity_still_invested=rational(equity), equity_source_ref=f"SYNTHETIC-D173-{name}-capital-snapshot")
    return case


def read(path):
    return json.loads(path.read_bytes())


def pdf_text(raw):
    reader = PdfReader(BytesIO(raw))
    require(len(reader.pages) == 1, "The summary must remain one page")
    return reader.pages[0].extract_text()


def verify(temp, package, output):
    evidence_raw = shuffled_pdf()
    evidence = temp / "Evidence.pdf"
    evidence.write_bytes(evidence_raw)
    if package is None:
        package = temp / "D166"
        run_package(CASE, CURRENT, evidence, package)
    verified, _ = verify_d167(package, CURRENT.read_bytes())
    previous = read(package / "results.json")
    case = fixture(dict(case=read(CASE), results=previous))
    current = encoded(snapshot_for_case(case, "SYNTHETIC-D173-current"))
    require(FIXTURE.read_bytes() == encoded(case) and REVISION.read_bytes() == current, "D173 fixture drift")
    status = run_package(FIXTURE, REVISION, evidence, output / "D173")
    result = read(output / "D173/results.json")
    require(result["profile"] == PROFILE and result["simulation_result"] == "FAIL" and result["decision"] == "PENDING"
            and not result["real_decisions_enabled"] and not result["deployment_enabled"], "The synthetic guard failed")
    audit = call("audit", output / "D173", "--current-revision", REVISION)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["pdf_sha256"] == status["pdf_sha256"],
            "B16 could not reproduce D173")
    display = pdf_text((output / "D173/MiniUW_Resumen.pdf").read_bytes())
    require(display.count("Impuesto comprador") == 2 and display.count("CoC del tramo") == 2, "PDF lost the revised definitions")

    for name, view in result["scenarios"].items():
        old = previous["scenarios"][name]
        tax = view["valuation_and_sale"]["buyer_property_tax"]
        new_forward = view["noi_by_period"][FORWARD_PERIOD]
        old_forward = old["noi_by_period"][FORWARD_PERIOD]
        delta_tax = amount(tax["total"]) - amount(old_forward["property_tax"]["annual_tax"])
        cap = amount(view["valuation_and_sale"]["exit_cap"])
        price_reduction = delta_tax / cap
        cash = view["cash_per_usd_10"]
        old_cash = old["cash_per_usd_10"]
        scale = amount(cash["scale_factor"])
        costs = amount(view["valuation_and_sale"]["sale_cost_fraction"])
        require(delta_tax > 0 and tax == new_forward["buyer_property_tax"]
                and amount(new_forward["noi"]) == amount(old_forward["noi"]) - delta_tax
                and amount(view["gross_sale"]) == amount(old["gross_sale"]) - price_reduction
                and amount(old_cash["total_distributions"]) - amount(cash["total_distributions"]) == scale * price_reduction * (1 - costs),
                f"{name}: buyer tax did not reconcile through value, costs and distributions")
        require(view["capacity"] == old["capacity"] and view["dated_debt_service"] == old["dated_debt_service"]
                and view["construction_refinance"] == old["construction_refinance"]
                and {k: v for k, v in view["noi_by_period"].items() if k != FORWARD_PERIOD}
                    == {k: v for k, v in old["noi_by_period"].items() if k != FORWARD_PERIOD},
                f"{name}: tax changed the seller operating or financing cash")
        require([e for e in cash["events"] if e["category"] != "net_sale_distribution"]
                == [e for e in old_cash["events"] if e["category"] != "net_sale_distribution"],
                f"{name}: non-sale cash events changed")
        coc = view["post_refinance_coc"]
        require(coc["state"] == "checked_synthetic" and not coc["annualized"]
                and amount(coc["value"]) * amount(coc["equity_still_invested"])
                    == amount(coc["period_noi"]) - amount(view["dated_debt_service"]["scheduled_service_due"]),
                f"{name}: CoC did not reconcile to period NOI, debt service and declared equity")

    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()
    documents = review_documents(case, plan, evidence_raw=evidence_raw, evidence_milestone="D162")

    def unchanged_documents(modified, plan_raw, *, evidence_raw, evidence_milestone):
        require(modified["local_sources"] == case["local_sources"] and plan_raw == plan
                and sha(evidence_raw) == case["local_sources"]["evidence_pdf"]["sha256"]
                and evidence_milestone == "D162", "A formula variant changed the unchanged document inputs")
        return deepcopy(documents)

    def replay(section, edit, *, use_current=False):
        modified = deepcopy(case)
        record = modified["rent_inputs"][section]["Downside"]
        edit(record)
        revision = current if use_current else encoded(snapshot_for_case(modified, "SYNTHETIC-D173-test"))
        with patch("worksheet_documented_finance_D147.review_documents", side_effect=unchanged_documents):
            replayed, _ = build_results(encoded(modified), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                        current_revision_raw=revision, plan_raw=plan, evidence_raw=evidence_raw)
        require(replayed["decision"] == "PENDING" and replayed["scenarios"]["Base"] == result["scenarios"]["Base"],
                "An edit in Downside changed Base or the decision guard")
        return replayed, replayed["scenarios"]["Downside"]

    tax_section = "buyer_forward_property_tax"
    coc_section = "post_refinance_coc"
    for section, key, value, reason in (
        (tax_section, "non_school_tax", None, "buyer_forward_property_tax_components_unconfirmed"),
        (tax_section, "window_start", "2029-07-01", "buyer_forward_property_tax_source_or_window_unconfirmed"),
        (coc_section, "equity_still_invested", rational(0), "post_refi_noi_debt_service_or_positive_remaining_equity_unconfirmed"),
        (coc_section, "period_noi", None, "post_refi_noi_debt_service_or_positive_remaining_equity_unconfirmed"),
        (coc_section, "basis", "gross_contributions", "post_refi_noi_and_equity_evidence_or_window_unconfirmed"),
    ):
        replayed, down = replay(section, lambda record: record.update({key: value}))
        require(replayed["simulation_result"] == "PENDING", "Incomplete definition produced a simulated verdict")
        if section == tax_section:
            require(down["cash_per_usd_10"] is None and reason in down["blockers"], "Missing buyer tax allowed sale cash")
        else:
            require(down["cash_per_usd_10"] == result["scenarios"]["Downside"]["cash_per_usd_10"]
                    and down["post_refinance_coc"]["value"] is None and reason in down["post_refinance_coc"]["blockers"],
                    "Missing CoC evidence altered cash or produced a ratio")

    replayed, _ = replay(tax_section, lambda row: row.update(school_tax=rational(0)), use_current=True)
    require(replayed["simulation_result"] == "PENDING" and "financial_sources_fingerprint_mismatch"
            in replayed["revision_review"]["blockers"], "Prior approval accepted a change in the buyer tax evidence")
    _, down = replay(tax_section, lambda row: row.update(school_tax=rational(0)))
    require(amount(down["valuation_and_sale"]["buyer_property_tax"]["total"]) == 45000
            and amount(down["gross_sale"]) - amount(result["scenarios"]["Downside"]["gross_sale"])
                == 25000 / amount(down["valuation_and_sale"]["exit_cap"]), "Explicit zero school tax did not flow to valuation")
    service = result["scenarios"]["Downside"]["dated_debt_service"]["scheduled_service_due"]
    _, down = replay(coc_section, lambda row: row.update(period_noi=service))
    require(amount(down["post_refinance_coc"]["value"]) == Fraction(), "An explicit zero cash numerator did not yield zero CoC")

    split_results = split(read(TERMS), read(PRIOR_TERMS), verified)
    revised = render(split_results, formula_review=True)
    display = pdf_text(revised)
    require(all(mark in display for mark in ("USD 19,10 (1,28x)", "USD 6,80 (0,37x)", "USD 14,87", "USD 18,19",
                                            "FAIL simulado")), "LP/GP summary lost the full contribution base")
    (output / "MiniUW_Ejemplo_LP_GP_D173.pdf").write_bytes(revised)
    return dict(status="passed", decision="PENDING", page_count=1, pending_cases=6, explicit_zero_cases=2,
                source_result_sha256=verified["source_result_sha256"], pdf_sha256=status["pdf_sha256"],
                example_pdf_sha256=sha(revised))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Existing D166 output")
    parser.add_argument("--output", type=Path, help="Directory for D173 evidence and both reports")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d173-") as folder:
        temp = Path(folder)
        output = args.output or temp / "reports"
        output.mkdir()
        print(json.dumps(verify(temp, args.package, output), sort_keys=True))


if __name__ == "__main__":
    main()
