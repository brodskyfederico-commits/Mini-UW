"""Verify citation recovery and current-only synthetic worksheet delivery."""
from argparse import ArgumentParser
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable
import json
import re
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
from check_worksheet_return_metrics_D167 import KINDS
from check_worksheet_technical_acceptance_D200 import source_files
from miniuw_foundation.debt_service import rational
from reconcile_worksheet_D179 import exact
from worksheet_intake_D198 import assemble, register
from worksheet_sale_rate_grid_D84 import money

CURRENT = worksheet.CURRENT_REVISION_FILE
DSCR = "Downside:permanent:minimum_dscr"
LOCATOR = "Evidence.pdf p. 5 / C72"


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


def verify_published_cash(text, ledgers, views):
    require("USD 10" in text and "Decisión real PENDING" in text, "The normalizing basis or real status is absent")
    dated = defaultdict(lambda: defaultdict(int))
    scopes = ("Base", "Downside")
    for name in scopes:
        ledger = ledgers[name]
        require(f"{name} | Aporte extra {money(ledger['additional'])}" in text
                and f"Cobro total {money(ledger['received'])}" in text, f"{name}: PDF totals disagree with the ledger")
        for event in ledger["events"]:
            dated[event["date"], event["category"]][name] += exact(event["amount"])
        closing = views[name]["construction_refinance"]
        cash_in = closing["projected_cash_in_required"]
        if cash_in is not None:
            scale = exact(views[name]["cash_per_usd_10"]["scale_factor"])
            dated[closing["date"], "refinance_cash_in"][name] = exact(cash_in) * scale

    expected = []
    for (day, category), movements in sorted(dated.items(), key=lambda item: (item[0][0], list(KINDS).index(item[0][1]))):
        amounts = " / ".join(money(rational(movements[name])) if name in movements else "—" for name in scopes)
        expected.append(f"{day} {KINDS[category]} · {amounts}")
    visible = [" ".join(line.split()) for line in text.splitlines() if re.match(r"^\d{4}-\d{2}-\d{2}\s", line)]
    require(visible == expected, "The PDF dated rows differ from the reconciled Base and Downside events")


@dataclass(frozen=True)
class BlockedRevision:
    name: str
    fields: tuple[str, ...]
    affected_scenarios: tuple[str, ...]
    invalidate: Callable[[dict], None]


