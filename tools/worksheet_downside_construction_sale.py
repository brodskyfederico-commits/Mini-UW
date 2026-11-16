"""Find the Downside sale prices that complement each direct construction cut."""

from fractions import Fraction
from hashlib import sha256
import json

from check_reference_package import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import encode
from miniuw_worksheet_v1 import publish_current_pdf, require_pdf_destination
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import ROUTES, audited_annual_comparison
from worksheet_annual_crossover_construction import construction_at_cut, normalized_route, reprice_route
from worksheet_annual_crossover_sale_price import certified_sale_price, display_money
from worksheet_annual_discount_crossover import crossover_by_scenario, shown_rate
from worksheet_annual_route_report import usd


CUTS = tuple(Fraction(value, 4) for value in range(5))


def downside_combinations(model, inputs, table, labels):
    name = "Downside"
    view = model["scenarios"][name]
    cross = crossover_by_scenario(table, width=Fraction(1, 10**14))[name]
    source_routes = model["calendar_checks"][name]
    original_budget = view["construction_budget"]
    original_direct = amount(original_budget["direct_hard_cost"])
    original_price = source_routes[labels[0]]["sale"]["gross"]
    rows = []
    for ratio in CUTS:
        cut = original_direct * ratio
        budget, funding = construction_at_cut(model, inputs, name, cut)
        paths = {}
        for label, (caption, _, _) in zip(labels, ROUTES, strict=True):
            original = source_routes[label]
            adjusted = reprice_route(view, inputs["calendar_checks"][name][label], original, funding)
            annual = normalized_route(adjusted)
            cash = annual["cash_per_usd_10"]
            annual["cash_sha256"] = sha256(encode(cash)).hexdigest()
            if ratio == 0:
                require(adjusted == original and annual["cash_sha256"] == table[name, caption]["cash_sha256"],
                        "La combinación sin recorte no reproduce D238")
            threshold = certified_sale_price(adjusted, annual, view["valuation_and_sale"], cross)
            paths[caption] = dict(
                price=threshold, dated_cash_at_original_price=cash,
                total_received_per_10_at_minimum=rational(amount(cash["received"]) + amount(threshold["net_sale_increase_per_10"])),
            )
        rows.append(dict(cut_ratio=rational(ratio), direct_cut=rational(cut), tested_direct_cost=budget["direct_hard_cost"],
                         construction_principal=funding["construction_principal_payoff"], paths=paths))
    return dict(cross=cross, original_direct=rational(original_direct), original_gross_sale=original_price, rows=rows)


def render_combinations(revision, result):
    cross = result["cross"]
    captions = [route[0] for route in ROUTES]
    commission = amount(result["rows"][0]["paths"]["Con refi"]["price"]["sale_cost_fraction"])
    lines = [
        ("Ensayo sintético Downside | 1101 real y retorno histórico PENDING", True),
        (f"Tasa de cruce original {shown_rate(cross)} mensual | Obra directa D238 USD {display_money(result['original_direct'])}", False),
        (f"Venta D238 USD {display_money(result['original_gross_sale'])} | Comisión de venta {usd(100 * commission)}%", False),
        ("El recorte reduce obra vertical, estacionamiento y sitio. Se recalculan indirectos y deuda de obra.", False),
        ("", False),
        ("Precio bruto mínimo para recuperar todos los aportes por USD 10 en valor presente", True),
        (f"{'Recorte directo':31} | {'Con refi (subida)':^30} | {'Sin refi (subida)':^30}", True),
    ]
    for row in result["rows"]:
        cut = f"{int(amount(row['cut_ratio']) * 100)}% / USD {display_money(row['direct_cut'])}"
        cells = []
        for caption in captions:
            path = row["paths"][caption]["price"]
            cells.append(f"{display_money(path['minimum_gross_at_cents'])} (+{usd(100 * amount(path['gross_increase_ratio']))}%)")
        lines.append((f"{cut:31} | " + " | ".join(f"{cell:>30}" for cell in cells), False))
    lines.extend([
        ("", False),
        ("Caja nominal al precio mínimo por USD 10 iniciales | Aporte adicional / Cobro total", True),
        (f"{'Recorte directo':31} | {'Con refi':^30} | {'Sin refi':^30}", True),
    ])
    for row in result["rows"]:
        cells = []
        for caption in captions:
            path = row["paths"][caption]
            cells.append(f"{display_money(path['dated_cash_at_original_price']['additional'])} / "
                         f"{display_money(path['total_received_per_10_at_minimum'])}")
        lines.append((f"{int(amount(row['cut_ratio']) * 100):>3}%{'':27} | " + " | ".join(f"{cell:>30}" for cell in cells), False))
    lines.extend([
        ("", False),
        (f"Refi el {cross['refinance_date']} en la ruta que aplica. Venta para ambas el {cross['sale_date']}.", False),
        ("El cobro total incluye operación, refi cuando aplica y venta neta. Cada mínimo se verificó al centavo.", False),
    ])
    return render_page(revision, lines, 16.5, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "D242 | Downside con recortes de obra y mayor precio de venta")


def deliver_downside_construction_sale(directory, output, current_revision, labels):
    require_pdf_destination(directory, output, current_revision)
    files, revision, case_revision, table = audited_annual_comparison(directory, current_revision, labels)
    model = json.loads(files["results.json"])
    inputs = json.loads(files["case.json"])["rent_inputs"]
    result = downside_combinations(model, inputs, table, labels)
    pdf = render_combinations(case_revision, result)
    publish_current_pdf(directory, files, current_revision, revision, output, pdf)
    return dict(decision="PENDING", current_revision=case_revision, page_count=1,
                revision_sha256=sha256(revision).hexdigest(), source_results_sha256=sha256(files["results.json"]).hexdigest(),
                pdf_sha256=sha256(pdf).hexdigest(), downside=result)
