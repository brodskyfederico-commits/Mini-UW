"""Reconcile the illustrative Base and Downside report and reject altered evidence."""
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_reference_package import PackageError
from miniuw_worksheet_v1 import build_results, encoded, verify_package, write_package


FIXTURE = "templates/synthetic-investor-scenarios-D75.json"


def verify():
    raw = (ROOT / FIXTURE).read_bytes()
    case = json.loads(raw)
    with TemporaryDirectory(prefix="miniuw-d75-") as directory:
        output = Path(directory) / "comparison"
        written = write_package(raw, output)
        audited = verify_package(output)
        result = json.loads((output / "results.json").read_bytes())
        require(written["pdf_sha256"] == audited["pdf_sha256"] == result["pdf_sha256"]
                and result["decision"] == "PENDING" and result["personal_investor_return"] is None
                and not result["deployment_enabled"] and not result["real_decisions_enabled"],
                "The two-scenario report did not replay or acquired real authority")
        base, downside = (result["scenarios"][name]["cash"] for name in ("Base", "Downside"))
        for cash, refi_receipt, extra in ((base, 2, 0), (downside, 0, Fraction(4, 5))):
            totals = {"distribution": 0, "contribution": 0}
            dated = {}
            for event in cash["events"]:
                value = amount(event["amount"])
                totals[event["kind"]] += value
                dated[event["date"], event["category"]] = value
            require(amount(cash["gross_contributions"]) == totals["contribution"] == 10 + extra
                    and amount(cash["gross_distributions"]) == totals["distribution"]
                    and amount(cash["net_cash_profit"]) == totals["distribution"] - totals["contribution"]
                    and amount(cash["cash_shortfall_at_horizon"])
                    == max(totals["contribution"] - totals["distribution"], 0),
                    "Nominal receipts, contributions and recovery must reconcile")
            require(dated["2027-01-01", "initial_capital"] == 10
                    and dated["2027-04-01", "net_refinance_distribution"] == refi_receipt
                    and dated["2027-04-01", "refinance_cash_in"] == extra
                    and dated["2027-07-01", "additional_capital"] == 0
                    and dated["2027-03-01", "operating_distribution"]
                    == dated["2027-06-01", "operating_distribution"] == 1,
                    "The April cash call and other dated flows differ")
        require(amount(base["gross_distributions"]) - amount(downside["gross_distributions"]) == 4
                and amount(base["cash_shortfall_at_horizon"]) == 0 < amount(downside["cash_shortfall_at_horizon"]),
                "The lower sale and refinance receipt did not flow into the downside shortfall")
        page, = PdfReader(output / "MiniUW_Resumen.pdf").pages
        text = page.extract_text()
        require(text.index("Cobros por USD 10 iniciales") < text.index("Calendario")
                and "Cash-in refi | Base 0.00 | Downside 0.80" in text
                and "Caja sin recuperar al vender | Base USD 0.00 | Downside USD 1.78" in text,
                "The one-page report lost the answer or downside funding and recovery")
        result_path = output / "results.json"
        result_path.write_bytes(encoded(result | {"decision": "PASS"}))
        try:
            verify_package(output)
        except PackageError as error:
            require("source-first replay" in str(error), "Unexpected tampering rejection")
        else:
            raise AssertionError("An altered report was accepted")

    try:
        build_results(encoded(case | {"allocation_terms_sha256": "0" * 64}))
    except PackageError as error:
        require("source bytes differ" in str(error), "Unexpected source rejection")
    else:
        raise AssertionError("An unbound source was accepted")
    return dict(status="passed", decision="PENDING", scenarios=2, report_pages=1,
                downside_requires_additional_funding=True, downside_cash_shortfall=True,
                altered_report_rejected=True, unbound_terms_rejected=True)


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
