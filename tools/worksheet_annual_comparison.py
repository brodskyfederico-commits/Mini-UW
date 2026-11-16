"""Compare two audited annual sale paths across Base and Downside."""

from hashlib import sha256
from itertools import product

from check_reference_package import require
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import SCENARIOS, encode
from miniuw_worksheet_v1 import (_audit_package, publish_current_pdf, read_current_revision,
                                require_delivery_evidence, require_pdf_destination)
from worksheet_annual_coc import quantity as amount
from worksheet_annual_route_report import STAGES, dated_cash, usd
from worksheet_lorena_annual_route import route_cash_story
from worksheet_revision_D128 import audit_revision


ROUTES = (
    ("Con refi", "interest_only_then_amortize", "annual_post_refi_coc"),
    ("Sin refi", "sell_without_refinance", "annual_without_refi"),
)


def annual_cash(result, labels):
    table = {}
    for name in SCENARIOS:
        terms_by_route = {}
        for label, (caption, mode, annual_key) in zip(labels, ROUTES, strict=True):
            route = result.get("calendar_checks", {}).get(name, {}).get(label, {})
            require(route.get("state") == "calculated_synthetic" and route.get("route") == mode
                    and annual_key in route,
                    f"Caja anual PENDING para {name} {caption.lower()} ({route.get('blocker') or 'ruta anual faltante'})")
            construction = [row for row in route["cash_by_period"] if row["stage"] == "construction"]
            refinance = [row["date"] for row in route["cash_by_period"] if row["stage"] == "refinance"]
            require(len(refinance) == (1 if annual_key == "annual_post_refi_coc" else 0),
                    f"Cierre de refinanciación no conciliado para {name}")
            upfront = amount(construction[0]["contribution"])
            require(upfront is not None and upfront > 0, f"Equity inicial PENDING para {name}")
            route_cash_story(route, rational(10 / upfront))
            cash = route["cash_per_usd_10"]
            table[name, caption] = dict(cash_per_usd_10=cash, cash_sha256=sha256(encode(cash)).hexdigest(),
                                        refinance_date=refinance[0] if refinance else None, sale_date=route["sale"]["date"])
            terms = route["debt"]
            terms_by_route[caption] = (
                construction, route[annual_key].get("window_start"), route[annual_key].get("window_end"),
                {when: amount(item["value"]) for when, item in terms["quarterly_noi_source"].items()},
                amount(route[annual_key].get("noi_after_reserves")),
                amount(terms["forward_noi_source"]["value"]),
                *(route["sale"][field] for field in ("date", "gross", "cost")),
            )
        require(terms_by_route["Con refi"] == terms_by_route["Sin refi"],
                f"Comparación PENDING para {name}: conciliá obra, NOI y fecha, precio y costos de salida")
    return table


def comparison_lines(table):
    columns = tuple(product(SCENARIOS, (route[0] for route in ROUTES)))
    ledgers = [dated_cash(table[key]) for key in columns]
    totals = [table[key]["cash_per_usd_10"] for key in columns]
    order = list(STAGES)
    days = sorted(set().union(*ledgers), key=lambda key: (key[0], order.index(key[1])))

    def row(label, cells, bold=False):
        return (f"{label:<30} | " + " | ".join(f"{cell:^19}" for cell in cells), bold)

    def receipts(ledger, stage):
        return usd(sum(balance[1] for (_, kind), balance in ledger.items() if kind == stage))

    lines = [
        ("Ensayo sintético | 1101 real, retorno histórico y retorno personal PENDING", True),
        ("USD por cada USD 10 de equity inicial del proyecto. Igual obra, NOI y venta dentro de cada escenario.", False),
        row("Totales por ruta", (f"{name} {caption.lower()}" for name, caption in columns), True),
        row("Aporte inicial", ("10,00",) * 4),
        row("Aportes adicionales", (usd(amount(cash["additional"])) for cash in totals)),
        row("Total aportado", (usd(10 + amount(cash["additional"])) for cash in totals)),
        row("Cobro por refi", (receipts(ledger, "refinance") if table[key]["refinance_date"] is not None else "N/A"
                              for key, ledger in zip(columns, ledgers, strict=True))),
        row("Cobros de operación", (receipts(ledger, "operation") for ledger in ledgers)),
        row("Cobro neto de venta", (receipts(ledger, "sale") for ledger in ledgers)),
        row("Cobro total", (usd(amount(cash["received"])) for cash in totals), True),
        row("Saldo sin recuperar", (usd(amount(cash["unrecovered"])) for cash in totals), True),
        row("Fecha y movimiento", ("Aporta / Cobra",) * 4, True),
    ]
    for when, stage in days:
        cells = (" / ".join(f"{usd(v):>8}" for v in ledger[when, stage]) if (when, stage) in ledger else "—"
                 for ledger in ledgers)
        lines.append(row(f"{when} {STAGES[stage]}", cells))
    lines.append(("— indica que no hay movimiento. Los totales se redondean después de sumar los importes exactos.", False))
    return lines


def audited_annual_comparison(directory, current_revision, labels):
    revision = read_current_revision(current_revision, directory)
    files, result = _audit_package(directory)
    require(result["decision"] == "PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"],
            "La comparación requiere un expediente sintético")
    review = audit_revision(result, revision)
    require(review["vigencia"] == "VIGENTE", "La revisión no está vigente")
    require_delivery_evidence(result)
    return files, revision, review["current_revision"], annual_cash(result, labels)


def deliver_annual_comparison(directory, output, current_revision, labels):
    require_pdf_destination(directory, output, current_revision)
    files, revision, case_revision, table = audited_annual_comparison(directory, current_revision, labels)
    pdf = render_page(case_revision, comparison_lines(table), 11.4,
                      "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                      "Comparación anual | Base y Downside, con y sin refinanciación")
    publish_current_pdf(directory, files, current_revision, revision, output, pdf)
    return dict(decision="PENDING", page_count=1, current_revision=case_revision,
                revision_sha256=sha256(revision).hexdigest(), source_results_sha256=sha256(files["results.json"]).hexdigest(),
                pdf_sha256=sha256(pdf).hexdigest(), route_labels=dict(with_refinance=labels[0], without_refinance=labels[1]),
                scenarios={name: {caption: table[name, caption] for caption, _, _ in ROUTES} for name in SCENARIOS})
