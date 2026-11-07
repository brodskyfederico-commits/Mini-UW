"""Reconcile the two synthetic operating snapshots archived in D19."""
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json
import sys

from check_reference_package import local_file, require


ROOT = Path(__file__).resolve().parents[1]
REGISTER = "docs/current-structure/MiniUW_NOI_Pagos_y_Distribuciones_D19.json"


def resolve(root, reference):
    raw = local_file(root, reference["path"]).read_bytes()
    require(sha256(raw).hexdigest() == reference["sha256"], f"Hash mismatch: {reference['path']}")
    document = json.loads(raw)
    for pointer in reference["embedded_json_pointers"]:
        document = json.loads(select(document, pointer))
    return select(document, reference["final_pointer"])


def select(document, pointer):
    if pointer == "":
        return document
    require(pointer.startswith("/"), "Expected an absolute JSON pointer")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(document, list):
            require(token.isdecimal() and str(int(token)) == token, "Invalid array index")
            document = document[int(token)]
        else:
            document = document[token]
    return document


def amount(value):
    if "value" in value:
        value = value["value"]
    require(isinstance(value["numerator"], str) and isinstance(value["denominator"], str),
            "Expected exact rational components as strings")
    numerator = int(value["numerator"])
    denominator = int(value["denominator"])
    require(denominator > 0, "Expected a positive denominator")
    return Fraction(numerator, denominator)


def replay_period(root, row, expenses, payments, input_path):
    for key in ("noi_source_ref", "cash_source_ref", "detail_source_ref"):
        require(row[key]["path"] == input_path, "Period points to a different input")
    noi = resolve(root, row["noi_source_ref"])
    cash = resolve(root, row["cash_source_ref"])
    detail = resolve(root, row["detail_source_ref"])
    period = cash["period_ref"]
    require(row["period_ref"] == noi["period_ref"] == detail["period_ref"] == period, "Period mismatch")
    require(noi["currency"] == cash["currency"] == detail["currency"] == "USD", "Currency mismatch")
    require(noi["context"] == cash["context"] == detail["context"], "Period context mismatch")
    for key in ("start_date", "end_date"):
        require(row[key] == cash[key] == detail[key], f"Period cutoff mismatch: {key}")
    require(amount(noi["tax_floor"]) == amount(noi["tax_coefficient"]) == 0, "Expected D19 zero-tax fixture")
    require(amount(cash["amounts"]["noncash_expense"]) == 0, "Noncash expense outside D19 scope")
    require(detail["inventory_declared_complete"] is True, "Expense inventory incomplete")
    items = {item["item_id"]: item for item in detail["items"]}
    pointers = {f"/expense_rows/{index}" for index in range(len(noi["expense_rows"]))}
    pointers.add("/property_tax")
    require(len(items) == len(detail["items"]) == len(expenses) == len(pointers), "Expense inventory size mismatch")
    require({item["noi_pointer"] for item in items.values()} == pointers, "NOI expense pointers differ")

    paid_by_item = Fraction()
    listed = {}
    for expense in expenses:
        item = items.pop(expense["detail_item_id"])
        pointer = item["noi_pointer"]
        accrued = Fraction() if pointer == "/property_tax" else amount(select(noi, pointer))
        require(accrued == amount(item["expense_amount"]) == amount(expense["expense_amount"]), "Accrual mismatch")
        expected = accrued + amount(item["opening_payables"]) - amount(item["closing_payables"])
        expected += amount(item["closing_prepaid"]) - amount(item["opening_prepaid"])
        require(item["payments_inventory_declared_complete"] is True, "Payment inventory incomplete")
        paid = Fraction()
        for payment in item["payments"]:
            payment_id = payment["payment_id"]
            require(payment_id not in listed, "Duplicate payment ID")
            require(cash["start_date"] <= payment["date"] < cash["end_date"], "Payment outside its period")
            value = amount(payment["amount"])
            listed[payment_id] = (item["item_id"], payment["date"], value)
            paid += value
        require(expected == paid == amount(expense["expected_payments"]) == amount(expense["listed_payments"]),
                "Payment reconciliation differs")
        paid_by_item += paid
    observed = {payment["payment_id"]: (payment["detail_item_id"], payment["date"], amount(payment["amount"]))
                for payment in payments}
    require(len(observed) == len(payments) and observed == listed, "Archived payments differ")

    balances = cash["working_balances"]
    changes = {name: amount(pair["closing"]) - amount(pair["opening"]) for name, pair in balances.items()}
    for name, suffix in (("payables", "payables"), ("prepaid_expenses", "prepaid")):
        for cut in ("opening", "closing"):
            stock = sum(amount(item[f"{cut}_{suffix}"]) for item in detail["items"])
            require(stock == amount(balances[name][cut]), f"Expense stocks differ: {period} {cut} {name}")
    values = {key: amount(value) for key, value in cash["amounts"].items()}
    income = sum(amount(item) for item in noi["income_rows"])
    accrued_cost = sum(amount(item) for item in noi["expense_rows"])
    receipts = income - values["noncash_revenue"] - changes["receivables"] + changes["advance_income"]
    paid = accrued_cost - values["noncash_expense"] - changes["payables"] + changes["prepaid_expenses"]
    require(receipts == values["operating_receipts_claim"], "Receipt claim differs")
    require(paid == values["operating_payments_claim"] == paid_by_item, "Operating payment claim differs")
    net = receipts - paid
    sources = ("opening_free_cash", "nonfinancing_other_cash_receipt", "reserve_release", "equity_contribution")
    uses = ("debt_principal_payment", "debt_interest_payment", "debt_fee_payment", "capital_expenditure",
            "other_cash_payment", "reserve_deposit")
    before = net + sum(values[key] for key in sources) - sum(values[key] for key in uses)
    closing = before - values["planned_operating_distribution"]
    restricted = values["opening_restricted_cash"] + values["reserve_deposit"] - values["reserve_release"]
    require(closing == values["closing_free_cash_claim"], "Closing free cash differs")
    require(restricted == values["closing_restricted_cash_claim"], "Closing restricted cash differs")
    values.update(accrued_NOI=income - accrued_cost, operating_receipts=receipts,
                  operating_payments=paid, net_operating_cash=net, free_cash_before_proposed_distribution=before)
    for key in ("accrued_NOI", "operating_receipts", "operating_payments", "net_operating_cash",
                "free_cash_before_proposed_distribution", "planned_operating_distribution",
                "closing_free_cash_claim", "closing_restricted_cash_claim"):
        require(values[key] == amount(row[key]), f"D19 period value differs: {period} {key}")
    return values, balances, detail["items"]


