"""Find the minimum refinance cost reduction at a fixed synthetic delayed sale price."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from math import ceil
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_participant_refinance_variants_D31 import build_variant_evidence
from check_worksheet_refinance_D45 import render_page
from delayed_sale_carry_D93 import maturity_cash, verify as delayed_cases
from fixed_sale_delay_D92 import month_grid, monthly_cash
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import REFI_CATEGORIES, downside_sources
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D95_Rebaja_Refi_Venta_Demorada_300_USD10.pdf"
CENT = Fraction(1, 100)


def verify():
    carry = delayed_cases()
    source = downside_sources()
    start, maturity = (date.fromisoformat(carry[k]) for k in ("discount_date", "maturity_date"))
    original_closing, payoff, _, _, _, loan_sha = maturity_cash(source, maturity)
    require(carry["case_sha256"] == source["case_sha256"] and carry["loan_run_sha256"] == loan_sha
            and amount(carry["maturity_cash_payment_project"]) == payoff, "The debt and holding source changed")
    variant = source["variant"]
    original_cost = amount(variant["refinance_closing_costs"])
    initial = amount(source["baseline"]["story"]["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    selected = source["selected"]
    refi_date, = {e["date"] for e in source["baseline"]["story"]["dated_events"] if e["category"] in REFI_CATEGORIES}
    rows = []
    for row in carry["rows"]:
        if amount(row["refinance_cost_project"]) != original_cost:
            continue
        scenarios = []
        for scenario in row["scenarios"]:
            events = scenario["dated_events"]
            baseline_flows = month_grid(start, date.fromisoformat(scenario["sale_date"]))
            refi_index = baseline_flows.index(refi_date)
            prior = [e for e in events if e["category"] not in REFI_CATEGORIES]
            refi_net = sum((1 if e["kind"] == "distribution" else -1) * amount(e["amount"])
                           for e in events if e["category"] in REFI_CATEGORIES)
            thresholds = []
            for gap in scenario["gaps"]:
                rate = amount(gap["monthly_rate"])
                discount = (1 + rate)**-refi_index
                baseline_pv = amount(gap["present_value_per_usd_10"])
                exact = -baseline_pv / (scale * discount)
                cut = ceil(exact / CENT) * CENT
                require(0 <= cut - CENT < exact <= cut <= original_cost, "Expected an achievable positive cost reduction")
                probes = {}
                for label, reduction in (("at_cents", cut), ("one_cent_below", cut - CENT)):
                    cost = original_cost - reduction
                    spec = variant | {"refinance_closing_costs": rational(cost), "variant_id": "SYNTHETIC-D86-refinance-cost"}
                    evidence = build_variant_evidence(source["base"], spec)
                    cap = evidence.capacity_run.payload
                    refinance, sale = evidence.closings
                    closing = refinance.closing_run.payload
                    require(not cap["blockers"] and evidence.guarded_run.investor_run is not None
                            and closing["decision"] == evidence.guarded_run.payload["decision"] == "PENDING"
                            and amount(cap["selected_principal"]) == Fraction(selected["selected_principal"])
                            and amount(cap["maximum_principal_capacity"]) == Fraction(selected["capacity"])
                            and closing["closing_date"] == refi_date
                            and json.loads(sale.closing_raw) == original_closing
                            and sale.loans[0].run.sha256 == loan_sha,
                            "The refinance cost probe changed the loan, maturity, or pre-hold cash")
                    receipt = amount(closing["exportable_equity_distribution"]) * scale
                    contribution = amount(closing["exportable_equity_contribution"]) * scale
                    repriced = prior.copy()
                    for kind, category, value in (("distribution", "net_refinance_distribution", receipt),
                                                   ("contribution", "refinance_cash_in", contribution)):
                        if value:
                            repriced.append(dict(date=refi_date, kind=kind, category=category, amount=rational(value)))
                    repriced.sort(key=lambda e: e["date"])
                    pv = present_value(monthly_cash(repriced, baseline_flows), rate)
                    receipts = sum(amount(e["amount"]) for e in repriced if e["kind"] == "distribution")
                    contributions = sum(amount(e["amount"]) for e in repriced if e["kind"] == "contribution")
                    require(receipt - contribution == refi_net + reduction * scale
                            and pv == baseline_pv + reduction * scale * discount
                            and (pv >= 0 if label == "at_cents" else pv < 0),
                            "The refinance cent boundary did not reconcile with the delayed cash")
                    probes[label] = dict(refinance_cost_project=rational(cost), reduction_project=rational(reduction),
                                         present_value_per_usd_10=rational(pv),
                                         refinance_net_per_usd_10=rational(receipt - contribution),
                                         extra_contribution_per_usd_10=rational(contributions - 10),
                                         cash_total_received_per_usd_10=rational(receipts),
                                         cash_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                                         dated_events=repriced, refinance_closing_sha256=refinance.closing_run.sha256)
                thresholds.append(dict(monthly_rate=rational(rate), exact_reduction_project=rational(exact),
                                       minimum_reduction_project=rational(cut), maximum_cost_project=rational(original_cost - cut),
                                       probes=probes))
            scenarios.append({key: scenario[key] for key in ("delay_months", "sale_date", "total_holding_cost_project",
                                                              "debt_payoff_at_sale_project", "sale_net_per_usd_10")}
                             | {"thresholds": thresholds})
        rows.append(dict(sale_cost_rate=row["sale_cost_rate"], scenarios=scenarios))
    require(len(rows) == 3, "Expected all three fee rows for the original refinance cost")
    return {key: value for key, value in carry.items() if key != "rows"} | {
        "original_refinance_cost_project": rational(original_cost), "refinance_date": refi_date, "rows": rows}


def build_report():
    result = verify()
    lines = [
        (f"Venta USD {money(result['sale_price_project'])}. Rebaja mínima desde un costo de refi de USD {money(result['original_refinance_cost_project'])}.", True),
        ("Costo de venta USD 10 fijos + porcentaje indicado. Tenencia USD 20 por mes, sin ingreso extra.", False),
        ("El proyecto paga USD 56,00 de deuda el 01/07/2027. La deuda al vender es USD 0.", False),
        ("Cada grupo muestra la rebaja en USD del proyecto al 0 % / 1 % / 2 % mensual.", False),
        ("Costo variable de venta | +1 mes (01/08) | +2 meses (01/09) | +3 meses (01/10)", True),
    ]
    for row in result["rows"]:
        cells = [" / ".join(money(t["minimum_reduction_project"]) for t in s["thresholds"])
                 for s in row["scenarios"]]
        lines.append((" | ".join([f"{amount(row['sale_cost_rate']) * 100} %", *cells]), True))
    example = result["rows"][1]
    lines.append(("EJEMPLO POR USD 10 INICIALES CON COSTO DE VENTA DE USD 10 + 5 %", True))
    lines.append(("Fecha de venta | Refi máxima al 1 % | Cobro total al 0 % / 1 % / 2 %", True))
    for s in example["scenarios"]:
        max_cost = money(s["thresholds"][1]["maximum_cost_project"])
        totals = " / ".join(money(t["probes"]["at_cents"]["cash_total_received_per_usd_10"]) for t in s["thresholds"])
        lines.append((f"{s['sale_date']} | USD {max_cost} | USD {totals}", False))
    refi_values = " / ".join(money(s["thresholds"][1]["probes"]["at_cents"]["refinance_net_per_usd_10"])
                             for s in example["scenarios"])
    sale_values = " / ".join(money(s["sale_net_per_usd_10"]) for s in example["scenarios"])
    lines.extend([
        ("Aportás USD 10 el 01/01/2027. Cobrás USD 1 el 01/03 y otro USD 1 el 01/06.", False),
        (f"Al 1 % mensual cobrás en la refi del 01/04 USD {refi_values}, según la demora.", False),
        (f"Cobrás al vender USD {sale_values}, según la demora. En este ejemplo no hay aporte extra.", False),
        ("Al mínimo quedan USD 0,00 sin recuperar. Un centavo menos de rebaja deja un faltante.", True),
        ("Simulación de Downside. Decisión real pendiente.", False),
    ])
    pdf = render_page("D95 | Downside", lines, 21, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Rebaja de refinanciación con venta fija y demorada")
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
