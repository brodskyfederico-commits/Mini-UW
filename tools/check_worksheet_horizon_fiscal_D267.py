"""Reproduce fiscal holding cash and audit it against source-based references."""
from argparse import ArgumentParser
from collections import Counter
from copy import deepcopy
from datetime import date
from fractions import Fraction as Q
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from check_lorena_criteria_D192 import change_cells
from check_worksheet_holding_horizon_D266 import settings as prior_settings,sources_for
from miniuw_foundation.debt_service import rational
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE,WORKBOOK_CRITICAL_EVIDENCE_SCHEMA,encoded,read_package,verify_package,deliver_package
from plan_refinance_D108 import BANK_PERIOD,VALUE_PERIOD
from plan_return_D107 import OPERATING_PERIOD,FORWARD_PERIOD
from worksheet_florida_tax_D203 import POLICY as TAX_POLICY,SCOPE
from worksheet_horizon_fiscal_D267 import PROFILE,RULES,CASH_PROFILE,CASH_RULES,REFERENCE
from worksheet_intake_D198 import assemble,register,SOURCES


def value(raw):
    if not isinstance(raw,dict) or set(raw)!={"numerator","denominator"}:raise ValueError("explicit rational required")
    return Q(raw["numerator"])/Q(raw["denominator"])


def month(start,number):
    y,m=divmod(start.year*12+start.month-1+number,12)
    return date(y,m+1,start.day)


def roll(amount,treatment="confirmed_no_change",event=None,*,ref):
    return dict(just_value=rational(amount),school_taxable_value=rational(amount),assessment_treatment=treatment,
        event_date=event,valuation_ref=ref+"-value",event_ref=ref+"-event")


def settings():
    spec=prior_settings()
    spec["schema"]=WORKBOOK_CRITICAL_EVIDENCE_SCHEMA
    spec["criteria_revision"]="SYNTHETIC-D267-five-year-criteria-fixture"
    spec["local_sources"]["revision"]="SYNTHETIC-D267-SOURCES"
    inputs=spec["rent_inputs"]
    inputs.pop("property_tax");inputs.pop("buyer_forward_property_tax")
    inputs["holding_horizon"].update(profile=PROFILE,rules=RULES,source_ref="SYNTHETIC-D267-explicit-fiscal-holding")
    inputs["holding_tax_cash"]=dict(profile=CASH_PROFILE,rules=CASH_RULES,source_ref="SYNTHETIC-D267-dated-tax-cash",scenarios={})
    scenarios={}
    for name in ("Base","Downside"):
        inputs["holding_tax_cash"]["scenarios"][name]=dict(source_ref=f"SYNTHETIC-D267-{name}-quarterly-tax-payments",
            budget_exclusion_ref=f"SYNTHETIC-D267-{name}-preopening-tax-not-in-budget")
        sale=inputs["supplemental_scope"][name]["sale_date"]["value"]
        seller={}
        for year in range(2027,2035):
            amount=2_000_000+(year-2027)*(300_000 if name=="Base" else 400_000)
            if name=="Downside" and year>=2028:amount+=600_000
            treatment,event="confirmed_no_change",None
            if year==2028:treatment,event="ownership_or_control_reset","2027-04-01"
            if name=="Downside" and year==2029:treatment,event="qualifying_improvement_reset","2028-01-01"
            seller[str(year)]=roll(amount,treatment,event,ref=f"SYNTHETIC-D267-{name}-{year}-forecast-roll")
        scenarios[name]=dict(classification="art_VII_4h",classification_ref=f"SYNTHETIC-D267-{name}-classification",
            scope=SCOPE,scope_ref=f"SYNTHETIC-D267-{name}-tax-scope-no-benefits",
            source_ref=f"SYNTHETIC-D267-{name}-explicit-synthetic-roll-forecasts",
            opening_assessment=dict(tax_year=2026,non_school_assessed_value=rational(1_500_000),
                source_ref=f"SYNTHETIC-D267-{name}-opening-roll"),
            rolls=dict(seller=seller,buyer={"2034":roll(5_000_000 if name=="Base" else 5_500_000,
                "ownership_or_control_reset",sale,ref=f"SYNTHETIC-D267-{name}-buyer-forecast")},
                millage={str(year):dict(school_mills=rational(4),non_school_mills=rational(9),
                    source_ref=f"SYNTHETIC-D267-{name}-{year}-millage-forecast") for year in range(2027,2035)}))
    inputs["florida_property_tax"]=dict(policy=TAX_POLICY,scenarios=scenarios)
    return spec


def source_cells(sources,name):
    sheet=inspect_synthetic_input_sheet(sources["workbook_raw" if name=="Base" else "downside_workbook_raw"]).cells
    def cell(key):
        raw=sheet[key]["literal"]
        if raw is None or raw=="":raise ValueError("missing source cell: "+key)
        return Q(raw)
    return sheet,cell


