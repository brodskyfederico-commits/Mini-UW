"""Reproduce D197 acceptance on a local source-first synthetic worksheet."""
from argparse import ArgumentParser
from collections import defaultdict
from copy import deepcopy
from datetime import date
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_lorena_criteria_D192 import change_cells
from check_reference_package import require
from check_worksheet_definition_screening_D193 import approvals_unchanged, detail, rows
from check_worksheet_formula_review_D173 import pdf_text
from check_worksheet_lorena_screening_D194 import CASE_FILE, FIXTURE
from check_worksheet_market_evidence_D166 import BOOKS, PLAN, shuffled_pdf
from check_worksheet_preferred_lp_gp_D169 import TERMS, waterfall
from check_worksheet_reconciliation_D179 import compare_scenario
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import (
    CURRENT_REVISION_FILE, WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA, encoded, read_package, verify_package,
)
from plan_return_D107 import OPERATING_PERIOD
from reconcile_worksheet_D179 import calculate, exact
from worksheet_calendar_routes_D199 import route_cash
from worksheet_definition_screening_D193 import OCCUPANCY, PHYSICAL, RLV
from worksheet_documented_finance_D147 import review_documents
from worksheet_intake_D198 import SOURCES, assemble, read_source_directory, register
from worksheet_local_sources_D127 import number
from worksheet_native_mapping_D139 import SCENARIOS, mapping_catalog
from worksheet_performance_policy_D184 import AFTER_RESERVES, BEFORE_RESERVES
from worksheet_project_calendar_D145 import offset


def settings_for_acceptance():
    settings = json.loads(CASE_FILE.read_bytes())
    settings["schema"] = WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA
    # The assembler binds each file at intake. Policies and source confirmations remain explicit.
    settings.pop("workbook_sha256")
    local = settings["local_sources"]
    local.pop("workbook_sha256")
    for key in ("plan_pdf", "evidence_pdf"):
        local[key].pop("sha256")
    settings["criteria_workbook"].pop("sha256")
    inputs = settings["rent_inputs"]
    downside = inputs["supplemental_scope"]["Downside"]["downside_scope"]
    for key in ("base_workbook_sha256", "downside_workbook_sha256"):
        downside.pop(key)
    inputs["calendar_checks"] = {}
    inputs["criterion_noi_contexts"] = {}
    for name in SCENARIOS:
        settings["native_mapping"]["scenarios"][name].pop("workbook_sha256")
        definition = inputs["definition_screening"][name]
        definition["rlv"]["binding_yields"] = [definition["rlv"].pop("yield_metric")]
        inputs["post_refinance_coc"][name]["noi_basis"] = AFTER_RESERVES
        inputs["criterion_noi_contexts"][name] = {
            item["metric_id"]: dict(noi_basis=AFTER_RESERVES, period_ref=item["period_ref"]) for item in settings["rules"]
            if item["scenario_id"] == name and item["metric_id"] in {"YoC", "spread", OCCUPANCY, "post_refi_CoC"}
        }
        cash_date = date.fromisoformat(inputs["supplemental_scope"][name]["sale_date"]["value"])
        sale_date = offset(cash_date, 3)
        start = offset(sale_date.replace(day=1), 1)
        no_tax = dict(applicability="no_incremental_tax_in_variant", source_ref=f"SYNTHETIC-D199-{name}-baseline-tax-scope")
        tax = dict(year=2028, paid_on="2028-03-30", land_value=rational(Fraction("1000000")), school_rate=rational(Fraction("0.004")),
                   non_school_rate=rational(Fraction("0.006")), source_ref="SYNTHETIC-D199-tax-cutoff-evidence",
                   improvements=[
                       dict(id="SYNTHETIC-D199-part-A", usable_on="2027-12-31", value=rational(Fraction("200000")),
                            source_ref="SYNTHETIC-D199-A-usable"),
                       dict(id="SYNTHETIC-D199-part-B", usable_on="2028-01-01", value=rational(Fraction("300000")),
                            source_ref="SYNTHETIC-D199-B-usable"),
                       dict(id="SYNTHETIC-D199-part-C", usable_on="2028-01-02", value=rational(Fraction("400000")),
                            source_ref="SYNTHETIC-D199-C-usable"),
                   ])
        inputs["calendar_checks"][name] = dict(
            sell_without_refinance=dict(route="sell_without_refinance",
                source_ref=f"SYNTHETIC-D199-{name}-sell-with-existing-construction-debt",
                construction_tax=tax if name == "Downside" else no_tax),
            interest_only_then_amortize=dict(route="interest_only_then_amortize",
                source_ref=f"SYNTHETIC-D199-{name}-interest-only-then-amortize", interest_only_payments=1,
                amortization_clock="count_interest_only_inside_original_amortization", sale_payment_index=2,
                requested_principal=dict(value=rational(1_400_000 if name == "Base" else 1_350_000),
                                         source_ref=f"SYNTHETIC-D199-{name}-explicit-phased-loan-request"),
                construction_tax=tax if name == "Downside" else no_tax,
                delayed_forward_noi=dict(value=rational(390_000 if name == "Base" else 200_000),
                    noi_basis=BEFORE_RESERVES, period_ref=f"{start}/{offset(start, 12)}",
                    source_ref=f"SYNTHETIC-D199-{name}-later-forward-noi"),
                intermediate_net_operating_cash={sale_date.isoformat(): dict(
                    value=rational(Fraction("24000")), source_ref=f"SYNTHETIC-D199-{name}-additional-dated-net-cash")}),
        )
    return settings


