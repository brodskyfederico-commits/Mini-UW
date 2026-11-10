"""Reproduce the eight historical blockers and exercise independent synthetic variants."""
from argparse import ArgumentParser
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from check_investor_answers_D77 import INDEX, answers, verified_reports
from check_operating_replay_D20 import ROOT, amount, local_file, require
from miniuw_foundation.current_settled_case import assemble_current_settled_case
from miniuw_foundation.phased_settled_output import assemble_phased_settled_output
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_settled_output import assemble_worksheet_settled_output
from miniuw_linked_cotejo_D54 import publish
from miniuw_worksheet_v1 import build_results, encoded
from reissue_investor_reports_D76 import FIXTURE, normalize
from worksheet_investor_D74 import display


CONTROLS = {
    "T109": ("docs/review/current-settled-fixtures-T109.json", assemble_current_settled_case),
    "T110": ("docs/review/phased-settled-fixtures-T110.json", assemble_phased_settled_output),
    "T111": ("docs/review/worksheet-settled-fixtures-T111.json", assemble_worksheet_settled_output),
}
CASES = (
    ("MiniUW_D50_Piloto_Refinanciacion__above-capacity", "selected_principal_exceeds_declared_bank_capacity",
     "Préstamo dentro de la capacidad sustentada y recálculo del cierre de refinanciación.", "worksheet", "cash-out"),
    ("MiniUW_D67_Motivo_Cierre_Pendiente", "tax-unresolved:cost_applicability_unresolved",
     "Definición y evidencia de si aplica el impuesto de venta. Si aplica, falta su monto y tratamiento en el cierre.",
     "worksheet", "price_400"),
    ("miniuw-v1-current-settled-blocked-example", "accounting_balances_missing_or_negative",
     "Saldo de cuentas por pagar antes de liquidar y conciliación de la liquidación con caja y contabilidad.",
     "T109", "current"),
    ("miniuw-v1-current-settled-expired-example", "/settlement/accounting_before_after:evidence_expired",
     "Evidencia contable antes y después de la liquidación, vigente al corte.",
     "T109", "current"),
    ("miniuw-v1-phased-settled-blocked-example", "period_recognition_basis_ref_missing",
     "Base documentada para reconocer la renta por tramo en el período operativo.",
     "T110", "current"),
    ("miniuw-v1-phased-settled-expired-example", "/T110/rental_calendars/0:evidence_expired",
     "Calendario de renta del primer tramo vigente al corte.",
     "T110", "current"),
    ("miniuw-v1-worksheet-settled-expired-example", "/T111/worksheet:evidence_expired",
     "Hoja de entrada vigente al corte y vinculada al expediente.",
     "T111", "matched"),
    ("miniuw-v1-worksheet-settled-zero-conflict-example", "INPUT_C8:worksheet_value_differs_from_claim",
     "Afirmación con fuente que concilie el cero explícito en la hoja con el dato ausente en el expediente.",
     "T111", "zero-matched"),
)


def worksheet_variant(row, replacement):
    original = json.loads(row["case_raw"])
    changed = original | {"archive_case": replacement}
    raw = encoded(changed)
    result, _ = build_results(raw)
    require(result["decision"] == "PENDING" and result["project"] is not None,
            "The synthetic worksheet variant did not produce illustrative cash")
    return result["project"], dict(kind="archived_worksheet_variant",
                                   previous_case=original["archive_case"], case=replacement,
                                   source_sha256=sha(raw), archive_sha256=original["archive_sha256"])


def settled_variant(control, name):
    path, assemble = CONTROLS[control]
    fixtures = json.loads(local_file(ROOT, path).read_bytes())
    row, = (record for record in fixtures["cases"] if record["label"] == name)
    raw = local_file(ROOT, row["path"]).read_bytes()
    require(sha(raw) == row["source_sha256"], "The synthetic control source differs")
    run = assemble(raw)
    data = run.payload
    require(run.sha256 == row["run_sha256"] and data["state"] == row["state"]
            and data["decision"] == "PENDING" and data["current_project_return_story"] is not None,
            "The archived synthetic variant did not reproduce")
    return data["current_project_return_story"], dict(kind=control, case=name, source_path=row["path"],
                                                      source_sha256=sha(raw), run_sha256=run.sha256)


def verify():
    source, _ = verified_reports()
    with ZipFile(BytesIO(source)) as archive:
        reports = json.loads(archive.read(INDEX))["reports"]
    expected = {name for name, *_ in CASES}
    require(len(expected) == 8 and {name for name, row in reports.items() if row["state"] == "PENDING"} == expected,
            "Expected exactly the eight published pending reports")
    delivered = json.loads(local_file(ROOT, FIXTURE).read_bytes())["delivered"]
    delivered_by_name = {row["id"]: row for row in delivered}
    checked = []
    variants = {}
    for name, blocker, needed, control, replacement in CASES:
        original = reports[name]
        require(original["cash"] is None and blocker in original["blockers"],
                "The original pending report acquired cash or lost its blocker")
        key = (control, replacement)
        if key not in variants:
            story, provenance = (worksheet_variant(delivered_by_name[name], replacement) if control == "worksheet"
                                 else settled_variant(control, replacement))
            cash = normalize(story)
            require(cash is not None, "The variant lacks a positive and reconciled USD initial basis")
            variants[key] = (answers(cash), provenance)
        view, provenance = variants[key]
        checked.append(dict(report=name, original_decision="PENDING", original_cash=None,
                            original_pdf_sha256=original["reissued_pdf_sha256"], blocker=blocker,
                            missing_for_usd_10=needed,
                            synthetic_variant=provenance | dict(answers_per_usd_10=view)))
    expected_cash = [("13.02", "0.00", "0.00"), ("12.92", "0.00", "0.00"),
                     *[("8.40", "4.00", "5.60")] * 2, *[("7.78", "4.00", "6.22")] * 4]
    for item, expected in zip(checked, expected_cash, strict=True):
        cash = item["synthetic_variant"]["answers_per_usd_10"]
        require(tuple(display(cash[field]) for field in ("receipts", "extra_contributions", "unrecovered")) == expected,
                "The illustrative cash, additional equity or unrecovered balance differs")
        require(cash["receipt_events"][-1]["date"] == "2027-07-01"
                and all(event["date"] == "2026-11-01" and amount(event["amount"]) == 4
                        for event in cash["extra_events"]), "The sale or contribution date differs")
    require(checked[-1]["synthetic_variant"]["case"] == "zero-matched", "Explicit zero control was not exercised")
    return dict(status="passed", decision="PENDING", synthetic_only=True,
                original_reports_kept_pending=8, synthetic_cases_exercised=8,
                source_archive_sha256=sha(source), reports=checked)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.output:
        publish(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != "reports"}, ensure_ascii=False))
