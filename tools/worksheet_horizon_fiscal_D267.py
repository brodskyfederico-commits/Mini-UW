"""Versioned quarterly M2 cash and independent critical-evidence bindings."""
from datetime import date
from fractions import Fraction
from pathlib import Path
import json
from hashlib import sha256
from types import FunctionType

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from plan_return_D107 import OPERATING_PERIOD, FORWARD_PERIOD
from worksheet_holding_horizon_D266 import RULES as PREVIOUS_RULES, amount
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_project_calendar_D145 import offset


PROFILE = "miniuw.synthetic-integrated-fiscal-holding-horizon.v2"
RULES = PREVIOUS_RULES | dict(
    cash="equal_operating_quarters_except_dated_M2_tax_roll_settlements",
    zero_roles=[key for key in PREVIOUS_RULES["zero_roles"] if key != "preopening_property_tax_outside_budget"],
    property_tax="documented_M2_rolls_from_purchase_through_forward_exit_window")
CASH_PROFILE = "miniuw.synthetic-dated-M2-quarterly-cash.v1"
CASH_RULES = dict(settlement="calendar_quarter_end_after_three_complete_months",
    preopening="additional_project_use_excluded_from_declared_budget",
    operating="dated_tax_replaces_annual_tax_quarter_allocation_once",
    source="M2_school_and_non_school_rolls_and_millage",
    closing="regular_operating_quarter_settled_before_sale_no_extra_tax_charge")
REFERENCE = Path(__file__).resolve().parents[1]/"templates/synthetic-critical-evidence-D267.json"
BASE_ALGORITHM_SHA256 = "bba535fd748b8f3fb6c982d4e8f9109e1db8dd36d64abce0ffb047a8f3b2c924"


def functions():
    """Reuse pinned D266 code in isolated globals; archived v1 remains untouched."""
    import worksheet_holding_horizon_D266 as base
    require(sha256(Path(base.__file__).read_bytes()).hexdigest()==BASE_ALGORITHM_SHA256,
            "holding_fiscal_base_algorithm_revision_unconfirmed")
    env=dict(vars(base))
    for name,value in vars(base).items():
        if isinstance(value,FunctionType) and value.__module__==base.__name__:
            cloned=FunctionType(value.__code__,env,value.__name__,value.__defaults__,value.__closure__)
            cloned.__kwdefaults__=None if value.__kwdefaults__ is None else dict(value.__kwdefaults__)
            env[name]=cloned
    env.update(PROFILE=PROFILE,RULES=RULES,__file__=__file__,operation_rows=operation_rows)
    return env


def configuration(raw,name):
    return functions()["configuration"](raw,name)


def horizon_calendar(*args,**kwargs):
    return functions()["horizon_calendar"](*args,**kwargs)


def calculate(*args,**kwargs):
    result=functions()["calculate"](*args,**kwargs)
    result["holding_horizon"]["fiscal_extension"]=dict(profile=PROFILE,base_algorithm_sha256=BASE_ALGORITHM_SHA256,
        extension_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),global_mutation=False,rounding="none")
    return result


