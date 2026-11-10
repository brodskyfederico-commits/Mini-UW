"""Audit Downside receipts and recovery gaps at a fixed synthetic USD 300 sale."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value, validate_grid
from check_integrated_participation_D28 import ledger
from check_operating_replay_D20 import ROOT, amount, require
from check_participant_joint_exit_D32 import replay_sale
from check_participant_refinance_variants_D31 import set_claim
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import REFI_CATEGORIES, adjusted_parent, downside_sources, refi_net
from refinance_sale_combinations_D87 import CUTS, fixed_events, sale_net
from sale_cost_rate_grid_D89 import FIXED_COST, SALE_RATES
from worksheet_sale_rate_grid_D84 import RATES, money


REPORT = "docs/review/MiniUW_D90_Venta_Fija_300_USD10.pdf"
SALE_PRICE = Fraction(300)


def fixed_sale_spec(sale, sale_cost):
    claims = {key: value.copy() for key, value in sale["replacement_claims"].items()}
    set_claim(claims["gross_proceeds"], SALE_PRICE, "SYNTHETIC-D90-fixed-price")
    set_claim(claims["closing_costs_paid"], sale_cost, "SYNTHETIC-D90-price-linked-cost")
    return sale | {"revision_id": "SYNTHETIC-D90-fixed-price", "replacement_claims": claims}


def verify():
    sources = downside_sources()
    base, variant, sale, selected, baseline = (
        sources[key] for key in ("base", "variant", "sale", "selected", "baseline"))
    baseline_story = baseline["story"]
    baseline_flows = validate_grid(baseline)
    dates = [event["date"] for event in baseline_flows]
    refi_date, = {event["date"] for event in baseline_story["dated_events"]
                  if event["category"] in REFI_CATEGORIES}
    refi_index = dates.index(refi_date)
    sale_index = len(dates) - 1
    initial = amount(baseline_story["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    original_refi_cost = amount(variant["refinance_closing_costs"])
    original_sale_price = amount(sale["replacement_claims"]["gross_proceeds"])
    original_sale_cost = amount(sale["replacement_claims"]["closing_costs_paid"])
    cases = []

    for cut in CUTS:
        refi_cost = original_refi_cost - cut
        _, evidence = adjusted_parent(base, variant, sale, refi_cost)
        guarded = evidence.guarded_run
        capacity = evidence.capacity_run.payload
        require(not capacity["blockers"]
                and amount(capacity["selected_principal"]) == Fraction(selected["selected_principal"])
                and amount(capacity["maximum_principal_capacity"]) == Fraction(selected["capacity"]),
                "The fixed sale case changed loan sizing or capacity")
        origin = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))

        for sale_rate in SALE_RATES:
            sale_cost = FIXED_COST + SALE_PRICE * sale_rate
            _, parent = replay_sale(evidence, fixed_sale_spec(sale, sale_cost), origin, False)
            story = parent["story"]
            flows = validate_grid(parent)
            change_at_sale = SALE_PRICE - sale_cost - (original_sale_price - original_sale_cost)
            require([event["date"] for event in flows] == dates
                    and fixed_events(story) == fixed_events(baseline_story)
                    and refi_net(story) == refi_net(baseline_story) + cut
                    and sale_net(story) == sale_net(baseline_story) + change_at_sale,
                    "The closing changed cash outside the specified refinance and sale costs")

            receipts = amount(story["gross_distributions"]) * scale
            events = [event | {"amount": rational(amount(event["amount"]) * scale)}
                      for event in story["dated_events"] if amount(event["amount"])]
            contributions = sum(amount(event["amount"]) for event in events if event["kind"] == "contribution")
            require(receipts == sum(amount(event["amount"]) for event in events if event["kind"] == "distribution"),
                    "Receipt total differs from the dated cash")
            gaps = []
            for rate in RATES:
                pv = present_value(flows, rate) * scale
                factor = 1 + rate
                expected = present_value(baseline_flows, rate) + cut / factor**refi_index + change_at_sale / factor**sale_index
                require(pv == expected * scale and (rate != 0 or pv == receipts - contributions),
                        "The present value did not reconcile with the baseline and dated changes")
                gaps.append(dict(monthly_rate=rational(rate), present_value_per_usd_10=rational(pv)))
            cases.append(dict(refinance_cost_project=rational(refi_cost),
                              sale_cost_rate=rational(sale_rate), sale_cost_project=rational(sale_cost),
                              sale_net_per_usd_10=rational(sale_net(story) * scale),
                              cash_total_received_per_usd_10=rational(receipts),
                              extra_contribution_per_usd_10=rational(contributions - 10),
                              nominal_cash_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                              gaps=gaps, dated_events=events, guarded_run_sha256=parent["guarded_run_sha256"]))

    return dict(status="passed", decision="PENDING", scope="synthetic_only",
                case_sha256=sources["case_sha256"], sale_price_project=rational(SALE_PRICE),
                fixed_sale_cost_project=rational(FIXED_COST), discount_date=dates[0],
                refinance_date=refi_date, sale_date=dates[-1], cases=cases)


def build_report():
    result = verify()
    lines = [
        (f"Venta bruta fija USD {money(result['sale_price_project'])}. Costos de venta = USD {money(result['fixed_sale_cost_project'])} fijos + 3 %, 5 % o 7 %.", True),
        ("Todos los cobros y saldos de la tabla están en USD por USD 10 iniciales.", False),
        ("El saldo descuenta aportes y cobros al 01/01/2027. Positivo = sobra. Negativo = falta.", False),
        ("Costo de venta | Neto al vender | Cobro total | Saldo 0 % | Saldo 1 % | Saldo 2 % mensual", True),
    ]
    for index, case in enumerate(result["cases"]):
        if index % len(SALE_RATES) == 0:
            lines.append((f"COSTO DE REFINANCIACIÓN DEL PROYECTO USD {money(case['refinance_cost_project'])}", True))
        gaps = [f"+{money(g['present_value_per_usd_10'])}" if amount(g["present_value_per_usd_10"]) > 0
                else money(g["present_value_per_usd_10"]) for g in case["gaps"]]
        fields = [f"{amount(case['sale_cost_rate']) * 100} %",
                  money(case["sale_net_per_usd_10"]), money(case["cash_total_received_per_usd_10"]), *gaps]
        lines.append((" | ".join(fields), False))
    lines.extend([
        ("Aportás USD 10 el 01/01/2027. Cobrás USD 1,00 el 01/03 y USD 1,00 el 01/06.", False),
        ("Refi 01/04 por USD 10 | Costo 300 aportás 0,80 | Costo 220 saldo cero | Costo 150 cobrás 0,70", False),
        (f"El {result['sale_date']} cobrás el neto de venta indicado. El saldo al 0 % es la diferencia en caja.", False),
        ("Simulación de Downside. Decisión real pendiente.", False),
    ])
    pdf = render_page("D90 | Downside", lines, 21, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Venta fija y tres tasas de costo de venta")
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
    print(json.dumps(dict(status=result["status"], decision=result["decision"],
                          closings=len(result["cases"]), combinations=sum(len(case["gaps"]) for case in result["cases"]),
                          one_page_report=result["page_count"] == 1, pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
