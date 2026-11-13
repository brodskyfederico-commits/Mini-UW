"""Replay the D190 pilot control workbook with the synthetic D181 intake."""
from argparse import ArgumentParser
from collections import Counter
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
from operator import ge, gt, le, lt
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZipInfo

from check_worksheet_integrated_screening_D181 import BOOKS, CASE, CURRENT, PLAN, shuffled_pdf
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_reconciliation_D179 import compare_scenario, require
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import encoded, verify_package, write_package
from pilot_workbook_D49 import METRICS, Formula, sheet
from reconcile_worksheet_D179 import calculate, exact
from worksheet_revision_D128 import audit_revision
from worksheet_sale_rate_grid_D84 import money


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/review/piloto-real-D190/MiniUW_Control_y_Cotejo_D190.xlsx"
NAMES = ("Base", "Downside")
METRIC_IDS = dict(zip(METRICS, (
    "YoC", "spread", "equity_recovered", "equity_cash_in", "breakeven_occupancy",
    "post_refi_CoC", "equity_TDC", "equity_multiple", "IRR", "asking_relative_to_supported_price",
), strict=True))
FLOW_LABELS = {
    "initial": "Aporte inicial", "operating-funding": "Aporte de operación",
    "refinance": "Cobro neto de refinanciación", "operating": "Cobro de operación",
    "sale": "Cobro neto de venta",
}
CASE_ID = "SYNTHETIC-D181"
OPERATORS = {">=": ge, ">": gt, "<=": le, "<": lt}


def digest(raw):
    return sha256(raw).hexdigest()


def read_sheet(raw):
    root = ET.fromstring(raw)
    widths = [int(col.get("width")) for col in root.findall(".//{*}col")]
    rows = []
    for item in root.findall(".//{*}sheetData/{*}row"):
        cells = []
        for cell in item:
            literal = cell.findtext("{*}v")
            formula = cell.findtext("{*}f")
            if formula is not None:
                value = Formula(formula, literal if cell.get("t") == "str" else Decimal(literal))
            elif cell.get("t") == "inlineStr":
                value = cell.findtext("{*}is/{*}t")
            else:
                value = None if literal is None else Decimal(literal)
            cells.append(value)
        rows.append(cells)
    return rows, widths


def edit_template(template, update):
    result = BytesIO()
    with ZipFile(BytesIO(template)) as source, ZipFile(result, "w", compression=8, compresslevel=6) as target:
        require(source.testzip() is None, "Damaged D190 workbook")
        for name in sorted(source.namelist()):
            raw = source.read(name)
            if name.startswith("xl/worksheets/sheet"):
                index = int(Path(name).stem.removeprefix("sheet"))
                rows, widths = read_sheet(raw)
                raw = sheet(update(index, rows), widths, filter_table=index > 1).encode()
            entry = ZipInfo(name)
            entry.compress_type = 8
            target.writestr(entry, raw)
    return result.getvalue()


def numeric(value):
    return None if value is None else float(value)


def guarded_diff(left, right, first, last, row):
    cached = "" if left is None or right is None else float(left - right)
    return Formula(f'IF(COUNT({first}{row}:{last}{row})=2,{first}{row}-{last}{row},"")', cached)


def ref_metrics(reference, inputs, name):
    events = reference["events"]
    opening = events["initial"][2]
    contributed = sum(value for _, kind, value in events.values() if kind == "contribution")
    received = sum(value for _, kind, value in events.values() if kind == "distribution")
    funding = reference["build"]["funding"].values()
    tdc = sum(row["project_uses"] + row["origination_fee_paid"] + row["interest_paid"] for row in funding)
    applied = tdc - sum(row["loan_draw"] for row in funding)
    yoc = reference["noi"]["valoracion"]["noi"] / tdc
    cap = exact(inputs["integrated_screening"][name]["reference_cap"]["value"])
    return {
        "YoC": yoc, "spread": (yoc - cap) * 10_000, "equity_TDC": applied / tdc,
        "equity_multiple": received / contributed, "equity_recovered": reference["refinance_net"] / opening,
        "equity_cash_in": max(0, -reference["refinance_net"]), "post_refi_CoC": reference["coc"],
    }


