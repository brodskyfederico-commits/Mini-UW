"""Replay isolated and combined worksheet shocks against verified synthetic cash."""
from fractions import Fraction

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CONSTRUCTION_SENSITIVITY_SCHEMA, encoded
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_alternatives_D155 import CASH_TOTALS, DRIVERS
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_native_mapping_D139 import SCENARIOS
from worksheet_market_evidence_D166 import RENT_UNITS


SCHEMA = "miniuw.synthetic-worksheet-sensitivities.v1"
EXTENDED_SCHEMA = "miniuw.synthetic-worksheet-sensitivities.v2"
BUDGET_SCHEMA = "miniuw.synthetic-worksheet-sensitivities.v3"
CALENDAR_SCHEMA = "miniuw.synthetic-worksheet-sensitivities.v4"
CONSTRUCTION_SCHEMA = CONSTRUCTION_SENSITIVITY_SCHEMA
EXPENSE_SCHEMA = "miniuw.synthetic-worksheet-sensitivities.v6"
RESERVE_SCHEMA = "miniuw.synthetic-worksheet-sensitivities.v7"
EXTENDED_UNITS = {
    "C14": "fraction", "C15": "fraction", "C19": "fraction",
    "C16": "USD_per_rentable_sf_per_year", "C17": "USD_per_rentable_sf_per_year",
    "C18": "USD_per_rentable_sf_per_year", "C76": "annual_effective_growth_fraction",
}
BUDGET_UNITS = {
    "C37": "USD_per_parking_space", "C38": "USD_total",
    "C39": "fraction", "C40": "fraction", "C41": "USD_per_rentable_sf", "C42": "fraction",
}
CHANGE_FIELDS = {"target_cell", "operation", "unit", "value", "source_ref"}
ADDITIVE_SCALES = {"basis_point_change": ("bps", 10_000), "percentage_point_change": ("percentage_points", 100)}


def pending(*blockers):
    return dict(state="PENDING", cash_per_usd_10=None, blockers=list(blockers))


def bind_change(change, rows, workbook_sha256, case_sha256, *, units=None):
    cell = change["target_cell"]
    record = rows[f"INPUT_{cell}"]
    require(change.keys() == CHANGE_FIELDS and synthetic_id(change.get("source_ref")),
            "sensitivity_change_or_source_unconfirmed")
    require(record["state"] == "CONFIRMED_SYNTHETIC", "sensitivity_baseline_cell_unconfirmed")
    prior, delta = _fraction(record["value"]), _fraction(change["value"], 24)
    require(prior is not None and delta is not None, "sensitivity_explicit_numeric_value_required")
    operation = change["operation"]
    unit = DRIVERS[cell][1] if units is None else units[cell]
    if unit == "months":
        require(operation in ("replace_absolute", "month_change") and prior.denominator == delta.denominator == 1,
                "sensitivity_calendar_requires_explicit_whole_months")
    if operation == "replace_absolute":
        expected_unit, candidate = unit, delta
    elif operation == "month_change" and unit == "months":
        expected_unit, candidate = "months", prior + delta
    elif operation == "relative_change":
        expected_unit, candidate = "fraction_of_baseline", prior * (1 + delta)
    else:
        require(isinstance(operation, str) and operation in ADDITIVE_SCALES, "sensitivity_operation_unsupported")
        require(units is None or not unit.startswith("USD_"), "sensitivity_additive_rate_operation_requires_fraction")
        expected_unit, divisor = ADDITIVE_SCALES[operation]
        candidate = prior + delta / divisor
    require(change["unit"] == expected_unit, "sensitivity_change_unit_mismatch")
    return dict(change=change, base_value=record["value"], resulting_value=rational(candidate), resulting_unit=unit,
                base_cell_ref=f"sha256:{workbook_sha256}#{record['value_cell']}", origin_case_sha256=case_sha256)


