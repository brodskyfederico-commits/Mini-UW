"""Find the construction cuts required at declared Downside sale prices."""

from datetime import date
from fractions import Fraction
from functools import cache
from hashlib import sha256
import json

from check_reference_package import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import publish_current_pdf, require_pdf_destination
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import ROUTES, audited_annual_comparison
from worksheet_annual_crossover_construction import (construction_at_cut, minimum_construction_cut, normalized_route,
                                                       reprice_route, require_monotone_funding)
from worksheet_annual_crossover_sale_price import accumulated_balance_bounds, display_money
from worksheet_annual_discount_crossover import crossover_by_scenario, monthly_flows, shown_rate
from worksheet_annual_route_report import usd


SALE_PRICES = (4_000_000, 5_000_000, 6_000_000)


def cash_with_sale_price(route, price, commission):
    gross = amount(route["sale"]["gross"])
    cost = amount(route["sale"]["cost"])
    require(0 <= commission < 1 and price >= gross and cost >= gross * commission,
            "El precio o la comisión no concilia con el cierre de D238")
    initial = next(row for row in route["cash_by_period"] if row["stage"] == "construction")
    scale = 10 / amount(initial["contribution"])
    extra = (price - gross) * (1 - commission) * scale
    annual = normalized_route(route)
    cash = annual["cash_per_usd_10"]
    events = cash["events"]
    sale_event, = [row for row in events if row["stage"] == "sale"]
    require(sale_event["date"] == annual["sale_date"], "El flujo de venta no coincide con el cierre de D238")
    paid = amount(cash["received"]) + extra
    adjusted = cash | dict(
        events=[row | {"receipt": rational(amount(row["receipt"]) + extra)} if row is sale_event else row for row in events],
        received=rational(paid), unrecovered=rational(max(0, 10 + amount(cash["additional"]) - paid)),
    )
    return annual | {"cash_per_usd_10": adjusted}


def downside_fixed_price_cuts(model, inputs, table, labels):
    name = "Downside"
    view = model["scenarios"][name]
    original_direct = amount(view["construction_budget"]["direct_hard_cost"])
    original_budget = amount(view["construction_budget"]["total_development_cost"])
    commission = amount(view["valuation_and_sale"]["sale_cost_fraction"])
    cross = crossover_by_scenario(table, width=Fraction(1, 10**14))[name]
    rates = tuple(amount(cross[key]) for key in ("monthly_rate_lower", "monthly_rate_upper"))
    purchase = date.fromisoformat(cross["purchase_date"])
    originals = model["calendar_checks"][name]

    @cache
    def funding_at(cut):
        return construction_at_cut(model, inputs, name, cut)

    require_monotone_funding(funding_at(Fraction())[1], funding_at(original_direct)[1])
    for label, (caption, _, _) in zip(labels, ROUTES, strict=True):
        baseline = originals[label]
        terms = inputs["calendar_checks"][name][label]
        require(reprice_route(view, terms, baseline, funding_at(Fraction())[1]) == baseline
                and baseline["cash_per_usd_10"] == table[name, caption]["cash_per_usd_10"],
                "La corrida sin sensibilidad no reproduce D238")

    rows = []
    for price in SALE_PRICES:
        paths = {}
        for label, (caption, _, _) in zip(labels, ROUTES, strict=True):
            baseline = originals[label]
            terms = inputs["calendar_checks"][name][label]

            def evaluate(cut):
                trial_budget, funding = funding_at(cut)
                trial = reprice_route(view, terms, baseline, funding)
                repriced = cash_with_sale_price(trial, price, commission)
                bounds = accumulated_balance_bounds(monthly_flows(repriced, purchase), rates)
                return bounds, (repriced["cash_per_usd_10"], trial_budget)

            cut, bounds, below_upper, (cash, budget) = minimum_construction_cut(original_direct, evaluate)
            paths[caption] = dict(
                minimum_direct_cut=None if cut is None else rational(cut),
                tested_direct_cost=budget["direct_hard_cost"],
                tested_budget_savings=rational(original_budget - amount(budget["total_development_cost"])),
                tested_cash_per_10=cash,
                tested_terminal_bounds=dict(lower=rational(bounds[0]), upper=rational(bounds[1])),
                one_cent_less_terminal_upper=None if below_upper is None else rational(below_upper),
                original_cash_sha256=table[name, caption]["cash_sha256"],
            )
        rows.append(dict(gross_sale=rational(price), paths=paths))
    return dict(cross=cross, original_direct=rational(original_direct), sale_cost_fraction=rational(commission),
                original_gross_sale=originals[labels[0]]["sale"]["gross"], rows=rows)


