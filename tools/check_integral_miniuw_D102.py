"""Run the synthetic Mini-UW workflow and check USD 10 cash against independent expectations."""
from argparse import ArgumentParser
from collections import Counter
from datetime import date
from fractions import Fraction
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import TEMPLATES, call, verify_case
from check_worksheet_refinance_D45 import render_page
from holding_cash_funding_boundary_D101 import verify as holding_funding_cases
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D102_Verificacion_Integral_USD10.pdf"
SCENARIO = ROOT / "templates/synthetic-investor-scenarios-D82.json"
INITIAL_DATE = "2027-01-01"
SALE_DATE = "2027-07-01"

# Independent fixture expectations, in USD per USD 10 of initial equity.
COMMON_EVENTS = (
    (INITIAL_DATE, "contribution", "initial_capital", Fraction(10)),
    ("2027-03-01", "distribution", "operating_distribution", Fraction(1)),
    ("2027-06-01", "distribution", "operating_distribution", Fraction(1)),
)
EXPECTED = {
    "Base": (("2027-04-01", "distribution", "net_refinance_distribution", Fraction(2)),
             Fraction(54662401, 6060200), Fraction(400), Fraction(6), Fraction("98.01")),
    "Downside": (("2027-04-01", "contribution", "refinance_cash_in", Fraction("0.80")),
                 Fraction(42542001, 6060200), Fraction(200), Fraction("8.80"), Fraction("378.01")),
}


def audit_case(path, output):
    written = call("run", path, "--output", output)
    audited = call("audit", output)
    result = json.loads((output / "results.json").read_bytes())
    pdf = output / "MiniUW_Resumen.pdf"
    page, = PdfReader(pdf).pages
    text = page.extract_text()
    require(written["status"] == "written_synthetic_package" and audited["status"] == "verified_source_first"
            and result["decision"] == "PENDING" and result["personal_investor_return"] is None
            and result["deployment_enabled"] is result["real_decisions_enabled"] is False
            and written["pdf_sha256"] == audited["pdf_sha256"] == result["pdf_sha256"] == sha(pdf.read_bytes())
            and (output / "case.json").read_bytes() == path.read_bytes() and "PENDIENTE" in text,
            "The CLI failed to preserve the input, output or decision guard")
    return result, text


def verify_cash_cases(temp):
    result, text = audit_case(SCENARIO, temp / "comparison")
    require(result["state"] == "computed_synthetic_scenario_cash"
            and set(result["scenarios"]) == EXPECTED.keys()
            and "Cobros por USD 10 iniciales" in text and "Caja sin recuperar al vender" in text,
            "The comparison is missing the USD 10 answer")
    checked = {}
    for name, (refinance, sale, gross_price, needed, rounded_minimum) in EXPECTED.items():
        cash = result["scenarios"][name]["cash"]
        expected_events = (*COMMON_EVENTS, refinance, (SALE_DATE, "distribution", "net_sale_distribution", sale))
        actual = Counter((e["date"], e["kind"], e["category"], amount(e["amount"]))
                         for e in cash["events"] if amount(e["amount"]))
        require(actual == Counter(expected_events), f"{name} dated cash differs from the expected fixture")
        contributed = sum(value for _, kind, _, value in expected_events if kind == "contribution")
        received = sum(value for _, kind, _, value in expected_events if kind == "distribution")
        shortfall = max(Fraction(), contributed - received)
        require(tuple(amount(cash[key]) for key in ("initial_capital", "gross_contributions", "gross_distributions",
                                                   "net_cash_profit", "cash_shortfall_at_horizon", "equity_multiple"))
                == (10, contributed, received, received - contributed, shortfall, received / contributed),
                f"{name} receipts, contributions or shortfall do not reconcile")

        recovery = result["nominal_sale_recovery"][name]
        exact = gross_price + (needed - sale) * 100
        require(Fraction(result["scenarios"][name]["gross_sale_proceeds"]) == gross_price
                and amount(recovery["minimum_net_receipt_per_usd_10"]) == needed
                and amount(recovery["minimum_gross_price_exact"]) == exact
                and amount(recovery["minimum_gross_price_at_cents"]) == rounded_minimum == Fraction(ceil(exact * 100), 100),
                f"{name} minimum does not reconcile to the dated cash")
        probes = recovery["price_probes"]
        require(set(probes) == {"below", "at", "above"}, f"{name} is missing a recovery probe")
        for label, price_change in (("below", -1), ("at", 0), ("above", 1)):
            probe = probes[label]
            require(amount(probe["gross_sale_price"]) == exact + price_change
                    and amount(probe["net_cash_per_usd_10"]) == Fraction(price_change, 100),
                    f"{name} {label} recovery probe did not cross zero")
        checked[name] = dict(initial_contribution=rational(Fraction(10)), extra_contribution=rational(contributed - 10),
                             cash_total_received=rational(received), nominal_unrecovered=rational(shortfall),
                             net_sale_receipt=rational(sale), cash=cash, minimum_sale_project=rational(rounded_minimum),
                             recovery_probes=probes)
    return checked, result["pdf_sha256"]


