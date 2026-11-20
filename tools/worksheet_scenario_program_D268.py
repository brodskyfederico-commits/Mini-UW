"""Execute fifteen explicitly sourced sensitivities through complete worksheet intake.

The program consumes immutable source packets, not post-calculation overrides.
All monetary outputs retain their verified initial-equity basis and dated events.
"""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded, read_package, CURRENT_REVISION_FILE, verify_package
from worksheet_intake_D198 import assemble, register, read_source_directory
from worksheet_local_sources_D127 import synthetic_id
from worksheet_variant_evidence_D268 import SCHEMA as CASE_SCHEMA, inputs_digest, stress_terms


SCHEMA = "miniuw.synthetic-explicit-scenario-program.v1"
# Identifiers refer to the reviewed policy matrix, not adopted default values.
DRIVERS = {
    "18": (("C8", "C9", "C10", "C11"), "relative", "fraction"),
    "19": (("C16", "C17", "C18"), "relative", "fraction"),
    "20": (("C14",), "add", "percentage_points"),
    "21": (("C19",), "add", "percentage_points"),
    "22": (("C35", "C37", "C38"), "relative", "fraction"),
    "23": (("C46",), "add", "months"),
    "24": (("C47",), "add", "months"),
    "25": (("C52",), "add", "bps"),
    "26": (("C69",), "add", "bps"),
    "27": (("C66",), "add", "bps"),
    "28": (("C59",), "relative", "fraction"),
    "29": ((), "post_assessment_tax", "fraction"),
    "30": (("C71",), "add", "percentage_points"),
    "31": (("C67",), "add", "bps"),
    "32": (("C75",), "add", "percentage_points"),
}
SCENARIOS = ("Base", "Downside")
UPSIDE_ROLE = "informative_only_never_rescues_base_or_downside"


def literal_cells(raw):
    return inspect_synthetic_input_sheet(raw).cells


def numeric_literal(cells, key):
    row = cells[key]
    require(row.get("formula") is None, "scenario_program_literal_input_required:" + key)
    value = row.get("literal")
    require(value is not None and value != "" and not isinstance(value, bool),
            "scenario_program_missing_input:" + key)
    try:
        return Fraction(value)
    except (ValueError, TypeError, ZeroDivisionError):
        raise ValueError("scenario_program_numeric_input_required:" + key) from None


def driver_terms(record, key):
    require(isinstance(record, dict) and synthetic_id(record.get("source_ref")),
            "scenario_program_driver_source_missing:" + key)
    mode = record.get("applicability")
    if mode == "excluded":
        require(set(record) == {"applicability", "source_ref", "reason"}
                and isinstance(record["reason"], str) and record["reason"].strip(),
                "scenario_program_exception_reason_missing:" + key)
        return None
    require(mode == "included" and set(record) == {"applicability", "source_ref", "unit", "values"}
            and record["unit"] == DRIVERS[key][2]
            and isinstance(record["values"], dict) and set(record["values"]) == set(SCENARIOS),
            "scenario_program_explicit_driver_contract_required:" + key)
    result = {}
    for name in SCENARIOS:
        delta = _fraction(record["values"][name])
        require(delta is not None, "scenario_program_explicit_delta_required:" + key + ":" + name)
        require(record["unit"] != "months" or delta.denominator == 1,
                "scenario_program_whole_month_delta_required")
        result[name] = delta
    return result


def transformed(prior, delta, key):
    _, operation, unit = DRIVERS[key]
    if operation == "relative":
        return prior * (1 + delta)
    require(operation == "add", "scenario_program_non_cell_driver")
    divisor = {"bps": 10_000, "percentage_points": 100, "months": 1}[unit]
    return prior + delta / divisor


def leaf_changes(before, after, path=()):
    """A complete declaration of changed settings, including source metadata."""
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return [row for key in sorted(before) for row in leaf_changes(before[key], after[key], path + (key,))]
    if before == after:
        return []
    return [dict(path=list(path), before=before, after=after)]


