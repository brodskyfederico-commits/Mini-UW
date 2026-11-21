"""Versioned source-first adapter: original worksheet -> integrated monthly cash.

Existing quarterly versions are not reinterpreted. The new profile requires
explicit schedule, bank amendment, per-space leases and insurance evidence.
"""
from copy import deepcopy
from datetime import date
from fractions import Fraction as Q
from hashlib import sha256
import json
from worksheet_frontiers_D275 import fraction as F,rational as R,digest
from worksheet_monthly_D275 import month,SCHEMA as CONSTRUCTION
from worksheet_monthly_integration_D276 import integrate,require,SCHEMA as INTEGRATION
from worksheet_monthly_integration_D276 import ledger
from worksheet_commercial_leaseup_D275 import schedule
from worksheet_rental_inputs_D140 import terms_for,rental_noi
from worksheet_utility_inputs_D142 import utility_expenses
from worksheet_operating_costs_D148 import declared_costs
from worksheet_growth_D154 import declared_growth,project_window
from worksheet_construction_budget_D144 import construction_budget
from worksheet_permanent_loan_D152 import declared_loan_terms
from worksheet_refinance_costs_D153 import declared_refinance_costs
from worksheet_replacement_reserve_D149 import declared_reserve
from worksheet_evidence_pdf_D156 import bind_bank_evidence
from worksheet_documented_finance_D147 import bind_development
from worksheet_debt_yield_D178 import bank_debt_yield_terms
from worksheet_market_evidence_D166 import review_assumptions
from worksheet_florida_tax_D203 import window_taxes
from worksheet_native_mapping_D139 import review_native_mapping
from worksheet_documented_finance_D147 import review_documents
from worksheet_revision_D128 import review_revision
from worksheet_variant_evidence_D268 import inputs_digest
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from plan_return_D107 import OPERATING_PERIOD,FORWARD_PERIOD
from plan_refinance_D108 import BANK_PERIOD,VALUE_PERIOD

SCHEMA='miniuw.synthetic-native-rental-inputs.v37'
PROFILE='miniuw.synthetic-native-monthly-integration.v1'
REFERENCE_SCHEMA='miniuw.synthetic-monthly-source-reference.v1'


def documents_for(raw):
 require(isinstance(raw,list),'Falta inventario de documentos mensuales, no se supone vacío')
 documents={}
 for row in raw:
  require(isinstance(row,dict) and set(row)=={'sha256','content_utf8'} and isinstance(row['content_utf8'],str),'Documento mensual sin bytes fuente')
  content=row['content_utf8'].encode();require(0<len(content)<=64000 and sha256(content).hexdigest()==row['sha256'] and row['sha256'] not in documents,'Documento mensual alterado, vacío o duplicado');documents[row['sha256']]=content
 return documents


def source_record(ref,documents):
 require(isinstance(ref,dict) and isinstance(ref.get('locator'),str) and ref['locator'].strip() and isinstance(ref.get('sha256'),str),'Falta cita / huella del respaldo mensual')
 raw=documents.get(ref['sha256']);require(isinstance(raw,bytes) and sha256(raw).hexdigest()==ref['sha256'],'Respaldo mensual ausente o alterado');return json.loads(raw)


def development(inputs,name,rows,groups,initial):
 record=inputs['development']['scenarios'][name];raw=inputs['development'];require(raw.get('closing_base')=='evaluated_purchase_price' and raw.get('vertical_scope')=='building_excluding_parking_and_site' and raw.get('currency')=='USD','Alcance de terreno / vertical no confirmado')
 price,closing,rate=(F(rows[k]['value']) for k in ('C32','C33','C35'));basis=rows['C34']['value'];require(price>=0 and 0<=closing<=1 and rate>=0 and F(record['evaluated_purchase_price'])==price and initial>=price*(1+closing),'Costo de compra, base o equity inicial incompatible')
 if basis=='$/GSF':
  gsf=record['plan_gsf'];require(gsf.get('state')=='declared' and gsf.get('source_ref') and rows['C36']['state']=='NOT_APPLICABLE','GSF declarado no está confirmado');quantity=F(gsf['value']);require(quantity>0,'GSF no positivo')
 else:
  require(rows['C36']['state']=='NOT_APPLICABLE' and basis in ('TOTAL','$/UNIT'),'Base de vertical incompatible');quantity=Q(1) if basis=='TOTAL' else Q(sum(g['units'] for g in groups.values()))
 require(record.get('purchase_source_ref') and record.get('vertical_source_ref') and record.get('program_source_ref'),'Faltan fuentes de terreno / obra / programa')
 return dict(purchase_date=record['purchase_date'],evaluated_purchase_price=R(price),land_closing_cost=R(price*closing),vertical_basis=basis,vertical_quantity=R(quantity),vertical_cost=R(rate*quantity),cell_sources={k:rows[k]['value_cell'] for k in ('C32','C33','C34','C35','C36')})


