"""Replay explicit worksheet percentage costs through valuation, sale and the equity ledger."""
from argparse import ArgumentParser
from base64 import b64decode
from pathlib import Path
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_refinance_variants_D31 import build_variant_evidence
from check_worksheet_exit_D62 import FIXTURE as EXIT, inputs, valuation_from_sheet
from check_worksheet_refinance_D45 import bind_worksheet_capacity, worksheet_parameters
from demo_costed_exit_sale import cost_source
from miniuw_linked_cotejo_D54 import publish
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.costed_exit_sale import assemble_costed_exit_sale, verify_costed_exit_sale
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.scheduled_expense_case import sha


FIXTURE = "templates/synthetic-worksheet-sale-costs-D63.json"


def calculate(case, worksheet, fixture, base, noi_raw, noi, initial_spec):
    checked = worksheet_parameters(worksheet, fixture["scenario_context"], fixture["worksheet_as_of_UTC"],
                                   {"C67": "exit_cap", "C68": "sale_cost_fraction"})
    result = dict(state="PENDING", decision="PENDING", worksheet=checked, candidate_price=None,
                  total_cost=None, cash=None, blockers=checked["blockers"])
    if checked["blockers"]:
        return result

    evidence = bind_worksheet_capacity(base, checked)
    vr, valuation = valuation_from_sheet(checked, noi_raw, noi, initial_spec)
    source = cost_source(valuation, case["unresolved_tax"])
    fee, = (row for row in source["costs"] if row["kind"] == "percent_of_gross")
    fraction = checked["parameters"]["sale_cost_fraction"]
    fee.update(value=fraction["value"], source_ref=f"sha256:{checked['workbook_sha256']}#{fraction['locator']}")
    cr = encoded(source)
    costs = produce_sale_costs(cr)
    br = encoded(dict(schema="miniuw.synthetic-costed-exit-sale.v1", revision_id=f"SYNTHETIC-D63-{case['id']}",
                      base_evidence_sha256=evidence_fingerprint(evidence), exit_spec_sha256=sha(vr),
                      exit_run_sha256=valuation.sha256, sale_node_id=evidence.closings[1].closing_id,
                      sale_at_value_hypothesis_ref="SYNTHETIC-D63-explicit-sale-at-value",
                      unchanged_other_sources_basis_ref="SYNTHETIC-D63-fixed-debt-dates-and-other-cash",
                      equity_funding_assumption_ref=None, cost_source_sha256=sha(cr), cost_run_sha256=costs.sha256))
    run = assemble_costed_exit_sale(evidence, noi_raw, noi, vr, valuation, cr, costs, br)
    verify_costed_exit_sale(evidence, noi_raw, noi, vr, valuation, cr, costs, br, run)
    payload = run.payload
    require(payload["decision"] == "PENDING" and payload["real_decisions_enabled"] is False,
            "Synthetic costed sale acquired a decision")
    price, total = valuation.payload["candidate_value"], costs.payload["total_closing_cost"]
    result.update(candidate_price=price, total_cost=total, cost_rows=costs.payload["cost_rows"],
                  blockers=sorted(set(payload["blockers"] + payload["cost_blockers"])),
                  cost_run_sha256=costs.sha256, costed_sale_sha256=run.sha256)
    if payload["state"] != "compiled_synthetic":
        require(result["blockers"], "Blocked sale lost its pending reason")
        return result

    require(amount(total) == 10 + amount(price) * amount(fraction["value"]),
            "Sale costs disagree with independent fixed-plus-percentage calculation")
    revision = run.exit_sale_run.sale_revision_run
    original = evidence.guarded_run.investor_run.payload
    investor = revision.guarded_run.investor_run.payload
    close = json.loads(evidence.closings[1].closing_raw)
    sale_date = close["closing_date"]
    claims = close["amounts"]
    delta = amount(price) - amount(claims["gross_proceeds"]) - amount(total) + amount(claims["closing_costs_paid"])
    require(amount(investor["gross_distributions"]) - amount(original["gross_distributions"]) == delta
            and investor["gross_contributions"] == original["gross_contributions"]
            and [e for e in investor["events"] if e["date"] < sale_date]
            == [e for e in original["events"] if e["date"] < sale_date],
            "Sale cost did not flow exactly once through the closing")
    result.update(state="computed_synthetic_costed_sale", cash=dict(
        gross_distributions=investor["gross_distributions"], gross_contributions=investor["gross_contributions"],
        net_cash_profit=investor["net_cash_profit"], equity_multiple=investor["equity_multiple"]))
    return result


def run():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = json.loads(raw)
    exit_raw = local_file(ROOT, EXIT).read_bytes()
    require(fixture["schema"] == "miniuw.synthetic-worksheet-sale-costs.v1"
            and fixture["exit_fixture_sha256"] == sha(exit_raw), "Sale cost fixture differs")
    exit_fixture, base, variants, noi_raw, noi, spec = inputs(exit_raw)
    evidence = build_variant_evidence(base, variants["SYNTHETIC-D31-lower"])
    cases = {}
    for case in fixture["cases"]:
        workbook = fixture["workbooks"][case["workbook"]]
        sheet = b64decode(workbook["xlsx_base64"], validate=True)
        require(sha(sheet) == workbook["sha256"], "Sale cost workbook differs")
        row = calculate(case, sheet, exit_fixture, evidence, noi_raw, noi, spec)
        for field, expected in (("candidate_price", case["price"]), ("total_cost", case["cost"])):
            actual = None if row[field] is None else str(amount(row[field]))
            require(actual == expected, f"Sale cost case {case['id']} differs: {field}")
        require((row["cash"] is not None) == (case["blocker"] is None)
                and (not row["blockers"] if case["blocker"] is None else case["blocker"] in row["blockers"]),
                f"Sale cost case differs: {case['id']}")
        cases[case["id"]] = row
    require(len(cases) == 5 and sum(row["cash"] is not None for row in cases.values()) == 3,
            "Unexpected costed sale inventory")
    require(amount(cases["price_500"]["cash"]["gross_distributions"])
            - amount(cases["price_400"]["cash"]["gross_distributions"]) == 95,
            "Price increase did not flow net of its percentage cost")
    return dict(status="passed", decision="PENDING", fixture_sha256=sha(raw), cases=cases)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New path for full synthetic evidence.")
    args = parser.parse_args()
    try:
        result = run()
        if args.output is not None:
            publish(args.output, result)
        print(json.dumps(dict(status=result["status"], decision=result["decision"], cases=len(result["cases"]),
                              computed=3, pending=2, evidence_sha256=sha(encoded(result))), ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
