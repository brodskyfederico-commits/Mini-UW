"""Apply explicit synthetic cash shares to the integrated sale and refinance ledgers."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require, resolve
from check_refinance_return_replay_D26 import run as replay_cash
from check_return_replay_D23 import REGISTER, indexed
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.cash_participation import ASSUMPTIONS, PROFILE, _allocate
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.operating_noi import ArithmeticBudgetError


TERMS = "templates/synthetic-integrated-cash-participation-D28.json"
SCHEMA = "miniuw.synthetic-integrated-cash-participation.v1"
CASH_FIELDS = ("gross_contributions", "gross_distributions", "net_cash_profit")
IDENTITY_FIELDS = ("date", "kind", "category", "currency")


def ledger(story, compiled):
    require(story["equity_level"] == compiled["equity_level"] == "aggregate_project_equity"
            and story["context"] == compiled["context"] and story["currency"] == compiled["currency"] == "USD"
            and story["events"] == compiled["events"] and story["decision"] == "PENDING",
            "Unexpected project ledger for synthetic participation")
    view = {key: story[key] for key in (*CASH_FIELDS, "currency", "cash_horizon", "cash_by_category",
                                        "annual_cash_receipts")}
    view["dated_events"] = story["events"]
    evidence = dict(grid=compiled["grid"], parameters=compiled["irr_parameters"],
                    dated_net_flows=story["dated_net_flows"])
    return dict(story=view, evidence=evidence, context=story["context"], source_sha256=story["source_sha256"])


def replay_ledgers():
    cash = replay_cash()
    register = json.loads(local_file(ROOT, REGISTER).read_bytes())
    archived = indexed(register["snapshots"], "snapshot_id")
    ledgers = {}
    for case in cash["sale_only"]:
        equity = case["project_equity"]
        name = equity["snapshot"]
        snapshot = archived.pop(name)
        saved = resolve(ROOT, snapshot["result_ref"])
        story = saved["current_project_return_story"]
        compiled = json.loads(saved["current_compiled_investor_json"])
        replayed = indexed(equity["events"], "event_id")
        original = indexed(story["events"], "event_id")
        require(case["input_sha256"] == snapshot["input_ref"]["sha256"] == saved["source_sha256"]
                and replayed.keys() == original.keys() and story["cash_horizon"] == snapshot["cash_horizon"],
                "Return replay does not match archived project ledger")
        for event_id, row in replayed.items():
            event = original[event_id]
            require(all(row[key] == event[key] for key in IDENTITY_FIELDS)
                    and Fraction(row["amount"]) == amount(event["amount"]), f"Replayed cash event differs: {event_id}")
        require([Fraction(row["net"]) for row in equity["calendar"]]
                == [amount(row["net"]) for row in story["dated_net_flows"]], "Replayed calendar net differs")
        ledgers[name] = ledger(story, compiled) | {"input_sha256": case["input_sha256"]}
    require(not archived and cash["refinance_original_blocked"]["project_equity"] is None,
            "Unexpected return case or fallback for blocked refinance")
    fixture = load_evidence(independent_test_fixture=True)
    guarded = fixture.guarded_run
    story = guarded.investor_run.payload
    equity = cash["refinance_independent_fixture"]["project_equity"]
    require(equity["events"] == story["events"] and equity["cash_horizon"] == story["cash_horizon"]
            and all(Fraction(equity[key]) == amount(story[key]) for key in CASH_FIELDS),
            "Refinance replay does not match guarded equity ledger")
    compiled = json.loads(guarded.compiled_raw)
    ledgers["refinance_independent_fixture"] = ledger(story, compiled) | {"guarded_run_sha256": guarded.sha256}
    return ledgers


def prepare_shares(terms):
    participants = terms["participants"]
    require(isinstance(participants, list) and 1 <= len(participants) <= 4, "Expected one to four synthetic participants")
    by_id = indexed(participants, "participant_id")
    shares = []
    blockers = []
    for identity, row in by_id.items():
        require(isinstance(identity, str) and identity.startswith("SYNTHETIC-")
                and set(row) == {"participant_id", "share_fraction", "source_ref"}, "Invalid synthetic participant")
        share = _fraction(row["share_fraction"])
        if share is None:
            blockers.append(f"{identity}:share_missing")
        elif not 0 <= share <= 1:
            blockers.append(f"{identity}:share_outside_zero_one")
        if not isinstance(row["source_ref"], str) or not row["source_ref"].strip():
            blockers.append(f"{identity}:source_ref_missing")
        shares.append(share)
    if None not in shares and sum(shares) != 1:
        blockers.append("supplied_shares_must_sum_exactly_one")
    return shares, blockers


def allocate(terms, parent, binding):
    if parent is None:
        return dict(state="PENDING", blockers=["current_project_cash_unavailable"], participants=None, reconciliation=None)
    shares, blockers = prepare_shares(terms)
    if binding != digest(canonical(parent)):
        blockers.append("exact_project_ledger_hash_mismatch")
    if terms["currency"] != parent["story"]["currency"]:
        blockers.append("currency_mismatch")
    if terms["participant_inventory_complete"] is not True:
        blockers.append("complete_participant_inventory_required")
    if canonical(terms["assumptions"]) != canonical(ASSUMPTIONS):
        blockers.append("missing_or_unsupported_share_assumptions")
    if blockers:
        return dict(state="PENDING", blockers=sorted(blockers), participants=None, reconciliation=None)
    try:
        participants, reconciliation = _allocate(parent["story"], parent["evidence"], terms, shares)
    except ArithmeticBudgetError:
        return dict(state="PENDING", blockers=["cash_allocation_exact_arithmetic_budget_exceeded"],
                    participants=None, reconciliation=None)
    positive_roots = []
    for row, share in zip(participants, shares, strict=True):
        require(all(row[key] is None for key in ("verified_personal_investor_return", "selected_IRR",
                                                 "capital_still_invested", "retained_equity_value", "conditional_CoC")),
                "Synthetic share acquired unsupported investor values")
        for key in CASH_FIELDS:
            require(amount(row[key]) == amount(parent["story"][key]) * share, f"Participant {key} differs")
        if share == 0:
            require(row["equity_multiple"] is None and not row["annual_IRR_roots"]
                    and row["periodic_IRR"]["root_classification"] == "identically_zero_net_polynomial",
                    "Zero participation acquired an implied return")
        else:
            roots = row["periodic_IRR"]
            require(row["positive_scalar_net_flow_identity_verified"] is True
                    and roots["status"] == "complete_synthetic" and roots["distinct_positive_discount_roots"] == 1
                    and row["annual_IRR_roots"], "Synthetic IRR enclosure did not reconcile")
            positive_roots.append((roots["roots"], row["annual_IRR_roots"]))
    require(all(roots == positive_roots[0] for roots in positive_roots),
            "Positive shares produced different IRR enclosures")
    return dict(state="computed_synthetic_cash_allocation", blockers=[], participants=participants,
                reconciliation=reconciliation)


def verify_controls(terms, parent, binding, wrong_binding):
    missing = deepcopy(terms)
    missing["participants"][0]["share_fraction"] = None
    short = deepcopy(terms)
    short["participants"][0]["share_fraction"] = {"numerator": "0", "denominator": "1"}
    zero = deepcopy(short)
    zero["participants"][1]["share_fraction"] = {"numerator": "1", "denominator": "1"}
    controls = {
        "missing_share": (allocate(missing, parent, binding), ":share_missing"),
        "incomplete_sum": (allocate(short, parent, binding), "supplied_shares_must_sum_exactly_one"),
        "other_project_ledger": (allocate(terms, parent, wrong_binding), "exact_project_ledger_hash_mismatch"),
        "blocked_refinance": (allocate(terms, None, None), "current_project_cash_unavailable"),
    }
    for name, (result, reason) in controls.items():
        require(result["state"] == "PENDING" and result["participants"] is result["reconciliation"] is None
                and any(blocker.endswith(reason) for blocker in result["blockers"]), f"Control did not block: {name}")
    result = allocate(zero, parent, binding)
    require(result["state"] == "computed_synthetic_cash_allocation"
            and amount(result["participants"][0]["share_fraction"]) == 0, "Explicit zero share was blocked")
    return dict(pending_controls=list(controls), explicit_zero_preserved=True)


def run():
    parents = replay_ledgers()
    raw = local_file(ROOT, TERMS).read_bytes()
    terms = json.loads(raw)
    require(set(terms) == {"schema", "profile", "terms_id", "revision", "currency", "participant_inventory_complete",
                           "source_ref", "whole_ledger_scope_ref", "assumptions", "project_ledgers", "participants"}
            and terms["schema"] == SCHEMA and terms["profile"] == PROFILE
            and terms["terms_id"] == "SYNTHETIC-integrated-cash-share-D28" and terms["revision"] == 1
            and terms["whole_ledger_scope_ref"] and terms["source_ref"], "Expected explicit synthetic terms")
    bindings = terms["project_ledgers"]
    require(bindings.keys() == parents.keys(), "Participation coverage differs from replayed ledgers")
    scenarios = {}
    for key, parent in parents.items():
        scenarios[key] = allocate(terms, parent, bindings[key])
        require(scenarios[key]["state"] == "computed_synthetic_cash_allocation",
                f"Archived terms did not reconcile: {key}")
    scenarios["refinance_original_blocked"] = allocate(terms, None, None)
    controls = verify_controls(terms, parents["L01"], bindings["L01"], bindings["L02"])
    return dict(status="passed", scope="archived_synthetic", decision="PENDING", currency="USD",
                terms_sha256=digest(raw.decode("utf-8")), project_ledgers=bindings, scenarios=scenarios,
                controls=controls, personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False)


def summary(result):
    return dict(status=result["status"], scope=result["scope"], decision=result["decision"],
                report_sha256=digest(canonical(result)),
                scenario_states={name: row["state"] for name, row in result["scenarios"].items()},
                controls=result["controls"])


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print states and a SHA-256 of the full report.")
    args = parser.parse_args()
    try:
        result = run()
        print(json.dumps(summary(result) if args.summary else result, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
