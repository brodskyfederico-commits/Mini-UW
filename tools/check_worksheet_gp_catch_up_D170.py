"""Verify D169 with a documented GP catch-up tier on D166 project cash."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, require
from check_worksheet_construction_pdf_D157 import run_package
from check_worksheet_lp_gp_D168 import SCENARIOS, amount, pending, usd
from check_worksheet_market_evidence_D166 import CASE, CURRENT, shuffled_pdf
from check_worksheet_preferred_lp_gp_D169 import (
    ORDER, ROLES, TERMS as PRIOR_TERMS, check_terms, split as split_d169, waterfall,
)
from check_worksheet_refinance_D45 import render_page
from check_worksheet_return_metrics_D167 import KINDS, verify as verify_parent
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, encoded
from worksheet_local_sources_D127 import number
from worksheet_sale_rate_grid_D84 import money


TERMS = ROOT / "templates/synthetic-gp-catch-up-terms-D170.json"
SCHEMA = "miniuw.synthetic-d169-gp-catch-up.v1"
TIERS = [*ORDER[:2], "pay_gp_catch_up", ORDER[-1]]


def split(terms, prior, verified):
    reason = None
    if terms is None:
        reason = "documented_catch_up_terms_required"
    elif (not isinstance(terms, dict)
          or terms.keys() != {"schema", "source_ref", "parent_terms_sha256", "gp_profit_share", "distribution_order"}
          or terms["schema"] != SCHEMA or terms["distribution_order"] != TIERS
          or terms["source_ref"] != "docs/workbook-gp-catch-up-D170.md#terminos-del-ensayo"):
        reason = "catch_up_terms_incomplete_or_unsupported"
    elif terms["parent_terms_sha256"] != sha(encoded(prior)):
        reason = "catch_up_parent_terms_mismatch"
    else:
        share = number(terms["gp_profit_share"])
        if share is None or not 0 <= share < 1:
            reason = "gp_catch_up_share_missing_or_invalid"
        else:
            reason = check_terms(prior, verified)
    if reason:
        return {name: pending(reason) for name in SCENARIOS}
    results = {}
    for name in SCENARIOS:
        view = verified["scenarios"][name]
        if view["state"] != "checked_synthetic" or view["cash_per_usd_10"] is None:
            results[name] = pending("current_project_cash_unavailable")
        elif prior["scenario_cash_sha256"][name] != view["cash_sha256"]:
            results[name] = pending("allocation_terms_scenario_cash_mismatch")
        else:
            results[name] = waterfall(view, prior, gp_catch_up_share=share)
    return results


def verify_controls(terms, prior, verified, results):
    baseline = split_d169(prior, verified)
    for name, result in results.items():
        require(result["state"] == "computed_synthetic_cash_allocation", "Expected a supported D170 allocation")
        records = result["reconciliation"]
        rows = records["events"]
        pref_paid = sum(amount(row["lp_preference_paid"]) for row in rows)
        catch_up = amount(records["gp_catch_up_paid"])
        require(all(sum(amount(value) for value in row["allocated"].values()) == amount(row["event"]["amount"])
                    for row in rows), "Cash did not reconcile by movement")
        for row, before in zip(rows, baseline[name]["reconciliation"]["events"], strict=True):
            require(row["event"] == before["event"] and row["returned_capital"] == before["returned_capital"]
                    and row["lp_preference_paid"] == before["lp_preference_paid"], "Catch-up displaced a senior tier")
        if name == "Base":
            require(catch_up == pref_paid / 4 > 0 and amount(records["gp_catch_up_due"]) == 0
                    and [r["event"]["category"] for r in rows if amount(r["gp_catch_up_paid"])] == ["net_sale_distribution"],
                    "Base failed to pay the full catch-up after the LP preference")
            cash = verified["scenarios"][name]["cash_per_usd_10"]
            require(all(result["participants"][role]["own_initial_usd_10"]["total_received"] == cash["total_distributions"]
                        for role in ROLES), "Full 20% catch-up did not restore proportional profit")
        else:
            require(catch_up == 0 and pref_paid == 0
                    and result["participants"] == baseline[name]["participants"],
                    "Catch-up was paid with unreturned capital")
    # Keep the LP preference fully paid and leave only half the GP target in cash.
    # Use a separately constructed control ledger so D166 itself stays exact.
    view = deepcopy(verified["scenarios"]["Base"])
    rows = results["Base"]["reconciliation"]["events"]
    sale = next(row for row in rows if row["event"]["category"] == "net_sale_distribution")
    target = amount(sale["lp_preference_paid"]) / 4
    available = sum(amount(value) for value in sale["returned_capital"].values()) + amount(sale["lp_preference_paid"]) + target / 2
    cash = view["cash_per_usd_10"]
    sale_event = next(e for e in cash["events"] if e["category"] == "net_sale_distribution")
    cash["total_distributions"] = rational(amount(cash["total_distributions"]) - amount(sale_event["amount"]) + available)
    sale_event["amount"] = rational(available)
    partial = waterfall(view, prior, gp_catch_up_share=Fraction(1, 5))
    evidence = partial["reconciliation"]
    require(amount(evidence["gp_catch_up_paid"]) == amount(evidence["gp_catch_up_due"]) == target / 2
            and all(amount(value) == 0 for value in evidence["events"][-1]["residual"].values()),
            "Partial catch-up paid a residual or lost the unpaid balance")

    for candidate, reason in ((None, "documented_catch_up_terms_required"),
                              (terms | {"gp_profit_share": None}, "gp_catch_up_share_missing_or_invalid"),
                              (terms | {"gp_profit_share": rational(1)}, "gp_catch_up_share_missing_or_invalid"),
                              (terms | {"parent_terms_sha256": "0" * 64}, "catch_up_parent_terms_mismatch"),
                              (terms | {"distribution_order": list(ORDER)}, "catch_up_terms_incomplete_or_unsupported")):
        require(all(row == pending(reason) for row in split(candidate, prior, verified).values()),
                "Incomplete catch-up terms yielded cash")
    require(split(terms | {"gp_profit_share": rational(0)}, prior, verified) == baseline,
            "An explicit zero catch-up did not reproduce D169")
    return 5


def render(results, *, formula_review=False):
    lines = [("Por USD 10 iniciales propios de cada rol | LP y GP se normalizan por separado", True),
             ("Capital primero, preferente LP 8 % simple, catch-up GP al 20 % de ganancias, remanente 80/20", False),
             ("Simulación con términos de prueba | Retorno personal real y decisión real PENDING", False)]
    for name, result in results.items():
        lines.append((name, True))
        if result["participants"] is None:
            lines.append(("PENDING | Revisar los términos y la caja de origen", False))
            continue
        initial = {role: amount(result["participants"][role]["project_usd_10"]["initial"]) for role in ROLES}
        for row in result["reconciliation"]["events"]:
            event = row["event"]
            if amount(event["amount"]):
                lp, gp = (usd(amount(row["allocated"][role]) * 10 / initial[role]) for role in ROLES)
                lines.append((f"{event['date']} | {KINDS[event['category']]} | LP USD {lp} | GP USD {gp}", False))
        lp, gp = (result["participants"][role]["own_initial_usd_10"] for role in ROLES)
        if formula_review:
            invested = {role: amount(row["initial"]) + amount(row["additional"])
                        for role, row in (("LP", lp), ("GP", gp))}
            lines.append(("Cobro total / múltiplo sobre todo lo aportado", False))
            lines.append((f"LP USD {money(lp['total_received'])} ({usd(amount(lp['total_received']) / invested['LP'])}x) | "
                          f"GP USD {money(gp['total_received'])} ({usd(amount(gp['total_received']) / invested['GP'])}x)", True))
            lines.append((f"Aporte total LP USD {usd(invested['LP'])} | GP USD {usd(invested['GP'])} | "
                          f"Sin recuperar LP {money(lp['cash_unrecovered'])} / GP {money(gp['cash_unrecovered'])}", False))
        else:
            lines.append((f"Cobro total LP {money(lp['total_received'])} | GP {money(gp['total_received'])}"
                      f" | Sin recuperar LP {money(lp['cash_unrecovered'])} | GP {money(gp['cash_unrecovered'])}", True))
        catch_up = amount(result["reconciliation"]["gp_catch_up_paid"])
        lines.append((f"Catch-up incluido en los cobros del GP: USD {usd(catch_up * 10 / initial['GP'])} por USD 10 propios", False))
    if formula_review:
        lines.append(("Ejemplo sintético de reparto. La evaluación del proyecto de origen dio FAIL simulado.", False))
    return render_page("D173 | Ejemplo D170" if formula_review else "D170 | D169 y D166", lines,
                       10 if formula_review else 11, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Reparto LP/GP con catch-up | Aportes y cobros por fecha")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Optional saved D166 package")
    parser.add_argument("--output", type=Path, help="Directory for the evidence and PDF")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d170-") as folder:
        temp = Path(folder)
        package = args.package
        if package is None:
            evidence = temp / EVIDENCE_FILE
            evidence.write_bytes(shuffled_pdf())
            package = temp / "D166"
            run_package(CASE, CURRENT, evidence, package)
        verified, _ = verify_parent(package, CURRENT.read_bytes())
        prior_raw, raw = PRIOR_TERMS.read_bytes(), TERMS.read_bytes()
        prior, terms = json.loads(prior_raw), json.loads(raw)
        require(prior_raw == encoded(prior), "Canonical D169 terms required")
        results = split(terms, prior, verified)
        blocked = verify_controls(terms, prior, verified, results)
        pdf = render(results)
        output = args.output or temp / "D170"
        output.mkdir()
        (output / "terms.json").write_bytes(raw)
        (output / "MiniUW_Resumen.pdf").write_bytes(pdf)
        proof = dict(status="passed", decision="PENDING", page_count=1, pending_cases=blocked,
                     pdf_sha256=sha(pdf), terms_sha256=sha(raw), source_result_sha256=verified["source_result_sha256"])
        (output / "results.json").write_bytes(encoded(proof | dict(scenarios=results, source_audit=verified["source_audit"],
            personal_investor_return=dict(state="PENDING", blockers=["verified_real_allocation_terms_required"]))))
        print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
