"""Replay synthetic Downside recovery with sale closing costs linked to gross price."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_sale_combinations_D87 import verify
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D88_Costos_Venta_Variables_USD10.pdf"
SALE_COST_RATE = Fraction(5, 100)


def build_report():
    result = verify(marginal_sale_cost=SALE_COST_RATE)
    rows = result["combinations"]
    original = result["original"]
    first, second = [e for e in original["events"] if e["category"] == "operating_distribution"]
    percent = amount(result["marginal_sale_cost"]) * 100
    lines = [
        (f"Supuesto sintético. Costo de venta = USD {money(result['fixed_sale_cost_component'])} + {percent} % del precio bruto.", True),
        (f"El costo original sigue en USD {money(result['original_sale_closing_cost'])} si el activo se vende por USD {money(result['original_sale_price'])}.", False),
        ("Cada columna usa su propio precio mínimo. Las tasas son mensuales.", False),
        ("Costo de refinanciación | 0 % mensual | 1 % mensual | 2 % mensual", True),
    ]

    def add_grid(title, field):
        lines.append((title, True))
        for row in rows:
            cells = []
            for threshold in row["thresholds"]:
                value = threshold["minimum_gross_price_project"] if field is None else threshold["probes"]["at_cents"][field]
                cells.append(f"USD {money(value)}")
            lines.append((f"USD {money(row['refinance_cost_project'])} | " + " | ".join(cells), False))

    add_grid("PRECIO BRUTO MÍNIMO DEL ACTIVO", None)
    add_grid(f"COBRO NETO DE VENTA POR USD 10 INICIALES EL {result['sale_date']}", "sale_net_per_usd_10")
    add_grid("COBRO TOTAL POR USD 10 INICIALES, INCLUYE OPERACIÓN Y REFI", "cash_total_received_per_usd_10")

    require(all(amount(t["probes"]["at_cents"]["cash_unrecovered_per_usd_10"]) == 0
                for row in rows for t in row["thresholds"]), "Recovery threshold left nominal cash unrecovered")
    lines.extend([
        (f"Aportás USD 10 el {result['discount_date']}. Cobrás USD {money(first['amount'])} el {first['date']} y USD {money(second['amount'])} el {second['date']}.", False),
        (f"Refi del {result['refinance_date']} por USD 10 | " + " | ".join(
            f"Costo {int(amount(row['refinance_cost_project']))}: "
            + (f"aportás {money(row['thresholds'][0]['probes']['at_cents']['extra_contribution_per_usd_10'])}"
               if amount(row["refinance_net_per_usd_10"]) < 0
               else f"cobrás {money(row['refinance_net_per_usd_10'])}")
            for row in rows), False),
        ("En los nuevos mínimos queda USD 0,00 sin recuperar. Los nueve precios anteriores quedan cortos.", True),
        ("Se mantiene la operación, la deuda y la capacidad del caso. Decisión real pendiente.", False),
    ])
    pdf = render_page("D88 | Downside", lines, 21, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Downside sintético con costo de venta variable")
    result.update(pdf_sha256=sha(pdf), page_count=1)
    return pdf, result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of auditing the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pdf, result = build_report()
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(pdf)
    else:
        require((ROOT / REPORT).read_bytes() == pdf, "The one-page report differs from source replay")
    if args.evidence:
        with args.evidence.open("xb") as stream:
            stream.write(encoded(result))
    print(json.dumps(dict(status="passed", decision=result["decision"], rates=3,
                          combinations=sum(len(row["thresholds"]) for row in result["combinations"]),
                          closing_probes=result["closing_probes"], one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
