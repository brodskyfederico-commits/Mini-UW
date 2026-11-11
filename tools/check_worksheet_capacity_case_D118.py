"""Recalculate capacity from a corrected C72 and gate the USD 10 return."""
from argparse import ArgumentParser
from base64 import b64decode
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_worksheet_intake_case_D117 import audit, changed_cells, workbook_with_dscr
from check_worksheet_sale_costs_D63 import FIXTURE as WORKBOOKS
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_plan_refinance_D109 import CAPACITY_BLOCKER


CASE = ROOT / "templates/synthetic-workbook-capacity-case-D118.json"


def verify(temp, saved_output):
    archived = json.loads(local_file(ROOT, WORKBOOKS).read_bytes())["workbooks"]["base"]
    raw = b64decode(archived["xlsx_base64"], validate=True)
    require(sha(raw) == archived["sha256"], "The synthetic source workbook changed")
    blank = workbook_with_dscr(raw)
    if saved_output is not None:
        saved_output.mkdir(exist_ok=True)
    output_root = saved_output or temp
    observed = {}
    for label, dscr in (("blank", None), ("compatible", "2"), ("above-capacity", "4")):
        book = blank if dscr is None else workbook_with_dscr(raw, dscr)
        if dscr is not None:
            require(changed_cells(blank, book) == {"C72"}, "The DSCR correction changed other cells")
        path = temp / f"{label}.xlsx"
        path.write_bytes(book)
        result, page = audit(path, output_root / label, case=CASE)
        checklist = result["preflight"]
        capacity = result["capacity"]
        cash = result["cash_per_usd_10"]
        if dscr is None:
            require(result["state"] == "PENDING" and not result["financial_calculation_run"]
                    and capacity is cash is None and "Inputs!C72 | FALTANTE" in page,
                    "A blank DSCR received capacity or return")
            continue

        # Archived bank NOI USD 2000 and three monthly amortization payments at 1%.
        minimum = Fraction(dscr)
        payment_per_unit = Fraction(1, 100) / (1 - Fraction(101, 100) ** -3)
        dscr_capacity = Fraction(2000) / (minimum * 12 * payment_per_unit)
        dscr_cell, = (row for row in checklist["checklist"] if row["cell"] == "Inputs!C72")
        dscr_claim, = (row["claim"] for row in capacity["lineage"] if row["locator"] == "/parameters/minimum_dscr")
        require(checklist["pending_items"] == 0 and amount(dscr_cell["value"]) == minimum
                and result["financial_calculation_run"] and amount(capacity["selected_principal"]) == 150
                and amount(capacity["maximum_principal_capacity"]) == dscr_capacity
                and capacity["capacity_limits"]["DSCR"] == capacity["maximum_principal_capacity"]
                and amount(capacity["capacity_limits"]["LTV"]) == 400 and capacity["binding_limit_ids"] == ["DSCR"]
                and amount(dscr_claim["value"]) == minimum
                and dscr_claim["source_ref"] == f"sha256:{sha(book)}#xlsx:sheet:Inputs:cell:C72"
                and "Préstamo solicitado USD 150,00" in page,
                "The revised C72 did not reach the exact capacity calculation")
        observed[label] = capacity["maximum_principal_capacity"]
        if label == "compatible":
            require(result["state"] == "computed_synthetic_project_cash" and not capacity["blockers"]
                    and cash["basis_event_ids"] == ["initial"]
                    and amount(cash["total_distributions"]) == Fraction(78297181, 6060200)
                    and amount(cash["unrecovered_after_sale"]) == 0
                    and "Por USD 10 iniciales cobrás USD 12,92 en total." in page
                    and "Capacidad USD 245,08" in page,
                    "The capacity-cleared worksheet did not reproduce the USD 10 cash")
        else:
            require(result["state"] == "PENDING" and capacity["blockers"] == [CAPACITY_BLOCKER]
                    and CAPACITY_BLOCKER in result["calculation_blockers"]
                    and cash is result["cash_recovery"] is result["worksheet_exit"] is result["costed_sale_sha256"] is None
                    and "Capacidad USD 122,54" in page and "El préstamo solicitado supera la capacidad" in page
                    and "Por USD 10 iniciales cobrás" not in page,
                    "The over-capacity worksheet emitted a closing, cash result or fallback")
    return dict(status="passed", decision="PENDING", worksheet_cases=3, corrections_checked=2,
                capacity_blocked_cases=1, capacity=observed, page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited blank, compatible and blocked cases.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d118-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
