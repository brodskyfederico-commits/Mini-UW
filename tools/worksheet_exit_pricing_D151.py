"""Bind C66–C68 to the documented synthetic valuation and sale scopes."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D151-valuation-and-sale-pricing"
RULES = dict(refinance="annual_valuation_noi_divided_by_refinance_cap",
             exit="forward_twelve_month_noi_divided_by_exit_cap", price="sale_at_computed_exit_value",
             sale_cost="one_complete_aggregate_transaction_rate_on_gross_price",
             nonoverlap="excludes_debt_payoff_reserve_and_operating_tax")
SOURCE_ROLES = ("refinance_cap_ref", "exit_cap_ref", "sale_at_value_ref", "sale_cost_inventory_ref", "nonoverlap_ref")


def declared_valuation_terms(raw, name, review):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("rules") == RULES and source.get("currency") == "USD"
            and synthetic_id(source.get("source_ref")), "valuation_and_sale_scope_unconfirmed:C66-C68")
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    require(record.keys() == {*SOURCE_ROLES, "inventory_declared_complete"}
            and record["inventory_declared_complete"] is True and all(synthetic_id(record[role]) for role in SOURCE_ROLES),
            "valuation_evidence_or_sale_cost_inventory_unconfirmed:C66-C68")
    rows = {row["field_id"]: row for row in review["rows"]}
    values, refs = {}, {}
    for cell, key in (("C66", "refinance_cap"), ("C67", "exit_cap"), ("C68", "sale_cost_fraction")):
        row = rows[f"INPUT_{cell}"]
        value = _fraction(row["value"])
        require(row["state"] == "CONFIRMED_SYNTHETIC" and value is not None and 0 <= value <= 1
                and (cell == "C68" or value > 0), f"valuation_or_sale_rate_unconfirmed_or_out_of_range:{cell}")
        values[key] = rational(value)
        refs[cell] = f"sha256:{review['workbook_sha256']}#{row['value_cell']}"
    return dict(policy_ref=source["source_ref"], rules=source["rules"], cell_sources=refs, **record, **values)


def price_sale_costs(exit_run, terms):
    valuation = exit_run.payload
    day = valuation["valuation_date"]
    source = dict(schema="miniuw.synthetic-fixed-and-gross-percent-sale-costs.v1", context=valuation["context"],
                  currency=valuation["currency"], sale_date=day,
                  gross_price=dict(value=valuation["candidate_value"], currency=valuation["currency"], as_of_date=day,
                                   basis="projected_gross_sale_price", source_ref=f"miniuw:synthetic-exit-value:{exit_run.sha256}#/candidate_value"),
                  inventory_declared_complete=terms["inventory_declared_complete"], inventory_basis_ref=terms["sale_cost_inventory_ref"],
                  nonoverlap_basis_ref=terms["nonoverlap_ref"], costs=[dict(
                      cost_id="C68-aggregate-transaction-cost", classification="transaction_cost", kind="percent_of_gross",
                      applicability="included", applicability_basis_ref=terms["sale_cost_inventory_ref"],
                      value=terms["sale_cost_fraction"], unit="fraction_of_gross_price", currency=valuation["currency"],
                      as_of_date=day, source_ref=terms["cell_sources"]["C68"])])
    return produce_sale_costs(encoded(source))
