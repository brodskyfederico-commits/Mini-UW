"""Build a documented synthetic five-year intake and preserve its audited package."""
from argparse import ArgumentParser
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image,ImageDraw,ImageFont
from pypdf import PdfReader,PdfWriter

from check_worksheet_construction_pdf_D157 import ORDER,pages
from check_worksheet_evidence_pdf_D156 import evidence_pdf
from check_worksheet_evidence_jpeg_D161 import jpeg_bundle
from check_worksheet_evidence_progressive_order_D164 import SCAN_ENCODINGS,SHUFFLED
from check_worksheet_evidence_scan_D158 import add_scan
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance,source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_holding_horizon_D266 import CALENDAR_POLICY,CALENDAR_RULES,PROFILE,RULES,RESERVE_POLICY,RESERVE_RULES,amount
from worksheet_holding_horizon_D266 import PROPERTY_TAX_POLICY,PROPERTY_TAX_CASH
from worksheet_intake_D198 import assemble,register
from worksheet_project_calendar_D145 import offset
from datetime import date
from fractions import Fraction
from math import isqrt


def settings():
    spec=settings_for_acceptance()
    inputs=spec["rent_inputs"]
    inputs.pop("post_refinance_coc")
    inputs["calendar_checks"]={}
    inputs["project_calendar"].update(policy=CALENDAR_POLICY,rules=CALENDAR_RULES,policy_ref="SYNTHETIC-D266-calendar")
    inputs["replacement_reserve"].update(policy=RESERVE_POLICY,rules=RESERVE_RULES,source_ref="SYNTHETIC-D266-quarterly-reserve")
    inputs["property_tax"].update(policy=PROPERTY_TAX_POLICY,source_ref="SYNTHETIC-D266-proxy-tax-explicit-quarterly-cash")
    inputs["property_tax"]["rules"]["operating_cash"]=PROPERTY_TAX_CASH
    spec["local_sources"]["revision"]="SYNTHETIC-D266-SOURCES"
    spec["criteria_revision"]="SYNTHETIC-D266-five-year-criteria-fixture"
    inputs["holding_horizon"]=dict(profile=PROFILE,rules=RULES,source_ref="SYNTHETIC-D266-explicit-holding",scenarios={})
    purchase=date(2027,4,1)
    for name,construction,lease in (("Base",6,3),("Downside",9,6)):
        tco=offset(purchase,construction)
        stabilized=offset(tco,lease)
        sale=offset(stabilized,60)
        period=f"{stabilized}/{offset(stabilized,12)}"
        inputs["development"]["scenarios"][name].update(purchase_date=str(purchase),purchase_source_ref=f"SYNTHETIC-D266-{name}-purchase")
        inputs["project_calendar"]["scenarios"][name].update(construction_start=str(purchase),start_ref=f"SYNTHETIC-D266-{name}-start",
            tco_date=str(tco),tco_ref=f"SYNTHETIC-D266-{name}-tco")
        inputs["holding_horizon"]["scenarios"][name]=dict(holding_months=60,source_ref=f"SYNTHETIC-D266-{name}-60-months",
            initial_equity=dict(value=rational(2400000),source_ref=f"SYNTHETIC-D266-{name}-initial-equity"),
            cash_assumptions_ref=f"SYNTHETIC-D266-{name}-explicit-uniform-quarter-cash-and-zero-inventory",
            closing_funding=dict(policy="equity_top_up",source_ref=f"SYNTHETIC-D266-{name}-closing-funding"),
            without_refinance=dict(applicability="included",source_ref=f"SYNTHETIC-D266-{name}-construction-carry",
                retention_terms="same_committed_facility_C52_until_documented_maturity",
                fee_at_stabilization=dict(value=rational(0),source_ref=f"SYNTHETIC-D266-{name}-explicit-zero-hold-fee")))
        inputs["supplemental_scope"][name]["sale_date"].update(value=str(sale),source_ref=f"SYNTHETIC-D266-{name}-sale-date")
        inputs["supplemental_scope"][name]["maturity_payments"].update(value=24,source_ref=f"SYNTHETIC-D266-{name}-24-payment-maturity")
        inputs["permanent_loan"]["scenarios"][name].update(maturity_payments=24,maturity_ref=f"SYNTHETIC-D266-{name}-bank-maturity")
        # A long maturity is explicit synthetic bank evidence, never an assumed real extension.
        inputs["construction_financing"]["scenarios"][name].update(maturity_date="2035-04-01",source_ref=f"SYNTHETIC-D266-{name}-long-construction-maturity-test")
        inputs["buyer_forward_property_tax"][name].update(window_start=str(sale),window_end=str(offset(sale,12)),
            source_ref=f"SYNTHETIC-D266-{name}-year-after-exit-buyer-tax-estimate")
        inputs["integrated_screening"][name]["reference_cap"].update(period_ref=period,source_ref=f"SYNTHETIC-D266-{name}-matched-reference-cap")
        for metric,context in inputs["criterion_noi_contexts"][name].items():
            context["period_ref"]=period
        inputs["definition_screening"][name]["rlv"].update(grid=[-500000,9500000,250000],source_ref=f"SYNTHETIC-D266-{name}-explicit-price-grid")
        for rule in spec["rules"]:
            if rule["scenario_id"]!=name:continue
            metric=rule["metric_id"]
            if metric in ("equity_multiple","IRR","asking_relative_to_supported_price"):
                rule["period_ref"]=f"{purchase}/{sale}"
            elif metric in ("equity_recovered","equity_cash_in","equity_TDC"):
                rule["period_ref"]=str(stabilized)
            else:
                rule["period_ref"]=period
    return spec


