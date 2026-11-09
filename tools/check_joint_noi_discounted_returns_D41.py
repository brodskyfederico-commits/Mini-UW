"""Discount the D40 gross equity cash while preserving capacity and dated participation."""
from argparse import ArgumentParser
from fractions import Fraction
import json
import sys

from check_discount_rate_crossover_D35 import BINDINGS as DISCOUNT, read_fixture
from check_discounted_sale_recovery_D34 import present_value, validate_grid
from check_joint_noi_sale_returns_D40 import BINDINGS as CASH, replay_with_allocations
from check_operating_replay_D20 import ROOT, amount, local_file, require
from miniuw_foundation.drafts import canonical, digest


FIXTURE = "templates/synthetic-joint-noi-discounted-returns-D41.json"
SCHEMA = "miniuw.synthetic-joint-noi-discounted-returns.v1"
ADDITIVE = ("present_value_contributions", "present_value_receipts", "net_present_value",
            "present_value_recovered", "present_value_shortfall", "present_value_surplus")


def discounted_cash(events, net_flows, rate):
    factors = {row["date"]: (1 + rate) ** -index for index, row in enumerate(net_flows)}
    contribution = receipt = Fraction()
    for event in events:
        value = amount(event["amount"]) * factors[event["date"]]
        require(value >= 0 and event["kind"] in ("contribution", "distribution"), "Unexpected gross cash event")
        if event["kind"] == "contribution":
            contribution += value
        else:
            receipt += value
    net = receipt - contribution
    require(contribution > 0 and net == present_value(net_flows, rate), "Discounted gross and net cash differ")
    recovered = min(contribution, receipt)
    return dict(present_value_contributions=contribution, present_value_receipts=receipt, net_present_value=net,
                present_value_recovered=recovered, present_value_shortfall=contribution - recovered,
                present_value_surplus=receipt - recovered, discounted_recovery_fraction=recovered / contribution)


def rate_observation(parent, project_flows, allocated, scenario, rate):
    project = discounted_cash(parent["story"]["dated_events"], project_flows, rate)
    participants = []
    totals = dict.fromkeys(ADDITIVE, Fraction())
    for part, nominal in zip(allocated, scenario["participants"], strict=True):
        require(part["participant_id"] == nominal["participant_id"]
                and [row["date"] for row in part["dated_net_flows"]] == [row["date"] for row in project_flows],
                "Participant identity or grid differs")
        participant = discounted_cash(part["dated_events"], part["dated_net_flows"], rate)
        for key in ADDITIVE:
            totals[key] += participant[key]
            require(participant[key] == project[key] * amount(part["share_fraction"]),
                    f"Participant discounted cash differs: {key}")
        require(participant["discounted_recovery_fraction"] == project["discounted_recovery_fraction"],
                "Proportional participant recovery differs")
        if rate == 0:
            require(participant["present_value_recovered"] == Fraction(nominal["cash_recovered"])
                    and participant["net_present_value"] == amount(nominal["metrics"]["net_cash_profit"]),
                    "Zero discount differs from D40 nominal recovery")
        participants.append(dict(participant_id=part["participant_id"], **{key: str(v) for key, v in participant.items()}))
    require(all(totals[key] == project[key] for key in ADDITIVE), "Participant present values do not sum to project")
    if rate == 0:
        require(project["present_value_recovered"] == Fraction(scenario["project"]["cash_recovered"]),
                "Zero discount does not reproduce the project")
    nominal_recovered = amount(scenario["project"]["cash_shortfall_at_horizon"]) == 0
    return dict(monthly_discount_rate=str(rate), project={key: str(v) for key, v in project.items()},
                participants=participants, nominal_recovery_with_discounted_shortfall=
                nominal_recovered and project["present_value_shortfall"] > 0)


def run():
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    cash_raw = local_file(ROOT, CASH).read_text(encoding="utf-8")
    discount_raw = local_file(ROOT, DISCOUNT).read_text(encoding="utf-8")
    require(fixture["schema"] == SCHEMA and fixture["cash_fixture_sha256"] == digest(cash_raw)
            and fixture["discount_fixture_sha256"] == digest(discount_raw) and fixture["discount_basis_ref"],
            "Discounted matrix sources differ")
    _, rates = read_fixture(json.loads(discount_raw))
    cash, dated = replay_with_allocations()
    scenarios = {}
    for case, row in cash["scenarios"].items():
        result = {key: row[key] for key in ("bank_noi", "valuation_noi", "principal", "capacity", "exceeded_limits",
                                           "blockers", "sale_revision", "gross_sale_proceeds", "sale_closing_costs",
                                           "return_state", "decision")}
        result.update(discount_date=None, sale_date=None, rate_observations=None)
        if row["return_state"] == "PENDING":
            require(case not in dated and row["project"] is row["participants"] is None, "Blocked case exposed cash")
        else:
            parent, allocated = dated.pop(case)
            flows = validate_grid(parent)
            result.update(discount_date=flows[0]["date"], sale_date=flows[-1]["date"],
                          rate_observations=[rate_observation(parent, flows, allocated, row, rate) for rate in rates])
        scenarios[case] = result
    require(not dated, "Unmatched discounted cash scenarios")
    return dict(status="passed", scope="synthetic_dated_cash_recovery", currency="USD", decision="PENDING",
                monthly_rates=[str(rate) for rate in rates], scenarios=scenarios,
                verified_personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    rows = [row["rate_observations"] for row in report["scenarios"].values() if row["rate_observations"] is not None]
    return dict(status=report["status"], decision=report["decision"], joint_discounted_returns_sha256=digest(canonical(report)),
                computed=len(rows), pending=len(report["scenarios"]) - len(rows),
                rate_observations=sum(len(row) for row in rows),
                nominal_only_recoveries=sum(o["nominal_recovery_with_discounted_shortfall"] for row in rows for o in row))


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
