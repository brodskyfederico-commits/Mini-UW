"""Replay archived sale revisions through the constant-share cash and risk checks."""
from argparse import ArgumentParser
import json
import sys

from check_integrated_participation_D28 import allocate, ledger, replay_with_ledgers
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_refinance_return_replay_D26 import ARCHIVE
from check_return_replay_D23 import indexed
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.project_sale_revision import evidence_fingerprint, recover_sale_revision, revise_project_sale


BINDINGS = "templates/synthetic-participant-sale-revisions-D30.json"
SALE_CATEGORIES = {"net_sale_distribution", "additional_capital"}
RISK_FIELDS = (
    "gross_contributions", "gross_distributions", "net_cash_profit", "additional_capital_contributions",
    "peak_cumulative_net_equity_funding_at_date_close", "possible_intraday_peak_upper_bound",
    "cash_shortfall_at_horizon", "net_sale_distribution", "sale_share_of_distributions",
)


def recover_revision(evidence, detail, row):
    raw = detail["spec_json"]
    spec = json.loads(raw)
    run = revise_project_sale(evidence, raw.encode("utf-8"))
    require(run.sha256 == detail["revision_run_sha256"] == row["revision_run_sha256"]
            and digest(raw) == row["spec_sha256"] and row["revision_id"] == spec["revision_id"]
            and run.payload["decision"] == row["decision"] == "PENDING"
            and run.payload["state"] == detail["state"] == row["state"], "Archived sale revision differs")
    recovered = recover_sale_revision(evidence, raw.encode("utf-8"), run)
    require(recovered is not None and evidence_fingerprint(recovered) == detail["revised_evidence_sha256"],
            "Sale revision recovery differs")
    guarded = recovered.guarded_run
    require(guarded.payload["production_authorized"] is False and guarded.payload["decision"] == "PENDING",
            "Unexpected authorization in revised cash")
    return spec, guarded


def replay_revisions():
    archive = json.loads(local_file(ROOT, ARCHIVE).read_bytes())
    cases = {}
    for key, independent in (("original_project_branch", False), ("independent_software_fixture_branch", True)):
        evidence = load_evidence(independent_test_fixture=independent)
        branch = archive[key]
        comparison = json.loads(branch["comparison"]["payload_json"])
        require(comparison["decision"] == "PENDING" and comparison["base_evidence_sha256"] == evidence_fingerprint(evidence)
                and comparison["real_decisions_enabled"] is False, "Archived comparison context differs")
        by_id = indexed(comparison["revisions"], "revision_id")
        require(len(by_id) == (4 if independent else 3), "Unexpected sale revision inventory")
        for detail in branch["revision_details"]:
            identity = json.loads(detail["spec_json"])["revision_id"]
            row = by_id.pop(identity)
            spec, guarded = recover_revision(evidence, detail, row)
            parent = None
            if independent:
                require(guarded.compiled_raw is not None and row["cash_metrics"] is not None,
                        "Independent revised cash is unavailable")
                parent = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
                parent["guarded_run_sha256"] = guarded.sha256
                parent["sale_revision_sha256"] = row["revision_run_sha256"]
            else:
                require(guarded.compiled_raw is guarded.investor_run is row["cash_metrics"] is None
                        and "refinance_capacity_or_selection_blocked" in guarded.payload["blockers"],
                        "Original capacity failure leaked revised cash")
            cases[f"{key}/{identity}"] = (spec, row, parent)
        require(not by_id, "Unmatched archived sale revision")
    return cases


def check_non_sale_cash(parent, baseline, cut):
    def before_sale(ledger_data):
        return [event for event in ledger_data["story"]["dated_events"]
                if event["date"] != cut or event["category"] not in SALE_CATEGORIES]
    require(parent["evidence"]["grid"] == baseline["evidence"]["grid"]
            and parent["evidence"]["parameters"] == baseline["evidence"]["parameters"]
            and before_sale(parent) == before_sale(baseline), "Sale revision changed non-sale cash or calendar")


def run():
    base, baseline_ledgers, terms = replay_with_ledgers()
    bindings = json.loads(local_file(ROOT, BINDINGS).read_bytes())
    require(bindings["schema"] == "miniuw.synthetic-participant-sale-revision-bindings.v1"
            and bindings["allocation_terms_sha256"] == base["terms_sha256"], "Sale revision terms differ")
    cases = replay_revisions()
    hashes = bindings["project_ledgers"]
    require(hashes.keys() == {key for key, (_, _, parent) in cases.items() if parent is not None},
            "Expected exact terms bindings for four computable revisions")
    baseline = baseline_ledgers["refinance_independent_fixture"]
    cut = baseline["story"]["cash_horizon"]["end"]
    results = {}
    for key, (spec, archived, parent) in cases.items():
        allocation = allocate(terms, parent, hashes.get(key), require_unique_irr=False)
        risk = observe_allocation(allocation, parent)
        claims = spec["replacement_claims"]
        result = dict(state=risk["state"], blockers=risk["blockers"],
                      revision_sha256=archived["revision_run_sha256"],
                      gross_sale_proceeds=str(amount(claims["gross_proceeds"])),
                      closing_costs=str(amount(claims["closing_costs_paid"])),
                      participants=None, project=None)
        if parent is not None:
            require(risk["project"] is not None, f"Archived revised cash did not allocate: {key}")
            check_non_sale_cash(parent, baseline, cut)
            project = risk["project"]["metrics"]
            require(all(project[field] == archived["cash_metrics"][field] for field in RISK_FIELDS),
                    "Project sale risk differs from archived revision")
            result["project"] = {field: project[field] for field in RISK_FIELDS}
            result["participants"] = []
            for part, cash in zip(risk["participants"], allocation["participants"], strict=True):
                require(part["participant_id"] == cash["participant_id"], "Revision participant identity differs")
                result["participants"].append(dict(
                    participant_id=part["participant_id"], share_fraction=part["share_fraction"],
                    metrics={field: part["metrics"][field] for field in RISK_FIELDS},
                    annual_irr_roots=cash["annual_IRR_roots"],
                    irr_root_classification=cash["periodic_IRR"]["root_classification"]))
        results[key] = result
    return dict(status="passed", scope="archived_synthetic_sale_revisions", currency="USD", decision="PENDING",
                allocation_terms_sha256=base["terms_sha256"], sale_cut_date=cut, revisions=results,
                verified_personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    return dict(status=report["status"], decision=report["decision"], revision_report_sha256=digest(canonical(report)),
                revision_states={key: row["state"] for key, row in report["revisions"].items()})


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print revision states and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
