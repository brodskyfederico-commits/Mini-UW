"""Build and audit the source-bound synthetic Base and Downside pilot package."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys

from check_first_pilot_D49 import rehearsal as sale_rehearsal
from check_operating_replay_D20 import ROOT, local_file, require
from check_scenario_pilot_D51 import WORKBOOK, rehearsal_with_packages
from miniuw_worksheet_v1 import MAX_FILE_BYTES, encoded, read_package
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.screening import simulate_screening
from pilot_workbook_D49 import workbook_bytes


SCENARIOS = ("Base", "Downside")
TOP_FILES = (Path(WORKBOOK).name, "ensayo_base_downside.json", "package.json")


REVISION = "SYNTHETIC-D57-R2"
THRESHOLD_REVISION = "SYNTHETIC-D58-R3"
REVISION_FIXTURES = {
    REVISION: "templates/synthetic-pilot-revision-D57.json",
    THRESHOLD_REVISION: "templates/synthetic-pilot-revision-D58.json",
}


def revised_evidence(evidence, revision):
    if revision == THRESHOLD_REVISION:
        revised_evidence(evidence, REVISION)
    raw = local_file(ROOT, REVISION_FIXTURES[revision]).read_bytes()
    fixture = json.loads(raw)
    require(fixture["schema"] == "miniuw.synthetic-revision-change.v1"
            and revision == fixture["revision"]
            and fixture["prior_evidence_sha256"] == sha(encoded(evidence)), "Synthetic revision binding differs")
    probe, = (probe for probe in evidence["probes"] if probe["id"] == fixture["probe_id"])
    source = probe["input"]
    require(source["criteria_revision"] == fixture["previous_criteria_revision"]
            and source["criteria_revision"] != fixture["criteria_revision"], "Criteria revision did not advance")
    updated = source | {"criteria_revision": fixture["criteria_revision"]}
    comparisons = probe["comparisons"]
    expected = fixture.get("expected_simulation", probe["expected"])
    blockers = fixture.get("expected_blockers", probe["blockers"])
    change = fixture.get("threshold_change")
    if change is not None:
        updated, comparisons = apply_threshold_change(updated, comparisons, change)
    replay = simulate_screening(encoded(updated))
    result = replay.payload
    require(result["decision"] == probe["decision"] == "PENDING"
            and result["simulation_result"] == expected
            and result["comparisons"] == comparisons
            and result["simulation_blockers"] == blockers, "Revision changed comparisons beyond its declared scope")
    probe.update(input=updated, screening_sha256=replay.sha256, expected=expected,
                 simulation=result["simulation_result"], comparisons=result["comparisons"], blockers=result["simulation_blockers"])
    evidence.update(revision=revision, prior_evidence_sha256=fixture["prior_evidence_sha256"],
                    revision_source_sha256=sha(raw))


def apply_threshold_change(source, comparisons, change):
    def target(row):
        return row["metric_id"] == change["metric_id"] and row["scenario_id"] == change["scenario_id"]

    criterion, = (row for row in source["criteria"] if target(row))
    condition = change["condition"]
    require(criterion[condition]["threshold"] == change["previous"]
            and change["value"] != change["previous"], "Prior threshold differs or the revision is empty")
    revised = criterion | {condition: criterion[condition] | {"threshold": change["value"]}}
    source = source | {"criteria": [revised if target(row) else row for row in source["criteria"]]}
    expected = [row | {"criterion_record": revised, "state": change["expected_state"]} if target(row) else row
                for row in comparisons]
    return source, expected


def build(revision=None):
    require(revision is None or isinstance(revision, str) and revision in REVISION_FIXTURES,
            "Unsupported synthetic pilot revision")
    scenarios, refinance, evidence = rehearsal_with_packages()
    _, sale = sale_rehearsal()
    book = workbook_bytes(sale, refinance, evidence)
    require(book == local_file(ROOT, WORKBOOK).read_bytes() and set(scenarios) == set(SCENARIOS),
            "Workbook or scenario inventory differs from its sources")
    if revision is not None:
        revised_evidence(evidence, revision)
        book = workbook_bytes(sale, refinance, evidence)
    files = {TOP_FILES[0]: book, TOP_FILES[1]: encoded(evidence)}
    for scenario in SCENARIOS:
        case = scenarios[scenario]
        require(sha(case["results.json"]) == evidence["sources"][scenario]["results_sha256"],
                f"{scenario} result differs from the screening source")
        files.update({f"{scenario}/{name}": content for name, content in case.items()})
    manifest = dict(schema="miniuw.synthetic-scenario-pilot-package.v1", decision="PENDING",
                    required_scenarios=list(SCENARIOS), criteria_adopted=False, deployment_enabled=False,
                    files=[dict(path=name, bytes=len(content), sha256=sha(content)) for name, content in sorted(files.items())])
    if revision is not None:
        manifest.update(revision=revision, revision_source_sha256=evidence["revision_source_sha256"])
    files["package.json"] = encoded(manifest)
    return files


def read(directory):
    require(directory.is_dir() and not directory.is_symlink(), "A regular pilot directory is required")
    entries = {p.name: p for p in directory.iterdir()}
    require(set(entries) == set(TOP_FILES) | set(SCENARIOS), "Exact pilot package inventory required")
    files = {}
    for name in TOP_FILES:
        entry = entries[name]
        require(entry.is_file() and not entry.is_symlink() and entry.stat().st_size <= MAX_FILE_BYTES,
                "Pilot files must be bounded regular files")
        files[name] = entry.read_bytes()
    for scenario in SCENARIOS:
        files.update({f"{scenario}/{name}": content for name, content in read_package(entries[scenario]).items()})
    return files


def verified_files(directory):
    files = read(directory)
    manifest = json.loads(files["package.json"])
    require(isinstance(manifest, dict), "Invalid pilot manifest")
    require(files == build(manifest.get("revision")), "Pilot package differs from source-first replay")
    return files


def verify(directory):
    return status("verified_source_first", verified_files(directory))


def status(operation, files):
    return dict(status=operation, decision="PENDING", files=len(files), scenarios=list(SCENARIOS),
                manifest_sha256=sha(files["package.json"]))


def write(directory, revision=None):
    files = build(revision)
    if directory.exists() or directory.is_symlink():
        require(read(directory) == files, "Existing pilot directory differs")
        return status("verified_identical_output", files)
    require(directory.parent.is_dir(), "Output parent directory must exist")
    with TemporaryDirectory(dir=directory.parent, prefix=".miniuw-scenario-package-") as temp:
        staged = Path(temp) / "pilot"
        for name, content in files.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        try:
            staged.rename(directory)
        except OSError:
            if directory.is_dir() and read(directory) == files:
                return status("verified_identical_output", files)
            raise
    return status("written_synthetic_package", files)


def main():
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("directory", type=Path)
    run.add_argument("--revision", choices=list(REVISION_FIXTURES))
    sub.add_parser("audit").add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        result = write(args.directory, args.revision) if args.command == "run" else verify(args.directory)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
