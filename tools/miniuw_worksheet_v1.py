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
PACKAGE_SCHEMA = "miniuw.synthetic-unified-worksheet-package.v1"
COSTED_SALE = "templates/synthetic-worksheet-sale-costs-D63.json"
COSTED_PROFILE = "with_refinance_worksheet_sale"
ARCHIVES = {"without_refinance": SALE, "with_refinance": REFINANCE, COSTED_PROFILE: COSTED_SALE}
FILES = frozenset({"case.json", "results.json", "MiniUW_Resumen.pdf", "package.json"})
WORKBOOK_FILE = "Inputs.xlsx"
MAX_FILE_BYTES = 4 * 1024 * 1024


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


def build_results(raw, *, workbook_raw=None):
    case = _json(raw, 4096)
    if isinstance(case, dict) and case.get("schema") == WORKBOOK_INTAKE_SCHEMA:
        from worksheet_intake_case_D117 import build_intake_case
        require(workbook_raw is not None, "The intake case requires the exact synthetic Inputs workbook")
        return build_intake_case(case, sha(raw), workbook_raw)
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


def build_package(raw, *, workbook_raw=None):
    result, pdf = build_results(raw, workbook_raw=workbook_raw)
    files = {"case.json": raw, "results.json": encoded(result), "MiniUW_Resumen.pdf": pdf}
    if workbook_raw is not None:
        files[WORKBOOK_FILE] = workbook_raw
    files["package.json"] = encoded(dict(
        schema=PACKAGE_SCHEMA, state=result["state"], decision=result["decision"],
        files=[dict(path=name, bytes=len(content), sha256=sha(content)) for name, content in sorted(files.items())],
    ))
    require(all(len(content) <= MAX_FILE_BYTES for content in files.values()), "Output exceeds the package size limit")
    return files, result


def read_package(directory):
    require(not directory.is_symlink() and directory.is_dir(), "A regular output directory is required")
    paths = list(directory.iterdir())
    require({p.name for p in paths} in (FILES, FILES | {WORKBOOK_FILE})
            and all(p.is_file() and not p.is_symlink() and p.stat().st_size <= MAX_FILE_BYTES for p in paths),
            "Exact regular case, results, PDF and manifest files are required")
    return {p.name: p.read_bytes() for p in paths}


def verify_package(directory):
    saved = read_package(directory)
    expected, result = build_package(saved["case.json"], workbook_raw=saved.get(WORKBOOK_FILE))
    require(saved == expected, "Output does not match source-first replay")
    return status("verified_source_first", result)


def status(operation, result):
    return dict(status=operation, state=result["state"], profile=result["profile"],
                decision=result["decision"], pdf_sha256=result["pdf_sha256"], page_count=1)


def write_package(raw, directory, *, workbook_raw=None):
    expected, result = build_package(raw, workbook_raw=workbook_raw)
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


def main():
    parser = ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run")
    run.add_argument("case", type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--workbook", type=Path)
    audit = subcommands.add_parser("audit")
    audit.add_argument("directory", type=Path)
    preflight = subcommands.add_parser("preflight")
    preflight.add_argument("workbook", type=Path)
    preflight.add_argument("--deal-id", required=True)
    preflight.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            require(args.case.is_file() and args.case.stat().st_size <= 4096, "A bounded case JSON file is required")
            workbook_raw = None
            if args.workbook is not None:
                require(args.workbook.is_file() and args.workbook.stat().st_size <= MAX_WORKBOOK_BYTES,
                        "Se requiere una planilla XLSX sintética dentro del tamaño admitido.")
                workbook_raw = args.workbook.read_bytes()
            result = write_package(args.case.read_bytes(), args.output, workbook_raw=workbook_raw)
        elif args.command == "audit":
            result = verify_package(args.directory)
        else:
            from worksheet_preflight_D116 import preflight as inspect_workbook
            require(args.workbook.is_file() and args.workbook.stat().st_size <= MAX_WORKBOOK_BYTES,
                    "Se requiere una planilla XLSX sintética dentro del tamaño admitido.")
            result = inspect_workbook(args.workbook.read_bytes(), args.deal_id, args.snapshot)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError, StopIteration) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
