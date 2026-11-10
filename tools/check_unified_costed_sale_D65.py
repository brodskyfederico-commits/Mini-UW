"""Exercise C67 and C68 in the public case command and audited one-page output."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call, save


TEMPLATE = ROOT / "templates/synthetic-unified-worksheet-costed-sale-D65.json"
CASES = {"price_400": (400, 30, 20178), "price_500": (500, 35, 20178),
         "explicit_zero": (400, 10, 19169), "missing_cost": (None, None, None), "tax_pending": (400, None, None)}


def verify():
    with TemporaryDirectory(prefix="miniuw-d65-") as temp:
        root = Path(temp)
        template = json.loads(TEMPLATE.read_bytes())
        results = {}
        for key, (price, cost, cents) in CASES.items():
            source, output = root / f"{key}.json", root / key
            save(source, template | {"archive_case": key})
            created = call("run", source, "--output", output)
            audited = call("audit", output)
            result = json.loads((output / "results.json").read_bytes())
            page, = PdfReader(output / "MiniUW_Resumen.pdf").pages
            text = page.extract_text()
            require(created["pdf_sha256"] == audited["pdf_sha256"] == result["pdf_sha256"]
                    and "C67 cap de salida / C68 costo variable de venta" in text
                    and result["decision"] == "PENDING" and result["real_decisions_enabled"] is False,
                    "Costed sale package or one-page output differs")
            cash = result["cash_recovery"]
            closing = result["worksheet_exit"]
            require((None if closing["candidate_price"] is None else amount(closing["candidate_price"]),
                     None if closing["total_cost"] is None else amount(closing["total_cost"])) == (price, cost),
                    "Projected sale or cost differs from the worksheet reference")
            if cents is None:
                require(cash is result["project"] is result["risk"] is None and "Minimo VP USD" not in text,
                        "An incomplete costed sale exposed a return")
            else:
                require(cash["minimum_gross_sale_price_in_cents"] == cents and result["project"] is not None
                        and f"Minimo VP USD {cents / 100:.2f}" in text,
                        "The costed recovery price did not reach the PDF")
            results[key] = result["state"]
    return dict(status="passed", decision="PENDING", audited_pages=len(results), states=results)


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