def reference_disposition(rule, lower, upper):
    def matches(condition):
        compare = OPERATORS[condition["operator"]]
        limit = exact(condition["threshold"])
        return compare(lower, limit) and compare(upper, limit)

    passes, fails = [matches(rule[key]) for key in ("pass_condition", "fail_condition")]
    require(not (passes and fails), "Overlapping fixture conditions")
    return "PASS_CONDITION" if passes else "FAIL_CONDITION" if fails else "PENDING"


def event_rows(references, model):
    rows = []
    for name, ref in references.items():
        view = model["scenarios"][name]
        cash = view["cash_per_usd_10"]
        scale = exact(cash["scale_factor"])
        ref_scale = 10 / ref["events"]["initial"][2]
        require(scale == ref_scale and exact(cash["reference_amount"]) == 10, "Incorrect initial basis")
        for i, event in enumerate(cash["events"]):
            identifier = event["event_id"]
            day, kind, project = ref["events"][identifier]
            model_amount = exact(event["amount"])
            rows.append([name, FLOW_LABELS.get(identifier, "Aporte adicional de obra"), day.isoformat(),
                         "Aporte" if kind == "contribution" else "Cobro",
                         f"D179 / {name} / events / {identifier}",
                         f"results.json#/scenarios/{name}/cash_per_usd_10/events/{i}",
                         model_amount / scale, project, model_amount, project * ref_scale])
        # The workbook calls for a cash-in row even when the closing has no contribution.
        model_cash_in = exact(view["construction_refinance"]["projected_cash_in_required"])
        ref_cash_in = max(0, -ref["refinance_net"])
        rows.append([name, "Aporte al refinanciar", ref["refi"].isoformat(), "Aporte",
                     f"D179 / {name} / cierre de refi", f"results.json#/scenarios/{name}/construction_refinance/projected_cash_in_required",
                     model_cash_in, ref_cash_in, model_cash_in * scale, ref_cash_in * ref_scale])
    name_order = {name: i for i, name in enumerate(NAMES)}
    return sorted(rows, key=lambda row: (name_order[row[0]], row[2], row[3] == "Cobro"))


def cash_flow_sheet(header, entries):
    rows = [header]
    for row_num, entry in enumerate(entries, 2):
        model, ref = entry[8:10]
        complete = all(value is not None for value in entry[:10])
        state = "PENDING" if not complete or entry[6] != entry[7] or model != ref else "CUADRA"
        issue = "Falta un dato o localizador" if not complete else "Diferencia por resolver"
        rows.append(entry[:6] + [numeric(value) for value in entry[6:10]]
                    + [guarded_diff(model, ref, "I", "J", row_num), None if state == "CUADRA" else issue, state])
    return rows


def control_summary(reference, inputs, view, evidence, name):
    opening = reference["events"]["initial"][2]
    scale = 10 / opening
    contributions = sum(value * scale for _, kind, value in reference["events"].values() if kind == "contribution")
    receipts = sum(value * scale for _, kind, value in reference["events"].values() if kind == "distribution")
    cash = view["cash_per_usd_10"]
    snapshot = evidence["refinance_capital_per_usd_10"]
    cash_path = "cash_per_usd_10/"
    return {
        "Aporte inicial verificado": (exact(cash["basis_amount"]), opening, cash_path + "basis_amount"),
        "Factor 10 / aporte inicial": (exact(cash["scale_factor"]), scale, cash_path + "scale_factor"),
        "Total aportado": (exact(cash["total_contributions"]), contributions, cash_path + "total_contributions"),
        "Aportes adicionales": (exact(cash["total_contributions"]) - 10, contributions - 10, cash_path + "events"),
        "Total cobrado": (exact(cash["total_distributions"]), receipts, cash_path + "total_distributions"),
        "Resultado nominal": (exact(cash["net_cash_profit"]), receipts - contributions, cash_path + "net_cash_profit"),
        "Saldo sin recuperar": (exact(cash["unrecovered_after_sale"]), max(0, contributions - receipts), cash_path + "unrecovered_after_sale"),
        "Capital remanente": (
            exact(snapshot["capital_still_invested"]), exact(inputs["post_refinance_coc"][name]["equity_still_invested"]) * scale,
            "post_refinance_coc/equity_still_invested",
        ),
        "Equity retenido, sin cobro": (
            exact(snapshot["retained_property_equity"]), (reference["valuation"] - reference["principal"]) * scale,
            "valuation_and_sale/refinance_value + construction_refinance/gross_proceeds",
        ),
    }