def operation_rows(calendar,years,schedule,reserve,opening_free,permanent_balance,config):
    from worksheet_holding_horizon_D266 import operation_rows as previous,verify_rows
    rows=previous(calendar,years,schedule,reserve,opening_free,permanent_balance,config)
    for index,row in enumerate(rows):
        year=years[index//4]
        quarters=year["quarterly_taxes"]
        require(len(quarters)==4,"M2:complete_quarter_tax_inventory_required")
        trace=quarters[index%4]
        tax=amount(trace["total"])
        require(tax is not None and tax>=0 and trace["window_end_exclusive"]==row["date"],
                "M2:quarter_tax_or_settlement_date_unconfirmed")
        annual=year["assembly"].noi_run.payload
        allocated=amount(annual["property_tax"])/4
        income=amount(annual["income_total"])/4
        expenses=amount(annual["expenses_excluding_tax"])/4+tax
        service=row["debt_interest"]+row["debt_principal"]
        net=income-expenses-service-row["reserve_deposit"]
        contribution,distribution=max(Fraction(),-net),max(Fraction(),net)
        row.update(sources=income+contribution,uses=expenses+service+distribution,
            contribution=contribution,distribution=distribution,noi=row["noi"]+allocated-tax,
            property_tax_paid=tax,property_tax_source_sha256=trace["source_sha256"],
            source_ref=row["source_ref"]+f" and sha256:{trace['source_sha256']}")
    verify_rows(rows)
    for i,year in enumerate(years):
        require(sum(r["noi"] for r in rows[4*i:4*i+4])==amount(year["assembly"].noi_run.payload["noi"]),
                "M2:dated_cash_noi_does_not_match_annual_accrual")
    return rows


def fiscal_input_digest(taxes, cash, name):
    return sha(encoded(dict(tax_policy=taxes.get("policy"),tax_scenario=object_or_empty(taxes.get("scenarios")).get(name),
        cash_profile=cash.get("profile"),cash_rules=cash.get("rules"),cash_source_ref=cash.get("source_ref"),
        cash_scenario=object_or_empty(cash.get("scenarios")).get(name))))


def reference_for(case):
    """Only reviewed repository reference paths; never a path supplied by a deal."""
    if object_or_empty(object_or_empty(case.get("rent_inputs")).get("holding_horizon")).get("profile") == PROFILE:
        return REFERENCE
    from audit_worksheet_critical_evidence_D219 import REFERENCE as previous
    return previous


def window_contract(calendar,name):
    start=date.fromisoformat(calendar["stabilization_date"])
    purchase=date.fromisoformat(calendar["purchase_date"])
    sale=date.fromisoformat(calendar["sale_date"])
    months=calendar["holding_months"]
    pre=(start.year-purchase.year)*12+start.month-purchase.month
    require(pre>0 and pre%3==0 and months%12==0,"M2:horizon_cash_grid_unconfirmed")
    windows={key:(date.fromisoformat(value),12,key==FORWARD_PERIOD) for key,value in calendar["noi_window_starts"].items()}
    annual=[OPERATING_PERIOD]+[f"SYNTHETIC-D266-{name}-year-{i+1}" for i in range(1,months//12)]
    for i,key in enumerate(annual):windows[key]=(offset(start,12*i),12,False)
    windows["holding_total"]=(start,months,False)
    for i in range(months//3):windows[f"operation-quarter-{i+1}"]=(offset(start,3*i),3,False)
    for i in range(pre//3):windows[f"preopening-quarter-{i+1}"]=(offset(purchase,3*i),3,False)
    require(offset(start,months)==sale,"M2:horizon_sale_date_conflicts")
    return windows,annual,pre//3


def fiscal_cash(raw,cash_raw,name,calendar):
    from worksheet_florida_tax_D203 import window_taxes
    cash=object_or_empty(cash_raw)
    require(cash.keys()=={"profile","rules","source_ref","scenarios"} and cash["profile"]==CASH_PROFILE
            and cash["rules"]==CASH_RULES and synthetic_id(cash["source_ref"])
            and set(object_or_empty(cash["scenarios"]))=={"Base","Downside"},"M2:cash_policy_or_inventory_unconfirmed")
    terms=object_or_empty(cash["scenarios"][name])
    require(terms.keys()=={"source_ref","budget_exclusion_ref"}
            and all(synthetic_id(value) for value in terms.values()),"M2:preopening_tax_budget_exclusion_unconfirmed")
    windows,annual,pre=window_contract(calendar,name)
    taxes=window_taxes(raw,name,date.fromisoformat(calendar["sale_date"]),windows)
    inputs_sha=fiscal_input_digest(object_or_empty(raw),cash,name)
    uses={}
    for i in range(pre):
        key=f"preopening-quarter-{i+1}"
        trace=taxes[key]
        uses[trace["window_end_exclusive"]]=dict(value=trace["total"],source_ref=f"sha256:{trace['source_sha256']}")
    quarters=[]
    for i in range(calendar["holding_months"]//3):quarters.append(taxes[f"operation-quarter-{i+1}"])
    for i,key in enumerate(annual):
        for component in ("school_tax","non_school_tax","total"):
            require(sum(amount(q[component]) for q in quarters[4*i:4*i+4])==amount(taxes[key][component]),
                    "M2:quarter_and_annual_tax_disagree:"+key+":"+component)
    require(sum(amount(taxes[key]["total"]) for key in annual)==amount(taxes["holding_total"]["total"]),
            "M2:annual_and_holding_tax_disagree")
    result=dict(state="checked_synthetic",blockers=[],profile=CASH_PROFILE,rules=CASH_RULES,
        source_ref=cash["source_ref"],scenario_sources=terms,inputs_sha256=inputs_sha,annual_keys=annual,
        audit_windows={key:dict(state="checked_synthetic",blockers=[],inputs_sha256=inputs_sha,payload=value)
                       for key,value in taxes.items()},
        preopening_uses=dict(source_ref=terms["budget_exclusion_ref"],by_date=uses),
        quarterly_taxes=quarters,
        preopening_tax_total=rational(sum(amount(row["value"]) for row in uses.values())),
        operating_tax_total=taxes["holding_total"]["total"],forward_tax=taxes[FORWARD_PERIOD])
    return taxes,taxes[OPERATING_PERIOD],result


def critical_fiscal_fields(ref):
    """Expected values come from a separate versioned inventory, never the result."""
    from audit_worksheet_critical_evidence_D219 import Claim,Field
    inventory=ref["holding_fiscal"]
    require(inventory.keys()=={"Base","Downside"},"D267:fiscal_reference_scenario_inventory_incomplete")
    for name,record in inventory.items():
        source=Claim("M2",("scenarios",name,"holding_horizon","fiscal_cash"),
            {("inputs_sha256",):record["inputs_sha256"],("profile",):CASH_PROFILE,("rules",):CASH_RULES})
        yield Field(f"{name}:fiscal:source_inventory",(source,),f"case.json / rent_inputs / florida_property_tax / {name}")
        for key,value in record["windows"].items():
            path=("scenarios",name,"holding_horizon","fiscal_cash","audit_windows",key)
            claim=Claim("M2",path,{("inputs_sha256",):record["inputs_sha256"],("payload",):value},
                (("scenarios",name,"holding_horizon","fiscal_cash"),))
            yield Field(f"{name}:fiscal:{key}",(claim,),f"case.json / rent_inputs / florida_property_tax / {name} / {key}")


def fiscal_source_issues(case,ref,documents=None):
    """Bind the independent inventory to the actual case's supplied fiscal data."""
    inputs=object_or_empty(object_or_empty(case).get("rent_inputs"))
    if object_or_empty(inputs.get("holding_horizon")).get("profile")!=PROFILE:
        return {}
    inventory=object_or_empty(ref.get("holding_fiscal"))
    require(set(inventory)=={"Base","Downside"},"D267:independent_fiscal_inventory_missing")
    issues={}
    for name,record in inventory.items():
        observed=fiscal_input_digest(object_or_empty(inputs.get("florida_property_tax")),object_or_empty(inputs.get("holding_tax_cash")),name)
        issues[name]=[] if observed==record.get("inputs_sha256") else [dict(bot="M2",reason="fuente_fiscal_ausente_o_huella_distinta",
            path=("rent_inputs","florida_property_tax",name))]
        try:
            from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
            from audit_worksheet_critical_evidence_D219 import WORKBOOKS
            sheet=inspect_synthetic_input_sheet(documents[WORKBOOKS[name]]).cells
            months=[]
            for cell in ("C46","C47"):
                row=sheet[cell]
                require(row["literal"] is not None and row["literal"]!="" and row.get("formula") is None,
                        "D267:source_calendar_literal_unavailable")
                duration=Fraction(row["literal"])
                require(duration.denominator==1 and duration>=0 and duration%3==0,"D267:source_calendar_grid_invalid")
                months.append(int(duration))
            horizon=inputs["holding_horizon"]["scenarios"][name]["holding_months"]
            require(type(horizon) is int and 12<=horizon<=60 and horizon%12==0,"D267:source_horizon_unavailable")
            expected={OPERATING_PERIOD,FORWARD_PERIOD,"SYNTHETIC-D108-bank-annual","SYNTHETIC-D108-refinance-valuation-annual","holding_total"}
            expected.update(f"SYNTHETIC-D266-{name}-year-{i+1}" for i in range(1,horizon//12))
            expected.update(f"operation-quarter-{i+1}" for i in range(horizon//3))
            expected.update(f"preopening-quarter-{i+1}" for i in range(sum(months)//3))
            if set(record["windows"])!=expected:
                issues[name].append(dict(bot="M2",reason="inventario_fiscal_incompleto_o_ajeno_al_calendario",
                    path=("holding_fiscal",name,"windows")))
        except (KeyError,ValueError,TypeError):
            issues[name].append(dict(bot="M2",reason="calendario_fiscal_sin_respaldo_literal",path=(name,"C46","C47")))
    return issues


def render_horizon(views,screening,*,delivery_report=False):
    """One page with actual dated tax-dependent quarters, never an annual average."""
    from worksheet_sale_rate_grid_D84 import money
    from worksheet_irr_D122 import display_enclosure
    from miniuw_foundation.synthetic_onepager import _pdf,_pdf_string
    columns=[]
    for name,view in views.items():
        columns.extend([(name+" refi",view,object_or_empty(view.get("holding_horizon"))),
            (name+" sin refi",object_or_empty(view.get("horizon_without_refinance")),
             object_or_empty(view.get("horizon_without_refinance")))])
    cashes=[view.get("cash_per_usd_10") for _,view,_ in columns]
    unavailable=["N/A" if view.get("state")=="not_requested" else "PENDING" for _,view,_ in columns]
    def table(label,cells,bold=False):
        return (f"{label:<24} | "+" | ".join(f"{cell:>20}" for cell in cells),bold)
    def cash_value(index,key):
        cash=cashes[index]
        return unavailable[index] if cash is None or cash.get(key) is None else money(cash[key])
    lines=[("Datos sintéticos | Dictamen real PENDING | Retorno personal sin reparto PENDING",True),
        ("Equity agregado por USD 10 iniciales. A = aporte; C = cobro. Movimientos brutos separados.",False),
        ("Dictamen simulado: "+str(screening.get("simulation_result","PENDING")),False),
        table("Ruta",[name for name,_,_ in columns],True),
        table("Aporte inicial",["10,00" if cash is not None else unavailable[i] for i,cash in enumerate(cashes)]),
        table("Aportes adicionales",[unavailable[i] if c is None else money(rational(amount(c["total_contributions"])-10)) for i,c in enumerate(cashes)]),
        table("Cobros totales",[cash_value(i,"total_distributions") for i in range(4)],True),
        table("Resultado neto",[cash_value(i,"net_cash_profit") for i in range(4)]),
        table("Caja sin recuperar",[cash_value(i,"unrecovered_after_sale") for i in range(4)]),
        table("Múltiplo",[cash_value(i,"equity_multiple") for i in range(4)])]
    irrs=[]
    cocs=[]
    for i,(label,view,_) in enumerate(columns):
        irr=view.get("irr") if label.endswith("sin refi") else object_or_empty(screening.get("irr_by_scenario")).get(label.split()[0])
        irrs.append(unavailable[i] if cashes[i] is None else display_enclosure(object_or_empty(irr).get("annual_enclosure")))
        coc=object_or_empty(view.get("post_refinance_coc")).get("value")
        cocs.append("N/A" if label.endswith("sin refi") else "PENDING" if coc is None else money(rational(amount(coc)*100))+" %")
    lines.extend([table("TIR anual",irrs),table("CoC año 1 post-refi",cocs)])
    dates={}
    for i,(_,_,data) in enumerate(columns):
        for row in data.get("cash_by_period",[]):
            if row["stage"] in ("construction","construction_hold") and amount(row["contribution"])>0:
                dates.setdefault(row["date"],{})[i]=amount(row["contribution"])*amount(cashes[i]["scale_factor"])
    lines.append(("Aportes de compra/obra/tenencia previa por fecha; — = sin movimiento calculado.",True))
    for day,values in sorted(dates.items()):
        lines.append(table(day,[unavailable[i] if cashes[i] is None else money(rational(values[i])) if i in values else "—" for i in range(4)]))
    for name,view in views.items():
        holding=object_or_empty(view.get("holding_horizon"))
        if holding:
            lines.append((f"{name}: estabiliza {holding['stabilization_date']} | venta {holding['sale_date']} | {holding['months']} meses",True))
        cash=view.get("cash_per_usd_10")
        if cash is None:
            if view.get("blockers"):lines.append((name+" PENDING: "+str(view["blockers"][0]),False))
            continue
        scale=amount(cash["scale_factor"])
        closing=view["construction_refinance"]
        capital=view["post_refinance_coc"].get("equity_still_invested")
        cap_value="PENDING" if capital is None else money(rational(amount(capital)*scale))
        retained=(amount(view["valuation_and_sale"]["refinance_value"])-amount(closing["gross_proceeds"]))*scale
        lines.append((f"{name} refi {closing['date']}: A {money(rational(amount(closing['projected_cash_in_required'])*scale))} / C "
            f"{money(rational(amount(closing['net_equity_distribution'])*scale))}; capital restante {cap_value}; valor retenido (no caja) {money(rational(retained))}",False))
    years=max((len(data.get("annual_cash",[])) for _,_,data in columns),default=0)
    for index in range(years):
        timing=[]
        for name in ("Base","Downside"):
            records=next((d.get("annual_cash",[]) for label,_,d in columns if label.startswith(name) and len(d.get("annual_cash",[]))>index),[])
            timing.append("PENDING" if not records else ",".join(x["date"] for x in records[index]["payments"]))
        lines.append((f"Año {index+1} | Q1–Q4 Base {timing[0]} | Downside {timing[1]}",False))
        grouped=[]
        for i,(_,_,data) in enumerate(columns):
            annual=data.get("annual_cash",[])
            if len(annual)<=index:grouped.append([unavailable[i]]);continue
            groups={}
            for quarter,item in enumerate(annual[index]["payments"],1):
                groups.setdefault((amount(item["contribution"]),amount(item["receipt"])),[]).append(quarter)
            grouped.append(["Q"+",".join(map(str,periods))+":"+money(rational(a))+"/"+money(rational(c))
                            for (a,c),periods in groups.items()])
        for group in range(max(map(len,grouped))):
            lines.append(table("Trimestre(s): A/C",[items[group] if len(items)>group else "—" for items in grouped]))
    for name in ("Base","Downside"):
        values=[];when=None
        for label,view,data in columns:
            if not label.startswith(name):continue
            row=next((x for x in data.get("cash_by_period",[]) if x["stage"]=="sale"),None)
            if row is None:values.append("PENDING");continue
            when=row["date"];scale=amount(view["cash_per_usd_10"]["scale_factor"])
            values.append("A "+money(rational(amount(row["contribution"])*scale))+" / C "+money(rational(amount(row["distribution"])*scale)))
        lines.append((f"{name} venta {when or 'PENDING'}: refi {values[0]} | sin refi {values[1]}",True))
    lines.extend([("M2: impuesto previo incluido una vez en aportes; cuotas fiscales fechadas; venta después de cuota y cancelación única.",False),
        ("El cero necesita respaldo. Faltantes, diferencias o falso verde: PENDING y entrega bloqueada donde corresponda.",False),
        ("Importes redondeados sólo para mostrar. Sin despliegue ni decisiones reales.",False)])
    font=min(9.0,430/max(1,len(lines)))
    require(font>=7.0 and all(len(label)*font*0.6<=736 for label,_ in lines),"holding_fiscal_report_exceeds_one_readable_page")
    commands=[b"0.06 0.17 0.25 rg 24 524 744 64 re f"]
    for y,size,label in [(566,15,"MINI-UW | HORIZONTE, M2 Y AUDITOR"),(546,10,"Aportes y cobros por USD 10 | Base y Downside | Con y sin refi"),
                         (532,7,"Ensayo sintético D267 | Fuentes y padrones declarados; sin certificación legal o financiera")]:
        commands.append(f"1 1 1 rg BT /F2 {size} Tf 1 0 0 1 36 {y} Tm (".encode()+_pdf_string(label)+b") Tj ET")
    spacing=min(12,438/max(1,len(lines)-1))
    for i,(label,bold) in enumerate(lines):
        y=498-spacing*i
        require(y>=60,"holding_fiscal_report_height_exceeds_one_page")
        commands.append(f"0.06 0.17 0.25 rg BT /{'F2' if bold else 'F1'} {font} Tf 1 0 0 1 28 {y} Tm (".encode()+_pdf_string(label)+b") Tj ET")
    return _pdf(commands)
