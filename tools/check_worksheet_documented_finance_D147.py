"""Replay the documented D146 pilot with both workbook and documentary gates."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_construction_financing_D146 import (
    BOOKS as DEBT_BOOKS, CASE as DEBT_CASE, CURRENT as DEBT_CURRENT, case_for as debt_case,
    workbook_values as debt_values,
)
from check_worksheet_development_inputs_D143 import not_applicable
from check_worksheet_plan_cropped_set_D138 import CASE as DOCUMENT_CASE, PLAN, cropped_pdf
from check_worksheet_rental_inputs_D140 import run
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import PLAN_FILE, WORKBOOK_DOCUMENTED_FINANCING_SCHEMA, encoded
from worksheet_documented_finance_D147 import AREA_SCOPE, POLICY, SF_TO_M2
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-documented-finance-D147.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D147.json"
BOOKS = {"Base": DEBT_BOOKS["Base"], "Downside": ROOT / "templates/synthetic-documented-finance-downside-D147.xlsx"}


def workbook_values(name, catalog):
    values = debt_values(name, catalog)
    if name == "Downside":
        values.update(C35={"value": "232.2576"}, C36="missing")
    return values


def edit_document(case, name, edit):
    envelope = case["local_sources"]["documents"][name]
    edit(envelope["document"])
    envelope["sha256"] = sha(encoded(envelope["document"]))


def case_for(books, catalog, plan_raw):
    case = debt_case(books, catalog)
    case.update(schema=WORKBOOK_DOCUMENTED_FINANCING_SCHEMA, criteria_revision="SYNTHETIC-D147-criteria-r1")
    case["rent_inputs"]["development"]["scenarios"]["Downside"]["plan_gsf"].update(
        state="declared", value=rational(1000 / SF_TO_M2), source_ref="SYNTHETIC-D147-verified-plan-gross-area")
    not_applicable(case, "Downside", "INPUT_C36")
    local = json.loads(DOCUMENT_CASE.read_bytes())["local_sources"]
    case["local_sources"] = local
    local.update(revision="SYNTHETIC-D147-input-r1", workbook_sha256=case["workbook_sha256"].copy(),
                 finance_binding=dict(policy=POLICY, source_ref="SYNTHETIC-D147-GBA-and-GC-scope",
                                      plan_ref=local["plan_pdf"]["plan_ref"], area_scope=AREA_SCOPE))
    local["plan_pdf"]["sha256"] = sha(plan_raw)
    local["official_request"]["as_of"] = "2027-03-01"
    edit_document(case, "official_snapshot", lambda doc: doc.update(revision=local["revision"], valid_through="2027-03-31"))

    def gc_quotes(doc):
        doc.pop("budget")
        doc.update(revision=local["revision"], budget_by_scenario={name: dict(
            value=rational(value), currency="USD", scope="vertical_building_excluding_parking_and_site",
            locator=f"GC/{name}/obra vertical") for name, value in (("Base", 2340000), ("Downside", 2500000))})

    edit_document(case, "gc_budget", gc_quotes)
    return case


def cash_amounts(view):
    cash = view["cash_per_usd_10"]
    if cash is None:
        return None
    return cash | dict(events=[{key: value for key, value in event.items() if key != "source_ref"} for event in cash["events"]])


def verify(temp, output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in SCENARIOS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    raw = PLAN.read_bytes()
    require(all(BOOKS[name].read_bytes() == source for name, source in originals.items()), "Fixture drift")
    require(CASE.read_bytes() == encoded(case_for(originals, catalog, raw)), "Case source drift")
    baseline = run(DEBT_CASE, DEBT_BOOKS, DEBT_CURRENT, temp / "D146")
    matching = run(CASE, BOOKS, CURRENT, output, plan=PLAN)
    review = matching["local_review"]
    bots = review["bots"]
    require(matching["simulation_result"] == "FAIL" and not review["blockers"] and not matching["revision_review"]["blockers"],
            "Valid documents and a valid synthetic FAIL did not reach the integrated output")
    stages = matching["pipeline"]["stages"]
    require([stage["dot"] for stage in stages] == [f"D{i:02}" for i in range(1, 8)] and
            sorted(bot for stage in stages for bot in stage["bots"]) == [f"B{i:02}" for i in range(1, 18)]
            and stages[4]["motor"] == "D146" and stages[5]["pdf_sha256"] == matching["pdf_sha256"]
            and not stages[6]["version_tests_run_per_case"], "The audit stages lost a contract or the D146 binding")
    for bot, sheet in (("B05", "A101"), ("B06", "A601")):
        reading = bots[bot]
        require(reading["sheet"] == sheet and reading["source_sha256"] == sha(raw)
                and set(reading["observations"]) == {"text", "ocr"}
                and all(amount(item["value"]) == 1000 for item in reading["observations"].values()),
                "The plan evidence was replaced by declared area")
    require(bots["B10"]["access"] == "local_snapshot" and bots["B11"]["value"] == 4
            and bots["B11"]["as_of"] == "2027-03-01" and amount(bots["B09"]["difference"]) == 0,
            "Official snapshot or area reconciliation was skipped")
    for name in SCENARIOS:
        view = matching["scenarios"][name]
        binding = view["document_financial_binding"]
        budget = view["construction_budget"]
        require(binding["state"] == "checked_synthetic" and binding["model_cost"] == binding["gc_quote"]["value"]
                and budget["document_financial_binding_sha256"] == sha(encoded(binding))
                and view["construction_financing"]["budget_ref"] == f"sha256:{sha(encoded(budget))}"
                and cash_amounts(view) == cash_amounts(baseline["scenarios"][name]),
                "Verified quote did not reach the D146 budget, or the comparable USD 10 flows changed")
    require(amount(review["financial_bindings"]["Downside"]["model_area_gsf"]) * SF_TO_M2 == 1000,
            "The verified plan GSF did not bind to the financial scenario")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "FAIL"
            and (output / PLAN_FILE).read_bytes() == raw, "B16 could not replay the saved sources")

    def variant(name, *, patch=None, edits=None, plan_raw=raw, supplied=True, stale=False):
        books = originals.copy()
        if edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        case = case_for(books, catalog, plan_raw)
        if patch:
            patch(case)
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, source in books.items():
            paths[scenario].write_bytes(source)
        case_path, revision, plan_path = (temp / f"{name}-{suffix}" for suffix in ("case.json", "revision.json", "plan.pdf"))
        case_path.write_bytes(encoded(case))
        revision.write_bytes(CURRENT.read_bytes() if stale else encoded(snapshot_for_case(case, f"SYNTHETIC-D147-{name}")))
        plan_path.write_bytes(plan_raw)
        return run(case_path, paths, revision, temp / name, plan=plan_path if supplied else None)

    def relaxed(case):
        for rule in case["rules"]:
            if rule["scenario_id"] == "Downside":
                for key in ("pass_condition", "fail_condition"):
                    rule[key]["threshold"] = rational(Fraction(3, 5))

    passing = variant("pass-with-current-rule", patch=relaxed)
    require(passing["simulation_result"] == "PASS" and passing["scenarios"] == matching["scenarios"],
            "Valid change of synthetic criterion rewrote cash or remained blocked")

    def pending(name, *, affected=(), reason, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING"
                and any(reason in blocker for blocker in result["screening"]["simulation_blockers"]), f"Missing PENDING reason for {name}")
        for scenario in SCENARIOS:
            expected = None if scenario in affected else cash_amounts(matching["scenarios"][scenario])
            require(cash_amounts(result["scenarios"][scenario]) == expected, f"Incorrect flow availability for {name}, {scenario}")
        return result

    pending("missing-plan", supplied=False, affected=SCENARIOS, reason="verified_plan_and_gc_area_required_for_financing")
    pending("crop-hides-area", plan_raw=cropped_pdf("A601", (20, 20, 280, 205)), affected=SCENARIOS,
            reason="required_sheet_area_unverified")
    pending("missing-gc", patch=lambda case: case["local_sources"]["documents"].pop("gc_budget"), affected=SCENARIOS,
            reason="verified_plan_and_gc_area_required_for_financing")
    pending("gc-area-conflict", patch=lambda case: edit_document(case, "gc_budget", lambda doc: doc["area"].update(value=rational(1001))),
            affected=SCENARIOS, reason="GC_area_conflict")
    pending("quote-missing", patch=lambda case: edit_document(case, "gc_budget", lambda doc: doc["budget_by_scenario"].pop("Downside")),
            affected=("Downside",), reason="verified_vertical_quote_required_for_financing")
    pending("quote-mismatch", affected=("Downside",), reason="model_vertical_cost_conflicts_with_gc_quote",
            patch=lambda case: edit_document(case, "gc_budget", lambda doc: doc["budget_by_scenario"]["Downside"].update(value=rational(2600000))))
    pending("model-gsf-mismatch", affected=("Downside",), reason="model_gsf_conflicts_with_verified_plan_area",
            patch=lambda case: case["rent_inputs"]["development"]["scenarios"]["Downside"]["plan_gsf"].update(value=rational(25000)))
    pending("official-missing", patch=lambda case: case["local_sources"]["documents"].pop("official_snapshot"),
            reason="current_authorized_local_snapshot_required")
    pending("wrong-official-date", patch=lambda case: case["local_sources"]["official_request"].update(as_of="2027-02-28"),
            reason="official_snapshot_date_does_not_match_case_as_of")
    pending("criterion-missing", patch=lambda case: case["rules"].pop(), reason="criterion_record_missing")
    stale = pending("stale-scope", stale=True, reason="plan_and_gc_documents_fingerprint_mismatch",
                    patch=lambda case: case["local_sources"]["finance_binding"].update(source_ref="SYNTHETIC-D147-new-scope-reference"))
    require(stale["local_review"]["state"] == "checked_synthetic", "Stale designation changed the underlying documents")
    pending("missing-financial-input", edits={"C52": "missing"}, affected=("Downside",),
            reason="construction_financing_field_unconfirmed_or_out_of_range:C52")

    tampered = temp / "tampered"
    copytree(output, tampered)
    replacement = cropped_pdf("A101", (20, 20, 640, 230))
    (tampered / PLAN_FILE).write_bytes(replacement)
    manifest = json.loads((tampered / "package.json").read_bytes())
    next(row for row in manifest["files"] if row["path"] == PLAN_FILE).update(bytes=len(replacement), sha256=sha(replacement))
    (tampered / "package.json").write_bytes(encoded(manifest))
    call("audit", tampered, "--current-revision", CURRENT, blocked=True)
    return dict(status="passed", decision="PENDING", full_workbook_cases=14, pending_cases=12,
                dots=7, bots=17, pdf_sha256=matching["pdf_sha256"], page_count=1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d147-") as temp:
        print(json.dumps(verify(Path(temp), args.output or Path(temp) / "matching"), sort_keys=True))


if __name__ == "__main__":
    main()