def populate(template, case, source, refs, model, dated):
    screening = model["screening"]
    comparisons = {(row["scenario_id"], row["metric_id"]): row for row in screening["comparisons"]}
    metrics = {name: ref_metrics(refs[name], case["rent_inputs"], name) for name in NAMES}
    totals = {
        name: control_summary(refs[name], case["rent_inputs"], model["scenarios"][name],
                              screening["metric_evidence_by_scenario"][name], name)
        for name in NAMES
    }

    def put_criteria(rows):
        for row in rows[1:]:
            name, metric = row[:2]
            comparison = comparisons[name, METRIC_IDS[metric]]
            record = comparison["metric_record"]
            row[2:6] = ["Aplica en el ensayo", record["definition_ref"], record["unit"], record["period_ref"]]
            locator = comparison["criterion_locator"]
            if locator is None:
                require(comparison["state"] == "PENDING", "Unresolved criterion received a state")
                row[2], row[6] = "Definición abierta", "; ".join(comparison["blockers"])
                continue
            rule = case["rules"][int(locator.split("/")[-1])]
            conditions = [rule["pass_condition"], rule["fail_condition"]]
            row[6:12] = [f"{case['criteria_revision']} · case.json#{locator}",
                         *[part for c in conditions for part in (c["operator"], numeric(exact(c["threshold"])))],
                         "Operadores explícitos de la prueba"]
            row[12:15] = ["Sólo ensayo", None, comparison["state"]]
        return rows

    def put_totals(rows):
        for num, row in enumerate(rows[1:], 2):
            name, key = row[:2]
            ref = refs[name]
            day, _, _ = ref["events"]["initial"]
            window = f"{day}/{ref['sale']}"
            state, independent_state, reason = "CUADRA", "CUADRA", None
            left, right, pointer = None, None, None
            comparison = comparisons.get((name, METRIC_IDS.get(key)))
            irr_comparison = comparisons[name, "IRR"]
            if key in totals[name]:
                left, right, source_key = totals[name][key]
                pointer = f"/scenarios/{name}/{source_key}"
                if key in {"Capital remanente", "Equity retenido, sin cobro"}:
                    window = ref["refi"].isoformat()
            elif key.startswith("TIR anual"):
                endpoint = "lower" if key.endswith("inferior") else "upper"
                interval = irr_comparison["metric_record"]["annual_enclosure"]
                left = exact(interval[endpoint])
                right = ref["irr"][0 if endpoint == "lower" else 1]
                pointer = f"/screening/irr_by_scenario/{name}/annual_enclosure/{endpoint}"
                state = independent_state = "CONTENIDA"
                reason = "El intervalo de referencia está dentro del intervalo del motor"
            elif comparison:
                rec = comparison["metric_record"]
                window, row[2], pointer = rec["period_ref"], rec["unit"], comparison["metric_locator"]
                state = comparison["state"]
                locator = comparison["criterion_locator"]
                if locator:
                    rule = case["rules"][int(locator.split("/")[-1])]
                    if key == "TIR / IRR":
                        independent_state = reference_disposition(rule, *ref["irr"])
                        reason = "Ver extremos en filas de TIR anual"
                    else:
                        metric_id = METRIC_IDS[key]
                        left, right = exact(rec["value"]), metrics[name][metric_id]
                        independent_state = reference_disposition(rule, right, right)
                    require(independent_state == state, f"{name} / {key}: criterion disposition differs")
                else:
                    independent_state = "PENDING"
                    reason = "; ".join(comparison["blockers"])
            elif key == "Dictamen":
                require(model["decision"] == screening["simulation_result"] == "PENDING", "Formal gate opened")
                pointer = "/decision"
                state = independent_state = "PENDING"
                reason = "SRC-02, SRC-03 y aprobaciones reales pendientes"
            else:
                raise ValueError(f"Unknown D190 comparison row: {key}")
            if left is not None and state != "CONTENIDA":
                require(left == right, f"{name} / {key}: totals disagree")
            row[3:12] = [window, f"D179 / cálculo independiente {name}",
                         f"results.json#{pointer}" if pointer else None, numeric(left), numeric(right),
                         guarded_diff(left, right, "G", "H", num), state, independent_state, reason]
        return rows

    def update(index, rows):
        if index == 1:
            rows[0][0] = "ENSAYO SINTÉTICO D191 · Piloto real PENDING"
            values = [CASE_ID, model["revision_review"]["reference_revision"], None, "USD",
                      f"Base {digest(source['workbook_raw'])} / Downside {digest(source['downside_workbook_raw'])}",
                      "D179 / cálculo directo desde Inputs y case.json", "Ensayo automatizado en el VPS", "PENDING"]
            for row, value in zip(rows[2:10], values, strict=True):
                row[1] = value
            rows[4][1] = "Corte del ensayo fijado por la revisión sintética D181"
        elif index == 2:
            return put_criteria(rows)
        elif index == 3:
            require(all(row[2] is None and row[5] == "PENDING" for row in rows[1:]), "Real roles must stay pending")
            for row in rows[1:]:
                row[3] = "Designación y aprobación reales pendientes"
        elif index == 4:
            return cash_flow_sheet(rows[0], dated)
        elif index == 5:
            return put_totals(rows)
        return rows

    return edit_template(template, update)