def independent_taxes(spec,sources,name):
    """Read literal inputs and evaluate declared roll rules without M2 functions."""
    inputs=spec["rent_inputs"];tax=inputs["florida_property_tax"]["scenarios"][name]
    _,cell=source_cells(sources,name)
    purchase=date.fromisoformat(inputs["development"]["scenarios"][name]["purchase_date"])
    tco=date.fromisoformat(inputs["project_calendar"]["scenarios"][name]["tco_date"])
    stabilized=month(tco,int(cell("C47")))
    count=inputs["holding_horizon"]["scenarios"][name]["holding_months"]
    sale=month(stabilized,count)
    pre=(stabilized.year-purchase.year)*12+stabilized.month-purchase.month
    windows={OPERATING_PERIOD:(stabilized,12,False),BANK_PERIOD:(stabilized,12,False),
        VALUE_PERIOD:(stabilized,12,False),FORWARD_PERIOD:(sale,12,True),"holding_total":(stabilized,count,False)}
    annual=[OPERATING_PERIOD]+[f"SYNTHETIC-D266-{name}-year-{i+1}" for i in range(1,count//12)]
    windows.update({key:(month(stabilized,12*i),12,False) for i,key in enumerate(annual)})
    windows.update({f"operation-quarter-{i+1}":(month(stabilized,3*i),3,False) for i in range(count//3)})
    windows.update({f"preopening-quarter-{i+1}":(month(purchase,3*i),3,False) for i in range(pre//3)})
    reset=sale.year+1
    previous=value(tax["opening_assessment"]["non_school_assessed_value"])
    rows={}
    for year in range(tax["opening_assessment"]["tax_year"]+1,sale.year+1):
        source=tax["rolls"]["seller"][str(year)]
        market=value(source["just_value"])
        unchanged=source["assessment_treatment"]=="confirmed_no_change"
        cap=Q(5,100) if year>=2027 else Q(10,100)
        ceiling=previous*(1+cap)
        assessed=min(market,ceiling) if unchanged else market
        rows[year]=dict(tax_year=year,owner="seller",assessment_treatment=source["assessment_treatment"],event_date=source["event_date"],
            event_ref=source["event_ref"],valuation_ref=source["valuation_ref"],prior_non_school_assessed=previous,
            just_value=market,school_taxable_value=value(source["school_taxable_value"]),non_school_assessed_value=assessed,
            cap=cap if unchanged else None,assessment_ceiling=ceiling if unchanged else None)
        previous=assessed
    result={}
    for key,(start,months,forward) in windows.items():
        parts=[]
        for year,n in Counter(month(start,i).year for i in range(months)).items():
            if forward and year>=reset:
                source=tax["rolls"]["buyer"][str(year)];market=value(source["just_value"])
                row=dict(tax_year=year,owner="buyer",assessment_treatment="ownership_or_control_reset",event_date=source["event_date"],
                    event_ref=source["event_ref"],valuation_ref=source["valuation_ref"],prior_non_school_assessed=None,
                    just_value=market,school_taxable_value=value(source["school_taxable_value"]),non_school_assessed_value=market,
                    cap=None,assessment_ceiling=None)
            else:row=rows[year]
            rates=tax["rolls"]["millage"][str(year)]
            school,other=value(rates["school_mills"]),value(rates["non_school_mills"])
            parts.append(row|dict(months=n,school_mills=school,non_school_mills=other,millage_ref=rates["source_ref"],
                school_tax=row["school_taxable_value"]*school*n/12000,
                non_school_tax=row["non_school_assessed_value"]*other*n/12000))
        school=sum(p["school_tax"] for p in parts);other=sum(p["non_school_tax"] for p in parts)
        trace=dict(basis=inputs["florida_property_tax"]["policy"],classification=tax["classification"],classification_ref=tax["classification_ref"],
            scope_ref=tax["scope_ref"],source_ref=tax["source_ref"],opening_assessment_ref=tax["opening_assessment"]["source_ref"],
            window_start=str(start),window_end_exclusive=str(month(start,months)),school_tax=school,non_school_tax=other,total=school+other,rolls=parts)
        trace=json.loads(json.dumps(trace,default=rational));trace["source_sha256"]=sha(encoded(trace));result[key]=trace
    return result


def build_reference(spec,sources):
    """Version a fixed synthetic inventory from source declarations, not bot output."""
    from audit_worksheet_critical_evidence_D219 import REFERENCE as old_reference
    ref=json.loads(old_reference.read_bytes())
    inputs=spec["rent_inputs"]
    ref["local_revision"]=spec["local_sources"]["revision"]
    ref["sources"]={SOURCES[key]:sha(raw) for key,raw in sources.items() if key!="criteria_raw"}
    ref["holding_fiscal"]={}
    for name in ("Base","Downside"):
        _,cell=source_cells(sources,name)
        for kind,bank in ref["bank"][name].items():
            if kind=="permanent":
                changes=dict(requested_principal=value(inputs["requested_principal"]),annual_nominal_rate=cell("C69"),
                    amortization_years=cell("C70"),maximum_ltv=cell("C71"),minimum_dscr=cell("C72"),
                    maturity_payments=inputs["permanent_loan"]["scenarios"][name]["maturity_payments"])
            else:
                record=inputs["construction_financing"]["scenarios"][name]
                changes=dict(ltc=cell("C51"),annual_interest=cell("C52"),origination_fee_fraction=cell("C53"),
                    maximum_commitment=value(record["maximum_commitment"]),requested_invoice_fraction=value(record["requested_invoice_fraction"]),
                    available_per_draw_checkpoint=value(record["available_per_draw_checkpoint"]),maturity_date=record["maturity_date"])
            for key,new in changes.items():
                assert key in bank["terms"],key
                old=bank["terms"][key][-1]
                if (old==str(new) if key=="maturity_date" else Q(old)==new):
                    continue
                # Reuse the source's literal representation for decimal rate cells.
                literal={"annual_nominal_rate":"C69","maximum_ltv":"C71","minimum_dscr":"C72", "ltc":"C51",
                    "annual_interest":"C52","origination_fee_fraction":"C53"}.get(key)
                bank["terms"][key][-1]=source_cells(sources,name)[0][literal]["literal"] if literal else str(new)
        from worksheet_horizon_fiscal_D267 import fiscal_input_digest
        ref["holding_fiscal"][name]=dict(inputs_sha256=fiscal_input_digest(inputs["florida_property_tax"],inputs["holding_tax_cash"],name),
            windows=independent_taxes(spec,sources,name))
    return ref


def independently_verify(spec,sources,result):
    """Financial reference from literal cells and rolls, not the engine's totals."""
    from math import isqrt
    checked={}
    for name in ("Base","Downside"):
        view=result["scenarios"][name]
        assert not view["blockers"],view["blockers"]
        inputs=spec["rent_inputs"];cfg=inputs["holding_horizon"]["scenarios"][name]
        sheet,cell=source_cells(sources,name)
        taxes=independent_taxes(spec,sources,name)
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
            residential=Q()
            for i,group in enumerate(("studio","1BR","2BR","3BR"),8):
                record=inputs["groups"][group];quantity=record["units"]
                if sheet["C7"]["literal"]=="PER SF":quantity*=value(record["rentable_sf_per_unit"])
                residential+=cell(f"C{i}")*quantity*12
            residential*=(1+cell("C75"))**year*(1-cell("C14")-cell("C15"))
            commercial=sum(cell(f"C{16+i}")*value(inputs["commercial"]["uses"][use]["rentable_sf"])
                for i,use in enumerate(("retail","restaurant","office")))
            commercial*=(1+cell("C75"))**year*(1-cell("C19"))*(1-cell("C20"))
            expenses=(value(inputs["annual_expenses"]["fixed_opex"])+cell("C57")*costs["controllable_units"]+
                cell("C59")*costs["insured_units"])*(1+cell("C76"))**year+cell("C58")*(residential+other)
            no_tax.append(residential+commercial+other-expenses)
        reserve=cell("C60")*inputs["replacement_reserve"]["scenarios"][name]["eligible_units"]
        sale_price=(no_tax[-1]-value(taxes[FORWARD_PERIOD]["total"]))/cell("C67")
        sale_cost=sale_price*cell("C68")+value(inputs["supplemental_scope"][name]["fixed_sale_cost"]["value"])
        assert value(view["gross_sale"])==sale_price
        reserve_release=reserve*count*value(inputs["replacement_reserve"]["scenarios"][name]["sale_release_fraction"])
        perm_reserve=cell("C74")*inputs["refinance_costs"]["scenarios"][name]["eligible_units"]
        refi_net=free+gross-principal-gross*cell("C73")-perm_reserve
        assert value(view["construction_refinance"]["net_equity_distribution"])==max(Q(),refi_net)
        capital_remaining=sum(amount for _,amount in equity)-refi_net
        coc_numerator=no_tax[0]-value(taxes[OPERATING_PERIOD]["total"])-reserve-4*payment
        assert capital_remaining>0 and value(view["post_refinance_coc"]["value"])==coc_numerator/capital_remaining
        assert view["post_refinance_coc"]["window_start"]==str(stabilized)
        assert view["post_refinance_coc"]["window_end"]==str(month(stabilized,12))
        annual_keys=[OPERATING_PERIOD]+[f"SYNTHETIC-D266-{name}-year-{i+1}" for i in range(1,count)]
        for strategy,data in (("refi",view),("without_refi",view["horizon_without_refinance"])):
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
            assert not irr["blockers"] and irr["annual_enclosure"] is not None
            for key,sign in (("lower",1),("upper",-1)):
                rate=value(irr["annual_enclosure"][key])+1
                num,den=isqrt(isqrt(rate.denominator)),isqrt(isqrt(rate.numerator))
                assert num**4==rate.denominator and den**4==rate.numerator
                discount=Q(num,den);npv=sum(flow*discount**i for i,flow in enumerate(expected.values()))
                assert npv*sign>=0
        checked[name]=dict(tax_windows=len(taxes),loan_payments=4*count,annual_noi_and_forward=count+1,
            preopening_tax_total=rational(extra),dated_funding_reconciled=True,dated_quarterly_tax_cash_reconciled=True,
            both_routes_gross_cash_and_all_dates_reconciled=True,annual_irr_bounds_checked=True)
    return checked


def run(output):
    spec=settings()
    sources=sources_for(spec,output/"sources")
    expected=build_reference(spec,sources)
    assert REFERENCE.read_bytes()==encoded(expected),"Versioned independent reference drift"
    (output/"settings.json").write_bytes(encoded(spec))
    receipt=assemble(spec,register(sources,"SYNTHETIC-D267-fiscal-horizon"),sources,output/"package")
    saved=read_package(output/"package")
    result=json.loads(saved["results.json"])
    (output/"receipt.json").write_bytes(encoded(receipt))
    return spec,sources,result,saved


def verify(output):
    from pypdf import PdfReader
    from worksheet_sale_rate_grid_D84 import money
    from worksheet_irr_D122 import display_enclosure
    spec,sources,result,saved=run(output)
    assert result["decision"]=="PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"]
    assert not result["local_review"]["blockers"] and not result["revision_review"]["blockers"]
    assert result["critical_evidence_review"]["counts"]==dict(VERIFIED_GREEN=116,FALSE_GREEN=0,PENDING=0)
    checked=independently_verify(spec,sources,result)
    audit=verify_package(output/"package",current_revision_raw=saved[CURRENT_REVISION_FILE])
    assert audit["vigencia"]=="VIGENTE" and audit["critical_evidence"]["status"]=="PASSED"
    current=output/"Vigente.json";current.write_bytes(saved[CURRENT_REVISION_FILE])
    destination=output/"MiniUW_Horizonte_Fiscal_Auditado_D267.pdf"
    delivered=deliver_package(output/"package",destination,current)
    assert destination.read_bytes()==saved["MiniUW_Resumen.pdf"]
    with PdfReader(destination,strict=True) as reader:
        assert len(reader.pages)==1
        text=reader.pages[0].extract_text()
        assert all(term in text for term in ("D267","USD 10","Q1,2:","Q3,4:","2033-01-01","2033-07-01","PENDING"))
    rows={}
    for name,view in result["scenarios"].items():
        scenario={}
        for route,data in (("with_refinance",view),("without_refinance",view["horizon_without_refinance"])):
            cash=data["cash_per_usd_10"]
            irr=result["screening"]["irr_by_scenario"][name] if route=="with_refinance" else data["irr"]
            scenario[route]=dict(initial_usd="10,00",additional_usd=money(rational(value(cash["total_contributions"])-10)),
                receipts_usd=money(cash["total_distributions"]),unrecovered_usd=money(cash["unrecovered_after_sale"]),
                equity_multiple=money(cash["equity_multiple"]),annual_irr=display_enclosure(irr["annual_enclosure"]),
                cash_sha256=sha(encoded(cash)))
        rows[name]=dict(stabilization=view["project_calendar"]["stabilization_date"],sale=view["project_calendar"]["sale_date"],
            preopening_tax=view["holding_horizon"]["fiscal_cash"]["preopening_tax_total"],
            operating_tax=view["holding_horizon"]["fiscal_cash"]["operating_tax_total"],routes=scenario)
    summary=dict(milestone="D267",status="passed",decision="PENDING",historical_return="PENDING",deployment_enabled=False,
        real_decisions_enabled=False,independent_checks=checked,scenarios=rows,
        critical_evidence={key:result["critical_evidence_review"][key] for key in ("status","counts","affected_scenarios","reference_sha256")},
        source_files={k:sha(v) for k,v in sources.items()},case_sha256=sha(saved["case.json"]),
        pdf_sha256=sha(destination.read_bytes()),pdf_pages=1,audit=audit,delivery=delivered,
        simulation_result=result["simulation_result"],simulation_blockers=result["screening"]["simulation_blockers"])
    (output/"validacion.json").write_bytes(encoded(summary))
    return summary


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(exist_ok=True)
    print(json.dumps(verify(args.output),sort_keys=True))
