"""Apply only explicit synthetic supporting records for a C46/C47 calendar trial."""
from copy import deepcopy

from check_operating_replay_D20 import require
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import day, object_or_empty, synthetic_id


FIELDS = {"tco_date", "sale_date", "maturity_payments", "buyer_forward_property_tax"}


def support_inventory(raw, cells):
    records = object_or_empty(raw)
    individual = object_or_empty(records.get("individual"))
    require(records.keys() == {"individual", "combined"} and individual.keys() == set(cells)
            and all(isinstance(record, dict) for record in (*individual.values(), records.get("combined"))),
            "sensitivity_calendar_support_inventory_invalid")
    tco = None
    for record in individual.values():
        if "tco_date" in record:
            require(tco is None or tco == record["tco_date"], "sensitivity_calendar_support_conflict")
            tco = record["tco_date"]
    require(records["combined"].get("tco_date") == tco, "sensitivity_calendar_combined_tco_differs")
    return records


def supported_inputs(raw, name, record):
    require(isinstance(record, dict) and {"source_ref"} <= record.keys()
            and record.keys() <= {"source_ref", *FIELDS} and synthetic_id(record["source_ref"]),
            "sensitivity_calendar_support_source_unconfirmed")
    inputs = deepcopy(raw)
    for key in ("tco_date", "sale_date", "maturity_payments"):
        if key not in record:
            continue
        entry = object_or_empty(record[key])
        require(entry.keys() == {"value", "source_ref"} and synthetic_id(entry["source_ref"]),
                f"sensitivity_calendar_support_entry_unconfirmed:{key}")
        value = entry["value"]
        if key == "maturity_payments":
            require(type(value) is int and value > 0, "sensitivity_calendar_maturity_count_unconfirmed")
            inputs["permanent_loan"]["scenarios"][name].update(maturity_payments=value, maturity_ref=entry["source_ref"])
            inputs["supplemental_scope"][name][key] = entry
        else:
            require(day(value) is not None, f"sensitivity_calendar_support_date_unconfirmed:{key}")
            if key == "tco_date":
                inputs["project_calendar"]["scenarios"][name].update(tco_date=value, tco_ref=entry["source_ref"])
            else:
                inputs["supplemental_scope"][name][key] = entry
    if "buyer_forward_property_tax" in record:
        tax = object_or_empty(record["buyer_forward_property_tax"])
        require(synthetic_id(tax.get("source_ref")), "sensitivity_calendar_buyer_tax_source_unconfirmed")
        inputs["buyer_forward_property_tax"][name] = tax
    return inputs, dict(source=record, source_sha256=sha(encoded(record)), origin_inputs_sha256=sha(encoded(raw)))
