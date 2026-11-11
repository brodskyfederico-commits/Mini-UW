"""Reproduce the synthetic D105 plan revision's impact on rent and costs."""
from argparse import ArgumentParser
from fractions import Fraction
import json

from check_operating_replay_D20 import ROOT, local_file, require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.rental_operations import SCHEMA, produce_rental_operations
from plan_schedule_D105 import FIXTURE_A, FIXTURE_B, compare_schedules


RENT_BASES = {
    "1BR-A": ("per_rentable_sf_per_month", 2),
    "2BR-A": ("per_unit_per_month", 1800),
}
EXPENSES = {
    "per_unit_opex": ("per_unit_per_regular_year", 600),
    "management": ("fraction_of_residential_effective_rent", Fraction(1, 20)),
    "fixed_opex": ("fixed_per_declared_period", 900),
}
VERTICAL_RATE_PER_GSF = 160
VERTICAL_RATE_PER_UNIT = 125000
VERTICAL_FIXED_TOTAL = 3600000


def values_at(comparison, revision):
    """Keep missing declarations and removed groups unresolved."""
    values = {}
    for row in comparison["fields"]:
        field = row["field"]
        claim = row[revision]
        value = None if claim is None else claim["value"]
        values[(row["group_id"], field)] = value if field == "unit_count" else _fraction(value)
    return values


def operations_source(comparison, revision, bases):
    values = values_at(comparison, revision)
    groups = []
    for group_id, (basis, rate) in bases.items():
        count = values.get((group_id, "unit_count"))
        area = values.get((group_id, "unit_rentable_sf"))
        groups.append({
            "group_id": group_id,
            "units": None if count is None else rational(Fraction(count)),
            "unit_rentable_sf": None if area is None else rational(area),
            "rent_basis": basis,
            "rent": rational(Fraction(rate)),
            "rent_definition": "gross_before_losses_and_concessions",
            "loss_fraction": rational(Fraction(1, 20)),
            "concession_fraction": rational(Fraction(1, 50)),
            "concession_basis": "gross_potential_rent",
            "currency": "USD",
            "source_ref": f"D106/{revision}/{group_id}",
            "policy_ref": "D106/synthetic-assumptions",
        })
    expenses = [
        dict(item_id=item, kind=basis, rate=rational(Fraction(rate)), currency="USD",
             source_ref=f"D106/{item}", policy_ref="D106/synthetic-assumptions")
        for item, (basis, rate) in EXPENSES.items()
    ]
    return {
        "schema": SCHEMA,
        "context": {
            "deal_id": comparison["deal_id"],
            "scenario_id": "SYNTHETIC-D106-same-rates",
            "run_id": f"SYNTHETIC-D106-{revision}",
            "definition_set_revision": "SYNTHETIC-D106-v1",
        },
        "currency": "USD",
        "period_ref": "SYNTHETIC-one-regular-month",
        "months_in_period": 1,
        "months_per_year": 12,
        "residential_groups": groups,
        "expense_items": expenses,
    }


def run_operations(comparison, revision, bases):
    return produce_rental_operations(json.dumps(operations_source(comparison, revision, bases)).encode()).payload


def vertical_alternatives(comparison, revision):
    values = values_at(comparison, revision)
    gross_area = values[(None, "building_gsf")]
    counts = [value for (_, field), value in values.items() if field == "unit_count"]
    return {
        "gsf": None if gross_area is None else gross_area * VERTICAL_RATE_PER_GSF,
        "units": None if any(count is None for count in counts) else Fraction(sum(counts) * VERTICAL_RATE_PER_UNIT),
        "fixed_total": Fraction(VERTICAL_FIXED_TOTAL),
    }


