"""Bind staged construction invoices to T68 draws, cash interest and the equity ledger."""
from check_operating_replay_D20 import require
from miniuw_foundation.construction_draws import produce_construction_draws
from miniuw_foundation.debt_service import _date, _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from plan_return_D107 import INITIAL
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


POLICY = "SYNTHETIC-D146-staged-construction-financing"
LIFECYCLE = "SYNTHETIC-D146-construction-debt-through-sale"
RULES = dict(eligible_cost="direct_hard_excluding_contingency", commitment="lesser_of_ltc_cap_and_fixed_limit",
             draws="declared_share_of_eligible_paid_invoices", interest="simple_nominal_annual_30_360_quarter_opening_plus_draw",
             fee="fraction_of_commitment_paid_at_opening", equity="initial_then_same_day_top_up_for_verified_uses",
             payoff="principal_at_refinance_after_cash_interest_no_automatic_cash_in")


def loan_cell(rows, cell):
    row = rows[cell]
    value = _fraction(row["value"])
    require(row["state"] == "CONFIRMED_SYNTHETIC" and value is not None and 0 <= value <= 1,
            f"construction_financing_field_unconfirmed_or_out_of_range:{cell}")
    return value


def cash_amount(value, ref):
    return dict(value=rational(value), currency="USD", source_ref=ref)


