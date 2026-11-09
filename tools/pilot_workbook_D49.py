"""Write the small D49 XLSX from independent events and the screening evidence."""
from dataclasses import dataclass
from fractions import Fraction
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZipInfo


MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"
TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
METRICS = ("YoC", "Spread", "Equity recuperado", "Equity cash-in", "Ocupación de equilibrio",
           "CoC pos-refi", "Equity / TDC", "Múltiplo de equity (EM)", "TIR / IRR", "Asking / precio soportado")
DIRECTIONS = (
    "D49 | Planilla de cotejo del primer piloto Mini-UW",
    "01. Flujos contiene la referencia independiente del caso sintético. Cobros / aportes = múltiplo de equity.",
    "02. Ensayo muestra las condiciones de prueba, el dictamen esperado y el del simulador. El dictamen operativo sigue PENDING.",
    "03. Cotejo se entrega en blanco para el futuro piloto. Completa una fila por métrica y escenario. Duplica filas si hacen falta.",
    "04. Usa la misma revisión, unidad, base y período. Conserva los valores sin redondear y documenta cualquier diferencia.",
    "05. Diferencia resta los dos valores numéricos. Cotejo de estado compara los textos. Un resultado coincidente requiere revisar las fuentes.",
    "06. Documenta criterios aprobados y agregación fuera del ensayo. Los umbrales sintéticos no se trasladan a otro deal.",
    "07. Si faltan datos o reglas, existe un conflicto o hay banda intermedia, el caso permanece PENDING.",
    "08. Un PASS de ensayo es una prueba técnica. El piloto real requiere autorización y contraste independiente.",
)
NOTES = {
    "igualdad_pass": "La igualdad entra en PASS con el operador inclusivo.",
    "fallo_explicito": "El mismo múltiplo cae bajo el límite FAIL de este ensayo.",
    "banda_intermedia": "Entre ambos límites. Pendiente de revisión profesional.",
    "regla_faltante": "Falta el criterio de FAIL.",
    "reglas_solapadas": "La igualdad satisface PASS y FAIL a la vez.",
    "fuente_vencida": "El expediente retira el múltiplo por evidencia vencida.",
}


@dataclass(frozen=True)
class Formula:
    expression: str
    cached: object = ""


def cell(row, column, value, style=0):
    address = chr(65 + column) + str(row)
    tag = f'<c r="{address}" s="{style}"'
    if value is None:
        return tag + "/>"
    if isinstance(value, Formula):
        result_type = ' t="str"' if isinstance(value.cached, str) else ""
        return (tag + result_type + f"><f>{escape(value.expression)}</f>"
                f"<v>{escape(str(value.cached))}</v></c>")
    if isinstance(value, (int, float)):
        return tag + f"><v>{value}</v></c>"
    return tag + f' t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>'


def sheet(rows, widths, header_row=1, filter_table=False):
    cols = "".join(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>'
                   for i, width in enumerate(widths, 1))
    data = []
    for row_number, row in enumerate(rows, 1):
        height = 29 if row_number == header_row else 25
        values = "".join(cell(row_number, i, value, 1 if row_number == header_row
                              else 2 if value is None else 0) for i, value in enumerate(row))
        data.append(f'<row r="{row_number}" ht="{height}" customHeight="1">{values}</row>')
    end_column = chr(64 + len(widths))
    filter_xml = f'<autoFilter ref="A{header_row}:{end_column}{len(rows)}"/>' if filter_table else ""
    return (f'{HEADER}<worksheet xmlns="{MAIN}"><sheetViews><sheetView workbookViewId="0">'
            f'<pane ySplit="{header_row}" topLeftCell="A{header_row+1}" activePane="bottomLeft" state="frozen"/>'
            f'</sheetView></sheetViews><cols>{cols}</cols><sheetData>{"".join(data)}</sheetData>{filter_xml}</worksheet>')


def condition(row):
    threshold = row["threshold"]
    if threshold is None:
        return "Sin regla"
    exact = Fraction(int(threshold["numerator"]), int(threshold["denominator"]))
    return f"{row['operator']} {exact}"


