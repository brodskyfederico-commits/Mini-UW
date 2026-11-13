"""Audit staged construction cash and interest through PRELIMINAR."""
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
from check_worksheet_preliminary_finance_D187 import AS_OF, DATES, SCENARIOS, fixture as prior_fixture, workbook as prior_workbook
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import PRELIMINARY_STAGED_SCHEMA, build_results, encoded, verify_package
from worksheet_preliminary_finance_D187 import STAGED_CONVENTION


DEAL = "SYNTHETIC-LOI-D188"
CASE = ROOT / "templates/synthetic-preliminary-staged-D188.json"
BOOKS = {name: ROOT / f"templates/synthetic-preliminary-staged-{name.lower()}-D188.xlsx" for name in SCENARIOS}


def workbook(name, edits=None):
    return prior_workbook(name, {"B3": {"text": DEAL}} | (edits or {}))


def fixture():
    case, _ = prior_fixture()
    case.update(schema=PRELIMINARY_STAGED_SCHEMA, focus=DEAL)
    books = {name: workbook(name) for name in SCENARIOS}
    for name, binding in case["scenarios"].items():
        binding["workbook_sha256"] = sha(books[name])
        term = binding["support"]["financing"]
        term.update(convention=STAGED_CONVENTION, source_ref=f"SYNTHETIC-D188-{name}-financing")
        draw_fractions = (F(1, 2), F(7, 10)) if name == "Base" else (F(30, 61), F(40, 61))
        term["construction_stages"] = [
            dict(date=DATES[i], eligible_hard_share=rational(F(1, 2)), requested_draw_fraction_of_eligible=rational(fraction),
                 available_draw_usd=rational(45000), source_ref=f"SYNTHETIC-D188-{name}-quote-stage-{i}",
                 as_of=AS_OF, owner="Equipo sintético LOI")
            for i, fraction in enumerate(draw_fractions, 1)
        ]
    return case, books


