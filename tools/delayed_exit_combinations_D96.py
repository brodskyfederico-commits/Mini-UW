"""Verify mixed refinance-cost and sale-price changes after a synthetic sale delay."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from math import ceil
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from delayed_sale_carry_D93 import maturity_cash, sale_closing, verify as delayed_cases
from delayed_sale_recovery_D94 import CENT
from fixed_sale_delay_D92 import month_grid, monthly_cash
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import REFI_CATEGORIES, adjusted_parent, downside_sources, refi_net
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D96_Combinaciones_Refi_Venta_Demorada_USD10.pdf"
CUTS = (100, 125, 175)


def verify():
    carry = delayed_cases()
    source = downside_sources()
    start, maturity = (date.fromisoformat(carry[k]) for k in ("discount_date", "maturity_date"))
    original_sale, payoff, _, _, _, loan_sha = maturity_cash(source, maturity)
    require(carry["case_sha256"] == source["case_sha256"] and carry["loan_run_sha256"] == loan_sha
            and payoff == amount(carry["maturity_cash_payment_project"]), "The maturity and holding source changed")
    archived = source["baseline"]["story"]
    initial = amount(archived["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    variant = source["variant"]
    original_cost = amount(variant["refinance_closing_costs"])
    base_price = amount(carry["sale_price_project"])
    fixed_fee = amount(carry["fixed_sale_cost_project"])
    anchor_rows = [r for r in carry["rows"] if amount(r["refinance_cost_project"]) == original_cost]
    require(len(anchor_rows) == 3, "Expected all fee rows from the original refinance cost")
    rows = []
    for cut in CUTS:
        cost = original_cost - cut
        repriced, evidence = adjusted_parent(source["base"], variant, source["sale"], cost)
        refinance, sale = evidence.closings
        cap = evidence.capacity_run.payload
        selected = source["selected"]
        require(amount(cap["selected_principal"]) == Fraction(selected["selected_principal"])
                and amount(cap["maximum_principal_capacity"]) == Fraction(selected["capacity"])
                and not cap["blockers"] and json.loads(sale.closing_raw) == original_sale
                and sale.loans[0].run.sha256 == loan_sha
                and refi_net(repriced["story"]) == refi_net(archived) + cut,
                "The mixed adjustment changed the loan, maturity or retained cash")
        refi_events = [dict(date=e["date"], kind=e["kind"], category=e["category"],
                            amount=rational(amount(e["amount"]) * scale))
                       for e in repriced["story"]["dated_events"] if e["category"] in REFI_CATEGORIES and amount(e["amount"])]
        refi_date, = {e["date"] for e in refi_events}
        for anchor in anchor_rows:
            fee_rate = amount(anchor["sale_cost_rate"])
            slope = (1 - fee_rate) * scale
            require(slope > 0, "The sale fee leaves no positive marginal proceeds")
            scenarios = []
            for scenario in anchor["scenarios"]:
                when = scenario["sale_date"]
                dates = month_grid(start, date.fromisoformat(when))
                refi_index, sale_index = dates.index(refi_date), len(dates) - 1
                base_events = scenario["dated_events"]
                sale_event, = [e for e in base_events if e["category"] == "net_sale_distribution"]
                base_net = amount(sale_event["amount"])
                free = amount(scenario["holding_expenses"][-1]["free_cash_after_project"])
                require(sale_event["date"] == when and amount(scenario["debt_payoff_at_sale_project"]) == 0
                        and free == amount(carry["cash_after_maturity_project"]) - amount(scenario["total_holding_cost_project"]),
                        "The mixed scenario changed holding cash or the sale debt")
                before_sale = [e for e in base_events if e != sale_event and e["category"] not in REFI_CATEGORIES] + refi_events
                before_sale.sort(key=lambda e: e["date"])
                thresholds = []
                for gap in scenario["gaps"]:
                    rate = amount(gap["monthly_rate"])
                    factor = 1 + rate
                    pv_after_cut = amount(gap["present_value_per_usd_10"]) + cut * scale / factor**refi_index
                    target = base_price - pv_after_cut * factor**sale_index / slope
                    price = max(base_price, ceil(target / CENT) * CENT)
                    sample_prices = {"at_minimum": price}
                    if price > base_price:
                        sample_prices["one_cent_below"] = price - CENT
                    probes = {}
                    for label, quote in sample_prices.items():
                        fee = fixed_fee + quote * fee_rate
                        close, distribution = sale_closing(original_sale, source, fee, when, free, gross_price=quote)
                        net_sale = distribution * scale
                        events = before_sale + [sale_event | {"amount": rational(net_sale)}]
                        pv = present_value(monthly_cash(events, dates), rate)
                        contributions = sum(amount(e["amount"]) for e in events if e["kind"] == "contribution")
                        receipts = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
                        require(net_sale == base_net + (quote - base_price) * slope
                                and pv == pv_after_cut + (net_sale - base_net) / factor**sale_index
                                and (pv >= 0 if label == "at_minimum" else pv < 0),
                                "The repriced sale failed to confirm the recovery boundary")
                        probes[label] = dict(gross_sale_project=rational(quote), closing_fee_project=rational(fee),
                                             present_value_per_usd_10=rational(pv), sale_net_per_usd_10=rational(net_sale),
                                             cash_total_received_per_usd_10=rational(receipts),
                                             extra_contribution_per_usd_10=rational(contributions - 10),
                                             cash_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                                             dated_events=events, closing_sha256=close.sha256)
                    thresholds.append(dict(monthly_rate=rational(rate), exact_recovery_price_project=rational(target),
                                           minimum_sale_at_or_above_base_project=rational(price),
                                           price_increase_project=rational(price - base_price), probes=probes))
                scenarios.append({key: scenario[key] for key in ("delay_months", "sale_date", "total_holding_cost_project",
                                                                  "debt_payoff_at_sale_project")}
                                 | {"thresholds": thresholds})
            rows.append(dict(refinance_cost_project=rational(cost), refinance_cost_reduction_project=rational(Fraction(cut)),
                             refinance_net_per_usd_10=rational(refi_net(repriced["story"]) * scale),
                             refinance_closing_sha256=refinance.closing_run.sha256,
                             sale_cost_rate=anchor["sale_cost_rate"], scenarios=scenarios))

    return {key: value for key, value in carry.items() if key != "rows"} | {
        "original_refinance_cost_project": rational(original_cost), "rows": rows}


def build_report():
    result = verify()
    lines = [
        ("Combinaciones para recuperar lo aportado por USD 10 iniciales.", True),
        ("Venta de referencia USD 300. Si ese precio alcanza, la tabla indica 300,00.", False),
        ("Tenencia USD 20/mes. Se paga deuda de USD 56,00 el 01/07/2027. Deuda al vender USD 0.", False),
        ("Costo de venta USD 10 + el porcentaje indicado. Cada grupo usa tasas del 0 % / 1 % / 2 % mensual.", False),
        ("Costo variable de venta | +1 mes (01/08) | +2 meses (01/09) | +3 meses (01/10)", True),
    ]
    prior = None
    for row in result["rows"]:
        cost = row["refinance_cost_project"]
        if cost != prior:
            lines.append((f"REFI USD {money(cost)} | REBAJA USD {money(row['refinance_cost_reduction_project'])} | PRECIO BRUTO DE VENTA", True))
            prior = cost
        groups = [" / ".join(money(t["minimum_sale_at_or_above_base_project"]) for t in s["thresholds"])
                  for s in row["scenarios"]]
        lines.append((" | ".join([f"{amount(row['sale_cost_rate']) * 100} %", *groups]), False))

    example = result["rows"][4]
    lines.append(("COBRO TOTAL POR USD 10 | REFI USD 175 | COSTO DE VENTA USD 10 + 5 %", True))
    for s in example["scenarios"]:
        total = " / ".join(money(t["probes"]["at_minimum"]["cash_total_received_per_usd_10"])
                           for t in s["thresholds"])
        lines.append((f"{s['sale_date']} | USD {total} al 0 % / 1 % / 2 % mensual", False))
    lines.extend([
        ("Ejemplo: cobrás USD 1 en marzo, USD 0,45 en abril, USD 1 en junio y el resto al vender.", False),
        ("Sin aporte extra en las combinaciones probadas. Las fechas de venta son de 2027.", False),
        ("Si el precio supera USD 300, un centavo por debajo del mínimo queda corto. Decisión real pendiente.", False),
    ])
    pdf = render_page("D96 | Downside", lines, 18, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Combinaciones de refinanciación y venta demorada")
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
