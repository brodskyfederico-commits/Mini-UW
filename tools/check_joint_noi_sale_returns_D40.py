"""Cross the D39 capacity and participant cash with the four archived sale revisions."""
from argparse import ArgumentParser
from fractions import Fraction
import json
import sys

from check_integrated_participation_D28 import TERMS, allocate
from check_joint_noi_capacity_D38 import FIXTURE as MATRIX, replay_with_evidence
from check_joint_noi_investor_returns_D39 import BINDINGS as RETURNS, cases_from_cash
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_participant_joint_exit_D32 import BINDINGS as JOINT_EXIT, load_sources, replay_sale
from check_participant_refinance_variants_D31 import participant_rows
from miniuw_foundation.drafts import canonical, digest


BINDINGS = "templates/synthetic-joint-noi-sale-returns-D40.json"
SCHEMA = "miniuw.synthetic-joint-noi-sale-returns.v1"
FIELDS = ("gross_contributions", "gross_distributions", "net_cash_profit",
          "additional_capital_contributions", "net_sale_distribution", "cash_shortfall_at_horizon",
          "cash_surplus_at_horizon", "peak_cumulative_net_equity_funding_at_date_close", "sale_share_of_distributions")


def sources(bindings):
    require(bindings["schema"] == SCHEMA, "Unexpected NOI sale return profile")
    values = {}
    for key, path in (("returns", RETURNS), ("joint_exit", JOINT_EXIT), ("terms", TERMS)):
        raw = local_file(ROOT, path).read_text(encoding="utf-8")
        require(digest(raw) == bindings[f"{key}_sha256"], f"NOI sale return source differs: {path}")
        values[key] = json.loads(raw)
    matrix_raw = local_file(ROOT, MATRIX).read_text(encoding="utf-8")
    _, sales, refinance_hash, sales_hash = load_sources()
    require(values["returns"]["matrix_fixture_sha256"] == digest(matrix_raw)
            and values["joint_exit"]["sale_inventory_sha256"] == sales_hash
            and values["joint_exit"]["refinance_fixture_sha256"] == refinance_hash
            and values["returns"]["allocation_terms_sha256"] == values["joint_exit"]["allocation_terms_sha256"]
            == bindings["terms_sha256"], "D39 and sale revisions bind different evidence")
    return values["terms"], values["returns"], sales


def replay_cases(returns, sales):
    matrix, evidence_by_case = replay_with_evidence()
    pending_bindings = dict(returns["project_ledgers"])
    guarded = {key: evidence.guarded_run for key, evidence in evidence_by_case.items()}
    for case, origin, parent in cases_from_cash(matrix, guarded):
        evidence = evidence_by_case[case]
        if parent is not None:
            require(digest(canonical(parent)) == pending_bindings.pop(case), "D39 loan cash differs")
        for sale in sales:
            claims = sale["replacement_claims"]
            key = f"{case}/{sale['revision_id']}"
            row = dict(bank_noi=origin["bank_noi"], valuation_noi=origin["valuation_noi"],
                       principal=origin["principal"], capacity=origin["capacity"],
                       exceeded_limits=origin["exceeded_limits"], blockers=origin["blockers"],
                       sale_revision=sale["revision_id"], gross_sale_proceeds=str(amount(claims["gross_proceeds"])),
                       sale_closing_costs=str(amount(claims["closing_costs_paid"])),
                       return_state="PENDING", decision="PENDING", project=None, participants=None)
            if parent is None:
                # The sale scenarios hold all capacity inputs fixed. D39 has already withheld this ledger.
                yield key, row, None, None
                continue
            revision, revised = replay_sale(evidence, sale, parent, False)
            metrics = json.loads(revision["risk_run"]["payload_json"])["metrics"]
            yield key, row, revised, metrics
    require(not pending_bindings, "Unexpected D39 loan cash inventory")


def recovery_fields(metrics):
    contributed = amount(metrics["gross_contributions"])
    received = amount(metrics["gross_distributions"])
    shortfall = amount(metrics["cash_shortfall_at_horizon"])
    surplus = amount(metrics["cash_surplus_at_horizon"])
    recovered = min(contributed, received)
    require(contributed > 0 and recovered + shortfall == contributed and recovered + surplus == received,
            "Nominal cash recovery does not reconcile")
    return dict(cash_recovered=str(recovered), recovery_fraction=str(recovered / contributed))


def replay_with_allocations():
    """Return the nominal report and its verified dated cash sources."""
    bindings = json.loads(local_file(ROOT, BINDINGS).read_bytes())
    terms, returns, sales = sources(bindings)
    hashes = dict(bindings["project_ledgers"])
    results = {}
    dated_cash = {}
    for key, row, parent, revised_project in replay_cases(returns, sales):
        if parent is not None:
            allocation = allocate(terms, parent, hashes.pop(key), require_unique_irr=False)
            risk = observe_allocation(allocation, parent)
            require(risk["project"] is not None, "Revised sale cash failed to allocate")
            project = {field: risk["project"]["metrics"][field] for field in FIELDS}
            require(all(project[field] == revised_project[field] for field in FIELDS),
                    "Revised project cash risk differs")
            participants = participant_rows(risk, allocation, FIELDS)
            for participant in participants:
                participant.update(recovery_fields(participant["metrics"]))
            recovery = recovery_fields(project)
            require(sum(Fraction(part["cash_recovered"]) for part in participants)
                    == Fraction(recovery["cash_recovered"]), "Participant recovery does not sum to project")
            row.update(return_state="computed_synthetic_cash_allocation",
                       project=project | recovery, participants=participants)
            dated_cash[key] = (parent, allocation["participants"])
        results[key] = row
    require(not hashes and len(results) == 96, "Unexpected joint NOI and sale inventory")
    report = dict(status="passed", scope="synthetic_joint_noi_sale_and_nominal_cash_recovery", currency="USD",
                  decision="PENDING", scenarios=results, verified_personal_investor_return=None,
                  deployment_enabled=False, real_decisions_enabled=False)
    return report, dated_cash


def run():
    report, _ = replay_with_allocations()
    return report


def summary(report):
    states = [row["return_state"] for row in report["scenarios"].values()]
    return dict(status=report["status"], decision=report["decision"], joint_noi_sale_sha256=digest(canonical(report)),
                computed=states.count("computed_synthetic_cash_allocation"), pending=states.count("PENDING"))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print verification counts and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
