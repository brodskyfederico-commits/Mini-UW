"""Regression test for blank, absent and explicit zero values in the Mini-UW worksheet."""
from copy import deepcopy
import json

from check_operating_replay_D20 import require
from check_worksheet_alternatives_D155 import workbook_values
from check_worksheet_evidence_progressive_crop_D163 import same_cash
from check_worksheet_market_evidence_D166 import BOOKS, CASE, CURRENT, PLAN, shuffled_pdf
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import build_results, encoded
from plan_return_D107 import OPERATING_PERIOD
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog, review_native_mapping
from worksheet_revision_D128 import snapshot_for_case


EMPTY_ENCODINGS = {"missing": "missing", "blank": {}, "empty_text": {"text": ""}, "whitespace": {"text": " "}}
ZERO = rational(0)


def variant(case, books, values, name, cell, descriptor, *, confirm=False):
    changed = deepcopy(case)
    raw = native_workbook(values[name] | {cell: descriptor})
    workbook_hash = sha(raw)
    changed["workbook_sha256"][name] = workbook_hash
    changed["local_sources"]["workbook_sha256"][name] = workbook_hash
    confirmation = changed["native_mapping"]["scenarios"][name]
    confirmation["workbook_sha256"] = workbook_hash
    field = f"INPUT_{cell}"
    if confirm and field in confirmation["not_applicable_fields"]:
        confirmation["not_applicable_fields"].remove(field)
        confirmation["confirmed_fields"].append(field)
    return changed, books | {name: raw}


def field_row(review, name, field):
    return next(row for row in review["scenarios"][name]["rows"] if row["field_id"] == field)


def verify_mapping(case, books, values, catalog):
    counts = dict(empty_cases=0, pending_empty_cases=0, not_applicable_empty_cases=0,
                  numeric_zero_cases=0, nonnumeric_zero_rejections=0)

    def inspect(name, cell, descriptor, *, confirm=False):
        changed, changed_books = variant(case, books, values, name, cell, descriptor, confirm=confirm)
        review = review_native_mapping(changed["native_mapping"], changed_books, changed["workbook_sha256"])
        return field_row(review, name, f"INPUT_{cell}")

    for name in SCENARIOS:
        declared_omissions = case["native_mapping"]["scenarios"][name]["not_applicable_fields"]
        for definition in catalog:
            field = definition["field_id"]
            cell = definition["value_cell"].split("!", 1)[1]
            for encoding, descriptor in EMPTY_ENCODINGS.items():
                row = inspect(name, cell, descriptor)
                if field in declared_omissions and encoding in ("missing", "blank"):
                    expected, blocker = "NOT_APPLICABLE", []
                    counts["not_applicable_empty_cases"] += 1
                else:
                    expected = "PENDING"
                    if field in declared_omissions:
                        blocker = ["incompatible_not_applicable_declaration"]
                    elif encoding in ("missing", "blank"):
                        blocker = ["confirmed_field_value_missing"]
                    else:
                        blocker = ["literal_does_not_match_field_representation"]
                    counts["pending_empty_cases"] += 1
                require(row["state"] == expected and row["value"] is None and row["blockers"] == blocker,
                        f"{name} {cell} {encoding}: expected {expected} with a null value")
                counts["empty_cases"] += 1

            zero = inspect(name, cell, {"value": "0"}, confirm=True)
            require(zero["cell_kind"] == "numeric_lexeme" and zero["source_literal"] == "0",
                    f"{name} {cell}: lost explicit numeric zero")
            if definition["role"] == "arithmetic_candidate":
                require(zero["state"] == "CONFIRMED_SYNTHETIC" and zero["value"] == ZERO and not zero["blockers"],
                        f"{name} {cell}: numeric zero was not preserved by the reader")
                counts["numeric_zero_cases"] += 1
            else:
                require(zero["state"] == "PENDING" and zero["value"] is None
                        and zero["blockers"] == ["literal_does_not_match_field_representation"],
                        f"{name} {cell}: numeric zero was accepted for a nonnumeric field")
                counts["nonnumeric_zero_rejections"] += 1
    return counts


