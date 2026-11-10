"""Verify the nominal sale target reaches the USD 10 comparison without changing cash."""
from fractions import Fraction
from io import BytesIO
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_reference_package import PackageError
from miniuw_worksheet_v1 import build_package, build_results, encoded


def verify():
    raw = (ROOT / "templates/synthetic-investor-scenarios-D82.json").read_bytes()
    files, result = build_package(raw)
    previous_raw = (ROOT / "templates/synthetic-investor-scenarios-D75.json").read_bytes()
    previous, _ = build_results(previous_raw)
    require(result["scenarios"] == previous["scenarios"] and result["decision"] == "PENDING",
            "Adding the recovery target changed the scenario cash or decision")
    for name, net, gross in (("Base", Fraction(6), Fraction("98.01")),
                             ("Downside", Fraction("8.80"), Fraction("378.01"))):
        target = result["nominal_sale_recovery"][name]
        exact = amount(target["minimum_gross_price_exact"])
        require(amount(target["minimum_net_receipt_per_usd_10"]) == net
                and amount(target["minimum_gross_price_at_cents"]) == gross
                and gross - Fraction(1, 100) < exact <= gross, "Incorrect minimum or cent boundary")
        for key, offset in (("below", -1), ("at", 0), ("above", 1)):
            probe = target["price_probes"][key]
            require(amount(probe["gross_sale_price"]) == exact + offset
                    and amount(probe["net_cash_per_usd_10"]) == Fraction(offset, 100),
                    "Cash failed to cross zero at the bound sale price")
    page, = PdfReader(BytesIO(files["MiniUW_Resumen.pdf"])).pages
    text = page.extract_text()
    require("Cobro neto de venta necesario por USD 10 | Base USD 6.00 | Downside USD 8.80" in text
            and "Precio bruto mínimo del activo | Base USD 98.01 | Downside USD 378.01" in text
            and text.index("Cobros por USD 10 iniciales") < text.index("Precio bruto mínimo"),
            "The PDF lost the initial USD 10 cash answer or sale thresholds")
    case = json.loads(raw)
    invalid = case | {"scenarios": case["scenarios"] | {
        "Downside": "SYNTHETIC-D31-cash-in/SYNTHETIC-sale-funding-required"}}
    try:
        build_results(encoded(invalid))
    except PackageError as error:
        require("different sale cost or funding structure" in str(error), "Unexpected incompatible anchor rejection")
    else:
        raise AssertionError("A recovery target from incompatible sale terms was reused")
    return dict(status="passed", decision="PENDING", scenarios=2, recovery_probes=6,
                one_page_report=True, incompatible_sale_terms_rejected=True)


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
