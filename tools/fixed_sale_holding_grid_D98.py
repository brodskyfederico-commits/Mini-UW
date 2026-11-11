"""Reconcile USD 10 cash and present-value gaps at a fixed synthetic sale price."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from delayed_sale_carry_D93 import maturity_cash, sale_closing
from fixed_sale_delay_D92 import month_grid, monthly_cash, signed
from holding_cost_sale_recovery_D97 import verify as holding_cases
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import downside_sources
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D98_Venta_300_Tenencia_Demora_USD10.pdf"
SALE_PRICE = Fraction(300)


def fixed_price_cases(baseline):
    source = downside_sources()
    start, maturity = (date.fromisoformat(baseline[k]) for k in ("discount_date", "maturity_date"))
    original, payoff, _, _, _, loan_sha = maturity_cash(source, maturity)
    require(source["case_sha256"] == baseline["case_sha256"] and loan_sha == baseline["loan_run_sha256"]
            and payoff == amount(baseline["maturity_cash_payment_project"]), "The debt or scenario source changed")
    initial = amount(source["baseline"]["story"]["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    fee_rate = amount(baseline["sale_cost_rate"])
    fee = amount(baseline["fixed_sale_cost_project"]) + SALE_PRICE * fee_rate
    rows = []

    for row in baseline["rows"]:
        scenarios = []
        holding = amount(row["monthly_holding_cost_project"])
        for scenario in row["scenarios"]:
            when = scenario["sale_date"]
            dates = month_grid(start, date.fromisoformat(when))
            free = amount(scenario["holding_cash"][-1]["free_cash_after_project"])
            require(free >= 0 and amount(scenario["debt_payoff_at_sale_project"]) == 0
                    and amount(scenario["total_holding_cost_project"]) == holding * scenario["delay_months"],
                    "The fixed sale changed the holding cash or debt basis")
            close, distribution = sale_closing(original, source, fee, when, free, gross_price=SALE_PRICE)
            net_sale = distribution * scale
            reference = scenario["thresholds"][0]["probes"]["at_cents"]
            original_events = reference["dated_events"]
            sale_event, = [event for event in original_events if event["category"] == "net_sale_distribution"]
            events = [event | {"amount": rational(net_sale)} if event == sale_event else event for event in original_events]
            receipts = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
            contributions = sum(amount(e["amount"]) for e in events if e["kind"] == "contribution")
            require(sale_event["date"] == when and contributions == 10
                    and receipts == Fraction(2) + amount(baseline["refinance_net_per_usd_10"]) + net_sale,
                    "The receipts or contributions do not reconcile with the USD 10 basis")
            flows = monthly_cash(events, dates)
            gaps = []
            for threshold in scenario["thresholds"]:
                rate = amount(threshold["monthly_rate"])
                before = threshold["probes"]["at_cents"]
                pv = present_value(flows, rate)
                change = (SALE_PRICE - amount(before["gross_price_project"])) * (1 - fee_rate) * scale
                require(net_sale == amount(before["sale_net_per_usd_10"]) + change
                        and pv == amount(before["present_value_per_usd_10"]) + change / (1 + rate)**(len(dates) - 1)
                        and (rate != 0 or pv == receipts - contributions),
                        "The fixed-price result did not reconcile with the minimum-price closing")
                gaps.append(dict(monthly_rate=rational(rate), present_value_per_usd_10=rational(pv)))
            scenarios.append({key: scenario[key] for key in ("delay_months", "sale_date", "total_holding_cost_project",
                                                              "debt_payoff_at_sale_project", "holding_cash")}
                             | dict(sale_net_per_usd_10=rational(net_sale), cash_total_received_per_usd_10=rational(receipts),
                                    nominal_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                                    extra_contribution_per_usd_10=rational(contributions - 10),
                                    dated_events=events, gaps=gaps, closing_sha256=close.sha256))
        rows.append(dict(monthly_holding_cost_project=row["monthly_holding_cost_project"], scenarios=scenarios))
    return {key: value for key, value in baseline.items() if key not in {"rows", "pdf_sha256", "page_count"}} | dict(
        sale_price_project=rational(SALE_PRICE), sale_cost_project=rational(fee), rows=rows)


def verify():
    return fixed_price_cases(holding_cases())


def render_report(result, revision):
    lines = [
        (f"Venta bruta fija USD {money(result['sale_price_project'])}. Refi USD {money(result['refinance_cost_project'])}. Costo de venta USD 10 + 5 % = USD {money(result['sale_cost_project'])}.", True),
        ("Todos los cobros y saldos de la tabla están en USD por USD 10 iniciales.", False),
        ("Los saldos descuentan aportes y cobros al 01/01/2027. + indica sobrante. - indica faltante.", False),
        (f"El proyecto paga USD {money(result['maturity_cash_payment_project'])} de deuda el {result['maturity_date']}. Al vender, la deuda es USD 0.", False),
        ("Demora / fecha | Neto venta | Cobro total | Saldo 0 % | Saldo 1 % | Saldo 2 % mensual", True),
    ]
    for row in result["rows"]:
        lines.append((f"TENENCIA USD {money(row['monthly_holding_cost_project'])} POR MES", True))
        for scenario in row["scenarios"]:
            fields = [f"+{scenario['delay_months']} / {scenario['sale_date']}",
                      money(scenario["sale_net_per_usd_10"]), money(scenario["cash_total_received_per_usd_10"])]
            fields.extend(signed(g["present_value_per_usd_10"]) for g in scenario["gaps"])
            lines.append((" | ".join(fields), False))
    lines.extend([
        ("Aportás USD 10 el 01/01/2027. Cobrás USD 1 el 01/03, USD 0,45 el 01/04 y USD 1 el 01/06.", False),
        ("Cobrás el neto de venta en la fecha indicada. La tenencia se paga con caja del proyecto.", False),
        ("Aportes extra USD 0,00. Al 0 % el saldo es el sobrante o faltante de caja nominal.", True),
        ("Tenencia con ingresos adicionales iguales a cero. Decisión real pendiente.", False),
    ])
    pdf = render_page(revision + " | Downside", lines, 20, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Venta fija con tres costos de tenencia y tres demoras")
    return pdf, result | {"pdf_sha256": sha(pdf), "page_count": 1}


def build_report():
    return render_report(verify(), "D98")


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
    scenarios = [s for row in result["rows"] for s in row["scenarios"]]
    print(json.dumps(dict(status=result["status"], decision=result["decision"], closings=len(scenarios),
                          combinations=sum(len(s["gaps"]) for s in scenarios), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