def verify_workbook(raw, dated):
    with ZipFile(BytesIO(raw)) as book:
        require(book.testzip() is None, "Unreadable copy of D190")
        for member in book.namelist():
            ET.fromstring(book.read(member))
        names = [item.get("name") for item in ET.fromstring(book.read("xl/workbook.xml")).findall(".//{*}sheet")]
        require(names == ["Guia", "Criterios", "Pendientes", "Flujos USD10", "Totales y metricas"],
                "Workbook tabs differ from D190")
        guide, criteria, roles, flows, totals = [
            read_sheet(book.read(f"xl/worksheets/sheet{i}.xml"))[0] for i in range(1, 6)
        ]
    require(guide[9][1] == "PENDING", "Workbook opened the pilot")
    require(len(roles) == 12 and all(row[2] is None and row[5] == "PENDING" for row in roles[1:]), "Role approval leaked")
    require(Counter(row[-1] for row in criteria[1:]) == {"PASS_CONDITION": 9, "FAIL_CONDITION": 7, "PENDING": 4},
            "Criterion count or disposition drift")
    require(all(row[8] is None and row[10] is None for row in criteria[1:] if row[-1] == "PENDING"),
            "Unresolved threshold filled")
    require(len(flows) == len(dated) + 1, "Dated workbook rows missing")
    for r, (saved, event) in enumerate(zip(flows[1:], dated, strict=True), 2):
        require(saved[:6] == event[:6] and saved[12] == "CUADRA"
                and saved[6:10] == [Decimal(str(float(value))) for value in event[6:10]]
                and saved[10] == guarded_diff(event[8], event[9], "I", "J", r),
                f"Invalid stored flow row {r}")
    require(len(totals) == 45 and all(row[9:11] == ["PENDING", "PENDING"]
            for row in totals[1:] if row[1] == "Dictamen"), "Summary dictamen drift")
    blank = dated[0][:8] + [dated[0][8], None]
    altered = dated[0][:7] + [dated[0][7] + 24_000, dated[0][8], dated[0][9] + exact("0.1")]
    missing, difference = cash_flow_sheet(flows[0], [blank, altered])[1:]
    require(missing[10].cached == "" and missing[-1] == "PENDING", "Missing amount became zero")
    require(difference[10].cached == -0.1 and difference[-1] == "PENDING", "Difference failed to block")
    require(any(row[1] == "Aporte de operación" and row[8:10] == [0, 0] for row in flows[1:]),
            "No explicit zero was exercised")


