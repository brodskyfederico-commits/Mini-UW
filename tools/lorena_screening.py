"""Compile the pinned standards and rehearse the verdict with synthetic observations."""

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import sys

from check_reference_package import local_file
from miniuw_foundation.lorena_screening import encode, prepare_configuration, rehearse


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "templates/lorena-screening-D230.json"


def source_files():
    recipe = RECIPE.read_bytes()
    path = local_file(ROOT, json.loads(recipe)["source"]["path"])
    return recipe, path.read_bytes()


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("--output", required=True, type=Path)
    evaluation = commands.add_parser("rehearse")
    evaluation.add_argument("configuration", type=Path)
    evaluation.add_argument("case", type=Path)
    workbook = commands.add_parser("rehearse-workbook")
    workbook.add_argument("configuration", type=Path)
    workbook.add_argument("package", type=Path)
    workbook.add_argument("--current-revision", type=Path, required=True)
    args = parser.parse_args()
    try:
        recipe, source = source_files()
        if args.command == "prepare":
            config = prepare_configuration(recipe, source)
            raw = encode(config)
            with args.output.open("xb") as stream:
                stream.write(raw)
            result = dict(criteria_revision=config["revision"], criteria_sha256=sha256(raw).hexdigest(),
                          status=config["status"], decision="PENDING")
        elif args.command == "rehearse":
            result = rehearse(recipe, source, args.configuration.read_bytes(), args.case.read_bytes())
        else:
            from worksheet_lorena_screening import rehearse_workbook

            result = rehearse_workbook(args.package, args.current_revision, recipe, source, args.configuration.read_bytes())
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(json.dumps(dict(status="blocked", decision="PENDING", reason=str(error))), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
