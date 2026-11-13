"""Reproduce D166 and verify an exact synthetic LP/GP waterfall."""
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
from check_worksheet_refinance_D45 import render_page
from check_worksheet_return_metrics_D167 import KINDS, verify as verify_parent
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import EVIDENCE_FILE, encoded
from worksheet_local_sources_D127 import number
from worksheet_sale_rate_grid_D84 import money


TERMS = ROOT / "templates/synthetic-preferred-lp-gp-terms-D169.json"
SCHEMA = "miniuw.synthetic-d166-preferred-lp-gp-terms.v1"
ROLES = ("LP", "GP")
ORDER = ("return_capital", "pay_lp_preference", "split_residual")
PREFERENCE_BASIS = "simple_on_opening_unreturned_lp_capital_quarterly"
SOURCE_ORDER = ("net_refinance_distribution", "operating_distribution", "net_sale_distribution")


def shares(raw):
    if not isinstance(raw, dict) or raw.keys() != set(ROLES):
        return None
    values = {role: number(raw[role]) for role in ROLES}
    if any(value is None or value <= 0 for value in values.values()) or sum(values.values()) != 1:
        return None
    return values


def check_terms(terms, verified):
    keys = {"schema", "terms_id", "revision", "source_ref", "currency", "source_result_sha256", "source_revision_sha256",
            "scenario_cash_sha256", "contribution_shares", "residual_shares", "annual_preference", "preference_basis",
            "distribution_order", "same_date_distribution_order", "same_date_contributions_before_distributions",
            "fees_taxes_and_catch_up"}
    if terms is None:
        return "documented_allocation_terms_required"
    if not isinstance(terms, dict) or terms.keys() != keys:
        return "allocation_terms_incomplete"
    if (terms["schema"] != SCHEMA or terms["terms_id"] != "SYNTHETIC-D169-LP-GP"
            or type(terms["revision"]) is not int or terms["revision"] != 1 or terms["currency"] != "USD"
            or terms["source_ref"] != "docs/workbook-preferred-lp-gp-D169.md#terminos-sinteticos"
            or terms["preference_basis"] != PREFERENCE_BASIS or terms["distribution_order"] != list(ORDER)
            or terms["same_date_distribution_order"] != list(SOURCE_ORDER)
            or terms["same_date_contributions_before_distributions"] is not True
            or terms["fees_taxes_and_catch_up"] is not False
            or not isinstance(terms["scenario_cash_sha256"], dict) or terms["scenario_cash_sha256"].keys() != set(SCENARIOS)):
        return "allocation_terms_unsupported"
    if any(terms[key] != verified[key] for key in ("source_result_sha256", "source_revision_sha256")):
        return "allocation_terms_source_revision_mismatch"
    rate = number(terms["annual_preference"])
    if rate is None or not 0 <= rate <= 1:
        return "annual_preference_missing_or_invalid"
    if shares(terms["contribution_shares"]) is None or shares(terms["residual_shares"]) is None:
        return "allocation_shares_incomplete_or_invalid"
    return None


