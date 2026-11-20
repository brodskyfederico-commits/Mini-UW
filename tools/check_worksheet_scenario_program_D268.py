"""Build explicit synthetic source packets and independently reconcile the program."""
from argparse import ArgumentParser
from copy import deepcopy
from datetime import date
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from math import isqrt
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

from check_worksheet_construction_pdf_D157 import pages, ORDER
from check_worksheet_evidence_pdf_D156 import evidence_pdf
from check_worksheet_evidence_jpeg_D161 import jpeg_bundle
from check_worksheet_evidence_progressive_order_D164 import SCAN_ENCODINGS, SHUFFLED
from check_worksheet_evidence_scan_D158 import add_scan
from check_worksheet_holding_horizon_D266 import sources_for
from check_worksheet_horizon_fiscal_D267 import settings as prior_settings, source_cells, value, month, roll
from check_worksheet_horizon_fiscal_D267 import build_reference as prior_reference, independent_taxes as prior_taxes
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from plan_return_D107 import OPERATING_PERIOD, FORWARD_PERIOD
from test_worksheet_integrated_transport import numeric_cells
from worksheet_intake_D198 import source_inventory
from worksheet_scenario_program_D268 import (SCHEMA, DRIVERS, UPSIDE_ROLE, driver_terms, transformed,
    leaf_changes, packet_hash, run_program, load_packet, check_variant)
from worksheet_variant_evidence_D268 import (SCHEMA as CASE_SCHEMA, STRESS_PROFILE, STRESS_RULE,
    inputs_digest, REFERENCE_FILE)


def decimal(value):
    with localcontext() as context:
        context.prec = 50
        text = format(Decimal(value.numerator) / Decimal(value.denominator), "f")
    assert Q(text) == value, "Non-terminating decimal requires a different worksheet source contract"
    return text


def settings():
    spec = prior_settings()
    spec["schema"] = CASE_SCHEMA
    inputs = spec["rent_inputs"]
    inputs["stabilized_tax_stress"] = dict(profile=STRESS_PROFILE, rule=STRESS_RULE, scenarios={
        name: dict(relative_change=rational(0), source_ref=f"SYNTHETIC-D268-{name}-explicit-zero-tax-stress")
        for name in ("Base", "Downside")})
    # Explicit forecasts covering the longest calendar in this test corpus.
    for name, tax in inputs["florida_property_tax"]["scenarios"].items():
        for year in (2035, 2036):
            assessed = 2_000_000 + (year - 2027) * (300_000 if name == "Base" else 400_000)
            if name == "Downside": assessed += 600_000
            tax["rolls"]["seller"][str(year)] = roll(assessed, ref=f"SYNTHETIC-D268-{name}-{year}-declared-forecast")
            tax["rolls"]["millage"][str(year)] = dict(school_mills=rational(4), non_school_mills=rational(9),
                source_ref=f"SYNTHETIC-D268-{name}-{year}-declared-millage")
            tax["rolls"]["buyer"][str(year)] = roll(5_000_000 if name == "Base" else 5_500_000,
                "ownership_or_control_reset", inputs["supplemental_scope"][name]["sale_date"]["value"],
                ref=f"SYNTHETIC-D268-{name}-{year}-declared-buyer-forecast")
    return spec


def drivers(*, upside=False):
    # These are test vectors only. No executable production default is defined.
    values = {"18": Q(-1, 100), "19": Q(-1, 100), "20": Q(1, 10), "21": Q(1, 10),
        "22": Q(1, 100), "23": Q(3), "24": Q(3), "25": Q(10), "26": Q(10),
        "27": Q(10), "28": Q(1, 10), "29": Q(1, 20), "30": Q(-1), "31": Q(10), "32": Q(-1, 10)}
    if upside:
        values = {key: Q() if key in ("23", "24") else -value for key, value in values.items()}
    return {key: dict(applicability="included", unit=DRIVERS[key][2],
        values={name: rational(delta) for name in ("Base", "Downside")},
        source_ref=f"SYNTHETIC-D268-{'upside' if upside else 'adverse'}-{key}-test-vector")
        for key, delta in values.items()}


