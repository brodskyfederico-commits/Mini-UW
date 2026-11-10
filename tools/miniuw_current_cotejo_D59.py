"""Track the designated current revision of the local synthetic Base/Downside pilot."""
from argparse import ArgumentParser
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import fcntl
import json
import os
import re
import sys

from check_operating_replay_D20 import require
from miniuw_linked_cotejo_D54 import compare, publish
from miniuw_scenario_package_D52 import REVISION, SCENARIOS, THRESHOLD_REVISION, TOP_FILES, verified_files
from miniuw_worksheet_v1 import MAX_FILE_BYTES, encoded
from miniuw_foundation.expense_cash_detail import _exact, _json
from miniuw_foundation.scheduled_expense_case import sha


SCHEMA = "miniuw.synthetic-current-pilot.v1"
REVISIONS = (REVISION, THRESHOLD_REVISION)
BOUND = 16 * 1024
RECORD_FIELDS = {"revision", "manifest_sha256", "evidence_sha256", "prior_evidence_sha256", "financial_result_sha256"}


@contextmanager
def revision_lock(path):
    lock = path.with_name("." + path.name + ".lock")
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(fd, "r+b") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def hex_digest(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def valid_history(history):
    require(isinstance(history, list) and 1 <= len(history) <= len(REVISIONS), "Synthetic revision history required")
    for index, row in enumerate(history):
        _exact(row, RECORD_FIELDS)
        require(row["revision"] == REVISIONS[index] and hex_digest(row["manifest_sha256"])
                and hex_digest(row["evidence_sha256"]) and hex_digest(row["prior_evidence_sha256"]),
                "Unexpected synthetic revision identity")
        _exact(row["financial_result_sha256"], set(SCENARIOS))
        require(all(hex_digest(value) for value in row["financial_result_sha256"].values()),
                "Exact scenario result hashes required")
        if index:
            previous = history[index - 1]
            require(row["prior_evidence_sha256"] == previous["evidence_sha256"]
                    and row["financial_result_sha256"] == previous["financial_result_sha256"]
                    and row["manifest_sha256"] != previous["manifest_sha256"],
                    "Revision history does not preserve the linked scenario evidence")


def register_bytes(history):
    return encoded(dict(schema=SCHEMA, decision="PENDING", history=history))


def load(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= BOUND,
            "A bounded regular synthetic revision register is required")
    with path.open("rb") as stream:
        raw = stream.read(BOUND + 1)
    state = _json(raw, BOUND)
    _exact(state, {"schema", "decision", "history"})
    require(state["schema"] == SCHEMA and state["decision"] == "PENDING", "Synthetic revision register differs")
    valid_history(state["history"])
    require(raw == register_bytes(state["history"]), "Register bytes differ from the canonical revision history")
    return state["history"], sha(raw)


def describe(directory):
    files = verified_files(directory)
    manifest = json.loads(files["package.json"])
    evidence = json.loads(files[TOP_FILES[1]])
    require(manifest.get("revision") in REVISIONS, "Only the two declared synthetic revisions can be registered")
    return dict(revision=manifest["revision"], manifest_sha256=sha(files["package.json"]),
                evidence_sha256=sha(files[TOP_FILES[1]]), prior_evidence_sha256=evidence["prior_evidence_sha256"],
                financial_result_sha256={name: sha(files[f"{name}/results.json"]) for name in SCENARIOS})


def record(path, package, expected_previous=None):
    candidate = describe(package)
    require(not path.resolve().is_relative_to(package.resolve()), "Keep the register outside the audited package")
    require(path.parent.is_dir(), "Register parent directory must exist")
    with revision_lock(path):
        history = load(path)[0] if path.exists() or path.is_symlink() else []
        if history and candidate == history[-1]:
            previous = history[-2]["manifest_sha256"] if len(history) > 1 else None
            require(expected_previous == previous, "Retry must identify the original prior revision")
            return dict(status="verified_identical_revision", decision="PENDING", vigente=candidate)
        current = history[-1]["manifest_sha256"] if history else None
        require(expected_previous == current, "Synthetic revision register advanced; refresh its current manifest")
        updated = [*history, candidate]
        valid_history(updated)
        raw = register_bytes(updated)
        with TemporaryDirectory(dir=path.parent, prefix=".miniuw-register-") as temp:
            prepared = Path(temp) / "register.json"
            with prepared.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if history:
                prepared.replace(path)
            else:
                os.link(prepared, path)
    return dict(status="recorded_current_revision", decision="PENDING", vigente=candidate)


def review_at_revision(package, workbook, current, token):
    result = compare(package, workbook, current["manifest_sha256"])
    require(result["evidence_sha256"] == current["evidence_sha256"]
            and result["resultados_sha256"] == current["financial_result_sha256"],
            "Cotejo differs from the designated revision record")
    return result | dict(revision_observada=current["revision"], registro_sha256=token)


def review_current(register, package, workbook):
    history, token = load(register)
    return review_at_revision(package, workbook, history[-1], token)


def audit_report(register, package, workbook, report_path):
    require(report_path.is_file() and not report_path.is_symlink()
            and report_path.stat().st_size <= MAX_FILE_BYTES, "A bounded regular review report is required")
    with report_path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    report = _json(raw, MAX_FILE_BYTES)
    require(isinstance(report, dict), "Invalid Cotejo report")
    history, _ = load(register)
    matches = [i for i, record in enumerate(history)
               if record["manifest_sha256"] == report.get("expediente_manifest_sha256")]
    require(len(matches) == 1, "Report manifest is not in the synthetic revision history")
    index = matches[0]
    prefix = history[:index + 1]
    observed = prefix[-1]
    token = sha(register_bytes(prefix))
    expected = review_at_revision(package, workbook, observed, token)
    require(encoded(expected) == raw, "Saved review differs from source-first replay")
    with revision_lock(register):
        latest, current_token = load(register)
        require(latest[:len(prefix)] == prefix, "Registered history changed during the audit")
        current = latest[-1]
        is_current = current == observed and current_token == token
    return dict(status="verified_source_first", decision="PENDING",
                vigencia="VIGENTE" if is_current else "HISTORICO",
                cotejo_guardado=expected["estado"], cotejo_vigente=expected["estado"] if is_current else "PENDING",
                revision_informe=observed["revision"], revision_vigente=current["revision"],
                informe_sha256=sha(raw), registro_vigente_sha256=current_token)


def publish_current(register, package, workbook, output):
    require(not output.resolve().is_relative_to(package.resolve()), "Write the review outside the delivered package")
    result = review_current(register, package, workbook)
    with revision_lock(register):
        history, token = load(register)
        require(token == result["registro_sha256"]
                and history[-1]["manifest_sha256"] == result["expediente_manifest_sha256"],
                "Revision advanced while preparing the review; no report was published")
        publish(output, result)
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register")
    register.add_argument("registry", type=Path)
    register.add_argument("package", type=Path)
    register.add_argument("--expected-previous")
    show = sub.add_parser("current")
    show.add_argument("registry", type=Path)
    review = sub.add_parser("review")
    review.add_argument("registry", type=Path)
    review.add_argument("package", type=Path)
    review.add_argument("workbook", type=Path)
    review.add_argument("--output", type=Path, help="Publish only if the registered revision remains current.")
    audit = sub.add_parser("audit")
    audit.add_argument("registry", type=Path)
    audit.add_argument("package", type=Path)
    audit.add_argument("workbook", type=Path)
    audit.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "register":
            result = record(args.registry, args.package, args.expected_previous)
        elif args.command == "current":
            history, token = load(args.registry)
            result = dict(decision="PENDING", vigente=history[-1], history=history, registro_sha256=token)
        elif args.command == "audit":
            result = audit_report(args.registry, args.package, args.workbook, args.report)
        elif args.output is not None:
            result = publish_current(args.registry, args.package, args.workbook, args.output)
        else:
            result = review_current(args.registry, args.package, args.workbook)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps(dict(status="blocked", estado="PENDING", decision="PENDING", reason=str(error)),
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
