"""Source-bound intake checklist for the synthetic refinance and sale worksheet."""
from datetime import datetime
import re

from check_operating_replay_D20 import require
from check_worksheet_refinance_D45 import CAPACITY_CELLS, worksheet_parameters
from check_worksheet_sale_costs_D63 import SALE_CELLS
from miniuw_foundation.debt_service import _fraction


FIELDS = {
    "C66": ("Cap de refinanciación", "valor de refinanciación y capacidad LTV"),
    "C67": ("Cap de salida", "valor de salida y cobro de venta"),
    "C68": ("Costo de venta variable", "cierre neto y precio mínimo de venta"),
    "C71": ("LTV máximo", "capacidad por valor del activo"),
    "C72": ("DSCR mínimo", "capacidad por cobertura de deuda"),
}
NUMERIC_RULES = {
    "C66": (lambda value: value > 0, "Ingresá un cap positivo como número decimal."),
    "C67": (lambda value: value > 0, "Ingresá un cap positivo como número decimal."),
    "C68": (lambda value: 0 <= value < 1, "Ingresá una fracción de costo desde cero y menor que uno."),
    "C71": (lambda value: value >= 0, "Ingresá un LTV máximo no negativo como número decimal."),
    "C72": (lambda value: value > 0, "Ingresá un DSCR mínimo positivo en múltiplos."),
}
CELL_REASONS = {
    "required_numeric_value_missing": ("FALTANTE", "Completá la celda con un número literal de la fuente."),
    "formula_or_error_not_resolved": ("PENDING", "Entregá el valor respaldado como número literal en una copia."),
}


def preflight(raw, deal_id, snapshot):
    require(re.fullmatch(r"SYNTHETIC-[A-Za-z0-9_-]{1,80}", deal_id),
            "Se requiere un identificador de caso sintético.")
    require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", snapshot),
            "Se requiere una fecha de corte UTC explícita en formato ISO.")
    datetime.fromisoformat(snapshot.removesuffix("Z"))

    checked = worksheet_parameters(raw, {"deal_id": deal_id}, snapshot, SALE_CELLS, include_source_cells=True)
    cells = checked["source_cells"]
    items = []
    for address, label, expected in (("B3", "Identificador de caso", deal_id), ("E3", "Fecha de corte UTC", snapshot)):
        source = cells.get(address, {"kind": "missing", "literal": None})
        actual = source["literal"]
        matches = source["kind"] == "text" and actual == expected
        items.append(dict(cell=f"Inputs!{address}", field=label, received=actual, expected=expected,
                          state="COINCIDE" if matches else "FALTANTE" if actual is None else "CONFLICTO",
                          action=None if matches else "Confirmá el caso y la fecha de corte de esta copia.",
                          affects="identidad y vigencia de la planilla"))

    mapping = CAPACITY_CELLS | SALE_CELLS
    for address, (label, consumer) in FIELDS.items():
        source = cells[address]
        row = checked["parameters"][mapping[address]]
        value = _fraction(row["value"]) if isinstance(row["value"], dict) else None
        reason = row["blockers"][0] if row["blockers"] else None
        if source["kind"] == "text":
            state, action = "INVÁLIDO", "Ingresá un número literal con la unidad indicada en la planilla."
        elif reason:
            state, action = CELL_REASONS.get(reason, ("INVÁLIDO", "Revisá el número y su formato decimal."))
        elif not NUMERIC_RULES[address][0](value):
            state, action = "INVÁLIDO", NUMERIC_RULES[address][1]
            reason = "value_outside_synthetic_consumer_domain"
        else:
            state, action = "LEÍDO", None
        items.append(dict(cell=f"Inputs!{address}", field=label, unit=row["unit_literal"], received=source["literal"],
                          cell_kind=source["kind"], value=row["value"] if state == "LEÍDO" else None,
                          formula=source["formula"], cached_value=source["cached_value"],
                          state=state, action=action, reason=reason, affects=consumer))

    for blocker in checked["blockers"]:
        address, _, reason = blocker.partition(":")
        if reason == "outside_worksheet_refinance_profile":
            items.append(dict(cell=f"Inputs!{address}", field="Campo fuera del perfil sintético",
                              received=cells[address]["literal"], state="PENDING", reason=reason,
                              action="Revisá el alcance de esta copia antes de calcular.",
                              affects="vinculación de la planilla con el perfil"))

    pending = sum(item["action"] is not None for item in items)
    return dict(status="PENDING" if pending else "checked_synthetic_inputs", decision="PENDING",
                profile="synthetic_refinance_and_costed_sale_intake",
                workbook_sha256=checked["workbook_sha256"], checked_fields=len(FIELDS),
                pending_items=pending, checklist=items, financial_calculation_run=False,
                real_decisions_enabled=False, deployment_enabled=False)
