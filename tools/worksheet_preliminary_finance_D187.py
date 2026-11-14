"""Construction and fixed-rate refinance for the synthetic residential LOI workbook."""
from fractions import Fraction

from miniuw_foundation.construction_draws import produce_construction_draws
from miniuw_foundation.debt_service import ASSUMPTIONS, SCHEMA, _fraction as amount, produce_debt_service, rational
from miniuw_foundation.drafts import ValidationError
from miniuw_worksheet_v1 import encoded
from worksheet_construction_financing_D146 import cash_amount
from worksheet_local_sources_D127 import day
from worksheet_project_calendar_D145 import offset


FINANCING_CELLS = ("C52", "C53", "C66", "C69", "C70", "C71", "C72", "C73", "C74")
CONVENTION = "SYNTHETIC-D187-single-draw-at-completion-fixed-quarterly-refi"


STAGED_CONVENTION = "SYNTHETIC-D188-staged-draws-fixed-quarterly-refi"


def finance(case, name, inputs, finish, stabilize, direct_hard, remaining_work, operating, *, stages=None, sizing_tax=None):
    staged = stages is not None
    convention = STAGED_CONVENTION if staged else CONVENTION
    run_id = "SYNTHETIC-D188" if staged else "SYNTHETIC-D187"
    v = inputs["values"]
    dates = case["dates"]
    term = inputs["support"]["financing"]
    refi_date = dates[stabilize]
    try:
        requested = amount(term.get("requested_refinance_usd"), 12)
        credit_cap = amount(term.get("construction_commitment_usd"), 12)
        bank_loss = amount(term.get("bank_vacancy_addition_H08"), 12)
        minimum_yield = amount(term.get("minimum_debt_yield"), 12)
        equity_at_refi = amount(term.get("maximum_refi_equity_usd"), 12)
        release_share = amount(term.get("permanent_reserve_sale_release_fraction"), 12)
    except ValidationError:
        return {}, ["términos de financiación inválidos"]
    maturity = day(term.get("construction_maturity_date"))
    loan_maturity = term.get("permanent_maturity_quarters_H02")
    debt_yield_applies = term.get("debt_yield_applicability")
    if (term.get("convention") != convention or any(x is None for x in
            (requested, credit_cap, bank_loss, equity_at_refi, release_share, maturity))
            or type(loan_maturity) is not int
            or debt_yield_applies not in ("applicable", "not_applicable")
            or (minimum_yield is None) != (debt_yield_applies == "not_applicable")):
        return {}, ["financiación: falta principal, plazo, respaldo o condición de capacidad"]
    if (stabilize <= finish or maturity < day(refi_date) or requested <= 0 or credit_cap <= 0
            or not 0 <= bank_loss <= 1 - v["C14"] or equity_at_refi < 0 or not 0 <= release_share <= 1
            or (minimum_yield is not None and minimum_yield <= 0)
            or not all(0 <= v[k] <= 1 for k in ("C51", "C52", "C53", "C69", "C71", "C73"))
            or v["C51"] == 0 or not 0 < v["C66"] <= 1 or v["C72"] <= 0
            or not 1 <= v["C70"] <= 30 or v["C70"].denominator != 1
            or not len(dates) - 1 - stabilize <= loan_maturity <= 4 * v["C70"]):
        return {}, ["financiación: términos o vencimiento fuera del perfil"]

    commitment = min(credit_cap, direct_hard * v["C51"])
    if not commitment or (not staged and commitment > remaining_work):
        return {}, ["desembolso de obra fuera del costo pendiente"]
    context = dict(deal_id=case["focus"], scenario_id=f"SYNTHETIC-{name}", run_id=run_id,
                   definition_set_revision=convention)
    ref = term["source_ref"]
    stage_refs = {row["index"]: row["assumption"]["source_ref"] for row in stages} if staged else {}
    by_index = {finish: (commitment, commitment)} if not staged else {
        row["index"]: (row["draw"], row["available"]) for row in stages}
    first_draw_period = min(by_index)
    total_draws = sum((row[0] for row in by_index.values()), Fraction())
    if total_draws <= 0:
        return {}, ["desembolso total de obra debe ser positivo"]
    periods = []
    for index in range(first_draw_period, stabilize):
        interval = f"{run_id}-{index}"
        draw, available = by_index.get(index, (Fraction(), Fraction()))
        periods.append(dict(period_id=interval, start_date=dates[index], end_date=dates[index + 1],
                            interval_basis_ref=convention,
                            draw_at_start=cash_amount(draw, stage_refs.get(index, ref)),
                            available_new_draw=cash_amount(available, stage_refs.get(index, ref)),
                            principal_repayment_at_end=cash_amount(total_draws if index + 1 == stabilize else 0, ref),
                            interest_fraction=dict(value=rational(v["C52"] / 4), unit="simple_interval_fraction",
                                                   interval_ref=interval, source_ref=ref)))
    source = dict(schema="miniuw.synthetic-construction-draws.v1",
                  profile="SYNTHETIC-START-DRAW-END-REPAY-SIMPLE-INTERVAL-NONREVOLVING-v1", context=context,
                  currency="USD", loan_id=f"{run_id}-{name}-construction", start_date=dates[first_draw_period],
                  end_date=refi_date, maturity_date=maturity.isoformat(), inventory_declared_complete=True,
                  zero_opening_principal_basis_ref=convention, nonrevolving_commitment_basis_ref=ref,
                  principal_commitment=cash_amount(commitment, ref),
                  draw_fee_fraction=dict(value=rational(Fraction()), unit="gross_draw_fraction", source_ref=ref),
                  periods=periods)
    draw_run = produce_construction_draws(encoded(source))
    draws = draw_run.payload
    if draws["blockers"]:
        details = dict(construction_commitment=rational(commitment), construction_draw_blockers=draws["blockers"]) if staged else {}
        return details, ["deuda de obra: desembolso supera disponibilidad o compromiso"
                         if staged else "deuda de obra: " + draws["blockers"][0]]
    stage_evidence = {}
    if staged:
        stage_evidence = dict(construction_commitment=rational(commitment), construction_draw_schedule=draws["periods"],
                              construction_stage_inputs=[dict(date=dates[row["index"]], cost=rational(row["cost"]),
                                                              eligible=rational(row["eligible"]), requested_draw=rational(row["draw"]),
                                                              available_draw=rational(row["available"]),
                                                              source_pointer=row["pointer"], source_ref=row["assumption"]["source_ref"])
                                                         for row in stages],
                              financing_source_ref=ref)

    loan_terms = ASSUMPTIONS | dict(schema=SCHEMA, context=context, currency="USD",
        loan_id=f"{run_id}-{name}-permanent", principal=rational(requested),
        periodic_rate=rational(v["C69"] / 4), amortization_payments=int(v["C70"] * 4),
        maturity_payment=loan_maturity, payments_per_year=4, rate_interval_ref=ref,
        annual_equivalent_ref=f"{convention}/stabilized-bank-year", origination_date=refi_date,
        payment_dates=[offset(day(refi_date), 3 * i).isoformat() for i in range(1, loan_maturity + 1)])
    loan_run = produce_debt_service(encoded(loan_terms), ())
    loan = loan_run.payload
    if loan["schedule_blockers"]:
        return {}, ["deuda permanente: " + loan["schedule_blockers"][0]]
    if sizing_tax is None:
        bank_noi, refi_noi = operating(0, bank_loss), operating(0)
    else:
        bank_noi, refi_noi = operating(0, bank_loss) - sizing_tax, operating(0) - sizing_tax
    annual_unit = amount(loan["payment_per_unit"], 1300) * 4
    if min(bank_noi, refi_noi) <= 0:
        return {}, ["NOI bancario o de valoración no positivo"]
    value = refi_noi / v["C66"]
    limits = {"LTV": value * v["C71"], "DSCR": bank_noi / (annual_unit * v["C72"])}
    if minimum_yield is not None:
        limits["debt_yield"] = bank_noi / minimum_yield
    capacity = min(limits.values())
    evidence = dict(requested=rational(requested), capacity=rational(capacity), bank_noi=rational(bank_noi),
                    refinance_value=rational(value), limits={k: rational(x) for k, x in limits.items()},
                    binding_limits=[k for k, x in limits.items() if x == capacity], refinance_date=refi_date)
    evidence.update(stage_evidence)
    if requested > capacity:
        return evidence, ["solicitud de refi supera capacidad"]
    origination = commitment * v["C53"]
    payoff = amount(draws["totals"]["principal_repaid"])
    costs = requested * v["C73"]
    reserve = v["C74"] * sum(inputs["units"])
    net = requested - payoff - costs - reserve
    if -net > equity_at_refi:
        return evidence, ["aporte al refinanciar supera fondeo declarado"]
    sale_payment = loan["schedule"][len(dates) - 2 - stabilize]
    release = reserve * release_share
    evidence.update(construction_run_sha256=draw_run.sha256, permanent_run_sha256=loan_run.sha256,
                    construction_draw=rational(total_draws), construction_payoff=rational(payoff),
                    construction_origination=rational(origination), construction_interest=draws["totals"]["interest_due"],
                    refi_cost=rational(costs), refi_net=rational(net), permanent_reserve=rational(reserve),
                    permanent_reserve_released=rational(release),
                    permanent_reserve_transferred=rational(reserve - release), sale_payment=sale_payment,
                    regular_payment=loan["regular_payment_due"])
    return dict(evidence=evidence, draw=total_draws, origination_fee=origination, net_refi=net,
                reserve_release=release, balance_at_sale=amount(sale_payment["closing_balance"], 1300),
                payment=amount(loan["regular_payment_due"], 1300),
                construction_interest={dates.index(row["end_date"]): amount(row["interest_due_at_end"])
                                       for row in draws["periods"]}), []
