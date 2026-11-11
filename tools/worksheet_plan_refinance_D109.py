"""Run a separately declared synthetic refinance request for the revised D105 plan."""
from fractions import Fraction
import re

from check_operating_replay_D20 import ROOT, local_file, require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.expense_cash_detail import _exact
from miniuw_foundation.scheduled_expense_case import sha
from plan_refinance_D108 import run_scenario
from plan_schedule_D105 import FIXTURE_A, FIXTURE_B, compare_schedules
from worksheet_sale_rate_grid_D84 import money


CASE_SCHEMA = "miniuw.synthetic-plan-refinance-request.v1"
PROFILE = "synthetic_revised_plan_refinance"
CAPACITY_BLOCKER = "selected_principal_exceeds_declared_bank_capacity"
SCENARIOS = ("Base", "Downside")
LABELS = {
    "initial_capital": "Aporte inicial",
    "additional_capital": "Aporte adicional",
    "net_refinance_distribution": "Cobro neto de refinanciación",
    "operating_distribution": "Cobro de operación después de cuota",
    "net_sale_distribution": "Cobro neto de venta después de cancelar deuda",
}


def render_request(case, principal, scenarios):
    lines = [(f"Plano A-601, revisión 2 | Solicitud bruta USD {money(rational(principal))} a nivel proyecto.", False)]
    for scenario, view in scenarios.items():
        cash = view["cash_per_usd_10"]
        if cash is None:
            lines.append((f"{scenario} | Retorno por USD 10 PENDING", True))
        else:
            lines.append((f"{scenario} | Por USD 10 iniciales cobrás USD {money(cash['total_distributions'])} en total.", True))
        capacity = view["capacity"]
        if capacity is not None and capacity["maximum_principal_capacity"] is not None:
            limit = ", ".join(capacity["binding_limit_ids"])
            lines.append((f"Capacidad del proyecto USD {money(capacity['maximum_principal_capacity'])} | Límite {limit}.", False))
        if cash is None:
            if CAPACITY_BLOCKER in view["blockers"]:
                lines.append(("La solicitud supera la capacidad. La caja de este escenario queda pendiente.", False))
            else:
                lines.append(("Faltan datos conciliados para mostrar aportes o cobros. Ver resultados.", False))
            continue
        lines.extend((f"{event['date']} | {LABELS[event['category']]} USD {money(event['amount'])}", False)
                     for event in cash["events"] if _fraction(event["amount"]))
        lines.append((f"Total aportado USD {money(cash['total_contributions'])} | Sin recuperar USD "
                      f"{money(cash['unrecovered_after_sale'])} al vender.", False))
    lines.append(("Equity agregado, cifras sintéticas. Condiciones reales y decisión de inversión pendientes.", False))
    return render_page(case["request_id"], lines, 19, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "PENDIENTE | Plan revisado y solicitud de refinanciación sintética")


def build_request(case, case_sha256):
    _exact(case, {"schema", "request_id", "reference_plan_sha256", "revised_plan_sha256", "requested_principal_usd"})
    require(case["schema"] == CASE_SCHEMA and isinstance(case["request_id"], str)
            and re.fullmatch(r"SYNTHETIC-[A-Za-z0-9_-]{1,54}", case["request_id"]),
            "A separate explicit synthetic request identity is required")
    principal = _fraction(case["requested_principal_usd"], 18)
    require(principal is not None and principal > 0 and (principal * 100).denominator == 1,
            "A positive explicit requested principal in USD cents is required")
    before, after = (local_file(ROOT, name).read_bytes() for name in (FIXTURE_A, FIXTURE_B))
    comparison = compare_schedules(before, after)
    require(case["reference_plan_sha256"] == comparison["reference_sha256"]
            and case["revised_plan_sha256"] == comparison["candidate_sha256"],
            "The exact synthetic reference and revised plans are required")
    scenarios = {name: run_scenario(comparison, "after", name, principal) for name in SCENARIOS}
    for view in scenarios.values():
        cap = view["capacity"]
        view["capacity_margin_usd"] = None
        if cap is not None and cap["maximum_principal_capacity"] is not None:
            view["capacity_margin_usd"] = rational(_fraction(cap["maximum_principal_capacity"]) - principal)
    state = "PENDING" if any(view["cash_per_usd_10"] is None for view in scenarios.values()) else "computed_synthetic_scenario_cash"
    pdf = render_request(case, principal, scenarios)
    return dict(profile=PROFILE, state=state, decision="PENDING", scope="synthetic_aggregate_equity",
                request_id=case["request_id"], requested_principal_usd=rational(principal), case_sha256=case_sha256,
                plan_comparison=comparison, scenarios=scenarios, pdf_sha256=sha(pdf), page_count=1,
                personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False), pdf
