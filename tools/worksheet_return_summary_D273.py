"""Versioned, source-replayed equity return summary; no investment criterion."""
from copy import deepcopy
from datetime import date
from fractions import Fraction

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import synthetic_id


SCHEMA = "miniuw.synthetic-native-rental-inputs.v36"
PROFILE = "miniuw.synthetic-equity-return-summary.v1"
BASE_SCHEMAS = ("miniuw.synthetic-native-rental-inputs.v34", "miniuw.synthetic-native-rental-inputs.v35")
RULES = dict(basis="verified_initial_project_equity_USD10",
    calendar="complete_first_day_quarters_from_verified_fiscal_horizon",
    aggregation="gross_calls_and_receipts_grouped_by_date_no_intraday_order",
    payback="first_date_receipts_cover_calls_after_positive_initial_contribution",
    peak="maximum_cumulative_calls_less_receipts_by_date",
    rate="explicit_D270_certified_annual_IRR_or_PENDING")


def cash_fraction(value):
    """Use the cash/IRR protocol's bounded precision, never impute an amount."""
    try:
        return _fraction(value, 1300)
    except ValueError:
        raise ValueError("Importe racional inválido o fuera del límite de precisión del protocolo") from None


def definition(raw):
    require(isinstance(raw, dict) and set(raw) == {"profile", "rules", "source_ref"}
            and raw["profile"] == PROFILE and raw["rules"] == RULES and synthetic_id(raw["source_ref"]),
            "Definición de resumen no confirmada; conservar PENDING")
    return raw


def baseline(case):
    require(isinstance(case, dict) and set(case) == {"schema", "baseline_case", "return_summary"}
            and case["schema"] == SCHEMA and isinstance(case["baseline_case"], dict)
            and case["baseline_case"].get("schema") in BASE_SCHEMAS,
            "Se requiere el contrato v36 y un único expediente base v34 o v35")
    definition(case["return_summary"])
    base = case["baseline_case"]
    require(base.get("rent_inputs", {}).get("holding_horizon", {}).get("profile") ==
            "miniuw.synthetic-integrated-fiscal-holding-horizon.v2",
            "El resumen requiere el horizonte fiscal documentado")
    return base


def revision_projection(case):
    from worksheet_revision_D128 import case_revision
    base = baseline(case)
    observed = deepcopy(case_revision(base))
    observed["fingerprints"]["financial_sources"] = sha(encoded(dict(
        baseline_financial_sources=observed["fingerprints"]["financial_sources"],
        baseline_case_sha256=sha(encoded(base)), summary_definition=case["return_summary"])))
    return observed


def missing(reason):
    return dict(state="PENDING", irr_annual=dict(state="PENDING", annual_enclosure=None,
        reason="PENDING · raíz no probada", blockers=[reason]), payback_date=None,
        payback_reason=reason, peak_equity=None, peak_dates=[], project_peak_equity=None,
        cash_sha256=None, blockers=[reason])


