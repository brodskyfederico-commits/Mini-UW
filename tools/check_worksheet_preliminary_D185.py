"""Verify the synthetic PRELIMINAR route through its normal run and audit commands."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory

from check_operating_replay_D20 import ROOT, require
from check_worksheet_formula_review_D173 import pdf_text
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_worksheet_v1 import PRELIMINARY_SCHEMA, build_results, encoded, verify_package
from worksheet_preliminary_D185 import POLICY, SUPPORT


DATES = ["2027-03-30", "2027-06-30", "2027-09-30", "2027-12-30", "2028-03-30"]
AS_OF = "2027-02-01"
SOURCE = dict(as_of=AS_OF, owner="Equipo sintético LOI", source_ref="SYNTHETIC-D185-presupuesto-indicativo")
FOCUS = "SYNTHETIC-LOI-A"
SECOND = "SYNTHETIC-LOI-B"
BLOCKED = "SYNTHETIC-LOI-C"


def fixture():
    def scenario(initial, extra, operations, sale):
        events = [("initial_capital", 0, initial), ("additional_capital", 1, extra),
                  ("operating_distribution", 3, operations), ("net_sale_distribution", 4, sale)]
        return dict(support={k: SOURCE | dict(summary=f"Estimación del caso para {k}") for k in SUPPORT},
                    events=[SOURCE | dict(category=category, date=DATES[index], amount=rational(Fraction(value)))
                            for category, index, value in events])

    common = dict(dates=DATES, as_of=AS_OF, financing="without_refinance")
    deals = [
        dict(id=FOCUS, scenarios=dict(Base=scenario(100, 20, 10, 140), Downside=scenario(100, 30, 5, 95))),
        dict(id=SECOND, scenarios=dict(Base=scenario(200, 0, 30, 340), Downside=scenario(200, 60, 10, 160))),
        dict(id=BLOCKED, scenarios=dict(Base=scenario(100, 0, 0, 170))),
    ]
    return common | dict(schema=PRELIMINARY_SCHEMA, policy=POLICY, focus=FOCUS,
                         deals=[d | common for d in deals])


def verify(output):
    case = fixture()
    fixture_path = ROOT / "templates/synthetic-preliminary-loi-D185.json"
    require(fixture_path.read_bytes() == encoded(case), "Synthetic LOI fixture drift")
    process = subprocess.run([sys.executable, str(ROOT / "tools/miniuw_worksheet_v1.py"), "run", str(fixture_path),
                              "--output", str(output)], check=True, capture_output=True)
    cli = json.loads(process.stdout)
    audited = verify_package(output)
    require(cli["state"] == "PRELIMINAR" and audited["decision"] == "PENDING", "CLI and replay lost the decision guard")
    baseline = json.loads((output / "results.json").read_bytes())
    require([row["deal_id"] for row in baseline["ranking"]] == [FOCUS, SECOND], "Wrong ranking or missing-case exclusion")
    report = pdf_text((output / "MiniUW_Resumen.pdf").read_bytes())
    require(all(x in report for x in ("PRELIMINAR", "Dictamen formal PENDING", "Cobro total 15,00", "Cobro total 10,00",
                                     "Sin recuperar 3,00", "2028-03-30", "Fuera del ranking")),
            "The one-page output lost the investor story")
    results = baseline["deals"][FOCUS]["scenarios"]
    require(amount(results["Base"]["cash"]["total_contributions"]) == 12
            and amount(results["Downside"]["cash"]["total_contributions"]) == 13
            and amount(results["Downside"]["cash"]["unrecovered_after_sale"]) == 3,
            "Wrong USD 10 basis")

    def probe(edit):
        modified = deepcopy(case)
        edit(modified)
        result, pdf = build_results(encoded(modified))
        require(result["decision"] == result["simulation_result"] == "PENDING" and not result["full_uw_eligible"]
                and not result["deployment_enabled"] and not result["real_decisions_enabled"]
                and "Dictamen formal PENDING" in pdf_text(pdf), "A preliminary variant could decide or advance")
        return result

    def reject_focus(edit, check):
        pending = probe(edit)
        focus = pending["deals"][FOCUS]
        require(focus["state"] == "PENDING" and all(row["deal_id"] != FOCUS for row in pending["ranking"])
                and check(focus), "An incomplete or incompatible deal entered the ranking")

    def downside(c):
        return c["deals"][0]["scenarios"]["Downside"]

    reject_focus(lambda c: downside(c)["support"]["calendar"].pop("owner"),
                 lambda v: v["scenarios"]["Downside"]["blockers"] == ["supuesto sin respaldo: calendar"])
    reject_focus(lambda c: downside(c)["events"][1].update(amount=None),
                 lambda v: v["scenarios"]["Downside"]["cash"] is None and v["scenarios"]["Base"]["cash"] is not None)
    reject_focus(lambda c: downside(c)["events"][2].update(as_of="2027-02-02"),
                 lambda v: v["scenarios"]["Downside"]["cash"] is None)
    reject_focus(lambda c: c["deals"][0].update(financing="with_refinance"), lambda v: "financiación" in v["reason"])
    reject_focus(lambda c: c["deals"][0].update(dates=DATES[:-1]), lambda v: "horizonte" in v["reason"])

    def tie(c):
        c["deals"][1]["scenarios"]["Downside"] = deepcopy(downside(c))
    tied = probe(tie)
    require([r["position"] for r in tied["ranking"]] == [1, 1], "A tie was assigned two priorities")

    def with_refi(c):
        c["financing"] = "with_refinance"
        for d in c["deals"]:
            d["financing"] = "with_refinance"
            for s in d["scenarios"].values():
                s["events"].extend([
                    SOURCE | dict(date=DATES[2], category="refinance_cash_in", amount=rational(Fraction())),
                    SOURCE | dict(date=DATES[2], category="net_refinance_distribution", amount=rational(Fraction(10))),
                ])
    refi = probe(with_refi)
    require(amount(refi["deals"][FOCUS]["scenarios"]["Base"]["cash"]["total_distributions"]) == 16
            and len(refi["ranking"]) == 2, "Refinance receipts were not included in normalized cash")
    def contradictory_refi(c):
        with_refi(c)
        downside(c)["events"][-2]["amount"] = rational(Fraction(5))

    reject_focus(contradictory_refi,
                 lambda v: v["scenarios"]["Downside"]["blockers"] == ["cobro y aporte de refi incompatibles"])
    return dict(status="passed", decision="PENDING", state="PRELIMINAR", probes=8,
                ranked_deals=len(baseline["ranking"]), excluded_deals=1, pdf_sha256=audited["pdf_sha256"])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d185-") as directory:
        print(json.dumps(verify(args.output or Path(directory) / "pilot"), sort_keys=True))
