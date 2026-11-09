"""Render the worksheet recovery sensitivity in the existing one-page case layout."""
from argparse import ArgumentParser
from decimal import Decimal
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, local_file, require
from check_worksheet_sale_recovery_D43 import observe_run, worksheet_bindings
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import _pdf, _pdf_string
from miniuw_foundation.worksheet_settled_output import assemble_worksheet_settled_output
from miniuw_foundation.worksheet_settled_report import _render_verified


def money(cents):
    return f"{cents // 100}.{cents % 100:02d} USD"


def render(binding, rate):
    raw = local_file(ROOT, binding["path"]).read_text(encoding="utf-8")
    require(digest(raw) == binding["sha256"], "Worksheet source bytes differ")
    run = assemble_worksheet_settled_output(raw.encode())
    pdf, evidence = render_run(raw, run, rate)
    require((evidence["cash_recovery"] is not None) is binding["expected_cash_available"], "Worksheet gate differs")
    return pdf, evidence


def render_run(raw, run, rate):
    recovery = observe_run(raw, run, (rate,))
    cash = recovery["cash_recovery"]
    if cash is None:
        line = "Recuperacion descontada: PENDIENTE por hoja o evidencia."
    else:
        threshold = cash["observations"][0]["minimum_gross_sale_price_in_cents"]
        percent = Decimal(rate.numerator * 100) / Decimal(rate.denominator)
        line = (f"Venta bruta: {cash['gross_sale_price']} USD | Minimo para recuperar (VP): {money(threshold)}"
                f" | Descuento sintetico: {percent:f}% mensual")
    base = _render_verified(run)
    manifest = base.manifest
    spans = manifest["display_spans"]
    row = dict(text=line, x=28, y=173, font_size=7.5, width=736, result_pointers=["/cash_recovery"])
    require(not any(span["y"] < row["y"] + row["font_size"]
                    and span["y"] + span["font_size"] > row["y"] for span in spans),
            "Recovery row overlaps an existing worksheet span")
    require(len(line) * row["font_size"] * 0.6 <= row["width"], "Recovery row exceeds one-page width")
    commands = [b"0.06 0.17 0.25 rg 24 524 744 64 re f"]
    for span in spans + [row]:
        x, y, size = span["x"], span["y"], span["font_size"]
        bold = y in (566, 546, 476, 457, 440, 214, 224, 294, 173, 164, 40)
        commands.append(b"1 1 1 rg" if y >= 532 else b"0.06 0.17 0.25 rg")
        commands.append(f'BT /{"F2" if bold else "F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()
                        + _pdf_string(span["text"]) + b") Tj ET")
    pdf = _pdf(commands)
    pages = PdfReader(BytesIO(pdf)).pages
    require(len(pages) == 1 and pages[0].mediabox == PdfReader(BytesIO(base.pdf_bytes)).pages[0].mediabox,
            "Worksheet recovery must fit the original single page")
    extracted = pages[0].extract_text()
    require(all(span["text"] in extracted for span in spans + [row]), "Missing worksheet recovery PDF text")
    evidence = dict(worksheet_run_sha256=run.sha256, original_manifest_sha256=base.manifest_sha256,
                    recovery_sha256=digest(canonical(recovery)), pdf_sha256=sha(pdf), monthly_discount_rate=str(rate),
                    page_count=1, recovery_line=line, cash_recovery=cash, decision="PENDING")
    return pdf, evidence


def summary(bindings, rates):
    # A fixed archived sensitivity point exercises all four gates without setting a default for report generation.
    reports = {name: render(binding, rates[-1])[1] for name, binding in bindings.items()}
    require(len(reports) == 4, "Unexpected worksheet recovery PDF inventory")
    return dict(status="passed", decision="PENDING", one_page_reports=len(reports),
                reports_with_prices=sum(row["cash_recovery"] is not None for row in reports.values()),
                reports_withheld=sum(row["cash_recovery"] is None for row in reports.values()),
                worksheet_recovery_page_sha256=digest(canonical(reports)))


if __name__ == "__main__":
    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", action="store_true", help="Reproduce the four worksheet gate cases.")
    group.add_argument("--case", help="Archived worksheet case to render.")
    parser.add_argument("--monthly-rate", type=Fraction)
    parser.add_argument("--output", type=Path, help="New PDF path for the selected case.")
    args = parser.parse_args()
    try:
        bindings, rates = worksheet_bindings()
        if args.summary:
            require(args.monthly_rate is args.output is None, "Summary does not accept report options")
            result = summary(bindings, rates)
        else:
            require(args.case in bindings and args.monthly_rate in rates and args.output is not None,
                    "A known case, an explicit archived monthly rate and a new output path are required")
            pdf, result = render(bindings[args.case], args.monthly_rate)
            with TemporaryDirectory(dir=args.output.parent, prefix=".miniuw-recovery-") as staging:
                prepared = Path(staging) / "summary.pdf"
                prepared.write_bytes(pdf)
                os.link(prepared, args.output)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