def verify(output):
    case, books = fixture()
    require(CASE.read_bytes() == encoded(case) and all(BOOKS[n].read_bytes() == books[n] for n in SCENARIOS),
            "Staged workbook fixture drift")
    run = subprocess.run([sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "run", str(CASE),
                          "--workbook", str(BOOKS["Base"]), "--downside-workbook", str(BOOKS["Downside"]),
                          "--output", str(output)], check=True, capture_output=True)
    status = json.loads(run.stdout)
    require(status["state"] == "PRELIMINAR" and verify_package(output)["pdf_sha256"] == status["pdf_sha256"],
            "CLI and audit did not reproduce the financing package")
    baseline = json.loads((output / "results.json").read_bytes())
    rows = baseline["deals"][DEAL]["scenarios"]
    require(len(baseline["ranking"]) == 1 and baseline["decision"] == "PENDING" and not baseline["full_uw_eligible"],
            "Staged financing bypassed the decision guard or lost eligibility")
    for name, draws, costs, fee, interest, refi, quarterly_cash, sale in (
        ("Base", (25000, 35000), (60500, 60500), 600, (500, 1200), 27800, F(6799), F(273562)),
        ("Downside", (30000, 40000), (73810, 73810), 700, (600, 1400), -1800, F("4414.8"), F("88947.8")),
    ):
        loan = rows[name]["financing"]
        schedule = loan["construction_draw_schedule"]
        expected = [
            (DATES[0], "initial_capital", 105000),
            (DATES[1], "additional_capital", costs[0] - draws[0] + fee),
            (DATES[2], "additional_capital", costs[1] - draws[1] + interest[0]),
            (DATES[3], "additional_capital", 2000 + interest[1]),
            (DATES[3], "refinance_cash_in", max(0, -refi)),
            (DATES[3], "net_refinance_distribution", max(0, refi)),
            *((d, "operating_distribution", quarterly_cash) for d in DATES[4:]),
            (DATES[-1], "net_sale_distribution", sale),
        ]
        cash = rows[name]["cash"]
        require([(e["date"], e["category"], amount(e["amount"])) for e in cash["events"]] ==
                [(date, kind, F(value) / 10500) for date, kind, value in expected], "Dated staged cash differs")
        require([amount(row["opening_principal"]) for row in schedule] == [0, draws[0]]
                and [amount(row["draw_at_start"]) for row in schedule] == list(draws)
                and [amount(row["interest_due_at_end"]) for row in schedule] == list(interest)
                and amount(loan["construction_payoff"]) == sum(draws)
                and amount(loan["construction_interest"]) == sum(interest)
                and amount(schedule[-1]["closing_principal"]) == 0
                and sum(amount(s["cost"]) for s in loan["construction_stage_inputs"]) == sum(costs),
                "Draws, interest or payoff did not reconcile")

    def probe(edit=None, cells=None, *, state="PENDING", expected=None):
        updated = deepcopy(case)
        variant = books.copy()
        if cells:
            variant["Downside"] = workbook("Downside", cells)
            updated["scenarios"]["Downside"]["workbook_sha256"] = sha(variant["Downside"])
        term = updated["scenarios"]["Downside"]["support"]["financing"]
        if edit:
            edit(term)
        result, pdf = build_results(encoded(updated), workbook_raw=variant["Base"], downside_workbook_raw=variant["Downside"])
        pair = result["deals"][DEAL]["scenarios"]
        content = pdf_text(pdf)
        require(result["decision"] == "PENDING" and result["state"] == state and not result["full_uw_eligible"]
                and not result["real_decisions_enabled"] and not result["deployment_enabled"]
                and pair["Base"] == rows["Base"] and "Dictamen formal PENDING" in content,
                "A stage change broke the decision guard or changed Base")
        if state == "PENDING":
            require(not result["ranking"] and pair["Downside"]["cash"] is None
                    and expected in pair["Downside"]["blockers"][0] and "Fuera del ranking" in content,
                    "A blocked Downside entered the ranking")
        return pair["Downside"]

    def stage(term, index=0):
        return term["construction_stages"][index]

    probe(cells={"C52": {}}, expected="C52")
    probe(cells={"C72": {}}, expected="C72")
    probe(lambda t: stage(t).pop("available_draw_usd"), expected="faltan")
    probe(lambda t: stage(t).update(date=DATES[2]), expected="fecha")
    probe(lambda t: stage(t).update(requested_draw_fraction_of_eligible=rational(F(11, 10))), expected="elegible")
    probe(lambda t: stage(t).update(eligible_hard_share=rational(F(3, 5))), expected="100%")
    blocked = probe(lambda t: stage(t).update(available_draw_usd=rational(29999)), expected="disponibilidad")
    require(any("available_new_draw" in b for b in blocked["financing"]["construction_draw_blockers"]), "Wrong stage limit")
    blocked = probe(lambda t: t.update(construction_commitment_usd=rational(69999)), expected="compromiso")
    require(any("nonrevolving_commitment" in b for b in blocked["financing"]["construction_draw_blockers"]), "Wrong credit limit")
    probe(lambda t: t.update(requested_refinance_usd=rational(82000)), expected="capacidad")
    lower = probe(lambda t: stage(t).update(requested_draw_fraction_of_eligible=rational(F())), state="PRELIMINAR")
    require(amount(lower["financing"]["construction_interest"]) == 800 and
            amount(lower["financing"]["construction_payoff"]) == 40000, "Explicit zero drew or accrued interest")
    shifted = probe(lambda t: (stage(t).update(requested_draw_fraction_of_eligible=rational(F(20, 61))),
                              stage(t, 1).update(requested_draw_fraction_of_eligible=rational(F(50, 61)), available_draw_usd=rational(50000))),
                    state="PRELIMINAR")
    require(amount(shifted["financing"]["construction_interest"]) == 1800
            and amount(shifted["financing"]["construction_payoff"]) == 70000
            and shifted["financing"]["refi_net"] == rows["Downside"]["financing"]["refi_net"],
            "Moving draw timing changed payoff or failed to change interest")
    changed_cost = probe(cells={"C35": {"value": "100000"}}, state="PRELIMINAR")
    changed = changed_cost["financing"]
    require(amount(changed["construction_draw"]) == F(3_850_000, 61)
            and amount(changed["construction_interest"]) == F(110_000, 61)
            and amount(changed["refi_net"]) == F(310200, 61), "C35 did not recalculate staged draws and payoff")
    return dict(status="passed", decision="PENDING", probes=12, exact_dated_cash=True, pdf_sha256=status["pdf_sha256"])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d188-") as directory:
        print(json.dumps(verify(args.output or Path(directory) / "pilot"), sort_keys=True))
