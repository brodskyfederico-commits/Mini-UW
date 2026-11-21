"""Integrated synthetic monthly M2/M3/M5/M6/M7 contract.

Every forecast month and every zero is explicit in the source adapter. The
contract does not accept an old cash result as a substitute for source inputs.
No deployment, real criterion or investor allocation is authorized here.
"""
from copy import deepcopy
from datetime import date
from fractions import Fraction as Q
from collections import defaultdict
from worksheet_frontiers_D275 import fraction as F,rational as R,digest
from worksheet_monthly_D275 import construction,monthly_irr,month,day_fraction
from worksheet_commercial_leaseup_D275 import schedule
from worksheet_builders_risk_D275 import line

SCHEMA='miniuw.synthetic-integrated-monthly-cash.v1'
BUDGET_ROLES={'land','direct_hard','contingency','soft','ti_lc','residential_leaseup'}


def require(value,reason):
 if not value:raise ValueError(reason)


def ledger(events,initial,start,sale,source_ref):
 """Gross investor cash and exact declared monthly grid; no date rounding."""
 initial=F(initial);require(initial>0,'Aporte inicial ausente o no positivo')
 require(isinstance(events,list) and isinstance(source_ref,str) and source_ref,'Falta inventario fechado de caja')
 copied=deepcopy(events);ids=[e['event_id'] for e in copied];require(len(ids)==len(set(ids)),'Movimientos de equity duplicados')
 scale=10/initial;dates=[str(month(start,i)) for i in range((sale.year-start.year)*12+sale.month-start.month+1)]
 by_date={d:dict(contribution=Q(),distribution=Q()) for d in dates};basis=[]
 for event in copied:
  amount=F(event['amount']);when=date.fromisoformat(event['date']);require(start<=when<=sale and amount>=0 and event.get('source_ref') and event['kind'] in ('contribution','distribution'),'Evento fuera del horizonte, sin fuente o sin importe')
  row=by_date.setdefault(event['date'],dict(contribution=Q(),distribution=Q()));row[event['kind']]+=amount
  if event.get('category')=='initial_capital':require(when==start and event['kind']=='contribution','Base inicial inválida');basis.append(event['event_id'])
  event.update(amount=R(amount*scale),currency='USD')
 require(sum((F(e['amount']) for e in copied if e['event_id'] in basis),Q())==10,'El aporte inicial no concilia con USD 10')
 # Complete monthly source inventories prove that an empty scheduled date has
 # no cash movement. This is not an absent observation or a guessed amount.
 for day in dates:
  if not any(e['date']==day for e in copied):copied.append(dict(event_id='monthly-observed-no-cash-'+day,date=day,kind='distribution',category='observed_no_cash_event',amount=R(0),currency='USD',source_ref=source_ref))
 copied.sort(key=lambda e:(e['date'],e['event_id']));calls=receipts=peak=Q();payback=None;reversed_payback=False;dated=[]
 for day,row in sorted(by_date.items()):
  calls+=row['contribution']*scale;receipts+=row['distribution']*scale;net=calls-receipts;peak=max(peak,net)
  if payback is None and receipts>=calls:payback=day
  elif payback is not None and receipts<calls:reversed_payback=True
  dated.append(dict(date=day,contributions=R(row['contribution']*scale),receipts=R(row['distribution']*scale),unrecovered=R(max(Q(),net))))
 require(calls>0,'Aportes totales sin base verificable')
 on_grid=all(d in dates for d in by_date)
 irr=monthly_irr(dates,[R(by_date[d]['distribution']-by_date[d]['contribution']) for d in dates],source_ref) if on_grid else dict(state='PENDING',annual_enclosure=None,reason='Hay equity fuera del primer día mensual; no se redondean fechas para seleccionar TIR')
 cash=dict(reference_amount=10,basis_amount=R(initial),scale_factor=R(scale),basis_event_ids=basis,events=copied,periods_per_year=12,total_contributions=R(calls),total_distributions=R(receipts),net_cash_profit=R(receipts-calls),unrecovered_after_sale=R(max(Q(),calls-receipts)),equity_multiple=R(receipts/calls))
 summary=dict(irr_annual=irr,payback_date=payback,payback_reason=None if payback else 'No recuperado en el horizonte',peak_equity=R(peak),project_peak_equity=R(peak/scale),reversed_recovery=reversed_payback,dated_cash=dated,blockers=[])
 return cash,summary


