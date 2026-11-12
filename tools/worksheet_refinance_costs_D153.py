"""Bind C73–C74 to dated refinance charges and a separate restricted reserve."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D153-refinance-costs-and-permanent-reserve"
RULES = dict(cost_basis="gross_selected_loan_actually_drawn", cost_scope="aggregate_cash_cost_excluding_payoff_and_reserve",
             reserve_basis="one_time_cash_reserve_per_confirmed_unit", reserve_scope="separate_from_c60",
             reserve_carry="no_movements_until_sale", sale_remainder="transferred_restricted_to_buyer",
             unfunded_shortfall="pending_without_explicit_equity_funding")
SOURCE_ROLES = ("cost_inventory_ref", "reserve_eligibility_ref", "sale_settlement_ref")


def declared_refinance_costs(raw, name, review, groups):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("rules") == RULES and source.get("currency") == "USD"
            and synthetic_id(source.get("source_ref")), "refinance_cost_or_reserve_scope_unconfirmed:C73-C74")
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    require(record.keys() == {*SOURCE_ROLES, "cost_inventory_declared_complete", "eligible_units", "sale_release_fraction"}
            and record["cost_inventory_declared_complete"] is True and all(synthetic_id(record[key]) for key in SOURCE_ROLES),
            "refinance_cost_inventory_or_sale_disposition_unconfirmed:C73-C74")
    units = record["eligible_units"]
    require(type(units) is int and 0 <= units <= sum(group["units"] for group in groups.values()),
            "permanent_reserve_eligible_units_unconfirmed:C74")
    fraction = _fraction(record["sale_release_fraction"])
    require(fraction is not None and 0 <= fraction <= 1, "permanent_reserve_sale_fraction_unconfirmed:C74")
    rows = {row["field_id"]: row for row in review["rows"]}
    values, refs = {}, {}
    for cell in ("C73", "C74"):
        row = rows[f"INPUT_{cell}"]
        value = _fraction(row["value"])
        require(row["state"] == "CONFIRMED_SYNTHETIC" and value is not None and value >= 0
                and (cell == "C74" or value <= 1), f"refinance_cost_or_reserve_input_unconfirmed_or_out_of_range:{cell}")
        values[cell] = value
        refs[cell] = f"sha256:{review['workbook_sha256']}#{row['value_cell']}"
    return dict(policy_ref=source["source_ref"], rules=source["rules"], cell_sources=refs, **record,
                cost_fraction=rational(values["C73"]), reserve_rate=rational(values["C74"]),
                reserve_deposit=rational(values["C74"] * units))


def settle_permanent_reserve(refinance, terms, sale_date):
    closing = refinance.payload
    balance = _fraction(closing["expected_closing_restricted_cash"])
    require(closing["state"] == "computed_synthetic_closing" and balance == _fraction(terms["reserve_deposit"])
            and closing["closing_date"] < sale_date, "permanent_reserve_does_not_match_refinance_carry")
    release = balance * _fraction(terms["sale_release_fraction"])
    return dict(funding_date=closing["closing_date"], sale_date=sale_date, opening_at_sale=rational(balance),
                released_at_sale=rational(release), transferred_restricted_to_buyer=rational(balance - release),
                refinance_closing_sha256=refinance.sha256, sale_settlement_ref=terms["sale_settlement_ref"])