def ledger_summary(cash, dates, certificate):
    """Do not infer a zero amount/date; totals use exact gross dated observations."""
    try:
        require(isinstance(cash, dict) and isinstance(dates, list) and len(dates) >= 2
                and dates == sorted(set(dates)), "Falta la grilla completa de fechas")
        for day in dates:
            require(isinstance(day, str) and date.fromisoformat(day).isoformat() == day,
                    "Fecha del calendario inválida")
        grid = [date.fromisoformat(d) for d in dates]
        offsets = [(d.year-grid[0].year)*12+d.month-grid[0].month for d in grid]
        require(offsets == list(range(0,3*len(grid),3)) and all(d.day == 1 for d in grid),
                "Falta un trimestre del calendario; no se puede asumir un movimiento cero")
        amount, scale, unit = (cash_fraction(cash.get(key)) for key in
                               ("basis_amount", "scale_factor", "reference_amount"))
        require(amount is not None and amount > 0 and unit == 10 and scale == Fraction(10)/amount,
                "Falta una base inicial positiva verificada para normalizar por USD 10")
        events = cash.get("events")
        require(isinstance(events, list) and events and all(isinstance(e, dict) for e in events)
                and {e.get("date") for e in events} == set(dates),
                "Falta un movimiento observado; no se reemplaza por cero")
        ids = [e.get("event_id") for e in events]
        require(all(isinstance(v, str) and v for v in ids) and len(set(ids)) == len(ids),
                "Identificadores de movimiento ausentes o duplicados")
        basis_ids = cash.get("basis_event_ids")
        require(isinstance(basis_ids, list) and basis_ids and len(set(basis_ids)) == len(basis_ids)
                and set(basis_ids) <= set(ids), "Faltan los aportes que acreditan la base inicial")
        by_date = {d: dict(contribution=Fraction(), distribution=Fraction()) for d in dates}
        initial = Fraction()
        for event in events:
            value = cash_fraction(event.get("amount"))
            require(value is not None and value >= 0 and event.get("currency") == "USD"
                    and event.get("kind") in ("contribution", "distribution")
                    and isinstance(event.get("source_ref"), str) and bool(event["source_ref"].strip()),
                    "Importe, moneda, tipo o fuente del movimiento ausente o inválido")
            by_date[event["date"]][event["kind"]] += value
            if event["event_id"] in basis_ids:
                require(event["kind"] == "contribution" and event["date"] == dates[0],
                        "La base inicial debe corresponder a aportes del inicio")
                initial += value
        require(initial == 10, "La base normalizada no concilia con USD 10 iniciales")
        calls = receipts = peak = Fraction()
        payback = None
        reversed_recovery = False
        peak_dates = []
        dated = []
        for day, row in by_date.items():
            calls += row["contribution"]; receipts += row["distribution"]
            net = calls-receipts
            if net > peak: peak, peak_dates = net, [day]
            elif net == peak: peak_dates.append(day)
            if payback is None and calls > 0 and receipts >= calls: payback = day
            elif payback is not None and receipts < calls: reversed_recovery = True
            dated.append(dict(date=day, cumulative_contributions=rational(calls),
                cumulative_distributions=rational(receipts), unrecovered=rational(max(Fraction(), net))))
        require(calls == cash_fraction(cash.get("total_contributions"))
                and receipts == cash_fraction(cash.get("total_distributions"))
                and cash_fraction(cash.get("equity_multiple")) == receipts/calls
                and cash_fraction(cash.get("unrecovered_after_sale")) == max(Fraction(), calls-receipts),
                "Los totales de caja no concilian con sus movimientos brutos")
        from worksheet_irr_certificate_D270 import verify_cash
        irr = verify_cash(cash, dates, certificate)
        if irr.get("annual_enclosure") is None:
            irr = irr | dict(reason="PENDING · raíz no probada")
        return dict(state="calculado con fuentes sintéticas verificadas", irr_annual=irr,
            payback_date=payback,
            payback_reason=None if payback is not None else "capital no recuperado en el horizonte",
            recovery_reversed_after_first_payback=reversed_recovery,
            peak_equity=rational(peak), project_peak_equity=rational(peak/scale), peak_dates=peak_dates,
            peak_basis="USD por USD 10 de equity inicial; saldos agregados por fecha, sin orden intradía",
            payback_definition="primer recupero acumulado; puede revertirse ante aportes posteriores",
            cash_sha256=sha(encoded(cash)), cumulative_by_date=dated, blockers=[])
    except (ValueError, TypeError, KeyError, AttributeError, ZeroDivisionError) as error:
        return missing(str(error))


def summarize(result, base, config):
    definition(config)
    out = dict(profile=PROFILE, definition=deepcopy(config), scenarios={},
               criterion_used=False, mathematical_summary_only=True)
    for name in ("Base", "Downside"):
        view = result["scenarios"][name]
        dates = view.get("project_calendar", {}).get("equity_dates")
        cases = {}
        for key, route in (("with_refinance", view), ("without_refinance", view.get("horizon_without_refinance"))):
            cash = route.get("cash_per_usd_10") if isinstance(route, dict) else None
            cases[key] = ledger_summary(cash, dates, base.get("rent_inputs", {}).get("irr_certificate"))
        out["scenarios"][name] = cases
    return out


