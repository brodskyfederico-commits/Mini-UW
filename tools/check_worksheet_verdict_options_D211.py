"""Exercise alternative verdict precedence and Downside RLV scope on synthetic cash."""
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
from miniuw_worksheet_v1 import build_results, encoded, verify_package, write_package
from worksheet_criteria_intake_D194 import PASS_ONLY_POLICY
from worksheet_definition_screening_D193 import OCCUPANCY, RLV
from worksheet_documented_finance_D147 import review_documents
from worksheet_integrated_screening_D181 import compare_pass_only
from worksheet_revision_D128 import snapshot_for_case


KEY = ("Downside", RLV)
MISS = f"Downside:{OCCUPANCY}:downside_pass_not_met_pending_review"
RLV_MISS = f"Downside:{RLV}:downside_pass_not_met_pending_review"
BAND = "intermediate_band_pending_professional_review"
PASS_MISS = "downside_pass_not_met_pending_review"


def preview(screening, scope, *, applicability_confirmed=False):
    """Evaluate candidate verdicts in this checker; leave the worksheet output intact."""
    comparisons = screening["comparisons"]
    rlv = next(row for row in comparisons if (row["scenario_id"], row["metric_id"]) == KEY)
    blockers = set(screening["simulation_blockers"])
    require(scope in ("required", "excluded", "unconfirmed"), "Explicit Downside RLV scope required")
    active = comparisons
    rlv_state = rlv["state"]
    if scope == "excluded" and applicability_confirmed:
        # Exclude only this comparison, using an explicit synthetic declaration.
        # The Base RLV and all other rows keep their original conditions.
        active = [row for row in comparisons if row is not rlv]
        blockers = {b for b in blockers if not b.startswith(f"{KEY[0]}:{KEY[1]}:")}
        # A BAND can be shared by more than one metric.
        if rlv["state"] == "BAND" and not any(row["state"] == "BAND" for row in active):
            blockers.discard(BAND)
        rlv_state = "N/A"
    elif scope != "required":
        blockers.add("Downside:RLV:applicability_unconfirmed")
        rlv_state = "PENDING"

    base_fail = any(row["scenario_id"] == "Base" and row["state"] == "FAIL_CONDITION" and not row["blockers"]
                    for row in active)
    any_fail = any(row["state"] == "FAIL_CONDITION" and not row["blockers"] for row in active)
    confirmed_misses = {
        f'Downside:{row["metric_id"]}:{PASS_MISS}'
        for row in active
        if row["scenario_id"] == "Downside" and row["state"] == "PENDING"
        and row.get("pass_only_policy") and row["blockers"] == [PASS_MISS]
    }
    # A hard blocker and an unclassified PENDING row both keep the case pending.
    for row in active:
        if row["state"] == "BAND":
            blockers.add(BAND)
        elif row["state"] in ("PENDING", "CONFLICT") and not row["blockers"]:
            blockers.add(f'{row["scenario_id"]}:{row["metric_id"]}:comparison_unresolved')
        blockers.update(f'{row["scenario_id"]}:{row["metric_id"]}:{reason}' for reason in row["blockers"])
    current = "PENDING" if blockers else ("FAIL" if any_fail else "PASS")
    material = blockers - confirmed_misses
    candidate = "PENDING" if material else ("FAIL" if base_fail else current)
    return dict(current_rule=current, base_fail_first=candidate, downside_rlv=rlv_state,
                confirmed_downside_misses=sorted(blockers & confirmed_misses), unresolved_blockers=sorted(material))


