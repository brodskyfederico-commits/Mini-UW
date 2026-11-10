"""Verify minimum gross prices for synthetic recovery after a delayed, costed sale."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from math import ceil
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from delayed_sale_carry_D93 import maturity_cash, sale_closing, verify as delay_cases
from fixed_sale_delay_D92 import month_grid, monthly_cash
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import downside_sources
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D94_Venta_Minima_Demorada_USD10.pdf"
CENT = Fraction(1, 100)


def verify():
    carry = delay_cases()
    source = downside_sources()
    start, maturity = (date.fromisoformat(carry[k]) for k in ("discount_date", "maturity_date"))
    original, payoff, _, _, _, loan_sha = maturity_cash(source, maturity)
    initial = amount(source["baseline"]["story"]["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    base_price = amount(carry["sale_price_project"])
    fixed_fee = amount(carry["fixed_sale_cost_project"])
    require(source["case_sha256"] == carry["case_sha256"] and loan_sha == carry["loan_run_sha256"]
            and payoff == amount(carry["maturity_cash_payment_project"]), "The maturity and carry source changed")

    rows = []
    for row in carry["rows"]:
        fee_rate = amount(row["sale_cost_rate"])
        net_per_price_unit = (1 - fee_rate) * scale
        require(net_per_price_unit > 0, "The sale fee leaves no positive marginal proceeds")
        scenarios = []
        for scenario in row["scenarios"]:
            when = scenario["sale_date"]
            dates = month_grid(start, date.fromisoformat(when))
            sale_index = len(dates) - 1
            free = amount(scenario["holding_expenses"][-1]["free_cash_after_project"])
            baseline_events = scenario["dated_events"]
            sale_event, = [e for e in baseline_events if e["category"] == "net_sale_distribution"]
            baseline_net = amount(sale_event["amount"])
            require(sale_event["date"] == when and baseline_net == amount(scenario["sale_net_per_usd_10"])
                    and free == amount(carry["cash_after_maturity_project"]) - amount(scenario["total_holding_cost_project"])
                    and amount(scenario["debt_payoff_at_sale_project"]) == 0,
                    "The sale did not retain the delayed closing's cash and debt balance")

            thresholds = []
            for gap in scenario["gaps"]:
                rate = amount(gap["monthly_rate"])
                discount = (1 + rate)**-sale_index
                baseline_pv = amount(gap["present_value_per_usd_10"])
                target = base_price - baseline_pv / (net_per_price_unit * discount)
                quote = ceil(target / CENT) * CENT
                require(0 <= quote - CENT < target <= quote, "Expected a positive bounded minimum")
                probes = {}
                for label, price in (("at_cents", quote), ("one_cent_below", quote - CENT)):
                    sale_fee = fixed_fee + price * fee_rate
                    close, distribution = sale_closing(original, source, sale_fee, when, free, gross_price=price)
                    net_sale = distribution * scale
                    events = [e | {"amount": rational(net_sale)} if e == sale_event else e for e in baseline_events]
                    pv = present_value(monthly_cash(events, dates), rate)
                    receipts = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
                    contributions = sum(amount(e["amount"]) for e in events if e["kind"] == "contribution")
                    require(net_sale == baseline_net + (price - base_price) * net_per_price_unit
                            and pv == baseline_pv + (net_sale - baseline_net) * discount
                            and contributions == 10 + amount(row["extra_contribution_per_usd_10"])
                            and (pv >= 0 if label == "at_cents" else pv < 0),
                            "The cent-boundary closing did not reconcile to the dated cash")
                    probes[label] = dict(gross_price_project=rational(price), sale_fee_project=rational(sale_fee),
                                         sale_net_per_usd_10=rational(net_sale),
                                         cash_total_received_per_usd_10=rational(receipts),
                                         present_value_per_usd_10=rational(pv),
                                         nominal_cash_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                                         dated_events=events, closing_sha256=close.sha256)
                thresholds.append(dict(monthly_rate=rational(rate), exact_price_project=rational(target),
                                       minimum_gross_price_project=rational(quote), probes=probes))
            scenarios.append({key: scenario[key] for key in ("delay_months", "sale_date", "total_holding_cost_project",
                                                              "debt_payoff_at_sale_project")}
                             | {"thresholds": thresholds})
        rows.append({key: value for key, value in row.items() if key != "scenarios"} | {"scenarios": scenarios})

    return {key: value for key, value in carry.items() if key != "rows"} | {"rows": rows}


def build_report():
    result = verify()
    lines = [
        ("Precio bruto mínimo del activo para recuperar los aportes por USD 10 iniciales.", True),
        ("Costo de venta USD 10 fijos + porcentaje de la tabla. Tenencia USD 20 por mes, sin ingreso extra.", False),
        ("El proyecto paga USD 56,00 de deuda el 01/07/2027. El saldo de deuda al vender es USD 0.", False),
        ("Cada grupo muestra el mínimo en USD al 0 % / 1 % / 2 % mensual.", False),
        ("Costo variable de venta | +1 mes (01/08) | +2 meses (01/09) | +3 meses (01/10)", True),
    ]
    prior = None
    for row in result["rows"]:
        cost = row["refinance_cost_project"]
        if cost != prior:
            lines.append((f"COSTO DE REFINANCIACIÓN DEL PROYECTO USD {money(cost)}", True))
            prior = cost
        cells = [" / ".join(money(t["minimum_gross_price_project"]) for t in s["thresholds"])
                 for s in row["scenarios"]]
        lines.append((" | ".join([f"{amount(row['sale_cost_rate']) * 100} %", *cells]), False))
    example = result["rows"][7]
    lines.append(("COBRO TOTAL POR USD 10 AL PRECIO MÍNIMO | REFI USD 150 Y COSTO DE VENTA DEL 5 % + FIJO", True))
    for scenario in example["scenarios"]:
        totals = " / ".join(money(t["probes"]["at_cents"]["cash_total_received_per_usd_10"])
                            for t in scenario["thresholds"])
        lines.append((f"{scenario['sale_date']} | USD {totals} al 0 % / 1 % / 2 % mensual", False))
    lines.extend([
        ("Ejemplo: cobrás USD 1 en marzo, USD 0,70 en abril, USD 1 en junio y el resto al vender.", False),
        ("El ejemplo queda sin aporte extra ni faltante. Refi de USD 300 requiere USD 0,80 en abril.", False),
        ("Los mínimos se verificaron al centavo y un centavo por debajo. Decisión real pendiente.", False),
    ])
    pdf = render_page("D94 | Downside", lines, 18, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Precio de recuperación con venta demorada, tenencia y deuda")
    return pdf, result | {"pdf_sha256": sha(pdf), "page_count": 1}


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
    thresholds = [t for row in result["rows"] for s in row["scenarios"] for t in s["thresholds"]]
    print(json.dumps(dict(status=result["status"], decision=result["decision"], combinations=len(thresholds),
                          closing_probes=sum(len(t["probes"]) for t in thresholds), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
