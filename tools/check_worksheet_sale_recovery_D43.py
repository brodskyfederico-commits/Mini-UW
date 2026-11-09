"""Verify conditional sale recovery from the T111 source-first worksheet run."""
from argparse import ArgumentParser
import json
from math import ceil
import sys

from check_discount_rate_crossover_D35 import BINDINGS as DISCOUNT, read_fixture
from check_discounted_sale_recovery_D34 import present_value, validate_grid
from check_joint_noi_discounted_returns_D41 import discounted_cash
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_sale_cash_recovery_D33 import OFFSETS
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_service import rational
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.worksheet_settled_output import assemble_worksheet_settled_output


FIXTURE = "templates/synthetic-worksheet-sale-recovery-D43.json"
SCHEMA = "miniuw.synthetic-worksheet-sale-recovery.v1"


def closing_source(worksheet):
    source = worksheet
    for key in ("phased_settled_source_utf8", "current_settled_source_utf8", "case_source_utf8"):
        source = json.loads(source[key])
    return json.loads(source["sale"]["closing_source_utf8"])


def closing_net(source, price=None):
    if price is not None:
        claims = source["amounts"]
        proceeds = claims["gross_proceeds"] | {
            "value": rational(price), "source_ref": "SYNTHETIC-D43-gross-sale-price-probe"
        }
        source = source | {"amounts": claims | {"gross_proceeds": proceeds}}
    result = produce_closing_cash(canonical(source).encode()).payload
    require(result["state"] == "computed_synthetic_closing"
            and amount(result["total_cash_conservation_residual"]) == 0, "Sale cash is blocked or does not reconcile")
    return amount(result["exportable_equity_distribution"]) - amount(result["exportable_equity_contribution"])


def recovery_observation(source, flows, events, rate, gross, baseline_close):
    project = discounted_cash(events, flows, rate)
    sale_discount = (1 + rate) ** (1 - len(flows))
    threshold = gross - project["net_present_value"] / sale_discount
    require(threshold >= 1, "Expected room for the lower sale-price probe in the nonnegative domain")
    probes = {}
    for label, offset in OFFSETS.items():
        price = threshold + offset
        net_sale_cash = closing_net(source, price)
        # The T111 replay bound every other date. Replace only the verified terminal equity cash.
        net = project["net_present_value"] + (net_sale_cash - baseline_close) * sale_discount
        require(net == offset * sale_discount, "Price probe differs from dated equity cash")
        probes[label] = dict(gross_sale_price=str(price), project_net_present_value=str(net))
    return dict(monthly_discount_rate=str(rate), minimum_gross_sale_price=str(threshold),
                minimum_gross_sale_price_in_cents=ceil(threshold * 100),
                gross_sale_price_margin=str(gross - threshold),
                project_cash_at_scenario_price={key: str(value) for key, value in project.items()}, probes=probes)


def observe(raw, rates):
    run = assemble_worksheet_settled_output(raw.encode())
    result = run.payload
    story = result["current_project_return_story"]
    output = dict(source_sha256=result["source_sha256"], worksheet_run_sha256=run.sha256, state=result["state"],
                  blockers=result["blockers"], decision=result["decision"], cash_recovery=None)
    require(result["decision"] == "PENDING", "Unexpected worksheet decision")
    if story is None:
        require(result["state"] == "PENDING"
                and result["current_irr_evidence"] is result["current_holding_sale_totals"] is None,
                "Blocked worksheet exposed current sale cash")
        return output

    flows = validate_grid({"story": story, "evidence": result["current_irr_evidence"]
                           | {"dated_net_flows": story["dated_net_flows"]}})
    events = story["events"]
    source = closing_source(json.loads(raw))
    gross = amount(source["amounts"]["gross_proceeds"])
    require(story["equity_level"] == "aggregate_project_equity" and source["kind"] == "sale"
            and story["currency"] == source["currency"] == "USD" and story["context"] == source["context"]
            and source["closing_date"] == flows[-1]["date"] and flows[0]["date"] == story["cash_horizon"]["start"]
            and gross == amount(result["current_holding_sale_totals"]["sale_proceeds"]),
            "Sale source differs from the verified worksheet run")
    baseline = closing_net(source)
    require(baseline == amount(flows[-1]["net"]) and baseline > 0, "Terminal sale cash differs from the verified ledger")
    require(present_value(flows, 0) == amount(story["net_cash_profit"]), "Nominal worksheet cash differs")
    output["cash_recovery"] = dict(currency=story["currency"], gross_sale_price=str(gross),
                                   fixed_sale_closing_costs=str(amount(source["amounts"]["closing_costs_paid"])),
                                   discount_date=flows[0]["date"], sale_date=flows[-1]["date"],
                                   observations=[recovery_observation(source, flows, events, rate, gross, baseline)
                                                 for rate in rates])
    return output


def run():
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    discount_raw = local_file(ROOT, DISCOUNT).read_text(encoding="utf-8")
    require(fixture["schema"] == SCHEMA and fixture["discount_fixture_sha256"] == digest(discount_raw),
            "Worksheet recovery discount source differs")
    _, rates = read_fixture(json.loads(discount_raw))
    cases = {}
    for name, binding in fixture["worksheet_cases"].items():
        raw = local_file(ROOT, binding["path"]).read_text(encoding="utf-8")
        require(digest(raw) == binding["sha256"], f"Worksheet recovery source differs: {name}")
        case = observe(raw, rates)
        require((case["cash_recovery"] is not None) is binding["expected_cash_available"],
                f"Worksheet recovery gate differs: {name}")
        cases[name] = case
    return dict(status="passed", scope="synthetic_worksheet_project_equity_recovery",
                cases=cases, decision="PENDING", verified_personal_investor_return=None,
                deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    observations = [o for case in report["cases"].values() if case["cash_recovery"] is not None
                    for o in case["cash_recovery"]["observations"]]
    return dict(status=report["status"], decision=report["decision"], worksheet_sale_recovery_sha256=digest(canonical(report)),
                computed=sum(case["cash_recovery"] is not None for case in report["cases"].values()),
                pending=sum(case["cash_recovery"] is None for case in report["cases"].values()),
                rate_observations=len(observations), probes=sum(len(o["probes"]) for o in observations))


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
