"""Find the monthly discount rate that equalizes the audited annual routes."""

from datetime import date
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256

from check_discounted_sale_recovery_D34 import present_value
from check_reference_package import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import SCENARIOS
from miniuw_worksheet_v1 import publish_current_pdf, require_pdf_destination
from reconcile_worksheet_D179 import months
from worksheet_annual_comparison import audited_annual_comparison
from worksheet_annual_coc import quantity as amount
from worksheet_annual_route_report import dated_cash, usd


def monthly_flows(route, origin):
    sale = date.fromisoformat(route["sale_date"])
    last = months(sale) - months(origin)
    require(0 < last and sale.day == origin.day, "Calendario mensual PENDING para la salida")
    flows = [Fraction()] * (last + 1)
    for (when, _), (contribution, receipt) in dated_cash(route).items():
        cash_date = date.fromisoformat(when)
        index = months(cash_date) - months(origin)
        require(0 <= index <= last and cash_date.day == origin.day, "Fecha fuera de la grilla mensual")
        flows[index] += receipt - contribution
    return flows


def exact_rows(values):
    return [dict(net=rational(value)) for value in values]


def bracket_crossover(relative, *, width=Fraction(1, 10**10)):
    """Prove a unique nonnegative crossing for an advance followed by shortfalls."""
    require(relative and relative[0] > 0 and all(value <= 0 for value in relative[1:]) and sum(relative) < 0,
            "Cruce PENDING: la caja diferencial no prueba un cruce único con adelanto inicial")
    observations = exact_rows(relative)
    lo, hi = Fraction(), Fraction(1, 100)
    while present_value(observations, hi) < 0:
        hi *= 2
    require(width > 0, "La precisión del intervalo debe ser positiva")
    while hi - lo > width:
        middle = (lo + hi) / 2
        if present_value(observations, middle) < 0:
            lo = middle
        else:
            hi = middle
    return lo, hi


def crossover_for_routes(with_refi, without, *, width=Fraction(1, 10**10)):
    initial = [date.fromisoformat(route["cash_per_usd_10"]["events"][0]["date"]) for route in (with_refi, without)]
    require(initial[0] == initial[1], "Las rutas requieren la misma fecha de aporte inicial")
    origin = initial[0]
    with_net, without_net = (monthly_flows(route, origin) for route in (with_refi, without))
    delta = [left - right for left, right in zip(with_net, without_net, strict=True)]
    first = next((index for index, value in enumerate(delta) if value), len(delta))
    lo, hi = bracket_crossover(delta[first:], width=width)
    refi, sale = exact_rows(with_net), exact_rows(without_net)

    def advantage(rate):
        return present_value(refi, rate) - present_value(sale, rate)

    require(advantage(lo) < 0 <= advantage(hi), "El VAN total no reproduce el intervalo del cruce")
    middle = (lo + hi) / 2
    return dict(
        purchase_date=origin.isoformat(), refinance_date=with_refi["refinance_date"], sale_date=with_refi["sale_date"],
        monthly_rate_lower=rational(lo), monthly_rate_upper=rational(hi),
        net_nominal_with_refi=rational(sum(with_net)), net_nominal_without_refi=rational(sum(without_net)),
        npv_at_midpoint_with_refi=rational(present_value(refi, middle)),
        npv_at_midpoint_without_refi=rational(present_value(sale, middle)),
        difference_at_lower=rational(advantage(lo)), difference_at_upper=rational(advantage(hi)),
        net_cash_delta_by_month=[dict(month=index, amount=rational(value)) for index, value in enumerate(delta) if value],
        cash_sha256=dict(with_refi=with_refi["cash_sha256"], without_refi=without["cash_sha256"]),
    )


def crossover_by_scenario(table, *, width=Fraction(1, 10**10)):
    return {name: crossover_for_routes(table[name, "Con refi"], table[name, "Sin refi"], width=width)
            for name in SCENARIOS}


def shown_rate(row):
    mid_percent = 50 * (amount(row["monthly_rate_lower"]) + amount(row["monthly_rate_upper"]))
    return f"{Decimal(mid_percent.numerator) / Decimal(mid_percent.denominator):.4f}".replace(".", ",") + "%"


def render_crossover(case_revision, results):
    lines = [
        ("Ensayo sintético | 1101 real y retorno histórico PENDING", True),
        ("D239 compara todos los aportes y cobros de D238 por cada USD 10 iniciales.", False),
        ("Cada flujo fechado se descuenta al día del aporte inicial con una tasa mensual efectiva.", False),
        ("VAN = suma de (cobro menos aporte) / (1 + tasa mensual) elevado a los meses transcurridos.", False),
        ("", False),
    ]
    for name, row in results.items():
        lines.extend([
            (f"{name} | Tasa de cruce {shown_rate(row)} mensual", True),
            (f"Refi el {row['refinance_date']} | Venta en ambas rutas el {row['sale_date']}", False),
            (f"Neto nominal con refi USD {usd(amount(row['net_nominal_with_refi']))}"
             f" | Sin refi USD {usd(amount(row['net_nominal_without_refi']))}", False),
            (f"VAN común en el cruce USD {usd(amount(row['npv_at_midpoint_with_refi']))}"
             " por USD 10 iniciales", False),
            ("", False),
        ])
    lines.append(("Por debajo del cruce, mayor VAN sin refi. Por encima, mayor VAN con refi.", True))
    if all(amount(row[f"npv_at_midpoint_{route}"]) < 0 for row in results.values()
           for route in ("with_refi", "without_refi")):
        lines.append(("El VAN de ambas rutas es negativo en el punto de igualdad en los dos escenarios.", False))
    lines.append(("El cruce es único para tasas no negativas. La refi adelanta caja y reduce el flujo neto posterior.", False))
    return render_page(case_revision, lines, 17, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "D239 | Tasa mensual que iguala el valor presente con y sin refinanciación")


def deliver_annual_crossover(directory, output, current_revision, labels):
    require_pdf_destination(directory, output, current_revision)
    files, revision, case_revision, table = audited_annual_comparison(directory, current_revision, labels)
    scenarios = crossover_by_scenario(table)
    pdf = render_crossover(case_revision, scenarios)
    publish_current_pdf(directory, files, current_revision, revision, output, pdf)
    return dict(decision="PENDING", current_revision=case_revision, page_count=1,
                revision_sha256=sha256(revision).hexdigest(), source_results_sha256=sha256(files["results.json"]).hexdigest(),
                pdf_sha256=sha256(pdf).hexdigest(), scenarios=scenarios)