def evidence_bundle(spec,bank_values=None):
    records=pages(spec)
    inputs=spec["rent_inputs"]
    for name in ("Base","Downside"):
        role=name.lower()
        records[role]=[f"Maturity | payments | {inputs['permanent_loan']['scenarios'][name]['maturity_payments']}"
                       if line.startswith("Maturity |") else
                       f"Requested principal | USD | {amount(inputs['requested_principal'])}"
                       if line.startswith("Requested principal |") else line for line in records[role]]
        for cell,value in (bank_values or {}).get(name,{}).items():
            records[role]=[" | ".join([*line.split(" | ")[:-1],value]) if line.startswith(cell+" |") else line
                           for line in records[role]]
        role="construction_"+name.lower()
        records[role]=[f"Maturity date | {inputs['construction_financing']['scenarios'][name]['maturity_date']}"
                       if line.startswith("Maturity date |") else line for line in records[role]]
    upright=PdfWriter()
    font=ImageFont.truetype("DejaVuSansMono.ttf",size=24)
    for role in ORDER:
        if role=="official":
            upright.add_page(PdfReader(BytesIO(evidence_pdf(records,(role,))),strict=True).pages[0])
        else:
            raster=Image.new("L",(1900,1100),255)
            draw=ImageDraw.Draw(raster)
            for index,line in enumerate(records[role]):
                draw.text((36,35+52*index),line,font=font,fill=0)
            add_scan(upright,*raster.size,raster.tobytes())
    output=BytesIO()
    upright.write(output)
    raw=jpeg_bundle(output.getvalue(),progressive_roles=SCAN_ENCODINGS,oriented=True,rgb_quality=98,jpeg_roles=SCAN_ENCODINGS)
    reader,writer=PdfReader(BytesIO(raw),strict=True),PdfWriter()
    for role in SHUFFLED:
        writer.add_page(reader.pages[ORDER.index(role)])
    output=BytesIO()
    writer.write(output)
    return output.getvalue()


def sources_for(spec,directory,*,cell_changes=None,bank_values=None):
    from test_worksheet_integrated_transport import numeric_cells
    from check_lorena_criteria_D192 import change_cells
    sources=source_files(directory)
    sources["criteria_raw"]=change_cells(sources["criteria_raw"],{"B18":spec["criteria_revision"]})
    # This new synthetic case reaches commercial stabilization together with C47.
    # The original D200 files are kept intact.
    for name,value in (("Base","3"),("Downside","6")):
        key="workbook_raw" if name=="Base" else "downside_workbook_raw"
        sources[key]=numeric_cells(sources[key],{"C21":value}|(cell_changes or {}).get(name,{}))
    sources["evidence_raw"]=evidence_bundle(spec,bank_values)
    for name in ("Base","Downside"):
        spec["rent_inputs"]["bank_debt_yield"][name].update(quote_source_sha256=sha(sources["evidence_raw"]),
            source_ref=f"SYNTHETIC-D266-{name}-annex-bound-to-new-bank-quote")
    from worksheet_intake_D198 import SOURCES
    for argument,filename in SOURCES.items():
        (directory/filename).write_bytes(sources[argument])
    return sources


