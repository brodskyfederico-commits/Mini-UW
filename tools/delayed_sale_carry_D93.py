"""Reconcile delayed sale with synthetic holding expenses and the scheduled debt maturity."""
from argparse import ArgumentParser
from datetime import date
from fractions import Fraction
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, require
from check_participant_refinance_variants_D31 import set_claim
from check_worksheet_refinance_D45 import render_page
from fixed_sale_cash_D90 import fixed_sale_spec, verify as fixed_sale_cases
from fixed_sale_delay_D92 import DELAYS, add_months, month_grid, monthly_cash, signed
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from refinance_cost_recovery_D86 import adjusted_parent, downside_sources
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D93_Demora_Tenencia_Deuda_USD10.pdf"
MONTHLY_HOLDING_COST = Fraction(20)
PROVENANCE = "SYNTHETIC-D93-retained-cash-and-no-extension"


def maturity_cash(source, sale_date):
    _, evidence = adjusted_parent(source["base"], source["variant"], source["sale"],
                                  amount(source["variant"]["refinance_closing_costs"]))
    closing = evidence.closings[-1]
    loan, = closing.loans
    schedule = loan.run.payload["schedule"]
    final = schedule[-1]
    raw = json.loads(closing.closing_raw)
    debt, = raw["old_debts"]
    post = json.loads(evidence.periods[-1].spec_raw)["amounts"]
    scheduled_principal = amount(final["principal_due"]) + amount(final["balloon_due"])
    scheduled_interest = amount(final["interest_due"])
    require(not evidence.capacity_run.payload["blockers"] and loan.run.payload["schedule_state"] == "computed_synthetic"
            and closing.debt_run.payload["state"] == "matched_synthetic_debt_assumptions"
            and raw["closing_date"] == final["date"] == sale_date.isoformat()
            and amount(final["closing_balance"]) == 0 and scheduled_principal == amount(final["opening_balance"])
            and scheduled_principal == amount(debt["principal_paid"]) and scheduled_interest == amount(debt["interest_paid"])
            and amount(post["debt_principal_payment"]) + scheduled_principal == amount(schedule[0]["opening_balance"]),
            "Debt did not reconcile from the opening loan through its existing maturity")
    categories = ("principal", "interest", "fees", "other")
    require(all(amount(debt[f"{k}_due"]) == amount(debt[f"{k}_paid"])
                and debt[f"{k}_paid"]["as_of_date"] == sale_date.isoformat() for k in categories)
            and amount(debt["other_paid"]) == 0, "The stated dated debt charges did not reconcile")
    fees = amount(debt["fees_paid"])
    payoff = scheduled_principal + scheduled_interest + fees
    opening_free = amount(raw["amounts"]["opening_free_cash"])
    require(opening_free == amount(post["closing_free_cash_claim"]) and opening_free >= payoff,
            "The retained free cash cannot cover the scheduled maturity")
    return raw, payoff, scheduled_principal, scheduled_interest, fees, loan.run.sha256


def sale_closing(original, source, fee, when, opening_cash, *, gross_price=None):
    spec = fixed_sale_spec(source["sale"], fee)
    closing = original | {"closing_date": when, "old_debts": [], "valuation_claim": None}
    closing["amounts"] = {key: claim | {"as_of_date": when} for key, claim in
                          (original["amounts"] | spec["replacement_claims"]).items()}
    set_claim(closing["amounts"]["opening_free_cash"], opening_cash, PROVENANCE)
    if gross_price is not None:
        set_claim(closing["amounts"]["gross_proceeds"], gross_price, "SYNTHETIC-D94-repriced-sale")
    run = produce_closing_cash(encoded(closing))
    payload = run.payload
    require(payload["state"] == "computed_synthetic_closing" and payload["decision"] == "PENDING"
            and not payload["blockers"] and amount(payload["total_cash_conservation_residual"]) == 0
            and amount(payload["exportable_equity_contribution"]) == 0
            and all(amount(value) == 0 for value in payload["payoff_totals"].values()),
            "Delayed close has unresolved cash, capital or debt")
    return run, amount(payload["exportable_equity_distribution"])


