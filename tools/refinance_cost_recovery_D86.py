"""Replay the Downside refinance cost cut required to recover USD 10 initial equity."""
from argparse import ArgumentParser
from fractions import Fraction
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os

from check_discount_rate_crossover_D35 import BINDINGS as RATE_SOURCE, read_fixture
from check_discounted_sale_recovery_D34 import present_value, validate_grid
from check_integrated_participation_D28 import TERMS, allocate, ledger
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_participant_joint_exit_D32 import BINDINGS, load_sources, replay_matrix, replay_sale
from check_participant_refinance_variants_D31 import build_variant_evidence
from check_worksheet_refinance_D45 import EVENTS, render_page
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.debt_service import rational
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_investor_D74 import investor_view
from worksheet_sale_rate_grid_D84 import RATES, money


CASE = "templates/synthetic-investor-scenarios-D85.json"
REPORT = "docs/review/MiniUW_D86_Costo_Refinanciacion_USD10.pdf"
REFI_CATEGORIES = {"refinance_cash_in", "net_refinance_distribution"}


def adjusted_parent(base, variant, sale, cost):
    spec = variant | {"refinance_closing_costs": rational(cost), "variant_id": "SYNTHETIC-D86-refinance-cost"}
    evidence = build_variant_evidence(base, spec)
    guarded = evidence.guarded_run
    require(not evidence.capacity_run.payload["blockers"] and guarded.investor_run is not None,
            "A refinance cost probe lost the synthetic capacity or cash gate")
    origin = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
    _, parent = replay_sale(evidence, sale, origin, False)
    return parent, evidence


def signature(story):
    return [(e["date"], e["kind"], e["category"], amount(e["amount"])) for e in story["dated_events"]
            if e["category"] not in REFI_CATEGORIES]


def refi_net(story):
    cash = story["cash_by_category"]
    return amount(cash["net_refinance_distribution"]) - amount(cash["refinance_cash_in"])


def downside_sources():
    case_raw = local_file(ROOT, CASE).read_bytes()
    case = json.loads(case_raw)
    bindings_raw = local_file(ROOT, BINDINGS).read_bytes()
    terms_raw = local_file(ROOT, TERMS).read_bytes()
    rate_raw = local_file(ROOT, RATE_SOURCE).read_bytes()
    rate_fixture = json.loads(rate_raw)
    nominal, rates = read_fixture(rate_fixture)
    require(sha(bindings_raw) == case["joint_exit_sha256"] == nominal["joint_matrix_sha256"]
            and sha(terms_raw) == case["allocation_terms_sha256"] == rate_fixture["allocation_terms_sha256"]
            and sha(rate_raw) == case["rate_grid_source_sha256"]
            and tuple(amount(rate) for rate in case["monthly_rates"]) == RATES and set(RATES) <= set(rates),
            "The Downside and rate sources differ from D85")
    bindings, terms = json.loads(bindings_raw), json.loads(terms_raw)
    refinance, sales, refinance_hash, sale_hash = load_sources()
    require(bindings["refinance_fixture_sha256"] == refinance_hash and bindings["sale_inventory_sha256"] == sale_hash,
            "Archived refinance and sale data differ")
    key = case["scenarios"]["Downside"]
    variant_id, sale_id = key.split("/")
    variant, = (v for v in refinance["variants"] if v["variant_id"] == variant_id)
    sale, = (s for s in sales if s["revision_id"] == sale_id)
    selected, baseline, _ = replay_matrix(refinance, sales, selected={key})[key]
    require(not selected["capacity_blockers"], "The archived Downside is capacity-blocked")
    allocation = allocate(terms, baseline, bindings["project_ledgers"][key], require_unique_irr=False)
    cash = investor_view(allocation | {"risk": observe_allocation(allocation, baseline)},
                         case["participant_id"])["cash"]
    require(cash is not None and amount(cash["initial_capital"]) == 10,
            "The archived Downside does not have a verified initial USD 10 view")
    base = load_evidence(independent_test_fixture=True)
    require(refinance["base_evidence_sha256"] == evidence_fingerprint(base),
            "Archived base evidence differs")

    return dict(case_sha256=sha(case_raw), base=base, variant=variant, sale=sale,
                selected=selected, baseline=baseline, cash=cash)


