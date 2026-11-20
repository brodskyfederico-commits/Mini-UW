"""Assemble and replay a synthetic worksheet package from registered source files."""
from argparse import ArgumentParser
from copy import deepcopy
import json
from pathlib import Path

from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import (
    CRITERIA_FILE, DOWNSIDE_WORKBOOK_FILE, EVIDENCE_FILE, MAX_FILE_BYTES, PLAN_FILE, WORKBOOK_FILE,
    TECHNICAL_SCHEMAS, WORKBOOK_CRITICAL_EVIDENCE_SCHEMA, encoded, write_package,
)
from preview_lorena_criteria_D192 import read_cells
from worksheet_local_sources_D127 import synthetic_id
from worksheet_native_mapping_D139 import SCENARIOS
from worksheet_revision_D128 import snapshot_for_case


SOURCES = dict(workbook_raw=WORKBOOK_FILE, downside_workbook_raw=DOWNSIDE_WORKBOOK_FILE,
               plan_raw=PLAN_FILE, evidence_raw=EVIDENCE_FILE, criteria_raw=CRITERIA_FILE)


def fingerprints(sources):
    result = {}
    for argument, filename in SOURCES.items():
        raw = sources.get(argument)
        if raw is None:
            result[filename] = None
            continue
        if len(raw) > MAX_FILE_BYTES:
            raise ValidationError(f"source_exceeds_size_limit:{filename}")
        cells = {}
        try:
            if filename in (WORKBOOK_FILE, DOWNSIDE_WORKBOOK_FILE):
                cells = inspect_synthetic_input_sheet(raw).cells
            elif filename == CRITERIA_FILE:
                cells = read_cells(raw)
        except ValidationError:
            # The existing workbook reviewer diagnoses unusable or incompatible workbook content.
            pass
        result[filename] = dict(sha256=sha(raw), cells={cell: sha(encoded(value)) for cell, value in cells.items()})
    return result


def compare_sources(expected, observed):
    issues = []
    for filename, source in expected.items():
        actual = observed[filename]
        if source == actual:
            continue
        before, after = (item["cells"] if item else {} for item in (source, actual))
        changed = sorted(cell for cell in before.keys() | after.keys() if before.get(cell) != after.get(cell))
        issues.append(dict(file=filename, cells=changed, blocker="registered_source_mismatch"))
    return issues


def register(sources, revision):
    if not synthetic_id(revision) or any(name not in sources for name in SOURCES):
        raise ValidationError("explicit_synthetic_revision_and_complete_source_inventory_required")
    return dict(revision=revision, files=fingerprints(sources))


def prepare(settings, registered):
    # Compare observed bytes separately. Bind the case only to the declared registration.
    if settings.get("schema") not in TECHNICAL_SCHEMAS:
        raise ValidationError("explicit_synthetic_worksheet_settings_required")
    if not synthetic_id(registered.get("revision")) or set(registered["files"]) != set(SOURCES.values()):
        raise ValidationError("invalid_synthetic_registration")
    case = deepcopy(settings)
    if case["schema"] == WORKBOOK_CRITICAL_EVIDENCE_SCHEMA:
        from worksheet_horizon_fiscal_D267 import reference_for
        case["critical_evidence_reference_sha256"] = sha(reference_for(case).read_bytes())
    files = registered["files"]

    def expected(filename):
        return files[filename]["sha256"] if files[filename] is not None else None

    workbooks = dict(zip(SCENARIOS, (expected(WORKBOOK_FILE), expected(DOWNSIDE_WORKBOOK_FILE)), strict=True))
    case["workbook_sha256"] = workbooks
    local = case["local_sources"]
    local["workbook_sha256"] = workbooks
    local["plan_pdf"]["sha256"] = expected(PLAN_FILE)
    local["evidence_pdf"]["sha256"] = expected(EVIDENCE_FILE)
    for name, digest in workbooks.items():
        case["native_mapping"]["scenarios"][name]["workbook_sha256"] = digest
    downside = case["rent_inputs"]["supplemental_scope"]["Downside"]["downside_scope"]
    downside.update(base_workbook_sha256=workbooks["Base"], downside_workbook_sha256=workbooks["Downside"])
    case["criteria_workbook"]["sha256"] = expected(CRITERIA_FILE)
    return encoded(case), encoded(snapshot_for_case(case, registered["revision"]))


def assemble(settings, registered, sources, output):
    issues = compare_sources(registered["files"], fingerprints(sources))
    case, current = prepare(settings, registered)
    report = write_package(case, output, current_revision_raw=current, **sources)
    return report | dict(registration_sha256=sha(encoded(registered)), source_blockers=issues)


def read_source_directory(path):
    result = {}
    for argument, filename in SOURCES.items():
        source = path / filename
        if not source.exists():
            result[argument] = None
        elif source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_FILE_BYTES:
            raise ValidationError(f"expected_bounded_regular_source:{filename}")
        else:
            result[argument] = source.read_bytes()
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    receipt = subcommands.add_parser("register")
    replay = subcommands.add_parser("run")
    for command in (receipt, replay):
        command.add_argument("source_directory", type=Path)
        command.add_argument("registration", type=Path)
    receipt.add_argument("--revision", required=True)
    replay.add_argument("--settings", type=Path, required=True)
    replay.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = read_source_directory(args.source_directory)
    if args.command == "register":
        with args.registration.open("xb") as stream:
            stream.write(encoded(register(sources, args.revision)))
        return
    settings = json.loads(args.settings.read_bytes())
    registered = json.loads(args.registration.read_bytes())
    print(json.dumps(assemble(settings, registered, sources, args.output), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
