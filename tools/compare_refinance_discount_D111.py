"""Compare dated USD 10 cash at the monthly refinance crossover for the revised plan."""
from argparse import ArgumentParser
from datetime import date
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
import json

from check_discounted_sale_recovery_D34 import present_value
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_worksheet_refinance_D45 import render_page
from compare_revised_plan_D110 import (
    EVENT_ROWS, REPORT as NOMINAL_REPORT, REQUEST, build_comparison, render_comparison, verify as verify_nominal,
)
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from plan_refinance_D108 import REFI_DATE
from plan_return_D107 import DATES, SALE_DATE
from worksheet_plan_refinance_D109 import SCENARIOS
from worksheet_sale_rate_grid_D84 import money


REPORT = "docs/review/MiniUW_D111_Tasa_de_Equilibrio_Refinanciacion.pdf"
OPTIONS = ("without_refinance", "with_refinance")
UPPER_RATE = Fraction(1, 50)


def month_offset(day):
    origin = date.fromisoformat(DATES[0])
    when = date.fromisoformat(day)
    months = (when.year - origin.year) * 12 + when.month - origin.month
    require(when.day == origin.day and months >= 0, "Expected a dated flow on the same-day monthly basis")
    return months


def monthly_flows(amounts):
    values = [Fraction()] * (month_offset(SALE_DATE) + 1)
    for key, _, day, kind in EVENT_ROWS:
        sign = -1 if kind == "contribution" else 1
        values[month_offset(day)] += sign * amount(amounts[key])
    return [{"net": rational(value)} for value in values]


def rate_bracket(cash_earlier, cash_reduction, months):
    # At sale, the difference is the earlier receipt compounded to sale less the reduced sale-day cash.
    require(months > 0 and cash_reduction > cash_earlier > 0, "Expected an earlier receipt with positive nominal cost")
    def difference(rate):
        return cash_earlier * (1 + rate) ** months - cash_reduction

    lower, upper = Fraction(), UPPER_RATE
    require(difference(lower) < 0 < difference(upper), "The comparison must bracket its crossover")
    for _ in range(36):
        middle = (lower + upper) / 2
        if difference(middle) < 0:
            lower = middle
        else:
            upper = middle
    require(difference(lower) < 0 <= difference(upper), "The exact crossover bracket lost its sign change")
    return lower, upper


def build_analysis(nominal):
    flows = {}
    pair_deltas = []
    refi_month, sale_month = month_offset(REFI_DATE), month_offset(SALE_DATE)
    for scenario in SCENARIOS:
        cases = nominal["cases"][scenario]
        require(all(cases[key]["amounts"] is not None for key in OPTIONS), "The four cash cases must be available")
        without, with_refi = (monthly_flows(cases[key]["amounts"]) for key in OPTIONS)
        flows[scenario] = dict(zip(OPTIONS, (without, with_refi), strict=True))
        differences = [amount(right["net"]) - amount(left["net"])
                       for left, right in zip(without, with_refi, strict=True)]
        require([index for index, delta in enumerate(differences) if delta] == [refi_month, sale_month],
                "The alternatives must share contributions and have only two cash differences")
        pair_deltas.append((differences[refi_month], -differences[sale_month]))
    early, reduced_at_sale = pair_deltas[0]
    require(all(pair == pair_deltas[0] for pair in pair_deltas), "The cases have different crossover equations")
    months = sale_month - refi_month
    lower, upper = rate_bracket(early, reduced_at_sale, months)
    approximate = (lower + upper) / 2
    for scenario, pair in flows.items():
        for rate, sign in ((lower, -1), (upper, 1)):
            delta = present_value(pair["with_refinance"], rate) - present_value(pair["without_refinance"], rate)
            require(delta * sign >= 0 and (rate != lower or delta != 0), f"{scenario} discounted cash missed the bracket")

    samples = []
    for label, rate in (("zero", Fraction()), ("one_percent", Fraction(1, 100)),
                        ("crossover_approximation", approximate), ("two_percent", UPPER_RATE)):
        values = {name: {option: present_value(flow, rate) for option, flow in pair.items()}
                  for name, pair in flows.items()}
        delta = (early * (1 + rate) ** months - reduced_at_sale) / (1 + rate) ** sale_month
        require(all(pair["with_refinance"] - pair["without_refinance"] == delta for pair in values.values()),
                "The discounted cash difference does not reproduce from the full ledgers")
        samples.append(dict(label=label, monthly_rate=rational(rate), refi_minus_no_refi=rational(delta),
                            net_present_value={name: {key: rational(value) for key, value in pair.items()}
                                               for name, pair in values.items()}))
    return dict(decision="PENDING", scope="synthetic_aggregate_equity", discount_date=DATES[0],
                refinance_date=REFI_DATE, sale_date=SALE_DATE, refinance_to_sale_months=months,
                requested_principal_usd=nominal["requested_principal_usd"],
                refi_cash_earlier=rational(early), reduced_cash_at_sale=rational(reduced_at_sale),
                nominal_refinance_cost=rational(reduced_at_sale - early),
                crossover=dict(lower=rational(lower), upper=rational(upper), approximate=rational(approximate),
                               monotone_sale_date_difference_for_nonnegative_rates=True),
                samples=samples, monthly_net_cash=flows, nominal=nominal,
                personal_investor_return=None, real_decisions_enabled=False, deployment_enabled=False)


def decimal_display(value, places):
    with localcontext() as ctx:
        ctx.prec = 36
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
        return f"{decimal:.{places}f}".replace(".", ",")