def scenario_contract(case,name,raw,review,local,source_documents):
 inputs=case['rent_inputs'];cfg=inputs['monthly_integration']['scenarios'][name];rows={r['value_cell'].split('!')[-1]:r for r in review['rows']}
 def number(cell):
  row=rows[cell];require(row['state']=='CONFIRMED_SYNTHETIC','Campo financiero sin confirmar: '+cell);return F(row['value'])
 values={k:rows[k]['value'] for k in ('C7','C8','C9','C10','C11','C12','C13','C14','C15')};refs={k:'sha256:'+review['workbook_sha256']+'#Inputs!'+k for k in values}
 require(not review['blockers'],'B04: hay celdas pendientes o incompatibles')
 market=review_assumptions(inputs,name,review);require(not market['blockers'],'B11: '+', '.join(market['blockers']))
 require(all(rows[k]['state']=='NOT_APPLICABLE' for k in ('C80','C81','C82')),'El perfil mensual no admite alternativas C80-C82 sin una conexión verificada')
 require('per_use_caps' not in cfg,'Caps por uso requieren asignaciones fiscales / reservas documentadas; no se reemplazan por cap combinado')
 require(isinstance(cfg.get('source_ref'),str) and cfg['source_ref'].startswith('SYNTHETIC-'),'Perfil mensual sin fuente sintética explícita')
 start=date.fromisoformat(inputs['development']['scenarios'][name]['purchase_date']);construction_months=number('C46');lease=number('C47');require(start.day==1 and construction_months.denominator==lease.denominator==1 and 1<=construction_months<=60 and 0<=lease<=36,'Duración mensual C46/C47 inválida')
 finish=month(start,int(construction_months));stable=month(finish,int(lease));holding=inputs['holding_horizon']['scenarios'][name];hold=holding['holding_months'];require(type(hold) is int and hold==60,'Este perfil requiere cinco años explícitos desde estabilización');sale=month(stable,hold)
 require(inputs['project_calendar']['scenarios'][name]['tco_date']==str(finish) and inputs['supplemental_scope'][name]['sale_date']['value']==str(sale),'Calendario declarado no coincide con C46/C47 y horizonte')
 initial=F(holding['initial_equity']['value']);require(initial>0 and holding['initial_equity'].get('source_ref'),'Aporte inicial sin fuente');requested=F(cfg['requested_principal'])
 scoped=inputs|{'requested_principal':R(requested)}
 terms=terms_for(scoped,name,values,inspect_synthetic_input_sheet(raw).cells,include_development=True,include_operating_costs=True,include_property_tax=True,include_exit_pricing=True,bank_vacancy=inputs['supplemental_scope'][name]['bank_vacancy_addition'])
 terms['utility_expenses'],terms['utility_evidence']=utility_expenses(inputs['utilities'],name,review,terms['groups'])
 terms['operating_costs']=declared_costs(inputs['operating_costs'],name,review,terms['groups'],terms['utility_evidence'])
 dev=development(inputs,name,rows,terms['groups'],initial);binding=bind_development(name,dev,local);require(not binding['blockers'],'B09: plano y costo de obra no conciliados')
 verified_area=F(binding['verified_area_gsf']);nrsf=sum(g['units']*F(g['rentable_sf_per_unit']) for g in terms['groups'].values());commercial_area=sum(F(g['rentable_sf']) for g in inputs['commercial']['uses'].values() if g['applies'])
 require(verified_area>=nrsf+commercial_area,'Área rentable residencial y comercial supera GSF verificado')
 declared=inputs['development']['scenarios'][name]['plan_gsf'];require(declared.get('state')=='declared' and F(declared['value'])==verified_area,'GSF compartido no coincide con el plano')
 up=inputs['project_calendar']['scenarios'][name];shortfall=F(up['lease_up_shortfall_per_month']);require(shortfall>=0 and up.get('lease_up_cash_ref'),'Falta déficit residencial de lease-up')
 calendar=dict(purchase_date=str(start),construction_start=str(start),construction_finish=str(finish),tco_date=str(finish),tco_ref=up['tco_ref'],stabilization_date=str(stable),refinance_date=str(stable),sale_date=str(sale),construction_months=int(construction_months),lease_up_months=int(lease),holding_months=hold,upfront_date=cfg['upfront_soft_date'],upfront_direct_hard_share=up['upfront_direct_hard_share'],lease_up_funding=R(shortfall*lease),construction_draw_ref=up['construction_draw_ref'],equity_dates=[str(month(start,i)) for i in range(int(construction_months+lease)+hold+1)])
 areas={k:dict(area=v['rentable_sf'],source_ref=v['source_ref']) for k,v in inputs['commercial']['uses'].items() if v['applies']}
 budget=construction_budget(inputs['construction_budget'],name,review,dev,dict(uses=areas,inventory_source_ref=inputs['commercial']['source_ref']),calendar=calendar,initial_equity=initial)
 commercial=deepcopy(cfg['commercial']);require(commercial['start']==str(start) and commercial['end']==str(month(sale,12)) and F(commercial['reconciled_area_sf'])==commercial_area,'Inventario comercial fuera de período / área')
 spaces=commercial['spaces'];require(isinstance(spaces,list),'Falta inventario por local')
 for use,cell in (('retail','C16'),('restaurant','C17'),('office','C18')):
  selected=[s for s in spaces if s.get('use')==use];expected=F(inputs['commercial']['uses'][use]['rentable_sf'])
  require(sum((F(s['area_sf']) for s in selected),Q())==expected,'Área por uso comercial no concilia: '+use)
  if selected:require(sum((F(s['area_sf'])*F(s['annual_rent_per_sf']) for s in selected),Q())==expected*number(cell),'La renta por local no concilia con '+cell)
 for space in spaces:
  if rows['C19']['state']=='CONFIRMED_SYNTHETIC':require(F(space['collection_loss_fraction'])==number('C19'),'Pérdidas por local no coinciden con C19')
  else:require(rows['C19']['state']=='NOT_APPLICABLE' and cfg['commercial_field_modes']['C19']=='per_space_only','C19 ausente sin reemplazo explícito por contratos')
  if rows['C20']['state']=='CONFIRMED_SYNTHETIC':require(space.get('owner_cost_mode')=='legacy_C20_collected_rent_fraction' and F(space['owner_cost_fraction'])==number('C20'),'C20 no se redefine como gasto fijo en silencio')
  else:require(rows['C20']['state']=='NOT_APPLICABLE' and cfg['commercial_field_modes']['C20']=='per_space_only','C20 ausente sin alcance de gastos por local')
  if rows['C21']['state']=='CONFIRMED_SYNTHETIC':require(space['lease_start']==str(month(finish,int(number('C21')))),'Fecha de contrato no coincide con el C21 uniforme')
  else:require(rows['C21']['state']=='NOT_APPLICABLE' and cfg['commercial_field_modes']['C21']=='per_space_only','C21 ausente sin calendario por local')
 # The raw bank addendum explicitly replaces the old quarter-only convention.
 bank=inputs['construction_financing']['scenarios'][name]
 financing=inputs['construction_financing'];rules=financing['rules']
 require(bank.get('currency')=='USD' and financing.get('policy')=='SYNTHETIC-D146-staged-construction-financing' and rules.get('eligible_cost')=='direct_hard_excluding_contingency' and rules.get('commitment')=='lesser_of_ltc_cap_and_fixed_limit' and rules.get('fee')=='fraction_of_commitment_paid_at_opening' and rules.get('equity')=='initial_then_same_day_top_up_for_verified_uses','Moneda o base contractual de obra sin conexión verificada; no se convierte LTC sobre TDC en LTC sobre hard')
 from worksheet_evidence_pdf_D156 import bind_document_terms
 candidate=dict(ltc=R(number('C51')),annual_interest=R(number('C52')),origination_fee_fraction=R(number('C53')),maximum_commitment=bank['maximum_commitment'],requested_invoice_fraction=bank['requested_invoice_fraction'],available_per_draw_checkpoint=bank['available_per_draw_checkpoint'],maturity_date=bank['maturity_date'])
 require(not bind_document_terms(local['bots']['B08']['construction_pdf_by_scenario'][name],candidate,'construction_pdf_and_worksheet_terms_disagree')['blockers'],'B08: C51-C53 o límites no coinciden con la cotización de obra')
 if cfg['builders_risk'].get('included_in_gc') is True:
  inclusion=source_record(cfg['builders_risk']['gc_inclusion_source'],source_documents)
  require(inclusion.get('gc_quote_sha256')==local['bots']['B08']['gc_pdf']['source_sha256'] and inclusion.get('scenario')==name and inclusion.get('deal_id')==inputs['deal_id'],'Inclusión de seguro no corresponde a la cotización GC vigente')
 amend=source_record(cfg['construction_amendment'],source_documents)
 require(amend.get('schema')=='miniuw.synthetic-monthly-bank-amendment.v1' and amend.get('bank_quote_sha256')==local['bots']['B08']['construction_pdf_by_scenario'][name]['source_sha256'] and amend.get('scenario')==name and amend.get('supersedes')==['interest_basis','draw_schedule'] and amend.get('day_count')==cfg['day_count'] and amend.get('interest_payment_every_months')==cfg['interest_payment_every_months'],'Enmienda de devengo mensual ausente o incompatible con el préstamo original')
 require(amend.get('schedule_sha256')==digest({k:cfg[k] for k in ('hard_schedule','soft_schedule','contingency_date','upfront_soft_date','allow_final_date_draws')}),'Calendario de desembolsos no coincide con la enmienda')
 n=int(construction_months+lease);periods=[dict(start=str(month(start,i)),end=str(month(start,i+1)),inventory_complete=True,source_ref=cfg['source_ref']+'/month/'+str(i),events=[]) for i in range(n)]
 def event(day,kind,amount,identifier,**extra):
  d=date.fromisoformat(day);index=(d.year-start.year)*12+d.month-start.month
  if d==stable:index=n-1
  require(0<=index<n and d.day==1,'Evento de obra fuera de la grilla mensual');periods[index]['events'].append(dict(id=identifier,date=day,kind=kind,amount=R(amount),source_ref=cfg['source_ref'],**extra))
 event(str(start),'use',F(dev['evaluated_purchase_price'])+F(dev['land_closing_cost']),'land-and-closing')
 def weights(key,total):
  items=cfg[key];require(isinstance(items,list) and items and sum((F(r['fraction']) for r in items),Q())==1,'Falta calendario completo: '+key)
  require(all(F(r['fraction'])>=0 and r.get('source_ref') for r in items) and len({r['date'] for r in items})==len(items),'Pesos, fuente o fechas duplicadas: '+key)
  return [(r['date'],F(r['fraction'])*total) for r in items]
 hard=F(budget['direct_hard_cost']);soft=F(budget['soft_budget']);ltc=number('C51');share=F(bank['requested_invoice_fraction']);require(0<=share<=ltc<=1,'Draw solicitado supera LTC de costo elegible directo')
 for i,(day,amount) in enumerate(weights('hard_schedule',hard)):
  event(day,'use',amount,'hard-invoice-'+str(i));event(day,'draw',amount*share,'hard-draw-'+str(i),invoice_id='SYNTHETIC-D276-INVOICE-'+str(i),eligible_invoice=R(amount),available_new_draw=bank['available_per_draw_checkpoint'])
 soft_weights=weights('soft_schedule',soft);require(sum((amount for day,amount in soft_weights if day==cfg['upfront_soft_date']),Q())==soft*number('C42'),'C42 no coincide con el desembolso inicial de soft')
 for i,(day,amount) in enumerate(soft_weights):event(day,'use',amount,'soft-'+str(i))
 event(cfg['contingency_date'],'use',F(budget['contingency_reserve']),'contingency');event(str(finish),'use',shortfall*lease,'residential-leaseup-prefund')
 commercial_result=schedule(commercial);require(commercial_result['state']=='CALCULATED',commercial_result.get('reason','Comercial PENDING'))
 for i,item in enumerate(commercial_result['capex_events']):
  if item['budget_location']=='M3':require(date.fromisoformat(item['date'])<=stable,'TI/LC M3 ocurre después de estabilización');event(item['date'],'use',F(item['amount']),'TI-LC-'+str(i))
 # Exact fiscal windows include every seller month and buyer forward reset.
 dates=[month(start,i) for i in range(n+hold+12)];windows={str(d):(d,1,d>=sale) for d in dates};taxes=window_taxes(inputs['florida_property_tax'],name,sale,windows)
 stress=inputs['stabilized_tax_stress']['scenarios'][name];factor=1+F(stress['relative_change']);require(factor>=0 and stress.get('source_ref'),'Estrés fiscal no declarado')
 monthly_taxes=[dict(start=str(d),amount=R(F(taxes[str(d)]['total'])*(factor if d>=stable else 1)),source_ref='sha256:'+taxes[str(d)]['source_sha256']) for d in dates]
 growth=declared_growth(inputs['growth'],name,review,calendar);residential=[];annual_cache={}
 for d in dates:
  if d<stable:
   # Explicit net residential losses are prefunded at TCO; no second receipt
   # or cost is manufactured before the stabilized operating model begins.
   require(cfg.get('residential_leaseup_mode')=='prefunded_net_residential_shortfall_at_TCO','Falta alcance de renta residencial previa a estabilización')
   vals={key:R(0) for key in ('operating_before_tax','bank_before_tax','refinance_before_tax','sale_before_tax')}
  else:
   year=((d.year-stable.year)*12+d.month-stable.month)//12
   if year not in annual_cache:
    anchor=month(stable,year*12);projection=project_window(growth,str(anchor));tax=R(sum((F(r['amount']) for r in monthly_taxes if str(anchor)<=r['start']<str(month(anchor,12))),Q()));trace=dict(source_sha256=digest([taxes[str(month(anchor,i))] for i in range(12)]),total=tax)
    cache={}
    for key,period in [('operating_before_tax',OPERATING_PERIOD),('bank_before_tax',BANK_PERIOD),('refinance_before_tax',VALUE_PERIOD),('sale_before_tax',FORWARD_PERIOD)]:
     assembly,_=rental_noi(terms,refs,values,period,commercial=None,window_start=str(anchor),growth=projection,seller_tax=trace);require(assembly.noi_run is not None,'NOI residencial sin base financiera completa');cache[key]=(F(assembly.noi_run.payload['noi'])+F(tax))/12
    annual_cache[year]=cache
   vals={k:R(v) for k,v in annual_cache[year].items()}
  residential.append(dict(start=str(d),source_ref='sha256:'+review['workbook_sha256']+'#Inputs/C7-C15/C25-C28/C57-C59/C75-C76',**vals))
 loan=declared_loan_terms(inputs['permanent_loan'],name,review,calendar,integrated_horizon=True);quote=local['bots']['B08']['bank_pdf_by_scenario'][name];binding_bank=bind_bank_evidence(quote,loan,requested);require(not binding_bank['blockers'],'Banco permanente no coincide con C69-C72 o el préstamo solicitado')
 debt_yield=bank_debt_yield_terms(inputs['bank_debt_yield'],name,quote)
 rr=declared_reserve(inputs['replacement_reserve'],name,review,terms['groups'],integrated_horizon=True);refi=declared_refinance_costs(inputs['refinance_costs'],name,review,terms['groups'])
 scope=inputs['supplemental_scope'][name]
 contract=dict(schema=INTEGRATION,scenario=name,currency='USD',source_ref=cfg['source_ref'],source_adapter_verified=True,source_inputs_sha256=inputs_digest(inputs),purchase_date=str(start),construction_finish=str(finish),stabilization_date=str(stable),sale_date=str(sale),budget=dict(land=R(F(dev['evaluated_purchase_price'])+F(dev['land_closing_cost'])),direct_hard=budget['direct_hard_cost'],contingency=budget['contingency_reserve'],soft=budget['soft_budget'],ti_lc=budget['ti_lc_cost'],residential_leaseup=R(shortfall*lease)),construction=dict(schema=CONSTRUCTION,currency='USD',scenario=name,start=str(start),stabilization=str(stable),maturity=bank['maturity_date'],annual_rate=R(number('C52')),ltc=R(ltc),eligible_total=R(hard),maximum_commitment=bank['maximum_commitment'],fee_fraction=R(number('C53')),initial_equity=R(initial),opening_free_cash=R(0),opening_principal=R(0),principal_payment_mode='interest_only_until_stabilization',other_costs_and_limits_complete=True,equity_policy='initial_then_top_up_for_sourced_uses',interest_payment_every_months=cfg['interest_payment_every_months'],pay_interest_at_stabilization=True,day_count=cfg['day_count'],allow_final_date_draws=cfg['allow_final_date_draws'],source_ref=cfg['construction_amendment']['sha256'],periods=periods),commercial=commercial,builders_risk=cfg['builders_risk'],monthly_taxes=monthly_taxes,residential_monthly=residential,preopening_scope='budget_excludes_tax_risk_and_commercial_net_cash',tax_payment_every_months=cfg['tax_payment_every_months'],operating_cash_every_months=cfg['operating_cash_every_months'],valuation_bases=cfg['valuation_bases'],replacement_reserve=dict(deposit_every_months=3,annual_amount=rr['deposit'],sale_release_fraction=rr['sale_release_fraction'],source_ref=rr['policy_ref']),refinance_cap=R(number('C66')),sale_cap=R(number('C67')),sale_cost_fraction=R(number('C68')),fixed_sale_cost=scope['fixed_sale_cost']['value'],permanent=dict(requested_principal=R(requested),annual_nominal_rate=loan['annual_nominal_rate'],maximum_ltv=loan['maximum_ltv'],minimum_dscr=loan['minimum_dscr'],amortization_years=loan['amortization_years'],maturity_payments=loan['maturity_payments'],payments_per_year=loan['payments_per_year'],source_ref=loan['policy_ref'],debt_yield=debt_yield),refinance=dict(cost_fraction=refi['cost_fraction'],reserve_amount=refi['reserve_deposit'],sale_release_fraction=refi['sale_release_fraction'],source_ref=refi['policy_ref']),without_refinance=dict(retention_terms=holding['without_refinance']['retention_terms'],maturity_date=bank['maturity_date'],fee_at_stabilization=holding['without_refinance']['fee_at_stabilization']['value'],source_ref=holding['without_refinance']['source_ref']))
 return contract,dict(calendar=calendar,development=dev,budget=budget,finance_binding=binding,permanent=loan,refinance=refi,reserve=rr,source_rows=rows,market_evidence=market)