def independently_verify(spec,sources,result):
    """Reference formulas read source cells, not the horizon's computed amounts."""
    from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
    checks={}
    for name in ("Base","Downside"):
        view=result["scenarios"][name]
        assert view["blockers"]==[],view["blockers"]
        sheet=inspect_synthetic_input_sheet(sources["workbook_raw" if name=="Base" else "downside_workbook_raw"]).cells
        def cell(k):
            return Fraction(sheet[k]["literal"])
        inputs=spec["rent_inputs"]
        cfg=inputs["holding_horizon"]["scenarios"][name]
        calendar=inputs["project_calendar"]["scenarios"][name]
        start=offset(date.fromisoformat(calendar["tco_date"]),int(cell("C47")))
        sale=offset(start,cfg["holding_months"])
        assert view["project_calendar"]["stabilization_date"]==str(start)
        assert view["project_calendar"]["sale_date"]==str(sale)
        units=sum(g["units"] for g in inputs["groups"].values())
        other=cell("C13")*inputs["other_income"]["eligible_units"]*12
        cost=inputs["operating_costs"]["scenarios"][name]
        tax=inputs["property_tax"]["scenarios"][name]
        reserve=cell("C60")*inputs["replacement_reserve"]["scenarios"][name]["eligible_units"]
        property_coefficient=cell("C61")*amount(tax["assessed_tax_rate"]["value"])/amount(tax["market_proxy_cap"]["value"])
        floor=cell("C62")*units
        expected_noi=[]
        count=cfg["holding_months"]//12
        for year in range(count+1):
            rg=(1+cell("C75"))**year
            eg=(1+cell("C76"))**year
            gross=Fraction()
            for i,group in enumerate(("studio","1BR","2BR","3BR"),8):
                record=inputs["groups"][group]
                quantity=record["units"]
                if sheet["C7"]["literal"]=="PER SF":
                    quantity*=amount(record["rentable_sf_per_unit"])
                else:assert sheet["C7"]["literal"]=="PER UNIT"
                gross+=cell(f"C{i}")*quantity*12*rg
            effective=gross*(1-cell("C14")-cell("C15"))
            commercial=sum((cell(f"C{16+i}")*amount(inputs["commercial"]["uses"][use]["rentable_sf"])*rg
                            for i,use in enumerate(("retail","restaurant","office"))),Fraction())
            commercial*= (1-cell("C19"))*(1-cell("C20"))
            expenses=(amount(inputs["annual_expenses"]["fixed_opex"])+cell("C57")*cost["controllable_units"]+
                      cell("C59")*cost["insured_units"])*eg+cell("C58")*(effective+other)
            before=effective+other+commercial-expenses
            if year==count:
                buyer=inputs["buyer_forward_property_tax"][name]
                tax_due=sum(amount(buyer[k]) for k in ("school_tax","non_school_tax"))
                noi=before-tax_due
            else:
                noi=min(before-floor,before/(1+property_coefficient))
                actual=view["holding_horizon"]["annual_cash"][year]
                assert amount(actual["noi"])==noi
                assert amount(actual["noi_uw"])==noi-reserve
                assert amount(actual["reserve_deposit"])==reserve
            expected_noi.append(noi)
        loan=view["permanent_loan"]
        principal=amount(inputs["requested_principal"])
        rate=cell("C69")/4
        periods=int(cell("C70"))*4
        installment=principal/periods if rate==0 else principal*rate/(1-(1+rate)**(-periods))
        balance=principal
        due=[]
        for index in range(1,count*4+1):
            interest=balance*rate
            capital=installment-interest
            balance-=capital
            actual=loan["projected_schedule"][index-1]
            assert amount(actual["interest_due"])==interest
            assert amount(actual["principal_due"])==capital
            assert amount(actual["closing_balance"])==balance
            due.append((interest,capital))
        assert amount(view["debt_principal_paid_at_sale"])==balance
        gross=expected_noi[-1]/cell("C67")
        cost=gross*cell("C68")+amount(inputs["supplemental_scope"][name]["fixed_sale_cost"]["value"])
        assert amount(view["valuation_and_sale"]["gross_sale_price"])==gross
        assert amount(view["valuation_and_sale"]["sale_cost"])==cost
        for strategy,data in (("refi",view),("without_refi",view["horizon_without_refinance"])):
            assert data["blockers"]==[],data["blockers"]
            cash=data["cash_per_usd_10"]
            scale=Fraction(10)/amount(cfg["initial_equity"]["value"])
            assert amount(cash["reference_amount"])==10 and amount(cash["scale_factor"])==scale
            assert cash["events"][0]["kind"]=="contribution" and amount(cash["events"][0]["amount"])==10
            annual=view["holding_horizon"]["annual_cash"] if strategy=="refi" else data["annual_cash"]
            for year,record in enumerate(annual):
                service=installment*4 if strategy=="refi" else amount(view["construction_financing"]["construction_principal_payoff"])*cell("C52")
                expected=expected_noi[year]-reserve-service
                assert amount(record["distributions"])-amount(record["contributions"])==expected*scale
                assert [r["date"] for r in record["payments"]]==[str(offset(start,year*12+i)) for i in (3,6,9,12)]
            a=sum((amount(e["amount"]) for e in cash["events"] if e["kind"]=="contribution"),Fraction())
            d=sum((amount(e["amount"]) for e in cash["events"] if e["kind"]=="distribution"),Fraction())
            assert (a,d,d-a,d/a,max(Fraction(),a-d))==tuple(amount(cash[k]) for k in
                ("total_contributions","total_distributions","net_cash_profit","equity_multiple","unrecovered_after_sale"))
            closing=view["holding_horizon"] if strategy=="refi" else data
            proof=closing["sale_closing"]
            sale_principal=balance if strategy=="refi" else amount(view["construction_financing"]["construction_principal_payoff"])
            reserve_released=reserve*count*amount(inputs["replacement_reserve"]["scenarios"][name]["sale_release_fraction"])
            if strategy=="refi":
                reserve_released+=cell("C74")*inputs["refinance_costs"]["scenarios"][name]["eligible_units"]*amount(inputs["refinance_costs"]["scenarios"][name]["sale_release_fraction"])
            opening_free=amount(closing["sale_source"]["amounts"]["opening_free_cash"]["value"])
            residual=opening_free+gross-cost-sale_principal+reserve_released
            assert amount(proof["exportable_equity_distribution"])-amount(proof["exportable_equity_contribution"])==residual
            assert amount(proof["payoff_totals"]["principal"])==sale_principal
            irr=result["screening"]["irr_by_scenario"][name] if strategy=="refi" else data["irr"]
            enclosure=irr.get("annual_enclosure")
            assert enclosure is not None and not irr["blockers"],irr["blockers"]
            flows={d:Fraction() for d in view["project_calendar"]["equity_dates"]}
            for e in cash["events"]: flows[e["date"]]+=amount(e["amount"])*(1 if e["kind"]=="distribution" else -1)
            signs=[v>0 for v in flows.values() if v]
            assert signs==sorted(signs) and signs[0] is False and signs[-1] is True
            for edge,positive in (("lower",True),("upper",False)):
                annual_rate=amount(enclosure[edge])+1
                num,den=isqrt(isqrt(annual_rate.denominator)),isqrt(isqrt(annual_rate.numerator))
                assert num**4==annual_rate.denominator and den**4==annual_rate.numerator
                discount=Fraction(num,den)
                npv=sum((flow*discount**i for i,flow in enumerate(flows.values())),Fraction())
                assert npv>=0 if positive else npv<=0
        checks[name]=dict(stabilization=str(start),sale=str(sale),full_years=count,loan_payments=count*4,
            annual_noi_and_forward_checked=count+1,regular_payment_checked=True,sale_payoff_after_regular_payment=True,
            four_cash_dates_each_year=True,two_route_gross_cash_and_normalization_verified=True,
            both_annual_irr_bounds_substituted_in_source_cash_polynomial=True)
    return checks


