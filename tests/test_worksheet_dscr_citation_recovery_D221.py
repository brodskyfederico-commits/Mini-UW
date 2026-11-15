"""Replay a missing Downside DSCR citation, restore it and deliver the current PDF."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import miniuw_worksheet_v1 as worksheet
from check_reference_package import require
from check_worksheet_florida_tax_D203 import settings_for_tax
from check_worksheet_technical_acceptance_D200 import source_files
from miniuw_foundation.debt_service import rational
from reconcile_worksheet_D179 import exact
from worksheet_intake_D198 import assemble, register
from worksheet_sale_rate_grid_D84 import money

CURRENT = worksheet.CURRENT_REVISION_FILE
DSCR = "Downside:permanent:minimum_dscr"
LOCATOR = "Evidence.pdf p. 5 / C72"
OUTPUT = "MiniUW_Sintetico_D221_Revision_Corregida.pdf"


def reconcile_cash(scenario):
    cash = scenario["cash_per_usd_10"]
    events = cash["events"]
    initial, = [event for event in events if event["category"] == "initial_capital"]
    require(exact(cash["basis_amount"]) * exact(cash["scale_factor"]) == exact(initial["amount"]) == 10,
            "The initial USD 10 basis did not reconcile")
    contributions = sum(exact(event["amount"]) for event in events if event["kind"] == "contribution")
    receipts = sum(exact(event["amount"]) for event in events if event["kind"] == "distribution")
    require((contributions, receipts, receipts - contributions, max(0, contributions - receipts)) ==
            tuple(exact(cash[field]) for field in ("total_contributions", "total_distributions",
                                                  "net_cash_profit", "unrecovered_after_sale")),
            "The totals did not reconcile with gross dated events")
    return dict(additional=rational(contributions - 10), received=rational(receipts),
                unrecovered=cash["unrecovered_after_sale"],
                events=[{field: event[field] for field in ("date", "category", "amount")} for event in events])


def verify(root):
    settings = settings_for_tax() | {"schema": worksheet.WORKBOOK_CRITICAL_EVIDENCE_SCHEMA}
    sources = source_files(root / "sources")
    current_file = root / "revision-vigente.json"
    output = root / OUTPUT

    def archive(label):
        path = root / label
        intake = assemble(settings, register(sources, f"SYNTHETIC-D221-{label}"), sources, path)
        require(not intake["source_blockers"], "An original source failed registration")
        files = worksheet.read_package(path)
        model = json.loads(files["results.json"])
        require(model["decision"] == "PENDING" and not model["deployment_enabled"]
                and not model["real_decisions_enabled"], "A real gate opened")
        return path, files, model

    def designate(package_files):
        current_file.write_bytes(package_files[CURRENT])

    def expect_block(directory, reason):
        try:
            worksheet.deliver_package(directory, output, current_file)
        except ValueError as error:
            require(reason in str(error), f"Unexpected reason for withholding delivery: {error}")
            require(not output.exists(), "A rejected revision left a PDF")
            return str(error)
        raise AssertionError(f"{directory.name} unexpectedly produced an external PDF")

    prior_path, prior_files, prior = archive("control-anterior")
    observed = deepcopy(prior["local_review"])
    del observed["financial_bindings"]

    def without_citation(case, plan_raw, *, evidence_raw, evidence_milestone):
        require(plan_raw == sources["plan_raw"] and evidence_raw == sources["evidence_raw"]
                and evidence_milestone == "D162"
                and case["local_sources"] == json.loads(prior_files["case.json"])["local_sources"],
                "The simulated omission must come from the registered synthetic sources")
        evidence = deepcopy(observed)
        del evidence["bots"]["B08"]["bank_pdf_by_scenario"]["Downside"]["locators"]["C72"]
        return evidence

    review_target = "worksheet_documented_finance_D147.review_documents"
    with patch(review_target, side_effect=without_citation):
        blocked_path, blocked_files, blocked = archive("sin-cita")
        designate(blocked_files)
        rejected = expect_block(blocked_path, f"Cotejo D219 PENDING: {DSCR}")
    require(blocked["critical_evidence_review"]["fields"][DSCR]["status"] == "FALSE_GREEN"
            and blocked["critical_evidence_review"]["affected_scenarios"] == ["Downside"]
            and blocked["simulation_result"] == "PENDING"
            and blocked["scenarios"]["Downside"]["cash_per_usd_10"] is None,
            "The missing citation did not withhold the dependent calculation")
    require(blocked["scenarios"]["Base"] == prior["scenarios"]["Base"], "Base changed while Downside was blocked")

    # With the simulated omission removed, B08 reads the original PDF again.
    fixed_path, fixed_files, fixed = archive("corregida")
    quote = fixed["local_review"]["bots"]["B08"]["bank_pdf_by_scenario"]["Downside"]
    require(quote["locators"]["C72"] == LOCATOR and quote["observations"]["C72"] == ["multiple", "1.30"]
            and quote["source_sha256"] == worksheet.sha(sources["evidence_raw"]),
            "The source citation and DSCR were not recovered from the original PDF")
    require(fixed["critical_evidence_review"]["counts"] == {"VERIFIED_GREEN": 48, "FALSE_GREEN": 0, "PENDING": 0}
            and fixed["scenarios"] == prior["scenarios"], "The restored calculation differs from the supported control")
    for path in ("case.json", worksheet.PLAN_FILE, worksheet.EVIDENCE_FILE,
                 worksheet.WORKBOOK_FILE, worksheet.DOWNSIDE_WORKBOOK_FILE, worksheet.CRITERIA_FILE):
        require(prior_files[path] == blocked_files[path] == fixed_files[path], f"{path} changed between revisions")
    require(len({files[CURRENT] for files in (prior_files, blocked_files, fixed_files)}) == 3,
            "The three archives require distinct revision records")
    ledgers = {name: reconcile_cash(view) for name, view in fixed["scenarios"].items()}

    designate(fixed_files)
    with patch(review_target, side_effect=without_citation):
        expect_block(blocked_path, f"Cotejo D219 PENDING: {DSCR}")
    stale = expect_block(prior_path, "archived_revision_differs_from_current")
    audit = worksheet.verify_package(fixed_path, current_revision_raw=current_file.read_bytes())
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and audit["critical_evidence"]["status"] == "PASSED", "B16 did not reproduce the corrected revision")

    command = [sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "deliver", str(fixed_path),
               "--current-revision", str(current_file), "--output", str(output)]
    delivery = json.loads(subprocess.check_output(command))
    pdf = output.read_bytes()
    require(delivery["status"] == "delivered_synthetic_pdf" and delivery["decision"] == "PENDING"
            and delivery["current_revision"] == "SYNTHETIC-D221-corregida"
            and delivery["revision_sha256"] == worksheet.sha(fixed_files[CURRENT])
            and delivery["pdf_sha256"] == worksheet.sha(pdf)
            and pdf == fixed_files["MiniUW_Resumen.pdf"] != blocked_files["MiniUW_Resumen.pdf"],
            "Delivery did not match the audited current PDF")
    page, = PdfReader(output).pages
    text = page.extract_text()
    require("USD 10" in text and "Decisión real PENDING" in text, "The normalizing basis or real status is absent")
    for name, ledger in ledgers.items():
        require(f"{name} | Aporte extra {money(ledger['additional'])}" in text
                and f"Cobro total {money(ledger['received'])}" in text,
                f"{name}: published totals do not agree with the ledger")
        for event in ledger["events"]:
            if event["category"] in ("net_refinance_distribution", "operating_distribution", "net_sale_distribution"):
                require(any(event["date"] in line and money(event["amount"]) in line for line in text.splitlines()),
                        f"{name}: PDF omits a dated receipt")
    for path, files in ((prior_path, prior_files), (blocked_path, blocked_files), (fixed_path, fixed_files)):
        require(worksheet.read_package(path) == files, f"Delivery modified archive {path.name}")
    return dict(status="passed", decision="PENDING", historical_return="PENDING",
                citation=LOCATOR, minimum_dscr=quote["observations"]["C72"],
                historical_rejection=stale, false_green_rejection=rejected,
                ledgers=ledgers, delivery=delivery)


class WorksheetDscrCitationRecoveryTests(unittest.TestCase):
    def test_only_the_corrected_revision_delivers_reconciled_usd10_cash(self):
        with TemporaryDirectory(prefix="miniuw-d221-") as temp:
            self.assertEqual(verify(Path(temp))["status"], "passed")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory for the synthetic trial")
    options = parser.parse_args()
    options.output.mkdir()
    print(json.dumps(verify(options.output), ensure_ascii=False, indent=2))
