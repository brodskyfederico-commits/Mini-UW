"""Adapt the verified worksheet sale bridge to the unified case and one-page report."""
import json

from check_operating_replay_D20 import ROOT, amount, local_file
from check_worksheet_exit_D62 import FIXTURE as EXIT
from check_worksheet_refinance_D45 import render_case
from check_worksheet_sale_costs_D63 import run


def build_costed_case(key, rate, *, diagnostics=False, terms_hash=None, investor_id=None):
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
    if terms_hash is not None:
        from worksheet_participation_D68 import build_participation
        report["synthetic_cash_participation"] = build_participation(key, report.get("allocation_parent"), terms_hash)
    if investor_id is not None:
        from worksheet_investor_D74 import investor_view, render_investor
        view = investor_view(report["synthetic_cash_participation"], investor_id)
        report["illustrative_investor"] = view
        return report, render_investor(key, view, report["sale_blockers"])
    return report, render_case(key, report, sale_diagnostics=diagnostics)
