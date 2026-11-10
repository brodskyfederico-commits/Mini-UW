"""Reconcile four-to-six-month synthetic sale delays and retained-cash limits."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from math import ceil, floor
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from delayed_sale_carry_D93 import maturity_cash, sale_closing
from delayed_sale_recovery_D94 import CENT
from fixed_sale_delay_D92 import add_months, month_grid, monthly_cash
from holding_cost_sale_recovery_D97 import verify as holding_cases
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import downside_sources
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D99_Tenencia_Demora_4_6_Meses_USD10.pdf"
DELAYS = (4, 5, 6)


def verify():
    baseline = holding_cases()
    source = downside_sources()
    start, maturity = (date.fromisoformat(baseline[k]) for k in ("discount_date", "maturity_date"))
    original, payoff, _, _, _, loan_sha = maturity_cash(source, maturity)
    require(source["case_sha256"] == baseline["case_sha256"] and loan_sha == baseline["loan_run_sha256"]
            and payoff == amount(baseline["maturity_cash_payment_project"]), "The debt or scenario source changed")
    initial = amount(source["baseline"]["story"]["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    fee_rate = amount(baseline["sale_cost_rate"])
    fixed_fee = amount(baseline["fixed_sale_cost_project"])
    after_maturity = amount(original["amounts"]["opening_free_cash"]) - payoff
    rows = []

    for row in baseline["rows"]:
        holding = amount(row["monthly_holding_cost_project"])
        require(holding > 0, "The funding limit requires a positive holding cost")
        reference = row["scenarios"][-1]
        require(amount(reference["holding_cash"][-1]["free_cash_after_project"])
                == after_maturity - holding * reference["delay_months"],
                "The retained cash does not reconcile with the prior holding period")
        funded_months = floor(after_maturity / holding)
        require(after_maturity - funded_months * holding >= 0 > after_maturity - (funded_months + 1) * holding,
                "The available-cash boundary is inconsistent")
        first_unfunded = dict(month=funded_months + 1,
                              cash_required_project=rational((funded_months + 1) * holding - after_maturity),
                              state="PENDING", blocker="retained_cash_insufficient_additional_funding_terms_required")
        scenarios = []
        for delay in DELAYS:
            sale_date = add_months(maturity, delay)
            when = sale_date.isoformat()
            dates = month_grid(start, sale_date)
            cash = [dict(date=add_months(maturity, month).isoformat(), expense_project=rational(holding),
                         free_cash_after_project=rational(after_maturity - holding * month))
                    for month in range(1, delay + 1)]
            free = amount(cash[-1]["free_cash_after_project"])
            require(all(amount(entry["free_cash_after_project"]) >= 0 for entry in cash),
                    "The extended delay requires additional funding")
            thresholds = []
            for previous in reference["thresholds"]:
                rate = amount(previous["monthly_rate"])
                before = previous["probes"]["at_cents"]
                original_events = before["dated_events"]
                sale_event, = [e for e in original_events if e["category"] == "net_sale_distribution"]
                pre_sale = [e for e in original_events if e != sale_event]
                require(all(e["date"] < maturity.isoformat() for e in pre_sale),
                        "Expected only the verified pre-maturity investor cash")
                pre_pv = present_value(monthly_cash(pre_sale, dates), rate)
                discount = (1 + rate)**-(len(dates) - 1)
                required_net = -pre_pv / discount
                reference_price = amount(before["gross_price_project"])
                holding_delta = holding * (delay - reference["delay_months"])
                exact = reference_price + ((required_net - amount(sale_event["amount"])) / scale + holding_delta) / (1 - fee_rate)
                quote = ceil(exact / CENT) * CENT
                require(0 <= quote - CENT < exact <= quote and required_net > 0,
                        "Expected a positive minimum price and terminal receipt")
                probes = {}
                for label, price in (("at_cents", quote), ("one_cent_below", quote - CENT)):
                    fee = fixed_fee + price * fee_rate
                    close, distribution = sale_closing(original, source, fee, when, free, gross_price=price)
                    net_sale = distribution * scale
                    events = pre_sale + [sale_event | {"date": when, "amount": rational(net_sale)}]
                    pv = present_value(monthly_cash(events, dates), rate)
                    receipts = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
                    contributions = sum(amount(e["amount"]) for e in events if e["kind"] == "contribution")
                    require(contributions == 10 and pv == pre_pv + net_sale * discount
                            and net_sale == amount(sale_event["amount"]) + ((price - reference_price) * (1 - fee_rate) - holding_delta) * scale
                            and (pv >= 0 if label == "at_cents" else pv < 0),
                            "The extended closing did not confirm the minimum recovery price")
                    probes[label] = dict(gross_price_project=rational(price), closing_fee_project=rational(fee),
                                         sale_net_per_usd_10=rational(net_sale), cash_total_received_per_usd_10=rational(receipts),
                                         present_value_per_usd_10=rational(pv), extra_contribution_per_usd_10=rational(contributions - 10),
                                         cash_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                                         dated_events=events, closing_sha256=close.sha256)
                thresholds.append(dict(monthly_rate=rational(rate), exact_recovery_price_project=rational(exact),
                                       minimum_sale_price_project=rational(quote), probes=probes))
            scenarios.append(dict(delay_months=delay, sale_date=when, holding_cash=cash,
                                  total_holding_cost_project=rational(holding * delay),
                                  debt_payoff_at_sale_project=rational(Fraction(0)), thresholds=thresholds))
        rows.append(dict(monthly_holding_cost_project=row["monthly_holding_cost_project"],
                         full_months_funded_from_retained_cash=funded_months, first_unfunded_month=first_unfunded,
                         scenarios=scenarios))

    return {key: value for key, value in baseline.items() if key not in {"rows", "pdf_sha256", "page_count"}} | dict(
        cash_after_maturity_project=rational(after_maturity), rows=rows)


def build_report():
    result = verify()
    lines = [
        ("Cada par muestra precio bruto mínimo del activo / cobro total por USD 10 iniciales, en USD.", True),
        ("Refinanciación USD 175. Costo de venta USD 10 fijos + 5 %. Tenencia con ingreso extra igual a cero.", False),
        (f"El proyecto paga deuda de USD {money(result['maturity_cash_payment_project'])} el {result['maturity_date']}. Al vender, deuda USD 0.", False),
        ("La tenencia se paga con caja retenida. Cada mínimo recupera aportes a la tasa indicada.", False),
        ("Demora y fecha de venta | 0 % mensual | 1 % mensual | 2 % mensual", True),
    ]
    for row in result["rows"]:
        lines.append((f"TENENCIA USD {money(row['monthly_holding_cost_project'])}/MES | CAJA SUFICIENTE PARA {row['full_months_funded_from_retained_cash']} MESES COMPLETOS", True))
        for scenario in row["scenarios"]:
            cells = [f"{money(t['minimum_sale_price_project'])} / {money(t['probes']['at_cents']['cash_total_received_per_usd_10'])}"
                     for t in scenario["thresholds"]]
            lines.append((f"+{scenario['delay_months']} meses | {scenario['sale_date']} | " + " | ".join(cells), False))
    lines.extend([
        ("Aportás USD 10 el 01/01/2027. Cobrás USD 1 el 01/03, USD 0,45 el 01/04 y USD 1 el 01/06.", False),
        ("Cobrás el resto al vender. Aportes extra en las demoras de 4, 5 y 6 meses USD 0,00.", True),
        ("Al agotarse la caja, el escenario queda PENDING hasta definir financiación adicional.", False),
        ("Un centavo menos de precio deja faltante. Supuestos sintéticos. Decisión real pendiente.", False),
    ])
    pdf = render_page("D99 | Downside", lines, 20, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Venta demorada de 4 a 6 meses y límite de caja")
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
                          sale_probes=sum(len(t["probes"]) for t in thresholds),
                          funding_boundaries=len(result["rows"]), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
