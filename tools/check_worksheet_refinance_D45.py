"""Replay workbook-sourced capacity, dated refinance cash and the one-page case output."""
from argparse import ArgumentParser
from base64 import b64decode
from dataclasses import replace
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys

from pypdf import PdfReader

from check_discounted_sale_recovery_D34 import validate_grid
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_refinance_variants_D31 import FIXTURE as VARIANTS, SCHEMA as VARIANT_SCHEMA, build_variant_evidence
from check_worksheet_sale_recovery_D43 import closing_net, recovery_observation, worksheet_bindings
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.capacity_project_returns import assemble_capacity_checked_returns
from miniuw_foundation.cash_risk import summarize_cash_risk
from miniuw_foundation.debt_service import rational
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet, layout
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.refinance_capacity import size_refinance
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import _pdf, _pdf_string
from miniuw_foundation.v1_report import EVENTS, amount as money, annual_irr
from miniuw_foundation.worksheet_case_output import _cell_value


FIXTURE = "templates/synthetic-worksheet-refinance-D45.json"
SCHEMA = "miniuw.synthetic-worksheet-refinance.v1"
CAPACITY_CELLS = {"C66": "cap_rate", "C71": "maximum_ltv", "C72": "minimum_dscr"}


def worksheet_parameters(raw, context, as_of, additional_cells=None, *, include_source_cells=False):
    mapped_cells = CAPACITY_CELLS | (additional_cells or {})
    sheet = inspect_synthetic_input_sheet(raw)
    cells = sheet.cells
    blockers = []
    for cell, value, blocker in (
        ("B3", context["deal_id"], "worksheet_deal_metadata_mismatch"),
        ("E3", as_of, "worksheet_snapshot_metadata_mismatch"),
    ):
        metadata = cells.get(cell, {})
        if metadata.get("kind") != "text" or metadata.get("literal") != value:
            blockers.append(blocker)

    rows = {}
    for field in layout()["fields"]:
        cell = field["value_cell"]
        if cell not in mapped_cells:
            if cells[cell]["kind"] not in ("missing", "blank"):
                blockers.append(f"{cell}:outside_worksheet_refinance_profile")
            continue
        unit = cells[field["unit_cell"]]["literal"]
        value, errors = _cell_value(cells[cell], field | {"unit_literal": unit})
        if not errors and not isinstance(value, dict):
            errors = ["required_numeric_value_missing"]
        blockers.extend(f"{cell}:{error}" for error in errors)
        rows[mapped_cells[cell]] = dict(value=value, unit_literal=unit,
                                        locator=f"xlsx:sheet:Inputs:cell:{cell}", blockers=errors)
    require(set(rows) == set(mapped_cells.values()), "Refinance field mapping differs")
    result = dict(workbook_sha256=sheet.source_sha256, parameters=rows, blockers=blockers)
    return result | {"source_cells": cells} if include_source_cells else result


def bind_worksheet_capacity(evidence, check):
    require(not check["blockers"], "Worksheet parameters must pass their checks before binding")
    source = json.loads(evidence.capacity_spec_raw)
    for name in CAPACITY_CELLS.values():
        row = check["parameters"][name]
        source["parameters"][name].update(value=row["value"],
                                          source_ref=f"sha256:{check['workbook_sha256']}#{row['locator']}")
    raw = canonical(source).encode()
    capacity = size_refinance(evidence.capacity_inputs, raw)
    binding = replace(evidence.binding, capacity_spec_sha256=sha(raw), capacity_run_sha256=capacity.sha256)
    run = assemble_capacity_checked_returns(
        evidence.periods, evidence.closings, evidence.manifest_raw, evidence.project_run,
        evidence.capacity_inputs, raw, capacity, evidence.investor_raw, binding,
    )
    return replace(evidence, capacity_spec_raw=raw, capacity_run=capacity, binding=binding, guarded_run=run)