def run(root=ROOT):
    register = json.loads(local_file(root, REGISTER).read_bytes())
    snapshots = register["snapshots"]
    require(register["snapshot_id"] == "D19" and [s["snapshot_id"] for s in snapshots] == ["O01", "O02"],
            "Expected both archived D19 snapshots")
    results = []
    for snapshot in snapshots:
        input_ref = snapshot["input_ref"]
        resolve(root, input_ref)
        saved = resolve(root, snapshot["result_ref"])
        require(saved["source_sha256"] == input_ref["sha256"] and saved["decision"] == "PENDING",
                "Archived result/input binding or decision differs")
        rows = snapshot["period_rows"]
        expenses = snapshot["expense_rows"]
        payments = snapshot["payment_rows"]
        require([row["period_index"] for row in rows] == [0, 1], "Expected two operating periods")
        require(len(expenses) == 6 and len(payments) == 4, "Archived expense or payment count differs")
        periods = []
        for index, row in enumerate(rows):
            periods.append(replay_period(root, row, [x for x in expenses if x["period_index"] == index],
                                         [x for x in payments if x["period_index"] == index], input_ref["path"]))
        (first, first_balances, first_items), (last, last_balances, last_items) = periods
        require(rows[0]["end_date"] == rows[1]["start_date"], "Operating dates are not contiguous")
        for key in first_balances:
            require(amount(first_balances[key]["closing"]) == amount(last_balances[key]["opening"]),
                    f"Working balance does not carry forward: {key}")
        for kind in ("free", "restricted"):
            require(first[f"closing_{kind}_cash_claim"] == last[f"opening_{kind}_cash"], f"Opening {kind} cash differs")
        for stock in ("payables", "prepaid"):
            closing_items = {item["item_id"]: amount(item[f"closing_{stock}"]) for item in first_items}
            opening_items = {item["item_id"]: amount(item[f"opening_{stock}"]) for item in last_items}
            require(closing_items == opening_items, f"Expense balances do not carry forward: {stock}")
        totals = saved["current_operating_totals"]
        comparisons = snapshot["aggregate_comparisons"]
        archived = {row["field"]: amount(row["calculated"]) for row in comparisons}
        require(len(comparisons) == len(archived) == len(totals) == 17 and set(totals) == set(archived),
                "Expected all 17 operating aggregate fields")
        for key, value in totals.items():
            if key.startswith("opening_"):
                calculated = first[key]
            elif key.startswith("closing_"):
                calculated = last[key]
            else:
                calculated = first[key] + last[key]
            require(calculated == amount(value) == archived[key], f"Saved operating aggregate differs: {key}")
        results.append(dict(snapshot=snapshot["snapshot_id"], periods=2, expenses=6, payments=4,
                            aggregates=17, net_operating_cash=str(first["net_operating_cash"] + last["net_operating_cash"]),
                            closing_free_cash=str(last["closing_free_cash_claim"])))
    return dict(status="passed", snapshots=results)


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
