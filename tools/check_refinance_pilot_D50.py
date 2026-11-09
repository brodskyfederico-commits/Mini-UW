"""Verify both refinance cash directions and add their evidence to the common pilot workbook."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from pypdf import PdfReader

from check_first_pilot_D49 import WORKBOOK as SALE_WORKBOOK, compare_probe, rehearsal as sale_rehearsal
from check_operating_replay_D20 import ROOT, local_file, require
from check_unified_worksheet_D48 import expected_events, verify_figures
from miniuw_worksheet_v1 import build_package, encoded, verify_package
from miniuw_foundation.scheduled_expense_case import sha
from pilot_workbook_D49 import workbook_bytes


FIXTURE = "templates/synthetic-refinance-pilot-D50.json"
WORKBOOK = "docs/review/MiniUW_Planilla_Cotejo_D50.xlsx"


def rehearsal():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = json.loads(raw)
    base = local_file(ROOT, fixture["case_path"]).read_bytes()
    require(fixture["schema"] == "miniuw.synthetic-refinance-pilot.v1" and sha(base) == fixture["case_sha256"]
            and fixture["metric_id"] == "equity_multiple", "Refinance pilot fixture or case differs")
    case = json.loads(base)
    require(case["profile"] == "with_refinance" and case["archive_case"] == "cash-out", "Unexpected pilot profile")

    packages, references, rows = {}, {}, []
    for probe in fixture["cases"]:
        name = probe["archive_case"]
        candidate = base if name == case["archive_case"] else encoded(case | {"archive_case": name})
        files, result = build_package(candidate)
        page, = PdfReader(BytesIO(files["MiniUW_Resumen.pdf"])).pages
        verify_figures(name, result, page.extract_text())
        packages[name] = files
        if result["project"] is not None:
            events = sorted(expected_events(name))
            contributions = sum(value for _, kind, _, value in events if kind == "contribution")
            receipts = sum(value for _, kind, _, value in events if kind == "distribution")
            references[name] = dict(events=[(date, kind, category, str(value)) for date, kind, category, value in events],
                                    contributions=str(contributions), receipts=str(receipts),
                                    equity_multiple=str(Fraction(receipts, contributions)))
        else:
            require(result["capacity"]["binding_limit_ids"] == ["DSCR"]
                    and "selected_principal_exceeds_declared_bank_capacity" in result["capacity"]["blockers"],
                    "Refinance should have been blocked by DSCR capacity")
        criteria = {key: fixture[key] for key in ("pass_condition", "fail_condition")}
        row = compare_probe(result, fixture, probe | criteria, "SYNTHETIC-D50",
                            "SYNTHETIC-D49-dated-gross-cash-multiple-v1",
                            "SYNTHETIC-D50:2027-01-01/2027-07-01")
        rows.append(row | {"note": probe["note"]})
    require(set(packages) == {"cash-out", "cash-in", "above-capacity"} and len(rows) == 3
            and set(references) == {"cash-out", "cash-in"}, "Unexpected refinance pilot inventory")
    return packages, dict(schema="miniuw.synthetic-refinance-pilot-evidence.v1", fixture_sha256=sha(raw),
                          decision="PENDING", criteria_adopted=False, deployment_enabled=False,
                          independent_references=references, cases=rows)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for the three audited refinance variants.")
    args = parser.parse_args()
    try:
        packages, evidence = rehearsal()
        _, sale = sale_rehearsal()
        require(workbook_bytes(sale) == local_file(ROOT, SALE_WORKBOOK).read_bytes(), "Sale-only workbook differs")
        workbook = workbook_bytes(sale, evidence)
        require(workbook == local_file(ROOT, WORKBOOK).read_bytes(), "Common workbook differs from its evidence")
        if args.output is not None:
            target = args.output
            require(not target.exists() and not target.is_symlink() and target.parent.is_dir(), "Use a new pilot output directory")
            with TemporaryDirectory(dir=target.parent, prefix=".miniuw-refi-pilot-") as temp:
                staged = Path(temp) / "piloto"
                for variant, files in packages.items():
                    case_dir = staged / variant
                    case_dir.mkdir(parents=True)
                    for name, content in files.items():
                        (case_dir / name).write_bytes(content)
                    verify_package(case_dir)
                (staged / Path(WORKBOOK).name).write_bytes(workbook)
                (staged / "ensayo_refinanciacion.json").write_bytes(encoded(evidence))
                staged.rename(target)
        print(json.dumps(dict(status="passed", decision=evidence["decision"], cases=len(evidence["cases"]),
                              simulated={row["archive_case"]: row["simulation"] for row in evidence["cases"]},
                              workbook_sha256=sha(workbook)), ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