def unchanged_support(inputs):
    """Remove only documented source/date leaves that may accompany these drivers."""
    value = deepcopy(inputs)
    for name in SCENARIOS:
        value["project_calendar"]["scenarios"][name].pop("tco_date")
        value["supplemental_scope"][name]["sale_date"].pop("value")
        value["integrated_screening"][name]["reference_cap"].pop("period_ref")
        for context in value["criterion_noi_contexts"][name].values(): context.pop("period_ref")
        value["bank_debt_yield"][name].pop("quote_source_sha256")
        for row in value["florida_property_tax"]["scenarios"][name]["rolls"]["buyer"].values():
            row.pop("event_date")
        market = value["market_evidence"]["scenarios"][name]
        market["absorption"]["document"]["ranges"].pop("C47")
        market["absorption"].pop("sha256")
        market["insurance"]["document"].pop("premium_per_insured_unit")
        market["insurance"].pop("sha256")
        value["stabilized_tax_stress"]["scenarios"][name] = "explicitly_checked_separately"
    return value


def load_packet(root, label):
    require(isinstance(label, str) and label and Path(label).name == label and label not in (".", ".."),
            "scenario_program_packet_name_invalid")
    directory = root / label
    require(directory.is_dir() and not directory.is_symlink(), "scenario_program_regular_packet_required")
    settings = directory / "settings.json"
    require(settings.is_file() and not settings.is_symlink() and settings.stat().st_size <= 4_000_000,
            "scenario_program_bounded_settings_required")
    spec = json.loads(settings.read_bytes())
    require(spec.get("schema") == CASE_SCHEMA, "scenario_program_explicit_v34_required")
    sources = read_source_directory(directory, include_reference=True)
    return spec, sources


def packet_hash(spec, sources):
    return sha(encoded(dict(settings=sha(encoded(spec)), sources={key: None if raw is None else sha(raw)
                                                               for key, raw in sorted(sources.items())})))


def check_variant(base, parent_sources, spec, sources, declaration, drivers, selected):
    require(declaration["packet_sha256"] == packet_hash(spec, sources), "scenario_program_packet_hash_mismatch")
    require(declaration["settings_changes"] == leaf_changes(base, spec),
            "scenario_program_undeclared_settings_change")
    # No sensitivity is allowed to alter criteria, approval, plan area, or initial basis.
    for key in base.keys() | spec.keys():
        if key not in {"rent_inputs", "local_sources", "rules"}:
            require(base.get(key) == spec.get(key), "scenario_program_unrelated_top_level_change:" + key)
    strip_period = lambda rules: [{k: v for k, v in rule.items() if k != "period_ref"} for rule in rules]
    require(strip_period(base["rules"]) == strip_period(spec["rules"]), "scenario_program_criteria_changed")
    require(parent_sources["criteria_raw"] == sources["criteria_raw"]
            and parent_sources["plan_raw"] == sources["plan_raw"], "scenario_program_criteria_or_plan_changed")
    for key in ("groups", "commercial", "development", "construction_budget", "policy", "irr_policy",
                "requested_principal", "construction_financing", "permanent_loan", "operating_costs",
                "replacement_reserve", "refinance_costs", "as_of_UTC", "deal_id"):
        # Some of these may not be in this explicit profile; never invent them.
        require(base["rent_inputs"].get(key) == spec["rent_inputs"].get(key),
                "scenario_program_unrelated_geometry_or_budget_contract_change:" + key)
    require(base["local_sources"].get("gc_criterion") == spec["local_sources"].get("gc_criterion"),
            "scenario_program_gc_acceptance_changed")
    require({key: value for key, value in base["local_sources"].items() if key != "revision"}
            == {key: value for key, value in spec["local_sources"].items() if key != "revision"},
            "scenario_program_unrelated_local_source_policy_changed")
    changed = {}
    for name, argument in zip(SCENARIOS, ("workbook_raw", "downside_workbook_raw"), strict=True):
        original, current = (literal_cells(packet[argument]) for packet in (parent_sources, sources))
        require(original.keys() == current.keys(), "scenario_program_input_inventory_changed")
        expected = {}
        for key in selected:
            terms = driver_terms(drivers[key], key)
            if terms is None:
                continue
            for cell in DRIVERS[key][0]:
                expected[cell] = transformed(numeric_literal(original, cell), terms[name], key)
        for cell in original:
            if cell in expected:
                require(numeric_literal(current, cell) == expected[cell],
                        "scenario_program_cell_transform_mismatch:" + name + ":" + cell)
            else:
                require(original[cell] == current[cell], "scenario_program_unplanned_cell_change:" + name + ":" + cell)
        cfg = spec["rent_inputs"]["holding_horizon"]["scenarios"][name]
        old_cfg = base["rent_inputs"]["holding_horizon"]["scenarios"][name]
        require(cfg == old_cfg, "scenario_program_initial_basis_or_holding_contract_changed")
        stress, _ = stress_terms(spec["rent_inputs"].get("stabilized_tax_stress"), name)
        old_stress, _ = stress_terms(base["rent_inputs"].get("stabilized_tax_stress"), name)
        terms = driver_terms(drivers["29"], "29") if "29" in selected else None
        target = old_stress if terms is None else (1 + old_stress) * (1 + terms[name]) - 1
        require(stress == target, "scenario_program_post_assessment_tax_transform_mismatch")
        changed[name] = {cell: dict(before=rational(numeric_literal(original, cell)), after=rational(value))
                         for cell, value in expected.items()}
    require(unchanged_support(base["rent_inputs"]) == unchanged_support(spec["rent_inputs"]),
            "scenario_program_unrelated_support_or_policy_change")
    return changed