def source_bundle(spec, sources):
    records = pages(spec)
    inputs = spec["rent_inputs"]
    for name in ("Base", "Downside"):
        sheet, cell = source_cells(sources, name)
        cfg = inputs["construction_financing"]["scenarios"][name]
        labels = {key: sheet[key]["literal"] for key in ("C51", "C52", "C53")}
        labels.update({"Maximum commitment": decimal(value(cfg["maximum_commitment"])),
            "Requested invoice share": decimal(value(cfg["requested_invoice_fraction"])),
            "Available per draw": decimal(value(cfg["available_per_draw_checkpoint"])), "Maturity date": cfg["maturity_date"]})
        bank = inputs["permanent_loan"]["scenarios"][name]
        permanent = {key: sheet[key]["literal"] for key in ("C69", "C70", "C71", "C72")}
        permanent.update({"Requested principal": decimal(value(inputs["requested_principal"])),
                          "Maturity": str(bank["maturity_payments"])})
        for role, changes in (("construction_" + name.lower(), labels), (name.lower(), permanent)):
            records[role] = [" | ".join([*line.split(" | ")[:-1], changes[line.split(" | ")[0]]])
                             if line.split(" | ")[0] in changes else line for line in records[role]]
        basis = sheet["C34"]["literal"]
        if basis == "$/UNIT": quantity = sum(g["units"] for g in inputs["groups"].values())
        elif basis == "TOTAL": quantity = Q(1)
        elif basis == "$/GSF":
            area = inputs["development"]["scenarios"][name]["plan_gsf"]
            quantity = value(area["value"]) if area["state"] == "declared" else cell("C36")
        else: raise ValueError("Unrecognized test cost basis")
        records["gc"] = [" | ".join([*line.split(" | ")[:-1], decimal(cell("C35") * quantity)])
                         if line.startswith("Vertical " + name + " |") else line for line in records["gc"]]
    writer = PdfWriter()
    font = ImageFont.truetype("DejaVuSansMono.ttf", size=24)
    for role in ORDER:
        if role == "official":
            writer.add_page(PdfReader(BytesIO(evidence_pdf(records, (role,))), strict=True).pages[0])
        else:
            image = Image.new("L", (1900, 1100), 255)
            draw = ImageDraw.Draw(image)
            for index, line in enumerate(records[role]): draw.text((36, 35 + 52 * index), line, font=font, fill=0)
            add_scan(writer, *image.size, image.tobytes())
    buffer = BytesIO(); writer.write(buffer)
    raw = jpeg_bundle(buffer.getvalue(), progressive_roles=SCAN_ENCODINGS, oriented=True,
                      rgb_quality=98, jpeg_roles=SCAN_ENCODINGS)
    reader = PdfReader(BytesIO(raw), strict=True); writer = PdfWriter()
    for role in SHUFFLED: writer.add_page(reader.pages[ORDER.index(role)])
    buffer = BytesIO(); writer.write(buffer)
    return buffer.getvalue()


def reference_taxes(spec, sources, name):
    traces = prior_taxes(spec, sources, name)
    record = spec["rent_inputs"]["stabilized_tax_stress"]["scenarios"][name]
    factor = 1 + value(record["relative_change"])
    for key, original in list(traces.items()):
        if key.startswith("preopening-"): continue
        trace = deepcopy(original)
        old_sha = trace.pop("source_sha256")
        trace.update(unstressed_source_sha256=old_sha,
                     stress_contract=record | dict(profile=STRESS_PROFILE, rule=STRESS_RULE))
        # Independent reference arithmetic operates on the source-based tax oracle.
        for field in ("school_tax", "non_school_tax", "total"):
            trace[field] = rational(value(original[field]) * factor)
        for row in trace["rolls"]:
            row["school_tax"] = rational(value(row["school_tax"]) * factor)
            row["non_school_tax"] = rational(value(row["non_school_tax"]) * factor)
        trace["source_sha256"] = sha(encoded(trace))
        traces[key] = trace
    return traces


