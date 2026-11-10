"""Verify the per-USD-10 example and the pending path."""
from fractions import Fraction
from io import BytesIO
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from miniuw_worksheet_v1 import build_package, encoded
from worksheet_investor_D74 import investor_view


def verify():
    fixture = json.loads((ROOT / "templates/synthetic-unified-worksheet-investor-D74.json").read_bytes())
    files, result = build_package(encoded(fixture))
    cash = result["illustrative_investor"]["cash"]
    sale = Fraction(54056381, 6060200)
    require(amount(cash["initial_capital"]) == amount(cash["gross_contributions"]) == 10
            and amount(cash["gross_distributions"]) == 4 + sale
            and amount(cash["net_cash_profit"]) == sale - 6,
            "Illustrative initial contribution, receipts or profit differ")
    expected = {
        ("2027-01-01", "initial_capital"): 10,
        ("2027-03-01", "operating_distribution"): 1,
        ("2027-04-01", "net_refinance_distribution"): 2,
        ("2027-04-01", "refinance_cash_in"): 0,
        ("2027-06-01", "operating_distribution"): 1,
        ("2027-07-01", "net_sale_distribution"): sale,
        ("2027-07-01", "additional_capital"): 0,
    }
    require(len(cash["events"]) == len(expected)
            and {(e["date"], e["category"]): amount(e["amount"]) for e in cash["events"]} == expected,
            "Illustrative amounts did not preserve event dates and categories")
    require(amount(cash["sale_share_of_distributions"]) == sale / (sale + 4)
            and result["decision"] == "PENDING" and result["personal_investor_return"] is None,
            "Sale dependence or operational decision differs")
    page, = PdfReader(BytesIO(files["MiniUW_Resumen.pdf"])).pages
    text = page.extract_text()
    require(text.index("cobros USD 12.92 | Ganancia neta USD 2.92") < text.index("Calendario de aportes"),
            "Investor answer must come before the calendar")

    participant = result["synthetic_cash_participation"]["participants"][0]
    zero = participant | {"cash_by_category": participant["cash_by_category"] | {
        "initial_capital": {"numerator": "0", "denominator": "1"}}}
    pending = investor_view(result["synthetic_cash_participation"] | {"participants": [zero]},
                            fixture["illustrative_investor_id"])
    require(pending["state"] == "PENDING" and pending["cash"] is None
            and pending["blockers"] == ["positive_initial_capital_required"],
            "Zero initial equity cannot be used as a denominator")

    for blocked_case in ("missing_cost", "tax_pending"):
        blocked_files, blocked = build_package(encoded(fixture | {"archive_case": blocked_case}))
        view = blocked["illustrative_investor"]
        require(view["state"] == "PENDING" and view["cash"] is None and view["blockers"],
                "Blocked sale exposed an illustrative return")
        blocked_page, = PdfReader(BytesIO(blocked_files["MiniUW_Resumen.pdf"])).pages
        require("Retorno por USD 10 pendiente" in blocked_page.extract_text(),
                "Blocked report did not explain pending return")
    return dict(status="passed", decision="PENDING", dated_events=len(cash["events"]),
                blocked_sales=2, zero_initial_capital_blocked=True)


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
