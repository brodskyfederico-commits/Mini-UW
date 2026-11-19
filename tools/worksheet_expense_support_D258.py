"""Bind a synthetic insurance-premium revision while retaining coverage and validity."""
from copy import deepcopy

from check_operating_replay_D20 import require
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


def support_inventory(raw, cells):
    records = object_or_empty(raw)
    individual = object_or_empty(records.get("individual"))
    require(records.keys() == {"individual", "combined"} and individual.keys() == set(cells)
            and all(isinstance(record, dict) for record in (*individual.values(), records.get("combined"))),
            "expense_support_inventory_invalid")
    return records


def supported_inputs(raw, name, record, bindings):
    require(isinstance(raw, dict), "expense_origin_inputs_required")
    insurance_changes = any(entry["change"]["target_cell"] == "C59" for entry in bindings)
    keys = {"source_ref", "insurance"} if insurance_changes else {"source_ref"}
    require(isinstance(record, dict) and record.keys() == keys and synthetic_id(record["source_ref"]),
            "expense_support_source_or_inventory_unconfirmed")
    inputs = deepcopy(raw)
    proof = dict(source_ref=record["source_ref"], origin_inputs_sha256=sha(encoded(raw)))
    if not insurance_changes:
        return inputs, proof
    parent = object_or_empty(object_or_empty(object_or_empty(object_or_empty(raw.get("market_evidence"))
        .get("scenarios")).get(name)).get("insurance"))
    parent_doc = object_or_empty(parent.get("document"))
    revision = object_or_empty(record["insurance"])
    doc = object_or_empty(revision.get("document"))
    require(parent.keys() == {"document", "sha256"} and parent["sha256"] == sha(encoded(parent_doc))
            and revision.keys() == {"parent_sha256", "document", "sha256"}
            and revision["parent_sha256"] == parent["sha256"] and revision["sha256"] == sha(encoded(doc))
            and doc.keys() == parent_doc.keys() and synthetic_id(doc.get("source_ref"))
            and doc["source_ref"] != parent_doc["source_ref"], "expense_insurance_revision_binding_unconfirmed")
    immutable = lambda item: {key: value for key, value in item.items() if key not in {"source_ref", "premium_per_insured_unit"}}
    require(immutable(doc) == immutable(parent_doc), "expense_insurance_coverage_or_scope_changed")
    inputs["market_evidence"]["scenarios"][name]["insurance"] = dict(document=doc, sha256=revision["sha256"])
    return inputs, proof | dict(insurance_revision=revision)