def reference(spec, sources):
    ref = prior_reference(spec, sources)
    ref["inputs_sha256"] = inputs_digest(spec["rent_inputs"])
    for name in ("Base", "Downside"):
        sheet, cell = source_cells(sources, name)
        cfg = spec["rent_inputs"]["development"]["scenarios"][name]
        basis = sheet["C34"]["literal"]
        if basis == "$/UNIT": quantity = sum(g["units"] for g in spec["rent_inputs"]["groups"].values())
        elif basis == "TOTAL": quantity = Q(1)
        else: quantity = value(cfg["plan_gsf"]["value"]) if cfg["plan_gsf"]["state"] == "declared" else cell("C36")
        ref["gc_cost"][name][-1] = decimal(cell("C35") * quantity)
        for kind, record in spec["rent_inputs"]["market_evidence"]["scenarios"][name].items():
            reading = ref["market"][name][kind]
            reading.update(document=deepcopy(record["document"]), sha256=record["sha256"])
            reading["cells"] = {key: sheet[key]["literal"] for key in reading["cells"]}
        ref["holding_fiscal"][name]["windows"] = reference_taxes(spec, sources, name)
    return ref


def independently_verify(spec,sources,result):
    """Financial reference from literal cells and rolls, not the engine's totals."""
    from math import isqrt
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
        assert value(view["valuation_and_sale"]["gross_sale_price"]) == sale_price
        if refi_allowed: assert value(view["gross_sale"]) == sale_price
        # Independent LTV, DSCR and debt-yield limits from literal terms and NOI.
        potential = sum(cell(f"C{i}") * inputs["groups"][group]["units"] * 12 *
                        (value(inputs["groups"][group]["rentable_sf_per_unit"]) if sheet["C7"]["literal"] == "PER SF" else 1)
                        for i, group in enumerate(("studio", "1BR", "2BR", "3BR"), 8))
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


def make_packet(base, base_sources, label, selected, driver_records, directory, *, revision=None):
    spec = deepcopy(base)
    spec["local_sources"]["revision"] = "SYNTHETIC-D268-" + label if revision is None else revision
    sources = dict(base_sources)
    changes = {}
    for name, argument in zip(("Base", "Downside"), ("workbook_raw", "downside_workbook_raw"), strict=True):
        sheet, cell = source_cells(base_sources, name)
        changes[name] = {}
        for key in selected:
            terms = driver_terms(driver_records[key], key)
            if terms is None: continue
            for target in DRIVERS[key][0]: changes[name][target] = decimal(transformed(cell(target), terms[name], key))
            if key == "29":
                previous = value(base["rent_inputs"]["stabilized_tax_stress"]["scenarios"][name]["relative_change"])
                spec["rent_inputs"]["stabilized_tax_stress"]["scenarios"][name] = dict(
                    relative_change=rational((1 + previous) * (1 + terms[name]) - 1), source_ref=driver_records[key]["source_ref"])
        sources[argument] = numeric_cells(base_sources[argument], changes[name])
        _, current = source_cells(sources, name)
        inputs = spec["rent_inputs"]
        purchase = date.fromisoformat(inputs["development"]["scenarios"][name]["purchase_date"])
        tco = month(purchase, int(current("C46"))); stabilization = month(tco, int(current("C47")))
        sale = month(stabilization, inputs["holding_horizon"]["scenarios"][name]["holding_months"])
        inputs["project_calendar"]["scenarios"][name]["tco_date"] = str(tco)
        inputs["supplemental_scope"][name]["sale_date"]["value"] = str(sale)
        for row in inputs["florida_property_tax"]["scenarios"][name]["rolls"]["buyer"].values(): row["event_date"] = str(sale)
        period = f"{stabilization}/{month(stabilization, 12)}"
        inputs["integrated_screening"][name]["reference_cap"]["period_ref"] = period
        for context in inputs["criterion_noi_contexts"][name].values(): context["period_ref"] = period
        for rule in spec["rules"]:
            if rule["scenario_id"] != name: continue
            metric = rule["metric_id"]
            rule["period_ref"] = f"{purchase}/{sale}" if metric in ("equity_multiple", "IRR", "asking_relative_to_supported_price") else (
                str(stabilization) if metric in ("equity_recovered", "equity_cash_in", "equity_TDC") else period)
        market = inputs["market_evidence"]["scenarios"][name]
        # Supporting synthetic absorption and insurance evidence are explicit new records.
        market["absorption"]["document"]["ranges"]["C47"] = dict(minimum=rational(current("C47")), maximum=rational(current("C47")))
        market["insurance"]["document"]["premium_per_insured_unit"] = rational(current("C59"))
        for record in market.values(): record["sha256"] = sha(encoded(record["document"]))
    sources["evidence_raw"] = source_bundle(spec, sources)
    for record in spec["rent_inputs"]["bank_debt_yield"].values(): record["quote_source_sha256"] = sha(sources["evidence_raw"])
    independent = reference(spec, sources)
    sources["independent_reference_raw"] = encoded(independent)
    directory.mkdir(parents=True)
    for argument, filename in source_inventory(sources).items(): (directory / filename).write_bytes(sources[argument])
    (directory / "settings.json").write_bytes(encoded(spec))
    return spec, sources


