"""Replay the original-layout 55-field mapping through the synthetic pilot."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_plan_cropped_set_D138 import CASE as PRIOR_CASE, PLAN
from check_worksheet_screening_pilot_D120 import BOOKS as PRIOR_BOOKS, check_cash_and_metrics
from inputsheet_fixture import native_workbook
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import DOWNSIDE_WORKBOOK_FILE, WORKBOOK_FILE, WORKBOOK_NATIVE_MAPPING_CHAIN_SCHEMA, encoded
from worksheet_native_mapping_D139 import MATRIX, PILOT_CELLS, mapping_catalog, matrix_csv
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-native-mapping-D139.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D139.json"
BOOKS = {name: ROOT / f"templates/synthetic-native-{name.lower()}-D139.xlsx" for name in PRIOR_BOOKS}


def example_values(name, catalog):
    original = inspect_synthetic_input_sheet(PRIOR_BOOKS[name].read_bytes()).cells
    values = {cell: {"text": original[cell]["literal"]} for cell in ("B3", "E3")}
    for index, row in enumerate(catalog, 1):
        cell = row["value_cell"].split("!")[1]
        role = row["role"]
        if cell in PILOT_CELLS:
            values[cell] = {"value": original[cell]["literal"]}
        elif role == "basis_selector_not_a_monetary_value":
            values[cell] = {"text": "PER UNIT" if cell == "C7" else "TOTAL"}
        elif role == "reference_evidence_not_arithmetic":
            values[cell] = {"text": "SYNTHETIC-D139-rent-comps"}
        elif role == "scenario_request_not_executable_text":
            values[cell] = {"text": f"SYNTHETIC review request for {cell}"}
        else:
            unit = row["literal_unit"]
            literal = "0" if cell == "C13" else f"0.{index:03d}" if unit.startswith("decimal") else str(index)
            values[cell] = {"value": literal}
    return values


def case_for(workbooks, catalog):
    case = json.loads(PRIOR_CASE.read_bytes())
    case["schema"] = WORKBOOK_NATIVE_MAPPING_CHAIN_SCHEMA
    hashes = {name: sha(raw) for name, raw in workbooks.items()}
    case["workbook_sha256"] = hashes
    case["local_sources"]["workbook_sha256"] = hashes
    for role in ("yield_inputs", "funding_inputs", "occupancy_inputs", "return_inputs"):
        for name, digest in hashes.items():
            case[role][name]["workbook_sha256"] = digest
    case["native_mapping"] = dict(catalog_sha256=sha(encoded(catalog)), scenarios={
        name: dict(workbook_sha256=digest, source_ref=f"SYNTHETIC-D139-{name}-field-review",
                   confirmed_fields=[row["field_id"] for row in catalog], not_applicable_fields=[])
        for name, digest in hashes.items()})
    return case


def run(case_path, books, revision, output):
    status = call("run", case_path, "--workbook", books["Base"], "--downside-workbook", books["Downside"],
                  "--current-revision", revision, "--plan", PLAN, "--output", output)
    result = json.loads((output / "results.json").read_bytes())
    pdf = output / "MiniUW_Resumen.pdf"
    page, = PdfReader(pdf).pages
    require(result["decision"] == "PENDING" and not result["deployment_enabled"] and not result["real_decisions_enabled"]
            and result["personal_investor_return"] is None and result["simulation_result"] == status["simulation_result"]
            and sha(pdf.read_bytes()) == status["pdf_sha256"] == result["pdf_sha256"]
            and f"Simulación PASS/FAIL  |  {result['simulation_result']}" in page.extract_text()
            and (output / WORKBOOK_FILE).read_bytes() == books["Base"].read_bytes()
            and (output / DOWNSIDE_WORKBOOK_FILE).read_bytes() == books["Downside"].read_bytes(),
            "The full pilot did not retain its decision guard and exact source evidence")
    return result


def rows_for(result, name):
    return {row["field_id"]: row for row in result["native_mapping_review"]["scenarios"][name]["rows"]}


def verify(temp, saved_output):
    catalog = mapping_catalog()
    require((ROOT / MATRIX).read_bytes() == matrix_csv(catalog), "The review matrix differs from the checked mapping")
    require({row["synthetic_pilot_parameter"] for row in catalog if row["synthetic_pilot_parameter"]}
            == set(PILOT_CELLS.values()) and all(row["real_status"] == "PENDING" for row in catalog),
            "A documented candidate was promoted to a confirmed real calculation")
    original = {name: path.read_bytes() for name, path in BOOKS.items()}
    values = {name: example_values(name, catalog) for name in BOOKS}
    require(all(original[name] == native_workbook(values[name]) for name in BOOKS),
            "A synthetic workbook does not reproduce from the original layout")
    output = saved_output or temp / "matching"
    matching = run(CASE, BOOKS, CURRENT, output)
    check_cash_and_metrics(matching)
    require(matching["simulation_result"] == "FAIL" and not matching["native_mapping_review"]["blockers"]
            and not matching["native_mapping_review"]["real_mapping_confirmed"]
            and not matching["revision_review"]["blockers"], "The fully reviewed synthetic fixture did not run")
    for name in BOOKS:
        rows = rows_for(matching, name)
        require(len(rows) == 55 and all(row["state"] == "CONFIRMED_SYNTHETIC"
                and row["source_literal"] == next(iter(values[name][row["value_cell"].split("!")[1]].values()))
                for row in rows.values()), "A field did not retain its exact cell and literal")
        require(amount(rows["INPUT_C13"]["value"]) == 0
                and rows["INPUT_C80"]["value"] == "SYNTHETIC review request for C80"
                and not rows["INPUT_C80"]["synthetic_pilot_parameter"], "Zero or alternative text was misinterpreted")
    audited = call("audit", output, "--current-revision", CURRENT)
    require(audited["audit_bot"] == "B16" and audited["vigencia"] == "VIGENTE"
            and audited["simulation_result"] == "FAIL", "Audit could not replay the 55-field mapping")

    def variant(name, *, cell_edits=None, unconfirmed=(), omitted=(), drop_rule=False, stale_confirmation=False):
        books = original.copy()
        if cell_edits is not None:
            books["Downside"] = native_workbook(values["Downside"] | cell_edits)
        case = case_for(books, catalog)
        review = case["native_mapping"]["scenarios"]["Downside"]
        for field in (*unconfirmed, *omitted):
            review["confirmed_fields"].remove(field)
        review["not_applicable_fields"] = list(omitted)
        if drop_rule:
            case["rules"] = [r for r in case["rules"] if (r["scenario_id"], r["metric_id"]) != ("Downside", "equity_cash_in")]
        if stale_confirmation:
            review["workbook_sha256"] = sha(original["Downside"])
        paths = {}
        for scenario, raw in books.items():
            paths[scenario] = temp / f"{name}-{scenario}.xlsx"
            paths[scenario].write_bytes(raw)
        case_path = temp / f"{name}-case.json"
        case_path.write_bytes(encoded(case))
        revision = temp / f"{name}-revision.json"
        revision.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D139-{name}")))
        result = run(case_path, paths, revision, temp / name)
        require(not result["revision_review"]["blockers"], "The probe did not isolate the tested blocker")
        return result

    def pending(name, *, field=None, reason=None, cash_available=True, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and result["scenarios"]["Base"]["cash_per_usd_10"] == matching["scenarios"]["Base"]["cash_per_usd_10"]
                and (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == cash_available,
                "Missing confirmation released a verdict or misrepresented available cash")
        if field is not None:
            require(rows_for(result, "Downside")[field]["blockers"] == [reason], "The field lost its pending reason")
        return result

    pending("unconfirmed-comps", unconfirmed=("INPUT_C12",), field="INPUT_C12", reason="field_confirmation_missing")
    pending("unconfirmed-dscr", unconfirmed=("INPUT_C72",), field="INPUT_C72", reason="field_confirmation_missing",
            cash_available=False)
    pending("blank-confirmed-rent", cell_edits={"C8": "missing"}, field="INPUT_C8", reason="confirmed_field_value_missing")
    formula = pending("cached-rent-formula", cell_edits={"C8": {"formula": "5+5", "value": "10"}},
                      field="INPUT_C8", reason="formula_or_error_not_resolved")
    require(rows_for(formula, "Downside")["INPUT_C8"]["cached_value"] == "10", "Formula evidence was lost")
    no_rule = pending("missing-investment-rule", drop_rule=True)
    require(not no_rule["native_mapping_review"]["blockers"]
            and any("equity_cash_in:Downside:" in reason for reason in no_rule["screening"]["simulation_blockers"]),
            "A field confirmation substituted for an investment rule")
    not_applicable = variant("explicit-not-applicable", cell_edits={"C16": "missing", "C80": "missing"},
                             omitted=("INPUT_C16", "INPUT_C80"))
    require(not_applicable["simulation_result"] == "FAIL" and all(rows_for(not_applicable, "Downside")[field]["state"]
            == "NOT_APPLICABLE" for field in ("INPUT_C16", "INPUT_C80")), "Explicit non-applicability was lost")
    pending("required-not-applicable", cell_edits={"C13": "missing"}, omitted=("INPUT_C13",), field="INPUT_C13",
            reason="incompatible_not_applicable_declaration")
    stale = pending("confirmation-from-other-workbook", cell_edits={"C8": {"value": "22"}},
                    stale_confirmation=True, cash_available=False)
    require("worksheet_confirmation_unbound" in stale["native_mapping_review"]["scenarios"]["Downside"]["blockers"],
            "A changed workbook reused the previous confirmation")
    corrected = variant("exit-cap-updated", cell_edits={"C67": values["Base"]["C67"]})
    require(corrected["scenarios"]["Downside"]["cash_per_usd_10"] == matching["scenarios"]["Base"]["cash_per_usd_10"],
            "An explicitly bound exit cap did not recalculate the affected cash")
    return dict(status="passed", decision="PENDING", full_workbook_cases=10, pending_cases=7,
                mapped_fields=55, scenarios_verified=2, direct_calculation_fields=len(PILOT_CELLS),
                pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited synthetic 55-field case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d139-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
