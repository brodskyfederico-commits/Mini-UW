"""Check the documented ranges and insurance quote before using worksheet assumptions."""
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import check, day, number, object_or_empty, synthetic_id


SCHEMA = "miniuw.synthetic-market-insurance-evidence.v1"
RENT_FIELDS = ("C8", "C9", "C10", "C11")
RENT_UNITS = {"PER UNIT": "USD_per_unit_per_month", "PER SF": "USD_per_rentable_sf_per_month"}
RANGE_FIELDS = {"rent": RENT_FIELDS, "concessions": ("C15",), "absorption": ("C47",), "exit_cap": ("C67",)}


def read_record(envelope, name, role, deal_id, as_of, unit, basis, fields):
    envelope = object_or_empty(envelope)
    if not envelope:
        return check(f"market_evidence_missing:{role}")
    doc = object_or_empty(envelope.get("document"))
    digest = sha(encoded(doc))
    evidence = dict(document=doc, observed_sha256=digest, declared_sha256=envelope.get("sha256"))
    expected = {"source_ref", "observed_on", "valid_through", "deal_id", "scenario", "unit", "basis", *fields}
    if (envelope.keys() != {"document", "sha256"} or envelope.get("sha256") != digest
            or doc.keys() != expected or not synthetic_id(doc.get("source_ref"))):
        return check(f"market_evidence_binding_unconfirmed:{role}", **evidence)
    start, end = day(doc["observed_on"]), day(doc["valid_through"])
    if start is None or end is None or as_of is None or not start <= as_of <= end:
        return check(f"market_evidence_outside_validity:{role}", **evidence)
    if (not unit or not basis or not synthetic_id(deal_id)
            or (doc["scenario"], doc["deal_id"], doc["unit"], doc["basis"]) != (name, deal_id, unit, basis)):
        return check(f"market_evidence_scope_mismatch:{role}", **evidence)
    return check(**evidence)


def check_range(reading, role, cells, rows, workbook_sha):
    if reading["blockers"]:
        return reading
    intervals = object_or_empty(reading["document"]["ranges"])
    if intervals.keys() != set(cells):
        return reading | check(f"market_evidence_fields_unconfirmed:{role}")
    comparisons, blockers = {}, []
    for cell in cells:
        row = rows.get(cell, {})
        interval = object_or_empty(intervals[cell])
        low, high = number(interval.get("minimum")), number(interval.get("maximum"))
        selected = number(row.get("value"))
        source = row.get("alternative_value_source_ref") or f"sha256:{workbook_sha}#{row.get('value_cell')}"
        comparisons[cell] = dict(value=row.get("value"), range=interval, value_source=source)
        if row.get("state") != "CONFIRMED_SYNTHETIC" or selected is None:
            blockers.append(f"market_workbook_value_unconfirmed:{cell}")
        elif (interval.keys() != {"minimum", "maximum"} or low is None or high is None or not 0 <= low <= high
              or (role in ("concessions", "exit_cap") and high > 1)
              or (role == "exit_cap" and low == 0)
              or (role == "absorption" and (low.denominator != 1 or high.denominator != 1))):
            blockers.append(f"market_range_unconfirmed:{cell}")
        elif not low <= selected <= high:
            blockers.append(f"market_assumption_outside_evidence:{cell}")
    return reading | dict(state="PENDING" if blockers else "checked_synthetic", blockers=blockers, comparisons=comparisons)


def check_insurance(reading, rows, workbook_sha, cost_record):
    if reading["blockers"]:
        return reading
    doc = reading["document"]
    row = rows.get("C59", {})
    rate, quote = number(row.get("value")), number(doc["premium_per_insured_unit"])
    units = doc["insured_units"]
    comparison = dict(value=row.get("value"), value_source=f"sha256:{workbook_sha}#{row.get('value_cell')}",
                      insured_units=cost_record.get("insured_units"), coverage_ref=cost_record.get("insurance_coverage_ref"))
    if row.get("state") != "CONFIRMED_SYNTHETIC" or rate is None:
        blocker = "market_workbook_value_unconfirmed:C59"
    elif (quote is None or quote < 0 or type(units) is not int or units < 0
          or not synthetic_id(doc["coverage_ref"])):
        blocker = "insurance_quote_fields_unconfirmed:C59"
    elif (quote, units, doc["coverage_ref"]) != (rate, comparison["insured_units"], comparison["coverage_ref"]):
        blocker = "insurance_quote_disagrees:C59"
    else:
        blocker = None
    return reading | check(blocker) | dict(comparison=comparison)


def review_assumptions(rent_inputs, name, review):
    rent_inputs = object_or_empty(rent_inputs)
    inventory = object_or_empty(rent_inputs.get("market_evidence"))
    scenarios = object_or_empty(inventory.get("scenarios"))
    if not inventory or not scenarios.get(name):
        return check("market_evidence_inventory_missing")
    records = object_or_empty(scenarios[name])
    if (inventory.keys() != {"schema", "scenarios"} or inventory.get("schema") != SCHEMA
            or not scenarios.keys() <= {"Base", "Downside"} or not records.keys() <= {*RANGE_FIELDS, "insurance"}):
        return check("market_evidence_inventory_invalid")
    rows = {row["field_id"].removeprefix("INPUT_"): row for row in review["rows"]}
    workbook_sha = review["workbook_sha256"]
    rent_basis = rows.get("C7", {}).get("value")
    policy = object_or_empty(rent_inputs.get("policy"))
    specs = {
        "rent": (RENT_UNITS.get(rent_basis) if isinstance(rent_basis, str) else None, "gross_before_losses_and_concessions"),
        "concessions": ("fraction", policy.get("concession_basis")),
        "absorption": ("months", "tco_to_stabilization"),
        "exit_cap": ("annual_cap_fraction", "forward_twelve_month_noi_divided_by_exit_cap"),
    }
    raw_date = rent_inputs.get("as_of_UTC")
    as_of = day(raw_date.split("T", 1)[0]) if isinstance(raw_date, str) else None
    deal_id = rent_inputs.get("deal_id")
    checks = {}
    for role, cells in RANGE_FIELDS.items():
        unit, basis = specs[role]
        reading = read_record(records.get(role), name, role, deal_id, as_of, unit, basis, ("ranges",))
        checks[role] = check_range(reading, role, cells, rows, workbook_sha)

    cost_records = object_or_empty(object_or_empty(rent_inputs.get("operating_costs")).get("scenarios"))
    quote = read_record(records.get("insurance"), name, "insurance", deal_id, as_of, "USD_per_insured_unit_per_year",
                        "residential_insurance", ("premium_per_insured_unit", "insured_units", "coverage_ref"))
    checks["insurance"] = check_insurance(quote, rows, workbook_sha, object_or_empty(cost_records.get(name)))
    blockers = [reason for row in checks.values() for reason in row["blockers"]]
    return dict(state="PENDING" if blockers else "checked_synthetic", blockers=blockers, records=checks)
