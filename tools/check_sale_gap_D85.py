"""Verify that the one-page USD 10 comparison shows the net sale cash gaps."""
from fractions import Fraction
from io import BytesIO
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from miniuw_worksheet_v1 import build_package
from worksheet_sale_rate_grid_D84 import money


def verify():
    raw = (ROOT / "templates/synthetic-investor-scenarios-D85.json").read_bytes()
    files, result = build_package(raw)
    comparison = result["sale_cash_comparison"]
    require(comparison["sale_date"] == "2027-07-01" and result["decision"] == "PENDING",
            "Unexpected scenario date or decision")
    expected = [
        (Fraction(0), ("6.00", "3.02"), ("8.80", "-1.78")),
        (Fraction(1, 100), ("6.51", "2.51"), ("9.39", "-2.37")),
        (Fraction(1, 50), ("7.04", "1.98"), ("10.01", "-2.99")),
    ]
    for row, (rate, base, downside) in zip(comparison["monthly_rates"], expected, strict=True):
        require(amount(row["monthly_rate"]) == rate, "Unexpected discount rate")
        for name, (minimum, difference), received in (
            ("Base", base, Fraction(54662401, 6060200)),
            ("Downside", downside, Fraction(42542001, 6060200)),
        ):
            values = row["scenarios"][name]
            require(amount(values["net_sale_received"]) == received
                    and amount(values["minimum_net_sale_at_cents"]) == Fraction(minimum)
                    and amount(values["cash_difference_at_sale"]) == received - Fraction(minimum)
                    and money(values["cash_difference_at_sale"]) == difference.replace(".", ",")
                    and values["state"] == ("surplus" if name == "Base" else "shortfall"),
                    "The signed cash gap at sale differs from the independent comparison")
    page, = PdfReader(BytesIO(files["MiniUW_Resumen.pdf"])).pages
    text = page.extract_text()
    require(all(line in text for line in (
        "La venta del escenario deja por USD 10 | Base USD 9,02 | Downside USD 7,02",
        "0,00% | Base 6,00, sobran 3,02 | Downside 8,80, faltan 1,78",
        "1,00% | Base 6,51, sobran 2,51 | Downside 9,39, faltan 2,37",
        "2,00% | Base 7,04, sobran 1,98 | Downside 10,01, faltan 2,99",
        "2027-04-01 Cash-in refi | Base 0,00 | Downside -0,80",
    )) and text.index("Cobros por USD 10 iniciales") < text.index("0,00% |"),
            "The PDF lost an answer, rate, sign or dated contribution")
    return dict(status="passed", decision="PENDING", rates=3, scenario_comparisons=6, one_page_report=True)


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
