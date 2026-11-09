"""Re-run explicit corrections to a synthetic workbook against one immutable D52 package."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from check_cotejo_diagnostics_D55 import check as make_discrepancies
from check_cotejo_review_D53 import replace_cotejo_cells, worksheet_cells
from check_linked_cotejo_D54 import call
from check_operating_replay_D20 import require
from miniuw_scenario_package_D52 import read, write
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.workbooks import _parts


STEPS = (
    ("parcial", {"H14": "80"}),
    ("corregida", {"D2": "SYNTHETIC-D51-downside_fail-v1", "M14": "80", "O10": "FAIL", "H9": "78903201/60602000"}),
)


def run_sequence(directory, staged):
    package = read(directory)
    original_path = staged / "inicial.xlsx"
    make_discrepancies(directory, original_path)
    original = original_path.read_bytes()
    initial = call(directory, original_path, staged / "inicial.json")
    require(initial["estado"] == "PENDING" and set(initial["incidencias"]) == {"D2", "H14", "M14", "O10", "H9"},
            "Initial discrepancy set differs")

    workbook, prior = original, initial
    history = [("inicial", initial)]
    for index, (name, edits) in enumerate(STEPS):
        corrected = replace_cotejo_cells(workbook, edits)
        old_cells, new_cells = worksheet_cells(workbook), worksheet_cells(corrected)
        changed = {cell for cell in old_cells.keys() | new_cells.keys() if old_cells.get(cell) != new_cells.get(cell)}
        old_parts, new_parts = _parts(workbook), _parts(corrected)
        require(changed == set(edits) and old_parts.keys() == new_parts.keys()
                and {p for p in old_parts if old_parts[p] != new_parts[p]} == {"xl/worksheets/sheet2.xml"},
                "Correction touched cells or workbook parts outside its declared scope")
        path = staged / f"{name}.xlsx"
        path.write_bytes(corrected)
        report = call(directory, path, staged / f"{name}.json")
        pending = set(prior["incidencias"]) - set(edits)
        require(set(report["incidencias"]) == pending and len(report["detalle_incidencias"]) == len(pending)
                and report["estado"] == ("PENDING" if index == 0 else "COINCIDE")
                and report["workbook_sha256"] == sha(corrected)
                and report["workbook_sha256"] != prior["workbook_sha256"],
                "Cotejo did not resolve exactly the corrected cells")
        history.append((name, report))
        workbook, prior = corrected, report

    repeated = call(directory, staged / "corregida.xlsx", staged / "repeticion.json")
    require(repeated == prior and all(row["estado"] == "COINCIDE" for row in repeated["comparaciones"])
            and len(repeated["comparaciones"]) == 6, "Corrected workbook did not replay exactly")
    for _, report in [*history, ("repeticion", repeated)]:
        require(report["decision"] == "PENDING" and report["expediente_verificado"] is True
                and report["expediente_manifest_sha256"] == sha(package["package.json"])
                and report["resultados_sha256"] == initial["resultados_sha256"]
                and report["evidence_sha256"] == initial["evidence_sha256"]
                and report["real_decisions_enabled"] is report["deployment_enabled"] is False,
                "The rerun changed its audited source or operating decision")
    require(read(directory) == package and original_path.read_bytes() == original,
            "Correction modified the delivered package or the original workbook")
    return dict(status="passed", decision="PENDING", expediente_manifest_sha256=initial["expediente_manifest_sha256"],
                archivos_expediente_verificados=len(package), resultados_sha256=initial["resultados_sha256"],
                etapas=[dict(nombre=name, estado=report["estado"], incidencias=len(report["incidencias"]),
                             workbook_sha256=report["workbook_sha256"])
                        for name, report in history],
                repeticion_identica=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Delivered synthetic D52 directory.")
    parser.add_argument("--output", type=Path, help="New directory for the workbook copies and review reports.")
    args = parser.parse_args()
    try:
        if args.output is not None:
            require(args.output.parent.is_dir() and not args.output.exists() and not args.output.is_symlink(),
                    "Use a new output directory")
            if args.package is not None:
                require(not args.output.resolve().is_relative_to(args.package.resolve()),
                        "Write the test outside the delivered package")
        with TemporaryDirectory(dir=args.output.parent if args.output else None, prefix=".miniuw-d56-") as temp:
            root = Path(temp)
            directory = args.package if args.package is not None else root / "expediente"
            if args.package is None:
                write(directory)
            staged = root / "correcciones"
            staged.mkdir()
            result = run_sequence(directory, staged)
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