def run_case(evidence, worksheet, context, as_of, monthly_rate=None, additional_cells=None):
    source = json.loads(evidence.capacity_spec_raw)
    require(source["context"] == context, "Worksheet and refinance case contexts differ")
    check = worksheet_parameters(worksheet, context, as_of, additional_cells)
    result = dict(state="PENDING", decision="PENDING", context=context, evaluated_as_of_UTC=as_of,
                  worksheet=check, base_evidence_sha256=evidence_fingerprint(evidence),
                  capacity=None, refinance=None, return_story=None, risk=None,
                  bank_credit_approved=False, personal_investor_return=None,
                  deployment_enabled=False, real_decisions_enabled=False)
    if monthly_rate is not None:
        result.update(monthly_discount_rate=str(monthly_rate), cash_recovery=None)
    if check["blockers"]:
        return result

    bound = bind_worksheet_capacity(evidence, check)
    raw, capacity, run = bound.capacity_spec_raw, bound.capacity_run, bound.guarded_run
    c = capacity.payload
    require(run.payload["decision"] == c["decision"] == "PENDING"
            and c["bank_credit_approved"] is c["funds_available_verified"] is False, "Refinance acquired authority")
    result["capacity"] = {key: c[key] for key in ("as_of_date", "selected_principal", "maximum_principal_capacity",
                                                 "capacity_limits", "binding_limit_ids", "blockers", "lineage")}
    result["capacity"].update(spec_sha256=sha(raw), run_sha256=capacity.sha256,
                              return_run_sha256=run.sha256, return_blockers=run.payload["blockers"])
    if run.investor_run is None:
        require(run.compiled_raw is None and run.payload["blockers"], "Blocked capacity leaked dated cash")
        return result

    story = run.investor_run.payload
    refi, sale = (closing.closing_run.payload for closing in evidence.closings)
    categories = story["cash_by_category"]
    require(amount(categories["net_refinance_distribution"]) == amount(refi["exportable_equity_distribution"])
            and amount(categories["refinance_cash_in"]) == amount(refi["exportable_equity_contribution"])
            and amount(categories["net_sale_distribution"]) == amount(sale["exportable_equity_distribution"]),
            "The guarded investor ledger differs from the reconciled closings")
    claims = json.loads(evidence.closings[0].closing_raw)["amounts"]
    sources = ("gross_proceeds", "opening_free_cash", "reserve_release", "other_cash_sources")
    uses = ("closing_costs_paid", "new_reserve", "retained_free_cash", "other_cash_uses")
    old_debt = sum(amount(value) for value in refi["payoff_totals"].values())
    source_total = sum(amount(claims[key]) for key in sources)
    use_total = sum(amount(claims[key]) for key in uses) + old_debt
    require(source_total - use_total == amount(categories["net_refinance_distribution"])
            - amount(categories["refinance_cash_in"]), "Refinance sources and uses differ from the ledger")
    bridge = {key: claims[key]["value"] for key in sources + uses}
    bridge.update(old_debt_paid=rational(old_debt), total_sources=rational(source_total), total_uses=rational(use_total))
    risk = summarize_cash_risk(run.compiled_raw, run.investor_run).payload
    require(risk["metrics"] is not None, "Project cash risk did not reconcile")
    result.update(state="computed_synthetic_worksheet_refinance", return_story=story, risk=risk["metrics"],
                  refinance=dict(date=refi["closing_date"], gross_loan=c["selected_principal"],
                                 cash_out=categories["net_refinance_distribution"], cash_in=categories["refinance_cash_in"],
                                 sale_date=sale["closing_date"], net_sale_receipt=categories["net_sale_distribution"],
                                 sources_and_uses=bridge))
    if monthly_rate is not None:
        sale_source = json.loads(evidence.closings[1].closing_raw)
        gross = amount(sale_source["amounts"]["gross_proceeds"])
        flows = validate_grid({"story": story, "evidence": {"grid": json.loads(run.compiled_raw)["grid"],
                                                           "dated_net_flows": story["dated_net_flows"]}})
        baseline = closing_net(sale_source)
        require(flows[-1]["date"] == sale_source["closing_date"]
                and amount(flows[-1]["net"]) == baseline, "Sale date or cash differs from the guarded ledger")
        recovery = recovery_observation(sale_source, flows, story["events"], monthly_rate, gross, baseline)
        result["cash_recovery"] = dict(gross_sale_price=str(gross),
                                       fixed_sale_closing_costs=str(amount(sale_source["amounts"]["closing_costs_paid"])),
                                       discount_date=flows[0]["date"], sale_date=flows[-1]["date"], **recovery)
    return result


def sources():
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    raw = local_file(ROOT, VARIANTS).read_bytes()
    require(fixture["schema"] == SCHEMA and fixture["refinance_variants_sha256"] == sha(raw),
            "Refinance variant source differs")
    variants = json.loads(raw)
    base = load_evidence(True)
    require(variants["schema"] == VARIANT_SCHEMA and variants["base_evidence_sha256"] == evidence_fingerprint(base),
            "Refinance base evidence differs")
    return fixture, base, {row["variant_id"]: row for row in variants["variants"]}


