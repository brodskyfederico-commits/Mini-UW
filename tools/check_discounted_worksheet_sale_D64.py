"""Verify the worksheet recovery price accounts for percentage sale costs."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
import json
import sys

from check_operating_replay_D20 import require
from check_worksheet_sale_costs_D63 import run
from check_worksheet_sale_recovery_D43 import worksheet_bindings
from miniuw_linked_cotejo_D54 import publish
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.scheduled_expense_case import sha


def verify():
    _, grid = worksheet_bindings()
    rates = (grid[0], grid[-1])
    result = run(rates)
    cases = result["cases"]
    require(cases["price_400"]["recovery"] == cases["price_500"]["recovery"],
            "Changing the starting sale price moved the same recovery boundary")
    for rate in map(str, rates):
        percent = cases["price_400"]["recovery"][rate]
        zero = cases["explicit_zero"]["recovery"][rate]
        require(Fraction(percent["minimum_gross_price"]) > Fraction(zero["minimum_gross_price"])
                and Fraction(percent["probes"]["0"]["net_present_value"]) == 0
                and Fraction(zero["probes"]["0"]["net_present_value"]) == 0,
                "Percentage cost did not increase the exact recovery price")
    require(cases["missing_cost"]["recovery"] is cases["tax_pending"]["recovery"] is None,
            "Incomplete sale costs produced a recovery price")
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify()
        if args.output is not None:
            publish(args.output, result)
        cases = result["cases"]
        print(json.dumps(dict(status="passed", decision="PENDING", cases=len(cases), calculated=3, pending=2,
                              cents_at_two_percent=cases["price_400"]["recovery"]["1/50"]["minimum_gross_price_in_cents"],
                              zero_cost_fraction_cents_at_two_percent=cases["explicit_zero"]["recovery"]["1/50"]["minimum_gross_price_in_cents"],
                              evidence_sha256=sha(encoded(result))), ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
