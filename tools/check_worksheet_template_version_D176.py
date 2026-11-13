"""Exercise the B04 template declaration and exact 55-field layout on the integrated pilot."""
from argparse import ArgumentParser
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_operating_replay_D20 import ROOT, require
from check_worksheet_alternatives_D155 import workbook_values
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from check_worksheet_scope_D174 import CASE as PRIOR, CURRENT as PRIOR_CURRENT
from inputsheet_fixture import native_workbook
from miniuw_foundation.inputsheet import layout
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import (
    WORKBOOK_VERSIONED_TEMPLATE_SCHEMA, build_results, encoded, verify_package, write_package,
)
from worksheet_documented_finance_D147 import review_documents
from worksheet_native_mapping_D139 import mapping_catalog, template_identity
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-template-version-D176.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D176.json"


def fixture():
    case = json.loads(PRIOR.read_bytes())
    case["schema"] = WORKBOOK_VERSIONED_TEMPLATE_SCHEMA
    for confirmation in case["native_mapping"]["scenarios"].values():
        confirmation["template"] = template_identity()
    return case


def verify(temp, output):
    case = fixture()
    current = encoded(snapshot_for_case(case, "SYNTHETIC-D176-current"))
    require(CASE.read_bytes() == encoded(case) and CURRENT.read_bytes() == current, "Template fixture drift")
    raw = shuffled_pdf()
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    plan = PLAN.read_bytes()
    sources = dict(workbook_raw=books["Base"], downside_workbook_raw=books["Downside"], plan_raw=plan, evidence_raw=raw)
    write_package(PRIOR.read_bytes(), temp / "D174", current_revision_raw=PRIOR_CURRENT.read_bytes(), **sources)
    previous = json.loads((temp / "D174/results.json").read_bytes())
    status = write_package(CASE.read_bytes(), output, current_revision_raw=current, **sources)
    result = json.loads((output / "results.json").read_bytes())
    require(result["decision"] == "PENDING" and result["simulation_result"] == previous["simulation_result"] == "FAIL"
            and not result["deployment_enabled"] and not result["real_decisions_enabled"]
            and result["scenarios"] == previous["scenarios"], "The compatible version changed D174 scenario cash or guards")
    audit = verify_package(output, current_revision_raw=current)
    require(audit["vigencia"] == "VIGENTE" and audit["pdf_sha256"] == status["pdf_sha256"],
            "B16 did not reproduce the versioned case")
    require("D176" in pdf_text((output / "MiniUW_Resumen.pdf").read_bytes()), "Wrong versioned report")
    catalog = mapping_catalog()
    ids = [field["field_id"] for field in catalog]
    require(len(set(ids)) == 55, "Unexpected field inventory")
    for scenario in result["native_mapping_review"]["scenarios"].values():
        require(scenario["verified_template"] == template_identity()
                and [field["field_id"] for field in scenario["rows"]] == ids, "Template identity or mapping drift")

    values = workbook_values("Downside", catalog)
    require(native_workbook(values) == books["Downside"], "Layout test did not reproduce the Downside XLSX")
    documents = review_documents(case, plan, evidence_raw=raw, evidence_milestone="D162")

    def run_variant(change, *, workbook=None):
        changed = deepcopy(case)
        confirm = changed["native_mapping"]["scenarios"]["Downside"]
        change(confirm)
        if workbook is not None:
            digest = sha(workbook)
            changed["workbook_sha256"]["Downside"] = digest
            changed["local_sources"]["workbook_sha256"]["Downside"] = digest
            changed["rent_inputs"]["supplemental_scope"]["Downside"]["downside_scope"]["downside_workbook_sha256"] = digest
            confirm["workbook_sha256"] = digest
        # Reuse OCR for declaration-only variants with identical sources.
        def reviewed_documents(candidate, plan_raw, *, evidence_raw, evidence_milestone):
            if workbook is not None:
                return review_documents(candidate, plan_raw, evidence_raw=evidence_raw, evidence_milestone=evidence_milestone)
            require(candidate["local_sources"] == case["local_sources"] and plan_raw == plan and evidence_raw == raw
                    and evidence_milestone == "D162", "Evidence changed in declaration-only variant")
            return deepcopy(documents)

        revision = encoded(snapshot_for_case(changed, "SYNTHETIC-D176-test"))
        with patch("worksheet_documented_finance_D147.review_documents", side_effect=reviewed_documents):
            replayed, _ = build_results(encoded(changed), workbook_raw=books["Base"],
                                        downside_workbook_raw=books["Downside"] if workbook is None else workbook,
                                        current_revision_raw=revision, plan_raw=plan, evidence_raw=raw)
        require(replayed["decision"] == replayed["simulation_result"] == "PENDING"
                and replayed["scenarios"]["Base"] == result["scenarios"]["Base"]
                and replayed["scenarios"]["Downside"]["cash_per_usd_10"] is None,
                "A template fault escaped PENDING or changed Base")
        down = replayed["native_mapping_review"]["scenarios"]["Downside"]
        require(down["rows"] == [] and not down["calculation_inputs_ready"],
                "The calculation read values from a mismatched template")
        return down

    probes = (
        (lambda confirm: confirm.pop("template"), "worksheet_template_declaration_missing"),
        (lambda confirm: confirm["template"].update(version="input-sheet-layout-v2"), "worksheet_template_identity_unverified"),
        (lambda confirm: confirm["template"].update(layout_sha256="0" * 64), "worksheet_template_identity_unverified"),
    )
    for change, reason in probes:
        require(run_variant(change)["blockers"] == [reason], f"Expected {reason}")

    field = next(row for row in layout()["fields"] if row["value_cell"] == "C72")
    unit_cell = field["unit_cell"]
    bad_unit = native_workbook(values | {unit_cell: {"text": "%"}})
    moved = native_workbook(values | {"C72": "missing", "C83": values["C72"]})
    for workbook, reason in ((bad_unit, unit_cell), (moved, "row")):
        blocked = run_variant(lambda confirm: None, workbook=workbook)
        require(blocked["blockers"] == ["native_workbook_layout_unverified"] and reason in blocked["layout_reason"],
                "Changed workbook geometry or units bypassed B04")
    return dict(status="passed", decision="PENDING", page_count=1, fields=len(ids), pending_cases=5,
                pdf_sha256=status["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d176-") as folder:
        temp = Path(folder)
        print(json.dumps(verify(temp, args.output or temp / "D176"), sort_keys=True))


if __name__ == "__main__":
    main()
