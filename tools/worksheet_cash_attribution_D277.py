"""Dated gross cash attribution; a later funding call is not closing cash-in.

No amounts, dates, source events, IRR or multiple are modified. A complete ledger
and reconciliation to its declared totals/closing cash are required before zeros
can be computed over an empty category inventory.
"""
from fractions import Fraction as Q
from collections import defaultdict
from copy import deepcopy
from datetime import date
from worksheet_frontiers_D275 import fraction as F,rational as R,digest

CLOSING_IN={'refinance_cash_in','refinance_closing_contribution'}
CLOSING_OUT={'net_refinance_distribution','refinance_closing_distribution'}


def require(condition,reason):
 if not condition:raise ValueError(reason)


def route_attribution(cash,refinance_date,*,with_refinance,expected_refinance_net=None):
 try:
  date.fromisoformat(refinance_date);require(isinstance(cash,dict) and isinstance(cash.get('events'),list),'Falta ledger completo; no se supone caja cero')
  events=cash['events'];require(events and F(cash.get('reference_amount'))==10 and F(cash.get('basis_amount'))>0,'Falta base inicial verificada por USD10')
  ids=[e.get('event_id') for e in events];require(all(ids) and len(ids)==len(set(ids)),'Eventos ausentes o duplicados')
  calls=receipts=Q();groups=defaultdict(Q);records=[];closing_in=closing_out=Q();initial=Q()
  for e in events:
   amount=F(e.get('amount'));when=e['date'];date.fromisoformat(when);kind=e.get('kind');category=e.get('category');require(amount>=0 and kind in ('contribution','distribution') and e.get('source_ref') and isinstance(category,str),'Evento sin importe, tipo, concepto o fuente')
   if kind=='contribution':calls+=amount
   else:receipts+=amount
   if category=='initial_capital':require(kind=='contribution' and e['event_id'] in cash['basis_event_ids'],'Aporte inicial no conciliado');initial+=amount
   closing=category in CLOSING_IN|CLOSING_OUT
   if closing:
    require(with_refinance and when==refinance_date,'Flujo de refi fuera de su fecha o de su estrategia')
    if category in CLOSING_IN:require(kind=='contribution','Cash-in con signo incorrecto');closing_in+=amount
    else:require(kind=='distribution','Cobro de refi con signo incorrecto');closing_out+=amount
   phase='BEFORE_REFI' if when<refinance_date else 'REFI_DATE' if when==refinance_date else 'AFTER_REFI'
   if kind=='contribution':
    purpose='REFINANCE_CLOSING' if closing else 'OPERATING' if category=='operating_funding' else 'SALE' if category=='sale_funding' else 'PROJECT' if category in ('initial_capital','additional_capital') else None
    require(purpose is not None,'Aporte con concepto no clasificado: '+category)
    groups[phase+'/'+purpose]+=amount
    if amount:records.append(dict(date=when,amount=e['amount'],phase=phase,purpose=purpose,event_id=e['event_id'],source_ref=e['source_ref']))
  require(initial==10 and calls==F(cash.get('total_contributions')) and receipts==F(cash.get('total_distributions')),'El ledger no concilia con la base o totales brutos; no se rellenan faltantes')
  if with_refinance:require(expected_refinance_net is not None and closing_out-closing_in==F(expected_refinance_net),'Falta cierre neto o los cobros y cash-in no concilian')
  else:require(closing_in==closing_out==0,'La alternativa sin refi contiene un cierre de refi')
  project_through_refi=sum((v for k,v in groups.items() if k in ('BEFORE_REFI/PROJECT','REFI_DATE/PROJECT')),Q())
  net=closing_out-closing_in
  post=sum((v for k,v in groups.items() if k.startswith('AFTER_REFI/')),Q());post_records=[r for r in records if r['phase']=='AFTER_REFI']
  all_on_date=sum((F(e['amount'])*(1 if e['kind']=='distribution' else -1) for e in events if e['date']==refinance_date),Q())
  return dict(state='ATTRIBUTED',reference_amount=10,source_cash_sha256=digest(cash),refinance_date=refinance_date,contributions_by_phase={k:R(v) for k,v in groups.items()},dated_contributions=records,project_contributions_through_refi=R(project_through_refi),refinance_gross_receipts=R(closing_out) if with_refinance else None,refinance_cash_in=R(closing_in) if with_refinance else None,refinance_net_receipt=R(net) if with_refinance else None,same_day_all_cash_net=R(all_on_date),equity_recovered_net=R(max(Q(),net)/project_through_refi) if with_refinance and project_through_refi>0 else None,cash_in_over_equity=R(closing_in/project_through_refi) if with_refinance and project_through_refi>0 else None,post_refinance_contributions=R(post),post_refinance_count=len(post_records),post_refinance_first=None if not post_records else post_records[0]['date'],post_refinance_last=None if not post_records else post_records[-1]['date'],gross_totals_unchanged=True,definition='Gross receipt means the investor cash receipt after loan payoff/closing costs, not the gross mortgage advance. Closing cash-in contains only refinance-purpose contributions. Common project settlement and later operating funding remain separately identified; total cash on the closing date is also shown.',decision='PENDING')
 except (ValueError,KeyError,TypeError,ZeroDivisionError) as err:return dict(state='PENDING',reason=str(err),equity_recovered_net=None,cash_in_over_equity=None)


