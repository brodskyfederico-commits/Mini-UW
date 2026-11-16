"""Versioned rehearsal of the documented Lorena screening criteria."""

from hashlib import sha256

from .debt_service import _fraction, rational
from .drafts import ContextSeed, ValidationError, canonical, nonempty
from .expense_cash_detail import _exact, _json
from .irr_interval_output import condition_relation
from .threshold_rehearsal import SOURCE_SHA256, read_documented_thresholds


RECIPE_SCHEMA = "miniuw.lorena-screening-source.v1"
CONFIG_SCHEMA = "miniuw.lorena-screening-configuration.v1"
CASE_SCHEMA = "miniuw.synthetic-lorena-screening-case.v1"
SCENARIOS = ("Base", "Downside")
RLV = "asking_relative_to_supported_price"
REFI_METRICS = ("equity_recovered", "equity_cash_in")
BASES = {
    "YoC": "stabilized_underwriting_noi_over_all_in_tdc",
    "spread": "yoc_less_comparable_cap_same_noi_basis",
    "equity_recovered": "net_refi_cash_out_over_equity_through_stabilization",
    "equity_cash_in": "net_refi_cash_in_over_equity_through_stabilization",
    "breakeven_occupancy": "stabilized_effective_revenue_covers_cost_and_debt_service",
    "post_refi_CoC": "annual_cash_after_debt_service_over_equity_remaining_after_refi",
    RLV: "asking_price_premium_over_positive_base_rlv",
    "equity_TDC": "equity_through_stabilization_over_all_in_tdc",
    "IRR": "annual_levered_project_equity_irr_over_documented_hold",
    "equity_multiple": "gross_project_equity_receipts_over_gross_equity_contributions_over_documented_hold",
}


def encode(value):
    return (canonical(value) + "\n").encode("utf-8")


def prepare_configuration(recipe_raw, source_raw):
    recipe = _json(recipe_raw)
    _exact(recipe, {"schema", "revision", "status", "source"})
    _exact(recipe["source"], {"path", "sha256", "date_literal", "date_locator", "decision_table_locator",
                             "verdict_policy_locator", "scenario_policy_locator"})
    if (recipe["schema"] != RECIPE_SCHEMA or recipe["status"] != "synthetic_rehearsal_only"
            or recipe["source"]["sha256"] != SOURCE_SHA256):
        raise ValidationError("explicit synthetic configuration and pinned standards source required")
    ContextSeed(deal_id=recipe["revision"], scenario_id="configuration", run_id="prepare",
                definition_set_revision=CONFIG_SCHEMA)
    source = read_documented_thresholds(source_raw)
    metrics = []
    for entry in source["metrics"]:
        metric = entry["metric_id"]
        unit = "bps" if metric == "spread" else entry["unit"]
        conditions = {}
        for field in ("pass_base", "pass_downside", "fail_base"):
            threshold = _fraction(entry[field])
            if threshold is None:
                conditions[field] = None
                continue
            operator = entry["fail_operator"] if field == "fail_base" else entry["pass_operator"]
            conditions[field] = {
                "operator": operator,
                "threshold": rational(threshold * 10_000 if unit == "bps" else threshold),
                "source_locator": entry["source_locators"][field],
            }
        metrics.append(dict(metric_id=metric, unit=unit, basis=BASES[metric],
                            source_literals=entry["source_literals"], fail_downside=None, **conditions))
    return dict(schema=CONFIG_SCHEMA, revision=recipe["revision"], status=recipe["status"],
                source=recipe["source"], recipe_sha256=sha256(recipe_raw).hexdigest(),
                comparison_convention_locator=source["comparison_convention_locator"],
                metrics=metrics, criteria_adopted=False, deployment_enabled=False)


def _scope(case, scenario, metric):
    if scenario == "Downside" and metric == RLV:
        return False
    if metric in ("IRR", "equity_multiple"):
        return case["irr_in_scope"]
    flags = case["scope"][scenario]
    refi = flags["refinance_in_scope"]
    if metric in REFI_METRICS:
        return refi
    if metric == "post_refi_CoC":
        return flags["equity_remains_after_refi"] if refi is True else refi
    return True


def _observe(observation, spec):
    if observation is None:
        return None, "metric_value_missing"
    _exact(observation, {"basis", "unit", "value"})
    if observation["basis"] != spec["basis"] or observation["unit"] != spec["unit"]:
        return None, "metric_basis_or_unit_mismatch"
    value = observation["value"]
    if value is None:
        return None, "metric_value_missing"
    if spec["metric_id"] == "IRR" and isinstance(value, dict) and "lower" in value:
        return value, None
    point = rational(_fraction(value))
    return dict(lower=point, upper=point, lower_closed=True, upper_closed=True), None


