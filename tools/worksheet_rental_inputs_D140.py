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


def terms_for(supplied, scenario, values, sheet, *, include_development=False, include_operating_costs=False,
              include_property_tax=False, include_exit_pricing=False):
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
    other_income_basis = ("explicit_eligible_units_included_in_residential_management" if include_operating_costs
                          else "explicit_eligible_units_excluding_rent_losses_and_management")
    require(source.get("currency") == "USD" and source.get("financing_profile") == FINANCING_PROFILE
            and (include_development or synthetic_id(source.get("cost_source_ref"))) and synthetic_id(policy.get("source_ref"))
            and policy.get("rent_definition") == "gross_before_losses_and_concessions"
            and policy.get("concession_basis") in ("gross_potential_rent", "after_vacancy_rent")
            and policy.get("other_income_basis") == other_income_basis,
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
    expense_keys = ("fixed_opex",) if include_operating_costs else tuple(EXPENSES)
    if not include_property_tax:
        expense_keys = (*expense_keys, "property_tax")
    require(set(expenses) == {*expense_keys, "source_ref"} and synthetic_id(expenses.get("source_ref"))
            and all((value := _fraction(expenses[key])) is not None and value >= 0 for key in expense_keys)
            and (include_operating_costs or _fraction(expenses["management"]) <= 1), "rental_expense_basis_unconfirmed")
    cost = None if include_development else _fraction(source.get("construction_cost"))
    principal = _fraction(source.get("requested_principal"))
    cap = None if include_exit_pricing else _fraction(source.get("exit_cap"))
    if include_exit_pricing:
        require("exit_cap" not in source, "conflicting_workbook_and_supplemental_exit_cap:C67")
    require((include_development or (cost is not None and cost >= INITIAL)) and principal is not None and principal > 0
            and (include_exit_pricing or (cap is not None and 0 < cap <= 1)), "rental_cost_or_loan_terms_unconfirmed")
    vacancy, concessions, stress = (_fraction(value) for value in
                                    (values["C14"], values["C15"], policy.get("bank_vacancy_addition")))
    require(stress is not None and 0 <= vacancy <= vacancy + stress <= 1 and 0 <= concessions <= 1
            and (policy["concession_basis"] != "gross_potential_rent" or vacancy + stress + concessions <= 1)
            and all(_fraction(values[cell]) >= 0 for cell in (*GROUPS, "C13")), "rent_or_loss_outside_profile")
    return dict(context=dict(deal_id=deal_id, scenario_id=f"SYNTHETIC-{scenario}", run_id="SYNTHETIC-D140",
                             definition_set_revision=policy["source_ref"]), basis=basis, policy=policy, comps=comps,
                groups=groups, other_income=others, expenses=expenses, cost=cost, principal=principal, cap=cap)


def rental_noi(terms, cells, values, period, commercial=None, *, window_start=None):
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
                     source_ref=expense_terms["source_ref"], policy_ref=policy["source_ref"])
                for key, kind in EXPENSES.items() if key in expense_terms]
    other = terms["other_income"]
    other_value = _fraction(values["C13"]) * other["eligible_units"] * 12
    if "operating_costs" in terms:
        from worksheet_operating_costs_D148 import expense_items
        expenses.extend(expense_items(terms["operating_costs"], other_value, cells["C13"]))
    expenses.extend(terms.get("utility_expenses", ()))
    raw = encoded(dict(schema=RENTAL_SCHEMA, context=context, currency="USD", period_ref=period,
                       months_in_period=12, months_per_year=12, residential_groups=groups, expense_items=expenses))
    producer = produce_rental_operations(raw)
    spec = template("synthetic-residential-noi-assembly")
    spec.update(context=context, rental_source_sha256=sha(raw), rental_run_sha256=producer.sha256)
    spec["additional_income_rows"][0].update(item_id="SYNTHETIC-other-residential-income",
                                             period_ref=period, value=rational(other_value), source_ref=cells["C13"])
    if commercial is not None:
        from worksheet_commercial_inputs_D141 import commercial_income
        commercial_result = commercial_income(commercial, period, window_start=window_start)
        spec["additional_income_rows"].append(spec["additional_income_rows"][0] | dict(
            item_id="SYNTHETIC-net-commercial-NNN", value=commercial_result["net"],
            source_ref=f"sha256:{sha(encoded(commercial))}#/uses"))
    property_tax = terms.get("property_tax")
    if property_tax is None:
        spec["tax_floor"].update(value=expense_terms["property_tax"], period_ref=period, source_ref=expense_terms["source_ref"])
        spec["tax_coefficient"].update(value=rational(0), source_ref=policy["source_ref"])
    else:
        tax_source = f"sha256:{sha(encoded(property_tax))}"
        spec["tax_floor"].update(value=property_tax["floor"], period_ref=period, source_ref=f"{tax_source}#/floor")
        spec["tax_coefficient"].update(value=property_tax["coefficient"], source_ref=f"{tax_source}#/coefficient")
    assembled = assemble_rental_noi(raw, producer, encoded(spec))
    rows = producer.payload
    evidence = dict(gross_rent=rows["gross_potential_total"], effective_rent=rows["residential_effective_rent"],
                    other_income=rational(other_value), operating_expenses_excluding_tax=rows["operating_expenses_excluding_tax"],
                    noi=assembled.payload["computed_noi"], rental_source_sha256=sha(raw), rental_run_sha256=producer.sha256,
                    noi_assembly_sha256=assembled.sha256, groups=rows["groups"], loss_fraction=rational(loss))
    if commercial is not None:
        evidence["commercial"] = commercial_result
    if "utility_evidence" in terms:
        evidence["utilities"] = terms["utility_evidence"]
    if "operating_costs" in terms:
        from worksheet_operating_costs_D148 import period_evidence
        evidence["operating_costs"] = period_evidence(terms["operating_costs"], rows, other_value)
    if property_tax is not None and assembled.noi_run is not None:
        result = assembled.noi_run.payload
        evidence["property_tax"] = property_tax | dict(period_ref=period, annual_tax=result["property_tax"],
                                                       operating_before_tax=result["operating_before_tax"],
                                                       branch=result["tax_branch"], equation_residual=result["equation_residual"])
    return assembled, evidence


