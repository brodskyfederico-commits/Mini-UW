"""Check append-only synthetic revision registration and old workbook withdrawal."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from check_cotejo_review_D53 import filled_workbook
from check_operating_replay_D20 import require
from miniuw_current_cotejo_D59 import load, record, review_current
from miniuw_scenario_package_D52 import REVISION, THRESHOLD_REVISION, read, write


def rejected(operation, message):
    try:
        operation()
    except ValueError as error:
        require(message in str(error), f"Unexpected rejection: {error}")
    else:
        raise ValueError("Expected current revision rejection")


def verify():
    with TemporaryDirectory(prefix="miniuw-d59-") as temp:
        root = Path(temp)
        old, new = root / "R2", root / "R3"
        write(old, REVISION)
        write(new, THRESHOLD_REVISION)
        old_book, new_book = root / "R2.xlsx", root / "R3.xlsx"
        old_book.write_bytes(filled_workbook(read(old)))
        new_book.write_bytes(filled_workbook(read(new)))
        registry = root / "vigencia.json"
        rejected(lambda: record(registry, new), "Unexpected synthetic revision identity")
        require(not registry.exists(), "Invalid initial revision was materialized")
        old_record = record(registry, old)["vigente"]
        previous = old_record["manifest_sha256"]
        prior = review_current(registry, old, old_book)
        require(prior["estado"] == "COINCIDE" and prior["revision_observada"] == REVISION, "R2 did not reconcile")
        rejected(lambda: record(registry, new, "0" * 64), "register advanced")
        new_record = record(registry, new, previous)["vigente"]
        exact = record(registry, new, previous)
        require(exact["status"] == "verified_identical_revision", "Exact register retry differed")
        rejected(lambda: record(registry, old, new_record["manifest_sha256"]), "Synthetic revision history required")
        rejected(lambda: review_current(registry, old, old_book), "not the designated current revision")
        mismatch = review_current(registry, new, old_book)
        current = review_current(registry, new, new_book)
        history, digest = load(registry)
        require(history == [old_record, new_record] and mismatch["estado"] == "PENDING"
                and current["estado"] == "COINCIDE" and current["registro_sha256"] == digest
                and current["revision_observada"] == THRESHOLD_REVISION
                and all(r["decision"] == "PENDING" for r in (prior, mismatch, current)),
                "Current review or immutable history differs")
    return dict(status="passed", decision="PENDING", revisions=len(history),
                previous_workbook=mismatch["estado"], current_workbook=current["estado"], rejected_probes=4)


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
