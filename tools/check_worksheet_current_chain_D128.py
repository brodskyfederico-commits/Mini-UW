"""Reinstate missing synthetic inputs and reject complete but obsolete revisions."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from check_unified_worksheet_D48 import call
from check_worksheet_screening_pilot_D120 import BOOKS, check_cash_and_metrics, condition
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, encoded
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-current-chain-D128.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D128.json"
PRIOR = ROOT / "templates/synthetic-workbook-local-chain-D127.json"


def run_case(case_path, output, reference):
    revision_arg = [] if reference is None else ["--current-revision", reference]
    created = call("run", case_path, "--workbook", BOOKS["Base"], "--downside-workbook", BOOKS["Downside"],
                   "--output", output, *revision_arg)
    result = json.loads((output / "results.json").read_bytes())
    pdf = output / "MiniUW_Resumen.pdf"
    page, = PdfReader(pdf).pages
    require(created["simulation_result"] == result["simulation_result"]
            and created["pdf_sha256"] == result["pdf_sha256"] == sha(pdf.read_bytes())
            and f"Simulación PASS/FAIL  |  {result['simulation_result']}" in page.extract_text()
            and result["decision"] == "PENDING" and result["real_decisions_enabled"] is False
            and result["deployment_enabled"] is False and result["personal_investor_return"] is None
            and (output / "case.json").read_bytes() == case_path.read_bytes()
            and (reference is None or (output / CURRENT_REVISION_FILE).read_bytes() == reference.read_bytes()),
            "The restored chain lost its source, PDF or synthetic guard")
    return result


def verify(temp, saved_output):
    case = json.loads(CASE.read_bytes())
    prior_sources = json.loads(PRIOR.read_bytes())["local_sources"]
    directory = saved_output or temp / "restored"
    restored = run_case(CASE, directory, CURRENT)
    scenarios = restored["scenarios"]
    check_cash_and_metrics(restored)
    result = call("audit", directory, "--current-revision", CURRENT)
    require(result["vigencia"] == "VIGENTE" and result["simulation_result"] == "PASS" and result["audit_bot"] == "B16"
            and restored["revision_review"]["state"] == "matched_synthetic_revision"
            and not restored["local_review"]["blockers"],
            "The complete restored case did not pass against the designated snapshot")

    def run_variant(name, spec, reference=CURRENT):
        path = temp / f"{name}.json"
        path.write_bytes(encoded(spec))
        output = temp / name
        variant = run_case(path, output, reference)
        require(variant["scenarios"] == scenarios, "A revision check changed the verified cash")
        return variant, output

    equity_index, = (index for index, row in enumerate(case["rules"])
                     if (row["metric_id"], row["scenario_id"]) == ("equity_TDC", "Downside"))
    candidate = deepcopy(case)
    official = candidate["local_sources"]["documents"].pop("official_snapshot")
    gc_rule = candidate["local_sources"].pop("gc_criterion")
    investment_rule = candidate["rules"].pop(equity_index)
    incomplete, _ = run_variant("missing-three", candidate)
    require(incomplete["simulation_result"] == "PENDING" and incomplete["local_review"]["bots"]["B11"]["state"] == "PENDING"
            and "equity_TDC:Downside:criterion_record_missing" in incomplete["screening"]["simulation_blockers"],
            "An incomplete expediente advanced")
    candidate["local_sources"]["documents"]["official_snapshot"] = official
    first, _ = run_variant("restored-official", candidate)
    require(first["simulation_result"] == "PENDING" and first["local_review"]["bots"]["B11"]["state"] == "checked_synthetic"
            and "gc_criterion_fingerprint_mismatch" in first["revision_review"]["blockers"],
            "Restoring the official copy bypassed the missing criteria")
    candidate["local_sources"]["gc_criterion"] = gc_rule
    second, _ = run_variant("restored-official-and-gc", candidate)
    require(second["simulation_result"] == "PENDING" and not second["local_review"]["blockers"]
            and second["revision_review"]["blockers"] == ["investment_rules_fingerprint_mismatch"],
            "Restoring the GC criterion bypassed the missing investment rule")
    candidate["rules"].insert(equity_index, investment_rule)
    require(candidate == case, "The third restoration changed unrelated sources or rules")

    historical = deepcopy(case)
    historical["criteria_revision"] = "SYNTHETIC-D128-investment-r1"
    local = historical["local_sources"]
    local["revision"] = "SYNTHETIC-D128-local-evidence-r1"
    local["gc_criterion"] = prior_sources["gc_criterion"]
    local["documents"]["official_snapshot"] = deepcopy(prior_sources["documents"]["official_snapshot"])
    for row in local["documents"].values():
        row["document"]["revision"] = local["revision"]
        row["sha256"] = sha(encoded(row["document"]))
    old_rule = historical["rules"][equity_index]
    old_rule.update(pass_condition=condition("<=", Fraction(49, 100)), fail_condition=condition(">", Fraction(49, 100)))
    old_reference = temp / "prior-revision.json"
    old_reference.write_bytes(encoded(snapshot_for_case(historical, "SYNTHETIC-D128-current-r1")))
    old, archived = run_variant("historical", historical, old_reference)
    prior_audit = call("audit", archived, "--current-revision", CURRENT)
    require(old["simulation_result"] == "PASS" and prior_audit["status"] == "verified_source_first"
            and prior_audit["vigencia"] == "HISTORICO" and prior_audit["simulation_result"] == "PENDING"
            and prior_audit["archived_simulation_result"] == "PASS",
            "A formerly complete case kept its old PASS after the current revision advanced")
    require(call("audit", directory)["simulation_result"] == "PENDING",
            "Historical replay assumed current designation without a supplied revision")
    require("outside the audited package" in call("audit", directory, "--current-revision",
            directory / CURRENT_REVISION_FILE, blocked=True)["reason"],
            "The saved snapshot was accepted as its own current designation")

    stale_official, stale_gc, stale_rule = (deepcopy(case) for _ in range(3))
    row = deepcopy(local["documents"]["official_snapshot"])
    row["document"]["revision"] = case["local_sources"]["revision"]
    row["sha256"] = sha(encoded(row["document"]))
    stale_official["local_sources"]["documents"]["official_snapshot"] = row
    stale_gc["local_sources"]["gc_criterion"] = local["gc_criterion"]
    stale_rule["rules"][equity_index] = old_rule
    for role, spec in (("official_source", stale_official), ("gc_criterion", stale_gc), ("investment_rules", stale_rule)):
        stale, _ = run_variant(f"stale-{role}", spec)
        require(stale["simulation_result"] == "PENDING" and not stale["local_review"]["blockers"]
                and stale["screening"]["worksheet_simulation_result"] == "PASS"
                and stale["revision_review"]["blockers"] == [f"{role}_fingerprint_mismatch"],
                f"An obsolete {role} reached PASS after being copied into the new case")

    unbound, _ = run_variant("no-current-snapshot", case, None)
    require(unbound["simulation_result"] == "PENDING"
            and unbound["revision_review"]["blockers"] == ["current_revision_snapshot_missing"],
            "A case supplied its own current revision")
    expired = deepcopy(case)
    expired["local_sources"]["official_request"]["as_of"] = "2027-03-01"
    expired_reference = temp / "expired-revision.json"
    expired_reference.write_bytes(encoded(snapshot_for_case(expired, "SYNTHETIC-D128-expired-probe")))
    blocked, _ = run_variant("expired", expired, expired_reference)
    require(blocked["simulation_result"] == "PENDING" and not blocked["revision_review"]["blockers"]
            and blocked["local_review"]["bots"]["B10"]["blockers"] == ["official_snapshot_date_missing_or_outside_validity"],
            "Matching the reference bypassed the snapshot date check")

    tampered = temp / "tampered"
    copytree(directory, tampered)
    previous = old_reference.read_bytes()
    (tampered / CURRENT_REVISION_FILE).write_bytes(previous)
    manifest_path = tampered / "package.json"
    manifest = json.loads(manifest_path.read_bytes())
    entry, = (row for row in manifest["files"] if row["path"] == CURRENT_REVISION_FILE)
    entry.update(bytes=len(previous), sha256=sha(previous))
    manifest_path.write_bytes(encoded(manifest))
    call("audit", tampered, "--current-revision", CURRENT, blocked=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=10, pending_incomplete=3, pending_stale=3,
                pending_expired=True, pending_unbound=True, historically_verified_but_current_pending=True,
                rehashed_revision_tamper_rejected=True, pdf_sha256=restored["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited restored case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d128-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
