"""Adapt the verified worksheet sale bridge to the unified case and one-page report."""
import json

from check_operating_replay_D20 import ROOT, amount, local_file
from check_worksheet_exit_D62 import FIXTURE as EXIT
from check_worksheet_refinance_D45 import render_case
from check_worksheet_sale_costs_D63 import run


def build_costed_case(key, rate, *, diagnostics=False):
    row = run((rate,), selected=key, with_report=True)
    origin = json.loads(local_file(ROOT, EXIT).read_bytes())
    report = row.get("report", dict(decision="PENDING", worksheet=row["worksheet"],
                                   context=origin["scenario_context"], evaluated_as_of_UTC=origin["worksheet_as_of_UTC"],
                                   capacity=None, refinance=None, return_story=None, risk=None))
    price = row["candidate_price"]
    recovery = row["recovery"]
    sensitivity = None
    if recovery is not None:
        sensitivity = recovery[str(rate)].copy()
        sensitivity.update(gross_sale_price=str(amount(price)), monthly_discount_rate=str(rate),
                           minimum_gross_sale_price=sensitivity.pop("minimum_gross_price"),
                           minimum_gross_sale_price_in_cents=sensitivity.pop("minimum_gross_price_in_cents"))
    report.update(
        worksheet_exit={"candidate_price": price, "total_cost": row["total_cost"]},
        cash_recovery=sensitivity,
        costed_sale_sha256=row.get("costed_sale_sha256"),
        sale_blockers=row["blockers"],
    )
    return report, render_case(key, report, sale_diagnostics=diagnostics)
