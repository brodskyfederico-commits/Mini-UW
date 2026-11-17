"""Replay isolated and combined worksheet shocks against verified synthetic cash."""
from fractions import Fraction

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from plan_return_D107 import FORWARD_PERIOD
from worksheet_alternatives_D155 import CASH_TOTALS, DRIVERS
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_native_mapping_D139 import SCENARIOS


SCHEMA = "miniuw.synthetic-worksheet-sensitivities.v1"
CHANGE_FIELDS = {"target_cell", "operation", "unit", "value", "source_ref"}
ADDITIVE_SCALES = {"basis_point_change": ("bps", 10_000), "percentage_point_change": ("percentage_points", 100)}


def pending(*blockers):
    return dict(state="PENDING", cash_per_usd_10=None, blockers=list(blockers))


def bind_change(change, rows, workbook_sha256, case_sha256):
    cell = change["target_cell"]
    record = rows[f"INPUT_{cell}"]
    require(change.keys() == CHANGE_FIELDS and synthetic_id(change.get("source_ref")),
            "sensitivity_change_or_source_unconfirmed")
    require(record["state"] == "CONFIRMED_SYNTHETIC", "sensitivity_baseline_cell_unconfirmed")
    prior, delta = _fraction(record["value"]), _fraction(change["value"], 24)
    require(prior is not None and delta is not None, "sensitivity_explicit_numeric_value_required")
    operation = change["operation"]
    unit = DRIVERS[cell][1]
    if operation == "replace_absolute":
        expected_unit, candidate = unit, delta
    elif operation == "relative_change":
        expected_unit, candidate = "fraction_of_baseline", prior * (1 + delta)
    else:
        require(isinstance(operation, str) and operation in ADDITIVE_SCALES, "sensitivity_operation_unsupported")
        expected_unit, divisor = ADDITIVE_SCALES[operation]
        candidate = prior + delta / divisor
    require(change["unit"] == expected_unit, "sensitivity_change_unit_mismatch")
    return dict(change=change, base_value=record["value"], resulting_value=rational(candidate), resulting_unit=unit,
                base_cell_ref=f"sha256:{workbook_sha256}#{record['value_cell']}", origin_case_sha256=case_sha256)


def evaluate_trial(name, review, bindings, origin, run_variant):
    by_cell = {entry["change"]["target_cell"]: entry for entry in bindings}
    rows = []
    for row in review["rows"]:
        entry = by_cell.get(row["field_id"].removeprefix("INPUT_"))
        if entry is not None:
            row = row | dict(value=entry["resulting_value"],
                             alternative_value_source_ref=f"sha256:{sha(encoded(entry))}#/resulting_value")
        rows.append(row)
    candidate = run_variant(name, review | dict(rows=rows))
    comparison = dict(bindings=bindings, capacity=candidate["capacity"],
                      candidate_sha256=sha(encoded(candidate)))
    cash = candidate["cash_per_usd_10"]
    if candidate["blockers"] or cash is None:
        blockers = candidate["blockers"] or ["sensitivity_cash_unavailable"]
        return comparison | pending(*blockers)
    base = origin["cash_per_usd_10"]
    if any(cash[key] != base[key] for key in ("reference_amount", "scale_factor")) or any(
        candidate["project_calendar"][key] != origin["project_calendar"][key] for key in ("purchase_date", "sale_date")
    ):
        return comparison | pending("sensitivity_cash_basis_or_dates_differ")
    deltas = {key: _fraction(cash[key], 1300) - _fraction(base[key], 1300) for key in CASH_TOTALS}
    net = deltas["total_distributions"] - deltas["total_contributions"]
    return comparison | dict(state="computed_synthetic", blockers=[], cash_per_usd_10=cash,
                             delta_per_usd_10={key: rational(value) for key, value in deltas.items()},
                             delta_net_cash_per_usd_10=rational(net),
                             forward_noi=candidate["noi_by_period"][FORWARD_PERIOD]["noi"],
                             valuation_and_sale=candidate["valuation_and_sale"])


