"""Reproduce financed PRELIMINAR cash from the original Inputs layout."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys

from check_operating_replay_D20 import ROOT, require
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_preliminary_workbook_D186 import AS_OF, DATES, SCENARIOS, fixture as prior_fixture, workbook as prior_workbook
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import PRELIMINARY_FINANCED_SCHEMA, build_results, encoded, verify_package
from worksheet_preliminary_finance_D187 import CONVENTION


DEAL = "SYNTHETIC-LOI-D187"
CASE = ROOT / "templates/synthetic-preliminary-financed-D187.json"
BOOKS = {name: ROOT / f"templates/synthetic-preliminary-financed-{name.lower()}-D187.xlsx" for name in SCENARIOS}


def workbook(name, edits=None):
    values = dict(C51="0.6", C52="0.08", C53="0.01", C66="0.16", C69="0", C70="10",
                  C71="0.65", C72="1.25", C73="0.02", C74="100")
    return prior_workbook(name, {key: {"value": val} for key, val in values.items()}
                          | {"B3": {"text": DEAL}} | (edits or {}))


def fixture():
    case, _ = prior_fixture()
    case.update(schema=PRELIMINARY_FINANCED_SCHEMA, focus=DEAL, financing="with_refinance")
    books = {name: workbook(name) for name in SCENARIOS}
    for name, binding in case["scenarios"].items():
        binding["workbook_sha256"] = sha(books[name])
        binding["support"]["financing"].update(
            convention=CONVENTION, source_ref=f"SYNTHETIC-D187-{name}-financing",
            requested_refinance_usd=rational(90000 if name == "Base" else 70000),
            construction_commitment_usd=rational(70000), construction_maturity_date=DATES[3],
            bank_vacancy_addition_H08=rational(F("0.03")), permanent_maturity_quarters_H02=8,
            debt_yield_applicability="applicable", minimum_debt_yield=rational(F("0.12" if name == "Base" else "0.30")),
            maximum_refi_equity_usd=rational(2000),
            permanent_reserve_sale_release_fraction=rational(F("0.5")))
    return case, books


def verify(output):
    case, books = fixture()
    require(CASE.read_bytes() == encoded(case) and all(BOOKS[n].read_bytes() == books[n] for n in SCENARIOS),
            "Financed workbook fixture drift")
    run = subprocess.run([sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "run", str(CASE),
                          "--workbook", str(BOOKS["Base"]), "--downside-workbook", str(BOOKS["Downside"]),
                          "--output", str(output)], check=True, capture_output=True)
    status = json.loads(run.stdout)
    require(status["state"] == "PRELIMINAR" and verify_package(output)["pdf_sha256"] == status["pdf_sha256"],
            "CLI and audit did not reproduce the financing package")
    baseline = json.loads((output / "results.json").read_bytes())
    rows = baseline["deals"][DEAL]["scenarios"]
    require(len(baseline["ranking"]) == 1 and baseline["decision"] == "PENDING" and not baseline["full_uw_eligible"],
            "Financing bypassed the PENDING decision or lost eligibility")
    # Independently calculated project-dollar ledgers. The permanent fixture is zero-rate.
    for name, draw, origination, interest, early, construction, refi, payment, noi, sale, lender_noi, limit in (
        ("Base", 60000, 600, 1200, 5500, 121000, 27800, 2250, F(37196), F(353362), F("35622.8"), "LTV"),
        ("Downside", 70000, 700, 1400, 6710, 147620, -1800, 1750, F("25659.2"), F("150747.8"), F("24321.98"), "debt_yield"),
    ):
        loan = rows[name]["financing"]
        principal = 90000 if name == "Base" else 70000
        balance = principal - 4 * payment
        expected = [
            (DATES[0], "initial_capital", 105000),
            (DATES[1], "additional_capital", early),
            (DATES[2], "additional_capital", construction - early - draw + origination),
            (DATES[3], "additional_capital", 2000 + interest),
            (DATES[3], "refinance_cash_in", max(0, -refi)),
            (DATES[3], "net_refinance_distribution", max(0, refi)),
            *((d, "operating_distribution", (noi - 1000) / 4 - payment) for d in DATES[4:]),
            (DATES[-1], "net_sale_distribution", sale + 1000 + 200 - balance),
        ]
        cash = rows[name]["cash"]
        require([(e["date"], e["category"], amount(e["amount"])) for e in cash["events"]] ==
                [(date, kind, F(value) / 10500) for date, kind, value in expected], "Dated financed cash differs")
        require(amount(loan["construction_payoff"]) == draw and amount(loan["construction_interest"]) == interest
                and amount(loan["bank_noi"]) == lender_noi and loan["binding_limits"] == [limit]
                and amount(loan["sale_payment"]["closing_balance"]) == balance
                and amount(loan["permanent_reserve_transferred"]) == 200, "Financing evidence differs")

    def probe(edit=None, cells=None, *, state="PENDING", expected=None):
        updated = deepcopy(case)
        variant = books.copy()
        if cells:
            variant["Downside"] = workbook("Downside", cells)
            updated["scenarios"]["Downside"]["workbook_sha256"] = sha(variant["Downside"])
        if edit:
            edit(updated["scenarios"]["Downside"]["support"]["financing"])
        result, pdf = build_results(encoded(updated), workbook_raw=variant["Base"], downside_workbook_raw=variant["Downside"])
        pair = result["deals"][DEAL]["scenarios"]
        content = pdf_text(pdf)
        require(result["decision"] == "PENDING" and result["state"] == state and not result["full_uw_eligible"]
                and not result["real_decisions_enabled"] and not result["deployment_enabled"]
                and pair["Base"] == rows["Base"] and "Dictamen formal PENDING" in content,
                "A financing change broke the decision guard or changed Base")
        if state == "PENDING":
            require(not result["ranking"] and pair["Downside"]["cash"] is None
                    and expected in pair["Downside"]["blockers"][0] and "Fuera del ranking" in content,
                    "A blocked Downside entered the ranking")
        return pair["Downside"]

    probe(cells={"C72": {}}, expected="C72")
    probe(cells={"C52": {"formula": "0.08", "value": "0.08"}}, expected="C52")
    probe(lambda term: term.pop("bank_vacancy_addition_H08"), expected="falta")
    probe(lambda term: term.update(construction_maturity_date=DATES[2]), expected="vencimiento")
    probe(lambda term: term.update(maximum_refi_equity_usd=rational(1799)), expected="fondeo")
    over = probe(lambda term: term.update(requested_refinance_usd=rational(82000)), expected="capacidad")
    require(amount(over["financing"]["requested"]) == 82000 and
            amount(over["financing"]["capacity"]) == F("24321.98") / F("0.30"), "Reported debt-yield capacity differs")
    dscr = probe(cells={"C72": {"value": "4"}}, expected="capacidad")
    require(dscr["financing"]["binding_limits"] == ["DSCR"], "DSCR did not bind")
    ltv = probe(cells={"C71": {"value": "0.4"}}, expected="capacidad")
    require(ltv["financing"]["binding_limits"] == ["LTV"], "LTV did not bind")
    at_limit = probe(lambda term: term.update(minimum_debt_yield=rational(F("24321.98") / 70000)),
                     state="PRELIMINAR")
    require(amount(at_limit["financing"]["capacity"]) == 70000, "Equality at the limit was excluded")
    positive = probe(cells={"C69": {"value": "0.06"}}, state="PRELIMINAR")
    require(amount(positive["financing"]["regular_payment"], 1300) > 1750, "Positive-rate amortization was lost")
    probe(lambda term: term.update(permanent_maturity_quarters_H02=3), expected="vencimiento")
    no_yield = probe(lambda term: term.update(debt_yield_applicability="not_applicable", minimum_debt_yield=None),
                     state="PRELIMINAR")
    require("debt_yield" not in no_yield["financing"]["limits"], "An inapplicable bank limit was evaluated")
    probe(cells={"C67": {"value": "1"}}, expected="liquidar")
    return dict(status="passed", decision="PENDING", probes=13, exact_dated_cash=True, pdf_sha256=status["pdf_sha256"])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d187-") as directory:
        print(json.dumps(verify(args.output or Path(directory) / "pilot"), sort_keys=True))
