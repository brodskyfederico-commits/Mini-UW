"""Render the audited annual worksheet comparison on one synthetic PDF page."""

from collections import defaultdict
from fractions import Fraction

from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.lorena_screening import BASES, SCENARIOS
from worksheet_annual_coc import quantity as amount
from worksheet_integrated_screening_D181 import LABELS, percent
from worksheet_irr_D122 import display_enclosure
from worksheet_sale_rate_grid_D84 import money


STAGES = {"construction": "Aporte inicial/obra", "refinance": "Refinanciación",
          "operation": "Operación", "sale": "Venta neta"}


def usd(value):
    return money(rational(value))


def totals(scenario, name):
    cash = scenario["cash_per_usd_10"]
    extra, received, unrecovered = (amount(cash[key]) for key in ("additional", "received", "unrecovered"))
    sale = sum(amount(row["receipt"]) for row in cash["events"] if row["stage"] == "sale")
    refi = scenario["refinance_date"]
    if refi is None:
        capital = "Refinanciación N/A"
    else:
        payout = sum(amount(row["receipt"]) for row in cash["events"] if row["stage"] == "refinance")
        invested_at_refi = sum(amount(row["contribution"]) for row in cash["events"] if row["date"] <= refi)
        capital = f"Capital remanente en refi {usd(max(Fraction(), invested_at_refi - payout))}"
    return [
        (f"{name} | Aporte extra {usd(extra)} | Cobro total {usd(received)} | Neto {usd(received - 10 - extra)}"
         f" | Sin recuperar {usd(unrecovered)}", True),
        (f"{capital} | Cobro final por venta {usd(sale)}"
         " | Valor retenido en el inmueble PENDING", False),
    ]


def dated_cash(scenario):
    dated = {}
    for stage in ("refinance", "sale"):
        when = scenario[f"{stage}_date"]
        if when is not None:
            dated[when, stage] = [Fraction(), Fraction()]
    for row in scenario["cash_per_usd_10"]["events"]:
        cell = dated.setdefault((row["date"], row["stage"]), [Fraction(), Fraction()])
        cell[0] += amount(row["contribution"])
        cell[1] += amount(row["receipt"])
    return dated


def dated_lines(scenarios):
    dated = defaultdict(dict)
    for name in SCENARIOS:
        for key, cell in dated_cash(scenarios[name]).items():
            dated[key][name] = cell
    order = {stage: index for index, stage in enumerate(STAGES)}
    lines = [(f"{'Fecha y etapa':32} | {'Base':^19} | {'Downside':^19}", True),
             (f"{'':32} | {'Aporta / Cobra':^19} | {'Aporta / Cobra':^19}", False)]
    for (when, stage), by_name in sorted(dated.items(), key=lambda item: (item[0][0], order[item[0][1]])):
        values = " | ".join(
            " / ".join(f"{usd(value):>8}" for value in by_name[name]) if name in by_name else f"{'—':^19}"
            for name in SCENARIOS)
        lines.append((f"{when}  {STAGES[stage]:20} | {values}", False))
    return lines


def metric_label(record, state):
    if state == "N/A":
        return state
    if not record:
        return "PENDING"
    value = record["value"]
    if "lower" in value:
        return display_enclosure(value)
    unit = record["unit"]
    if unit == "fraction":
        return percent(value)
    return money(value) + {"multiple": "×", "bps": " pb"}[unit]


def render_annual_route(receipt):
    route = receipt["annual_calendar_route"]
    scenarios = route["scenarios"]
    unavailable = [name for name in SCENARIOS if scenarios[name]["state"] != "calculated_synthetic"]
    if unavailable:
        raise ValidationError("Caja anual por USD 10 PENDING: " + ", ".join(unavailable))
    lines = [
        ("Dictamen real PENDING | Retorno histórico y personal PENDING", True),
        ("Equity agregado del proyecto. Importes en USD por USD 10 iniciales.", False),
    ]
    for name in SCENARIOS:
        lines.extend(totals(scenarios[name], name))
    lines.extend(dated_lines(scenarios))
    coc_basis = "CoC de los primeros 12 meses posrefi"
    if any(scenarios[name]["refinance_date"] is None for name in SCENARIOS):
        coc_basis = "CoC anual posrefi cuando aplica"
    lines.append((f"Métricas calculadas | Base / Downside | {coc_basis}", True))
    states = {(row["scenario"], row["metric_id"]): row["state"] for row in receipt["comparisons"]}
    for metric in BASES:
        values = " / ".join(metric_label(receipt["observed_metrics"][name].get(metric), states[name, metric])
                            for name in SCENARIOS)
        lines.append((f"{LABELS[metric]} | {values}", False))
    lines.append(("Umbrales del ensayo y motivos de PENDING en el recibo del expediente.", False))
    return render_page(receipt["current_revision"], lines, 10.2,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       f"Simulación sintética | Ruta {route['label']}")