def evaluate_scenario(spec, name, review, origin, run_variant, origin_blockers, case_sha256):
    if origin_blockers:
        return pending(*origin_blockers)
    changes = spec.get("changes")
    if (spec.keys() != {"changes"} or not isinstance(changes, list) or not 1 <= len(changes) <= len(DRIVERS)
            or not all(isinstance(change, dict) and isinstance(change.get("target_cell"), str)
                       and change["target_cell"] in DRIVERS for change in changes)):
        return pending("sensitivity_driver_inventory_invalid")
    if len({change["target_cell"] for change in changes}) != len(changes):
        return pending("sensitivity_duplicate_driver")
    rows = {row["field_id"]: row for row in review["rows"]}
    bindings, individual = [], {}
    for change in changes:
        cell = change["target_cell"]
        try:
            binding = bind_change(change, rows, review["workbook_sha256"], case_sha256)
        except (ValueError, TypeError, KeyError) as error:
            individual[cell] = pending(str(error))
            continue
        bindings.append(binding)
        individual[cell] = evaluate_trial(name, review, [binding], origin, run_variant)
    if len(bindings) != len(changes):
        combined = pending("sensitivity_combination_has_unconfirmed_inputs")
    elif len(bindings) == 1:
        combined = next(iter(individual.values()))
    else:
        combined = evaluate_trial(name, review, bindings, origin, run_variant)
    complete = all(row["state"] == "computed_synthetic" for row in individual.values())
    # Equal effects share a group. The combined recalculation is a distinct observation.
    ranking = []
    if complete:
        by_delta = {}
        for cell, row in sorted(individual.items()):
            delta = _fraction(row["delta_net_cash_per_usd_10"], 1300)
            by_delta.setdefault(delta, []).append(cell)
        ranking = [dict(drivers=by_delta[delta], delta_net_cash_per_usd_10=rational(delta)) for delta in sorted(by_delta)]
    return dict(state="computed_synthetic" if complete and combined["state"] == "computed_synthetic" else "PENDING",
                blockers=[], cash_per_usd_10=origin["cash_per_usd_10"],
                baseline_cash_sha256=sha(encoded(origin["cash_per_usd_10"])),
                individual=individual, combined=combined, rank_by_signed_net_cash_delta=ranking)


def evaluate_sensitivities(raw, mapping, views, run_variant, *, revision, documents, evidence_gate, case_sha256):
    heading = dict(schema=SCHEMA, decision="PENDING", origin_case_sha256=case_sha256,
                   revision_sha256=revision["reference_sha256"], request_sha256=sha(encoded(raw)))
    spec = object_or_empty(raw)
    cases = object_or_empty(spec.get("scenarios"))
    if spec.keys() != {"schema", "scenarios"} or spec["schema"] != SCHEMA or cases.keys() != set(SCENARIOS):
        return heading | dict(state="PENDING", blockers=["sensitivity_request_or_scenarios_unconfirmed"], scenarios={})
    common = list(revision["blockers"])
    if documents["blockers"]:
        common.append("sensitivity_origin_documents_pending")
    if evidence_gate is not None and evidence_gate["status"] != "PASSED":
        common.append("sensitivity_critical_evidence_pending")
    scenarios = {}
    for name in SCENARIOS:
        origin = views[name]
        blockers = common + origin["blockers"]
        if origin["cash_per_usd_10"] is None:
            blockers.append("sensitivity_origin_cash_pending")
        scenarios[name] = evaluate_scenario(object_or_empty(cases[name]), name, mapping["scenarios"][name],
                                               origin, run_variant, blockers, case_sha256)
    state = "computed_synthetic" if all(row["state"] == "computed_synthetic" for row in scenarios.values()) else "PENDING"
    return heading | dict(state=state, blockers=[], scenarios=scenarios)
