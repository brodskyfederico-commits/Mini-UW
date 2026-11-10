"""Replay the sale required to recover USD 10 at three synthetic discount rates."""
from fractions import Fraction
from functools import partial
import json

from check_discount_rate_crossover_D35 import BINDINGS, read_fixture, sample_rates
from check_discounted_sale_recovery_D34 import present_value, validate_grid
from check_integrated_participation_D28 import TERMS, allocate
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_joint_exit_D32 import load_sources
from check_sale_cash_recovery_D33 import replay_targets
from check_worksheet_refinance_D45 import EVENTS, render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_discounted_recovery_D83 import cents_up, required_sale_cash
from worksheet_investor_D74 import display
from worksheet_investor_scenarios_D75 import SCENARIOS, build_scenarios
from worksheet_scenario_recovery_D82 import fixed_sale_terms


RATES = (Fraction(0), Fraction(1, 100), Fraction(1, 50))


def money(value):
    return display(value).replace(".", ",")


def render_grid(views, rows, dates, gap=None):
    def totals(field):
        return " | ".join(f"{name} USD {money(views[name]['cash'][field])}" for name in SCENARIOS)
    lines = [(f"Cobros por USD 10 iniciales | {totals('gross_distributions')}", True),
             (f"Caja nominal sin recuperar | {totals('cash_shortfall_at_horizon')}", True),
             (f"Aportes totales | {totals('gross_contributions')}", False),
             (f"Descuento al {dates[0]} | Venta el {dates[-1]} | Tasas sintéticas mensuales", False),
             ("Cuánto debe dejar la venta al cierre por cada USD 10 iniciales", True)]
    for row in rows:
        rate = f"{money(rational(amount(row['rate']) * 100))}%"
        net = " | ".join(f"{name} USD {money(row['scenarios'][name]['net_at_sale_cents'])}" for name in SCENARIOS)
        lines.append((f"{rate} mensual | {net}", True))
    if gap is not None:
        lines[4:] = gap
    lines.append(("Calendario de aportes y cobros del escenario | USD por USD 10 iniciales", True))
    events = {}
    for name in SCENARIOS:
        for e in views[name]["cash"]["events"]:
            when, category, kind = (e[key] for key in ("date", "category", "kind"))
            by_case = events.setdefault((when, category, kind), {})
            by_case[name] = by_case.get(name, 0) + amount(e["amount"])
    for (when, category, kind), by_case in sorted(events.items()):
        parts = []
        for name in SCENARIOS:
            if name not in by_case:
                parts.append(f"{name} Sin evento")
                continue
            value = by_case[name]
            sign = "-" if value and kind == "contribution" else "+" if value else ""
            parts.append(f"{name} {sign}{money(rational(value))}")
        lines.append((f"{when} {EVENTS[category]} | " + " | ".join(parts), False))
    lines.append(("Mínimos al centavo. Costos de venta y demás flujos fijos. Retorno real pendiente.", False))
    revision = "D84" if gap is None else "D85"
    return render_page(revision + " | Base y Downside", lines, 22, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "PENDIENTE | Sensibilidad sintética del cobro de venta")


def build_rate_grid(case, case_sha256):
    raw = local_file(ROOT, BINDINGS).read_bytes()
    require(case.get("rate_grid_source_sha256") == sha(raw), "The discount grid source differs")
    fixture = json.loads(raw)
    nominal, archived_rates = read_fixture(fixture)
    require(tuple(amount(rate) for rate in case["monthly_rates"]) == RATES
            and set(RATES) <= set(archived_rates)
            and case["allocation_terms_sha256"] == fixture["allocation_terms_sha256"]
            and case["joint_exit_sha256"] == nominal["joint_matrix_sha256"],
            "The explicit three-rate comparison and scenario sources differ")
    previous = {key: value for key, value in case.items() if key not in ("monthly_rates", "rate_grid_source_sha256")}
    previous["schema"] = "miniuw.synthetic-investor-scenarios.v1"
    result, _ = build_scenarios(previous, case_sha256)

    terms = json.loads(local_file(ROOT, TERMS).read_bytes())
    _, sales, _, _ = load_sources()
    sales = {sale["revision_id"]: sale for sale in sales}
    anchor = "SYNTHETIC-sale-0"
    views = result["scenarios"]
    groups = {}
    for name, view in views.items():
        refi, sale_id = view["archive_case"].split("/")
        require(fixed_sale_terms(sales[sale_id]) == fixed_sale_terms(sales[anchor]),
                "The fixed-cost anchor differs from the selected case")
        groups[name] = f"{refi}/{anchor}"
    targets = replay_targets(nominal, sample_prices=partial(sample_rates, rates=archived_rates),
                             groups=set(groups.values()))
    require(targets.keys() == set(groups.values()), "Expected both recovery groups")
    rows = []
    grid_dates = None
    for rate in RATES:
        by_name = {}
        for name, group in groups.items():
            _, target = targets[group]
            price, parent = target["samples"][str(rate)]
            ledger_hash = fixture["sample_ledgers"][f"{group}/{rate}"]
            allocation = allocate(terms, parent, ledger_hash, require_unique_irr=False)
            require(allocation["participants"] and all(
                present_value(part["dated_net_flows"], rate) == 0 for part in allocation["participants"]),
                "The repriced closing did not recover the participant equity in present value")
            dates = [row["date"] for row in validate_grid(parent)]
            if grid_dates is None:
                grid_dates = dates
            require(dates == grid_dates, "The sensitivity uses different dates")
            view = views[name]
            cash = view["cash"]
            needed_pv, needed, discount, pre_sale_pv = required_sale_cash(cash, dates, rate)
            initial = amount(parent["story"]["cash_by_category"]["initial_capital"])
            current_sale = sum(amount(e["amount"]) for e in cash["events"] if e["category"] == "net_sale_distribution")
            require(amount(cash["initial_capital"]) == 10
                    and (price - Fraction(view["gross_sale_proceeds"])) * 10 / initial == needed - current_sale
                    and needed * discount == needed_pv, "The rate grid differs from the dated USD 10 cash")
            by_name[name] = dict(net_at_sale_exact=rational(needed), net_at_sale_cents=cents_up(needed),
                                 net_receipt_present_value=rational(needed_pv),
                                 minimum_gross_price_exact=rational(price), minimum_gross_price_at_cents=cents_up(price),
                                 current_net_present_value=rational(pre_sale_pv + current_sale * discount),
                                 replay_ledger_sha256=ledger_hash)
        rows.append(dict(rate=rational(rate), scenarios=by_name))
    pdf = render_grid(views, rows, grid_dates)
    return result | dict(rate_sensitivity=dict(monthly_rates=rows, discount_date=grid_dates[0],
                                               sale_date=grid_dates[-1], source_sha256=sha(raw)),
                         pdf_sha256=sha(pdf)), pdf