def verify_citation_recovery(root, *, milestone, blocked_revisions, restored_citation):
    settings = settings_for_tax() | {"schema": worksheet.WORKBOOK_CRITICAL_EVIDENCE_SCHEMA}
    sources = source_files(root / "sources")
    current_file = root / "revision-vigente.json"
    output = root / f"MiniUW_Sintetico_{milestone}_Revision_Corregida.pdf"

    def archive(label):
        path = root / label
        intake = assemble(settings, register(sources, f"SYNTHETIC-{milestone}-{label}"), sources, path)
        require(not intake["source_blockers"], "An original source failed registration")
        files = worksheet.read_package(path)
        model = json.loads(files["results.json"])
        require(model["decision"] == "PENDING" and not model["deployment_enabled"]
                and not model["real_decisions_enabled"], "A real gate opened")
        return path, files, model

    def designate(package_files):
        current_file.write_bytes(package_files[CURRENT])

    def expect_block(directory, *reasons):
        try:
            worksheet.deliver_package(directory, output, current_file)
        except ValueError as error:
            require(all(reason in str(error) for reason in reasons), f"Unexpected delivery rejection: {error}")
            require(not output.exists(), "A rejected revision left a PDF")
            return str(error)
        raise AssertionError(f"{directory.name} unexpectedly produced an external PDF")

    prior_path, prior_files, prior = archive("control-anterior")
    observed = deepcopy(prior["local_review"])
    del observed["financial_bindings"]

    def faulty_review(revision):
        def read(case, plan_raw, *, evidence_raw, evidence_milestone):
            require(plan_raw == sources["plan_raw"] and evidence_raw == sources["evidence_raw"]
                    and evidence_milestone == "D162"
                    and case["local_sources"] == json.loads(prior_files["case.json"])["local_sources"],
                    "The simulated citation fault must come from the registered synthetic sources")
            evidence = deepcopy(observed)
            revision.invalidate(evidence)
            return evidence
        return patch("worksheet_documented_finance_D147.review_documents", side_effect=read)

    rejected_archives = []
    rejected_revisions = {}
    for revision in blocked_revisions:
        with faulty_review(revision):
            path, files, blocked = archive(revision.name)
            designate(files)
            rejection = expect_block(path, "Cotejo D219 PENDING", *revision.fields)
        evidence = blocked["critical_evidence_review"]
        actual_faults = {field for field, row in evidence["fields"].items() if row["status"] == "FALSE_GREEN"}
        require(actual_faults == set(revision.fields)
                and evidence["counts"] == dict(VERIFIED_GREEN=48 - len(revision.fields),
                                               FALSE_GREEN=len(revision.fields), PENDING=0)
                and evidence["affected_scenarios"] == list(revision.affected_scenarios)
                and blocked["simulation_result"] == "PENDING", "The citation fault did not reach the expected scenarios")
        ledgers = {}
        for name, view in blocked["scenarios"].items():
            if name in revision.affected_scenarios:
                require(view["state"] == "PENDING" and view["cash_per_usd_10"] is None
                        and view["capacity"] is None and view["noi_by_period"] == {},
                        f"{name}: the faulty citation did not withhold the dependent calculation")
                ledgers[name] = None
            else:
                require(view == prior["scenarios"][name], f"{name}: an independent scenario changed")
                ledgers[name] = reconcile_cash(view)
        rejected_archives.append((revision, path, files))
        rejected_revisions[revision.name] = dict(rejection=rejection, critical_evidence=evidence["counts"],
                                                  false_green_fields=sorted(actual_faults), ledgers=ledgers)

    # The corrected run reads the registered PDF without the injected fault.
    fixed_path, fixed_files, fixed = archive("corregida")
    restored = restored_citation(fixed["local_review"]["bots"], sources)
    require(fixed["critical_evidence_review"]["counts"] == {"VERIFIED_GREEN": 48, "FALSE_GREEN": 0, "PENDING": 0}
            and fixed["scenarios"] == prior["scenarios"], "The restored calculation differs from the supported control")
    archives = [(prior_path, prior_files), *((path, files) for _, path, files in rejected_archives),
                (fixed_path, fixed_files)]
    for name in ("case.json", worksheet.PLAN_FILE, worksheet.EVIDENCE_FILE,
                 worksheet.WORKBOOK_FILE, worksheet.DOWNSIDE_WORKBOOK_FILE, worksheet.CRITERIA_FILE):
        require(all(files[name] == prior_files[name] for _, files in archives), f"{name} changed between revisions")
    require(len({files[CURRENT] for _, files in archives}) == len(archives),
            "The archives require distinct revision records")
    ledgers = {name: reconcile_cash(view) for name, view in fixed["scenarios"].items()}

    designate(fixed_files)
    for revision, path, _ in rejected_archives:
        with faulty_review(revision):
            expect_block(path, "Cotejo D219 PENDING", *revision.fields)
    stale = expect_block(prior_path, "archived_revision_differs_from_current")
    audit = worksheet.verify_package(fixed_path, current_revision_raw=current_file.read_bytes())
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE"
            and audit["critical_evidence"]["status"] == "PASSED", "B16 did not reproduce the corrected revision")

    command = [sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "deliver", str(fixed_path),
               "--current-revision", str(current_file), "--output", str(output)]
    delivery = json.loads(subprocess.check_output(command))
    pdf = output.read_bytes()
    require(delivery["status"] == "delivered_synthetic_pdf" and delivery["decision"] == "PENDING"
            and delivery["current_revision"] == f"SYNTHETIC-{milestone}-corregida"
            and delivery["revision_sha256"] == worksheet.sha(fixed_files[CURRENT])
            and delivery["pdf_sha256"] == worksheet.sha(pdf)
            and pdf == fixed_files["MiniUW_Resumen.pdf"]
            and all(pdf != files["MiniUW_Resumen.pdf"] for _, _, files in rejected_archives)
            and list(root.glob("*.pdf")) == [output],
            "Delivery did not match the audited current PDF")
    page, = PdfReader(output).pages
    verify_published_cash(page.extract_text(), ledgers, fixed["scenarios"])
    for path, files in archives:
        require(worksheet.read_package(path) == files, f"Delivery modified archive {path.name}")
    return dict(status="passed", decision="PENDING", historical_return="PENDING",
                historical_rejection=stale, false_green_rejection=next(iter(rejected_revisions.values()))["rejection"],
                rejected_revisions=rejected_revisions, ledgers=ledgers, delivery=delivery, **restored)


def omit_dscr_citation(review):
    del review["bots"]["B08"]["bank_pdf_by_scenario"]["Downside"]["locators"]["C72"]


def restored_dscr_citation(bots, sources):
    quote = bots["B08"]["bank_pdf_by_scenario"]["Downside"]
    require(quote["locators"]["C72"] == LOCATOR and quote["observations"]["C72"] == ["multiple", "1.30"]
            and quote["source_sha256"] == worksheet.sha(sources["evidence_raw"]),
            "The source citation and DSCR were not recovered from the original PDF")
    return dict(citation=LOCATOR, minimum_dscr=quote["observations"]["C72"])


def verify(root):
    blocked = BlockedRevision("cita-invalida", (DSCR,), ("Downside",), omit_dscr_citation)
    return verify_citation_recovery(root, milestone="D221", blocked_revisions=(blocked,),
                                    restored_citation=restored_dscr_citation)


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
