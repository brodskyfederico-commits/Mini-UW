"""Reconcile the archived synthetic construction debt and sale cases in D18 and D17."""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require, resolve, select


STRUCTURE = "docs/current-structure/"
CASE_CHAIN = ["/phased_settled_source_utf8", "/current_settled_source_utf8", "/case_source_utf8"]
DEBT_EVENTS = {
    "loan_draw": ("draw", "start_date", "draw_at_start"),
    "debt_fee_payment": ("gross_draw_fee", "start_date", "fee_due_at_start"),
    "debt_interest_payment": ("interest", "end_date", "interest_due_at_end"),
    "loan_principal_repayment": ("principal_repayment", "end_date", "principal_repayment_at_end"),
}
INFLOWS = {"initial_equity_contribution", "additional_equity_contribution", "loan_draw", "other_cash_receipt"}
OUTFLOWS = {"equity_distribution", "acquisition_payment", "construction_payment", "soft_cost_payment",
            "other_cash_payment"} | (DEBT_EVENTS.keys() - INFLOWS)
CLOSING_SIGNS = {
    "opening_free_cash": 1, "gross_proceeds": 1, "reserve_release": 1, "other_cash_sources": 1,
    "closing_costs_paid": -1, "new_reserve": -1, "other_cash_uses": -1, "retained_free_cash": -1,
    "opening_restricted_cash": 0, "closing_restricted_cash_claim": 0,
}
DEBT_FIELDS = ("principal", "interest", "fees", "other")
CONTRIBUTIONS = {"initial_equity_contribution": "initial_capital", "additional_equity_contribution": "additional_capital"}


def digest(raw):
    return sha256(raw.encode("utf-8")).hexdigest()


def verify_amounts(row, expected, label):
    for field, value in expected.items():
        require(amount(row[field]) == value, f"{label}: {field} differs")


def replay_periods(loan, archived):
    require(loan["profile"] == "SYNTHETIC-START-DRAW-END-REPAY-SIMPLE-INTERVAL-NONREVOLVING-v1"
            and loan["inventory_declared_complete"] and loan["zero_opening_principal_basis_ref"]
            and loan["nonrevolving_commitment_basis_ref"], "Unexpected construction loan profile")
    commitment = amount(loan["principal_commitment"])
    fee = amount(loan["draw_fee_fraction"])
    require(loan["draw_fee_fraction"]["unit"] == "gross_draw_fraction" and fee >= 0, "Unexpected draw fee")
    require(len(loan["periods"]) == len(archived) == 3, "Expected three construction periods")
    principal = drawn = Fraction()
    end = loan["start_date"]
    periods = {}
    for index, (source, row) in enumerate(zip(loan["periods"], archived)):
        period_id = source["period_id"]
        require(period_id not in periods and source["start_date"] == end < source["end_date"],
                f"Invalid construction period sequence: {period_id}")
        require(row["period_index"] == index and all(row[key] == source[key] for key in
                ("period_id", "start_date", "end_date")), f"Construction period identity differs: {period_id}")
        end = source["end_date"]
        draw = amount(source["draw_at_start"])
        available = amount(source["available_new_draw"])
        repay = amount(source["principal_repayment_at_end"])
        rate = amount(source["interest_fraction"])
        exposure = principal + draw
        require(source["interest_fraction"]["unit"] == "simple_interval_fraction"
                and source["interest_fraction"]["interval_ref"] == period_id and source["interval_basis_ref"],
                f"Interest basis differs: {period_id}")
        require(0 <= draw <= min(available, commitment - drawn) and 0 <= repay <= exposure and rate >= 0,
                f"Draw or repayment outside supplied limits: {period_id}")
        drawn += draw
        values = dict(opening_principal=principal, draw=draw, declared_period_available_draw=available,
                      interest_exposure=exposure, supplied_interval_factor=rate, interest=exposure * rate,
                      gross_draw_fee=draw * fee, principal_repayment=repay, closing_principal=exposure - repay,
                      cumulative_gross_draws=drawn, nonrevolving_commitment_remaining=commitment - drawn,
                      commitment_minus_outstanding_not_draw_capacity=commitment - exposure + repay)
        verify_amounts(row, values, period_id)
        periods[period_id] = (index, source, values)
        principal = values["closing_principal"]
    require(end == loan["end_date"] <= loan["maturity_date"], "Construction loan boundary differs")
    return periods, principal, drawn, commitment