def compare_prefix(with_cash,without_cash,refinance_date):
 def canonical(cash,include_closing_date):
  require(isinstance(cash,dict) and isinstance(cash.get('events'),list),'Falta una ruta para cotejar su prefijo')
  values=defaultdict(Q)
  for e in cash['events']:
   amount=F(e.get('amount'));day=e['date']
   if day<refinance_date or include_closing_date and day==refinance_date and e['category'] not in CLOSING_IN|CLOSING_OUT:values[(day,e['kind'],e['category'])]+=amount
  return {key:value for key,value in values.items() if value!=0}
 try:
  before=canonical(with_cash,False)==canonical(without_cash,False);common=canonical(with_cash,True)==canonical(without_cash,True);require(before and common,'Las rutas difieren antes de la refi o en los usos comunes del cierre')
  return dict(state='PASSED',before_refinance_identical=before,common_project_settlement_on_refi_date_identical=common,refinance_date=refinance_date,scope='Refinance-purpose closing legs are explicitly excluded from the common prefix; they are the legitimate strategy divergence.')
 except (ValueError,KeyError,TypeError) as err:return dict(state='PENDING',reason=str(err))


def reconcile_case(result):
 out={}
 for name,v in result['scenarios'].items():
  when=v.get('project_calendar',{}).get('stabilization_date')
  if when is None:
   out[name]=dict(with_refinance=dict(state='PENDING',reason='Falta calendario / cálculo'),without_refinance=dict(state='PENDING',reason='Falta calendario / cálculo'),prefix=dict(state='PENDING',reason='Falta una ruta'),operating_funding_details=[],additional_post_refinance_vs_no_refinance=None);continue
  a=v.get('with_refinance',v);b=v['horizon_without_refinance'];cash=a.get('cash_per_usd_10');scale=None if cash is None else F(cash['scale_factor']);net=a.get('refinance_net')
  expected=None if net is None or scale is None else R(F(net)*scale)
  first=route_attribution(cash,when,with_refinance=True,expected_refinance_net=expected);second=route_attribution(b.get('cash_per_usd_10'),when,with_refinance=False);prefix=compare_prefix(cash,b.get('cash_per_usd_10'),when)
  operating=[]
  if first['state']=='ATTRIBUTED':
   by_date={row['end']:row for row in a['operating_months']}
   for row in first['dated_contributions']:
    if row['purpose']=='OPERATING':
     source=by_date[row['date']];require(-F(source['cash_settled'])*scale==F(row['amount']),'El aporte operativo no concilia con su mes / deuda');operating.append(row|dict(operating_noi=R(F(source['operating_noi'])*scale),debt_service=R(F(source['debt_service'])*scale),reserve_deposit=R(F(source['reserve_deposit'])*scale),operating_capex=R(F(source['operating_capex'])*scale),explanation='Déficit operativo liquidado después de la refi; incluye servicio de deuda y reserva de ese período, no cash-in del cierre.'))
  out[name]=dict(with_refinance=first,without_refinance=second,prefix=prefix,operating_funding_details=operating,additional_post_refinance_vs_no_refinance=None if first['state']!='ATTRIBUTED' or second['state']!='ATTRIBUTED' else R(F(first['post_refinance_contributions'])-F(second['post_refinance_contributions'])))
 return dict(schema='miniuw.synthetic-dated-cash-attribution.D277.v1',scenarios=out,financial_results_sha256=digest(result),financial_results_mutated=False,criteria_adopted=False,decision='PENDING')
