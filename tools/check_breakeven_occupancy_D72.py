"""Verify a synthetic economic-occupancy break-even against the NOI engine."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_yoc_spread_D70 import FIXTURE as OPERATING_ARCHIVE
from miniuw_linked_cotejo_D54 import publish
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.expense_cash_detail import _exact, _json
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.scheduled_expense_case import sha


FIXTURE = "templates/synthetic-breakeven-occupancy-D72.json"
BASIS = "synthetic_economic_rent_realization_fraction"
FIELDS = ("rent_at_full_occupancy", "fixed_expenses", "tax_floor", "tax_coefficient", "debt_service")


def solve(case, operating):
    _exact(case, {*FIELDS, "operating_inventory", "debt_service_period", "source_ref"})
    source = deepcopy(operating)
    period = source["period_ref"]
    blockers = []
    if case["debt_service_period"] != period:
        blockers.append("debt_service_period_mismatch")
    if not isinstance(case["source_ref"], str) or not case["source_ref"].startswith("SYNTHETIC-D72-"):
        blockers.append("explicit_synthetic_source_required")
    values = {key: _fraction(case[key]) for key in FIELDS}
    for key, value in values.items():
        if value is None or value < 0:
            blockers.append(f"missing_or_outside_profile:{key}")
    if values["rent_at_full_occupancy"] == 0:
        blockers.append("positive_rent_slope_required")
    result = dict(state="PENDING", decision="PENDING", occupancy_basis=BASIS, period=period,
                  minimum_occupancy=None, algebraic_crossing=None, blockers=blockers,
                  evaluated_points=[], source_sha256=sha(encoded(case)))
    if blockers:
        return result

    rent, expense, floor, coefficient, service = (values[k] for k in FIELDS)
    crossing = (expense + service + max(floor, coefficient * service)) / rent
    result["algebraic_crossing"] = rational(crossing)

    def evaluate(q):
        for row in (*source["income_rows"], *source["expense_rows"], source["tax_floor"], source["tax_coefficient"]):
            row["source_ref"] = case["source_ref"]
        source["income_rows"][0]["value"] = rational(rent * q)
        source["income_rows"][1]["value"] = rational(Fraction(0))
        source["expense_rows"][0]["value"] = rational(expense)
        source["tax_floor"]["value"] = rational(floor)
        source["tax_coefficient"]["value"] = rational(coefficient)
        run = produce_operating_noi(encoded(source))
        payload = run.payload
        require(payload["calculation_status"] == "computed_synthetic_profile" and payload["noi"] is not None,
                "The existing NOI engine did not reproduce the synthetic profile")
        covered = amount(payload["noi"]) >= service
        require(covered == (q >= crossing), "Algebraic crossing differs from the NOI engine")
        return dict(occupancy=rational(q), noi=payload["noi"], debt_service=rational(service),
                    tax=payload["property_tax"], tax_branch=payload["tax_branch"],
                    covers_debt_service=covered, noi_run_sha256=run.sha256)

    points = {Fraction(0), Fraction(1)}
    if 0 <= crossing <= 1:
        points.add(crossing)
        step = Fraction(1, 100)
        points.update(q for q in (crossing - step, crossing + step) if 0 <= q <= 1)
    result["evaluated_points"] = [evaluate(q) for q in sorted(points)]
    if crossing > 1:
        result["state"] = "infeasible_within_domain"
    else:
        result.update(state="computed_synthetic", minimum_occupancy=rational(crossing))
    return result


def verify():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = _json(raw)
    _exact(fixture, {"schema", "operating_archive_sha256", "occupancy_basis", "scenarios"})
    archive_raw = local_file(ROOT, OPERATING_ARCHIVE).read_bytes()
    require(fixture["schema"] == "miniuw.synthetic-breakeven-occupancy-rehearsal.v1"
            and fixture["operating_archive_sha256"] == sha(archive_raw)
            and fixture["occupancy_basis"] == BASIS, "Unsupported or changed occupancy fixture")
    inventory = _json(archive_raw)["scenarios"]
    scenarios = fixture["scenarios"]
    _exact(scenarios, {"Base", "Downside", "no_feasible_occupancy", "all_occupancies_feasible"})
    cases = {name: solve(row, inventory[row["operating_inventory"]]["stabilized_noi"])
             for name, row in scenarios.items()}
    for name, minimum in {"Base": Fraction(13, 20), "Downside": Fraction(9, 10),
                          "all_occupancies_feasible": Fraction(0)}.items():
        require(cases[name]["state"] == "computed_synthetic"
                and amount(cases[name]["minimum_occupancy"]) == minimum, "Minimum differs from the independent check")
    impossible = cases["no_feasible_occupancy"]
    require(impossible["state"] == "infeasible_within_domain" and impossible["minimum_occupancy"] is None
            and amount(impossible["algebraic_crossing"]) > 1
            and not any(row["covers_debt_service"] for row in impossible["evaluated_points"]),
            "Infeasibility was hidden by clipping at full occupancy")

    base = scenarios["Base"]
    operating = inventory["Base"]["stabilized_noi"]
    blocked = {"period_mismatch": solve(base | {"debt_service_period": "SYNTHETIC-D72-other-year"}, operating),
               "missing_debt_service": solve(base | {"debt_service": None}, operating)}
    require(all(row["state"] == "PENDING" and row["minimum_occupancy"] is None
                and not row["evaluated_points"] for row in blocked.values()),
            "Missing or incompatible debt input produced an occupancy figure")
    return dict(status="passed", decision="PENDING", occupancy_basis=BASIS, cases=cases,
                blocked=blocked, fixture_sha256=sha(raw), real_decisions_enabled=False, deployment_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New path for full synthetic evidence.")
    try:
        args = parser.parse_args()
        report = verify()
        if args.output is not None:
            publish(args.output, report)
        print(json.dumps(dict(status=report["status"], decision=report["decision"],
                              cases={key: {"state": row["state"], "minimum": row["minimum_occupancy"]}
                                     for key, row in report["cases"].items()},
                              blocked_cases=list(report["blocked"])), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
