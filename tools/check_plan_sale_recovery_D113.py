"""Check the audited sale minimum, including payoff, sale costs and capacity withholding."""
from argparse import ArgumentParser
from fractions import Fraction
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_integral_miniuw_D102 import audit_case
from check_operating_replay_D20 import ROOT, amount, require
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import encoded
from worksheet_plan_refinance_D109 import CAPACITY_BLOCKER


FIXTURE = ROOT / "templates/synthetic-plan-sale-recovery-D113.json"


def independent_minimum(name, rate, principal):
    noi = Fraction("257815.2") if name == "Base" else Fraction(201180)
    factor = 1 + rate
    payment = principal * Fraction(1, 80) / (1 - Fraction(81, 80) ** -40)
    interest = Fraction(principal, 80)
    payoff = principal - payment + interest
    refi_receipt = Fraction(principal * 98, 100 * 240000)
    net = 10 * factor ** 15 + Fraction(5, 12) * factor ** 12 - refi_receipt * factor ** 3 - (noi - payment) / 240000
    return net, (net * 240000 + payoff) / Fraction(95, 100)


def verify(temp, saved_output):
    case = json.loads(FIXTURE.read_bytes())
    request = case["refinance_request"]
    complete, page = audit_case(FIXTURE, saved_output or temp / "available")
    require("Neto de venta mínimo por USD 10" in page and "Venta bruta mínima del proyecto" in page,
            "The one-page comparison omitted a sale recovery figure")
    zero_case = temp / "zero-rate.json"
    zero_case.write_bytes(encoded(case | {"monthly_discount_rate": rational(0)}))
    zero, _ = audit_case(zero_case, temp / "zero-rate")

    blocked_case = temp / "blocked.json"
    blocked_case.write_bytes(encoded(case | {"refinance_request": request | {
        "request_id": "SYNTHETIC-D113-blocked-1400000", "requested_principal_usd": rational(1400000)
    }}))
    blocked, blocked_page = audit_case(blocked_case, temp / "blocked")
    require(blocked["state"] == "PENDING" and "Downside | Comparación PENDING" in blocked_page,
            "A capacity-blocked alternative lost its status")

    checked = 0
    for result, rate, principal in ((complete, Fraction(1, 50), 1100000),
                                    (zero, Fraction(), 1100000),
                                    (blocked, Fraction(1, 50), 1400000)):
        for name, scenario in result["scenarios"].items():
            for label, view in scenario["alternatives"].items():
                recovery = view["sale_recovery"]
                if result is blocked and name == "Downside" and label == "with_refinance":
                    require(recovery is None and view["sale_basis"] is None
                            and view["blockers"] == [CAPACITY_BLOCKER], "Blocked capacity acquired a sale minimum")
                    continue
                p = 0 if label == "without_refinance" else principal
                net, gross = independent_minimum(name, rate, p)
                gross_cents = Fraction(ceil(100 * gross), 100)
                require(amount(recovery["minimum_net_sale_per_usd_10"]) == net
                        and amount(recovery["minimum_gross_sale_exact"]) == gross
                        and amount(recovery["minimum_gross_sale_at_cents"]) == gross_cents
                        and amount(recovery["net_present_value_one_cent_below"]) < 0
                        <= amount(recovery["net_present_value_at_minimum_gross_cents"]),
                        "The minimum recovery price or adjacent cent disagrees with the independent dated formula")
                checked += 1
    return dict(status="passed", decision="PENDING", discounted_recovery_cases=checked,
                capacity_blocked_cases=1, page_count=1, pdf_sha256=complete["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the verified one-page worksheet package.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d113-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