def replay_preopening(bundle, register, root):
    pre = json.loads(bundle["preopening_source"])
    binding = json.loads(bundle["binding_source"])
    require(len(bundle["loans"]) == len(binding["loans"]) == len(pre["loan_ids"]) == 1,
            "Expected a single construction liability")
    loan_raw = bundle["loans"][0]["source"]
    loan = json.loads(loan_raw)
    loan_id = loan["loan_id"]
    bound_loan = binding["loans"][0]
    run = bundle["expected_run"]
    saved = json.loads(run["payload_json"])
    cash_run = saved["preopening_run"]
    cash_saved = json.loads(cash_run["payload_json"])
    compiled = json.loads(saved["compiled_preopening_json"])
    require(run == resolve(root, register["saved_construction_run_ref"])
            and cash_run == resolve(root, register["saved_preopening_run_ref"])
            and digest(run["payload_json"]) == run["sha256"]
            and digest(cash_run["payload_json"]) == cash_run["sha256"]
            and digest(saved["compiled_preopening_json"]) == saved["compiled_preopening_source_sha256"]
            == cash_saved["source_sha256"], "Saved construction or preopening run differs")
    require(digest(bundle["preopening_source"]) == binding["preopening_source_sha256"]
            == saved["preopening_source_sha256"] and digest(bundle["binding_source"]) == saved["binding_source_sha256"]
            and loan_id == pre["loan_ids"][0] == bound_loan["loan_id"]
            and digest(loan_raw) == bound_loan["source_sha256"]
            and bound_loan["run_sha256"] == saved["staged_loan_run_sha256s"][loan_id],
            "Construction source or liability binding differs")
    require(pre["profile"] == "SYNTHETIC-ZERO-OPENING-PREOPERATING-CASH-v1"
            and pre["inventory_declared_complete"] and pre["zero_opening_basis_ref"]
            and pre["currency"] == loan["currency"] == cash_saved["currency"] == "USD"
            and pre["opening_operation_date"] == loan["end_date"], "Unexpected preopening profile")
    periods, principal, draws, commitment = replay_periods(loan, register["loan_periods"])
    slots = {slot["target_event_id"]: slot for slot in binding["event_slots"]}
    require(len(slots) == len(binding["event_slots"]) == 12, "Expected twelve unique debt slots")
    require(len(pre["events"]) == len(compiled["events"]) == len(cash_saved["events"])
            == len(register["preopening_events"]) == 17, "Expected seventeen preopening events")
    events_by_date = {}
    totals = Counter()
    used_slots = set()
    seen_events = set()
    equity_events = []
    for event, effective, saved_event, row in zip(pre["events"], compiled["events"], cash_saved["events"],
                                                   register["preopening_events"]):
        event_id, date, category = (event[key] for key in ("event_id", "date", "category"))
        require(event_id not in seen_events and category in INFLOWS | OUTFLOWS
                and all(event[key] == effective[key] == row[key] for key in ("event_id", "date", "category", "loan_id"))
                and event["amount"]["currency"] == effective["amount"]["currency"] == "USD",
                f"Preopening event identity differs: {event_id}")
        seen_events.add(event_id)
        linked = category in DEBT_EVENTS
        if linked:
            slot = slots[event_id]
            period_id = slot["period_id"]
            field, date_field, source_field = DEBT_EVENTS[category]
            index, period, values = periods[period_id]
            slot_key = (period_id, category)
            require(slot_key not in used_slots and event["loan_id"] == slot["loan_id"] == loan_id
                    and category == slot["category"] and date == period[date_field]
                    and event["amount"]["value"] is event["amount"]["source_ref"] is None,
                    f"Debt slot identity differs: {event_id}")
            used_slots.add(slot_key)
            value = values[field]
            source_ref = f"miniuw:construction-draws:{bound_loan['run_sha256']}#/periods/{index}/{source_field}"
            require(effective["amount"]["source_ref"] == source_ref, f"Debt slot provenance differs: {event_id}")
        else:
            value = amount(event["amount"])
            require(event == effective and event["loan_id"] is None, f"Direct event differs: {event_id}")
        sign = 1 if category in INFLOWS else -1
        require(0 <= value == amount(effective["amount"]) and effective == saved_event
                and row["original_value"] == event["amount"]["value"] and row["original_null_preserved"] is linked
                and row["cash_sign"] == sign, f"Preopening event differs: {event_id}")
        verify_amounts(row, dict(effective_amount=value, signed_free_cash=sign * value), event_id)
        events_by_date.setdefault(date, []).append((event_id, category, value, sign))
        totals[category] += value
        if category in CONTRIBUTIONS:
            equity_events.append(dict(source_event_id=event_id, date=date, kind="contribution",
                                      category=CONTRIBUTIONS[category], amount=str(value)))
    require(len(used_slots) == len(slots), "Unused construction debt slot")

    cash = balance = Fraction()
    dates = sorted(events_by_date)
    require(len(dates) == len(register["date_close_rows"]) == len(cash_saved["date_close_balances"]) == 4,
            "Expected four preopening closing dates")
    for date, row, saved_row in zip(dates, register["date_close_rows"], cash_saved["date_close_balances"]):
        events = events_by_date[date]
        receipts = sum(value for _, _, value, sign in events if sign == 1)
        uses = sum(value for _, _, value, sign in events if sign == -1)
        opening = cash
        cash += receipts - uses
        balance += sum(value for _, kind, value, _ in events if kind == "loan_draw")
        balance -= sum(value for _, kind, value, _ in events if kind == "loan_principal_repayment")
        require(date == row["date"] == saved_row["date"] and row["event_ids"] == [item[0] for item in events],
                f"Preopening closing date differs: {date}")
        verify_amounts(row, dict(opening_free_cash=opening, gross_cash_sources=receipts, gross_cash_uses=uses,
                                closing_free_cash=cash, closing_restricted_cash=0, closing_loan_principal=balance),
                       date)
        verify_amounts(saved_row, dict(free_cash=cash, restricted_cash=0), date)
        require(amount(saved_row["loan_principal"][loan_id]) == balance, f"Saved principal differs: {date}")
    terminal = pre["terminal_claims"]
    verify_amounts(terminal, dict(free_cash=cash, restricted_cash=0), "Preopening terminal claims")
    require(amount(terminal["loan_principal"][loan_id]) == balance == principal, "Terminal principal differs")
    archived_totals = {row["category"]: row["amount"] for row in register["category_totals"]}
    require(len(register["category_totals"]) == len(archived_totals) == len(cash_saved["totals"]) == 14
            and set(archived_totals) == set(cash_saved["totals"]) and totals.keys() <= archived_totals.keys(),
            "Preopening category inventory differs")
    verify_amounts(archived_totals, {key: totals[key] for key in archived_totals}, "D18 category totals")
    verify_amounts(cash_saved["totals"], {key: totals[key] for key in archived_totals}, "Saved category totals")
    equity = totals["initial_equity_contribution"] + totals["additional_equity_contribution"]
    summary = dict(gross_equity=equity, gross_draws=draws, principal_repayments=totals["loan_principal_repayment"],
                   paid_acquisition_construction_soft_costs=sum(totals[key] for key in
                                                              ("acquisition_payment", "construction_payment", "soft_cost_payment")),
                   paid_interest_and_draw_fees=totals["debt_interest_payment"] + totals["debt_fee_payment"],
                   closing_free_cash=cash, closing_principal=principal, commitment=commitment,
                   unused_nonrevolving_commitment=commitment - draws)
    verify_amounts(register["observed_summary"], summary, "D18 summary")
    summary["equity_events"] = equity_events
    return summary, bound_loan, pre["opening_operation_date"]