def waterfall(view, terms):
    cash = view["cash_per_usd_10"]
    dates = [entry["date"] for entry in view["irr"]["dated_net_flows"]]
    events_by_date = {d: [] for d in dates}
    for event in cash["events"]:
        require(event["currency"] == "USD" and event["date"] in events_by_date, "Incompatible project cash event")
        events_by_date[event["date"]].append(event)
    contributions, residual = (shares(terms[key]) for key in ("contribution_shares", "residual_shares"))
    rate = amount(terms["annual_preference"]) / 4
    capital = dict.fromkeys(ROLES, Fraction())
    pref_due = Fraction()
    ledger, checkpoints = [], []
    for index, (when, events) in enumerate(events_by_date.items()):
        opening = capital.copy()
        accrued = opening["LP"] * rate if index else Fraction()
        pref_due += accrued
        contributions_today = [e for e in events if e["kind"] == "contribution"]
        distributions_today = [e for e in events if e["kind"] == "distribution"]
        distributions_today.sort(key=lambda event: SOURCE_ORDER.index(event["category"]))
        for event in contributions_today + distributions_today:
            value = amount(event["amount"])
            capital_paid = dict.fromkeys(ROLES, Fraction())
            residual_paid = dict.fromkeys(ROLES, Fraction())
            pref_paid = Fraction()
            if event["kind"] == "contribution":
                allocation = {role: value * contributions[role] for role in ROLES}
                for role in ROLES:
                    capital[role] += allocation[role]
            else:
                outstanding = sum(capital.values())
                capital_total = min(value, outstanding)
                if capital_total:
                    for role in ROLES:
                        capital_paid[role] = capital_total * capital[role] / outstanding
                        capital[role] -= capital_paid[role]
                pref_paid = min(value - capital_total, pref_due)
                pref_due -= pref_paid
                residual_paid = {role: (value - capital_total - pref_paid) * residual[role] for role in ROLES}
                allocation = {role: capital_paid[role] + residual_paid[role] for role in ROLES}
                allocation["LP"] += pref_paid
            require(sum(allocation.values()) == value and min(*capital.values(), pref_due) >= 0,
                    "Waterfall did not conserve project cash")
            ledger.append(dict(event=event, allocated={k: rational(v) for k, v in allocation.items()},
                               returned_capital={k: rational(v) for k, v in capital_paid.items()},
                               lp_preference_paid=rational(pref_paid), residual={k: rational(v) for k, v in residual_paid.items()}))
        checkpoints.append(dict(date=when, lp_opening_capital=rational(opening["LP"]),
                                lp_preference_accrued=rational(accrued), lp_preference_due=rational(pref_due),
                                ending_capital={k: rational(v) for k, v in capital.items()}))

    participants = {}
    for role in ROLES:
        first = sum(amount(row["allocated"][role]) for row in ledger if row["event"]["category"] == "initial_capital")
        invested = sum(amount(row["allocated"][role]) for row in ledger if row["event"]["kind"] == "contribution")
        received = sum(amount(row["allocated"][role]) for row in ledger if row["event"]["kind"] == "distribution")
        require(first == 10 * contributions[role] and first > 0, "Verified initial equity basis required")
        values = dict(initial=first, additional=invested - first, total_received=received,
                      cash_unrecovered=max(Fraction(), invested - received), capital_unreturned=capital[role],
                      preference_paid=sum(amount(row["lp_preference_paid"]) for row in ledger) if role == "LP" else Fraction())
        participants[role] = dict(project_usd_10={k: rational(v) for k, v in values.items()},
                                  own_initial_usd_10={k: rational(v * 10 / first) for k, v in values.items()})
    for kind, key in (("contribution", "total_contributions"), ("distribution", "total_distributions")):
        require(sum(amount(v) for row in ledger if row["event"]["kind"] == kind for v in row["allocated"].values())
                == amount(cash[key]), "Allocated totals do not reconcile")
    return dict(state="computed_synthetic_cash_allocation", blockers=[], participants=participants,
                reconciliation=dict(events=ledger, quarterly_checkpoints=checkpoints, ending_lp_preference_due=rational(pref_due)))


def split(terms, verified):
    issue = check_terms(terms, verified)
    if issue:
        return {name: pending(issue) for name in SCENARIOS}
    result = {}
    for name in SCENARIOS:
        view = verified["scenarios"][name]
        if view["state"] != "checked_synthetic" or view["cash_per_usd_10"] is None:
            result[name] = pending("current_project_cash_unavailable")
        elif terms["scenario_cash_sha256"][name] != view["cash_sha256"]:
            result[name] = pending("allocation_terms_scenario_cash_mismatch")
        else:
            result[name] = waterfall(view, terms)
    return result


