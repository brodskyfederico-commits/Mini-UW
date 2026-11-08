"""Cross the declared refinance and sale variants and reconcile participant cash risk."""
from argparse import ArgumentParser
import json
import sys

from check_integrated_participation_D28 import allocate, ledger, replay_with_ledgers
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_participant_refinance_variants_D31 import CAPACITY_BLOCKER, FIXTURE, build_variant_evidence, encode, participant_rows
from check_participant_sale_revisions_D30 import RISK_FIELDS, check_non_sale_cash
from check_refinance_return_replay_D26 import ARCHIVE
from check_return_replay_D23 import indexed
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.project_sale_revision import evidence_fingerprint, recover_sale_revision, revise_project_sale


BINDINGS = "templates/synthetic-participant-joint-exit-D32.json"
SCHEMA = "miniuw.synthetic-participant-joint-exit.v1"
FIELDS = (*RISK_FIELDS, "refinance_cash_in_contributions")


def load_sources():
    refinance_raw = local_file(ROOT, FIXTURE).read_text(encoding="utf-8")
    archive = json.loads(local_file(ROOT, ARCHIVE).read_bytes())
    branch = archive["independent_software_fixture_branch"]
    comparison = json.loads(branch["comparison"]["payload_json"])
    archived_specs = indexed(comparison["revisions"], "revision_id")
    sales = []
    for detail in branch["revision_details"]:
        raw = detail["spec_json"]
        spec = json.loads(raw)
        row = archived_specs.pop(spec["revision_id"])
        require(digest(raw) == row["spec_sha256"] and row["revision_run_sha256"] == detail["revision_run_sha256"],
                "Archived sale source differs")
        sales.append(spec)
    require(not archived_specs and len(sales) == 4, "Expected all four archived sale revisions")
    return json.loads(refinance_raw), sales, digest(refinance_raw), digest(canonical(sales))


def replay_sale(evidence, sale_spec, refinance_parent, capacity_blocked):
    raw = encode(sale_spec | {"base_evidence_sha256": evidence_fingerprint(evidence)})
    revision = revise_project_sale(evidence, raw)
    recovered = recover_sale_revision(evidence, raw, revision)
    require(recovered is not None and recovered.capacity_run == evidence.capacity_run
            and recovered.capacity_inputs == evidence.capacity_inputs
            and recovered.periods == evidence.periods and recovered.closings[0] == evidence.closings[0],
            "Sale changed refinance capacity or pre-sale cash sources")
    guarded = recovered.guarded_run
    result = revision.payload
    require(result["decision"] == guarded.payload["decision"] == "PENDING"
            and result["real_decisions_enabled"] is result["production_authorized"] is False,
            "Joint scenario acquired authorization")
    if capacity_blocked:
        require(result["state"] == "blocked" and guarded.compiled_raw is guarded.investor_run is None
                and result["risk_run"] is None and "refinance_capacity_or_selection_blocked" in result["blockers"],
                "Sale revision lifted the refinance capacity gate")
        return result, None

    require(result["state"] == "compiled_synthetic" and guarded.compiled_raw is not None,
            "Joint sale and refinance did not reconcile")
    parent = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
    parent.update(guarded_run_sha256=guarded.sha256, sale_revision_sha256=revision.sha256)
    check_non_sale_cash(parent, refinance_parent, parent["story"]["cash_horizon"]["end"])
    return result, parent


def replay_matrix(refinance, sales):
    base = load_evidence(independent_test_fixture=True)
    require(refinance["base_evidence_sha256"] == evidence_fingerprint(base), "Refinance base evidence differs")
    maximum = amount(base.capacity_run.payload["maximum_principal_capacity"])
    cases = {}
    for key, variant in indexed(refinance["variants"], "variant_id").items():
        evidence = build_variant_evidence(base, variant)
        capacity = evidence.capacity_run.payload
        selected = amount(capacity["selected_principal"])
        blocked = selected > maximum
        require(selected == amount(variant["selected_principal"])
                and amount(capacity["maximum_principal_capacity"]) == maximum
                and capacity["blockers"] == ([CAPACITY_BLOCKER] if blocked else [])
                and capacity["bank_credit_approved"] is capacity["funds_available_verified"] is False,
                "Refinance capacity differs from the declared variant")
        guarded = evidence.guarded_run
        refinance_parent = None
        if blocked:
            require(guarded.compiled_raw is guarded.investor_run is None, "Blocked refinance has investor cash")
        else:
            refinance_parent = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
            refinance_parent["guarded_run_sha256"] = guarded.sha256
            require(digest(canonical(refinance_parent)) == refinance["project_ledgers"][key],
                    "Refinance-only ledger differs from D31")
        for sale_spec in sales:
            revision, parent = replay_sale(evidence, sale_spec, refinance_parent, blocked)
            amounts = sale_spec["replacement_claims"]
            row = dict(refinance_variant=key, sale_revision=sale_spec["revision_id"],
                       selected_principal=str(selected), capacity=str(maximum), capacity_blockers=capacity["blockers"],
                       sale_proceeds=str(amount(amounts["gross_proceeds"])),
                       sale_closing_costs=str(amount(amounts["closing_costs_paid"])),
                       project=None, participants=None)
            archived_metrics = None if blocked else json.loads(revision["risk_run"]["payload_json"])["metrics"]
            cases[f"{key}/{sale_spec['revision_id']}"] = (row, parent, archived_metrics)
    return cases


def run():
    allocation, _, terms = replay_with_ledgers()
    refinance, sales, refinance_hash, sale_hash = load_sources()
    bindings = json.loads(local_file(ROOT, BINDINGS).read_bytes())
    require(bindings["schema"] == SCHEMA and bindings["refinance_fixture_sha256"] == refinance_hash
            and bindings["sale_inventory_sha256"] == sale_hash
            and bindings["allocation_terms_sha256"] == allocation["terms_sha256"],
            "Joint scenario or allocation sources differ")
    cases = replay_matrix(refinance, sales)
    hashes = bindings["project_ledgers"]
    require(hashes.keys() == {key for key, (_, parent, _) in cases.items() if parent is not None},
            "Joint scenario ledger inventory differs")
    results = {}
    for key, (row, parent, project_metrics) in cases.items():
        apportioned = allocate(terms, parent, hashes.get(key), require_unique_irr=False)
        risk = observe_allocation(apportioned, parent)
        row["state"] = risk["state"]
        if parent is not None:
            require(risk["project"] is not None, f"Joint scenario failed to allocate: {key}")
            metrics = risk["project"]["metrics"]
            require(all(metrics[field] == project_metrics[field] for field in FIELDS),
                    "Joint scenario metrics differ from the recomputed project")
            row["project"] = {field: metrics[field] for field in FIELDS}
            row["participants"] = participant_rows(risk, apportioned, FIELDS)
        results[key] = row
    return dict(status="passed", scope="synthetic_joint_refinance_and_sale", currency="USD", decision="PENDING",
                scenarios=results, verified_personal_investor_return=None,
                deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    states = [row["state"] for row in report["scenarios"].values()]
    return dict(status=report["status"], decision=report["decision"], joint_exit_sha256=digest(canonical(report)),
                computed=states.count("computed_synthetic_cash_risk_observations"), pending=states.count("PENDING"))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print scenario counts and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
