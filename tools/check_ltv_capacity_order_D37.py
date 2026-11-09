"""Verify the valuation-side capacity gate and its tie with the bank NOI limit."""
from argparse import ArgumentParser
from dataclasses import replace
from fractions import Fraction
import json
import sys

from check_bank_noi_capacity_order_D36 import FIXTURE as BANK, RATES, verified_prices
from check_discount_rate_crossover_D35 import BINDINGS as CROSSOVER, HIGH, LOW, read_fixture
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_refinance_variants_D31 import CAPACITY_BLOCKER, build_variant_evidence, encode, rebind_closing, set_claim
from check_return_replay_D23 import indexed
from check_sale_cash_recovery_D33 import source_data
from demo_project_sale_revisions import load_evidence, sha
from miniuw_foundation.capacity_project_returns import assemble_capacity_checked_returns
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.project_cash import reconcile_project_cash
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.refinance_capacity import size_refinance


FIXTURE = "templates/synthetic-ltv-capacity-order-D37.json"
SCHEMA = "miniuw.synthetic-ltv-capacity-order.v1"
VALUATION_BLOCKER = "closing_valuation_claim_differs_from_computed_noi_cap_value"


def observe(base, valuation_noi, source, *, stale_valuation=False):
    original = base.capacity_run.payload
    valuation = json.loads(base.capacity_inputs.valuation_noi_raw)
    income = indexed(valuation["income_rows"], "item_id")["SYNTHETIC-income-residential"]
    set_claim(income, valuation_noi, source)
    valuation_raw = encode(valuation)
    valuation_run = produce_operating_noi(valuation_raw)
    require(amount(valuation_run.payload["noi"]) == valuation_noi, "Valuation NOI source differs")
    spec = json.loads(base.capacity_spec_raw)
    cap_rate = amount(spec["parameters"]["cap_rate"])
    ltv = amount(spec["parameters"]["maximum_ltv"])
    value = valuation_noi / cap_rate

    refinance, sale = base.closings
    closing = json.loads(refinance.closing_raw)
    if not stale_valuation:
        set_claim(closing["valuation_claim"], value, source)
    refinance = rebind_closing(refinance, closing, refinance.loans)
    closings = (refinance, sale)
    manifest = json.loads(base.manifest_raw)
    refi_node = indexed(manifest["nodes"], "node_id")[refinance.closing_id]
    refi_node.update(source_sha256=sha(refinance.closing_raw), run_sha256=refinance.closing_run.sha256,
                     upstream_source_sha256=sha(refinance.debt_spec_raw), upstream_run_sha256=refinance.debt_run.sha256)
    manifest_raw = encode(manifest)
    project = reconcile_project_cash(base.periods, closings, manifest_raw)
    require(project.payload["declared_cash_window_reconciled"]
            and project.payload["totals"] == base.project_run.payload["totals"]
            and amount(project.payload["cash_conservation_residual"]) == 0
            and refinance.closing_run.payload["valuation_included_in_cash"] is False,
            "Valuation change altered project cash")

    inputs = replace(base.capacity_inputs, valuation_noi_raw=valuation_raw, valuation_noi_run=valuation_run,
                     closing_raw=refinance.closing_raw, closing_run=refinance.closing_run)
    spec.update(valuation_noi_source_sha256=sha(valuation_raw), valuation_noi_run_sha256=valuation_run.sha256,
                closing_source_sha256=sha(refinance.closing_raw), closing_run_sha256=refinance.closing_run.sha256)
    spec_raw = encode(spec)
    capacity = size_refinance(inputs, spec_raw)
    inner = replace(base.binding.project_return_binding, manifest_source_sha256=sha(manifest_raw),
                    project_run_sha256=project.sha256)
    binding = replace(base.binding, capacity_spec_sha256=sha(spec_raw), capacity_run_sha256=capacity.sha256,
                      project_return_binding=inner)
    guarded = assemble_capacity_checked_returns(base.periods, closings, manifest_raw, project, inputs, spec_raw,
                                                 capacity, base.investor_raw, binding)

    sizing = capacity.payload
    principal = amount(original["selected_principal"])
    dscr_cap = amount(original["capacity_limits"]["DSCR"])
    ltv_cap = value * ltv
    limits = {"DSCR": dscr_cap, "LTV": ltv_cap}
    maximum = min(limits.values())
    binding_limits = [key for key, limit in limits.items() if limit == maximum]
    blockers = [CAPACITY_BLOCKER] if principal > maximum else []
    if stale_valuation:
        require(value != amount(closing["valuation_claim"]), "Stale valuation control did not change value")
        blockers.append(VALUATION_BLOCKER)
    require(sizing["bank_noi"] == original["bank_noi"]
            and sizing["regular_annual_sizing_constant"] == original["regular_annual_sizing_constant"]
            and amount(sizing["selected_principal"]) == principal
            and amount(sizing["computed_property_value"]) == value
            and {key: amount(v) for key, v in sizing["capacity_limits"].items()} == limits
            and amount(sizing["maximum_principal_capacity"]) == maximum
            and sizing["binding_limit_ids"] == binding_limits and sizing["blockers"] == sorted(blockers)
            and sizing["bank_credit_approved"] is sizing["funds_available_verified"] is False
            and sizing["decision"] == guarded.payload["decision"] == "PENDING"
            and guarded.payload["production_authorized"] is False, "Valuation capacity or scope differs")
    if blockers:
        require(guarded.compiled_raw is guarded.investor_run is None, "Blocked valuation leaked investor cash")
    else:
        actual = guarded.investor_run.payload
        prior = base.guarded_run.investor_run.payload
        financial = ("dated_net_flows", "cash_by_category", "gross_contributions", "gross_distributions",
                     "net_cash_profit", "annual_irr_roots", "cash_horizon")
        require(all(actual[key] == prior[key] for key in financial), "Valuation altered investor cash")
        for event, old in zip(actual["events"], prior["events"], strict=True):
            require(all(event[key] == old[key] for key in old if key != "source_ref"),
                    "Valuation altered a gross investor cash event")
            if old["category"] in ("net_refinance_distribution", "refinance_cash_in"):
                require(refinance.closing_run.sha256 in event["source_ref"], "Refinance event retains stale provenance")
            else:
                require(event["source_ref"] == old["source_ref"], "Unrelated event provenance changed")
    return dict(valuation_noi=str(valuation_noi), property_value=str(value), principal=str(principal),
                capacity=str(maximum), dscr_capacity=str(dscr_cap), ltv_capacity=str(ltv_cap),
                binding_limits=binding_limits, blockers=blockers,
                state="PENDING" if blockers else "compatible_synthetic_capacity")


