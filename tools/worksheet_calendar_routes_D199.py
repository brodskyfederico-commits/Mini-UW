"""Calculate audited synthetic cash variants for the D197 quarterly calendar checks."""
from datetime import date
from fractions import Fraction

from miniuw_foundation.debt_service import rational
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_exit_pricing_D151 import RULES as SALE_PRICING_RULES
from worksheet_local_sources_D127 import day, number, object_or_empty, synthetic_id
from worksheet_project_calendar_D145 import offset


def pending(reason):
    return dict(state="PENDING", blocker=reason, cash_per_usd_10=None)


def tax_at_cutoff(record, year):
    """Apply an explicit one-year synthetic levy to supplied land and usable components."""
    cutoff = date(year, 1, 1)
    if not isinstance(record, dict) or not synthetic_id(record.get("source_ref")):
        return pending("assessment_cutoff_source_unconfirmed")
    land = number(record.get("land_value"))
    rates = {component: number(record.get(f"{component}_rate")) for component in ("school", "non_school")}
    parts = record.get("improvements")
    if land is None or land < 0 or any(rate is None or not 0 <= rate <= 1 for rate in rates.values()):
        return pending("assessment_value_or_component_tax_rate_unconfirmed")
    if not isinstance(parts, list) or not parts:
        return pending("improvement_inventory_unconfirmed")
    rows = []
    ids = set()
    for part in parts:
        if not isinstance(part, dict):
            return pending("improvement_inventory_unconfirmed")
        value, usable = number(part.get("value")), day(part.get("usable_on"))
        identity = part.get("id")
        if (value is None or value < 0 or usable is None or not synthetic_id(identity) or identity in ids
                or not synthetic_id(part.get("source_ref"))):
            return pending("substantial_completion_date_or_value_unconfirmed")
        ids.add(identity)
        rows.append(part | {"included": usable <= cutoff, "assessed_value": value if usable <= cutoff else Fraction()})
    assessed = land + sum(row["assessed_value"] for row in rows)
    levies = {component: assessed * rate for component, rate in rates.items()}
    return dict(state="calculated_synthetic", cutoff=cutoff.isoformat(), source_ref=record["source_ref"],
                land_value=land, improvements=rows, assessed_value=assessed, **levies, total=sum(levies.values()))


def phased_schedule(view, terms, principal):
    loan = view["permanent_loan"]
    count = terms.get("interest_only_payments")
    if (type(count) is not int or not 0 < count < loan["maturity_payments"]
            or count >= loan["amortization_payments"] or not synthetic_id(terms.get("source_ref"))
            or terms.get("amortization_clock") != "count_interest_only_inside_original_amortization"):
        return pending("interest_only_schedule_or_amortization_basis_unconfirmed")
    rate = number(loan["periodic_rate"])
    remaining = loan["amortization_payments"] - count
    # The declared total amortization clock includes the interest-only tranche.
    installment = principal / sum(((1 + rate) ** -i for i in range(1, remaining + 1)), Fraction())
    schedule = []
    balance = principal
    for index, date_due in enumerate(loan["payment_dates"], 1):
        interest = balance * rate
        amortizing = index > count
        capital = installment - interest if amortizing else Fraction()
        closing = balance - capital
        balloon = closing if index == loan["maturity_payments"] else Fraction()
        schedule.append(dict(date=date_due, phase="amortizing" if amortizing else "interest_only", opening=balance,
                             service=interest + capital, interest=interest, principal=capital,
                             closing=closing, balloon=balloon))
        balance = closing
    return dict(state="calculated_synthetic", source_ref=terms["source_ref"], schedule=schedule,
                annual_sizing_service=installment * loan["payments_per_year"])