def verify_checks(rows, comparisons):
    require(len(rows) == len(comparisons), "Reconciliation check count differs")
    for index, (row, (left, right)) in enumerate(zip(rows, comparisons), start=1):
        label = f"B{index:02d}"
        require(row["check_id"] == label and left == right, f"Reconciliation differs: {label}")
        verify_amounts(row, dict(left=left, right=right, residual=0), label)


def replay_holding(case, phase, source_hash, summary, bound_loan, bundle, closing, saved, opening_checks,
                   operating):
    phase_loan, = phase["loan_phases"]
    sale_loan, = case["sale"]["loans"]
    schedule_raw = phase_loan["schedule_source_utf8"]
    loan = json.loads(schedule_raw)
    debt, = closing["old_debts"]
    require(phase["profile"] == "SYNTHETIC-SAME-LIABILITY-NO-NEW-CASH-NO-EXTENSION-v1"
            and all(phase_loan[key] is True for key in ("same_liability_declared", "no_new_cash_declared",
                    "no_principal_adjustments_declared", "prior_interest_fees_settled_declared"))
            and source_hash == phase["construction_bundle_sha256"]
            and bundle["expected_run"]["sha256"] == phase["construction_cash_run_sha256"]
            and phase_loan["construction_loan_source_sha256"] == bound_loan["source_sha256"]
            and phase_loan["construction_loan_run_sha256"] == bound_loan["run_sha256"]
            and schedule_raw == sale_loan["source"]
            and bound_loan["loan_id"] == phase_loan["loan_id"] == loan["loan_id"] == debt["loan_id"],
            "Construction, operating and sale liability binding differs")
    require(amount(loan["periodic_rate"]) == 0 and loan["fixed_rate"] is True
            and all(loan[key] is False for key in ("interest_only", "capitalized_fees", "new_draws"))
            and loan["payment_timing"] == "arrears" and loan["rounding"] == "none_exact"
            and loan["amortization_payments"] > 0, "Unsupported archived amortization profile")
    periods = [json.loads(period["cash_source_utf8"]) for period in case["periods"]]
    first, last = periods
    cut = closing["closing_date"]
    dates = loan["payment_dates"]
    require(dates == sorted(set(dates)) and first["start_date"] < first["end_date"] == last["start_date"]
            < last["end_date"] == cut, "Operating windows or payment dates differ")
    verify_amounts(last["amounts"], {
        key: amount(saved["current_operating_totals"][key])
        for key in ("closing_free_cash_claim", "closing_restricted_cash_claim")
    }, "Operating balances at sale")
    prior = [date for date in dates if date < cut]
    coincident = [date for date in dates if date == cut]
    require(len(coincident) == 1 and all(first["start_date"] <= date for date in prior),
            "Expected one coincident payment and no prior payments outside operations")
    original = amount(loan["principal"])
    installment = original / loan["amortization_payments"]
    operating_principal = Fraction()
    for index, period in enumerate(periods):
        count = sum(period["start_date"] <= date < period["end_date"] for date in dates)
        payment = count * installment
        if operating is None:
            verify_amounts(period["amounts"], dict(debt_principal_payment=payment, debt_interest_payment=0),
                           period["period_ref"])
        else:
            replayed = operating["period_amounts"][index]
            paid = replayed["debt_principal_payment"]
            require(paid == payment and replayed["debt_interest_payment"] == 0,
                    f"Operating debt payments differ from schedule: {period['period_ref']}")
            payment = paid
        operating_principal += payment
    principal_at_cut = original - operating_principal
    opening = (operating["period_amounts"][0] if operating is not None else
               {key: amount(first["amounts"][key]) for key in ("opening_free_cash", "opening_restricted_cash")})
    verify_checks(opening_checks, [
        (summary["closing_free_cash"], opening["opening_free_cash"]),
        (summary["closing_principal"], original),
        (0, opening["opening_restricted_cash"]),
        (summary["gross_equity"], amount(saved["current_project_return_story"]["gross_contributions"])),
    ])
    return prior, coincident, installment, principal_at_cut, operating_principal


