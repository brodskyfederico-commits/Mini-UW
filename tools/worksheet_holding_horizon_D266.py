"""Explicit integrated holding horizon; legacy worksheet profiles stay reproducible."""
from copy import deepcopy
from datetime import timedelta
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from check_operating_replay_D20 import require
from miniuw_foundation import operating_noi
from miniuw_foundation.construction_draws import produce_construction_draws
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import encoded
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import OPERATING_PERIOD, FORWARD_PERIOD, template
from worksheet_exact_cash_D263 import cash_engine, exact_fraction as amount
from worksheet_local_sources_D127 import day, object_or_empty, synthetic_id
from worksheet_project_calendar_D145 import offset


PROFILE = "miniuw.synthetic-integrated-holding-horizon.v1"
CALENDAR_POLICY = "SYNTHETIC-D266-first-day-quarterly-stabilization-horizon"
CALENDAR_RULES = dict(cash_grid="quarterly_first_day", construction_origin="documented_purchase_date",
    lease_up_origin="documented_tco_on_construction_finish", refinance="at_stabilization",
    sale="explicit_holding_months_after_stabilization", lease_up_funding="net_shortfall_reserved_at_construction_finish")
RULES = dict(cash="four_equal_cash_quarters_per_fully_stabilized_year", working_capital="no_changes",
    rent_expense_growth="documented_C75_C76_anniversaries", reserve="flat_C60_quarterly_deposits_no_interim_use",
    debt="documented_regular_quarterly_service_then_payoff_after_final_regular_payment",
    sale="year_after_exit_NOI_with_documented_buyer_tax_and_C67_cap", basis="verified_initial_equity_only",
    post_refi_coc="first_complete_year_from_derived_NOI_reserves_service_and_equity",
    zero_roles=["unquoted_closing_costs", "noncash_adjustments", "capex_outside_budget", "other_cash_flows",
                "preopening_property_tax_outside_budget"])
DERIVED_COC = "derive_first_complete_year_from_horizon"
RESERVE_POLICY = "SYNTHETIC-D266-quarterly-replacement-reserve"
RESERVE_RULES = dict(classification="restricted_cash_excluded_from_noi_and_valuation",
    deposit_timing="quarterly_one_fourth_of_documented_annual_rate",period_months=12,
    opening_balance="zero_then_cumulative_no_interim_withdrawals",
    shortfall_funding="equity_at_quarterly_operating_settlement",sale_remainder="transferred_restricted_to_buyer")
PROPERTY_TAX_POLICY = "SYNTHETIC-D266-annual-proxy-tax-quarterly-cash"
PROPERTY_TAX_CASH = "annual_accrued_tax_settled_in_four_explicit_equal_quarters"


def serial(value):
    return json.loads(json.dumps(value, default=rational))


def digest(value):
    return sha256(encoded(serial(value))).hexdigest()


def pending(reason, **extra):
    return dict(state="PENDING", cash_per_usd_10=None, blockers=[reason]) | extra


def horizon_irr(cash,dates):
    from worksheet_lorena_annual_route import route_annual_irr
    from check_worksheet_return_metrics_D167 import quarterly_cash
    import reconcile_worksheet_D179
    import miniuw_foundation.primitive_periodic_returns as primitive
    result=route_annual_irr(cash,dates)
    flows=quarterly_cash(cash,dates)
    return result|dict(cash_sha256=digest(cash),step_months=3,periods_per_year=4,
        method="unique_sign_change_rational_bracket_or_complete_root_isolation",
        method_source_sha256=sha256(Path(route_annual_irr.__code__.co_filename).read_bytes()).hexdigest(),
        bracket_source_sha256=sha256(Path(reconcile_worksheet_D179.__file__).read_bytes()).hexdigest(),
        isolation_source_sha256=sha256(Path(primitive.__file__).read_bytes()).hexdigest(),
        dated_net_flows=None if flows is None else [dict(date=k,net=rational(v)) for k,v in flows.items()])


def configuration(raw, name):
    source = object_or_empty(raw)
    require(source.keys() == {"profile", "source_ref", "rules", "scenarios"}
            and source["profile"] == PROFILE and source["rules"] == RULES
            and synthetic_id(source["source_ref"]) and set(object_or_empty(source["scenarios"])) == {"Base", "Downside"},
            "holding_horizon_profile_or_complete_inventory_unconfirmed")
    record = object_or_empty(source["scenarios"][name])
    require(record.keys() == {"holding_months", "source_ref", "initial_equity", "cash_assumptions_ref",
                              "closing_funding", "without_refinance"}
            and synthetic_id(record["source_ref"]) and synthetic_id(record["cash_assumptions_ref"]),
            "holding_horizon_scenario_or_cash_assumptions_unconfirmed")
    months = record["holding_months"]
    require(type(months) is int and 12 <= months <= 60 and months % 12 == 0,
            "holding_horizon_requires_explicit_supported_whole_years")
    equity = object_or_empty(record["initial_equity"])
    require(equity.keys() == {"value", "source_ref"} and amount(equity["value"]) is not None
            and amount(equity["value"]) > 0 and synthetic_id(equity["source_ref"]),
            "holding_initial_equity_missing_nonpositive_or_unsourced")
    funding = object_or_empty(record["closing_funding"])
    require(funding.keys() == {"policy", "source_ref"} and funding["policy"] in ("equity_top_up", "block_shortfall")
            and synthetic_id(funding["source_ref"]), "holding_closing_shortfall_policy_unconfirmed")
    alternative = object_or_empty(record["without_refinance"])
    if alternative.get("applicability") == "not_requested":
        require(alternative.keys() == {"applicability", "source_ref"} and synthetic_id(alternative["source_ref"]),
                "holding_without_refinance_scope_unconfirmed")
    else:
        require(alternative.keys() == {"applicability", "source_ref", "retention_terms", "fee_at_stabilization"}
                and alternative["applicability"] == "included" and synthetic_id(alternative["source_ref"])
                and alternative["retention_terms"] == "same_committed_facility_C52_until_documented_maturity",
                "holding_without_refinance_scope_unconfirmed")
        fee = object_or_empty(alternative["fee_at_stabilization"])
        require(fee.keys() == {"value", "source_ref"} and synthetic_id(fee["source_ref"])
                and amount(fee["value"]) is not None and amount(fee["value"]) >= 0,
                "holding_construction_retention_fee_unconfirmed")
    return record | dict(profile=PROFILE, profile_ref=source["source_ref"])


