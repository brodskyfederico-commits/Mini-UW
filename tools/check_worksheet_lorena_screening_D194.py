"""Verify a synthetic Lorena XLSX through the public D193 run and audit path."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_lorena_criteria_D192 import change_cells
from check_reference_package import require
from check_worksheet_definition_screening_D193 import CASE, CRITERIA, approvals_unchanged, detail, rows
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from miniuw_foundation.debt_service import _fraction as amount
from miniuw_foundation.threshold_rehearsal import ROWS
from miniuw_worksheet_v1 import CRITERIA_FILE, build_results, encoded, main as worksheet_cli, verify_package
from worksheet_criteria_intake_D194 import CONTEXT_FIELDS, LAND_BAND_LITERAL
from worksheet_definition_screening_D193 import OCCUPANCY, RLV
from worksheet_documented_finance_D147 import review_documents
from worksheet_revision_D128 import snapshot_for_case

REVISION = "SYNTHETIC-D194-lorena-v1"
ROOT = CASE.parents[1]
FIXTURE = ROOT / "templates/synthetic-criteria-lorena-D194.xlsx"
CASE_FILE = ROOT / "templates/synthetic-workbook-lorena-screening-D194.json"
CURRENT_FILE = ROOT / "templates/synthetic-workbook-current-revision-D194.json"


def condition_text(condition, unit):
    suffix, scale = {"fraction": ("%", 100), "bps": ("pb", 1), "multiple": ("x", 1), "USD": ("USD", 1)}[unit]
    value = amount(condition["threshold"]) * scale
    literal = f"{float(value):.12f}".rstrip("0").rstrip(".")
    require(Fraction(literal) == value, "Fixture threshold needs exact decimal representation")
    return f'{condition["operator"]} {literal} {suffix}'


def fixture():
    case = json.loads(CASE.read_bytes())
    positions = {metric: i for i, (_, metric) in enumerate(ROWS, 7)}
    edits = {"B18": REVISION, "B19": "SYNTHETIC · ambos umbrales en los dos escenarios"}
    for row in case["rules"]:
        name, metric = row["scenario_id"], row["metric_id"]
        cols = "EF" if name == "Base" else "GH"
        for col, condition in zip(cols, ("pass_condition", "fail_condition"), strict=True):
            edits[col + str(positions[metric])] = (
                LAND_BAND_LITERAL if metric == RLV and condition == "fail_condition"
                else condition_text(row[condition], row["unit"])
            )
    template = CRITERIA.read_bytes()
    workbook = change_cells(template, edits)
    case.update(criteria_revision=REVISION, criteria_workbook=dict(sha256=sha256(workbook).hexdigest()),
                rules=[{key: row[key] for key in CONTEXT_FIELDS} for row in case["rules"]])
    return template, edits, case, workbook


def verify(output):
    template, edits, case, workbook = fixture()
    revision = encoded(snapshot_for_case(case, "SYNTHETIC-D194-current"))
    require(CASE_FILE.read_bytes() == encoded(case) and FIXTURE.read_bytes() == workbook
            and CURRENT_FILE.read_bytes() == revision, "Published fixture drift")
    evidence = output.parent / "D194_Evidence.pdf"
    evidence.write_bytes(shuffled_pdf())
    source = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=evidence.read_bytes())
    arguments = ["miniuw_worksheet_v1.py", "run", str(CASE_FILE), "--criteria", str(FIXTURE),
                 "--workbook", str(BOOKS["Base"]), "--downside-workbook", str(BOOKS["Downside"]),
                 "--plan", str(PLAN), "--evidence", str(evidence), "--current-revision", str(CURRENT_FILE),
                 "--output", str(output)]
    with patch("sys.argv", arguments), patch("sys.stdout"):
        require(worksheet_cli() == 0, "Public run command rejected the XLSX")
    audit = verify_package(output, current_revision_raw=revision)
    model = json.loads((output / "results.json").read_bytes())
    approvals_unchanged(model)
    require(audit["vigencia"] == "VIGENTE" and audit["audit_bot"] == "B16" and audit["simulation_result"] == "PASS"
            and (output / CRITERIA_FILE).read_bytes() == workbook, "Version-bound replay did not verify")
    report = (output / "MiniUW_Resumen.pdf").read_bytes()
    page = pdf_text(report)
    require(all(label in page for label in ("Dictamen simulado PASS", "Decisión real PENDING",
                "32,66% [PASS] / 69,37% [PASS]", "3200000 / 7350000", "2720000 / 4140000", "18,06", "6,08")),
            "The one-page report lost occupancy, RLV or USD 10")
    comparisons = rows(model)
    require(len(comparisons) == 20 and all(row["state"] == "PASS_CONDITION" for row in comparisons.values()),
            "Workbook rules did not drive all comparisons")
    trace = model["screening"]["criteria_workbook"]
    for name, cells in (("Base", ("E11", "F13")), ("Downside", ("G11", "H13"))):
        require(comparisons[name, OCCUPANCY]["criteria_workbook_cells"]["pass"]["cell"] == cells[0]
                and comparisons[name, RLV]["criteria_workbook_cells"]["fail"] == dict(cell=cells[1], literal=LAND_BAND_LITERAL),
                "Excel cell lineage lost")
        row = comparisons[name, RLV]
        index = int(row["criterion_locator"].rsplit("/", 1)[-1])
        rule = trace["rules"][index]
        require(rule["fail_condition"]["threshold"] == detail(model, name, RLV)["fail_boundary_multiple"],
                "Derived rule did not use the recalculated RLV band")

    documents = review_documents(case, source["plan_raw"], evidence_raw=source["evidence_raw"], evidence_milestone="D162")

    def cached(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(candidate["local_sources"] == case["local_sources"] and candidate["workbook_sha256"] == case["workbook_sha256"]
                and plan_raw == source["plan_raw"] and evidence_raw == source["evidence_raw"] and evidence_milestone == "D162",
                "A criteria-only variant modified an audited source")
        return deepcopy(documents)

    def run(book, expected, *, bind=True, revise=True):
        updated = deepcopy(case)
        if bind:
            updated["criteria_workbook"]["sha256"] = sha256(book).hexdigest() if book is not None else None
        snapshot = encoded(snapshot_for_case(updated, "SYNTHETIC-D194-probe")) if revise else revision
        result, pdf = build_results(encoded(updated), current_revision_raw=snapshot, criteria_raw=book, **source)
        approvals_unchanged(result)
        require(result["simulation_result"] == expected and f"Dictamen simulado {expected}" in pdf_text(pdf),
                f"Expected {expected}, got {result['simulation_result']}")
        require(result["scenarios"] == model["scenarios"], "A criteria-only change altered cash or debt")
        return result

    with patch("worksheet_documented_finance_D147.review_documents", cached):
        def variant(**changes):
            return change_cells(template, edits | changes)
        missing = run(variant(F11=""), "PENDING")
        require("fail_condition_missing" in rows(missing)["Base", OCCUPANCY]["blockers"], "Blank became a default")
        fail = run(variant(E11="<= 20 %", F11="> 30 %"), "FAIL")
        require(rows(fail)["Base", OCCUPANCY]["state"] == "FAIL_CONDITION", "Excel edit did not change the decision")
        rlv = run(variant(F13=""), "PENDING")
        require("fail_condition_missing" in rows(rlv)["Base", RLV]["blockers"], "RLV defaulted an absent rule")
        revised = run(variant(E14="<= 83 %", F14="> 85 %"), "PENDING")
        require(detail(revised, "Base", RLV)["calculation"]["pass_price"] == 640_000
                and rows(revised)["Base", RLV]["state"] == "BAND", "Excel did not recalculate the RLV price search")
        unit = run(variant(G11="<= 75 USD"), "PENDING")
        require("pass_condition_unit_mismatch" in rows(unit)["Downside", OCCUPANCY]["blockers"], "Units were coerced")
        older = run(variant(E11="<= 20 %"), "PENDING", bind=False)
        require("criteria_workbook_hash_mismatch" in older["screening"]["simulation_blockers"], "Unexpected XLSX bytes accepted")
        snapshot = run(variant(E11="<= 20 %"), "PENDING", revise=False)
        require(not snapshot["screening"]["current_criteria_confirmed"], "An old revision authorized new criteria")
        absent = run(None, "PENDING", bind=False)
        require("criteria_workbook_missing" in absent["screening"]["simulation_blockers"], "Missing Excel inherited JSON rules")
        blank = run(change_cells(template, {"B18": REVISION}), "PENDING")
        require(all(row["criterion_locator"] is None and "pass_condition_missing" in row["blockers"]
                    for row in rows(blank).values()), "Historical thresholds were activated")
        mislabeled = run(variant(B18="SYNTHETIC-D194-expired"), "PENDING")
        require("criteria_workbook_revision_mismatch" in mislabeled["screening"]["simulation_blockers"],
                "An XLSX from another criteria revision was activated")
        no_fail = run(variant(H11="Sin FAIL"), "PENDING")
        require("pass_only_policy_unconfirmed_for_D193" in rows(no_fail)["Downside", OCCUPANCY]["blockers"],
                "The intake chose a policy for Downside without a FAIL hurdle")
        bad_formula = run(change_cells(template, edits, formula="E11"), "PENDING")
        require(any(reason.startswith("criteria_workbook_invalid:") for reason in bad_formula["screening"]["simulation_blockers"]),
                "Formula used as source value")

        missing_inputs, raw_pdf = build_results(encoded(case), current_revision_raw=revision, criteria_raw=workbook,
                                                **(source | {"downside_workbook_raw": None}))
        require(missing_inputs["simulation_result"] == "PENDING"
                and missing_inputs["scenarios"]["Downside"]["cash_per_usd_10"] is None
                and missing_inputs["scenarios"]["Base"]["cash_per_usd_10"] == model["scenarios"]["Base"]["cash_per_usd_10"]
                and "Downside | Caja PENDING" in pdf_text(raw_pdf),
                "A valid criteria workbook concealed a missing financial scenario")

    summary = {}
    for name, view in model["scenarios"].items():
        cash = view["cash_per_usd_10"]
        summary[name] = dict(occupancy_percent=round(float(amount(detail(model, name, OCCUPANCY)["value"]) * 100), 2),
                             rlv=detail(model, name, RLV)["calculation"]["pass_price"],
                             additional=round(float(amount(cash["total_contributions"]) - 10), 2),
                             received=round(float(amount(cash["total_distributions"])), 2),
                             unrecovered=round(float(amount(cash["unrecovered_after_sale"])), 2),
                             last_receipt=view["project_calendar"]["sale_date"])
    return dict(status="passed", comparison_rows=20, variants=13, simulation_result=audit["simulation_result"],
                decision="PENDING", real_decisions_enabled=False, deployment_enabled=False, pdf_pages=1,
                workbook_sha256=trace["observed_sha256"], pdf_sha256=sha256(report).hexdigest(), scenarios=summary)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d194-") as temporary:
        print(json.dumps(verify(args.output or Path(temporary) / "Expediente"), ensure_ascii=False, sort_keys=True))