def _comparison(case, scenario, spec):
    metric = spec["metric_id"]
    passing = spec["pass_base" if scenario == "Base" else "pass_downside"]
    failing = spec["fail_base"] if scenario == "Base" else None
    row = dict(scenario=scenario, metric_id=metric, state="PENDING", reason=None,
               pass_source=passing["source_locator"] if passing else None,
               fail_source=failing["source_locator"] if failing else None)
    scope = _scope(case, scenario, metric)
    if scope is False:
        reason = "base_only_rlv_policy_13" if metric == RLV else "synthetic_strategy_not_applicable"
        return row | dict(state="N/A", reason=reason)
    if scope is None:
        return row | dict(reason="metric_applicability_unresolved")
    if passing is None or (scenario == "Base" and failing is None):
        return row | dict(reason="criterion_missing")
    enclosure, issue = _observe(case["metric_values"][scenario].get(metric), spec)
    if issue:
        return row | dict(reason=issue)
    pass_relation = condition_relation(enclosure, passing["threshold"], passing["operator"])
    fail_relation = condition_relation(enclosure, failing["threshold"], failing["operator"]) if failing else "none"
    if "mixed" in (pass_relation, fail_relation):
        return row | dict(reason="irr_interval_crosses_criterion")
    if fail_relation == "every":
        return row | dict(state="FAIL_CONDITION")
    if pass_relation == "every":
        return row | dict(state="PASS_CONDITION")
    return row | dict(state="PASS_NOT_MET")


def rehearse(recipe_raw, source_raw, configuration_raw, case_raw):
    config = prepare_configuration(recipe_raw, source_raw)
    if configuration_raw != encode(config):
        raise ValidationError("configuration differs from the versioned source")
    configuration_hash = sha256(configuration_raw).hexdigest()
    case = _json(case_raw)
    _exact(case, {"schema", "deal_id", "criteria_revision", "criteria_sha256", "scope", "irr_in_scope",
                  "material_gaps", "metric_values"})
    if (case["schema"] != CASE_SCHEMA or case["criteria_revision"] != config["revision"]
            or case["criteria_sha256"] != configuration_hash):
        raise ValidationError("case must bind the exact synthetic criteria version and hash")
    ContextSeed(deal_id=case["deal_id"], scenario_id="Base-Downside", run_id="rehearsal",
                definition_set_revision=config["revision"])
    if not isinstance(case["material_gaps"], list) or len(case["material_gaps"]) > 32:
        raise ValidationError("explicit bounded material gap list required")
    gaps = list(case["material_gaps"])
    for gap in gaps:
        nonempty(gap, "material_gap")
    _exact(case["scope"], set(SCENARIOS))
    _exact(case["metric_values"], set(SCENARIOS))
    if case["irr_in_scope"] is not None and type(case["irr_in_scope"]) is not bool:
        raise ValidationError("explicit IRR scope required")
    for scenario in SCENARIOS:
        flags = case["scope"][scenario]
        _exact(flags, {"refinance_in_scope", "equity_remains_after_refi"})
        if any(flag is not None and type(flag) is not bool for flag in flags.values()):
            raise ValidationError("explicit scenario applicability flags required")
        if flags["refinance_in_scope"] is False and flags["equity_remains_after_refi"] is True:
            raise ValidationError("equity after refi requires refi in scope")
        values = case["metric_values"][scenario]
        if type(values) is not dict or not set(values) <= set(BASES):
            raise ValidationError("unknown or invalid investment metric inventory")
    comparisons = [_comparison(case, scenario, spec) for scenario in SCENARIOS for spec in config["metrics"]]
    for row in comparisons:
        if row["state"] == "PENDING":
            gaps.append(f"{row['scenario']}:{row['metric_id']}:{row['reason']}")
    states = {row["state"] for row in comparisons}
    if gaps and "FAIL_CONDITION" in states:
        verdict, reason = "PENDING", "material_gaps_with_verified_base_fail_precedence_unconfirmed"
    elif gaps:
        verdict, reason = "HOLD", "MORE_DD_REQUIRED"
    elif "FAIL_CONDITION" in states:
        verdict, reason = "FAIL", "BASE_FAIL_THRESHOLD_BREACHED"
    elif "PASS_NOT_MET" in states:
        verdict, reason = "HOLD", "ECONOMICS_NOT_SUPPORTED"
    else:
        verdict, reason = "PASS", "ALL_APPLICABLE_BASE_AND_DOWNSIDE_PASS"
    return dict(criteria_revision=config["revision"], criteria_sha256=configuration_hash,
                case_sha256=sha256(case_raw).hexdigest(), simulation_result=verdict, reason=reason,
                decision="PENDING", criteria_adopted=False, deployment_enabled=False, production_authorized=False,
                material_gaps=sorted(set(gaps)), comparisons=comparisons)
