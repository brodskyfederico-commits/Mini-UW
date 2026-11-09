"""Read a filled synthetic Cotejo sheet against the verified pilot evidence."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZipInfo
import json
import re
import sys

from check_operating_replay_D20 import require
from miniuw_scenario_package_D52 import TOP_FILES, build
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.workbooks import DOC_REL, MAIN, _parts, _read_cell, _relationships, _text, _xml


NS = "{" + MAIN + "}"
LABELS = {"equity_multiple": "Múltiplo de equity (EM)", "equity_recovered": "Equity recuperado",
          "equity_cash_in": "Equity cash-in"}
HEADERS = ("Escenario", "Métrica", "Aplica / motivo", "Unidad", "Definición / base / período", "Fuente / revisión",
           "Valor Mini-UW", "Valor independiente", "Diferencia", "Oper. PASS", "Umbral PASS", "Oper. FAIL", "Umbral FAIL",
           "Estado Mini-UW", "Estado referencia", "Cotejo de estado", "Notas")
INPUT_COLS = "ACDEFGHJKLMNO"


def cotejo_sheet(parts):
    require({"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels"} <= parts.keys(),
            "Workbook metadata missing")
    for path, data in parts.items():
        if path.endswith(".rels"):
            _relationships(data)
    types = _xml(parts["[Content_Types].xml"])
    require(not any("macroenabled" in item.get("ContentType", "").lower() for item in types),
            "Macro-enabled workbook unsupported")
    links = _relationships(parts["xl/_rels/workbook.xml.rels"])
    workbook = _xml(parts["xl/workbook.xml"])
    sheets = [item for item in workbook.findall(f"{NS}sheets/{NS}sheet") if item.get("name") == "Cotejo"]
    require(len(sheets) == 1 and sheets[0].get("state", "visible") == "visible", "One visible Cotejo sheet required")
    kind, target = links[sheets[0].get("{" + DOC_REL + "}id")]
    path = target.lstrip("/") if target.startswith("/") else "xl/" + target
    require(kind == DOC_REL + "/worksheet" and path.startswith("xl/worksheets/") and path in parts,
            "Cotejo relationship unavailable")
    strings = []
    tables = [target for kind, target in links.values() if kind == DOC_REL + "/sharedStrings"]
    require(len(tables) <= 1, "Multiple shared string tables")
    if tables:
        target = tables[0]
        string_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        table = _xml(parts[string_path])
        require(table.tag == NS + "sst", "Unexpected shared string table")
        strings = [_text(item) for item in table.findall(NS + "si")]
    return path, _xml(parts[path]), strings


def worksheet_cells(raw):
    path, sheet, strings = cotejo_sheet(_parts(raw))
    require(sheet.tag == NS + "worksheet" and sheet.find(NS + "mergeCells") is None
            and len(sheet.findall(NS + "sheetData")) == 1, "Unsupported Cotejo layout")
    require(not any(col.get("hidden") in ("1", "true") for col in sheet.findall(f"{NS}cols/{NS}col")),
            "Hidden Cotejo columns unsupported")
    rows, cells = set(), {}
    for row in sheet.findall(f"{NS}sheetData/{NS}row"):
        number = row.get("r", "")
        require(re.fullmatch(r"[1-9][0-9]{0,2}", number) and int(number) <= 18 and number not in rows
                and row.get("hidden") not in ("1", "true"), "Unsupported Cotejo row")
        rows.add(number)
        for entry in row:
            address = entry.get("r", "")
            require(entry.tag == NS + "c" and re.fullmatch("[A-Q]" + number, address)
                    and address not in cells, "Unexpected or duplicate Cotejo cell")
            cells[address] = _read_cell(entry, strings, path)
    require(tuple(cells.get(f"{chr(65+i)}8", {}).get("literal") for i in range(len(HEADERS))) == HEADERS,
            "Cotejo column headers differ")
    return cells


def ratio(record):
    return str(Fraction(int(record["numerator"]), int(record["denominator"])))


def reference_inputs(package):
    evidence = json.loads(package[TOP_FILES[1]])
    (probe_index, chosen), = ((i, p) for i, p in enumerate(evidence["probes"]) if p["id"] == "downside_fail")
    probe_pointer = f"/probes/{probe_index}"
    evidence_file = TOP_FILES[1]
    require(chosen["simulation"] == "FAIL" and chosen["decision"] == "PENDING", "Unexpected synthetic comparison")
    base = json.loads(package["Base/results.json"])
    metadata = {
        "B2": base["context"]["deal_id"], "D2": chosen["input"]["criteria_revision"],
        "F2": base["evaluated_as_of_UTC"], "H2": base["project"]["currency"],
        "B3": "Base / Downside", "D3": chosen["input"]["aggregation_rule"],
        "B4": sha(package[TOP_FILES[1]]), "B5": chosen["simulation"], "D5": chosen["expected"],
    }
    references = {addr: {"archivo": "Base/results.json", "puntero": pointer} for addr, pointer in (
        ("B2", "/context/deal_id"), ("F2", "/evaluated_as_of_UTC"), ("H2", "/project/currency"),
    )}
    references.update({addr: {"archivo": evidence_file, "puntero": pointer} for addr, pointer in (
        ("D2", probe_pointer + "/input/criteria_revision"), ("B3", probe_pointer + "/input/required_scenarios"),
        ("D3", probe_pointer + "/input/aggregation_rule"), ("B4", ""), ("B5", probe_pointer + "/simulation"),
        ("D5", probe_pointer + "/expected"),
    )})
    rows = []
    for index, row in enumerate(chosen["comparisons"], 9):
        value = row["metric_record"]
        criterion = row["criterion_record"]
        amount = ratio(value["value"])
        independent = evidence["sources"][row["scenario_id"]]["values"][row["metric_id"]]
        require(amount == independent, "Pilot result and independent metric differ")
        state = {"PASS_CONDITION": "PASS", "FAIL_CONDITION": "FAIL"}[row["state"]]
        rows.append(dict(zip(INPUT_COLS, (
            row["scenario_id"], "aplicable", value["unit"],
            value["definition_ref"] + " | " + value["period_ref"], chosen["input"]["criteria_revision"],
            amount, independent, criterion["pass_condition"]["operator"], ratio(criterion["pass_condition"]["threshold"]),
            criterion["fail_condition"]["operator"], ratio(criterion["fail_condition"]["threshold"]), state, state,
        ))) | {"B": LABELS[row["metric_id"]]})
        comparison_pointer = f"{probe_pointer}/comparisons/{index - 9}"
        metric_pointer = probe_pointer + "/input" + row["metric_locator"].removesuffix("/value")
        rule_pointer = probe_pointer + "/input" + row["criterion_locator"]
        pointers = {
            "A": metric_pointer + "/scenario_id", "B": metric_pointer + "/metric_id",
            "C": metric_pointer + "/applicability", "D": metric_pointer + "/unit",
            "E": metric_pointer, "F": probe_pointer + "/input/criteria_revision",
            "G": metric_pointer + "/value",
            "H": f"/sources/{row['scenario_id']}/values/{row['metric_id']}",
            "J": rule_pointer + "/pass_condition/operator", "K": rule_pointer + "/pass_condition/threshold",
            "L": rule_pointer + "/fail_condition/operator", "M": rule_pointer + "/fail_condition/threshold",
            "N": comparison_pointer + "/state", "O": comparison_pointer + "/state",
        }
        references.update({f"{column}{index}": {"archivo": evidence_file, "puntero": pointer}
                           for column, pointer in pointers.items()})
    return metadata, rows, references


def exact_number(literal):
    if not re.fullmatch(r"[-+]?(?:[0-9]{1,40}(?:\.[0-9]{1,40})?|[0-9]{1,40}/[1-9][0-9]{0,39})", literal or ""):
        return None
    return Fraction(literal)


def compare_cell(cells, address, expected, numeric=False):
    item = cells.get(address, {"kind": "blank", "literal": None})
    kind, literal = item["kind"], item["literal"]
    if kind == "formula":
        return "formula_no_evaluada"
    if kind == "blank" or literal == "":
        return "faltante"
    if numeric:
        value = exact_number(literal) if kind in ("text", "numeric_lexeme") else None
        if value is None:
            return "formato_exacto_no_admitido"
        return None if value == Fraction(expected) else "valor_distinto"
    return None if kind == "text" and literal == expected else "texto_distinto"


def review(raw, package):
    cells = worksheet_cells(raw)
    metadata, rows, references = reference_inputs(package)
    require(cells.get("A1", {}).get("literal") == "ENSAYO SINTÉTICO D53 | Cotejo de Base y Downside",
            "Explicit synthetic Cotejo marker required")
    issues = {addr: err for addr, expected in metadata.items() if (err := compare_cell(cells, addr, expected))}
    output_rows = []
    expected_cells = dict(metadata)
    for index, row in enumerate(rows, 9):
        expected_cells.update({col + str(index): value for col, value in row.items()})
        errors = {col + str(index): err for col, expected in row.items()
                  if (err := compare_cell(cells, col + str(index), expected, numeric=col in "GHKM"))}
        issues.update(errors)
        output_rows.append(dict(escenario=row["A"], metrica=row["B"], estado="PENDING" if errors else "COINCIDE",
                                incidencias=errors))
    require(all(cells.get(f"{col}{index}", {}).get("kind", "blank") == "blank"
                for index in range(15, 19) for col in INPUT_COLS), "Unexpected additional populated Cotejo rows")
    details = []
    for address, issue in sorted(issues.items()):
        item = cells.get(address, {"kind": "blank", "literal": None})
        expected = expected_cells[address]
        received = item["literal"]
        details.append(dict(celda=f"Cotejo!{address}", motivo=issue, recibido=received, tipo_recibido=item["kind"],
                            esperado=expected, fuente=references[address],
                            diferencia_exacta=str(Fraction(received) - Fraction(expected))
                            if issue == "valor_distinto" else None))
    return dict(estado="PENDING" if issues else "COINCIDE", decision="PENDING", synthetic=True,
                workbook_sha256=sha(raw), evidence_sha256=sha(package[TOP_FILES[1]]),
                formulas_cotejo_ignoradas=["I", "P"], incidencias=issues, detalle_incidencias=details,
                comparaciones=output_rows)


def filled_workbook(package, changes=None):
    metadata, rows, _ = reference_inputs(package)
    edits = {"A1": "ENSAYO SINTÉTICO D53 | Cotejo de Base y Downside",
             "A5": "Resultado simulado (Mini-UW)",
             "A6": "Las fracciones se guardan como texto exacto. El verificador compara valores, reglas y estados."} | metadata
    edits.update({f"{col}{i}": value for i, row in enumerate(rows, 9) for col, value in row.items()})
    edits.update(changes or {})
    return replace_cotejo_cells(package[TOP_FILES[0]], edits)


def replace_cotejo_cells(raw, edits):
    parts = _parts(raw)
    path, sheet, _ = cotejo_sheet(parts)
    cells = {entry.get("r"): entry for entry in sheet.findall(f"{NS}sheetData/{NS}row/{NS}c")}
    for address, value in edits.items():
        cell = cells[address]
        for entry in list(cell):
            cell.remove(entry)
        cell.attrib.pop("t", None)
        if isinstance(value, tuple):
            cell.set("t", "str")
            ET.SubElement(cell, NS + "f").text = value[0]
            ET.SubElement(cell, NS + "v").text = value[1]
        elif value is not None and address[0] in "GHKM" and re.fullmatch(r"-?[0-9]{1,15}", value):
            ET.SubElement(cell, NS + "v").text = value
        elif value is not None:
            cell.set("t", "inlineStr")
            ET.SubElement(ET.SubElement(cell, NS + "is"), NS + "t").text = value
    parts[path] = ET.tostring(sheet, encoding="utf-8", xml_declaration=True)
    output = BytesIO()
    with ZipFile(output, "w") as workbook:
        for name, content in sorted(parts.items()):
            workbook.writestr(ZipInfo(name), content)
    return output.getvalue()


def check(package):
    tests = (
        ("coincide", {}, {}),
        ("equivalencia_exacta", {"H11": "0.20"}, {}),
        ("dato_faltante", {"H9": None}, {"H9": "faltante"}),
        ("cero_es_dato", {"G13": None}, {"G13": "faltante"}),
        ("valor_distinto", {"H14": "81"}, {"H14": "valor_distinto"}),
        ("regla_distinta", {"M14": "81"}, {"M14": "valor_distinto"}),
        ("estado_distinto", {"O10": "PASS"}, {"O10": "texto_distinto"}),
        ("revision_distinta", {"D2": "otra-version"}, {"D2": "texto_distinto"}),
        ("formula_con_cache", {"H14": ("40*2", "80")}, {"H14": "formula_no_evaluada"}),
        ("formula_de_pantalla_ignorada", {"P9": ('"REVISAR"', "REVISAR")}, {}),
    )
    reports = {}
    for name, edits, expected in tests:
        raw = filled_workbook(package, edits)
        result = review(raw, package)
        require(result["incidencias"] == expected and result["decision"] == "PENDING",
                f"Unexpected Cotejo result: {name}")
        reports[name] = result
    return reports


def main():
    parser = ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--output", type=Path, help="Write a sample filled workbook and its report.")
    modes.add_argument("--review", type=Path, help="Read a filled D53 synthetic workbook and report discrepancies.")
    args = parser.parse_args()
    try:
        package = build()
        if args.review is not None:
            require(args.review.is_file() and args.review.stat().st_size <= 4 * 1024 * 1024, "Bounded XLSX required")
            result = review(args.review.read_bytes(), package)
        else:
            reports = check(package)
            result = dict(status="passed", decision="PENDING", cases=len(reports),
                          coincide=sum(row["estado"] == "COINCIDE" for row in reports.values()),
                          pending=sum(row["estado"] == "PENDING" for row in reports.values()))
            if args.output is not None:
                target = args.output
                require(not target.exists() and not target.is_symlink() and target.parent.is_dir(), "Use a new output directory")
                with TemporaryDirectory(dir=target.parent, prefix=".miniuw-cotejo-") as temp:
                    staged = Path(temp) / "cotejo"
                    staged.mkdir()
                    (staged / "MiniUW_Cotejo_Sintetico_D53.xlsx").write_bytes(filled_workbook(package))
                    (staged / "revision_cotejo.json").write_bytes(encoded(reports))
                    staged.rename(target)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError, ET.ParseError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
