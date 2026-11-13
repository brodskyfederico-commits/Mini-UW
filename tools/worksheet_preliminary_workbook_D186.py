"""Calculate a bounded residential LOI cash projection from two native Inputs sheets."""
from fractions import Fraction
import re
from zipfile import BadZipFile

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet, layout
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_case_output import _cell_value
from worksheet_local_sources_D127 import day
from worksheet_preliminary_D185 import POLICY, SCENARIOS, SUPPORT, assumption_ready, estimate, finish_preliminary
from worksheet_project_calendar_D145 import offset


PROFILE = "synthetic_preliminary_loi_workbook"
NUMERIC = (
    "C8", "C9", "C10", "C11", "C13", "C14", "C15", "C32", "C33", "C35",
    "C37", "C38", "C39", "C40", "C42", "C46", "C47", "C51", "C57", "C58", "C59", "C60", "C62", "C67", "C68", "C75", "C76",
)
FRACTIONS = ("C14", "C15", "C33", "C39", "C40", "C42", "C58", "C67", "C68")


def read_inputs(raw, deal, name, cutoff):
    binding = deal["scenarios"].get(name)
    if raw is None or not isinstance(binding, dict) or binding.get("workbook_sha256") != sha(raw):
        return {}, ["planilla ausente o huella distinta"]
    try:
        book = inspect_synthetic_input_sheet(raw)
    except (ValidationError, BadZipFile):
        return {}, ["plantilla Inputs incompatible"]
    cells = book.cells
    if any(cells.get(ref, {}).get("literal") != expected for ref, expected in
           (("B3", deal["id"]), ("E3", deal["as_of"]))):
        return {}, ["identidad o fecha de la planilla incompatible"]
    if any(cells[ref]["kind"] not in ("blank", "missing") for ref in ("C16", "C17", "C18", "C25", "C26", "C27", "C28", "C41")):
        return {}, ["celdas comerciales o servicios fuera del perfil residencial"]
    if any(cells[ref]["kind"] != "text" or cells[ref]["literal"] != expected for ref, expected in
           (("C7", "PER UNIT"), ("C34", "TOTAL"))):
        return {}, ["C7 o C34: base de renta o costo fuera del perfil"]

    fields = {f["value_cell"]: f for f in layout()["fields"]}
    values, blockers = {}, []
    for ref in NUMERIC:
        field = fields[ref]
        value, issues = _cell_value(cells[ref], dict(field, unit_literal=cells[field["unit_cell"]]["literal"]))
        if not issues and isinstance(value, dict):
            try:
                values[ref] = amount(value, 12)
                continue
            except ValidationError:
                pass
        blockers.append(f"{ref}: valor numérico faltante o inválido")
    if blockers:
        return {}, blockers

    support = binding.get("support")
    if not isinstance(support, dict) or set(support) != set(SUPPORT):
        return {}, ["inventario de respaldos incompleto"]
    for key in SUPPORT:
        row = support[key]
        if (not assumption_ready(row, cutoff) or not isinstance(row.get("summary"), str)
                or not row["summary"].strip()):
            return {}, ["supuesto sin respaldo: " + key]
    units = support["program"].get("units")
    carry = support["calendar"].get("lease_up_carry_usd_per_quarter")
    parking_spaces = support["acquisition_and_costs"].get("parking_spaces")
    if (support["exit"].get("reserve_at_sale") != "release_to_equity"
            or support["acquisition_and_costs"].get("scope") != "residential_budget_complete"
            or support["rent_and_expenses"].get("scope") != "stabilized_residential_expenses_complete"):
        return {}, ["alcance de costos, operación o liberación de reservas sin confirmar"]
    if (not isinstance(units, list) or len(units) != 4 or any(type(x) is not int or not 0 <= x <= 10000 for x in units)
            or sum(units) == 0 or type(carry) is not int or not 0 <= carry <= 10**9
            or type(parking_spaces) is not int or not 0 <= parking_spaces <= 10000):
        return {}, ["faltan unidades, estacionamientos o costo trimestral de absorción"]
    if (any(values[ref] < 0 for ref in NUMERIC if ref not in ("C75", "C76"))
            or any(values[ref] > 1 for ref in FRACTIONS)
            or any(not -1 < values[ref] <= 1 for ref in ("C75", "C76"))
            or any(values[ref] for ref in ("C15", "C51")) or values["C67"] == 0):
        return {}, ["concesiones, deuda, cap o rangos fuera del perfil"]
    return dict(values=values, support=support, workbook_sha256=book.source_sha256, units=units, carry=carry,
                parking_spaces=parking_spaces), []


