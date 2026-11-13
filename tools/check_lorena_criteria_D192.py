"""Replay Lorena's blank and synthetic completed criteria against the audited pilot."""
from argparse import ArgumentParser
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from check_worksheet_integrated_screening_D181 import BOOKS, CASE, CURRENT, PLAN, shuffled_pdf
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.workbooks import MAIN
from miniuw_worksheet_v1 import encoded, write_package
from preview_lorena_criteria_D192 import comparison, parse_condition, preview, preview_package, read_cells, require


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/MiniUW_Criterios_PASS_FAIL_Lorena.xlsx"
EDITS = {
    "E7": "≥ 8 %", "F7": "< 5 %", "G7": ">= 5,75 %", "H7": "Sin FAIL",
    "E8": ">= 200 pb", "F8": "< 0 pb", "G8": ">= 50 pb", "H8": "< 0 pb",
    "E10": "≤ 0 USD", "F10": "> 0 USD", "G10": "≤ 5 %", "H10": "> 10 %",
    "E13": "No aplica", "F13": "No aplica", "I13": "SYNTHETIC-D192 · ejemplo de motivo no aprobado",
    "E15": ">= 0 %", "F15": "< 0 %", "G15": ">= 0 %", "H15": "< 0 %",
    "E16": ">= 1,30 x", "F16": "< 1,00 x",
    "B18": "SYNTHETIC-D192 · criterios de prueba", "B19": "Revisión humana cuando sólo Downside no cumple",
}


def change_cells(raw, edits, *, formula=None):
    output = BytesIO()
    with ZipFile(BytesIO(raw)) as source, ZipFile(output, "w", compression=8) as target:
        for member in source.namelist():
            data = source.read(member)
            if member == "xl/worksheets/sheet1.xml":
                sheet = ET.fromstring(data)
                namespace = f"{{{MAIN}}}"
                for cell in sheet.findall(f".//{namespace}c"):
                    address = cell.get("r")
                    if address in edits:
                        cell[:] = []
                        cell.set("t", "inlineStr")
                        content = ET.SubElement(cell, f"{namespace}is")
                        ET.SubElement(content, f"{namespace}t").text = edits[address]
                    if address == formula:
                        cell[:] = []
                        cell.set("t", "n")
                        ET.SubElement(cell, f"{namespace}f").text = "1-1"
                        ET.SubElement(cell, f"{namespace}v").text = "0"
                data = ET.tostring(sheet, encoding="utf-8")
            target.writestr(member, data)
    return output.getvalue()


def check(output):
    source = TEMPLATE.read_bytes()
    case, revision = CASE.read_bytes(), CURRENT.read_bytes()
    inputs = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "Expediente"
    write_package(case, result_path, current_revision_raw=revision, **inputs)
    completed_path = output / "Criterios_Sinteticos_D192.xlsx"
    completed_path.write_bytes(change_cells(source, EDITS))
    report = preview_package(result_path, CURRENT, completed_path)
    model = json.loads((result_path / "results.json").read_bytes())
    blank = preview(source, model)
    require(len(blank["comparisons"]) == 20 and all(row["state"] == "PENDING" and not row["parsed_rules"]
            for row in blank["comparisons"]), "Historical thresholds entered the active inventory")
    require(report["scenario_cash_per_usd_10"] == blank["scenario_cash_per_usd_10"]
            and report["decision"] == "PENDING" and report["pilot_state"] == "PENDING"
            and not report["matching_financial_bases_confirmed"] and not report["criteria_adopted"],
            "Criteria changed cash or authorized a decision")
    rows = {(row["scenario"], row["metric"]): row for row in report["comparisons"]}
    checks = [
        ("Base", "YoC", "PASS_CONDITION", None, "E7"),
        ("Downside", "YoC", "PENDING", "downside_no_alcanza_pass_sin_regla_fail", "G7"),
        ("Base", "spread", "PASS_CONDITION", None, "E8"),
        ("Downside", "spread", "FAIL_CONDITION", None, "G8"),
        ("Base", "equity_cash_in", "PASS_CONDITION", None, "E10"),
        ("Downside", "equity_cash_in", "PENDING", "pass_unidad_incompatible", "G10"),
        ("Base", "asking_relative_to_supported_price", "PENDING", "aplicabilidad_por_verificar", "E13"),
        ("Base", "IRR", "PASS_CONDITION", None, "E15"),
        ("Downside", "IRR", "FAIL_CONDITION", None, "G15"),
        ("Base", "equity_multiple", "PENDING", "banda_intermedia", "E16"),
    ]
    for name, metric_id, state, reason, locator in checks:
        row = rows[name, metric_id]
        require(row["state"] == state and (reason is None or reason in row["blockers"])
                and row["criteria_cells"]["passing"] == locator, f"{name} {metric_id}: comparison or citation changed")
    require(rows["Base", "equity_cash_in"]["parsed_rules"]["PASS"]["threshold"] == {"numerator": "0", "denominator": "1"},
            "Explicit zero lost")
    require(parse_condition(">= 1,234.56 USD") is None and parse_condition("6.5%") is None,
            "Ambiguous or incomplete literals accepted")
    for edits, formula in (({"A7": "Changed"}, None), ({}, "E7")):
        try:
            read_cells(change_cells(source, edits, formula=formula))
        except ValidationError:
            pass
        else:
            raise ValueError("Modified layout or formula accepted")

    metric = rows["Base", "IRR"]["metric_record"]
    test_metric = metric | {"annual_enclosure": {"lower": {"numerator": "5", "denominator": "100"},
                                                 "upper": {"numerator": "6", "denominator": "100"},
                                                 "lower_closed": True, "upper_closed": True}}
    state, blockers, _ = comparison(test_metric, ">= 5,5 %", "< 3 %", "")
    require(state == "PENDING" and blockers == ["intervalo_cruza_umbral"], "TIR interval reduced to a point")
    state, blockers, _ = comparison(test_metric, ">= 5 %", "<= 5 %", "")
    require(state == "CONFLICT" and blockers == ["regiones_pass_fail_solapadas"], "Conflicting rules accepted")

    historical = json.loads(revision)
    historical["revision"] = "SYNTHETIC-D192-different-revision"
    stale = output / "different_revision.json"
    stale.write_bytes(encoded(historical))
    try:
        preview_package(result_path, stale, completed_path)
    except ValidationError as error:
        require("vigente" in str(error), "Wrong stale revision rejection")
    else:
        raise ValueError("Historical revision accepted")

    require(TEMPLATE.read_bytes() == source, "Blank workbook was modified")
    (output / "Cotejo_Criterios_D192.json").write_bytes(encoded(report))
    return dict(status="passed", decision="PENDING", blank_rows=20, filled_rows=len(report["comparisons"]),
                exact_assertions=len(checks), unresolved_metrics=["SRC-02", "SRC-03"],
                workbook_sha256=report["criteria_xlsx_sha256"], results_sha256=report["results_sha256"],
                cash_and_sources_replayed=True, formula_rejected=True, outdated_revision_rejected=True,
                real_decisions_enabled=False, deployment_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output:
        report = check(args.output)
    else:
        with TemporaryDirectory(prefix="miniuw-d192-") as temp:
            report = check(Path(temp))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
