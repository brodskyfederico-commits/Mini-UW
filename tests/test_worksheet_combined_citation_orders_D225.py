"""Audit both citation-recovery orders and export only the final designated revision."""
from argparse import ArgumentParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_worksheet_dscr_citation_recovery_D221 import (
    CURRENT, expect_delivery_block, publish_citation_recovery, worksheet,
)
from test_worksheet_reverse_citation_recovery_D224 import verify as dscr_first
from test_worksheet_sequential_citation_recovery_D223 import verify as plan_first

OUTPUT = "MiniUW_Sintetico_D225_Revision_Final_Vigente.pdf"


def verify(root):
    plan_branch, dscr_branch = (root / name for name in ("plano-primero", "dscr-primero"))
    plan_branch.mkdir()
    dscr_branch.mkdir()
    plan = plan_first(plan_branch, milestone="D225-plano-primero", publish=False)
    dscr = dscr_first(dscr_branch, milestone="D225-dscr-primero", publish=False)

    if plan["status"] != "passed" or dscr["status"] != "passed" or plan["ledgers"] != dscr["ledgers"]:
        raise AssertionError("The two correction orders did not reconcile to the same dated USD 10 cash")
    if any(result["decision"] != "PENDING" or result["historical_return"] != "PENDING"
           or result["delivery"] is not None for result in (plan, dscr)):
        raise AssertionError("A review was exported before both orders were compared")
    if list(root.rglob("MiniUW_Sintetico_*_Revision_*.pdf")):
        raise AssertionError("An intermediate revision left an exported PDF")

    plan_final, dscr_final = plan_branch / "corregida", dscr_branch / "corregida"
    prior = worksheet.read_package(plan_final)
    current = worksheet.read_package(dscr_final)
    if prior[CURRENT] == current[CURRENT] or prior["MiniUW_Resumen.pdf"] != current["MiniUW_Resumen.pdf"]:
        raise AssertionError("Distinct complete revisions must reconcile to the same internal report")

    revision = root / "revision-vigente.json"
    revision.write_bytes(current[CURRENT])
    output = root / OUTPUT
    stale = expect_delivery_block(plan_final, revision, output, "archived_revision_differs_from_current")
    delivered = publish_citation_recovery(dscr_final, revision, output, dscr["ledgers"])
    if (delivered["current_revision"] != "SYNTHETIC-D225-dscr-primero-corregida"
            or list(root.rglob("MiniUW_Sintetico_*_Revision_*.pdf")) != [output]):
        raise AssertionError("The designated revision did not produce the sole external PDF")
    if worksheet.read_package(plan_final) != prior or worksheet.read_package(dscr_final) != current:
        raise AssertionError("Delivery changed a corrected archive")
    return dict(status="passed", decision="PENDING", historical_return="PENDING",
                ledgers=dscr["ledgers"], checks={"plan_first": plan["rejected_revisions"],
                                                "dscr_first": dscr["rejected_revisions"]},
                earlier_complete_revision_rejection=stale, delivery=delivered)


class WorksheetCombinedCitationOrdersTests(unittest.TestCase):
    def test_both_orders_reconcile_to_one_current_pdf(self):
        with TemporaryDirectory(prefix="miniuw-d225-") as temp:
            self.assertEqual(verify(Path(temp))["status"], "passed")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory for the synthetic comparison")
    options = parser.parse_args()
    options.output.mkdir()
    print(json.dumps(verify(options.output), ensure_ascii=False, indent=2))
