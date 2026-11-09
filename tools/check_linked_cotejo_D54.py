"""Exercise the actual package-to-workbook handoff, including incomplete and tampered inputs."""
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
import json
import sys

from check_cotejo_review_D53 import filled_workbook
from check_operating_replay_D20 import ROOT, require
from check_scenario_package_D52 import rewrite_manifest
from miniuw_scenario_package_D52 import TOP_FILES, read, write
from miniuw_foundation.scheduled_expense_case import sha


TOOL = ROOT / "tools/miniuw_linked_cotejo_D54.py"


def call(directory, workbook, output, rejected=False):
    proc = run([sys.executable, str(TOOL), "--package", str(directory), "--workbook", str(workbook),
                "--output", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
    require(proc.returncode == (2 if rejected else 0), f"Unexpected linked Cotejo outcome: {proc.stderr}")
    result = json.loads(proc.stderr if rejected else proc.stdout)
    require(result["decision"] == "PENDING", "Linked synthetic review acquired a decision")
    if not rejected:
        require(json.loads(output.read_bytes()) == result, "Written report differs from its CLI output")
    return result


def verify():
    with TemporaryDirectory(prefix="miniuw-d54-") as temp:
        root = Path(temp)
        directory = root / "pilot"
        write(directory)
        source = read(directory)
        workbook = root / "filled.xlsx"
        reports = {}
        for name, edits, expected in (
            ("coincide", {}, {}),
            ("faltante", {"H9": None}, {"H9": "faltante"}),
            ("diferencia", {"H14": "81"}, {"H14": "valor_distinto"}),
            ("otra_revision", {"D2": "otra-revision"}, {"D2": "texto_distinto"}),
        ):
            workbook.write_bytes(filled_workbook(source, edits))
            report = call(directory, workbook, root / f"{name}.json")
            require(report["incidencias"] == expected and report["estado"] == ("PENDING" if expected else "COINCIDE")
                    and report["expediente_verificado"] is True and report["real_decisions_enabled"] is False
                    and report["workbook_sha256"] == sha(workbook.read_bytes())
                    and report["expediente_manifest_sha256"] == sha(source["package.json"])
                    and all(value == sha(source[f"{scenario}/results.json"])
                            for scenario, value in report["resultados_sha256"].items()),
                    f"Linked review or provenance differs: {name}")
            reports[name] = report["estado"]
        require(read(directory) == source, "Review changed the delivered package")

        workbook.write_bytes(filled_workbook(source))
        output = root / "blocked.json"
        call(directory, root / "missing.xlsx", output, rejected=True)
        require(not output.exists(), "Missing workbook produced a report")

        altered = {f"Downside/{path.name}": path.read_bytes() for path in (directory / "Base").iterdir()}
        for name, value in altered.items():
            (directory / name).write_bytes(value)
        rewrite_manifest(directory, altered)
        blocked = call(directory, workbook, output, rejected=True)
        require(blocked["estado"] == "PENDING" and "source-first replay" in blocked["reason"] and not output.exists(),
                "Swapped scenario was accepted after rehashing")
        for name in (*altered, "package.json"):
            (directory / name).write_bytes(source[name])
        evidence = directory / TOP_FILES[1]
        evidence.unlink()
        blocked = call(directory, workbook, output, rejected=True)
        require(blocked["estado"] == "PENDING" and not output.exists(), "Incomplete package produced a report")
        evidence.write_bytes(source[TOP_FILES[1]])

        existing = root / "coincide.json"
        before = existing.read_bytes()
        call(directory, workbook, existing, rejected=True)
        require(existing.read_bytes() == before, "Retry modified an existing report")
        call(directory, workbook, directory / "review.json", rejected=True)
        require(read(directory) == source, "Review modified the delivered package")
    return dict(status="passed", decision="PENDING", reports=reports, rejected_probes=5)


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