def run_rental_scenario(name, raw, review, rent_inputs, *, include_commercial=False, include_utilities=False,
                        include_development=False, include_budget=False, include_calendar=False,
                        include_construction_financing=False, document_review=None, include_operating_costs=False,
                        include_replacement_reserve=False, include_property_tax=False, include_exit_pricing=False,
                        include_permanent_loan=False):
    pending = dict(state="PENDING", cash_per_usd_10=None, capacity=None, noi_by_period={})
    if not review["calculation_inputs_ready"]:
        return pending | dict(blockers=["required_rental_cells_unconfirmed"])
    rows = {row["value_cell"].split("!")[1]: row for row in review["rows"] if row["field_id"] in FIELDS}
    values = {cell: row["value"] for cell, row in rows.items()}
    cells = {cell: f"sha256:{review['workbook_sha256']}#{row['value_cell']}" for cell, row in rows.items()}
    binding = None
    try:
        terms = terms_for(rent_inputs, name, values, inspect_synthetic_input_sheet(raw).cells,
                          include_development=include_development, include_operating_costs=include_operating_costs,
                          include_property_tax=include_property_tax, include_exit_pricing=include_exit_pricing)
        development = None
        cost_source = rent_inputs.get("cost_source_ref")
        if include_development:
            from worksheet_development_inputs_D143 import development_costs
            development = development_costs(rent_inputs.get("development"), name, review, terms["groups"])
            terms["cost"] = _fraction(development["total_development_cost"])
            cost_source = f"sha256:{sha(encoded(development))}#/total_development_cost"
        if document_review is not None:
            from worksheet_documented_finance_D147 import bind_development
            binding = bind_development(name, development, document_review)
            if binding["blockers"]:
                return pending | dict(blockers=binding["blockers"], development_costs=development,
                                      document_financial_binding=binding, cell_sources=cells)
        if include_utilities:
            from worksheet_utility_inputs_D142 import utility_expenses
            terms["utility_expenses"], terms["utility_evidence"] = utility_expenses(
                rent_inputs.get("utilities"), name, review, terms["groups"])
        if include_operating_costs:
            from worksheet_operating_costs_D148 import declared_costs
            terms["operating_costs"] = declared_costs(rent_inputs.get("operating_costs"), name, review, terms["groups"],
                                                     terms["utility_evidence"])
        reserve = None
        if include_replacement_reserve:
            from worksheet_replacement_reserve_D149 import declared_reserve
            reserve = declared_reserve(rent_inputs.get("replacement_reserve"), name, review, terms["groups"])
        if include_property_tax:
            from worksheet_property_tax_D150 import declared_property_tax
            terms["property_tax"] = declared_property_tax(rent_inputs.get("property_tax"), name, review, terms["groups"])
        valuation_terms = None
        if include_exit_pricing:
            from worksheet_exit_pricing_D151 import declared_valuation_terms
            valuation_terms = declared_valuation_terms(rent_inputs.get("valuation_and_sale"), name, review)
            terms["cap"] = _fraction(valuation_terms["exit_cap"])
        calendar = None
        if include_calendar:
            from worksheet_project_calendar_D145 import project_calendar
            calendar = project_calendar(rent_inputs.get("project_calendar"), name, review, development["purchase_date"])
        permanent_terms = None
        if include_permanent_loan:
            from worksheet_permanent_loan_D152 import declared_loan_terms
            permanent_terms = declared_loan_terms(rent_inputs.get("permanent_loan"), name, review, calendar)
            calendar["payment_dates"] = permanent_terms["payment_dates"]
        commercial = None
        if include_commercial:
            from worksheet_commercial_inputs_D141 import commercial_terms
            commercial_source = rent_inputs.get("commercial")
            if calendar is not None:
                commercial_source = object_or_empty(commercial_source)
                require("tco_date" not in commercial_source and "tco_source_ref" not in commercial_source,
                        "conflicting_commercial_tco_sources:C47")
                commercial_source = commercial_source | dict(tco_date=calendar["tco_date"], tco_source_ref=calendar["tco_ref"])
            commercial = commercial_terms(commercial_source, review)
        budget = None
        draws = None
        if include_budget:
            from worksheet_construction_budget_D144 import construction_budget
            budget = construction_budget(rent_inputs.get("construction_budget"), name, review, development, commercial,
                                         calendar=calendar)
            if binding is not None:
                budget["document_financial_binding_sha256"] = sha(encoded(binding))
            terms["cost"] = _fraction(budget["total_development_cost"])
            if calendar is not None:
                terms["cost"] += _fraction(calendar["lease_up_funding"])
            cost_source = f"sha256:{sha(encoded(budget))}#/equity_draws"
            draws = [draw | dict(source_ref=f"{cost_source}/{index}") for index, draw in enumerate(budget["equity_draws"])]
        funding = None
        if include_construction_financing:
            from worksheet_construction_financing_D146 import staged_construction_financing
            funding = staged_construction_financing(rent_inputs.get("construction_financing"), name, review, terms["context"],
                                                  development, budget, calendar)
            if funding["blockers"]:
                evidence = dict(document_financial_binding=binding) if binding is not None else {}
                return pending | dict(blockers=funding["blockers"], construction_financing=funding,
                                      project_calendar=calendar, construction_budget=budget, development_costs=development) | evidence
            terms["cost"] = _fraction(funding["equity_funding_through_refinance"])
            cost_source = f"sha256:{sha(encoded(funding))}#/equity_draws"
            draws = [draw | dict(source_ref=f"{cost_source}/{index}") for index, draw in enumerate(funding["equity_draws"])]
        periods = {}

        def noi_for(period):
            window_start = None if calendar is None else calendar["noi_window_starts"][period]
            assembled, periods[period] = rental_noi(terms, cells, values, period, commercial, window_start=window_start)
            return assembled

        # The accrued operating result remains available when the refinance request is blocked.
        operating = noi_for(OPERATING_PERIOD)
        result = financed_cash(terms["context"], terms["cost"], cost_source,
                               terms["principal"], terms["cap"],
                               lambda period: operating if period == OPERATING_PERIOD else noi_for(period),
                               construction_draws=draws, calendar=calendar, construction_financing=funding,
                               replacement_reserve=reserve, valuation_terms=valuation_terms, permanent_terms=permanent_terms)
    except (ValueError, TypeError, KeyError) as error:
        evidence = dict(document_financial_binding=binding) if binding is not None else {}
        return pending | dict(blockers=[str(error)], cell_sources=cells) | evidence
    if commercial is not None:
        result["commercial_terms"] = commercial
    if development is not None:
        result.pop("vertical_cost", None)
        result["development_costs"] = development
    if budget is not None:
        result["construction_budget"] = budget
    if calendar is not None:
        result["project_calendar"] = calendar
    if funding is not None:
        result["construction_financing"] = funding
    if binding is not None:
        result["document_financial_binding"] = binding
    return result | dict(noi_by_period=periods, cell_sources=cells, comps_evidence=terms["comps"], rent_basis=terms["basis"])


