"""Check the six independently derived thresholds and the PDF rate comparison."""
from fractions import Fraction
from io import BytesIO
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_reference_package import PackageError
from miniuw_worksheet_v1 import build_package, build_results, encoded


def verify():
    raw = (ROOT / "templates/synthetic-investor-scenarios-D84.json").read_bytes()
    files, result = build_package(raw)
    grid = result["rate_sensitivity"]
    require(grid["discount_date"] == "2027-01-01" and grid["sale_date"] == "2027-07-01"
            and result["decision"] == "PENDING", "Unexpected sensitivity period or decision")
    expected = [("0", "6.00", "8.80"), ("0.01", "6.51", "9.39"), ("0.02", "7.04", "10.01")]
    for row, (rate, base, downside) in zip(grid["monthly_rates"], expected, strict=True):
        f = 1 + Fraction(rate)
        require(amount(row["rate"]) == Fraction(rate), "Unexpected rate")
        exact_base = 10*f**6 - f**4 - 2*f**3 - f
        exact_downside = 10*f**6 - f**4 + Fraction(4, 5)*f**3 - f
        for name, shown, exact in (("Base", base, exact_base), ("Downside", downside, exact_downside)):
            value = row["scenarios"][name]
            cent = Fraction(shown)
            require(amount(value["net_at_sale_exact"]) == exact
                    and amount(value["net_receipt_present_value"]) == exact / f**6
                    and amount(value["net_at_sale_cents"]) == cent
                    and cent - Fraction(1, 100) < exact <= cent,
                    "Independent discounted cash or minimum-cent calculation differs")
    page, = PdfReader(BytesIO(files["MiniUW_Resumen.pdf"])).pages
    text = page.extract_text()
    require(all(line in text for line in (
        "0,00% mensual | Base USD 6,00 | Downside USD 8,80",
        "1,00% mensual | Base USD 6,51 | Downside USD 9,39",
        "2,00% mensual | Base USD 7,04 | Downside USD 10,01",
        "2027-04-01 Cash-in refi | Base 0,00 | Downside -0,80",
    )) and text.index("Cobros por USD 10 iniciales") < text.index("0,00% mensual"),
            "The one-page output lost a rate, cash requirement or lead answer")
    case = json.loads(raw)
    try:
        build_results(encoded(case | {"monthly_rates": case["monthly_rates"][:-1]}))
    except PackageError as error:
        require("explicit three-rate" in str(error), "Unexpected incomplete rate-grid rejection")
    else:
        raise AssertionError("A partial rate grid was silently accepted")
    return dict(status="passed", decision="PENDING", scenarios=2, rates=3, zero_pv_closings=6,
                one_page_report=True, incomplete_rate_grid_rejected=True)


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
