"""Run the package command and prove that altered or mixed evidence fails replay."""
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import sys

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from miniuw_scenario_package_D52 import TOP_FILES
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.scheduled_expense_case import sha


TOOL = ROOT / "tools/miniuw_scenario_package_D52.py"


def call(*args, rejected=False):
    proc = run([sys.executable, str(TOOL), *(str(arg) for arg in args)], cwd=ROOT, capture_output=True,
               text=True, timeout=90, check=False)
    require(proc.returncode == (2 if rejected else 0), f"Unexpected package CLI outcome: {proc.stderr}")
    result = json.loads(proc.stderr if rejected else proc.stdout)
    require(result["decision"] == "PENDING", "Package acquired a decision")
    return result


def rewrite_manifest(directory, updates):
    path = directory / "package.json"
    original = path.read_bytes()
    manifest = json.loads(original)
    for row in manifest["files"]:
        if row["path"] in updates:
            content = updates[row["path"]]
            row.update(bytes=len(content), sha256=sha(content))
    path.write_bytes(encoded(manifest))
    return original


def probe(directory, updates):
    originals = {name: (directory / name).read_bytes() for name in updates}
    for name, content in updates.items():
        require(originals[name] != content, "Probe did not modify its artifact")
        (directory / name).write_bytes(content)
    manifest = rewrite_manifest(directory, updates)
    try:
        result = call("audit", directory, rejected=True)
        require(result["reason"] == "Pilot package differs from source-first replay",
                "The recalculated manifest should still fail replay")
    finally:
        for name, content in originals.items():
            (directory / name).write_bytes(content)
        (directory / "package.json").write_bytes(manifest)


def verify():
    with TemporaryDirectory(prefix="miniuw-d52-check-") as temp:
        directory = Path(temp) / "pilot"
        written = call("run", directory)
        check = call("audit", directory)
        require(written["manifest_sha256"] == check["manifest_sha256"]
                and check["files"] == 11 and call("run", directory)["status"] == "verified_identical_output",
                "Package did not reproduce or retry exactly")
        workbook = directory / TOP_FILES[0]
        with ZipFile(workbook) as spreadsheet:
            require(spreadsheet.testzip() is None, "Workbook CRC failed")
        for scenario in ("Base", "Downside"):
            pages = PdfReader(directory / scenario / "MiniUW_Resumen.pdf").pages
            require(len(pages) == 1 and "PENDIENTE" in pages[0].extract_text(), "Scenario PDF must be pending and one page")
        evidence_path = TOP_FILES[1]
        source = (directory / evidence_path).read_bytes()
        data = json.loads(source)
        data["probes"][0]["simulation"] = "FAIL"
        probe(directory, {evidence_path: encoded(data)})
        probe(directory, {TOP_FILES[0]: workbook.read_bytes() + b"tampered"})
        # Replacing the entire Downside package retains its valid internal manifest but binds the wrong scenario.
        probe(directory, {f"Downside/{path.name}": path.read_bytes() for path in (directory / "Base").iterdir()})
        extra = directory / "extra.txt"
        extra.write_text("outside the package")
        require(call("audit", directory, rejected=True)["reason"] == "Exact pilot package inventory required",
                "Unexpected file was accepted")
        extra.unlink()
        require(call("audit", directory)["manifest_sha256"] == check["manifest_sha256"],
                "Restored package differs")
    return dict(status="passed", decision="PENDING", scenarios=2, files=check["files"], rejected_probes=4,
                manifest_sha256=check["manifest_sha256"])


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
