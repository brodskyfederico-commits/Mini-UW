"""Rebuild the audited D178 case and export the independent comparison row by row."""
import argparse
import csv
from datetime import date
from decimal import Decimal, localcontext
from hashlib import sha256
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from check_worksheet_debt_yield_D178 import BOOKS, CASE, CURRENT, PLAN, shuffled_pdf
from check_worksheet_return_metrics_D167 import verify_irr
from miniuw_worksheet_v1 import verify_package, write_package
from reconcile_worksheet_D179 import PERIODS, exact, calculate


def require(condition, message):
    if not condition:
        raise ValueError(message)


def human(value):
    with localcontext() as context:
        context.prec = 32
        return format(Decimal(value.numerator) / Decimal(value.denominator), ".8f")


def compare_scenario(expected, actual, name):
    rows = []

    def row(section, label, reference, miniuw, *, unit="USD", when="", pointer=""):
        left, right = exact(reference), exact(miniuw)
        rows.append([name, section, label, when, unit, human(left), human(right), human(left - right),
                     str(left), str(right), str(left - right), "CUADRA" if left == right else "DIFERENCIA", pointer])

    for label, reference in expected["noi"].items():
        period_id = PERIODS[label][0]
        period = actual["noi_by_period"][period_id]
        prefix = f"/noi_by_period/{period_id}"

        def period_row(label_key, value, reported, field, unit="USD"):
            row(f"NOI/{label}", label_key, value, reported, unit=unit,
                when=period["growth"]["window_start"], pointer=f"{prefix}/{field}")

        for field in ("gross_rent", "effective_rent", "other_income", "operating_expenses_excluding_tax", "noi"):
            period_row(field, reference[field], period[field], field)
        tax_key, tax_value = ("buyer_property_tax/total", period["buyer_property_tax"]["total"]) if label == "salida" else (
            "property_tax/annual_tax", period["property_tax"]["annual_tax"])
        period_row("property_tax", reference["tax"], tax_value, tax_key)
        for index, group in enumerate(period["groups"]):
            for field, value in reference["groups"][group["group_id"]].items():
                period_row(f"{group['group_id']}/{field}", value, group["results"][field], f"groups/{index}/results/{field}")
        for field, value in reference["commercial"].items():
            period_row(f"commercial/{field}", value, period["commercial"][field], f"commercial/{field}",
                       "months" if field == "recognized_months" else "USD")
        period_row("utilities", reference["utility_total"], period["utilities"]["annual_total"], "utilities/annual_total")
        for index, expense in enumerate(period["operating_costs"]["expense_rows"]):
            item = expense["item_id"]
            value = reference["utilities"][item.removeprefix("SYNTHETIC-utilities-")] if item.startswith(
                "SYNTHETIC-utilities-") else reference["expenses"][item]
            period_row(item, value, expense["amount"], f"operating_costs/expense_rows/{index}/amount")

    build = expected["build"]
    funding = actual["construction_financing"]
    budget = actual["construction_budget"]
    for key, ref, value, pointer in (
        ("direct_hard", build["direct"], budget["direct_hard_cost"], "/construction_budget/direct_hard_cost"),
        ("development_cost", build["total_cost"], budget["total_development_cost"], "/construction_budget/total_development_cost"),
        ("commitment", build["commitment"], funding["commitment"], "/construction_financing/commitment"),
        ("origination_fee", build["fee"], funding["origination_fee"], "/construction_financing/origination_fee"),
        ("construction_payoff", build["payoff"], funding["construction_principal_payoff"], "/construction_financing/construction_principal_payoff"),
    ):
        row("obra", key, ref, value, pointer=pointer)

    def schedule(section, reference, reported, date_key, pointer):
        dates = [date.fromisoformat(item[date_key]) for item in reported]
        require(dates == list(reference), f"{name} {section}: date inventory mismatch")
        for index, (day, item) in enumerate(zip(dates, reported, strict=True)):
            for key, value in reference[day].items():
                if key == "end_date":
                    require(value.isoformat() == item[key], f"{name} {section}: period end mismatch at {day}")
                else:
                    label = "saldo_tras_cuota_antes_de_balloon" if section == "deuda_permanente" and key == "closing_balance" else key
                    row(section, label, value, item[key], when=day.isoformat(), pointer=f"{pointer}/{index}/{key}")

    schedule("deuda_obra", build["debt"], funding["debt_run"]["periods"], "start_date",
             "/construction_financing/debt_run/periods")
    schedule("caja_obra", build["funding"], funding["cash_by_date"], "date", "/construction_financing/cash_by_date")
    schedule("deuda_permanente", expected["schedule"], actual["permanent_loan"]["projected_schedule"], "date",
             "/permanent_loan/projected_schedule")

    capacity = actual["capacity"]
    for limit, value in expected["limits"].items():
        row("capacidad", limit, value, capacity["capacity_limits"][limit], pointer=f"/capacity/capacity_limits/{limit}")
    minimum = min(expected["limits"].values())
    require(sorted(key for key, value in expected["limits"].items() if value == minimum) == capacity["binding_limit_ids"],
            f"{name}: incorrect binding bank limit")
    refinance = actual["construction_refinance"]
    pricing = actual["valuation_and_sale"]
    permanent = actual["permanent_reserve"]
    replacement = actual["replacement_reserve"]
    sale_costs = {item["claim"]["kind"]: (index, item["computed_cost"])
                  for index, item in enumerate(pricing["sale_cost_run"]["cost_rows"])}
    for key, kind in (("variable_cost", "percent_of_gross"), ("fixed_cost", "fixed")):
        index, value = sale_costs[kind]
        row("venta", key, expected[key], value, when=expected["sale"].isoformat(),
            pointer=f"/valuation_and_sale/sale_cost_run/cost_rows/{index}/computed_cost")
    for section, key, reference, reported, pointer, unit in (
        ("capacidad", "principal_solicitado", expected["principal"], capacity["selected_principal"], "/capacity/selected_principal", "USD"),
        ("capacidad", "limite_combinado", minimum, capacity["maximum_principal_capacity"], "/capacity/maximum_principal_capacity", "USD"),
        ("capacidad", "debt_yield_observado", expected["achieved_debt_yield"], capacity["debt_yield"]["achieved"], "/capacity/debt_yield/achieved", "fraction"),
        ("refi", "valor_inmueble", expected["valuation"], pricing["refinance_value"], "/valuation_and_sale/refinance_value", "USD"),
        ("refi", "caja_previa", build["free_cash"], refinance["opening_free_cash"], "/construction_refinance/opening_free_cash", "USD"),
        ("refi", "costos", expected["refi_cost"], refinance["closing_fee"], "/construction_refinance/closing_fee", "USD"),
        ("refi", "reserva_permanente", expected["permanent_reserve"], refinance["permanent_reserve_deposit"], "/construction_refinance/permanent_reserve_deposit", "USD"),
        ("refi", "cobro_neto", expected["refinance_net"], refinance["net_equity_distribution"], "/construction_refinance/net_equity_distribution", "USD"),
        ("operacion", "reserva_reposicion", expected["replacement"], replacement["deposit"], "/replacement_reserve/deposit", "USD"),
        ("operacion", "servicio_deuda", expected["payment"], actual["dated_debt_service"]["scheduled_service_due"], "/dated_debt_service/scheduled_service_due", "USD"),
        ("operacion", "CoC_posrefi_del_tramo", expected["coc"], actual["post_refinance_coc"]["value"], "/post_refinance_coc/value", "fraction"),
        ("venta", "precio_bruto", expected["gross_sale"], pricing["gross_sale_price"], "/valuation_and_sale/gross_sale_price", "USD"),
        ("venta", "costos_totales", expected["fixed_cost"] + expected["variable_cost"], pricing["sale_cost"], "/valuation_and_sale/sale_cost", "USD"),
        ("venta", "liquidacion_principal", expected["payoff"], actual["debt_principal_paid_at_sale"], "/debt_principal_paid_at_sale", "USD"),
        ("venta", "liberacion_reserva_permanente", expected["released_permanent"], permanent["released_at_sale"], "/permanent_reserve/released_at_sale", "USD"),
        ("venta", "liberacion_reserva_reposicion", expected["released_replacement"], replacement["released_at_sale"], "/replacement_reserve/released_at_sale", "USD"),
        ("venta", "saldo_restringido_transferido", expected["replacement"] + expected["permanent_reserve"]
         - expected["released_permanent"] - expected["released_replacement"], permanent["total_restricted_transferred_to_buyer"],
         "/permanent_reserve/total_restricted_transferred_to_buyer", "USD"),
    ):
        cutoff = expected["refi"] if section in ("refi", "capacidad") else expected["sale"]
        row(section, key, reference, reported, unit=unit, when=cutoff.isoformat(), pointer=pointer)

    cash = actual["cash_per_usd_10"]
    events = expected["events"]
    require([item["event_id"] for item in cash["events"]] == list(events), f"{name}: event inventory or ordering mismatch")
    scale = 10 / events["initial"][2]
    row("por_USD_10", "factor", scale, cash["scale_factor"], unit="fraction", pointer="/cash_per_usd_10/scale_factor")
    event_categories = {"initial": "initial_capital", "refinance": "net_refinance_distribution",
                        "operating": "operating_distribution", "sale": "net_sale_distribution"}
    for index, item in enumerate(cash["events"]):
        day, kind, value = events[item["event_id"]]
        category = event_categories.get(item["event_id"], "additional_capital")
        require((day.isoformat(), kind, category) == (item["date"], item["kind"], item["category"]),
                f"{name}: wrong event metadata")
        pointer = f"/cash_per_usd_10/events/{index}/amount"
        row("caja_proyecto", item["event_id"], value, exact(item["amount"]) / exact(cash["scale_factor"]),
            when=item["date"], pointer=pointer)
        row("por_USD_10", item["event_id"], value * scale, item["amount"],
            unit="USD_per_10", when=item["date"], pointer=pointer)
    capital = sum(value for _, kind, value in events.values() if kind == "contribution") * scale
    receipts = sum(value for _, kind, value in events.values() if kind == "distribution") * scale
    for key, value in (("total_contributions", capital), ("total_distributions", receipts),
                       ("net_cash_profit", receipts - capital), ("unrecovered_after_sale", max(0, capital - receipts)),
                       ("equity_multiple", receipts / capital)):
        row("retorno", key, value, cash[key], unit="x" if key == "equity_multiple" else "USD_per_10",
            pointer=f"/cash_per_usd_10/{key}")

    dates = [day.isoformat() for day in expected["grid"]]
    require(actual["project_calendar"]["equity_dates"] == dates, f"{name}: quarterly calendar mismatch")
    annual = verify_irr(cash, dates)
    require(annual["state"] == "checked_synthetic", f"{name}: model TIR not available")
    for index, item in enumerate(annual["dated_net_flows"]):
        day = date.fromisoformat(item["date"])
        row("TIR", "flujo_trimestral_neto", expected["grid"][day] * scale, item["net"], unit="USD_per_10",
            when=item["date"], pointer=f"/D167/deduced_irr/dated_net_flows/{index}/net")
    enclosure = annual["annual_enclosure"]
    lo, hi = expected["irr"]
    model_lo, model_hi = (exact(enclosure[key]) for key in ("lower", "upper"))
    require(model_lo <= lo <= hi <= model_hi, f"{name}: independent TIR lies outside the model's exact interval")
    rows.append([name, "TIR", "anual_efectiva", "", "fraction",
                 f"[{human(lo)}, {human(hi)}]", f"[{human(model_lo)}, {human(model_hi)}]", "",
                 f"[{lo},{hi}]", f"[{model_lo},{model_hi}]", "", "CONTENIDA", "/D167/deduced_irr/annual_enclosure"])
    summary = dict(lines=len(rows), dated_events=len(events), total_contributions=human(capital),
                   total_receipts=human(receipts), sale_net_project=human(expected["sale_net"]),
                   multiple=human(receipts / capital), irr_percent=human(100 * (lo + hi) / 2))
    return rows, summary


