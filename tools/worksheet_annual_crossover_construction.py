"""Reprice direct construction costs with the sale price and crossover rates held fixed."""

from datetime import date
from fractions import Fraction
from hashlib import sha256
import json

from check_discounted_sale_recovery_D34 import present_value
from check_reference_package import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import SCENARIOS
from miniuw_worksheet_v1 import publish_current_pdf, require_pdf_destination
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import ROUTES, audited_annual_comparison
from worksheet_annual_crossover_sale_price import accumulated_balance_bounds, display_money
from worksheet_annual_discount_crossover import crossover_by_scenario, exact_rows, monthly_flows, shown_rate
from worksheet_annual_route_report import usd
from worksheet_calendar_routes_D199 import route_cash
from worksheet_construction_budget_D144 import construction_budget
from worksheet_construction_financing_D146 import staged_construction_financing


def construction_at_cut(model, inputs, name, cut):
    view = model["scenarios"][name]
    review = model["native_mapping_review"]["scenarios"][name]
    development = view["development_costs"]
    original_budget = view["construction_budget"]
    original_funding = view["construction_financing"]
    direct = amount(original_budget["direct_hard_cost"])
    require(0 < direct and 0 <= cut <= direct, "La reducción requiere un costo directo original positivo")
    factor = 1 - cut / direct
    adjusted = review | {"rows": [
        row | {"value": rational(amount(row["value"]) * factor)}
        if row["value_cell"].split("!")[-1] in {"C37", "C38"} else row
        for row in review["rows"]
    ]}
    cost = development | {"vertical_cost": rational(amount(development["vertical_cost"]) * factor)}
    calendar = view["project_calendar"]
    budget = construction_budget(inputs["construction_budget"], name, adjusted, cost, view["commercial_terms"],
                                 calendar=calendar)
    require(amount(budget["direct_hard_cost"]) == direct - cut, "El presupuesto no concilia la reducción de obra")
    funding = staged_construction_financing(inputs["construction_financing"], name, adjusted,
        original_funding["debt_source"]["context"], cost, budget, calendar,
        construction_quote=original_funding["bank_document_binding"]["quote"])
    require(funding["state"] == "computed_synthetic", "La financiación de obra quedó PENDING")
    return budget, funding


def reprice_route(view, terms, original, funding):
    adjusted = route_cash(view | {"construction_financing": funding}, terms)
    require(adjusted["state"] == "calculated_synthetic", f"Ruta PENDING: {adjusted.get('blocker')}")
    replay = json.loads(json.dumps(adjusted, default=rational))
    require(all(replay["sale"][key] == original["sale"][key] for key in ("date", "gross", "cost")),
            "La fecha, el precio y los costos de venta deben reproducir D238")
    return replay


def normalized_route(route):
    refinance = next((row["date"] for row in route["cash_by_period"] if row["stage"] == "refinance"), None)
    return dict(cash_per_usd_10=route["cash_per_usd_10"], sale_date=route["sale"]["date"], refinance_date=refinance)


def require_monotone_funding(base, zero):
    # D144 allocates direct and linked costs linearly. D146 draws a fixed share
    # of invoices, with fees and cash interest nondecreasing in eligible cost.
    require(all(a["date"] == b["date"]
                and amount(a["project_uses"]) - amount(a["loan_draw"]) >= amount(b["project_uses"]) - amount(b["loan_draw"])
                for a, b in zip(base["cash_by_date"], zero["cash_by_date"], strict=True)),
            "No se comprobó que reducir obra reduzca los usos netos en las fechas de aporte")


def minimum_construction_cut(direct, evaluate):
    """Certify the first recoverable cent under the D144/D146 funding order."""
    direct_cents = direct * 100
    require(direct_cents.denominator == 1 and direct_cents > 0, "La obra base debe expresarse en centavos")
    baseline, study = evaluate(Fraction())
    if baseline[0] >= 0:
        return Fraction(), baseline, None, study
    require(baseline[1] < 0, "La precisión del cruce no determina el resultado sin recorte")
    bounds, study = evaluate(direct)
    if bounds[1] < 0:
        return None, bounds, None, study
    require(bounds[0] >= 0, "La precisión del cruce no determina el resultado con obra cero")
    low, high = 0, int(direct_cents)
    below_upper = baseline[1]
    while high - low > 1:
        cents = (low + high) // 2
        (floor, ceiling), trial = evaluate(Fraction(cents, 100))
        if ceiling < 0:
            low, below_upper = cents, ceiling
        else:
            require(floor >= 0, "La precisión del cruce no separa los dos centavos de costo")
            high, bounds, study = cents, (floor, ceiling), trial
    require(below_upper < 0 <= bounds[0], "La reducción no pasó la prueba del centavo")
    return Fraction(high, 100), bounds, below_upper, study


