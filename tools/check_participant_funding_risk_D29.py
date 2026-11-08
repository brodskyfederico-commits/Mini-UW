"""Link the D28 cash allocation to the existing T105 dated funding and sale-risk arithmetic."""
from argparse import ArgumentParser
from copy import deepcopy
import json
import sys

from check_integrated_participation_D28 import CASH_FIELDS, IDENTITY_FIELDS, allocate, replay_with_ledgers
from check_operating_replay_D20 import amount, require
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.participant_cash_risk import ADDITIVE, DATED, _cash_observations


def verify_scaled(values, project, keys, share, label):
    for key in keys:
        require(amount(values[key]) == amount(project[key]) * share, f"{label}: {key} differs")


def observe_participant(part, story, project_metrics, project_dates):
    require(part["currency"] == story["currency"] and part["cash_horizon"] == story["cash_horizon"],
            "Participant currency or cash horizon differs")
    identity = part["participant_id"]
    share = amount(part["share_fraction"])
    for actual, project in zip(part["dated_events"], story["dated_events"], strict=True):
        require(actual["event_id"] == project["event_id"]
                and all(actual[key] == project[key] for key in IDENTITY_FIELDS)
                and amount(actual["amount"]) == amount(project["amount"]) * share,
                f"Participant gross event differs: {identity} {project['event_id']}")
    metrics, dates = _cash_observations(part["dated_events"], part["dated_net_flows"])
    verify_scaled(metrics, part, CASH_FIELDS, 1, identity)
    verify_scaled(metrics, project_metrics, ADDITIVE, share, identity)
    for actual, project in zip(dates, project_dates, strict=True):
        require(actual["date"] == project["date"] and actual["event_ids"] == project["event_ids"],
                f"Participant calendar differs: {identity}")
        verify_scaled(actual, project, DATED, share, f"{identity} {actual['date']}")
    ratio = project_metrics["sale_share_of_distributions"] if amount(metrics["gross_distributions"]) > 0 else None
    require(metrics["sale_share_of_distributions"] == ratio, f"Participant sale dependence differs: {identity}")
    return dict(participant_id=identity, share_fraction=part["share_fraction"], metrics=metrics,
                dated_observations=dates, actual_funding_available=None, capital_still_invested=None,
                final_economic_capital_loss=None, verified_personal_investor_return=None)


def observe_allocation(scenario, parent):
    if scenario["state"] == "PENDING":
        require(scenario["participants"] is scenario["reconciliation"] is None,
                "Pending allocation supplied participant cash")
        return dict(state="PENDING", blockers=scenario["blockers"], project=None, participants=None)
    require(parent is not None and scenario["state"] == "computed_synthetic_cash_allocation"
            and scenario["participants"] and not scenario["blockers"], "Expected reconciled allocation")
    story = parent["story"]
    project_metrics, project_dates = _cash_observations(story["dated_events"], parent["evidence"]["dated_net_flows"])
    verify_scaled(project_metrics, story, CASH_FIELDS, 1, "Project")
    parts = [observe_participant(part, story, project_metrics, project_dates) for part in scenario["participants"]]
    require(sum(amount(part["share_fraction"]) for part in parts) == 1, "Participation does not cover the project")
    for key in ADDITIVE:
        require(sum(amount(part["metrics"][key]) for part in parts) == amount(project_metrics[key]),
                f"Participant amounts do not reconcile: {key}")
    for index, project in enumerate(project_dates):
        for key in DATED:
            require(sum(amount(part["dated_observations"][index][key]) for part in parts) == amount(project[key]),
                    f"Participant date totals differ: {project['date']} {key}")
    return dict(state="computed_synthetic_cash_risk_observations", blockers=[],
                currency=story["currency"], cash_horizon=story["cash_horizon"],
                project=dict(metrics=project_metrics, dated_observations=project_dates), participants=parts)


def verify_controls(terms, parent, binding):
    zero_terms = deepcopy(terms)
    zero_terms["participants"][0]["share_fraction"] = {"numerator": "0", "denominator": "1"}
    zero_terms["participants"][1]["share_fraction"] = {"numerator": "1", "denominator": "1"}
    zero = observe_allocation(allocate(zero_terms, parent, binding), parent)["participants"][0]["metrics"]
    require(all(amount(zero[key]) == 0 for key in ADDITIVE)
            and zero["sale_share_of_distributions"] is None
            and zero["sale_share_state"] == "undefined_zero_distributions", "Zero share has defined sale dependence")
    missing_terms = deepcopy(terms)
    missing_terms["participants"][0]["share_fraction"] = None
    pending = observe_allocation(allocate(missing_terms, parent, binding), parent)
    require(pending["state"] == "PENDING" and pending["participants"] is None, "Missing share produced risk")
    return dict(zero_share_has_undefined_sale_dependence=True, missing_share_has_pending_risk=True)


def run():
    allocation, ledgers, terms = replay_with_ledgers()
    require(allocation["decision"] == "PENDING" and allocation["personal_investor_return"] is None,
            "Unexpected decision or personal return")
    scenarios = {key: observe_allocation(row, ledgers.get(key)) for key, row in allocation["scenarios"].items()}
    binding = allocation["project_ledgers"]["L01"]
    controls = verify_controls(terms, ledgers["L01"], binding)
    return dict(status="passed", scope="archived_synthetic", decision="PENDING",
                allocation_report_sha256=digest(canonical(allocation)), terms_sha256=allocation["terms_sha256"],
                scenarios=scenarios, controls=controls, intraday_order_verified=False,
                verified_personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False)


def summary(result):
    return dict(status=result["status"], decision=result["decision"], risk_report_sha256=digest(canonical(result)),
                allocation_report_sha256=result["allocation_report_sha256"],
                scenario_states={key: row["state"] for key, row in result["scenarios"].items()},
                controls=result["controls"])


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print states and the full risk report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
