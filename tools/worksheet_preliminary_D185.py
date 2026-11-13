"""Synthetic LOI comparison with an explicit, provisional ranking convention."""
from fractions import Fraction
import re

from check_operating_replay_D20 import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.investor_returns import SCHEMA as RETURN_SCHEMA, produce_investor_returns
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import day
from worksheet_sale_rate_grid_D84 import money


PROFILE = "synthetic_preliminary_loi"
POLICY = "SYNTHETIC-D185-downside-equity-multiple"
SCENARIOS = ("Base", "Downside")
REQUIRED = {
    "initial_capital": "contribution",
    "additional_capital": "contribution",
    "refinance_cash_in": "contribution",
    "net_refinance_distribution": "distribution",
    "operating_distribution": "distribution",
    "net_sale_distribution": "distribution",
}
LABELS = dict(initial_capital="Aporte inicial", additional_capital="Aporte adicional",
              refinance_cash_in="Aporte en refi", net_refinance_distribution="Cobro en refi",
              operating_distribution="Cobro operativo", net_sale_distribution="Cobro neto de venta")
SUPPORT = ("program", "acquisition_and_costs", "rent_and_expenses", "calendar", "financing", "exit")


def assumption_ready(row, cutoff):
    if not isinstance(row, dict):
        return False
    observed = day(row.get("as_of"))
    return (observed is not None and observed <= cutoff
            and all(isinstance(row.get(k), str) and row[k].strip() and len(row[k]) <= 180
                    for k in ("source_ref", "owner")))


def estimate(spec, deal, name, cutoff, *, amount_digits=12, max_events=12):
    dates = spec["dates"]
    inputs = deal["scenarios"].get(name)
    if not isinstance(inputs, dict):
        return dict(cash=None, blockers=["escenario ausente"])
    support = inputs.get("support", {})
    missing = [k for k in SUPPORT if not isinstance(support, dict) or not assumption_ready(support.get(k), cutoff)
               or not isinstance(support[k].get("summary"), str) or not support[k]["summary"].strip()]
    if missing:
        return dict(cash=None, blockers=["supuesto sin respaldo: " + k for k in missing])

    events = inputs.get("events")
    if not isinstance(events, list) or not events or len(events) > max_events:
        return dict(cash=None, blockers=["inventario de caja incompleto"])
    ledger = []
    for i, row in enumerate(events):
        if not assumption_ready(row, cutoff):
            return dict(cash=None, blockers=[f"flujo {i + 1} sin fuente, fecha o responsable"])
        category, when = row.get("category"), row.get("date")
        try:
            value = amount(row.get("amount"), amount_digits)
        except ValidationError:
            value = None
        if (not isinstance(category, str) or category not in REQUIRED or when not in dates or value is None or value < 0):
            return dict(cash=None, blockers=[f"flujo {i + 1} con importe, fecha o tipo inválido"])
        ledger.append(dict(event_id=f"estimate-{i + 1}", date=when, kind=REQUIRED[category],
                           category=category, amount=rational(value), currency="USD", source_ref=row["source_ref"]))

    present = {row["category"] for row in ledger}
    mandatory = {"initial_capital", "additional_capital", "operating_distribution", "net_sale_distribution"}
    refi = {"refinance_cash_in", "net_refinance_distribution"}
    if spec["financing"] == "with_refinance":
        mandatory |= refi
    else:
        if present & refi:
            return dict(cash=None, blockers=["flujos de refi en una estrategia sin refi"])
    initial = [row for row in ledger if row["category"] == "initial_capital"]
    if (not mandatory <= present or len(initial) != 1 or initial[0]["date"] != dates[0]
            or amount(initial[0]["amount"]) <= 0):
        return dict(cash=None, blockers=["faltan flujos explícitos o aporte inicial positivo"])
    if any(row["date"] != dates[-1] for row in ledger if row["category"] == "net_sale_distribution"):
        return dict(cash=None, blockers=["venta fuera del cierre de la ventana"])
    if spec["financing"] == "with_refinance":
        refi_rows = [row for row in ledger if row["category"] in refi]
        if len(refi_rows) != 2 or refi_rows[0]["date"] != refi_rows[1]["date"] or refi_rows[0]["date"] not in dates[1:-1]:
            return dict(cash=None, blockers=["fecha o inventario de refi incompatible"])
        if all(amount(row["amount"]) > 0 for row in refi_rows):
            return dict(cash=None, blockers=["cobro y aporte de refi incompatibles"])
    source = dict(schema=RETURN_SCHEMA, context=dict(deal_id=deal["id"], scenario_id=f"SYNTHETIC-{name}",
                  run_id="SYNTHETIC-D185", definition_set_revision=POLICY),
                  currency="USD", equity_level="aggregate_project_equity", event_inventory_declared_complete=True,
                  grid=dict(spacing="calendar_months_same_day", step_months=3, dates=dates, timing_basis_ref=POLICY),
                  events=ledger, normalization=dict(reference_amount=rational(Fraction(10)),
                                                     contribution_event_ids=[initial[0]["event_id"]], basis_ref=POLICY),
                  capital_snapshots=[], annual_cash_bases=[],
                  irr_parameters=dict(rate_domain="r_gt_minus_one_positive_discount_factor",
                                      max_periodic_rate_interval_width=rational(Fraction(1, 100_000_000)),
                                      split_budget=128, operation_budget=50_000, periods_per_year=4))
    result = produce_investor_returns(encoded(source)).payload
    cash = result["normalized_story"]
    if not cash or cash["events"] is None:
        return dict(cash=None, blockers=["caja no reproducible"])
    cash["unrecovered_after_sale"] = rational(max(Fraction(), -amount(cash["net_cash_profit"])))
    cash["equity_multiple"] = rational(amount(cash["total_distributions"]) / amount(cash["total_contributions"]))
    roots = result["annual_irr_roots"]
    return dict(cash=cash, blockers=[], annual_irr=roots[0] if len(roots) == 1
                and result["periodic_irr"]["status"] == "complete_synthetic" else None)


