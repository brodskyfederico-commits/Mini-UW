"""Check one financial correction through both USD 10 ledgers and PDF delivery."""
from copy import deepcopy
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import miniuw_worksheet_v1 as worksheet
from check_reference_package import require
from check_worksheet_alternatives_D155 import workbook_values
from check_worksheet_florida_tax_D203 import settings_for_tax
from check_worksheet_technical_acceptance_D200 import source_files
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from reconcile_worksheet_D179 import cells, exact
from worksheet_intake_D198 import assemble, register
from worksheet_native_mapping_D139 import mapping_catalog
from worksheet_sale_rate_grid_D84 import money

CORRECTION = {
    "Base": ("workbook_raw", "0.04", "0.05"),
    "Downside": ("downside_workbook_raw", "0.07", "0.08"),
}
SALE = "net_sale_distribution"


def reconcile_exit(name, older, newer, old_rate, rate):
    old_cash, cash = (view["cash_per_usd_10"] for view in (older, newer))
    before, after = (view["valuation_and_sale"] for view in (older, newer))
    sale_day = after["sale_date"]
    gross = exact(after["gross_sale_price"])
    scale = exact(cash["scale_factor"])
    require(gross == exact(after["forward_noi"]) / exact(after["exit_cap"]) == exact(before["gross_sale_price"]),
            f"{name}: gross price changed or does not reconcile")
    require(before["sale_date"] == sale_day and exact(old_cash["scale_factor"]) == scale
            and exact(cash["basis_amount"]) * scale == 10, f"{name}: date or USD 10 basis changed")
    cost_delta = gross * (rate - old_rate)
    require(exact(after["sale_cost"]) - exact(before["sale_cost"]) == cost_delta,
            f"{name}: the change in sale costs differs from gross price times the rate change")
    require(newer["debt_principal_paid_at_sale"] == older["debt_principal_paid_at_sale"],
            f"{name}: editing the sale fee changed the debt payoff")

    sale_receipts = []
    for old, new in zip(old_cash["events"], cash["events"], strict=True):
        identity = ("event_id", "kind", "category", "date")
        require(all(old[key] == new[key] for key in identity), f"{name}: a dated movement changed identity")
        if new["category"] == SALE:
            require(new["date"] == sale_day and exact(old["amount"]) - exact(new["amount"]) == cost_delta * scale,
                    f"{name}: net sale cash did not move by the normalized fee change")
            sale_receipts.append(new["amount"])
        else:
            require(exact(old["amount"]) == exact(new["amount"]), f"{name}: a non-sale movement changed")
    sale, = sale_receipts
    received = sum(exact(row["amount"]) for row in cash["events"] if row["kind"] == "distribution")
    paid = sum(exact(row["amount"]) for row in cash["events"] if row["kind"] == "contribution")
    require(received == exact(old_cash["total_distributions"]) - cost_delta * scale == exact(cash["total_distributions"])
            and paid == exact(old_cash["total_contributions"]) == exact(cash["total_contributions"])
            and max(0, paid - received) == exact(cash["unrecovered_after_sale"]),
            f"{name}: the revised totals did not reconcile to the dated ledger")
    return dict(sale_date=sale_day, old_rate=rational(old_rate), new_rate=rational(rate),
                additional=rational(paid - 10), old_received=old_cash["total_distributions"],
                received=cash["total_distributions"], sale=sale, loss_of_receipts=rational(cost_delta * scale),
                unrecovered=cash["unrecovered_after_sale"])


