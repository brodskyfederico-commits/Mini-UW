"""Bind confirmed C80–C82 literals to isolated, typed worksheet alternatives."""
from fractions import Fraction
import re

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from plan_return_D107 import FORWARD_PERIOD
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_native_mapping_D139 import SCENARIOS


POLICY = "SYNTHETIC-D155-confirmed-single-driver-replacement"
SLOTS = ("C80", "C81", "C82")
SLOT_FIELDS = tuple(f"INPUT_{cell}:" for cell in SLOTS)
DRIVERS = {"C67": ("Exit cap rate", "annual_cap_fraction"),
           "C68": ("Sale costs", "fraction_of_gross_sale_price"),
           "C75": ("Rent growth", "annual_effective_growth_fraction")}
LITERAL = re.compile(r"([A-Za-z ]+) = (-?[0-9]{1,12}(?:\.[0-9]{1,12})?)")
CASH_TOTALS = ("total_contributions", "total_distributions", "unrecovered_after_sale")


def confirmed_replacement(cell, request, record, rows, workbook_sha, scope_ref):
    require(record.keys() == {"target_cell", "operation", "unit", "value", "source_ref"}
            and record["operation"] == "replace_absolute"
            and isinstance(record["target_cell"], str) and record["target_cell"] in DRIVERS
            and synthetic_id(record["source_ref"]), "alternative_driver_or_confirmation_unbound")
    target = record["target_cell"]
    label, unit = DRIVERS[target]
    match = LITERAL.fullmatch(request["value"])
    value = _fraction(record["value"])
    require(match is not None and match[1] == label and Fraction(match[2]) == value and record["unit"] == unit,
            "alternative_literal_or_unit_mismatch")
    prior = rows[f"INPUT_{target}"]
    require(prior["state"] == "CONFIRMED_SYNTHETIC", "alternative_baseline_driver_unconfirmed")
    binding = dict(request_cell=cell, request_literal=request["value"],
                   request_ref=f"sha256:{workbook_sha}#{request['value_cell']}",
                   baseline_driver_ref=f"sha256:{workbook_sha}#{prior['value_cell']}",
                   prior_value=prior["value"], scenario_scope_ref=scope_ref, **record)
    source_ref = f"sha256:{sha(encoded(binding))}#/value"
    return binding, [row | dict(value=rational(value), alternative_value_source_ref=source_ref)
                     if row["field_id"] == prior["field_id"] else row for row in rows.values()]


def evaluate_alternatives(raw, mapping, views, run_variant, *, revision, documents, case_sha256):
    spec = object_or_empty(raw)
    scenario_records = object_or_empty(spec.get("scenarios"))
    profile_ready = (spec.keys() == {"policy", "source_ref", "scenarios"} and spec["policy"] == POLICY
                     and synthetic_id(spec["source_ref"]) and scenario_records.keys() == set(SCENARIOS))
    slots = {cell: {} for cell in SLOTS}
    for name in SCENARIOS:
        review = mapping["scenarios"][name]
        rows = {row["field_id"]: row for row in review["rows"]}
        origin = views[name]
        baseline = origin["cash_per_usd_10"]
        scenario = object_or_empty(scenario_records.get(name))
        records = object_or_empty(scenario.get("slots"))
        scope_ref = scenario.get("scope_ref")
        inventory_ready = (profile_ready and scenario.keys() == {"scope_ref", "slots"} and synthetic_id(scope_ref)
                           and isinstance(scenario["slots"], dict) and records.keys() <= set(SLOTS))
        for cell in SLOTS:
            request = rows.get(f"INPUT_{cell}", {})
            entry = dict(state="PENDING", request_literal=request.get("source_literal"),
                         cash_per_usd_10=None, blockers=[])
            slots[cell][name] = entry
            try:
                require(inventory_ready, "alternative_inventory_unconfirmed")
                if request.get("state") == "NOT_APPLICABLE":
                    require(cell not in records, "alternative_record_for_inapplicable_slot")
                    entry["state"] = "NOT_APPLICABLE"
                    continue
                require(request.get("state") == "CONFIRMED_SYNTHETIC", "alternative_request_unconfirmed")
                require(cell in records, "alternative_confirmation_missing")
                require(not revision["blockers"] and not documents["blockers"], "alternative_origin_revision_or_documents_pending")
                require(baseline is not None and all(reason.startswith(SLOT_FIELDS) for reason in review["blockers"]),
                        "alternative_origin_scenario_pending")
                binding, candidate_rows = confirmed_replacement(
                    cell, request, object_or_empty(records[cell]), rows, review["workbook_sha256"], scope_ref)
                entry["binding"] = binding
                candidate = run_variant(name, review | dict(rows=candidate_rows))
                entry["candidate_sha256"] = sha(encoded(candidate))
                entry["capacity"] = candidate["capacity"]
                entry["blockers"] = candidate["blockers"]
                cash = candidate["cash_per_usd_10"]
                if cash is not None:
                    entry.update(state="computed_synthetic", cash_per_usd_10=cash, baseline_cash_sha256=sha(encoded(baseline)),
                                 delta_per_usd_10={key: rational(_fraction(cash[key]) - _fraction(baseline[key])) for key in CASH_TOTALS},
                                 growth_terms=candidate["growth_terms"],
                                 forward_noi=candidate["noi_by_period"][FORWARD_PERIOD]["noi"],
                                 net_refinance=candidate["construction_refinance"]["net_equity_distribution"],
                                 valuation_and_sale=candidate["valuation_and_sale"])
            except (ValueError, TypeError, KeyError) as error:
                entry["blockers"] = [str(error)]
    return dict(state="PENDING" if any(entry["state"] == "PENDING" for pair in slots.values() for entry in pair.values())
                else "checked_synthetic", origin_case_sha256=case_sha256, revision_sha256=revision["reference_sha256"],
                source_ref=spec.get("source_ref"), slots=slots, decision="PENDING")
