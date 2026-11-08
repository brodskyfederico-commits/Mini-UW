"""Replay the archived sale-only and capacity-checked refinance return paths."""
from fractions import Fraction
import json
import sys

from check_annual_return_replay_D24 import run as replay_sale_only
from check_debt_sale_replay_D21 import verify_amounts
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_return_replay_D23 import indexed
from demo_project_sale_revisions import branch, load_evidence


ARCHIVE = "docs/review/synthetic-project-sale-revisions-demo.json"
DEBT_FIELDS = ("principal", "interest", "fees", "other")


def replay_refinance_bridge(evidence):
    refinance, sale = evidence.closings
    closing = refinance.closing_run.payload
    capacity = evidence.capacity_run.payload
    source = json.loads(refinance.closing_raw)
    cash = {field: amount(claim) for field, claim in source["amounts"].items()}
    old_debt = sum(amount(debt[f"{field}_paid"]) for debt in source["old_debts"] for field in DEBT_FIELDS)
    sources = sum(cash[key] for key in ("opening_free_cash", "gross_proceeds", "reserve_release", "other_cash_sources"))
    uses = old_debt + sum(cash[key] for key in ("closing_costs_paid", "new_reserve", "other_cash_uses",
                                                "retained_free_cash"))
    residual = sources - uses
    require(source["kind"] == "refinance" and residual > 0 and amount(closing["total_cash_conservation_residual"]) == 0
            and residual == amount(closing["exportable_equity_distribution"])
            and amount(closing["exportable_equity_contribution"]) == 0, "Refinance gross-to-net cash differs")
    restricted = cash["opening_restricted_cash"] + cash["new_reserve"] - cash["reserve_release"]
    require(restricted == cash["closing_restricted_cash_claim"], "Refinance reserve balance differs")

    new_loan = source["new_loan"]
    sale_loan, = sale.loans
    terms = json.loads(sale_loan.loan_raw)
    require(amount(new_loan["principal_after_closing"]) == amount(capacity["selected_principal"])
            == amount(terms["principal"]) == cash["gross_proceeds"]
            and new_loan["loan_id"] == terms["loan_id"], "Permanent loan differs between refinance and sale")
    project = evidence.project_run.payload
    boundaries = project["cash_boundary_checks"]
    link, = project["refinance_to_sale_loan_links"]
    require(project["declared_cash_window_reconciled"] is True and amount(project["cash_conservation_residual"]) == 0
            and len(boundaries) == 6 and all(row["equal_exact_value"] is True for row in boundaries)
            and link["refinance_node"] == refinance.closing_id and link["new_loan_id"] == new_loan["loan_id"]
            and link["sale_loan_inventory_matches_refinance_origin_principal"] is True,
            "Operating cash or refinance-to-sale loan continuity differs")
    return dict(date=closing["closing_date"], gross_new_loan=str(cash["gross_proceeds"]),
                opening_free_cash=str(cash["opening_free_cash"]), reserve_released=str(cash["reserve_release"]),
                old_debt_paid=str(old_debt), closing_costs=str(cash["closing_costs_paid"]),
                new_reserve=str(cash["new_reserve"]), retained_free_cash=str(cash["retained_free_cash"]),
                projected_equity_distribution=str(residual), retained_restricted_cash=str(restricted),
                cash_boundary_checks=len(boundaries), loan_id=new_loan["loan_id"])


def replay_equity(evidence, bridge):
    guarded = evidence.guarded_run
    project = evidence.project_run.payload
    story = guarded.investor_run.payload
    declared = json.loads(evidence.investor_raw)
    events = indexed(story["events"], "event_id")
    raw = indexed(declared["events"], "event_id")
    require(events.keys() == raw.keys() and story["equity_level"] == "aggregate_project_equity"
            and story["decision"] == "PENDING" and story["production_authorized"] is False
            and story["selected_IRR"] is None, "Unexpected refinance equity result")
    inner = evidence.binding.project_return_binding
    opening_id, = inner.opening_contribution_event_ids
    opening = events.pop(opening_id)
    require(opening == raw[opening_id] and opening["category"] == "initial_capital"
            and opening["kind"] == "contribution", "Declared opening equity differs")
    opening_amount = amount(opening["amount"])
    contributions = opening_amount
    distributions = Fraction()
    moves = indexed(project["exportable_equity_movements"], "node_id")
    slots = indexed([vars(slot) for slot in inner.slots], "node_id")
    require(moves.keys() == slots.keys() and len(moves) == 4, "Expected four equity cash nodes")
    for node, move in moves.items():
        slot = slots[node]
        for kind in ("contribution", "distribution"):
            target = slot[f"{kind}_event_id"]
            value = amount(move[kind])
            if target is None:
                require(value == 0, f"Missing equity target for {node} {kind}")
                continue
            event = events.pop(target)
            require(raw[target]["amount"] is raw[target]["source_ref"] is None
                    and event["kind"] == kind == raw[target]["kind"]
                    and event["date"] == move["date"] == raw[target]["date"]
                    and event["category"] == raw[target]["category"] and amount(event["amount"]) == value,
                    f"Equity export differs: {node} {kind}")
        contributions += amount(move["contribution"])
        distributions += amount(move["distribution"])
    require(not events and contributions > 0, "Unmatched equity movements")
    verify_amounts(story, dict(gross_contributions=contributions, gross_distributions=distributions,
                               net_cash_profit=distributions - contributions,
                               equity_multiple=distributions / contributions), "Refinance equity totals")
    categories = story["cash_by_category"]
    require(amount(categories["net_refinance_distribution"]) == Fraction(bridge["projected_equity_distribution"])
            and amount(categories["refinance_cash_in"]) == 0, "Refinance cash direction differs")
    return dict(equity_level=story["equity_level"], events=story["events"], cash_horizon=story["cash_horizon"],
                gross_contributions=str(contributions), gross_distributions=str(distributions),
                net_cash_profit=str(distributions - contributions), equity_multiple=str(distributions / contributions),
                normalized_total_distributions=str(amount(story["normalized_story"]["total_distributions"])),
                annual_irr_roots=story["annual_irr_roots"], selected_rate=None)


