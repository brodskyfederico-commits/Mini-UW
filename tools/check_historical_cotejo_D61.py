"""Audit a published report across a revision advance without reclassifying historical cash."""
from argparse import ArgumentParser
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
import json
import sys

from check_cotejo_review_D53 import filled_workbook
from check_operating_replay_D20 import ROOT, require
from miniuw_current_cotejo_D59 import publish_current, record
from miniuw_linked_cotejo_D54 import publish
from miniuw_scenario_package_D52 import REVISION, THRESHOLD_REVISION, read, write
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.scheduled_expense_case import sha


TOOL = ROOT / "tools/miniuw_current_cotejo_D59.py"


def audit(register, package, workbook, report, rejected=False):
    proc = run([sys.executable, str(TOOL), "audit", str(register), str(package), str(workbook), str(report)],
               cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
    require(proc.returncode == (2 if rejected else 0), f"Unexpected audit result: {proc.stderr}")
    result = json.loads(proc.stderr if rejected else proc.stdout)
    require(result["decision"] == "PENDING", "Synthetic audit acquired a decision")
    return result


def verify():
    with TemporaryDirectory(prefix="miniuw-d61-") as temp:
        root = Path(temp)
        old, new = root / "R2", root / "R3"
        write(old, REVISION)
        write(new, THRESHOLD_REVISION)
        packages = [read(old), read(new)]
        old_book, new_book = root / "R2.xlsx", root / "R3.xlsx"
        old_book.write_bytes(filled_workbook(packages[0]))
        new_book.write_bytes(filled_workbook(packages[1]))
        register = root / "vigencia.json"
        old_revision = record(register, old)["vigente"]

        original = root / "informe_R2.json"
        publish_current(register, old, old_book, original)
        original_raw = original.read_bytes()
        initial = audit(register, old, old_book, original)
        require(initial["vigencia"] == "VIGENTE" and initial["cotejo_vigente"] == "COINCIDE",
                "R2 should be current before activation")

        record(register, new, old_revision["manifest_sha256"])
        historical = audit(register, old, old_book, original)
        require(historical["vigencia"] == "HISTORICO" and historical["cotejo_guardado"] == "COINCIDE"
                and historical["cotejo_vigente"] == "PENDING" and historical["revision_informe"] == REVISION
                and historical["revision_vigente"] == THRESHOLD_REVISION
                and historical["informe_sha256"] == initial["informe_sha256"] == sha(original_raw),
                "Historic report did not retain its original result or lose currency")

        report = root / "informe_R3.json"
        publish_current(register, new, new_book, report)
        current = audit(register, new, new_book, report)
        require(current["vigencia"] == "VIGENTE" and current["cotejo_vigente"] == "COINCIDE"
                and current["revision_informe"] == current["revision_vigente"] == THRESHOLD_REVISION,
                "R3 report must be current")

        forged = root / "alterado.json"
        edited = json.loads(original_raw)
        edited["estado"] = "PENDING"
        forged.write_bytes(encoded(edited))
        require("source-first replay" in audit(register, old, old_book, forged, rejected=True)["reason"],
                "Altered report was not rejected for replay mismatch")
        require("designated current revision" in audit(register, new, new_book, original, rejected=True)["reason"],
                "An unrelated revision reproduced the historical report")
        require(read(old) == packages[0] and read(new) == packages[1] and original.read_bytes() == original_raw,
                "Audit modified its original evidence")
    return dict(status="passed", decision="PENDING", informe_R2_antes=initial["vigencia"],
                informe_R2_despues=historical["vigencia"], cotejo_R2_vigente=historical["cotejo_vigente"],
                informe_R3=current["vigencia"], informe_R2_sha256=historical["informe_sha256"], rechazos=2)


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
