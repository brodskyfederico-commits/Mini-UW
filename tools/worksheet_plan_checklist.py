"""Propagate architecture preflight findings to the calculations that depend on them."""

from decimal import Decimal


# Prerequisites appear before their consumers. A clear documentary gate only
# certifies the plan inputs that this profile checks.
DEPENDENCIES = {
    "unit_count": (),
    "unit_mix": ("unit_count",),
    "residential_rentable_area": ("unit_mix",),
    "commercial_area": (),
    "reserves_by_unit": ("unit_count",),
    "construction_cost_by_unit": ("unit_count",),
    "residential_costs_by_type": ("unit_mix",),
    "residential_rent_by_unit": ("unit_mix",),
    "residential_rent_by_area": ("residential_rentable_area",),
    "commercial_rent": ("commercial_area",),
    # No rent basis has been verified in documentary intake. Carry both
    # potential dependencies to the shared NOI until C7 can select the route.
    "noi": ("residential_costs_by_type", "residential_rent_by_unit", "residential_rent_by_area", "commercial_rent"),
    "operating_cash": ("noi", "reserves_by_unit"),
    "refinance_capacity": ("noi",),
    "sale_valuation": ("noi",),
    "return_per_usd_10": ("operating_cash", "construction_cost_by_unit", "refinance_capacity", "sale_valuation"),
}
FINDINGS = {
    "floor_index_missing": ("unit_count", "Confirmá el índice de láminas de piso."),
    "unlisted_floor_sheet": ("unit_count", "Conciliá la lámina de piso con el índice."),
    "incomplete_unit_labels": ("unit_count", "Completá los rótulos de unidad en la lámina."),
    "duplicate_unit_id": ("unit_count", "Conciliá el identificador repetido entre las láminas citadas."),
    "unit_total_mismatch": ("unit_count", "Conciliá el total de viviendas declarado y el observado."),
    "unit_mix_mismatch": ("unit_mix", "Conciliá el conteo de esta tipología con las láminas de piso."),
    "unit_area_missing": ("residential_rentable_area", "Confirmá la superficie rentable de este tipo en el cuadro de áreas."),
    "unit_area_schedule_missing": ("residential_rentable_area", "Incorporá el cuadro documentado de áreas rentables."),
    "cover_area_unreadable": ("commercial_area", "Confirmá el área comercial de la portada."),
    "narrative_area_unreadable": ("commercial_area", "Confirmá el área comercial de la carta de revisión."),
    "commercial_area_mismatch": ("commercial_area", "Conciliá las superficies comerciales con la revisión aplicable."),
}
SHEET_FINDINGS = {
    "missing_sheet": "Incorporá la lámina indicada.",
    "duplicate_sheet": "Identificá la lámina aplicable entre las copias.",
    "ambiguous_sheet": "Confirmá la identidad de la lámina indicada.",
    "site_tables_unreadable": "Confirmá las tablas de unidades y áreas en A1.0.",
}


def affected_inputs(finding):
    code = finding["code"]
    if code in SHEET_FINDINGS:
        sheets = finding.get("candidates", [finding.get("sheet")])
        inputs = ["unit_count"]
        if any(sheet in {"A1.0", "G0.0"} for sheet in sheets):
            inputs.append("commercial_area")
        return inputs, SHEET_FINDINGS[code]
    if code not in FINDINGS:
        return ["unit_count", "commercial_area"], "Revisá el hallazgo documental antes de habilitar los cálculos."
    key, action = FINDINGS[code]
    return [key], action


def plan_preflight(findings):
    checklist = []
    for index, finding in enumerate(findings, 1):
        inputs, action = affected_inputs(finding)
        affects = []
        for key, dependencies in DEPENDENCIES.items():
            if key in inputs or any(dependency in affects for dependency in dependencies):
                affects.append(key)
        checklist.append({"id": f"plan-{index}", "reason": finding["code"], "state": "PENDING", "action": action,
                          "evidence": finding, "direct_inputs": inputs, "affects": affects})
    calculations = {}
    for key in DEPENDENCIES:
        blockers = [row["id"] for row in checklist if key in row["affects"]]
        calculations[key] = {"documentary_state": "PENDING" if blockers else "CLEAR", "plan_blockers": blockers}
    return {"status": "PENDING" if checklist else "READ", "pending_items": len(checklist), "checklist": checklist,
            "calculations": calculations, "financial_calculation_run": False}


def calculate_if_plan_clear(preflight, key, produce):
    if preflight["calculations"][key]["documentary_state"] == "CLEAR":
        return produce()
    return None


def plan_values(preflight, site, units, schedule):
    """Emit only documentary values whose prerequisites passed the checklist."""
    producers = {
        "unit_count": lambda: site["units"],
        "unit_mix": lambda: site["unit_mix"],
        "residential_rentable_area": lambda: str(sum(
            (Decimal(schedule[unit["unit_type"]]["area_sf"]) for unit in units), Decimal(0))),
        "commercial_area": lambda: site["commercial_total_sf"],
    }
    return {key: calculate_if_plan_clear(preflight, key, produce) for key, produce in producers.items()}
