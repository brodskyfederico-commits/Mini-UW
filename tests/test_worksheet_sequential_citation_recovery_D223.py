"""Recover the shared plan citation before the Downside DSCR citation."""
from argparse import ArgumentParser
import json
from pathlib import Path

from test_worksheet_dscr_citation_recovery_D221 import (
    BlockedRevision, DSCR, omit_dscr_citation, restored_dscr_citation, verify_citation_recovery,
)
from test_worksheet_plan_citation_recovery_D222 import AREA, misdirect_plan_citation, restored_plan_citation


def omit_both_citations(review):
    misdirect_plan_citation(review)
    omit_dscr_citation(review)


def restored_citations(bots, sources):
    return dict(plan=restored_plan_citation(bots, sources), dscr=restored_dscr_citation(bots, sources))


def verify(root, *, milestone="D223", publish=True):
    failures = BlockedRevision("ambos-fallos", (AREA, DSCR), ("Base", "Downside"), omit_both_citations)
    plan_restored = BlockedRevision("plano-repuesto", (DSCR,), ("Downside",), omit_dscr_citation)
    return verify_citation_recovery(root, milestone=milestone, blocked_revisions=(failures, plan_restored),
                                    restored_citation=restored_citations, publish=publish)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory for the synthetic trial")
    options = parser.parse_args()
    options.output.mkdir()
    print(json.dumps(verify(options.output), ensure_ascii=False, indent=2))