def render(results, terms):
    pref = usd(100 * amount(terms["annual_preference"]))
    lines = [(f"Por USD 10 iniciales del proyecto | Capital primero, preferente LP {pref} % simple anual, luego remanente", True),
             ("Reparto de prueba | Retorno personal real PENDING | Decisión real PENDING", False)]
    for name, result in results.items():
        if result["participants"] is None:
            lines.append((f"{name} | PENDING", True))
            continue
        lines.append((f"{name} | Aportes y cobros en USD", True))
        for row in result["reconciliation"]["events"]:
            event = row["event"]
            if amount(event["amount"]):
                lp, gp = (money(row["allocated"][role]) for role in ROLES)
                lines.append((f"{event['date']} | {KINDS[event['category']]} | LP {lp} | GP {gp}", False))
        for role in ROLES:
            own = result["participants"][role]["own_initial_usd_10"]
            project = result["participants"][role]["project_usd_10"]
            lines.append((f"{role} | Cobro total {money(project['total_received'])} | Por USD 10 propios: cobro {money(own['total_received'])}"
                          f", aporte extra {money(own['additional'])}, sin recuperar {money(own['cash_unrecovered'])}", True))
        due = result["reconciliation"]["ending_lp_preference_due"]
        lines.append((f"Preferente LP pagado {money(result['participants']['LP']['project_usd_10']['preference_paid'])}"
                      f" | Preferente LP impago {money(due)} por USD 10 iniciales del proyecto", False))
    lines.append(("El cuadre usa importes exactos. El redondeo se aplica al presentar cada cifra.", False))
    return render_page("D169 | Corrida D166", lines, 11,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Devolución de capital, preferencia LP y reparto del remanente | Piloto sintético")


def verify_controls(terms, verified, results):
    for name, result in results.items():
        require(result["state"] == "computed_synthetic_cash_allocation", "Expected complete synthetic allocation")
        project = verified["scenarios"][name]["cash_per_usd_10"]
        lp, gp = (result["participants"][role]["project_usd_10"] for role in ROLES)
        ledger = result["reconciliation"]["events"]
        require(len(ledger) == len(project["events"]) and {r["event"]["event_id"] for r in ledger}
                == {event["event_id"] for event in project["events"]}, "Gross events were omitted")
        # Independent fixture identity. Capital is paid pari passu, and every
        # dollar of pref shifts 20 cents of otherwise pro-rata residual to LP.
        preference = amount(lp["preference_paid"])
        require(amount(lp["total_received"]) == Fraction(4, 5) * amount(project["total_distributions"]) + preference / 5
                and amount(gp["total_received"]) == Fraction(1, 5) * amount(project["total_distributions"]) - preference / 5,
                "Return of capital and preferred distribution did not reconcile")
        due = amount(result["reconciliation"]["ending_lp_preference_due"])
        # Independently sum opening LP capital from original flows before each
        # quarterly checkpoint. In these fixtures all pre-sale receipts repay capital.
        dates = [row["date"] for row in verified["scenarios"][name]["irr"]["dated_net_flows"]]
        expected_pref = sum(
            sum((amount(event["amount"]) if event["kind"] == "contribution" else -amount(event["amount"]))
                for event in project["events"] if event["date"] < cutoff) * Fraction(4, 5) / 50
            for cutoff in dates[1:]
        )
        require(preference + due == expected_pref, "Preference accrual differs from the independent opening capital check")
        if name == "Base":
            require(preference == Fraction(29107, 20000) and all(amount(row["capital_unreturned"]) == 0 for row in (lp, gp))
                    and due == 0, "Base preference was not paid")
        else:
            require(preference == 0 and all(amount(row["capital_unreturned"]) > 0 for row in (lp, gp))
                    and due > 0, "Downside paid pref before returning capital")
    missing = deepcopy(terms)
    missing["annual_preference"] = None
    bad_shares = deepcopy(terms)
    bad_shares["residual_shares"]["LP"] = rational(Fraction(3, 4))
    wrong_revision = deepcopy(terms)
    wrong_revision["source_revision_sha256"] = "0" * 64
    for candidate, reason in ((None, "documented_allocation_terms_required"), (missing, "annual_preference_missing_or_invalid"),
                              (bad_shares, "allocation_shares_incomplete_or_invalid"),
                              (wrong_revision, "allocation_terms_source_revision_mismatch")):
        require(all(row == pending(reason) for row in split(candidate, verified).values()), "Incomplete terms yielded cash")
    wrong_cash = deepcopy(terms)
    wrong_cash["scenario_cash_sha256"]["Downside"] = "0" * 64
    isolated = split(wrong_cash, verified)
    require(isolated["Base"] == results["Base"] and isolated["Downside"] == pending("allocation_terms_scenario_cash_mismatch"),
            "Wrong source scope affected the other scenario")
    zero = deepcopy(terms)
    zero["annual_preference"] = rational(Fraction())
    for name, result in split(zero, verified).items():
        require(result["state"] == "computed_synthetic_cash_allocation"
                and all(amount(row["project_usd_10"]["preference_paid"]) == 0 for row in result["participants"].values())
                and all(amount(row["allocated"][role]) == amount(row["event"]["amount"]) * share
                        for row in result["reconciliation"]["events"]
                        for role, share in (("LP", Fraction(4, 5)), ("GP", Fraction(1, 5)))),
                "An explicit zero preference did not reproduce the pro-rata split")
    return 5


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Optional saved D166 package")
    parser.add_argument("--output", type=Path, help="Directory for the PDF, terms and audit evidence")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d169-") as folder:
        temp = Path(folder)
        package = args.package
        if package is None:
            evidence = temp / EVIDENCE_FILE
            evidence.write_bytes(shuffled_pdf())
            package = temp / "D166"
            run_package(CASE, CURRENT, evidence, package)
        verified, _ = verify_parent(package, CURRENT.read_bytes())
        raw = TERMS.read_bytes()
        terms = json.loads(raw)
        results = split(terms, verified)
        pending_cases = verify_controls(terms, verified, results)
        pdf = render(results, terms)
        output = args.output or temp / "D169"
        output.mkdir()
        (output / "terms.json").write_bytes(raw)
        (output / "MiniUW_Resumen.pdf").write_bytes(pdf)
        proof = dict(status="passed", decision="PENDING", page_count=1, pending_cases=pending_cases,
                     pdf_sha256=sha(pdf), terms_sha256=sha(raw), source_result_sha256=verified["source_result_sha256"])
        (output / "results.json").write_bytes(encoded(proof | dict(scenarios=results, source_audit=verified["source_audit"],
            personal_investor_return=dict(state="PENDING", blockers=["verified_real_allocation_terms_required"]))))
        print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
