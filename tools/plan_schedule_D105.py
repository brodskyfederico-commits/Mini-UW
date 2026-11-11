"""Compare explicitly declared synthetic plan schedules and identify fields to review."""
from argparse import ArgumentParser
from pathlib import Path
import json
import re
import sys

from check_operating_replay_D20 import ROOT, local_file, require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.expense_cash_detail import _exact, _json
from miniuw_foundation.scheduled_expense_case import sha


SCHEMA = "miniuw.synthetic-declared-plan-schedule.v1"
MAX_BYTES = 64 * 1024
FIELDS = {
    "building_gsf": ("ft2_gross", "construction_budget_if_gsf_basis_and_scope_verified"),
    "unit_count": ("unit", "residential_rental_capacity"),
    "unit_rentable_sf": ("ft2_rentable_per_unit", "residential_income_if_per_rentable_sf"),
}
FIXTURE_A = "templates/synthetic-plan-schedule-D105-A.json"
FIXTURE_B = "templates/synthetic-plan-schedule-D105-B.json"


def parse_plan(raw):
    plan = _json(raw, MAX_BYTES)
    _exact(plan, {"schema", "deal_id", "document_id", "sheet", "revision", "building_gsf", "groups"})
    require(plan["schema"] == SCHEMA, "An explicit synthetic plan schedule is required")
    for key in ("deal_id", "document_id"):
        value = plan[key]
        require(isinstance(value, str) and re.fullmatch(r"SYNTHETIC-[A-Za-z0-9_-]{1,80}", value),
                f"{key} must be an explicit synthetic identity")
    require(type(plan["revision"]) is int and plan["revision"] > 0, "An ordered revision number is required")
    require(isinstance(plan["sheet"], str) and 0 < len(plan["sheet"].strip()) <= 64, "Sheet reference missing")
    require(isinstance(plan["groups"], list) and 1 <= len(plan["groups"]) <= 64, "Expected 1 to 64 declared groups")
    source_hash = sha(raw)
    rows = {}

    def add(group_id, field, claim, pointer):
        _exact(claim, {"value", "schedule_ref"})
        locator = claim["schedule_ref"]
        require(isinstance(locator, str) and 0 < len(locator.strip()) <= 160, "Schedule row reference missing")
        value = claim["value"]
        if field == "unit_count":
            require(value is None or (type(value) is int and value >= 0), "Unit count must be a nonnegative integer or null")
        else:
            value = _fraction(value)
            require(value is None or value >= 0, "Area must be nonnegative")
            value = None if value is None else rational(value)
        rows[(group_id, field)] = dict(value=value, source_sha256=source_hash, sheet=plan["sheet"],
                                       revision=plan["revision"], pointer=pointer + "/value", schedule_ref=locator)

    add("", "building_gsf", plan["building_gsf"], "/building_gsf")
    groups = set()
    for i, group in enumerate(plan["groups"]):
        _exact(group, {"id", "unit_count", "unit_rentable_sf"})
        identity = group["id"]
        require(isinstance(identity, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity)
                and identity not in groups, "Expected unique explicit group identities")
        groups.add(identity)
        for field in ("unit_count", "unit_rentable_sf"):
            add(identity, field, group[field], f"/groups/{i}/{field}")
    return plan, rows


def compare_schedules(before_raw, after_raw):
    before, old = parse_plan(before_raw)
    after, new = parse_plan(after_raw)
    require((before["deal_id"], before["document_id"]) == (after["deal_id"], after["document_id"]),
            "Plan revisions must refer to the same deal and document")
    require(after["revision"] > before["revision"], "The candidate revision must be later")
    rows = []
    for group_id, field in sorted(old.keys() | new.keys()):
        prior, current = old.get((group_id, field)), new.get((group_id, field))
        if current is None:
            status = "removed_from_schedule"
        elif current["value"] is None:
            status = "not_declared"
        elif prior is None:
            status = "added"
        elif prior["value"] != current["value"]:
            status = "changed"
        else:
            status = "same_declared_value"
        unit, consumer = FIELDS[field]
        rows.append(dict(group_id=group_id or None, field=field, unit=unit, conditional_consumer=consumer,
                         before=prior, after=current, status=status,
                         input_review_state="PENDING" if status != "same_declared_value" else "value_matches_prior_revision"))
    return dict(status="compared", decision="PENDING", scope="synthetic_declared_schedule_only",
                deal_id=after["deal_id"], document_id=after["document_id"],
                reference_sha256=sha(before_raw), candidate_sha256=sha(after_raw), fields=rows,
                candidate_applied_to_financial_model=False, investor_return_per_usd_10=None)