def closing_terms(snapshot, closing, input_ref, root):
    coefficients = {f"/amounts/{key}": sign for key, sign in CLOSING_SIGNS.items()}
    for key in DEBT_FIELDS:
        coefficients[f"/old_debts/0/{key}_paid"] = -1
        coefficients[f"/old_debts/0/{key}_due"] = 0
    coefficients["/valuation_claim"] = 0
    claims = snapshot["closing_claim_inventory"]
    terms = {row["inventory_claim_id"]: row for row in snapshot["free_cash_terms"]}
    pointers = {row["source_ref"]["final_pointer"] for row in claims}
    require(len(claims) == len(pointers) == 19 and pointers == coefficients.keys()
            and len({row["claim_id"] for row in claims}) == 19
            and len(terms) == len(snapshot["free_cash_terms"]) == 12, "Closing inventory differs")
    residual = Fraction()
    for row in claims:
        ref = row["source_ref"]
        pointer = ref["final_pointer"]
        sign = coefficients[pointer]
        claim = select(closing, pointer)
        require(ref == (input_ref | {"embedded_json_pointers": CASE_CHAIN + ["/sale/closing_source_utf8"],
                                    "final_pointer": pointer})
                and claim == resolve(root, ref) == row["declared_claim"] and claim["currency"] == "USD"
                and claim["as_of_date"] == closing["closing_date"] and claim["source_ref"]
                and row["coefficient_in_free_cash_residual"] == sign and row["included_in_residual"] is bool(sign),
                f"Closing claim identity or classification differs: {pointer}")
        value = None if pointer == "/valuation_claim" else amount(claim)
        require((claim["value"] is None) == (value is None) == row["missing_value"]
                and row["explicit_zero"] is (value == 0), f"Missing or zero claim differs: {pointer}")
        if value is None:
            require(row["amount"] is row["signed_cash_term"] is None, "Missing valuation must stay missing")
        else:
            require(value >= 0, f"Negative closing claim: {pointer}")
            verify_amounts(row, {"amount": value}, pointer)
        if sign:
            verify_amounts(row, {"signed_cash_term": sign * value}, pointer)
            term = terms.pop(row["claim_id"])
            require(term["source_ref"] == ref and term["coefficient"] == sign and term["role"] == row["role"],
                    f"Closing term classification differs: {pointer}")
            verify_amounts(term, dict(amount=value, signed_amount=sign * value), pointer)
            residual += sign * value
        else:
            require(row["signed_cash_term"] is None, f"Excluded claim has a cash term: {pointer}")
    require(not terms and residual > 0, "Expected the archived positive sale residual")
    return residual


