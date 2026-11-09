"""Test whether synthetic bank NOI leaves the D35 price comparison available."""
from argparse import ArgumentParser
from dataclasses import replace
from fractions import Fraction
import json
import sys

from check_discount_rate_crossover_D35 import BINDINGS as CROSSOVER, HIGH, LOW, RATE_GRID, read_fixture, sample_rates
from check_integrated_participation_D28 import ledger
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_refinance_variants_D31 import CAPACITY_BLOCKER, build_variant_evidence, encode, set_claim
from check_return_replay_D23 import indexed
from check_sale_cash_recovery_D33 import source_data
from demo_project_sale_revisions import load_evidence, sha
from miniuw_foundation.capacity_project_returns import assemble_capacity_checked_returns
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.refinance_capacity import size_refinance


FIXTURE = "templates/synthetic-bank-noi-capacity-order-D36.json"
SCHEMA = "miniuw.synthetic-bank-noi-capacity-order.v1"
RATES = (Fraction("0.0066"), Fraction("0.0067"))


def revised_bank_evidence(base, bank_noi, source):
    raw = json.loads(base.capacity_inputs.bank_noi_raw)
    income = indexed(raw["income_rows"], "item_id")["SYNTHETIC-income-residential"]
    set_claim(income, bank_noi, source)
    bank_raw = encode(raw)
    bank = produce_operating_noi(bank_raw)
    require(amount(bank.payload["noi"]) == bank_noi, "Bank NOI source did not reproduce the declared shock")
    inputs = replace(base.capacity_inputs, bank_noi_raw=bank_raw, bank_noi_run=bank)
    spec = json.loads(base.capacity_spec_raw)
    spec.update(bank_noi_source_sha256=sha(bank_raw), bank_noi_run_sha256=bank.sha256)
    spec_raw = encode(spec)
    capacity = size_refinance(inputs, spec_raw)
    binding = replace(base.binding, capacity_spec_sha256=sha(spec_raw), capacity_run_sha256=capacity.sha256)
    guarded = assemble_capacity_checked_returns(base.periods, base.closings, base.manifest_raw, base.project_run,
                                                 inputs, spec_raw, capacity, base.investor_raw, binding)
    return capacity.payload, guarded


def verified_prices(evidence, refinance, sale, matrix, crossover, variant_id):
    guarded = evidence.guarded_run
    parent = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
    parent["guarded_run_sha256"] = guarded.sha256
    require(digest(canonical(parent)) == refinance["project_ledgers"][variant_id], "D31 cash anchor differs")
    group = f"{variant_id}/{sale['revision_id']}"
    # D35 IDs use the index in its full grid. Verify the two stored scenario hashes with that grid.
    _, data = sample_rates(evidence, sale, parent, matrix["project_ledgers"][group], group, rates=RATE_GRID)
    prices = {}
    for rate in RATES:
        price, revised = data["samples"][str(rate)]
        require(digest(canonical(revised)) == crossover["sample_ledgers"][f"{group}/{rate}"],
                "D35 price scenario differs")
        prices[str(rate)] = str(price)
    return prices


def observe(base, bank_noi, source, prices):
    sizing, guarded = revised_bank_evidence(base, bank_noi, source)
    original = base.capacity_run.payload
    require(sizing["bank_credit_approved"] is sizing["funds_available_verified"] is False
            and sizing["decision"] == guarded.payload["decision"] == "PENDING"
            and guarded.payload["production_authorized"] is False
            and sizing["valuation_noi"] == original["valuation_noi"]
            and sizing["computed_property_value"] == original["computed_property_value"]
            and sizing["capacity_limits"]["LTV"] == original["capacity_limits"]["LTV"]
            and sizing["regular_annual_sizing_constant"] == original["regular_annual_sizing_constant"],
            "Bank sensitivity changed valuation, debt service or approval")
    principal = amount(sizing["selected_principal"])
    capacity = amount(sizing["maximum_principal_capacity"])
    blocked = principal > capacity
    require(sizing["binding_limit_ids"] == ["DSCR"]
            and sizing["blockers"] == ([CAPACITY_BLOCKER] if blocked else []), "Unexpected capacity result")
    if blocked:
        require(guarded.compiled_raw is guarded.investor_run is None, "Capacity block leaked cash or a price")
    else:
        require(guarded.compiled_raw is not None and guarded.compiled_raw == base.guarded_run.compiled_raw
                and guarded.investor_run.payload == base.guarded_run.investor_run.payload,
                "A bank-only change altered dated investor cash")
    return dict(state="PENDING" if blocked else "compatible_synthetic_capacity",
                principal=str(principal), capacity=str(capacity),
                achieved_dscr=str(amount(sizing["achieved_dscr_annual_sizing_only"])),
                blockers=sizing["blockers"], sale_recovery_prices=None if blocked else prices)


