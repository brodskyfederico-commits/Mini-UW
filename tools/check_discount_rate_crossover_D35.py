"""Verify the synthetic sale-price ordering across monthly discount rates."""
from argparse import ArgumentParser
from fractions import Fraction
from functools import partial
import json
import sys

from check_discounted_sale_recovery_D34 import BINDINGS as DISCOUNTED, present_value, validate_grid
from check_integrated_participation_D28 import allocate, replay_with_ledgers
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_joint_exit_D32 import replay_sale
from check_sale_cash_recovery_D33 import BINDINGS as NOMINAL, replay_priced_sale, replay_targets
from miniuw_foundation.drafts import canonical, digest


BINDINGS = "templates/synthetic-discount-rate-crossover-D35.json"
SCHEMA = "miniuw.synthetic-discount-rate-crossover.v1"
RATE_GRID = tuple(Fraction(x) for x in ("0", "0.005", "0.0066", "0.0067", "0.01", "0.02"))
LOW = "SYNTHETIC-D31-lower"
HIGH = "SYNTHETIC-D31-near-limit"
CASH_IN = "SYNTHETIC-D31-cash-in"


def read_fixture(fixture):
    nominal_raw = local_file(ROOT, NOMINAL).read_text(encoding="utf-8")
    discounted_raw = local_file(ROOT, DISCOUNTED).read_text(encoding="utf-8")
    nominal = json.loads(nominal_raw)
    discounted = json.loads(discounted_raw)
    rates = tuple(amount(row) for row in fixture["monthly_rates"])
    require(fixture["schema"] == SCHEMA and fixture["nominal_bindings_sha256"] == digest(nominal_raw)
            == discounted["nominal_bindings_sha256"]
            and fixture["discounted_bindings_sha256"] == digest(discounted_raw)
            and fixture["allocation_terms_sha256"] == nominal["allocation_terms_sha256"]
            == discounted["allocation_terms_sha256"]
            and fixture["discount_rate_basis_ref"] and rates == RATE_GRID,
            "Discount crossover sources or rate grid differ")
    return nominal, rates


def sample_rates(evidence, sale, origin, matrix_hash, group, *, rates):
    require(amount(sale["replacement_claims"]["gross_proceeds"]) == 0, "Expected zero-price anchor")
    _, anchor = replay_sale(evidence, sale, origin, False)
    require(digest(canonical(anchor)) == matrix_hash, "Crossover anchor differs from D32")
    flows = validate_grid(anchor)
    last_index = len(flows) - 1
    samples = {}
    for index, rate in enumerate(rates):
        price = -present_value(flows, rate) * (1 + rate) ** last_index
        require(price > 0, "Expected a positive recovery price")
        parent = replay_priced_sale(evidence, sale, origin, price, f"SYNTHETIC-D35/{group}/rate-{index}")
        require(present_value(validate_grid(parent), rate) == 0, "Replayed sale present value is not zero")
        samples[str(rate)] = (price, parent)
    return samples["0"][0], {"anchor_flows": flows, "samples": samples}


def price_difference(certificate, rate):
    return certificate["terminal_cash_reduction"] - certificate["earlier_cash_gain"] * (1 + rate) ** certificate["months_to_sale"]