def settlement_amount(case, closing, saved, operating):
    boundary = json.loads(case["boundary_source_utf8"])
    terminal = json.loads(boundary["terminal_binding_source_utf8"])
    plan = json.loads(boundary["plan_source_utf8"])
    cut = closing["closing_date"]
    require(digest(case["sale"]["closing_source_utf8"]) == terminal["closing_source_sha256"]
            and digest(boundary["plan_source_utf8"]) == terminal["plan_source_sha256"]
            and terminal["context"] == plan["context"] == closing["context"]
            and terminal["economic_item_id"] == boundary["economic_item_id"] == plan["economic_item_id"]
            and terminal["settlement_date"] == plan["cutoff_date"] == cut
            and terminal["payment_inventory_declared_complete"] is boundary["inventory_declared_complete"] is True
            and terminal["assumptions"]["other_cash_uses"] == "only_all_on_cut_payments_of_this_insurance_item"
            and terminal["assumptions"]["payment_representation"] == "already_in_supplied_closing_no_second_deduction",
            "Terminal insurance payment binding differs")
    planned, = [payment for payment in plan["planned_payments"] if payment["payment_date"] == cut]
    payment, = terminal["payments"]
    require(all(item["payment_date"] <= cut for item in plan["planned_payments"])
            and all(payment[key] == planned[key] for key in ("payment_id", "payment_date", "installment_id")),
            "On-cut insurance payment identity differs")
    account = boundary["accounting"]
    if operating is not None:
        item, = [item for item in operating["closing_items"] if item["item_id"] == boundary["economic_item_id"]]
        require(amount(item["closing_payables"]) == amount(account["before_payables"])
                and amount(item["closing_prepaid"]) == amount(account["before_prepaid"]),
                "Closing operating insurance balances differ from sale settlement")
    balance_change = (amount(account["before_payables"]) - amount(account["after_payables"])
                      + amount(account["after_prepaid"]) - amount(account["before_prepaid"]))
    settlement = amount(payment["amount"])
    require(amount(saved["current_settlement_summary"]["settlement_cash"]) == settlement,
            "Saved insurance settlement differs")
    return settlement, balance_change, amount(planned["amount"])


