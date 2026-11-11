"""Reproduce the one-page USD 10 comparison for the same revised plan."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
from pathlib import Path
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, local_file, require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import _pdf, _pdf_string
from miniuw_worksheet_v1 import build_results, encoded
from plan_refinance_D108 import REFI_DATE
from plan_return_D107 import DATES, SALE_COST_RATE, SALE_DATE, run_scenario
from worksheet_plan_refinance_D109 import SCENARIOS
from worksheet_sale_rate_grid_D84 import money


REQUEST = "templates/synthetic-plan-refinance-request-D109.json"
REPORT = "docs/review/MiniUW_D110_Plano_Revisado_Con_y_Sin_Refinanciacion.pdf"
EVENT_ROWS = (
    ("initial_capital", "Aporte inicial", DATES[0], "contribution"),
    ("additional_capital", "Aporte extra de obra", DATES[1], "contribution"),
    ("net_refinance_distribution", "Cobro neto de refinanciación", REFI_DATE, "distribution"),
    ("operating_distribution", "Cobro de operación", SALE_DATE, "distribution"),
    ("net_sale_distribution", "Cobro neto de venta", SALE_DATE, "distribution"),
)
TOTAL_ROWS = (
    ("total_distributions", "Cobro total", "Hasta la venta", None),
    ("unrecovered_after_sale", "Saldo sin recuperar", "Al vender", None),
)


def summarize_case(view, with_refinance):
    cash = view["cash_per_usd_10"]
    if cash is None:
        return None
    expected = {category: (day, kind) for category, _, day, kind in EVENT_ROWS}
    amounts = {}
    for event in cash["events"]:
        value = _fraction(event["amount"])
        category = event["category"]
        day, kind = event["date"], event["kind"]
        if (category, day, kind, value) == ("additional_capital", SALE_DATE, "contribution", 0):
            continue
        require(expected.get(category) == (day, kind) and category not in amounts and value is not None
                and value >= 0 and event["currency"] == "USD", "Unexpected dated cash flow in the one-page comparison")
        amounts[category] = value
    expected_categories = set(expected)
    if not with_refinance:
        expected_categories.remove("net_refinance_distribution")
    require(set(amounts) == expected_categories, "A required gross cash event is missing")
    amounts.setdefault("net_refinance_distribution", Fraction())
    paid = sum(amounts[key] for key, (_, kind) in expected.items() if kind == "contribution")
    receipts = sum(amounts[key] for key, (_, kind) in expected.items() if kind == "distribution")
    unrecovered = max(Fraction(), paid - receipts)
    require(cash["basis_event_ids"] == ["initial"] and _fraction(cash["reference_amount"]) == amounts["initial_capital"] == 10
            and (paid, receipts, unrecovered) == tuple(_fraction(cash[key]) for key in (
                "total_contributions", "total_distributions", "unrecovered_after_sale")),
            "The USD 10 basis, receipts or recovery does not match the dated ledger")
    amounts.update(total_distributions=receipts, unrecovered_after_sale=unrecovered)
    return {key: rational(value) for key, value in amounts.items()}


def build_comparison(request_raw, *, include_sale_basis=False):
    refinance, _ = build_results(request_raw)
    comparison = refinance["plan_comparison"]
    cases = {}
    for scenario in SCENARIOS:
        funded = refinance["scenarios"][scenario]
        cash_only = run_scenario(comparison, "after", scenario)
        if cash_only["cash_per_usd_10"] is not None and funded["cash_per_usd_10"] is not None:
            require(cash_only["vertical_cost"] == funded["vertical_cost"]
                    and cash_only["gross_sale"] == funded["gross_sale"],
                    "The compared scenarios must retain the same scope and gross sale")
        cases[scenario] = {}
        for label, view in (("without_refinance", cash_only), ("with_refinance", funded)):
            cases[scenario][label] = dict(state=view["state"], blockers=view["blockers"],
                amounts=summarize_case(view, label == "with_refinance"), source_runs=view.get("source_runs"))
            if include_sale_basis:
                cash = view["cash_per_usd_10"]
                cases[scenario][label]["sale_basis"] = None if cash is None else dict(
                    gross_price=view["gross_sale"], sale_cost_rate=rational(SALE_COST_RATE),
                    initial_equity_scale=cash["scale_factor"],
                    debt_principal_paid_at_sale=(view["debt_principal_paid_at_sale"] if label == "with_refinance"
                                                 else rational(0)),
                )
        cases[scenario]["with_refinance"]["capacity"] = funded["capacity"]

    return dict(decision="PENDING", scope="synthetic_aggregate_equity", cases=cases,
                reference_plan_sha256=comparison["reference_sha256"], revised_plan_sha256=comparison["candidate_sha256"],
                refinance_request_sha256=sha(request_raw), refinance_request_id=refinance["request_id"],
                requested_principal_usd=refinance["requested_principal_usd"], refinance_pdf_sha256=refinance["pdf_sha256"])


def render_comparison(comparison):
    commands = []
    labels = []

    def rect(x, y, width, height, color):
        commands.append(f"{color} rg {x} {y} {width} {height} re f".encode())

    def text(x, y, label, size=11, *, bold=False, color="0.08 0.16 0.23", right=False):
        if right:
            x -= len(label) * size * 0.6
        require(25 <= x and x + len(label) * size * 0.6 <= 768 and 25 <= y <= 585, "Text exceeds page")
        font = "F2" if bold else "F1"
        commands.append(f"{color} rg BT /{font} {size} Tf 1 0 0 1 {x} {y} Tm (".encode()
                        + _pdf_string(label) + b") Tj ET")
        labels.append(label)

    columns = [(name, key) for name in SCENARIOS for key in ("without_refinance", "with_refinance")]
    rect(24, 506, 744, 83, "0.06 0.17 0.25")
    text(40, 554, "Si invierto USD 10, ¿cuánto cobro y cuándo?", 20, bold=True, color="1 1 1")
    text(40, 529, "Mini-UW  /  Plano A-601 revisado  /  Datos sintéticos", 11, color="0.87 0.94 0.98")
    whole, cents = money(comparison["requested_principal_usd"]).split(",")
    principal = f"{int(whole):,}".replace(",", ".") + "," + cents
    text(32, 477, f"Con refinanciación se solicitan USD {principal} al nivel del proyecto.", 11)
    text(32, 458, "Todos los flujos de la tabla están expresados en USD por USD 10 iniciales.", 11)
    rect(24, 392, 744, 51, "0.86 0.91 0.95")
    rect(334, 418, 216, 25, "0.75 0.85 0.92")
    rect(550, 418, 218, 25, "0.79 0.88 0.89")
    text(424, 427, "Base", 12, bold=True)
    text(634, 427, "Downside", 12, bold=True)
    text(36, 402, "Flujo", 11, bold=True)
    text(224, 402, "Fecha", 11, bold=True)
    for x, title in zip((355, 466, 572, 683), ("Sin refi", "Con refi", "Sin refi", "Con refi")):
        text(x, 402, title, 11, bold=True)

    rows = EVENT_ROWS + TOTAL_ROWS
    for index, (key, label, day, kind) in enumerate(rows):
        y = 370 - index * 33
        final = kind is None
        if final or index % 2 == 0:
            rect(24, y - 11, 744, 33, "0.90 0.95 0.96" if final else "0.95 0.97 0.98")
        display_date = "/".join(reversed(day.split("-"))) if kind is not None else day
        text(36, y, label, 11, bold=final)
        text(224, y, display_date, 10)
        for (scenario, option), x in zip(columns, (424, 534, 644, 754)):
            amounts = comparison["cases"][scenario][option]["amounts"]
            text(x, y, "PENDING" if amounts is None else money(amounts[key]), 12, bold=final, right=True)

    text(32, 134, "Saldo sin recuperar = aportes totales menos cobros totales, con mínimo de cero.", 10)
    text(32, 117, "Los cobros con refi descuentan la cuota en operación y el saldo de deuda en venta.", 10)
    text(32, 100, "Importes nominales. Cada cifra se redondea por separado.", 10)
    text(32, 63, "D110  /  Capital agregado del proyecto  /  Decisión de inversión PENDING", 10, bold=True)
    pdf = _pdf(commands)
    page, = PdfReader(BytesIO(pdf)).pages
    extracted = page.extract_text()
    require(all(label in extracted for label in labels), "One-page PDF omitted expected text")
    return pdf


def verify(comparison, pdf):
    # The four values are the previously audited scenario totals, rounded only for display.
    expected = {
        ("Base", "without_refinance"): ("12,41", "0,00"),
        ("Base", "with_refinance"): ("12,26", "0,00"),
        ("Downside", "without_refinance"): ("8,08", "2,34"),
        ("Downside", "with_refinance"): ("7,93", "2,49"),
    }
    extracted = PdfReader(BytesIO(pdf)).pages[0].extract_text()
    for (scenario, option), display in expected.items():
        amounts = comparison["cases"][scenario][option]["amounts"]
        require(amounts is not None and (money(amounts["total_distributions"]), money(amounts["unrecovered_after_sale"]))
                == display and money(amounts["additional_capital"]) == "0,42",
                "The comparison differs from the audited revised-plan results")
    for day in (DATES[0], DATES[1], REFI_DATE, SALE_DATE):
        require("/".join(reversed(day.split("-"))) in extracted, "The PDF is missing a cash date")
    for name in SCENARIOS:
        old, new = (comparison["cases"][name][option]["amounts"] for option in ("without_refinance", "with_refinance"))
        require(_fraction(old["total_distributions"]) - _fraction(new["total_distributions"]) == Fraction(143, 960)
                and _fraction(new["net_refinance_distribution"]) == Fraction(539, 120),
                "The nominal cost or earlier refinance proceeds do not reconcile")
    require(comparison["decision"] == "PENDING", "The one-page comparison acquired a real decision")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of checking the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    comparison = build_comparison(local_file(ROOT, REQUEST).read_bytes())
    pdf = render_comparison(comparison)
    verify(comparison, pdf)
    if args.output:
        with args.output.open("xb") as file:
            file.write(pdf)
    else:
        require(local_file(ROOT, REPORT).read_bytes() == pdf, "The versioned PDF differs from exact source replay")
    if args.evidence:
        with args.evidence.open("xb") as file:
            file.write(encoded(comparison | dict(pdf_sha256=sha(pdf), page_count=1)))
    print(json.dumps(dict(status="passed", decision=comparison["decision"], cases=4,
                          page_count=1, pdf_sha256=sha(pdf)), sort_keys=True))


if __name__ == "__main__":
    main()
