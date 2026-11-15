"""Recover Downside DSCR before the plan citation shared by both scenarios."""
from argparse import ArgumentParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_worksheet_dscr_citation_recovery_D221 import (
    BlockedRevision, DSCR, verify_citation_recovery,
)
from test_worksheet_plan_citation_recovery_D222 import AREA, misdirect_plan_citation
from test_worksheet_sequential_citation_recovery_D223 import omit_both_citations, restored_citations


def verify(root):
    failures = BlockedRevision("ambos-fallos", (AREA, DSCR), ("Base", "Downside"), omit_both_citations)
    dscr_restored = BlockedRevision("dscr-repuesto", (AREA,), ("Base", "Downside"), misdirect_plan_citation)
    return verify_citation_recovery(root, milestone="D224", blocked_revisions=(failures, dscr_restored),
                                    restored_citation=restored_citations)


class WorksheetReverseCitationRecoveryTests(unittest.TestCase):
    def test_dscr_alone_cannot_release_either_ledger_or_pdf(self):
        with TemporaryDirectory(prefix="miniuw-d224-") as temp:
            self.assertEqual(verify(Path(temp))["status"], "passed")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory for the synthetic trial")
    options = parser.parse_args()
    options.output.mkdir()
    print(json.dumps(verify(options.output), ensure_ascii=False, indent=2))
