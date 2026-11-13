"""Independent arithmetic for the two fully documented D178 synthetic cases.

This calculator reads the original fixture XLSX and case JSON. It uses only
the standard library and does not take a model result as an input.
"""
from datetime import date
from fractions import Fraction as Q
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile


PERIODS = {
    "operacion": ("SYNTHETIC-D107-operating-year", 0),
    "valoracion": ("SYNTHETIC-D108-refinance-valuation-annual", 9),
    "banco": ("SYNTHETIC-D108-bank-annual", 9),
    "salida": ("SYNTHETIC-D107-year-from-sale", 12),
}
GROUPS = ("studio", "1BR", "2BR", "3BR")
USES = ("retail", "restaurant", "office")
INITIAL_EQUITY = Q(2_400_000)  # Declared synthetic opening equity in D107.


def exact(value):
    if isinstance(value, dict):
        return Q(int(value["numerator"]), int(value["denominator"]))
    return Q(value)


def cells(raw):
    with ZipFile(BytesIO(raw)) as book:
        sheet = ElementTree.fromstring(book.read("xl/worksheets/sheet1.xml"))
    parsed = {}
    for cell in sheet.findall(".//{*}c"):
        address = cell.attrib["r"]
        if not address.startswith("C"):
            continue
        if cell.find("{*}f") is not None:
            raise ValueError(f"Formula in source cell {address}")
        literal = cell.findtext("{*}v")
        if cell.get("t") == "n" and literal is not None:
            parsed[address] = exact(literal)
        elif cell.get("t") == "inlineStr":
            parsed[address] = cell.findtext("{*}is/{*}t")
    return parsed


def months(day):
    return day.year * 12 + day.month - 1


def shift(day, count, *, day_of_month=None):
    year, month = divmod(months(day) + int(count), 12)
    return date(year, month + 1, day.day if day_of_month is None else day_of_month)


def annual_irr_interval(flows):
    """Bound the unique positive discount root by rational bisection."""
    signs = [flow > 0 for flow in flows if flow]
    if sum(a != b for a, b in zip(signs, signs[1:])) != 1:
        raise ValueError("Independent IRR requires a single sign change")

    def npv(discount):
        value = Q(0)
        for flow in reversed(flows):
            value = value * discount + flow
        return value

    low, high = Q(0), Q(1)
    for _ in range(32):
        if npv(high) >= 0:
            break
        high *= 2
    else:
        raise ValueError("Independent IRR root is outside the bracket budget")
    for _ in range(68):
        middle = (low + high) / 2
        if npv(middle) < 0:
            low = middle
        else:
            high = middle
    return high ** -4 - 1, low ** -4 - 1


