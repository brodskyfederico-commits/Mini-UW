"""Validate supplemental scenario inputs against the scope of the quarterly pilot."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import rational
from worksheet_local_sources_D127 import day, number, object_or_empty, synthetic_id


PROFILE = "synthetic_documented_supplemental_scope"


def scenario_scope(raw, name):
    record = object_or_empty(object_or_empty(raw).get(name))
    required = {"sale_date", "maturity_payments", "fixed_sale_cost", "bank_vacancy_addition"}
    require(required <= record.keys(), "supplemental_scenario_scope_incomplete")
    for key in sorted(required):
        entry = object_or_empty(record[key])
        require(entry.keys() == {"value", "source_ref"} and synthetic_id(entry["source_ref"]),
                f"supplemental_source_unconfirmed:{key}")
    require(day(record["sale_date"]["value"]) is not None, "explicit_sale_date_required")
    maturity = record["maturity_payments"]["value"]
    require(type(maturity) is int and maturity > 0, "explicit_permanent_maturity_payments_required")
    costs = number(record["fixed_sale_cost"]["value"])
    stress = number(record["bank_vacancy_addition"]["value"])
    require(costs is not None and costs >= 0, "explicit_fixed_sale_cost_required")
    require(stress is not None and 0 <= stress <= 1, "explicit_bank_vacancy_stress_required")
    downside = object_or_empty(record.get("downside_scope"))
    if name == "Downside":
        require(downside.keys() == {"basis", "source_ref", "base_workbook_sha256", "downside_workbook_sha256"}
                and downside["basis"] == "explicit_combined_scenario_workbook"
                and synthetic_id(downside["source_ref"]), "integrated_downside_scope_unconfirmed")
    else:
        require("downside_scope" not in record, "integrated_downside_scope_must_bind_downside")
    live_local = object_or_empty(record.get("live_local"))
    require(live_local.keys() == {"applicability", "source_ref"} and synthetic_id(live_local["source_ref"])
            and live_local["applicability"] == "not_applicable", "live_local_program_and_eligibility_pending")
    return record | dict(fixed_sale_cost=record["fixed_sale_cost"] | {"value": rational(costs)},
                         bank_vacancy_addition=record["bank_vacancy_addition"] | {"value": rational(stress)})