def evaluate_trial(name, review, bindings, origin, run_variant, *, extended=False, budget=False,
                   calendar=False, support=None, scenario_inputs=None, construction=False, parent_quote=None, expense=False, reserve=False):
    by_cell = {entry["change"]["target_cell"]: entry for entry in bindings}
    rows = []
    for row in review["rows"]:
        entry = by_cell.get(row["field_id"].removeprefix("INPUT_"))
        if entry is not None:
            row = row | dict(value=entry["resulting_value"],
                             alternative_value_source_ref=f"sha256:{sha(encoded(entry))}#/resulting_value")
            if extended:
                row["sensitivity_value_source_ref"] = row["alternative_value_source_ref"]
        rows.append(row)
    support_binding = None
    if expense:
        from worksheet_expense_support_D258 import supported_inputs
        try:
            inputs, support_binding = supported_inputs(scenario_inputs, name, support, bindings)
        except (ValueError, TypeError, KeyError) as error:
            return pending(str(error)) | dict(bindings=bindings, capacity=None)
        candidate = run_variant(name, review | dict(rows=rows), scenario_inputs=inputs)
    elif construction:
        from worksheet_construction_support_D257 import supported_quote
        try:
            quote, support_binding = supported_quote(support, name, object_or_empty(scenario_inputs).get("deal_id"), parent_quote)
        except (ValueError, TypeError, KeyError) as error:
            return pending(str(error)) | dict(bindings=bindings, capacity=None)
        candidate = run_variant(name, review | dict(rows=rows), construction_quote=quote)
    elif calendar:
        from worksheet_calendar_support_D256 import supported_inputs
        try:
            inputs, support_binding = supported_inputs(scenario_inputs, name, support)
        except (ValueError, TypeError, KeyError) as error:
            return pending(str(error)) | dict(bindings=bindings, capacity=None)
        candidate = run_variant(name, review | dict(rows=rows), scenario_inputs=inputs)
    else:
        candidate = run_variant(name, review | dict(rows=rows))
    comparison = dict(bindings=bindings, capacity=candidate["capacity"],
                      candidate_sha256=sha(encoded(candidate)))
    if budget:
        comparison.update({key: candidate[key] for key in (
            "development_costs", "construction_budget", "construction_financing", "construction_refinance", "project_calendar"
        ) if key in candidate})
    if calendar:
        comparison["calendar_support"] = support_binding
        comparison.update({key: candidate[key] for key in (
            "permanent_loan", "market_insurance_review", "bank_document_binding") if key in candidate})
    if construction:
        comparison["construction_support"] = support_binding
    if expense:
        comparison["expense_support"] = support_binding
        comparison.update({key: candidate[key] for key in ("market_insurance_review", "cell_sources") if key in candidate})
    if reserve:
        comparison.update({key: candidate[key] for key in (
            "replacement_reserve", "permanent_reserve", "dated_debt_service", "gross_sale", "debt_principal_paid_at_sale"
        ) if key in candidate})
    cash = candidate["cash_per_usd_10"]
    if candidate["blockers"] or cash is None:
        blockers = candidate["blockers"] or ["sensitivity_cash_unavailable"]
        return comparison | pending(*blockers)
    base = origin["cash_per_usd_10"]
    date_keys = ("purchase_date",) if calendar else ("purchase_date", "sale_date")
    if any(cash[key] != base[key] for key in ("reference_amount", "scale_factor")) or any(
        candidate["project_calendar"][key] != origin["project_calendar"][key] for key in date_keys
    ):
        return comparison | pending("sensitivity_cash_basis_or_dates_differ")
    if calendar:
        comparison["date_comparison"] = {key: dict(original=origin["project_calendar"][key],
                                                    variant=candidate["project_calendar"][key]) for key in (
            "purchase_date", "construction_finish", "tco_date", "stabilization_date", "refinance_date", "sale_date")}
    if reserve:
        operating = candidate["noi_by_period"][OPERATING_PERIOD]
        terms = candidate["replacement_reserve"]
        comparison["operating_noi_after_reserve"] = dict(
            period_ref=OPERATING_PERIOD, currency="USD", noi_assembly_sha256=operating["noi_assembly_sha256"],
            reserve_cell_ref=terms["cell_source"], value=rational(_fraction(operating["noi"]) - _fraction(terms["deposit"])))
    deltas = {key: _fraction(cash[key], 1300) - _fraction(base[key], 1300) for key in CASH_TOTALS}
    net = deltas["total_distributions"] - deltas["total_contributions"]
    if extended:
        comparison.update(noi_by_period=candidate["noi_by_period"], cell_sources=candidate["cell_sources"],
                          growth_terms=candidate["growth_terms"],
                          commercial_terms=candidate["commercial_terms"])
    return comparison | dict(state="computed_synthetic", blockers=[], cash_per_usd_10=cash,
                             delta_per_usd_10={key: rational(value) for key, value in deltas.items()},
                             delta_net_cash_per_usd_10=rational(net),
                             forward_noi=candidate["noi_by_period"][FORWARD_PERIOD]["noi"],
                             valuation_and_sale=candidate["valuation_and_sale"])


