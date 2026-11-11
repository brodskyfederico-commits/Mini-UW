"""Verify the selected-rate comparison from worksheet input through PDF and audit."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_integral_miniuw_D102 import audit_case
from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_plan_refinance_D109 import CAPACITY_BLOCKER


FIXTURE = ROOT / "templates/synthetic-plan-discount-comparison-D112.json"


def expected_npv(name, rate, principal):
    annual_noi, cap = {"Base": (Fraction("257815.2"), Fraction(9, 100)),
                       "Downside": (Fraction(201180), Fraction(11, 100))}[name]
    operating_and_sale = (annual_noi + annual_noi / cap * Fraction(95, 100)) / 240000
    discount = 1 + rate
    without = -10 - Fraction(5, 12) / discount ** 3 + operating_and_sale / discount ** 15
    early = Fraction(principal, 240000) * Fraction(98, 100)
    sale_day_reduction = Fraction(principal, 240000) * Fraction(81, 80)
    return without, without + early / discount ** 12 - sale_day_reduction / discount ** 15


def case_for(template, principal, rate):
    request = template["refinance_request"] | dict(request_id=f"SYNTHETIC-D112-{principal}",
                                                 requested_principal_usd=rational(principal))
    return template | dict(refinance_request=request, monthly_discount_rate=rational(rate))


def verify(temp, saved_output):
    template = json.loads(FIXTURE.read_bytes())
    good, text = audit_case(FIXTURE, saved_output or temp / "two-percent")
    require(good["case_sha256"] == sha(FIXTURE.read_bytes()) and "Tasa de descuento 2,0000 % mensual" in text
            and "Base | Mayor VAN: con refi" in text and "Downside | Mayor VAN: con refi" in text,
            "The one-page report omitted the selected monthly rate or exact ranking")
    require(good["provenance"]["refinance_request_sha256"] == sha(encoded(template["refinance_request"]))
            and good["provenance"]["revised_plan_sha256"] == template["refinance_request"]["revised_plan_sha256"],
            "The report lost its request or plan evidence")

    combinations = (
        ("two-percent", 1100000, Fraction(1, 50), {"Base", "Downside"}),
        ("zero-rate", 1100000, Fraction(), {"Base", "Downside"}),
        ("downside-blocked", 1400000, Fraction(1, 50), {"Base"}),
        ("both-blocked", 2000000, Fraction(1, 50), set()),
    )
    available = 0
    for label, principal, rate, compatible in combinations:
        if label == "two-percent":
            result, page = good, text
        else:
            path = temp / f"{label}.json"
            path.write_bytes(encoded(case_for(template, principal, rate)))
            result, page = audit_case(path, temp / label)
        require(amount(result["monthly_discount_rate"]) == rate
                and amount(result["requested_principal_usd"]) == principal
                and result["state"] == ("computed_synthetic_scenario_cash" if len(compatible) == 2 else "PENDING"),
                "The stated rate, principal or availability changed")
        if not rate:
            require("Tasa de descuento 0,0000 % mensual" in page, "Explicit zero rate did not reach the PDF")
        for name, scenario in result["scenarios"].items():
            without, with_refi = (scenario["alternatives"][key] for key in ("without_refinance", "with_refinance"))
            expected_without, expected_with = expected_npv(name, rate, principal)
            require(without["state"] == "computed_synthetic" and amount(without["npv_per_usd_10"]) == expected_without,
                    "The no-refinance branch lost cash or the correct monthly discount")
            require(amount(without["amounts"]["initial_capital"]) == 10
                    and amount(without["amounts"]["additional_capital"]) == Fraction(5, 12),
                    "The one-page comparison changed the contribution basis")
            available += 1
            if name in compatible:
                expected_higher = "without_refinance" if not rate else "with_refinance"
                require(scenario["state"] == "computed_synthetic" and scenario["higher_npv"] == expected_higher
                        and amount(with_refi["npv_per_usd_10"]) == expected_with
                        and amount(scenario["refi_minus_no_refi"]) == expected_with - expected_without,
                        "The with-refi branch differs from independent discounted cash")
                available += 1
            else:
                require(scenario["state"] == "PENDING" and with_refi["blockers"] == [CAPACITY_BLOCKER]
                        and with_refi["npv_per_usd_10"] is None and with_refi["amounts"] is None
                        and scenario["refi_minus_no_refi"] is None and scenario["higher_npv"] is None
                        and f"{name} | Comparación PENDING. Capacidad" in page
                        and f"{name} | Mayor VAN" not in page,
                        "A blocked refinance obtained a VAN, a preference or fallback cash")

    invalid = (
        {key: value for key, value in template.items() if key != "monthly_discount_rate"},
        template | {"monthly_discount_rate": None},
        template | {"monthly_discount_rate": rational(Fraction(-1, 100))},
        template | {"monthly_discount_rate": {"numerator": "1", "denominator": "0"}},
        template | {"refinance_request": {"schema": template["schema"]}},
    )
    for index, bad in enumerate(invalid):
        path = temp / f"bad-{index}.json"
        path.write_bytes(encoded(bad))
        output = temp / f"bad-{index}"
        call("run", path, "--output", output, blocked=True)
        require(not output.exists(), "An invalid discount case wrote output")
    return dict(status="passed", decision="PENDING", worksheet_cases=len(combinations),
                available_discounted_variants=available, invalid_inputs_rejected=len(invalid),
                page_count=1, pdf_sha256=good["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the verified 2% worksheet package.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d112-") as temp:
        print(json.dumps(verify(Path(temp), args.output), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
