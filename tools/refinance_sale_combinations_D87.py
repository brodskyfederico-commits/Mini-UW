"""Replay combined refinance-cost cuts and sale increases for USD 10 recovery."""
from argparse import ArgumentParser
from fractions import Fraction
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os

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
from worksheet_sale_rate_grid_D84 import RATES, money


REPORT = "docs/review/MiniUW_D87_Combinaciones_Refi_Venta_USD10.pdf"
CUTS = (0, 80, 150)


def sale_net(story):
    cash = story["cash_by_category"]
    return amount(cash["net_sale_distribution"]) - amount(cash["additional_capital"])


def fixed_events(story):
    changed = REFI_CATEGORIES | {"net_sale_distribution", "additional_capital"}
    return [(e["date"], e["kind"], e["category"], amount(e["amount"]))
            for e in story["dated_events"] if e["category"] not in changed]


def verify():
    sources = downside_sources()
    base, variant, sale, selected, baseline, cash = (
        sources[k] for k in ("base", "variant", "sale", "selected", "baseline", "cash"))
    original_cost = amount(variant["refinance_closing_costs"])
    original_price = Fraction(selected["sale_proceeds"])
    initial = amount(baseline["story"]["cash_by_category"]["initial_capital"])
    scale = Fraction(10) / initial
    flows = validate_grid(baseline)
    dates = [row["date"] for row in flows]
    refi_dates = {e["date"] for e in baseline["story"]["dated_events"] if e["category"] in REFI_CATEGORIES}
    refi_date, = refi_dates
    refi_index = dates.index(refi_date)
    sale_index = len(dates) - 1
    rows = []
    for cut in CUTS:
        cost = original_cost - cut
        refi_only, evidence = adjusted_parent(base, variant, sale, cost)
        guarded = evidence.guarded_run
        origin = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
        require(not evidence.capacity_run.payload["blockers"]
                and amount(evidence.capacity_run.payload["selected_principal"]) == Fraction(selected["selected_principal"])
                and amount(evidence.capacity_run.payload["maximum_principal_capacity"]) == Fraction(selected["capacity"])
                and refi_net(refi_only["story"]) == refi_net(baseline["story"]) + cut
                and sale_net(refi_only["story"]) == sale_net(baseline["story"]),
                "The refinance change did not preserve the loan and sale cash")
        thresholds = []
        for rate in RATES:
            refi_discount = (1 + rate) ** -refi_index
            sale_discount = (1 + rate) ** -sale_index
            baseline_pv = present_value(flows, rate)
            pv_after_cut = baseline_pv + cut * refi_discount
            target = original_price - pv_after_cut / sale_discount
            quote = Fraction(ceil(target * 100), 100)
            require(target > original_price and quote - Fraction(1, 100) < target <= quote,
                    "Expected a higher sale price with an exact cent boundary")
            probes = {}
            for label, price in (("below", quote - Fraction(1, 100)), ("at_cents", quote)):
                proceeds = sale["replacement_claims"]["gross_proceeds"].copy()
                set_claim(proceeds, price, "SYNTHETIC-D87-gross-sale-price")
                spec = sale | {"revision_id": "SYNTHETIC-D87-combination",
                               "replacement_claims": sale["replacement_claims"] | {"gross_proceeds": proceeds}}
                _, parent = replay_sale(evidence, spec, origin, False)
                story = parent["story"]
                verified = validate_grid(parent)
                require([row["date"] for row in verified] == dates
                        and fixed_events(story) == fixed_events(baseline["story"])
                        and refi_net(story) == refi_net(baseline["story"]) + cut
                        and sale_net(story) - sale_net(baseline["story"]) == price - original_price,
                        "The probe changed cash outside the two declared closings")
                pv = present_value(verified, rate)
                require(pv == pv_after_cut + (price - original_price) * sale_discount
                        and (pv < 0 if label == "below" else pv >= 0),
                        "The repriced closing did not verify the minimum")
                probes[label] = dict(sale_price_project=rational(price),
                                     present_value_per_usd_10=rational(pv * scale),
                                     sale_net_per_usd_10=rational(sale_net(story) * scale),
                                     cash_total_received_per_usd_10=rational(amount(story["gross_distributions"]) * scale),
                                     guarded_run_sha256=parent["guarded_run_sha256"])
            thresholds.append(dict(monthly_rate=rational(rate), exact_gross_price=rational(target),
                                   minimum_gross_price_project=rational(quote),
                                   increase_gross_price_project=rational(quote - original_price), probes=probes))
        rows.append(dict(refinance_cost_reduction_project=rational(Fraction(cut)),
                         refinance_cost_project=rational(cost),
                         refinance_net_per_usd_10=rational(refi_net(refi_only["story"]) * scale),
                         thresholds=thresholds))

    # The no-sale-increase endpoint was replayed on both sides of the cent boundary in D86.
    fixed_sale = [
        rational(Fraction(ceil(-present_value(flows, rate) * (1 + rate)**refi_index * 100), 100)) for rate in RATES]
    return dict(status="passed", decision="PENDING", scope="synthetic_only",
                case_sha256=sources["case_sha256"], original=cash, original_refinance_cost=rational(original_cost),
                original_sale_price=rational(original_price), discount_date=dates[0], refinance_date=refi_date,
                sale_date=dates[-1], fixed_sale_refinance_cut_project=fixed_sale, combinations=rows, closing_probes=18)


