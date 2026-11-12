"""Bind C7–C15 to scoped residential NOI, refinance and equity cash."""
from datetime import date, datetime
from fractions import Fraction

from check_operating_replay_D20 import require
from check_scenario_pilot_D51 import METRICS
from check_worksheet_refinance_D45 import render_page
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.rental_noi import assemble_rental_noi
from miniuw_foundation.rental_operations import SCHEMA as RENTAL_SCHEMA, produce_rental_operations
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.screening import SCHEMA as SCREENING_SCHEMA, simulate_screening
from miniuw_worksheet_v1 import encoded
from plan_refinance_D108 import BANK_PERIOD, SOURCE as FINANCING_PROFILE, financed_cash
from plan_return_D107 import DATES, INITIAL, OPERATING_PERIOD, SALE_DATE, template
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_native_mapping_D139 import SCENARIOS, review_native_mapping
from worksheet_plan_refinance_D109 import LABELS
from worksheet_revision_D128 import review_revision
from worksheet_sale_rate_grid_D84 import money
from worksheet_screening_pilot_D120 import criterion_records


PROFILE = "synthetic_native_rent_and_noi"
GROUPS = {"C8": "studio", "C9": "1BR", "C10": "2BR", "C11": "3BR"}
FIELDS = {f"INPUT_C{index}" for index in range(7, 16)}
RENT_BASES = {"PER UNIT": "per_unit_per_month", "PER SF": "per_rentable_sf_per_month"}
EXPENSES = {"unit_opex": "per_unit_per_regular_year", "fixed_opex": "fixed_per_declared_period",
            "management": "fraction_of_residential_effective_rent"}
METRIC = "equity_multiple"
PERIOD = f"{DATES[0]}/{SALE_DATE}"


def terms_for(supplied, scenario, values, sheet):
    source = object_or_empty(supplied)
    policy = object_or_empty(source.get("policy"))
    comps = object_or_empty(object_or_empty(source.get("rent_comps")).get(scenario))
    group_records = object_or_empty(source.get("groups"))
    basis = RENT_BASES[values["C7"]]
    deal_id = source.get("deal_id")
    as_of = source.get("as_of_UTC")
    require(synthetic_id(deal_id) and isinstance(as_of, str) and as_of.endswith("Z") and "T" in as_of
            and datetime.fromisoformat(as_of).utcoffset() is not None
            and all(sheet.get(cell, {}).get("literal") == value and sheet[cell]["kind"] == "text"
                    for cell, value in (("B3", deal_id), ("E3", as_of))), "rental_workbook_metadata_unconfirmed")
    require(source.get("currency") == "USD" and source.get("financing_profile") == FINANCING_PROFILE
            and synthetic_id(source.get("cost_source_ref")) and synthetic_id(policy.get("source_ref"))
            and policy.get("rent_definition") == "gross_before_losses_and_concessions"
            and policy.get("concession_basis") in ("gross_potential_rent", "after_vacancy_rent")
            and policy.get("other_income_basis") == "explicit_eligible_units_excluding_rent_losses_and_management",
            "rental_policy_or_financing_scope_unconfirmed")
    require(comps.get("literal") == values["C12"] and synthetic_id(comps.get("source_ref"))
            and isinstance(comps.get("observed_on"), str)
            and date.fromisoformat(comps["observed_on"]).isoformat() == comps["observed_on"]
            and date.fromisoformat(comps["observed_on"]) <= date.fromisoformat(as_of[:10]),
            "rent_comps_reference_unconfirmed")
    require(set(group_records) == set(GROUPS.values()), "rental_group_inventory_unconfirmed")
    groups = {}
    for group_id, record in group_records.items():
        record = object_or_empty(record)
        units = record.get("units")
        sf = _fraction(record.get("rentable_sf_per_unit"))
        require(type(units) is int and 0 <= units <= 10000 and synthetic_id(record.get("source_ref"))
                and (basis != "per_rentable_sf_per_month" or (sf is not None and (sf > 0 or units == 0))),
                f"rental_group_quantity_unconfirmed:{group_id}")
        groups[group_id] = record
    others = object_or_empty(source.get("other_income"))
    eligible = others.get("eligible_units")
    require(type(eligible) is int and 0 <= eligible <= sum(row["units"] for row in groups.values())
            and synthetic_id(others.get("source_ref")), "other_income_population_unconfirmed")
    expenses = object_or_empty(source.get("annual_expenses"))
    require(set(expenses) == {*EXPENSES, "property_tax", "source_ref"} and synthetic_id(expenses.get("source_ref"))
            and all((value := _fraction(expenses[key])) is not None and value >= 0 for key in (*EXPENSES, "property_tax"))
            and _fraction(expenses["management"]) <= 1, "rental_expense_basis_unconfirmed")
    cost, principal, cap = (_fraction(source.get(key)) for key in ("construction_cost", "requested_principal", "exit_cap"))
    require(cost is not None and cost >= INITIAL and principal is not None and principal > 0
            and cap is not None and 0 < cap <= 1, "rental_cost_or_loan_terms_unconfirmed")
    vacancy, concessions, stress = (_fraction(value) for value in
                                    (values["C14"], values["C15"], policy.get("bank_vacancy_addition")))
    require(stress is not None and 0 <= vacancy <= vacancy + stress <= 1 and 0 <= concessions <= 1
            and (policy["concession_basis"] != "gross_potential_rent" or vacancy + stress + concessions <= 1)
            and all(_fraction(values[cell]) >= 0 for cell in (*GROUPS, "C13")), "rent_or_loss_outside_profile")
    return dict(context=dict(deal_id=deal_id, scenario_id=f"SYNTHETIC-{scenario}", run_id="SYNTHETIC-D140",
                             definition_set_revision=policy["source_ref"]), basis=basis, policy=policy, comps=comps,
                groups=groups, other_income=others, expenses=expenses, cost=cost, principal=principal, cap=cap)