def run(output):
    spec=settings()
    sources=sources_for(spec,output/"sources")
    registration=register(sources,"SYNTHETIC-D266-five-year-intake")
    (output/"settings.json").write_bytes(encoded(spec))
    (output/"registration.json").write_bytes(encoded(registration))
    assemble(spec,registration,sources,output/"package")
    result=json.loads((output/"package/results.json").read_bytes())
    return dict(decision=result["decision"],simulation=result["simulation_result"],
        blockers=result["local_review"]["blockers"],
        scenarios={n:dict(state=v["state"],blockers=v["blockers"],cash=v.get("cash_per_usd_10"),
            no_refi_state=v.get("horizon_without_refinance",{}).get("state"),
            no_refi_blockers=v.get("horizon_without_refinance",{}).get("blockers")) for n,v in result["scenarios"].items()})


def verify(output):
    from miniuw_worksheet_v1 import CURRENT_REVISION_FILE,read_package,verify_package,deliver_package
    from worksheet_intake_D198 import read_source_directory
    from worksheet_sale_rate_grid_D84 import money
    from worksheet_irr_D122 import display_enclosure
    run(output)
    spec=json.loads((output/"settings.json").read_bytes())
    sources=read_source_directory(output/"sources")
    saved=read_package(output/"package")
    result=json.loads(saved["results.json"])
    assert result["decision"]=="PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"]
    assert not result["local_review"]["blockers"] and not result["revision_review"]["blockers"]
    checked=independently_verify(spec,sources,result)
    audit=verify_package(output/"package",current_revision_raw=saved[CURRENT_REVISION_FILE])
    assert audit["vigencia"]=="VIGENTE"
    current=output/"Vigente.json"
    current.write_bytes(saved[CURRENT_REVISION_FILE])
    destination=output/"MiniUW_Horizonte_Cinco_Anos_D266.pdf"
    delivery=deliver_package(output/"package",destination,current)
    assert destination.read_bytes()==saved["MiniUW_Resumen.pdf"]
    with PdfReader(destination,strict=True) as document:
        assert len(document.pages)==1
        text=document.pages[0].extract_text()
        assert all(word in text for word in ("USD 10","Base","Downside","2033-01-01","2033-07-01","PENDING"))
    rows={}
    for name,view in result["scenarios"].items():
        scenarios={}
        for route,value in (("with_refinance",view),("without_refinance",view["horizon_without_refinance"])):
            cash=value["cash_per_usd_10"]
            irr=result["screening"]["irr_by_scenario"][name] if route=="with_refinance" else value["irr"]
            scenarios[route]=dict(initial_usd="10.00",additional_usd=money(rational(amount(cash["total_contributions"])-10)),
                receipts_usd=money(cash["total_distributions"]),unrecovered_usd=money(cash["unrecovered_after_sale"]),
                equity_multiple=money(cash["equity_multiple"]),annual_irr=display_enclosure(irr["annual_enclosure"]),
                cash_sha256=sha(encoded(cash)))
        rows[name]=dict(stabilization=view["project_calendar"]["stabilization_date"],sale=view["project_calendar"]["sale_date"],
            holding_months=view["holding_horizon"]["months"],routes=scenarios)
    summary=dict(status="passed",milestone="D266",decision="PENDING",historical_return="PENDING",deployment_enabled=False,
        real_decisions_enabled=False,simulation_result=result["simulation_result"],simulation_blockers=result["screening"]["simulation_blockers"],
        independent_checks=checked,scenarios=rows,source_files={k:sha(v) for k,v in sources.items()},
        case_sha256=sha(saved["case.json"]),pdf_sha256=sha(destination.read_bytes()),pdf_pages=1,audit=audit,delivery=delivery)
    (output/"validacion.json").write_bytes(encoded(summary))
    return summary


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d266-") as temporary:
        root=args.output or Path(temporary)
        root.mkdir(exist_ok=True)
        result=verify(root)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
