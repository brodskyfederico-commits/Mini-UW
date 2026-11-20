"""Source-based AMI references and full financial reconciliation, synthetic only."""
from argparse import ArgumentParser
from copy import deepcopy
from datetime import date
from fractions import Fraction as Q
from math import isqrt
import json
from pathlib import Path

from check_worksheet_horizon_fiscal_D267 import source_cells, value, month
from check_worksheet_scenario_program_D268 import settings as previous_settings, drivers, make_packet, sources_for, reference_taxes
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded, read_package, CURRENT_REVISION_FILE, verify_package, deliver_package
from plan_return_D107 import OPERATING_PERIOD, FORWARD_PERIOD
from worksheet_intake_D198 import assemble, register
from worksheet_regulated_rent_D269 import PROFILE, RULES, GROUPS, SCHEMA, annual_starts


def settings(*, regulated=True):
    spec = previous_settings()
    spec["schema"] = SCHEMA
    spec["criteria_revision"] = "SYNTHETIC-D269-explicit-fixture-criteria"
    inputs = spec["rent_inputs"]
    # A separately declared synthetic bank proposal, identical in both controls.
    inputs["requested_principal"] = rational(1_000_000)
    source = dict(profile=PROFILE, currency="USD", rules=RULES, source_ref="SYNTHETIC-D269-flat-AMI-forecast-no-benefits", scenarios={})
    for name in ("Base", "Downside"):
        tco = date.fromisoformat(inputs["project_calendar"]["scenarios"][name]["tco_date"])
        stabilization = month(tco, 3 if name == "Base" else 6)
        allocations = {group: dict(regulated_units=1 if regulated else 0,
            market_units=inputs["groups"][group]["units"]-(1 if regulated else 0),
            source_ref=f"SYNTHETIC-D269-{name}-{group}-explicit-unit-allocation") for group in GROUPS.values()}
        windows = {}
        for year in range(6):
            start = month(stabilization, year*12)
            limits = {}
            for index, group in enumerate(GROUPS.values()):
                ref = f"SYNTHETIC-D269-{name}-{group}-{year}-declared-AMI-forecast"
                if not regulated:
                    limits[group] = dict(applicability="not_applicable", source_ref=ref)
                    continue
                limits[group] = dict(applicability="applicable", source_ref=ref,
                    imputed_household_size=index+1, household_basis_ref=ref+"-household-table",
                    annual_AMI_income=dict(value=rational(60_000+10_000*index), unit="USD_per_year", source_ref=ref+"-income"),
                    income_limit_fraction=dict(value=rational(Q(4,5)), unit="fraction", source_ref=ref+"-income-limit"),
                    rent_income_share=dict(value=rational(Q(3,10)), unit="fraction", source_ref=ref+"-rent-rule"),
                    utility_allowance_monthly=dict(value=rational(100), unit="USD_per_unit_per_month", source_ref=ref+"-tenant-utilities"))
            windows[str(start)] = dict(source_ref=f"SYNTHETIC-D269-{name}-{year}-flat-forecast",
                evidence_kind="synthetic_forecast", valid_from=str(start), valid_until_exclusive=str(month(start,12)), limits=limits)
        source["scenarios"][name] = dict(source_ref=f"SYNTHETIC-D269-{name}-rent-limits",
            leaseup_assumption_ref=f"SYNTHETIC-D269-{name}-calendar-net-shortfall-explicitly-retained-for-test",
            allocations=allocations, windows=windows)
    inputs["regulated_rent"] = source
    return spec


