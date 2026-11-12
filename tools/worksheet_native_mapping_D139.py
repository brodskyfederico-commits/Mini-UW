"""Map the original Inputs layout to scoped pilot parameters and review candidates."""
from csv import DictReader, DictWriter
from io import StringIO

from check_operating_replay_D20 import ROOT, local_file, require
from check_worksheet_refinance_D45 import CAPACITY_CELLS
from check_worksheet_sale_costs_D63 import SALE_CELLS
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet, layout
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_case_output import _cell_value
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import check, object_or_empty, synthetic_id


ORIGINAL = "sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx"
MATRIX = "docs/current-structure/MiniUW_Mapeo_55_Campos_D139.csv"
DESIGN = "docs/current-structure/"
PILOT_CELLS = CAPACITY_CELLS | SALE_CELLS
SCENARIOS = ("Base", "Downside")


def indexed_csv(name):
    with local_file(ROOT, DESIGN + name).open(encoding="utf-8", newline="") as source:
        rows = list(DictReader(source))
    indexed = {row["field_id"]: row for row in rows}
    require(len(indexed) == len(rows) == 55, "Expected exactly 55 distinct original field records")
    return indexed


def mapping_catalog():
    spec = layout()
    require(sha(local_file(ROOT, ORIGINAL).read_bytes()) == spec["source_sha256"], "The original worksheet changed")
    fields = indexed_csv("MiniUW_55_campos_D04.csv")
    connections = indexed_csv("MiniUW_Conexiones_55_campos_D08.csv")
    contracts = indexed_csv("MiniUW_Catalogo_55_Conexiones_D10.csv")
    fixed = spec["fixed_text"]
    rows = []
    for field in spec["fields"]:
        field_id = field["field_id"]
        cell = field["value_cell"]
        row, connection, contract = fields[field_id], connections[field_id], contracts[field_id]
        label = fixed[field["label_cell"]]
        unit = fixed[field["unit_cell"]]
        applicability = fixed[field["requirement_cell"]]
        require((row["variable"], row["current_literal_unit"], row["value_cell"], row["source_document"], row["source_sha256"])
                == (label, unit, f"Inputs!{cell}", ORIGINAL, spec["source_sha256"])
                and (connection["label"], connection["literal_unit"], connection["historical_requirement"])
                == (label, unit, applicability)
                and (contract["label"], contract["literal_unit"], contract["exact_location"])
                == (label, unit, row["exact_location"]), f"Conflicting documentary mapping for {field_id}")
        parameter = PILOT_CELLS.get(cell, "")
        rows.append(dict(field_id=field_id, source_document=ORIGINAL, source_sha256=spec["source_sha256"],
                         source_range=row["exact_location"], value_cell=f"Inputs!{cell}",
                         label=label, literal_unit=unit, source_requirement=applicability,
                         definition=row["provisional_definition"], role=connection["representation_role"],
                         candidate_module=row["proposed_consumers"], candidate_contract=contract["card_id"],
                         contract_location=f"{contract['document_path']}#{contract['json_pointer']}",
                         synthetic_pilot_parameter=parameter,
                         synthetic_scope="calculation_and_mapping" if parameter else "mapping_only",
                         validation_evidence="tools/check_worksheet_native_mapping_D139.py",
                         real_status="PENDING",
                         real_pending="Confirmar fuente, unidad, período, base y aplicabilidad; validar el destino financiero."))
    return rows


