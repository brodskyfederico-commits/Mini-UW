"""Exact conditional recovery price with fixed and price-dependent sale costs."""
from math import ceil

from check_discounted_sale_recovery_D34 import validate_grid
from check_joint_noi_discounted_returns_D41 import discounted_cash
from check_operating_replay_D20 import amount, require
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_service import rational
from miniuw_foundation.sale_costs import produce_sale_costs


def closing_cash_at_price(source, closing, price):
    price_claim = source["gross_price"] | {"value": rational(price), "source_ref": "SYNTHETIC-D64-price-probe"}
    cost = produce_sale_costs(encoded(source | {"gross_price": price_claim})).payload
    require(cost["state"] == "computed_synthetic_sale_costs", "Probe did not produce a complete cost")
    amounts = closing["amounts"]
    amounts = amounts | {
        "gross_proceeds": amounts["gross_proceeds"] | {"value": rational(price),
                                                      "source_ref": "SYNTHETIC-D64-price-probe"},
        "closing_costs_paid": amounts["closing_costs_paid"] | {
            "value": cost["total_closing_cost"], "source_ref": "SYNTHETIC-D64-replayed-probe-cost"},
    }
    result = produce_closing_cash(encoded(closing | {"amounts": amounts})).payload
    require(result["state"] == "computed_synthetic_closing"
            and amount(result["total_cash_conservation_residual"]) == 0, "Price probe closing did not reconcile")
    return (amount(result["exportable_equity_distribution"]) - amount(result["exportable_equity_contribution"]),
            amount(cost["total_closing_cost"]))


def recovery_prices(investor, compiled, closing, source, rates):
    flows = validate_grid({"story": investor, "evidence": {"grid": compiled["grid"],
                                                           "dated_net_flows": investor["dated_net_flows"]}})
    require(flows[-1]["date"] == closing["closing_date"] == source["sale_date"], "Sale date differs")
    gross = amount(source["gross_price"])
    sale_cash, _ = closing_cash_at_price(source, closing, gross)
    require(amount(flows[-1]["net"]) == sale_cash, "Replayed sale differs from the dated ledger")
    fee = sum(amount(row["value"]) for row in source["costs"]
              if row["kind"] == "percent_of_gross" and row["applicability"] == "included")
    require(0 <= fee < 1, "Positive recovery slope requires a sale cost fraction below one")
    recovery = {}
    for rate in rates:
        pv = discounted_cash(investor["events"], flows, rate)["net_present_value"]
        factor = (1 + rate) ** (1 - len(flows))
        slope = (1 - fee) * factor
        price = gross - pv / slope
        require(1 <= price <= 999, "Recovery and adjacent probes must fit the declared USD 0–1,000 domain")
        probes = {}
        for offset in (-1, 0, 1):
            probe_price = price + offset
            net, cost = closing_cash_at_price(source, closing, probe_price)
            probe_pv = pv + (net - sale_cash) * factor
            require(probe_pv == offset * slope, "Replayed discounted closing differs from the recovery boundary")
            probes[str(offset)] = dict(gross_price=str(probe_price), sale_cost=str(cost), net_present_value=str(probe_pv))
        recovery[str(rate)] = dict(minimum_gross_price=str(price), minimum_gross_price_in_cents=ceil(price * 100),
                                   cost_fraction=str(fee), discounted_cash_slope=str(slope), probes=probes)
    return recovery
