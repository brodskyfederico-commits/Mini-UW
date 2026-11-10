"""Discount the USD 10 dated cash and verify the sale threshold against D34."""
from fractions import Fraction
from functools import partial
from math import ceil
import json

from check_discounted_sale_recovery_D34 import BINDINGS, check_probe, load_case, samples, validate_grid
from check_integrated_participation_D28 import TERMS
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_sale_cash_recovery_D33 import OFFSETS, replay_targets
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_investor_scenarios_D75 import render_comparison
from worksheet_scenario_recovery_D82 import build_recovery


def cents_up(value):
    return rational(Fraction(ceil(value * 100), 100))


def build_discounted_recovery(case, case_sha256):
    raw = local_file(ROOT, BINDINGS).read_bytes()
    require(case.get("discounted_recovery_source_sha256") == sha(raw), "Discounted recovery source differs")
    fixture = json.loads(raw)
    nominal, rate = load_case(fixture)
    require(case.get("monthly_discount_rate") == fixture["monthly_discount_rate"]
            and case.get("nominal_recovery_source_sha256") == fixture["nominal_bindings_sha256"]
            and case.get("allocation_terms_sha256") == fixture["allocation_terms_sha256"],
            "An exact rate and the same recovery sources are required")
    previous = {k: v for k, v in case.items()
                if k not in ("monthly_discount_rate", "discounted_recovery_source_sha256")}
    previous["schema"] = "miniuw.synthetic-investor-scenarios.v2"
    result, _ = build_recovery(previous, case_sha256)

    terms = json.loads(local_file(ROOT, TERMS).read_bytes())
    groups = {name: view["archive_case"].split("/")[0] + "/SYNTHETIC-sale-0"
              for name, view in result["scenarios"].items()}
    targets = replay_targets(nominal, sample_prices=partial(samples, monthly_rate=rate),
                             groups=set(groups.values()))
    require(targets.keys() == set(groups.values()), "The discounted targets differ")
    recovery = {}
    for name, group in groups.items():
        row, probes = targets[group]
        view = result["scenarios"][name]
        cash = view["cash"]
        require(set(probes) == set(OFFSETS) and amount(cash["initial_capital"]) == 10,
                "Expected capacity-cleared PV probes and exactly USD 10 of initial capital")
        center = probes["at"]
        dates = [flow["date"] for flow in validate_grid(center["parent"])]
        periods = {when: n for n, when in enumerate(dates)}
        discounts = {when: (1 + rate) ** -n for when, n in periods.items()}
        require({e["date"] for e in cash["events"]} <= periods.keys()
                and all(e["date"] == dates[0] for e in cash["events"] if e["category"] == "initial_capital")
                and all(e["date"] == dates[-1] for e in cash["events"] if e["category"] == "net_sale_distribution"),
                "The investor events differ from the verified discount dates")
        pre_sale_pv = sum((1 if e["kind"] == "distribution" else -1)
                          * amount(e["amount"]) * discounts[e["date"]]
                          for e in cash["events"] if e["category"] != "net_sale_distribution")
        sale_discount = discounts[dates[-1]]
        needed_pv = max(Fraction(), -pre_sale_pv)
        needed_at_sale = needed_pv / sale_discount
        original = result["nominal_sale_recovery"][name]
        current_sale = amount(original["current_net_sale_receipt_per_usd_10"])
        target = Fraction(row["cash_recovery_sale_price"])
        gross = Fraction(view["gross_sale_proceeds"])
        initial = amount(center["parent"]["story"]["cash_by_category"]["initial_capital"])
        scale = Fraction(10) / initial
        require((target - gross) * scale == needed_at_sale - current_sale
                and center["nominal_price"] == amount(original["minimum_gross_price_exact"]),
                "The dated USD 10 cash and the replayed gross price differ")
        verified = {}
        for label, probe in probes.items():
            checked = check_probe(terms, probe, fixture["probe_ledgers"][f"{group}/{label}"], rate)
            value = Fraction(checked["project_present_value"]) * scale
            require(value == OFFSETS[label] * scale * sale_discount, "The discounted USD 10 probe differs")
            verified[label] = dict(gross_sale_price=rational(probe["price"]), net_present_value_per_usd_10=rational(value))
        recovery[name] = dict(discount_date=dates[0], sale_date=dates[-1], months_to_sale=len(dates) - 1,
                              minimum_net_receipt_at_sale_exact=rational(needed_at_sale),
                              minimum_net_receipt_at_sale_cents=cents_up(needed_at_sale),
                              minimum_net_receipt_present_value=rational(needed_pv),
                              current_net_present_value=rational(pre_sale_pv + current_sale * sale_discount),
                              minimum_gross_price_exact=rational(target),
                              minimum_gross_price_at_cents=cents_up(target), price_probes=verified)
    require(len({(r["discount_date"], r["sale_date"]) for r in recovery.values()}) == 1,
            "The comparison needs the same discount and sale dates")
    discounted = dict(monthly_rate=rational(rate), monthly_rate_percent=rational(rate * 100),
                      discount_date=next(iter(recovery.values()))["discount_date"],
                      source_sha256=sha(raw), scenarios=recovery)
    pdf = render_comparison(result["scenarios"], discounted=discounted)
    return result | dict(discounted_sale_recovery=discounted, pdf_sha256=sha(pdf)), pdf
