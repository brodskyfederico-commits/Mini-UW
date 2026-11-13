"""Preview thresholds from Lorena's worksheet against a current synthetic D181 package."""
from argparse import ArgumentParser
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re

from miniuw_foundation.debt_service import rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.intake import MAX_BYTES
from miniuw_foundation.irr_interval_output import condition_relation
from miniuw_foundation.screening import _overlap
from miniuw_foundation.threshold_rehearsal import ROWS
from miniuw_foundation.workbooks import DOC_REL, MAIN, _parts, _read_cell, _relationships, _text, _xml
from miniuw_worksheet_v1 import encoded, read_current_revision, verify_package
from worksheet_integrated_screening_D181 import METRICS
from worksheet_definition_screening_D193 import RLV, land_band_rules


SHEET = "Criterios PASS FAIL"
ROW_LABELS = (
    "Yield on Cost (YoC)", "Spread sobre cap comparable", "Equity recuperado en refi",
    "Aporte de equity en refi", "Ocupación de equilibrio", "Cash-on-cash posrefi",
    "Exceso del precio pedido sobre RLV", "Equity / costo total (TDC)", "TIR apalancada",
    "Múltiplo de equity (EM)",
)
MARKER = "Mini-UW v1 · Criterios PASS y FAIL"
THRESHOLD = re.compile(r"(>=|<=|>|<|≥|≤)\s*(-?[0-9]{1,14}(?:[,.][0-9]{1,12})?)\s*(%|pb|bps|x|×|USD)", re.I)
UNIT = {"%": "fraction", "pb": "bps", "bps": "bps", "x": "multiple", "×": "multiple", "usd": "USD"}


def require(condition, reason):
    if not condition:
        raise ValidationError(reason)


def read_cells(raw):
    parts = _parts(raw)
    for path, data in parts.items():
        if path.startswith("xl/worksheets/_rels/") and path.endswith(".rels"):
            # Comments on the provided template use local parent-relative targets.
            # They are presentation metadata. Do not open or resolve those parts.
            for link in _xml(data):
                require(link.get("TargetMode", "Internal") == "Internal"
                        and link.get("Type") in {DOC_REL + "/comments", DOC_REL + "/vmlDrawing"},
                        "Relación de hoja no compatible")
        elif path.endswith(".rels"):
            _relationships(data)
    for name in ("xl/workbook.xml", "xl/_rels/workbook.xml.rels", "_rels/.rels"):
        require(name in parts, "Faltan metadatos del Excel de criterios")
    workbook = _xml(parts["xl/workbook.xml"])
    roots = _relationships(parts["_rels/.rels"])
    require([target for kind, target in roots.values() if kind == DOC_REL + "/officeDocument"]
            == ["xl/workbook.xml"], "Relación principal del Excel no compatible")
    links = _relationships(parts["xl/_rels/workbook.xml.rels"])
    sheets = workbook.findall(f"{{{MAIN}}}sheets/{{{MAIN}}}sheet")
    require(len(sheets) == 1 and sheets[0].get("name") == SHEET
            and sheets[0].get("state", "visible") == "visible", "Se requiere la pestaña de criterios de Lorena")

    def related(kind):
        targets = [target for rel, target in links.values() if rel == DOC_REL + "/" + kind]
        require(len(targets) <= 1, "Partes duplicadas en el Excel de criterios")
        if not targets:
            return None
        target, = targets
        path = target[1:] if target.startswith("/") else "xl/" + target
        require(path in parts, "Parte ausente en el Excel de criterios")
        return path

    strings_path = related("sharedStrings")
    strings = [] if strings_path is None else [_text(item) for item in _xml(parts[strings_path]).findall(f"{{{MAIN}}}si")]
    sheet_path = related("worksheet")
    relation = links.get(sheets[0].get(f"{{{DOC_REL}}}id"), (None, None))
    require(sheet_path is not None and relation[0] == DOC_REL + "/worksheet", "Relación de pestaña inválida")
    sheet = _xml(parts[sheet_path])
    require(not any(col.get("hidden") in ("1", "true") for col in sheet.findall(f"{{{MAIN}}}cols/{{{MAIN}}}col")),
            "La planilla tiene columnas ocultas")
    cells = {}
    require(len(sheet.findall(f"{{{MAIN}}}sheetData")) == 1, "Datos de pestaña ambiguos")
    for row in sheet.findall(f"{{{MAIN}}}sheetData/{{{MAIN}}}row"):
        for cell in row:
            address = cell.get("r", "")
            if not re.fullmatch(r"[A-I](?:[1-9]|1[0-9]|2[0-2])", address):
                require(_read_cell(cell, strings, sheet_path)["kind"] == "blank", "Celda fuera del formato de criterios")
                continue
            require(address not in cells and address[1:] == row.get("r")
                    and row.get("hidden") not in ("1", "true"), "Celda movida, repetida u oculta")
            item = _read_cell(cell, strings, sheet_path)
            kind = item["kind"]
            require(kind in ("blank", "text"), f"{address}: se requiere texto, por ejemplo >= 6,5 %")
            cells[address] = (item["literal"] or "").strip()
    require(cells.get("A1") == MARKER and
            [cells.get(f"{col}6") for col in "EFGH"] == ["PASS Base", "FAIL Base", "PASS Downside", "FAIL Downside"],
            "Título o encabezados de criterios no reconocidos")
    for i, label in enumerate(ROW_LABELS, 7):
        require(cells.get(f"A{i}") == label, f"Fila {i}: métrica movida o cambiada")
    return cells