def source_files(directory):
    directory.mkdir()
    data = dict(workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes(),
                plan_raw=PLAN.read_bytes(), evidence_raw=shuffled_pdf(), criteria_raw=FIXTURE.read_bytes())
    for argument, filename in SOURCES.items():
        (directory / filename).write_bytes(data[argument])
    return read_source_directory(directory)


def cash_summary(cash):
    if cash is None:
        return None
    events = [dict(date=row["date"], category=row["category"], usd=round(float(exact(row["amount"])), 2))
              for row in cash["events"] if exact(row["amount"])]
    return dict(events=events, received=round(float(exact(cash["total_distributions"])), 2),
                additional=round(float(exact(cash["total_contributions"]) - 10), 2),
                unrecovered=round(float(exact(cash["unrecovered_after_sale"])), 2))


def verify_periods(view):
    funding = view["construction_financing"]
    amounts = [exact(row["opening_free_cash"]) + exact(row["loan_draw"]) + exact(row["equity_contribution"])
               == sum(exact(row[key]) for key in ("project_uses", "origination_fee_paid", "interest_paid", "closing_free_cash"))
               for row in funding["cash_by_date"]]
    require(all(amounts), "Construction does not balance")
    require(all(prior["closing_free_cash"] == next_row["opening_free_cash"]
                for prior, next_row in zip(funding["cash_by_date"], funding["cash_by_date"][1:])), "Cash discontinuity")
    refi = view["construction_refinance"]
    reserve = view["replacement_reserve"]
    permanent = view["permanent_reserve"]
    cash = view["cash_per_usd_10"]
    scale = exact(cash["scale_factor"])
    events = {row["event_id"]: exact(row["amount"]) / scale for row in cash["events"]}
    require(sum(exact(refi[key]) for key in ("gross_proceeds", "opening_free_cash", "projected_cash_in_required")) ==
            sum(exact(refi[key]) for key in ("prior_principal_paid", "closing_fee", "closing_restricted_cash",
                                           "net_equity_distribution")), "Refinance sources and uses differ")
    require(refi["opening_free_cash"] == funding["cash_by_date"][-1]["closing_free_cash"]
            and refi["closing_restricted_cash"] == permanent["opening_at_sale"], "Cash carried into refinance or sale differs")
    noi = exact(view["noi_by_period"][OPERATING_PERIOD]["noi"])
    service = exact(view["dated_debt_service"]["scheduled_service_due"])
    require(noi + events["operating-funding"] == service + exact(reserve["deposit"]) + events["operating"],
            "Operating sources and uses differ")
    require(exact(view["gross_sale"]) + exact(permanent["total_restricted_before_sale"]) ==
            exact(view["valuation_and_sale"]["sale_cost"]) + exact(view["debt_principal_paid_at_sale"]) +
            events["sale"] + exact(permanent["total_restricted_transferred_to_buyer"]), "Sale sources and uses differ")
    return len(amounts) + 3