def render_case(case, row, *, sale_diagnostics=False):
    lines = []
    story = row["return_story"]
    cap = row["capacity"]
    lines.append(("Hoja sintetica | C66 tasa cap / C71 LTV maximo / C72 DSCR minimo", True))
    exit_summary = row.get("worksheet_exit")
    if exit_summary is not None:
        lines.append(("Salida desde la hoja | C67 cap de salida / C68 costo variable de venta", True))
        lines.append((f"Precio bruto proyectado USD {money(exit_summary['candidate_price'])} | "
                      f"Costo total USD {money(exit_summary['total_cost'])}", False))
    if cap is None:
        lines.append(("Hoja pendiente. Capacidad y retorno pendientes.", True))
    else:
        lines.append((f"Prestamo solicitado USD {money(cap['selected_principal'])} | Capacidad USD "
                      f"{money(cap['maximum_principal_capacity'])} | Limite: {' / '.join(cap['binding_limit_ids']) or 'Pendiente'}",
                      True))
    if story is None:
        if sale_diagnostics:
            blockers = row["sale_blockers"]
            messages = {
                "C68:required_numeric_value_missing": "Falta C68 (costo variable de venta) en la hoja.",
                "tax-unresolved:cost_applicability_unresolved": "Falta resolver si aplica el impuesto de venta.",
            }
            reasons = [message for code, message in messages.items() if code in blockers]
            if not reasons:
                reasons = ["Hay datos de venta pendientes. Ver motivos en el expediente."]
            lines.extend((reason, True) for reason in reasons)
        elif row["worksheet"]["blockers"]:
            lines.append(("Falta cotejar un dato requerido o la identidad de la hoja.", False))
        elif exit_summary is not None:
            lines.append(("El cierre de venta permanece pendiente.", False))
        elif cap["blockers"]:
            lines.append(("Capacidad pendiente para el prestamo seleccionado.", False))
        lines.append(("Sin cifras de aportes, cobros ni retorno en esta corrida.", True))
    else:
        r = row["refinance"]
        lines.append((f"Refinanciacion {r['date']} | Cobro neto USD {money(r['cash_out'])} | "
                      f"Aporte requerido USD {money(r['cash_in'])}", True))
        bridge = r["sources_and_uses"]
        lines.append((f"Fuentes refi USD {money(bridge['total_sources'])}: prestamo, caja de apertura y reserva liberada.", False))
        lines.append((f"Usos refi USD {money(bridge['total_uses'])}: deuda anterior, costos, nueva reserva y caja retenida.", False))
        lines.append((f"Venta {r['sale_date']} | Cobro neto USD {money(r['net_sale_receipt'])}", True))
        lines.append((f"Aportes USD {money(story['gross_contributions'])} | Cobros USD {money(story['gross_distributions'])} | "
                      f"Neto USD {money(story['net_cash_profit'])}", True))
        lines.append((f"Multiplo {money(story['equity_multiple'])} | TIR anual {annual_irr(story['annual_irr_roots'])}", False))
        lines.append(("Movimientos del equity del proyecto", True))
        for event in sorted(story["events"], key=lambda event: event["date"]):
            lines.append((f"{event['date']}  {EVENTS[event['category']]}  USD {money(event['amount'])}", False))
        for year in story["annual_cash_receipts"]:
            lines.append((f"{year['calendar_cash_receipt_year']} | Cobro operativo USD "
                          f"{money(year['operating_distributions_only'])} | CoC {money(year['conditional_coc'])}", False))
        lines.append((f"Caja sin recuperar USD {money(row['risk']['cash_shortfall_at_horizon'])} | "
                      f"Pico neto USD {money(row['risk']['peak_cumulative_net_equity_funding_at_date_close'])}", False))
    if "cash_recovery" in row:
        recovery = row["cash_recovery"]
        if recovery is None:
            lines.append(("Precio de recuperacion en valor presente: Pendiente.", True))
        else:
            cents = recovery["minimum_gross_sale_price_in_cents"]
            minimum = f"{cents // 100}.{cents % 100:02d}"
            rate = money(rational(Fraction(recovery["monthly_discount_rate"]) * 100))
            lines.append((f"Venta bruta USD {recovery['gross_sale_price']} | Minimo VP USD {minimum} | "
                          f"Tasa sintetica {rate}% mensual", True))
    participation = row.get("synthetic_cash_participation")
    if participation is not None:
        if participation["participants"] is None:
            lines.append(("Reparto sintetico pendiente. Ver motivos en el expediente.", True))
        else:
            lines.append(("Reparto hipotetico | Aportes / cobros / ganancia neta (USD)", True))
            for part in participation["participants"]:
                amounts = " / ".join(money(part[field]) for field in
                                     ("gross_contributions", "gross_distributions", "net_cash_profit"))
                lines.append((f"{part['participant_id']} | {amounts}", False))
    lines.append(("Capital remanente, equity retenido y retorno personal pendientes.", False))
    lines.append(("Criterios de inversion pendientes | Capacidad sintetica sin aprobacion bancaria.", False))

    spacing = 16 if participation is not None else 18 if exit_summary is not None else 20
    return render_page(case, lines, spacing, "MINI-UW | HOJA, REFINANCIACION Y VENTA",
                       "PENDIENTE | Prueba sintetica | Equity agregado del proyecto")


