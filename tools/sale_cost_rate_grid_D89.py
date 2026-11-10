"""Audit three synthetic price-linked sale costs in the same Downside."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from price_linked_sale_cost_D88 import SALE_COST_RATE
from refinance_sale_combinations_D87 import verify
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D89_Tasas_Costo_Venta_USD10.pdf"
FIXED_COST = Fraction(10)
SALE_RATES = (Fraction(3, 100), SALE_COST_RATE, Fraction(7, 100))


def build_report():
    grids = [verify(marginal_sale_cost=rate, fixed_sale_cost=FIXED_COST) for rate in SALE_RATES]
    _, center, _ = grids
    first, second = [e for e in center["original"]["events"] if e["category"] == "operating_distribution"]
    lines = [
        (f"Costo de venta sintético = USD {money(center['fixed_sale_cost_component'])} fijos + 3 %, 5 % o 7 % del precio bruto.", True),
        ("Cada par muestra precio bruto mínimo del activo / cobro total por USD 10 iniciales, en USD.", False),
        ("Costo variable de venta | 0 % mensual | 1 % mensual | 2 % mensual", True),
    ]
    for group in zip(*(grid["combinations"] for grid in grids), strict=True):
        cost = group[0]["refinance_cost_project"]
        lines.append((f"COSTO DE REFINANCIACIÓN DEL PROYECTO USD {money(cost)}", True))
        for fee_rate, row in zip(SALE_RATES, group, strict=True):
            require(row["refinance_cost_project"] == cost, "Refinance rows do not align")
            cells = []
            for t in row["thresholds"]:
                at = t["probes"]["at_cents"]
                require(amount(at["cash_unrecovered_per_usd_10"]) == 0,
                        "An accepted threshold left cash unrecovered")
                cells.append(f"{money(t['minimum_gross_price_project'])} / {money(at['cash_total_received_per_usd_10'])}")
            lines.append((f"{fee_rate * 100} % de venta | " + " | ".join(cells), False))
        for a, b, c in zip(*(row["thresholds"] for row in group), strict=True):
            require(amount(a["minimum_gross_price_project"]) < amount(b["minimum_gross_price_project"])
                    < amount(c["minimum_gross_price_project"]), "Minimum price did not increase with fee rate")

    refi_text = []
    for row in center["combinations"]:
        net = amount(row["refinance_net_per_usd_10"])
        refi_text.append(f"Costo {int(amount(row['refinance_cost_project']))} "
                         + (f"aportás {money(rational(-net))}" if net < 0 else f"cobrás {money(rational(net))}" if net else "saldo cero"))
    lines.extend([
        (f"Aportás USD 10 el {center['discount_date']}. Cobrás USD {money(first['amount'])} el {first['date']} y USD {money(second['amount'])} el {second['date']}.", False),
        (f"Refi {center['refinance_date']} por USD 10 | " + " | ".join(refi_text), False),
        (f"El {center['sale_date']} cobrás el resto. Al mínimo quedan USD 0,00 sin recuperar a la tasa indicada.", True),
        ("Cada precio se verificó al centavo y un centavo por debajo. Decisión real pendiente.", False),
    ])
    pdf = render_page("D89 | Downside", lines, 21, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Downside sintético con tres tasas de costo de venta")
    return pdf, dict(status="passed", decision="PENDING", scope="synthetic_only",
                     grids=grids, closing_probes=sum(grid["closing_probes"] for grid in grids),
                     pdf_sha256=sha(pdf), page_count=1)


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
    print(json.dumps(dict(status=result["status"], decision=result["decision"], sale_cost_rates=len(SALE_RATES),
                          combinations=sum(len(row["thresholds"]) for grid in result["grids"] for row in grid["combinations"]),
                          closing_probes=result["closing_probes"], one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
