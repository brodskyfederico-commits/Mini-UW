"""D273 T1 reference: financial and summary equations from literal sources."""
from datetime import date
from fractions import Fraction as Q
from math import isqrt
from pathlib import Path
import json
from check_worksheet_regulated_rent_D269 import (settings, make_sources, reference_window,
    source_cells, value, month, reference_taxes)
from check_worksheet_irr_certificate_D270 import certified_sources
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import (encoded,read_package,write_package,verify_package,deliver_package,CURRENT_REVISION_FILE)
from worksheet_intake_D198 import prepare,register
from worksheet_revision_D128 import snapshot_for_case
from worksheet_return_summary_D273 import SCHEMA,PROFILE,RULES
from plan_return_D107 import OPERATING_PERIOD,FORWARD_PERIOD


def configuration():
    return dict(profile=PROFILE,rules=RULES.copy(),source_ref="SYNTHETIC-D273-explicit-summary-definition")


def fixture(output):
    expected=json.loads((Path(__file__).resolve().parents[1]/'templates/synthetic-return-summary-D273.json').read_bytes())
    assert expected['usage']=='synthetic_test_only_no_investment_criterion'
    assert expected['return_summary']==configuration(), 'Cambió la definición versionada del resumen'
    output.mkdir(parents=True,exist_ok=False)
    original,sources=make_sources(settings(),output)
    baseline,sources=certified_sources(original,sources)
    base_raw,_=prepare(baseline,register(sources,'SYNTHETIC-D273-source-registration'))
    base=json.loads(base_raw)
    case=dict(schema=SCHEMA,baseline_case=base,return_summary=configuration())
    current=encoded(snapshot_for_case(case,'SYNTHETIC-D273-summary-current'))
    return case,current,sources


def capacity_fixture(output):
    """Reproduce D268's explicit combined stress, never a production default."""
    from check_worksheet_scenario_program_D268 import settings as stress_settings, sources_for, make_packet, drivers
    from worksheet_scenario_program_D268 import DRIVERS
    output.mkdir(parents=True,exist_ok=False)
    spec=stress_settings();seed=sources_for(spec,output/'seed')
    parent,sources=make_packet(spec,seed,'baseline',[],drivers(),output/'baseline')
    sources={key:value for key,value in sources.items() if key!='independent_reference_raw'}
    spec,sources=make_packet(parent,sources,'33',list(DRIVERS),drivers(),output/'combined')
    raw,_=prepare(spec,register(sources,'SYNTHETIC-D273-capacity-stress-source-registration'))
    base=json.loads(raw);case=dict(schema=SCHEMA,baseline_case=base,return_summary=configuration())
    current=encoded(snapshot_for_case(case,'SYNTHETIC-D273-capacity-stress-current'))
    return case,current,sources


def execute(output):
    output.mkdir(parents=True,exist_ok=False)
    case,current,sources=fixture(output/'sources')
    write_package(encoded(case),output/'package',current_revision_raw=current,**sources)
    saved=read_package(output/'package');result=json.loads(saved['results.json'])
    assert result['pipeline']['case_sha256']==sha(saved['case.json'])
    report_stages=[stage for stage in result['pipeline']['stages'] if 'B15' in stage.get('bots',[])]
    assert len(report_stages)==1
    assert report_stages[0]['pdf_sha256']==sha(saved['MiniUW_Resumen.pdf'])==result['pdf_sha256']
    assert report_stages[0]['pages']==1
    checked=independently_verify_summary(case['baseline_case'],sources,result)
    review=verify_package(output/'package',current_revision_raw=current)
    assert review['vigencia']=='VIGENTE' and result['decision']=='PENDING'
    (output/'current.json').write_bytes(current)
    delivery=deliver_package(output/'package',output/'MiniUW_Resumen_Retorno_D273.pdf',output/'current.json')
    proof=dict(status='passed',milestone='D273',task='T1',schema=SCHEMA,independent_source_checks=checked,
        audit=review,delivery=delivery,decision='PENDING',deployment_enabled=False,criterion_used=False,
        current_case_and_delivered_pdf_bound_in_pipeline=True)
    (output/'validation.json').write_bytes(encoded(proof))
    return proof


def independently_verify_summary(spec,sources,result):
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
        expected_summaries={}
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
            # Expected prefix balances are built exclusively from source-derived cash,
            # before looking at the model ledger or the new summary.
            deployed=Q();peak=Q();payback=None;peak_dates=[];reverse=False
            for day,flow in expected.items():
                deployed-=flow*scale
                if deployed>peak:peak,peak_dates=deployed,[day]
                elif deployed==peak:peak_dates.append(day)
                if payback is None and deployed<=0:payback=day
                elif payback is not None and deployed>0:reverse=True
            mode='with_refinance' if strategy=='refi' else 'without_refinance'
            summary=result['return_summary']['scenarios'][name][mode]
            assert value(summary['peak_equity'])==peak
            assert value(summary['project_peak_equity'])==peak/scale
            assert summary['peak_dates']==peak_dates and summary['payback_date']==payback
            assert summary['recovery_reversed_after_first_payback']==reverse
            assert summary['payback_reason']==(None if payback else 'capital no recuperado en el horizonte')
            expected_summaries[mode]=dict(peak_equity=rational(peak),payback_date=payback,
                peak_dates=peak_dates,source_derived_net_cash={k:rational(v*scale) for k,v in expected.items()})
            observed={day:Q() for day in dates}
            for event in cash["events"]:observed[event["date"]]+=value(event["amount"])*(1 if event["kind"]=="distribution" else -1)
            assert observed=={day:flow*scale for day,flow in expected.items()}
            irr=result["return_summary"]["scenarios"][name][mode]["irr_annual"]
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
        checked[name]=dict(return_summary_from_sources=expected_summaries,tax_windows=len(taxes),loan_payments=4*count,annual_noi_and_forward=count+1,
            preopening_tax_total=rational(extra),dated_funding_reconciled=True,dated_quarterly_tax_cash_reconciled=True,
            verified_routes=[route for route, _ in routes],
            gross_cash_and_all_dates_reconciled=True, capacity_independently_checked=True, annual_irr=irr_states)
    return checked

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    result=execute(p.parse_args().output);print(json.dumps(dict(status=result['status'],task='T1',decision='PENDING')))
