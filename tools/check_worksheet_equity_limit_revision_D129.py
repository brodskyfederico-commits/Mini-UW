"""Recheck the Downside equity/TDC limit across two designated revisions."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_current_chain_D128 import CASE as PRIOR_CASE, CURRENT as PRIOR_REFERENCE, run_case
from check_worksheet_screening_pilot_D120 import check_cash_and_metrics, condition, replace_rule
from miniuw_worksheet_v1 import read_package


CASE = ROOT / "templates/synthetic-workbook-current-chain-D129.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D129.json"
METRIC = ("Downside", "equity_TDC")
LIMIT = Fraction(45, 100)
REVISION_BLOCKERS = ["criteria_revision_mismatch", "investment_rules_fingerprint_mismatch"]


def comparisons(result):
    return {(row["scenario_id"], row["metric_id"]): row for row in result["screening"]["comparisons"]}


def verify(temp, saved_output):
    prior_case = json.loads(PRIOR_CASE.read_bytes())
    current_case = json.loads(CASE.read_bytes())
    expected = replace_rule(prior_case, "equity_TDC", "Downside", pass_condition=condition("<=", LIMIT),
                            fail_condition=condition(">", LIMIT))
    require(current_case == expected | {"criteria_revision": "SYNTHETIC-D129-investment-r3"},
            "The new case changed something besides the Downside equity limit and criteria revision")
    old_fingerprints = json.loads(PRIOR_REFERENCE.read_bytes())["fingerprints"]
    new_fingerprints = json.loads(CURRENT.read_bytes())["fingerprints"]
    require({role for role in old_fingerprints if old_fingerprints[role] != new_fingerprints[role]} == {"investment_rules"},
            "The new reference changed another source fingerprint")

    old_path = temp / "prior"
    new_path = saved_output or temp / "current"
    prior = run_case(PRIOR_CASE, old_path, PRIOR_REFERENCE)
    before = read_package(old_path)
    current = run_case(CASE, new_path, CURRENT)
    check_cash_and_metrics(current)
    require(current["scenarios"] == prior["scenarios"],
            "A rule-only revision changed the worksheets, exact cash or dates")
    old, new = comparisons(prior), comparisons(current)
    old_row, new_row = old[METRIC], new[METRIC]
    require(old.keys() == new.keys() and len(new) == 20
            and {key for key in old if old[key] != new[key]} == {METRIC}
            and old_row["metric_record"] == new_row["metric_record"]
            and amount(new_row["metric_record"]["value"]) == Fraction(5, 11)
            and amount(old_row["criterion_record"]["pass_condition"]["threshold"]) == Fraction(1, 2)
            and amount(new_row["criterion_record"]["pass_condition"]["threshold"]) == LIMIT
            and old_row["state"] == "PASS_CONDITION" and new_row["state"] == "FAIL_CONDITION"
            and not current["local_review"]["blockers"] and not current["revision_review"]["blockers"],
            "The new failure was not isolated to the supplied Downside equity rule")
    page, = PdfReader(new_path / "MiniUW_Resumen.pdf").pages
    require("Equity / TDC | Base 40,00% (PASS) | Downside 45,45% (FAIL)" in page.extract_text(),
            "The one-page result lost the changed comparison")

    current_audit = call("audit", new_path, "--current-revision", CURRENT)
    historical = call("audit", old_path, "--current-revision", CURRENT)
    require(prior["simulation_result"] == "PASS" and current["simulation_result"] == "FAIL"
            and current_audit["vigencia"] == "VIGENTE" and current_audit["simulation_result"] == "FAIL"
            and historical["status"] == "verified_source_first" and historical["vigencia"] == "HISTORICO"
            and historical["archived_simulation_result"] == "PASS" and historical["simulation_result"] == "PENDING"
            and historical["current_revision"] == current_audit["current_revision"] and read_package(old_path) == before,
            "The previous PASS remained current or the audit changed the original package")

    for case_path, pin, name, worksheet_state in (
        (PRIOR_CASE, CURRENT, "prior-under-current", "PASS"),
        (CASE, PRIOR_REFERENCE, "current-under-prior", "FAIL"),
    ):
        mismatch = run_case(case_path, temp / name, pin)
        require(mismatch["simulation_result"] == "PENDING"
                and mismatch["screening"]["worksheet_simulation_result"] == worksheet_state
                and mismatch["revision_review"]["blockers"] == REVISION_BLOCKERS
                and mismatch["scenarios"] == current["scenarios"],
                "A mismatched revision reused a worksheet verdict or changed the available cash")
    return dict(status="passed", decision="PENDING", full_workbook_cases=4, current_simulation="FAIL",
                prior_current_simulation="PENDING", prior_archived_simulation="PASS", exact_cash_preserved=True,
                pdf_sha256=current["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited current revision.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d129-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