def verify(output):
    template, edits, case, _ = fixture()
    revision = "SYNTHETIC-D211-verdict-options"
    policy = dict(policy=PASS_ONLY_POLICY, source_ref="SYNTHETIC-D211-downside-pass-only")
    case["criteria_revision"] = revision
    case["criteria_workbook"]["downside_pass_only"] = dict.fromkeys((OCCUPANCY, RLV), policy)
    edits.update(B18=revision, H11="Sin FAIL", H13="Sin FAIL")
    workbook = change_cells(template, edits)
    case["criteria_workbook"]["sha256"] = sha256(workbook).hexdigest()
    snapshot = encoded(snapshot_for_case(case, "SYNTHETIC-D211-current"))
    source = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())
    output.mkdir(parents=True, exist_ok=True)
    package = output / "control"
    write_package(encoded(case), package, current_revision_raw=snapshot, criteria_raw=workbook, **source)
    audit = verify_package(package, current_revision_raw=snapshot)
    reference = json.loads((package / "results.json").read_bytes())
    approvals_unchanged(reference)
    require(audit["vigencia"] == "VIGENTE" and audit["audit_bot"] == "B16"
            and reference["simulation_result"] == "PASS", "B16 did not reproduce the control PASS")
    require(all(scenario["cash_per_usd_10"]["events"] for scenario in reference["scenarios"].values()),
            "Reference cash events must be available")
    require(detail(reference, "Downside", RLV)["calculation"]["pass_price"] == 2_720_000,
            "The applicable Downside RLV was not calculated")
    original_cash = {name: view["cash_per_usd_10"] for name,view in reference["scenarios"].items()}
    signatures = {name: sha256(encoded(cash)).hexdigest() for name,cash in original_cash.items()}

    checked = review_documents(case, source["plan_raw"], evidence_raw=source["evidence_raw"], evidence_milestone="D162")

    def reuse(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(candidate["local_sources"] == case["local_sources"] and candidate["workbook_sha256"] == case["workbook_sha256"]
                and plan_raw == source["plan_raw"] and evidence_raw == source["evidence_raw"]
                and evidence_milestone == "D162", "Criteria probes must preserve the audited financial inputs")
        return deepcopy(checked)

    def probe(label, changes, expected, *, stale=False):
        touched = deepcopy(case)
        book = change_cells(template, edits | changes)
        touched["criteria_workbook"]["sha256"] = sha256(book).hexdigest()
        raw = snapshot if stale else encoded(snapshot_for_case(touched, "SYNTHETIC-D211-probe"))
        model, pdf = build_results(encoded(touched), current_revision_raw=raw, criteria_raw=book, **source)
        approvals_unchanged(model)
        require(model["simulation_result"] == expected and f"Dictamen simulado {expected}" in pdf_text(pdf),
                f"{label}: unexpected current worksheet result")
        require(model["scenarios"] == reference["scenarios"], f"{label}: a criteria edit changed financial output")
        return model

    def evaluate(label, model, scope, current, alternate, *, exclusion=False):
        result = preview(model["screening"], scope, applicability_confirmed=exclusion)
        require((result["current_rule"], result["base_fail_first"]) == (current, alternate),
                f"{label}: {result}")
        if scope == "required":
            require(current == model["simulation_result"], f"{label}: current rule differs from the engine")
        return dict(case=label, scope=scope, **result)

    base_fail = {"E11": "<= 20 %", "F11": "> 30 %"}
    records = [evaluate("Todos cumplen", reference, "required", "PASS", "PASS"),
               evaluate("RLV Downside excluido con respaldo", reference, "excluded", "PASS", "PASS", exclusion=True),
               evaluate("Exclusión sin respaldo", reference, "excluded", "PENDING", "PENDING"),
               evaluate("Aplicabilidad del RLV sin resolver", reference, "unconfirmed", "PENDING", "PENDING")]
    variants = {}
    with patch("worksheet_documented_finance_D147.review_documents", reuse):
        for label, changes, current, alternate, expected_blocker in (
            ("FAIL en Base", base_fail, "FAIL", "FAIL", None),
            ("Banda intermedia en Base", {"E11": "<= 25 %"}, "PENDING", "PENDING", BAND),
            ("Downside incumple PASS", {"G11": "<= 60 %"}, "PENDING", "PENDING", MISS),
            ("Base FAIL y Downside incumple PASS", base_fail | {"G11": "<= 60 %"}, "PENDING", "FAIL", MISS),
            ("Base FAIL y falta el umbral PASS de Downside", base_fail | {"G11": ""}, "PENDING", "PENDING", None),
            ("Falta el umbral FAIL de Base", {"F11": ""}, "PENDING", "PENDING", None),
        ):
            model = probe(label, changes, current)
            variants[label] = model
            record = evaluate(label, model, "required", current, alternate)
            if expected_blocker:
                require(expected_blocker in model["screening"]["simulation_blockers"], f"{label}: incorrect cause")
            records.append(record)
        stale = probe("Revisión desactualizada", {"G11": "<= 60 %"}, "PENDING", stale=True)
        require(not stale["screening"]["current_criteria_confirmed"], "Stale criteria became current")
        records.append(evaluate("Revisión desactualizada", stale, "required", "PENDING", "PENDING"))

        missing = probe("RLV Downside sin umbral", {"G13": ""}, "PENDING")
        records.append(evaluate("RLV aplicable y falta umbral", missing, "required", "PENDING", "PENDING"))
        records.append(evaluate("RLV sin umbral con exclusión documentada", missing, "excluded",
                                "PASS", "PASS", exclusion=True))
        records.append(evaluate("RLV sin umbral con exclusión sin respaldo", missing, "excluded",
                                "PENDING", "PENDING"))
        mixed = probe("Faltan el RLV y la ocupación de Downside", {"G13": "", "G11": ""}, "PENDING")
        records.append(evaluate("Exclusión de RLV conserva otro faltante", mixed, "excluded",
                                "PENDING", "PENDING", exclusion=True))
        base_rlv = probe("Falta RLV Base", {"E13": ""}, "PENDING")
        records.append(evaluate("Exclusión Downside conserva RLV Base", base_rlv, "excluded",
                                "PENDING", "PENDING", exclusion=True))
        unresolved = probe("Falta evidencia de una métrica necesaria para RLV", {"H14": ""}, "PENDING")
        require(detail(unresolved, "Downside", RLV).get("calculation") is None, "An incomplete RLV produced a price")
        records.append(evaluate("RLV aplicable con una dependencia incompleta", unresolved, "required",
                                "PENDING", "PENDING"))

    # Compare real thresholds around the audited ratio without changing purchase or assumptions.
    # The canonical RLV row has a contract-bound PASS threshold, so these probes
    # vary the scalar comparison in a local copy of the review only.
    control_row = rows(reference)["Downside", RLV]
    value = Fraction(control_row["metric_record"]["value"]["numerator"]) / Fraction(
        control_row["metric_record"]["value"]["denominator"])
    for name, offset, expected_state in (
            ("RLV exactamente en su umbral", Fraction(), "PASS_CONDITION"),
            ("RLV excede umbral", Fraction(-1, 10000), "PENDING"),
    ):
        clone = deepcopy(reference)
        row = rows(clone)["Downside", RLV]
        row["criterion_record"]["pass_condition"]["threshold"] = rational(value + offset)
        row["state"], _, row["blockers"] = compare_pass_only(row["metric_record"], row["criterion_record"], None)
        require(row["state"] == expected_state, f"{name}: RLV comparator differs")
        if row["state"] == "PENDING":
            clone["screening"]["simulation_blockers"].append(RLV_MISS)
            clone["simulation_result"] = "PENDING"
        expected = "PASS" if row["state"] == "PASS_CONDITION" else "PENDING"
        records.append(evaluate(name, clone, "required", expected, expected))
        records.append(evaluate(name + " · N/A documentado", clone, "excluded", "PASS", "PASS", exclusion=True))
    base_failure = variants["FAIL en Base"]
    records.append(evaluate("Base FAIL y RLV Downside sin aplicabilidad", base_failure, "unconfirmed", "PENDING", "PENDING"))
    failure_and_rlv_miss = deepcopy(base_failure)
    missed = rows(clone)["Downside", RLV]
    require(missed["state"] == "PENDING", "The RLV miss fixture is not pending")
    active_rlv = rows(failure_and_rlv_miss)["Downside", RLV]
    active_rlv.update(missed)
    failure_and_rlv_miss["screening"]["simulation_blockers"].append(RLV_MISS)
    failure_and_rlv_miss["simulation_result"] = "PENDING"
    records.append(evaluate("Base FAIL y RLV aplicable incumple PASS", failure_and_rlv_miss, "required", "PENDING", "FAIL"))
    records.append(evaluate("Base FAIL y RLV Downside N/A documentado", failure_and_rlv_miss, "excluded",
                            "FAIL", "FAIL", exclusion=True))
    for blocker in ("B03:source_missing", "B12:criteria_revision_unconfirmed"):
        with_material = deepcopy(failure_and_rlv_miss["screening"])
        with_material["simulation_blockers"].append(blocker)
        result = preview(with_material, "required")
        require(result["current_rule"] == result["base_fail_first"] == "PENDING"
                and blocker in result["unresolved_blockers"], f"{blocker}: a critical gate was suppressed")
        records.append(dict(case=blocker, scope="required", **result))
    require({name: sha256(encoded(cash)).hexdigest() for name,cash in original_cash.items()} == signatures,
            "The preview modified dated cash")
    results = dict(status="passed", decision="PENDING", policy_adopted=False,
                   deployment_enabled=False, dated_cash_preserved=True, audited_cash_sha256=signatures,
                   cash_per_usd_10=original_cash, cases=records)
    (output / "verification.json").write_bytes(encoded(results))
    return dict(status=results["status"], cases=len(records), decision=results["decision"], cash_sha256=signatures)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d211-") as temp:
        print(json.dumps(verify(args.output or Path(temp)), ensure_ascii=False, sort_keys=True))
