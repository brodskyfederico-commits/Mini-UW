"""Publish eight calculated synthetic revisions with the pending originals preserved."""
from argparse import ArgumentParser
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import wrap
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from check_initial_equity_basis_D80 import verify_variants
from check_operating_replay_D20 import ROOT, amount, require
from check_pending_investor_answers_D78 import verify as verify_cases
from check_worksheet_refinance_D45 import EVENTS, render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from onepage_pending_cases_D79 import LABELS, day, money


PACKAGE = "docs/review/MiniUW_D81_Ocho_Revisiones_Sinteticas.zip"
FIXES = {
    "selected_principal_exceeds_declared_bank_capacity":
        "Préstamo sintético de USD 150 dentro de la capacidad. Cierre recalculado.",
    "tax-unresolved:cost_applicability_unresolved":
        "Se probó el inventario sintético completo de costos de venta del caso price_400.",
    "accounting_balances_missing_or_negative":
        "Se incorporó el saldo previo de cuentas por pagar y se concilió la liquidación.",
    "/settlement/accounting_before_after:evidence_expired":
        "Se usó evidencia contable sintética vigente al corte, antes y después de liquidar.",
    "period_recognition_basis_ref_missing":
        "Se usó la base sintética de reconocimiento de renta por tramo y período.",
    "/T110/rental_calendars/0:evidence_expired":
        "Se usó el calendario sintético del primer tramo vigente al corte.",
    "/T111/worksheet:evidence_expired":
        "Se usó la hoja sintética vigente y vinculada al expediente.",
    "INPUT_C8:worksheet_value_differs_from_claim":
        "Se documentó el cero explícito de C8 con su fuente y se concilió con el expediente.",
}


def render_revision(label, source, basis, fix):
    received = source["receipts"]
    extra = source["extra_contributions"]
    total = basis["total_equity"]
    shortfall = source["unrecovered"]
    require(amount(basis["initial_equity"]) == amount(source["initial_equity"]) == 10
            and amount(basis["extra_equity"]) == amount(extra)
            and amount(total) == 10 + amount(extra)
            and amount(shortfall) == max(0, amount(total) - amount(received)),
            "The revision does not reconcile on the initial USD 10 basis")
    net = rational(amount(received) - amount(total))
    lines = [(f"Cuánto cobro: USD {money(received)} | Resultado neto: USD {money(net)}", True),
             (f"Aportes extra: USD {money(extra)} | Caja sin recuperar: USD {money(shortfall)}", True),
             (f"Aporte inicial: USD 10,00 | Aportes totales: USD {money(total)}", False),
             ("Cuándo: calendario de aportes y cobros por USD 10 iniciales", True)]
    events = basis["initial_events"] + source["extra_events"] + source["receipt_events"]
    for event in sorted(events, key=lambda row: row["date"]):
        sign = "-" if event["kind"] == "contribution" else "+"
        lines.append((f"{day(event['date'])}  {EVENTS[event['category']]}  {sign}USD {money(event['amount'])}", False))
    lines.append(("Qué faltaba en el original", True))
    lines.extend((line, False) for line in wrap(label[1], 115))
    lines.append(("Qué se resolvió en esta variante sintética", True))
    lines.extend((line, False) for line in wrap(fix, 115))
    lines.append(("Original: PENDING. Retorno personal real y decisión de inversión: PENDING.", True))
    return render_page(label[0], lines, 23, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "REVISIÓN CALCULADA | Caja sintética del equity agregado")


def build_package():
    original = verify_cases()
    bases, _ = verify_variants()
    require(original["original_reports_kept_pending"] == 8 and len(bases) == 8,
            "Expected eight distinct pending originals")
    files = {}
    revisions = []
    for item in original["reports"]:
        name = item["report"]
        variant = item["synthetic_variant"]
        basis = bases[name]
        fix = FIXES[item["blocker"]]
        require(all(variant[key] == value for key, value in basis["source"].items()),
                "The funding basis and the variant have different sources")
        pdf = render_revision(LABELS[name], variant["answers_per_usd_10"], basis, fix)
        path = name + "__revision_D81.pdf"
        files[path] = pdf
        revisions.append(dict(report=name, revision_state="computed_synthetic", original_state="PENDING",
                              original_pdf_sha256=item["original_pdf_sha256"], original_cash=None,
                              original_blocker=item["blocker"], original_missing=item["missing_for_usd_10"],
                              synthetic_correction=fix, variant=variant, initial_equity_basis=basis,
                              pdf=path, pdf_sha256=sha(pdf), decision="PENDING"))
    require(len(files) == len(revisions) == 8, "The revision inventory is incomplete")
    files["Revisiones_por_USD_10.json"] = encoded(dict(
        schema="miniuw.synthetic-investor-revisions.v1", decision="PENDING", scope="synthetic_aggregate_project_equity",
        real_decisions_enabled=False, deployment_enabled=False, d78_sha256=sha(encoded(original)),
        d77_archive_sha256=original["source_archive_sha256"], revisions=revisions))
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(ZipInfo(name), raw, compress_type=ZIP_DEFLATED)
    return buffer.getvalue(), dict(status="passed", decision="PENDING", revised_synthetic_reports=8,
                                   one_page_pdfs=8, historical_pending_reports=8)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new archive instead of auditing the published copy.")
    args = parser.parse_args()
    archive, summary = build_package()
    if args.output:
        with TemporaryDirectory(dir=args.output.parent) as temporary:
            source = Path(temporary) / "revisions.zip"
            source.write_bytes(archive)
            os.link(source, args.output)
    else:
        require((ROOT / PACKAGE).read_bytes() == archive, "Archived revisions differ from the source replay")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