def run():
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    bank_raw = local_file(ROOT, BANK).read_text(encoding="utf-8")
    crossover_raw = local_file(ROOT, CROSSOVER).read_text(encoding="utf-8")
    bank = json.loads(bank_raw)
    crossover = json.loads(crossover_raw)
    nominal, _ = read_fixture(crossover)
    matrix, refinance, sales = source_data(nominal)
    require(fixture["schema"] == SCHEMA and fixture["bank_fixture_sha256"] == digest(bank_raw)
            and bank["crossover_fixture_sha256"] == digest(crossover_raw)
            and fixture["valuation_noi_basis_ref"]
            and [amount(v) for v in fixture["valuation_noi_scenarios"]] == [15, 30, 49, 50],
            "Unexpected valuation stress fixture")
    reference = load_evidence(independent_test_fixture=True)
    require(evidence_fingerprint(reference) == refinance["base_evidence_sha256"], "Refinance base evidence differs")
    variants = indexed(refinance["variants"], "variant_id")
    keys = (LOW, HIGH)
    parents = {key: build_variant_evidence(reference, variants[key]) for key in keys}
    sale = indexed(sales, "revision_id")["SYNTHETIC-sale-0"]
    prices = {key: verified_prices(parent, refinance, sale, matrix, crossover, key) for key, parent in parents.items()}

    shocks = []
    for value in fixture["valuation_noi_scenarios"]:
        noi = amount(value)
        results = {key: observe(parent, noi, f"SYNTHETIC-D37-valuation-noi-{noi}") for key, parent in parents.items()}
        available = [key for key in keys if results[key]["state"] == "compatible_synthetic_capacity"]
        for key in keys:
            results[key]["sale_recovery_prices"] = prices[key] if key in available else None
        comparison = None
        if len(available) == 2:
            comparison = {str(rate): min(available, key=lambda key: Fraction(prices[key][str(rate)]))
                          for rate in RATES}
            require(list(comparison.values()) == [LOW, HIGH], "Valuation-only shock altered the D35 order")
        shocks.append(dict(valuation_noi=str(noi), eligible_for_synthetic_comparison=available,
                           lower_sale_price_by_monthly_rate=comparison, results=results))
    require([len(row["eligible_for_synthetic_comparison"]) for row in shocks] == [0, 1, 2, 2],
            "Valuation shocks did not reproduce the declared availability states")

    spec = json.loads(reference.capacity_spec_raw)
    value_to_noi = amount(spec["parameters"]["cap_rate"]) / amount(spec["parameters"]["maximum_ltv"])
    boundaries = {}
    for key, parent in parents.items():
        principal = amount(parent.capacity_run.payload["selected_principal"])
        minimum = principal * value_to_noi
        probes = {}
        for label, delta in (("below", -1), ("at", 0), ("above", 1)):
            probe = observe(parent, minimum + delta, f"SYNTHETIC-D37/{key}/{label}")
            require((probe["state"] == "PENDING") == (delta < 0)
                    and (Fraction(probe["capacity"]) == principal) == (delta == 0), "LTV boundary differs")
            probes[label] = probe
        boundaries[key] = dict(minimum_valuation_noi=str(minimum), probes=probes)

    tie = amount(reference.capacity_run.payload["capacity_limits"]["DSCR"]) * value_to_noi
    tie_cases = {}
    for label, delta, limits in (("below", Fraction(-1, 100), ["LTV"]), ("at", 0, ["DSCR", "LTV"]),
                                 ("above", Fraction(1, 100), ["DSCR"])):
        probe = observe(parents[HIGH], tie + delta, f"SYNTHETIC-D37/tie/{label}")
        require(probe["binding_limits"] == limits, "DSCR and LTV tie differs")
        tie_cases[label] = probe
    stale = observe(parents[LOW], Fraction(30), "SYNTHETIC-D37/stale-valuation", stale_valuation=True)
    require(stale["state"] == "PENDING" and stale["blockers"] == [VALUATION_BLOCKER], "Stale valuation control failed")
    return dict(status="passed", scope="synthetic_valuation_and_bank_capacity", currency="USD", decision="PENDING",
                bank_noi=str(amount(reference.capacity_run.payload["bank_noi"])), valuation_cases=shocks,
                capacity_boundaries=boundaries, binding_limit_tie=dict(valuation_noi=str(tie), probes=tie_cases),
                stale_valuation_control=stale, deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    return dict(status=report["status"], decision=report["decision"], ltv_capacity_sha256=digest(canonical(report)),
                eligible_counts=[len(row["eligible_for_synthetic_comparison"]) for row in report["valuation_cases"]],
                capacity_probes=sum(len(row["probes"]) for row in report["capacity_boundaries"].values()),
                tie_probes=len(report["binding_limit_tie"]["probes"]),
                stale_valuation_state=report["stale_valuation_control"]["state"])


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
