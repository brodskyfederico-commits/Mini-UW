"""Exercise one-cell worksheet corrections through run and audit."""
from argparse import ArgumentParser
from base64 import b64decode
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree
from zipfile import ZipFile, ZipInfo
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_unified_worksheet_D48 import call
from check_worksheet_sale_costs_D63 import FIXTURE as WORKBOOKS
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.workbooks import MAIN


CASE = ROOT / "templates/synthetic-workbook-intake-case-D117.json"


def workbook_with_dscr(raw, literal=None):
    ref = inspect_synthetic_input_sheet(raw).cells["C72"]["sheet_part"]
    with ZipFile(BytesIO(raw)) as book:
        parts = {name: book.read(name) for name in book.namelist()}
    xml = ElementTree.fromstring(parts[ref])
    ns = {"m": MAIN}
    cell = xml.find("./m:sheetData/m:row/m:c[@r='C72']", ns)
    for child in list(cell):
        cell.remove(child)
    cell.attrib.pop("t", None)
    if literal is not None:
        ElementTree.SubElement(cell, f"{{{MAIN}}}v").text = literal
    parts[ref] = ElementTree.tostring(xml, encoding="utf-8", xml_declaration=True)
    buffer = BytesIO()
    with ZipFile(buffer, "w") as book:
        for name, value in parts.items():
            book.writestr(ZipInfo(name), value)
    return buffer.getvalue()


def changed_cells(before, after):
    old, new = (inspect_synthetic_input_sheet(raw).cells for raw in (before, after))
    return {cell for cell in old.keys() | new.keys() if old.get(cell) != new.get(cell)}


def audit(workbook, output, *, case=CASE):
    created = call("run", case, "--workbook", workbook, "--output", output)
    verified = call("audit", output)
    result = json.loads((output / "results.json").read_bytes())
    pdf = (output / "MiniUW_Resumen.pdf").read_bytes()
    page, = PdfReader(BytesIO(pdf)).pages
    require(created["pdf_sha256"] == verified["pdf_sha256"] == result["pdf_sha256"] == sha(pdf)
            and (output / "Inputs.xlsx").read_bytes() == workbook.read_bytes()
            and result["preflight"]["workbook_sha256"] == sha(workbook.read_bytes())
            and result["decision"] == "PENDING" and result["deployment_enabled"] is False
            and result["real_decisions_enabled"] is False and result["personal_investor_return"] is None,
            "The audit did not bind the exact workbook or preserve the synthetic decision")
    return result, page.extract_text()


def verify(temp, saved_output):
    fixture = json.loads(local_file(ROOT, WORKBOOKS).read_bytes())
    books = {}
    for key in ("missing", "base", "zero"):
        record = fixture["workbooks"][key]
        raw = b64decode(record["xlsx_base64"], validate=True)
        require(sha(raw) == record["sha256"], "Synthetic workbook bytes differ")
        books[key] = raw
    books["two_missing"] = workbook_with_dscr(books["missing"])
    books["partial"] = workbook_with_dscr(books["base"])
    for before, after in (("missing", "base"), ("base", "zero"), ("two_missing", "partial")):
        require(changed_cells(books[before], books[after]) == {"C68"}, "The correction changed other cells")

    results, workbooks = {}, {}
    for key, raw in books.items():
        workbook = temp / f"{key}.xlsx"
        workbook.write_bytes(raw)
        workbooks[key] = workbook
        output = saved_output if key == "base" and saved_output is not None else temp / key
        results[key], text = audit(workbook, output)
        row = results[key]
        if key in ("missing", "two_missing", "partial"):
            expected = {"missing": {"Inputs!C68"}, "two_missing": {"Inputs!C68", "Inputs!C72"},
                        "partial": {"Inputs!C72"}}[key]
            require(row["state"] == "PENDING" and row["financial_calculation_run"] is False
                    and row["cash_per_usd_10"] is row["cash_recovery"] is row["worksheet_exit"] is None
                    and "Retorno por USD 10 PENDING" in text
                    and {item["cell"] for item in row["preflight"]["checklist"] if item["action"] is not None} == expected,
                    "A remaining missing cell leaked results or lost its location")
        else:
            require(row["state"] == "computed_synthetic_project_cash" and row["financial_calculation_run"] is True
                    and row["preflight"]["pending_items"] == 0 and "Por USD 10 iniciales cobrás" in text,
                    "The corrected copy did not reach the financial calculation")

    old, new = results["base"], results["zero"]
    a, b = old["cash_per_usd_10"], new["cash_per_usd_10"]
    sale_a, sale_b = [next(e for e in cash["events"] if e["category"] == "net_sale_distribution") for cash in (a, b)]
    other_a, other_b = ([{key: value for key, value in event.items() if key != "source_ref"}
                        for event in cash["events"] if event["category"] != "net_sale_distribution"] for cash in (a, b))
    require(amount(old["worksheet_exit"]["candidate_price"]) == amount(new["worksheet_exit"]["candidate_price"]) == 400
            and (amount(old["worksheet_exit"]["total_cost"]), amount(new["worksheet_exit"]["total_cost"])) == (30, 10)
            and amount(sale_b["amount"]) - amount(sale_a["amount"]) == Fraction(1, 5)
            and amount(b["total_distributions"]) - amount(a["total_distributions"]) == Fraction(1, 5)
            and a["basis_event_ids"] == b["basis_event_ids"] == ["initial"] and other_a == other_b
            and old["capacity"]["maximum_principal_capacity"] == new["capacity"]["maximum_principal_capacity"]
            and (old["cash_recovery"]["minimum_gross_price_in_cents"], new["cash_recovery"]["minimum_gross_price_in_cents"])
            == (20178, 19169), "Changing only C68 did not isolate its downstream sale and return effect")

    original = temp / "missing"
    call("run", CASE, "--workbook", workbooks["base"], "--output", original, blocked=True)
    require(call("audit", original)["status"] == "verified_source_first"
            and (original / "Inputs.xlsx").read_bytes() == books["missing"], "The correction overwrote the source package")
    (original / "Inputs.xlsx").write_bytes(books["base"])
    call("audit", original, blocked=True)
    call("run", CASE, "--output", temp / "no-workbook", blocked=True)
    return dict(status="passed", decision="PENDING", workbook_cases=len(results), corrections_checked=3,
                pending_cases=3, tampered_workbook_rejected=True, page_count=1,
                pdf_sha256=results["base"]["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited package for the corrected workbook.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d117-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
