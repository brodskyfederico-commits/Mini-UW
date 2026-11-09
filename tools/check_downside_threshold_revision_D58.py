"""Replay a Downside-only threshold revision and withdraw the old workbook's cotejo."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from check_cotejo_review_D53 import filled_workbook, replace_cotejo_cells, worksheet_cells
from check_cotejo_revision_D57 import REVISION_CELLS, call
from check_operating_replay_D20 import require
from miniuw_scenario_package_D52 import REVISION, THRESHOLD_REVISION, TOP_FILES, read, write
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.scheduled_expense_case import sha


CHANGED_CELLS = REVISION_CELLS | {"B5", "D5", "M10", "N10", "O10"}


def probe(package):
    result = json.loads(package[TOP_FILES[1]])
    selected, = (item for item in result["probes"] if item["id"] == "downside_fail")
    return selected


def check(old_directory, workbook, output):
    old = read(old_directory)
    old_workbook = workbook.read_bytes()
    require(json.loads(old["package.json"])["revision"] == REVISION, "Use the R2 synthetic package")
    old_digest = sha(old["package.json"])
    baseline = call(old_directory, workbook, old_digest, output / "01_cotejo_R2.json")
    require(baseline["estado"] == "COINCIDE", "Prior workbook must match R2")

    current_directory = output / "expediente_R3"
    write(current_directory, THRESHOLD_REVISION)
    current = read(current_directory)
    current_digest = sha(current["package.json"])
    require(current_digest != old_digest
            and all(old[name] == current[name] for name in old if name.startswith(("Base/", "Downside/"))),
            "Threshold revision changed financial scenario files")

    before, after = probe(old), probe(current)
    require(before["simulation"] == "FAIL" and after["simulation"] == "PENDING"
            and after["blockers"] == ["intermediate_band_pending_professional_review"]
            and before["screening_sha256"] != after["screening_sha256"], "Screening did not recalculate")
    require(before["input"]["metric_values"] == after["input"]["metric_values"], "Threshold revision changed metric values")
    differences = [(a, b) for a, b in zip(before["input"]["criteria"], after["input"]["criteria"], strict=True) if a != b]
    require(len(differences) == 1, "Exactly one criterion must change")
    original, revised = differences[0]
    new_threshold = {"numerator": "1", "denominator": "1"}
    require(original["scenario_id"] == "Downside" and original["metric_id"] == "equity_multiple"
            and original["fail_condition"] == {"operator": "<", "threshold": {"numerator": "21", "denominator": "20"}}
            and revised == original | {"fail_condition": {"operator": "<", "threshold": new_threshold}},
            "Unexpected threshold or operator change")
    changed, = ((a, b) for a, b in zip(before["comparisons"], after["comparisons"], strict=True) if a != b)
    require(changed[0]["state"] == "FAIL_CONDITION" and changed[1]["state"] == "BAND"
            and changed[1]["scenario_id"] == "Downside" and changed[1]["metric_id"] == "equity_multiple",
            "Expected only the Downside multiple to move into the pending band")

    outdated = call(current_directory, workbook, current_digest, output / "02_planilla_R2_en_R3.json")
    require(outdated["estado"] == "PENDING" and set(outdated["incidencias"]) == CHANGED_CELLS
            and outdated["incidencias"]["M10"] == "valor_distinto",
            "Prior workbook did not identify the changed revision, threshold and result")
    cells = worksheet_cells(filled_workbook(current))
    patched = replace_cotejo_cells(old_workbook, {cell: cells[cell]["literal"] for cell in CHANGED_CELLS})
    before_cells, after_cells = worksheet_cells(old_workbook), worksheet_cells(patched)
    require({cell for cell in before_cells if before_cells[cell] != after_cells[cell]} == CHANGED_CELLS,
            "Cotejo update changed cells outside the revision, threshold and result")
    patched_path = output / "Planilla_Sintetica_R3.xlsx"
    patched_path.write_bytes(patched)
    aligned = call(current_directory, patched_path, current_digest, output / "03_planilla_R3.json")
    require(aligned["estado"] == "COINCIDE" and not aligned["incidencias"]
            and all(row["estado"] == "COINCIDE" for row in aligned["comparaciones"])
            and aligned["resultados_sha256"] == outdated["resultados_sha256"] == baseline["resultados_sha256"]
            and aligned["expediente_manifest_sha256"] == outdated["expediente_manifest_sha256"] == current_digest,
            "Revised workbook did not reconcile to the designated R3")
    require(read(old_directory) == old and read(current_directory) == current and workbook.read_bytes() == old_workbook,
            "Review modified the original inputs")
    return dict(status="passed", decision="PENDING", criterio="equity_multiple/Downside",
                umbral_fail_anterior="< 1.05", umbral_fail_vigente="< 1.00",
                simulacion_anterior=before["simulation"], simulacion_vigente=after["simulation"],
                planilla_anterior=outdated["estado"], planilla_vigente=aligned["estado"],
                incidencias_planilla_anterior=len(outdated["incidencias"]), resultados_financieros_identicos=True,
                expediente_vigente_manifest_sha256=current_digest)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        require((args.package is None) == (args.workbook is None), "Provide both R2 inputs or neither")
        if args.output is not None:
            require(args.output.parent.is_dir() and not args.output.exists() and not args.output.is_symlink(),
                    "Use a new output directory")
            if args.package is not None:
                require(not args.output.resolve().is_relative_to(args.package.resolve()),
                        "Write the test outside the original package")
        with TemporaryDirectory(dir=args.output.parent if args.output else None, prefix=".miniuw-d58-") as temp:
            root = Path(temp)
            package, workbook = args.package, args.workbook
            if package is None:
                package, workbook = root / "R2", root / "planilla.xlsx"
                write(package, REVISION)
                workbook.write_bytes(filled_workbook(read(package)))
            staged = root / "umbral"
            staged.mkdir()
            result = check(package, workbook, staged)
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
