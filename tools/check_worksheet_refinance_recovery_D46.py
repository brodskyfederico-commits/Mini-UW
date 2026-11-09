"""Verify that the refinanced worksheet page carries the recovery price from its own dated cash."""
from fractions import Fraction
from io import BytesIO
import json
import sys

from pypdf import PdfReader

from check_discount_rate_crossover_D35 import CASH_IN, LOW, run as price_reference
from check_operating_replay_D20 import require
from check_worksheet_refinance_D45 import replay
from check_worksheet_sale_recovery_D43 import worksheet_bindings
from miniuw_foundation.drafts import canonical, digest


def run():
    _, rates = worksheet_bindings()
    reference = price_reference()
    variants = {"cash-out": LOW, "cash-in": CASH_IN}
    reports = {}
    for rate in (rates[0], rates[-1]):
        for name, row, pdf in replay(monthly_rate=rate):
            recovery = row["cash_recovery"]
            page, = PdfReader(BytesIO(pdf)).pages
            text = page.extract_text()
            require(row["decision"] == "PENDING", "Recovery sensitivity acquired a decision")
            if name in variants:
                sample, = (sample for sample in reference["by_sale_closing_cost"][recovery["fixed_sale_closing_costs"]]
                           if Fraction(sample["monthly_rate"]) == rate)
                require(Fraction(recovery["minimum_gross_sale_price"]) == Fraction(sample["prices"][variants[name]])
                        and "Minimo VP USD " in text, "Worksheet recovery differs from the separately replayed sale")
            else:
                require(recovery is None and row["return_story"] is None and "Minimo VP USD " not in text
                        and "Precio de recuperacion en valor presente: Pendiente." in text,
                        "A blocked worksheet or loan exposed a recovery price")
            reports[f"{name}/{rate}"] = dict(state=row["state"], pdf_sha256=row["pdf_sha256"], recovery=recovery)
    require(len(reports) == 14, "Unexpected refinance recovery page inventory")
    return dict(status="passed", decision="PENDING", worksheet_refinance_recovery_sha256=digest(canonical(reports)),
                pages=len(reports), computed=sum(row["recovery"] is not None for row in reports.values()),
                pending=sum(row["recovery"] is None for row in reports.values()))


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
