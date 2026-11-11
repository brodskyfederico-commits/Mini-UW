"""Gate an actual synthetic Inputs workbook before the costed-sale run."""
from fractions import Fraction
import json

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_refinance_variants_D31 import build_variant_evidence
from check_worksheet_exit_D62 import FIXTURE as SOURCE_FIXTURE, inputs
from check_worksheet_refinance_D45 import render_page
from check_worksheet_sale_costs_D63 import calculate
from check_worksheet_sale_recovery_D43 import worksheet_bindings
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.expense_cash_detail import _exact
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_plan_refinance_D109 import LABELS
from worksheet_preflight_D116 import preflight
from worksheet_sale_rate_grid_D84 import money


PROFILE = "synthetic_workbook_intake_and_costed_sale"
VARIANT = "SYNTHETIC-D31-lower"


def initial_equity_cash(story):
    require(story["currency"] == "USD" and story["cash_metrics_state"] == "computed_synthetic",
            "A verified USD project cash ledger is required")
    initial = [event for event in story["events"]
               if event["kind"] == "contribution" and event["category"] == "initial_capital"]
    basis = sum(amount(event["amount"]) for event in initial)
    require(basis > 0, "The USD 10 initial-equity basis is unavailable")
    scale = Fraction(10) / basis
    events = [event | {"amount": rational(amount(event["amount"]) * scale)}
              for event in sorted(story["events"], key=lambda row: row["date"])]
    paid = amount(story["gross_contributions"]) * scale
    received = amount(story["gross_distributions"]) * scale
    return dict(reference_amount=rational(10), basis_event_ids=[event["event_id"] for event in initial],
                basis_amount=rational(basis), scale_factor=rational(scale), events=events,
                total_contributions=rational(paid), total_distributions=rational(received),
                net_cash_profit=rational(received - paid), unrecovered_after_sale=rational(max(0, paid - received)))


def render(result):
    check = result["preflight"]
    lines = [(f"Planilla Inputs | Huella {check['workbook_sha256'][:16]} | Perfil sintético", False)]
    cash = result["cash_per_usd_10"]
    if cash is None:
        lines.append(("Retorno por USD 10 PENDING", True))
        pending = [row for row in check["checklist"] if row["action"] is not None]
        for row in pending[:8]:
            lines.append((f"{row['cell']} | {row['state']} | {row['action']}", False))
        if len(pending) > 8:
            lines.append((f"Quedan {len(pending) - 8} bloqueos adicionales en el expediente.", False))
        if not pending:
            lines.append(("El checklist está completo. Quedan bloqueos en la corrida financiera.", False))
        else:
            lines.append(("La corrida espera la corrección de los datos requeridos.", False))
    else:
        lines.append((f"Por USD 10 iniciales cobrás USD {money(cash['total_distributions'])} en total.", True))
        for event in cash["events"]:
            if amount(event["amount"]):
                label = LABELS.get(event["category"], "Movimiento de capital")
                lines.append((f"{event['date']} | {label} USD {money(event['amount'])}", False))
        lines.append((f"Aportes totales USD {money(cash['total_contributions'])} | "
                      f"Saldo sin recuperar USD {money(cash['unrecovered_after_sale'])}", True))
        sale = result["worksheet_exit"]
        lines.append((f"Venta bruta USD {money(sale['candidate_price'])} | "
                      f"Costo de venta USD {money(sale['total_cost'])} a nivel del proyecto.", False))
        recovery = result["cash_recovery"]
        minimum = rational(_fraction(result["monthly_discount_rate"]) * 100)
        cents = recovery["minimum_gross_price_in_cents"]
        price = f"{cents // 100},{cents % 100:02d}"
        lines.append((f"Venta mínima en VP USD {price} | Tasa {money(minimum)} % mensual.", False))
    lines.append(("Capital agregado del proyecto. Decisión de inversión PENDING.", False))
    return render_page("D117 | Ingreso y corrida de la planilla", lines, 20,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "PENDIENTE | Chequeo de ingreso y resultado sintético")


def build_intake_case(case, case_sha256, workbook_raw):
    _exact(case, {"schema", "source_fixture_sha256", "monthly_discount_rate"})
    raw = local_file(ROOT, SOURCE_FIXTURE).read_bytes()
    require(sha(raw) == case["source_fixture_sha256"], "The synthetic case basis has changed")
    origin = json.loads(raw)
    _, rates = worksheet_bindings()
    rate = _fraction(case["monthly_discount_rate"])
    require(rate in rates, "An explicit rate from the synthetic monthly grid is required")
    context = origin["scenario_context"]
    as_of = origin["worksheet_as_of_UTC"]
    check = preflight(workbook_raw, context["deal_id"], as_of)
    result = dict(profile=PROFILE, scope="synthetic_aggregate_equity", state="PENDING", decision="PENDING",
                  case_sha256=case_sha256, source_fixture_sha256=sha(raw), preflight=check,
                  monthly_discount_rate=rational(rate), context=context, evaluated_as_of_UTC=as_of,
                  worksheet_exit=None, capacity=None, cash_per_usd_10=None, cash_recovery=None,
                  financial_calculation_run=False, calculation_blockers=[],
                  personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False)
    if not check["pending_items"]:
        origin, base, variants, noi_raw, noi, spec = inputs(raw)
        evidence = build_variant_evidence(base, variants[VARIANT])
        request = dict(id=f"D117-{check['workbook_sha256'][:16]}", unresolved_tax=False)
        calculated = calculate(request, workbook_raw, origin, evidence, noi_raw, noi, spec, (rate,), with_report=True)
        require(calculated["worksheet"]["workbook_sha256"] == check["workbook_sha256"],
                "The calculation did not use the preflight workbook")
        result.update(financial_calculation_run=True, calculation_blockers=calculated["blockers"],
                      costed_sale_sha256=calculated.get("costed_sale_sha256"))
        if calculated["state"] == "computed_synthetic_costed_sale":
            report = calculated["report"]
            result.update(state="computed_synthetic_project_cash",
                          worksheet_exit=dict(candidate_price=calculated["candidate_price"],
                                              total_cost=calculated["total_cost"]),
                          capacity=report["capacity"], cash_recovery=calculated["recovery"][str(rate)],
                          cash_per_usd_10=initial_equity_cash(report["return_story"]))
    pdf = render(result)
    return result | dict(pdf_sha256=sha(pdf), page_count=1), pdf