def screen(case, views, blockers, *, period_ref=PERIOD):
    unit, quantity, currency, definition = METRICS[METRIC]
    refs = dict(metric_id=METRIC, definition_ref=f"SYNTHETIC-D51-{definition}", unit=unit, quantity_kind=quantity,
                currency=currency, period_ref=period_ref, applicability="applicable", applicability_evidence_ref=None)
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


def render(views, result, *, include_commercial=False, include_utilities=False, include_development=False,
           include_budget=False, include_calendar=False, include_construction_financing=False, document_review=None,
           include_operating_costs=False, include_replacement_reserve=False, include_property_tax=False,
           include_exit_pricing=False, include_permanent_loan=False):
    lines = [(f"Simulación por múltiplo de equity | {result} | Decisión real PENDING", True)]
    if document_review is not None:
        label = "Documentos cotejados" if document_review["state"] == "checked_synthetic" else "Validación documental PENDING"
        if result == "PENDING":
            label += " | Flujos disponibles sujetos a los pendientes del expediente"
        lines.append((label, False))
    for name, view in views.items():
        accrued = view["noi_by_period"].get(OPERATING_PERIOD)
        cash = view["cash_per_usd_10"]
        lines.append((f"{name} | Cobro total por USD 10 iniciales: "
                      + ("PENDING" if cash is None else f"USD {money(cash['total_distributions'])}"), True))
        if include_calendar and "project_calendar" in view:
            calendar = view["project_calendar"]
            lines.append((f"Fin de obra {calendar['construction_finish']} | TCO {calendar['tco_date']} | "
                          f"Estabilización {calendar['stabilization_date']}", False))
            lines.append((f"Refi prevista {calendar['refinance_date']} | Venta prevista {calendar['sale_date']}", False))
        if include_construction_financing and view.get("construction_financing", {}).get("state") == "computed_synthetic":
            funding = view["construction_financing"]
            totals = funding["debt_run"]["totals"]
            lines.append((f"Obra | Deuda desembolsada USD {money(totals['gross_draws'])} | Interés USD "
                          f"{money(totals['interest_due'])} | Comisión USD {money(funding['origination_fee'])}", False))
        if include_operating_costs and accrued and accrued["noi"] is not None:
            if include_property_tax:
                taxes = accrued["property_tax"]
                lines.append((f"NOI anual USD {money(accrued['noi'])} | Impuesto inmobiliario USD {money(taxes['annual_tax'])}", False))
            else:
                costs = accrued["operating_costs"]
                lines.append((f"NOI anual USD {money(accrued['noi'])} | Administración USD {money(costs['management_fee'])} | "
                              f"Seguro USD {money(costs['insurance_total'])}", False))
        if include_replacement_reserve and "replacement_reserve" in view:
            reserve = view["replacement_reserve"]
            lines.append((f"Reserva del proyecto USD {money(reserve['deposit'])} | Liberada USD {money(reserve['released_at_sale'])} | "
                          f"Transferida al comprador USD {money(reserve['transferred_restricted_to_buyer'])}", False))
        if include_exit_pricing and "valuation_and_sale" in view:
            pricing = view["valuation_and_sale"]
            if pricing["refinance_value"] is not None:
                capacity = view["capacity"]["maximum_principal_capacity"]
                limit = "PENDING" if capacity is None else f"USD {money(capacity)}"
                if include_permanent_loan and capacity is not None:
                    limit += " · " + "/".join(view["capacity"]["binding_limit_ids"])
                lines.append((f"Valor para refi USD {money(pricing['refinance_value'])} | Capacidad {limit}", False))
            if "gross_sale_price" in pricing:
                lines.append((f"Precio bruto USD {money(pricing['gross_sale_price'])} | Costos de venta USD {money(pricing['sale_cost'])}", False))
        if include_permanent_loan and view.get("permanent_loan", {}).get("quote_state") == "computed_synthetic":
            loan = view["permanent_loan"]
            lines.append((f"Cuota trimestral proyectada USD {money(loan['regular_payment_due'])} | "
                          f"Servicio anual para capacidad USD {money(loan['annual_sizing_service'])}", False))
        if include_calendar and cash is None:
            lines.append((f"Pendiente por {view['blockers'][0][:105]}", False))
        if accrued and accrued["noi"] is not None and not include_calendar:
            lines.append((f"NOI anual del proyecto USD {money(accrued['noi'])} | Otros ingresos USD {money(accrued['other_income'])}", False))
            if include_commercial:
                commercial = accrued["commercial"]
                lines.append((f"Renta comercial neta USD {money(commercial['net'])} | {commercial['recognized_months']} meses", False))
            if include_utilities:
                lines.append((f"Gasto anual de servicios USD {money(accrued['utilities']['annual_total'])}", False))
        if include_development and not include_calendar and "development_costs" in view:
            costs = view["development_costs"]
            lines.append((f"Terreno USD {money(costs['evaluated_purchase_price'])} | Cierre USD "
                          f"{money(costs['land_closing_cost'])} | Obra vertical USD {money(costs['vertical_cost'])}", False))
        if include_budget and not include_calendar and "construction_budget" in view:
            budget = view["construction_budget"]
            lines.append((f"Presupuesto USD {money(budget['total_development_cost'])} | Soft meses 1-3 USD "
                          f"{money(budget['upfront_soft'])} | Saldo soft USD {money(budget['remaining_soft'])}", False))
        if cash is not None:
            events = [event for event in cash["events"] if _fraction(event["amount"])]
            for index, event in enumerate(events):
                if include_construction_financing and len(events) > 12 and 6 <= index < len(events) - 5:
                    if index == 6:
                        lines.append(("Fechas intermedias de aportes en el expediente de cálculo", False))
                    continue
                label = "Aporte para estabilización" if event["event_id"] == "lease-up-funding" else LABELS[event["category"]]
                lines.append((f"{event['date']} | {label} USD {money(event['amount'])}", False))
            lines.append((f"Aportado USD {money(cash['total_contributions'])} | Sin recuperar USD {money(cash['unrecovered_after_sale'])}", False))
    label = "D142 | C25-C28" if include_utilities else "D141 | C7-C21" if include_commercial else "D140 | C7-C15"
    if include_development:
        label = "D143 | C32-C36"
    spacing = 17 if include_development else 19 if include_utilities else 21
    if include_permanent_loan:
        return render_page("D152 | C69-C72", lines, 10, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Deuda permanente, capacidad de refinanciación y caja | Piloto sintético")
    if include_exit_pricing:
        return render_page("D151 | C66-C68", lines, 10, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Valor de refi, precio de salida, costos y caja | Piloto sintético")
    if include_property_tax:
        return render_page("D150 | C61-C62", lines, 11, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Impuesto inmobiliario, NOI, aportes y cobros | Piloto sintético")
    if include_replacement_reserve:
        return render_page("D149 | C60", lines, 11, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Reserva de reposición, aportes y cobros | Piloto sintético")
    if include_operating_costs:
        return render_page("D148 | C57-C59", lines, 11, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Gastos operativos, aportes y cobros | Piloto sintético")
    if document_review is not None:
        return render_page("D147 | Validación documental y motor D146", lines, 12,
                           "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Planos, GC, vigencia, aportes y cobros | Piloto sintético")
    if include_construction_financing:
        return render_page("D146 | C51-C53", lines, 12, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Deuda de obra, aportes y cobros | Piloto sintético")
    if include_calendar:
        return render_page("D145 | C46-C47", lines, 16, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Obra, estabilización, aportes y cobros | Piloto sintético")
    if include_budget:
        return render_page("D144 | C37-C42", lines, 16, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                           "Presupuesto de obra, aportes y cobros | Piloto sintético")
    return render_page(label, lines, spacing, "MINI-UW | SI INVIERTO USD 10, ¿CUÁNTO COBRO Y CUÁNDO?",
                       "Renta, NOI y cobros del proyecto | Piloto sintético")


def build_rental_case(case, case_sha256, workbooks, current_revision_raw, *, include_commercial=False, include_utilities=False,
                      include_development=False, include_budget=False, include_calendar=False,
                      include_construction_financing=False, document_review=None, include_operating_costs=False,
                      include_replacement_reserve=False, include_property_tax=False, include_exit_pricing=False,
                      include_permanent_loan=False):
    hashes = object_or_empty(case.get("workbook_sha256"))
    review = review_native_mapping(case.get("native_mapping"), workbooks, hashes, calculation_fields=FIELDS)
    revision = review_revision(case, current_revision_raw)
    views = {name: run_rental_scenario(name, workbooks[name], review["scenarios"][name], case.get("rent_inputs"),
                                      include_commercial=include_commercial, include_utilities=include_utilities,
                                      include_development=include_development, include_budget=include_budget,
                                      include_calendar=include_calendar,
                                      include_construction_financing=include_construction_financing,
                                      document_review=document_review, include_operating_costs=include_operating_costs,
                                      include_replacement_reserve=include_replacement_reserve,
                                      include_property_tax=include_property_tax, include_exit_pricing=include_exit_pricing,
                                      include_permanent_loan=include_permanent_loan)
             for name in SCENARIOS}
    blockers = [f"B04:{reason}" for reason in review["blockers"]] + [f"B12:{reason}" for reason in revision["blockers"]]
    blockers += [f"{name}:{reason}" for name, view in views.items() for reason in view["blockers"]]
    if document_review is not None:
        bindings = {name: view["document_financial_binding"] for name, view in views.items()
                    if "document_financial_binding" in view}
        document_blockers = document_review["blockers"] + [f"{name}:{reason}" for name, binding in bindings.items()
                                                          for reason in binding["blockers"]]
        document_review = document_review | dict(financial_bindings=bindings, blockers=sorted(set(document_blockers)),
                                                 state="PENDING" if document_blockers else "checked_synthetic")
        blockers += document_review["blockers"]
    period_ref = PERIOD
    if include_calendar:
        from worksheet_project_calendar_D145 import LIFECYCLE
        period_ref = LIFECYCLE
    if include_construction_financing:
        from worksheet_construction_financing_D146 import LIFECYCLE
        period_ref = LIFECYCLE
    screening = screen(case, views, blockers, period_ref=period_ref)
    simulation = screening["simulation_result"]
    pdf = render(views, simulation, include_commercial=include_commercial, include_utilities=include_utilities,
                 include_development=include_development, include_budget=include_budget, include_calendar=include_calendar,
                 include_construction_financing=include_construction_financing, document_review=document_review,
                 include_operating_costs=include_operating_costs, include_replacement_reserve=include_replacement_reserve,
                 include_property_tax=include_property_tax, include_exit_pricing=include_exit_pricing,
                 include_permanent_loan=include_permanent_loan)
    profile = "synthetic_native_residential_and_commercial_rent" if include_commercial else PROFILE
    if include_utilities:
        profile = "synthetic_native_rent_and_utility_expenses"
    if include_development:
        profile = "synthetic_native_rent_and_development_costs"
    if include_budget:
        profile = "synthetic_native_rent_and_construction_budget"
    if include_calendar:
        profile = "synthetic_native_project_calendar"
    if include_construction_financing:
        profile = "synthetic_native_construction_financing"
    pipeline = {}
    if document_review is not None:
        from worksheet_documented_finance_D147 import record_pipeline
        profile = "synthetic_documented_construction_financing"
        pipeline = dict(local_review=document_review,
                        pipeline=record_pipeline(case_sha256, views, review, revision, screening, pdf, document_review))
    if include_operating_costs:
        profile = "synthetic_documented_operating_costs"
        pipeline["pipeline"]["stages"][-1]["version_suite"] = "check_worksheet_operating_costs_D148.py"
    if include_replacement_reserve:
        profile = "synthetic_documented_replacement_reserve"
        pipeline["pipeline"]["stages"][-1]["version_suite"] = "check_worksheet_replacement_reserve_D149.py"
    if include_property_tax:
        profile = "synthetic_documented_property_tax"
        pipeline["pipeline"]["stages"][-1]["version_suite"] = "check_worksheet_property_tax_D150.py"
    if include_exit_pricing:
        profile = "synthetic_documented_exit_pricing"
        pipeline["pipeline"]["stages"][-1]["version_suite"] = "check_worksheet_exit_pricing_D151.py"
    if include_permanent_loan:
        profile = "synthetic_documented_permanent_loan"
        pipeline["pipeline"]["stages"][-1]["version_suite"] = "check_worksheet_permanent_loan_D152.py"
    return dict(profile=profile, state="PENDING" if simulation == "PENDING" else "computed_synthetic_scenario_cash",
                case_sha256=case_sha256, decision="PENDING", simulation_result=simulation,
                real_decisions_enabled=False, deployment_enabled=False, personal_investor_return=None,
                scenarios=views, native_mapping_review=review, revision_review=revision, screening=screening,
                pdf_sha256=sha(pdf), page_count=1) | pipeline, pdf
