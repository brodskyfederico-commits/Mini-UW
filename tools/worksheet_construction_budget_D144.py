"""Bind C37–C42 to the synthetic construction budget and dated funding."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from plan_return_D107 import DATES, INITIAL
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D144-construction-budget"
BASES = dict(contingency_base="vertical_parking_site", soft_base="hard_including_contingency",
             cost_scope="separate_vertical_parking_site_and_ti_lc", soft_scope="includes_dev_fee_excludes_ti_lc")
TIMING = dict(window_start=DATES[0], early_date=DATES[1], remainder_date=DATES[2],
              early_scope="hard_including_funded_reserve_ti_lc_and_upfront_soft",
              remainder_scope="remaining_soft_only")


def confirmed_number(rows, cell, *, fraction=False):
    row = rows[cell]
    require(row["state"] == "CONFIRMED_SYNTHETIC", f"construction_budget_field_unconfirmed:{cell}")
    value = _fraction(row["value"])
    require(value is not None and value >= 0 and (not fraction or value <= 1),
            f"construction_budget_value_outside_profile:{cell}")
    return value


def construction_budget(raw, name, review, development, commercial):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("currency") == "USD"
            and synthetic_id(source.get("policy_ref")) and source.get("bases") == BASES,
            "construction_budget_scope_or_base_unconfirmed")
    schedule = object_or_empty(source.get("schedule"))
    require(schedule.get("terms") == TIMING and synthetic_id(schedule.get("source_ref")),
            "construction_funding_schedule_unconfirmed:C42")
    scenario = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    require(synthetic_id(scenario.get("scope_source_ref")), "construction_budget_line_scope_unconfirmed")
    inventory = object_or_empty(scenario.get("parking"))
    spaces = inventory.get("spaces")
    require(type(spaces) is int and 0 <= spaces <= 10000 and synthetic_id(inventory.get("source_ref")),
            "parking_quantity_or_source_unconfirmed:C37")
    rows = {row["value_cell"].split("!")[1]: row for row in review["rows"]}
    parking_rate = confirmed_number(rows, "C37")
    parking = parking_rate * spaces
    site = confirmed_number(rows, "C38")
    contingency_rate = confirmed_number(rows, "C39", fraction=True)
    soft_rate = confirmed_number(rows, "C40", fraction=True)
    upfront_share = confirmed_number(rows, "C42", fraction=True)
    uses = commercial["uses"]
    area = sum(_fraction(use["area"]) for use in uses.values())
    if uses:
        ti_rate = confirmed_number(rows, "C41")
        ti_lc = ti_rate * area
    else:
        require(rows["C41"]["state"] == "NOT_APPLICABLE", "ti_lc_non_applicability_unconfirmed:C41")
        ti_rate, ti_lc = None, 0

    direct_hard = _fraction(development["vertical_cost"]) + parking + site
    reserve = contingency_rate * direct_hard
    hard = direct_hard + reserve
    soft = soft_rate * hard
    upfront = soft * upfront_share
    remainder = soft - upfront
    land = _fraction(development["evaluated_purchase_price"]) + _fraction(development["land_closing_cost"])
    total = land + hard + soft + ti_lc
    early_uses = land + hard + ti_lc + upfront
    early_equity = max(0, early_uses - INITIAL)
    late_equity = total - INITIAL - early_equity
    draws = [dict(event_id="construction-early", date=TIMING["early_date"], amount=rational(early_equity)),
             dict(event_id="construction-late", date=TIMING["remainder_date"], amount=rational(late_equity))]
    cell_sources = {cell: f"sha256:{review['workbook_sha256']}#{rows[cell]['value_cell']}" for cell in
                    ("C37", "C38", "C39", "C40", "C41", "C42")}
    amounts = dict(parking_rate=parking_rate, parking_cost=parking, site_cost=site, direct_hard_cost=direct_hard,
                   contingency_rate=contingency_rate, contingency_reserve=reserve, hard_budget=hard,
                   soft_rate=soft_rate, soft_budget=soft, commercial_area_sf=area, ti_lc_cost=ti_lc,
                   upfront_soft_share=upfront_share, upfront_soft=upfront, remaining_soft=remainder,
                   total_development_cost=total, uses_and_reserve_through_early_date=early_uses)
    return {key: rational(value) for key, value in amounts.items()} | dict(
        cell_sources=cell_sources, policy_ref=source["policy_ref"], bases=source["bases"],
        scope_source_ref=scenario["scope_source_ref"], parking_spaces=spaces, parking_source_ref=inventory["source_ref"],
        ti_lc_rate=None if ti_rate is None else rational(ti_rate),
        commercial_area_source_refs={key: use["source_ref"] for key, use in uses.items()},
        commercial_inventory_source_ref=commercial["inventory_source_ref"], schedule=schedule, equity_draws=draws)