def verify_blocked_cases(temp):
    source = json.loads(TEMPLATES["with_refinance"].read_bytes())
    blocked = {}
    for name, group, reason in (
        ("above-capacity", "capacity", "selected_principal_exceeds_declared_bank_capacity"),
        ("missing-dscr", "worksheet", "C72:required_numeric_value_missing"),
    ):
        path = temp / f"{name}.json"
        path.write_bytes(encoded(source | {"archive_case": name}))
        result, text = audit_case(path, temp / name)
        require(result["state"] == "PENDING" and reason in result["blockers"][group]
                and all(result[key] is None for key in ("project", "risk", "cash_recovery", "refinance"))
                and "Minimo VP USD" not in text, f"{name} exposed cash despite the blocker")
        blocked[name] = dict(state=result["state"], reason=reason, pdf_sha256=result["pdf_sha256"])
    return blocked


def verify_holding_funding():
    result = holding_funding_cases()
    require(result["decision"] == "PENDING" and amount(result["sale_price_project"]) == 300
            and amount(result["maturity_cash_payment_project"]) == Fraction(3393913, 60602),
            "The delayed sale or debt payoff changed")
    start = date.fromisoformat(INITIAL_DATE)
    rows = []
    for row, holding, last in zip(result["rows"], (10, 20, 30), (32, 16, 10), strict=True):
        require(amount(row["monthly_holding_cost_project"]) == holding, "Unexpected holding cost")
        for scenario, step in zip(row["scenarios"], range(3), strict=True):
            delay = last + step
            cash_left = Fraction(19513241, 60602) - holding * delay
            extra = max(Fraction(), -cash_left) / 100
            net_sale = Fraction("4.75") + max(Fraction(), cash_left) / 100
            receipts = Fraction("2.45") + net_sale
            events = scenario["dated_events"]
            additional = [e for e in events if e["category"] == "additional_capital"]
            require(scenario["delay_months"] == delay and len(additional) == step
                    and amount(scenario["debt_payoff_at_sale_project"]) == 0
                    and amount(scenario["extra_contribution_per_usd_10"]) == extra
                    and amount(scenario["sale_net_per_usd_10"]) == net_sale
                    and amount(scenario["cash_total_received_per_usd_10"]) == receipts
                    and amount(scenario["nominal_unrecovered_per_usd_10"]) == 10 + extra - receipts,
                    "The funding boundary does not reconcile to independent cash expectations")
            pending = scenario["without_funding_terms"]
            if step:
                require(pending["state"] == "PENDING"
                        and pending["cash_total_received_per_usd_10"] is pending["gaps"] is None
                        and sum(amount(e["amount"]) for e in additional) == extra,
                        "Missing funding terms exposed cash or implied an unfunded contribution")
            else:
                require(pending is None, "The last fully funded month was incorrectly blocked")
            for gap, rate in zip(scenario["gaps"], (Fraction(), Fraction("0.01"), Fraction("0.02")), strict=True):
                discounted = Fraction()
                for event in events:
                    when = date.fromisoformat(event["date"])
                    months = (when.year - start.year) * 12 + when.month - start.month
                    direction = 1 if event["kind"] == "distribution" else -1
                    discounted += direction * amount(event["amount"]) / (1 + rate)**months
                require(amount(gap["monthly_rate"]) == rate and amount(gap["present_value_per_usd_10"]) == discounted,
                        "The delayed cash does not discount by the verified calendar")
            rows.append(dict(holding_cost_project=holding, delay_months=delay, sale_date=scenario["sale_date"],
                             cash_total_received=rational(receipts), extra_contribution=rational(extra),
                             nominal_unrecovered=scenario["nominal_unrecovered_per_usd_10"],
                             additional_events=additional, gaps=scenario["gaps"], without_funding_terms=pending))
    return rows