def build_report(before, after):
    comparison = compare_schedules(before, after)
    groups = {row["group_id"] for row in comparison["fields"] if row["field"] == "unit_count"}
    require(groups == RENT_BASES.keys(), "This example requires explicit terms for every declared group")
    revisions = ("before", "after")
    operations = [run_operations(comparison, rev, RENT_BASES) for rev in revisions]
    unit_alternative = RENT_BASES | {"1BR-A": ("per_unit_per_month", 1400)}
    alternate = [run_operations(comparison, rev, unit_alternative) for rev in revisions]
    vertical = [vertical_alternatives(comparison, rev) for rev in revisions]
    amounts = {}

    def add(key, pair, period):
        old, new = pair
        delta = None if old is None or new is None else new - old
        amounts[key] = {
            "period": period,
            "status": "PENDING" if delta is None else "unchanged" if delta == 0 else "changed",
            "before_usd": None if old is None else rational(old),
            "after_usd": None if new is None else rational(new),
            "delta_usd": None if delta is None else rational(delta),
        }

    for run_pair, group_index, key in (
        (operations, 0, "1BR-A_rent_by_rentable_sf"),
        (alternate, 0, "1BR-A_rent_by_unit"),
        (operations, 1, "2BR-A_rent_by_unit"),
    ):
        add(key, [_fraction(run["groups"][group_index]["results"]["gross_potential"])
                  for run in run_pair], "month")
    for key, field in (("potential_rent", "gross_potential_total"),
                       ("effective_residential_rent", "residential_effective_rent")):
        add(key, [_fraction(run[field]) for run in operations], "month")
    for index, key in enumerate(EXPENSES):
        add(key, [_fraction(run["expenses"][index]["amount"]) for run in operations], "month")
    for key in vertical[0]:
        add(f"vertical_{key}", [budget[key] for budget in vertical], "project_total")

    return {
        "status": "compared",
        "decision": "PENDING",
        "scope": "isolated_synthetic_calculation_impact",
        "plan_comparison": comparison,
        "amounts": amounts,
        "operations_blockers": dict(zip(revisions, [run["blockers"] for run in operations])),
        "investor_return_per_usd_10": None,
        "investor_return_status": "PENDING",
        "candidate_applied_to_financial_model": False,
    }


def verify(before, after, report):
    expected = {
        "1BR-A_rent_by_rentable_sf": (28400, 27600),
        "1BR-A_rent_by_unit": (28000, 28000),
        "2BR-A_rent_by_unit": (10800, 0),
        "potential_rent": (39200, 27600),
        "effective_residential_rent": (36456, 25668),
        "per_unit_opex": (1300, 1000),
        "management": (Fraction(9114, 5), Fraction(6417, 5)),
        "fixed_opex": (900, 900),
        "vertical_gsf": (4000000, None),
        "vertical_units": (3250000, 2500000),
        "vertical_fixed_total": (3600000, 3600000),
    }
    for key, pair in expected.items():
        row = report["amounts"][key]
        require(tuple(_fraction(row[f"{side}_usd"]) for side in ("before", "after")) == pair,
                f"Unexpected synthetic amount for {key}")
        expected_delta = None if pair[1] is None else pair[1] - pair[0]
        require(_fraction(row["delta_usd"]) == expected_delta, f"Unexpected delta for {key}")
    require(report["amounts"]["vertical_gsf"]["status"] == "PENDING"
            and all(not blockers for blockers in report["operations_blockers"].values()),
            "Missing GSF must block only the GSF calculation in this profile")

    comparison = report["plan_comparison"]
    area_required = RENT_BASES | {"2BR-A": ("per_rentable_sf_per_month", 2)}
    blocked = run_operations(comparison, "after", area_required)
    require(blocked["state"] == "blocked" and blocked["gross_potential_total"] is None
            and "rentable_area_missing_or_outside_profile" in blocked["groups"][1]["blockers"]
            and blocked["expenses"][0]["amount"] is None,
            "The T21 area requirement or dependent expense was bypassed")
    candidate = json.loads(before)
    candidate["revision"] = 2
    candidate["building_gsf"]["value"] = rational(Fraction(24000))
    gsf_only = build_report(before, json.dumps(candidate).encode())["amounts"]
    require(_fraction(gsf_only["vertical_gsf"]["delta_usd"]) == -160000
            and all(row["status"] == "unchanged" for key, row in gsf_only.items() if key != "vertical_gsf"),
            "A gross-only area change affected an unrelated basis")

    candidate = json.loads(after)
    zero_group = candidate["groups"][0]
    zero_group["unit_count"]["value"] = None
    missing_count = build_report(before, json.dumps(candidate).encode())["amounts"]
    for key in ("2BR-A_rent_by_unit", "potential_rent", "per_unit_opex", "management", "vertical_units"):
        require(missing_count[key]["status"] == "PENDING" and missing_count[key]["after_usd"] is None,
                f"An undeclared count was treated as zero for {key}")
    candidate["groups"].remove(zero_group)
    removed_group = build_report(before, json.dumps(candidate).encode())["amounts"]
    require(removed_group == missing_count, "Omitting a group implied a declared zero")

    require(report["decision"] == "PENDING" and report["investor_return_per_usd_10"] is None
            and not report["candidate_applied_to_financial_model"],
            "An isolated plan diagnostic acquired financial authority")
    return dict(status="passed", decision="PENDING", compared_amounts=len(expected), cases=5)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "report"))
    args = parser.parse_args()
    before = local_file(ROOT, FIXTURE_A).read_bytes()
    after = local_file(ROOT, FIXTURE_B).read_bytes()
    report = build_report(before, after)
    output = verify(before, after, report) if args.command == "check" else report
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
