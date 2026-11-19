"""Bind the confirmed C60 rate to the synthetic restricted cash policy."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D149-replacement-reserve"
RULES = dict(classification="restricted_cash_excluded_from_noi_and_valuation",
             deposit_timing="annual_operating_settlement_before_sale", period_months=12,
             opening_balance="zero_and_no_other_reserve_movements_before_sale",
             shortfall_funding="equity_at_operating_settlement", sale_remainder="transferred_restricted_to_buyer")


def declared_reserve(raw, name, review, groups, *, integrated_horizon=False):
    source = object_or_empty(raw)
    policy,rules=POLICY,RULES
    if integrated_horizon:
        from worksheet_holding_horizon_D266 import RESERVE_POLICY,RESERVE_RULES
        policy,rules=RESERVE_POLICY,RESERVE_RULES
    require(source.get("policy") == policy and source.get("rules") == rules and source.get("currency") == "USD"
            and synthetic_id(source.get("source_ref")), "replacement_reserve_policy_unconfirmed:C60")
    scenario = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    units = scenario.get("eligible_units")
    require(type(units) is int and 0 <= units <= sum(row["units"] for row in groups.values())
            and synthetic_id(scenario.get("eligible_units_ref")), "replacement_reserve_units_unconfirmed:C60")
    row = next(item for item in review["rows"] if item["field_id"] == "INPUT_C60")
    rate = _fraction(row["value"])
    require(row["state"] == "CONFIRMED_SYNTHETIC" and rate is not None and rate >= 0,
            "replacement_reserve_rate_unconfirmed_or_negative:C60")
    fraction = _fraction(scenario.get("sale_release_fraction"))
    require(fraction is not None and 0 <= fraction <= 1 and synthetic_id(scenario.get("sale_settlement_ref")),
            "replacement_reserve_sale_disposition_unconfirmed:C60")
    return dict(policy_ref=source["source_ref"], rules=source["rules"],
                cell_source=row.get("sensitivity_value_source_ref", f"sha256:{review['workbook_sha256']}#{row['value_cell']}"),
                annual_rate=rational(rate), eligible_units=units, eligible_units_ref=scenario["eligible_units_ref"],
                deposit=rational(rate * units), sale_release_fraction=rational(fraction),
                sale_settlement_ref=scenario["sale_settlement_ref"])
