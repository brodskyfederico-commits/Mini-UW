"""Present a participant's synthetic cash flows per USD 10 of initial capital."""
from fractions import Fraction

from check_operating_replay_D20 import amount, require
from check_worksheet_refinance_D45 import EVENTS, annual_irr, render_page
from miniuw_foundation.debt_service import rational


def investor_view(participation, identity):
    view = dict(scope="synthetic_only", state="PENDING", participant_id=identity,
                basis="USD 10 of initial equity, additional contributions scaled separately",
                personal_investor_return=None, cash=None, blockers=participation["blockers"])
    if participation["participants"] is None:
        return view
    candidates = [row for row in participation["participants"] if row["participant_id"] == identity]
    require(len(candidates) == 1, "The illustrative participant does not match the archived terms")
    row = candidates[0]
    require(row["currency"] == "USD", "USD is required for this illustrative normalization")
    initial = amount(row["cash_by_category"]["initial_capital"])
    if initial <= 0:
        return view | {"blockers": ["positive_initial_capital_required"]}

    factor = Fraction(10) / initial
    events = sorted(row["dated_events"], key=lambda event: event["date"])
    scaled_events = [dict(date=e["date"], kind=e["kind"], category=e["category"],
                          amount=rational(amount(e["amount"]) * factor)) for e in events]
    summary = {k: rational(amount(row[k]) * factor)
               for k in ("gross_contributions", "gross_distributions", "net_cash_profit")}
    risk = next(x["metrics"] for x in participation["risk"]["participants"] if x["participant_id"] == identity)
    return view | dict(state="computed_synthetic", cash=summary | dict(
        initial_capital=rational(Fraction(10)), events=scaled_events,
        annual_operating_receipts=[dict(year=y["calendar_cash_receipt_year"],
                                       amount=rational(amount(y["operating_distributions_only"]) * factor))
                                   for y in row["annual_cash"]],
        equity_multiple=row["equity_multiple"], annual_irr_roots=row["annual_IRR_roots"],
        cash_shortfall_at_horizon=rational(amount(risk["cash_shortfall_at_horizon"]) * factor),
        sale_share_of_distributions=risk["sale_share_of_distributions"]))


def display(value):
    cents = round(amount(value) * 100)
    units, remainder = divmod(abs(cents), 100)
    return f"{'-' if cents < 0 else ''}{units}.{remainder:02d}"


def render_investor(case, view, sale_blockers):
    cash = view["cash"]
    lines = []
    if cash is None:
        lines.append(("Retorno por USD 10 pendiente. No hay caja calculada.", True))
        if "tax-unresolved:cost_applicability_unresolved" in sale_blockers:
            lines.append(("Falta resolver si aplica el impuesto de venta.", False))
        if "C68:required_numeric_value_missing" in sale_blockers:
            lines.append(("Falta C68 (costo variable de venta) en la hoja.", False))
    else:
        lines.append((f"Por USD 10 iniciales: cobros USD {display(cash['gross_distributions'])} | "
                      f"Ganancia neta USD {display(cash['net_cash_profit'])}", True))
        lines.append((f"Aportes totales USD {display(cash['gross_contributions'])} | "
                      f"Multiplo {display(cash['equity_multiple'])}x | TIR anual {annual_irr(cash['annual_irr_roots'])}", False))
        lines.append(("Calendario de aportes y cobros por USD 10 iniciales", True))
        for event in cash["events"]:
            lines.append((f"{event['date']}  {EVENTS[event['category']]}  USD {display(event['amount'])}", False))
        for year in cash["annual_operating_receipts"]:
            lines.append((f"{year['year']}  Cobro operativo USD {display(year['amount'])} | CoC pendiente", False))
        sale_share = cash["sale_share_of_distributions"]
        if sale_share is not None:
            lines.append((f"Porcentaje de los cobros que depende de la venta: "
                          f"{display(rational(amount(sale_share) * 100))}%", False))
        lines.append((f"Caja sin recuperar al corte: USD {display(cash['cash_shortfall_at_horizon'])}", False))
    lines.append(("Capital remanente, equity retenido y retorno personal real: pendientes.", False))
    return render_page(case, lines, 23, "MINI-UW | QUE RETORNO TENGO SI INVIERTO USD 10?",
                       "PENDIENTE | Ejemplo sintetico por participante")