def horizon_calendar(raw, name, review, purchase_date, sale_term, horizon):
    from worksheet_project_calendar_D145 import confirmed_months
    config = configuration(horizon, name)
    source = object_or_empty(raw)
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    require(source.get("policy") == CALENDAR_POLICY and source.get("rules") == CALENDAR_RULES
            and synthetic_id(source.get("policy_ref")), "holding_calendar_policy_unconfirmed")
    rows = {r["value_cell"].split("!")[1]:r for r in review["rows"]}
    construction, lease_up = confirmed_months(rows, "C46", 3), confirmed_months(rows, "C47", 0)
    start, tco = day(purchase_date), day(record.get("tco_date"))
    require(start is not None and start.day == 1 and start.month in (1,4,7,10)
            and record.get("construction_start") == purchase_date and synthetic_id(record.get("start_ref")),
            "holding_construction_start_unconfirmed")
    finish = offset(start, construction)
    require(tco is not None and tco.day == 1 and tco.month in (1,4,7,10) and tco == finish
            and synthetic_id(record.get("tco_ref")), "holding_tco_conflicts_with_construction_or_quarter_grid")
    stabilized = offset(tco, lease_up)
    sale = offset(stabilized, config["holding_months"])
    require(isinstance(sale_term, dict) and sale_term.get("value") == sale.isoformat()
            and synthetic_id(sale_term.get("source_ref")), "holding_sale_date_must_match_stabilization_plus_horizon")
    shortfall, early = (amount(record.get(k)) for k in ("lease_up_shortfall_per_month", "upfront_direct_hard_share"))
    require(shortfall is not None and shortfall >= 0 and early is not None and 0 <= early <= 1
            and synthetic_id(record.get("lease_up_cash_ref")) and synthetic_id(record.get("construction_draw_ref")),
            "holding_preopening_funding_or_cash_timing_unconfirmed")
    months = (sale.year-start.year)*12+sale.month-start.month
    require(months % 3 == 0 and months <= 192, "holding_horizon_exceeds_verified_equity_grid")
    return dict(profile=PROFILE, policy_ref=source["policy_ref"], rules=source["rules"],
        holding_months=config["holding_months"], holding_source_ref=config["source_ref"],
        cell_sources={c:rows[c].get("sensitivity_value_source_ref",f"sha256:{review['workbook_sha256']}#{rows[c]['value_cell']}")
                      for c in ("C46","C47")},
        purchase_date=purchase_date, construction_start=purchase_date, construction_start_ref=record["start_ref"],
        upfront_date=offset(start,3).isoformat(), construction_months=construction, construction_finish=finish.isoformat(),
        tco_date=tco.isoformat(), tco_ref=record["tco_ref"], lease_up_months=lease_up,
        stabilization_date=stabilized.isoformat(), refinance_date=stabilized.isoformat(),
        sale_date=sale.isoformat(), sale_source_ref=sale_term["source_ref"], exit_forward_end=offset(sale,12).isoformat(),
        operating_window=[stabilized.isoformat(),sale.isoformat()],
        noi_window_starts={OPERATING_PERIOD:stabilized.isoformat(),FORWARD_PERIOD:sale.isoformat(),
                           BANK_PERIOD:stabilized.isoformat(),VALUE_PERIOD:stabilized.isoformat()},
        equity_dates=[offset(start,m).isoformat() for m in range(0,months+1,3)], payment_dates=[],
        lease_up_funding=rational(shortfall*lease_up),lease_up_shortfall_per_month=rational(shortfall),
        lease_up_cash_ref=record["lease_up_cash_ref"],upfront_direct_hard_share=rational(early),
        construction_draw_ref=record["construction_draw_ref"])


def engines():
    anchor, transport = cash_engine()
    env = anchor.__globals__
    investor = env["bind_closing"].__globals__["assemble_closing_returns"].__globals__["produce_investor_returns"]
    return env | dict(investor=investor, transport=transport,
                      operating_cash=env["reconcile_year"].__globals__["operating_cash"])


def construction_rows(funding):
    rows=[]
    for row in funding["cash_by_date"]:
        draw, equity, use, interest, fee = (amount(row[k]) for k in
            ("loan_draw","equity_contribution","project_uses","interest_paid","origination_fee_paid"))
        rows.append(dict(date=row["date"],stage="construction",opening_free=amount(row["opening_free_cash"]),
            opening_restricted=Fraction(),sources=draw+equity,uses=use+interest+fee,
            closing_free=amount(row["closing_free_cash"]),closing_restricted=Fraction(),
            contribution=equity,distribution=Fraction(),debt_interest=interest,debt_principal=Fraction(),
            source_ref=f"sha256:{digest(funding)}#/cash_by_date/{len(rows)}"))
    return rows


def verify_rows(rows):
    for row in rows:
        require(row["opening_free"]+row["opening_restricted"]+row["sources"] ==
                row["uses"]+row["closing_free"]+row["closing_restricted"],
                "holding_cash_conservation_failed:"+row["date"]+":"+row["stage"])
        require(min(row[k] for k in ("opening_free","opening_restricted","sources","uses","closing_free",
                                     "closing_restricted","contribution","distribution")) >= 0,
                "holding_negative_gross_cash_or_stock")
    for prior,row in zip(rows,rows[1:]):
        require(prior["date"] <= row["date"] and prior["closing_free"] == row["opening_free"]
                and prior["closing_restricted"] == row["opening_restricted"],"holding_cash_stock_discontinuity")


