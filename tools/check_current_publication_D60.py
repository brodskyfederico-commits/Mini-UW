"""Prove the local current revision cannot change between final validation and report publication."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
import json
import sys

from check_cotejo_review_D53 import filled_workbook
from check_operating_replay_D20 import ROOT, require
from miniuw_current_cotejo_D59 import load, publish_current, record, review_current
from miniuw_linked_cotejo_D54 import publish
from miniuw_scenario_package_D52 import REVISION, THRESHOLD_REVISION, read, write


TOOL = ROOT / "tools/miniuw_current_cotejo_D59.py"


def verify():
    with TemporaryDirectory(prefix="miniuw-d60-") as temp:
        root = Path(temp)
        old, new = root / "R2", root / "R3"
        write(old, REVISION)
        write(new, THRESHOLD_REVISION)
        packages = [read(old), read(new)]
        old_book, new_book = root / "R2.xlsx", root / "R3.xlsx"
        old_book.write_bytes(filled_workbook(packages[0]))
        new_book.write_bytes(filled_workbook(packages[1]))
        register = root / "vigencia.json"
        prior = record(register, old)["vigente"]

        calculated, release = Event(), Event()
        candidate = root / "obsoleto.json"

        def pause_after_calculation(*args):
            result = review_current(*args)
            require(result["estado"] == "COINCIDE" and result["revision_observada"] == REVISION,
                    "The staged R2 review did not reconcile")
            calculated.set()
            require(release.wait(60), "Concurrent revision test did not resume")
            return result

        with patch("miniuw_current_cotejo_D59.review_current", side_effect=pause_after_calculation):
            with ThreadPoolExecutor(max_workers=1) as executor:
                task = executor.submit(publish_current, register, old, old_book, candidate)
                try:
                    require(calculated.wait(60), "The earlier review did not reach the publication barrier")
                    record(register, new, prior["manifest_sha256"])
                finally:
                    release.set()
                try:
                    task.result(timeout=60)
                except ValueError as error:
                    require("Revision advanced while preparing the review" in str(error),
                            "Stale publication failed for the wrong reason")
                else:
                    raise ValueError("An obsolete review was published")

        require(not candidate.exists(), "The stale review left an output")
        output = root / "vigente.json"
        proc = run([sys.executable, str(TOOL), "review", str(register), str(new), str(new_book),
                    "--output", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
        require(proc.returncode == 0, f"Current review was not published: {proc.stderr}")
        result = json.loads(proc.stdout)
        history, token = load(register)
        require(result == json.loads(output.read_bytes()) and result["revision_observada"] == THRESHOLD_REVISION
                and result["registro_sha256"] == token and result["expediente_manifest_sha256"] == history[-1]["manifest_sha256"]
                and result["estado"] == "COINCIDE" and result["decision"] == "PENDING",
                "Current report did not preserve its exact publication binding")
        before = output.read_bytes()
        duplicate = run([sys.executable, str(TOOL), "review", str(register), str(new), str(new_book),
                         "--output", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
        require(duplicate.returncode == 2 and json.loads(duplicate.stderr)["decision"] == "PENDING"
                and output.read_bytes() == before, "Publication overwrote a prior report")
        require(read(old) == packages[0] and read(new) == packages[1], "Publication modified an audited package")
    return dict(status="passed", decision="PENDING", revision_obsoleta_publicada=False,
                revision_vigente=result["revision_observada"], cotejo_vigente=result["estado"],
                informe_existente_conservado=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New path for the synthetic test summary.")
    args = parser.parse_args()
    try:
        result = verify()
        if args.output is not None:
            publish(args.output, result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
