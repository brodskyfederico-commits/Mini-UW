"""Audit USD 10 cash and discounted gaps at USD 300 after four-to-six-month delays."""
from argparse import ArgumentParser
from pathlib import Path
import json

from check_operating_replay_D20 import ROOT, require
from extended_holding_sale_D99 import verify as extended_cases
from fixed_sale_holding_grid_D98 import fixed_price_cases, render_report
from miniuw_worksheet_v1 import encoded


REPORT = "docs/review/MiniUW_D100_Venta_300_Demora_4_6_Meses_USD10.pdf"


def build_report():
    return render_report(fixed_price_cases(extended_cases()), "D100")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of auditing the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pdf, result = build_report()
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(pdf)
    else:
        require((ROOT / REPORT).read_bytes() == pdf, "The one-page report differs from source replay")
    if args.evidence:
        with args.evidence.open("xb") as stream:
            stream.write(encoded(result))
    scenarios = [s for row in result["rows"] for s in row["scenarios"]]
    print(json.dumps(dict(status=result["status"], decision=result["decision"], closings=len(scenarios),
                          combinations=sum(len(s["gaps"]) for s in scenarios), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
