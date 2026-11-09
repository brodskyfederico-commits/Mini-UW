"""Verify exact discrepancy details and their locators in the delivered synthetic package."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from check_cotejo_review_D53 import filled_workbook
from check_operating_replay_D20 import require, select
from miniuw_linked_cotejo_D54 import compare, publish
from miniuw_scenario_package_D52 import read, write


def check(directory, workbook_path):
    package = read(directory)
    workbook_path.write_bytes(filled_workbook(package, {
        "D2": "otra-revision", "H14": "81", "M14": None,
        "O10": "PASS", "H9": ("78903201/60602000", "1.3019900498333388"),
    }))
    result = compare(directory, workbook_path)
    expected = {
        "Cotejo!D2": ("texto_distinto", "otra-revision", "SYNTHETIC-D51-downside_fail-v1", None),
        "Cotejo!H14": ("valor_distinto", "81", "80", "1"),
        "Cotejo!M14": ("faltante", None, "80", None),
        "Cotejo!O10": ("texto_distinto", "PASS", "FAIL", None),
        "Cotejo!H9": ("formula_no_evaluada", None, "78903201/60602000", None),
    }
    details = {row["celda"]: row for row in result["detalle_incidencias"]}
    require(result["estado"] == result["decision"] == "PENDING" and set(details) == expected.keys(),
            "Mismatch report differs")
    for cell, values in expected.items():
        row = details[cell]
        require(tuple(row[key] for key in ("motivo", "recibido", "esperado", "diferencia_exacta")) == values,
                f"Diagnostic values differ: {cell}")
        source = row["fuente"]
        linked = select(json.loads(package[source["archivo"]]), source["puntero"])
        if cell == "Cotejo!M14":
            linked = linked["numerator"]
        if cell == "Cotejo!O10":
            require(linked == "FAIL_CONDITION", "State locator differs")
        else:
            require(linked == row["esperado"], f"Reference locator differs: {cell}")
    require(details["Cotejo!H9"]["tipo_recibido"] == "formula" and read(directory) == package,
            "Formula or package behavior differs")
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with TemporaryDirectory(prefix="miniuw-d55-") as temp:
            root = Path(temp)
            directory = args.package if args.package is not None else root / "expediente"
            if args.package is None:
                write(directory)
            result = check(directory, root / "cotejo.xlsx")
            if args.output is not None:
                require(not args.output.resolve().is_relative_to(directory.resolve()),
                        "Write the review outside the delivered package")
                publish(args.output, result)
        print(json.dumps(dict(status="passed", decision=result["decision"],
                              diagnostics=len(result["detalle_incidencias"])), ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