def build_program(directory):
    directory.mkdir(parents=True, exist_ok=False)
    base = settings(); initial = sources_for(base, directory / "seed")
    base, sources = make_packet(base, initial, "baseline", [], drivers(), directory / "baseline")
    program = dict(schema=SCHEMA, id="SYNTHETIC-D268-fifteen-explicit-drivers",
        source_ref="SYNTHETIC-D268-test-program-no-production-defaults",
        baseline=dict(name="baseline", packet_sha256=packet_hash(base, sources)),
        drivers=drivers(), variants={}, upside=dict(role=UPSIDE_ROLE, drivers=drivers(upside=True), packet={}))
    for label in (*DRIVERS, "combined", "upside"):
        records = program["upside"]["drivers"] if label == "upside" else program["drivers"]
        selected = list(DRIVERS) if label in ("combined", "upside") else [label]
        spec, packet = make_packet(base, {key: raw for key, raw in sources.items() if key != "independent_reference_raw"},
                                  label, selected, records, directory / label)
        declaration = dict(name=label, packet_sha256=packet_hash(spec, packet), settings_changes=leaf_changes(base, spec))
        if label == "upside": program["upside"]["packet"] = declaration
        else: program["variants"][label] = declaration
    (directory / "program.json").write_bytes(encoded(program))
    return program


def build_repair(source_root):
    program = json.loads((source_root / "program.json").read_bytes())
    base, sources = load_packet(source_root, program["baseline"]["name"])
    sources.pop("independent_reference_raw")
    spec, packet = make_packet(base, sources, "33", list(DRIVERS), program["drivers"], source_root / "combined-restored")
    program["variants"]["combined"] = dict(name="combined-restored", packet_sha256=packet_hash(spec, packet),
                                           settings_changes=leaf_changes(base, spec))
    (source_root / "program-restored.json").write_bytes(encoded(program))
    return program