def construction_recovery(model, inputs, table, labels):
    crosses = crossover_by_scenario(table, width=Fraction(1, 10**14))
    result = {}
    for name in SCENARIOS:
        original = model["scenarios"][name]
        budget = original["construction_budget"]
        original_direct = amount(budget["direct_hard_cost"])
        original_development = amount(budget["total_development_cost"])
        cross = crosses[name]
        purchase = date.fromisoformat(cross["purchase_date"])
        rates = tuple(amount(cross[key]) for key in ("monthly_rate_lower", "monthly_rate_upper"))
        base_budget, base_funding = construction_at_cut(model, inputs, name, Fraction())
        zero_budget, zero_funding = construction_at_cut(model, inputs, name, original_direct)
        require_monotone_funding(base_funding, zero_funding)
        paths = {}
        for label, (caption, _, _) in zip(labels, ROUTES, strict=True):
            baseline = model["calendar_checks"][name][label]
            terms = inputs["calendar_checks"][name][label]
            require(reprice_route(original, terms, baseline, base_funding) == baseline
                    and baseline["cash_per_usd_10"] == table[name, caption]["cash_per_usd_10"],
                    "La caja sin reducción no reproduce D238")
            baseline_balance = accumulated_balance_bounds(monthly_flows(normalized_route(baseline), purchase), rates)
            require(baseline_balance[1] < 0, "El caso de partida no necesita una reducción positiva")
            def evaluate(cut):
                if cut == 0:
                    return baseline_balance, (baseline, base_budget)
                trial_budget, funding = (zero_budget, zero_funding) if cut == original_direct else (
                    construction_at_cut(model, inputs, name, cut))
                replay = reprice_route(original, terms, baseline, funding)
                bounds = accumulated_balance_bounds(monthly_flows(normalized_route(replay), purchase), rates)
                return bounds, (replay, trial_budget)

            cut, bounds, below_upper, (tested, tested_budget) = minimum_construction_cut(original_direct, evaluate)
            pv = present_value(exact_rows(monthly_flows(normalized_route(tested), purchase)), sum(rates) / 2)
            paths[caption] = dict(
                direct_cut=None if cut is None else rational(cut),
                tested_direct_cost=tested_budget["direct_hard_cost"],
                tested_total_budget_reduction=rational(original_development - amount(tested_budget["total_development_cost"])),
                tested_van_per_10=rational(pv), tested_cash_per_10=tested["cash_per_usd_10"],
                tested_principal_at_sale=tested["sale"]["principal_paid"],
                tested_terminal_bounds=dict(lower=rational(bounds[0]), upper=rational(bounds[1])),
                one_cent_less_terminal_upper=None if below_upper is None else rational(below_upper),
                cash_sha256=table[name, caption]["cash_sha256"],
            )
        result[name] = dict(cross=cross, original_direct=base_budget["direct_hard_cost"],
                            original_gross_sale=model["calendar_checks"][name][labels[0]]["sale"]["gross"], paths=paths)
    return result


def render_construction(case_revision, results):
    lines = [
        ("Ensayo sintético | 1101 real y retorno histórico PENDING", True),
        ("Recuperación en valor presente por cada USD 10 iniciales, usando las tasas de cruce originales de D239.", False),
        ("Se reducen obra vertical, estacionamiento y sitio en la misma proporción.", False),
        ("Se recalculan contingencia, indirectos, desembolsos, intereses de obra y aportes. Precio de venta fijo.", False),
        ("", False),
    ]
    for name, row in results.items():
        lines.append((f"{name} | {shown_rate(row['cross'])} mensual | Venta USD {display_money(row['original_gross_sale'])}"
                      f" | Obra directa inicial USD {display_money(row['original_direct'])}", True))
        for caption, path in row["paths"].items():
            cut = path["direct_cut"]
            if cut is None:
                prefix = (f"{caption} | Con obra directa en USD 0 faltan USD {usd(-amount(path['tested_van_per_10']))}"
                          " en valor presente por USD 10")
            else:
                ratio = usd(amount(cut) * 100 / amount(row["original_direct"]))
                prefix = f"{caption} | Reducción mínima USD {display_money(cut)} ({ratio}%)"
            lines.append((prefix, True))
            if cut is not None:
                lines.append((f"Obra directa resultante USD {display_money(path['tested_direct_cost'])}"
                              f" | Ahorro con contingencia e indirectos USD {display_money(path['tested_total_budget_reduction'])}", False))
            cash = path["tested_cash_per_10"]
            lines.append((f"Por USD 10 | Aporte extra USD {display_money(cash['additional'])}"
                          f" | Cobro total USD {display_money(cash['received'])}"
                          f" | Venta {row['cross']['sale_date']}", False))
        lines.append(("", False))
    lines.append(("Los mínimos alcanzables se verificaron al centavo. Sin reducción viable, se muestra el límite con obra cero.", False))
    return render_page(case_revision, lines, 17, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "D241 | Reducción de obra requerida para recuperar aportes en valor presente")


def deliver_annual_crossover_construction(directory, output, current_revision, labels):
    require_pdf_destination(directory, output, current_revision)
    files, revision, case_revision, table = audited_annual_comparison(directory, current_revision, labels)
    model = json.loads(files["results.json"])
    inputs = json.loads(files["case.json"])["rent_inputs"]
    reductions = construction_recovery(model, inputs, table, labels)
    pdf = render_construction(case_revision, reductions)
    publish_current_pdf(directory, files, current_revision, revision, output, pdf)
    return dict(decision="PENDING", current_revision=case_revision, page_count=1,
                revision_sha256=sha256(revision).hexdigest(), source_results_sha256=sha256(files["results.json"]).hexdigest(),
                pdf_sha256=sha256(pdf).hexdigest(), scenarios=reductions)
