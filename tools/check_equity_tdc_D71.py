"""Reconcile applied debt and equity to the synthetic all-in budget."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import sys

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_yoc_spread_D70 import FIXTURE as TDC_ARCHIVE, verify as verify_tdc
from miniuw_linked_cotejo_D54 import publish
from miniuw_worksheet_v1 import encoded
from miniuw_foundation.debt_service import _date, _fraction, rational
from miniuw_foundation.expense_cash_detail import _exact, _json
from miniuw_foundation.scheduled_expense_case import sha


FIXTURE = "templates/synthetic-equity-tdc-D71.json"
TYPES = ("debt_drawn", "equity_paid")


def declared(value):
    return isinstance(value, str) and value.startswith("SYNTHETIC-D71-")


def reconcile(funding, budget, cutoff):
    _exact(funding, {"context", "currency", "cutoff", "funding_inventory_complete", "scope_ref",
                     "debt_commitment", "sources"})
    blockers = []
    if (funding["context"] != budget["context"] or funding["currency"] != "USD"
            or funding["cutoff"] != cutoff or funding["funding_inventory_complete"] is not True
            or not declared(funding["scope_ref"])):
        blockers.append("funding_scope_incomplete_or_incompatible")
    tdc = _fraction(budget["tdc"])
    if tdc is None or tdc <= 0:
        blockers.append("positive_complete_tdc_required")
    commitment = _fraction(funding["debt_commitment"])
    if commitment is None or commitment < 0:
        blockers.append("explicit_debt_commitment_required")

    sources = funding["sources"]
    require(isinstance(sources, list) and len(sources) <= 16, "Bounded applied funding inventory required")
    seen = set()
    by_kind = {kind: Fraction(0) for kind in TYPES}
    kinds = set()
    for row in sources:
        _exact(row, {"id", "kind", "amount", "date", "source_ref"})
        require(declared(row["id"]) and row["id"] not in seen and row["kind"] in TYPES,
                "Each funding item requires a distinct identity and explicit funding kind")
        seen.add(row["id"])
        kinds.add(row["kind"])
        value = _fraction(row["amount"])
        if (value is None or value < 0 or _date(row["date"]) > _date(cutoff)
                or not declared(row["source_ref"])):
            blockers.append(f"unavailable_or_out_of_scope:{row['id']}")
            continue
        by_kind[row["kind"]] += value
    if kinds != set(TYPES):
        blockers.append("explicit_debt_and_equity_amounts_required")
    if not blockers:
        if by_kind["debt_drawn"] > commitment:
            blockers.append("applied_debt_exceeds_commitment")
        if sum(by_kind.values()) != tdc:
            blockers.append("applied_funding_does_not_reconcile_to_tdc")
    value = None if blockers else by_kind["equity_paid"] / tdc
    return dict(state="PENDING" if blockers else "computed_synthetic", blockers=blockers,
                equity_to_tdc=None if value is None else rational(value),
                applied_funding=None if blockers else {k: rational(v) for k, v in by_kind.items()},
                tdc=budget["tdc"], debt_commitment=funding["debt_commitment"], cutoff=cutoff,
                tdc_source_sha256=budget["tdc_source_sha256"], funding_source_sha256=sha(encoded(funding)),
                decision="PENDING")


def verify():
    raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = _json(raw)
    _exact(fixture, {"schema", "tdc_archive_sha256", "funding_cutoff", "scenarios"})
    require(fixture["schema"] == "miniuw.synthetic-equity-tdc-rehearsal.v1"
            and fixture["tdc_archive_sha256"] == sha(local_file(ROOT, TDC_ARCHIVE).read_bytes()),
            "Equity/TDC fixture or its budget archive differs")
    cutoff = str(_date(fixture["funding_cutoff"]))
    tdc_report = verify_tdc()
    require(_date(cutoff) < _date(tdc_report["stabilized_period"].split("/")[0]),
            "Funding cutoff must precede the stabilized period in this synthetic case")
    budgets = tdc_report["sources"]
    _exact(fixture["scenarios"], budgets)
    cases = {key: reconcile(funding, budgets[key], cutoff) for key, funding in fixture["scenarios"].items()}
    for key, expected in {"Base": Fraction(2, 5), "Downside": Fraction(5, 11)}.items():
        require(cases[key]["state"] == "computed_synthetic"
                and amount(cases[key]["equity_to_tdc"]) == expected, "Equity/TDC differs from the independent ratio")
    base = fixture["scenarios"]["Base"]
    over = deepcopy(base)
    over["sources"][0]["amount"] = over["debt_commitment"]
    late = deepcopy(base)
    late["sources"][1]["date"] = "2027-01-01"
    missing = deepcopy(base)
    missing["sources"].pop()
    rejected = {"commitment_substituted": reconcile(over, budgets["Base"], cutoff),
                "late_equity": reconcile(late, budgets["Base"], cutoff),
                "missing_equity": reconcile(missing, budgets["Base"], cutoff)}
    require(all(row["state"] == "PENDING" and row["equity_to_tdc"] is row["applied_funding"] is None
                for row in rejected.values())
            and rejected["commitment_substituted"]["blockers"] == ["applied_funding_does_not_reconcile_to_tdc"],
            "Unreconciled funding leaked an equity ratio")
    extra_commitment = deepcopy(base)
    extra_commitment["debt_commitment"] = rational(Fraction(900))
    require(reconcile(extra_commitment, budgets["Base"], cutoff)["equity_to_tdc"] == cases["Base"]["equity_to_tdc"],
            "Undrawn commitment changed equity required")
    return dict(status="passed", decision="PENDING", fixture_sha256=sha(raw), cases=cases,
                rejected=rejected, unused_commitment_excluded=True, real_decisions_enabled=False,
                deployment_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New path for full synthetic evidence.")
    try:
        args = parser.parse_args()
        report = verify()
        if args.output is not None:
            publish(args.output, report)
        print(json.dumps(dict(status=report["status"], decision=report["decision"],
                              scenario_values={key: row["equity_to_tdc"] for key, row in report["cases"].items()},
                              blocked_cases=list(report["rejected"]),
                              unused_commitment_excluded=report["unused_commitment_excluded"]), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