def project(case, deal, name, raw, cutoff):
    inputs, blockers = read_inputs(raw, deal, name, cutoff)
    if blockers:
        return dict(cash=None, blockers=blockers)

    v, support = inputs["values"], inputs["support"]
    dates = case["dates"]
    construction, lease_up = v["C46"], v["C47"]
    if construction < 3 or construction % 3 or lease_up % 3 or construction + lease_up >= 3 * (len(dates) - 1):
        return dict(cash=None, blockers=["C46/C47: calendario trimestral incompatible"])
    finish = int(construction / 3)
    stabilize = finish + int(lease_up / 3)
    units = sum(inputs["units"])
    initial = v["C32"] * (1 + v["C33"])
    direct_hard = v["C35"] + v["C37"] * inputs["parking_spaces"] + v["C38"]
    hard = direct_hard * (1 + v["C39"])
    soft = hard * v["C40"]
    construction_cost = hard + soft
    early_soft = soft * v["C42"]
    gross_rent = 12 * sum(v[f"C{8 + i}"] * n for i, n in enumerate(inputs["units"]))
    other_income = 12 * v["C13"] * units
    fixed_opex = units * (v["C57"] + v["C59"])
    property_tax = units * v["C62"]
    annual_reserve = units * v["C60"]

    def operating(years):
        rent = gross_rent * (1 - v["C14"]) * (1 + v["C75"]) ** years
        opex = fixed_opex * (1 + v["C76"]) ** years
        return rent + other_income - rent * v["C58"] - opex - property_tax

    events = []

    def event(category, index, value, basis, refs):
        provenance = support[basis]
        events.append(dict(category=category, date=dates[index], amount=rational(value),
                           source_ref=f"sha256:{inputs['workbook_sha256']}#Inputs!{refs}",
                           as_of=provenance["as_of"], owner=provenance["owner"]))

    if initial <= 0:
        return dict(cash=None, blockers=["C32: aporte inicial de compra debe ser positivo"])
    event("initial_capital", 0, initial, "acquisition_and_costs", "C32:C33")
    if finish == 1:
        event("additional_capital", finish, construction_cost, "acquisition_and_costs", "C34:C42")
    else:
        event("additional_capital", 1, early_soft, "acquisition_and_costs", "C40:C42")
        event("additional_capital", finish, construction_cost - early_soft, "acquisition_and_costs", "C34:C42")
    for i in range(finish + 1, stabilize + 1):
        event("additional_capital", i, Fraction(inputs["carry"]), "calendar", "C46:C47")
    restricted = Fraction()
    for i in range(stabilize + 1, len(dates)):
        cash = (operating((i - stabilize - 1) // 4) - annual_reserve) / 4
        restricted += annual_reserve / 4
        event("operating_distribution" if cash >= 0 else "additional_capital", i, abs(cash), "rent_and_expenses", "C7:C15,C57:C62,C75:C76")

    sale_noi = sum((operating((i - stabilize) // 4) for i in range(len(dates) - 1, len(dates) + 3)), Fraction()) / 4
    if sale_noi <= 0:
        return dict(cash=None, blockers=["NOI de salida no positivo"])
    net_sale = sale_noi / v["C67"] * (1 - v["C68"])
    event("net_sale_distribution", len(dates) - 1, net_sale + restricted, "exit", "C60,C67:C68")
    if not any(e["category"] == "operating_distribution" for e in events):
        event("operating_distribution", len(dates) - 1, Fraction(), "rent_and_expenses", "C7:C15,C57:C62,C75:C76")
    projected = {"scenarios": {name: dict(support=support, events=events)}, "id": deal["id"]}
    view = estimate(case, projected, name, cutoff)
    return view | dict(worksheet_sha256=inputs["workbook_sha256"], cell_sources={
        ref: f"sha256:{inputs['workbook_sha256']}#Inputs!{ref}" for ref in (*NUMERIC, "C7", "C34")},
        projection=dict(land_and_closing=rational(initial), construction=rational(construction_cost),
                        sale_noi=rational(sale_noi), sale_net_before_reserve_release=rational(net_sale),
                        reserve_released_at_sale=rational(restricted), stabilization_date=dates[stabilize]))


def build_preliminary_workbook(case, raw, workbooks):
    require(set(case) == {"schema", "policy", "as_of", "dates", "financing", "focus", "scenarios"}
            and case["policy"] == POLICY and case["financing"] == "without_refinance",
            "Expected a bounded synthetic residential case without debt")
    require(isinstance(case["focus"], str) and re.fullmatch(r"SYNTHETIC-[A-Z0-9-]{1,22}", case["focus"]),
            "Explicit synthetic case identity required")
    cutoff = day(case["as_of"])
    dates = case["dates"]
    require(cutoff and isinstance(dates, list) and 3 <= len(dates) <= 9 and day(dates[0])
            and day(dates[0]) >= cutoff, "Explicit quarterly dates and cutoff required")
    require(dates == [offset(day(dates[0]), 3 * i).isoformat() for i in range(len(dates))],
            "Expected a common quarterly grid")
    require(isinstance(case["scenarios"], dict) and case["scenarios"].keys() <= set(SCENARIOS),
            "Unknown scenario")
    deal = case | {"id": case["focus"]}
    views = {deal["id"]: dict(scenarios={n: project(case, deal, n, workbooks[n], cutoff) for n in SCENARIOS})}
    return finish_preliminary(case, raw, views, profile=PROFILE)
