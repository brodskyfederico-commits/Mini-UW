"""Compare a synthetic filled Cotejo workbook against a delivered, verified D52 package."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys

from check_cotejo_review_D53 import review
from check_operating_replay_D20 import require
from miniuw_scenario_package_D52 import SCENARIOS, verified_files
from miniuw_worksheet_v1 import MAX_FILE_BYTES, encoded
from miniuw_foundation.scheduled_expense_case import sha


def compare(package_directory, workbook_path, current_manifest_sha256=None):
    package = verified_files(package_directory)
    manifest_sha256 = sha(package["package.json"])
    require(current_manifest_sha256 is None or current_manifest_sha256 == manifest_sha256,
            "Delivered package is not the designated current revision")
    require(workbook_path.is_file() and not workbook_path.is_symlink()
            and workbook_path.stat().st_size <= MAX_FILE_BYTES, "Bounded regular filled workbook required")
    result = review(workbook_path.read_bytes(), package)
    require(result["decision"] == "PENDING", "Synthetic Cotejo acquired a decision")
    return result | dict(schema="miniuw.synthetic-linked-cotejo.v1", expediente_verificado=True,
                         expediente_manifest_sha256=manifest_sha256,
                         resultados_sha256={scenario: sha(package[f"{scenario}/results.json"]) for scenario in SCENARIOS},
                         real_decisions_enabled=False, deployment_enabled=False)


def publish(path, result):
    # Publish only a complete report and never replace an existing file, including a source file.
    with TemporaryDirectory(dir=path.parent, prefix=".miniuw-linked-cotejo-") as temp:
        prepared = Path(temp) / "review.json"
        prepared.write_bytes(encoded(result))
        os.link(prepared, path)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Optional new path for the review JSON.")
    parser.add_argument("--current-manifest-sha256", help="Require the designated current synthetic package digest.")
    args = parser.parse_args()
    try:
        result = compare(args.package, args.workbook, args.current_manifest_sha256)
        if args.output is not None:
            require(not args.output.resolve().is_relative_to(args.package.resolve()),
                    "Write the review outside the delivered package")
            publish(args.output, result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps(dict(status="blocked", estado="PENDING", decision="PENDING", reason=str(error)),
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
