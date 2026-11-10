"""Measure the timing-only effect of delaying a synthetic USD 300 sale receipt."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from fixed_sale_cash_D90 import verify as fixed_sale_cases
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D92_Demora_Venta_300_USD10.pdf"
DELAYS = (1, 2, 3)


def add_months(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, month + 1, day.day)


def month_grid(first, last):
    count = (last.year - first.year) * 12 + last.month - first.month
    require(count >= 0 and first.day == last.day, "Expected a same-day monthly grid")
    return [add_months(first, i).isoformat() for i in range(count + 1)]


def monthly_cash(events, dates):
    by_date = dict.fromkeys(dates, Fraction())
    for event in events:
        require(event["date"] in by_date and event["kind"] in {"contribution", "distribution"},
                "Dated cash falls outside the declared monthly grid")
        sign = 1 if event["kind"] == "distribution" else -1
        by_date[event["date"]] += sign * amount(event["amount"])
    return [{"date": when, "net": rational(value)} for when, value in by_date.items()]


def verify():
    baseline = fixed_sale_cases()
    start, original_sale = (date.fromisoformat(baseline[key]) for key in ("discount_date", "sale_date"))
    original_dates = month_grid(start, original_sale)
    rows = []
    for case in baseline["cases"]:
        events = case["dated_events"]
        sale_receipt, = [e for e in events if e["category"] == "net_sale_distribution"]
        require(sale_receipt["date"] == original_sale.isoformat()
                and sale_receipt["kind"] == "distribution"
                and amount(sale_receipt["amount"]) == amount(case["sale_net_per_usd_10"])
                and amount(sale_receipt["amount"]) > 0
                and all(date.fromisoformat(e["date"]) < original_sale for e in events if e != sale_receipt),
                "Expected a single positive sale receipt after the earlier cash events")
        nominal_receipts = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
        require(nominal_receipts == amount(case["cash_total_received_per_usd_10"]),
                "The nominal receipts did not reconcile")
        original_flows = monthly_cash(events, original_dates)
        delayed = []
        for delay in DELAYS:
            sale_date = add_months(original_sale, delay)
            dates = month_grid(start, sale_date)
            moved = [e | {"date": sale_date.isoformat()} if e == sale_receipt else e for e in events]
            flows = monthly_cash(moved, dates)
            require([e | {"date": original_sale.isoformat()} if e["category"] == "net_sale_distribution" else e
                     for e in moved] == events and present_value(flows, Fraction()) == present_value(original_flows, Fraction()),
                    "The delay changed an amount or a pre-sale cash event")
            gaps = []
            for baseline_gap in case["gaps"]:
                rate = amount(baseline_gap["monthly_rate"])
                original_pv = amount(baseline_gap["present_value_per_usd_10"])
                pv = present_value(flows, rate)
                factor = 1 + rate
                original_index = len(original_dates) - 1
                sale_index = len(dates) - 1
                loss = amount(sale_receipt["amount"]) * (factor**-original_index - factor**-sale_index)
                require(original_pv == present_value(original_flows, rate)
                        and pv == original_pv - loss and (loss > 0 if rate else loss == 0),
                        "Repriced cash does not reconcile with the isolated sale receipt shift")
                gaps.append(dict(monthly_rate=rational(rate), present_value_per_usd_10=rational(pv),
                                 present_value_lost_vs_on_time_per_usd_10=rational(loss)))
            delayed.append(dict(delay_months=delay, sale_date=sale_date.isoformat(),
                                dated_events=moved, gaps=gaps))
        rows.append({key: value for key, value in case.items() if key not in {"dated_events", "gaps"}}
                    | {"on_time_gaps": case["gaps"], "delays": delayed})

    return dict(status="passed", decision="PENDING", scope="synthetic_timing_only",
                sale_price_project=baseline["sale_price_project"], fixed_sale_cost_project=baseline["fixed_sale_cost_project"],
                case_sha256=baseline["case_sha256"], discount_date=baseline["discount_date"],
                refinance_date=baseline["refinance_date"], original_sale_date=baseline["sale_date"],
                incremental_holding_cash_mode="assumed_zero_for_timing_isolation", rows=rows)


def signed(value):
    return ("+" if amount(value) > 0 else "") + money(value)


def build_report():
    result = verify()
    rows = result["rows"]
    dates = [d["sale_date"] for d in rows[0]["delays"]]
    lines = [
        (f"Venta bruta USD {money(result['sale_price_project'])}. Costo de venta = USD {money(result['fixed_sale_cost_project'])} fijos + 3 %, 5 % o 7 %.", True),
        ("Solo se mueve el cobro neto de la venta. Se supone caja adicional de tenencia igual a cero.", False),
        ("Cobros y saldos en USD por USD 10 iniciales. En cada grupo de tres: 0 % / 1 % / 2 % mensual.", False),
        ("Saldo en valor presente al 01/01/2027. El signo + indica sobrante y el signo - indica faltante.", False),
        ("Costo venta | Neto venta / total cobrado | +1 mes | +2 meses | +3 meses", True),
    ]
    prior = None
    for row in rows:
        cost = row["refinance_cost_project"]
        if cost != prior:
            lines.append((f"COSTO DE REFINANCIACIÓN DEL PROYECTO USD {money(cost)}", True))
            prior = cost
        totals = f"{money(row['sale_net_per_usd_10'])} / {money(row['cash_total_received_per_usd_10'])}"
        gaps = [" / ".join(signed(g["present_value_per_usd_10"]) for g in d["gaps"]) for d in row["delays"]]
        lines.append((" | ".join([f"{amount(row['sale_cost_rate']) * 100} %", totals, *gaps]), False))
    lines.extend([
        (f"Venta original {result['original_sale_date']}. Con demora cobrás el {' / '.join(dates)}.", False),
        ("Aportás USD 10 en enero. Cobrás USD 1,00 el 01/03 y USD 1,00 el 01/06 de 2027.", False),
        ("Refi 01/04 | Costo 300 aportás 0,80 | Costo 220 saldo cero | Costo 150 cobrás 0,70", False),
        ("El cobro total se mantiene. El saldo al 0 % muestra la diferencia de caja nominal.", True),
        ("No se recalculan intereses, deuda ni operación del plazo extra. Decisión real pendiente.", False),
    ])
    pdf = render_page("D92 | Downside", lines, 20, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Demora de 1, 2 o 3 meses del cobro de venta")
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
    print(json.dumps(dict(status=result["status"], decision=result["decision"], sale_cost_variants=len(result["rows"]),
                          delay_cases=sum(len(row["delays"]) for row in result["rows"]),
                          combinations=sum(len(d["gaps"]) for row in result["rows"] for d in row["delays"]),
                          one_page_report=result["page_count"] == 1, pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
