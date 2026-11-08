"""Replay declared capital cuts and conditional CoC alongside synthetic cash returns."""
from fractions import Fraction
from hashlib import sha256
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_refinance_return_replay_D26 import run as replay_cash
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.capital_checked_output import assemble_capital_checked_output


REGISTER = "docs/review/capital-fixture-generation-T98.json"
CASES = ("declared", "zero", "pending-basis", "missing-value", "large-pending")
STOCK_FIELDS = ("capital_still_invested", "retained_equity_value")
CASH_FIELDS = ("gross_contributions", "gross_distributions", "net_cash_profit", "equity_multiple",
               "cash_by_category", "annual_cash_receipts", "annual_irr_roots", "selected_IRR")


def replay_capital_case(root, record, name):
    raw = local_file(root, record["case"]).read_bytes()
    require(sha256(raw).hexdigest() == record["sha256"], f"Capital fixture hash differs: {name}")
    run = assemble_capital_checked_output(raw)
    payload = run.payload
    story = payload["current_project_return_story"]
    parent = run.parent_run.payload["current_project_return_story"]
    require(run.parent_run.sha256 == record["parent_run_sha256"]
            and story["upstream_story_blockers"] == record["upstream_story_blockers"]
            and all(story[key] == parent[key] for key in CASH_FIELDS)
            and story["gross_contributions"] == record["gross_contributions"]
            and story["gross_distributions"] == record["gross_receipts"],
            f"Parent result or cash changed: {name}")
    require(payload["decision"] == "PENDING" and payload["capital_values_derived"] is False
            and payload["retained_equity_counted_as_cash"] is False
            and payload["older_valid_snapshot_substituted"] is False
            and payload["deployment_enabled"] is payload["real_decisions_enabled"] is False,
            f"Unexpected authority or fallback: {name}")
    cuts = story["capital_snapshots"]
    claims = record["source_claims"]
    visibility = payload["capital_visibility"]
    require(len(cuts) == len(claims) == len(visibility), f"Capital inventory differs: {name}")
    factor = amount(story["normalized_story"]["scale_factor"])
    output = []
    for index, (cut, claim, state) in enumerate(zip(cuts, claims, visibility)):
        pending = (claim["basis_ref"] is None or claim["source_ref"] is None
                   or claim["currency"] != story["currency"]
                   or any(claim[key] is None for key in STOCK_FIELDS)
                   or amount(claim["capital_still_invested"]) < 0)
        expected_state = "PENDING" if pending else "declared_synthetic_not_derived"
        require(cut["as_of_date"] == claim["as_of_date"] == state["as_of_date"]
                and cut["retained_value_included_in_receipts"] is False
                and state["source_index"] == index and state["state"] == expected_state
                and bool(state["blockers"]) == pending
                and all(payload["capital_source_claims"][index][key] == value for key, value in claim.items()),
                f"Capital source or visibility differs: {name}")
        view = {}
        for key in STOCK_FIELDS:
            normalized = "normalized_" + key
            if pending:
                require(cut[key] is cut[normalized] is None, f"Pending stock is visible: {name}")
                view.update({key: None, normalized: None})
            else:
                value = amount(claim[key])
                require(cut[key] == claim[key] and amount(cut[normalized]) == value * factor,
                        f"Declared stock or its scale differs: {name}")
                view.update({key: str(value), normalized: str(value * factor)})
        output.append(dict(date=cut["as_of_date"], state=expected_state, blockers=state["blockers"], **view))
    latest = max(range(len(output)), key=lambda index: output[index]["date"])
    require(latest == payload["latest_capital_snapshot_index"]
            and output[latest]["state"] == payload["latest_capital_state"],
            f"Latest capital cutoff differs: {name}")
    require(not any(row["conditional_coc"] is not None for row in story["annual_cash_receipts"]),
            f"Capital snapshot used as a CoC denominator: {name}")
    return dict(case=name, case_sha256=record["sha256"], latest=output[latest], cuts=output,
                gross_distributions=str(amount(story["gross_distributions"])), conditional_coc=None)


def replay_refinance_coc(fixture):
    evidence = load_evidence(independent_test_fixture=True)
    story = evidence.guarded_run.investor_run.payload
    published = fixture["project_equity"]
    require(story["events"] == published["events"] and story["cash_horizon"] == published["cash_horizon"]
            and amount(story["gross_distributions"]) == Fraction(published["gross_distributions"]),
            "CoC ledger differs from the reconciled refinance cash")
    source = json.loads(evidence.investor_raw)
    basis, = source["annual_cash_bases"]
    annual, = story["annual_cash_receipts"]
    year = basis["year"]
    denominator = amount(basis["capital_base"])
    require(year == annual["calendar_cash_receipt_year"] and basis["basis_ref"] and basis["source_ref"]
            and basis["currency"] == story["currency"] == "USD" and denominator > 0,
            "Conditional CoC basis differs")
    cash = sum((amount(row["amount"]) for row in published["events"] if row["kind"] == "distribution"
                and row["category"] == "operating_distribution" and int(row["date"][:4]) == year), Fraction())
    ratio = cash / denominator
    stock, = story["capital_snapshots"]
    declared_stock, = source["capital_snapshots"]
    require(stock["as_of_date"] == declared_stock["as_of_date"]
            and all(stock[key] is declared_stock[key] is None for key in (*STOCK_FIELDS, "basis_ref", "source_ref")),
            "Refinance CoC basis supplied unsupported capital stock")
    require(amount(annual["declared_capital_base"]) == denominator
            and amount(annual["operating_distributions_only"]) == cash
            and amount(annual["conditional_coc"]) == ratio and annual["blocker"] is None
            and annual["operating_year_coverage_financially_verified"] is False
            and story["LP_allocation_applied"] is False,
            "Unexpected CoC scope or numerator")
    return dict(year=year, cash_horizon=published["cash_horizon"], operating_distributions=str(cash),
                declared_capital_base=str(denominator), conditional_coc=str(ratio),
                basis_ref=basis["basis_ref"], source_ref=basis["source_ref"], full_year_yield=None)


def run():
    cash = replay_cash()
    records = json.loads(local_file(ROOT, REGISTER).read_bytes())["cases"]
    require([record["case"] for record in records] ==
            [f"templates/miniuw-v1-capital-{name}-case.json" for name in CASES], "Expected five capital fixtures")
    capital = [replay_capital_case(ROOT, record, name) for record, name in zip(records, CASES)]
    conditional_coc = replay_refinance_coc(cash["refinance_independent_fixture"])
    require(cash["refinance_original_blocked"]["project_equity"] is None, "Blocked refinance supplied equity cash")
    for case in cash["sale_only"]:
        equity = case["project_equity"]
        require(all(equity[key] is None for key in STOCK_FIELDS)
                and all(row["conditional_coc"] is None for row in equity["calendar_year_cash"]),
                "Sale-only case acquired an unrelated capital or CoC base")
    equity = cash["refinance_independent_fixture"]["project_equity"]
    equity.update(conditional_coc=conditional_coc, capital_still_invested=None, retained_equity_value=None)
    cash["separate_capital_fixtures"] = capital
    return cash


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