def verify():
    source = downside_sources()
    fixed = fixed_sale_cases()
    require(source["case_sha256"] == fixed["case_sha256"], "D90 scenario changed")
    start, maturity = (date.fromisoformat(fixed[key]) for key in ("discount_date", "sale_date"))
    original, payoff, principal, interest, fees, loan_sha = maturity_cash(source, maturity)
    initial = amount(source["baseline"]["story"]["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    opening_free = amount(original["amounts"]["opening_free_cash"])
    after_payoff = opening_free - payoff
    rows = []

    for case in fixed["cases"]:
        original_sale, = [e for e in case["dated_events"] if e["category"] == "net_sale_distribution"]
        prior = [e for e in case["dated_events"] if e != original_sale]
        require(original_sale["date"] == fixed["sale_date"] and original_sale["kind"] == "distribution"
                and all(e["date"] < fixed["sale_date"] for e in prior)
                and amount(original_sale["amount"]) == amount(case["sale_net_per_usd_10"]),
                "Missing unique on-time sale receipt")
        fee = amount(case["sale_cost_project"])
        scenarios = []
        for delay in DELAYS:
            sale_date = add_months(maturity, delay)
            when = sale_date.isoformat()
            holding = []
            free = after_payoff
            for month in range(1, delay + 1):
                free -= MONTHLY_HOLDING_COST
                require(free >= 0, "Retained free cash does not cover the holding cost")
                holding.append(dict(date=add_months(maturity, month).isoformat(),
                                    expense_project=rational(MONTHLY_HOLDING_COST), free_cash_after_project=rational(free)))
            run, distribution = sale_closing(original, source, fee, when, free)
            net_sale = distribution * scale
            original_net = amount(original_sale["amount"])
            require(net_sale == original_net - MONTHLY_HOLDING_COST * delay * scale,
                    "The original debt payoff was duplicated or holding cash was missed")
            events = prior + [original_sale | {"date": when, "amount": rational(net_sale)}]
            dates = month_grid(start, sale_date)
            maturity_index = dates.index(maturity.isoformat())
            flows = monthly_cash(events, dates)
            receipts = sum(amount(e["amount"]) for e in events if e["kind"] == "distribution")
            contributions = sum(amount(e["amount"]) for e in events if e["kind"] == "contribution")
            require(contributions == 10 + amount(case["extra_contribution_per_usd_10"])
                    and receipts == amount(case["cash_total_received_per_usd_10"]) - MONTHLY_HOLDING_COST * delay * scale,
                    "Retained project cash was treated as an investor cash flow")
            gaps = []
            for gap in case["gaps"]:
                rate = amount(gap["monthly_rate"])
                pv = present_value(flows, rate)
                factor = 1 + rate
                expected = (amount(gap["present_value_per_usd_10"]) - original_net / factor**maturity_index
                            + net_sale / factor**(maturity_index + delay))
                require(pv == expected and (rate != 0 or pv == receipts - contributions),
                        "The delayed sale cash did not reconcile to the discounted ledger")
                gaps.append(dict(monthly_rate=rational(rate), present_value_per_usd_10=rational(pv)))
            scenarios.append(dict(delay_months=delay, sale_date=when, holding_expenses=holding,
                                  total_holding_cost_project=rational(MONTHLY_HOLDING_COST * delay),
                                  debt_payoff_at_sale_project=rational(Fraction(0)),
                                  sale_net_per_usd_10=rational(net_sale), cash_total_received_per_usd_10=rational(receipts),
                                  nominal_unrecovered_per_usd_10=rational(max(0, contributions - receipts)),
                                  incremental_investor_contribution_per_usd_10=rational(Fraction(0)),
                                  dated_events=events, gaps=gaps, closing_sha256=run.sha256))
        rows.append(dict(refinance_cost_project=case["refinance_cost_project"], sale_cost_rate=case["sale_cost_rate"],
                         extra_contribution_per_usd_10=case["extra_contribution_per_usd_10"], scenarios=scenarios))

    return dict(status="passed", decision="PENDING", scope="synthetic_cash_and_existing_debt_only",
                case_sha256=source["case_sha256"], sale_price_project=fixed["sale_price_project"],
                fixed_sale_cost_project=fixed["fixed_sale_cost_project"], discount_date=start.isoformat(),
                maturity_date=maturity.isoformat(), monthly_holding_cost_project=rational(MONTHLY_HOLDING_COST),
                incremental_operating_receipts_project=rational(Fraction(0)), loan_run_sha256=loan_sha,
                maturity_principal_project=rational(principal), maturity_interest_project=rational(interest),
                maturity_fees_project=rational(fees),
                maturity_cash_payment_project=rational(payoff), cash_before_maturity_project=rational(opening_free),
                cash_after_maturity_project=rational(after_payoff), rows=rows)


def build_report():
    result = verify()
    lines = [
        (f"Venta bruta USD {money(result['sale_price_project'])}. Tenencia sintética USD {money(result['monthly_holding_cost_project'])}/mes, sin ingresos extra.", True),
        (f"La deuda vence el {result['maturity_date']}. Se pagan USD {money(result['maturity_cash_payment_project'])} de caja del proyecto.", False),
        (f"El pago incluye principal, interés y USD {money(result['maturity_fees_project'])} de cargo. Deuda al vender USD 0.", False),
        ("Cada grupo indica cobro total / saldo al 0 % / saldo al 1 % / saldo al 2 % mensual.", False),
        ("Todos los importes de la tabla son por USD 10 iniciales. Saldo descontado al 01/01/2027.", False),
        ("Costo variable de venta | +1 mes (01/08) | +2 meses (01/09) | +3 meses (01/10)", True),
    ]
    prior = None
    for row in result["rows"]:
        cost = row["refinance_cost_project"]
        if cost != prior:
            lines.append((f"COSTO DE REFINANCIACIÓN DEL PROYECTO USD {money(cost)}", True))
            prior = cost
        cells = []
        for scenario in row["scenarios"]:
            amounts = [money(scenario["cash_total_received_per_usd_10"])]
            amounts.extend(signed(g["present_value_per_usd_10"]) for g in scenario["gaps"])
            cells.append(" / ".join(amounts))
        lines.append((f"{amount(row['sale_cost_rate']) * 100} % | " + " | ".join(cells), False))
    example = result["rows"][7]
    net_sale = " / ".join(money(s["sale_net_per_usd_10"]) for s in example["scenarios"])
    lines.extend([
        (f"Venta neta con costo de USD 10 + 5 %, por USD 10 iniciales, según demora: {net_sale}.", False),
        ("2027. Aportás USD 10 el 01/01. Cobrás USD 1,00 el 01/03 y otro USD 1,00 el 01/06.", False),
        ("Refi 01/04 | Costo 300 aportás 0,80 | Costo 220 saldo cero | Costo 150 cobrás 0,70", False),
        ("La demora se financia con caja del proyecto. Aporte nuevo del inversor por demora USD 0,00.", True),
        ("Costo de venta = USD 10 fijos + porcentaje de la tabla. Decisión real pendiente.", False),
    ])
    pdf = render_page("D93 | Downside", lines, 19, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Demora de venta con tenencia y vencimiento de la deuda")
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
    cases = [s for row in result["rows"] for s in row["scenarios"]]
    print(json.dumps(dict(status=result["status"], decision=result["decision"], closing_replays=len(cases),
                          combinations=sum(len(s["gaps"]) for s in cases), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