def verify():
    before = local_file(ROOT, FIXTURE_A).read_bytes()
    after = local_file(ROOT, FIXTURE_B).read_bytes()
    result = compare_schedules(before, after)
    fields = {(r["group_id"], r["field"]): r for r in result["fields"]}
    building = fields[(None, "building_gsf")]
    rentable = fields[("1BR-A", "unit_rentable_sf")]
    count = fields[("2BR-A", "unit_count")]
    require(building["status"] == "not_declared" and building["after"]["value"] is None
            and _fraction(building["before"]["value"]) == 25000,
            "A missing gross area inherited the prior figure")
    require(rentable["status"] == "changed" and _fraction(rentable["before"]["value"]) == 710
            and _fraction(rentable["after"]["value"]) == 690
            and rentable["after"]["pointer"] == "/groups/1/unit_rentable_sf/value",
            "Rentable area was inferred or matched by row position")
    require(count["status"] == "changed" and count["before"]["value"] == 6 and count["after"]["value"] == 0,
            "The declared zero was lost")
    require(fields[("1BR-A", "unit_count")]["status"] == "same_declared_value"
            and fields[("2BR-A", "unit_rentable_sf")]["status"] == "not_declared",
            "Unchanged and undeclared fields were not preserved separately")
    for row in result["fields"]:
        for side, raw in (("before", before), ("after", after)):
            record = row[side]
            require(record["source_sha256"] == sha(raw), "Source bytes do not match field provenance")
            value = json.loads(raw)
            for token in record["pointer"].split("/")[1:]:
                value = value[int(token)] if isinstance(value, list) else value[token]
            require(record["value"] == value, "Source pointer does not reproduce the field")

    candidate = json.loads(after)
    new_group = candidate["groups"][1] | {"id": "1BR-B"}
    changed = compare_schedules(before, json.dumps(candidate | {"groups": [candidate["groups"][1], new_group]}).encode())
    moved = {(r["group_id"], r["field"]): r for r in changed["fields"]}
    require(moved[("2BR-A", "unit_count")]["status"] == "removed_from_schedule"
            and moved[("2BR-A", "unit_count")]["after"] is None
            and moved[("1BR-B", "unit_count")]["status"] == "added"
            and moved[("1BR-B", "unit_count")]["before"] is None,
            "Group membership was guessed across revisions")
    bad_group = candidate["groups"][0] | {"unit_count": {"value": True, "schedule_ref": "B2"}}
    invalid = (
        candidate | {"revision": 1},
        candidate | {"deal_id": "SYNTHETIC-other-deal"},
        candidate | {"groups": [candidate["groups"][0]] * 2},
        candidate | {"groups": [bad_group, candidate["groups"][1]]},
    )
    for bad in invalid:
        try:
            compare_schedules(before, json.dumps(bad).encode())
        except ValueError:
            continue
        raise AssertionError("An invalid revision or field was accepted")
    require(result["decision"] == "PENDING" and result["investor_return_per_usd_10"] is None
            and not result["candidate_applied_to_financial_model"], "Comparison acquired financial authority")
    return dict(status="passed", decision="PENDING", fields=len(fields),
                pending_fields=sum(row["input_review_state"] == "PENDING" for row in fields.values()),
                invalid_cases_rejected=len(invalid), candidate_sha256=result["candidate_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    compare = commands.add_parser("compare")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = verify()
        else:
            require(all(p.is_file() and p.stat().st_size <= MAX_BYTES for p in (args.before, args.after)),
                    "Two bounded schedule files are required")
            result = compare_schedules(args.before.read_bytes(), args.after.read_bytes())
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps(dict(status="blocked", decision="PENDING", reason=str(error)), ensure_ascii=False),
              file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
