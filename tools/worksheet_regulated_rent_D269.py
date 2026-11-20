"""Explicit AMI rent-limit schedules, separate from owner-paid utility expenses.

All fractions, imputed household sizes, utility allowances and future schedules
are supplied with sources. This producer grants no eligibility or tax benefit.
"""
from datetime import date
from fractions import Fraction

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import synthetic_id
from worksheet_project_calendar_D145 import offset


SCHEMA = "miniuw.synthetic-native-rental-inputs.v35"
PROFILE = "miniuw.synthetic-documented-AMI-rent-limits.v1"
RULES = dict(
    scope="rent_limits_only_no_tax_density_or_eligibility_benefit",
    cap_basis="gross_monthly_rent_including_tenant_paid_utilities",
    gross_cap="annual_AMI_income_times_income_limit_fraction_times_rent_income_share_divided_by_12",
    net_cap="gross_monthly_cap_minus_explicit_tenant_utility_allowance",
    selection="lower_of_projected_market_rent_and_net_regulated_cap",
    allocation="explicit_regulated_and_market_units_reconciled_by_unit_group",
    period="annual_complete_windows_from_stabilization_including_forward_exit_year",
    expenses="utility_allowance_does_not_modify_owner_utility_expenses",
    forecasts="every_window_has_its_own_explicit_values_and_validity_no_inherited_growth",
    leaseup="separately_documented_net_shortfall_in_project_calendar",
)
GROUPS = {"C8": "studio", "C9": "1BR", "C10": "2BR", "C11": "3BR"}
NUMBERS = ("annual_AMI_income", "income_limit_fraction", "rent_income_share", "utility_allowance_monthly")
UNITS = dict(annual_AMI_income="USD_per_year", income_limit_fraction="fraction",
             rent_income_share="fraction", utility_allowance_monthly="USD_per_unit_per_month")


def quantity(record, key):
    entry = record.get(key)
    require(isinstance(entry, dict) and set(entry) == {"value", "unit", "source_ref"}
            and entry["unit"] == UNITS[key] and synthetic_id(entry["source_ref"]),
            "regulated_rent_value_unit_or_source_missing:" + key)
    value = _fraction(entry["value"])
    require(value is not None and value >= 0, "regulated_rent_explicit_nonnegative_value_required:" + key)
    return value


def annual_starts(calendar):
    start = date.fromisoformat(calendar["stabilization_date"])
    months = calendar["holding_months"]
    require(type(months) is int and 12 <= months <= 60 and months % 12 == 0,
            "regulated_rent_supported_horizon_required")
    return [str(offset(start, i)) for i in range(0, months + 1, 12)]


def configuration(raw, name, groups, calendar, *, rent_basis):
    require(isinstance(raw, dict) and set(raw) == {"profile", "currency", "rules", "source_ref", "scenarios"}
            and raw["currency"] == "USD"
            and raw["profile"] == PROFILE and raw["rules"] == RULES and synthetic_id(raw["source_ref"])
            and set(raw["scenarios"]) == {"Base", "Downside"}, "regulated_rent_contract_missing")
    require(rent_basis == "per_unit_per_month", "regulated_rent_requires_documented_per_unit_basis")
    source = raw["scenarios"][name]
    require(isinstance(source, dict) and set(source) == {"source_ref", "leaseup_assumption_ref", "allocations", "windows"}
            and synthetic_id(source["source_ref"]) and synthetic_id(source["leaseup_assumption_ref"])
            and set(source["allocations"]) == set(GROUPS.values()),
            "regulated_rent_allocation_inventory_missing")
    for group, allocation in source["allocations"].items():
        require(isinstance(allocation, dict) and set(allocation) == {"regulated_units", "market_units", "source_ref"}
                and synthetic_id(allocation["source_ref"]), "regulated_rent_allocation_source_missing:" + group)
        regulated, market = allocation["regulated_units"], allocation["market_units"]
        require(type(regulated) is type(market) is int and regulated >= 0 and market >= 0
                and regulated + market == groups[group]["units"], "regulated_rent_unit_count_discrepancy:" + group)
    expected = annual_starts(calendar)
    require(isinstance(source["windows"], dict) and set(source["windows"]) == set(expected),
            "regulated_rent_annual_and_forward_inventory_incomplete")
    for start, window in source["windows"].items():
        require(isinstance(window, dict) and set(window) == {"source_ref", "evidence_kind", "valid_from", "valid_until_exclusive", "limits"}
                and window["evidence_kind"] in {"synthetic_observation", "synthetic_forecast"}
                and synthetic_id(window["source_ref"]) and set(window["limits"]) == set(GROUPS.values()),
                "regulated_rent_window_source_or_group_missing:" + start)
        end = offset(date.fromisoformat(start), 12)
        require(date.fromisoformat(window["valid_from"]) <= date.fromisoformat(start)
                and date.fromisoformat(window["valid_until_exclusive"]) >= end,
                "regulated_rent_evidence_does_not_cover_complete_window:" + start)
        for group, limit in window["limits"].items():
            regulated = source["allocations"][group]["regulated_units"]
            require(isinstance(limit, dict) and synthetic_id(limit.get("source_ref")),
                    "regulated_rent_limit_source_missing:" + group)
            if regulated == 0:
                require(set(limit) == {"applicability", "source_ref"} and limit["applicability"] == "not_applicable",
                        "regulated_rent_zero_regulated_population_requires_explicit_NA:" + group)
            else:
                require(set(limit) == {"applicability", "source_ref", "imputed_household_size", "household_basis_ref", *NUMBERS}
                        and limit["applicability"] == "applicable"
                        and type(limit["imputed_household_size"]) is int and limit["imputed_household_size"] > 0
                        and synthetic_id(limit["household_basis_ref"]), "regulated_rent_AMI_or_household_basis_invalid_or_unconfirmed:" + group)
                amounts = {key: quantity(limit, key) for key in NUMBERS}
                require(amounts["rent_income_share"] <= 1, "regulated_rent_income_share_exceeds_full_income")
                gross = amounts["annual_AMI_income"] * amounts["income_limit_fraction"] * amounts["rent_income_share"] / 12
                require(gross >= amounts["utility_allowance_monthly"],
                        "regulated_rent_negative_net_cap_not_replaced_by_zero:" + group)
    return source