def verify_allocation(view, irr, terms):
    allocated = waterfall(dict(cash_per_usd_10=view["cash_per_usd_10"], irr=irr), terms)
    dates = defaultdict(lambda: [Fraction(), Fraction()])
    for row in allocated["reconciliation"]["events"]:
        if row["event"]["kind"] == "distribution":
            matched = dates[row["event"]["date"]]
            matched[0] += sum(map(exact, row["allocated"].values()))
            matched[1] += exact(row["event"]["amount"])
    require(dates and all(lp_gp == distributed for lp_gp, distributed in dates.values()),
            "LP plus GP differs from dated distributable cash")
    return dict(reconciled_dates=sorted(dates), participants=allocated["participants"])


def verify_neighbors(record):
    calc = record["calculation"]
    require(record["state"] == "calculated_synthetic", "RLV bound unresolved")
    passing = calc["pass_boundary"]
    failing = calc["before_fail_boundary"]
    require(passing["below"]["state"] == passing["at"]["state"] == "PASS"
            and passing["above"]["state"] != "PASS", "Invalid upper PASS boundary")
    require(failing["below"]["state"] != "FAIL" and failing["at"]["state"] != "FAIL"
            and failing["above"]["state"] == "FAIL", "Invalid first formal FAIL boundary")
    return dict(last_pass=passing["price"], last_before_fail=failing["price"])


def verify_calendar(model, settings):
    results = {}
    for name, view in model["scenarios"].items():
        variants = model["calendar_checks"][name]
        phased = variants["interest_only_then_amortize"]
        sale_only = variants["sell_without_refinance"]
        require(phased["state"] == sale_only["state"] == "calculated_synthetic", f"Calendar route blocked: {name}: {variants}")
        loan = view["permanent_loan"]
        principal = exact(phased["debt"]["requested_principal"]["value"])
        rate = exact(loan["periodic_rate"])
        interest, amortizing = phased["debt"]["schedule"]
        months = loan["amortization_payments"] - 1
        payment = principal / months if rate == 0 else principal * rate / (1 - (1 + rate) ** -months)
        require(exact(interest["closing"]) == exact(interest["opening"]) == principal
                and exact(interest["service"]) == principal * rate and exact(interest["principal"]) == 0
                and exact(amortizing["service"]) == payment and exact(amortizing["interest"]) == principal * rate
                and exact(amortizing["closing"]) == principal - payment + principal * rate
                and amortizing["date"] == phased["sale"]["date"], "Interest-only transition or sale payoff invalid")
        held = view["construction_financing"]
        payoff = exact(held["construction_principal_payoff"])
        require(all(row["stage"] != "refinance" for row in sale_only["cash_by_period"])
                and exact(sale_only["sale"]["principal_paid"]) == payoff
                and sale_only["sale"]["date"] == view["project_calendar"]["sale_date"]
                and exact(sale_only["debt"]["schedule"][0]["interest"]) == payoff * exact(
                    held["debt_source"]["periods"][-1]["interest_fraction"]["value"]),
                "No-refinance route lost construction debt or its final interest")
        route_summary = {}
        for mode, route in variants.items():
            flows = route["cash_per_usd_10"]
            scale = exact(view["cash_per_usd_10"]["scale_factor"])
            ledger = route["cash_by_period"]
            require(exact(ledger[0]["contribution"]) * scale == 10, "Initial USD 10 basis changed")
            require(sum(exact(row["distribution"]) for row in ledger) * scale == exact(flows["received"])
                    and sum(exact(row["contribution"]) for row in ledger) * scale == 10 + exact(flows["additional"]),
                    "Route cash does not match ledger or normalization")
            for row in ledger:
                require(sum(exact(row[key]) for key in ("opening_free", "opening_restricted", "sources"))
                        == sum(exact(row[key]) for key in ("uses", "closing_free", "closing_restricted")),
                        "Route sources and uses differ")
            route_summary[mode] = dict(
                last_receipt=route["sale"]["date"],
                additional=round(float(exact(flows["additional"])), 2),
                received=round(float(exact(flows["received"])), 2),
                unrecovered=round(float(exact(flows["unrecovered"])), 2),
            )
        results[name] = route_summary

    config = settings["rent_inputs"]["calendar_checks"]["Downside"]["sell_without_refinance"]
    calculated = model["calendar_checks"]["Downside"]["sell_without_refinance"]["tax"]
    require([row["included"] for row in calculated["improvements"]] == [True, True, False]
            and exact(calculated["assessed_value"]) == 1_500_000 and exact(calculated["school"]) == 6_000
            and exact(calculated["non_school"]) == 9_000 and exact(calculated["total"]) == 15_000,
            "Tax at Jan 1 must preserve land and include only usable improvement portions")
    charged = sum(number(row.get("preopening_tax")) or 0 for row in
                  model["calendar_checks"]["Downside"]["sell_without_refinance"]["cash_by_period"])
    require(charged == 15_000, "Confirmed synthetic tax did not reach cash")
    oversize = deepcopy(settings["rent_inputs"]["calendar_checks"]["Downside"]["interest_only_then_amortize"])
    oversize["requested_principal"]["value"] = rational(1_400_000)
    blocked_capacity = route_cash(model["scenarios"]["Downside"], oversize)
    require(blocked_capacity["state"] == "PENDING" and blocked_capacity["cash_per_usd_10"] is None
            and blocked_capacity["blocker"] == "selected_principal_exceeds_declared_bank_capacity",
            "Phased refinance exceeded bank capacity")
    missing = deepcopy(config)
    missing["construction_tax"]["improvements"][1].pop("usable_on")
    blocked = route_cash(model["scenarios"]["Downside"], missing)
    require(blocked["state"] == "PENDING" and blocked["cash_per_usd_10"] is None
            and blocked["blocker"] == "substantial_completion_date_or_value_unconfirmed", "Undocumented completion produced cash")
    return results