def replay_sale(root, snapshot, case, phase, source_hash, summary, bound_loan, bundle, saved, opening_checks,
                operating):
    closing = json.loads(case["sale"]["closing_source_utf8"])
    cut = closing["closing_date"]
    require(closing["kind"] == "sale" and closing["representation"] == "explicit_gross_cash_movements"
            and closing["profile"] == snapshot["closing_profile"] == "SYNTHETIC-RESIDUAL-AFTER-EXPLICIT-RETENTION-v1"
            and closing["new_loan"] is closing["equity_funding_assumption_ref"] is None
            and closing["debt_inventory_declared_complete"] is True
            and closing["context"] == saved["context"] == snapshot["context"]
            and closing["currency"] == snapshot["currency"] == "USD" and snapshot["closing_date"] == cut
            and set(closing["amounts"]) == CLOSING_SIGNS.keys(), "Unexpected sale closing profile")
    residual = closing_terms(snapshot, closing, snapshot["input_ref"], root)
    prior, coincident, installment, principal, holding_principal = replay_holding(
        case, phase, source_hash, summary, bound_loan, bundle, closing, saved, opening_checks, operating)
    loan_cut = snapshot["loan_cut"]
    require(prior == loan_cut["prior_payment_dates"] and coincident == loan_cut["coincident_payment_dates"]
            and loan_cut["regular_cut_payment_deducted_again"] is False, "Archived payment cut differs")
    verify_amounts(loan_cut, dict(regular_principal_per_payment=installment,
                                 principal_before_all_cut_events=principal), "Sale loan cut")
    settlement, balance_change, planned_payment = settlement_amount(case, closing, saved, operating)
    require(snapshot["insurance_payment_in_other_uses_only_once"] is True, "Insurance inclusion differs")
    cash = {key: amount(value) for key, value in closing["amounts"].items()}
    debt, = closing["old_debts"]
    debt_pairs = [(amount(debt[f"{key}_due"]), amount(debt[f"{key}_paid"])) for key in DEBT_FIELDS]
    payoff = sum(paid for _, paid in debt_pairs)
    story = saved["current_project_return_story"]
    sale_event, = [event for event in story["events"] if event["category"] == "net_sale_distribution"]
    require(sale_event["date"] == cut and amount(story["cash_by_category"]["net_sale_distribution"]) == residual,
            "Saved sale distribution differs")
    sources = sum(cash[key] for key in ("opening_free_cash", "opening_restricted_cash", "gross_proceeds",
                                         "other_cash_sources"))
    uses = payoff + residual + sum(cash[key] for key in ("closing_costs_paid", "other_cash_uses",
                                                        "retained_free_cash", "closing_restricted_cash_claim"))
    closing_cash_keys = ("closing_free_cash_claim", "closing_restricted_cash_claim")
    operating_cash = (operating["period_amounts"][-1] if operating is not None else
                      {key: amount(saved["current_operating_totals"][key]) for key in closing_cash_keys})
    verify_checks(snapshot["checks"], [
        (operating_cash["closing_free_cash_claim"], cash["opening_free_cash"]),
        (operating_cash["closing_restricted_cash_claim"], cash["opening_restricted_cash"]),
        (cash["opening_restricted_cash"] + cash["new_reserve"] - cash["reserve_release"],
         cash["closing_restricted_cash_claim"]),
        *debt_pairs,
        (balance_change, settlement),
        (settlement, cash["other_cash_uses"]),
        (planned_payment, settlement),
        (residual, amount(sale_event["amount"])),
        (sources, uses),
        (principal, amount(debt["principal_due"])),
        (holding_principal + amount(debt["principal_paid"]), amount(saved["current_holding_sale_totals"]["debt_principal"])),
    ])
    verify_amounts(snapshot, dict(free_cash_distribution=residual, total_closing_sources=sources,
                                  total_closing_uses=uses, closing_retained_free_cash=cash["retained_free_cash"],
                                  closing_restricted_cash=cash["closing_restricted_cash_claim"]), "D17 closing")
    result = dict(snapshot=snapshot["snapshot_id"], checks=14, claims=19, cash_terms=12,
                  holding_principal=str(holding_principal), sale_principal=str(principal), sale_debt_paid=str(payoff),
                  insurance_at_cut=str(settlement), closing_sources=str(sources), sale_distribution=str(residual))
    if operating is not None:
        first = operating["period_amounts"][0]
        result["input_sha256"] = snapshot["input_ref"]["sha256"]
        result["operation"] = operating["summary"]
        result["handoffs"] = {
            "construction_to_operation": dict(date=operating["period_rows"][0]["start_date"],
                                              free_cash=str(first["opening_free_cash"]),
                                              restricted_cash=str(first["opening_restricted_cash"]),
                                              principal=str(summary["closing_principal"])),
            "operation_to_sale": dict(date=cut, free_cash=str(operating_cash["closing_free_cash_claim"]),
                                      restricted_cash=str(operating_cash["closing_restricted_cash_claim"]),
                                      principal=str(principal)),
        }
    return result