def evaluate_scenario(spec, name, review, origin, run_variant, origin_blockers, case_sha256, *, extended=False,
                      budget=False, calendar=False, scenario_inputs=None, construction=False, parent_quote=None, expense=False, reserve=False):
    if origin_blockers:
        return pending(*origin_blockers)
    units = {cell: driver[1] for cell, driver in DRIVERS.items()}
    rows = {row["field_id"]: row for row in review["rows"]}
    if extended:
        rent_basis = object_or_empty(rows.get("INPUT_C7")).get("value")
        rent_unit = RENT_UNITS.get(rent_basis) if isinstance(rent_basis, str) else None
        if rent_unit is None:
            return pending("sensitivity_rent_basis_unconfirmed:C7")
        units.update(EXTENDED_UNITS)
        units.update({cell: rent_unit for cell in ("C8", "C9", "C10", "C11")})
    if budget:
        units.update(BUDGET_UNITS)
    if calendar:
        units = {"C46": "months", "C47": "months"}
    if construction:
        units = {"C51": "fraction", "C52": "annual_nominal_fraction", "C53": "fraction_of_commitment"}
    if expense:
        units = {"C57": "USD_per_residential_unit_per_year", "C58": "fraction_of_effective_residential_income_plus_c13",
                 "C59": "USD_per_insured_unit_per_year"}
    if reserve:
        units["C60"] = "USD_per_eligible_unit_per_year"
    changes = spec.get("changes")
    support_key = "expense_support" if expense else "calendar_support" if calendar else "construction_support"
    fields = {"changes", support_key} if calendar or construction or expense else {"changes"}
    if (spec.keys() != fields or not isinstance(changes, list) or not 1 <= len(changes) <= len(units)
            or not all(isinstance(change, dict) and isinstance(change.get("target_cell"), str)
                       and change["target_cell"] in units for change in changes)):
        return pending("sensitivity_driver_inventory_invalid")
    if len({change["target_cell"] for change in changes}) != len(changes):
        return pending("sensitivity_duplicate_driver")
    support = None
    if calendar or construction or expense:
        if expense:
            from worksheet_expense_support_D258 import support_inventory
        elif calendar:
            from worksheet_calendar_support_D256 import support_inventory
        else:
            from worksheet_construction_support_D257 import support_inventory
        try:
            support = support_inventory(spec[support_key], [change["target_cell"] for change in changes])
        except (ValueError, TypeError, KeyError) as error:
            return pending(str(error))
    bindings, individual = [], {}
    for change in changes:
        cell = change["target_cell"]
        try:
            binding = bind_change(change, rows, review["workbook_sha256"], case_sha256, units=units if extended else None)
        except (ValueError, TypeError, KeyError) as error:
            individual[cell] = pending(str(error))
            continue
        bindings.append(binding)
        individual[cell] = evaluate_trial(name, review, [binding], origin, run_variant, extended=extended, budget=budget,
                                          calendar=calendar, support=None if support is None else support["individual"][cell],
                                          scenario_inputs=scenario_inputs, construction=construction, parent_quote=parent_quote, expense=expense, reserve=reserve)
    if len(bindings) != len(changes):
        combined = pending("sensitivity_combination_has_unconfirmed_inputs")
    elif len(bindings) == 1 and not calendar and not construction and not expense:
        combined = next(iter(individual.values()))
    else:
        combined = evaluate_trial(name, review, bindings, origin, run_variant, extended=extended, budget=budget,
                                   calendar=calendar, support=None if support is None else support["combined"],
                                   scenario_inputs=scenario_inputs, construction=construction, parent_quote=parent_quote, expense=expense, reserve=reserve)
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


def evaluate_sensitivities(raw, mapping, views, run_variant, *, revision, documents, evidence_gate, case_sha256, scenario_inputs=None):
    spec = object_or_empty(raw)
    schema = spec.get("schema")
    supported = (SCHEMA, EXTENDED_SCHEMA, BUDGET_SCHEMA, CALENDAR_SCHEMA, CONSTRUCTION_SCHEMA, EXPENSE_SCHEMA, RESERVE_SCHEMA)
    heading = dict(schema=schema if schema in supported else SCHEMA, decision="PENDING", origin_case_sha256=case_sha256,
                   revision_sha256=revision["reference_sha256"], request_sha256=sha(encoded(raw)))
    cases = object_or_empty(spec.get("scenarios"))
    if spec.keys() != {"schema", "scenarios"} or schema not in supported or cases.keys() != set(SCENARIOS):
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
                                               origin, run_variant, blockers, case_sha256,
                                               extended=schema in (EXTENDED_SCHEMA, BUDGET_SCHEMA, CALENDAR_SCHEMA, CONSTRUCTION_SCHEMA, EXPENSE_SCHEMA, RESERVE_SCHEMA),
                                               budget=schema in (BUDGET_SCHEMA, CALENDAR_SCHEMA, CONSTRUCTION_SCHEMA, EXPENSE_SCHEMA, RESERVE_SCHEMA), calendar=schema == CALENDAR_SCHEMA,
                                               scenario_inputs=scenario_inputs, construction=schema == CONSTRUCTION_SCHEMA,
                                               parent_quote=object_or_empty(object_or_empty(object_or_empty(documents.get("bots")).get("B08"))
                                                                           .get("construction_pdf_by_scenario")).get(name), expense=schema in (EXPENSE_SCHEMA, RESERVE_SCHEMA),
                                               reserve=schema == RESERVE_SCHEMA)
    state = "computed_synthetic" if all(row["state"] == "computed_synthetic" for row in scenarios.values()) else "PENDING"
    return heading | dict(state=state, blockers=[], scenarios=scenarios)
