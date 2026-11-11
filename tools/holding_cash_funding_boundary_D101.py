"""Audit the first holding cash shortfall and an explicit synthetic equity contribution."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from delayed_sale_carry_D93 import maturity_cash, sale_closing
from extended_holding_sale_D99 import verify as extended_cases
from fixed_sale_delay_D92 import add_months, month_grid, monthly_cash, signed
from fixed_sale_holding_grid_D98 import SALE_PRICE
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import downside_sources
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D101_Aporte_Al_Agotarse_Caja_USD10.pdf"


def verify():
    baseline = extended_cases()
    source = downside_sources()
    start, maturity = (date.fromisoformat(baseline[k]) for k in ("discount_date", "maturity_date"))
    original, payoff, _, _, _, loan_sha = maturity_cash(source, maturity)
    after_payoff = amount(original["amounts"]["opening_free_cash"]) - payoff
    require(source["case_sha256"] == baseline["case_sha256"] and loan_sha == baseline["loan_run_sha256"]
            and payoff == amount(baseline["maturity_cash_payment_project"])
            and after_payoff == amount(baseline["cash_after_maturity_project"]),
            "The original debt payment or cash reserve changed")
    scale = Fraction(10) / amount(source["baseline"]["story"]["cash_by_category"]["initial_capital"])
    fee_rate = amount(baseline["sale_cost_rate"])
    sale_fee = amount(baseline["fixed_sale_cost_project"]) + SALE_PRICE * fee_rate
    rows = []

    for row in baseline["rows"]:
        holding = amount(row["monthly_holding_cost_project"])
        last = row["full_months_funded_from_retained_cash"]
        boundary = row["first_unfunded_month"]
        reference = row["scenarios"][-1]
        reference_close = reference["thresholds"][0]["probes"]["at_cents"]
        sale_event, = [e for e in reference_close["dated_events"] if e["category"] == "net_sale_distribution"]
        prior = [e for e in reference_close["dated_events"] if e != sale_event]
        reference_free = amount(reference["holding_cash"][-1]["free_cash_after_project"])
        require(boundary["month"] == last + 1 and boundary["state"] == "PENDING"
                and after_payoff - last * holding >= 0 > after_payoff - (last + 1) * holding,
                "The prior cash funding boundary changed")
        scenarios = []
        for delay in (last, last + 1, last + 2):
            sale_date = add_months(maturity, delay)
            when = sale_date.isoformat()
            free = after_payoff
            cash = []
            contributions = []
            total_injected = Fraction()
            for month in range(1, delay + 1):
                pay_date = add_months(maturity, month).isoformat()
                injection = max(Fraction(), holding - free)
                free += injection - holding
                total_injected += injection
                if injection > 0:
                    contributions.append(dict(date=pay_date, kind="contribution", category="additional_capital",
                                              amount=rational(injection * scale)))
                cash.append(dict(date=pay_date, expense_project=rational(holding),
                                 equity_injection_project=rational(injection), free_cash_after_project=rational(free)))
            require(free == max(Fraction(), after_payoff - delay * holding)
                    and total_injected == max(Fraction(), delay * holding - after_payoff)
                    and len(contributions) == delay - last,
                    "The contribution does not cover the holding cash deficit exactly")
            if contributions:
                require(amount(contributions[0]["amount"]) == amount(boundary["cash_required_project"]) * scale,
                        "The first contribution changed the previously verified shortfall")
            close, distribution = sale_closing(original, source, sale_fee, when, free, gross_price=SALE_PRICE)
            net_sale = distribution * scale
            events = prior + contributions + [sale_event | {"date": when, "amount": rational(net_sale)}]
            flow = monthly_cash(events, month_grid(start, sale_date))
            paid = sum(amount(e["amount"]) for e in events if e["kind"] == "contribution")
            received = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
            change = ((SALE_PRICE - amount(reference_close["gross_price_project"])) * (1 - fee_rate)
                      + free - reference_free) * scale
            require(net_sale == amount(reference_close["sale_net_per_usd_10"]) + change
                    and paid == 10 + total_injected * scale and received == Fraction("2.45") + net_sale,
                    "The contribution or receipt does not reconcile to the USD 10 basis")
            gaps = [dict(monthly_rate=t["monthly_rate"],
                         present_value_per_usd_10=rational(present_value(flow, amount(t["monthly_rate"]))))
                    for t in reference["thresholds"]]
            require(amount(gaps[0]["present_value_per_usd_10"]) == received - paid,
                    "The nominal gap differs from paid and received cash")
            without_terms = (dict(state=boundary["state"], blocker=boundary["blocker"],
                                  first_required_project=boundary["cash_required_project"],
                                  cash_total_received_per_usd_10=None, gaps=None)
                             if contributions else None)
            scenarios.append(dict(delay_months=delay, sale_date=when, holding_cash=cash,
                                  debt_payoff_at_sale_project=rational(Fraction()),
                                  additional_equity_project=rational(total_injected),
                                  extra_contribution_per_usd_10=rational(total_injected * scale),
                                  sale_net_per_usd_10=rational(net_sale), cash_total_received_per_usd_10=rational(received),
                                  nominal_unrecovered_per_usd_10=rational(max(Fraction(), paid - received)),
                                  dated_events=events, gaps=gaps, closing_sha256=close.sha256,
                                  without_funding_terms=without_terms))
        rows.append(dict(monthly_holding_cost_project=row["monthly_holding_cost_project"], scenarios=scenarios))

    return {key: value for key, value in baseline.items() if key != "rows"} | dict(
        sale_price_project=rational(SALE_PRICE), sale_cost_project=rational(sale_fee),
        funding_assumption="synthetic_pro_rata_equity_same_share_contributed_before_holding_cost", rows=rows)


def build_report():
    result = verify()
    lines = [
        ("Venta bruta USD 300. Refi USD 175. Costo de venta USD 25. Deuda pagada USD 56,00 el 01/07/2027.", False),
        ("La caja remanente paga la tenencia. El ejemplo aporta solo el faltante a prorrata, con la misma participación.", False),
        ("El aporte del mes se paga antes del gasto y del cierre. Sin términos de financiación, el faltante queda PENDING.", False),
        ("USD por USD 10 iniciales. + indica sobrante. - indica faltante descontado al 01/01/2027.", False),
        ("Mes / fecha de venta | Aporte extra total | Neto venta | Cobro total | Saldo 0 % / 1 % / 2 % mensual", True),
    ]
    for row in result["rows"]:
        lines.append((f"TENENCIA USD {money(row['monthly_holding_cost_project'])} POR MES", True))
        for s in row["scenarios"]:
            gaps = " / ".join(signed(g["present_value_per_usd_10"]) for g in s["gaps"])
            lines.append((f"{s['delay_months']} / {s['sale_date']} | {money(s['extra_contribution_per_usd_10'])} | "
                          f"{money(s['sale_net_per_usd_10'])} | {money(s['cash_total_received_per_usd_10'])} | {gaps}", False))
    lines.extend([
        ("En 2027 aportás USD 10 en enero. Cobrás USD 1 en marzo, USD 0,45 en abril y USD 1 en junio.", False),
        ("Primer aporte en el mes 33, 17 u 11 según tenencia de USD 10, 20 o 30 por mes.", False),
        ("Si esperás otro mes, agregás USD 0,10, USD 0,20 o USD 0,30 por USD 10, respectivamente.", False),
        ("El neto de venta se cobra en la fecha indicada. Escenarios sintéticos. Decisión real pendiente.", True),
    ])
    pdf = render_page("D101 | Downside", lines, 20, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Aporte adicional al agotarse la caja de tenencia")
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
    scenarios = [s for row in result["rows"] for s in row["scenarios"]]
    print(json.dumps(dict(status=result["status"], decision=result["decision"], closings=len(scenarios),
                          pending_without_funding=sum(s["without_funding_terms"] is not None for s in scenarios),
                          combinations=sum(len(s["gaps"]) for s in scenarios), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
