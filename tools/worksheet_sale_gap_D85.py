"""Compare verified net sale cash to the minimum at each discount rate."""
from datetime import date

from check_operating_replay_D20 import amount, require
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_investor_scenarios_D75 import SCENARIOS
from worksheet_sale_rate_grid_D84 import build_rate_grid, money, render_grid


def sale_cash(view):
    return sum(amount(event["amount"]) for event in view["cash"]["events"]
               if event["category"] == "net_sale_distribution")


def gap_label(gap):
    if gap == 0:
        return "justo 0,00"
    return ("sobran " if gap > 0 else "faltan ") + money(rational(abs(gap)))


def build_sale_gap(case, case_sha256):
    result, _ = build_rate_grid(case | {"schema": "miniuw.synthetic-investor-scenarios.v4"}, case_sha256)
    sensitivity = result["rate_sensitivity"]
    views = result["scenarios"]
    dates = [sensitivity["discount_date"], sensitivity["sale_date"]]
    start, end = map(date.fromisoformat, dates)
    require(start.day == end.day and start < end, "The sale date differs from the monthly cash grid")
    months = (end.year - start.year) * 12 + end.month - start.month
    received = {name: sale_cash(views[name]) for name in SCENARIOS}
    received_text = " | ".join(f"{name} USD {money(rational(received[name]))}" for name in SCENARIOS)
    lines = [(f"La venta del escenario deja por USD 10 | {received_text}", True),
             ("Tasa mensual | Mínimo neto y cuánto sobra o falta el día de venta (USD)", True)]
    rows = []
    for row in sensitivity["monthly_rates"]:
        rate = amount(row["rate"])
        comparisons = {}
        fields = []
        for name in SCENARIOS:
            verified = row["scenarios"][name]
            minimum = amount(verified["net_at_sale_cents"])
            exact = amount(verified["net_at_sale_exact"])
            gap = received[name] - minimum
            exact_gap = received[name] - exact
            require(exact <= minimum and exact_gap / (1 + rate)**months == amount(verified["current_net_present_value"]),
                    "Sale cash did not reconcile to the independently verified discounted flows")
            comparisons[name] = dict(net_sale_received=rational(received[name]),
                                     minimum_net_sale_at_cents=rational(minimum),
                                     cash_difference_at_sale=rational(gap),
                                     difference_against_exact_minimum=rational(exact_gap),
                                     state="surplus" if gap > 0 else "shortfall" if gap < 0 else "break_even")
            fields.append(f"{name} {money(rational(minimum))}, {gap_label(gap)}")
        label = money(rational(rate * 100))
        lines.append((f"{label}% | " + " | ".join(fields), True))
        rows.append(dict(monthly_rate=row["rate"], scenarios=comparisons))
    pdf = render_grid(views, sensitivity["monthly_rates"], dates, gap=lines)
    return result | dict(sale_cash_comparison=dict(unit="USD per USD 10 initial equity at sale",
                                                  minimum_basis="minimum net receipt rounded up to cents",
                                                  sale_date=dates[-1], discount_date=dates[0], monthly_rates=rows),
                         pdf_sha256=sha(pdf)), pdf