def reference_window(spec, sources, name, index):
    """Separate arithmetic from literal market rent and explicit AMI declarations."""
    inputs = spec["rent_inputs"]
    raw = inputs["regulated_rent"]; source = raw["scenarios"][name]
    _, cell = source_cells(sources, name)
    purchase = date.fromisoformat(inputs["development"]["scenarios"][name]["purchase_date"])
    stabilized = month(purchase, int(cell("C46")+cell("C47")))
    start = str(month(stabilized, 12*index)); end = str(month(stabilized, 12*(index+1)))
    window = source["windows"][start]
    groups = {}
    for target, group in GROUPS.items():
        allocation = source["allocations"][group]; limit = window["limits"][group]
        count = inputs["groups"][group]["units"]
        market = cell(target) * (1+cell("C75"))**index
        gross_cap, net_cap, charged = None, None, None
        if allocation["regulated_units"]:
            income = value(limit["annual_AMI_income"]["value"])
            ratio = value(limit["income_limit_fraction"]["value"])
            rent_share = value(limit["rent_income_share"]["value"])
            allowance = value(limit["utility_allowance_monthly"]["value"])
            gross_cap = income*ratio*rent_share/12; net_cap = gross_cap-allowance
            assert net_cap >= 0
            charged = min(market, net_cap)
            gross = (allocation["regulated_units"]*charged+allocation["market_units"]*market)*12
        else: gross = count*market*12
        effective = market if count == 0 else gross/(12*count)
        groups[group] = dict(units=count, allocation=allocation, market_rent=rational(market),
            gross_regulated_cap=None if gross_cap is None else rational(gross_cap),
            net_regulated_cap=None if net_cap is None else rational(net_cap),
            charged_regulated_rent=None if charged is None else rational(charged),
            effective_per_unit_monthly_rent=rational(effective), annual_gross_potential=rational(gross), limit=limit)
    proof = dict(state="checked_synthetic", blockers=[], profile=PROFILE, rules=RULES,
        source_ref=raw["source_ref"], scenario_source_ref=source["source_ref"], window=window,
        inputs_sha256=sha(encoded(raw)), window_start=start, window_end_exclusive=end,
        groups=groups, annual_gross_potential=rational(sum(value(g["annual_gross_potential"]) for g in groups.values())),
        owner_utility_expenses_modified=False, real_eligibility_confirmed=False)
    proof["source_sha256"] = sha(encoded(proof))
    return proof


def make_sources(spec, output, *, revision="SYNTHETIC-D269-01"):
    seed = sources_for(spec, output / "seed")
    spec, sources = make_packet(spec, seed, "269", [], drivers(), output / "sources", revision=revision)
    ref = json.loads(sources["independent_reference_raw"])
    ref["regulated_rents"] = {}
    for name in ("Base", "Downside"):
        windows = [reference_window(spec, sources, name, i) for i in range(6)]
        ref["regulated_rents"][name] = dict(inputs_sha256=sha(encoded(spec["rent_inputs"]["regulated_rent"])),
                                          windows={window["window_start"]:window for window in windows})
    sources["independent_reference_raw"] = encoded(ref)
    (output / "sources/Independent_Reference.json").write_bytes(sources["independent_reference_raw"])
    (output / "settings.json").write_bytes(encoded(spec))
    return spec, sources


def run(output, *, regulated=True):
    output.mkdir(parents=True, exist_ok=False)
    spec, sources = make_sources(settings(regulated=regulated), output,
                                revision="SYNTHETIC-D269-01" if regulated else "SYNTHETIC-D269-02")
    receipt = assemble(spec, register(sources, "SYNTHETIC-D269-regulated-rent" if regulated else "SYNTHETIC-D269-unregulated-control"),
                       sources, output / "package")
    saved = read_package(output / "package")
    (output / "receipt.json").write_bytes(encoded(receipt))
    return spec, sources, json.loads(saved["results.json"]), saved