def render_cuts(revision, result):
    cross = result["cross"]
    direct = amount(result["original_direct"])
    captions = [route[0] for route in ROUTES]
    lines = [
        ("Ensayo sintético Downside | 1101 real y retorno histórico PENDING", True),
        (f"Tasa de cruce original {shown_rate(cross)} mensual | Obra directa D238 USD {display_money(result['original_direct'])}", False),
        (f"Comisión de venta {usd(100 * amount(result['sale_cost_fraction']))}% | Venta para ambas rutas el {cross['sale_date']}", False),
        ("El recorte reduce obra vertical, estacionamiento y sitio. Se recalculan indirectos y deuda de obra.", False),
        ("", False),
        ("Recorte mínimo para recuperar todos los aportes por USD 10 en valor presente", True),
        (f"{'Venta bruta (USD)':22} | {'Con refi (USD y %)':^36} | {'Sin refi (USD y %)':^36}", True),
    ]
    for row in result["rows"]:
        cells = []
        for caption in captions:
            cut = row["paths"][caption]["minimum_direct_cut"]
            if cut is None:
                cells.append("Inalcanzable con obra en cero")
            else:
                cells.append(f"{display_money(cut)} ({usd(100 * amount(cut) / direct)}%)")
        lines.append((f"{display_money(row['gross_sale']):22} | " + " | ".join(f"{cell:>36}" for cell in cells), False))
    lines.extend([
        ("", False),
        ("Por USD 10 iniciales al recorte probado | Aporte adicional / Cobro total nominal", True),
        (f"{'Venta bruta (USD)':22} | {'Con refi':^36} | {'Sin refi':^36}", True),
    ])
    for row in result["rows"]:
        cash = [row["paths"][caption]["tested_cash_per_10"] for caption in captions]
        cells = [f"{display_money(path['additional'])} / {display_money(path['received'])}" for path in cash]
        lines.append((f"{display_money(row['gross_sale']):22} | " + " | ".join(f"{cell:>36}" for cell in cells), False))
    lines.extend([
        ("", False),
        (f"Refi el {cross['refinance_date']} en la ruta que aplica. Los cobros incluyen operación y venta neta.", False),
        ("Cada mínimo se verificó al centavo para todo el intervalo que contiene la tasa de cruce.", False),
    ])
    return render_page(revision, lines, 17, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "D243 | Recorte de obra requerido con precios de venta fijos en Downside")


def deliver_downside_fixed_sale_construction(directory, output, current_revision, labels):
    require_pdf_destination(directory, output, current_revision)
    files, revision, case_revision, table = audited_annual_comparison(directory, current_revision, labels)
    model = json.loads(files["results.json"])
    inputs = json.loads(files["case.json"])["rent_inputs"]
    result = downside_fixed_price_cuts(model, inputs, table, labels)
    pdf = render_cuts(case_revision, result)
    publish_current_pdf(directory, files, current_revision, revision, output, pdf)
    return dict(decision="PENDING", current_revision=case_revision, page_count=1,
                revision_sha256=sha256(revision).hexdigest(), source_results_sha256=sha256(files["results.json"]).hexdigest(),
                pdf_sha256=sha256(pdf).hexdigest(), downside=result)
