"""Replay all local Dot/bot stages with complete and incomplete synthetic sources."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_screening_pilot_D120 import BOOKS, audit, check_cash_and_metrics, condition, replace_rule
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.v1_contracts import load_contracts
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import review_local_sources


CASE = ROOT / "templates/synthetic-workbook-local-chain-D127.json"


def audit_variant(case, temp, name):
    path = temp / f"{name}.json"
    path.write_bytes(encoded(case))
    return audit(path, BOOKS["Base"], BOOKS["Downside"], temp / name)


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    output = saved_output or temp / "complete"
    primary, page = audit(CASE, BOOKS["Base"], BOOKS["Downside"], output)
    check_cash_and_metrics(primary)
    contract, contract_hash = load_contracts()
    stages = primary["pipeline"]["stages"]
    local = primary["local_review"]
    bots = local["bots"]
    require([(row["dot"], row["bots"]) for row in stages]
            == [(row["dot_id"], row["bot_ids"]) for row in contract["dots"]]
            and local["contract_sha256"] == contract_hash and not local["blockers"]
            and all(row["state"] == "checked_synthetic" for row in bots.values())
            and primary["simulation_result"] == "PASS" and "Simulación PASS/FAIL  |  PASS" in page,
            "The complete synthetic case did not exercise the declared stages or pass")
    require(bots["B05"]["source_sha256"] != bots["B06"]["source_sha256"]
            and amount(bots["B07"]["value"]) == 1000 and amount(bots["B09"]["difference"]) == 0
            and amount(bots["B08"]["budget"]["value"]) == 450
            and bots["B10"]["access"] == "local_snapshot" and bots["B11"]["value"] == 4
            and bots["B11"]["source_sha256"] == bots["B10"]["sha256"],
            "Readings, GC control or archived data lost their evidence")

    no_snapshot = deepcopy(case)
    no_snapshot["local_sources"]["documents"].pop("official_snapshot")
    missing_data, page = audit_variant(no_snapshot, temp, "missing-snapshot")
    require(missing_data["simulation_result"] == "PENDING" and "Simulación PASS/FAIL  |  PENDING" in page
            and missing_data["screening"]["worksheet_simulation_result"] == "PASS"
            and missing_data["scenarios"] == primary["scenarios"]
            and missing_data["local_review"]["bots"]["B11"]["state"] == "PENDING",
            "Missing official evidence failed to stop the simulation or discarded unrelated cash")

    no_gc_rule = deepcopy(case)
    no_gc_rule["local_sources"].pop("gc_criterion")
    missing_gc, _ = audit_variant(no_gc_rule, temp, "missing-gc-criterion")
    require(missing_gc["simulation_result"] == "PENDING" and missing_gc["scenarios"] == primary["scenarios"]
            and missing_gc["screening"]["worksheet_simulation_result"] == "PASS"
            and missing_gc["local_review"]["bots"]["B09"]["blockers"] == ["explicit_GC_area_criterion_required"],
            "A missing GC criterion was silently filled")

    no_financial_rule = replace_rule(case, "equity_TDC", "Downside", fail_condition=None)
    missing_rule, _ = audit_variant(no_financial_rule, temp, "missing-investment-rule")
    require(missing_rule["simulation_result"] == "PENDING" and missing_rule["scenarios"] == primary["scenarios"]
            and missing_rule["local_review"]["state"] == "checked_synthetic"
            and "equity_TDC:Downside:fail_condition_rule_missing_or_unsupported" in missing_rule["screening"]["simulation_blockers"],
            "Passing the source checks supplied a missing investment rule")

    ceiling = Fraction(45, 100)
    strict = replace_rule(case, "equity_TDC", "Downside", pass_condition=condition("<=", ceiling),
                          fail_condition=condition(">", ceiling)) | {"criteria_revision": "SYNTHETIC-D127-strict-r2"}
    failed, _ = audit_variant(strict, temp, "fail")
    require(failed["simulation_result"] == "FAIL" and failed["scenarios"] == primary["scenarios"]
            and failed["local_review"]["state"] == "checked_synthetic",
            "A complete case with an explicitly failing criterion did not report FAIL")

    section = case["local_sources"]
    hashes = case["workbook_sha256"]
    conflicting = deepcopy(section)
    row = conflicting["documents"]["plan_b"]
    row["document"]["area"]["value"] = rational(Fraction(1001))
    row["sha256"] = sha(encoded(row["document"]))
    conflict = review_local_sources(conflicting, hashes)
    require(conflict["bots"]["B07"]["blockers"] == ["plan_readings_conflict"]
            and conflict["bots"]["B09"]["state"] == "PENDING", "A discrepancy overwrote a plan observation")
    expired = deepcopy(section)
    expired["official_request"]["as_of"] = "2027-02-01"
    require(review_local_sources(expired, hashes)["bots"]["B10"]["blockers"]
            == ["official_snapshot_date_missing_or_outside_validity"], "An expired snapshot was accepted")
    unknown = deepcopy(section)
    unknown["documents"]["plan_a"]["document"]["schema"] = "ambiguous"
    row = unknown["documents"]["plan_a"]
    row["sha256"] = sha(encoded(row["document"]))
    require(review_local_sources(unknown, hashes)["bots"]["B03"]["documents"]["plan_a"]["blockers"]
            == ["document_type_ambiguous_or_incompatible"], "An ambiguous document was classified")

    altered = temp / "altered"
    copytree(output, altered)
    primary["local_review"]["bots"]["B11"]["value"] = 5
    rewritten = encoded(primary)
    (altered / "results.json").write_bytes(rewritten)
    manifest_path = altered / "package.json"
    manifest = json.loads(manifest_path.read_bytes())
    entry, = (row for row in manifest["files"] if row["path"] == "results.json")
    entry.update(bytes=len(rewritten), sha256=sha(rewritten))
    manifest_path.write_bytes(encoded(manifest))
    call("audit", altered, blocked=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=5, dots=7, bot_contracts=17,
                simulated=dict(PASS=1, FAIL=1, PENDING=3), page_count=1, pdf_sha256=primary["pdf_sha256"],
                rehashed_local_result_tamper_rejected=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited complete case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d127-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
