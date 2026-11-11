"""Check the revised-plan request through the worksheet CLI and its one-page audit."""
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
from plan_refinance_D108 import run_scenario as run_refinance
from plan_return_D107 import run_scenario as run_cash_only
from worksheet_plan_refinance_D109 import CAPACITY_BLOCKER


FIXTURE = ROOT / "templates/synthetic-plan-refinance-request-D109.json"


def check_cash(scenario, view, plan):
    annual_noi, exit_cap = (Fraction("257815.2"), Fraction(9, 100)) if scenario == "Base" else (
        Fraction(201180), Fraction(11, 100))
    principal = 1100000
    payment = principal * Fraction(1, 80) / (1 - Fraction(81, 80) ** -40)
    payoff = principal - payment + Fraction(13750)
    scale = Fraction(1, 240000)
    sale = (annual_noi * Fraction(95, 100) / exit_cap - payoff) * scale
    cash = view["cash_per_usd_10"]
    events = [(e["date"], e["kind"], e["category"], amount(e["amount"])) for e in cash["events"] if amount(e["amount"])]
    expected = [
        ("2027-03-30", "contribution", "initial_capital", 10),
        ("2027-06-30", "contribution", "additional_capital", 100000 * scale),
        ("2028-03-30", "distribution", "net_refinance_distribution", 1078000 * scale),
        ("2028-06-30", "distribution", "operating_distribution", (annual_noi - payment) * scale),
        ("2028-06-30", "distribution", "net_sale_distribution", sale),
    ]
    require(events == expected and cash["basis_event_ids"] == ["initial"],
            f"{scenario} request changed the USD 10 basis or dated cash")
    invested = Fraction(2500000) * scale
    received = sum(e[3] for e in expected if e[1] == "distribution")
    require([amount(cash[key]) for key in ("total_contributions", "total_distributions", "unrecovered_after_sale")]
            == [invested, received, max(0, invested - received)], f"{scenario} total or unrecovered cash differs")
    cash_only = run_cash_only(plan, "after", scenario)["cash_per_usd_10"]
    require(amount(cash_only["total_distributions"]) - received == (22000 + 13750) * scale,
            "The same-plan nominal cash difference must reconcile to refinance fee and interest")


def verify(temp, saved_output):
    request = json.loads(FIXTURE.read_bytes())
    revised, page = audit_case(FIXTURE, saved_output or temp / "revised")
    require(revised["state"] == "computed_synthetic_scenario_cash" and revised["case_sha256"] == sha(FIXTURE.read_bytes())
            and revised["request_id"] == request["request_id"] and amount(revised["requested_principal_usd"]) == 1100000
            and "Cobro neto de refinanciación USD 4,49" in page,
            "The smaller request must produce an auditable one-page case")
    plan = revised["plan_comparison"]
    for scenario, view in revised["scenarios"].items():
        require(view["state"] == "computed_synthetic"
                and amount(view["capacity"]["selected_principal"]) == 1100000
                and amount(view["capacity_margin_usd"]) == amount(view["capacity"]["maximum_principal_capacity"]) - 1100000
                and amount(view["capacity_margin_usd"]) > 0, f"{scenario} missed the explicit smaller request")
        check_cash(scenario, view, plan)

    original_request = request | dict(request_id="SYNTHETIC-D108-request-1400000",
                                       requested_principal_usd=rational(1400000))
    original_raw = encoded(original_request)
    original_case = temp / "original.json"
    original_case.write_bytes(original_raw)
    output = temp / "original"
    original, original_page = audit_case(original_case, output)
    downside = original["scenarios"]["Downside"]
    expected_blocked = run_refinance(plan, "after", "Downside")
    require(original["state"] == "PENDING" and "Downside | Retorno por USD 10 PENDING" in original_page
            and "Downside | Por USD 10 iniciales cobrás" not in original_page
            and downside["blockers"] == [CAPACITY_BLOCKER] and downside["cash_per_usd_10"] is None
            and downside["capacity"] == expected_blocked["capacity"]
            and original["scenarios"]["Base"]["state"] == "computed_synthetic"
            and original["pdf_sha256"] != revised["pdf_sha256"],
            "The original blocked case was overwritten or suppressed its available Base")
    call("run", FIXTURE, "--output", output, blocked=True)
    require(call("audit", output)["status"] == "verified_source_first"
            and (output / "case.json").read_bytes() == original_raw, "The new request replaced the old package")

    invalid = (
        request | {"revised_plan_sha256": request["reference_plan_sha256"]},
        request | {"requested_principal_usd": None},
        request | {"requested_principal_usd": rational(0)},
        request | {"requested_principal_usd": rational(Fraction(110000001, 1000))},
        request | {"request_id": "actual-project"},
    )
    for index, bad in enumerate(invalid):
        path, directory = temp / f"bad-{index}.json", temp / f"bad-{index}"
        path.write_bytes(encoded(bad))
        call("run", path, "--output", directory, blocked=True)
        require(not directory.exists(), "A rejected request produced an output")

    results = output / "results.json"
    results.write_bytes(encoded(original | {"requested_principal_usd": rational(1100000)}))
    call("audit", output, blocked=True)
    return dict(status="passed", decision="PENDING", dated_cash_cases=2, capacity_blocked_cases=1,
                invalid_requests_rejected=len(invalid), tampered_package_rejected=True, one_page_report=True,
                pdf_sha256=revised["pdf_sha256"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the verified one-page package for the revised request.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d109-") as temp:
        print(json.dumps(verify(Path(temp), args.output), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
