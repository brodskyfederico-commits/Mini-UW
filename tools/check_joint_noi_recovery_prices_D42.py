"""Reconcile the sale price needed for recovery with dated cash and loan capacity."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from math import ceil
import json
import sys

from check_discount_rate_crossover_D35 import BINDINGS as PRICES, run as replay_prices
from check_joint_noi_discounted_returns_D41 import FIXTURE as CASH, run as replay_cash
from check_operating_replay_D20 import ROOT, local_file, require
from miniuw_foundation.drafts import canonical, digest


FIXTURE = "templates/synthetic-joint-noi-recovery-prices-D42.json"
SCHEMA = "miniuw.synthetic-joint-noi-recovery-prices.v1"


def sale_period(row):
    start = date.fromisoformat(row["discount_date"])
    sale = date.fromisoformat(row["sale_date"])
    months = 12 * (sale.year - start.year) + sale.month - start.month
    require(months > 0 and start.day == sale.day, "Recovery price needs the monthly cash calendar")
    return months


def recovery_at_rate(observation, reference_price, gross_price, months):
    rate = Fraction(observation["monthly_discount_rate"])
    sale_discount = (1 + rate) ** -months
    project = observation["project"]
    net = Fraction(project["net_present_value"])
    minimum_price = gross_price - net / sale_discount
    require(minimum_price == reference_price > 0, "Recovery price differs from the independently replayed sale")
    contributions = Fraction(project["present_value_contributions"])
    participants = []
    for part in observation["participants"]:
        # D41 verified the same documented proportional share at every dated cash event.
        share = Fraction(part["present_value_contributions"]) / contributions
        participant_net = Fraction(part["net_present_value"])
        require(share > 0 and participant_net == (gross_price - minimum_price) * sale_discount * share,
                "Participant cash does not recover at the verified sale price")
        participants.append(dict(participant_id=part["participant_id"], share_fraction=str(share),
                                 minimum_gross_sale_price=str(minimum_price),
                                 net_present_value_at_scenario_sale_price=str(participant_net)))
    return dict(monthly_discount_rate=str(rate), minimum_gross_sale_price=str(minimum_price),
                minimum_gross_sale_price_in_cents=ceil(minimum_price * 100),
                gross_sale_price_margin=str(gross_price - minimum_price),
                project_net_present_value=str(net), participants=participants)


def run():
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    require(fixture["schema"] == SCHEMA
            and fixture["cash_fixture_sha256"] == digest(local_file(ROOT, CASH).read_text(encoding="utf-8"))
            and fixture["price_fixture_sha256"] == digest(local_file(ROOT, PRICES).read_text(encoding="utf-8")),
            "Recovery price evidence differs")
    cash = replay_cash()
    price_report = replay_prices()
    verified_prices = {
        (cost, sample["monthly_rate"], variant): Fraction(price)
        for cost, samples in price_report["by_sale_closing_cost"].items()
        for sample in samples for variant, price in sample["prices"].items()
    }
    scenarios = {}
    for case, row in cash["scenarios"].items():
        result = {key: row[key] for key in ("bank_noi", "valuation_noi", "principal", "capacity", "exceeded_limits",
                                           "blockers", "sale_revision", "gross_sale_proceeds", "sale_closing_costs",
                                           "return_state", "discount_date", "sale_date", "decision")}
        result["recovery_prices"] = None
        observations = row["rate_observations"]
        if row["return_state"] == "PENDING":
            require(observations is None and row["blockers"], "Blocked case exposed discounted cash")
        else:
            require([o["monthly_discount_rate"] for o in observations] == cash["monthly_rates"]
                    and row["sale_date"] == price_report["crossover"]["sale_date"], "Recovery calendars or rates differ")
            variant = case.split("/")[2]
            gross_price = Fraction(row["gross_sale_proceeds"])
            months = sale_period(row)
            result["recovery_prices"] = [
                recovery_at_rate(o, verified_prices[row["sale_closing_costs"], o["monthly_discount_rate"], variant],
                                 gross_price, months)
                for o in observations
            ]
        scenarios[case] = result
    return dict(status="passed", scope="synthetic_discounted_sale_price_to_recover_cash", currency="USD",
                decision="PENDING", scenarios=scenarios, verified_personal_investor_return=None,
                deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    rows = [row["recovery_prices"] for row in report["scenarios"].values() if row["recovery_prices"] is not None]
    margins = [Fraction(price["gross_sale_price_margin"]) for row in rows for price in row]
    return dict(status=report["status"], decision=report["decision"], recovery_prices_sha256=digest(canonical(report)),
                computed=len(rows), pending=len(report["scenarios"]) - len(rows), rate_observations=len(margins),
                below_recovery_price=sum(margin < 0 for margin in margins),
                at_recovery_price=sum(margin == 0 for margin in margins),
                above_recovery_price=sum(margin > 0 for margin in margins))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print counts and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