def replay_branch(archive, independent):
    evidence = load_evidence(independent_test_fixture=independent)
    regenerated = branch(evidence, include_cash_in=independent)
    require(regenerated == archive, "Archived refinance and sale revision evidence differs")
    comparison = json.loads(regenerated["comparison"]["payload_json"])
    capacity = evidence.capacity_run.payload
    guarded = evidence.guarded_run
    bridge = replay_refinance_bridge(evidence)
    selected = amount(capacity["selected_principal"])
    maximum = amount(capacity["maximum_principal_capacity"])
    require(capacity["bank_credit_approved"] is capacity["funds_available_verified"] is False
            and guarded.payload["decision"] == comparison["decision"] == "PENDING"
            and comparison["real_decisions_enabled"] is comparison["production_authorized"] is False,
            "Unexpected refinance approval or decision")
    if independent:
        require(selected <= maximum and guarded.compiled_raw is not None and not capacity["blockers"],
                "Independent fixture failed its declared capacity")
        equity = replay_equity(evidence, bridge)
    else:
        require(selected > maximum and guarded.compiled_raw is guarded.investor_run is None
                and "selected_principal_exceeds_declared_bank_capacity" in capacity["blockers"],
                "Original financing failure must withhold the return")
        equity = None
    revisions = []
    for row in comparison["revisions"]:
        metrics = row["cash_metrics"]
        require(row["decision"] == "PENDING" and (metrics is not None) == independent,
                "Sale revision changed the refinance gate")
        contribution = amount(row["projected_sale_contribution_required"])
        distribution = amount(row["projected_sale_distribution"])
        require(contribution >= 0 and distribution >= 0 and not (contribution and distribution),
                "Sale residual exported in both directions")
        if metrics is not None:
            verify_amounts(metrics, dict(additional_capital_contributions=contribution, net_sale_distribution=distribution),
                           row["revision_id"])
            require(amount(metrics["gross_contributions"]) == Fraction(equity["gross_contributions"]) + contribution
                    and amount(metrics["gross_distributions"]) == amount(metrics["receipts_excluding_sale_distributions"])
                    + distribution, "Sale revision changed or netted gross equity")
        revisions.append(dict(revision=row["revision_id"], state=row["state"], sale_cash_in=str(contribution),
                              sale_distribution=str(distribution),
                              net_cash_profit=None if metrics is None else str(amount(metrics["net_cash_profit"]))))
    return dict(bank_noi=str(amount(capacity["bank_noi"])), selected_principal=str(selected),
                maximum_principal=str(maximum), binding_limits=capacity["binding_limit_ids"],
                capacity_blockers=capacity["blockers"], refinance_bridge=bridge,
                project_equity=equity, sale_revisions=revisions)


def run():
    sale_only = replay_sale_only()
    archive = json.loads(local_file(ROOT, ARCHIVE).read_bytes())
    require(archive["original_bank_source_preserved"] is True and archive["decision"] == "PENDING"
            and archive["personal_investor_return"] is None, "Unexpected archived refinance profile")
    original = replay_branch(archive["original_project_branch"], independent=False)
    fixture = replay_branch(archive["independent_software_fixture_branch"], independent=True)
    require(original["refinance_bridge"] == fixture["refinance_bridge"], "Independent fixture changed cash inputs")
    return dict(status="passed", scope="archived_synthetic", decision="PENDING", currency="USD",
                sale_only=sale_only["snapshots"], refinance_original_blocked=original,
                refinance_independent_fixture=fixture, personal_investor_return=None)


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