def verify():
    sources = downside_sources()
    base, variant, sale, selected, baseline, cash = (
        sources[k] for k in ("base", "variant", "sale", "selected", "baseline", "cash"))
    original_cost = amount(variant["refinance_closing_costs"])
    flows = validate_grid(baseline)
    dates = [row["date"] for row in flows]
    refi_dates = {e["date"] for e in baseline["story"]["dated_events"] if e["category"] in REFI_CATEGORIES}
    refi_date, = refi_dates
    period = dates.index(refi_date)
    factor = Fraction(10) / amount(baseline["story"]["cash_by_category"]["initial_capital"])
    rows = []
    for rate in RATES:
        discount = (1 + rate) ** -period
        loss = present_value(flows, rate)
        exact = -loss / discount
        cut = Fraction(ceil(exact * 100), 100)
        require(0 < exact <= cut <= original_cost, "Recovery needs a refinance cost outside the supported range")
        probes = {}
        for label, reduction in (("below", cut - Fraction(1, 100)), ("exact", exact), ("at_cents", cut)):
            parent, evidence = adjusted_parent(base, variant, sale, original_cost - reduction)
            updated = validate_grid(parent)
            require([v["date"] for v in updated] == dates
                    and signature(parent["story"]) == signature(baseline["story"])
                    and refi_net(parent["story"]) == refi_net(baseline["story"]) + reduction
                    and amount(evidence.capacity_run.payload["selected_principal"]) == Fraction(selected["selected_principal"])
                    and amount(evidence.capacity_run.payload["maximum_principal_capacity"]) == Fraction(selected["capacity"]),
                    "A cost probe changed non-refinance cash, the loan or capacity")
            value = present_value(updated, rate)
            require(value == loss + reduction * discount
                    and (value < 0 if label == "below" else value == 0 if label == "exact" else value >= 0),
                    "The repriced closing does not cross the break-even boundary")
            probes[label] = dict(reduction_project=rational(reduction), present_value_per_usd_10=rational(value * factor),
                                 refinance_net_per_usd_10=rational(refi_net(parent["story"]) * factor),
                                 guarded_run_sha256=parent["guarded_run_sha256"])
        rows.append(dict(monthly_rate=rational(rate), exact_reduction_per_usd_10=rational(exact * factor),
                         reduction_project_cents=rational(cut), maximum_refinance_cost_project=rational(original_cost - cut),
                         probes=probes))
    return dict(status="passed", decision="PENDING", scope="synthetic_only", scenario="Downside",
                case_sha256=sources["case_sha256"], initial_equity_per_usd_10=cash["initial_capital"],
                cost_baseline_project=rational(original_cost), refinance_date=refi_date,
                discount_date=dates[0], sale_date=dates[-1], baseline=cash,
                source_sale_price=selected["sale_proceeds"], rates=rows, closing_probes=9)


def build_report():
    result = verify()
    cash = result["baseline"]
    lines = [
        (f"Downside original por USD 10 | Cobrás USD {money(cash['gross_distributions'])} en total", True),
        (f"Sin recuperar en caja nominal: USD {money(cash['cash_shortfall_at_horizon'])} | Aportes totales: USD {money(cash['gross_contributions'])}", False),
        (f"Costo de refinanciación original del proyecto: USD {money(result['cost_baseline_project'])}", False),
        (f"Descuento al {result['discount_date']} | Refi el {result['refinance_date']} | Venta el {result['sale_date']}", False),
        ("Tasa mensual | Rebaja en el proyecto / por USD 10 | Costo máximo del proyecto | Cobro en refi", True),
    ]
    for row in result["rates"]:
        rate = money(rational(amount(row["monthly_rate"]) * 100))
        lines.append((f"{rate}% | USD {money(row['reduction_project_cents'])} / USD {money(row['exact_reduction_per_usd_10'])} aprox. | "
                      f"USD {money(row['maximum_refinance_cost_project'])} | USD {money(row['probes']['at_cents']['refinance_net_per_usd_10'])} por USD 10", True))
    lines.append(("Fechas e importes del escenario original | USD por USD 10 iniciales", True))
    for e in cash["events"]:
        value = amount(e["amount"])
        sign = "-" if value and e["kind"] == "contribution" else "+" if value else ""
        lines.append((f"{e['date']}  {EVENTS[e['category']]}  {sign}USD {money(e['amount'])}", False))
    lines.append(("Con la rebaja desaparece el aporte extra de abril. La operación y la venta se mantienen.", False))
    lines.append(("Mínimo al centavo del proyecto. Decisión y retorno personal real pendientes.", False))
    pdf = render_page("D86 | Downside", lines, 21, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "PENDIENTE | Cuánto debe bajar el costo de refinanciación")
    result["pdf_sha256"] = sha(pdf)
    result["page_count"] = 1
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
    print(json.dumps(dict(status="passed", decision="PENDING", rates=len(result["rates"]),
                          closing_probes=result["closing_probes"], one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