def independently_verify(spec,sources,result):
    """Financial reference from literal cells and rolls, not the engine's totals."""
    checked={}
    for name in ("Base","Downside"):
        view=result["scenarios"][name]
        refi_allowed = not view["blockers"]
        assert refi_allowed or view["blockers"] == ["selected_principal_exceeds_declared_bank_capacity"], view["blockers"]
        inputs=spec["rent_inputs"];cfg=inputs["holding_horizon"]["scenarios"][name]
        sheet,cell=source_cells(sources,name)
        taxes=reference_taxes(spec,sources,name)
        fiscal=view["holding_horizon"]["fiscal_cash"]
        assert {k:v["payload"] for k,v in fiscal["audit_windows"].items()}==taxes
        purchase=date.fromisoformat(inputs["development"]["scenarios"][name]["purchase_date"])
        finish=month(purchase,int(cell("C46")));stabilized=month(finish,int(cell("C47")))
        count=cfg["holding_months"]//12;sale=month(stabilized,12*count)
        dates=[str(month(purchase,i)) for i in range(0,(sale.year-purchase.year)*12+sale.month-purchase.month+1,3)]
        assert view["project_calendar"]["equity_dates"]==dates
        units=sum(g["units"] for g in inputs["groups"].values())
        basis=sheet["C34"]["literal"]
        if basis=="$/UNIT":quantity=units
        elif basis=="TOTAL":quantity=1
        elif basis=="$/GSF":
            plan=inputs["development"]["scenarios"][name]["plan_gsf"]
            quantity=value(plan["value"]) if plan["state"]=="declared" else cell("C36")
        else:raise ValueError("unrecognized source cost basis")
        vertical=cell("C35")*quantity
        budget=inputs["construction_budget"]["scenarios"][name]
        direct=vertical+cell("C37")*budget["parking"]["spaces"]+cell("C38")
        hard=direct*(1+cell("C39"));soft=hard*cell("C40")
        land=cell("C32")*(1+cell("C33"))
        area=sum(value(v["rentable_sf"]) for v in inputs["commercial"]["uses"].values())
        calendar=inputs["project_calendar"]["scenarios"][name]
        pre_budget=land+hard+soft+cell("C41")*area+value(calendar["lease_up_shortfall_per_month"])*cell("C47")
        initial=value(cfg["initial_equity"]["value"])
        pre_dates=dates[:dates.index(str(stabilized))+1]
        uses={day:Q() for day in pre_dates}
        eligible=uses.copy()
        early=month(purchase,3)
        upfront=direct*value(calendar["upfront_direct_hard_share"])
        uses[str(purchase)]+=land
        uses[str(early)]+=upfront+soft*cell("C42")
        uses[str(finish)]+=pre_budget-land-upfront-soft*cell("C42")
        eligible[str(early)]+=upfront;eligible[str(finish)]+=direct-upfront
        extra=Q()
        for key,trace in taxes.items():
            if key.startswith("preopening-quarter-"):
                amount=value(trace["total"]);extra+=amount;uses[trace["window_end_exclusive"]]+=amount
        assert value(fiscal["preopening_tax_total"])==extra
        terms=inputs["construction_financing"]["scenarios"][name]
        commitment=min(direct*cell("C51"),value(terms["maximum_commitment"]))
        fee=commitment*cell("C53")
        principal=Q();free=Q();previous_interest=Q();equity=[]
        funding=view["construction_financing"]
        for i,day in enumerate(pre_dates):
            draw=eligible[day]*value(terms["requested_invoice_fraction"]) if i<len(pre_dates)-1 else Q()
            opening=free;interest=previous_interest;paid_fee=fee if i==0 else Q()
            net=free+draw-uses[day]-interest-paid_fee
            contribution=initial if i==0 else max(Q(),-net)
            free=net+contribution;principal+=draw
            actual=funding["cash_by_date"][i]
            assert tuple(value(actual[k]) for k in ("opening_free_cash","loan_draw","project_uses","interest_paid",
                "origination_fee_paid","equity_contribution","closing_free_cash"))==(opening,draw,uses[day],interest,paid_fee,contribution,free)
            previous_interest=principal*cell("C52")/4
            equity.append((day,contribution))
        assert value(funding["additional_project_uses"]["total"])==extra
        assert value(funding["construction_principal_payoff"])==principal
        assert sum(value(r["project_uses"]) for r in funding["cash_by_date"])==pre_budget+extra
        gross=value(inputs["requested_principal"]);rate=cell("C69")/4;n=int(cell("C70"))*4
        payment=gross/n if rate==0 else gross*rate/(1-(1+rate)**(-n))
        balance=gross
        schedule=[]
        for i in range(4*count):
            interest=balance*rate;capital=payment-interest;balance-=capital
            actual=view["permanent_loan"]["projected_schedule"][i]
            assert tuple(value(actual[k]) for k in ("interest_due","principal_due","closing_balance"))==(interest,capital,balance)
            schedule.append((interest,capital))
        costs=inputs["operating_costs"]["scenarios"][name]
        other=cell("C13")*inputs["other_income"]["eligible_units"]*12
        no_tax=[]
        for year in range(count+1):
            window_reference=reference_window(spec,sources,name,year)
            # AMI arithmetic above reads source declarations, not the engine's rent.
            potential_residential=value(window_reference["annual_gross_potential"])
            residential=potential_residential*(1-cell("C14")-cell("C15"))
            assert view["holding_horizon"]["regulated_rents"]["windows"][window_reference["window_start"]]==window_reference
            commercial=sum(cell(f"C{16+i}")*value(inputs["commercial"]["uses"][use]["rentable_sf"])
                for i,use in enumerate(("retail","restaurant","office")))
            commercial*=(1+cell("C75"))**year*(1-cell("C19"))*(1-cell("C20"))
            expenses=(value(inputs["annual_expenses"]["fixed_opex"])+cell("C57")*costs["controllable_units"]+
                cell("C59")*costs["insured_units"])*(1+cell("C76"))**year+cell("C58")*(residential+other)
            no_tax.append(residential+commercial+other-expenses)
        reserve=cell("C60")*inputs["replacement_reserve"]["scenarios"][name]["eligible_units"]
        sale_price=(no_tax[-1]-value(taxes[FORWARD_PERIOD]["total"]))/cell("C67")
        sale_cost=sale_price*cell("C68")+value(inputs["supplemental_scope"][name]["fixed_sale_cost"]["value"])
        assert value(view["valuation_and_sale"]["gross_sale_price"]) == sale_price
        if refi_allowed: assert value(view["gross_sale"]) == sale_price
        # Independent LTV, DSCR and debt-yield limits from literal terms and NOI.
        potential = value(reference_window(spec,sources,name,0)["annual_gross_potential"])
        extra_bank_loss = potential * value(inputs["supplemental_scope"][name]["bank_vacancy_addition"]["value"])
        bank_noi = no_tax[0] - value(taxes["SYNTHETIC-D108-bank-annual"]["total"]) - extra_bank_loss * (1-cell("C58"))
        valuation_noi = no_tax[0] - value(taxes["SYNTHETIC-D108-refinance-valuation-annual"]["total"])
        debt_yield = inputs["bank_debt_yield"][name]
        assert debt_yield["applicability"] == "applicable"
        capacity = min(valuation_noi / cell("C66") * cell("C71"),
                       bank_noi / (cell("C72") * 4 * payment / gross),
                       bank_noi / value(debt_yield["minimum"]))
        assert value(view["capacity"]["maximum_principal_capacity"]) == capacity
        assert value(view["capacity"]["bank_noi"]) == bank_noi
        assert value(view["capacity"]["selected_principal"]) == gross
        assert refi_allowed == (gross <= capacity)
        reserve_release=reserve*count*value(inputs["replacement_reserve"]["scenarios"][name]["sale_release_fraction"])
        perm_reserve=cell("C74")*inputs["refinance_costs"]["scenarios"][name]["eligible_units"]
        refi_net=free+gross-principal-gross*cell("C73")-perm_reserve
        if refi_allowed:
            assert value(view["construction_refinance"]["net_equity_distribution"])==max(Q(),refi_net)
        else:
            assert view["construction_refinance"]["net_equity_distribution"] is None
            assert view["cash_per_usd_10"] is None
        capital_remaining=sum(amount for _,amount in equity)-refi_net
        coc_numerator=no_tax[0]-value(taxes[OPERATING_PERIOD]["total"])-reserve-4*payment
        if refi_allowed:
            assert capital_remaining>0 and value(view["post_refinance_coc"]["value"])==coc_numerator/capital_remaining
            assert view["post_refinance_coc"]["window_start"]==str(stabilized)
            assert view["post_refinance_coc"]["window_end"]==str(month(stabilized,12))
        annual_keys=[OPERATING_PERIOD]+[f"SYNTHETIC-D266-{name}-year-{i+1}" for i in range(1,count)]
        irr_states={} if refi_allowed else dict(refi=dict(state="PENDING", reason="requested_loan_exceeds_independently_verified_capacity"))
        routes = [("refi", view)] if refi_allowed else []
        routes.append(("without_refi", view["horizon_without_refinance"]))
        for strategy,data in routes:
            cash=data["cash_per_usd_10"];scale=Q(10)/initial
            assert value(cash["basis_amount"])==initial and value(cash["scale_factor"])==scale
            contributions=sum(amount for _,amount in equity);receipts=Q()
            expected={day:Q() for day in dates}
            for day,amount in equity:expected[day]-=amount
            if strategy=="refi":
                contributions+=max(Q(),-refi_net);receipts+=max(Q(),refi_net);expected[str(stabilized)]+=refi_net
            else:
                hold=value(cfg["without_refinance"]["fee_at_stabilization"]["value"])
                topup=max(Q(),hold-free);contributions+=topup;expected[str(stabilized)]-=topup;held_free=free+topup-hold
            records=view["holding_horizon"]["annual_cash"] if strategy=="refi" else data["annual_cash"]
            for i in range(count*4):
                tax=value(taxes[f"operation-quarter-{i+1}"]["total"])
                service=payment if strategy=="refi" else principal*cell("C52")/4
                net=no_tax[i//4]/4-tax-reserve/4-service
                day=str(month(stabilized,3*(i+1)))
                expected[day]+=net;contributions+=max(Q(),-net);receipts+=max(Q(),net)
                actual=records[i//4]["payments"][i%4]
                assert (actual["date"],value(actual["contribution"]),value(actual["receipt"]))==(day,max(Q(),-net)*scale,max(Q(),net)*scale)
                assert value(records[i//4]["noi"])==no_tax[i//4]-value(taxes[annual_keys[i//4]]["total"])
            released=reserve_release+(perm_reserve*value(inputs["refinance_costs"]["scenarios"][name]["sale_release_fraction"]) if strategy=="refi" else Q())
            sale_net=sale_price-sale_cost-(balance if strategy=="refi" else principal)+released+(Q() if strategy=="refi" else held_free)
            contributions+=max(Q(),-sale_net);receipts+=max(Q(),sale_net);expected[str(sale)]+=sale_net
            assert tuple(value(cash[k]) for k in ("total_contributions","total_distributions","net_cash_profit","equity_multiple",
                "unrecovered_after_sale"))==(contributions*scale,receipts*scale,(receipts-contributions)*scale,receipts/contributions,max(Q(),contributions-receipts)*scale)
            observed={day:Q() for day in dates}
            for event in cash["events"]:observed[event["date"]]+=value(event["amount"])*(1 if event["kind"]=="distribution" else -1)
            assert observed=={day:flow*scale for day,flow in expected.items()}
            irr=result["screening"]["irr_by_scenario"][name] if strategy=="refi" else data["irr"]
            if irr["annual_enclosure"] is None:
                assert irr["state"] == "PENDING"
                assert set(irr["blockers"]) == {"IRR_incomplete_root_inventory_current_intervals_withheld", "complete_periodic_root_inventory_required"}
                assert irr["periodic_result"]["root_classification"] == "arithmetic_budget_exhausted"
                assert irr["periodic_result"]["selected_rate"] is None
                assert irr["periodic_result"]["roots"] == []
                irr_states[strategy] = dict(state="PENDING", reason="complete_root_inventory_not_certified")
            else:
                assert not irr["blockers"]
                for key,sign in (("lower",1),("upper",-1)):
                    rate=value(irr["annual_enclosure"][key])+1
                    num,den=isqrt(isqrt(rate.denominator)),isqrt(isqrt(rate.numerator))
                    assert num**4==rate.denominator and den**4==rate.numerator
                    discount=Q(num,den);npv=sum(flow*discount**i for i,flow in enumerate(expected.values()))
                    assert npv*sign>=0
                irr_states[strategy] = dict(state="enclosure_independently_checked")
        checked[name]=dict(tax_windows=len(taxes),loan_payments=4*count,annual_noi_and_forward=count+1,
            preopening_tax_total=rational(extra),dated_funding_reconciled=True,dated_quarterly_tax_cash_reconciled=True,
            verified_routes=[route for route, _ in routes],
            gross_cash_and_all_dates_reconciled=True, capacity_independently_checked=True, annual_irr=irr_states)
    return checked



def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    spec,sources,result,saved=run(output/'regulated')
    fixture=json.loads((Path(__file__).resolve().parents[1]/'templates/synthetic-regulated-rent-D269.json').read_bytes())
    assert fixture['usage']=='synthetic_test_only_not_production_defaults'
    assert spec['rent_inputs']['regulated_rent']==fixture['regulated_rent'], 'Versioned AMI fixture drift'
    control_spec,control_sources,control,control_saved=run(output/'market-control',regulated=False)
    checked={label:independently_verify(case,source,view) for label,case,source,view in (
        ('regulated',spec,sources,result),('market_control',control_spec,control_sources,control))}
    comparisons={}
    for name in ('Base','Downside'):
        assert result['critical_evidence_review']['counts']==dict(VERIFIED_GREEN=130,FALSE_GREEN=0,PENDING=0)
        assert control['critical_evidence_review']['counts']==dict(VERIFIED_GREEN=130,FALSE_GREEN=0,PENDING=0)
        current,original=result['scenarios'][name],control['scenarios'][name]
        assert current['construction_financing']['equity_funding_through_refinance']==original['construction_financing']['equity_funding_through_refinance']
        _,cell=source_cells(sources,name)
        annual=[]
        for index in range(6):
            capped=reference_window(spec,sources,name,index)
            market=reference_window(control_spec,control_sources,name,index)
            gross_difference=value(market['annual_gross_potential'])-value(capped['annual_gross_potential'])
            noi_difference=gross_difference*(1-cell('C14')-cell('C15'))*(1-cell('C58'))
            if index<5:
                actual=value(original['holding_horizon']['annual_noi'][index]['producer']['noi'])-value(current['holding_horizon']['annual_noi'][index]['producer']['noi'])
            else:actual=value(original['noi_by_period'][FORWARD_PERIOD]['noi'])-value(current['noi_by_period'][FORWARD_PERIOD]['noi'])
            assert actual==noi_difference
            annual.append(dict(year=index+1,gross_rent_reduction=rational(gross_difference),noi_reduction=rational(noi_difference)))
        routes={}
        for label,view,baseline in [('with_refi',current,original),('without_refi',current['horizon_without_refinance'],original['horizon_without_refinance'])]:
            cash,before=view['cash_per_usd_10'],baseline['cash_per_usd_10']
            assert value(cash['reference_amount'])==10
            assert value(cash['basis_amount'])==value(before['basis_amount'])==2_400_000
            assert value(cash['total_distributions'])<=value(before['total_distributions'])
            assert value(cash['total_contributions'])>=value(before['total_contributions'])
            routes[label]=dict(additional=rational(value(cash['total_contributions'])-10),receipts=cash['total_distributions'],
                unrecovered=cash['unrecovered_after_sale'],dated_cash_sha256=sha(encoded(cash)),
                contribution_events=[e for e in cash['events'] if e['kind']=='contribution' and value(e['amount'])>0],
                receipt_events=[e for e in cash['events'] if e['kind']=='distribution' and value(e['amount'])>0])
        comparisons[name]=dict(annual=annual,routes=routes,owner_utilities_not_deducted_again=True)
    audits={}
    for label in ('regulated','market-control'):
        package=output/label/'package';saved_case=read_package(package)
        audits[label]=verify_package(package,current_revision_raw=saved_case[CURRENT_REVISION_FILE])
        assert audits[label]['vigencia']=='VIGENTE' and audits[label]['critical_evidence']['status']=='PASSED'
    current=output/'Current.json';current.write_bytes(saved[CURRENT_REVISION_FILE])
    destination=output/'MiniUW_Renta_Regulada_D269.pdf'
    delivery=deliver_package(output/'regulated/package',destination,current)
    assert destination.read_bytes()==saved['MiniUW_Resumen.pdf']
    report=dict(milestone='D269',status='passed',profile=PROFILE,source_case_sha256=sha(saved['case.json']),
        control_case_sha256=sha(control_saved['case.json']),independent_checks=checked,comparisons=comparisons,
        current_audits=audits,delivery=delivery,pdf_sha256=sha(destination.read_bytes()),
        real_decision='PENDING',historical_return='PENDING',personal_return_without_terms='PENDING',
        real_eligibility_confirmed=False,conditional_tax_benefits_enabled=False,
        deployment_enabled=False,real_decisions_enabled=False,all_33_policies_certified=False,
        scope='Explicit per-unit AMI forecasts with reconciled group allocations; six annual windows including exit-forward; no PER_SF inference or statutory eligibility approval')
    (output/'validation.json').write_bytes(encoded(report))
    return report


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    report=verify(args.output)
    print(json.dumps(dict(status=report['status'],real_decision=report['real_decision'],pdf_sha256=report['pdf_sha256'])))


if __name__=='__main__':
    main()
