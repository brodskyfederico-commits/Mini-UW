"""Sale recovery for the selected-rate revised-plan worksheet profile."""
from decimal import Decimal, localcontext
from fractions import Fraction

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import amount, require
from compare_refinance_discount_D111 import month_offset, monthly_flows
from miniuw_foundation.debt_service import rational
from plan_return_D107 import SALE_DATE
from worksheet_discounted_recovery_D83 import cents_up
from worksheet_sale_rate_grid_D84 import money


def sale_recovery(view, rate):
    amounts = view["amounts"]
    basis = view["sale_basis"]
    gross = amount(basis["gross_price"])
    payoff = amount(basis["debt_principal_paid_at_sale"])
    fee = amount(basis["sale_cost_rate"])
    scale = amount(basis["initial_equity_scale"])
    require(gross >= 0 and payoff >= 0 and 0 <= fee < 1 and scale > 0,
            "An explicit nonnegative price and payoff, a valid sale-cost rate and positive equity basis are required")

    def net_receipt(price):
        return (price * (1 - fee) - payoff) * scale

    def pv_at_sale_price(price):
        new_receipt = net_receipt(price)
        adjusted = amounts | {"net_sale_distribution": rational(new_receipt)}
        return present_value(monthly_flows(adjusted), rate)

    discount = (1 + rate) ** -month_offset(SALE_DATE)
    current_npv = amount(view["npv_per_usd_10"])
    current_net = amount(amounts["net_sale_distribution"])
    require(current_net == net_receipt(gross) and current_npv == pv_at_sale_price(gross),
            "The verified net sale does not reconcile to gross price, proportional costs and payoff")
    minimum_net = current_net - current_npv / discount
    require(minimum_net > 0, "This sale recovery profile requires a positive net receipt at sale")
    exact = (minimum_net / scale + payoff) / (1 - fee)
    at_cents = amount(cents_up(exact))
    below = at_cents - Fraction(1, 100)
    require(pv_at_sale_price(exact) == 0 and below < exact <= at_cents
            and pv_at_sale_price(below) < 0 <= pv_at_sale_price(at_cents),
            "The minimum sale price failed its exact and adjacent-cent checks")
    return dict(state="computed_synthetic", sale_date=SALE_DATE,
                minimum_net_sale_per_usd_10=rational(minimum_net),
                minimum_net_sale_per_usd_10_at_cents=cents_up(minimum_net),
                minimum_gross_sale_exact=rational(exact),
                minimum_gross_sale_at_cents=rational(at_cents),
                gross_gap_to_minimum=rational(at_cents - gross),
                net_present_value_at_minimum_gross_cents=rational(pv_at_sale_price(at_cents)),
                net_present_value_one_cent_below=rational(pv_at_sale_price(below)),
                basis="fixed_dated_cash_and_payoff_with_proportional_sale_cost")


def add_sale_recovery(scenarios, rate):
    for scenario in scenarios.values():
        for view in scenario["alternatives"].values():
            view["sale_recovery"] = None if view["amounts"] is None else sale_recovery(view, rate)


def compact_money(value, *, group=False):
    displayed = money(value)
    if group:
        whole, cents = displayed.split(",")
        displayed = f"{int(whole):,}".replace(",", ".") + "," + cents
    if len(displayed) <= 12:
        return displayed
    exact = amount(value)
    with localcontext() as ctx:
        ctx.prec = 16
        decimal = Decimal(exact.numerator) / Decimal(exact.denominator)
        return f"{decimal:.3E}".replace(".", ",")


def recovery_lines(columns, width):
    rows = [
        ("Neto de venta mínimo por USD 10", "minimum_net_sale_per_usd_10_at_cents", False),
        ("Venta bruta mínima del proyecto (USD)", "minimum_gross_sale_at_cents", True),
    ]
    lines = [("PARA RECUPERAR LO APORTADO EN VALOR PRESENTE  /  VENTA DEL 30/06/2028", True)]
    for label, key, group in rows:
        cells = ["PENDING" if view["sale_recovery"] is None else compact_money(view["sale_recovery"][key], group=group)
                 for view in columns]
        lines.append((f"{label:<40}" + "".join(f"{value:>{width}}" for value in cells), True))
    lines.append(("Costos de venta sobre el precio y saldo de deuda fijo. Mínimos redondeados hacia arriba.", False))
    return lines
