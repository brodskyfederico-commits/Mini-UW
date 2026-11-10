"""Find the maximum synthetic refinance cost at a fixed USD 300 gross sale."""
from argparse import ArgumentParser
from fractions import Fraction
from math import floor
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value, validate_grid
from check_operating_replay_D20 import ROOT, amount, require
from check_worksheet_refinance_D45 import render_page
from fixed_sale_cash_D90 import SALE_PRICE, fixed_sale_spec
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import REFI_CATEGORIES, adjusted_parent, downside_sources, refi_net
from refinance_sale_combinations_D87 import fixed_events, sale_net
from sale_cost_rate_grid_D89 import FIXED_COST, SALE_RATES
from worksheet_sale_rate_grid_D84 import RATES, money


REPORT = "docs/review/MiniUW_D91_Costo_Maximo_Refi_Venta_300_USD10.pdf"


def verify():
    sources = downside_sources()
    base, variant, sale, selected, baseline = (
        sources[key] for key in ("base", "variant", "sale", "selected", "baseline"))
    archived = baseline["story"]
    baseline_flows = validate_grid(baseline)
    dates = [event["date"] for event in baseline_flows]
    refi_date, = {event["date"] for event in archived["dated_events"] if event["category"] in REFI_CATEGORIES}
    refi_index = dates.index(refi_date)
    sale_index = len(dates) - 1
    initial = amount(archived["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    original_cost = amount(variant["refinance_closing_costs"])
    archived_sale = amount(sale["replacement_claims"]["gross_proceeds"])
    archived_fee = amount(sale["replacement_claims"]["closing_costs_paid"])
    rows = []

    for sale_rate in SALE_RATES:
        fee = FIXED_COST + SALE_PRICE * sale_rate
        sale_spec = fixed_sale_spec(sale, fee)
        change_at_sale = (SALE_PRICE - fee) - (archived_sale - archived_fee)
        limits = []
        for rate in RATES:
            factor = 1 + rate
            pv_before_cut = present_value(baseline_flows, rate) + change_at_sale / factor**sale_index
            exact = original_cost + pv_before_cut * factor**refi_index
            maximum = Fraction(floor(exact * 100), 100)
            above = maximum + Fraction(1, 100)
            require(0 <= maximum <= exact < above <= original_cost, "Expected a lower nonnegative cost ceiling")
            probes = {}
            for label, cost in (("at_cents", maximum), ("one_cent_above", above)):
                parent, evidence = adjusted_parent(base, variant, sale_spec, cost)
                capacity = evidence.capacity_run.payload
                story = parent["story"]
                flows = validate_grid(parent)
                refi = refi_net(story)
                net_sale = sale_net(story)
                require(not capacity["blockers"]
                        and amount(capacity["selected_principal"]) == Fraction(selected["selected_principal"])
                        and amount(capacity["maximum_principal_capacity"]) == Fraction(selected["capacity"])
                        and [event["date"] for event in flows] == dates and fixed_events(story) == fixed_events(archived)
                        and refi == refi_net(archived) + original_cost - cost
                        and net_sale == sale_net(archived) + change_at_sale,
                        "The ceiling probe changed cash or capacity outside the declared costs")
                pv = present_value(flows, rate)
                require(pv == (exact - cost) / factor**refi_index
                        and (pv >= 0 if label == "at_cents" else pv < 0),
                        "The replay did not confirm the maximum to the cent")
                receipts = amount(story["gross_distributions"])
                contributions = sum(amount(event["amount"]) for event in story["dated_events"]
                                    if event["kind"] == "contribution")
                probes[label] = dict(refinance_cost_project=rational(cost),
                                     present_value_per_usd_10=rational(pv * scale),
                                     refinance_net_per_usd_10=rational(refi * scale),
                                     extra_contribution_per_usd_10=rational((contributions - initial) * scale),
                                     cash_unrecovered_per_usd_10=rational(max(0, contributions - receipts) * scale),
                                     sale_net_per_usd_10=rational(net_sale * scale),
                                     cash_total_received_per_usd_10=rational(receipts * scale),
                                     guarded_run_sha256=parent["guarded_run_sha256"])
            limits.append(dict(monthly_rate=rational(rate), exact_maximum_cost_project=rational(exact),
                               maximum_cost_project=rational(maximum),
                               minimum_cost_reduction_project=rational(original_cost - maximum), probes=probes))
        rows.append(dict(sale_cost_rate=rational(sale_rate), sale_cost_project=rational(fee), limits=limits))

    return dict(status="passed", decision="PENDING", scope="synthetic_only",
                case_sha256=sources["case_sha256"], sale_price_project=rational(SALE_PRICE),
                fixed_sale_cost_project=rational(FIXED_COST), original_refinance_cost_project=rational(original_cost),
                discount_date=dates[0], refinance_date=refi_date, sale_date=dates[-1],
                operating=[event for event in sources["cash"]["events"] if event["category"] == "operating_distribution"],
                rows=rows)


def build_report():
    result = verify()
    first, second = result["operating"]
    lines = [
        (f"Venta bruta fija USD {money(result['sale_price_project'])}. Costo de venta = USD {money(result['fixed_sale_cost_project'])} fijos + 3 %, 5 % o 7 %.", True),
        ("Cada par indica costo máximo de refinanciación del proyecto / cobro total por USD 10 iniciales.", False),
        ("Valores en USD. Cada máximo recupera los aportes en valor presente a la tasa de su columna.", False),
        ("Costo variable de venta | 0 % mensual | 1 % mensual | 2 % mensual", True),
    ]
    for row in result["rows"]:
        cells = []
        for threshold in row["limits"]:
            at = threshold["probes"]["at_cents"]
            require(amount(at["cash_unrecovered_per_usd_10"]) == 0, "The ceiling left cash unrecovered")
            cells.append(f"{money(threshold['maximum_cost_project'])} / {money(at['cash_total_received_per_usd_10'])}")
        lines.append((f"{amount(row['sale_cost_rate']) * 100} % | " + " | ".join(cells), True))

    lines.append(("APORTE O COBRO AL REFINANCIAR POR USD 10 INICIALES", True))
    for row in result["rows"]:
        cells = []
        for threshold in row["limits"]:
            net = threshold["probes"]["at_cents"]["refinance_net_per_usd_10"]
            direction = "Aportás" if amount(net) < 0 else "Cobrás"
            cells.append(f"{direction} {money(rational(abs(amount(net))))}")
        lines.append((f"{amount(row['sale_cost_rate']) * 100} % | " + " | ".join(cells), False))
    sale_values = " | ".join(
        f"{amount(row['sale_cost_rate']) * 100} %: USD {money(row['limits'][0]['probes']['at_cents']['sale_net_per_usd_10'])}"
        for row in result["rows"])
    lines.extend([
        (f"{result['discount_date']} aportás USD 10. {first['date']} cobrás USD {money(first['amount'])}.", False),
        (f"{result['refinance_date']} ocurre la refi de la tabla. {second['date']} cobrás USD {money(second['amount'])}.", False),
        (f"{result['sale_date']} cobrás neto de venta | {sale_values}", False),
        ("Al máximo quedan USD 0,00 sin recuperar. Un centavo más de costo deja faltante.", True),
        ("La operación y el préstamo se mantienen. Decisión real pendiente.", False),
    ])
    pdf = render_page("D91 | Downside", lines, 22, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Costo máximo de refinanciación con venta fija en USD 300")
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
    limits = [t for row in result["rows"] for t in row["limits"]]
    print(json.dumps(dict(status=result["status"], decision=result["decision"], combinations=len(limits),
                          closing_probes=sum(len(t["probes"]) for t in limits), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
