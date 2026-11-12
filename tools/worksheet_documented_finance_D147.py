"""Connect verified plan scope and GC quotes to the D146 calculation."""
from fractions import Fraction

from miniuw_foundation.debt_service import rational
from worksheet_local_sources_D127 import check, day, number, object_or_empty, review_local_sources, synthetic_id
from worksheet_native_mapping_D139 import SCENARIOS
from worksheet_plan_set_D135 import CROPPED_PROFILE, read_plan_set


POLICY = "SYNTHETIC-D147-plan-and-vertical-quote-binding"
AREA_SCOPE = "entire_building_gross_floor_area"
SF_TO_M2 = Fraction("0.09290304")


def review_documents(case, plan_raw, *, evidence_raw=None, evidence_milestone=None):
    source = object_or_empty(case.get("local_sources"))
    hashes = object_or_empty(case.get("workbook_sha256"))
    plan = read_plan_set(plan_raw, source.get("plan_pdf"), profile=CROPPED_PROFILE)
    inputs = object_or_empty(case.get("rent_inputs"))
    if evidence_milestone is not None:
        from worksheet_evidence_pdf_D156 import pdf_document_sources, record_pdf_evidence
        include_construction_pdf = evidence_milestone != "D156"
        source, inventory, pages = pdf_document_sources(source, evidence_raw, inputs.get("deal_id"),
                                                        include_construction=include_construction_pdf,
                                                        scanned=evidence_milestone in ("D158", "D159", "D160", "D161"),
                                                        oriented=evidence_milestone in ("D159", "D160", "D161"),
                                                        allow_rgb=evidence_milestone in ("D160", "D161"),
                                                        allow_jpeg=evidence_milestone == "D161")
    review = review_local_sources(source, hashes, pdf_plan=plan, gc_scenarios=SCENARIOS)
    if evidence_milestone is not None:
        record_pdf_evidence(review, inventory, pages, include_construction=include_construction_pdf)
    as_of = inputs.get("as_of_UTC")
    official = review["bots"]["B11"]
    if not official["blockers"] and (not isinstance(as_of, str) or day(as_of.split("T", 1)[0]) != day(official["as_of"])):
        blocker = "official_snapshot_date_does_not_match_case_as_of"
        review["bots"]["B11"] = check(blocker, archived_observation=official)
        review["blockers"].append(f"B11:{blocker}")
        review["state"] = "PENDING"
    review["finance_binding_source"] = source.get("finance_binding")
    return review


def bind_development(name, development, review):
    bots = review["bots"]
    plan, gc = bots["B07"], bots["B09"]
    if bots["B03"]["documents"]["plan_pdf"]["blockers"] or plan["blockers"] or gc["blockers"]:
        return check("B09:verified_plan_and_gc_area_required_for_financing")
    declaration = object_or_empty(review["finance_binding_source"])
    if (declaration.get("policy") != POLICY or declaration.get("area_scope") != AREA_SCOPE
            or declaration.get("plan_ref") != plan["plan_ref"] or not synthetic_id(declaration.get("source_ref"))):
        return check("B09:financial_plan_scope_unconfirmed")
    quote = bots["B08"]["scenario_quotes"][name]
    if quote["blockers"]:
        return check("B08:verified_vertical_quote_required_for_financing")
    plan_m2 = number(plan["value"])
    model_gsf = development["vertical_quantity"] if development["vertical_basis"] == "$/GSF" else None
    evidence = dict(source_ref=declaration["source_ref"], plan_ref=plan["plan_ref"], area_scope=AREA_SCOPE,
                    verified_area_m2=rational(plan_m2), verified_area_gsf=rational(plan_m2 / SF_TO_M2),
                    area_source_sha256=plan["readings"][0]["source_sha256"], model_area_gsf=model_gsf,
                    model_cost=development["vertical_cost"], model_quote_cells=development["cell_sources"], gc_quote=quote)
    if model_gsf is not None and number(model_gsf) * SF_TO_M2 != plan_m2:
        return check("B09:model_gsf_conflicts_with_verified_plan_area", **evidence)
    if number(development["vertical_cost"]) != number(quote["value"]):
        return check("B09:model_vertical_cost_conflicts_with_gc_quote", **evidence)
    return check(**evidence)


def record_pipeline(case_sha256, scenarios, mapping, revision, screening, pdf, review):
    from worksheet_screening_pilot_D120 import pilot_pipeline

    scoped = {name: dict(source_blockers=workbook["blockers"] if "workbook_sha256" not in workbook else [],
                         preflight=dict(checklist=[dict(cell=row["value_cell"], action=row["blockers"]) for row in workbook["rows"]]),
                         cash_per_usd_10=scenarios[name]["cash_per_usd_10"])
              for name, workbook in mapping["scenarios"].items()}
    result = pilot_pipeline(case_sha256, scoped, screening, pdf, review, "check_worksheet_documented_finance_D147.py")
    stages = {stage["dot"]: stage for stage in result["stages"]}
    stages["D01"]["current_revision"] = revision["state"]
    stages["D02"]["native_mapping_state"] = mapping["state"]
    stages["D03"]["finance_bindings"] = {name: view.get("document_financial_binding", {}).get("state", "PENDING")
                                         for name, view in scenarios.items()}
    stages["D05"]["motor"] = "D146"
    stages["D07"]["version_tests_run_per_case"] = False
    return result
