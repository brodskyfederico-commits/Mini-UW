"""Compare audited synthetic scenarios on the same USD 10 initial-equity basis."""
import json

from check_integrated_participation_D28 import TERMS, allocate
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_participant_joint_exit_D32 import BINDINGS, SCHEMA, load_sources, replay_matrix
from check_worksheet_refinance_D45 import EVENTS, annual_irr, render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.expense_cash_detail import _exact
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_investor_D74 import display, investor_view


SCENARIOS = ("Base", "Downside")


def render_comparison(views, recovery=None):
    base, downside = (views[name]["cash"] for name in SCENARIOS)
    lines = [
        (f"Cobros por USD 10 iniciales | Base USD {display(base['gross_distributions'])} | "
         f"Downside USD {display(downside['gross_distributions'])}", True),
        (f"Ganancia neta de caja | Base USD {display(base['net_cash_profit'])} | "
         f"Downside USD {display(downside['net_cash_profit'])}", True),
        (f"Aportes totales | Base USD {display(base['gross_contributions'])} | "
         f"Downside USD {display(downside['gross_contributions'])}", False),
        (f"Caja sin recuperar al vender | Base USD {display(base['cash_shortfall_at_horizon'])} | "
         f"Downside USD {display(downside['cash_shortfall_at_horizon'])}", True),
    ]
    if recovery is not None:
        def comparison(field):
            return " | ".join(f"{name} USD {display(recovery[name][field])}" for name in SCENARIOS)
        lines.append((f"Cobro neto de venta necesario por USD 10 | {comparison('minimum_net_receipt_per_usd_10')}", True))
        lines.append((f"Precio bruto mínimo del activo | {comparison('minimum_gross_price_at_cents')}", False))
    lines.append(("Calendario por USD 10 iniciales | Importes en USD", True))
    events = {}
    for name in SCENARIOS:
        for event in views[name]["cash"]["events"]:
            key = (event["date"], event["category"], event["kind"])
            values = events.setdefault(key, {})
            values[name] = values.get(name, 0) + amount(event["amount"])
    for (date, category, _), values in sorted(events.items()):
        amounts = " | ".join(f"{name} {display(rational(values[name])) if name in values else 'Sin evento'}"
                             for name in SCENARIOS)
        lines.append((f"{date}  {EVENTS[category]} | {amounts}", False))
    for name in SCENARIOS:
        cash = views[name]["cash"]
        lines.append((f"{name} | Multiplo {display(cash['equity_multiple'])}x | "
                      f"TIR anual {annual_irr(cash['annual_irr_roots'])}", False))
    lines.append(("Retorno personal real, equity retenido y CoC: pendientes.", False))
    return render_page(("D75" if recovery is None else "D82") + " | Base y Downside", lines, 23, "MINI-UW | QUE RETORNO TENGO SI INVIERTO USD 10?",
                       "PENDIENTE | Comparacion sintetica por participante")


def build_scenarios(case, case_sha256):
    _exact(case, {"schema", "joint_exit_sha256", "allocation_terms_sha256", "participant_id", "scenarios"})
    selection = case["scenarios"]
    _exact(selection, SCENARIOS)
    require(all(isinstance(key, str) for key in selection.values()) and selection["Base"] != selection["Downside"],
            "Base and Downside require separate archived cases")
    bindings_raw = local_file(ROOT, BINDINGS).read_bytes()
    terms_raw = local_file(ROOT, TERMS).read_bytes()
    require(case["joint_exit_sha256"] == sha(bindings_raw)
            and case["allocation_terms_sha256"] == sha(terms_raw), "Scenario source bytes differ")
    bindings, terms = json.loads(bindings_raw), json.loads(terms_raw)
    refinance, sales, refinance_hash, sales_hash = load_sources()
    require(bindings["schema"] == SCHEMA and bindings["refinance_fixture_sha256"] == refinance_hash
            and bindings["sale_inventory_sha256"] == sales_hash
            and bindings["allocation_terms_sha256"] == sha(terms_raw), "Joint scenario source inventory differs")
    require(set(selection.values()) <= bindings["project_ledgers"].keys(),
            "Each scenario needs an archived, capacity-cleared ledger")
    cases = replay_matrix(refinance, sales, selected=set(selection.values()))
    views = {}
    for name in SCENARIOS:
        key = selection[name]
        row, parent, _ = cases[key]
        bound_hash = bindings["project_ledgers"][key]
        allocated = allocate(terms, parent, bound_hash, require_unique_irr=False)
        view = investor_view(allocated | {"risk": observe_allocation(allocated, parent)}, case["participant_id"])
        require(view["state"] == "computed_synthetic", "Illustrative scenario cash could not be verified")
        views[name] = view | dict(archive_case=key, ledger_sha256=bound_hash,
                                 gross_sale_proceeds=row["sale_proceeds"], sale_closing_costs=row["sale_closing_costs"])
    pdf = render_comparison(views)
    return dict(state="computed_synthetic_scenario_cash", profile="investor_scenarios",
                scope="synthetic_only", decision="PENDING", real_decisions_enabled=False,
                deployment_enabled=False, personal_investor_return=None, page_count=1,
                pdf_sha256=sha(pdf), case_sha256=case_sha256, joint_exit_sha256=sha(bindings_raw),
                allocation_terms_sha256=sha(terms_raw), scenarios=views), pdf
