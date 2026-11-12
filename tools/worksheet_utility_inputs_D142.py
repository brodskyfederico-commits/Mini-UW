"""Bind the utility allowances to an explicitly separate synthetic expense."""
from fractions import Fraction

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


GROUPS = {"C25": "studio", "C26": "1BR", "C27": "2BR", "C28": "3BR"}
POLICY = "SYNTHETIC-D142-owner-paid-utilities-outside-base-opex"


def utility_expenses(raw, scenario, review, program):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("base_expenses_exclude_utilities") is True
            and synthetic_id(source.get("expense_scope_ref")), "utility_treatment_or_base_expense_scope_unconfirmed")
    inventory = object_or_empty(object_or_empty(source.get("eligible_units")).get(scenario))
    require(inventory.keys() == set(GROUPS.values()), "utility_eligible_inventory_unconfirmed")
    worksheet = {row["value_cell"]: row for row in review["rows"]}
    rows, expenses = [], []
    for cell, group in GROUPS.items():
        entry = object_or_empty(inventory[group])
        eligible = entry.get("count")
        require(synthetic_id(entry.get("source_ref")) and type(entry.get("applies")) is bool
                and type(eligible) is int and 0 <= eligible <= program[group]["units"],
                f"utility_eligible_units_unconfirmed:{cell}")
        row = worksheet[f"Inputs!{cell}"]
        if entry["applies"]:
            require(row["state"] == "CONFIRMED_SYNTHETIC", f"utility_rate_unconfirmed:{cell}")
            rate = _fraction(row["value"])
            require(rate >= 0, f"utility_rate_outside_profile:{cell}")
        else:
            require(eligible == 0 and row["state"] == "NOT_APPLICABLE", f"utility_non_applicability_unconfirmed:{cell}")
            rate = None
        annual = rational(rate * eligible * 12 if rate is not None else 0)
        locator = f"sha256:{review['workbook_sha256']}#Inputs!{cell}"
        rows.append(dict(cell=cell, group=group, eligible_units=eligible, applies=entry["applies"],
                         monthly_rate=None if rate is None else rational(rate), annual_expense=annual,
                         worksheet_source_ref=locator, eligibility_source_ref=entry["source_ref"]))
        expenses.append(dict(item_id=f"SYNTHETIC-utilities-{group}", kind="fixed_per_declared_period",
                             rate=annual, currency="USD", source_ref=locator, policy_ref=POLICY))
    total = sum((_fraction(row["annual_expense"]) for row in rows), Fraction())
    return expenses, dict(policy=POLICY, expense_scope_ref=source["expense_scope_ref"], rows=rows, annual_total=rational(total))