def render_page(case, lines, spacing, title, subtitle):
    commands = [b"0.06 0.17 0.25 rg 24 524 744 64 re f"]
    header = [(566, 15, title), (546, 10, subtitle), (532, 7, "Caso " + case)]
    for y, size, label in header:
        commands.append(f"1 1 1 rg BT /F2 {size} Tf 1 0 0 1 36 {y} Tm (".encode() + _pdf_string(label) + b") Tj ET")
    for i, (label, bold) in enumerate(lines):
        y = 498 - spacing * i
        require(y >= 60 and len(label) * 10 * 0.6 <= 736, "Refinance report exceeds one page")
        commands.append(f'0.06 0.17 0.25 rg BT /{"F2" if bold else "F1"} 10 Tf 1 0 0 1 28 {y} Tm ('.encode()
                        + _pdf_string(label) + b") Tj ET")
    pdf = _pdf(commands)
    pages = PdfReader(BytesIO(pdf)).pages
    require(len(pages) == 1, "Refinance report must have exactly one page")
    extracted = pages[0].extract_text()
    require(all(text in extracted for text, _ in lines), "Refinance report text did not reproduce")
    return pdf


def replay(selected=None, monthly_rate=None):
    if monthly_rate is not None:
        _, rates = worksheet_bindings()
        require(monthly_rate in rates, "Monthly rate is outside the archived sensitivity grid")
    fixture, base, variants = sources()
    evidence_by_variant = {}
    for key, case in fixture["cases"].items():
        if selected is not None and key != selected:
            continue
        variant = case["variant"]
        if variant not in evidence_by_variant:
            evidence_by_variant[variant] = build_variant_evidence(base, variants[variant])
        entry = fixture["workbooks"][case["workbook"]]
        worksheet = b64decode(entry["xlsx_base64"], validate=True)
        require(sha(worksheet) == entry["sha256"], "Worksheet bytes differ")
        result = run_case(evidence_by_variant[variant], worksheet, fixture["scenario_context"],
                          fixture["worksheet_as_of_UTC"], monthly_rate)
        blocked = result["worksheet"]["blockers"] + ([] if result["capacity"] is None else result["capacity"]["blockers"])
        require((result["return_story"] is not None and not blocked) if case["expected_blocker"] is None
                else (result["return_story"] is None and case["expected_blocker"] in blocked),
                f"Unexpected worksheet refinance gate: {key}")
        pdf = render_case(key, result)
        yield key, result | {"pdf_sha256": sha(pdf), "page_count": 1}, pdf


def summary():
    cases = {key: row for key, row, _ in replay()}
    require(len(cases) == 7, "Unexpected worksheet refinance case inventory")
    return dict(status="passed", decision="PENDING", worksheet_refinance_sha256=digest(canonical(cases)),
                pages=len(cases), computed=sum(row["return_story"] is not None for row in cases.values()),
                pending=sum(row["return_story"] is None for row in cases.values()))


if __name__ == "__main__":
    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", action="store_true")
    group.add_argument("--case")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--monthly-rate", type=Fraction)
    args = parser.parse_args()
    try:
        if args.summary:
            require(args.output is args.monthly_rate is None, "Summary does not accept report options")
            result = summary()
        else:
            require(args.output is not None, "A new PDF output path is required")
            matches = list(replay(args.case, args.monthly_rate))
            require(len(matches) == 1, "Unknown synthetic refinance case")
            _, result, pdf = matches[0]
            with TemporaryDirectory(dir=args.output.parent, prefix=".miniuw-refinance-") as staging:
                prepared = Path(staging) / "summary.pdf"
                prepared.write_bytes(pdf)
                os.link(prepared, args.output)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