def verify(package, reference_path):
    raw = shuffled_pdf()
    source = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                  plan_raw=PLAN.read_bytes(), evidence_raw=raw)
    case_raw, revision = CASE.read_bytes(), CURRENT.read_bytes()
    inputs = json.loads(case_raw)["rent_inputs"]
    expected = {name: calculate(source[key], inputs, name) for name, key in
                (("Base", "workbook_raw"), ("Downside", "downside_workbook_raw"))}
    write_package(case_raw, package, current_revision_raw=revision, **source)
    audit = verify_package(package, current_revision_raw=revision)
    require(audit["vigencia"] == "VIGENTE" and audit["audit_bot"] == "B16" and audit["decision"] == "PENDING",
            "Model package did not reproduce from the source files")
    model_raw = (package / "results.json").read_bytes()
    model = json.loads(model_raw)
    require(not model["deployment_enabled"] and not model["real_decisions_enabled"], "Unexpected authorization")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("escenario", "bloque", "concepto", "fecha", "unidad", "independiente", "miniuw", "diferencia",
                     "independiente_exacto", "miniuw_exacto", "diferencia_exacta", "estado", "ubicacion_en_resultado"))
    summary, rows = {}, []
    for name, reference in expected.items():
        compared, summary[name] = compare_scenario(reference, model["scenarios"][name], name)
        rows.extend(compared)
    writer.writerows(rows)
    comparison = buffer.getvalue().encode("utf-8")
    reference_path.write_bytes(comparison)
    differences = [row[:4] for row in rows if row[-2] == "DIFERENCIA"]
    require(not differences, f"Unreconciled rows: {differences}")
    return dict(status="passed", decision="PENDING", compared_rows=len(rows), exact_matches=len(rows)-len(expected),
                enclosed_irrs=len(expected), differences=len(differences), scenarios=summary,
                csv_sha256=sha256(comparison).hexdigest(), model_results_sha256=sha256(model_raw).hexdigest(),
                case_sha256=sha256(case_raw).hexdigest(), pdf_sha256=audit["pdf_sha256"], page_count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d179-") as temp:
        report = verify(Path(temp) / "D178", args.csv)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
