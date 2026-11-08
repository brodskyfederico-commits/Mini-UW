"""Reject specific failures in the archived synthetic equity and IRR handoffs."""
from copy import deepcopy
from fractions import Fraction
import json
import sys

from check_annual_return_replay_D24 import verify_irr
from check_integrated_replay_D22 import run as replay_lifecycle
from check_operating_replay_D20 import ROOT, local_file, require
from check_return_replay_D23 import REGISTER, indexed, reconcile_snapshot, totals


def rejected(label, reason, check):
    try:
        check()
    except ValueError as error:
        require(reason in str(error), f"{label} failed for an unexpected reason: {error}")
        return label
    raise ValueError(f"{label} was accepted")


def dated_net(events):
    result = {}
    for date in {event["date"] for event in events}:
        contributed, received = totals([event for event in events if event["date"] == date])
        result[date] = received - contributed
    return result


def run(root=ROOT):
    replay = replay_lifecycle(root, include_return_cash=True)
    first, second = (case["return_cash"] for case in replay["snapshots"])
    register = json.loads(local_file(root, REGISTER).read_bytes())
    snapshot = indexed(register["snapshots"], "snapshot_id")["L01"]
    equity, sources = reconcile_snapshot(root, snapshot, first)
    verify_irr(equity, *sources)

    moved = deepcopy(first)
    next(event for event in moved["events"] if event["kind"] == "distribution")["date"] = "2027-04-01"

    shifted = deepcopy(first)
    for event in shifted["events"]:
        if event["date"] == "2027-03-01":
            event["amount"] = str(Fraction(event["amount"]) + 10)

    duplicate = deepcopy(first)
    zero = next(event for event in duplicate["events"] if event["amount"] == "0")
    duplicate["events"].append(dict(zero))

    missing = deepcopy(first)
    missing["events"] = [event for event in missing["events"] if event["source_event_id"] != zero["source_event_id"]]

    relabeled = deepcopy(first)
    next(event for event in relabeled["events"] if event["category"] == "net_sale_distribution")[
        "category"] = "operating_distribution"

    scaled = deepcopy(equity)
    sale = scaled["calendar"][-1]
    sale["normalized_net"] = str(Fraction(sale["normalized_net"]) + 1)

    require(totals(moved["events"]) == totals(first["events"]), "Timing control changed gross totals")
    baseline = dated_net(first["events"])
    for case in (shifted, duplicate, missing, relabeled):
        require(dated_net(case["events"]) == baseline, "Detail control changed dated net cash")

    cases = [
        ("mixed_version_result", "Return source or result differs", first | {"result_ref": second["result_ref"]}),
        ("moved_operating_payment", "Equity event differs", moved),
        ("offsetting_gross_movements", "Equity event differs", shifted),
        ("duplicated_explicit_zero", "Duplicate source_event_id", duplicate),
        ("omitted_explicit_zero", "Equity event inventory differs", missing),
        ("sale_reclassified_as_operating", "Equity event differs", relabeled),
    ]
    failures = []
    for label, reason, case in cases:
        failures.append(rejected(label, reason, lambda: reconcile_snapshot(root, snapshot, case)))
    failures.append(rejected("changed_normalized_irr_cash", "Normalizing equity changed",
                             lambda: verify_irr(scaled, *sources)))
    return dict(status="passed", scope="archived_synthetic", decision="PENDING",
                rejected_cases=failures, rejected_count=len(failures))


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
