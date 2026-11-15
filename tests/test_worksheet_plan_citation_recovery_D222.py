"""Restore the shared plan citation and deliver both recalculated USD 10 ledgers."""
from argparse import ArgumentParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_worksheet_dscr_citation_recovery_D221 import BlockedRevision, verify_citation_recovery

from check_reference_package import require
from miniuw_worksheet_v1 import sha
from reconcile_worksheet_D179 import exact

AREA = "Compartido:GBA"
A601 = "p. 2 / A601 / Declared GBA"
A101 = "p. 4 / A101 / Gross building area"


def misdirect_plan_citation(review):
    review["bots"]["B06"]["locator"] = A101


def restored_plan_citation(bots, sources):
    a101, a601 = bots["B05"], bots["B06"]
    plan_sha = sha(sources["plan_raw"])
    for record, locator, page, sheet in ((a101, A101, 4, "A101"), (a601, A601, 2, "A601")):
        require((record["locator"], record["page"], record["sheet"], record["source_file"],
                 record["source_sha256"]) == (locator, page, sheet, "Plan.pdf", plan_sha),
                f"{sheet}: restored citation did not match the registered original")
        for method in ("text", "ocr"):
            source = record["observations"][method]
            require(source["locator"] == locator and source["source_sha256"] == plan_sha
                    and source["unit"] == "m2" and exact(source["value"]) == 1000,
                    f"{sheet}: {method} did not reproduce the cited area")
    require(exact(bots["B07"]["value"]) == exact(bots["B08"]["area"]["value"]) == 1000
            and exact(bots["B09"]["difference"]) == 0, "The plans and GC area no longer reconcile")
    return dict(citation="Plan.pdf " + A601, area_m2=1000, plan_sha256=plan_sha)


def verify(root):
    blocked = BlockedRevision("cita-invalida", (AREA,), ("Base", "Downside"), misdirect_plan_citation)
    return verify_citation_recovery(root, milestone="D222", blocked_revisions=(blocked,),
                                    restored_citation=restored_plan_citation)


class WorksheetPlanCitationRecoveryTests(unittest.TestCase):
    def test_corrected_shared_citation_restores_both_ledgers_and_only_current_pdf(self):
        with TemporaryDirectory(prefix="miniuw-d222-") as temp:
            self.assertEqual(verify(Path(temp))["status"], "passed")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory for the synthetic trial")
    options = parser.parse_args()
    options.output.mkdir()
    print(json.dumps(verify(options.output), ensure_ascii=False, indent=2))