def rental_noi(terms, cells, values, period, commercial=None):
    context = terms["context"]
    policy = terms["policy"]
    loss = _fraction(values["C14"])
    if period == BANK_PERIOD:
        loss += _fraction(policy["bank_vacancy_addition"])
    groups = []
    for cell, group_id in GROUPS.items():
        record = terms["groups"][group_id]
        groups.append(dict(group_id=group_id, units=rational(record["units"]), unit_rentable_sf=record.get("rentable_sf_per_unit"),
                           rent=values[cell], rent_basis=terms["basis"], rent_definition=policy["rent_definition"],
                           loss_fraction=rational(loss), concession_fraction=values["C15"],
                           concession_basis=policy["concession_basis"], currency="USD",
                           source_ref=cells[cell], policy_ref=policy["source_ref"]))
    expense_terms = terms["expenses"]
    expenses = [dict(item_id=key, kind=kind, rate=expense_terms[key], currency="USD",
                     source_ref=expense_terms["source_ref"], policy_ref=policy["source_ref"]) for key, kind in EXPENSES.items()]
    raw = encoded(dict(schema=RENTAL_SCHEMA, context=context, currency="USD", period_ref=period,
                       months_in_period=12, months_per_year=12, residential_groups=groups, expense_items=expenses))
    producer = produce_rental_operations(raw)
    spec = template("synthetic-residential-noi-assembly")
    other = terms["other_income"]
    other_value = _fraction(values["C13"]) * other["eligible_units"] * 12
    spec.update(context=context, rental_source_sha256=sha(raw), rental_run_sha256=producer.sha256)
    spec["additional_income_rows"][0].update(item_id="SYNTHETIC-other-residential-income",
                                             period_ref=period, value=rational(other_value), source_ref=cells["C13"])
    if commercial is not None:
        from worksheet_commercial_inputs_D141 import commercial_income
        commercial_result = commercial_income(commercial, period)
        spec["additional_income_rows"].append(spec["additional_income_rows"][0] | dict(
            item_id="SYNTHETIC-net-commercial-NNN", value=commercial_result["net"],
            source_ref=f"sha256:{sha(encoded(commercial))}#/uses"))
    spec["tax_floor"].update(value=expense_terms["property_tax"], period_ref=period, source_ref=expense_terms["source_ref"])
    spec["tax_coefficient"].update(value=rational(0), source_ref=policy["source_ref"])
    assembled = assemble_rental_noi(raw, producer, encoded(spec))
    rows = producer.payload
    evidence = dict(gross_rent=rows["gross_potential_total"], effective_rent=rows["residential_effective_rent"],
                    other_income=rational(other_value), operating_expenses_excluding_tax=rows["operating_expenses_excluding_tax"],
                    noi=assembled.payload["computed_noi"], rental_source_sha256=sha(raw), rental_run_sha256=producer.sha256,
                    noi_assembly_sha256=assembled.sha256, groups=rows["groups"], loss_fraction=rational(loss))
    if commercial is not None:
        evidence["commercial"] = commercial_result
    return assembled, evidence


def run_rental_scenario(name, raw, review, rent_inputs, *, include_commercial=False):
    pending = dict(state="PENDING", cash_per_usd_10=None, capacity=None, noi_by_period={})
    if not review["calculation_inputs_ready"]:
        return pending | dict(blockers=["required_rental_cells_unconfirmed"])
    rows = {row["value_cell"].split("!")[1]: row for row in review["rows"] if row["field_id"] in FIELDS}
    values = {cell: row["value"] for cell, row in rows.items()}
    cells = {cell: f"sha256:{review['workbook_sha256']}#{row['value_cell']}" for cell, row in rows.items()}
    try:
        terms = terms_for(rent_inputs, name, values, inspect_synthetic_input_sheet(raw).cells)
        commercial = None
        if include_commercial:
            from worksheet_commercial_inputs_D141 import commercial_terms
            commercial = commercial_terms(rent_inputs.get("commercial"), review)
        periods = {}

        def noi_for(period):
            assembled, periods[period] = rental_noi(terms, cells, values, period, commercial)
            return assembled

        # The accrued operating result remains available when the refinance request is blocked.
        operating = noi_for(OPERATING_PERIOD)
        result = financed_cash(terms["context"], terms["cost"], rent_inputs["cost_source_ref"],
                               terms["principal"], terms["cap"],
                               lambda period: operating if period == OPERATING_PERIOD else noi_for(period))
    except (ValueError, TypeError, KeyError) as error:
        return pending | dict(blockers=[str(error)], cell_sources=cells)
    if commercial is not None:
        result["commercial_terms"] = commercial
    return result | dict(noi_by_period=periods, cell_sources=cells, comps_evidence=terms["comps"], rent_basis=terms["basis"])