def percent(value, places):
    return decimal_display(100 * amount(value), places) + " %"


def page_for(analysis):
    columns = [(name, option) for name in SCENARIOS for option in OPTIONS]
    rate = percent(analysis["crossover"]["approximate"], 4)
    table_head = f"{' ':<46}{'Base':^24}{'Downside':^24}"
    options = "".join(f"{label:>12}" for label in ("Sin refi", "Con refi", "Sin refi", "Con refi"))
    lines = [
        (f"TASA DE EQUILIBRIO  {rate} mensual en Base y Downside", True),
        ("Por debajo, mayor VAN sin refi. Por encima, mayor VAN con refi.", False),
        ("La refi adelanta USD 4,49 tres meses y cuesta USD 0,15 nominales por USD 10.", False),
        ("Aportás USD 10 el 30/03/2027 y USD 0,42 extra el 30/06/2027 en los cuatro casos.", False),
        ("COBROS NOMINALES Y SALDO AL VENDER  /  USD POR USD 10 INICIALES", True),
        (table_head, True),
        (f"{'Flujo y fecha':<40}{options}", True),
    ]
    labels = (
        ("net_refinance_distribution", "Refi neta  30/03/2028"),
        ("operating_distribution", "Operación  30/06/2028"),
        ("net_sale_distribution", "Venta neta  30/06/2028"),
        ("total_distributions", "Cobro total"),
        ("unrecovered_after_sale", "Saldo sin recuperar al vender"),
    )
    for key, label in labels:
        values = [money(analysis["nominal"]["cases"][name][option]["amounts"][key]) for name, option in columns]
        lines.append((f"{label:<40}" + "".join(f"{value:>12}" for value in values), key == "total_distributions"))

    lines.extend([
        ("VALOR ACTUAL NETO AL 30/03/2027  /  USD POR USD 10 INICIALES", True),
        ("VAN = cobros menos aportes, descontados a la tasa mensual indicada.", False),
        (table_head, True),
        (f"{'Tasa mensual':<40}{options}   {'Dif. refi':>10}", True),
    ])
    for sample in analysis["samples"]:
        crossover = sample["label"] == "crossover_approximation"
        label = rate + " aprox." if crossover else percent(sample["monthly_rate"], 0)
        pv = [money(sample["net_present_value"][name][option]) for name, option in columns]
        difference = "0,000" if crossover else decimal_display(amount(sample["refi_minus_no_refi"]), 3)
        lines.append((f"{label:<40}" + "".join(f"{value:>12}" for value in pv) + f"   {difference:>10}", crossover))
    lines.extend([
        ("Dif. refi = VAN con refi menos VAN sin refi. Se redondea cada importe por separado.", False),
        ("En el cruce, el VAN de Downside sigue negativo. La tasa iguala alternativas.", False),
        ("Préstamo sintético USD 1.100.000. Capital agregado. Decisión de inversión PENDING.", False),
    ])
    return render_page("D111 | Plano A-601 revisado", lines, 19,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Cuándo cobrar antes compensa el costo de refinanciar")


def verify(analysis):
    lower, upper = (amount(analysis["crossover"][key]) for key in ("lower", "upper"))
    require(Fraction("0.0109344243") < lower < upper < Fraction("0.0109344244")
            and analysis["refinance_to_sale_months"] == 3
            and amount(analysis["nominal_refinance_cost"]) == Fraction(143, 960),
            "The rate bracket or dated nominal comparison differs from the independent result")
    samples = {row["label"]: row for row in analysis["samples"]}
    require(amount(samples["zero"]["refi_minus_no_refi"]) == -Fraction(143, 960)
            and amount(samples["one_percent"]["refi_minus_no_refi"]) < 0
            and amount(samples["two_percent"]["refi_minus_no_refi"]) > 0
            and abs(amount(samples["crossover_approximation"]["refi_minus_no_refi"])) < Fraction(1, 10**10),
            "The rate samples failed to confirm the comparison ordering")
    cross_values = samples["crossover_approximation"]["net_present_value"]
    require([money(cross_values[name][option]) for name in SCENARIOS for option in OPTIONS]
            == ["0,14", "0,14", "-3,54", "-3,54"] and analysis["decision"] == "PENDING",
            "Crossing the relative returns must preserve absolute scenario values and the decision guard")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new PDF instead of checking the versioned report.")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    nominal = build_comparison(local_file(ROOT, REQUEST).read_bytes())
    nominal_pdf = render_comparison(nominal)
    verify_nominal(nominal, nominal_pdf)
    require(nominal_pdf == local_file(ROOT, NOMINAL_REPORT).read_bytes(), "Nominal report differs from source replay")
    analysis = build_analysis(nominal) | {"nominal_pdf_sha256": sha(nominal_pdf)}
    verify(analysis)
    pdf = page_for(analysis)
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(pdf)
    else:
        require(local_file(ROOT, REPORT).read_bytes() == pdf, "The versioned PDF differs from exact source replay")
    if args.evidence:
        with args.evidence.open("xb") as stream:
            stream.write(encoded(analysis | dict(pdf_sha256=sha(pdf), page_count=1)))
    print(json.dumps(dict(status="passed", decision="PENDING", scenarios=len(SCENARIOS), rate_samples=4,
                          monthly_crossover=percent(analysis["crossover"]["approximate"], 4),
                          page_count=1, pdf_sha256=sha(pdf)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
