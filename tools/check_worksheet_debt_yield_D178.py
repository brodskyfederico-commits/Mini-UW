"""Replay the versioned worksheet with a documented debt yield covenant."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_operating_replay_D20 import ROOT, require
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from check_worksheet_template_version_D176 import CASE as PRIOR, CURRENT as PRIOR_CURRENT
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_worksheet_v1 import WORKBOOK_DEBT_YIELD_SCHEMA, build_results, encoded, verify_package, write_package
from worksheet_debt_yield_D178 import BASIS, LIMIT_ID, PROFILE
from worksheet_documented_finance_D147 import review_documents
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-debt-yield-D178.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D178.json"
SCENARIOS = {"Base": Fraction(1, 10), "Downside": Fraction(3, 20)}


def fixture():
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_DEBT_YIELD_SCHEMA
    evidence = case["local_sources"]["evidence_pdf"]
    case["rent_inputs"]["bank_debt_yield"] = {
        name: dict(source_ref=f"SYNTHETIC-D178-{name}-bank-addendum",
                   quote_document_id=f"SYNTHETIC-D156-BANK-{name}", quote_source_sha256=evidence["sha256"],
                   applicability="applicable", basis=BASIS, minimum=rational(minimum))
        for name, minimum in SCENARIOS.items()
    }
    return case


def verify(temp, output):
    case = fixture()
    revision = encoded(snapshot_for_case(case, "SYNTHETIC-D178-current"))
    require(CASE.read_bytes() == encoded(case) and CURRENT.read_bytes() == revision, "Debt yield fixture drift")
    raw = shuffled_pdf()
    plan = PLAN.read_bytes()
    sources = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                   plan_raw=plan, evidence_raw=raw)
    documents = review_documents(case, plan, evidence_raw=raw, evidence_milestone="D162")

    def checked_documents(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(candidate["workbook_sha256"] == case["workbook_sha256"]
                and candidate["local_sources"] == case["local_sources"]
                and candidate["rent_inputs"]["deal_id"] == case["rent_inputs"]["deal_id"]
                and candidate["rent_inputs"]["as_of_UTC"] == case["rent_inputs"]["as_of_UTC"]
                and plan_raw == plan and evidence_raw == raw and evidence_milestone == "D162",
                "The documents or the case they belong to changed")
        return deepcopy(documents)

    status = write_package(CASE.read_bytes(), output, current_revision_raw=revision, **sources)
    audit = verify_package(output, current_revision_raw=revision)
    result = json.loads((output / "results.json").read_bytes())
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["pdf_sha256"] == status["pdf_sha256"]
            and result["decision"] == "PENDING" and not result["real_decisions_enabled"]
            and not result["deployment_enabled"] and result["profile"] == PROFILE and result["simulation_result"] == "FAIL",
            "Version or synthetic decision guard failed")
    report_text = pdf_text((output / "MiniUW_Resumen.pdf").read_bytes())
    require(report_text.count("Debt yield") == 2 and "D178" in report_text, "Debt yield missing from the single-page PDF")

    def run(candidate, current_revision):
        with patch("worksheet_documented_finance_D147.review_documents", side_effect=checked_documents):
            replayed, _ = build_results(candidate, current_revision_raw=current_revision, **sources)
        return replayed

    previous = run(PRIOR.read_bytes(), PRIOR_CURRENT.read_bytes())
    for name, view in result["scenarios"].items():
        cap = view["capacity"]
        dy = cap["debt_yield"]
        noi, loan = (amount(cap[key], 1300) for key in ("bank_noi", "selected_principal"))
        require(amount(dy["achieved"], 1300) == noi / loan
                and amount(cap["capacity_limits"][LIMIT_ID]) == noi / SCENARIOS[name]
                and cap["maximum_principal_capacity"] == previous["scenarios"][name]["capacity"]["maximum_principal_capacity"],
                f"{name}: wrong NOI, debt yield or non-binding cap")
        require(view["cash_per_usd_10"] == previous["scenarios"][name]["cash_per_usd_10"],
                f"{name}: a non-binding bank condition changed the cash ledger")

    down = result["scenarios"]["Downside"]
    noi = amount(down["capacity"]["bank_noi"], 1300)
    loan = amount(down["capacity"]["selected_principal"])

    def probe(change, *, stale=False):
        candidate = deepcopy(case)
        change(candidate["rent_inputs"]["bank_debt_yield"]["Downside"])
        expected = revision if stale else encoded(snapshot_for_case(candidate, "SYNTHETIC-D178-test"))
        replayed = run(encoded(candidate), expected)
        require(replayed["decision"] == "PENDING" and replayed["scenarios"]["Base"] == result["scenarios"]["Base"],
                "Downside mutation affected Base or the release guard")
        return replayed, replayed["scenarios"]["Downside"]

    _, equal = probe(lambda row: row.update(minimum=rational(noi / loan)))
    require(equal["capacity"]["binding_limit_ids"] == [LIMIT_ID]
            and equal["cash_per_usd_10"] == down["cash_per_usd_10"], "Equality should satisfy a bank minimum")
    dscr_ceiling = amount(down["capacity"]["capacity_limits"]["DSCR"])
    _, tied = probe(lambda row: row.update(minimum=rational(noi / dscr_ceiling)))
    require(tied["capacity"]["binding_limit_ids"] == [LIMIT_ID, "DSCR"]
            and amount(tied["capacity"]["maximum_principal_capacity"]) == dscr_ceiling
            and tied["cash_per_usd_10"] == down["cash_per_usd_10"], "A tie must identify both bank limits")
    blocked, under = probe(lambda row: row.update(minimum=rational(Fraction(9, 50))))
    require(blocked["simulation_result"] == "PENDING" and under["cash_per_usd_10"] is None
            and under["capacity"]["binding_limit_ids"] == [LIMIT_ID]
            and amount(under["capacity"]["maximum_principal_capacity"]) == noi / Fraction(9, 50)
            and "selected_principal_exceeds_declared_bank_capacity" in under["blockers"]
            and under["construction_refinance"]["net_equity_distribution"] is None,
            "A loan above the debt yield cap reached the equity cash ledger")
    for changes, blocker in (
        ({"minimum": None}, "positive_bank_debt_yield_minimum_required"),
        ({"minimum": rational(0)}, "positive_bank_debt_yield_minimum_required"),
        ({"quote_document_id": "SYNTHETIC-other-quote"}, "debt_yield_addendum_missing_or_incompatible"),
        ({"quote_source_sha256": "0" * 64}, "debt_yield_addendum_missing_or_incompatible"),
        ({"basis": "seller_noi_over_net_proceeds"}, "debt_yield_addendum_missing_or_incompatible"),
        ({"applicability": "not_applicable"}, "debt_yield_not_applicable_with_minimum"),
    ):
        replayed, invalid = probe(lambda row: row.update(changes))
        require(replayed["simulation_result"] == "PENDING" and invalid["capacity"] is None
                and invalid["cash_per_usd_10"] is None and blocker in invalid["blockers"], "Invalid bank terms reached sizing")
    replayed, missing = probe(lambda row: row.clear())
    require(replayed["simulation_result"] == "PENDING" and missing["cash_per_usd_10"] is None
            and "debt_yield_addendum_missing_or_incompatible" in missing["blockers"], "Missing addendum reached sizing")
    _, not_applicable = probe(lambda row: row.update(applicability="not_applicable", minimum=None))
    require(LIMIT_ID not in not_applicable["capacity"]["capacity_limits"]
            and not_applicable["cash_per_usd_10"] == down["cash_per_usd_10"], "Explicit non-applicability changed cash")
    stale, _ = probe(lambda row: row.update(minimum=rational(Fraction(4, 25))), stale=True)
    require(stale["simulation_result"] == "PENDING"
            and "financial_sources_fingerprint_mismatch" in stale["revision_review"]["blockers"],
            "A stale revision accepted an updated bank minimum")
    return dict(status="passed", decision="PENDING", page_count=1, pending_cases=9,
                equality_verified=True, tied_limits_verified=True, not_applicable_verified=True, pdf_sha256=status["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d178-") as folder:
        temp = Path(folder)
        print(json.dumps(verify(temp, args.output or temp / "D178"), sort_keys=True))


if __name__ == "__main__":
    main()