def parse_condition(text):
    match = THRESHOLD.fullmatch(text)
    if not match:
        return None
    op, raw_value, suffix = match.groups()
    value = Fraction(raw_value.replace(",", "."))
    if suffix == "%":
        value /= 100
    return dict(operator={"≥": ">=", "≤": "<="}.get(op, op), threshold=rational(value)), UNIT[suffix.lower()]


def comparison(metric, passing, failing, evidence, *, downside=False):
    if all(value.casefold() == "no aplica" for value in (passing, failing)):
        # This note documents a candidate exclusion. No approved applicability is available in the pilot.
        return "PENDING", ["aplicabilidad_por_verificar" if evidence else "falta_motivo_no_aplica"], {}
    pass_only = downside and failing.casefold() == "sin fail"
    parsed = {"PASS": parse_condition(passing), "FAIL": parse_condition(failing)}
    blockers = []
    for label, literal in (("PASS", passing), ("FAIL", failing)):
        if label == "FAIL" and pass_only:
            continue
        candidate = parsed[label]
        if candidate is None:
            blockers.append(f"{label.lower()}_ausente" if not literal else f"{label.lower()}_formato_incompatible")
        elif candidate[1] != metric.get("unit"):
            blockers.append(f"{label.lower()}_unidad_incompatible")
    value = metric.get("value")
    enclosure = metric.get("annual_enclosure")
    if enclosure is None and value is not None:
        enclosure = dict(lower=value, upper=value, lower_closed=True, upper_closed=True)
    if enclosure is None or metric.get("period_ref") is None:
        blockers.append("metrica_o_definicion_no_disponible")
    if pass_only:
        parsed.pop("FAIL")
    rules = {name: candidate[0] | {"unit": candidate[1]} for name, candidate in parsed.items() if candidate is not None}
    if blockers:
        return "PENDING", blockers, rules
    if not pass_only and _overlap(rules["PASS"], rules["FAIL"]):
        return "CONFLICT", ["regiones_pass_fail_solapadas"], rules
    relations = {name: condition_relation(enclosure, rule["threshold"], rule["operator"]) for name, rule in rules.items()}
    if relations["PASS"] == "every":
        return "PASS_CONDITION", [], rules
    if relations.get("FAIL") == "every":
        return "FAIL_CONDITION", [], rules
    if pass_only and relations["PASS"] == "none":
        return "PENDING", ["downside_no_alcanza_pass_sin_regla_fail"], rules
    reason = "intervalo_cruza_umbral" if "mixed" in relations.values() else "banda_intermedia"
    return "PENDING", [reason], rules