def project_window(raw, name, groups, calendar, values, growth, *, rent_basis):
    source = configuration(raw, name, groups, calendar, rent_basis=rent_basis)
    start = growth["window_start"]
    require(start in source["windows"] and growth["window_end_exclusive"] == str(offset(date.fromisoformat(start), 12)),
            "regulated_rent_window_does_not_match_NOI_period")
    factor = _fraction(growth["rent_factor"])
    require(factor is not None and factor >= 0, "regulated_rent_market_growth_factor_missing")
    window = source["windows"][start]
    result = {}
    for cell, group in GROUPS.items():
        allocation = source["allocations"][group]
        count = groups[group]["units"]
        market = _fraction(values[cell])
        require(market is not None and market >= 0, "regulated_rent_market_value_missing:" + cell)
        projected_market = market * factor
        limited, gross_cap, net_cap = None, None, None
        if allocation["regulated_units"]:
            limit = window["limits"][group]
            gross_cap = quantity(limit, "annual_AMI_income") * quantity(limit, "income_limit_fraction") * quantity(limit, "rent_income_share") / 12
            net_cap = gross_cap - quantity(limit, "utility_allowance_monthly")
            limited = min(projected_market, net_cap)
            gross = (allocation["market_units"] * projected_market + allocation["regulated_units"] * limited) * 12
        else:
            gross = count * projected_market * 12
        # Zero group population is explicit N/A; its canonical price is the sourced market price.
        effective = projected_market if count == 0 else gross / (12 * count)
        result[group] = dict(units=count, allocation=allocation, market_rent=rational(projected_market),
            gross_regulated_cap=None if gross_cap is None else rational(gross_cap),
            net_regulated_cap=None if net_cap is None else rational(net_cap),
            charged_regulated_rent=None if limited is None else rational(limited),
            effective_per_unit_monthly_rent=rational(effective), annual_gross_potential=rational(gross),
            limit=window["limits"][group])
    proof = dict(state="checked_synthetic", blockers=[], profile=PROFILE, rules=RULES,
        source_ref=raw["source_ref"], scenario_source_ref=source["source_ref"], window=window,
        inputs_sha256=sha(encoded(raw)), window_start=start, window_end_exclusive=growth["window_end_exclusive"],
        groups=result, annual_gross_potential=rational(sum(_fraction(g["annual_gross_potential"]) for g in result.values())),
        owner_utility_expenses_modified=False, real_eligibility_confirmed=False)
    proof["source_sha256"] = sha(encoded(proof))
    return proof


def validate_reference(case, ref):
    inputs = case["rent_inputs"]["regulated_rent"]
    inventory = ref["regulated_rents"]
    require(isinstance(inventory, dict) and set(inventory) == {"Base", "Downside"},
            "regulated_rent_independent_scenario_inventory_missing")
    digest = sha(encoded(inputs))
    for name, record in inventory.items():
        require(isinstance(record, dict) and set(record) == {"inputs_sha256", "windows"}
                and record["inputs_sha256"] == digest
                and isinstance(record["windows"], dict)
                and set(record["windows"]) == set(inputs["scenarios"][name]["windows"]),
                "regulated_rent_independent_window_inventory_missing:" + name)
        for start, proof in record["windows"].items():
            require(isinstance(proof, dict) and proof.get("window_start") == start
                    and proof.get("inputs_sha256") == digest
                    and set(proof.get("groups", {})) == set(GROUPS.values()),
                    "regulated_rent_independent_group_inventory_missing:" + name + ":" + start)


def critical_fields(ref):
    from audit_worksheet_critical_evidence_D219 import Claim, Field
    for name, record in ref["regulated_rents"].items():
        root = ("scenarios", name, "holding_horizon", "regulated_rents")
        source = Claim("M1_AMI", root, {("profile",): PROFILE, ("rules",): RULES,
                                        ("inputs_sha256",): record["inputs_sha256"]})
        yield Field(f"{name}:regulated_rent:source_inventory", (source,),
                    f"case.json / rent_inputs / regulated_rent / scenarios / {name}")
        for start, proof in record["windows"].items():
            claim = Claim("M1_AMI", root + ("windows", start), {(): proof}, (root,))
            yield Field(f"{name}:regulated_rent:{start}", (claim,),
                        f"case.json / rent_inputs / regulated_rent / scenarios / {name} / windows / {start}")
