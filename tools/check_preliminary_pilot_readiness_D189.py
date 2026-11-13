"""Verify the frozen v1 preliminary ranking minimums on the staged pilot."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from check_operating_replay_D20 import require
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_preliminary_stages_D188 import CASE, DEAL, DATES, SCENARIOS, fixture, workbook
from miniuw_foundation.debt_service import _fraction as amount, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import build_results, encoded, verify_package, write_package
from worksheet_preliminary_D185 import SUPPORT
from worksheet_preliminary_finance_D187 import FINANCING_CELLS
from worksheet_preliminary_workbook_D186 import NUMERIC


def verify():
    case, books = fixture()
    require(CASE.read_bytes() == encoded(case), "Frozen staged pilot fixture drift")

    def run(data, inputs):
        result, pdf = build_results(encoded(data), workbook_raw=inputs.get("Base"),
                                    downside_workbook_raw=inputs.get("Downside"))
        require(result["decision"] == result["simulation_result"] == "PENDING"
                and not result["full_uw_eligible"] and not result["real_decisions_enabled"]
                and not result["deployment_enabled"], "Preliminary run left its authorized scope")
        return result, pdf

    baseline, pdf = run(case, books)
    require(baseline["state"] == "PRELIMINAR" and len(baseline["ranking"]) == 1
            and baseline["ranking"][0]["deal_id"] == DEAL, "Complete pilot did not enter the ranking")
    require("Dictamen formal PENDING" in pdf_text(pdf), "Missing formal status on the pilot PDF")
    original = baseline["deals"][DEAL]["scenarios"]
    for row in original.values():
        cash = row["cash"]
        require(amount(cash["reference_amount"]) == 10 and amount(cash["events"][0]["amount"]) == 10,
                "The pilot changed the investor reference amount")
    require(amount(baseline["ranking"][0]["downside_equity_multiple"])
            == amount(original["Downside"]["cash"]["equity_multiple"]), "Ranking used the wrong scenario or metric")

    findings = {}

    def record(name, check, data, inputs, reason=None):
        result, report = run(data, inputs)
        pair = result["deals"][DEAL]["scenarios"]
        affected, other = pair[name], next(s for s in SCENARIOS if s != name)
        require(result["state"] == "PENDING" and not result["ranking"]
                and affected["cash"] is None and affected["blockers"] and pair[other] == original[other],
                f"{name} {check}: expected exclusion with independent cash preserved")
        if reason is not None:
            require(any(reason in r for r in affected["blockers"]), f"{name} {check}: unexpected blocker")
        content = pdf_text(report)
        require("Dictamen formal PENDING" in content and f"{name} | Caja PENDING" in content
                and f"{other} | Aporte extra" in content and "Fuera del ranking" in content,
                f"{name} {check}: investor PDF did not show the exclusion")
        findings.setdefault(name, {})[check] = affected["blockers"]

    funding = (
        "convention", "requested_refinance_usd", "construction_commitment_usd", "construction_maturity_date",
        "bank_vacancy_addition_H08", "permanent_maturity_quarters_H02", "debt_yield_applicability",
        "minimum_debt_yield", "maximum_refi_equity_usd", "permanent_reserve_sale_release_fraction",
        "construction_stages",
    )
    supplemental = {
        "program": ("units",),
        "acquisition_and_costs": ("parking_spaces", "scope"),
        "rent_and_expenses": ("scope",),
        "calendar": ("lease_up_carry_usd_per_quarter",),
        "exit": ("reserve_at_sale",),
        "financing": funding,
    }

    for name in SCENARIOS:
        for cell in ("B3", "E3", "C7", "C34", *NUMERIC, *FINANCING_CELLS):
            modified = workbook(name, {cell: {}})
            updated = deepcopy(case)
            updated["scenarios"][name]["workbook_sha256"] = sha(modified)
            record(name, f"Inputs!{cell} vacío", updated, books | {name: modified},
                   reason=None if cell in ("B3", "E3") else cell)

        record(name, "XLSX ausente", case, {key: raw for key, raw in books.items() if key != name}, "planilla")
        updated = deepcopy(case)
        updated["scenarios"].pop(name)
        record(name, "Escenario ausente", updated, books, "planilla")
        updated = deepcopy(case)
        updated["scenarios"][name].pop("workbook_sha256")
        record(name, "Huella ausente", updated, books, "huella")

        for group in SUPPORT:
            updated = deepcopy(case)
            updated["scenarios"][name]["support"].pop(group)
            record(name, f"Respaldo {group} ausente", updated, books)
            for field in ("source_ref", "owner", "as_of", "summary", *supplemental[group]):
                updated = deepcopy(case)
                updated["scenarios"][name]["support"][group].pop(field)
                record(name, f"{group}.{field} ausente", updated, books)

        for i, row in enumerate(case["scenarios"][name]["support"]["financing"]["construction_stages"]):
            for field in row:
                updated = deepcopy(case)
                updated["scenarios"][name]["support"]["financing"]["construction_stages"][i].pop(field)
                record(name, f"Etapa {i + 1}.{field} ausente", updated, books, "etapa")

    def downside_variant(label, term_change, reason):
        changed = deepcopy(case)
        term_change(changed["scenarios"]["Downside"]["support"]["financing"])
        record("Downside", label, changed, books, reason)

    downside_variant("Disponibilidad insuficiente en etapa 1",
                     lambda t: t["construction_stages"][0].update(available_draw_usd=rational(29_999)), "disponibilidad")
    downside_variant("Compromiso de obra insuficiente", lambda t: t.update(construction_commitment_usd=rational(69_999)),
                     "compromiso")
    downside_variant("Solicitud por encima de capacidad de refi",
                     lambda t: t.update(requested_refinance_usd=rational(82_000)), "capacidad")
    downside_variant("Fuente de una etapa posterior al corte",
                     lambda t: t["construction_stages"][0].update(as_of=DATES[0]), "respaldo")

    modified = workbook("Downside", {"C75": {}})
    corrected = workbook("Downside", {"C75": {"value": "0"}})
    require(modified != corrected and corrected == books["Downside"], "The explicit zero did not restore the exact fixture")
    with TemporaryDirectory(prefix="miniuw-d189-") as directory:
        folder = Path(directory) / "pilot"
        write_package(encoded(case), folder, workbook_raw=books["Base"], downside_workbook_raw=corrected)
        audit = verify_package(folder)
        require(audit["decision"] == "PENDING" and audit["state"] == "PRELIMINAR"
                and (folder / "MiniUW_Resumen.pdf").read_bytes() == pdf
                and (folder / "results.json").read_bytes() == encoded(baseline), "Corrected pilot did not reproduce")

    return dict(status="passed", decision="PENDING", state="PRELIMINAR",
                pdf_sha256=sha(pdf), usd10_verified=True, exact_replay_after_explicit_zero=True,
                ranked_deals_complete=1, checks=sum(map(len, findings.values())), blockers_by_scenario=findings)


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True))
