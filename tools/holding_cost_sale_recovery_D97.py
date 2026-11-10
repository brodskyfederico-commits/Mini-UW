"""Verify delayed sale recovery across three monthly synthetic holding costs."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from math import ceil
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from delayed_exit_combinations_D96 import verify as combined_cases
from delayed_sale_carry_D93 import MONTHLY_HOLDING_COST, maturity_cash, sale_closing
from delayed_sale_recovery_D94 import CENT
from fixed_sale_delay_D92 import add_months, month_grid, monthly_cash
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from price_linked_sale_cost_D88 import SALE_COST_RATE
from refinance_cost_recovery_D86 import downside_sources
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D97_Tenencia_Precio_Minimo_USD10.pdf"
REFINANCE_COST = Fraction(175)
HOLDING_COSTS = (10, 20, 30)


def verify():
    baseline = combined_cases()
    anchor, = [r for r in baseline["rows"] if amount(r["refinance_cost_project"]) == REFINANCE_COST
               and amount(r["sale_cost_rate"]) == SALE_COST_RATE]
    source = downside_sources()
    start, maturity = (date.fromisoformat(baseline[k]) for k in ("discount_date", "maturity_date"))
    original, payoff, _, _, _, loan_sha = maturity_cash(source, maturity)
    require(source["case_sha256"] == baseline["case_sha256"] and loan_sha == baseline["loan_run_sha256"]
            and payoff == amount(baseline["maturity_cash_payment_project"]), "The maturity or scenario evidence changed")
    initial = amount(source["baseline"]["story"]["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    retained = 1 - SALE_COST_RATE
    fixed_fee = amount(baseline["fixed_sale_cost_project"])
    after_maturity = amount(baseline["cash_after_maturity_project"])
    rows = []

    for holding_cost in HOLDING_COSTS:
        scenarios = []
        for scenario in anchor["scenarios"]:
            delay = scenario["delay_months"]
            when = scenario["sale_date"]
            dates = month_grid(start, date.fromisoformat(when))
            require(when == add_months(maturity, delay).isoformat()
                    and amount(scenario["debt_payoff_at_sale_project"]) == 0
                    and amount(scenario["total_holding_cost_project"]) == MONTHLY_HOLDING_COST * delay,
                    "The delayed settlement basis changed")
            monthly_cash_balances = [
                dict(date=add_months(maturity, month).isoformat(), expense_project=rational(Fraction(holding_cost)),
                     free_cash_after_project=rational(after_maturity - holding_cost * month))
                for month in range(1, delay + 1)]
            free = amount(monthly_cash_balances[-1]["free_cash_after_project"])
            require(free >= 0, "Holding cash requires funding beyond the retained balance")
            holding_delta = (holding_cost - MONTHLY_HOLDING_COST) * delay
            thresholds = []
            for threshold in scenario["thresholds"]:
                rate = amount(threshold["monthly_rate"])
                discount = (1 + rate)**-(len(dates) - 1)
                reference = threshold["probes"]["at_minimum"]
                reference_price = amount(reference["gross_sale_project"])
                reference_pv = amount(reference["present_value_per_usd_10"])
                exact = reference_price + (holding_delta - reference_pv / (discount * scale)) / retained
                quote = ceil(exact / CENT) * CENT
                require(0 <= quote - CENT < exact <= quote
                        and exact == amount(threshold["exact_recovery_price_project"]) + holding_delta / retained,
                        "The holding sensitivity did not match the recovery price")
                prior_events = reference["dated_events"]
                sale_event, = [e for e in prior_events if e["category"] == "net_sale_distribution"]
                require(sale_event["date"] == when
                        and present_value(monthly_cash(prior_events, dates), rate) == reference_pv,
                        "The prior minimum's dated cash changed")
                probes = {}
                for label, price in (("at_cents", quote), ("one_cent_below", quote - CENT)):
                    fee = fixed_fee + price * SALE_COST_RATE
                    close, distribution = sale_closing(original, source, fee, when, free, gross_price=price)
                    net_sale = distribution * scale
                    events = [e | {"amount": rational(net_sale)} if e == sale_event else e for e in prior_events]
                    pv = present_value(monthly_cash(events, dates), rate)
                    receipts = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
                    contributions = sum(amount(e["amount"]) for e in events if e["kind"] == "contribution")
                    delta = ((price - reference_price) * retained - holding_delta) * scale
                    require(contributions == 10 and net_sale == amount(sale_event["amount"]) + delta
                            and pv == reference_pv + delta * discount
                            and (pv >= 0 if label == "at_cents" else pv < 0),
                            "The costed sale did not verify the recovery boundary")
                    probes[label] = dict(gross_price_project=rational(price), sale_cost_project=rational(fee),
                                         sale_net_per_usd_10=rational(net_sale),
                                         cash_total_received_per_usd_10=rational(receipts),
                                         present_value_per_usd_10=rational(pv),
                                         extra_contribution_per_usd_10=rational(contributions - 10),
                                         cash_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                                         dated_events=events, closing_sha256=close.sha256)
                thresholds.append(dict(monthly_rate=rational(rate), exact_recovery_price_project=rational(exact),
                                       minimum_sale_price_project=rational(quote), probes=probes))
            scenarios.append(dict(delay_months=delay, sale_date=when,
                                  total_holding_cost_project=rational(Fraction(holding_cost * delay)),
                                  debt_payoff_at_sale_project=rational(Fraction(0)),
                                  holding_cash=monthly_cash_balances, thresholds=thresholds))
        rows.append(dict(monthly_holding_cost_project=rational(Fraction(holding_cost)), scenarios=scenarios))

    return dict(status="passed", decision="PENDING", scope="synthetic_only",
                case_sha256=source["case_sha256"], refinance_cost_project=rational(REFINANCE_COST),
                refinance_net_per_usd_10=anchor["refinance_net_per_usd_10"], sale_cost_rate=rational(SALE_COST_RATE),
                fixed_sale_cost_project=rational(fixed_fee), discount_date=start.isoformat(),
                maturity_date=maturity.isoformat(), maturity_cash_payment_project=rational(payoff),
                loan_run_sha256=loan_sha, rows=rows)


def build_report():
    result = verify()
    lines = [
        ("Cada par muestra el precio bruto mínimo de venta / cobro total por USD 10 iniciales, en USD.", True),
        ("Refinanciación USD 175. Costo de venta USD 10 fijos + 5 % del precio. Sin ingresos extra de tenencia.", False),
        (f"El proyecto paga USD {money(result['maturity_cash_payment_project'])} de deuda el {result['maturity_date']}. Al vender, la deuda es USD 0.", False),
        ("La tenencia se paga con caja del proyecto. Se permiten precios por debajo de USD 300.", False),
        ("Demora y fecha de venta | 0 % mensual | 1 % mensual | 2 % mensual", True),
    ]
    for row in result["rows"]:
        lines.append((f"COSTO DE TENENCIA USD {money(row['monthly_holding_cost_project'])} POR MES", True))
        for s in row["scenarios"]:
            cells = []
            for t in s["thresholds"]:
                at = t["probes"]["at_cents"]
                require(amount(at["cash_unrecovered_per_usd_10"]) == 0, "An accepted price left cash unrecovered")
                cells.append(f"{money(t['minimum_sale_price_project'])} / {money(at['cash_total_received_per_usd_10'])}")
            lines.append((f"+{s['delay_months']} {'mes' if s['delay_months'] == 1 else 'meses'} | {s['sale_date']} | " + " | ".join(cells), False))
    lines.extend([
        ("Aportás USD 10 el 01/01/2027. Cobrás USD 1 el 01/03, USD 0,45 el 01/04 y USD 1 el 01/06.", False),
        ("Cobrás el resto en la fecha de venta indicada. Aportes extra USD 0,00.", False),
        ("Cada precio recupera lo aportado a su tasa. Un centavo menos queda corto. Decisión real pendiente.", True),
    ])
    pdf = render_page("D97 | Downside", lines, 21, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Tres costos de tenencia y precio mínimo de venta")
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
                          sale_probes=sum(len(t["probes"]) for t in thresholds), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
