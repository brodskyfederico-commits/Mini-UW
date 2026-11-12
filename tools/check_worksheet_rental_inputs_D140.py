"""Check exact rent, NOI and dated equity cash against independent arithmetic."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call
from check_worksheet_native_mapping_D139 import example_values
from inputsheet_fixture import native_workbook
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import WORKBOOK_RENTAL_INPUTS_SCHEMA, encoded
from plan_return_D107 import OPERATING_PERIOD
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_rental_inputs_D140 import METRIC, PERIOD
from worksheet_revision_D128 import snapshot_for_case


CASE = ROOT / "templates/synthetic-workbook-rental-inputs-D140.json"
CURRENT = ROOT / "templates/synthetic-workbook-current-revision-D140.json"
BOOKS = {name: ROOT / f"templates/synthetic-rental-{name.lower()}-D140.xlsx" for name in SCENARIOS}
DEAL = "SYNTHETIC-D140-rental-return"
AS_OF = "2027-03-01T00:00:00Z"
NUMBERS = {"Base": ("1200", "1500", "1900", "2400", "35", "0.05", "0.02"),
           "Downside": ("1100", "1375", "1620", "1980", "25", "0.20", "0.05")}
NUMERIC_CELLS = ("C8", "C9", "C10", "C11", "C13", "C14", "C15")


def workbook_values(name, catalog):
    return example_values(name, catalog) | {"B3": {"text": DEAL}, "E3": {"text": AS_OF},
            "C12": {"text": f"SYNTHETIC-D140-{name}-survey"}} | {
                cell: {"value": value} for cell, value in zip(NUMERIC_CELLS, NUMBERS[name], strict=True)}


def case_for(books, catalog):
    hashes = {name: sha(raw) for name, raw in books.items()}
    sources = {name: dict(workbook_sha256=digest, source_ref=f"SYNTHETIC-D140-{name}-field-review",
                         confirmed_fields=[row["field_id"] for row in catalog], not_applicable_fields=[])
               for name, digest in hashes.items()}
    inputs = dict(deal_id=DEAL, as_of_UTC=AS_OF, currency="USD", financing_profile="SYNTHETIC-D108",
                  cost_source_ref="SYNTHETIC-D140-fixed-construction-budget", construction_cost=rational(3250000),
                  requested_principal=rational(1400000), exit_cap=rational(Fraction(9, 100)),
                  groups={name: dict(units=count, rentable_sf_per_unit=rational(area),
                                     source_ref=f"SYNTHETIC-D140-program-{name}")
                          for name, count, area in (("studio", 4, 500), ("1BR", 12, 625), ("2BR", 8, 900), ("3BR", 2, 1100))},
                  policy=dict(source_ref="SYNTHETIC-D140-gross-rent-policy", rent_definition="gross_before_losses_and_concessions",
                              concession_basis="gross_potential_rent", bank_vacancy_addition=rational(Fraction(1, 20)),
                              other_income_basis="explicit_eligible_units_excluding_rent_losses_and_management"),
                  other_income=dict(eligible_units=20, source_ref="SYNTHETIC-D140-eligible-units"),
                  annual_expenses=dict(unit_opex=rational(600), fixed_opex=rational(10800), management=rational(Fraction(1, 20)),
                                       property_tax=rational(12000), source_ref="SYNTHETIC-D140-explicit-expense-budget"),
                  rent_comps={name: dict(literal=f"SYNTHETIC-D140-{name}-survey", observed_on="2027-02-01",
                                        source_ref=f"SYNTHETIC-D140-{name}-comps-record") for name in SCENARIOS})
    rules = [dict(scenario_id=name, metric_id=METRIC, definition_ref="SYNTHETIC-D51-gross-dated-cash-window",
                  unit="multiple", period_ref=PERIOD,
                  pass_condition=dict(operator=">=", threshold=rational(1)),
                  fail_condition=dict(operator="<", threshold=rational(1))) for name in SCENARIOS]
    return dict(schema=WORKBOOK_RENTAL_INPUTS_SCHEMA, local_sources={"revision": "SYNTHETIC-D140-input-r1"},
                workbook_sha256=hashes, native_mapping=dict(catalog_sha256=sha(encoded(catalog)), scenarios=sources),
                rent_inputs=inputs, criteria_revision="SYNTHETIC-D140-criteria-r1", rules=rules,
                aggregation_rule="all_pass_any_fail_pending_blocks")


def run(case, books, revision, output):
    status = call("run", case, "--workbook", books["Base"], "--downside-workbook", books["Downside"],
                  "--current-revision", revision, "--output", output)
    result = json.loads((output / "results.json").read_bytes())
    pdf = output / "MiniUW_Resumen.pdf"
    page, = PdfReader(pdf).pages
    require(status["simulation_result"] == result["simulation_result"]
            and result["decision"] == "PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"]
            and sha(pdf.read_bytes()) == result["pdf_sha256"] == status["pdf_sha256"]
            and f"Simulación por múltiplo de equity | {result['simulation_result']}" in page.extract_text(),
            "The one-page result did not preserve its source and decision guard")
    return result


def verify_cash(view, gross, effective, other):
    expense = 26 * 600 + 10800 + effective / 20
    noi = effective + other - expense - 12000
    evidence = view["noi_by_period"][OPERATING_PERIOD]
    require([amount(evidence[k]) for k in ("gross_rent", "effective_rent", "other_income", "operating_expenses_excluding_tax", "noi")]
            == [gross, effective, other, expense, noi], "Gross rent, loss allocation or NOI differs from the independent arithmetic")
    payment = 1400000 * Fraction(1, 80) / (1 - Fraction(81, 80) ** -40)
    payoff = 1400000 - payment + 17500
    sale = noi / Fraction(9, 100) * Fraction(95, 100) - payoff
    scale = Fraction(1, 240000)
    cash = view["cash_per_usd_10"]
    expected = [("2027-03-30", 10), ("2027-06-30", 850000 * scale), ("2028-03-30", 1372000 * scale),
                ("2028-06-30", 0), ("2028-06-30", (noi - payment) * scale), ("2028-06-30", sale * scale)]
    require(cash["basis_event_ids"] == ["initial"] and amount(cash["basis_amount"]) == 2400000
            and [(event["date"], amount(event["amount"])) for event in cash["events"]] == expected
            and amount(cash["unrecovered_after_sale"]) == max(0, (3250000 - 1372000 - noi + payment - sale) * scale),
            "The worksheet-to-NOI change did not reach the dated USD 10 ledger exactly")


def verify(temp, saved_output):
    catalog = mapping_catalog()
    values = {name: workbook_values(name, catalog) for name in BOOKS}
    originals = {name: native_workbook(cells) for name, cells in values.items()}
    require(all(BOOKS[name].read_bytes() == raw for name, raw in originals.items()), "Fixture drift")
    output = saved_output or temp / "matching"
    matching = run(CASE, BOOKS, CURRENT, output)
    require(matching["simulation_result"] == "PASS" and not matching["revision_review"]["blockers"], "Synthetic rules did not clear")
    scenarios = matching["scenarios"]
    verify_cash(scenarios["Base"], 513600, Fraction(477648), 8400)
    verify_cash(scenarios["Downside"], 453840, Fraction(340380), 6000)
    for view in scenarios.values():
        require(set(view["cell_sources"]) == {f"C{index}" for index in range(7, 16)}, "Lost a rental-cell citation")
    audit = call("audit", output, "--current-revision", CURRENT)
    require(audit["vigencia"] == "VIGENTE" and audit["simulation_result"] == "PASS", "Audit could not replay the sheet-driven cash")

    def variant(name, edits=None, patch=None):
        books = originals.copy()
        if edits:
            books["Downside"] = native_workbook(values["Downside"] | edits)
        case = case_for(books, catalog)
        if patch:
            patch(case)
        case_path = temp / f"{name}.json"
        revision = temp / f"{name}-revision.json"
        paths = {scenario: temp / f"{name}-{scenario}.xlsx" for scenario in books}
        for scenario, raw in books.items():
            paths[scenario].write_bytes(raw)
        case_path.write_bytes(encoded(case))
        revision.write_bytes(encoded(snapshot_for_case(case, f"SYNTHETIC-D140-{name}")))
        return run(case_path, paths, revision, temp / name)

    per_sf = variant("rent-by-sf", {"C7": {"text": "PER SF"}, "C8": {"value": "2.2"}, "C9": {"value": "2.2"},
                                    "C10": {"value": "1.8"}, "C11": {"value": "1.8"}})
    verify_cash(per_sf["scenarios"]["Downside"], 453840, Fraction(340380), 6000)
    zero = variant("explicit-zero-other-income", {"C13": {"value": "0"}})
    verify_cash(zero["scenarios"]["Downside"], 453840, Fraction(340380), 0)
    vacancy = variant("vacancy-reduced", {"C14": {"value": "0.05"}})
    verify_cash(vacancy["scenarios"]["Downside"], 453840, Fraction(408456), 6000)
    changed_basis = variant("concession-after-vacancy", patch=lambda case: case["rent_inputs"]["policy"].update(
                             concession_basis="after_vacancy_rent"))
    verify_cash(changed_basis["scenarios"]["Downside"], 453840, Fraction(3449184, 10), 6000)

    def pending(name, *, keep_cash=False, **kwargs):
        result = variant(name, **kwargs)
        require(result["simulation_result"] == "PENDING" and
                (result["scenarios"]["Downside"]["cash_per_usd_10"] is not None) == keep_cash,
                "An unresolved cell, source or criterion released a result")
        return result

    for field in ("INPUT_C9", "INPUT_C12"):
        blocked = pending(f"unconfirmed-{field}", patch=lambda case: case["native_mapping"]["scenarios"]["Downside"]
                          ["confirmed_fields"].remove(field))
        require(blocked["scenarios"]["Base"] == scenarios["Base"]
                and f"B04:Downside:{field}:field_confirmation_missing" in blocked["screening"]["simulation_blockers"],
                "A missing confirmation withdrew unrelated cash or lost its cell")
    pending("criterion-missing", keep_cash=True, patch=lambda case: case["rules"].pop())
    pending("concession-basis-missing", patch=lambda case: case["rent_inputs"]["policy"].pop("concession_basis"))
    pending("comps-reference-mismatch", edits={"C12": {"text": "SYNTHETIC-other-survey"}})
    capacity = pending("capacity-blocked", edits={"C14": {"value": "0.35"}})
    require(amount(capacity["scenarios"]["Downside"]["noi_by_period"][OPERATING_PERIOD]["noi"]) > 0
            and "selected_principal_exceeds_declared_bank_capacity" in capacity["scenarios"]["Downside"]["blockers"],
            "The lower NOI bypassed bank capacity or hid an available accrual")
    return dict(status="passed", decision="PENDING", full_workbook_cases=11, pending_cases=6,
                worksheet_cells=9, scenarios_verified=2, pdf_sha256=matching["pdf_sha256"], page_count=1,
                vacancy_probe_cash=vacancy["scenarios"]["Downside"]["cash_per_usd_10"]["total_distributions"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Keep the audited synthetic rent case.")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d140-") as temp:
        print(json.dumps(verify(Path(temp), args.output), sort_keys=True))


if __name__ == "__main__":
    main()
