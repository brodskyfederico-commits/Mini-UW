"""Compute the required price increase over the audited synthetic sale forecast."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
import json

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_worksheet_refinance_D45 import render_page
from compare_refinance_discount_D111 import OPTIONS, decimal_display, percent
from compare_sale_to_minimum_D114 import CASE, REPORT as SOURCE_REPORT, build_comparison
from compare_sale_to_minimum_D114 import render as render_source, verify as verify_source
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from plan_return_D107 import INITIAL, SALE_COST_RATE
from worksheet_plan_refinance_D109 import SCENARIOS
from worksheet_plan_sale_recovery_D113 import compact_money
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D115_Aumento_Venta_para_Recuperar_2pct.pdf"
NET_PER_PROJECT_DOLLAR = (1 - SALE_COST_RATE) * Fraction(10, INITIAL)


def sale_increase(row):
    forecast = amount(row["expected_gross_price"])
    target = amount(row["minimum_gross_price_at_cents"])
    require(forecast > 0 and target > forecast and (target * 100).denominator == 1,
            "The synthetic forecast requires a positive price and a greater cent-denominated sale minimum")
    increase = target - forecast
    net_required = -amount(row["sale_gap_per_usd_10"])
    net_at_target = increase * NET_PER_PROJECT_DOLLAR
    require(net_at_target - NET_PER_PROJECT_DOLLAR / 100 < net_required <= net_at_target,
            "Only the minimum gross price at cents must cover the exact USD 10 shortfall")
    return dict(gross_increase_usd=rational(increase), gross_increase_fraction=rational(increase / forecast),
                net_increase_needed_per_usd_10=rational(net_required),
                net_increase_at_minimum_per_usd_10=rational(net_at_target))


def build_report(raw):
    comparison = build_comparison(raw)
    verify_source(comparison)
    source_pdf = render_source(comparison)
    require(source_pdf == local_file(ROOT, SOURCE_REPORT).read_bytes(),
            "The price increase must reproduce from the exact D114 report")
    cases = {scenario: {option: row | sale_increase(row) for option, row in pair.items()}
             for scenario, pair in comparison["cases"].items()}
    return comparison | {"cases": cases, "sale_gap_report_sha256": sha(source_pdf)}


def render(report):
    columns = [report["cases"][name][option] for name in SCENARIOS for option in OPTIONS]
    width = 15

    def row(label, values, bold=False):
        return f"{label:<39}" + "".join(f"{value:>{width}}" for value in values), bold

    lines = [
        ("Recuperación de los aportes en valor presente al 2 % mensual.", True),
        ("Plano A-601 revisado. Venta 30/06/2028. Valor presente al 30/03/2027.", False),
        (f"{' ':<46}{'Base':^30}{'Downside':^30}", True),
        row("PRECIO BRUTO DEL PROYECTO", ("Sin refi", "Con refi", "Sin refi", "Con refi"), True),
    ]
    for key, label in (
        ("expected_gross_price", "Venta prevista (USD)"),
        ("minimum_gross_price_at_cents", "Venta mínima (USD)"),
        ("gross_increase_usd", "Aumento necesario (USD)"),
    ):
        lines.append(row(label, [compact_money(case[key], group=True) for case in columns],
                         bold=key == "gross_increase_usd"))
    lines.append(row("Aumento sobre venta prevista", [percent(case["gross_increase_fraction"], 2) for case in columns], True))
    lines.extend([
        ("El mínimo bruto incluye costos de venta del 5 % y cancelación de deuda si corresponde.", False),
        ("Aumento porcentual = aumento bruto dividido por la venta prevista. Se redondea al mostrar.", False),
        ("USD POR USD 10 INICIALES", True),
        ("Aportás USD 10 el 30/03/2027 y USD 0,42 extra el 30/06/2027 en los cuatro casos.", False),
    ])
    for key, label in (
        ("net_refinance_distribution", "Refi neta 30/03/2028"),
        ("operating_distribution", "Operación 30/06/2028"),
        ("net_sale_distribution", "Venta neta prevista 30/06/2028"),
        ("total_distributions", "Cobro total previsto"),
        ("unrecovered_after_sale", "Saldo nominal sin recuperar"),
    ):
        lines.append(row(label, [money(case["amounts"][key]) for case in columns]))
    lines.extend([
        row("Neto adicional necesario al vender",
            [decimal_display(amount(case["net_increase_needed_per_usd_10"]), 2) for case in columns], True),
        ("La refi usa una solicitud sintética de USD 1.100.000. Los demás flujos siguen fijos.", False),
        ("Datos sintéticos. Capital agregado del proyecto. Decisión de inversión PENDING.", False),
    ])
    return render_page("D115 | Aumento de la venta prevista", lines, 20,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO DEBE SUBIR LA VENTA?",
                       "Aumento en USD y porcentaje para recuperar lo aportado")


def verify(report):
    expected = (
        ("397.589,82", "13,88 %"), ("365.766,43", "12,77 %"),
        ("1.492.910,06", "81,63 %"), ("1.461.086,67", "79,89 %"),
    )
    for (scenario, option), pair in zip(((s, o) for s in SCENARIOS for o in OPTIONS), expected, strict=True):
        row = report["cases"][scenario][option]
        require((compact_money(row["gross_increase_usd"], group=True),
                 percent(row["gross_increase_fraction"], 2)) == pair,
                "The expected synthetic increase or percentage changed")
    require(report["decision"] == "PENDING", "The one-page comparison acquired a real decision")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of checking the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    report = build_report(local_file(ROOT, CASE).read_bytes())
    verify(report)
    pdf = render(report)
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(pdf)
    else:
        require(local_file(ROOT, REPORT).read_bytes() == pdf, "The versioned PDF differs from exact source replay")
    if args.evidence:
        with args.evidence.open("xb") as stream:
            stream.write(encoded(report | dict(pdf_sha256=sha(pdf), page_count=1)))
    print(json.dumps(dict(status="passed", decision="PENDING", cases=4, monthly_discount_rate="2%",
                          page_count=1, pdf_sha256=sha(pdf)), sort_keys=True))


if __name__ == "__main__":
    main()