def bind_operating(operating, snapshot, case, opening_date):
    input_ref = snapshot["input_ref"]
    require(operating["input_ref"] == input_ref and operating["result_ref"] == snapshot["result_ref"],
            "Operating and sale source or result references differ")
    rows = operating["period_rows"]
    require(len(rows) == len(operating["period_amounts"]) == len(case["periods"])
            and rows[0]["start_date"] == opening_date, "Construction and operating cutoffs differ")
    for index, row in enumerate(rows):
        for source in ("noi", "cash", "detail"):
            chain = CASE_CHAIN + (["/boundary_source_utf8"] if source == "detail" else [])
            expected_ref = input_ref | {
                "embedded_json_pointers": chain + [f"/periods/{index}/{source}_source_utf8"],
                "final_pointer": "",
            }
            require(row[f"{source}_source_ref"] == expected_ref, f"Operating period {source} source differs: {index}")


def return_cash_events(summary, operating, case, sale):
    events = list(summary["equity_events"])
    for row, values in zip(operating["period_rows"], operating["period_amounts"]):
        for kind, category, field in (
            ("contribution", "additional_capital", "equity_contribution"),
            ("distribution", "operating_distribution", "planned_operating_distribution"),
        ):
            events.append(dict(source_event_id=f"{row['period_ref']}:{kind}", date=row["cash_date"],
                               kind=kind, category=category, amount=str(values[field])))
    closing_id = case["sale"]["closing_id"]
    cut = sale["handoffs"]["operation_to_sale"]["date"]
    # The checked sale profile has a positive residual and no additional equity funding.
    events.extend([
        dict(source_event_id=f"{closing_id}:contribution", date=cut, kind="contribution",
             category="additional_capital", amount="0"),
        dict(source_event_id=f"{closing_id}:distribution", date=cut, kind="distribution",
             category="net_sale_distribution", amount=sale["sale_distribution"]),
    ])
    return events