def investor_story(env, context, calendar, rows, config, retained):
    verify_rows(rows)
    events=[]
    ledger_ref=f"sha256:{digest(rows)}"
    for i,row in enumerate(rows):
        initial=i==0
        for kind,value in (("contribution",row["contribution"]),("distribution",row["distribution"])):
            category = ("initial_capital" if initial else "refinance_cash_in" if row["stage"]=="refinance" else "additional_capital") if kind=="contribution" else {
                "construction":"other_distribution","construction_hold":"other_distribution","refinance":"net_refinance_distribution",
                "operation":"operating_distribution","sale":"net_sale_distribution"}[row["stage"]]
            events.append(dict(event_id=f"{row['stage']}-{i}-{kind}",date=row["date"],kind=kind,category=category,
                               amount=rational(value),currency="USD",source_ref=f"{ledger_ref}#/{i}/{kind}"))
    require(rows[0]["contribution"]==amount(config["initial_equity"]["value"]),"holding_initial_equity_does_not_match_ledger")
    spec=template("synthetic-closing-investor-slots")
    spec.update(context=context,event_inventory_declared_complete=True,
        grid=dict(spacing="calendar_months_same_day",step_months=3,dates=calendar["equity_dates"],timing_basis_ref=calendar["policy_ref"]),
        events=events,normalization=dict(reference_amount=rational(10),contribution_event_ids=[events[0]["event_id"]],
                                       basis_ref=config["initial_equity"]["source_ref"]),annual_cash_bases=[],
        capital_snapshots=[dict(as_of_date=calendar["refinance_date"],capital_still_invested=rational(max(Fraction(),retained[0])),
            retained_equity_value=rational(retained[1]),currency="USD",basis_ref=config["source_ref"],source_ref=ledger_ref),
            dict(as_of_date=calendar["sale_date"],capital_still_invested=rational(0),retained_equity_value=rational(0),
                 currency="USD",basis_ref=config["source_ref"],source_ref=ledger_ref)])
    raw=encoded(spec)
    run=env["investor"](raw)
    result=run.payload
    require(result["cash_metrics_state"]=="computed_synthetic" and result["normalized_story"] is not None
            and result["normalized_story"]["events"] is not None,"holding_return_cash_unavailable")
    cash=result["normalized_story"]
    return cash | dict(unrecovered_after_sale=rational(max(Fraction(),-amount(cash["net_cash_profit"])))),dict(
        investor_source_sha256=sha256(raw).hexdigest(),investor_run_sha256=run.sha256,
        cash_by_period=serial(rows),cash_ledger_sha256=digest(rows),equity_source=spec,
        cash_metrics={k:result[k] for k in ("gross_contributions","gross_distributions","net_cash_profit","equity_multiple")},
        story_blockers=result["story_blockers"])


def annual_aggregate(env, context, calendar, years, operations, reserve, opening_free, config):
    """Reproduce the sum of yearly accruals and every gross quarterly cash movement."""
    period="SYNTHETIC-D266-complete-holding-operations"
    def row(value, source, item=None):
        result=dict(value=rational(value),currency="USD",period_ref=period,unit="currency_per_declared_period",
                    basis="accrual",source_ref=source)
        return result if item is None else result|dict(item_id=item)
    taxes=sum(amount(item["assembly"].noi_run.payload["property_tax"]) for item in years)
    spec=dict(schema=operating_noi.SCHEMA,profile_id=operating_noi.PROFILE,context=context,currency="USD",period_ref=period,
        income_rows=[row(amount(y["assembly"].noi_run.payload["income_total"]),f"sha256:{y['assembly'].noi_run.sha256}",f"income-{i}") for i,y in enumerate(years)],
        expense_rows=[row(amount(y["assembly"].noi_run.payload["expenses_excluding_tax"]),f"sha256:{y['assembly'].noi_run.sha256}",f"cost-{i}") for i,y in enumerate(years)],
        tax_floor=row(taxes,config["cash_assumptions_ref"]),
        tax_coefficient=dict(value=rational(0),unit="scalar",source_ref=config["cash_assumptions_ref"]),
        modelling_assumptions=operating_noi.ASSUMPTIONS)
    noi_raw=encoded(spec)
    noi=operating_noi.produce_operating_noi(noi_raw)
    require(not noi.payload["blockers"],"holding_aggregate_noi_unavailable")
    cashmod=env["operating_cash"]
    def claim(value,ref=period):
        return dict(value=rational(value),currency="USD",period_ref=ref,source_ref=config["cash_assumptions_ref"])
    source=template("synthetic-operating-cash")
    values=dict(operating_receipts_claim=sum(amount(y["assembly"].noi_run.payload["income_total"]) for y in years),
        operating_payments_claim=sum(amount(y["assembly"].noi_run.payload[k]) for y in years for k in ("expenses_excluding_tax","property_tax")),
        debt_principal_payment=sum(r["debt_principal"] for r in operations),debt_interest_payment=sum(r["debt_interest"] for r in operations),
        reserve_deposit=reserve,planned_operating_distribution=sum(r["distribution"] for r in operations),
        equity_contribution=sum(r["contribution"] for r in operations))
    source.update(context=context,period_ref=period,start_date=calendar["stabilization_date"],
        end_date=(day(calendar["sale_date"])+timedelta(days=1)).isoformat(),cash_date=calendar["sale_date"],
        noi_source_sha256=sha256(noi_raw).hexdigest(),noi_run_sha256=noi.sha256,
        period_basis_ref=config["source_ref"],distribution_basis_ref=config["cash_assumptions_ref"],classification_basis_ref=config["cash_assumptions_ref"],
        working_balances={k:dict(opening=claim(0,"OPENING:"+period),closing=claim(0,"CLOSING:"+period)) for k in cashmod.WORKING},
        amounts={k:claim(values.get(k,0)) for k in cashmod.FLOWS+cashmod.ADJUSTMENTS+cashmod.CLAIMS}|
            {k:claim(reserve if k=="closing_restricted_cash_claim" else opening_free if k in ("opening_free_cash","closing_free_cash_claim") else 0,prefix+period)
             for k,prefix in cashmod.STOCKS.items()})
    raw=encoded(source)
    run=cashmod.reconcile_operating_cash(noi_raw,noi,raw)
    require(not run.payload["blockers"],"holding_aggregate_operating_cash_unavailable:"+",".join(run.payload["blockers"]))
    return run,dict(noi_source=spec,noi_run_sha256=noi.sha256,cash_source=source,cash_run_sha256=run.sha256)


