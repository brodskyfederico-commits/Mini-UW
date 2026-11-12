"""One source-bound synthetic worksheet entry point for both sale paths."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys

from check_operating_replay_D20 import ROOT, local_file, require
from check_worksheet_recovery_page_D44 import render_run
from check_worksheet_refinance_D45 import FIXTURE as REFINANCE, replay
from check_worksheet_sale_recovery_D43 import FIXTURE as SALE, worksheet_bindings
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.drafts import canonical
from miniuw_foundation.expense_cash_detail import _exact, _json
from miniuw_foundation.intake import MAX_BYTES as MAX_WORKBOOK_BYTES
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_settled_output import assemble_worksheet_settled_output


CASE_SCHEMA = "miniuw.synthetic-unified-worksheet-case.v1"
DIAGNOSTIC_CASE_SCHEMA = "miniuw.synthetic-unified-worksheet-case.v2"
PARTICIPATION_CASE_SCHEMA = "miniuw.synthetic-unified-worksheet-case.v3"
INVESTOR_CASE_SCHEMA = "miniuw.synthetic-unified-worksheet-case.v4"
PARTICIPATION_SCHEMAS = (PARTICIPATION_CASE_SCHEMA, INVESTOR_CASE_SCHEMA)
SCENARIO_INVESTOR_SCHEMA = "miniuw.synthetic-investor-scenarios.v1"
SCENARIO_RECOVERY_SCHEMA = "miniuw.synthetic-investor-scenarios.v2"
SCENARIO_DISCOUNTED_RECOVERY_SCHEMA = "miniuw.synthetic-investor-scenarios.v3"
SCENARIO_SENSITIVITY_SCHEMA = "miniuw.synthetic-investor-scenarios.v4"
SCENARIO_SALE_GAP_SCHEMA = "miniuw.synthetic-investor-scenarios.v5"
SCENARIO_AVAILABILITY_SCHEMA = "miniuw.synthetic-investor-scenarios.v6"
PLAN_REFINANCE_REQUEST_SCHEMA = "miniuw.synthetic-plan-refinance-request.v1"
PLAN_DISCOUNT_COMPARISON_SCHEMA = "miniuw.synthetic-plan-discount-comparison.v1"
PLAN_DISCOUNT_RECOVERY_SCHEMA = "miniuw.synthetic-plan-discount-comparison.v2"
WORKBOOK_INTAKE_SCHEMA = "miniuw.synthetic-workbook-intake-case.v1"
WORKBOOK_CAPACITY_SCHEMA = "miniuw.synthetic-workbook-intake-case.v2"
WORKBOOK_PILOT_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v1"
WORKBOOK_EXTENDED_PILOT_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v2"
WORKBOOK_IRR_PILOT_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v3"
WORKBOOK_YIELD_PILOT_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v4"
WORKBOOK_EQUITY_PILOT_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v5"
WORKBOOK_OCCUPANCY_PILOT_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v6"
WORKBOOK_COMPLETE_PILOT_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v7"
WORKBOOK_LOCAL_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v8"
WORKBOOK_CURRENT_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v9"
WORKBOOK_PLAN_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v10"
WORKBOOK_SCAN_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v11"
WORKBOOK_MIXED_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v12"
WORKBOOK_OVERLAY_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v13"
WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v14"
WORKBOOK_PLAN_SET_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v15"
WORKBOOK_ROTATED_PLAN_SET_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v16"
WORKBOOK_DUAL_ROTATED_PLAN_SET_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v17"
WORKBOOK_CROPPED_PLAN_SET_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v18"
WORKBOOK_NATIVE_MAPPING_CHAIN_SCHEMA = "miniuw.synthetic-workbook-screening-pilot.v19"
WORKBOOK_RENTAL_INPUTS_SCHEMA = "miniuw.synthetic-native-rental-inputs.v1"
WORKBOOK_COMMERCIAL_INPUTS_SCHEMA = "miniuw.synthetic-native-rental-inputs.v2"
WORKBOOK_PDF_CHAIN_SCHEMAS = (WORKBOOK_PLAN_CHAIN_SCHEMA, WORKBOOK_SCAN_CHAIN_SCHEMA,
                              WORKBOOK_MIXED_CHAIN_SCHEMA, WORKBOOK_OVERLAY_CHAIN_SCHEMA,
                              WORKBOOK_ROTATED_OVERLAY_CHAIN_SCHEMA, WORKBOOK_PLAN_SET_CHAIN_SCHEMA,
                              WORKBOOK_ROTATED_PLAN_SET_CHAIN_SCHEMA, WORKBOOK_DUAL_ROTATED_PLAN_SET_CHAIN_SCHEMA,
                              WORKBOOK_CROPPED_PLAN_SET_CHAIN_SCHEMA, WORKBOOK_NATIVE_MAPPING_CHAIN_SCHEMA)
WORKBOOK_CURRENT_CHAIN_SCHEMAS = (WORKBOOK_CURRENT_CHAIN_SCHEMA, *WORKBOOK_PDF_CHAIN_SCHEMAS)
WORKBOOK_LOCAL_CHAIN_SCHEMAS = (WORKBOOK_LOCAL_CHAIN_SCHEMA, *WORKBOOK_CURRENT_CHAIN_SCHEMAS)
WORKBOOK_RETURN_PILOT_SCHEMAS = (WORKBOOK_COMPLETE_PILOT_SCHEMA, *WORKBOOK_LOCAL_CHAIN_SCHEMAS)
WORKBOOK_OPERATING_PILOT_SCHEMAS = (WORKBOOK_OCCUPANCY_PILOT_SCHEMA, *WORKBOOK_RETURN_PILOT_SCHEMAS)
WORKBOOK_FUNDING_PILOT_SCHEMAS = (WORKBOOK_EQUITY_PILOT_SCHEMA, *WORKBOOK_OPERATING_PILOT_SCHEMAS)
PACKAGE_SCHEMA = "miniuw.synthetic-unified-worksheet-package.v1"
COSTED_SALE = "templates/synthetic-worksheet-sale-costs-D63.json"
COSTED_PROFILE = "with_refinance_worksheet_sale"
ARCHIVES = {"without_refinance": SALE, "with_refinance": REFINANCE, COSTED_PROFILE: COSTED_SALE}
FILES = frozenset({"case.json", "results.json", "MiniUW_Resumen.pdf", "package.json"})
WORKBOOK_FILE = "Inputs.xlsx"
DOWNSIDE_WORKBOOK_FILE = "Downside_Inputs.xlsx"
CURRENT_REVISION_FILE = "current_revision.json"
PLAN_FILE = "Plan.pdf"
MAX_CURRENT_REVISION_BYTES = 16 * 1024
MAX_PLAN_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_EXTENDED_PILOT_BYTES = 32 * 1024


def read_case(case):
    fields = {"schema", "profile", "archive_case", "archive_sha256", "monthly_discount_rate"}
    schema = case.get("schema") if isinstance(case, dict) else None
    if schema in PARTICIPATION_SCHEMAS:
        fields.add("allocation_terms_sha256")
    if schema == INVESTOR_CASE_SCHEMA:
        fields.add("illustrative_investor_id")
    _exact(case, fields)
    require(case["schema"] in (CASE_SCHEMA, DIAGNOSTIC_CASE_SCHEMA, *PARTICIPATION_SCHEMAS) and isinstance(case["profile"], str)
            and case["profile"] in ARCHIVES and isinstance(case["archive_case"], str),
            "An explicit supported synthetic worksheet profile and case are required")
    require(case["schema"] == CASE_SCHEMA or case["profile"] == COSTED_PROFILE,
            "Versioned costed sale requires worksheet valuation and costs")
    if schema in PARTICIPATION_SCHEMAS:
        require(isinstance(case["allocation_terms_sha256"], str), "A synthetic participation terms hash is required")
    if schema == INVESTOR_CASE_SCHEMA:
        investor = case["illustrative_investor_id"]
        require(isinstance(investor, str) and investor.startswith("SYNTHETIC-"),
                "An explicit synthetic participant ID is required")
    archive_path = ARCHIVES[case["profile"]]
    archive_raw = local_file(ROOT, archive_path).read_bytes()
    require(case["archive_sha256"] == sha(archive_raw), "Case archive bytes differ")
    bindings, rates = worksheet_bindings()
    rate = _fraction(case["monthly_discount_rate"])
    require(rate in rates, "An explicit rate from the synthetic monthly grid is required")
    return case, archive_path, archive_raw, bindings, rate


def build_results(raw, *, workbook_raw=None, downside_workbook_raw=None, current_revision_raw=None, plan_raw=None):
    case = _json(raw, MAX_EXTENDED_PILOT_BYTES)
    schema = case.get("schema") if isinstance(case, dict) else None
    require(current_revision_raw is None or schema in (*WORKBOOK_CURRENT_CHAIN_SCHEMAS, WORKBOOK_RENTAL_INPUTS_SCHEMA,
                                                       WORKBOOK_COMMERCIAL_INPUTS_SCHEMA),
            "The designated revision belongs to the current local chain schema")
    require(plan_raw is None or schema in WORKBOOK_PDF_CHAIN_SCHEMAS and len(plan_raw) <= MAX_PLAN_BYTES,
            "A bounded PDF plan belongs to the plan chain schema")
    if schema in (WORKBOOK_RENTAL_INPUTS_SCHEMA, WORKBOOK_COMMERCIAL_INPUTS_SCHEMA):
        from worksheet_rental_inputs_D140 import build_rental_case
        return build_rental_case(case, sha(raw), {"Base": workbook_raw, "Downside": downside_workbook_raw},
                                 current_revision_raw, include_commercial=schema == WORKBOOK_COMMERCIAL_INPUTS_SCHEMA)
    yield_metrics = schema in (WORKBOOK_YIELD_PILOT_SCHEMA, *WORKBOOK_FUNDING_PILOT_SCHEMAS)
    interval_irr = schema == WORKBOOK_IRR_PILOT_SCHEMA or yield_metrics
    extended = schema == WORKBOOK_EXTENDED_PILOT_SCHEMA or interval_irr
    require(extended or len(raw) <= 4096, "The worksheet case exceeds its schema size limit")
    if extended or schema == WORKBOOK_PILOT_SCHEMA:
        from worksheet_screening_pilot_D120 import build_pilot
        return build_pilot(case, sha(raw), {"Base": workbook_raw, "Downside": downside_workbook_raw},
                           extended=extended, interval_irr=interval_irr, yield_metrics=yield_metrics,
                           current_revision_raw=current_revision_raw, plan_raw=plan_raw)
    require(downside_workbook_raw is None, "This case schema does not accept a Downside workbook")
    if isinstance(case, dict) and case.get("schema") in (WORKBOOK_INTAKE_SCHEMA, WORKBOOK_CAPACITY_SCHEMA):
        from worksheet_intake_case_D117 import build_intake_case
        require(workbook_raw is not None, "The intake case requires the exact synthetic Inputs workbook")
        return build_intake_case(case, sha(raw), workbook_raw, capacity_first=case["schema"] == WORKBOOK_CAPACITY_SCHEMA)
    require(workbook_raw is None, "This case schema does not accept an additional workbook")
    if isinstance(case, dict) and case.get("schema") == SCENARIO_INVESTOR_SCHEMA:
        from worksheet_investor_scenarios_D75 import build_scenarios
        return build_scenarios(case, sha(raw))
    if isinstance(case, dict) and case.get("schema") == SCENARIO_RECOVERY_SCHEMA:
        from worksheet_scenario_recovery_D82 import build_recovery
        return build_recovery(case, sha(raw))
    if isinstance(case, dict) and case.get("schema") == SCENARIO_DISCOUNTED_RECOVERY_SCHEMA:
        from worksheet_discounted_recovery_D83 import build_discounted_recovery
        return build_discounted_recovery(case, sha(raw))
    if isinstance(case, dict) and case.get("schema") == SCENARIO_SENSITIVITY_SCHEMA:
        from worksheet_sale_rate_grid_D84 import build_rate_grid
        return build_rate_grid(case, sha(raw))
    if isinstance(case, dict) and case.get("schema") == SCENARIO_SALE_GAP_SCHEMA:
        from worksheet_sale_gap_D85 import build_sale_gap
        return build_sale_gap(case, sha(raw))
    if isinstance(case, dict) and case.get("schema") == SCENARIO_AVAILABILITY_SCHEMA:
        from worksheet_investor_scenarios_D75 import build_scenarios
        return build_scenarios(case, sha(raw), allow_pending=True)
    if isinstance(case, dict) and case.get("schema") == PLAN_REFINANCE_REQUEST_SCHEMA:
        from worksheet_plan_refinance_D109 import build_request
        return build_request(case, sha(raw))
    if isinstance(case, dict) and case.get("schema") in (PLAN_DISCOUNT_COMPARISON_SCHEMA, PLAN_DISCOUNT_RECOVERY_SCHEMA):
        from worksheet_plan_discount_D112 import build_discount_comparison
        return build_discount_comparison(case, sha(raw), include_recovery=case["schema"] == PLAN_DISCOUNT_RECOVERY_SCHEMA)
    case, archive_path, archive_raw, bindings, rate = read_case(case)
    key = case["archive_case"]
    profile = case["profile"]
    refinance = capacity = None
    if profile == "without_refinance":
        require(key in bindings, "Case does not belong to the sale-only profile")
        binding = bindings[key]
        source = local_file(ROOT, binding["path"]).read_text(encoding="utf-8")
        require(sha(source.encode()) == binding["sha256"], "Worksheet source bytes differ")
        run = assemble_worksheet_settled_output(source.encode())
        result = run.payload
        pdf, page = render_run(source, run, rate)
        project = result["current_project_return_story"]
        risk = result["current_risk_observations"]
        recovery = page["cash_recovery"]
        if recovery is not None:
            recovery = {key: value for key, value in recovery.items() if key != "observations"} | recovery["observations"][0]
        worksheet = result["worksheet_reconciliation"]
        blockers = result["blockers"]
        context = result["context"]
        as_of = result["evaluated_as_of_UTC"]
        provenance = dict(workbook_sha256=worksheet["source_hashes"]["workbook_sha256"],
                          worksheet_source_sha256=sha(source.encode()), worksheet_run_sha256=run.sha256,
                          recovery_run_sha256=page["recovery_sha256"])
    elif profile == COSTED_PROFILE:
        from worksheet_costed_case_D65 import build_costed_case
        result, pdf = build_costed_case(key, rate, diagnostics=case["schema"] != CASE_SCHEMA,
                                        terms_hash=case.get("allocation_terms_sha256"),
                                        investor_id=case.get("illustrative_investor_id"))
        project, risk, recovery = result["return_story"], result["risk"], result["cash_recovery"]
        worksheet, capacity, refinance = result["worksheet"], result["capacity"], result["refinance"]
        blockers = dict(worksheet=worksheet["blockers"], sale=result["sale_blockers"])
        context, as_of = result["context"], result["evaluated_as_of_UTC"]
        provenance = dict(workbook_sha256=worksheet["workbook_sha256"],
                          costed_sale_sha256=result["costed_sale_sha256"],
                          guarded_return_run_sha256=None if capacity is None else capacity["return_run_sha256"])
    else:
        require(key in _json(archive_raw, MAX_FILE_BYTES)["cases"], "Case does not belong to the refinance profile")
        _, result, pdf = next(replay(key, rate))
        project = result["return_story"]
        risk = result["risk"]
        recovery = result["cash_recovery"]
        if recovery is not None:
            recovery = recovery | {"currency": project["currency"]}
        worksheet = result["worksheet"]
        capacity = result["capacity"]
        refinance = result["refinance"]
        blockers = dict(worksheet=worksheet["blockers"],
                        capacity=[] if capacity is None else capacity["blockers"],
                        calculation=[] if capacity is None else capacity["return_blockers"])
        context = result["context"]
        as_of = result["evaluated_as_of_UTC"]
        provenance = dict(workbook_sha256=worksheet["workbook_sha256"],
                          base_evidence_sha256=result["base_evidence_sha256"],
                          guarded_return_run_sha256=None if capacity is None else capacity["return_run_sha256"])
    require(result["decision"] == "PENDING", "Unexpected case decision")
    if project is None:
        require(risk is recovery is refinance is None, "Blocked project exposed cash")
    else:
        require(risk is not None and recovery is not None and project["equity_level"] == "aggregate_project_equity",
                "Complete project lost its reconciled recovery or cash risk")
    normalized = dict(profile=profile, archive_case=key, context=context, evaluated_as_of_UTC=as_of,
                      state="PENDING" if project is None else "computed_synthetic_project_cash",
                      decision="PENDING", scope="synthetic_project_equity", monthly_discount_rate=str(rate),
                      blockers=blockers, worksheet=worksheet, capacity=capacity, refinance=refinance,
                      project=project, risk=risk, cash_recovery=recovery,
                      provenance=provenance | dict(archive_path=archive_path, archive_sha256=sha(archive_raw),
                                                   case_sha256=sha(raw)),
                      pdf_sha256=sha(pdf), page_count=1, personal_investor_return=None,
                      deployment_enabled=False, real_decisions_enabled=False)
    if profile == COSTED_PROFILE:
        normalized["worksheet_exit"] = result["worksheet_exit"]
    if case["schema"] in PARTICIPATION_SCHEMAS:
        normalized["synthetic_cash_participation"] = result["synthetic_cash_participation"]
    if case["schema"] == INVESTOR_CASE_SCHEMA:
        normalized["illustrative_investor"] = result["illustrative_investor"]
    return normalized, pdf


def encoded(value):
    return (canonical(value) + "\n").encode()


def build_package(raw, *, workbook_raw=None, downside_workbook_raw=None, current_revision_raw=None, plan_raw=None):
    result, pdf = build_results(raw, workbook_raw=workbook_raw, downside_workbook_raw=downside_workbook_raw,
                                current_revision_raw=current_revision_raw, plan_raw=plan_raw)
    files = {"case.json": raw, "results.json": encoded(result), "MiniUW_Resumen.pdf": pdf}
    if workbook_raw is not None:
        files[WORKBOOK_FILE] = workbook_raw
    if downside_workbook_raw is not None:
        files[DOWNSIDE_WORKBOOK_FILE] = downside_workbook_raw
    if current_revision_raw is not None:
        files[CURRENT_REVISION_FILE] = current_revision_raw
    if plan_raw is not None:
        files[PLAN_FILE] = plan_raw
    files["package.json"] = encoded(dict(
        schema=PACKAGE_SCHEMA, state=result["state"], decision=result["decision"],
        files=[dict(path=name, bytes=len(content), sha256=sha(content)) for name, content in sorted(files.items())],
    ))
    require(all(len(content) <= MAX_FILE_BYTES for content in files.values()), "Output exceeds the package size limit")
    return files, result


def read_package(directory):
    require(not directory.is_symlink() and directory.is_dir(), "A regular output directory is required")
    paths = list(directory.iterdir())
    names = {p.name for p in paths}
    require(FILES <= names <= FILES | {WORKBOOK_FILE, DOWNSIDE_WORKBOOK_FILE, CURRENT_REVISION_FILE, PLAN_FILE}
            and all(p.is_file() and not p.is_symlink() and p.stat().st_size <= MAX_FILE_BYTES for p in paths),
            "Exact regular case, results, PDF and manifest files are required")
    return {p.name: p.read_bytes() for p in paths}


def verify_package(directory, *, current_revision_raw=None):
    saved = read_package(directory)
    expected, result = build_package(saved["case.json"], workbook_raw=saved.get(WORKBOOK_FILE),
                                     downside_workbook_raw=saved.get(DOWNSIDE_WORKBOOK_FILE),
                                     current_revision_raw=saved.get(CURRENT_REVISION_FILE), plan_raw=saved.get(PLAN_FILE))
    require(saved == expected, "Output does not match source-first replay")
    response = status("verified_source_first", result)
    if "revision_review" in result:
        from worksheet_revision_D128 import audit_revision
        return response | audit_revision(result, current_revision_raw)
    require(current_revision_raw is None, "The designated revision belongs to the current local chain schema")
    return response


def status(operation, result):
    response = dict(status=operation, state=result["state"], profile=result["profile"],
                    decision=result["decision"], pdf_sha256=result["pdf_sha256"], page_count=1)
    if "simulation_result" in result:
        response["simulation_result"] = result["simulation_result"]
    if "pipeline" in result and operation == "verified_source_first":
        response["audit_bot"] = "B16"
    return response


def write_package(raw, directory, *, workbook_raw=None, downside_workbook_raw=None, current_revision_raw=None, plan_raw=None):
    expected, result = build_package(raw, workbook_raw=workbook_raw, downside_workbook_raw=downside_workbook_raw,
                                     current_revision_raw=current_revision_raw, plan_raw=plan_raw)
    if directory.exists() or directory.is_symlink():
        require(read_package(directory) == expected, "Existing output differs from the requested case")
        return status("verified_identical_output", result)
    require(directory.parent.is_dir(), "Output parent directory must exist")
    with TemporaryDirectory(dir=directory.parent, prefix=".miniuw-worksheet-") as temp:
        staging = Path(temp) / "package"
        staging.mkdir()
        for name, content in expected.items():
            with (staging / name).open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        try:
            staging.rename(directory)
        except OSError:
            if directory.is_dir() and read_package(directory) == expected:
                return status("verified_identical_output", result)
            raise
    return status("written_synthetic_package", result)


def read_workbook(path):
    require(path.is_file() and path.stat().st_size <= MAX_WORKBOOK_BYTES,
            "Se requiere una planilla XLSX sintética dentro del tamaño admitido.")
    return path.read_bytes()


def read_current_revision(path, package):
    if path is None:
        return None
    require(not path.resolve().is_relative_to(package.resolve()),
            "Designate the current revision outside the audited package")
    require(path.is_file() and not path.is_symlink(), "An explicit regular revision file is required")
    with path.open("rb") as stream:
        raw = stream.read(MAX_CURRENT_REVISION_BYTES + 1)
    require(len(raw) <= MAX_CURRENT_REVISION_BYTES, "The designated revision file exceeds its size limit")
    return raw


def read_plan_file(path):
    if path is None:
        return None
    require(path.is_file() and not path.is_symlink(), "An explicit regular plan file is required")
    with path.open("rb") as stream:
        raw = stream.read(MAX_PLAN_BYTES + 1)
    require(len(raw) <= MAX_PLAN_BYTES, "The plan file exceeds its size limit")
    return raw


def main():
    parser = ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run")
    run.add_argument("case", type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--workbook", type=Path)
    run.add_argument("--downside-workbook", type=Path)
    run.add_argument("--current-revision", type=Path)
    run.add_argument("--plan", type=Path)
    audit = subcommands.add_parser("audit")
    audit.add_argument("directory", type=Path)
    audit.add_argument("--current-revision", type=Path)
    preflight = subcommands.add_parser("preflight")
    preflight.add_argument("workbook", type=Path)
    preflight.add_argument("--deal-id", required=True)
    preflight.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            require(args.case.is_file() and args.case.stat().st_size <= MAX_EXTENDED_PILOT_BYTES,
                    "A bounded case JSON file is required")
            workbook_raw = None if args.workbook is None else read_workbook(args.workbook)
            downside = None if args.downside_workbook is None else read_workbook(args.downside_workbook)
            result = write_package(args.case.read_bytes(), args.output, workbook_raw=workbook_raw,
                                   downside_workbook_raw=downside,
                                   current_revision_raw=read_current_revision(args.current_revision, args.output),
                                   plan_raw=read_plan_file(args.plan))
        elif args.command == "audit":
            result = verify_package(args.directory,
                                    current_revision_raw=read_current_revision(args.current_revision, args.directory))
        else:
            from worksheet_preflight_D116 import preflight as inspect_workbook
            result = inspect_workbook(read_workbook(args.workbook), args.deal_id, args.snapshot)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError, StopIteration) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
