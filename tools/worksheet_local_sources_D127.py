"""Exercise the supplemental bot contracts with structured local synthetic sources."""
from datetime import date
from urllib.parse import urlsplit

from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.v1_contracts import load_contracts
from miniuw_worksheet_v1 import encoded


KINDS = {"plan_a": "plan_reading", "plan_b": "plan_reading",
         "gc_budget": "gc_budget", "official_snapshot": "official_snapshot"}
SCHEMA_PREFIX = "miniuw.synthetic-local-source."


def object_or_empty(value):
    return value if isinstance(value, dict) else {}


def synthetic_id(value):
    return isinstance(value, str) and value.startswith("SYNTHETIC-") and len(value) > len("SYNTHETIC-")


def check(blocker=None, **evidence):
    return dict(state="PENDING" if blocker else "checked_synthetic",
                blockers=[blocker] if blocker else [], **evidence)


def number(value):
    try:
        return _fraction(value)
    except ValidationError:
        return None


def day(value):
    try:
        result = date.fromisoformat(value)
        return result if result.isoformat() == value else None
    except (TypeError, ValueError):
        return None


def classify(sources, revision):
    """B03 checks typed content and its claimed revision before it reaches a reader."""
    documents, findings = {}, {}
    for name, kind in KINDS.items():
        envelope = object_or_empty(sources.get(name))
        document = object_or_empty(envelope.get("document"))
        digest = sha(encoded(document)) if document else None
        pointer = f"/local_sources/documents/{name}/document"
        if not document:
            findings[name] = check("local_document_missing", pointer=pointer)
        elif digest != envelope.get("sha256") or document.get("revision") != revision:
            findings[name] = check("document_hash_or_revision_mismatch", pointer=pointer, observed_sha256=digest)
        elif document.get("schema") != f"{SCHEMA_PREFIX}{kind}.v1" or not synthetic_id(document.get("document_id")):
            findings[name] = check("document_type_ambiguous_or_incompatible", pointer=pointer, observed_sha256=digest)
        else:
            documents[name] = document
            findings[name] = check(pointer=pointer, sha256=digest, kind=kind)
    for name in sorted(sources.keys() - KINDS.keys()):
        findings[name] = check("undeclared_document_role")
    blocker = "local_document_inventory_pending" if any(row["blockers"] for row in findings.values()) else None
    return documents, check(blocker, documents=findings)


def area_reading(document, source_name):
    """Read an explicit area on its own source; never infer or interpolate geometry."""
    row = object_or_empty(document.get("area"))
    amount = number(row.get("value"))
    locator = row.get("locator")
    if (amount is None or amount <= 0 or row.get("unit") != "m2"
            or not isinstance(locator, str) or not locator.strip() or not synthetic_id(document.get("plan_ref"))):
        return check("explicit_area_or_source_locator_missing")
    return check(value=rational(amount), unit="m2", locator=locator, plan_ref=document["plan_ref"],
                 document_id=document["document_id"], source_sha256=sha(encoded(document)),
                 source_pointer=f"/local_sources/documents/{source_name}/document")


def reconcile_readings(first, second):
    if first["blockers"] or second["blockers"]:
        return check("both_plan_readings_required")
    if first["document_id"] == second["document_id"] or first["source_sha256"] == second["source_sha256"]:
        return check("distinct_plan_reading_sources_required", readings=[first, second])
    if any(first[key] != second[key] for key in ("plan_ref", "unit", "value")):
        return check("plan_readings_conflict", readings=[first, second])
    return check(value=first["value"], unit=first["unit"], plan_ref=first["plan_ref"], readings=[first, second])


def read_budget(document):
    area = area_reading(document, "gc_budget")
    claim = object_or_empty(document.get("budget"))
    value, locator = number(claim.get("value")), claim.get("locator")
    if (area["blockers"] or value is None or value < 0 or claim.get("currency") != "USD"
            or not isinstance(locator, str) or not locator.strip()):
        return check("structured_gc_area_or_budget_claim_missing", area=area)
    return check(area=area, budget=dict(value=rational(value), currency="USD", locator=locator))