def render(result):
    from check_worksheet_refinance_D45 import render_page
    from worksheet_sale_rate_grid_D84 import money
    from worksheet_irr_D122 import display_enclosure
    summaries = result["return_summary"]["scenarios"]
    routes = [(name, key) for name in ("Base", "Downside")
              for key in ("with_refinance", "without_refinance")]
    titles = ["Base refi", "Base sin refi", "Down refi", "Down sin refi"]
    cashes = {}
    for name, mode in routes:
        view = result["scenarios"][name]
        if mode == "without_refinance": view = view.get("horizon_without_refinance")
        cashes[name, mode] = (view.get("cash_per_usd_10") if isinstance(view, dict)
                             and not summaries[name][mode]["blockers"] else None)
    lines = [("Datos sintéticos | Sin dictamen de inversión | Criterios por confirmar", True),
             ("Equity agregado por USD 10 iniciales; retorno personal pendiente de términos de reparto.", False),
             ("Concepto                 | " + " | ".join(f"{s:>18}" for s in titles), True)]
    for label, key in (("Pico de equity por fecha", "peak_equity"), ("Fecha de primer recupero", "payback_date")):
        values=[]
        for name, mode in routes:
            value=summaries[name][mode].get(key)
            row = summaries[name][mode]
            empty = "No recuperado" if key == "payback_date" and not row["blockers"] else "PENDING"
            values.append((money(value) if key == "peak_equity" else value) if value is not None else empty)
        lines.append((f"{label:<25}| "+" | ".join(f"{v:>18}" for v in values), False))
    irrs=[]
    for name, mode in routes:
        v=summaries[name][mode]["irr_annual"];bounds=v.get("annual_enclosure")
        irrs.append(display_enclosure(bounds) if bounds is not None else "PENDING: sin raíz")
    lines.append(("TIR anual certificada    | "+" | ".join(f"{v:>18}" for v in irrs),True))
    for label,key in (("Aporte inicial","initial"),("Aportes adicionales","additional"),
                      ("Aportes totales","total_contributions"),("Cobros totales","total_distributions"),
                      ("Caja sin recuperar","unrecovered_after_sale"),("Múltiplo de equity","equity_multiple")):
        values=[]
        for name,mode in routes:
            c=cashes[name,mode]
            if c is None:values.append("PENDING")
            elif key == "initial":values.append(money(c["reference_amount"]))
            elif key == "additional":values.append(money(rational(cash_fraction(c["total_contributions"])-cash_fraction(c["reference_amount"]))))
            else:values.append(money(c[key]))
        lines.append((f"{label:<25}| "+" | ".join(f"{v:>18}" for v in values),False))
    lines.extend([("Aportes y cobros brutos por año y ruta; no se compensan entre sí.",True)])
    years=sorted({e["date"][:4] for cash in cashes.values() if cash is not None for e in cash["events"]})
    for year in years:
        values=[]
        for name,mode in routes:
            cash=cashes[name,mode]
            if cash is None:values.append("PENDING");continue
            es=[e for e in cash["events"] if e["date"].startswith(year)]
            if not es: values.append("Fuera de horizonte");continue
            a=sum((cash_fraction(e["amount"]) for e in es if e["kind"]=="contribution"),Fraction())
            c=sum((cash_fraction(e["amount"]) for e in es if e["kind"]=="distribution"),Fraction())
            values.append(f"A {money(rational(a))} / C {money(rational(c))}")
        lines.append((f"{year:<25}| "+" | ".join(f"{v:>18}" for v in values),False))
    for name in ("Base","Downside"):
        cal=result["scenarios"][name].get("project_calendar",{})
        lines.append((f"{name}: compra {cal.get('purchase_date','PENDING')}; estabiliza/refi {cal.get('stabilization_date','PENDING')}; venta {cal.get('sale_date','PENDING')}",False))
    lines.extend([("Sin recupero: capital no recuperado en el horizonte; el primer recupero puede revertirse.",False),
        ("Pico por fecha; la liquidez intradía requiere un calendario explícito. Detalle fechado en el expediente.",False),
        ("TIR sin prueba única: PENDING. Una celda vacía no se convierte en cero.",False)])
    return render_page("D273 | Resumen de retorno",lines,15,"MINI-UW | CAJA, TIR Y RECUPERACIÓN",
                       "Base y Downside · Con y sin refi · USD 10 de equity inicial")


def build_case(case, raw, *, current_revision_raw=None, delivery_report=False, **sources):
    from miniuw_worksheet_v1 import build_results
    from worksheet_revision_D128 import review_revision, parse_snapshot, snapshot_for_case
    base=baseline(case)
    revision=review_revision(case,current_revision_raw)
    current=parse_snapshot(current_revision_raw)
    base_current=encoded(snapshot_for_case(base,current["revision"])) if current is not None and not revision["blockers"] else None
    result,_=build_results(encoded(base),current_revision_raw=base_current,
                           delivery_report=delivery_report,**sources)
    summary=summarize(result,base,case["return_summary"])
    result=result|dict(case_sha256=sha(raw),baseline_case_sha256=sha(encoded(base)),
        revision_review=revision,return_summary=summary,summary_schema=SCHEMA)
    result["pipeline"]["case_sha256"] = result["case_sha256"]
    result["pipeline"]["version_tests"]["return_summary_suite"] = "test_worksheet_return_summary.py"
    pdf=render(result)
    result.update(pdf_sha256=sha(pdf),page_count=1)
    report_stages = [stage for stage in result["pipeline"]["stages"] if "B15" in stage.get("bots", [])]
    require(len(report_stages) == 1, "Se requiere una única traza del informe B15")
    report_stages[0].update(pdf_sha256=result["pdf_sha256"], pages=result["page_count"])
    return result,pdf