def funded_closing(env, raw, config):
    source=json.loads(raw)
    run=env["closing_cash"].produce_closing_cash(raw)
    required=amount(run.payload.get("projected_equity_contribution_required"))
    if required is not None and required > 0:
        require(config["closing_funding"]["policy"]=="equity_top_up", "holding_closing_shortfall_requires_confirmed_funding")
        source["equity_funding_assumption_ref"]=config["closing_funding"]["source_ref"]
        raw=encoded(source)
        run=env["closing_cash"].produce_closing_cash(raw)
    require(not run.payload["blockers"], "holding_closing_unavailable:"+",".join(run.payload["blockers"]))
    return raw,run


def operation_rows(calendar, years, schedule, reserve, opening_free, permanent_balance, config):
    require(len(schedule)==calendar["holding_months"]//3, "holding_debt_schedule_incomplete")
    rows=[]
    restricted=permanent_balance
    deposit=amount(reserve["deposit"])/4
    for index,payment in enumerate(schedule):
        year=index//4
        n=years[year]["assembly"].noi_run.payload
        income=amount(n["income_total"])/4
        expenses=(amount(n["expenses_excluding_tax"])+amount(n["property_tax"]))/4
        service,interest,capital=(amount(payment[k]) for k in ("scheduled_service_due","interest_due","principal_due"))
        require(service is not None and interest is not None and capital is not None
                and service==interest+capital and min(service,interest,capital)>=0,"holding_debt_service_unconfirmed")
        when=offset(day(calendar["stabilization_date"]),3*(index+1)).isoformat()
        require(payment["date"]==when,"holding_debt_dates_do_not_match_stabilized_quarters")
        net=income-expenses-service-deposit
        contribution,distribution=max(Fraction(),-net),max(Fraction(),net)
        rows.append(dict(date=when,stage="operation",year=year+1,
            opening_free=opening_free,opening_restricted=restricted,sources=income+contribution,
            uses=expenses+service+distribution,closing_free=opening_free,closing_restricted=restricted+deposit,
            contribution=contribution,distribution=distribution,debt_interest=interest,debt_principal=capital,
            noi=income-expenses,reserve_deposit=deposit,
            source_ref=f"sha256:{years[year]['assembly'].noi_run.sha256}"))
        restricted+=deposit
    verify_rows(rows)
    return rows


def sale_close(env,context,calendar,operating,exit_run,costs,reserve,permanent,principal,loan_id,config):
    raw=encoded(env["sale_source"](context,operating,exit_run,sale_date=calendar["sale_date"],
        replacement_reserve=reserve,sale_costs=costs,permanent_reserve=permanent))
    source=json.loads(raw)
    debt=dict(loan_id=loan_id)
    for category in env["closing_cash"].DUE:
        for role,basis in (("due","debt_obligation_before_closing"),("paid","cash_flow_at_closing")):
            debt[f"{category}_{role}"]=dict(value=rational(principal if category=="principal" else 0),
                currency="USD",as_of_date=calendar["sale_date"],basis=basis,
                source_ref=config["source_ref"]+"/regular-payments-settled-before-single-sale-payoff")
    source["old_debts"]=[debt]
    return funded_closing(env,encoded(source),config)


def append_sale(rows,closing,raw,config):
    proof=closing.payload
    claims=json.loads(raw)["amounts"]
    contribution=amount(proof["exportable_equity_contribution"])
    gross=amount(claims["gross_proceeds"]["value"])
    costs=amount(claims["closing_costs_paid"]["value"])
    principal=amount(proof["payoff_totals"]["principal"])
    distribution=amount(proof["exportable_equity_distribution"])
    rows.append(dict(date=proof["closing_date"],stage="sale",opening_free=rows[-1]["closing_free"],
        opening_restricted=rows[-1]["closing_restricted"],sources=gross+contribution,
        uses=costs+principal+distribution,closing_free=amount(claims["retained_free_cash"]["value"]),
        closing_restricted=amount(proof["expected_closing_restricted_cash"]),
        contribution=contribution,distribution=distribution,debt_interest=Fraction(),debt_principal=principal,
        source_ref=f"sha256:{closing.sha256}"))
    verify_rows(rows)


def yearly_cash(calendar,years,operations,cash):
    scale=amount(cash["scale_factor"])
    annual=[]
    for i,item in enumerate(years):
        quarters=operations[4*i:4*i+4]
        noi=amount(item["assembly"].noi_run.payload["noi"])
        reserve=sum(row["reserve_deposit"] for row in quarters)
        service=sum(row["debt_interest"]+row["debt_principal"] for row in quarters)
        annual.append(dict(index=i+1,start=offset(day(calendar["stabilization_date"]),12*i).isoformat(),
            end=offset(day(calendar["stabilization_date"]),12*(i+1)).isoformat(),noi=noi,noi_uw=noi-reserve,
            reserve_deposit=reserve,debt_service=service,
            interest=sum(row["debt_interest"] for row in quarters),principal=sum(row["debt_principal"] for row in quarters),
            contributions=sum(row["contribution"] for row in quarters)*scale,
            distributions=sum(row["distribution"] for row in quarters)*scale,
            payments=[dict(date=row["date"],contribution=row["contribution"]*scale,receipt=row["distribution"]*scale) for row in quarters],
            noi_source_sha256=sha256(item["assembly"].compiled_raw).hexdigest(),noi_run_sha256=item["assembly"].noi_run.sha256))
    return serial(annual)


def without_refinance(env,context,calendar,funding,years,forward,exit_run,costs,reserve,config,retained_value):
    terms=config["without_refinance"]
    if terms["applicability"]=="not_requested":
        return dict(state="not_requested",cash_per_usd_10=None,blockers=[],source_ref=terms["source_ref"])
    try:
        require(day(funding["debt_source"]["maturity_date"])>=day(calendar["sale_date"]),
                "holding_construction_loan_matures_before_sale_without_refinance")
        source=deepcopy(funding["debt_source"])
        source["end_date"]=calendar["sale_date"]
        source["nonrevolving_commitment_basis_ref"]=terms["source_ref"]
        final=source["periods"][-1]
        final["principal_repayment_at_end"].update(value=rational(0),source_ref=terms["source_ref"])
        principal=amount(funding["construction_principal_payoff"])
        for index in range(calendar["holding_months"]//3):
            start=offset(day(calendar["stabilization_date"]),3*index).isoformat()
            end=offset(day(calendar["stabilization_date"]),3*(index+1)).isoformat()
            item=deepcopy(final)
            period=f"SYNTHETIC-D266-hold-{index+1}"
            item.update(period_id=period,start_date=start,end_date=end,interval_basis_ref=config["source_ref"])
            for key,value in (("draw_at_start",0),("available_new_draw",0),("principal_repayment_at_end",principal if end==calendar["sale_date"] else 0)):
                item[key].update(value=rational(value),source_ref=terms["source_ref"])
            item["interest_fraction"].update(value=rational(amount(funding["annual_interest"])/4),interval_ref=period,
                                               source_ref=terms["source_ref"])
            source["periods"].append(item)
        run=produce_construction_draws(encoded(source))
        proof=run.payload
        require(not proof["blockers"],"holding_construction_continuation_unavailable")
        tail=proof["periods"][-calendar["holding_months"]//3:]
        schedule=[dict(date=r["end_date"],scheduled_service_due=r["interest_due_at_end"],
                       interest_due=r["interest_due_at_end"],principal_due=rational(0)) for r in tail]
        rows=construction_rows(funding)
        fee=amount(terms["fee_at_stabilization"]["value"])
        free=rows[-1]["closing_free"]
        topup=max(Fraction(),fee-free)
        free=free+topup-fee
        rows.append(dict(date=calendar["stabilization_date"],stage="construction_hold",opening_free=rows[-1]["closing_free"],
            opening_restricted=Fraction(),sources=topup,uses=fee,closing_free=free,closing_restricted=Fraction(),
            contribution=topup,distribution=Fraction(),debt_interest=Fraction(),debt_principal=Fraction(),source_ref=terms["source_ref"]))
        operations=operation_rows(calendar,years,schedule,reserve,free,Fraction(),config)
        rows.extend(operations)
        total_reserve=amount(reserve["deposit"])*len(years)
        operating,aggregate=annual_aggregate(env,context,calendar,years,operations,total_reserve,free,config)
        sale_raw,sale=sale_close(env,context,calendar,operating,exit_run,costs,reserve|dict(deposit=rational(total_reserve)),
                               None,principal,proof["loan_id"],config)
        require(amount(sale.payload["payoff_totals"]["principal"])==amount(tail[-1]["principal_repayment_at_end"]),
                "holding_construction_payoff_must_occur_once_at_sale")
        append_sale(rows,sale,sale_raw,config)
        retained=(sum(row["contribution"] for row in rows if row["date"]<=calendar["stabilization_date"]),
                  retained_value-principal)
        cash,evidence=investor_story(env,context,calendar,rows,config,retained)
        return dict(state="computed_synthetic",blockers=[],cash_per_usd_10=cash,
            annual_cash=yearly_cash(calendar,years,operations,cash),sale=serial(dict(date=calendar["sale_date"],
                gross=amount(exit_run.payload["candidate_value"]),cost=amount(costs.payload["total_closing_cost"]),principal=principal)),
            construction_hold_debt=dict(source=source,run_sha256=run.sha256,run=proof),
            operating_aggregate=aggregate,sale_closing= sale.payload,sale_source=json.loads(sale_raw),
            irr=horizon_irr(cash,calendar["equity_dates"]),**evidence)
    except (ValueError,TypeError,KeyError) as error:
        return pending(str(error))


def calculate(context,name,config,calendar,funding,principal,valuation_terms,permanent_terms,refinance_costs,
              reserve,buyer_tax,debt_yield_terms,noi_for,years):
    from worksheet_debt_yield_D178 import debt_yield_capacity
    from worksheet_exit_pricing_D151 import price_sale_costs
    from worksheet_refinance_costs_D153 import settle_permanent_reserve
    from worksheet_annual_coc import SCHEMA as COC_SCHEMA,verify_annual_coc
    from worksheet_formula_review_D173 import COC_BASIS
    from worksheet_performance_policy_D184 import AFTER_RESERVES
    env=engines()
    forward=noi_for(FORWARD_PERIOD)
    valuation,bank=noi_for(VALUE_PERIOD),noi_for(BANK_PERIOD)
    require(all(not x.payload["blockers"] and x.noi_run is not None for x in [forward,valuation,bank]+[y["assembly"] for y in years]),
            "holding_computed_noi_incomplete")
    exit_run=env["value_at_exit"](forward,context,amount(valuation_terms["exit_cap"]),sale_date=calendar["sale_date"],
        forward_end=calendar["exit_forward_end"],cap_source_ref=valuation_terms["cell_sources"]["C67"],
        sale_at_value_ref=valuation_terms["sale_at_value_ref"],window_basis_ref=f"sha256:{buyer_tax['source_sha256']}")
    require(not exit_run.payload["blockers"],"holding_exit_value_unavailable")
    costs=price_sale_costs(exit_run,valuation_terms)
    require(not costs.payload["blockers"],"holding_sale_costs_unavailable")
    alternative=without_refinance(env,context,calendar,funding,years,forward,exit_run,costs,reserve,config,
                                 amount(valuation.noi_run.payload["noi"])/amount(valuation_terms["refinance_cap"]))
    result=dict(state="PENDING",cash_per_usd_10=None,capacity=None,
        holding_horizon=dict(profile=PROFILE,months=calendar["holding_months"],stabilization_date=calendar["stabilization_date"],
            sale_date=calendar["sale_date"],source_ref=config["source_ref"],rules=RULES,
            engine_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),exact_transport=env["transport"],
            annual_noi=[dict(index=i+1,source_sha256=sha256(y["assembly"].compiled_raw).hexdigest(),
                            run_sha256=y["assembly"].noi_run.sha256,producer=y["assembly"].noi_run.payload) for i,y in enumerate(years)]),
        horizon_without_refinance=alternative,
        valuation_and_sale=valuation_terms|dict(refinance_date=calendar["refinance_date"],sale_date=calendar["sale_date"],
            forward_noi=exit_run.payload["forward_noi"],forward_window=exit_run.payload["forward_window"],
            gross_sale_price=exit_run.payload["candidate_value"],sale_cost=costs.payload["total_closing_cost"],
            sale_cost_run=costs.payload,sale_cost_run_sha256=costs.sha256,buyer_property_tax=buyer_tax))
    loan=env["loan_evidence"](context,principal,refi_date=calendar["refinance_date"],
        payment_dates=calendar["payment_dates"],permanent_terms=permanent_terms)
    loan_run=loan.run.payload
    result["permanent_loan"]=permanent_terms|dict(origination_date=calendar["refinance_date"],requested_principal=rational(principal),
        loan_source_sha256=sha256(loan.loan_raw).hexdigest(),loan_run_sha256=loan.run.sha256,projected_schedule=loan_run["schedule"],
        regular_payment_due=loan_run["regular_payment_due"],annual_sizing_service=loan_run["annual_sizing"]["amount"],
        quote_state=loan_run["schedule_state"])
    require(not loan_run["schedule_blockers"],"holding_permanent_loan_schedule_unavailable")
    if calendar["sale_date"] not in permanent_terms["payment_dates"]:
        return result|dict(blockers=["holding_permanent_loan_matures_before_horizon_sale"])
    refi_raw,_=env["refi_closing"](context,loan,principal,refi_date=calendar["refinance_date"],
        construction_financing=funding,refinance_costs=refinance_costs)
    try:
        refi_raw,refi=funded_closing(env,refi_raw,config)
    except (ValueError,TypeError,KeyError) as error:
        return result|dict(blockers=[str(error)])
    refi_view=refi.payload
    claims=json.loads(refi_raw)["amounts"]
    result["construction_refinance"]=dict(date=calendar["refinance_date"],gross_proceeds=rational(principal),
        closing_fee=claims["closing_costs_paid"]["value"],prior_principal_paid=refi_view["payoff_totals"]["principal"],
        net_equity_distribution=refi_view["exportable_equity_distribution"],blockers=[],
        closing_source_sha256=sha256(refi_raw).hexdigest(),closing_run_sha256=refi.sha256,
        permanent_reserve_deposit=claims["new_reserve"]["value"],opening_free_cash=claims["opening_free_cash"]["value"],
        closing_restricted_cash=refi_view["expected_closing_restricted_cash"],
        projected_cash_in_required=refi_view["exportable_equity_contribution"],closing_cash_residual=refi_view["total_cash_conservation_residual"])
    dy=debt_yield_capacity(debt_yield_terms,bank.noi_run.payload["noi"],principal)
    cap_run=env["capacity_check"](context,valuation,bank,loan,refi_raw,refi,principal,refi_date=calendar["refinance_date"],
        valuation_terms=valuation_terms,permanent_terms=permanent_terms,debt_yield=dy)
    cap=cap_run.payload
    result["capacity"]={k:cap[k] for k in ("valuation_noi","bank_noi","selected_principal","maximum_principal_capacity",
        "binding_limit_ids","capacity_limits","capacity_state","state","as_of_date","input_bindings")}|dict(capacity_run_sha256=cap_run.sha256,debt_yield=dy)
    result["valuation_and_sale"].update(refinance_noi=cap["valuation_noi"],refinance_value=cap["computed_property_value"])
    if cap["state"]!="compatible_synthetic_refinance_capacity":
        result["construction_refinance"]["net_equity_distribution"]=None
        return result|dict(blockers=cap["blockers"])
    rows=construction_rows(funding)
    deposit=amount(claims["new_reserve"]["value"])
    payout=amount(refi_view["exportable_equity_distribution"])
    topup=amount(refi_view["exportable_equity_contribution"])
    fee=amount(claims["closing_costs_paid"]["value"])
    paid=amount(refi_view["payoff_totals"]["principal"])
    rows.append(dict(date=calendar["refinance_date"],stage="refinance",opening_free=rows[-1]["closing_free"],
        opening_restricted=Fraction(),sources=principal+topup,uses=fee+paid+payout,
        closing_free=amount(claims["retained_free_cash"]["value"]),closing_restricted=deposit,
        contribution=topup,distribution=payout,debt_interest=Fraction(),debt_principal=paid,source_ref=f"sha256:{refi.sha256}"))
    schedule=[r for r in loan_run["schedule"] if r["date"]<=calendar["sale_date"]]
    operations=operation_rows(calendar,years,schedule,reserve,rows[-1]["closing_free"],deposit,config)
    rows.extend(operations)
    total_reserve=amount(reserve["deposit"])*len(years)
    operating,aggregate=annual_aggregate(env,context,calendar,years,operations,total_reserve,
                                       amount(claims["retained_free_cash"]["value"]),config)
    permanent=settle_permanent_reserve(refi,refinance_costs,calendar["sale_date"])
    sale_raw,sale=sale_close(env,context,calendar,operating,exit_run,costs,reserve|dict(deposit=rational(total_reserve)),
        permanent,amount(schedule[-1]["closing_balance"]),loan_run["loan_id"],config)
    debt_spec=template("synthetic-project-sale-debt-binding")
    debt_spec.update(context=context,closing_source_sha256=sha256(sale_raw).hexdigest(),closing_run_sha256=sale.sha256)
    debt_spec["loans"][0].update(loan_id=loan_run["loan_id"],loan_source_sha256=sha256(loan.loan_raw).hexdigest(),
        loan_run_sha256=loan.run.sha256,payment_cutoff="after_regular_payment_before_balloon",cutoff_basis_ref=config["source_ref"])
    debt_check=env["reconcile_debt_closing"]((loan,),sale_raw,sale,encoded(debt_spec))
    require(not debt_check.payload["blockers"],"holding_sale_debt_reconciliation_failed")
    append_sale(rows,sale,sale_raw,config)
    retained=sum(r["contribution"] for r in rows if r["date"]<=calendar["refinance_date"])-payout
    cash,returns=investor_story(env,context,calendar,rows,config,(retained,amount(cap["computed_property_value"])-principal))
    result.update(state="computed_synthetic",blockers=[],cash_per_usd_10=cash,dated_debt_service=schedule[-1],
        debt_principal_paid_at_sale=sale.payload["payoff_totals"]["principal"],gross_sale=exit_run.payload["candidate_value"],
        replacement_reserve=reserve|dict(total_deposited=rational(total_reserve),deposit_dates=[r["date"] for r in operations],
            restricted_before_sale=rational(total_reserve),released_at_sale=rational(total_reserve*amount(reserve["sale_release_fraction"])),
            transferred_restricted_to_buyer=rational(total_reserve*(1-amount(reserve["sale_release_fraction"]))),sale_date=calendar["sale_date"]),
        permanent_reserve=permanent,source_runs=dict(operating_cash_sha256=operating.sha256,exit_value_sha256=exit_run.sha256,
            sale_closing_sha256=sale.sha256,debt_check_sha256=debt_check.sha256,equity_returns_sha256=returns["investor_run_sha256"]))
    result["holding_horizon"].update(annual_cash=yearly_cash(calendar,years,operations,cash),**returns,
        operating_aggregate=aggregate,sale_source=json.loads(sale_raw),sale_closing=sale.payload,debt_check=debt_check.payload)
    coc_source=dict(schema=COC_SCHEMA,noi_basis=AFTER_RESERVES,source_ref=config["cash_assumptions_ref"],quarters=[dict(
        start=offset(day(calendar["refinance_date"]),3*i).isoformat(),end=row["date"],
        noi_after_reserves=rational(row["noi"]-row["reserve_deposit"]),source_ref=config["cash_assumptions_ref"])
        for i,row in enumerate(operations[:4])])
    view=result|dict(project_calendar=calendar)
    coc=verify_annual_coc(view,coc_source)
    result["post_refinance_coc"]=dict(definition=COC_BASIS,value=coc.get("value"),annualized=False,noi_basis=AFTER_RESERVES,
        window_start=calendar["refinance_date"],window_end=offset(day(calendar["refinance_date"]),12).isoformat(),
        period_noi=coc.get("noi_after_reserves"),equity_still_invested=coc.get("equity_remaining"),
        scheduled_debt_service=coc.get("scheduled_debt_service"),blockers=[] if coc.get("blocker") is None else [coc["blocker"]],
        annual_proof=coc,source=coc_source)
    return result


def render_horizon(views,screening,*,delivery_report=False):
    """One external page; quarterly source movements remain in the audited bundle."""
    from worksheet_sale_rate_grid_D84 import money
    from worksheet_irr_D122 import display_enclosure
    from miniuw_foundation.synthetic_onepager import _pdf,_pdf_string
    columns=[]
    for name,view in views.items():
        columns.append((name+" refi",view,view.get("holding_horizon",{})))
        alternative=object_or_empty(view.get("horizon_without_refinance"))
        columns.append((name+" sin refi",alternative,alternative))
    def value(cash,key,index):
        return ("N/A" if columns[index][1].get("state")=="not_requested" else "PENDING") if cash is None or cash.get(key) is None else money(cash[key])
    def table(label,cells,bold=False):
        return (f"{label:<27} | "+" | ".join(f"{cell:>17}" for cell in cells),bold)
    cashes=[view.get("cash_per_usd_10") for _,view,_ in columns]
    unavailable=["N/A" if view.get("state")=="not_requested" else "PENDING" for _,view,_ in columns]
    lines=[("Dictamen real PENDING | Retorno personal sin reparto PENDING | Datos sintéticos",True),
           ("Equity agregado. USD por USD 10 iniciales; aportes extra y cobros brutos separados.",False),
           table("Ruta",[name for name,_,_ in columns],True),
           table("Aporte inicial",["10,00" if c else unavailable[i] for i,c in enumerate(cashes)]),
           table("Aportes adicionales",[unavailable[i] if c is None else money(rational(amount(c["total_contributions"])-10)) for i,c in enumerate(cashes)]),
           table("Cobros totales",[value(c,"total_distributions",i) for i,c in enumerate(cashes)],True),
           table("Resultado neto",[value(c,"net_cash_profit",i) for i,c in enumerate(cashes)]),
           table("Caja sin recuperar",[value(c,"unrecovered_after_sale",i) for i,c in enumerate(cashes)]),
           table("Múltiplo",[value(c,"equity_multiple",i) for i,c in enumerate(cashes)])]
    irr=[]
    for index,(name,view,_) in enumerate(columns):
        scenario=name.split()[0]
        record=object_or_empty(view.get("irr")) if name.endswith("sin refi") else object_or_empty(screening.get("irr_by_scenario",{}).get(scenario))
        irr.append(unavailable[index] if cashes[index] is None else display_enclosure(record.get("annual_enclosure")))
    lines.append(table("TIR anual",irr))
    constructions={}
    for index,(_,_,evidence) in enumerate(columns):
        for row in evidence.get("cash_by_period",[]):
            if row["stage"] in ("construction","construction_hold") and amount(row["contribution"])>0:
                constructions.setdefault(row["date"],{})[index]=amount(row["contribution"])*amount(cashes[index]["scale_factor"])
    if constructions:
        lines.append(("Aportes de compra/obra/retención por fecha; — indica que no hay movimiento.",True))
        for when,by_column in sorted(constructions.items()):
            lines.append(table(when,[unavailable[i] if cashes[i] is None else money(rational(by_column[i])) if i in by_column else "—" for i in range(4)]))
    for name,view in views.items():
        cal=object_or_empty(view.get("project_calendar"))
        holding=object_or_empty(view.get("holding_horizon"))
        if holding:
            lines.append((f"{name}: estabiliza {holding['stabilization_date']} | venta {holding['sale_date']} | {holding['months']} meses",True))
        cash=view.get("cash_per_usd_10")
        if cash:
            close=view["construction_refinance"]
            scale=amount(cash["scale_factor"])
            lines.append((f"{name} refi {close['date']}: aporta {money(rational(amount(close['projected_cash_in_required'])*scale))}"
                f" / cobra {money(rational(amount(close['net_equity_distribution'])*scale))} | Sin refi: N/A",False))
        elif view.get("blockers"):
            lines.append((name+" refi PENDING: "+str(view["blockers"][0]),False))
    max_years=max((len(evidence.get("annual_cash",[])) for _,_,evidence in columns),default=0)
    for year in range(max_years):
        dates=[]
        for scenario in ("Base","Downside"):
            records=next((evidence.get("annual_cash",[]) for name,_,evidence in columns
                          if name.startswith(scenario) and len(evidence.get("annual_cash",[]))>year),[])
            dates.append("PENDING" if not records else ",".join(row["date"] for row in records[year]["payments"]))
        lines.append((f"Año {year+1} | Fechas Base {dates[0]} | Downside {dates[1]}",False))
        cells=[]
        for index,(_,_,evidence) in enumerate(columns):
            annual=evidence.get("annual_cash",[])
            if len(annual)<=year:
                cells.append(unavailable[index])
                continue
            payments=annual[year]["payments"]
            pairs={(amount(r["contribution"]),amount(r["receipt"])) for r in payments}
            require(len(pairs)==1,"holding_report_requires_explicit_nonuniform_quarter_layout")
            contribution,receipt=pairs.pop()
            cells.append(money(rational(contribution))+" / "+money(rational(receipt)))
        lines.append(table("Aporta / cobra CADA fecha",cells))
    for scenario in ("Base","Downside"):
        values=[]
        when=None
        for name,view,evidence in columns:
            if not name.startswith(scenario):continue
            sale=next((r for r in evidence.get("cash_by_period",[]) if r["stage"]=="sale"),None)
            if sale is None:values.append("N/A" if view.get("state")=="not_requested" else "PENDING");continue
            when=sale["date"]
            scale=amount(view["cash_per_usd_10"]["scale_factor"])
            values.append("aporta "+money(rational(amount(sale["contribution"])*scale))+" / cobra "+money(rational(amount(sale["distribution"])*scale)))
        lines.append((f"{scenario} venta {when or 'PENDING'}: refi {values[0]} | sin refi {values[1]}",True))
    lines.append(("Venta: después de la cuota final, una sola cancelación de deuda y liberación documentada de reservas.",False))
    lines.append(("Los criterios o bases sin confirmar conservan PENDING; el múltiplo/TIR no autorizan una inversión.",False))
    lines.append(("Importes redondeados sólo para mostrar. La caja sin recuperar corresponde al horizonte de este ensayo.",False))
    size=min(9.0,430/max(1,len(lines)))
    require(size>=7.0 and all(len(label)*size*0.6<=736 for label,_ in lines),"holding_report_exceeds_one_readable_page")
    commands=[b"0.06 0.17 0.25 rg 24 524 744 64 re f"]
    headers=[(566,15,"MINI-UW | HORIZONTE DESDE ESTABILIZACIÓN"),(546,10,"Aportes y cobros por USD 10 | Base y Downside | Con y sin refi"),
             (532,7,"Ensayo sintético D266 | Sin despliegue ni decisiones reales")]
    for y,font,label in headers:
        commands.append(f"1 1 1 rg BT /F2 {font} Tf 1 0 0 1 36 {y} Tm (".encode()+_pdf_string(label)+b") Tj ET")
    spacing=min(12,438/max(1,len(lines)-1))
    for i,(label,bold) in enumerate(lines):
        y=498-spacing*i
        require(y>=60,"holding_report_height_exceeds_one_page")
        commands.append(f"0.06 0.17 0.25 rg BT /{'F2' if bold else 'F1'} {size} Tf 1 0 0 1 28 {y} Tm (".encode()+_pdf_string(label)+b") Tj ET")
    return _pdf(commands)