def verify_integrated(case, books, values):
    pdf, plan = shuffled_pdf(), PLAN.read_bytes()

    def run(case, books, revision):
        result, _ = build_results(encoded(case), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"],
                                  current_revision_raw=revision, plan_raw=plan, evidence_raw=pdf)
        require(result["decision"] == "PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"]
                and not result["revision_review"]["blockers"], "The probe lost its synthetic decision or revision guard")
        return result

    baseline = run(case, books, CURRENT.read_bytes())
    require(baseline["simulation_result"] == "FAIL" and all(row["cash_per_usd_10"] is not None for row in baseline["scenarios"].values()),
            "Complete D166 fixture must compute Base and Downside")

    def replay(cell, descriptor):
        changed, changed_books = variant(case, books, values, "Downside", cell, descriptor)
        revision = encoded(snapshot_for_case(changed, "SYNTHETIC-D171-current"))
        result = run(changed, changed_books, revision)
        require(result["scenarios"]["Base"]["cash_per_usd_10"] == baseline["scenarios"]["Base"]["cash_per_usd_10"],
                f"Downside {cell} altered Base cash")
        row = field_row(result["native_mapping_review"], "Downside", f"INPUT_{cell}")
        return result, row

    missing_cases = (("C13", {}, "blank"), ("C13", "missing", "missing"),
                     ("C13", {"formula": "0", "value": "0"}, "formula"),
                     ("C59", "missing", "missing"), ("C72", "missing", "missing"))
    for cell, descriptor, kind in missing_cases:
        result, row = replay(cell, descriptor)
        blocker = "formula_or_error_not_resolved" if kind == "formula" else "confirmed_field_value_missing"
        require(result["simulation_result"] == "PENDING" and result["scenarios"]["Downside"]["cash_per_usd_10"] is None
                and row["value"] is None and row["state"] == "PENDING" and row["cell_kind"] == kind
                and row["blockers"] == [blocker], f"Downside {cell} {kind} released cash or lost its blocker")
        if kind == "formula":
            require(row["cached_value"] == "0", "Cached zero was not preserved as evidence")

    result, row = replay("C13", {"value": "0"})
    downside = result["scenarios"]["Downside"]
    require(row["value"] == ZERO and row["state"] == "CONFIRMED_SYNTHETIC"
            and downside["noi_by_period"][OPERATING_PERIOD]["other_income"] == ZERO
            and downside["cash_per_usd_10"] is None
            and downside["blockers"] == ["selected_principal_exceeds_declared_bank_capacity"],
            "C13 zero did not reach NOI, or the later capacity check did not block")

    def c81(result):
        return result["alternative_evaluation"]["slots"]["C81"]["Downside"]

    require(c81(baseline)["state"] == "computed_synthetic" and c81(baseline)["binding"]["value"] == ZERO
            and c81(baseline)["cash_per_usd_10"] is not None, "Explicit zero sale costs did not compute")
    blank_c81, row = replay("C81", {})
    entry = c81(blank_c81)
    require(row["state"] == "PENDING" and row["value"] is None
            and entry["state"] == "PENDING" and entry["cash_per_usd_10"] is None
            and entry["blockers"] == ["alternative_request_unconfirmed"]
            and blank_c81["simulation_result"] == baseline["simulation_result"],
            "An empty C81 produced a zero-cost alternative or changed the baseline screening")
    # The edited worksheet has a new hash, so source references change even
    # though the Downside baseline amounts and dates are unchanged.
    same_cash(blank_c81, baseline, "Downside")
    return dict(integrated_pending_cases=len(missing_cases) + 1, integrated_explicit_zero_cases=2,
                page_count=baseline["page_count"], pdf_sha256=baseline["pdf_sha256"])


def main():
    case = json.loads(CASE.read_bytes())
    books = {name: path.read_bytes() for name, path in BOOKS.items()}
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in SCENARIOS}
    require(len(catalog) == 55 and all(native_workbook(values[name]) == books[name] for name in SCENARIOS),
            "The test must use the 55 original field IDs and reproduce the D166 workbooks")
    mapping = verify_mapping(case, books, values, catalog)
    integrated = verify_integrated(case, books, values)
    print(json.dumps(dict(status="passed", decision="PENDING", fields=len(catalog),
                          scenarios=list(SCENARIOS), **mapping, **integrated), sort_keys=True))


if __name__ == "__main__":
    main()
