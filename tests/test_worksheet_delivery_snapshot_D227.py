"""Require the audited synthetic package to stay unchanged through PDF delivery."""
from argparse import ArgumentParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pypdf import PdfReader

from test_worksheet_dscr_citation_recovery_D221 import reconcile_cash, verify_published_cash, worksheet
from check_reference_package import require
from check_worksheet_florida_tax_D203 import settings_for_tax
from check_worksheet_technical_acceptance_D200 import source_files
from worksheet_intake_D198 import assemble, register


def verify(root):
    settings = settings_for_tax() | {"schema": worksheet.WORKBOOK_CRITICAL_EVIDENCE_SCHEMA}
    sources = source_files(root / "sources")
    package = root / "expediente"
    registered = assemble(settings, register(sources, "SYNTHETIC-D227-entrega"), sources, package)
    require(not registered["source_blockers"], "Synthetic source registration failed")
    saved = worksheet.read_package(package)
    revision = root / "revision.json"
    revision.write_bytes(saved[worksheet.CURRENT_REVISION_FILE])
    output = root / "MiniUW_Sintetico_D227_Vigente.pdf"
    evidence = package / worksheet.EVIDENCE_FILE
    original_audit = worksheet._audit_package

    def audit_then_change(directory):
        audited = original_audit(directory)
        evidence.write_bytes(saved[worksheet.EVIDENCE_FILE] + b"\n")
        return audited

    try:
        with patch.object(worksheet, "_audit_package", side_effect=audit_then_change):
            worksheet.deliver_package(package, output, revision)
    except ValueError as exc:
        rejection = str(exc)
        require("El expediente cambió durante la entrega" in rejection, rejection)
        require(evidence.read_bytes() == saved[worksheet.EVIDENCE_FILE] + b"\n",
                "The injected change did not take place")
        require(not output.exists() and not list(root.glob(".miniuw-delivery-*")),
                "A rejected attempt left an export or a staging directory")
    else:
        raise AssertionError("Delivery accepted a package changed after audit")
    finally:
        evidence.write_bytes(saved[worksheet.EVIDENCE_FILE])

    receipt = worksheet.deliver_package(package, output, revision)
    pdf = output.read_bytes()
    require(receipt["decision"] == "PENDING" and receipt["vigencia"] == "VIGENTE"
            and receipt["current_revision"] == "SYNTHETIC-D227-entrega"
            and receipt["pdf_sha256"] == worksheet.sha(pdf) and pdf == saved["MiniUW_Resumen.pdf"]
            and list(root.glob("*.pdf")) == [output] and worksheet.read_package(package) == saved,
            "Retry did not publish an exact, unchanged audit snapshot")
    model = json.loads(saved["results.json"])
    require(not model["real_decisions_enabled"] and not model["deployment_enabled"],
            "The synthetic case opened a real decision gate")
    ledgers = {name: reconcile_cash(view) for name, view in model["scenarios"].items()}
    page, = PdfReader(output).pages
    verify_published_cash(page.extract_text(), ledgers, model["scenarios"])
    return dict(status="passed", rejection=rejection, delivery=receipt,
                movements={name: len(ledger["events"]) for name, ledger in ledgers.items()})


class WorksheetDeliverySnapshotTests(unittest.TestCase):
    def test_package_change_after_audit_blocks_export_and_restoration_allows_retry(self):
        with TemporaryDirectory(prefix="miniuw-d227-") as temp:
            self.assertEqual(verify(Path(temp))["status"], "passed")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    print(json.dumps(verify(args.output), ensure_ascii=False, indent=2))