def build_preliminary(case, raw):
    require(set(case) == {"schema", "policy", "as_of", "dates", "financing", "focus", "deals"}
            and case["policy"] == POLICY, "Explicit synthetic preliminary policy required")
    cutoff = day(case["as_of"])
    dates = case["dates"]
    require(cutoff and isinstance(dates, list) and 3 <= len(dates) <= 9
            and all(day(d) is not None and day(d) >= cutoff for d in dates)
            and case["financing"] in ("with_refinance", "without_refinance"), "Unsupported comparison window or financing")
    first = day(dates[0])
    require(all(d.day == first.day and 12 * (d.year - first.year) + d.month - first.month == i * 3
                for i, d in enumerate(map(day, dates))), "Expected a common quarterly grid")
    require(isinstance(case["deals"], list) and 1 <= len(case["deals"]) <= 4, "One to four synthetic deals required")
    views = {}
    for deal in case["deals"]:
        require(isinstance(deal, dict) and set(deal) == {"id", "scenarios", "dates", "financing", "as_of"}
                and isinstance(deal["id"], str) and re.fullmatch(r"SYNTHETIC-[A-Z0-9-]{1,22}", deal["id"])
                and deal["id"] not in views and isinstance(deal["scenarios"], dict)
                and deal["scenarios"].keys() <= set(SCENARIOS), "Invalid or repeated synthetic deal")
        comparable = all(deal[k] == case[k] for k in ("dates", "financing", "as_of"))
        views[deal["id"]] = (dict(state="PENDING", reason="fecha, horizonte o financiación incompatible", scenarios={})
                             if not comparable else dict(scenarios={n: estimate(case, deal, n, cutoff) for n in SCENARIOS}))
    require(isinstance(case["focus"], str) and case["focus"] in views, "Explicit focus deal required")
    return finish_preliminary(case, raw, views)


def finish_preliminary(case, raw, views, *, profile=PROFILE):
    comparable = []
    for deal_id, view in views.items():
        if all(view["scenarios"].get(n, {}).get("cash") is not None for n in SCENARIOS):
            view["state"] = "PRELIMINAR"
            score = amount(view["scenarios"]["Downside"]["cash"]["equity_multiple"])
            comparable.append((deal_id, score))
        else:
            view["state"] = "PENDING"
    ranking = []
    rank, last = 0, None
    for i, (deal_id, score) in enumerate(sorted(comparable, key=lambda x: (-x[1], x[0])), 1):
        if score != last:
            rank = i
        ranking.append(dict(deal_id=deal_id, position=rank, downside_equity_multiple=rational(score)))
        last = score
    pdf = report(case, views, ranking)
    return dict(profile=profile, state=views[case["focus"]]["state"], decision="PENDING", simulation_result="PENDING",
                real_decisions_enabled=False, deployment_enabled=False, full_uw_eligible=False, personal_investor_return=None,
                case_sha256=sha(raw), pdf_sha256=sha(pdf), page_count=1, ranking_policy=POLICY, ranking=ranking, deals=views), pdf


def report(case, views, ranking):
    focus = views[case["focus"]]
    lines = [(f"{focus['state']} | Dictamen formal PENDING | Retorno personal PENDING", True),
             ("Estimación sintética del equity agregado por USD 10 iniciales, antes de impuestos personales.", False)]
    for name in SCENARIOS:
        result = focus["scenarios"].get(name, {})
        cash = result.get("cash")
        if cash is None:
            reason = focus.get("reason") or result["blockers"][0]
            lines.append((f"{name} | Caja PENDING · {reason}", True))
            continue
        extra = rational(amount(cash["total_contributions"]) - 10)
        lines.append((f"{name} | Aporte extra {money(extra)} | Cobro total {money(cash['total_distributions'])}"
                      f" | Sin recuperar {money(cash['unrecovered_after_sale'])}", True))
        lines.append((f"Total aportado {money(cash['total_contributions'])} | Resultado neto {money(cash['net_cash_profit'])}"
                      f" | Múltiplo {money(cash['equity_multiple'])}×", False))
        lines.extend((f"{e['date']}  {LABELS[e['category']]}  {money(e['amount'])}", False)
                     for e in sorted(cash["events"], key=lambda e: e["date"]))
    lines.append(("Prioridad de revisión · múltiplo de equity estimado en Downside", True))
    lines.extend((f"{r['position']}. {r['deal_id']}  {money(r['downside_equity_multiple'])}×", False) for r in ranking)
    lines.extend((f"{name} | Fuera del ranking · PENDING", False) for name, view in views.items() if view["state"] == "PENDING")
    lines.append(("Términos personales y valor retenido PENDING. Supuestos, fuentes y fechas en case.json.", False))
    lines.append(("Convención de ranking para ensayo. Importes estimados; fechas en formato AAAA-MM-DD.", False))
    return render_page(case["focus"], lines, 10, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Piloto sintético de LOI | Priorización para revisión")
