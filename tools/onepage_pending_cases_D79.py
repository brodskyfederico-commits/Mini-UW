"""Render the eight pending reports and their USD 10 synthetic variants on one page."""
from argparse import ArgumentParser
from datetime import date
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import wrap

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from check_pending_investor_answers_D78 import verify as verify_cases
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import _pdf, _pdf_string
from miniuw_worksheet_v1 import encoded
from worksheet_investor_D74 import display


REPORT = "docs/review/MiniUW_USD10_Ocho_Casos_D79.pdf"
LABELS = {
    "MiniUW_D50_Piloto_Refinanciacion__above-capacity": (
        "D50 · Capacidad", "El préstamo de USD 400 supera USD 392,13. Se probó un préstamo de USD 150."),
    "MiniUW_D67_Motivo_Cierre_Pendiente": (
        "D67 · Impuesto", "Falta definir si aplica el impuesto de venta y el importe que iría al cierre."),
    "miniuw-v1-current-settled-blocked-example": (
        "T109 · Saldo contable", "Falta el saldo previo de cuentas por pagar y su conciliación con la caja."),
    "miniuw-v1-current-settled-expired-example": (
        "T109 · Saldo vencido", "Falta evidencia contable vigente al corte de los saldos antes y después."),
    "miniuw-v1-phased-settled-blocked-example": (
        "T110 · Base de renta", "Falta la regla documentada para reconocer la renta de cada tramo en su período."),
    "miniuw-v1-phased-settled-expired-example": (
        "T110 · Renta vencida", "Falta un calendario de renta del primer tramo vigente al corte."),
    "miniuw-v1-worksheet-settled-expired-example": (
        "T111 · Hoja vencida", "Falta una hoja de entrada vigente y vinculada al expediente."),
    "miniuw-v1-worksheet-settled-zero-conflict-example": (
        "T111 · Cero en C8", "La hoja dice cero y el expediente no declara un valor. Falta conciliarlos."),
}


def money(value):
    return display(value).replace(".", ",")


def day(value):
    return date.fromisoformat(value).strftime("%d/%m/%y")


def calendar(view):
    def group(key):
        return tuple((row["date"], row["category"], money(row["amount"])) for row in view[key])
    return group("receipt_events"), group("extra_events")


def build_page():
    evidence = verify_cases()
    reports = evidence["reports"]
    require([row["report"] for row in reports] == list(LABELS) and evidence["decision"] == "PENDING",
            "Unexpected pending report inventory")
    commands = []
    expected = []

    def box(x, y, w, h, color):
        commands.append(f"{color} rg {x} {y} {w} {h} re f".encode())

    def text(x, y, w, label, size=9, *, bold=False, light=False):
        require(24 <= x and x + w <= 768 and 26 <= y and y + size <= 588
                and len(label) * size * 0.6 <= w, f"Text outside its cell: {label}")
        color = "1 1 1" if light else "0.08 0.16 0.23"
        font = "F2" if bold else "F1"
        commands.append(f"{color} rg BT /{font} {size} Tf 1 0 0 1 {x} {y} Tm (".encode()
                        + _pdf_string(label) + b") Tj ET")
        expected.append(label)

    box(24, 525, 744, 63, "0.06 0.17 0.25")
    text(35, 561, 712, "SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?", 17, bold=True, light=True)
    text(35, 540, 712, "MINI-UW  /  D79  /  OCHO VARIANTES SINTÉTICAS", 10, bold=True, light=True)
    text(32, 504, 728, "Por USD 10 iniciales. Los ocho expedientes originales siguen PENDING.", 10, bold=True)
    text(32, 486, 728, "Los importes de la tabla son USD. La letra identifica el calendario de la variante.", 9)

    box(24, 454, 744, 23, "0.85 0.91 0.95")
    columns = ((32, 132, "Caso original"), (168, 270, "Qué falta en el original"),
               (443, 42, "Fechas"), (494, 65, "Cobro"),
               (565, 81, "Aporte extra"), (654, 108, "Sin recuperar"))
    for x, w, heading in columns:
        text(x, 462, w, heading, 9, bold=True)
    calendars = {}
    for i, row in enumerate(reports):
        label, missing = LABELS[row["report"]]
        view = row["synthetic_variant"]["answers_per_usd_10"]
        key = calendar(view)
        code = calendars.setdefault(key, chr(ord("A") + len(calendars)))
        bottom = 454 - 31 * (i + 1)
        if i % 2 == 0:
            box(24, bottom, 744, 31, "0.95 0.97 0.98")
        baseline = bottom + 17
        text(32, baseline, 132, label, 9, bold=True)
        missing_lines = wrap(missing, 49, break_long_words=False)
        require(len(missing_lines) <= 2, "A blocker exceeds its two-line cell")
        for j, line in enumerate(missing_lines):
            text(168, baseline - 11 * j, 270, line, 9)
        text(443, baseline, 42, code, 10, bold=True)
        for field, (x, w) in zip(("receipts", "extra_contributions", "unrecovered"),
                                 ((494, 65), (565, 81), (654, 108)), strict=True):
            text(x, baseline, w, money(view[field]), 10, bold=True)

    require(len(calendars) == 4, "Expected four distinct cash calendars")
    text(32, 185, 728, "CUÁNDO SE COBRA Y CUÁNDO SE APORTA MÁS", 11, bold=True)
    labels = {"operating_distribution": "operación", "net_refinance_distribution": "refi",
              "net_sale_distribution": "venta", "additional_capital": "aporte"}
    for i, ((receipts, extras), code) in enumerate(calendars.items()):
        top = 166 - i * 29
        flows = "  |  ".join(f"{day(when)} {labels[kind]} +{value}" for when, kind, value in receipts)
        text(32, top, 728, f"{code}  Cobros: {flows}", 9, bold=True)
        funding = "  |  ".join(f"{day(when)} {labels[kind]} {value}" for when, kind, value in extras)
        text(47, top - 12, 713, f"Aporte extra: {funding or '0,00'}", 8.5)
    text(32, 37, 728, "Simulación. Sin recuperar = aportes acumulados menos cobros al cierre, si hay déficit.", 8)
    pdf = _pdf(commands)
    page, = PdfReader(BytesIO(pdf)).pages
    lines = page.extract_text()
    require(all(label in lines for label in expected), "A visible table cell did not survive PDF extraction")
    return pdf, dict(status="passed", decision="PENDING", page_count=1, cases=len(reports),
                     cash_calendars=len(calendars), d78_evidence_sha256=sha(encoded(evidence)), pdf_sha256=sha(pdf))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new one-page PDF instead of auditing the archived copy.")
    args = parser.parse_args()
    pdf, summary = build_page()
    if args.output:
        with TemporaryDirectory(dir=args.output.parent) as temporary:
            source = Path(temporary) / "report.pdf"
            source.write_bytes(pdf)
            os.link(source, args.output)
    else:
        require((ROOT / REPORT).read_bytes() == pdf, "Archived one-page report differs from the source replay")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