def capacity_boundary(base, variant_id):
    sizing = base.capacity_run.payload
    spec = json.loads(base.capacity_spec_raw)
    dscr = amount(spec["parameters"]["minimum_dscr"])
    principal = amount(sizing["selected_principal"])
    exact = principal * dscr * amount(sizing["regular_annual_sizing_constant"])
    rows = {}
    for label, offset in (("below", -1), ("at", 0), ("above", 1)):
        noi = exact + offset
        result = observe(base, noi, f"SYNTHETIC-D36/{variant_id}/{label}", None)
        require((result["state"] == "PENDING") == (offset < 0)
                and (Fraction(result["capacity"]) == principal) == (offset == 0), "DSCR boundary differs")
        rows[label] = dict(bank_noi=str(noi), **result)
    return dict(exact_bank_noi=str(exact), probes=rows)


def run():
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    crossover_raw = local_file(ROOT, CROSSOVER).read_text(encoding="utf-8")
    crossover = json.loads(crossover_raw)
    nominal, _ = read_fixture(crossover)
    matrix, refinance, sales = source_data(nominal)
    require(fixture["schema"] == SCHEMA and fixture["crossover_fixture_sha256"] == digest(crossover_raw)
            and fixture["bank_noi_basis_ref"] and [amount(v) for v in fixture["bank_noi_scenarios"]] == [750, 1500, 2000],
            "Unexpected bank-only stress fixture")
    reference = load_evidence(independent_test_fixture=True)
    require(evidence_fingerprint(reference) == refinance["base_evidence_sha256"], "Refinance base evidence differs")
    variants = indexed(refinance["variants"], "variant_id")
    keys = (LOW, HIGH)
    parents = {key: build_variant_evidence(reference, variants[key]) for key in keys}
    sale = indexed(sales, "revision_id")["SYNTHETIC-sale-0"]
    prices = {key: verified_prices(parent, refinance, sale, matrix, crossover, key) for key, parent in parents.items()}
    boundaries = {key: capacity_boundary(parent, key) for key, parent in parents.items()}
    shocks = []
    for value in fixture["bank_noi_scenarios"]:
        noi = amount(value)
        results = {key: observe(parent, noi, f"SYNTHETIC-D36-bank-noi-{noi}", prices[key])
                   for key, parent in parents.items()}
        available = [key for key in keys if results[key]["sale_recovery_prices"] is not None]
        comparison = None
        if len(available) == 2:
            comparison = {str(rate): min(available, key=lambda key: Fraction(prices[key][str(rate)]))
                          for rate in RATES}
            require(list(comparison.values()) == [LOW, HIGH], "D35 crossover changed under a bank-only shock")
        shocks.append(dict(bank_noi=str(noi), eligible_for_synthetic_comparison=available,
                           lower_sale_price_by_monthly_rate=comparison, results=results))
    require([len(row["eligible_for_synthetic_comparison"]) for row in shocks] == [0, 1, 2],
            "Bank NOI shocks did not reproduce all availability states")
    return dict(status="passed", scope="synthetic_bank_noi_and_discount_order", currency="USD", decision="PENDING",
                sale_closing_costs=str(amount(sale["replacement_claims"]["closing_costs_paid"])),
                monthly_rates=[str(rate) for rate in RATES], bank_noi_cases=shocks, capacity_boundaries=boundaries,
                deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    return dict(status=report["status"], decision=report["decision"], bank_noi_capacity_sha256=digest(canonical(report)),
                eligible_counts=[len(row["eligible_for_synthetic_comparison"]) for row in report["bank_noi_cases"]],
                capacity_probes=sum(len(row["probes"]) for row in report["capacity_boundaries"].values()))


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
