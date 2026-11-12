"""Bind C57–C59 to the documented residential expense scope."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D148-worksheet-operating-costs"
RULES = dict(controllable="annual_per_declared_residential_unit_including_c25_to_c28",
             management="effective_residential_rent_plus_c13_excluding_commercial",
             insurance="annual_per_confirmed_insured_residential_unit_paid_within_operating_window",
             fixed_costs="separate_from_controllable_management_insurance_and_property_tax", period_months=12)


def declared_costs(raw, name, review, groups, utilities):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("rules") == RULES and source.get("currency") == "USD"
            and synthetic_id(source.get("source_ref")), "operating_expense_scope_unconfirmed:C57-C59")
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    total_units = sum(group["units"] for group in groups.values())
    controllable_units, insured_units = record.get("controllable_units"), record.get("insured_units")
    require(type(controllable_units) is int and controllable_units == total_units
            and synthetic_id(record.get("controllable_units_ref")), "controllable_unit_inventory_unconfirmed:C57")
    require(type(insured_units) is int and 0 <= insured_units <= total_units
            and synthetic_id(record.get("insurance_coverage_ref")), "insured_unit_inventory_unconfirmed:C59")
    rows = {row["value_cell"].split("!")[1]: row for row in review["rows"]}
    rates, refs = {}, {}
    for cell in ("C57", "C58", "C59"):
        row = rows[cell]
        value = _fraction(row["value"])
        require(row["state"] == "CONFIRMED_SYNTHETIC" and value is not None and value >= 0,
                f"operating_expense_rate_unconfirmed_or_negative:{cell}")
        rates[cell] = value
        refs[cell] = f"sha256:{review['workbook_sha256']}#{row['value_cell']}"
    require(rates["C58"] <= 1, "management_fraction_outside_profile:C58")
    total = rates["C57"] * controllable_units
    utility_total = _fraction(utilities["annual_total"])
    require(utility_total <= total, "utilities_exceed_controllable_budget:C57")
    return dict(policy_ref=source["source_ref"], rules=source["rules"], cell_sources=refs,
                controllable_units=controllable_units, controllable_units_ref=record["controllable_units_ref"],
                controllable_total=rational(total), utilities_in_controllable=rational(utility_total),
                controllable_excluding_utilities=rational(total - utility_total), management_rate=rational(rates["C58"]),
                insured_units=insured_units, insurance_coverage_ref=record["insurance_coverage_ref"],
                insurance_total=rational(rates["C59"] * insured_units))


def expense_items(costs, other_income, other_income_ref):
    refs = costs["cell_sources"]
    management_rate = costs["management_rate"]
    return [dict(item_id=key, kind=kind, rate=rate, currency="USD", source_ref=source, policy_ref=costs["policy_ref"])
            for key, kind, rate, source in (
                ("controllable_excluding_utilities", "fixed_per_declared_period", costs["controllable_excluding_utilities"], refs["C57"]),
                ("management", "fraction_of_residential_effective_rent", management_rate, refs["C58"]),
                ("management_other_income", "fixed_per_declared_period", rational(_fraction(management_rate) * other_income),
                 f"{refs['C58']} and {other_income_ref}"),
                ("insurance", "fixed_per_declared_period", costs["insurance_total"], refs["C59"]))]


def period_evidence(costs, rows, other_income):
    items = {row["item_id"]: row for row in rows["expenses"]}
    effective = _fraction(rows["residential_effective_rent"])
    fee = sum(_fraction(items[key]["amount"]) for key in ("management", "management_other_income"))
    return costs | dict(management_eligible_egi=rational(effective + other_income), management_fee=rational(fee),
                        expense_rows=rows["expenses"])