def run(output):
    template = TEMPLATE.read_bytes()
    case_raw, current = CASE.read_bytes(), CURRENT.read_bytes()
    case = json.loads(case_raw)
    source = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf())
    refs = {name: calculate(source[key], case["rent_inputs"], name) for name, key in
            zip(NAMES, ("workbook_raw", "downside_workbook_raw"), strict=True)}
    with TemporaryDirectory(prefix="miniuw-d191-") as temp:
        package = Path(temp) / "synthetic"
        write_package(case_raw, package, current_revision_raw=current, **source)
        audit = verify_package(package, current_revision_raw=current)
        model = json.loads((package / "results.json").read_bytes())
        pdf = (package / "MiniUW_Resumen.pdf").read_bytes()
    require((audit["audit_bot"], audit["vigencia"], model["decision"], model["simulation_result"])
            == ("B16", "VIGENTE", "PENDING", "PENDING"), "Synthetic package gates changed")
    require(model["personal_investor_return"] is None and not model["real_decisions_enabled"]
            and not model["deployment_enabled"], "Real return or authorization leaked")

    older = json.loads(current)
    older["revision"] = "SYNTHETIC-D191-different-cut"
    stale = audit_revision(model, encoded(older))
    require(stale["vigencia"] == "HISTORICO" and stale["state"] == stale["simulation_result"] == "PENDING",
            "Stale revision was accepted")

    count = Counter()
    summary = {}
    for name, reference in refs.items():
        compared, summary[name] = compare_scenario(reference, model["scenarios"][name], name)
        count.update(row[-2] for row in compared)
    require(count == {"CUADRA": 734, "CONTENIDA": 2}, f"Reference reconciliation drift: {count}")
    dated = event_rows(refs, model)
    workbook = populate(template, case, source, refs, model, dated)
    verify_workbook(workbook, dated)
    require(TEMPLATE.read_bytes() == template, "The blank pilot workbook changed")

    report = pdf_text(pdf)
    headlines = ["USD 10", "Dictamen simulado PENDING", "Decisión real PENDING", "Retorno personal LP/GP PENDING"]
    for name, ref in refs.items():
        cash = model["scenarios"][name]["cash_per_usd_10"]
        scale = 10 / ref["events"]["initial"][2]
        headlines.extend([ref["refi"].isoformat(), ref["sale"].isoformat(),
                          *[money(cash[key]) for key in ("total_distributions", "unrecovered_after_sale")]])
        summary[name]["cash_by_usd10"] = {
            event: dict(date=day.isoformat(), type=kind, amount=money(rational(amount * scale)))
            for event, (day, kind, amount) in ref["events"].items()
        }
        summary[name]["totals_by_usd10"] = {
            key: money(cash[key]) for key in ("total_contributions", "total_distributions",
                                             "net_cash_profit", "unrecovered_after_sale")
        }
        summary[name]["totals_by_usd10"]["additional_contributions"] = money(
            rational(exact(cash["total_contributions"]) - 10)
        )
    require(all(label in report for label in headlines), "The one-page source report lost a material cash result")

    output.mkdir(parents=True, exist_ok=True)
    artifacts = {"MiniUW_Cotejo_Sintetico_D191.xlsx": workbook, "MiniUW_Informe_USD10_D191.pdf": pdf}
    for name, raw in artifacts.items():
        (output / name).write_bytes(raw)
    result = dict(status="passed", decision="PENDING", simulation_result="PENDING", real_pilot="PENDING",
                  personal_return="PENDING", real_decisions_enabled=False, deployment_enabled=False,
                  independent_exact_matches=count["CUADRA"], independent_enclosed_irrs=count["CONTENIDA"],
                  dated_cash_events=len(dated) - len(NAMES), additional_cash_in_checks=len(NAMES), criterion_rows=20,
                  pdf_pages=1, synthetic_case=CASE_ID, revision=audit["current_revision"],
                  workbook_checks=["cash_and_date", "blank", "explicit_zero", "difference", "pending_roles", "criteria"],
                  stale_revision="PENDING", sources={k: digest(v) for k, v in source.items()} | {
                      "case": digest(case_raw), "current_revision": digest(current), "blank_D190_workbook": digest(template)},
                  artifacts={k: digest(v) for k, v in artifacts.items()}, scenarios=summary)
    (output / "MiniUW_Verificacion_D191.json").write_bytes(encoded(result))
    return result


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(run(parser.parse_args().output), ensure_ascii=False, sort_keys=True))