def run(root=ROOT, *, operating_by_input=None, include_return_cash=False):
    d18 = json.loads(local_file(root, STRUCTURE + "MiniUW_Presupuesto_Deuda_y_Aportes_D18.json").read_bytes())
    d17 = json.loads(local_file(root, STRUCTURE + "MiniUW_Cierre_y_Uso_Unico_D17.json").read_bytes())
    snapshots = d17["snapshots"]
    bindings = d18["outer_snapshot_bindings"]
    require(d18["snapshot_id"] == "D18" and d17["snapshot_id"] == "D17"
            and [row["snapshot_id"] for row in snapshots] == ["S01", "S02"] and len(bindings) == 2,
            "Expected both archived D17 and D18 snapshots")
    require(not include_return_cash or operating_by_input is not None, "Return cash requires integrated operating evidence")
    if operating_by_input is not None:
        require(operating_by_input.keys() == {row["input_ref"]["path"] for row in snapshots},
                "Expected operating evidence for both sale snapshots")
    bundle_raw = resolve(root, bindings[0]["bundle_ref"])
    source_hash = digest(bundle_raw)
    require(source_hash == d18["shared_bundle_UTF8_sha256"], "Shared construction bundle hash differs")
    bundle = json.loads(bundle_raw)
    summary, bound_loan, opening_date = replay_preopening(bundle, d18, root)
    results = []
    for snapshot, binding in zip(snapshots, bindings):
        input_ref = snapshot["input_ref"]
        require(binding["input_ref"] == input_ref and binding["result_ref"] == snapshot["result_ref"],
                "D17 and D18 snapshot references differ")
        case = resolve(root, input_ref | {"embedded_json_pointers": CASE_CHAIN})
        phase_raw = case["phase_source_utf8"]
        require(case["construction_bundle_utf8"] == bundle_raw == resolve(root, binding["bundle_ref"])
                and source_hash == binding["bundle_UTF8_sha256"]
                and phase_raw == resolve(root, binding["phase_ref"])
                and digest(phase_raw) == binding["phase_UTF8_sha256"], "Bundle or phase snapshot differs")
        saved = resolve(root, snapshot["result_ref"])
        require(saved["source_sha256"] == input_ref["sha256"]
                and saved["decision"] == snapshot["financial_decision"] == binding["financial_decision"] == "PENDING"
                and saved["real_decisions_enabled"] is saved["deployment_enabled"] is False
                and saved["personal_investor_return"] is None, "Saved result binding or synthetic status differs")
        operating = None
        if operating_by_input is not None:
            operating = operating_by_input[input_ref["path"]]
            bind_operating(operating, snapshot, case, opening_date)
        sale = replay_sale(root, snapshot, case, json.loads(phase_raw), source_hash, summary, bound_loan,
                           bundle, saved, d18["opening_boundary_checks"], operating)
        if include_return_cash:
            sale["return_cash"] = dict(input_ref=input_ref, result_ref=snapshot["result_ref"],
                                       events=return_cash_events(summary, operating, case, sale))
        results.append(sale)
    return dict(status="passed", decision="PENDING", construction=dict(periods=3, events=17, linked_nulls=12,
                dates=4, gross_draws=str(summary["gross_draws"]), closing_principal=str(summary["closing_principal"]),
                closing_free_cash=str(summary["closing_free_cash"]),
                unused_nonrevolving_commitment=str(summary["unused_nonrevolving_commitment"])), snapshots=results)


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