def crossover(low, high, cash_in):
    require([row["date"] for row in low] == [row["date"] for row in high] == [row["date"] for row in cash_in],
            "Discount comparison calendars differ")
    delta = [amount(right["net"]) - amount(left["net"]) for left, right in zip(low, high, strict=True)]
    increased_cost = [amount(right["net"]) - amount(left["net"]) for left, right in zip(low, cash_in, strict=True)]
    earlier_index, terminal_index = [index for index, value in enumerate(delta) if value]
    require(terminal_index == len(low) - 1 and delta[earlier_index] > 0 and delta[terminal_index] < 0
            and [index for index, value in enumerate(increased_cost) if value] == [earlier_index]
            and increased_cost[earlier_index] < 0, "Expected only the refinance and sale cash differences")
    certificate = dict(earlier_cash_gain=delta[earlier_index], terminal_cash_reduction=-delta[terminal_index],
                       months_to_sale=terminal_index - earlier_index)
    left, right = Fraction(), RATE_GRID[-1]
    require(price_difference(certificate, left) > 0 and price_difference(certificate, right) < 0,
            "Expected a crossover inside the declared rate range")
    # The difference is strictly decreasing for nonnegative rates.
    for _ in range(24):
        middle = (left + right) / 2
        if price_difference(certificate, middle) > 0:
            left = middle
        else:
            right = middle
    require(price_difference(certificate, left) > 0 >= price_difference(certificate, right),
            "Crossover bracket lost its sign change")
    return certificate | {"monthly_rate_lower": left, "monthly_rate_upper": right,
                          "earlier_date": low[earlier_index]["date"], "sale_date": low[-1]["date"],
                          "cash_in_cost_increase": -increased_cost[earlier_index]}


def run():
    allocation, _, terms = replay_with_ledgers()
    fixture = json.loads(local_file(ROOT, BINDINGS).read_bytes())
    nominal, rates = read_fixture(fixture)
    require(fixture["allocation_terms_sha256"] == allocation["terms_sha256"], "Crossover allocation terms differ")
    targets = replay_targets(nominal, sample_prices=partial(sample_rates, rates=rates))
    hashes = fixture["sample_ledgers"]
    require(hashes.keys() == {f"{group}/{rate}" for group, (_, data) in targets.items()
                              for rate in data.get("samples", {})}, "Crossover ledger inventory differs")
    levels = {}
    pending = []
    for group, (row, data) in targets.items():
        if data:
            levels.setdefault(row["sale_closing_costs"], {})[row["refinance_variant"]] = (group, data)
        else:
            pending.append(dict(case=group, state=row["state"], blockers=row["blockers"], prices=None))

    tables = {}
    certificates = []
    for cost, variants in levels.items():
        certificate = crossover(*(variants[key][1]["anchor_flows"] for key in (LOW, HIGH, CASH_IN)))
        certificates.append(certificate)
        table = []
        for rate in rates:
            prices = {}
            for key, (group, data) in variants.items():
                price, parent = data["samples"][str(rate)]
                shares = allocate(terms, parent, hashes[f"{group}/{rate}"], require_unique_irr=False)
                require(shares["participants"] and all(present_value(part["dated_net_flows"], rate) == 0
                                                     for part in shares["participants"]),
                        "Participant present value did not recover at the scenario price")
                prices[key] = price
            delta = price_difference(certificate, rate)
            require(prices[HIGH] - prices[LOW] == delta and prices[CASH_IN] - prices[LOW]
                    == certificate["cash_in_cost_increase"] * (1 + rate) ** certificate["months_to_sale"]
                    and prices[CASH_IN] > max(prices[LOW], prices[HIGH]), "Rate ordering differs from dated cash evidence")
            table.append(dict(monthly_rate=str(rate), prices={key: str(price) for key, price in prices.items()},
                              lower_price_variant=LOW if delta > 0 else HIGH if delta < 0 else None))
        tables[cost] = table
    require(len(certificates) == 2 and certificates[0] == certificates[1], "Sale costs changed the crossover")
    certificate = {key: str(value) if isinstance(value, Fraction) else value for key, value in certificates[0].items()}
    return dict(status="passed", scope="synthetic_discount_rate_sensitivity", currency="USD", decision="PENDING",
                crossover=certificate, by_sale_closing_cost=tables, pending=pending,
                verified_personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    return dict(status=report["status"], decision=report["decision"], discount_crossover_sha256=digest(canonical(report)),
                rate_samples=len(RATE_GRID), price_replays=sum(len(row["prices"]) for table in report["by_sale_closing_cost"].values()
                                                             for row in table), pending=len(report["pending"]))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print sample counts and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
