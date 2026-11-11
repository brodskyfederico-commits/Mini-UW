"""Exercise PDF extraction, independent sheet readings and PENDING gates."""
from argparse import ArgumentParser
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_screening_pilot_D120 import BOOKS, check_cash_and_metrics
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import PLAN_FILE, encoded
from worksheet_plan_pdf_D130 import read_plan
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-plan-chain-D130.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D130.json"
PLAN = ROOT / "templates/synthetic-plan-D130.pdf"
AREA_A = b"Gross building area | 1000.00 | m2"
AREA_B = b"Declared GBA: 1,000.00 m2"


def replace_text(raw, index, old, new):
    writer = PdfWriter(clone_from=PdfReader(BytesIO(raw), strict=True))
    page = writer.pages[index]
    data = page.get_contents().get_data()
    require(data.count(old) == 1, "Expected one literal to change on the requested sheet")
    stream = DecodedStreamObject()
    stream.set_data(data.replace(old, new))
    page.replace_contents(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def run_case(case, output, reference, plan):
    plan_arg = [] if plan is None else ["--plan", plan]
    created = call("run", case, "--workbook", BOOKS["Base"], "--downside-workbook", BOOKS["Downside"],
                   "--current-revision", reference, "--output", output, *plan_arg)
    result = json.loads((output / "results.json").read_bytes())
    pdf = output / "MiniUW_Resumen.pdf"
    page, = PdfReader(pdf).pages
    require(created["simulation_result"] == result["simulation_result"]
            and created["pdf_sha256"] == result["pdf_sha256"] == sha(pdf.read_bytes())
            and f"Simulación PASS/FAIL  |  {result['simulation_result']}" in page.extract_text()
            and result["decision"] == "PENDING" and result["real_decisions_enabled"] is False
            and result["deployment_enabled"] is False and result["personal_investor_return"] is None
            and (not (output / PLAN_FILE).exists() if plan is None else (output / PLAN_FILE).read_bytes() == plan.read_bytes()),
            "The PDF plan case lost source bytes, a one-page report or the synthetic guard")
    return result


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    raw = PLAN.read_bytes()
    output = saved_output or temp / "matching"
    matching = run_case(CASE, output, CURRENT, PLAN)
    check_cash_and_metrics(matching)
    bots = matching["local_review"]["bots"]
    require(matching["simulation_result"] == "FAIL" and not matching["local_review"]["blockers"]
            and not matching["revision_review"]["blockers"]
            and bots["B03"]["documents"]["plan_pdf"]["sha256"] == sha(raw)
            and (bots["B05"]["sheet"], bots["B05"]["page"], amount(bots["B05"]["value"])) == ("A101", 1, 1000)
            and (bots["B06"]["sheet"], bots["B06"]["page"], amount(bots["B06"]["value"])) == ("A601", 2, 1000)
            and all(bots[key]["source_sha256"] == sha(raw) for key in ("B05", "B06"))
            and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0,
            "The two readers did not independently reproduce the printed source and GC comparison")
    audited = call("audit", output, "--current-revision", CURRENT)
    require(audited["vigencia"] == "VIGENTE" and audited["audit_bot"] == "B16"
            and audited["simulation_result"] == "FAIL", "The matching plan lost its source-first audit")

    def pending_variant(name, plan, case_path=CASE, revision=CURRENT):
        result = run_case(case_path, temp / name, revision, plan)
        require(result["simulation_result"] == "PENDING"
                and result["screening"]["worksheet_simulation_result"] == "FAIL"
                and result["scenarios"] == matching["scenarios"],
                "An incomplete or conflicting plan released a verdict or changed independent cash")
        return result["local_review"]["bots"]

    def revised_plan(name, data):
        path = temp / f"{name}.pdf"
        path.write_bytes(data)
        spec = deepcopy(case)
        spec["local_sources"]["plan_pdf"]["sha256"] = sha(data)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(spec))
        reference = temp / f"{name}-reference.json"
        reference.write_bytes(encoded(snapshot_for_case(spec, f"SYNTHETIC-D130-{name}")))
        return path, pending_variant(name, path, case_path, reference)

    _, missing = revised_plan("missing-area", replace_text(raw, 1, AREA_B, b"Area value not supplied"))
    require(missing["B05"]["state"] == "checked_synthetic"
            and missing["B06"]["blockers"] == ["explicit_area_missing_or_ambiguous"]
            and missing["B07"]["blockers"] == ["both_plan_readings_required"],
            "A missing area was inferred from the other reading")

    disputed_raw = replace_text(raw, 1, AREA_B, b"Declared GBA: 1,050.00 m2")
    disputed, conflict = revised_plan("conflicting-areas", disputed_raw)
    require(conflict["B07"]["blockers"] == ["plan_readings_conflict"] and "value" not in conflict["B07"]
            and [amount(row["value"]) for row in conflict["B07"]["readings"]] == [1000, 1050]
            and conflict["B09"]["state"] == "PENDING",
            "The reconciler selected one reading or averaged a conflict")
    _, gc = revised_plan("gc-discrepancy", replace_text(disputed_raw, 0, AREA_A, b"Gross building area | 1050.00 | m2"))
    require(amount(gc["B07"]["value"]) == 1050 and gc["B09"]["blockers"] == ["GC_area_conflict"]
            and amount(gc["B09"]["difference"]) == 50, "Matching plan readings bypassed the GC criterion")

    require(pending_variant("absent-plan", None)["B03"]["documents"]["plan_pdf"]["blockers"] == ["plan_pdf_missing"],
            "A missing PDF acquired a reading")
    require(pending_variant("wrong-hash", disputed)["B03"]["documents"]["plan_pdf"]["blockers"]
            == ["plan_pdf_hash_or_reference_mismatch"], "A PDF from another revision supplied readings")

    wrong_unit = replace_text(raw, 1, AREA_B, b"Declared GBA: 1,000.00 ft2")
    unit_reading = read_plan(wrong_unit, case["local_sources"]["plan_pdf"] | {"sha256": sha(wrong_unit)})
    require(unit_reading["B06"]["blockers"] == ["area_value_or_unit_unsupported"],
            "The reader silently converted an unsupported unit")

    altered = temp / "altered"
    copytree(output, altered)
    (altered / PLAN_FILE).write_bytes(disputed_raw)
    manifest_path = altered / "package.json"
    manifest = json.loads(manifest_path.read_bytes())
    row, = (row for row in manifest["files"] if row["path"] == PLAN_FILE)
    row.update(bytes=len(disputed_raw), sha256=sha(disputed_raw))
    manifest_path.write_bytes(encoded(manifest))
    call("audit", altered, "--current-revision", CURRENT, blocked=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=6, agreeing_readings=True,
                pending_cases=5, conflict_observations_preserved=True, rehashed_plan_tamper_rejected=True,
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited matching plan case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d130-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
