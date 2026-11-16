"""Evaluate both Downside cash balances at the fixed USD 6M sale and 50% cut."""

from datetime import date
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json

from check_discounted_sale_recovery_D34 import present_value
from check_reference_package import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import publish_current_pdf, require_pdf_destination
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import ROUTES, audited_annual_comparison
from worksheet_annual_crossover_construction import construction_at_cut, reprice_route
from worksheet_annual_crossover_sale_price import accumulated_balance_bounds, display_money
from worksheet_annual_discount_crossover import crossover_by_scenario, exact_rows, monthly_flows, shown_rate
from worksheet_annual_route_report import dated_lines
from worksheet_downside_fixed_sale_construction import cash_with_sale_price


GROSS_SALE = 6_000_000
COST_CUT = Fraction(1, 2)


def downside_fixed_balance(model, inputs, table, labels):
    name = "Downside"
    view = model["scenarios"][name]
    direct = amount(view["construction_budget"]["direct_hard_cost"])
    commission = amount(view["valuation_and_sale"]["sale_cost_fraction"])
    cross = crossover_by_scenario(table, width=Fraction(1, 10**14))[name]
    rates = tuple(amount(cross[key]) for key in ("monthly_rate_lower", "monthly_rate_upper"))
    purchase = date.fromisoformat(cross["purchase_date"])
    originals = model["calendar_checks"][name]
    base_budget, base_funding = construction_at_cut(model, inputs, name, Fraction())
    cut = direct * COST_CUT
    budget, funding = construction_at_cut(model, inputs, name, cut)
    paths = {}
    for label, (caption, _, _) in zip(labels, ROUTES, strict=True):
        baseline = originals[label]
        terms = inputs["calendar_checks"][name][label]
        require(reprice_route(view, terms, baseline, base_funding) == baseline, "La corrida base no reproduce D238")
        trial = reprice_route(view, terms, baseline, funding)
        repriced = cash_with_sale_price(trial, GROSS_SALE, commission)
        flows = monthly_flows(repriced, purchase)
        low, high = accumulated_balance_bounds(flows, rates)
        require(high < 0 or low > 0 or low == high == 0, "La precisión de la tasa no permite clasificar el saldo")
        paths[caption] = repriced | dict(
            original_cash_sha256=table[name, caption]["cash_sha256"],
            van_per_10=rational(present_value(exact_rows(flows), sum(rates) / 2)),
            terminal_bounds=dict(lower=rational(low), upper=rational(high)),
        )
    return dict(
        cross=cross, gross_sale=rational(GROSS_SALE), cut_ratio=rational(COST_CUT),
        direct_cut=rational(cut), tested_direct_cost=budget["direct_hard_cost"],
        budget_savings=rational(amount(base_budget["total_development_cost"]) - amount(budget["total_development_cost"])),
        sale_cost_fraction=rational(commission), paths=paths,
    )


def balance_money(value):
    net = amount(value)
    return f"{Decimal(net.numerator) / Decimal(net.denominator):+.4f}".replace(".", ",")


def render_balance(revision, result):
    paths = result["paths"]
    names = ("Con refi", "Sin refi")
    lines = [
        ("Ensayo sintético Downside | 1101 real y retorno histórico PENDING", True),
        (f"Venta bruta USD {display_money(result['gross_sale'])} | Reducción de obra directa "
         f"{int(amount(result['cut_ratio']) * 100)}% | {shown_rate(result['cross'])} mensual", False),
        ("Importes por USD 10 de equity inicial. VAN al día del primer aporte.", False),
        ("", False),
    ]
    for name in names:
        path = paths[name]
        cash = path["cash_per_usd_10"]
        lines.append((f"{name} | VAN USD {balance_money(path['van_per_10'])}"
                      f" | Aporte adicional USD {display_money(cash['additional'])}"
                      f" | Cobro total USD {display_money(cash['received'])}", True))
    lines.extend([("", False), *dated_lines(paths, names), ("", False)])
    fee = display_money(rational(100 * amount(result["sale_cost_fraction"])))
    lines.append((f"Comisión de venta {fee}%. Los saldos de deuda se concilian en cada ruta.", False))
    return render_page(revision, lines, 13, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "D244 | Saldo de Downside con venta en USD 6 millones y recorte del 50%")


def deliver_downside_fixed_sale_balance(directory, output, current_revision, labels):
    require_pdf_destination(directory, output, current_revision)
    files, revision, case_revision, table = audited_annual_comparison(directory, current_revision, labels)
    model = json.loads(files["results.json"])
    inputs = json.loads(files["case.json"])["rent_inputs"]
    result = downside_fixed_balance(model, inputs, table, labels)
    pdf = render_balance(case_revision, result)
    publish_current_pdf(directory, files, current_revision, revision, output, pdf)
    return dict(decision="PENDING", current_revision=case_revision, page_count=1,
                revision_sha256=sha256(revision).hexdigest(), source_results_sha256=sha256(files["results.json"]).hexdigest(),
                pdf_sha256=sha256(pdf).hexdigest(), downside=result)
