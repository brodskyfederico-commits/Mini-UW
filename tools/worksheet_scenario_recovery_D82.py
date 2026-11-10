"""Bind the USD 10 investor comparison to the exact nominal recovery prices."""
from fractions import Fraction
from math import ceil
import json

from check_integrated_participation_D28 import TERMS
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_joint_exit_D32 import load_sources
from check_sale_cash_recovery_D33 import BINDINGS, OFFSETS, check_probe, replay_targets
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_investor_scenarios_D75 import build_scenarios, render_comparison


def fixed_sale_terms(sale):
    return {key: value for key, value in sale.items() if key not in ("revision_id", "replacement_claims")} | {
        "replacement_claims": {key: {field: value for field, value in claim.items() if field != "source_ref"}
                               for key, claim in sale["replacement_claims"].items() if key != "gross_proceeds"}}


def build_recovery(case, case_sha256):
    raw = local_file(ROOT, BINDINGS).read_bytes()
    require(case.get("nominal_recovery_source_sha256") == sha(raw), "The nominal recovery sources differ")
    original = {key: value for key, value in case.items() if key != "nominal_recovery_source_sha256"}
    original["schema"] = "miniuw.synthetic-investor-scenarios.v1"
    result, _ = build_scenarios(original, case_sha256)

    fixture = json.loads(raw)
    terms = json.loads(local_file(ROOT, TERMS).read_bytes())
    require(fixture["joint_matrix_sha256"] == case["joint_exit_sha256"]
            and fixture["allocation_terms_sha256"] == case["allocation_terms_sha256"],
            "Recovery and scenario terms bind different sources")
    _, sales, _, _ = load_sources()
    sales = {row["revision_id"]: row for row in sales}
    anchor = "SYNTHETIC-sale-0"
    groups = {}
    for name, view in result["scenarios"].items():
        refi, sale_id = view["archive_case"].split("/")
        require(fixed_sale_terms(sales[sale_id]) == fixed_sale_terms(sales[anchor]),
                "The scenario has a different sale cost or funding structure")
        groups[name] = f"{refi}/{anchor}"
    targets = replay_targets(fixture, groups=set(groups.values()))
    require(targets.keys() == set(groups.values()), "The recovery target inventory differs")

    recovery = {}
    for name, group in groups.items():
        row, probes = targets[group]
        cash = result["scenarios"][name]["cash"]
        require(set(probes) == set(OFFSETS) and amount(cash["initial_capital"]) == 10,
                "Missing capacity-cleared recovery probes or USD 10 basis")
        target = Fraction(row["cash_recovery_sale_price"])
        gross = Fraction(result["scenarios"][name]["gross_sale_proceeds"])
        project_initial = amount(probes["at"][1]["story"]["cash_by_category"]["initial_capital"])
        factor = Fraction(10) / project_initial
        sale = sum(amount(e["amount"]) for e in cash["events"] if e["category"] == "net_sale_distribution")
        contributions = amount(cash["gross_contributions"])
        needed = max(0, contributions - (amount(cash["gross_distributions"]) - sale))
        require(not any(amount(e["amount"]) for e in cash["events"] if e["category"] == "additional_capital")
                and (gross - target) * factor == amount(cash["net_cash_profit"]) == sale - needed,
                "Gross and net cash recovery do not reconcile to the dated scenario")
        verified = {}
        for label, (price, parent) in probes.items():
            check = check_probe(terms, price, parent, fixture["probe_ledgers"][f"{group}/{label}"], OFFSETS[label])
            require(Fraction(check["project_net_cash"]) == OFFSETS[label], "Recovery probe differs")
            verified[label] = {"gross_sale_price": rational(price),
                               "net_cash_per_usd_10": rational(OFFSETS[label] * factor)}
        recovery[name] = dict(minimum_net_receipt_per_usd_10=rational(needed),
                              current_net_sale_receipt_per_usd_10=rational(sale),
                              minimum_gross_price_exact=rational(target),
                              minimum_gross_price_at_cents=rational(Fraction(ceil(target * 100), 100)),
                              price_probes=verified, sale_scope="synthetic_fixed_costs_and_other_cash",
                              recovery_basis="nominal_dated_cash_without_discounting")
    pdf = render_comparison(result["scenarios"], recovery)
    return result | dict(nominal_sale_recovery=recovery, nominal_recovery_source_sha256=sha(raw),
                         pdf_sha256=sha(pdf)), pdf
