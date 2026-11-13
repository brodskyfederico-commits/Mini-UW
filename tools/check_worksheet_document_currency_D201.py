"""Verify that B16 checks the registered plan and supporting PDF before designating a run current."""
from argparse import ArgumentParser
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfWriter

from check_reference_package import require
from check_worksheet_definition_screening_D193 import approvals_unchanged
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_technical_acceptance_D200 import cash_summary, settings_for_acceptance, source_files
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, read_package, verify_package
from worksheet_intake_D198 import SOURCES, assemble, register


VARIANTS = {
    "plan_raw": ("plan_pdf", "plan_pdf_hash_or_reference_mismatch", "plan_pdf_missing"),
    "evidence_raw": ("evidence_pdf", "evidence_pdf_binding_unconfirmed", "evidence_pdf_missing"),
}


def modified_pdf(raw):
    writer = PdfWriter(clone_from=BytesIO(raw))
    writer.add_metadata({"/Subject": "SYNTHETIC-D201 · alternate bytes, same declared document"})
    output = BytesIO()
    writer.write(output)
    modified = output.getvalue()
    require(sha(modified) != sha(raw), "Modification must change the registered hash")
    return modified


def verify(output):
    output.mkdir(exist_ok=True)
    source_dir = output / "sources"
    sources = source_files(source_dir)
    settings = settings_for_acceptance()
    snapshot_id = "SYNTHETIC-D201-current"
    registered = register(sources, snapshot_id)

    original = output / "original"
    original_run = assemble(settings, registered, sources, original)
    require(original_run["source_blockers"] == [], "Unmodified sources failed intake")
    baseline = read_package(original)
    current = baseline[CURRENT_REVISION_FILE]
    baseline_audit = verify_package(original, current_revision_raw=current)
    require(baseline_audit["vigencia"] == "VIGENTE" and baseline_audit["simulation_result"] == "PASS",
            "The existing current expediente did not replay")

    results = {}
    for argument, (key, mismatch, missing) in VARIANTS.items():
        filename = SOURCES[argument]
        for label, raw, blocker in (("modified", modified_pdf(sources[argument]), mismatch), ("missing", None, missing)):
            folder = output / f"{key}-{label}"
            run = assemble(settings, registered, sources | {argument: raw}, folder)
            saved = read_package(folder)
            model = json.loads(saved["results.json"])
            approvals_unchanged(model)
            audit = verify_package(folder, current_revision_raw=current)
            classifier = model["local_review"]["bots"]["B03"]["documents"][key]
            require(run["source_blockers"] == [
                dict(file=filename, cells=[], blocker="registered_source_mismatch")],
                f"{filename}: intake did not locate the affected PDF")
            require(saved[CURRENT_REVISION_FILE] == current and audit["audit_bot"] == "B16"
                    and audit["archived_revision"] == snapshot_id and audit["current_revision"] == snapshot_id
                    and audit["revision_blockers"] == [blocker] and classifier["blockers"] == [blocker]
                    and audit["vigencia"] == "PENDING" and audit["simulation_result"] == "PENDING",
                    f"{filename}: a matching declaration was mistaken for verified source bytes")
            require(all(view["cash_per_usd_10"] is None for view in model["scenarios"].values())
                    and "Base | Caja PENDING" in pdf_text(saved["MiniUW_Resumen.pdf"])
                    and "Downside | Caja PENDING" in pdf_text(saved["MiniUW_Resumen.pdf"]),
                    f"{filename}: cash appeared without a verified PDF")
            results[folder.name] = dict(filename=filename, blocker=blocker, vigencia=audit["vigencia"],
                                        simulation_result=audit["simulation_result"],
                                        registered_sha256=registered["files"][filename]["sha256"],
                                        observed_sha256=None if raw is None else sha(raw))

    restored = output / "restored"
    retry = assemble(settings, registered, sources, restored)
    require(retry["source_blockers"] == [] and read_package(restored) == baseline,
            "Restoring registered bytes changed the original package")
    restored_audit = verify_package(restored, current_revision_raw=current)
    require(restored_audit == baseline_audit, "The restored package lost its original audit result")
    model = json.loads(baseline["results.json"])
    return dict(status="passed", decision="PENDING", real_decisions_enabled=False, deployment_enabled=False,
                variants=results, restored_identical_files=len(baseline),
                restored_vigencia=restored_audit["vigencia"], restored_simulation_result=restored_audit["simulation_result"],
                scenarios={name: cash_summary(view["cash_per_usd_10"]) for name, view in model["scenarios"].items()})


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d201-") as temporary:
        print(json.dumps(verify(args.output or Path(temporary)), ensure_ascii=False, sort_keys=True))
