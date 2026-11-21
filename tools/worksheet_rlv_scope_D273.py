"""Explicit joint RLV scope; preserve historical single-tag source contracts.

This declares calculation scope, never investment-criterion adoption. A new
source revision is required. All non-RLV Base criteria must remain in scope.
"""
from miniuw_foundation.lorena_screening import BASES, RLV
from worksheet_local_sources_D127 import synthetic_id


PROFILE = "miniuw.synthetic-joint-applicable-rlv-scope.v1"
RULE = "all_applicable_non_RLV_Base_criteria_jointly_including_YoC_and_spread"
FIELD = "applicable_criteria_contract"


def scope_issues(settings, configuration):
    """An incomplete or unknown explicit declaration cannot select a subset."""
    contract = settings.get(FIELD)
    expected = sorted(set(BASES) - {RLV})
    if (not isinstance(contract, dict)
            or set(contract) != {"profile", "rule", "scenario_id", "metric_ids", "source_ref"}
            or contract.get("profile") != PROFILE or contract.get("rule") != RULE
            or contract.get("scenario_id") != "Base"
            or contract.get("metric_ids") != expected
            or not synthetic_id(contract.get("source_ref"))):
        return ["RLV: falta declarar conjuntamente todos los criterios aplicables"]
    if settings.get("binding_yields") != ["YoC", "spread"] or "yield_metric" in settings:
        return ["RLV: YoC y spread aplicables deben permanecer juntos"]
    records = configuration.get("metrics")
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        return ["RLV: falta la configuración completa de criterios"]
    ids = [row.get("metric_id") for row in records]
    if any(not isinstance(value, str) for value in ids) or len(ids) != len(set(ids)) or set(ids) != set(BASES):
        return ["RLV: no se puede omitir ni duplicar un criterio aplicable"]
    for row in records:
        if row["metric_id"] == RLV:
            continue
        for field in ("pass_base", "fail_base"):
            condition = row.get(field)
            if (not isinstance(condition, dict)
                    or condition.get("operator") not in ("<=", ">=", "<", ">")
                    or condition.get("threshold") is None):
                return ["RLV: falta confirmar una condición aplicable"]
    return []
