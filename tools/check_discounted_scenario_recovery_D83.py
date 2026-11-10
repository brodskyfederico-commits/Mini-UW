"""Independently verify the time-value cash recovery shown in the one-page comparison."""
from fractions import Fraction
from io import BytesIO
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_reference_package import PackageError
from miniuw_worksheet_v1 import build_package, build_results, encoded


def verify():
    raw = (ROOT / "templates/synthetic-investor-scenarios-D83.json").read_bytes()
    files, result = build_package(raw)
    prior, _ = build_results((ROOT / "templates/synthetic-investor-scenarios-D82.json").read_bytes())
    require(result["scenarios"] == prior["scenarios"]
            and result["nominal_sale_recovery"] == prior["nominal_sale_recovery"]
            and result["decision"] == "PENDING", "Discounting changed the underlying scenario cash")
    check = result["discounted_sale_recovery"]
    rate = Fraction(1, 100)
    require(amount(check["monthly_rate"]) == rate and check["discount_date"] == "2027-01-01",
            "The declared synthetic rate or discount date differs")
    f = 1 + rate
    expected = {"Base": (10 * f**6 - f**4 - 2 * f**3 - f, "6.51", "148.41"),
                "Downside": (10 * f**6 - f**4 + Fraction(4, 5) * f**3 - f, "9.39", "436.90")}
    for name, (due, due_cents, gross_cents) in expected.items():
        row = check["scenarios"][name]
        exact_gross = amount(row["minimum_gross_price_exact"])
        require(row["months_to_sale"] == 6 and row["sale_date"] == "2027-07-01"
                and amount(row["minimum_net_receipt_at_sale_exact"]) == due
                and amount(row["minimum_net_receipt_present_value"]) == due / f**6
                and amount(row["minimum_net_receipt_at_sale_cents"]) == Fraction(due_cents)
                and amount(row["minimum_gross_price_at_cents"]) == Fraction(gross_cents)
                and Fraction(gross_cents) - Fraction(1, 100) < exact_gross <= Fraction(gross_cents),
                "Incorrect discounted net or gross threshold")
        for key, offset in (("below", -1), ("at", 0), ("above", 1)):
            probe = row["price_probes"][key]
            require(amount(probe["gross_sale_price"]) == exact_gross + offset
                    and amount(probe["net_present_value_per_usd_10"]) == Fraction(offset, 100) / f**6,
                    "The verified closing failed to cross zero in present value")
    page, = PdfReader(BytesIO(files["MiniUW_Resumen.pdf"])).pages
    text = page.extract_text()
    require("Descuento sintético: 1.00% mensual | Corte 2027-01-01" in text
            and "Cobro neto necesario al vender por USD 10 | Base USD 6.51 | Downside USD 9.39" in text
            and text.index("Cobros por USD 10 iniciales") < text.index("Descuento sintético"),
            "The USD 10 answer or discount basis is missing in the one-page report")
    case = json.loads(raw)
    try:
        build_results(encoded(case | {"monthly_discount_rate": {"numerator": "2", "denominator": "100"}}))
    except PackageError as error:
        require("An exact rate" in str(error), "The unbound rate was rejected for an unexpected reason")
    else:
        raise AssertionError("An unbound rate was accepted")
    return dict(status="passed", decision="PENDING", scenarios=2, discounted_probes=6,
                one_page_report=True, unbound_rate_rejected=True, monthly_rate="1/100")


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
