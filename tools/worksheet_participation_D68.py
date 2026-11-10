"""Allocate the exact costed-sale ledger using expressly archived synthetic terms."""
from check_integrated_participation_D28 import PROFILE, allocate
from check_operating_replay_D20 import ROOT, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from miniuw_foundation.expense_cash_detail import _exact, _json
from miniuw_foundation.scheduled_expense_case import sha


TERMS = "templates/synthetic-worksheet-participation-terms-D68.json"


def build_participation(case, parent, terms_hash):
    raw = local_file(ROOT, TERMS).read_bytes()
    require(sha(raw) == terms_hash, "Synthetic participation terms bytes differ")
    terms = _json(raw)
    _exact(terms, {"schema", "profile", "terms_id", "revision", "currency", "participant_inventory_complete",
                   "source_ref", "whole_ledger_scope_ref", "assumptions", "project_ledgers", "participants"})
    require(terms["schema"] == "miniuw.synthetic-worksheet-participation.v1" and terms["profile"] == PROFILE
            and terms["terms_id"] == "SYNTHETIC-D68-constant-cash-shares" and terms["revision"] == 1
            and terms["source_ref"] and terms["whole_ledger_scope_ref"],
            "Explicit archived synthetic worksheet terms are required")
    binding = terms["project_ledgers"].get(case)
    allocation = allocate(terms, parent, binding)
    observations = observe_allocation(allocation, parent)
    for participant in allocation["participants"] or []:
        for index, event in enumerate(participant["dated_events"]):
            event["project_event_pointer"] = f"/project/events/{index}"
    return allocation | {"terms_path": TERMS, "terms_sha256": terms_hash, "project_ledger_sha256": binding,
                         "risk": observations, "personal_investor_return": None, "decision": "PENDING"}
