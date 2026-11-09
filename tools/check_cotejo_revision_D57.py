"""Prove that a corrected workbook must match the designated current pilot revision."""
from argparse import ArgumentParser
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
import json
import sys

from check_cotejo_review_D53 import filled_workbook, replace_cotejo_cells, worksheet_cells
from check_operating_replay_D20 import ROOT, require
from miniuw_scenario_package_D52 import REVISION, TOP_FILES, read, write
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.scheduled_expense_case import sha


TOOL = ROOT / "tools/miniuw_linked_cotejo_D54.py"
REVISION_CELLS = {"B4", "D2", *(f"F{row}" for row in range(9, 15))}


def call(package, workbook, current, output, rejected=False):
    proc = run([sys.executable, str(TOOL), "--package", str(package), "--workbook", str(workbook),
                "--current-manifest-sha256", current, "--output", str(output)], cwd=ROOT, capture_output=True,
               text=True, timeout=90, check=False)
    require(proc.returncode == (2 if rejected else 0), f"Unexpected revision Cotejo outcome: {proc.stderr}")
    result = json.loads(proc.stderr if rejected else proc.stdout)
    require(result["decision"] == "PENDING", "Revision comparison acquired a decision")
    require(not output.exists() if rejected else json.loads(output.read_bytes()) == result,
            "Unexpected revision report publication")
    return result


def check(old_directory, old_workbook, output):
    old = read(old_directory)
    old_book = old_workbook.read_bytes()
    previous_digest = sha(old["package.json"])
    old_result = call(old_directory, old_workbook, previous_digest, output / "01_revision_anterior.json")
    require(old_result["estado"] == "COINCIDE", "Original corrected workbook must match its original revision")

    current_directory = output / "expediente_vigente"
    write(current_directory, REVISION)
    current = read(current_directory)
    current_digest = sha(current["package.json"])
    require(current_digest != previous_digest
            and current[TOP_FILES[1]] != old[TOP_FILES[1]]
            and all(current[name] == old[name] for name in old if name.startswith(("Base/", "Downside/"))),
            "Revision did not isolate the evidence change")

    blocked = call(old_directory, old_workbook, current_digest, output / "obsoleto.json", rejected=True)
    require(blocked["estado"] == "PENDING" and "designated current revision" in blocked["reason"],
            "Historical package was allowed under the current revision")
    (output / "02_expediente_anterior_rechazado.json").write_bytes(encoded(blocked))

    pending = call(current_directory, old_workbook, current_digest, output / "03_planilla_anterior.json")
    require(pending["estado"] == "PENDING" and set(pending["incidencias"]) == REVISION_CELLS
            and all(value == "texto_distinto" for value in pending["incidencias"].values()),
            "The old workbook must be blocked only by revision bindings")

    # Update only the synthetic revision references on a copy of the already-corrected workbook.
    current_cells = worksheet_cells(filled_workbook(current))
    patched = replace_cotejo_cells(old_book, {cell: current_cells[cell]["literal"] for cell in REVISION_CELLS})
    old_cells, new_cells = worksheet_cells(old_book), worksheet_cells(patched)
    require({cell for cell in old_cells if old_cells[cell] != new_cells[cell]} == REVISION_CELLS,
            "Revision alignment altered fields outside the declared bindings")
    patched_path = output / "Planilla_Sintetica_Revision_Vigente.xlsx"
    patched_path.write_bytes(patched)
    aligned = call(current_directory, patched_path, current_digest, output / "04_planilla_vigente.json")
    require(aligned["estado"] == "COINCIDE" and not aligned["incidencias"]
            and all(row["estado"] == "COINCIDE" for row in aligned["comparaciones"])
            and aligned["resultados_sha256"] == pending["resultados_sha256"] == old_result["resultados_sha256"]
            and aligned["expediente_manifest_sha256"] == pending["expediente_manifest_sha256"] == current_digest
            and aligned["evidence_sha256"] == pending["evidence_sha256"] != old_result["evidence_sha256"],
            "Current workbook did not reconcile against the designated revision")
    require(read(old_directory) == old and read(current_directory) == current and old_workbook.read_bytes() == old_book,
            "The test changed an input package or workbook")
    return dict(status="passed", decision="PENDING", comparaciones=4,
                revision_anterior_manifest_sha256=previous_digest, revision_vigente_manifest_sha256=current_digest,
                incidencias_revision_anterior=len(pending["incidencias"]), filas_vigentes=len(aligned["comparaciones"]),
                resultados_financieros_identicos=True,
                estados=["COINCIDE_HISTORICO", "PENDING_EXPEDIENTE_ANTERIOR", "PENDING_PLANILLA_ANTERIOR", "COINCIDE_VIGENTE"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Original audited D52 package.")
    parser.add_argument("--workbook", type=Path, help="Corrected D56 workbook for the original package.")
    parser.add_argument("--output", type=Path, help="New directory for the synthetic revision demonstration.")
    args = parser.parse_args()
    try:
        require((args.package is None) == (args.workbook is None), "Provide both original inputs or neither")
        if args.output is not None:
            require(args.output.parent.is_dir() and not args.output.exists() and not args.output.is_symlink(),
                    "Use a new output directory")
            if args.package is not None:
                require(not args.output.resolve().is_relative_to(args.package.resolve()),
                        "Write the test outside the original package")
        with TemporaryDirectory(dir=args.output.parent if args.output else None, prefix=".miniuw-d57-") as temp:
            root = Path(temp)
            directory, workbook = args.package, args.workbook
            if directory is None:
                directory, workbook = root / "anterior", root / "corregida.xlsx"
                write(directory)
                workbook.write_bytes(filled_workbook(read(directory)))
            staged = root / "revision"
            staged.mkdir()
            result = check(directory, workbook, staged)
            if args.output is not None:
                (staged / "resumen.json").write_bytes(encoded(result))
                staged.rename(args.output)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
