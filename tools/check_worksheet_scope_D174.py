"""Verify the supplemental inputs that extend the original 55-field pilot."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

from check_operating_replay_D20 import ROOT, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_pdf_D157 import run_package
from check_worksheet_formula_review_D173 import FIXTURE as PRIOR, REVISION as PRIOR_CURRENT, pdf_text
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_SUPPLEMENTAL_SCOPE_SCHEMA, build_results, encoded
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from worksheet_documented_finance_D147 import review_documents
from worksheet_revision_D128 import snapshot_for_case
from worksheet_scope_D174 import PROFILE


CASE = ROOT / "templates/synthetic-workbook-supplemental-scope-D174.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D174.json"


def case_for():
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_SUPPLEMENTAL_SCOPE_SCHEMA
    inputs = case["rent_inputs"]
    stress = inputs["policy"].pop("bank_vacancy_addition")
    scope = {}
    for name, fixed in (("Base", 10000), ("Downside", 0)):
        def claim(value, kind):
            return dict(value=value, source_ref=f"SYNTHETIC-D174-{name}-{kind}")

        scope[name] = dict(sale_date=claim(inputs["buyer_forward_property_tax"][name]["window_start"], "sale-date"),
                           maturity_payments=claim(inputs["permanent_loan"]["scenarios"][name]["maturity_payments"], "maturity"),
                           fixed_sale_cost=claim(rational(fixed), "fixed-sale-cost"),
                           bank_vacancy_addition=claim(stress, "bank-stress"),
                           live_local=dict(applicability="not_applicable", source_ref=f"SYNTHETIC-D174-{name}-program"))
    scope["Downside"]["downside_scope"] = dict(
        basis="explicit_combined_scenario_workbook", source_ref="SYNTHETIC-D174-integrated-downside",
        base_workbook_sha256=case["workbook_sha256"]["Base"], downside_workbook_sha256=case["workbook_sha256"]["Downside"])
    inputs["supplemental_scope"] = scope
    return case


def verify(temp, output):
    case = case_for()
    current = encoded(snapshot_for_case(case, "SYNTHETIC-D174-current"))
    require(CASE.read_bytes() == encoded(case) and CURRENT.read_bytes() == current, "Supplemental fixture drift")
    raw = shuffled_pdf()
    evidence = temp / "Evidence.pdf"
    evidence.write_bytes(raw)
    run_package(PRIOR, PRIOR_CURRENT, evidence, temp / "D173")
    before = json.loads((temp / "D173/results.json").read_bytes())
    status = run_package(CASE, CURRENT, evidence, output)
    result = json.loads((output / "results.json").read_bytes())
    audit = call("audit", output, "--current-revision", CURRENT)
    require(result["profile"] == PROFILE and result["decision"] == "PENDING" and result["simulation_result"] == "FAIL"
            and not result["deployment_enabled"] and not result["real_decisions_enabled"]
            and audit["vigencia"] == "VIGENTE" and audit["pdf_sha256"] == status["pdf_sha256"],
            "Supplemental case failed the current audit or synthetic guard")
    require("D174" in pdf_text((output / "MiniUW_Resumen.pdf").read_bytes()), "Missing milestone in PDF")

    for name, view in result["scenarios"].items():
        old = before["scenarios"][name]
        scope = view["supplemental_scope"]
        pricing = view["valuation_and_sale"]
        require(view["project_calendar"]["sale_date"] == scope["sale_date"]["value"]
                and view["project_calendar"]["sale_source_ref"] == scope["sale_date"]["source_ref"]
                and view["permanent_loan"]["maturity_payments"] == scope["maturity_payments"]["value"]
                and view["permanent_loan"]["supplemental_maturity_ref"] == scope["maturity_payments"]["source_ref"],
                f"{name}: missing sale or loan provenance")
        fixed = amount(scope["fixed_sale_cost"]["value"])
        cash = view["cash_per_usd_10"]
        require(view["gross_sale"] == old["gross_sale"]
                and amount(pricing["sale_cost"]) - amount(old["valuation_and_sale"]["sale_cost"]) == fixed
                and amount(old["cash_per_usd_10"]["total_distributions"]) - amount(cash["total_distributions"])
                    == fixed * amount(cash["scale_factor"]), f"{name}: fixed cost did not flow through once")
        require(view["capacity"]["maximum_principal_capacity"] == old["capacity"]["maximum_principal_capacity"],
                f"{name}: identical stress changed capacity")

    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()
    documents = review_documents(case, plan, evidence_raw=raw, evidence_milestone="D162")

    def replay(edit):
        modified = deepcopy(case)
        edit(modified["rent_inputs"]["supplemental_scope"]["Downside"])
        revision = encoded(snapshot_for_case(modified, "SYNTHETIC-D174-test"))
        def unchanged_documents(candidate, plan_raw, *, evidence_raw, evidence_milestone):
            require(candidate["local_sources"] == case["local_sources"] and plan_raw == plan
                    and sha(evidence_raw) == case["local_sources"]["evidence_pdf"]["sha256"]
                    and evidence_milestone == "D162", "A supplemental variant changed the source documents")
            return deepcopy(documents)

        with patch("worksheet_documented_finance_D147.review_documents", side_effect=unchanged_documents):
            replayed, _ = build_results(encoded(modified), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                        current_revision_raw=revision, plan_raw=plan, evidence_raw=raw)
        require(replayed["decision"] == "PENDING" and replayed["scenarios"]["Base"] == result["scenarios"]["Base"],
                "Downside input changed Base or the decision guard")
        return replayed

    for edit, reason in (
        (lambda scope: scope.pop("sale_date"), "supplemental_scenario_scope_incomplete"),
        (lambda scope: scope["sale_date"].update(value="2029-09-30"), "declared_sale_date_outside_supported_quarterly_hold"),
        (lambda scope: scope["maturity_payments"].update(value=7), "permanent_maturity_evidence_and_loan_terms_disagree"),
        (lambda scope: scope["fixed_sale_cost"].update(value=None), "explicit_fixed_sale_cost_required"),
        (lambda scope: scope["bank_vacancy_addition"].update(value=None), "explicit_bank_vacancy_stress_required"),
        (lambda scope: scope["downside_scope"].update(downside_workbook_sha256="0" * 64), "integrated_downside_scope_unconfirmed"),
        (lambda scope: scope["live_local"].update(applicability="applicable"), "live_local_program_and_eligibility_pending"),
    ):
        replayed = replay(edit)
        down = replayed["scenarios"]["Downside"]
        require(replayed["simulation_result"] == "PENDING" and down["cash_per_usd_10"] is None and reason in down["blockers"],
                f"Missing supplemental gate: {reason}")

    down = replay(lambda scope: scope["bank_vacancy_addition"].update(value=rational(0)))["scenarios"]["Downside"]
    original = result["scenarios"]["Downside"]
    require(amount(down["capacity"]["bank_noi"]) > amount(original["capacity"]["bank_noi"])
            and down["noi_by_period"][VALUE_PERIOD] == original["noi_by_period"][VALUE_PERIOD]
            and amount(down["noi_by_period"][BANK_PERIOD]["loss_fraction"])
                < amount(original["noi_by_period"][BANK_PERIOD]["loss_fraction"]),
            "The explicit zero bank stress did not flow only to the bank NOI")
    return dict(status="passed", decision="PENDING", page_count=1, pending_cases=7,
                pdf_sha256=status["pdf_sha256"], explicit_zero_cases=2)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d174-") as folder:
        temp = Path(folder)
        print(json.dumps(verify(temp, args.output or temp / "D174"), sort_keys=True))


if __name__ == "__main__":
    main()
