"""Audit D166 and verify project-equity IRR and post-refinance cash yield."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader

from check_operating_replay_D20 import require
from check_worksheet_construction_pdf_D157 import run_package
from check_worksheet_market_evidence_D166 import CASE, CURRENT, shuffled_pdf
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.irr_checked_output import _current_annual_roots
from miniuw_foundation.irr_interval_output import _annual_enclosure
from miniuw_foundation.primitive_periodic_returns import isolate_primitive_periodic_returns
from miniuw_worksheet_v1 import EVIDENCE_FILE, encoded, verify_package
from worksheet_final_metrics_D126 import COC_BASIS, post_refinance_coc
from worksheet_irr_D122 import display_enclosure
from worksheet_local_sources_D127 import day
from worksheet_sale_rate_grid_D84 import money


PROFILE = "synthetic_documented_market_insurance_and_bank"
CASH_BASIS = "SYNTHETIC-D167-gross-project-equity-contributed-through-refinance"
KINDS = {"initial_capital": "Aporte inicial", "additional_capital": "Aporte adicional",
         "refinance_cash_in": "Aporte al refinanciar", "net_refinance_distribution": "Cobro neto de refi",
         "operating_distribution": "Cobro de operación", "net_sale_distribution": "Cobro neto de venta"}


def quarterly_cash(cash, dates):
    grid = [day(value) for value in dates]
    if not 2 <= len(grid) <= 65 or None in grid:
        return None
    first = grid[0]
    offsets = [(d.year - first.year) * 12 + d.month - first.month for d in grid]
    if offsets != list(range(0, 3 * len(grid), 3)) or any(d.day != first.day for d in grid):
        return None
    flows = dict.fromkeys(dates, Fraction())
    for event in cash["events"]:
        if event["date"] not in flows:
            return None
        value = _fraction(event["amount"])
        flows[event["date"]] += value if event["kind"] == "distribution" else -value
    return flows


def verify_irr(cash, dates):
    flows = quarterly_cash(cash, dates)
    if flows is None:
        return dict(state="PENDING", annual_enclosure=None, blockers=["cash_dates_outside_declared_quarterly_grid"])
    roots = isolate_primitive_periodic_returns(list(flows.values()), Fraction(1, 100_000_000), 128, 50_000)
    annual, _, issues = _current_annual_roots(roots, 4, 3)
    enclosure, blockers = _annual_enclosure(dict(periodic_irr=roots, annual_irr_roots=annual),
                                           dict(annualization_blockers=issues))
    result = dict(state="PENDING", annual_enclosure=None, blockers=sorted(set(blockers + issues)),
                  dated_net_flows=[dict(date=d, net=rational(v)) for d, v in flows.items()],
                  period_ref=f"{dates[0]}/{dates[-1]}", step_months=3, periods_per_year=4, periodic_result=roots)
    if enclosure is None:
        return result

    # An independent sign check of the discounted ledger. One sign change also
    # establishes uniqueness for these fixtures on the positive discount domain.
    values = list(flows.values())
    signs = [value > 0 for value in values if value]
    changes = sum(a != b for a, b in zip(signs, signs[1:]))
    root, = roots["roots"]
    interval = root["periodic_rate_interval"]
    if interval is None:
        lower = upper = Fraction(root["exact_periodic_rate"])
    else:
        lower, upper = (Fraction(interval[k]) for k in ("lower", "upper"))

    def npv(rate):
        return sum((value / (1 + rate) ** i for i, value in enumerate(values)), Fraction())

    low_npv, high_npv = npv(lower), npv(upper)
    # Keep signs rather than expanded fractions, which can be very large.
    verified = changes == 1 and low_npv * high_npv <= 0
    return result | dict(state="checked_synthetic" if verified else "PENDING",
                         annual_enclosure=enclosure if verified else None,
                         blockers=[] if verified else ["independent_irr_sign_check_inconclusive"],
                         independent_sign_check=dict(sign_changes=changes,
                                                     npv_at_lower=(low_npv > 0) - (low_npv < 0),
                                                     npv_at_upper=(high_npv > 0) - (high_npv < 0)))


def verify_coc(cash, refi, sale):
    events = cash["events"]
    scale = _fraction(cash["scale_factor"])
    base_events = [e for e in events if e["kind"] == "contribution" and e["date"] <= refi]
    base = sum((_fraction(e["amount"]) for e in base_events), Fraction())
    timing = dict(window_start=refi, window_end=sale, definition=COC_BASIS, capital_basis=CASH_BASIS,
                  capital_event_ids=[e["event_id"] for e in base_events], annualized=False)
    if (scale is None or scale <= 0 or base <= 0 or {e["date"] for e in events
            if e["category"] in ("net_refinance_distribution", "refinance_cash_in")} != {refi}
            or {e["date"] for e in events if e["category"] == "net_sale_distribution"} != {sale}):
        return timing | dict(state="PENDING", value=None, blockers=["compatible_refinance_sale_and_capital_basis_required"])
    evidence = post_refinance_coc(cash, COC_BASIS, {refi[:4]: rational(base / scale)})
    if evidence["blockers"]:
        return evidence | timing | dict(state="PENDING")
    operating = [e for e in events if e["category"] == "operating_distribution" and refi < e["date"] <= sale]
    # A recorded zero is admissible. The absence of an operating row is unresolved.
    if not operating:
        return timing | dict(state="PENDING", value=None, blockers=["documented_operating_distribution_required"])
    receipts = sum((_fraction(e["amount"]) for e in operating), Fraction())
    require(_fraction(evidence["value"]) * base == receipts
            and _fraction(evidence["operating_receipts"]) * scale == receipts
            and _fraction(evidence["capital_base"]) * scale == base, "CoC did not reconcile to the ledger")
    return evidence | timing | dict(state="checked_synthetic", capital_per_usd_10=rational(base),
                                    operating_cash_per_usd_10=rational(receipts))


def scenario_metrics(view):
    cash = view.get("cash_per_usd_10")
    calendar = view.get("project_calendar")
    if cash is None or calendar is None or view["blockers"]:
        return dict(state="PENDING", cash_per_usd_10=None, irr=None, coc=None,
                    blockers=["verified_scenario_cash_and_calendar_required", *view["blockers"]])
    require(_fraction(cash["reference_amount"]) == 10, "D167 requires USD 10 of initial equity")
    irr = verify_irr(cash, calendar["equity_dates"])
    coc = verify_coc(cash, calendar["refinance_date"], calendar["sale_date"])
    blockers = irr["blockers"] + coc["blockers"]
    return dict(state="PENDING" if blockers else "checked_synthetic", cash_per_usd_10=cash,
                cash_sha256=sha256(encoded(cash)).hexdigest(), irr=irr, coc=coc, blockers=blockers)


def render(scenarios):
    lines = [("Equity agregado del proyecto | Retorno personal PENDING | Decisión real PENDING", True)]
    for name, view in scenarios.items():
        cash, irr, coc = (view[key] for key in ("cash_per_usd_10", "irr", "coc"))
        if cash is None:
            lines.append((f"{name} | PENDING · faltan flujos y calendario verificados", True))
            continue
        lines.append((f"{name} | Cobros USD {money(cash['total_distributions'])} | Aportado USD {money(cash['total_contributions'])}"
                      f" | Sin recuperar USD {money(cash['unrecovered_after_sale'])}", True))
        lines.append((f"TIR anual {display_enclosure(irr['annual_enclosure'])} | Múltiplo {money(cash['equity_multiple'])}x", False))
        rate = "PENDING" if coc["value"] is None else money(rational(100 * _fraction(coc["value"]))) + " %"
        label = f"CoC del tramo {rate} | {coc['window_start']} a {coc['window_end']} | Sin anualizar"
        lines.append((label, False))
        for event in cash["events"]:
            if _fraction(event["amount"]):
                lines.append((f"{event['date']} | {KINDS[event['category']]} USD {money(event['amount'])}", False))
    lines.append(("CoC sintético: cobro de operación del tramo / aportes brutos acumulados hasta refi.", False))
    lines.append(("El cobro operativo registrado al cierre puede incluir caja acumulada antes de la refi.", False))
    return render_page("D167 | Corrida D166", lines, 11,
                       "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "TIR anual y CoC del tramo posrefinanciación | Ejemplo sintético")


def verify(directory, current_revision):
    audit = verify_package(directory, current_revision_raw=current_revision)
    require(audit["audit_bot"] == "B16" and audit["vigencia"] == "VIGENTE" and audit["profile"] == PROFILE,
            "A current and reproducible D166 package is required")
    raw = (directory / "results.json").read_bytes()
    original = json.loads(raw)
    require(original["decision"] == "PENDING" and original["personal_investor_return"] is None
            and not original["real_decisions_enabled"] and not original["deployment_enabled"],
            "D166 must be an aggregate project-equity simulation")
    scenarios = {name: scenario_metrics(original["scenarios"][name]) for name in ("Base", "Downside")}
    report = render(scenarios)
    return dict(status="verified", decision="PENDING", personal_investor_return=dict(
                state="PENDING", blockers=["documented_allocation_terms_required"]), source_result_sha256=sha256(raw).hexdigest(),
                source_pdf_sha256=audit["pdf_sha256"], source_revision_sha256=sha256(current_revision).hexdigest(),
                source_audit=audit, scenarios=scenarios, pdf_sha256=sha256(report).hexdigest()), report


def check_examples(result):
    views = result["scenarios"]
    for name, expected_irr, expected_coc in (("Base", "17,58% a 17,59%", "9,63"),
                                            ("Downside", "-42,32% a -42,31%", "3,02")):
        view = views[name]
        require(view["state"] == "checked_synthetic" and display_enclosure(view["irr"]["annual_enclosure"]) == expected_irr
                and money(rational(_fraction(view["coc"]["value"]) * 100)) == expected_coc, f"{name} metrics drift")
    base = views["Base"]
    cash = base["cash_per_usd_10"]
    dates = [e["date"] for e in base["irr"]["dated_net_flows"]]
    off_grid = deepcopy(cash)
    off_grid["events"][-1]["date"] = "2028-12-29"
    require(verify_irr(off_grid, dates)["state"] == "PENDING", "Off-grid TIR was used")
    refi, sale = (base["coc"][key] for key in ("window_start", "window_end"))
    no_coc = deepcopy(cash)
    no_coc["events"] = [e for e in cash["events"] if e["kind"] != "contribution"]
    require(verify_coc(no_coc, refi, sale)["value"] is None, "A zero CoC denominator was used")
    missing = deepcopy(cash)
    missing["events"] = [e for e in cash["events"] if e["category"] != "operating_distribution"]
    require(verify_coc(missing, refi, sale)["value"] is None, "Missing operating cash was silently treated as zero")
    zero = deepcopy(cash)
    for event in zero["events"]:
        if event["category"] == "operating_distribution":
            event["amount"] = rational(Fraction())
    require(_fraction(verify_coc(zero, refi, sale)["value"]) == 0, "Documented zero was not preserved")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Optional existing D166 output to verify")
    parser.add_argument("--output", type=Path, help="Directory for the D167 PDF and evidence")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d167-") as folder:
        temp = Path(folder)
        package = args.package
        if package is None:
            evidence = temp / EVIDENCE_FILE
            evidence.write_bytes(shuffled_pdf())
            package = temp / "D166"
            run_package(CASE, CURRENT, evidence, package)
        result, pdf = verify(package, CURRENT.read_bytes())
        check_examples(result)
        output = args.output or temp / "D167"
        output.mkdir()
        (output / "results.json").write_bytes(encoded(result))
        (output / "MiniUW_Resumen.pdf").write_bytes(pdf)
        print(json.dumps(dict(status="passed", decision="PENDING", pending_cases=3,
                              page_count=len(PdfReader(BytesIO(pdf)).pages), pdf_sha256=result["pdf_sha256"],
                              source_result_sha256=result["source_result_sha256"]), sort_keys=True))


if __name__ == "__main__":
    main()