def integrate(spec,documents):
 """Calculate both strategies from one source-derived monthly contract."""
 pending=dict(schema=SCHEMA,state='PENDING',cash_per_usd_10=None,horizon_without_refinance=dict(state='PENDING',cash_per_usd_10=None),decision='PENDING',deployment_enabled=False)
 try:
  require(isinstance(spec,dict) and spec.get('schema')==SCHEMA and spec.get('currency')=='USD' and spec.get('scenario') in ('Base','Downside') and spec.get('source_ref'),'Falta contrato integrado con fuente, moneda o escenario')
  require(spec.get('source_adapter_verified') is True and isinstance(spec.get('source_inputs_sha256'),str) and len(spec['source_inputs_sha256'])==64,'Falta enlace con la planilla y sus fuentes')
  start,stable,sale=(date.fromisoformat(spec[k]) for k in ('purchase_date','stabilization_date','sale_date'))
  require(start.day==stable.day==sale.day==1 and start<stable<sale,'Calendario mensual inválido')
  pre=(stable.year-start.year)*12+stable.month-start.month;hold=(sale.year-stable.year)*12+sale.month-stable.month
  require(pre<=120 and hold%12==0 and 12<=hold<=120 and pre+hold<=240,'Horizonte mensual fuera del contrato acotado')
  cfg=deepcopy(spec['construction']);require(cfg['start']==str(start) and cfg['stabilization']==str(stable),'Obra y calendario no coinciden')
  commercial=schedule(spec['commercial']);require(commercial['state']=='CALCULATED',commercial.get('reason','Comercial PENDING'))
  require(spec['commercial']['start']==str(start) and spec['commercial']['end']==str(month(sale,12)),'Falta ventana comercial desde compra hasta forward de salida')
  commercial_by_month={r['start']:r for r in commercial['monthly']}
  risk=line(spec['builders_risk'],documents);require(risk['state']=='CALCULATED',risk.get('reason','Seguro de obra PENDING'))
  require(date.fromisoformat(risk['term_start'])<=start and date.fromisoformat(risk['term_end'])>=date.fromisoformat(spec['construction_finish']),'Seguro no cubre el plazo de construcción declarado')
  require(start<=date.fromisoformat(risk['payment_date'])<=stable,'Prima fuera del presupuesto de desarrollo')
  budget=spec['budget'];require(isinstance(budget,dict) and set(budget)==BUDGET_ROLES and all(F(v)>=0 for v in budget.values()),'Falta una partida de presupuesto; no se asume cero')
  require(F(commercial['m3_ti_lc'])==F(budget['ti_lc']),'TI/LC por local no concilia con el presupuesto C41')
  taxes=spec['monthly_taxes'];residential=spec['residential_monthly'];require(isinstance(taxes,list) and isinstance(residential,list),'Falta inventario mensual M2')
  forecast_dates=[str(month(start,i)) for i in range(pre+hold+12)]
  require([r.get('start') for r in taxes]==forecast_dates and [r.get('start') for r in residential]==forecast_dates,'M2 omite o duplica un mes; no se rellena con cero')
  for r in taxes:require(F(r.get('amount'))>=0 and r.get('source_ref'),'Impuesto mensual sin dato o fuente')
  for r in residential:
   require(r.get('source_ref') and all(F(r.get(k)) is not None for k in ('operating_before_tax','bank_before_tax','refinance_before_tax','sale_before_tax')),'Renta / NOI mensual sin dato o fuente')
  tax_by_date={r['start']:F(r['amount']) for r in taxes};res_by_date={r['start']:r for r in residential}
  def pre_event(when,kind,amount,label,**kw):
   day=date.fromisoformat(when);i=(day.year-start.year)*12+day.month-start.month
   if day==stable:i=pre-1
   require(0<=i<pre,'Uso preoperativo fuera del calendario')
   cfg['periods'][i]['events'].append(dict(id=label,kind=kind,date=when,amount=R(amount),source_ref=spec['source_ref'],**kw))
  # Budget-origin events only; taxes, premium and commercial cash are injected
  # exactly once below. Their declarations must explicitly exclude each other.
  require(spec.get('preopening_scope')=='budget_excludes_tax_risk_and_commercial_net_cash','No está probada la exclusión de duplicados preoperativos')
  base_uses=sum((F(e['amount']) for p in cfg['periods'] for e in p['events'] if e['kind']=='use'),Q())
  require(base_uses==sum((F(v) for v in budget.values()),Q()),'Los pagos de obra no concilian con M3')
  pre_event(risk['payment_date'],'use',F(risk['incremental_budget_cost']),'builders-risk-premium')
  tax_cadence=spec.get('tax_payment_every_months');require(type(tax_cadence) is int and tax_cadence in (1,3),'Cadencia fiscal sin confirmar')
  accrued=Q()
  for i in range(pre):
   when=month(start,i);accrued+=tax_by_date[str(when)]
   if (i+1)%tax_cadence==0 or i+1==pre:pre_event(str(month(start,i+1)),'use',accrued,'preopening-tax-'+str(i+1));accrued=Q()
   c=commercial_by_month[str(when)];net=F(c['operating_noi'])
   pre_event(str(month(start,i+1)),'receipt' if net>=0 else 'use',abs(net),'preopening-commercial-'+str(i+1))
  for event in commercial['capex_events']:
   when=date.fromisoformat(event['date'])
   if event['budget_location']=='operating_capex' and when<stable:pre_event(event['date'],'use',F(event['amount']),'preopening-capex-'+event['space_id']+'-'+event['kind']+'-'+event['date'])
  funding=construction(cfg);require(funding['state']=='CALCULATED',funding.get('reason','Financiación de obra PENDING'))
  principal=F(funding['terminal_principal']);free=F(funding['closing_free_cash']);initial=F(funding['initial_equity']);tdc=F(funding['uses_total_including_fee'])+F(funding['interest_total'])
  observed_other_sources=sum((F(e['amount']) for p in cfg['periods'] for e in p['events'] if e['kind']=='receipt'),Q())
  require(F(funding['total_contributions'])+F(funding['drawn'])+observed_other_sources==tdc+free,'No concilian TDC, deuda, equity, ingresos y caja')
  bases=spec['valuation_bases'];require(set(bases)=={'refinance','sale'} and all(v in ('before_reserves','after_reserves') for v in bases.values()),'Base de NOI del cap no confirmada')
  reserve=spec['replacement_reserve'];annual_reserve=F(reserve.get('annual_amount'));release=F(reserve.get('sale_release_fraction'));reserve_cadence=reserve.get('deposit_every_months');require(type(reserve_cadence) is int and reserve_cadence in (1,3),'Cadencia de reserva C60 no confirmada');require(annual_reserve>=0 and 0<=release<=1 and reserve.get('source_ref'),'Reserva C60 sin fuente o destino')
  def window(day,role):
   values=[]
   for i in range(12):
    d=str(month(day,i));r=res_by_date[d];c=commercial_by_month[d]
    reskey={'operating':'operating_before_tax','bank':'bank_before_tax','refinance':'refinance_before_tax','sale':'sale_before_tax'}[role]
    com=F(c['operating_noi']) if role=='operating' else F(c['noi_by_basis'][{'bank':'bank','refinance':'refinance_valuation','sale':'sale_valuation'}[role]])
    values.append(F(r[reskey])+com-tax_by_date[d])
   return sum(values,Q())
  bank_noi=window(stable,'bank');refi_noi=window(stable,'refinance')-(annual_reserve if bases['refinance']=='after_reserves' else 0)
  exit_noi=window(sale,'sale')-(annual_reserve if bases['sale']=='after_reserves' else 0)
  cap_refi,cap_exit=(F(spec[k]) for k in ('refinance_cap','sale_cap'));require(0<cap_refi<=1 and 0<cap_exit<=1,'Cap no confirmado o fuera de dominio')
  refi_value=refi_noi/cap_refi;gross_sale=exit_noi/cap_exit
  require(gross_sale>=0,'Valor de salida negativo: no se recorta a cero ni se supone precio de venta')
  loan=spec['permanent'];requested,rate,ltv,dscr=(F(loan[k]) for k in ('requested_principal','annual_nominal_rate','maximum_ltv','minimum_dscr'))
  years,maturity,frequency=(loan[k] for k in ('amortization_years','maturity_payments','payments_per_year'))
  require(requested>0 and 0<=rate<=1 and 0<=ltv<=1 and dscr>0 and type(years) is int and years>0 and frequency==4 and type(maturity) is int and 2<=maturity<=years*frequency<=480 and loan.get('source_ref'),'Términos permanentes ausentes o fuera del perfil trimestral explícito')
  r=rate/frequency;n=years*frequency;constant=Q(1,n) if r==0 else r/(1-(1+r)**-n);payment=requested*constant;annual_service=payment*frequency
  limits={'LTV':max(Q(),refi_value*ltv),'DSCR':max(Q(),bank_noi/(constant*frequency*dscr))}
  dy=loan['debt_yield'];require(dy.get('applicability') in ('applicable','not_applicable') and dy.get('source_ref'),'Debt yield sin alcance o fuente')
  if dy['applicability']=='applicable':require(F(dy.get('minimum'))>0,'Debt yield aplicable sin mínimo positivo');limits['DEBT_YIELD']=max(Q(),bank_noi/F(dy['minimum']))
  else:require(dy.get('minimum') is None,'Debt yield N/A no puede contener un mínimo')
  capacity=min(limits.values());within=requested<=capacity
  refi=spec['refinance'];fee,reserve_cash,perm_release=(F(refi[k]) for k in ('cost_fraction','reserve_amount','sale_release_fraction'));require(0<=fee<=1 and reserve_cash>=0 and 0<=perm_release<=1 and refi.get('source_ref'),'Cierre refi sin términos')
  sale_cost=F(spec['sale_cost_fraction'])*gross_sale+F(spec['fixed_sale_cost']);require(0<=F(spec['sale_cost_fraction'])<=1 and F(spec['fixed_sale_cost'])>=0,'Costos de venta sin alcance')
  operative_cadence=spec.get('operating_cash_every_months');require(operative_cadence in (1,3) and type(operative_cadence) is int,'Puente de caja operativa no declarado')
  require(hold%operative_cadence==0,'Caja operativa no cierra en la venta')
  initial_events=[e|dict(amount=e['amount']) for e in funding['equity_events']]
  def route(with_refi):
   blockers=[];events=deepcopy(initial_events);refinet=None;route_free=free
   def event(day,kind,amount,category,event_id):events.append(dict(event_id=event_id,date=str(day),kind=kind,amount=R(amount),category=category,source_ref=spec['source_ref']))
   if with_refi and not within:return dict(state='PENDING',blockers=['Préstamo solicitado supera la menor capacidad contractual'],cash_per_usd_10=None,return_summary=None)
   if with_refi:
    refinet=requested+route_free-principal-requested*fee-reserve_cash;event(stable,'distribution' if refinet>=0 else 'contribution',abs(refinet),'net_refinance_distribution' if refinet>=0 else 'refinance_cash_in','refinance-closing');balance=requested
   else:
    carry=spec['without_refinance'];require(carry.get('source_ref') and carry.get('retention_terms')=='same_committed_facility_C52_until_documented_maturity','Sin refi requiere retención contractual explícita')
    require(date.fromisoformat(carry['maturity_date'])>=sale,'Deuda de obra vence antes de la venta sin refi; no se supone extensión')
    hold_fee=F(carry['fee_at_stabilization']);require(hold_fee>=0,'Fee de retención sin importe');gap=hold_fee-route_free
    if gap>0:event(stable,'contribution',gap,'additional_capital','no-refi-roll-fee')
    route_free=max(Q(),route_free-hold_fee);balance=principal
   operating=[];net_accrued=Q();debt_accrued=Q();c60_balance=Q();permanent_schedule=[];first_year_cash=Q();pre_reserve_noi=Q()
   for i in range(hold):
    day=month(stable,i);end=month(stable,i+1);key=str(day);c=commercial_by_month[key];tax=tax_by_date[key]
    income=F(res_by_date[key]['operating_before_tax'])+F(c['operating_noi'])-tax
    pre_reserve_noi+=income;reserved=annual_reserve*reserve_cadence/12 if (i+1)%reserve_cadence==0 else Q();c60_balance+=reserved
    operating_capex=F(c['operating_capex']);debt_payment=interest=principal_payment=balloon=Q()
    if with_refi and (i+1)%3==0 and balance>0:
     index=(i+1)//3;opening=balance;interest=opening*r;principal_payment=min(balance,payment-interest);require(principal_payment>=0,'Amortización negativa no autorizada');balance-=principal_payment
     if index==maturity:balloon=balance;balance=Q()
     debt_payment=interest+principal_payment+balloon
     permanent_schedule.append(dict(date=str(end),opening_balance=R(opening),interest_due=R(interest),principal_due=R(principal_payment),balloon_due=R(balloon),closing_balance=R(balance),scheduled_plus_balloon_due=R(debt_payment)))
    elif not with_refi:
     debt_accrued+=principal*F(cfg['annual_rate'])*day_fraction(day,end,cfg['day_count'])
     if (i+1)%cfg['interest_payment_every_months']==0 or i+1==hold:debt_payment=debt_accrued;interest=debt_accrued;debt_accrued=Q()
    net_accrued+=income-reserved-operating_capex-debt_payment
    if i<12:first_year_cash+=income-reserved-operating_capex-debt_payment
    paid=Q()
    if (i+1)%operative_cadence==0 or i+1==hold:
     paid=net_accrued;event(end,'distribution' if paid>=0 else 'contribution',abs(paid),'operating_distribution' if paid>=0 else 'operating_funding','operation-'+str(i+1));net_accrued=Q()
    operating.append(dict(start=str(day),end=str(end),residential_before_tax=res_by_date[key]['operating_before_tax'],commercial_noi=c['operating_noi'],property_tax=R(tax),operating_noi=R(income),reserve_deposit=R(reserved),operating_capex=R(operating_capex),debt_service=R(debt_payment),cash_settled=R(paid),unsettled_operating_cash=R(net_accrued)))
   net_sale=gross_sale-sale_cost-balance+c60_balance*release+(reserve_cash*perm_release if with_refi else route_free)
   event(sale,'distribution' if net_sale>=0 else 'contribution',abs(net_sale),'net_sale_distribution' if net_sale>=0 else 'sale_funding','sale-closing')
   cash,summary=ledger(events,initial,start,sale,spec['source_ref']);remaining=F(funding['total_contributions'])-(refinet if with_refi else Q())
   coc=R(first_year_cash/remaining) if remaining>0 else None
   return dict(state='CALCULATED',blockers=blockers,cash_per_usd_10=cash,return_summary=summary,operating_months=operating,permanent_schedule=permanent_schedule,terminal_debt_paid=R(balance),gross_sale=R(gross_sale),net_sale=R(net_sale),first_year_cash=R(first_year_cash),post_refi_coc=coc,refinance_net=None if refinet is None else R(refinet),replacement_reserve_released=R(c60_balance*release),c60_restricted_transferred=R(c60_balance*(1-release)),permanent_reserve_released=R(reserve_cash*perm_release if with_refi else 0),operating_noi_total=R(pre_reserve_noi))
  routes=[]
  for requested_route in (True,False):
   try:routes.append(route(requested_route))
   except (ValueError,KeyError,TypeError,ZeroDivisionError) as err:routes.append(dict(state='PENDING',blockers=[str(err)],cash_per_usd_10=None,return_summary=None))
  with_refi,without=routes
  return dict(schema=SCHEMA,state='CALCULATED',blockers=[],scenario=spec['scenario'],cash_per_usd_10=with_refi['cash_per_usd_10'],return_summary=with_refi.get('return_summary'),with_refinance=with_refi,horizon_without_refinance=without,construction_financing=funding,construction_budget=deepcopy(budget),tdc=R(tdc),commercial_leaseup=commercial,builders_risk=risk,bank_noi=R(bank_noi),refinance_noi=R(refi_noi),exit_noi=R(exit_noi),annual_noi=R(window(stable,'operating')),noi_uw=R(window(stable,'operating')-annual_reserve),capacity=dict(maximum_principal_capacity=R(capacity),limits={k:R(v) for k,v in limits.items()},active_limits=[k for k,v in limits.items() if v==capacity],requested_principal=R(requested),within_capacity=within,bank_noi=R(bank_noi),annual_service=R(annual_service)),refinance_value=R(refi_value),gross_sale=R(gross_sale),permanent_payment=R(payment),source_inputs_sha256=spec['source_inputs_sha256'],integration_inputs_sha256=digest(spec),monthly_taxes=deepcopy(taxes),operating_cash_every_months=operative_cadence,decision='PENDING',deployment_enabled=False,criteria_adopted=False)
 except (ValueError,KeyError,TypeError,AttributeError,ZeroDivisionError) as error:return pending|dict(blockers=[str(error)],reason=str(error))
