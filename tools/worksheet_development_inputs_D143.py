"""Bind evaluated land purchase and vertical hard cost to confirmed C32–C36."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from plan_return_D107 import DATES, INITIAL
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D143-evaluated-purchase-and-vertical-cost"


def confirmed(worksheet, cell):
    row = worksheet[cell]
    require(row["state"] == "CONFIRMED_SYNTHETIC", f"development_field_unconfirmed:{cell}")
    return row["value"]


def vertical_quantity(basis, worksheet, declaration, groups):
    if basis != "$/GSF":
        require(worksheet["C36"]["state"] == "NOT_APPLICABLE", "construction_gsf_non_applicability_unconfirmed:C36")
        if basis == "TOTAL":
            return 1, declaration["vertical_source_ref"]
        require(basis == "$/UNIT" and synthetic_id(declaration.get("program_source_ref")),
                "construction_unit_inventory_unconfirmed")
        count = sum(group["units"] for group in groups.values())
        require(count > 0, "construction_unit_inventory_unconfirmed")
        return count, declaration["program_source_ref"]

    plan = object_or_empty(declaration.get("plan_gsf"))
    require(synthetic_id(plan.get("source_ref")), "construction_plan_gsf_unconfirmed")
    if plan.get("state") == "TBD":
        require(plan.get("value") is None and synthetic_id(declaration.get("worksheet_gsf_source_ref")),
                "construction_worksheet_gsf_source_unconfirmed:C36")
        quantity = _fraction(confirmed(worksheet, "C36"))
        ref = declaration["worksheet_gsf_source_ref"]
    else:
        require(plan.get("state") == "declared" and worksheet["C36"]["state"] == "NOT_APPLICABLE",
                "construction_gsf_source_conflict:C36")
        quantity = _fraction(plan.get("value"))
        ref = plan["source_ref"]
    require(quantity is not None and quantity > 0, "construction_gsf_missing_or_nonpositive")
    return quantity, ref


def development_costs(raw, scenario, review, groups):
    source = object_or_empty(raw)
    declaration = object_or_empty(object_or_empty(source.get("scenarios")).get(scenario))
    require(source.get("policy") == POLICY and source.get("currency") == "USD"
            and source.get("closing_base") == "evaluated_purchase_price"
            and source.get("vertical_scope") == "building_excluding_parking_and_site"
            and synthetic_id(source.get("policy_ref"))
            and synthetic_id(declaration.get("vertical_source_ref")), "development_cost_scope_unconfirmed")
    worksheet = {row["value_cell"].split("!")[1]: row for row in review["rows"]}
    asking = _fraction(confirmed(worksheet, "C32"))
    price = _fraction(declaration.get("evaluated_purchase_price"))
    require(price is not None and price >= 0 and asking == price and synthetic_id(declaration.get("purchase_source_ref"))
            and declaration.get("purchase_date") == DATES[0], "evaluated_purchase_price_unconfirmed_or_mismatched:C32")
    fraction = _fraction(confirmed(worksheet, "C33"))
    require(0 <= fraction <= 1, "land_closing_cost_fraction_outside_profile:C33")
    basis = confirmed(worksheet, "C34")
    rate = _fraction(confirmed(worksheet, "C35"))
    require(rate >= 0, "vertical_cost_outside_profile:C35")
    quantity, quantity_ref = vertical_quantity(basis, worksheet, declaration, groups)
    land_closing = price * fraction
    vertical = rate * quantity
    total = price + land_closing + vertical
    require(price + land_closing <= INITIAL <= total, "development_costs_outside_declared_equity_schedule")
    cells = {f"C{i}": f"sha256:{review['workbook_sha256']}#Inputs!C{i}" for i in range(32, 37)}
    return dict(policy_ref=source["policy_ref"], cell_sources=cells, purchase_date=declaration["purchase_date"],
                worksheet_asking=rational(asking), evaluated_purchase_price=rational(price),
                purchase_source_ref=declaration["purchase_source_ref"], closing_fraction=rational(fraction),
                land_closing_cost=rational(land_closing), vertical_basis=basis, vertical_rate_or_total=rational(rate),
                vertical_quantity=rational(quantity), quantity_source_ref=quantity_ref, vertical_cost=rational(vertical),
                vertical_source_ref=declaration["vertical_source_ref"], total_development_cost=rational(total))