def workbook_bytes(evidence):
    guide = sheet([[line] for line in DIRECTIONS], [132])
    independent = evidence["independent_reference"]
    events = independent["events"]
    last = len(events) + 1
    flows = [["Fecha", "Tipo de flujo", "Concepto", "Importe USD"]]
    flows.extend([date, "Aporte" if kind == "contribution" else "Cobro", category, float(Fraction(value))]
                 for date, kind, category, value in events)
    flows += [
        [],
        ["Aportes brutos", Formula(f'SUMIF(B2:B{last},"Aporte",D2:D{last})', float(Fraction(independent["contributions"])))],
        ["Cobros brutos", Formula(f'SUMIF(B2:B{last},"Cobro",D2:D{last})', float(Fraction(independent["receipts"])))],
        ["Múltiplo (EM)", Formula(f"B{last+3}/B{last+2}", float(Fraction(independent["equity_multiple"])))],
        ["Múltiplo exacto", independent["equity_multiple"]],
    ]
    flow_sheet = sheet(flows, [24, 21, 34, 17])

    tests = [["Ensayo sintético", "EM exacto", "Regla PASS", "Regla FAIL", "Esperado", "Simulador", "Operativo", "Control probado"]]
    for row in evidence["cases"]:
        case = row["input"]
        criterion = case["criteria"][0]
        value = case["metric_values"][0]["value"]
        tests.append([row["id"], independent["equity_multiple"] if value is not None else "Retirado",
                      condition(criterion["pass_condition"]), condition(criterion["fail_condition"]),
                      row["expected"], row["simulation"], row["operational_decision"], NOTES[row["id"]]])
    rehearsal = sheet(tests, [23, 14, 16, 16, 14, 14, 14, 50], filter_table=True)

    compare = [
        ["Cotejo del piloto real | completar con la revisión aplicable"],
        ["Deal / ID", None, "Revisión", None, "Fecha de corte", None, "Moneda", None],
        ["Escenarios requeridos", None, "Regla de agregación y fuente", None],
        ["Cálculo independiente y versión", None, "Autor / revisor", None],
        ["Resultado del caso (Mini-UW)", None, "Esperado independiente", None, "Resultado aprobado y fecha", None],
        ["Una fila por métrica y escenario. Registra no aplica con su motivo. Copia las fórmulas al duplicar filas."],
        ["La diferencia es Mini-UW menos referencia. Completar los estados y revisar la evidencia aunque coincidan."],
        ["Escenario", "Métrica", "Aplica / motivo", "Unidad", "Definición / base / período", "Fuente / revisión",
         "Valor Mini-UW", "Valor independiente", "Diferencia", "Oper. PASS", "Umbral PASS", "Oper. FAIL", "Umbral FAIL",
         "Estado Mini-UW", "Estado referencia", "Cotejo de estado", "Notas"],
    ]
    for r, metric in enumerate(METRICS, len(compare) + 1):
        compare.append([None, metric, None, None, None, None, None, None,
                        Formula(f'IF(COUNT(G{r}:H{r})=2,G{r}-H{r},"")'),
                        None, None, None, None, None, None,
                        Formula(f'IF(OR(N{r}="",O{r}=""),"PENDIENTE",IF(EXACT(N{r},O{r}),"COINCIDE","REVISAR"))', "PENDIENTE"),
                        None])
    compare_sheet = sheet(compare, [18, 27, 19, 15, 32, 26, 17, 19, 15, 13, 15, 13, 15, 17, 18, 19, 32],
                          header_row=8, filter_table=True)

    sheets = [("Guia", guide), ("Cotejo", compare_sheet), ("Ensayo", rehearsal), ("Flujos", flow_sheet)]
    overrides = {"xl/workbook.xml": "sheet.main", "xl/styles.xml": "styles"} | {
        f"xl/worksheets/sheet{i}.xml": "worksheet" for i in range(1, 5)
    }
    content_types = f'{HEADER}<Types xmlns="{TYPES}">' + (
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
    ) + "".join(f'<Override PartName="/{path}" ContentType="application/vnd.openxmlformats-officedocument.'
                f'spreadsheetml.{kind}+xml"/>' for path, kind in overrides.items()) + "</Types>"
    workbook = (f'{HEADER}<workbook xmlns="{MAIN}" xmlns:r="{OFFICE}"><bookViews><workbookView/></bookViews><sheets>'
                + "".join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets, 1))
                + '</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    relationships = (f'{HEADER}<Relationships xmlns="{PACKAGE}">'
                     + "".join(f'<Relationship Id="rId{i}" Type="{OFFICE}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                               for i in range(1, 5))
                     + f'<Relationship Id="rId5" Type="{OFFICE}/styles" Target="styles.xml"/></Relationships>')
    styles = f'''{HEADER}<styleSheet xmlns="{MAIN}">
      <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>
      <font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts>
      <fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
      <fill><patternFill patternType="solid"><fgColor rgb="FF142638"/><bgColor indexed="64"/></patternFill></fill>
      <fill><patternFill patternType="solid"><fgColor rgb="FFEAF5F4"/><bgColor indexed="64"/></patternFill></fill></fills>
      <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
      <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
      <cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
      <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
      <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0"/></cellXfs>
      <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
    parts = {
        "[Content_Types].xml": content_types,
        "_rels/.rels": f'{HEADER}<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": workbook,
        "xl/_rels/workbook.xml.rels": relationships,
        "xl/styles.xml": styles,
    } | {f"xl/worksheets/sheet{i}.xml": xml for i, (_, xml) in enumerate(sheets, 1)}
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for name, xml in sorted(parts.items()):
            info = ZipInfo(name)
            archive.writestr(info, xml.encode("utf-8"))
    return output.getvalue()