def build_case(case,raw,*,workbook_raw=None,downside_workbook_raw=None,current_revision_raw=None,plan_raw=None,evidence_raw=None,criteria_raw=None,independent_reference_raw=None,delivery_report=False):
 from miniuw_worksheet_v1 import encoded,WORKBOOK_CRITICAL_EVIDENCE_PROFILE
 from worksheet_criteria_plug_D275 import apply,UNITS
 from miniuw_foundation.lorena_screening import BASES,RLV
 from worksheet_decision_page_D275 import report_view,render,ratio
 from worksheet_review_controls_D275 import empty_roles
 from worksheet_performance_policy_D184 import BEFORE_RESERVES,AFTER_RESERVES
 require(case.get('schema')==SCHEMA and case.get('investment_criteria','missing') is None,'El perfil mensual inicia criterios vacíos explícitos; no hereda umbrales')
 inputs=case['rent_inputs'];monthly=inputs['monthly_integration'];require(monthly.get('profile')==PROFILE and monthly.get('source_ref') and set(monthly.get('scenarios',{}))=={'Base','Downside'},'Falta contrato mensual versionado completo')
 require('requested_principal' not in inputs,'La solicitud permanente mensual debe declararse por escenario sin préstamo global ambiguo')
 workbooks={'Base':workbook_raw,'Downside':downside_workbook_raw};mapping=review_native_mapping(case['native_mapping'],workbooks,case['workbook_sha256'],calculation_fields={f'INPUT_C{i}' for i in range(7,16)},require_template_identity=True)
 revision=review_revision(case,current_revision_raw);local=review_documents(case,plan_raw,evidence_raw=evidence_raw,evidence_milestone='D162');global_blockers=list(local['blockers'])+list(revision['blockers'])
 source_values={'Inputs.xlsx':workbook_raw,'Downside_Inputs.xlsx':downside_workbook_raw,'Plan.pdf':plan_raw,'Evidence.pdf':evidence_raw,'Criterios_Lorena.xlsx':criteria_raw}
 try:
  require(isinstance(independent_reference_raw,bytes) and len(independent_reference_raw)<=4000000 and sha256(independent_reference_raw).hexdigest()==case.get('critical_evidence_reference_sha256'),'Inventario mensual independiente ausente o alterado')
  reference=json.loads(independent_reference_raw);require(reference.get('schema')==REFERENCE_SCHEMA and reference.get('inputs_sha256')==inputs_digest(inputs),'Inventario mensual no corresponde a las entradas vigentes')
  require(reference.get('sources')=={k:None if v is None else sha256(v).hexdigest() for k,v in source_values.items()},'Los respaldos fuente discrepan del inventario mensual')
  require(reference.get('deal_id')==inputs['deal_id'] and reference.get('local_revision')==case['local_sources']['revision'],'Inventario de otro deal o revisión')
 except (ValueError,KeyError,TypeError) as err:global_blockers.append(str(err))
 scenarios={};metrics={};metric_evidence={};contracts={};fields={}
 for name in ('Base','Downside'):
  try:
   require(not global_blockers,'B12: '+', '.join(global_blockers));cfg=monthly['scenarios'][name];documents=documents_for(cfg['documents']);contract,source=scenario_contract(case,name,workbooks[name],mapping['scenarios'][name],local,documents);result=integrate(contract,documents);require(result['state']=='CALCULATED',result.get('reason','Integración mensual PENDING'));contracts[name]=contract
   rows=source['source_rows'];v=result;fund=result['construction_financing'];loan=source['permanent'];initial_calls=F(fund['total_contributions']);free=F(fund['closing_free_cash']);tdc=F(result['tdc']);applied=initial_calls-free;requested=F(contract['permanent']['requested_principal']);refi=result['with_refinance'];no_refi=result['horizon_without_refinance']
   yoc=F(result['noi_uw'])/tdc;spread=None;cap=inputs['integrated_screening'][name]['reference_cap']
   if cap.get('source_ref') and cap.get('noi_basis') in (BEFORE_RESERVES,AFTER_RESERVES):
    comparable=F(result['annual_noi']) if cap['noi_basis']==BEFORE_RESERVES else F(result['noi_uw']);spread=R(10000*(comparable/tdc-F(cap['value'])))
   net=refi.get('refinance_net');refi_net=None if net is None else F(net)
   recover=None if refi_net is None else R(max(Q(),refi_net)/initial_calls)
   coc=refi.get('post_refi_coc');irr=None if refi.get('return_summary') is None else refi['return_summary']['irr_annual'].get('annual_enclosure');cash=refi.get('cash_per_usd_10')
   # Economic occupancy is distinct from physical vacancy; no physical result
   # is inferred from an undivided C14 value.
   gross=sum(F(rows[c]['value'])*g['units']*(F(g['rentable_sf_per_unit']) if rows['C7']['value']=='PER SF' else 1)*12 for c,g in zip(('C8','C9','C10','C11'),[inputs['groups'][key] for key in ('studio','1BR','2BR','3BR')]))
   mgmt=F(rows['C58']['value']);fixed=F(inputs['annual_expenses']['fixed_opex'])+F(rows['C57']['value'])*sum(g['units'] for g in inputs['groups'].values())+F(rows['C59']['value'])*inputs['operating_costs']['scenarios'][name]['insured_units']
   other=F(rows['C13']['value'])*inputs['other_income']['eligible_units']*12;stable=source['calendar']['stabilization_date'];end=str(month(date.fromisoformat(stable),12));tax=sum((F(r['amount']) for r in contract['monthly_taxes'] if stable<=r['start']<end),Q());commercial=sum((F(r['operating_noi']) for r in v['commercial_leaseup']['monthly'] if stable<=r['start']<end),Q());den=gross*(1-mgmt)
   occupancy=R((fixed+tax+F(contract['replacement_reserve']['annual_amount'])+F(v['capacity']['annual_service'])+mgmt*other-other-commercial)/den) if den>0 and cash is not None else None
   observations={'YoC':R(yoc),'spread':spread,'equity_recovered':recover,'equity_cash_in':None if refi_net is None else R(max(Q(),-refi_net)/initial_calls),'breakeven_occupancy':occupancy,'post_refi_CoC':coc,RLV:None,'equity_TDC':R(applied/tdc),'IRR':irr,'equity_multiple':None if cash is None else cash['equity_multiple']}
   metrics[name]={key:dict(value=value,basis=BASES[key],unit=UNITS[key],period_ref=str(source['calendar']['stabilization_date'])+'/'+end) for key,value in observations.items()}
   metric_evidence[name]=dict(cost_basis=dict(tdc=result['tdc'],applied_equity=R(applied),components=dict(loan_draw=fund['drawn'])),candidate_definitions={key:dict(value=val,noi_after_reserve=result['noi_uw']) for key,val in observations.items()})
   scenario=result|dict(project_calendar=source['calendar'],development_costs=source['development'],document_financial_binding=source['finance_binding'],construction_budget=source['budget'],construction_financing=fund|dict(construction_principal_payoff=fund['terminal_principal'],eligible_direct_hard=source['budget']['direct_hard_cost'],equity_funding_through_refinance=R(applied),ltc=contract['construction']['ltc']),permanent_loan=loan|dict(requested_principal=R(requested),annual_sizing_service=v['capacity']['annual_service']),construction_refinance=dict(net_equity_distribution=R(max(Q(),refi_net)) if refi_net is not None else None),post_refinance_coc=dict(annual_proof=dict(value=coc)),valuation_and_sale=dict(refinance_value=v['refinance_value'],gross_sale_price=v['gross_sale']),horizon_without_refinance=no_refi,blockers=refi['blockers'])
   scenarios[name]=scenario
  except (ValueError,KeyError,TypeError,AttributeError,ZeroDivisionError) as err:
   scenarios[name]=dict(state='PENDING',blockers=[str(err)],cash_per_usd_10=None,return_summary=None,horizon_without_refinance=dict(state='PENDING',cash_per_usd_10=None,return_summary=None,blockers=[str(err)]));metrics[name]={};metric_evidence[name]={}
 screening=apply({'computed_metrics':metrics},None,inputs['as_of_UTC'][:10]);screening.update(metric_evidence_by_scenario=metric_evidence,irr_by_scenario={s:dict(annual_enclosure=metrics[s].get('IRR',{}).get('value')) for s in ('Base','Downside')})
 # Each green is tied to a specific source/cell or generated month. A case-level
 # success is not substituted for critical-field coverage.
 for name in ('Base','Downside'):
  succeeded=scenarios[name]['state']=='CALCULATED';report=mapping['scenarios'][name]
  for row in report['rows']:
   status='VERIFIED_GREEN' if succeeded and row['state'] in ('CONFIRMED_SYNTHETIC','NOT_APPLICABLE') else 'PENDING'
   fields[name+'/'+row['field_id']]=dict(status=status,source_sha256=report['workbook_sha256'],locator=row['value_cell'],source_state=row['state'],value=row.get('value'),not_applicable=row['state']=='NOT_APPLICABLE',reason=None if status=='VERIFIED_GREEN' else scenarios[name]['blockers'])
  contract=contracts.get(name)
  if contract:
   for role,sha_value,locator in [('plan',sha256(plan_raw).hexdigest(),'A101/A601'),('construction_quote',sha256(evidence_raw).hexdigest(),'B08/'+name+'/C51-C53'),('permanent_quote',sha256(evidence_raw).hexdigest(),'B08/'+name+'/C69-C72'),('builders_risk',contract['builders_risk']['quote_source']['sha256'],contract['builders_risk']['quote_source']['locator'])]:
    fields[name+'/'+role]=dict(status='VERIFIED_GREEN',source_sha256=sha_value,locator=locator)
   for month_row in contract['monthly_taxes']:
    fields[name+'/property_tax/'+month_row['start']]=dict(status='VERIFIED_GREEN',source_sha256=month_row['source_ref'].removeprefix('sha256:'),locator='M2/month/'+month_row['start'],value=month_row['amount'])
   for month_row in contract['residential_monthly']:
    for role in ('operating_before_tax','bank_before_tax','refinance_before_tax','sale_before_tax'):
     fields[name+'/'+role+'/'+month_row['start']]=dict(status='VERIFIED_GREEN',source_sha256=report['workbook_sha256'],locator=month_row['source_ref'],value=month_row[role])
 counts={status:sum(v['status']==status for v in fields.values()) for status in ('VERIFIED_GREEN','PENDING','FALSE_GREEN')}
 critical=dict(status='PASSED' if not global_blockers and counts['PENDING']==0 else 'PENDING',counts=counts,affected_scenarios=[s for s in ('Base','Downside') if scenarios[s]['state']=='PENDING'],fields=fields,scope='Synthetic source consistency; no real-document accuracy or independent financial oracle claimed')
 result=dict(schema=SCHEMA,profile=WORKBOOK_CRITICAL_EVIDENCE_PROFILE,state='PENDING',decision='PENDING',simulation_result='PENDING',criteria_adopted=False,real_decisions_enabled=False,deployment_enabled=False,historical_return='PENDING',case_sha256=sha256(raw).hexdigest(),scenarios=scenarios,screening=screening,computed_metrics=metrics,monthly_contracts=contracts,native_mapping_review=mapping,revision_review=revision,local_review=local,critical_evidence_review=critical,pipeline=dict(case_sha256=sha256(raw).hexdigest(),stages=[dict(dot='D01',bots=['B01','B02','B03']),dict(dot='D02',bots=['B04']),dict(dot='D03',bots=['B05','B06','B07','B08','B09']),dict(dot='D04',bots=['B10','B11']),dict(dot='D05',bots=['B12','B13','B14'],motor='D276-monthly'),dict(dot='D06',bots=['B15']),dict(dot='D07',bots=['B16'])],version_tests=dict(run_per_deal=False)),return_summary=dict(scenarios={s:{'with_refinance':scenarios[s].get('return_summary'),'without_refinance':scenarios[s]['horizon_without_refinance'].get('return_summary')} for s in ('Base','Downside')}))
 view=report_view(result,case,{},empty_roles());pdf,fields=render(view);result.update(pdf_sha256=sha256(pdf).hexdigest(),page_count=1,rendered_fields_sha256=digest(fields));return result,pdf
