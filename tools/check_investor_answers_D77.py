"""Reissue and audit the four USD 10 answers in all historical investor reports."""
from argparse import ArgumentParser
from collections import Counter
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pypdf import PdfReader

from check_operating_replay_D20 import amount, require
from check_worksheet_refinance_D45 import EVENTS, annual_irr, render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from reissue_investor_reports_D76 import TITLE, build_archive
from worksheet_investor_D74 import display


INDEX = "Resultados_por_USD_10.json"
QUESTIONS = ("Cuanto cobro", "Cuando cobro", "Aportes extra", "Caja sin recuperar")


def answers(cash):
    totals = Counter()
    receipts = []
    extra = []
    for event in cash["events"]:
        value = amount(event["amount"])
        kind, category = event["kind"], event["category"]
        require(kind in ("contribution", "distribution") and value >= 0, "Unsupported cash event")
        totals[kind] += value
        if kind == "contribution":
            if category == "initial_capital":
                totals["initial"] += value
            elif value:
                extra.append(event)
        elif value:
            receipts.append(event)
    contributed = amount(cash.get("contributions", cash.get("gross_contributions")))
    received = amount(cash.get("distributions", cash.get("gross_distributions")))
    net = amount(cash.get("net_cash", cash.get("net_cash_profit")))
    unrecovered = amount(cash.get("unrecovered_at_cutoff", cash.get("cash_shortfall_at_horizon")))
    require(totals["initial"] == 10 and totals["contribution"] == contributed
            and totals["distribution"] == received and net == received - contributed
            and unrecovered == max(0, contributed - received)
            and sum(amount(e["amount"]) for e in extra) == contributed - 10,
            "The USD 10 answers do not reconcile to the dated ledger")
    return dict(initial_equity=rational(totals["initial"]), receipts=rational(received),
                receipt_events=receipts, extra_contributions=rational(contributed - 10),
                extra_events=extra, unrecovered=rational(unrecovered))


def report_cash(report):
    investor = report.get("investor")
    if investor is None:
        return {"": report["cash"]}
    if "cash" in investor:
        return {"": investor["cash"]}
    require(set(investor) == {"Base", "Downside"}, "Expected the two illustrative scenarios")
    return {scenario: investor[scenario]["cash"] for scenario in ("Base", "Downside")}


def render_report(name, report):
    cases = report_cash(report)
    require(all(cash is None for cash in cases.values()) or all(cash is not None for cash in cases.values()),
            "Partial scenario availability requires an explicit report")
    if all(cash is None for cash in cases.values()):
        lines = [(f"{label}: PENDIENTE.", True) for label in QUESTIONS]
        lines.append(("Faltan flujos verificables o una base positiva de aporte inicial en USD.", False))
        lines.extend((f"Motivo registrado: {reason[:96]}", False) for reason in report["blockers"][:2])
        checked = {"": None}
    else:
        checked = {label: answers(cash) for label, cash in cases.items()}

        def column(field):
            return " | ".join(f"{label + ' ' if label else ''}USD {display(row[field])}"
                              for label, row in checked.items())

        lines = [(f"Cuanto cobro: {column('receipts')}", True),
                 (f"Aportes extra: {column('extra_contributions')}", True),
                 (f"Caja sin recuperar: {column('unrecovered')}", True),
                 ("Cuando cobro: calendario de caja por USD 10 iniciales", True)]
        grouped = {}
        for label, cash in cases.items():
            for event in cash["events"]:
                date, category, kind = (event[key] for key in ("date", "category", "kind"))
                row = grouped.setdefault((date, category, kind), {})
                row[label] = row.get(label, 0) + amount(event["amount"])
        for (date, category, kind), values in sorted(grouped.items()):
            parts = []
            for label in cases:
                prefix = f"{label} " if label else ""
                if label in values:
                    value = values[label]
                    sign = ("-" if kind == "contribution" else "+") if value else ""
                    parts.append(f"{prefix}{sign}USD {display(rational(value))}")
                else:
                    parts.append(f"{prefix}Sin evento")
            lines.append((f"{date}  {EVENTS.get(category, category)} | " + " | ".join(parts), False))
        for label, cash in cases.items():
            net = cash.get("net_cash", cash.get("net_cash_profit"))
            lines.append((f"{label + ' | ' if label else ''}Neto USD {display(net)} | "
                          f"Multiplo {display(cash['equity_multiple'])}x | "
                          f"TIR anual {annual_irr(cash['annual_irr_roots'])}", False))
    lines.append(("Ejemplo sintetico. Retorno personal real pendiente.", False))
    scope = ("Equity agregado del proyecto" if report["scope"] == "synthetic_aggregate_project_equity"
             else "Reparto hipotetico por participante")
    pdf = render_page(name, lines, 16, TITLE, f"PENDIENTE | {scope}")
    page, = PdfReader(BytesIO(pdf)).pages
    text = page.extract_text().splitlines()
    require(TITLE in text and all(label in text[3 + i] for i, label in
                                 enumerate(("Cuanto cobro", "Aportes extra", "Caja sin recuperar", "Cuando cobro")
                                           if all(v is not None for v in checked.values()) else QUESTIONS)),
            "The four answers must be visible before the detail")
    require(not (Counter(line for line, _ in lines) - Counter(text)), "A dated flow or answer is missing from the PDF")
    return pdf, checked


def verified_reports():
    source_archive, _ = build_archive()
    with ZipFile(BytesIO(source_archive)) as previous:
        index = json.loads(previous.read(INDEX))
        files = {}
        for name, report in index["reports"].items():
            filename = name + ".pdf"
            require(sha(previous.read(filename)) == report["reissued_pdf_sha256"],
                    "The corrected source report differs from its manifest")
            pdf, checked = render_report(name, report)
            report["d76_pdf_sha256"] = report["reissued_pdf_sha256"]
            report["reissued_pdf_sha256"] = sha(pdf)
            report["verified_answers_per_usd_10"] = checked
            files[filename] = pdf
    reports = index["reports"].values()
    pending = sum(all(value is None for value in r["verified_answers_per_usd_10"].values()) for r in reports)
    index.update(schema="miniuw.synthetic-investor-reissues.v2", d76_archive_sha256=sha(source_archive))
    files[INDEX] = encoded(index)
    out = BytesIO()
    with ZipFile(out, "w", compression=ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(ZipInfo(name), raw, compress_type=ZIP_DEFLATED)
    return out.getvalue(), dict(status="passed", decision="PENDING", reports=len(reports),
                               answers_verified=len(reports) - pending, pending=pending,
                               complete_dated_calendars=True)


def main():
    parser = ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--output", type=Path)
    group.add_argument("--audit", type=Path)
    args = parser.parse_args()
    archive, summary = verified_reports()
    if args.audit:
        require(args.audit.is_file() and not args.audit.is_symlink()
                and args.audit.stat().st_size == len(archive) and args.audit.read_bytes() == archive,
                "Verified report archive differs from the source replay")
    if args.output:
        with TemporaryDirectory(dir=args.output.parent) as temporary:
            prepared = Path(temporary) / "reports.zip"
            prepared.write_bytes(archive)
            os.link(prepared, args.output)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