def cash_summary(result):
    summary = {}
    for name in SCENARIOS:
        view = result["scenarios"][name]
        summary[name] = {}
        for route, candidate in (("with_refi", view), ("without_refi", view.get("horizon_without_refinance"))):
            cash = None if candidate is None else candidate.get("cash_per_usd_10")
            summary[name][route] = dict(state="PENDING" if cash is None else "computed_synthetic",
                                       cash_per_usd_10=cash, blockers=view["blockers"] if cash is None else [])
    return summary


def cash_deltas(records):
    """Compare gross cash on the same initial basis; no implicit time-value ranking."""
    result = {}
    base = records.get("baseline", {}).get("cash")
    for key, record in records.items():
        if key == "baseline": continue
        result[key] = {}
        for name in SCENARIOS:
            result[key][name] = {}
            for route in ("with_refi", "without_refi"):
                before = None if base is None else base[name][route]["cash_per_usd_10"]
                current = record.get("cash")
                after = None if current is None else current[name][route]["cash_per_usd_10"]
                if before is None or after is None:
                    comparison = dict(state="PENDING", blockers=["both_verified_route_cash_stories_required"], deltas=None)
                elif (before["basis_amount"] != after["basis_amount"] or
                      _fraction(before["reference_amount"]) != 10 or _fraction(after["reference_amount"]) != 10):
                    comparison = dict(state="PENDING", blockers=["same_verified_initial_equity_basis_required"], deltas=None)
                else:
                    fields = ("total_contributions", "total_distributions", "unrecovered_after_sale")
                    values = {field: (_fraction(before[field], 4096), _fraction(after[field], 4096)) for field in fields}
                    require(all(x is not None and y is not None for x, y in values.values()),
                            "scenario_program_comparison_missing_numeric_cash")
                    comparison = dict(state="computed_synthetic", blockers=[],
                        deltas={field: rational(y-x) for field, (x,y) in values.items()},
                        timing="retain_each_route_dated_events_no_discount_rate_or_recommendation_inferred")
                result[key][name][route] = comparison
    return result


