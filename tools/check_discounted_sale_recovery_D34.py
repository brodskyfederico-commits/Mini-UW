"""Replay synthetic sale prices that make present-value equity cash exactly zero."""
from argparse import ArgumentParser
from fractions import Fraction
from functools import partial
import json
import sys

from check_integrated_participation_D28 import allocate, replay_with_ledgers
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_participant_joint_exit_D32 import replay_sale
from check_sale_cash_recovery_D33 import BINDINGS as NOMINAL, OFFSETS, replay_priced_sale, replay_targets
from miniuw_foundation.drafts import canonical, digest


BINDINGS = "templates/synthetic-discounted-sale-recovery-D34.json"
SCHEMA = "miniuw.synthetic-discounted-sale-recovery.v1"


def present_value(flows, monthly_rate):
    factor = 1 + monthly_rate
    return sum((amount(row["net"]) / factor ** index for index, row in enumerate(flows)), Fraction())


def validate_grid(parent):
    evidence = parent["evidence"]
    dates = evidence["grid"]["dates"]
    flows = evidence["dated_net_flows"]
    require(evidence["grid"]["spacing"] == "calendar_months_same_day"
            and evidence["grid"]["step_months"] == 1
            and [row["date"] for row in flows] == dates
            and dates[-1] == parent["story"]["cash_horizon"]["end"], "Expected a monthly grid through sale")
    return flows


def samples(evidence, sale, origin, matrix_hash, group, *, monthly_rate):
    require(amount(sale["replacement_claims"]["gross_proceeds"]) == 0, "Expected zero-price anchor")
    _, anchor = replay_sale(evidence, sale, origin, False)
    require(digest(canonical(anchor)) == matrix_hash, "Discounted anchor differs from D32")
    flows = validate_grid(anchor)
    final_index = len(flows) - 1
    factor = 1 + monthly_rate
    sale_discount = factor ** -final_index
    zero_price_pv = present_value(flows, monthly_rate)
    required_price = -zero_price_pv / sale_discount
    nominal_price = -present_value(flows, Fraction())
    require(nominal_price == -amount(anchor["story"]["net_cash_profit"])
            and required_price > nominal_price >= 1, "Unexpected discounted cash recovery price")
    probes = {}
    for label, offset in OFFSETS.items():
        price = required_price + offset
        parent = replay_priced_sale(evidence, sale, origin, price, f"SYNTHETIC-D34/{group}/{label}")
        require(present_value(validate_grid(parent), monthly_rate) == offset * sale_discount,
                "Replayed discounted cash does not match exact price probe")
        probes[label] = dict(price=price, parent=parent, expected_pv=offset * sale_discount,
                             nominal_price=nominal_price, discount_date=flows[0]["date"], sale_date=flows[-1]["date"])
    return required_price, probes


def load_case(bindings):
    raw = local_file(ROOT, NOMINAL).read_text(encoding="utf-8")
    nominal = json.loads(raw)
    monthly_rate = amount(bindings["monthly_discount_rate"])
    require(bindings["schema"] == SCHEMA and bindings["nominal_bindings_sha256"] == digest(raw)
            and bindings["allocation_terms_sha256"] == nominal["allocation_terms_sha256"]
            and bindings["discount_rate_basis_ref"] and monthly_rate == Fraction(1, 100),
            "Discounted sensitivity or nominal bindings differ")
    return nominal, monthly_rate


def check_probe(terms, probe, binding, monthly_rate):
    parent = probe["parent"]
    allocation = allocate(terms, parent, binding, require_unique_irr=False)
    risk = observe_allocation(allocation, parent)
    require(risk["project"] is not None, "Discounted sale probe failed to allocate")
    rows = []
    for part in allocation["participants"]:
        share = amount(part["share_fraction"])
        value = present_value(part["dated_net_flows"], monthly_rate)
        require(value == probe["expected_pv"] * share, "Participant present value differs from its share")
        rows.append(dict(participant_id=part["participant_id"], share_fraction=str(share), present_value=str(value)))
    require(sum(Fraction(row["present_value"]) for row in rows) == probe["expected_pv"],
            "Participant present values do not conserve the project")
    return dict(gross_sale_price=str(probe["price"]), project_present_value=str(probe["expected_pv"]), participants=rows)


def run():
    allocation, _, terms = replay_with_ledgers()
    bindings = json.loads(local_file(ROOT, BINDINGS).read_bytes())
    nominal, monthly_rate = load_case(bindings)
    require(bindings["allocation_terms_sha256"] == allocation["terms_sha256"], "Discounted terms differ")
    targets = replay_targets(nominal, sample_prices=partial(samples, monthly_rate=monthly_rate))
    hashes = bindings["probe_ledgers"]
    require(hashes.keys() == {f"{group}/{label}" for group, (_, probes) in targets.items() for label in probes},
            "Discounted probe inventory differs")
    rows = {}
    for group, (row, probes) in targets.items():
        row["discounted_cash_recovery_sale_price"] = row.pop("cash_recovery_sale_price")
        row.update(nominal_cash_recovery_sale_price=None, discount_date=None, sale_date=None)
        if probes:
            center = probes["at"]
            row.update(nominal_cash_recovery_sale_price=str(center["nominal_price"]),
                       discount_date=center["discount_date"], sale_date=center["sale_date"],
                       probes={label: check_probe(terms, probe, hashes[f"{group}/{label}"], monthly_rate)
                               for label, probe in probes.items()})
        rows[group] = row
    return dict(status="passed", scope="synthetic_discounted_cash_recovery", currency="USD", decision="PENDING",
                monthly_discount_rate=str(monthly_rate), annual_effective_equivalent=str((1 + monthly_rate) ** 12 - 1),
                sale_cash_recovery=rows, verified_personal_investor_return=None,
                deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    rows = report["sale_cash_recovery"].values()
    return dict(status=report["status"], decision=report["decision"], discounted_recovery_sha256=digest(canonical(report)),
                computed=sum(row["probes"] is not None for row in rows),
                pending=sum(row["state"] == "PENDING" for row in rows),
                probes=sum(len(row["probes"] or {}) for row in rows))


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
