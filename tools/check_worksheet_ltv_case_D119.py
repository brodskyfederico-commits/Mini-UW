"""Verify C71 and C72 competing limits through the audited synthetic worksheet."""
from argparse import ArgumentParser
from base64 import b64decode
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_worksheet_capacity_case_D118 import CASE
from check_worksheet_intake_case_D117 import audit, changed_cells, workbook_with_numeric_cell
from check_worksheet_sale_costs_D63 import FIXTURE as WORKBOOKS
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_plan_refinance_D109 import CAPACITY_BLOCKER


REQUESTED = 150
EXPECTED_CASH = (
    ("2027-01-01", "contribution", "initial_capital", Fraction(10)),
    ("2027-03-01", "distribution", "operating_distribution", Fraction(1)),
    ("2027-04-01", "distribution", "net_refinance_distribution", Fraction(2)),
    ("2027-06-01", "distribution", "operating_distribution", Fraction(1)),
    ("2027-07-01", "distribution", "net_sale_distribution", Fraction(54056381, 6060200)),
)
CASES = (
    ("dscr-limits", "0.8", "2", "DSCR", True),
    ("ltv-limits", "0.4", "2", "LTV", True),
    ("at-ltv-limit", "0.3", "2", "LTV", True),
    ("over-ltv-limit", "0.2999", "2", "LTV", False),
    ("over-dscr-limit", "0.4", "4", "DSCR", False),
    ("missing-ltv", None, "2", None, False),
)


def verify_limits(capacity, workbook, ltv, dscr, binding):
    # Archived valuation NOI USD 50 at 10%; bank NOI USD 2000 and 3 monthly payments at 1%.
    property_value = Fraction(50) / Fraction(1, 10)
    unit_payment = Fraction(1, 100) / (1 - Fraction(101, 100) ** -3)
    limits = {"LTV": property_value * Fraction(ltv), "DSCR": Fraction(2000) / (Fraction(dscr) * 12 * unit_payment)}
    expected = min(limits.values())
    claims = {row["locator"]: row["claim"] for row in capacity["lineage"]}
    ltv_claim, dscr_claim = (claims[f"/parameters/{field}"] for field in ("maximum_ltv", "minimum_dscr"))
    require({key: amount(value) for key, value in capacity["capacity_limits"].items()} == limits
            and amount(capacity["maximum_principal_capacity"]) == expected
            and amount(capacity["selected_principal"]) == REQUESTED
            and capacity["binding_limit_ids"] == [binding]
            and amount(ltv_claim["value"]) == Fraction(ltv)
            and amount(dscr_claim["value"]) == Fraction(dscr)
            and all(claim["source_ref"] == f"sha256:{sha(workbook)}#xlsx:sheet:Inputs:cell:{cell}"
                    for claim, cell in ((ltv_claim, "C71"), (dscr_claim, "C72"))),
            "The exact LTV/DSCR limits, binding reason or cell provenance differ")
    return expected


def verify(temp, saved_output):
    archived = json.loads(local_file(ROOT, WORKBOOKS).read_bytes())["workbooks"]["base"]
    raw = b64decode(archived["xlsx_base64"], validate=True)
    require(sha(raw) == archived["sha256"], "The synthetic source workbook changed")
    base = workbook_with_numeric_cell(raw, "C72", "2")
    if saved_output is not None:
        saved_output.mkdir(exist_ok=True)
    output_root = saved_output or temp
    records = {}
    compatible = blocked = missing = 0
    for label, ltv, dscr, binding, fits in CASES:
        workbook = workbook_with_numeric_cell(base, "C71", ltv)
        require(changed_cells(base, workbook) == (set() if ltv == "0.8" else {"C71"}),
                "The C71 edit changed other cells")
        if dscr != "2":
            prior = workbook
            workbook = workbook_with_numeric_cell(workbook, "C72", dscr)
            require(changed_cells(prior, workbook) == {"C72"}, "The C72 edit changed other cells")
        path = temp / f"{label}.xlsx"
        path.write_bytes(workbook)
        result, page = audit(path, output_root / label, case=CASE)
        capacity, cash = result["capacity"], result["cash_per_usd_10"]
        if ltv is None:
            require(result["state"] == "PENDING" and result["financial_calculation_run"] is False
                    and capacity is cash is None and "Inputs!C71 | FALTANTE" in page,
                    "A missing LTV was treated as a numeric limit")
            missing += 1
            continue

        maximum = verify_limits(capacity, workbook, ltv, dscr, binding)
        require((REQUESTED <= maximum) == fits and result["preflight"]["pending_items"] == 0
                and f"Límite {binding}" in page and "Préstamo solicitado USD 150,00" in page,
                "The PDF or capacity gate lost the smaller exact limit")
        if label == "at-ltv-limit":
            require(maximum == REQUESTED, "The equality case must be exact")
        if label == "over-ltv-limit":
            require(maximum == Fraction("149.95"), "The LTV boundary must fall below the request by USD 0.05")
        if fits:
            events = tuple((event["date"], event["kind"], event["category"], amount(event["amount"]))
                           for event in cash["events"] if amount(event["amount"]))
            require(result["state"] == "computed_synthetic_project_cash" and not capacity["blockers"]
                    and cash["basis_event_ids"] == ["initial"] and events == EXPECTED_CASH
                    and amount(cash["total_distributions"]) == sum(value for _, kind, _, value in EXPECTED_CASH
                                                                 if kind == "distribution")
                    and amount(cash["unrecovered_after_sale"]) == 0
                    and "Por USD 10 iniciales cobrás USD 12,92 en total." in page,
                    "A different compatible limit changed the fixed-principal cash ledger")
            compatible += 1
        else:
            require(result["state"] == "PENDING" and capacity["blockers"] == [CAPACITY_BLOCKER]
                    and CAPACITY_BLOCKER in result["calculation_blockers"]
                    and cash is result["cash_recovery"] is result["worksheet_exit"] is result["costed_sale_sha256"] is None
                    and "El préstamo solicitado supera la capacidad" in page
                    and "Por USD 10 iniciales cobrás" not in page,
                    "The smaller capacity limit failed to withhold results")
            blocked += 1
        records[label] = dict(ltv=capacity["capacity_limits"]["LTV"], dscr=capacity["capacity_limits"]["DSCR"],
                              maximum=rational(maximum), limit=binding,
                              cash_total=None if cash is None else cash["total_distributions"])
    return dict(status="passed", decision="PENDING", worksheet_cases=len(CASES), compatible_cases=compatible,
                capacity_blocked_cases=blocked, missing_cases=missing, limits=records, page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited workbook and one-page PDF for each case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d119-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
