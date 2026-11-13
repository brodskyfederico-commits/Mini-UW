"""Replay an explicit synthetic Downside PASS-only policy with the audited workbook."""
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
from check_worksheet_definition_screening_D193 import approvals_unchanged, detail, rows
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_lorena_screening_D194 import fixture
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import CRITERIA_FILE, build_results, encoded, verify_package, write_package
from worksheet_criteria_intake_D194 import PASS_ONLY_POLICY
from worksheet_definition_screening_D193 import OCCUPANCY, RLV
from worksheet_documented_finance_D147 import review_documents
from worksheet_integrated_screening_D181 import compare_pass_only
from worksheet_revision_D128 import snapshot_for_case


def verify(output):
    template, edits, case, _ = fixture()
    revision_label = "SYNTHETIC-D196-criteria"
    edits.update(B18=revision_label, H11="Sin FAIL", H13="Sin FAIL", H9="Sin FAIL")
    policy = dict(policy=PASS_ONLY_POLICY, source_ref="SYNTHETIC-D196-scenario-policy")
    selected = [OCCUPANCY, RLV, "equity_recovered"]
    case["criteria_revision"] = revision_label
    case["criteria_workbook"]["downside_pass_only"] = dict.fromkeys(selected, policy)
    workbook = change_cells(template, edits)
    case["criteria_workbook"]["sha256"] = sha256(workbook).hexdigest()
    current = encoded(snapshot_for_case(case, "SYNTHETIC-D196-current"))
    source = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())

    output.mkdir(parents=True, exist_ok=True)
    package = output / "vigente"
    write_package(encoded(case), package, current_revision_raw=current, criteria_raw=workbook, **source)
    audit = verify_package(package, current_revision_raw=current)
    require(audit["vigencia"] == "VIGENTE" and audit["audit_bot"] == "B16" and audit["simulation_result"] == "PASS"
            and (package / CRITERIA_FILE).read_bytes() == workbook, "PASS-only package did not replay")
    model = json.loads((package / "results.json").read_bytes())
    approvals_unchanged(model)
    require(model["screening"]["run_ready"] is False, "Operational readiness changed")
    require("Dictamen simulado PASS" in pdf_text((package / "MiniUW_Resumen.pdf").read_bytes()), "PASS report missing")
    for key in selected:
        row = rows(model)["Downside", key]
        require(row["state"] == "PASS_CONDITION" and row["pass_only_policy"] == policy
                and row["criterion_record"]["fail_condition"] == {"operator": None, "threshold": None},
                f"Downside {key} acquired an implied FAIL")
    require(len(rows(model)) == 20 and detail(model, "Downside", RLV)["calculation"]["pass_price"] == 2_720_000,
            "PASS-only overlay changed the RLV price search")

    documents = review_documents(case, source["plan_raw"], evidence_raw=source["evidence_raw"], evidence_milestone="D162")

    def cached(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(candidate["local_sources"] == case["local_sources"] and candidate["workbook_sha256"] == case["workbook_sha256"]
                and plan_raw == source["plan_raw"] and evidence_raw == source["evidence_raw"] and evidence_milestone == "D162",
                "Criteria variant changed the audited financial sources")
        return deepcopy(documents)

    def probe(name, expected, *, change=None, cells=None, stale=False):
        revised = deepcopy(case)
        if change:
            change(revised["criteria_workbook"]["downside_pass_only"])
        candidate = change_cells(template, edits | (cells or {}))
        revised["criteria_workbook"]["sha256"] = sha256(candidate).hexdigest()
        snapshot = current if stale else encoded(snapshot_for_case(revised, "SYNTHETIC-D196-probe"))
        result, raw_pdf = build_results(encoded(revised), current_revision_raw=snapshot, criteria_raw=candidate, **source)
        approvals_unchanged(result)
        require(result["simulation_result"] == expected and f"Dictamen simulado {expected}" in pdf_text(raw_pdf)
                and result["scenarios"] == model["scenarios"], f"{name}: decision or cash did not match")
        return result

    def reason(result, metric, blocker, scenario="Downside"):
        row = rows(result)[scenario, metric]
        require(row["state"] == "PENDING" and blocker in row["blockers"], f"{scenario} {metric}: {row}")

    with patch("worksheet_documented_finance_D147.review_documents", cached):
        missed = probe("miss", "PENDING", cells={"G11": "<= 60 %"})
        reason(missed, OCCUPANCY, "downside_pass_not_met_pending_review")
        unconfirmed = probe("unconfirmed", "PENDING", change=lambda rules: rules.pop(OCCUPANCY))
        reason(unconfirmed, OCCUPANCY, "pass_only_policy_unconfirmed_for_D193")
        empty = probe("blank", "PENDING", cells={"H11": ""})
        reason(empty, OCCUPANCY, "downside_pass_only_declaration_missing_or_conflicting")
        conflict = probe("conflict", "PENDING", cells={"H13": "> banda RLV"})
        reason(conflict, RLV, "downside_pass_only_declaration_missing_or_conflicting")
        incompatible = probe("unit", "PENDING", cells={"G11": "<= 75 USD"})
        reason(incompatible, OCCUPANCY, "pass_condition_unit_mismatch")
        outdated = probe("stale", "PENDING", cells={"G11": "<= 60 %"}, stale=True)
        require(not outdated["screening"]["current_criteria_confirmed"], "A historical rule was applied")
        base_missing = probe("base without fail", "PENDING", cells={"F11": "Sin FAIL"})
        reason(base_missing, OCCUPANCY, "pass_only_policy_unconfirmed_for_D193", scenario="Base")
        failed = probe("base fail", "FAIL", cells={"E11": "<= 20 %", "F11": "> 30 %"})
        require(rows(failed)["Base", OCCUPANCY]["state"] == "FAIL_CONDITION", "Base FAIL was suppressed")
        blocked = probe("Base fail and Downside miss", "PENDING",
                        cells={"E11": "<= 20 %", "F11": "> 30 %", "G11": "<= 60 %"})
        reason(blocked, OCCUPANCY, "downside_pass_not_met_pending_review")
        missing_rlv_fail = probe("missing joint RLV hurdle", "PENDING", cells={"H14": "Sin FAIL"},
                                 change=lambda rules: rules.update(equity_TDC=policy))
        require(rows(missing_rlv_fail)["Downside", "equity_TDC"]["state"] == "PASS_CONDITION",
                "Explicit PASS-only equity/TDC was not evaluated")
        reason(missing_rlv_fail, RLV, "metric_value_missing")
        require(detail(missing_rlv_fail, "Downside", RLV)["blocker"] == "SRC-03_incomplete_criterion:equity_TDC",
                "RLV filled a missing joint FAIL hurdle")

        irr = probe("TIR without FAIL", "PENDING", cells={"H15": "Sin FAIL"},
                    change=lambda rules: rules.update(IRR=policy))
        require(rows(irr)["Downside", "IRR"]["state"] == "PASS_CONDITION",
                "Explicit PASS-only TIR failed its verified interval")
        reason(irr, RLV, "metric_value_missing")

    criterion = rows(model)["Downside", "IRR"]["criterion_record"]
    metric = rows(model)["Downside", "IRR"]["metric_record"]
    interval = dict(lower=rational(Fraction(1, 20)), upper=rational(Fraction(3, 50)),
                    lower_closed=True, upper_closed=True)
    criterion["pass_condition"] = dict(operator=">=", threshold=rational(Fraction(11, 200)))
    state, relations, blockers = compare_pass_only(metric, criterion, interval)
    require((state, relations, blockers) == ("PENDING", {"pass_condition": "mixed"},
                ["IRR_enclosure_crosses_criterion_boundary"]), "A crossing TIR interval received a verdict")
    return dict(status="passed", decision="PENDING", simulation_result="PASS", comparison_rows=20,
                verified_pass_only_rows=selected, variants=11, irr_crossing="PENDING",
                base_total_receipts_per_usd10=18.06, downside_total_receipts_per_usd10=6.08,
                cash_preserved=True, workbook_sha256=sha256(workbook).hexdigest(),
                real_decisions_enabled=False, deployment_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d196-") as temporary:
        print(json.dumps(verify(args.output or Path(temporary)), ensure_ascii=False, sort_keys=True))