def build_report():
    with TemporaryDirectory(prefix="miniuw-d102-") as directory:
        temp = Path(directory)
        cases, comparison_sha = verify_cash_cases(temp)
        blocked = verify_blocked_cases(temp)
        sale_only = verify_case("without_refinance", "matched", temp)
    holding = verify_holding_funding()
    lines = [
        ("CASO | APORTE EXTRA | COBRO NETO DE VENTA | COBRO TOTAL | CAJA SIN RECUPERAR", True),
    ]
    for name, label in (("Base", "Normal"), ("Downside", "Adverso")):
        case = cases[name]
        fields = [money(case[key]) for key in ("extra_contribution", "net_sale_receipt", "cash_total_received",
                                                "nominal_unrecovered")]
        lines.append((label + " | " + " | ".join("USD " + value for value in fields), True))
    lines.extend([
        ("Ambos casos aportan USD 10 el 01/01/2027, cobran USD 1 el 01/03 y otro USD 1 el 01/06.", False),
        ("Normal cobra USD 2 al refinanciar el 01/04. Adverso aporta USD 0,80 ese día.", False),
        ("Ambos cobran el neto de venta el 01/07/2027. El saldo sin recuperar incluye el aporte extra.", False),
        ("Límites de venta. Los cierres por debajo, en y por encima del equilibrio cruzan cero.", True),
        ("Capacidad excedida o DSCR faltante. El expediente queda PENDING sin cobros ni precio de recuperación.", False),
        ("Ruta sin refinanciación. La hoja, los flujos y el PDF se conciliaron con la entrada original.", False),
        ("Tenencia. Nueve cierres verifican el último mes cubierto y los dos que requieren aportes.", False),
        ("Con tenencia de USD 20, el primer aporte es USD 0,18 en diciembre de 2028 y el cobro total es USD 7,20.", False),
        ("Sin términos de financiación, los seis escenarios que requieren aportes quedan PENDING sin cifras.", False),
        ("Pruebas automatizadas con datos sintéticos. Decisión real PENDING.", True),
    ])
    pdf = render_page("D102 | Verificación integral", lines, 24,
                      "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "PENDIENTE | Pruebas del flujo de inversión y sus límites")
    result = dict(status="passed", decision="PENDING", scope="synthetic_integration", cases=cases,
                  comparison_pdf_sha256=comparison_sha, blocked_cases=blocked, sale_only=sale_only,
                  holding_cases=holding, pdf_sha256=sha(pdf), page_count=1)
    return pdf, result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of auditing the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pdf, result = build_report()
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(pdf)
    else:
        require((ROOT / REPORT).read_bytes() == pdf, "The one-page report differs from source replay")
    if args.evidence:
        with args.evidence.open("xb") as stream:
            stream.write(encoded(result))
    print(json.dumps(dict(status=result["status"], decision=result["decision"], cash_cases=len(result["cases"]),
                          recovery_probes=sum(len(case["recovery_probes"]) for case in result["cases"].values()),
                          blocked_inputs=len(result["blocked_cases"]), sale_only_verified=True,
                          funding_cases=len(result["holding_cases"]), one_page_report=result["page_count"] == 1,
                          pdf_sha256=result["pdf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
