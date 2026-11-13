"""Exercise the original Inputs layout and USD 10 LOI cash through run and audit."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys

from check_operating_replay_D20 import ROOT, require
from check_worksheet_formula_review_D173 import pdf_text
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import _fraction as amount
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import PRELIMINARY_WORKBOOK_SCHEMA, build_results, encoded, verify_package
from worksheet_preliminary_D185 import POLICY, SCENARIOS, SUPPORT


DEAL = "SYNTHETIC-LOI-D186"
AS_OF = "2027-02-01"
DATES = ["2027-03-30", "2027-06-30", "2027-09-30", "2027-12-30", "2028-03-30",
         "2028-06-30", "2028-09-30", "2028-12-30"]
TEMPLATE = ROOT / "templates/synthetic-preliminary-workbook-D186.json"
BOOKS = {name: ROOT / f"templates/synthetic-preliminary-{name.lower()}-D186.xlsx" for name in SCENARIOS}


def workbook(name, changes=None):
    values = dict(C8=1000, C9=1200, C10=0, C11=0, C13=0, C14="0.1", C15=0,
                  C32=100000, C33="0.05", C35=90000, C37=5000, C38=5000, C39="0.1", C40="0.1",
                  C42="0.5", C46=6, C47=3, C51=0, C57=1500, C58="0.05", C59=500, C60=250,
                  C62=500, C67="0.1", C68="0.05", C75=0, C76=0)
    if name == "Downside":
        values.update(C8=850, C9=1020, C14="0.2", C35=112000, C67="0.16", C68="0.06")
    descriptors = {k: {"value": str(v)} for k, v in values.items()}
    return native_workbook(descriptors | {k: {"text": v} for k, v in
                           dict(B3=DEAL, E3=AS_OF, C7="PER UNIT", C34="TOTAL").items()} | (changes or {}))


def fixture():
    books = {name: workbook(name) for name in SCENARIOS}
    bindings = {}
    for name, raw in books.items():
        support = {key: dict(summary="Supuesto de ensayo para " + key, as_of=AS_OF, owner="Equipo sintético LOI",
                             source_ref=f"SYNTHETIC-D186-{name}-{key}") for key in SUPPORT}
        support["program"].update(units=[1, 3, 0, 0])
        support["acquisition_and_costs"].update(parking_spaces=1, scope="residential_budget_complete")
        support["rent_and_expenses"].update(scope="stabilized_residential_expenses_complete")
        support["calendar"].update(lease_up_carry_usd_per_quarter=2000)
        support["exit"].update(reserve_at_sale="release_to_equity")
        bindings[name] = dict(support=support, workbook_sha256=sha(raw))
    return dict(schema=PRELIMINARY_WORKBOOK_SCHEMA, policy=POLICY, as_of=AS_OF, dates=DATES,
                financing="without_refinance", focus=DEAL, scenarios=bindings), books


def verify(output):
    case, books = fixture()
    require(TEMPLATE.read_bytes() == encoded(case) and all(BOOKS[n].read_bytes() == books[n] for n in SCENARIOS),
            "Synthetic workbook fixture drift")
    run = subprocess.run([sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "run", str(TEMPLATE),
                          "--workbook", str(BOOKS["Base"]), "--downside-workbook", str(BOOKS["Downside"]),
                          "--output", str(output)], check=True, capture_output=True)
    status = json.loads(run.stdout)
    require(status["state"] == "PRELIMINAR" and verify_package(output)["pdf_sha256"] == status["pdf_sha256"],
            "CLI and audit did not reproduce the workbook package")
    baseline = json.loads((output / "results.json").read_bytes())
    rows = baseline["deals"][DEAL]["scenarios"]
    require(len(baseline["ranking"]) == 1, "Complete deal excluded from ranking")
    # Independent USD cash amounts before scaling by 10 / 105000.
    expected = {"Base": (121000, "37196", "353362"), "Downside": (147620, "25659.2", "150747.8")}
    for name, (construction, annual_noi, sale) in expected.items():
        row = rows[name]
        cash, projection = row["cash"], row["projection"]
        require(amount(cash["basis_amount"]) == 105000 and amount(projection["construction"]) == construction
                and amount(projection["sale_noi"]) == Fraction(annual_noi), "Workbook projection did not reconcile")
        require(amount(projection["sale_net_before_reserve_release"]) == Fraction(sale),
                "Sale projection did not reconcile")
        factor = Fraction(10, 105000)
        expected_first_soft = {"Base": 5500, "Downside": 6710}[name]
        expected_dated = [
            (DATES[0], "initial_capital", Fraction(105000)),
            (DATES[1], "additional_capital", Fraction(expected_first_soft)),
            (DATES[2], "additional_capital", Fraction(construction - expected_first_soft)),
            (DATES[3], "additional_capital", Fraction(2000)),
            *((d, "operating_distribution", (Fraction(annual_noi) - 1000) / 4) for d in DATES[4:]),
            (DATES[-1], "net_sale_distribution", Fraction(sale) + 1000),
        ]
        require([(e["date"], e["category"], amount(e["amount"])) for e in cash["events"]] ==
                [(d, k, value * factor) for d, k, value in expected_dated],
                "Dated construction, operation or reserve release did not reconcile")
        require(amount(cash["total_contributions"]) == (105000 + construction + 2000) * factor
                and amount(cash["total_distributions"]) == (Fraction(annual_noi) + Fraction(sale)) * factor
                and amount(cash["unrecovered_after_sale"]) == max(0, (107000 + construction - Fraction(annual_noi) - Fraction(sale)) * factor),
                "Workbook flows did not reconcile on the initial USD 10 basis")

    def variant(name, changes, blocker, *, unbound=False):
        variant_case = deepcopy(case)
        modified = workbook(name, changes)
        inputs = books | {name: modified}
        if not unbound:
            variant_case["scenarios"][name]["workbook_sha256"] = sha(modified)
        result, pdf = build_results(encoded(variant_case), workbook_raw=inputs["Base"], downside_workbook_raw=inputs["Downside"])
        pair = result["deals"][DEAL]["scenarios"]
        report = pdf_text(pdf)
        other = "Base" if name == "Downside" else "Downside"
        require(result["state"] == result["decision"] == "PENDING" and not result["ranking"] and not result["full_uw_eligible"]
                and pair[name]["cash"] is None and blocker in pair[name]["blockers"][0]
                and pair[other] == rows[other] and f"{name} | Caja PENDING" in report and "Fuera del ranking" in report,
                "An incomplete worksheet entered the ranking or removed independent cash")
    variant("Downside", {"C14": {}}, "C14")
    variant("Base", {"C51": "missing"}, "C51")
    variant("Downside", {"C57": {"formula": "1+1", "value": "2"}}, "C57")
    variant("Downside", {"C8": {"value": "900"}}, "huella", unbound=True)
    variant("Base", {"C51": {"value": "0.5"}}, "fuera del perfil")
    corrected = workbook("Downside", {"C14": {"value": "0"}})
    case["scenarios"]["Downside"]["workbook_sha256"] = sha(corrected)
    result, _ = build_results(encoded(case), workbook_raw=books["Base"], downside_workbook_raw=corrected)
    require(result["ranking"] and result["decision"] == "PENDING"
            and amount(result["ranking"][0]["downside_equity_multiple"]) > amount(baseline["ranking"][0]["downside_equity_multiple"])
            and result["deals"][DEAL]["scenarios"]["Base"] == rows["Base"], "A numeric zero was lost or changed Base")
    return dict(status="passed", decision="PENDING", probes=6, pdf_sha256=status["pdf_sha256"])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d186-") as directory:
        print(json.dumps(verify(args.output or Path(directory) / "pilot"), sort_keys=True))