def verify(output):
    settings = settings_for_acceptance()
    published = CASE_FILE.with_name("synthetic-acceptance-settings-D200.json")
    require(published.read_bytes() == encoded(settings), "Published acceptance settings drift")
    output.mkdir(exist_ok=True)
    sources = source_files(output / "sources")
    terms = json.loads(TERMS.read_bytes())
    registration = register(sources, "SYNTHETIC-D200-complete")

    def run(label, config, files, receipt, expected, *, audit=True):
        path = output / label
        report = assemble(config, receipt, files, path)
        require(report["simulation_result"] == expected, f"{label}: unexpected disposition {report}")
        saved = read_package(path)
        model = json.loads(saved["results.json"])
        approvals_unchanged(model)
        pdf = pdf_text(saved["MiniUW_Resumen.pdf"])
        require(f"Dictamen simulado {expected}" in pdf and "Decisión real PENDING" in pdf, f"{label}: PDF differs")
        if audit:
            verified = verify_package(path, current_revision_raw=saved[CURRENT_REVISION_FILE])
            require(verified["audit_bot"] == "B16" and verified["simulation_result"] == expected,
                    f"{label}: unsuccessful source-first audit")
        return model, report, saved

    complete, _, saved = run("complete", settings, sources, registration, "PASS")
    repeated = run("repeat", settings, sources, registration, "PASS", audit=False)[2]
    require(saved == repeated, "Identical inputs and registration produced different files")

    adverse = dict(sources, criteria_raw=change_cells(sources["criteria_raw"], {"G11": "<= 50 %", "H11": "> 65 %"}))
    adversarial, _, _ = run("adverse", settings, adverse, register(adverse, "SYNTHETIC-D200-adverse"), "FAIL")
    require(rows(adversarial)["Downside", OCCUPANCY]["state"] == "FAIL_CONDITION", "Adverse Downside did not fail")

    # Keep the original registration for this edit to test change location and recalculation blocking.
    from check_worksheet_alternatives_D155 import workbook_values
    from inputsheet_fixture import native_workbook
    changed = native_workbook(workbook_values("Downside", mapping_catalog()) | {"C70": {"value": "9"}})
    tampered = dict(sources, downside_workbook_raw=changed)
    stale, report, stale_files = run("changed-source", settings, tampered, registration, "PENDING", audit=False)
    require(report["source_blockers"] == [dict(file="Downside_Inputs.xlsx", cells=["C70"],
                blocker="registered_source_mismatch")] and stale["scenarios"]["Downside"]["cash_per_usd_10"] is None,
            "Changed input did not block with exact file and cell")
    stale_audit = verify_package(output / "changed-source", current_revision_raw=stale_files[CURRENT_REVISION_FILE])
    require(stale_audit["vigencia"] == "PENDING" and
            "Downside:native_workbook_missing_or_unbound" in stale_audit["revision_blockers"],
            "B16 recognized a stale worksheet as current")

    blanks = dict(sources, criteria_raw=change_cells(sources["criteria_raw"], {"F14": "", "H14": "", "G11": ""}))
    incomplete, _, incomplete_files = run("incomplete", settings, blanks,
                                          register(blanks, "SYNTHETIC-D200-incomplete"), "PENDING")
    for name in SCENARIOS:
        require(detail(incomplete, name, RLV)["blocker"] == "SRC-03_incompatible_or_missing_criterion:equity_TDC",
                f"{name}: RLV passed without its FAIL hurdle")
    require("pass_condition_missing" in rows(incomplete)["Downside", OCCUPANCY]["blockers"],
            "Absent PASS did not block the criterion")
    corrected = dict(sources, criteria_raw=change_cells(sources["criteria_raw"], {"B18": "SYNTHETIC-D200-restored"}))
    restored_settings = deepcopy(settings)
    restored_settings["criteria_revision"] = "SYNTHETIC-D200-restored"
    restored, _, corrected_files = run("corrected", restored_settings, corrected,
                                       register(corrected, "SYNTHETIC-D200-corrected"), "PASS")
    historical = verify_package(output / "incomplete", current_revision_raw=corrected_files[CURRENT_REVISION_FILE])
    require(historical["vigencia"] == "HISTORICO" and historical["simulation_result"] == "PENDING"
            and read_package(output / "incomplete") == incomplete_files, "A prior incomplete revision was rewritten")

    registered_case = json.loads(saved["case.json"])
    checked_documents = review_documents(registered_case, sources["plan_raw"], evidence_raw=sources["evidence_raw"],
                                         evidence_milestone="D162")

    def reuse_checked_documents(candidate, plan_raw, *, evidence_raw, evidence_milestone):
        require(all(candidate[key] == registered_case[key] for key in ("local_sources", "workbook_sha256"))
                and plan_raw == sources["plan_raw"] and evidence_raw == sources["evidence_raw"]
                and evidence_milestone == "D162", "A criterion probe changed an audited source")
        return deepcopy(checked_documents)

    def probe(*args):
        with patch("worksheet_documented_finance_D147.review_documents", reuse_checked_documents):
            return run(*args, audit=False)

    base_variants = settings["rent_inputs"]["definition_screening"]["Base"]
    from worksheet_criteria_intake_D194 import PASS_ONLY_POLICY
    pass_only_settings = deepcopy(settings)
    pass_only_settings["criteria_workbook"]["downside_pass_only"] = {
        "equity_recovered": dict(policy=PASS_ONLY_POLICY, source_ref="SYNTHETIC-D200-pass-only")}
    pass_only = dict(sources, criteria_raw=change_cells(sources["criteria_raw"], {"H9": "Sin FAIL"}))
    pass_result, _, _ = probe("pass-only-non-RLV", pass_only_settings, pass_only,
                             register(pass_only, "SYNTHETIC-D200-pass-only"), "PASS")
    require(rows(pass_result)["Downside", "equity_recovered"]["state"] == "PASS_CONDITION"
            and detail(pass_result, "Downside", RLV)["state"] == "calculated_synthetic", "Non-RLV PASS-only affected RLV")

    on_spread = deepcopy(settings)
    on_spread["rent_inputs"]["definition_screening"]["Base"]["rlv"]["binding_yields"] = ["spread"]
    spread, _, _ = probe("spread-grid", on_spread, sources, registration, "PASS")
    require(detail(spread, "Base", RLV)["calculation"]["yield_criterion"] == "spread_bps", "Spread did not drive the grid")

    conflicting = deepcopy(settings)
    conflicting_inputs = conflicting["rent_inputs"]
    conflicting_inputs["definition_screening"]["Base"]["rlv"]["binding_yields"] = ["YoC", "spread"]
    conflicting_inputs["criterion_noi_contexts"]["Base"]["YoC"]["noi_basis"] = BEFORE_RESERVES
    conflicting_inputs["criterion_noi_contexts"]["Downside"]["spread"]["period_ref"] = "2030-01-01/2031-01-01"
    conflicting_inputs["criterion_noi_contexts"]["Base"].pop("post_refi_CoC")
    physical = conflicting_inputs["definition_screening"]["Base"]["occupancy"]
    physical["definition"] = PHYSICAL
    next(rule for rule in conflicting["rules"] if rule["scenario_id"] == "Base"
         and rule["metric_id"] == OCCUPANCY)["definition_ref"] = PHYSICAL
    blocked, _, _ = probe("incompatible-and-C14", conflicting, sources, registration, "PENDING")
    require(detail(blocked, "Base", RLV)["blocker"] == "SRC-03_exactly_one_binding_yield_required",
            "Conflicting yield hurdles drove a grid")
    for name, metric in (("Base", "YoC"), ("Downside", "spread"), ("Base", "post_refi_CoC")):
        comparison = rows(blocked)[name, metric]
        require(comparison["state"] == "PENDING" and comparison["metric_record"]["value"] is None
                and "NOI_basis_or_window_unconfirmed_or_incompatible" in comparison["blockers"],
                f"{name} {metric}: mismatched NOI executed")
    require(detail(blocked, "Base", OCCUPANCY)["blocker"] == "C14_sin_desglose"
            and rows(blocked)["Base", OCCUPANCY]["state"] == "PENDING", "Physical occupancy guessed a C14 split")

    no_neighbor = deepcopy(settings)
    no_neighbor["rent_inputs"]["definition_screening"]["Base"]["rlv"]["grid"] = [
        detail(complete, "Base", RLV)["calculation"]["pass_price"], *base_variants["rlv"]["grid"][1:]]
    edge, _, _ = probe("missing-neighbor", no_neighbor, sources, registration, "PENDING")
    require(detail(edge, "Base", RLV)["blocker"] == "lower_neighbor_missing", "Unbracketed RLV was published")

    checks = {}
    for name in SCENARIOS:
        source = sources["workbook_raw" if name == "Base" else "downside_workbook_raw"]
        view = complete["scenarios"][name]
        independent = calculate(source, settings["rent_inputs"], name)
        comparison, _ = compare_scenario(independent, view, name)
        require(all(line[-2] in ("CUADRA", "CONTENIDA") for line in comparison),
                f"{name}: independent D179 values differ")
        cash = view["cash_per_usd_10"]
        require(all(model["scenarios"][name]["cash_per_usd_10"] == cash
                    for model in (adversarial, incomplete, restored, pass_result, spread, blocked, edge)),
                "A criteria-only change revised cash")
        boundaries = verify_neighbors(detail(complete, name, RLV))
        require(verify_neighbors(detail(restored, name, RLV)) == boundaries, "Restored limits did not recalculate")
        checks[name] = dict(independent_lines=len(comparison), sources_and_uses_periods=verify_periods(view), **boundaries,
                            cash_per_usd_10=cash_summary(cash),
                            allocation=verify_allocation(view, complete["screening"]["irr_by_scenario"][name], terms))
    return dict(status="passed", technical_checklist="16/16", cases=dict(complete="PASS", adverse="FAIL",
                incomplete="PENDING", corrected="PASS"), independent_checks=checks, identical_replay_files=len(saved),
                package_hashes={name: sha(raw) for name, raw in saved.items()},
                allocation_terms_sha256=sha(TERMS.read_bytes()), routes=verify_calendar(complete, settings),
                pilot_real="PENDING", decision="PENDING", real_decisions_enabled=False, deployment_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d200-") as temporary:
        output = args.output or Path(temporary)
        output.mkdir(exist_ok=True)
        print(json.dumps(verify(output), ensure_ascii=False, sort_keys=True))