def preview(raw, result):
    require(result.get("profile") in ("synthetic_documented_integrated_screening", "synthetic_documented_definition_screening")
            and result["deployment_enabled"] is False
            and result["decision"] == "PENDING" and result["real_decisions_enabled"] is False,
            "Sólo se admite un perfil sintético integrado")
    cells = read_cells(raw)
    definition_screening = result["profile"] == "synthetic_documented_definition_screening"
    original = result["screening"]["comparisons"]
    index = {(row["scenario_id"], row["metric_id"]): row for row in original}
    require(len(index) == len(original) == 2 * len(METRICS), "Inventario de métricas incompleto o repetido")
    source = cells.get("B18", "")
    policy = cells.get("B19", "")
    rows = []
    for row_num, (_, metric_id) in enumerate(ROWS, 7):
        for scenario, columns in (("Base", "EF"), ("Downside", "GH")):
            pass_ref, fail_ref = [f"{col}{row_num}" for col in columns]
            note_ref = f"I{row_num}"
            row = index[scenario, metric_id]
            metric = row["metric_record"]
            passing, failing, note = [cells.get(ref, "") for ref in (pass_ref, fail_ref, note_ref)]
            state, blockers, rules = comparison(metric, passing, failing, note, downside=scenario == "Downside")
            if definition_screening and metric_id == RLV and rules:
                trace = result["screening"]["metric_evidence_by_scenario"][scenario]["candidate_definitions"][RLV]
                boundary = trace.get("fail_boundary_multiple")
                expected = {key: rule | {"unit": "multiple"} for key, rule in land_band_rules(boundary).items()}
                if boundary is not None and rules != expected:
                    state = "PENDING"
                    blockers.append("SRC-03_ratio_rule_does_not_match_computed_price_band")
            rows.append(dict(scenario=scenario, metric=metric_id, state=state, blockers=blockers, parsed_rules=rules,
                             criteria_cells=dict(passing=pass_ref, failing=fail_ref, note=note_ref),
                             input_literals=dict(passing=passing, failing=failing, note=note),
                             result_locator=row["metric_locator"], metric_record=metric))
    return dict(sheet=SHEET, criteria_xlsx_sha256=sha256(raw).hexdigest(),
                criteria_source_and_validity=source or None, downside_policy_note=policy or None,
                comparison_scope="arithmetic_on_D181_definitions_for_reconciliation"
                if not definition_screening else "arithmetic_on_D193_candidate_definitions_for_reconciliation",
                criteria_adopted=False, matching_financial_bases_confirmed=False, decision="PENDING",
                pilot_state="PENDING", real_decisions_enabled=False, deployment_enabled=False,
                source_revision=result["revision_review"]["reference_revision"],
                scenario_cash_per_usd_10={name: view.get("cash_per_usd_10") for name, view in result["scenarios"].items()},
                comparisons=rows)


def preview_package(directory, revision_path, criteria_path):
    revision = read_current_revision(revision_path, directory)
    audit = verify_package(directory, current_revision_raw=revision)
    require(audit["vigencia"] == "VIGENTE" and audit["audit_bot"] == "B16",
            "El expediente no es la revisión vigente designada")
    raw = (directory / "results.json").read_bytes()
    with criteria_path.open("rb") as stream:
        criteria = stream.read(MAX_BYTES + 1)
    require(len(criteria) <= MAX_BYTES, "El Excel supera el límite de lectura")
    return preview(criteria, json.loads(raw)) | {"results_sha256": sha256(raw).hexdigest(), "revision_audit": audit["vigencia"]}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--current-revision", type=Path, required=True)
    parser.add_argument("--criteria", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = preview_package(args.package, args.current_revision, args.criteria)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"PENDING: {error}\n")
    print(encoded(result).decode(), end="")


if __name__ == "__main__":
    main()