def route_cash(view, terms):
    """Reconcile construction, operation and terminal equity on explicit quarterly cutoffs."""
    mode = terms.get("route")
    if mode not in ("interest_only_then_amortize", "sell_without_refinance") or not synthetic_id(terms.get("source_ref")):
        return pending("calendar_route_unconfirmed" if view.get("cash_per_usd_10") is not None
                       else "audited_input_cash_unavailable")
    if mode == "interest_only_then_amortize" and any(
            view.get(key) is None for key in ("cash_per_usd_10", "permanent_loan", "construction_refinance")):
        return pending("audited_input_cash_unavailable")
    original = view.get("project_calendar")
    funding = view.get("construction_financing")
    reserve = view.get("replacement_reserve")
    if mode == "sell_without_refinance":
        reserve = view.get("replacement_reserve_for_sale_only", reserve)
    price_terms = view.get("valuation_and_sale")
    if any(item is None for item in (original, funding, reserve, price_terms)) or funding.get("state") != "computed_synthetic":
        return pending("audited_input_cash_unavailable")
    periods = object_or_empty(view.get("noi_by_period"))
    operating_noi = number(object_or_empty(periods.get(OPERATING_PERIOD)).get("noi"))
    exit_cap = number(price_terms.get("exit_cap"))
    sale_cost_fraction = number(price_terms.get("sale_cost_fraction"))
    fixed_terms = price_terms.get("fixed_sale_cost")
    if (fixed_terms is None and price_terms.get("rules") == SALE_PRICING_RULES
            and price_terms.get("inventory_declared_complete") is True):
        # D151 declares all transaction costs in the single gross-price percentage.
        fixed_sale_cost = Fraction()
    else:
        fixed_sale_cost = number(object_or_empty(fixed_terms).get("value"))
    if (operating_noi is None or exit_cap is None or exit_cap <= 0 or sale_cost_fraction is None
            or not 0 <= sale_cost_fraction <= 1 or fixed_sale_cost is None or fixed_sale_cost < 0):
        return pending("audited_input_cash_unavailable")
    # Keep the documented stabilized year and take its cash at the original cutoff.
    # The later exit carries only explicitly supplied interim net operating cash.
    cash_date = original["sale_date"]
    start = day(original["refinance_date"])
    tax_record = terms.get("construction_tax")
    tax_date = None
    if (isinstance(tax_record, dict) and tax_record.get("applicability") == "no_incremental_tax_in_variant"
            and synthetic_id(tax_record.get("source_ref"))):
        tax = dict(state="not_applicable_in_variant", source_ref=tax_record["source_ref"], total=Fraction())
    else:
        if not isinstance(tax_record, dict) or type(tax_record.get("year")) is not int or not 1 <= tax_record["year"] <= 9999:
            return pending("construction_tax_year_unconfirmed")
        tax = tax_at_cutoff(tax_record, tax_record["year"])
        if tax["state"] == "PENDING":
            return tax
        tax_date = tax_record.get("paid_on")
        if (day(tax_date) is None or tax_date not in original["equity_dates"]
                or tax_date >= original["stabilization_date"] or tax_date < tax["cutoff"]):
            return pending("construction_tax_payment_date_not_in_preopening_schedule")

    rows = []
    if mode == "sell_without_refinance":
        ledger = funding.get("cash_by_date")
        opening = ledger[0] if ledger else {}
        basis = number(opening.get("equity_contribution"))
        if opening.get("date") != original["purchase_date"] or basis is None or basis <= 0:
            return pending("initial_equity_basis_unconfirmed")
        scale = 10 / basis
    else:
        scale = number(view["cash_per_usd_10"]["scale_factor"])
    free_cash = Fraction()
    payoff = number(funding["construction_principal_payoff"])
    for item in funding["cash_by_date"]:
        when = item["date"]
        levy = tax["total"] if when == tax_date else Fraction()
        loan_draw = number(item["loan_draw"])
        uses = sum(number(item[field]) for field in ("project_uses", "interest_paid", "origination_fee_paid")) + levy
        contribution = (number(item["equity_contribution"]) if when == original["purchase_date"]
                        else max(Fraction(), uses - free_cash - loan_draw))
        closing = free_cash + loan_draw + contribution - uses
        if closing < 0:
            return pending("construction_needs_additional_opening_equity")
        rows.append(dict(date=when, stage="construction", opening_free=free_cash, opening_restricted=Fraction(),
                         sources=loan_draw + contribution, uses=uses, closing_free=closing,
                         closing_restricted=Fraction(), contribution=contribution, distribution=Fraction(),
                         debt_interest=number(item["interest_paid"]), debt_principal=Fraction(), preopening_tax=levy))
        free_cash = closing

    deposit = number(reserve["deposit"])
    replacement_release = deposit * number(reserve["sale_release_fraction"])
    # The existing forward NOI and quote are valid only for the original sale.
    if mode == "interest_only_then_amortize":
        refi = view["construction_refinance"]
        request = terms.get("requested_principal")
        if (not isinstance(request, dict) or not synthetic_id(request.get("source_ref"))
                or number(request.get("value")) is None or number(request["value"]) <= 0):
            return pending("phased_refinance_principal_unconfirmed")
        principal = number(request["value"])
        phased = phased_schedule(view, terms, principal)
        if phased["state"] == "PENDING":
            return phased
        reserve_balance = number(refi["permanent_reserve_deposit"])
        refinance_fee = principal * number(refi["closing_fee"]) / number(refi["gross_proceeds"])
        limits = view["capacity"]["capacity_limits"]
        bank_noi = number(view["capacity"]["bank_noi"])
        dscr_limit = bank_noi * principal / (
            phased["annual_sizing_service"] * number(view["permanent_loan"]["minimum_dscr"]))
        capacity = min(dscr_limit, *(number(v) for key, v in limits.items() if key != "DSCR"))
        if principal > capacity:
            return pending("selected_principal_exceeds_declared_bank_capacity") | dict(capacity=capacity)
        cash_out = free_cash + principal - payoff - refinance_fee - reserve_balance
        if cash_out < 0:
            return pending("refinance_cash_in_terms_unconfirmed")
        rows.append(dict(date=start.isoformat(), stage="refinance", opening_free=free_cash, opening_restricted=Fraction(),
                         sources=principal, uses=payoff + refinance_fee + cash_out, closing_free=Fraction(),
                         closing_restricted=reserve_balance, contribution=Fraction(), distribution=cash_out,
                         debt_interest=Fraction(), debt_principal=payoff))
        free_cash = Fraction()
        release = number(view["permanent_reserve"]["released_at_sale"])
        sale_index = terms.get("sale_payment_index")
        if type(sale_index) is not int or not terms["interest_only_payments"] < sale_index < len(phased["schedule"]):
            return pending("sale_after_first_amortizing_payment_before_maturity_required")
        payments = phased["schedule"][:sale_index]
        sale_date = payments[-1]["date"]
        forward = terms.get("delayed_forward_noi")
        period_start = offset(day(sale_date).replace(day=1), 1)
        expected_window = f"{period_start}/{offset(period_start, 12)}"
        interim = terms.get("intermediate_net_operating_cash")
        interim_dates = [row["date"] for row in payments if row["date"] != cash_date]
        if (not isinstance(interim, dict) or set(interim) != set(interim_dates) or any(
                not isinstance(row, dict) or not synthetic_id(row.get("source_ref")) or number(row.get("value")) is None
                for row in interim.values())):
            return pending("delayed_exit_interim_cash_unconfirmed")
        if (not isinstance(forward, dict) or not synthetic_id(forward.get("source_ref"))
                or forward.get("period_ref") != expected_window or forward.get("noi_basis") != "before_replacement_reserves"
                or number(forward.get("value")) is None):
            return pending("delayed_exit_forward_noi_or_interim_cash_unconfirmed")
        forward_noi = number(forward["value"])
        reference = dict(schedule=payments, capacity=capacity, requested_principal=request,
                         forward_noi_source=forward, interim_cash=interim)
        sale_principal = payments[-1]["closing"]
    else:
        sale_date = original["sale_date"]
        if day(sale_date) > day(funding["debt_source"]["maturity_date"]):
            return pending("construction_loan_matures_before_sale")
        reserve_balance = release = Fraction()
        # The final quarter carries existing construction debt at its documented interval rate.
        interest = payoff * number(funding["debt_source"]["periods"][-1]["interest_fraction"]["value"])
        payments = [dict(date=sale_date, service=interest, principal=Fraction(), interest=interest)]
        forward_noi = number(object_or_empty(periods.get(FORWARD_PERIOD)).get("noi"))
        if forward_noi is None:
            return pending("audited_input_cash_unavailable")
        reference = dict(schedule=payments, construction_maturity=funding["debt_source"]["maturity_date"])
        sale_principal = payoff

    for payment in payments:
        when = payment["date"]
        at_stabilized_close = when == cash_date
        net_income = operating_noi if at_stabilized_close else number(interim[when]["value"])
        deposit_today = deposit if at_stabilized_close else Fraction()
        net = net_income - payment["service"] - deposit_today
        contribution, distribution = max(Fraction(), -net), max(Fraction(), net)
        restricted_close = reserve_balance + deposit_today
        rows.append(dict(date=when, stage="operation", opening_free=free_cash, opening_restricted=reserve_balance,
                         sources=max(Fraction(), net_income) + contribution,
                         uses=max(Fraction(), -net_income) + payment["service"] + distribution,
                         closing_free=free_cash, closing_restricted=restricted_close,
                         contribution=contribution, distribution=distribution,
                         debt_interest=payment["interest"], debt_principal=payment["principal"]))
        reserve_balance = restricted_close

    gross = forward_noi / exit_cap
    cost = gross * sale_cost_fraction + fixed_sale_cost
    restricted_close = reserve_balance - replacement_release - release
    proceeds = free_cash + gross - cost - sale_principal + replacement_release + release
    if proceeds < 0 or gross < 0:
        return pending("sale_cash_in_terms_unconfirmed")
    rows.append(dict(date=sale_date, stage="sale", opening_free=free_cash, opening_restricted=reserve_balance,
                     sources=gross, uses=cost + sale_principal + proceeds, closing_free=Fraction(),
                     closing_restricted=restricted_close, contribution=Fraction(), distribution=proceeds,
                     debt_interest=Fraction(), debt_principal=sale_principal))
    for row in rows:
        if row["opening_free"] + row["opening_restricted"] + row["sources"] != (
                row["uses"] + row["closing_free"] + row["closing_restricted"]):
            raise ValueError(f"Unbalanced {row['stage']} cash at {row['date']}")
    for prior, row in zip(rows, rows[1:]):
        if (row["date"] < prior["date"] or row["opening_free"] != prior["closing_free"]
                or row["opening_restricted"] != prior["closing_restricted"]):
            raise ValueError(f"Discontinuous cash at {row['date']}")
    flows = [dict(date=row["date"], stage=row["stage"], contribution=row["contribution"] * scale,
                  receipt=row["distribution"] * scale) for row in rows if row["contribution"] or row["distribution"]]
    contributed = sum(flow["contribution"] for flow in flows)
    received = sum(flow["receipt"] for flow in flows)
    return dict(state="calculated_synthetic", route=mode, source_ref=terms["source_ref"], tax=tax,
                debt=reference, sale=dict(date=sale_date, gross=gross, cost=cost, principal_paid=sale_principal),
                cash_by_period=rows, cash_per_usd_10=dict(events=flows, additional=contributed - 10,
                                                       received=received, unrecovered=max(Fraction(), contributed - received)))
