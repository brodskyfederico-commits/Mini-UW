"""Verify current, historical and unmatched designations through the D194 package audit."""
from argparse import ArgumentParser
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_lorena_criteria_D192 import change_cells
from check_reference_package import require
from check_worksheet_definition_screening_D193 import approvals_unchanged
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_lorena_screening_D194 import CASE_FILE, CURRENT_FILE, FIXTURE
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from miniuw_worksheet_v1 import encoded, verify_package, write_package
from worksheet_documented_finance_D147 import review_documents
from worksheet_revision_D128 import snapshot_for_case


def verify(output):
    case_raw, current = CASE_FILE.read_bytes(), CURRENT_FILE.read_bytes()
    case = json.loads(case_raw)
    criteria = FIXTURE.read_bytes()
    source = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())
    output.mkdir(parents=True, exist_ok=True)
    valid = output / "vigente"
    write_package(case_raw, valid, current_revision_raw=current, criteria_raw=criteria, **source)
    audit = verify_package(valid, current_revision_raw=current)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and audit["simulation_result"] == "PASS" and audit["revision_blockers"] == [],
            "Matching case and criteria failed current audit")
    model = json.loads((valid / "results.json").read_bytes())
    baseline = (valid / "MiniUW_Resumen.pdf").read_bytes()
    cash = {name: scenario["cash_per_usd_10"] for name, scenario in model["scenarios"].items()}
    docs = review_documents(case, source["plan_raw"], evidence_raw=source["evidence_raw"], evidence_milestone="D162")

    def cached(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(candidate["local_sources"] == case["local_sources"] and candidate["workbook_sha256"] == case["workbook_sha256"]
                and plan_raw == source["plan_raw"] and evidence_raw == source["evidence_raw"] and evidence_milestone == "D162",
                "A revision-only variant changed the documents")
        return deepcopy(docs)

    def expect(directory, snapshot, status, reason, archived="PENDING"):
        audited = verify_package(directory, current_revision_raw=snapshot)
        require(audited["vigencia"] == status and audited["revision_blockers"] == [reason]
                and audited["simulation_result"] == "PENDING" and audited["archived_simulation_result"] == archived,
                f"Unexpected audit disposition: {audited}")
        return audited["vigencia"]

    def pending_case(name, raw, workbook, reason, embedded=current):
        package = output / name
        write_package(raw, package, current_revision_raw=embedded, criteria_raw=workbook, **source)
        pending_model = json.loads((package / "results.json").read_bytes())
        approvals_unchanged(pending_model)
        require({scenario: view["cash_per_usd_10"] for scenario, view in pending_model["scenarios"].items()} == cash
                and "Dictamen simulado PENDING" in pdf_text((package / "MiniUW_Resumen.pdf").read_bytes()),
                "Revision check changed financial flows")
        return expect(package, current, "PENDING", reason)

    with patch("worksheet_documented_finance_D147.review_documents", cached):
        changed = deepcopy(case)
        changed["rules"].pop()
        newer = encoded(snapshot_for_case(changed, "SYNTHETIC-D195-next"))
        variants = {
            "revision_advanced": expect(valid, newer, "HISTORICO", "archived_revision_differs_from_current", archived="PASS"),
            "designation_missing": expect(valid, None, "PENDING", "current_revision_snapshot_missing", archived="PASS"),
            "designation_invalid": expect(valid, b"{}", "PENDING", "current_revision_snapshot_invalid", archived="PASS"),
            "different_rules": pending_case("reglas_distintas", encoded(changed), criteria, "investment_rules_fingerprint_mismatch"),
            "criteria_workbook_missing": pending_case("sin_excel", case_raw, None, "criteria_workbook_missing"),
            "criteria_workbook_hash_mismatch": pending_case("excel_distinto", case_raw,
                (CASE_FILE.parent / "MiniUW_Criterios_PASS_FAIL_Lorena.xlsx").read_bytes(), "criteria_workbook_hash_mismatch"),
            "embedded_revision_missing": pending_case("sin_revision", case_raw, criteria, "current_revision_snapshot_missing", embedded=None),
        }
        rejected = expect(output / "reglas_distintas", newer, "PENDING", "investment_rules_fingerprint_mismatch")
        variants["never_matched"] = rejected
        other_xlsx = change_cells(criteria, {"B18": "SYNTHETIC-D195-other-criteria-revision"})
        revised_case = deepcopy(case)
        revised_case["criteria_workbook"]["sha256"] = sha256(other_xlsx).hexdigest()
        revised = encoded(snapshot_for_case(revised_case, "SYNTHETIC-D195-wrong-xlsx-label"))
        different_label = output / "version_excel_distinta"
        write_package(encoded(revised_case), different_label, current_revision_raw=revised, criteria_raw=other_xlsx, **source)
        variants["criteria_workbook_revision_mismatch"] = expect(
            different_label, revised, "PENDING", "criteria_workbook_revision_mismatch")
        require((valid / "MiniUW_Resumen.pdf").read_bytes() == baseline, "Audit mutated the historical PDF")
    return dict(status="passed", decision="PENDING", simulation_result=audit["simulation_result"],
                valid_designation=audit["vigencia"], variants=variants, cash_preserved=True,
                base_total_receipts_per_usd10=18.06, downside_total_receipts_per_usd10=6.08,
                archived_pdf_sha256=model["pdf_sha256"], real_decisions_enabled=False, deployment_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d195-") as temp:
        print(json.dumps(verify(args.output or Path(temp)), ensure_ascii=False, sort_keys=True))