def noi_lines(c, inputs, name, tco, stabilized, area):
    lines = {}
    policy = inputs["policy"]
    if policy["concession_basis"] != "gross_potential_rent":
        raise ValueError("Unsupported concession basis")
    costs = inputs["operating_costs"]["scenarios"][name]
    other = c["C13"] * inputs["other_income"]["eligible_units"] * 12
    annual_commercial = sum(area[use] * c[f"C{16+i}"] for i, use in enumerate(USES))
    lease_start = months(tco) + c["C21"]
    tax_terms = inputs["property_tax"]["scenarios"][name]
    buyer = inputs["buyer_forward_property_tax"][name]
    for label, (_, start) in PERIODS.items():
        rent_factors = [(1 + c["C75"]) ** (month // 12) for month in range(start, start + 12)]
        expense_factor = sum((1 + c["C76"]) ** (month // 12) for month in range(start, start + 12)) / 12
        bank_stress = exact(inputs["supplemental_scope"][name]["bank_vacancy_addition"]["value"])
        vacancy = c["C14"] + (bank_stress if label == "banco" else 0)
        group_rows = {}
        for i, group in enumerate(GROUPS):
            source = inputs["groups"][group]
            quantity = source["units"]
            if c["C7"] == "PER SF":
                quantity *= exact(source["rentable_sf_per_unit"])
            elif c["C7"] != "PER UNIT":
                raise ValueError("Unknown rent basis")
            gross = c[f"C{8+i}"] * quantity * sum(rent_factors)
            group_rows[group] = dict(gross_potential=gross, vacancy_loss=gross * vacancy,
                                     concession_loss=gross * c["C15"],
                                     effective_rent=gross * (1 - vacancy - c["C15"]))
        effective = sum(row["effective_rent"] for row in group_rows.values())
        active = [factor for i, factor in enumerate(rent_factors) if months(stabilized) + start + i >= lease_start]
        gross_commercial = annual_commercial * sum(active) / 12
        commercial_vacancy = gross_commercial * c["C19"]
        non_recoverable = (gross_commercial - commercial_vacancy) * c["C20"]
        commercial = gross_commercial - commercial_vacancy - non_recoverable
        utilities = {group: c[f"C{25+i}"] * inputs["utilities"]["eligible_units"][name][group]["count"] * 12 * expense_factor
                     for i, group in enumerate(GROUPS)}
        utility_total = sum(utilities.values())
        controllable = c["C57"] * costs["controllable_units"] * expense_factor
        expense = dict(fixed_opex=exact(inputs["annual_expenses"]["fixed_opex"]) * expense_factor,
                       controllable_excluding_utilities=controllable - utility_total,
                       management=c["C58"] * effective, management_other_income=c["C58"] * other,
                       insurance=c["C59"] * costs["insured_units"] * expense_factor)
        total_expense = sum(expense.values()) + utility_total
        before_tax = effective + other + commercial - total_expense
        if label == "salida":
            tax = exact(buyer["school_tax"]) + exact(buyer["non_school_tax"])
            noi = before_tax - tax
        else:
            # Independently solve both tax regimes, then select the admissible lower NOI.
            floor = c["C62"] * tax_terms["comparable_units"]
            slope = c["C61"] * exact(tax_terms["assessed_tax_rate"]["value"]) / exact(tax_terms["market_proxy_cap"]["value"])
            noi = min(before_tax - floor, before_tax / (1 + slope))
            tax = before_tax - noi
        lines[label] = dict(groups=group_rows, gross_rent=sum(row["gross_potential"] for row in group_rows.values()),
                            effective_rent=effective, other_income=other, utilities=utilities, expenses=expense, utility_total=utility_total,
                            operating_expenses_excluding_tax=total_expense, tax=tax, noi=noi,
                            commercial=dict(recognized_months=len(active), gross=gross_commercial,
                                            vacancy=commercial_vacancy, non_recoverable=non_recoverable, net=commercial))
    return lines


def construction(c, inputs, name, purchase, early, finish, refi, area):
    development = inputs["development"]["scenarios"][name]
    land = c["C32"] * (1 + c["C33"])
    vertical_basis = c["C34"]
    if vertical_basis == "$/UNIT":
        quantity = sum(row["units"] for row in inputs["groups"].values())
    elif vertical_basis == "$/GSF":
        quantity = exact(development["plan_gsf"]["value"])
    else:
        raise ValueError("Unsupported vertical cost basis")
    direct = c["C35"] * quantity + c["C37"] * inputs["construction_budget"]["scenarios"][name]["parking"]["spaces"] + c["C38"]
    hard = direct * (1 + c["C39"])
    soft = hard * c["C40"]
    total_cost = land + hard + soft + c["C41"] * sum(area.values())
    calendar = inputs["project_calendar"]["scenarios"][name]
    early_hard = direct * exact(calendar["upfront_direct_hard_share"])
    early_uses = early_hard + soft * c["C42"]
    lease_up = c["C47"] * exact(calendar["lease_up_shortfall_per_month"])
    uses = {purchase: land, early: early_uses, finish: total_cost + lease_up - land - early_uses}
    terms = inputs["construction_financing"]["scenarios"][name]
    commitment = min(c["C51"] * direct, exact(terms["maximum_commitment"]))
    fee = commitment * c["C53"]
    share = exact(terms["requested_invoice_fraction"])
    draws = {early: early_hard * share, finish: (direct - early_hard) * share}
    if sum(draws.values()) > commitment or max(draws.values()) > exact(terms["available_per_draw_checkpoint"]):
        raise ValueError("Construction commitment exceeded")

    # Split each quarter into opening draw and end-of-quarter interest/payoff.
    debt, cash, prior_interest = Q(0), Q(0), Q(0)
    rows, debt_rows = {}, {}
    for i in range(0, months(refi) - months(purchase) + 1, 3):
        day = shift(purchase, i)
        draw, use = draws.get(day, Q(0)), uses.get(day, Q(0))
        opening_fee = fee if day == purchase else Q(0)
        before_equity = cash + draw - use - prior_interest - opening_fee
        contribution = INITIAL_EQUITY if day == purchase else max(Q(0), -before_equity)
        rows[day] = dict(opening_free_cash=cash, loan_draw=draw, project_uses=use, interest_paid=prior_interest,
                         origination_fee_paid=opening_fee, equity_contribution=contribution,
                         closing_free_cash=before_equity + contribution)
        cash += draw + contribution - use - prior_interest - opening_fee
        if day != refi:
            end = shift(day, 3)
            exposure = debt + draw
            prior_interest = exposure * c["C52"] / 4
            debt_rows[day] = dict(end_date=end, opening_principal=debt, draw_at_start=draw, interest_exposure=exposure,
                                  interest_due_at_end=prior_interest, principal_repayment_at_end=exposure if end == refi else Q(0),
                                  closing_principal=Q(0) if end == refi else exposure)
            debt = exposure
    return dict(total_cost=total_cost, direct=direct, commitment=commitment, fee=fee, payoff=debt,
                free_cash=cash, funding=rows, debt=debt_rows)


def calculate(raw, inputs, name):
    c = cells(raw)
    calendar = inputs["project_calendar"]["scenarios"][name]
    purchase = date.fromisoformat(calendar["construction_start"])
    early, finish = shift(purchase, 3), shift(purchase, c["C46"])
    tco = date.fromisoformat(calendar["tco_date"])
    stabilized = shift(tco, c["C47"])
    refi = shift(stabilized, 8, day_of_month=30)
    sale = date.fromisoformat(inputs["supplemental_scope"][name]["sale_date"]["value"])
    if sale != shift(refi, 3):
        raise ValueError("Fixture must have one full post-refinance quarter")
    area = {use: exact(inputs["commercial"]["uses"][use]["rentable_sf"]) for use in USES}
    noi = noi_lines(c, inputs, name, tco, stabilized, area)
    build = construction(c, inputs, name, purchase, early, finish, refi, area)
    principal = exact(inputs["requested_principal"])
    quarters = inputs["permanent_loan"]["rules"]["payments_per_year"]
    amortization = int(c["C70"]) * quarters
    maturity = inputs["supplemental_scope"][name]["maturity_payments"]["value"]
    rate = c["C69"] / quarters
    # Present value of a unit quarterly annuity yields the amortizing payment.
    payment = principal / sum((1 + rate) ** -i for i in range(1, amortization + 1))
    valuation = noi["valoracion"]["noi"] / c["C66"]
    bank_noi = noi["banco"]["noi"]
    limits = dict(LTV=valuation * c["C71"], DSCR=bank_noi / (payment * quarters / principal * c["C72"]),
                  DEBT_YIELD=bank_noi / exact(inputs["bank_debt_yield"][name]["minimum"]))
    if principal > min(limits.values()) or maturity <= 1:
        raise ValueError("The independent cash scenario requires compatible refinancing")
    reserve_terms = inputs["refinance_costs"]["scenarios"][name]
    permanent_reserve = c["C74"] * reserve_terms["eligible_units"]
    refi_cost = c["C73"] * principal
    refinance_net = principal + build["free_cash"] - build["payoff"] - refi_cost - permanent_reserve
    if refinance_net < 0:
        raise ValueError("The fixture has no permitted cash-in refinance")
    balance, schedule = principal, {}
    for i in range(1, maturity + 1):
        day = shift(refi, i * 3)
        interest = balance * rate
        principal_paid = payment - interest
        # The schedule states amounts due. The final balance is after the
        # regular installment and before the separately due balloon.
        post_installment = balance - principal_paid
        balloon = post_installment if i == maturity else Q(0)
        schedule[day] = dict(opening_balance=balance, interest_due=interest, principal_due=principal_paid,
                             scheduled_service_due=payment, balloon_due=balloon,
                             scheduled_plus_balloon_due=payment + balloon, closing_balance=post_installment)
        balance = schedule[day]["closing_balance"]
    sale_payoff = schedule[sale]["closing_balance"]
    replacement_terms = inputs["replacement_reserve"]["scenarios"][name]
    replacement = c["C60"] * replacement_terms["eligible_units"]
    operating_net = noi["operacion"]["noi"] - payment - replacement
    gross_sale = noi["salida"]["noi"] / c["C67"]
    variable_cost = gross_sale * c["C68"]
    fixed_cost = exact(inputs["supplemental_scope"][name]["fixed_sale_cost"]["value"])
    released_permanent = permanent_reserve * exact(reserve_terms["sale_release_fraction"])
    released_replacement = replacement * exact(replacement_terms["sale_release_fraction"])
    sale_net = gross_sale - variable_cost - fixed_cost - sale_payoff + released_permanent + released_replacement

    events = {"initial": (purchase, "contribution", INITIAL_EQUITY)}
    for day, row in build["funding"].items():
        if day != purchase and row["equity_contribution"]:
            events[f"construction-funding-{day}"] = (day, "contribution", row["equity_contribution"])
    events.update({
        "refinance": (refi, "distribution", refinance_net),
        "operating-funding": (sale, "contribution", max(Q(0), -operating_net)),
        "operating": (sale, "distribution", max(Q(0), operating_net)),
        "sale": (sale, "distribution", sale_net),
    })
    grid = {shift(purchase, i): Q(0) for i in range(0, months(sale) - months(purchase) + 1, 3)}
    for day, kind, value in events.values():
        grid[day] += value if kind == "distribution" else -value
    return dict(noi=noi, build=build, refi=refi, sale=sale, principal=principal, valuation=valuation,
                limits=limits, achieved_debt_yield=bank_noi / principal, refi_cost=refi_cost, refinance_net=refinance_net,
                payment=payment, quarters=quarters, schedule=schedule, payoff=sale_payoff,
                permanent_reserve=permanent_reserve, replacement=replacement, released_permanent=released_permanent,
                released_replacement=released_replacement, gross_sale=gross_sale, variable_cost=variable_cost,
                fixed_cost=fixed_cost, sale_net=sale_net, events=events, grid=grid,
                coc=(exact(inputs["post_refinance_coc"][name]["period_noi"]) - payment)
                    / exact(inputs["post_refinance_coc"][name]["equity_still_invested"]),
                irr=annual_irr_interval(list(grid.values())))