def build_report():
    result = verify()
    cash = result["original"]
    operating = [e for e in cash["events"] if e["category"] == "operating_distribution"]
    first, second = operating
    refi_cash_in, = [e["amount"] for e in cash["events"] if e["category"] == "refinance_cash_in"]
    lines = [
        (f"Downside original: cobrás USD {money(cash['gross_distributions'])} por USD 10 iniciales.", True),
        (f"Aportás USD {money(refi_cash_in)} en refi y quedan USD {money(cash['cash_shortfall_at_horizon'])} sin recuperar.", False),
        (f"Proyecto original: costo refi USD {money(result['original_refinance_cost'])} | venta bruta USD {money(result['original_sale_price'])}.", False),
        (f"Descuento al {result['discount_date']} | Refi {result['refinance_date']} | Venta {result['sale_date']}", False),
        ("PRECIO BRUTO MÍNIMO DE VENTA DEL ACTIVO (USD)", True),
        ("Costo refi del proyecto / rebaja | 0% mensual | 1% mensual | 2% mensual", True),
    ]
    for row in result["combinations"]:
        prices = " | ".join(f"USD {money(v['minimum_gross_price_project'])}" for v in row["thresholds"])
        lines.append((f"USD {money(row['refinance_cost_project'])} / {money(row['refinance_cost_reduction_project'])} | {prices}", True))
    lines.append(("Al refinanciar por USD 10: con costo 300 aportás 0,80; con 220, saldo cero; con 150, cobrás 0,70.", False))
    fixed = " | ".join(f"USD {money(x)}" for x in result["fixed_sale_refinance_cut_project"])
    lines.append((f"Con venta fija en USD 200, la rebaja de refi sería: {fixed} (D86).", False))
    lines.append(("EJEMPLO POR USD 10 INICIALES | COSTO DE REFI DEL PROYECTO USD 150", True))
    example = result["combinations"][-1]
    lines.extend([(f"{result['discount_date']} aportás USD 10 | {first['date']} cobrás USD {money(first['amount'])} de operación.", False),
                  (f"{result['refinance_date']} cobrás USD {money(example['refinance_net_per_usd_10'])} en refi | {second['date']} cobrás USD {money(second['amount'])} de operación.", False),
                  ("Aporte extra: USD 0,00 | Caja sin recuperar: USD 0,00 a las tres tasas.", True)])
    sale_values = " | ".join(f"USD {money(v['probes']['at_cents']['sale_net_per_usd_10'])}" for v in example["thresholds"])
    lines.append((f"{result['sale_date']} cobrás neto de venta: {sale_values} al 0%, 1% y 2%.", False))
    totals = " | ".join(f"USD {money(v['probes']['at_cents']['cash_total_received_per_usd_10'])}" for v in example["thresholds"])
    lines.append((f"Cobrás en total: {totals} por USD 10 iniciales.", True))
    lines.append(("Se mantiene la operación, el préstamo y los costos de venta. Retorno real pendiente.", False))
    pdf = render_page("D87 | Downside", lines, 22, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "PENDIENTE | Combinaciones sintéticas de refinanciación y venta")
    result.update(pdf_sha256=sha(pdf), page_count=1)
    return pdf, result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of auditing the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pdf, result = build_report()
    if args.output:
        with TemporaryDirectory(dir=args.output.parent) as directory:
            source = Path(directory) / "report.pdf"
            source.write_bytes(pdf)
            os.link(source, args.output)
    else:
        require((ROOT / REPORT).read_bytes() == pdf, "The one-page report differs from source replay")
    if args.evidence:
        with args.evidence.open("xb") as stream:
            stream.write(encoded(result))
    print(json.dumps(dict(status="passed", decision="PENDING", rates=len(RATES),
                          combinations=len(result["combinations"]) * len(RATES), closing_probes=result["closing_probes"],
                          one_page_report=result["page_count"] == 1, pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
