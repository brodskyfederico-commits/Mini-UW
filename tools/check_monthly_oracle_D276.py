"""Independent rational oracle from literal XLSX and authored source contracts.

No monthly motor, commercial motor, fiscal motor, amortization motor, returned
cash total or returned NOI is used to construct expected amounts. This is a
synthetic arithmetic check, not an independent professional opinion.
"""
from fractions import Fraction as Q
from datetime import date
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
from worksheet_frontiers_D275 import fraction as F,rational as R,digest
from check_worksheet_scenario_program_D268 import source_cells


def offset(d,n):
 y,m=divmod(d.year*12+d.month-1+n,12);return date(y,m+1,d.day)


def span(a,b,convention):
 if convention=='ACT/360':return Q((b-a).days,360)
 if convention=='30E/360':return Q((b.year-a.year)*360+(b.month-a.month)*30+min(30,b.day)-min(30,a.day),360)
 raise ValueError('Independent oracle requires explicit day count')


def oracle(spec,sources,name):
 inputs=spec['rent_inputs'];cfg=inputs['monthly_integration']['scenarios'][name];sheet,c=source_cells(sources,name);units=sum(g['units'] for g in inputs['groups'].values())
 start=date.fromisoformat(inputs['development']['scenarios'][name]['purchase_date']);finish=offset(start,int(c('C46')));stable=offset(finish,int(c('C47')));sale=offset(stable,60);pre=int(c('C46')+c('C47'));all_dates=[offset(start,i) for i in range(pre+72)]
 tax=inputs['florida_property_tax']['scenarios'][name];assess=F(tax['opening_assessment']['non_school_assessed_value']);rolls={}
 for year in range(tax['opening_assessment']['tax_year']+1,sale.year+1):
  r=tax['rolls']['seller'][str(year)];market=F(r['just_value']);assess=min(market,assess*(1+Q(5 if year>=2027 else 10,100))) if r['assessment_treatment']=='confirmed_no_change' else market;rolls[year]=(F(r['school_taxable_value']),assess)
 taxes={}
 for d in all_dates:
  if d>=sale and d.year>sale.year:
   r=tax['rolls']['buyer'][str(d.year)];school,non_school=F(r['school_taxable_value']),F(r['just_value'])
  else:school,non_school=rolls[d.year]
  rate=tax['rolls']['millage'][str(d.year)];taxes[d]=(school*F(rate['school_mills'])+non_school*F(rate['non_school_mills']))/12000
  if d>=stable:taxes[d]*=1+F(inputs['stabilized_tax_stress']['scenarios'][name]['relative_change'])
 cost_scope=inputs['operating_costs']['scenarios'][name];base_res=sum(c('C'+str(i))*inputs['groups'][g]['units']*(F(inputs['groups'][g]['rentable_sf_per_unit']) if sheet['C7']['literal']=='PER SF' else 1)*12 for i,g in zip(range(8,12),('studio','1BR','2BR','3BR')))
 other=c('C13')*inputs['other_income']['eligible_units']*12;fixed=F(inputs['annual_expenses']['fixed_opex'])+c('C57')*cost_scope['controllable_units']+c('C59')*cost_scope['insured_units'];bank_extra=F(inputs['supplemental_scope'][name]['bank_vacancy_addition']['value']);res={};commercial={}
 for d in all_dates:
  y=((d.year-stable.year)*12+d.month-stable.month)//12
  res[d]={}
  for role in ('operating','bank','refinance','sale'):
   if d<stable:value=Q()
   else:
    rent=base_res*(1+c('C75'))**y;collected=rent*(1-c('C14')-c('C15')-(bank_extra if role=='bank' else 0));value=(collected+other-fixed*(1+c('C76'))**y-c('C58')*(collected+other))/12
   res[d][role]=value
  totals={k:Q() for k in ('operating','bank','refinance','sale','capex')}
  for space in cfg['commercial']['spaces']:
   lease=date.fromisoformat(space['lease_start']);expiry=date.fromisoformat(space['lease_end']);active=lease<=d<expiry;age=(d.year-lease.year)*12+d.month-lease.month;factor=Q(1)
   for step in space['rent_steps']:
    if d>=date.fromisoformat(step['effective_date']):factor*=1+F(step['relative_increase'])
   rent=F(space['area_sf'])*F(space['annual_rent_per_sf'])*factor/12 if active and age>=space['free_rent_months'] else Q();loss=F(space['collection_loss_fraction']);owner=rent*(1-loss)*F(space['owner_cost_fraction']) if space.get('owner_cost_mode')=='legacy_C20_collected_rent_fraction' else F(space['owner_cost_per_month']);recover=owner*F(space['recovery_fraction']) if active and not (age<space['free_rent_months'] and space['recoveries_waived_during_free_rent']) else Q();cash=(rent+recover)*(1-loss)-owner;contractual=rent+recover-owner
   totals['operating']+=cash
   for role,basis in [('bank','bank'),('refinance','refinance_valuation'),('sale','sale_valuation')]:totals[role]+=contractual if space['noi_bases'][basis]=='contractual_net' else cash
   for e in space['ti_lc_events']:
    if e['budget_location']=='operating_capex' and date.fromisoformat(e['date']).replace(day=1)==d:totals['capex']+=F(e['amount'])
  commercial[d]=totals
 budget_cfg=inputs['construction_budget']['scenarios'][name];basis=sheet['C34']['literal'];qty=units if basis=='$/UNIT' else Q(1) if basis=='TOTAL' else F(inputs['development']['scenarios'][name]['plan_gsf']['value']);vertical=c('C35')*qty;hard=vertical+c('C37')*budget_cfg['parking']['spaces']+c('C38');contingency=hard*c('C39');soft=(hard+contingency)*c('C40');area=sum(F(v['rentable_sf']) for v in inputs['commercial']['uses'].values() if v['applies']);land=c('C32')*(1+c('C33'));leaseup=F(inputs['project_calendar']['scenarios'][name]['lease_up_shortfall_per_month'])*c('C47');uses=defaultdict(Q);draws=defaultdict(Q);receipts=defaultdict(Q)
 uses[start]+=land;uses[finish]+=contingency+leaseup+c('C41')*area
 bank=inputs['construction_financing']['scenarios'][name];eligible=land+hard+contingency+soft+c('C41')*area if spec.get('schema')=='miniuw.synthetic-native-rental-inputs.v38' else hard;commitment=min(eligible*c('C51'),F(bank['maximum_commitment']));fee=commitment*c('C53');uses[start]+=fee
 for row in cfg['hard_schedule']:
  d=date.fromisoformat(row['date']);amount=hard*F(row['fraction']);uses[d]+=amount;draws[d]+=amount*F(bank['requested_invoice_fraction'])
 for row in cfg['soft_schedule']:uses[date.fromisoformat(row['date'])]+=soft*F(row['fraction'])
 if spec.get('schema')=='miniuw.synthetic-native-rental-inputs.v38':
  share=F(bank['requested_invoice_fraction']);draws[start]+=land*share;draws[finish]+=(contingency+c('C41')*area)*share
  for row in cfg['soft_schedule']:draws[date.fromisoformat(row['date'])]+=soft*F(row['fraction'])*share
 premium=F(cfg['builders_risk']['quoted_premium']);assert cfg['builders_risk']['premium_basis']=='quoted_premium' and not cfg['builders_risk']['included_in_gc'] and not cfg['builders_risk']['included_in_soft_percentage'];uses[date.fromisoformat(cfg['builders_risk']['payment_date'])]+=premium
 tax_accrual=Q()
 for i in range(pre):
  d=offset(start,i);end=offset(start,i+1);tax_accrual+=taxes[d]
  if (i+1)%cfg['tax_payment_every_months']==0 or i+1==pre:uses[end]+=tax_accrual;tax_accrual=Q()
  amount=commercial[d]['operating'];receipts[end]+=max(Q(),amount);uses[end]+=max(Q(),-amount)
  uses[end]+=commercial[d]['capex']
 # Integrate principal daily between source events, pay only on declared dates.
 interest_due=defaultdict(Q);balance=Q();accrued=Q()
 for i in range(pre):
  a,b=offset(start,i),offset(start,i+1);previous=a
  for d in sorted(day for day in draws if a<=day<b or i+1==pre and day==b):accrued+=balance*c('C52')*span(previous,d,cfg['day_count']);balance+=draws[d];previous=d
  accrued+=balance*c('C52')*span(previous,b,cfg['day_count'])
  if (i+1)%cfg['interest_payment_every_months']==0 or i+1==pre:interest_due[b]+=accrued;accrued=Q()
 initial=F(inputs['holding_horizon']['scenarios'][name]['initial_equity']['value']);free=initial;equity=[(start,initial)];fund_dates=sorted(set(uses)|set(draws)|set(receipts)|set(interest_due));funding=[]
 for d in fund_dates:
  before=free+draws[d]+receipts[d]-uses[d]-interest_due[d];extra=max(Q(),-before);assert d!=start or extra==0;free=before+extra
  if extra:equity.append((d,extra))
  funding.append((d,draws[d],uses[d],receipts[d],interest_due[d],extra,free))
 principal=sum(draws.values());tdc=sum(uses.values())+sum(interest_due.values());reserve=c('C60')*inputs['replacement_reserve']['scenarios'][name]['eligible_units']
 def annual(day,role):return sum(res[offset(day,i)][role]+commercial[offset(day,i)][role]-taxes[offset(day,i)] for i in range(12))
 bank_noi=annual(stable,'bank');refi_noi=annual(stable,'refinance')-(reserve if cfg['valuation_bases']['refinance']=='after_reserves' else 0);sale_noi=annual(sale,'sale')-(reserve if cfg['valuation_bases']['sale']=='after_reserves' else 0);refi_value=refi_noi/c('C66');gross=sale_noi/c('C67');requested=F(cfg['requested_principal']);rate=c('C69')/4;n=int(c('C70'))*4;constant=Q(1,n) if rate==0 else rate/(1-(1+rate)**-n);payment=requested*constant;limits={'LTV':max(Q(),refi_value*c('C71')),'DSCR':max(Q(),bank_noi/(4*constant*c('C72')))};dy=inputs['bank_debt_yield'][name]
 if dy['applicability']=='applicable':limits['DEBT_YIELD']=max(Q(),bank_noi/F(dy['minimum']))
 capacity=min(limits.values());routes={};release=F(inputs['replacement_reserve']['scenarios'][name]['sale_release_fraction']);r_cfg=inputs['refinance_costs']['scenarios'][name];rsv=c('C74')*r_cfg['eligible_units'];r_release=F(r_cfg['sale_release_fraction']);fixed_sale=F(inputs['supplemental_scope'][name]['fixed_sale_cost']['value'])
 for with_refi in (True,False):
  mode='with_refinance' if with_refi else 'without_refinance'
  if with_refi and requested>capacity:routes[mode]=dict(state='PENDING');continue
  if not with_refi:
   carry=inputs['holding_horizon']['scenarios'][name]['without_refinance'];maturity=bank.get('maturity_date')
   if not carry.get('source_ref') or carry.get('retention_terms')!='same_committed_facility_C52_until_documented_maturity':routes[mode]=dict(state='PENDING',reason_code='UNCONFIRMED_RETENTION');continue
   if not isinstance(maturity,str) or not maturity:routes[mode]=dict(state='PENDING',reason_code='MISSING_MATURITY');continue
   if date.fromisoformat(maturity)<sale:routes[mode]=dict(state='PENDING',reason_code='RETAINED_LOAN_MATURITY',maturity=maturity,sale_date=str(sale));continue
  cf=defaultdict(lambda:dict(contribution=Q(),distribution=Q()))
  for d,amount in equity:cf[d]['contribution']+=amount
  if with_refi:net=requested+free-principal-requested*c('C73')-rsv;cf[stable]['distribution']+=max(Q(),net);cf[stable]['contribution']+=max(Q(),-net);debt=requested;held=Q()
  else:
   hold_fee=F(inputs['holding_horizon']['scenarios'][name]['without_refinance']['fee_at_stabilization']['value']);extra=max(Q(),hold_fee-free);cf[stable]['contribution']+=extra;held=free+extra-hold_fee;debt=principal
  aggregate=interest=Q();permanent=[];operating=[]
  for i in range(60):
   d=offset(stable,i);end=offset(stable,i+1);service=Q();before=debt
   if with_refi and (i+1)%3==0 and debt>0:
    interest=debt*rate;capital=min(debt,payment-interest);debt-=capital;balloon=debt if (i+1)//3==inputs['permanent_loan']['scenarios'][name]['maturity_payments'] else Q();debt-=balloon;service=interest+capital+balloon;permanent.append((end,before,interest,capital,balloon,debt))
   if not with_refi:
    interest+=principal*c('C52')*span(d,end,cfg['day_count'])
    if (i+1)%cfg['interest_payment_every_months']==0 or i==59:service=interest;interest=Q()
   net=res[d]['operating']+commercial[d]['operating']-taxes[d]-(reserve/4 if (i+1)%3==0 else 0)-commercial[d]['capex']-service;aggregate+=net;operating.append(net)
   if (i+1)%cfg['operating_cash_every_months']==0:cf[end]['distribution']+=max(Q(),aggregate);cf[end]['contribution']+=max(Q(),-aggregate);aggregate=Q()
  sale_net=gross*(1-c('C68'))-fixed_sale-debt+reserve*5*release+(rsv*r_release if with_refi else held);cf[sale]['distribution']+=max(Q(),sale_net);cf[sale]['contribution']+=max(Q(),-sale_net)
  calls=sum(v['contribution'] for v in cf.values());received=sum(v['distribution'] for v in cf.values());routes[mode]=dict(state='CALCULATED',cash={str(d):{k:R(v*10/initial) for k,v in row.items()} for d,row in sorted(cf.items())},total_contributions=R(calls*10/initial),total_distributions=R(received*10/initial),equity_multiple=R(received/calls),net_sale=R(sale_net),terminal_debt=R(debt),permanent_schedule=[dict(date=str(d),opening_balance=R(o),interest_due=R(i),principal_due=R(p),balloon_due=R(b),closing_balance=R(c)) for d,o,i,p,b,c in permanent])
 return dict(tdc=R(tdc),funding=[dict(date=str(d),loan_draw=R(dr),uses=R(u),other_receipts=R(re),interest_paid=R(i),equity_contribution=R(e),closing_free_cash=R(f)) for d,dr,u,re,i,e,f in funding],taxes={str(k):R(v) for k,v in taxes.items()},residential={str(k):{r:R(v) for r,v in vals.items()} for k,vals in res.items()},annual_noi=R(annual(stable,'operating')),bank_noi=R(bank_noi),refinance_value=R(refi_value),gross_sale=R(gross),capacity=R(capacity),limits={k:R(v) for k,v in limits.items()},routes=routes)


