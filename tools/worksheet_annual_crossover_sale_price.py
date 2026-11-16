"""Certify the gross sale price that recovers project cash at each monthly crossover."""

from datetime import date
from fractions import Fraction
from hashlib import sha256
import json

from check_reference_package import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import SCENARIOS
from miniuw_worksheet_v1 import publish_current_pdf, require_pdf_destination
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import ROUTES, audited_annual_comparison
from worksheet_annual_discount_crossover import crossover_by_scenario, monthly_flows, shown_rate
from worksheet_annual_route_report import usd
from worksheet_discounted_recovery_D83 import cents_up


def accumulated_balance_bounds(flows, rates):
    """Bound terminal-value cash for every rate in the exact crossover bracket."""
    low = high = Fraction()
    for index, flow in enumerate(flows):
        months_to_sale = len(flows) - 1 - index
        endpoints = [flow * (1 + rate) ** months_to_sale for rate in rates]
        low += min(endpoints)
        high += max(endpoints)
    return low, high


def certified_sale_price(route, annual, valuation, cross):
    sale = route["sale"]
    gross, cost, payoff = (amount(sale[key]) for key in ("gross", "cost", "principal_paid"))
    commission = amount(valuation["sale_cost_fraction"])
    require(None not in (gross, cost, payoff, commission) and 0 < gross and 0 <= commission < 1,
            "Precio o costo marginal de venta PENDING")
    fixed = cost - gross * commission
    require(fixed >= 0, "Los costos de venta no concilian con la comisión documentada")
    purchase = date.fromisoformat(cross["purchase_date"])
    initial = next(row for row in route["cash_by_period"] if row["stage"] == "construction")
    final, = [row for row in route["cash_by_period"] if row["stage"] == "sale"]
    require(initial["date"] == purchase.isoformat() and final["date"] == annual["sale_date"] == cross["sale_date"],
            "Las fechas del aporte inicial y de venta deben coincidir con el cruce")
    scale = 10 / amount(initial["contribution"])
    released = amount(final["opening_restricted"]) - amount(final["closing_restricted"])
    unchanged_cash = amount(final["opening_free"]) + released - payoff
    proceeds = sum(amount(row["receipt"]) for row in annual["cash_per_usd_10"]["events"] if row["stage"] == "sale")
    require(proceeds == scale * (gross - cost + unchanged_cash), "El cobro de venta no concilia con el cierre auditado")

    rates = tuple(amount(cross[key]) for key in ("monthly_rate_lower", "monthly_rate_upper"))
    balance_low, balance_high = accumulated_balance_bounds(monthly_flows(annual, purchase), rates)
    slope = scale * (1 - commission)
    minimum_low = gross - balance_high / slope
    minimum_high = gross - balance_low / slope
    minimum_cents = amount(cents_up(minimum_high))
    below = minimum_cents - Fraction(1, 100)
    # The lower cent fails throughout the rate interval and the reported cent covers it.
    below_terminal_upper = balance_high + (below - gross) * slope
    minimum_terminal_lower = balance_low + (minimum_cents - gross) * slope
    require(below_terminal_upper < 0 <= minimum_terminal_lower,
            "Precio mínimo PENDING: el intervalo de la tasa no separa los dos centavos")
    increase = max(Fraction(), minimum_cents - gross)
    return dict(
        current_gross=rational(gross), minimum_gross_at_cents=rational(minimum_cents),
        gross_increase=rational(increase), gross_increase_ratio=rational(increase/gross),
        price_bounds=dict(lower=rational(minimum_low), upper=rational(minimum_high)),
        sale_cost_fraction=rational(commission), fixed_cost=rational(fixed), debt_principal_paid=rational(payoff),
        reserves_released=rational(released), current_net_sale_per_10=rational(proceeds),
        net_sale_per_10_at_minimum=rational(scale * (minimum_cents * (1 - commission) - fixed + unchanged_cash)),
        net_sale_increase_per_10=rational(increase * slope), cash_sha256=annual["cash_sha256"],
        below_terminal_upper=rational(below_terminal_upper), minimum_terminal_lower=rational(minimum_terminal_lower),
    )


def sale_prices(model, table, labels):
    cross = crossover_by_scenario(table, width=Fraction(1, 10**14))
    result = {}
    for name in SCENARIOS:
        valuation = model["scenarios"][name]["valuation_and_sale"]
        cases = model["calendar_checks"][name]
        paths = {caption: certified_sale_price(cases[label], table[name, caption], valuation, cross[name])
                 for label, (caption, _, _) in zip(labels, ROUTES, strict=True)}
        require(paths["Con refi"]["minimum_gross_at_cents"] == paths["Sin refi"]["minimum_gross_at_cents"],
                "Las dos rutas no concilian al mismo precio bruto mínimo en el cruce")
        result[name] = dict(cross=cross[name], paths=paths)
    return result


def display_money(value):
    whole, cents = usd(amount(value)).split(",")
    return f"{int(whole):,}".replace(",", ".") + "," + cents


def render_prices(case_revision, results):
    lines = [
        ("Ensayo sintético | 1101 real y retorno histórico PENDING", True),
        ("Primer precio al centavo que recupera todos los aportes en valor presente por USD 10 iniciales.", False),
        ("El precio cambia y se mantienen la fecha, los flujos previos, los saldos de deuda y las reglas de costos.", False),
        ("", False),
    ]
    for name, row in results.items():
        cross = row["cross"]
        refi, no_refi = (row["paths"][path] for path in ("Con refi", "Sin refi"))
        increase_pct = usd(100 * amount(refi["gross_increase_ratio"]))
        rate_pct = usd(100 * amount(refi["sale_cost_fraction"]))
        lines.extend([
            (f"{name} | Cruce {shown_rate(cross)} mensual | Venta {cross['sale_date']}", True),
            (f"Precio bruto D238 USD {display_money(refi['current_gross'])} -> mínimo USD "
             f"{display_money(refi['minimum_gross_at_cents'])} en ambas rutas", True),
            (f"Subida USD {display_money(refi['gross_increase'])} ({increase_pct}%)"
             f" | Comisión {rate_pct}% y costo fijo USD {display_money(refi['fixed_cost'])}", False),
            (f"Aumento del cobro neto al cierre por USD 10 iniciales: USD {display_money(refi['net_sale_increase_per_10'])}", False),
            (f"Cobro neto de venta al precio mínimo por USD 10 | Con refi {display_money(refi['net_sale_per_10_at_minimum'])}"
             f" | Sin refi {display_money(no_refi['net_sale_per_10_at_minimum'])}", False),
            ("", False),
        ])
    lines.append(("Cada mínimo se verificó al centavo en todo el intervalo que contiene la tasa de cruce.", False))
    return render_page(case_revision, lines, 17, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "D240 | Precio de venta para recuperar los aportes a la tasa mensual de cruce")


def deliver_annual_crossover_sale(directory, output, current_revision, labels):
    require_pdf_destination(directory, output, current_revision)
    files, revision, case_revision, table = audited_annual_comparison(directory, current_revision, labels)
    prices = sale_prices(json.loads(files["results.json"]), table, labels)
    pdf = render_prices(case_revision, prices)
    publish_current_pdf(directory, files, current_revision, revision, output, pdf)
    return dict(decision="PENDING", current_revision=case_revision, page_count=1,
                revision_sha256=sha256(revision).hexdigest(), source_results_sha256=sha256(files["results.json"]).hexdigest(),
                pdf_sha256=sha256(pdf).hexdigest(), scenarios=prices)