def screen(case, views, blockers):
    unit, quantity, currency, definition = METRICS[METRIC]
    refs = dict(metric_id=METRIC, definition_ref=f"SYNTHETIC-D51-{definition}", unit=unit, quantity_kind=quantity,
                currency=currency, period_ref=PERIOD, applicability="applicable", applicability_evidence_ref=None)
    revision = case.get("criteria_revision")
    raw = dict(schema=SCREENING_SCHEMA, context=dict(deal_id="SYNTHETIC-D140-screening", scenario_id="SYNTHETIC-pair",
              run_id="SYNTHETIC-D140", definition_set_revision="SYNTHETIC-D140-rental"),
              case_id="SYNTHETIC-D140", criteria_revision=revision if synthetic_id(revision) else "SYNTHETIC-unconfirmed",
              criteria_status="synthetic_fixture_only", required_metrics=[METRIC], required_scenarios=list(SCENARIOS),
              metric_values=[refs | dict(scenario_id=name, value=None if view["cash_per_usd_10"] is None
                              else view["cash_per_usd_10"]["equity_multiple"]) for name, view in views.items()],
              criteria=criterion_records(case.get("rules") or [], {METRIC: METRICS[METRIC]}) if synthetic_id(revision) else [],
              aggregation_rule=case.get("aggregation_rule"), hypothetical_band_policy=None)
    result = simulate_screening(encoded(raw)).payload
    return result | dict(simulation_result="PENDING" if blockers else result["simulation_result"],
                         simulation_blockers=sorted(set(result["simulation_blockers"] + blockers)))


def render(views, result, *, include_commercial=False):
    lines = [(f"Simulación por múltiplo de equity | {result} | Decisión real PENDING", True)]
    for name, view in views.items():
        accrued = view["noi_by_period"].get(OPERATING_PERIOD)
        cash = view["cash_per_usd_10"]
        lines.append((f"{name} | Cobro total por USD 10 iniciales: "
                      + ("PENDING" if cash is None else f"USD {money(cash['total_distributions'])}"), True))
        if accrued and accrued["noi"] is not None:
            lines.append((f"NOI anual del proyecto USD {money(accrued['noi'])} | Otros ingresos USD {money(accrued['other_income'])}", False))
            if include_commercial:
                commercial = accrued["commercial"]
                lines.append((f"Renta comercial neta USD {money(commercial['net'])} | {commercial['recognized_months']} meses", False))
        if cash is not None:
            for event in cash["events"]:
                if _fraction(event["amount"]):
                    lines.append((f"{event['date']} | {LABELS[event['category']]} USD {money(event['amount'])}", False))
            lines.append((f"Aportado USD {money(cash['total_contributions'])} | Sin recuperar USD {money(cash['unrecovered_after_sale'])}", False))
    label = "D141 | C7-C21" if include_commercial else "D140 | C7-C15"
    return render_page(label, lines, 21, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Renta, NOI y cobros del proyecto | Piloto sintético")


def build_rental_case(case, case_sha256, workbooks, current_revision_raw, *, include_commercial=False):
    hashes = object_or_empty(case.get("workbook_sha256"))
    review = review_native_mapping(case.get("native_mapping"), workbooks, hashes, calculation_fields=FIELDS)
    revision = review_revision(case, current_revision_raw)
    views = {name: run_rental_scenario(name, workbooks[name], review["scenarios"][name], case.get("rent_inputs"),
                                      include_commercial=include_commercial)
             for name in SCENARIOS}
    blockers = [f"B04:{reason}" for reason in review["blockers"]] + [f"B12:{reason}" for reason in revision["blockers"]]
    blockers += [f"{name}:{reason}" for name, view in views.items() for reason in view["blockers"]]
    screening = screen(case, views, blockers)
    simulation = screening["simulation_result"]
    pdf = render(views, simulation, include_commercial=include_commercial)
    profile = "synthetic_native_residential_and_commercial_rent" if include_commercial else PROFILE
    return dict(profile=profile, state="PENDING" if simulation == "PENDING" else "computed_synthetic_scenario_cash",
                case_sha256=case_sha256, decision="PENDING", simulation_result=simulation,
                real_decisions_enabled=False, deployment_enabled=False, personal_investor_return=None,
                scenarios=views, native_mapping_review=review, revision_review=revision, screening=screening,
                pdf_sha256=sha(pdf), page_count=1), pdf
