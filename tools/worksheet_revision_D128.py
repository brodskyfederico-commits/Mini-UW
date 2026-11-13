"""Bind the local pilot to an independently supplied synthetic revision snapshot."""
import re

from miniuw_foundation.expense_cash_detail import _json
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import MAX_CURRENT_REVISION_BYTES, encoded
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


SCHEMA = "miniuw.synthetic-workbook-current-revision.v1"
ROLES = ("workbooks", "financial_sources", "plan_and_gc_documents", "official_source", "gc_criterion", "investment_rules")
FINANCIAL_SOURCES = ("worksheet_case", "irr_policy", "yield_inputs", "funding_inputs", "occupancy_inputs",
                     "return_inputs", "reference_metrics")


def case_revision(case):
    """Project the exact inputs for each gate independently of their revision labels."""
    local = object_or_empty(case.get("local_sources"))
    documents = object_or_empty(local.get("documents"))
    plans = {name: value for name, value in documents.items() if name != "official_snapshot"}
    if "plan_pdf" in local:
        plans = dict(documents=plans, plan_pdf=local["plan_pdf"])
    if "finance_binding" in local:
        plans = dict(source_inventory=plans, finance_binding=local["finance_binding"])
    if "evidence_pdf" in local:
        plans = dict(source_inventory=plans, evidence_pdf=local["evidence_pdf"])
    payloads = dict(
        workbooks=case.get("workbook_sha256"),
        financial_sources={name: case.get(name) for name in FINANCIAL_SOURCES},
        plan_and_gc_documents=plans,
        official_source=dict(document=documents.get("official_snapshot"), request=local.get("official_request")),
        gc_criterion=local.get("gc_criterion"),
        investment_rules=dict(rules=case.get("rules"), aggregation_rule=case.get("aggregation_rule")),
    )
    if "native_mapping" in case:
        payloads["financial_sources"]["native_mapping"] = case["native_mapping"]
    if "rent_inputs" in case:
        payloads["financial_sources"]["rent_inputs"] = case["rent_inputs"]
    if "criteria_workbook" in case:
        payloads["investment_rules"]["criteria_workbook"] = case["criteria_workbook"]
    return dict(local_revision=local.get("revision"), criteria_revision=case.get("criteria_revision"),
                fingerprints={role: sha(encoded(value)) for role, value in payloads.items()})


def snapshot_for_case(case, revision):
    return dict(schema=SCHEMA, revision=revision, **case_revision(case))


def parse_snapshot(raw):
    if raw is None:
        return None
    try:
        value = _json(raw, MAX_CURRENT_REVISION_BYTES)
    except ValueError:
        return None
    if (not isinstance(value, dict)
            or set(value) != {"schema", "revision", "local_revision", "criteria_revision", "fingerprints"}
            or value["schema"] != SCHEMA
            or not all(synthetic_id(value[key]) for key in ("revision", "local_revision", "criteria_revision"))):
        return None
    fingerprints = value["fingerprints"]
    if (not isinstance(fingerprints, dict) or fingerprints.keys() != set(ROLES)
            or not all(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
                       for digest in fingerprints.values())):
        return None
    return value


def review_revision(case, raw):
    expected = parse_snapshot(raw)
    observed = case_revision(case)
    if expected is None:
        return dict(state="PENDING", reference_revision=None, reference_sha256=None,
                    blockers=["current_revision_snapshot_missing" if raw is None else "current_revision_snapshot_invalid"],
                    observed=observed)
    blockers = [f"{name}_mismatch" for name in ("local_revision", "criteria_revision")
                if observed[name] != expected[name]]
    blockers.extend(f"{role}_fingerprint_mismatch" for role in ROLES
                    if observed["fingerprints"][role] != expected["fingerprints"][role])
    return dict(state="PENDING" if blockers else "matched_synthetic_revision", reference_revision=expected["revision"],
                reference_sha256=sha(raw), blockers=blockers, observed=observed, expected=expected["fingerprints"])


def audit_revision(result, raw):
    """Distinguish replay of the saved case from its designation as current."""
    captured = result["revision_review"]
    current = parse_snapshot(raw)
    status = "PENDING"
    revision_blockers = list(captured["blockers"])
    # A matching case declaration alone does not establish the identity of
    # the criteria XLSX that the package actually replayed.
    intake = object_or_empty(result.get("screening", {}).get("criteria_workbook"))
    revision_blockers.extend(reason for reason in intake.get("blockers", []) if reason in {
        "criteria_workbook_missing", "criteria_workbook_hash_mismatch", "criteria_workbook_revision_mismatch",
    })
    if result.get("profile") == "synthetic_documented_technical_acceptance":
        for scenario, review in result["native_mapping_review"]["scenarios"].items():
            if "native_workbook_missing_or_unbound" in review["blockers"]:
                revision_blockers.append(f"{scenario}:native_workbook_missing_or_unbound")
    if current is None:
        revision_blockers.append("current_revision_snapshot_missing" if raw is None else "current_revision_snapshot_invalid")
    elif not revision_blockers and captured["state"] == "matched_synthetic_revision":
        if captured["reference_sha256"] == sha(raw):
            status = "VIGENTE"
        else:
            status = "HISTORICO"
            revision_blockers.append("archived_revision_differs_from_current")
    archived = result["simulation_result"]
    return dict(vigencia=status, revision_blockers=sorted(set(revision_blockers)),
                archived_simulation_result=archived,
                state=result["state"] if status == "VIGENTE" else "PENDING",
                simulation_result=archived if status == "VIGENTE" else "PENDING",
                archived_revision=captured["reference_revision"],
                current_revision=None if current is None else current["revision"])