def check_gc(plans, budget, criterion):
    if plans["blockers"] or budget["blockers"]:
        return check("reconciled_plans_and_gc_source_required")
    area = budget["area"]
    if area["plan_ref"] != plans["plan_ref"] or area["unit"] != plans["unit"]:
        return check("GC_scope_or_unit_mismatch")
    rule = object_or_empty(criterion)
    tolerance = number(rule.get("maximum_absolute_difference"))
    if tolerance is None or tolerance < 0 or rule.get("unit") != plans["unit"] or not synthetic_id(rule.get("rule_ref")):
        return check("explicit_GC_area_criterion_required")
    difference = abs(number(area["value"]) - number(plans["value"]))
    return check("GC_area_conflict" if difference > tolerance else None,
                 difference=rational(difference), maximum=rational(tolerance), rule_ref=rule["rule_ref"], unit=plans["unit"])


def archive_official_snapshot(document, request):
    request = object_or_empty(request)
    url, allowed = document.get("url"), request.get("allowed_hosts")
    try:
        origin = urlsplit(url) if isinstance(url, str) else None
    except ValueError:
        origin = None
    if (origin is None or origin.scheme != "https" or not origin.hostname or origin.netloc != origin.hostname
            or not origin.hostname.endswith(".invalid") or origin.query or origin.fragment
            or not isinstance(allowed, list) or origin.hostname not in allowed):
        return check("authorized_synthetic_snapshot_host_required")
    observed = day(request.get("as_of"))
    valid_from, valid_through = day(document.get("valid_from")), day(document.get("valid_through"))
    if observed is None or valid_from is None or valid_through is None or not valid_from <= observed <= valid_through:
        return check("official_snapshot_date_missing_or_outside_validity")
    return check(url=url, as_of=request["as_of"], sha256=sha(encoded(document)), access="local_snapshot")


def verify_official_record(document, archived, request):
    if archived["blockers"]:
        return check("current_authorized_local_snapshot_required")
    record_id = request.get("record_id")
    if not synthetic_id(record_id):
        return check("explicit_official_record_locator_required")
    record = object_or_empty(object_or_empty(document.get("records")).get(record_id))
    floors = record.get("max_floors")
    if type(floors) is not int or floors < 0:
        return check("archived_official_value_missing")
    return check(value=floors, unit="floors", locator=f"/records/{record_id}/max_floors",
                 source_sha256=archived["sha256"], url=archived["url"], as_of=archived["as_of"])


def review_local_sources(section, workbook_hashes):
    _, contract_sha256 = load_contracts()
    section = object_or_empty(section)
    revision = section.get("revision")
    sources = object_or_empty(section.get("documents"))
    binding_ok = synthetic_id(revision) and section.get("workbook_sha256") == workbook_hashes
    documents, classifier = classify(sources if binding_ok else {}, revision)
    if not binding_ok:
        classifier["blockers"].append("local_evidence_revision_or_workbook_binding_missing")
        classifier["state"] = "PENDING"
    first = area_reading(documents.get("plan_a", {}), "plan_a")
    second = area_reading(documents.get("plan_b", {}), "plan_b")
    plans = reconcile_readings(first, second)
    budget = read_budget(documents.get("gc_budget", {}))
    gc = check_gc(plans, budget, section.get("gc_criterion"))
    snapshot = documents.get("official_snapshot", {})
    request = object_or_empty(section.get("official_request"))
    archived = archive_official_snapshot(snapshot, request)
    official = verify_official_record(snapshot, archived, request)
    bots = dict(B03=classifier, B05=first, B06=second, B07=plans, B08=budget, B09=gc, B10=archived, B11=official)
    blockers = [f"{bot}:{reason}" for bot, row in bots.items() for reason in row["blockers"]]
    return dict(contract_sha256=contract_sha256, revision=revision, state="PENDING" if blockers else "checked_synthetic",
                bots=bots, blockers=blockers)