def verify(root):
    originals = source_files(root / "sources")
    revised = originals.copy()
    catalog = mapping_catalog()
    for name, (key, old_rate, rate) in CORRECTION.items():
        values = workbook_values(name, catalog)
        require(originals[key] == native_workbook(values), f"{name}: unexpected source workbook")
        revised[key] = native_workbook(values | {"C68": {"value": rate}})
        old, new = (cells(book) for book in (originals[key], revised[key]))
        require(old.keys() == new.keys() and [cell for cell in old if old[cell] != new[cell]] == ["C68"]
                and old["C68"] == Q(old_rate) and new["C68"] == Q(rate), f"{name}: edit not confined to C68")

    settings = settings_for_tax()
    revised_settings = deepcopy(settings)
    for name, pricing in revised_settings["rent_inputs"]["valuation_and_sale"]["scenarios"].items():
        pricing["sale_cost_inventory_ref"] = f"SYNTHETIC-D217-{name}-corrected-sale-cost"
    old_registry = register(originals, "SYNTHETIC-D217-original")
    new_registry = register(revised, "SYNTHETIC-D217-corrected")
    original, changed, unregistered = (root / name for name in ("original", "corrected", "unregistered"))
    before = assemble(settings, old_registry, originals, original)
    after = assemble(revised_settings, new_registry, revised, changed)
    require(not before["source_blockers"] and not after["source_blockers"], "A registered input did not match")
    unbound = assemble(settings, old_registry, revised, unregistered)
    require(unbound["source_blockers"] == [
        dict(file=book, cells=["C68"], blocker="registered_source_mismatch")
        for book in (worksheet.WORKBOOK_FILE, worksheet.DOWNSIDE_WORKBOOK_FILE)
    ], "Unregistered corrections were not isolated by file and cell")
    archived_files = worksheet.read_package(original)
    revised_files = worksheet.read_package(changed)
    history, current = (json.loads(files["results.json"]) for files in (archived_files, revised_files))
    require(all(model["decision"] == "PENDING" and not model["deployment_enabled"]
                and not model["real_decisions_enabled"] for model in (history, current)), "Real gate changed")
    rejected = json.loads((unregistered / "results.json").read_bytes())
    require(all(view["cash_per_usd_10"] is None for view in rejected["scenarios"].values()),
            "The unregistered correction produced cash")
    ledgers = {name: reconcile_exit(name, history["scenarios"][name], current["scenarios"][name], Q(old_rate), Q(rate))
               for name, (_, old_rate, rate) in CORRECTION.items()}

    revision = root / "revision-vigente.json"
    revision.write_bytes(revised_files[worksheet.CURRENT_REVISION_FILE])
    destination = root / "MiniUW_Vigente.pdf"
    command = [sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "deliver"]

    def deliver(package):
        return subprocess.run([*command, str(package), "--current-revision", str(revision),
                               "--output", str(destination)], capture_output=True, check=False)

    for package in (original, unregistered):
        blocked = deliver(package)
        require(blocked.returncode == 2 and json.loads(blocked.stderr)["decision"] == "PENDING"
                and not destination.exists(), f"{package.name}: a stale report was emitted")
    accepted = deliver(changed)
    require(accepted.returncode == 0, accepted.stderr.decode())
    receipt = json.loads(accepted.stdout)
    report = destination.read_bytes()
    require(receipt["status"] == "delivered_synthetic_pdf" and receipt["vigencia"] == "VIGENTE"
            and receipt["decision"] == "PENDING" and receipt["pdf_sha256"] == sha256(report).hexdigest()
            and receipt["revision_sha256"] == sha256(revision.read_bytes()).hexdigest()
            and report == revised_files["MiniUW_Resumen.pdf"] != archived_files["MiniUW_Resumen.pdf"],
            "The delivered PDF or its revision did not match the audited corrected package")
    page, = PdfReader(destination).pages
    text = page.extract_text()
    require("Decisión real PENDING" in text and "USD 10" in text, "The PDF omitted the report basis or real status")
    for name, row in ledgers.items():
        require(f"{name} | Aporte extra {money(row['additional'])}" in text
                and f"Cobro total {money(row['received'])}" in text
                and any(row["sale_date"] in line and "Cobro neto de venta" in line and money(row["sale"]) in line
                        for line in text.splitlines()), f"{name}: the PDF omitted the corrected cash amount or date")
    require(worksheet.read_package(original) == archived_files and worksheet.read_package(changed) == revised_files,
            "Delivery changed the archived packages")
    return dict(status="passed", decision="PENDING", ledgers=ledgers, delivery=receipt)


class WorksheetCashRevisionTests(unittest.TestCase):
    def test_registered_sale_cost_correction_recomputes_both_scenarios(self):
        with TemporaryDirectory(prefix="miniuw-d217-") as temp:
            self.assertEqual(verify(Path(temp))["status"], "passed")
