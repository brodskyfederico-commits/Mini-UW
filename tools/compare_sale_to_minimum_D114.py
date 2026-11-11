"""Compare the expected sale and the discounted recovery minimum on the revised plan."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
import json

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_worksheet_refinance_D45 import render_page
from compare_refinance_discount_D111 import OPTIONS, decimal_display, month_offset
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import build_results, encoded
from plan_return_D107 import DATES, SALE_DATE
from worksheet_plan_refinance_D109 import SCENARIOS
from worksheet_plan_sale_recovery_D113 import compact_money
from worksheet_sale_rate_grid_D84 import money


CASE = "templates/synthetic-plan-sale-recovery-D113.json"
REPORT = "docs/review/MiniUW_D114_Venta_Prevista_vs_Minimo_2pct.pdf"
RATE = Fraction(1, 50)


def compare_case(view):
    recovery = view["sale_recovery"]
    require(recovery is not None and recovery["sale_date"] == SALE_DATE,
            "The one-page comparison requires a verified sale on the stated date")
    basis = view["sale_basis"]
    amounts = view["amounts"]
    expected = amount(amounts["net_sale_distribution"])
    minimum = amount(recovery["minimum_net_sale_per_usd_10"])
    gap = expected - minimum
    pv_gap = gap / (1 + RATE) ** month_offset(SALE_DATE)
    gross = amount(basis["gross_price"])
    gross_minimum_exact = amount(recovery["minimum_gross_sale_exact"])
    require(gap == (gross - gross_minimum_exact) * (1 - amount(basis["sale_cost_rate"]))
            * amount(basis["initial_equity_scale"]) and pv_gap == amount(view["npv_per_usd_10"]),
            "The net sale gap, gross price difference and dated VAN do not reconcile")
    return dict(
        amounts=amounts, expected_net_sale_per_usd_10=rational(expected),
        exact_minimum_net_sale_per_usd_10=rational(minimum),
        sale_gap_per_usd_10=rational(gap), present_value_gap_per_usd_10=rational(pv_gap),
        expected_gross_price=rational(gross), minimum_gross_price_at_cents=recovery["minimum_gross_sale_at_cents"],
        source_runs=view["source_runs"],
    )


def build_comparison(case_raw):
    base, _ = build_results(case_raw)
    require(base["decision"] == "PENDING" and base["discount_date"] == DATES[0]
            and amount(base["monthly_discount_rate"]) == RATE
            and amount(base["requested_principal_usd"]) == 1100000
            and not base["deployment_enabled"] and not base["real_decisions_enabled"],
            "The sale gap requires the declared synthetic 2% case and original discount date")
    cases = {name: {option: compare_case(base["scenarios"][name]["alternatives"][option])
                    for option in OPTIONS} for name in SCENARIOS}
    require(all(amount(row["amounts"]["initial_capital"]) == 10
                and amount(row["amounts"]["additional_capital"]) == Fraction(5, 12)
                for pair in cases.values() for row in pair.values()),
            "The report requires the verified common contribution schedule")
    return dict(decision="PENDING", scope="synthetic_aggregate_equity", monthly_discount_rate=rational(RATE),
                discount_date=DATES[0], sale_date=SALE_DATE, source_case_sha256=sha(case_raw),
                source_pdf_sha256=base["pdf_sha256"], source_provenance=base["provenance"], cases=cases)


def render(comparison):
    columns = [comparison["cases"][name][option] for name in SCENARIOS for option in OPTIONS]
    width = 14
    headers = "".join(f"{label:>{width}}" for label in ("Sin refi", "Con refi", "Sin refi", "Con refi"))

    def row(label, cells, bold=False):
        return (f"{label:<40}" + "".join(f"{cell:>{width}}" for cell in cells), bold)

    lines = [
        ("Descuento de 2 % mensual al 30/03/2027. Venta prevista el 30/06/2028.", True),
        ("Aportás USD 10 el 30/03/2027 y USD 0,42 extra el 30/06/2027 en los cuatro casos.", False),
        ("Con refi, préstamo sintético de USD 1.100.000 a nivel del proyecto.", False),
        ("USD POR USD 10 INICIALES", True),
        (f"{' ':<47}{'Base':^28}{'Downside':^28}", True),
        (f"{'Cobros y recuperación':<40}{headers}", True),
    ]
    for key, label in (
        ("net_refinance_distribution", "Refi neta 30/03/2028"),
        ("operating_distribution", "Operación 30/06/2028"),
        ("total_distributions", "Cobro total previsto"),
        ("unrecovered_after_sale", "Saldo nominal sin recuperar"),
    ):
        lines.append(row(label, [money(case["amounts"][key]) for case in columns]))
    for key, label, places in (
        ("expected_net_sale_per_usd_10", "Neto de venta previsto 30/06/2028", 4),
        ("exact_minimum_net_sale_per_usd_10", "Neto de venta mínimo al 2 %", 4),
        ("sale_gap_per_usd_10", "Sobra (+) / falta (-) al vender", 2),
        ("present_value_gap_per_usd_10", "Sobra (+) / falta (-) en valor presente", 2),
    ):
        lines.append(row(label, [decimal_display(amount(case[key]), places) for case in columns],
                         bold=key.endswith("gap_per_usd_10")))
    lines.extend([
        ("PRECIO BRUTO EN USD DEL PROYECTO", True),
        row("Venta bruta prevista", [compact_money(case["expected_gross_price"], group=True) for case in columns]),
        row("Venta bruta mínima", [compact_money(case["minimum_gross_price_at_cents"], group=True) for case in columns]),
        ("La brecha se calcula antes de redondear. El mínimo bruto se redondea hacia arriba.", False),
        ("El neto incluye costos de venta del 5 % y cancelación de deuda cuando corresponde.", False),
        ("Plano revisado A-601. Datos sintéticos. Decisión de inversión PENDING.", False),
    ])
    return render_page("D114 | Venta prevista frente a venta mínima", lines, 20,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNTO FALTA?",
                       "Comparación de la venta prevista con el mínimo para recuperar los aportes")


def verify(comparison):
    expected = {
        ("Base", "without_refinance"): ("-1,57", "-1,17"),
        ("Base", "with_refinance"): ("-1,45", "-1,08"),
        ("Downside", "without_refinance"): ("-5,91", "-4,39"),
        ("Downside", "with_refinance"): ("-5,78", "-4,30"),
    }
    for (name, option), gaps in expected.items():
        row = comparison["cases"][name][option]
        require(tuple(decimal_display(amount(row[key]), 2) for key in
                      ("sale_gap_per_usd_10", "present_value_gap_per_usd_10")) == gaps,
                "The expected synthetic sale gap changed")
    require(comparison["decision"] == "PENDING", "The report acquired a real decision")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of checking the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    comparison = build_comparison(local_file(ROOT, CASE).read_bytes())
    verify(comparison)
    pdf = render(comparison)
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(pdf)
    else:
        require(local_file(ROOT, REPORT).read_bytes() == pdf, "The versioned PDF differs from exact source replay")
    if args.evidence:
        with args.evidence.open("xb") as stream:
            stream.write(encoded(comparison | dict(pdf_sha256=sha(pdf), page_count=1)))
    print(json.dumps(dict(status="passed", decision="PENDING", cases=4, monthly_discount_rate="2%",
                          page_count=1, pdf_sha256=sha(pdf)), sort_keys=True))


if __name__ == "__main__":
    main()
