"""Verify exact gross sale prices for cash recovery in the fixed synthetic exit profile."""
from argparse import ArgumentParser
from fractions import Fraction
import json
import sys

from check_integrated_participation_D28 import allocate, ledger, replay_with_ledgers
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_participant_joint_exit_D32 import BINDINGS as MATRIX, load_sources, replay_sale
from check_participant_refinance_variants_D31 import CAPACITY_BLOCKER, build_variant_evidence, set_claim
from check_return_replay_D23 import indexed
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.project_sale_revision import evidence_fingerprint


BINDINGS = "templates/synthetic-sale-cash-recovery-D33.json"
SCHEMA = "miniuw.synthetic-sale-cash-recovery.v1"
SAMPLES = ("SYNTHETIC-sale-0", "SYNTHETIC-sale-funding-required")
OFFSETS = {"below": -1, "at": 0, "above": 1}


def source_data(bindings):
    matrix_raw = local_file(ROOT, MATRIX).read_text(encoding="utf-8")
    matrix = json.loads(matrix_raw)
    refinance, sales, refinance_hash, sale_hash = load_sources()
    require(bindings["schema"] == SCHEMA and bindings["joint_matrix_sha256"] == digest(matrix_raw)
            and matrix["refinance_fixture_sha256"] == refinance_hash and matrix["sale_inventory_sha256"] == sale_hash
            and bindings["allocation_terms_sha256"] == matrix["allocation_terms_sha256"], "Cash recovery sources differ")
    sales_by_id = indexed(sales, "revision_id")
    return matrix, refinance, [sales_by_id[key] for key in SAMPLES]


def replay_priced_sale(evidence, sale, origin, price, identity):
    proceeds = sale["replacement_claims"]["gross_proceeds"].copy()
    set_claim(proceeds, price, identity)
    spec = sale | {"revision_id": identity, "replacement_claims": sale["replacement_claims"] | {"gross_proceeds": proceeds}}
    _, parent = replay_sale(evidence, spec, origin, False)
    return parent


def price_samples(evidence, sale, origin, matrix_hash, group):
    require(amount(sale["replacement_claims"]["gross_proceeds"]) == 0, "Expected zero-price anchor")
    _, anchor = replay_sale(evidence, sale, origin, False)
    require(digest(canonical(anchor)) == matrix_hash, "Zero-price anchor differs from D32")
    required_price = -amount(anchor["story"]["net_cash_profit"])
    require(required_price >= 1, "Expected a positive cash recovery price with room for the lower probe")
    probes = {}
    for label, offset in OFFSETS.items():
        identity = f"SYNTHETIC-D33/{group}/{label}"
        price = required_price + offset
        parent = replay_priced_sale(evidence, sale, origin, price, identity)
        require(amount(parent["story"]["net_cash_profit"]) == offset, "Replayed sale does not match exact cash recovery")
        probes[label] = (price, parent)
    return required_price, probes


def replay_targets(bindings, *, sample_prices=price_samples, groups=None):
    matrix, refinance, sales = source_data(bindings)
    base = load_evidence(independent_test_fixture=True)
    require(refinance["base_evidence_sha256"] == evidence_fingerprint(base), "Refinance base evidence differs")
    maximum = amount(base.capacity_run.payload["maximum_principal_capacity"])
    results = {}
    for key, variant in indexed(refinance["variants"], "variant_id").items():
        selected_sales = [sale for sale in sales if groups is None or f"{key}/{sale['revision_id']}" in groups]
        if not selected_sales:
            continue
        evidence = build_variant_evidence(base, variant)
        sizing = evidence.capacity_run.payload
        principal = amount(sizing["selected_principal"])
        blocked = principal > maximum
        require(principal == amount(variant["selected_principal"]) and amount(sizing["maximum_principal_capacity"]) == maximum
                and sizing["blockers"] == ([CAPACITY_BLOCKER] if blocked else [])
                and sizing["bank_credit_approved"] is sizing["funds_available_verified"] is False,
                "Cash recovery refinance gate differs")
        guarded = evidence.guarded_run
        origin = None
        if blocked:
            require(guarded.investor_run is guarded.compiled_raw is None, "Blocked refinance exposed equity cash")
        else:
            origin = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
            origin["guarded_run_sha256"] = guarded.sha256
            require(digest(canonical(origin)) == refinance["project_ledgers"][key], "Refinance anchor differs from D31")
        for sale in selected_sales:
            group = f"{key}/{sale['revision_id']}"
            row = dict(refinance_variant=key, refinance_principal=str(principal),
                       refinance_closing_costs=str(amount(variant["refinance_closing_costs"])),
                       sale_closing_costs=str(amount(sale["replacement_claims"]["closing_costs_paid"])),
                       state="PENDING", blockers=sizing["blockers"], cash_recovery_sale_price=None, probes=None)
            probes = {}
            if origin is not None:
                price, probes = sample_prices(evidence, sale, origin, matrix["project_ledgers"][group], group)
                row.update(state="computed_synthetic_cash_recovery", cash_recovery_sale_price=str(price))
            results[group] = row, probes
    return results


def check_probe(terms, price, parent, binding, offset):
    allocation = allocate(terms, parent, binding, require_unique_irr=False)
    risk = observe_allocation(allocation, parent)
    require(risk["project"] is not None, "Cash recovery probe did not allocate")
    parts = []
    for part in risk["participants"]:
        share = amount(part["share_fraction"])
        metrics = part["metrics"]
        net = Fraction(offset) * share
        require(amount(metrics["net_cash_profit"]) == net
                and amount(metrics["cash_shortfall_at_horizon"]) == max(0, -net)
                and amount(metrics["cash_surplus_at_horizon"]) == max(0, net), "Participant cash recovery differs")
        parts.append(dict(participant_id=part["participant_id"], share_fraction=str(share), net_cash=str(net),
                          cash_not_recovered=str(amount(metrics["cash_shortfall_at_horizon"]))))
    return dict(gross_sale_price=str(price), project_net_cash=str(offset), participants=parts)


def run():
    allocation, _, terms = replay_with_ledgers()
    bindings = json.loads(local_file(ROOT, BINDINGS).read_bytes())
    require(bindings["allocation_terms_sha256"] == allocation["terms_sha256"], "Cash recovery allocation terms differ")
    targets = replay_targets(bindings)
    expected = {f"{group}/{label}" for group, (_, probes) in targets.items() for label in probes}
    hashes = bindings["probe_ledgers"]
    require(hashes.keys() == expected, "Cash recovery probe inventory differs")
    rows = {}
    for group, (row, probes) in targets.items():
        if probes:
            row["probes"] = {
                label: check_probe(terms, price, parent, hashes[f"{group}/{label}"], OFFSETS[label])
                for label, (price, parent) in probes.items()
            }
        rows[group] = row
    return dict(status="passed", scope="synthetic_nominal_cash_recovery_at_sale", currency="USD", decision="PENDING",
                sale_cash_recovery=rows, verified_personal_investor_return=None,
                deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    rows = report["sale_cash_recovery"].values()
    return dict(status=report["status"], decision=report["decision"], cash_recovery_sha256=digest(canonical(report)),
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
