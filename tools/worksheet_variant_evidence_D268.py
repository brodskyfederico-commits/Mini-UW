"""Independent source inventory and explicit post-assessment tax stresses.

This opt-in synthetic contract does not authenticate an approval or a legal rule.
Every variant supplies its own reference; baseline references are never rewritten.
"""
from copy import deepcopy
from fractions import Fraction
import json

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.expense_cash_detail import _json
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


SCHEMA = "miniuw.synthetic-native-rental-inputs.v34"
SUPPORTED_SCHEMAS = (SCHEMA, "miniuw.synthetic-native-rental-inputs.v35")
REFERENCE_FILE = "Independent_Reference.json"
STRESS_PROFILE = "miniuw.synthetic-post-assessment-operating-tax-stress.v1"
STRESS_RULE = "multiply_operating_and_forward_tax_once_after_M2_no_benefits_preopening_unchanged"


def inputs_digest(inputs):
    value = deepcopy(inputs)
    scope = object_or_empty(object_or_empty(value.get("supplemental_scope")).get("Downside"))
    link = object_or_empty(scope.get("downside_scope"))
    # These two transport hashes are inserted by intake after source registration.
    for key in ("base_workbook_sha256", "downside_workbook_sha256"):
        link.pop(key, None)
    return sha(encoded(value))


def reference_issues(raw, case):
    """Reject truncated inventories before their claimed greens can authorize cash."""
    issues = []
    try:
        require(isinstance(raw, bytes) and 0 < len(raw) <= 4_000_000,
                "independent_reference_missing_or_oversize")
        ref = _json(raw, 4_000_000)
        from audit_worksheet_critical_evidence_D219 import REFERENCE
        required = json.loads(REFERENCE.read_bytes())
        regulated = case.get("schema") == "miniuw.synthetic-native-rental-inputs.v35"
        extra = {"regulated_rents"} if regulated else set()
        require(set(ref) == set(required) | {"holding_fiscal", "inputs_sha256"} | extra,
                "independent_reference_top_level_inventory_incomplete")
        require(ref["schema"] == required["schema"] and synthetic_id(ref["deal_id"])
                and ref["deal_id"] == case["rent_inputs"]["deal_id"]
                and ref["local_revision"] == case["local_sources"]["revision"],
                "independent_reference_deal_or_revision_mismatch")
        require(ref["inputs_sha256"] == inputs_digest(case["rent_inputs"]),
                "independent_reference_input_contract_mismatch")
        require(set(ref["sources"]) == set(required["sources"])
                and set(ref["plan"]) == {"B05", "B06"}
                and set(ref["page_documents"]) == set(required["page_documents"]),
                "independent_reference_source_or_page_inventory_incomplete")
        for section in ("bank", "market", "gc_cost", "holding_fiscal"):
            require(set(ref[section]) == {"Base", "Downside"},
                    "independent_reference_scenario_inventory_incomplete:" + section)
        for name in ("Base", "Downside"):
            require(set(ref["bank"][name]) == set(required["bank"][name])
                    and set(ref["market"][name]) == set(required["market"][name]),
                    "independent_reference_role_inventory_incomplete:" + name)
            for kind, bank in required["bank"][name].items():
                observed = ref["bank"][name][kind]
                require(set(observed) == {"page", "terms"}
                        and observed["page"] == bank["page"]
                        and set(observed["terms"]) == set(bank["terms"]),
                        "independent_reference_bank_inventory_incomplete:" + name + ":" + kind)
                for key, label in bank["terms"].items():
                    row = observed["terms"][key]
                    require(isinstance(row, list) and len(row) == len(label)
                            and row[:-1] == label[:-1], "independent_reference_bank_label_mismatch")
            for kind, reading in required["market"][name].items():
                observed = ref["market"][name][kind]
                require(set(observed) == set(reading)
                        and set(observed["cells"]) == set(reading["cells"]),
                        "independent_reference_market_inventory_incomplete:" + name + ":" + kind)
        # Window completeness and binding to the actual workbook are checked by D267.
        from worksheet_horizon_fiscal_D267 import critical_fiscal_fields
        list(critical_fiscal_fields(ref))
        if regulated:
            from worksheet_regulated_rent_D269 import validate_reference
            validate_reference(case, ref)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        issues.append(str(error))
    return issues