def matrix_csv(catalog):
    buffer = StringIO(newline="")
    writer = DictWriter(buffer, fieldnames=list(catalog[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(catalog)
    return buffer.getvalue().encode()


def check_confirmation(raw, digest, valid_ids):
    entry = object_or_empty(raw)
    if entry.get("workbook_sha256") != digest or not synthetic_id(entry.get("source_ref")):
        return set(), set(), "worksheet_confirmation_unbound"
    lists = [entry.get(key) for key in ("confirmed_fields", "not_applicable_fields")]
    if any(not isinstance(items, list) or any(type(field) is not str or field not in valid_ids for field in items)
           or len(items) != len(set(items)) for items in lists):
        return set(), set(), "worksheet_confirmation_inventory_invalid"
    confirmed, omitted = map(set, lists)
    if confirmed & omitted:
        return set(), set(), "worksheet_confirmation_conflict"
    return confirmed, omitted, None


def check_field(row, cell, confirmed, omitted):
    field_id = row["field_id"]
    empty = cell["kind"] in ("blank", "missing")
    if field_id in omitted:
        if row["source_requirement"] == "REQUIRED" or not empty:
            return "PENDING", None, ["incompatible_not_applicable_declaration"]
        return "NOT_APPLICABLE", None, []
    if field_id not in confirmed:
        return "PENDING", None, ["field_confirmation_missing"]
    if empty:
        return "PENDING", None, ["confirmed_field_value_missing"]
    unit = row["literal_unit"]
    value, blockers = _cell_value(cell, {"field_id": field_id, "unit_literal": unit})
    if not blockers:
        role = row["role"]
        if role == "basis_selector_not_a_monetary_value":
            valid = isinstance(value, str) and value in unit.split(" / ")
        elif role == "arithmetic_candidate":
            valid = isinstance(value, dict)
        else:
            valid = isinstance(value, str) and bool(value.strip())
        if not valid:
            blockers = ["literal_does_not_match_field_representation"]
    return ("PENDING", None, blockers) if blockers else ("CONFIRMED_SYNTHETIC", value, [])


def review_scenario(raw, expected, confirmation, catalog, catalog_verified):
    if raw is None or sha(raw) != expected:
        return check("native_workbook_missing_or_unbound", rows=[], calculation_inputs_ready=False)
    try:
        inspection = inspect_synthetic_input_sheet(raw)
    except ValidationError as error:
        return check("native_workbook_layout_unverified", rows=[], layout_reason=str(error), calculation_inputs_ready=False)
    cells = inspection.cells
    confirmed, omitted, issue = check_confirmation(confirmation, inspection.source_sha256,
                                                     {row["field_id"] for row in catalog})
    blockers = [issue] if issue else []
    if not catalog_verified:
        blockers.append("native_mapping_catalog_unconfirmed")
    rows = []
    for row in catalog:
        cell = cells[row["value_cell"].split("!")[1]]
        state, value, issues = check_field(row, cell, confirmed, omitted)
        rows.append(row | dict(state=state, value=value, source_literal=cell["literal"], cell_kind=cell["kind"],
                               formula=cell["formula"], cached_value=cell["cached_value"], blockers=issues))
        blockers.extend(f"{row['field_id']}:{issue}" for issue in issues)
    return dict(state="PENDING" if blockers else "checked_synthetic", blockers=blockers, rows=rows,
                workbook_sha256=inspection.source_sha256, confirmation_source_ref=object_or_empty(confirmation).get("source_ref"),
                calculation_inputs_ready=catalog_verified and all(row["state"] == "CONFIRMED_SYNTHETIC"
                    for row in rows if row["synthetic_pilot_parameter"]))


def review_native_mapping(mapping, workbooks, hashes):
    catalog = mapping_catalog()
    specification = object_or_empty(mapping)
    confirmations = object_or_empty(specification.get("scenarios"))
    digest = sha(encoded(catalog))
    verified = specification.get("catalog_sha256") == digest and not (confirmations.keys() - set(SCENARIOS))
    results = {name: review_scenario(workbooks[name], hashes.get(name), confirmations.get(name), catalog, verified)
               for name in SCENARIOS}
    blockers = [f"{name}:{reason}" for name, result in results.items() for reason in result["blockers"]]
    return dict(state="PENDING" if blockers else "checked_synthetic", catalog_sha256=digest,
                scenarios=results, blockers=blockers, real_mapping_confirmed=False)