def verify(spec,sources,result,*,scenario_names=('Base','Downside')):
 checked={};observations={}
 for name in scenario_names:
  expected=oracle(spec,sources,name);actual=result['scenarios'][name];assert actual['state']=='CALCULATED',actual['blockers'];checks=0
  def equal(a,b,label):
   nonlocal checks
   assert F(a)==F(b),(name,label,str(F(a)),str(F(b)));checks+=1
  for key in ('tdc','annual_noi','bank_noi','refinance_value','gross_sale'):equal(actual[key],expected[key],key)
  equal(actual['capacity']['maximum_principal_capacity'],expected['capacity'],'capacity')
  for key,v in expected['limits'].items():equal(actual['capacity']['limits'][key],v,'limit/'+key)
  assert [r['date'] for r in actual['construction_financing']['cash_by_date']]==[r['date'] for r in expected['funding']]
  for a,b in zip(actual['construction_financing']['cash_by_date'],expected['funding'],strict=True):
   for key in ('loan_draw','uses','interest_paid','equity_contribution','closing_free_cash'):equal(a[key],b[key],'funding/'+a['date']+'/'+key)
   equal(a.get('other_receipts',R(0)),b['other_receipts'],'source-proven commercial receipts')
  for row in actual['monthly_taxes']:equal(row['amount'],expected['taxes'][row['start']],'M2/'+row['start'])
  contract=result['monthly_contracts'][name]
  for row in contract['residential_monthly']:
   for role in ('operating','bank','refinance','sale'):equal(row[role+'_before_tax'],expected['residential'][row['start']][role],'NOI/'+row['start']+'/'+role)
  for mode,key in [('with_refinance','with_refinance'),('without_refinance','horizon_without_refinance')]:
   route=actual[key];target=expected['routes'][mode];assert route['state']==target['state'],('Independent source oracle state mismatch',name,mode,route['state'],target['state'])
   if target['state']=='PENDING':assert route['cash_per_usd_10'] is None;continue
   cash=route['cash_per_usd_10'];observed=defaultdict(lambda:dict(contribution=Q(),distribution=Q()))
   for e in cash['events']:observed[e['date']][e['kind']]+=F(e['amount'])
   for d in set(observed)|set(target['cash']):
    for kind in ('contribution','distribution'):equal(R(observed[d][kind]),target['cash'].get(d,{}).get(kind,R(0)),'gross/'+mode+'/'+d+'/'+kind)
   for key in ('total_contributions','total_distributions','equity_multiple'):equal(cash[key],target[key],mode+'/'+key)
   equal(route['net_sale'],target['net_sale'],mode+'/net_sale');equal(route['terminal_debt_paid'],target['terminal_debt'],mode+'/debt')
   if mode=='with_refinance':
    # CoC capital includes a negative refinance receipt (cash-in). Derive both
    # numerator and denominator independently from source cash, not the ratio.
    inputs=spec['rent_inputs'];_,cell=source_cells(sources,name);initial=F(inputs['holding_horizon']['scenarios'][name]['initial_equity']['value']);cfg=inputs['monthly_integration']['scenarios'][name];start=date.fromisoformat(inputs['development']['scenarios'][name]['purchase_date']);stable=offset(start,int(cell('C46')+cell('C47')));pre_calls=initial+sum(F(row['equity_contribution']) for row in expected['funding']);draws=sum(F(row['loan_draw']) for row in expected['funding']);free=F(expected['funding'][-1]['closing_free_cash']);net_refi=F(cfg['requested_principal'])*(1-cell('C73'))+free-draws-cell('C74')*inputs['refinance_costs']['scenarios'][name]['eligible_units'];capital=pre_calls-net_refi;annual_net=sum((F(row['distribution'])-F(row['contribution']) for day,row in target['cash'].items() if str(stable)<day<=str(offset(stable,12))),Q())*initial/10
    if capital>0:equal(route['post_refi_coc'],R(annual_net/capital),'CoC includes refinance cash-in')
    else:assert route['post_refi_coc'] is None

   for a,b in zip(route['permanent_schedule'],target['permanent_schedule'],strict=True):
    assert a['date']==b['date']
    for field in ('opening_balance','interest_due','principal_due','balloon_due','closing_balance'):equal(a[field],b[field],mode+'/permanent/'+a['date']+'/'+field)
   irr=route['return_summary']['irr_annual']
   if irr['state']=='CERTIFIED':
    dates=[offset(date.fromisoformat(contract['purchase_date']),i) for i in range(len(route['return_summary']['dated_cash']))];coeff=[sum((F(r['distribution'])-F(r['contribution']) for day,r in target['cash'].items() if day==str(d)),Q()) for d in dates];lo,hi=(F(irr['discount_factor_enclosure'][k]) for k in ('lower','upper'))
    assert sum(v*lo**i for i,v in enumerate(coeff))*sum(v*hi**i for i,v in enumerate(coeff))<=0
    equal(irr['annual_enclosure']['lower'],R(hi**-12-1),'irr lower');equal(irr['annual_enclosure']['upper'],R(lo**-12-1),'irr upper')
  checked[name]=dict(exact_comparisons=checks,gross_dates=True,tdc=True,monthly_tax=True,independent_amortization=True,irr_bracket_checked=True);observations[name]=expected
 return dict(state='PASSED',schema='miniuw.monthly-literal-source-oracle.D276.v1',checks=checked,observations=observations,results_sha256=digest(result),settings_sha256=digest(spec),source_sha256s={k:sha256(v).hexdigest() for k,v in sources.items() if isinstance(v,bytes)},criteria_adopted=False,real_decision='PENDING',deployment_enabled=False)