def staged_construction_financing(raw, name, review, context, development, budget, calendar, *, construction_quote=None):
    source = object_or_empty(raw)
    rule_ref = source.get("policy_ref")
    require(source.get("policy") == POLICY and source.get("rules") == RULES and synthetic_id(rule_ref),
            "construction_financing_policy_unconfirmed")
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    term_ref = record.get("source_ref")
    require(synthetic_id(term_ref) and record.get("currency") == "USD", "construction_term_sheet_unconfirmed")
    cap, draw_share, per_checkpoint = (_fraction(record.get(key)) for key in
                                       ("maximum_commitment", "requested_invoice_fraction", "available_per_draw_checkpoint"))
    require(cap is not None and cap >= 0 and draw_share is not None and 0 <= draw_share <= 1
            and per_checkpoint is not None and per_checkpoint >= 0, "construction_bank_limit_or_draw_share_unconfirmed")
    maturity_text = record.get("maturity_date")
    require(isinstance(maturity_text, str), "construction_maturity_unconfirmed")
    maturity = _date(maturity_text)
    require(maturity.isoformat() == maturity_text, "construction_maturity_unconfirmed")
    rows = {row["value_cell"].split("!")[1]: row for row in review["rows"]}
    ltc, annual, fee_rate = (loan_cell(rows, cell) for cell in ("C51", "C52", "C53"))
    cells = {cell: f"sha256:{review['workbook_sha256']}#{rows[cell]['value_cell']}" for cell in ("C51", "C52", "C53")}
    bank_document = None
    if construction_quote is not None:
        from worksheet_evidence_pdf_D156 import bind_document_terms
        candidate = dict(ltc=rational(ltc), annual_interest=rational(annual), origination_fee_fraction=rational(fee_rate),
                         maximum_commitment=record["maximum_commitment"], requested_invoice_fraction=record["requested_invoice_fraction"],
                         available_per_draw_checkpoint=record["available_per_draw_checkpoint"], maturity_date=maturity_text)
        bank_document = bind_document_terms(construction_quote, candidate, "construction_pdf_and_worksheet_terms_disagree")
        if bank_document["blockers"]:
            return dict(state="PENDING", blockers=[f"B08:{reason}" for reason in bank_document["blockers"]],
                        bank_document_binding=bank_document, cell_sources=cells)
        term_ref = f"sha256:{sha(encoded(bank_document))}#/quote"
    eligible_cost = _fraction(budget["direct_hard_cost"])
    eligible_upfront = eligible_cost * _fraction(calendar["upfront_direct_hard_share"])
    commitment = min(eligible_cost * ltc, cap)
    origination_fee = commitment * fee_rate
    purchase, first_work, finish, refi = (calendar[key] for key in
                                           ("purchase_date", "upfront_date", "construction_finish", "refinance_date"))
    dates = calendar["equity_dates"][:calendar["equity_dates"].index(refi) + 1]
    eligible_by_day = dict.fromkeys(dates, 0)
    eligible_by_day[first_work] += eligible_upfront
    eligible_by_day[finish] += eligible_cost - eligible_upfront
    gross_draws = eligible_cost * draw_share
    budget_ref = f"sha256:{sha(encoded(budget))}"
    calendar_ref = f"sha256:{sha(encoded(calendar))}"
    periods = []
    for start, end in zip(dates[:-1], dates[1:]):
        period = f"SYNTHETIC-D146-{start}-{end}"
        periods.append(dict(
            period_id=period, start_date=start, end_date=end, interval_basis_ref=f"{calendar_ref}#/equity_dates",
            draw_at_start=cash_amount(eligible_by_day[start] * draw_share, f"{term_ref}/eligible-invoice-draw"),
            available_new_draw=cash_amount(per_checkpoint if start in (first_work, finish) else 0, term_ref),
            principal_repayment_at_end=cash_amount(gross_draws if end == refi else 0, f"{rule_ref}/principal-at-refinance"),
            interest_fraction=dict(value=rational(annual / 4), unit="simple_interval_fraction",
                                   source_ref=cells["C52"], interval_ref=period)))
    spec = dict(schema="miniuw.synthetic-construction-draws.v1",
                profile="SYNTHETIC-START-DRAW-END-REPAY-SIMPLE-INTERVAL-NONREVOLVING-v1", context=context, currency="USD",
                loan_id=f"SYNTHETIC-D146-{name}-construction-loan", start_date=purchase, end_date=refi,
                maturity_date=record["maturity_date"], inventory_declared_complete=True,
                zero_opening_principal_basis_ref=rule_ref, nonrevolving_commitment_basis_ref=term_ref,
                principal_commitment=cash_amount(commitment, cells["C51"]),
                draw_fee_fraction=dict(value=rational(0), unit="gross_draw_fraction", source_ref=f"{rule_ref}/fee-only-at-opening"),
                periods=periods)
    run = produce_construction_draws(encoded(spec))
    proof = run.payload
    evidence = dict(cell_sources=cells, policy_ref=rule_ref, terms_source_ref=term_ref, rules=source["rules"],
                    calendar_ref=calendar_ref, budget_ref=budget_ref, eligible_direct_hard=rational(eligible_cost),
                    ltc=rational(ltc), ltc_limit=rational(eligible_cost * ltc), contractual_limit=rational(cap),
                    commitment=rational(commitment), annual_interest=rational(annual), origination_fee_fraction=rational(fee_rate),
                    origination_fee=rational(origination_fee), debt_source=spec, debt_run=proof, debt_run_sha256=run.sha256)
    if bank_document is not None:
        evidence["bank_document_binding"] = bank_document
    if proof["blockers"]:
        return evidence | dict(state="PENDING", blockers=proof["blockers"])
    require(_fraction(proof["totals"]["principal_repaid"]) == gross_draws
            and _fraction(proof["totals"]["terminal_principal"]) == 0, "construction_principal_rollforward_mismatch")

    land = _fraction(development["evaluated_purchase_price"]) + _fraction(development["land_closing_cost"])
    early_uses = _fraction(budget["uses_and_reserve_through_early_date"])
    project_uses = _fraction(budget["total_development_cost"]) + _fraction(calendar["lease_up_funding"])
    uses = dict.fromkeys(dates, 0)
    uses[purchase] += land
    uses[first_work] += early_uses - land
    uses[finish] += project_uses - early_uses
    draws = {row["start_date"]: _fraction(row["draw_at_start"]) for row in proof["periods"]}
    interest = {row["end_date"]: _fraction(row["interest_due_at_end"]) for row in proof["periods"]}
    balance = total_equity = 0
    cash_by_date = []
    equity_draws = []
    for day in dates:
        fee = origination_fee if day == purchase else 0
        draw, interest_payment = draws.get(day, 0), interest.get(day, 0)
        before_equity = balance + draw - uses[day] - interest_payment - fee
        equity = INITIAL if day == purchase else max(0, -before_equity)
        closing = before_equity + equity
        require(closing >= 0, "initial_equity_cannot_cover_purchase_and_financing_fee")
        cash_by_date.append(dict(date=day, opening_free_cash=rational(balance), eligible_invoices=rational(eligible_by_day[day]),
                                 project_uses=rational(uses[day]), loan_draw=rational(draw), interest_paid=rational(interest_payment),
                                 origination_fee_paid=rational(fee), equity_contribution=rational(equity), closing_free_cash=rational(closing)))
        if day != purchase and equity > 0:
            equity_draws.append(dict(event_id=f"construction-funding-{day}", date=day, amount=rational(equity)))
        total_equity += equity
        balance = closing
    require(total_equity + gross_draws == project_uses + origination_fee + _fraction(proof["totals"]["interest_due"]) + balance,
            "construction_funding_does_not_reconcile")
    return evidence | dict(state="computed_synthetic", blockers=[], cash_by_date=cash_by_date, equity_draws=equity_draws,
                           equity_funding_through_refinance=rational(total_equity), free_cash_at_refinance=rational(balance),
                           construction_principal_payoff=proof["totals"]["principal_repaid"], payoff_date=refi)
