"""Bind confirmed C61 and C62 to the explicitly scoped synthetic tax model."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D150-property-tax-and-noi"
RULES = dict(comparable="whole_asset_annual_tax_per_declared_residential_unit",
             assessment="fraction_of_noi_based_market_value_proxy",
             payable="maximum_of_comparable_and_assessed_value_proxy",
             exclusions="no_abatement_cap_or_other_tax_adjustments",
             period_scope="same_scope_for_all_twelve_month_model_windows",
             operating_cash="annual_accrued_tax_settled_at_operating_cutoff")
RATE_UNIT = "annual_USD_per_USD_assessed"
CAP_UNIT = "annual_cap_fraction"


def declared_property_tax(raw, name, review, groups):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("rules") == RULES and source.get("currency") == "USD"
            and synthetic_id(source.get("source_ref")), "property_tax_scope_unconfirmed:C61-C62")
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    units = record.get("comparable_units")
    require(type(units) is int and units == sum(row["units"] for row in groups.values()) and units > 0
            and synthetic_id(record.get("comparable_source_ref")), "property_tax_comparable_units_or_scope_unconfirmed:C62")
    require(synthetic_id(record.get("assessment_source_ref")), "property_tax_assessment_source_unconfirmed:C61")
    rate_record = object_or_empty(record.get("assessed_tax_rate"))
    cap_record = object_or_empty(record.get("market_proxy_cap"))
    rate = _fraction(rate_record.get("value"))
    cap = _fraction(cap_record.get("value"))
    require(rate is not None and 0 <= rate <= 1 and rate_record.get("unit") == RATE_UNIT
            and synthetic_id(rate_record.get("source_ref")), "property_tax_rate_or_unit_unconfirmed:C61")
    require(cap is not None and 0 < cap <= 1 and cap_record.get("unit") == CAP_UNIT
            and synthetic_id(cap_record.get("source_ref")), "property_tax_market_proxy_cap_unconfirmed:C61")
    rows = {row["field_id"]: row for row in review["rows"]}
    assessment, comparable = (rows[f"INPUT_{cell}"] for cell in ("C61", "C62"))
    ratio = _fraction(assessment["value"])
    comparable_rate = _fraction(comparable["value"])
    require(assessment["state"] == "CONFIRMED_SYNTHETIC" and ratio is not None and 0 <= ratio <= 1,
            "property_tax_assessment_ratio_unconfirmed_or_out_of_range:C61")
    require(comparable["state"] == "CONFIRMED_SYNTHETIC" and comparable_rate is not None and comparable_rate >= 0,
            "property_tax_comparable_rate_unconfirmed_or_negative:C62")
    cells = {cell: row.get("sensitivity_value_source_ref", f"sha256:{review['workbook_sha256']}#{row['value_cell']}")
             for cell, row in (("C61", assessment), ("C62", comparable))}
    return dict(policy_ref=source["source_ref"], rules=source["rules"], cell_sources=cells, comparable_units=units,
                comparable_source_ref=record["comparable_source_ref"], assessment_source_ref=record["assessment_source_ref"],
                assessment_ratio=rational(ratio), comparable_rate=rational(comparable_rate),
                assessed_tax_rate=rate_record, market_proxy_cap=cap_record,
                floor=rational(comparable_rate * units), coefficient=rational(ratio * rate / cap))