def verify_completed(source_root, output, repaired_output):
    """Read the immutable sources again; do not substitute results for the oracle."""
    from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, read_package
    program = json.loads((source_root / "program.json").read_bytes())
    report = json.loads((output / "report.json").read_bytes())
    assert report["program_sha256"] == sha(encoded(program))
    assert set(report["records"]) == {"baseline", *DRIVERS, "combined", "upside"}
    base, base_sources = load_packet(source_root, program["baseline"]["name"])
    assert packet_hash(base, base_sources) == program["baseline"]["packet_sha256"]
    checked = {}
    declarations = {"baseline": program["baseline"], **program["variants"], "upside": program["upside"]["packet"]}
    for key, declaration in declarations.items():
        spec, sources = load_packet(source_root, declaration["name"])
        record = report["records"][key]
        if key != "baseline":
            selected = list(DRIVERS) if key in ("combined", "upside") else [key]
            records = program["upside"]["drivers"] if key == "upside" else program["drivers"]
            assert record["changes"] == check_variant(base, base_sources, spec, sources, declaration, records, selected)
        saved = read_package(output / ("case-" + key))
        result = json.loads(saved["results.json"])
        assert saved[REFERENCE_FILE] == sources["independent_reference_raw"]
        assert sha(saved["results.json"]) == record["results_sha256"]
        assert record["replay"]["status"] == "verified_source_first" and record["replay"]["audit_bot"] == "B16", key
        assert record["replay"]["vigencia"] == ("PENDING" if key == "combined" else "VIGENTE"), key
        assert result["decision"] == "PENDING" and not result["deployment_enabled"] and not result["real_decisions_enabled"]
        if key == "combined":
            assert result["critical_evidence_review"]["status"] == "PENDING"
            assert result["critical_evidence_review"]["counts"]["FALSE_GREEN"] == 0
            assert any("ocr_confidence_below" in reason for reason in result["local_review"]["blockers"])
            assert all(view["cash_per_usd_10"] is None for view in result["scenarios"].values())
            checks = dict(state="PENDING", source_blockers=result["local_review"]["blockers"],
                          no_unverified_cash_published=True)
        else:
            assert result["critical_evidence_review"]["status"] == "PASSED", key
            checks = independently_verify(spec, sources, result)
            for name in ("Base", "Downside"):
                for route, view in (("with_refi", result["scenarios"][name]),
                                    ("without_refi", result["scenarios"][name]["horizon_without_refinance"])):
                    assert record["cash"][name][route]["cash_per_usd_10"] == view["cash_per_usd_10"]
                    assert value(view["cash_per_usd_10"]["reference_amount"]) == 10
        assert len(PdfReader(BytesIO(saved["MiniUW_Resumen.pdf"]), strict=True).pages) == 1
        checked[key] = dict(source_packet_sha256=packet_hash(spec, sources), independent_checks=checks,
            verified_critical_fields=result["critical_evidence_review"]["critical_fields"],
            source_first_replay=record["replay"], case_sha256=sha(saved["case.json"]),
            results_sha256=sha(saved["results.json"]), pdf_sha256=sha(saved["MiniUW_Resumen.pdf"]))
    assert report["baseline_simulation"] == json.loads((output / "case-baseline/results.json").read_bytes())["simulation_result"]
    assert report["upside_role"] == UPSIDE_ROLE and not report["defaults_loaded"]
    corrected_program = json.loads((source_root / "program-restored.json").read_bytes())
    corrected_report = json.loads((repaired_output / "report.json").read_bytes())
    assert corrected_report["execution_scope"] == ["combined"]
    assert corrected_report["baseline_simulation"] == "NOT_EXECUTED"
    assert set(corrected_report["records"]) == {"combined"}
    declaration = corrected_program["variants"]["combined"]
    spec, sources = load_packet(source_root, declaration["name"])
    check_variant(base, base_sources, spec, sources, declaration, program["drivers"], list(DRIVERS))
    saved = read_package(repaired_output / "case-combined")
    result = json.loads(saved["results.json"])
    assert result["critical_evidence_review"]["status"] == "PASSED"
    assert corrected_report["records"]["combined"]["replay"]["vigencia"] == "VIGENTE"
    checked["combined_restored"] = dict(independent_checks=independently_verify(spec, sources, result),
        source_packet_sha256=packet_hash(spec, sources), case_sha256=sha(saved["case.json"]),
        pdf_sha256=sha(saved["MiniUW_Resumen.pdf"]), results_sha256=sha(saved["results.json"]),
        verified_critical_fields=result["critical_evidence_review"]["critical_fields"],
        source_first_replay=corrected_report["records"]["combined"]["replay"])
    return dict(milestone="D268", status="passed", synthetic_source_packets=len(checked),
        financial_routes_checked=sum(len(value.get("verified_routes", [])) for row in checked.values()
            for name, value in row["independent_checks"].items() if name in ("Base", "Downside")),
        dated_debt_schedules_checked=(len(checked)-1)*2,
        annual_and_forward_NOI_checked=(len(checked)-1)*2*6, program_sha256=sha(encoded(program)),
        independent_reference_origin="source_cells_explicit_forecasts_and_separate_financial_formulas_not_model_results",
        cases=checked, real_decision="PENDING", historical_return="PENDING",
        personal_return_without_terms="PENDING", deployment_enabled=False, real_decisions_enabled=False,
        all_33_policies_certified=False)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    program = build_program(args.output / "sources")
    expected = Path(__file__).resolve().parents[1] / "templates/synthetic-scenario-program-D268.json"
    assert encoded(program) == expected.read_bytes(), "Versioned synthetic program drift"
    report = run_program(program, args.output / "sources", args.output / "run")
    corrected = build_repair(args.output / "sources")
    run_program(corrected, args.output / "sources", args.output / "repair", cases_to_run={"combined"})
    validation = verify_completed(args.output / "sources", args.output / "run", args.output / "repair")
    (args.output / "validation.json").write_bytes(encoded(validation))
    print(json.dumps({key: validation[key] for key in ("status", "synthetic_source_packets", "financial_routes_checked")}))


if __name__ == "__main__":
    main()
