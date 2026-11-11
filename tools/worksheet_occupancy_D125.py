"""Join the synthetic rent realization profile to the pilot's refinance service."""
from check_breakeven_occupancy_D72 import FIELDS, solve
from check_operating_replay_D20 import require
from check_reference_package import PackageError
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.drafts import ValidationError
from worksheet_yoc_spread_D123 import annual_period


METRIC_ID = "breakeven_occupancy"
DEFINITION = "SYNTHETIC-D125-economic-occupancy-for-regular-annual-service"
METRIC = ("fraction", "scalar", None, DEFINITION)
DEBT_BASIS = "SYNTHETIC-D125-post-refinance-regular-annual-equivalent"
PROFILE_FIELDS = set(FIELDS) - {"debt_service"} | {"source_ref"}


def occupancy_evidence(group, operating, name, scenario):
    service = scenario.get("annual_sizing_service")
    result = dict(state="PENDING", decision="PENDING", period=None, minimum_occupancy=None,
                  algebraic_crossing=None, annual_sizing_service=service, evaluated_points=[], inputs=None)
    if not isinstance(group, dict) or not group.keys() <= {"workbook_sha256", "period", "debt_basis", "profile"}:
        blocker = "occupancy_inputs_missing_or_invalid"
    elif scenario["cash_per_usd_10"] is None:
        blocker = "current_scenario_cash_unavailable"
    elif group.get("workbook_sha256") != scenario["preflight"]["workbook_sha256"]:
        blocker = "occupancy_workbook_revision_mismatch_or_missing"
    elif group.get("debt_basis") != DEBT_BASIS or service is None or service["amount"] is None:
        blocker = "compatible_annual_debt_service_unavailable"
    else:
        period = group.get("period")
        profile = group.get("profile")
        context = scenario["context"] | {"scenario_id": f"SYNTHETIC-{name}"}
        if (not annual_period(period) or not isinstance(operating, dict)
                or operating.get("context") != context or operating.get("period_ref") != period
                or operating.get("currency") != service["currency"]):
            blocker = "compatible_annual_operating_period_unavailable"
        elif not isinstance(profile, dict) or not profile.keys() <= PROFILE_FIELDS:
            blocker = "rent_cost_and_tax_profile_missing_or_invalid"
        else:
            inputs = dict.fromkeys(PROFILE_FIELDS) | profile | dict(operating_inventory=name,
                     debt_service=service["amount"], debt_service_period=period)
            try:
                return result | solve(inputs, operating) | {"inputs": inputs}
            except (ValidationError, PackageError, KeyError, IndexError, TypeError):
                blocker = "rent_cost_and_tax_profile_missing_or_invalid"
    return result | {"blockers": [blocker]}


def occupancy_records(inventory, yield_inputs, scenarios, case_sha256):
    inventory = {} if inventory is None else inventory
    require(isinstance(inventory, dict) and inventory.keys() <= scenarios.keys(),
            "Occupancy inputs must identify a pilot scenario")
    values, evidence = [], {}
    for name, scenario in scenarios.items():
        operating = (yield_inputs.get(name) or {}).get("stabilized_noi") if isinstance(yield_inputs.get(name), dict) else None
        row = occupancy_evidence(inventory.get(name), operating, name, scenario)
        evidence[name] = row | dict(case_sha256=case_sha256, source_pointer=f"/occupancy_inputs/{name}",
                                    debt_pointer=f"/scenarios/{name}/annual_sizing_service")
        values.append(dict(metric_id=METRIC_ID, scenario_id=name, definition_ref=DEFINITION, unit="fraction",
                           quantity_kind="scalar", currency=None, period_ref=row["period"],
                           applicability="applicable", applicability_evidence_ref=None, value=row["algebraic_crossing"]))
    return values, evidence


def validate_occupancy_conditions(record):
    for name, operators in (("pass_condition", ("<", "<=")), ("fail_condition", (">", ">="))):
        condition = record[name]
        threshold = _fraction(condition["threshold"])
        if condition["operator"] not in operators or threshold is None or not 0 <= threshold <= 1:
            condition["operator"] = None
