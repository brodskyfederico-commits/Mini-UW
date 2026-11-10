"""Replay the worksheet exit cap through forward NOI, closing and guarded equity cash."""
from argparse import ArgumentParser
from base64 import b64decode
from fractions import Fraction
from pathlib import Path
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_refinance_variants_D31 import FIXTURE as REFINANCE, build_variant_evidence
from check_worksheet_refinance_D45 import bind_worksheet_capacity, worksheet_parameters
from demo_project_sale_revisions import load_evidence
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.exit_sale_bridge import assemble_exit_sale, verify_exit_sale
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.scheduled_expense_case import sha


FIXTURE = "templates/synthetic-worksheet-exit-cap-D62.json"
NOI = "templates/synthetic-exit-forward-noi.json"
VALUATION = "templates/synthetic-exit-value-spec.json"


def calculate(case, worksheet, evidence, fixture, noi_raw, noi, initial_spec):
    checked = worksheet_parameters(worksheet, fixture["scenario_context"], fixture["worksheet_as_of_UTC"],
                                   {"C67": "exit_cap"})
    result = dict(state="PENDING", decision="PENDING", worksheet=checked,
                  forward_noi=None, candidate_price=None, cash=None, blockers=checked["blockers"])
    if checked["blockers"]:
        return result
    bound = bind_worksheet_capacity(evidence, checked)
    exit_cap = checked["parameters"]["exit_cap"]
    source = f"sha256:{checked['workbook_sha256']}#{exit_cap['locator']}"
    spec = initial_spec | {"cap_rate": initial_spec["cap_rate"] | {"value": exit_cap["value"], "source_ref": source}}
    raw = encoded(spec)
    value = produce_exit_value(noi_raw, noi, raw)
    close = bound.closings[1]
    bridge = encoded(dict(schema="miniuw.synthetic-exit-value-to-sale.v1",
                          revision_id=f"SYNTHETIC-D62-{case['id']}", base_evidence_sha256=evidence_fingerprint(bound),
                          exit_spec_sha256=sha(raw), exit_run_sha256=value.sha256, sale_node_id=close.closing_id,
                          sale_at_value_hypothesis_ref="SYNTHETIC-D62-explicit-sale-at-conditional-value",
                          unchanged_other_sources_basis_ref="SYNTHETIC-D62-fixed-dates-debt-reserves-and-sale-costs",
                          equity_funding_assumption_ref=None,
                          closing_cost_claim=json.loads(close.closing_raw)["amounts"]["closing_costs_paid"]))
    sale = assemble_exit_sale(bound, noi_raw, noi, raw, value, bridge)
    verify_exit_sale(bound, noi_raw, noi, raw, value, bridge, sale)
    payload = sale.payload
    require(payload["decision"] == "PENDING" and payload["real_decisions_enabled"] is False,
            "Synthetic exit acquired a decision")
    price = value.payload["candidate_value"]
    result.update(forward_noi=value.payload["forward_noi"], candidate_price=price, blockers=payload["blockers"],
                  valuation_blockers=value.payload["blockers"], valuation_sha256=value.sha256,
                  sale_sha256=sale.sha256, capacity=bound.capacity_run.payload["maximum_principal_capacity"])
    if price is not None:
        require(amount(price) == amount(noi.payload["noi"]) / amount(exit_cap["value"]),
                "Exit candidate disagrees with independent division")
    revision = sale.sale_revision_run
    investor = None if revision is None else revision.guarded_run.investor_run
    if investor is None:
        require(payload["blockers"], "Blocked sale lost its pending reason")
        return result
    original = bound.guarded_run.investor_run.payload
    revised = investor.payload
    sale_date = spec["valuation_date"]
    require([e for e in original["events"] if e["date"] < sale_date]
            == [e for e in revised["events"] if e["date"] < sale_date], "Exit revision changed earlier cash")
    original_proceeds = amount(json.loads(close.closing_raw)["amounts"]["gross_proceeds"])
    require(amount(revised["gross_distributions"]) - amount(original["gross_distributions"])
            == amount(price) - original_proceeds
            and revised["gross_contributions"] == original["gross_contributions"],
            "Candidate value did not flow exactly once through the sale cash")
    result.update(state="computed_synthetic_exit_sale", cash=dict(
        gross_contributions=revised["gross_contributions"], gross_distributions=revised["gross_distributions"],
        equity_multiple=revised["equity_multiple"], net_cash_profit=revised["net_cash_profit"],
        dated_events=revised["events"]))
    return result


def run():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = json.loads(raw)
    require(fixture["schema"] == "miniuw.synthetic-worksheet-exit-cap.v1"
            and set(fixture["sources"]) == {NOI, VALUATION, REFINANCE}, "Exit fixture inventory differs")
    sources = {path: local_file(ROOT, path).read_bytes() for path in fixture["sources"]}
    require(all(sha(value) == fixture["sources"][path] for path, value in sources.items()), "Exit source bytes differ")
    base = load_evidence(True, "synthetic-exit-test-sale-closing.json")
    require(evidence_fingerprint(base) == fixture["base_evidence_sha256"]
            and base.capacity_run.payload["context"] == fixture["scenario_context"], "Base exit evidence differs")
    variants = {row["variant_id"]: row for row in json.loads(sources[REFINANCE])["variants"]}
    noi = produce_operating_noi(sources[NOI])
    initial_spec = json.loads(sources[VALUATION])
    cases = {}
    for case in fixture["cases"]:
        workbook = fixture["workbooks"][case["workbook"]]
        sheet = b64decode(workbook["xlsx_base64"], validate=True)
        require(sha(sheet) == workbook["sha256"], "Synthetic exit workbook differs")
        evidence = build_variant_evidence(base, variants[case["variant"]])
        row = calculate(case, sheet, evidence, fixture, sources[NOI], noi, initial_spec)
        price = None if row["candidate_price"] is None else str(amount(row["candidate_price"]))
        require(price == case["price"] and (row["cash"] is not None) == (case["blocker"] is None)
                and (not row["blockers"] if case["blocker"] is None else case["blocker"] in row["blockers"]),
                f"Exit case differs: {case['id']}")
        cases[case["id"]] = row
    require(len(cases) == 5 and sum(row["cash"] is not None for row in cases.values()) == 2,
            "Unexpected exit cap inventory")
    return dict(status="passed", decision="PENDING", fixture_sha256=sha(raw), cases=cases)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New path for full synthetic evidence.")
    args = parser.parse_args()
    try:
        result = run()
        if args.output is not None:
            from miniuw_linked_cotejo_D54 import publish
            publish(args.output, result)
        print(json.dumps(dict(status=result["status"], decision=result["decision"], cases=len(result["cases"]),
                              computed=2, pending=3, evidence_sha256=sha(encoded(result))), ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
