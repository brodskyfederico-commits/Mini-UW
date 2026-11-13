"""Replay the D166 package and reconcile a documented synthetic LP/GP split."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from check_integrated_participation_D28 import allocate
from check_operating_replay_D20 import ROOT, require
from check_worksheet_construction_pdf_D157 import run_package
from check_worksheet_market_evidence_D166 import CASE, CURRENT, shuffled_pdf
from check_worksheet_refinance_D45 import render_page
from check_worksheet_return_metrics_D167 import KINDS, quarterly_cash, verify as verify_parent
from miniuw_foundation.cash_participation import ASSUMPTIONS, PROFILE
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.investor_returns import CATEGORIES
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, encoded
from worksheet_sale_rate_grid_D84 import money


TERMS = ROOT / "templates/synthetic-lp-gp-terms-D168.json"
SCHEMA = "miniuw.synthetic-d166-lp-gp-terms.v1"
SCENARIOS = ("Base", "Downside")
PARTICIPANTS = ("SYNTHETIC-LP", "SYNTHETIC-GP")


def amount(value):
    return _fraction(value, 1300)


def parent_ledger(view):
    cash = view["cash_per_usd_10"]
    if cash is None:
        return None
    events = cash["events"]
    dates = [entry["date"] for entry in view["irr"]["dated_net_flows"]]
    flows = quarterly_cash(cash, dates)
    require(flows is not None, "A complete quarterly D166 ledger is required")
    categories = sorted(set().union(*CATEGORIES.values()))
    totals = {key: Fraction() for key in categories}
    annual = {str(y): dict(gross_contributions=Fraction(), gross_distributions=Fraction(),
                           net_equity_cash=Fraction(), operating_distributions_only=Fraction())
              for y in range(int(dates[0][:4]), int(dates[-1][:4]) + 1)}
    for event in events:
        value = amount(event["amount"])
        kind = event["kind"]
        totals[event["category"]] += value
        row = annual[event["date"][:4]]
        row["gross_" + kind + "s"] += value
        row["net_equity_cash"] += value if kind == "distribution" else -value
        if event["category"] == "operating_distribution":
            row["operating_distributions_only"] += value
    story = dict(currency="USD", cash_horizon=dict(start=dates[0], end=dates[-1]), dated_events=events,
                 gross_contributions=cash["total_contributions"], gross_distributions=cash["total_distributions"],
                 net_cash_profit=cash["net_cash_profit"], cash_by_category={k: rational(v) for k, v in totals.items()},
                 annual_cash_receipts=[dict(calendar_cash_receipt_year=int(y), **{k: rational(v) for k, v in row.items()})
                                       for y, row in annual.items()])
    return dict(story=story, evidence=dict(grid=dict(dates=dates, step_months=3),
        parameters=dict(periods_per_year=4, max_periodic_rate_interval_width=rational(Fraction(1, 100_000_000)),
                        split_budget=128, operation_budget=50_000),
        dated_net_flows=[dict(date=d, net=rational(v)) for d, v in flows.items()]))


def pending(reason):
    return dict(state="PENDING", blockers=[reason], participants=None, reconciliation=None)


def split(terms, verified):
    if terms is None:
        return {name: pending("documented_allocation_terms_required") for name in SCENARIOS}
    keys = {"schema", "profile", "terms_id", "revision", "currency", "source_ref", "participant_inventory_complete",
            "assumptions", "source_result_sha256", "source_revision_sha256", "scenario_cash_sha256", "participants"}
    if (not isinstance(terms, dict) or terms.keys() != keys or terms["schema"] != SCHEMA or terms["profile"] != PROFILE
            or terms["terms_id"] != "SYNTHETIC-D168-LP-GP" or type(terms["revision"]) is not int or terms["revision"] != 1
            or terms["source_ref"] != "docs/workbook-lp-gp-D168.md#terminos-del-ensayo"
            or not isinstance(terms["scenario_cash_sha256"], dict) or terms["scenario_cash_sha256"].keys() != set(SCENARIOS)
            or not isinstance(terms["participants"], list)
            or any(not isinstance(row, dict) for row in terms["participants"])
            or tuple(row.get("participant_id") for row in terms["participants"]) != PARTICIPANTS):
        return {name: pending("allocation_terms_unconfirmed") for name in SCENARIOS}
    if any(terms[key] != verified[key] for key in ("source_result_sha256", "source_revision_sha256")):
        return {name: pending("allocation_terms_source_revision_mismatch") for name in SCENARIOS}

    results = {}
    for name in SCENARIOS:
        view = verified["scenarios"][name]
        if view["cash_per_usd_10"] is None:
            results[name] = pending("current_project_cash_unavailable")
            continue
        if terms["scenario_cash_sha256"][name] != view["cash_sha256"]:
            results[name] = pending("allocation_terms_scenario_cash_mismatch")
            continue
        parent = parent_ledger(view)
        try:
            results[name] = allocate(terms, parent, digest(canonical(parent)))
        except (ValueError, TypeError):
            results[name] = pending("allocation_terms_invalid")
            continue
        for row in results[name]["participants"] or []:
            initial = amount(row["cash_by_category"]["initial_capital"])
            require(initial == 10 * amount(row["share_fraction"]), "Participant initial equity did not reconcile")
            row["unrecovered_after_sale"] = rational(max(Fraction(), -amount(row["net_cash_profit"])))
            row["per_own_initial_usd_10"] = None
            if initial > 0:
                factor = 10 / initial
                row["per_own_initial_usd_10"] = {
                    key: rational(amount(row[key]) * factor)
                    for key in ("gross_contributions", "gross_distributions", "net_cash_profit", "unrecovered_after_sale")}
                row["per_own_initial_usd_10"]["dated_events"] = [
                    dict(event, amount=rational(amount(event["amount"]) * factor)) for event in row["dated_events"]]
    return results


def usd(value):
    return money(rational(value))


def render(results):
    lines = [("Reparto hipotético LP 80 % / GP 20 % de cada movimiento | Retorno personal real PENDING", True),
             ("Importes en USD por 10 iniciales del proyecto | Refi, operación y venta se muestran por fecha", False)]
    for name, result in results.items():
        if result["participants"] is None:
            lines.append((f"{name} | PENDING · faltan términos o flujos compatibles", True))
            continue
        lp, gp = result["participants"]
        lines.append((f"{name} | LP y GP se muestran por separado", True))
        for first, second in zip(lp["dated_events"], gp["dated_events"], strict=True):
            if amount(first["amount"]) or amount(second["amount"]):
                lines.append((f"{first['date']} | {KINDS[first['category']]} | LP {money(first['amount'])}"
                              f" | GP {money(second['amount'])}", False))
        lines.append((f"Cobro total LP {money(lp['gross_distributions'])} | GP {money(gp['gross_distributions'])}"
                      f" | Sin recuperar LP {money(lp['unrecovered_after_sale'])} | GP {money(gp['unrecovered_after_sale'])}", True))
        own = lp["per_own_initial_usd_10"]
        lines.append((f"Por USD 10 propios (cada rol) | Aporte extra {usd(amount(own['gross_contributions']) - 10)}"
                      f" | Cobro {money(own['gross_distributions'])} | Sin recuperar {money(own['unrecovered_after_sale'])}", False))
    lines.append(("Las cifras redondeadas pueden diferir de la suma. Decisión real PENDING.", False))
    return render_page("D168 | Corrida D166", lines, 11,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Reparto LP/GP y movimientos fechados | Ejemplo sintético")


def verify_controls(terms, verified, results):
    for name in SCENARIOS:
        result = results[name]
        require(result["state"] == "computed_synthetic_cash_allocation"
                and result["reconciliation"]["every_project_event_reconciled"], "Synthetic LP/GP split did not reconcile")
        lp, gp = result["participants"]
        require([amount(row["cash_by_category"]["initial_capital"]) for row in (lp, gp)] == [8, 2],
                "Fixture must allocate the initial USD 10 exactly")
        require(all(row["verified_personal_investor_return_state"] == "PENDING" for row in (lp, gp)),
                "Hypothetical terms acquired real authority")
        cash = verified["scenarios"][name]["cash_per_usd_10"]
        for row in (lp, gp):
            normalized = row["per_own_initial_usd_10"]
            require([event["amount"] for event in normalized["dated_events"]] == [event["amount"] for event in cash["events"]]
                    and normalized["gross_distributions"] == cash["total_distributions"]
                    and normalized["unrecovered_after_sale"] == cash["unrecovered_after_sale"],
                    "Participant normalization did not retain the original proportional cash flows")
            annual = row["annual_IRR_roots"][0]["annual_rate_interval"]
            require(annual == verified["scenarios"][name]["irr"]["annual_enclosure"],
                    "Constant share changed the annual TIR interval")
    missing_share = deepcopy(terms)
    missing_share["participants"][0]["share_fraction"] = None
    short = deepcopy(terms)
    short["participants"][0]["share_fraction"] = rational(Fraction(3, 4))
    expired = deepcopy(terms)
    expired["source_revision_sha256"] = "0" * 64
    controls = ((None, "documented_allocation_terms_required"), (missing_share, "SYNTHETIC-LP:share_missing"),
                (short, "supplied_shares_must_sum_exactly_one"), (expired, "allocation_terms_source_revision_mismatch"))
    for variant, reason in controls:
        require(all(row["state"] == "PENDING" and reason in row["blockers"] and row["participants"] is None
                    for row in split(variant, verified).values()), "Incomplete or stale terms produced a split")
    wrong_cash = deepcopy(terms)
    wrong_cash["scenario_cash_sha256"]["Downside"] = "0" * 64
    isolated = split(wrong_cash, verified)
    require(isolated["Base"] == results["Base"] and isolated["Downside"]["state"] == "PENDING"
            and isolated["Downside"]["participants"] is None
            and isolated["Downside"]["blockers"] == ["allocation_terms_scenario_cash_mismatch"],
            "A misbound scenario affected the wrong split")
    return len(controls) + 1


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Optional saved D166 package")
    parser.add_argument("--output", type=Path, help="Directory for the PDF, terms and audit evidence")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d168-") as folder:
        temp = Path(folder)
        package = args.package
        if package is None:
            evidence = temp / EVIDENCE_FILE
            evidence.write_bytes(shuffled_pdf())
            package = temp / "D166"
            run_package(CASE, CURRENT, evidence, package)
        verified, _ = verify_parent(package, CURRENT.read_bytes())
        terms_raw = TERMS.read_bytes()
        terms = json.loads(terms_raw)
        require(terms["assumptions"] == ASSUMPTIONS, "The fixture must explicitly declare the T104 assumptions")
        results = split(terms, verified)
        pending_cases = verify_controls(terms, verified, results)
        pdf = render(results)
        output = args.output or temp / "D168"
        output.mkdir()
        (output / "terms.json").write_bytes(terms_raw)
        (output / "results.json").write_bytes(encoded(dict(status="passed", decision="PENDING",
            personal_investor_return=dict(state="PENDING", blockers=["verified_real_allocation_terms_required"]),
            terms_sha256=sha(terms_raw), source_result_sha256=verified["source_result_sha256"],
            source_audit=verified["source_audit"], scenarios=results, pdf_sha256=sha(pdf))))
        (output / "MiniUW_Resumen.pdf").write_bytes(pdf)
        print(json.dumps(dict(status="passed", decision="PENDING", page_count=1, pdf_sha256=sha(pdf),
                              pending_cases=pending_cases, terms_sha256=sha(terms_raw)), sort_keys=True))


if __name__ == "__main__":
    main()
