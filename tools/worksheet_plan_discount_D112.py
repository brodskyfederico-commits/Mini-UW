"""Run a one-page worksheet comparison at an explicitly supplied monthly rate."""
from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import require
from check_worksheet_refinance_D45 import render_page
from compare_refinance_discount_D111 import OPTIONS, monthly_flows, percent
from compare_revised_plan_D110 import EVENT_ROWS, TOTAL_ROWS, build_comparison
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.expense_cash_detail import _exact
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import PLAN_REFINANCE_REQUEST_SCHEMA, encoded
from worksheet_plan_refinance_D109 import CAPACITY_BLOCKER, SCENARIOS
from worksheet_sale_rate_grid_D84 import money


PROFILE = "synthetic_revised_plan_discount_comparison"


def compare_at_rate(nominal, rate):
    scenarios = {}
    for name, variants in nominal["cases"].items():
        cases = {}
        for option, view in variants.items():
            amounts = view["amounts"]
            value = None if amounts is None else rational(present_value(monthly_flows(amounts), rate))
            cases[option] = view | {"npv_per_usd_10": value}
        npv_without, npv_with = (_fraction(cases[key]["npv_per_usd_10"], 1300) for key in OPTIONS)
        if npv_without is None or npv_with is None:
            scenarios[name] = dict(state="PENDING", alternatives=cases, refi_minus_no_refi=None, higher_npv=None)
            continue
        delta = npv_with - npv_without
        higher = "with_refinance" if delta > 0 else "without_refinance" if delta < 0 else "equal"
        scenarios[name] = dict(state="computed_synthetic", alternatives=cases,
                               refi_minus_no_refi=rational(delta), higher_npv=higher)
    return scenarios


def render(nominal, scenarios, rate, *, include_recovery=False):
    columns = [scenarios[name]["alternatives"][option] for name in SCENARIOS for option in OPTIONS]
    width = 14 if include_recovery else 12
    options = "".join(f"{label:>{width}}" for label in ("Sin refi", "Con refi", "Sin refi", "Con refi"))
    # Expose very small positive supplied rates without presenting them as explicit zero.
    rate_label = percent(rational(rate), 4)
    if rate and rate_label == "0,0000 %":
        rate_label = f"{rate.numerator}/{rate.denominator} mensual (fracción)"
    else:
        rate_label += " mensual"
    lines = [
        (f"Plano A-601 revisado | Tasa de descuento {rate_label}", True),
        ("Cobros y aportes nominales en USD por USD 10 de equity inicial.", False),
        (f"{' ':<{40 + width // 2}}{'Base':^{width * 2}}{'Downside':^{width * 2}}", True),
        (f"{'Flujo y fecha':<40}{options}", True),
    ]
    for key, label, day, kind in EVENT_ROWS + TOTAL_ROWS:
        when = "  " + "/".join(reversed(day.split("-"))) if kind is not None else ""
        cells = ["PENDING" if case["amounts"] is None else money(case["amounts"][key]) for case in columns]
        lines.append((f"{label + when:<40}" + "".join(f"{cell:>{width}}" for cell in cells), kind is None))
    cells = ["PENDING" if case["npv_per_usd_10"] is None else money(case["npv_per_usd_10"]) for case in columns]
    lines.append((f"{'VAN al 30/03/2027':<40}" + "".join(f"{cell:>{width}}" for cell in cells), True))
    lines.append(("El VAN descuenta cobros y aportes. El orden se calcula con valores exactos.", False))
    descriptions = {"with_refinance": "con refi", "without_refinance": "sin refi", "equal": "empate"}
    for name, scenario in scenarios.items():
        if scenario["higher_npv"] is None:
            refi = scenario["alternatives"]["with_refinance"]
            if CAPACITY_BLOCKER in refi["blockers"]:
                capacity = money(refi["capacity"]["maximum_principal_capacity"])
                lines.append((f"{name} | Comparación PENDING. Capacidad del proyecto USD {capacity}.", True))
            else:
                lines.append((f"{name} | Comparación PENDING. Ver bloqueos en el expediente.", True))
        else:
            lines.append((f"{name} | Mayor VAN: {descriptions[scenario['higher_npv']]}.", True))
    whole, cents = money(nominal["requested_principal_usd"]).split(",")
    principal = f"{int(whole):,}".replace(",", ".") + "," + cents
    lines.append((f"Solicitud sintética bruta USD {principal}. Decisión de inversión PENDING.", False))
    if include_recovery:
        from worksheet_plan_sale_recovery_D113 import recovery_lines
        lines.extend(recovery_lines(columns, width))
    return render_page(nominal["refinance_request_id"], lines, 20,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "PENDIENTE | Comparación de una página con y sin refinanciación")


def build_discount_comparison(case, case_sha256, *, include_recovery=False):
    _exact(case, {"schema", "refinance_request", "monthly_discount_rate"})
    request = case["refinance_request"]
    require(isinstance(request, dict) and request.get("schema") == PLAN_REFINANCE_REQUEST_SCHEMA,
            "An explicit synthetic plan refinance request is required")
    rate = _fraction(case["monthly_discount_rate"], 18)
    require(rate is not None and rate >= 0, "An explicit nonnegative monthly discount rate is required")
    nominal = build_comparison(encoded(request), include_sale_basis=include_recovery)
    scenarios = compare_at_rate(nominal, rate)
    if include_recovery:
        from worksheet_plan_sale_recovery_D113 import add_sale_recovery
        add_sale_recovery(scenarios, rate)
    pdf = render(nominal, scenarios, rate, include_recovery=include_recovery)
    state = "PENDING" if any(row["state"] == "PENDING" for row in scenarios.values()) else "computed_synthetic_scenario_cash"
    return dict(profile=PROFILE, state=state, decision="PENDING", scope="synthetic_aggregate_equity",
                monthly_discount_rate=rational(rate), discount_date=EVENT_ROWS[0][2],
                case_sha256=case_sha256, pdf_sha256=sha(pdf), page_count=1,
                scenarios=scenarios, provenance={key: value for key, value in nominal.items()
                                                 if key.endswith("sha256") or key == "refinance_request_id"},
                requested_principal_usd=nominal["requested_principal_usd"],
                personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False), pdf