def run_program(program, source_root, output, *, cases_to_run=None):
    require(isinstance(program, dict) and set(program) == {
        "schema", "id", "source_ref", "baseline", "drivers", "variants", "upside"}
        and program["schema"] == SCHEMA and synthetic_id(program["id"])
        and synthetic_id(program["source_ref"]), "scenario_program_contract_missing")
    require(isinstance(program["drivers"], dict) and set(program["drivers"]) == set(DRIVERS),
            "scenario_program_fifteen_driver_inventory_required")
    for key, record in program["drivers"].items():
        driver_terms(record, key)
    require(set(program["variants"]) == {*DRIVERS, "combined"},
            "scenario_program_isolated_and_combined_inventory_required")
    require(set(program["upside"]) == {"role", "drivers", "packet"}
            and program["upside"]["role"] == UPSIDE_ROLE
            and set(program["upside"]["drivers"]) == set(DRIVERS), "scenario_program_upside_role_unconfirmed")
    base, base_sources = load_packet(source_root, program["baseline"]["name"])
    require(packet_hash(base, base_sources) == program["baseline"]["packet_sha256"],
            "scenario_program_baseline_hash_mismatch")
    output.mkdir(parents=True, exist_ok=False)
    records = {}
    cases = [("baseline", program["baseline"], None, [])]
    cases += [(key, declaration, program["drivers"], list(DRIVERS) if key == "combined" else [key])
              for key, declaration in program["variants"].items()]
    cases += [("upside", program["upside"]["packet"], program["upside"]["drivers"], list(DRIVERS))]
    if cases_to_run is not None:
        require(isinstance(cases_to_run, set) and cases_to_run and cases_to_run <= {row[0] for row in cases},
                "scenario_program_explicit_execution_selection_required")
        cases = [row for row in cases if row[0] in cases_to_run]
    for key, declaration, drivers, selected in cases:
        changed = {}
        try:
            spec, sources = load_packet(source_root, declaration["name"])
            if drivers is not None:
                changed = check_variant(base, base_sources, spec, sources, declaration, drivers, selected)
            registration = register(sources, program["id"] + "-" + key)
            package = output / ("case-" + key)
            receipt = assemble(spec, registration, sources, package)
            saved = read_package(package)
            result = json.loads(saved["results.json"])
            audit = verify_package(package, current_revision_raw=saved[CURRENT_REVISION_FILE])
            records[key] = dict(state=result["state"], simulation_result=result["simulation_result"],
                real_decision="PENDING", source_packet_sha256=packet_hash(spec, sources),
                changes=changed, cash=cash_summary(result), receipt=receipt,
                critical_evidence=result["critical_evidence_review"], replay=audit,
                case_sha256=sha(saved["case.json"]), results_sha256=sha(saved["results.json"]),
                pdf_sha256=sha(saved["MiniUW_Resumen.pdf"]))
        except (ValueError, TypeError, KeyError, OSError) as error:
            records[key] = dict(state="PENDING", real_decision="PENDING", changes=changed,
                                cash=None, blockers=[str(error)])
    report = dict(schema=SCHEMA, program_sha256=sha(encoded(program)), records=records,
        baseline_simulation=records.get("baseline", {}).get("simulation_result", "NOT_EXECUTED"),
        execution_scope="all" if cases_to_run is None else sorted(cases_to_run),
        upside_role=UPSIDE_ROLE, real_decision="PENDING", historical_return="PENDING",
        deployment_enabled=False, real_decisions_enabled=False,
        defaults_loaded=False, external_assumptions_authenticated=False)
    report["cash_deltas_from_baseline"] = cash_deltas(records)
    (output / "program.json").write_bytes(encoded(program))
    (output / "report.json").write_bytes(encoded(report))
    return report


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", action="append", dest="cases")
    args = parser.parse_args()
    print(json.dumps(run_program(json.loads(args.program.read_bytes()), args.sources, args.output,
                                cases_to_run=None if args.cases is None else set(args.cases)),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