def inventory_pending(issues):
    row = dict(status="PENDING", locator=REFERENCE_FILE,
               bots=["B12"], green_bots=[], issues=[dict(reason=value) for value in issues])
    return dict(status="PENDING", decision="PENDING", critical_fields=1,
                counts=dict(VERIFIED_GREEN=0, FALSE_GREEN=0, PENDING=1), green_claims=0,
                current_revision_verified=False, fields={"Compartido:inventario_independiente": row})


def stress_terms(raw, name):
    require(isinstance(raw, dict) and set(raw) == {"profile", "rule", "scenarios"}
            and raw["profile"] == STRESS_PROFILE and raw["rule"] == STRESS_RULE
            and set(raw["scenarios"]) == {"Base", "Downside"}, "tax_stress_contract_missing")
    record = raw["scenarios"][name]
    require(isinstance(record, dict) and set(record) == {"relative_change", "source_ref"}
            and synthetic_id(record["source_ref"]), "tax_stress_source_missing")
    change = _fraction(record["relative_change"])
    require(change is not None and change >= -1, "tax_stress_explicit_fraction_required")
    return change, record


def stress_trace(trace, change, record):
    value = deepcopy(trace)
    value.pop("source_sha256")
    value["unstressed_source_sha256"] = trace["source_sha256"]
    value["stress_contract"] = record | dict(profile=STRESS_PROFILE, rule=STRESS_RULE)
    factor = 1 + change
    for key in ("school_tax", "non_school_tax", "total"):
        value[key] = rational(_fraction(trace[key]) * factor)
    for row in value["rolls"]:
        for key in ("school_tax", "non_school_tax"):
            row[key] = rational(_fraction(row[key]) * factor)
    value["source_sha256"] = sha(encoded(value))
    return value


def fiscal_cash(taxes_raw, cash_raw, stress_raw, name, calendar):
    from worksheet_horizon_fiscal_D267 import fiscal_cash as base_cash
    from plan_return_D107 import OPERATING_PERIOD, FORWARD_PERIOD
    # M2's existing scope explicitly excludes conditional tax benefits.
    change, record = stress_terms(stress_raw, name)
    taxes, _, proof = base_cash(taxes_raw, cash_raw, name, calendar)
    taxes = {key: trace if key.startswith("preopening-") else stress_trace(trace, change, record)
             for key, trace in taxes.items()}
    proof["audit_windows"] = {
        key: row | dict(payload=taxes[key]) for key, row in proof["audit_windows"].items()}
    proof["quarterly_taxes"] = [taxes[f"operation-quarter-{i+1}"]
                                for i in range(calendar["holding_months"] // 3)]
    proof["operating_tax_total"] = taxes["holding_total"]["total"]
    proof["forward_tax"] = taxes[FORWARD_PERIOD]
    proof["post_assessment_stress"] = record | dict(profile=STRESS_PROFILE, rule=STRESS_RULE)
    return taxes, taxes[OPERATING_PERIOD], proof


def capacity_only_delivery(case, result, name):
    """A sourced no-refi alternative may be reported beside an explicitly blocked refi."""
    view = result["scenarios"][name]
    if (case.get("schema") not in SUPPORTED_SCHEMAS or view.get("cash_per_usd_10") is not None
            or view.get("blockers") != ["selected_principal_exceeds_declared_bank_capacity"]
            or result["critical_evidence_review"]["status"] != "PASSED"):
        return False
    capacity = object_or_empty(view.get("capacity"))
    selected = _fraction(capacity.get("selected_principal"), 4096)
    maximum = _fraction(capacity.get("maximum_principal_capacity"), 4096)
    alternative = object_or_empty(view.get("horizon_without_refinance"))
    cash = object_or_empty(alternative.get("cash_per_usd_10"))
    basis = case["rent_inputs"]["holding_horizon"]["scenarios"][name]["initial_equity"]["value"]
    initial = _fraction(basis)
    return bool(selected is not None and maximum is not None and selected > maximum >= 0
        and alternative.get("blockers") == [] and cash.get("events")
        and initial is not None and initial > 0
        and _fraction(cash.get("reference_amount")) == 10
        and _fraction(cash.get("basis_amount")) == initial
        and _fraction(cash.get("scale_factor")) == 10 / initial
        and object_or_empty(view.get("construction_refinance")).get("net_equity_distribution") is None)
