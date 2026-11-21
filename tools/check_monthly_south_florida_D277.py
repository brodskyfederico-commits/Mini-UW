"""New authored synthetic v3; reviewer ranges are calibration, not market data."""
from pathlib import Path
from datetime import date
from fractions import Fraction as Q
from copy import deepcopy
import json
from check_monthly_native_D276 import make_sources as seed_sources,evidence,source_cells,set_numeric_cells,change_cells
from worksheet_project_financing_D277 import SCHEMA,PROFILE,POLICY,BASIS,ROLES,ADDENDUM
from worksheet_monthly_native_D276 import REFERENCE_SCHEMA
from worksheet_monthly_D275 import month
from worksheet_frontiers_D275 import fraction as F,rational as R,digest
from worksheet_variant_evidence_D268 import inputs_digest
from worksheet_intake_D198 import source_inventory,assemble,register
from miniuw_worksheet_v1 import encoded,read_package,verify_package,CURRENT_REVISION_FILE
from miniuw_foundation.scheduled_expense_case import sha
from check_monthly_oracle_D276 import oracle,verify


def values(down):
 return {'C32':'1600000','C35':'272700' if down else '270000','C37':'15150' if down else '15000','C38':'404000' if down else '400000','C39':'0.05','C40':'0.10','C41':'35.35' if down else '35','C42':'0.30','C46':'19' if down else '18','C47':'7' if down else '6','C51':'0.65','C52':'0.09' if down else '0.085','C53':'0.01','C69':'0.064' if down else '0.0625','C70':'30','C71':'0.625','C72':'1.25','C66':'0.061' if down else '0.06','C67':'0.064' if down else '0.0625','C8':'2965' if down else '2980','C9':'3720' if down else '3740','C10':'4375' if down else '4400','C11':'5275' if down else '5305','C14':'0.055' if down else '0.05','C15':'0.01','C16':'45','C17':'50','C18':'40','C19':'0.08','C20':'0.12','C57':'6060' if down else '6000','C59':'2100' if down else '2000','C60':'1200','C75':'0.025' if down else '0.03','C76':'0.03' if down else '0.025'}


def make_sources(directory):
 directory=Path(directory);spec,sources=seed_sources(directory,requested={'Base':1,'Downside':1},edits={s:values(s=='Downside') for s in ('Base','Downside')});i=spec['rent_inputs'];spec['schema']=SCHEMA;spec['local_sources']['revision']='SYNTHETIC-D277-V3';i['deal_id']='SYNTHETIC-D277-V3';i['monthly_integration']['profile']=PROFILE;i['holding_horizon']['profile']=PROFILE;i['construction_financing']['policy']=POLICY;i['construction_financing']['rules']['eligible_cost']=BASIS
 for name,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
  sources[arg]=change_cells(sources[arg],{'B3':i['deal_id']});_,c=source_cells(sources,name);cfg=i['monthly_integration']['scenarios'][name];start=date.fromisoformat(i['development']['scenarios'][name]['purchase_date']);finish=month(start,int(c('C46')));stable=month(finish,int(c('C47')));sale=month(stable,60)
  i['holding_horizon']['scenarios'][name]['initial_equity']=dict(value=R(2000000),source_ref='SYNTHETIC-D277-authored-initial-equity');bank=i['construction_financing']['scenarios'][name];bank.update(requested_invoice_fraction=R(Q(62,100)),maximum_commitment=R(10000000),available_per_draw_checkpoint=R(10000000),maturity_date='2036-01-01',source_ref='SYNTHETIC-D277-fixed-construction-facility');cfg['operating_cash_every_months']=3
  i['integrated_screening'][name]['reference_cap']['value']=R(Q('0.058'))
  tax=i['florida_property_tax']['scenarios'][name]
  from check_worksheet_horizon_fiscal_D267 import roll
  for year in range(2027,2042):
   reset=finish.year+1;market=Q(10100000 if name=='Downside' else 10000000)*Q('1.02')**max(0,year-reset) if year>=reset else Q(2000000)
   tax['rolls']['seller'][str(year)]=roll(market,'qualifying_improvement_reset' if year==reset else 'confirmed_no_change',str(finish) if year==reset else None,ref='SYNTHETIC-D277-authored-seller-forecast-'+str(year))
   tax['rolls']['buyer'][str(year)]=roll(13400000 if name=='Downside' else 13000000,'ownership_or_control_reset',str(sale),ref='SYNTHETIC-D277-authored-buyer-forecast-'+str(year))
  cfg['builders_risk']['quoted_premium']=R(36000 if name=='Downside' else 35000)
  for record in i['market_evidence']['scenarios'][name].values():record['document']['deal_id']=i['deal_id'];record['sha256']=sha(encoded(record['document']))
 # Author the fixed request ONCE in fixture creation. Native intake cannot autosize.
 requested={}
 for name in ('Base','Downside'):
  cfg=i['monthly_integration']['scenarios'][name];observed=oracle(spec,sources,name);p=F(observed['capacity'])*Q(999,1000);requested[name]=int(p//1000)*1000;cfg['requested_principal']=R(requested[name])
 sources['evidence_raw']=evidence(spec,sources,requested)
 for name,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
  cfg=i['monthly_integration']['scenarios'][name];_,c=source_cells(sources,name);cfg['documents']=[]
  def add(doc,locator):
   raw=encoded(doc);h=sha(raw);cfg['documents'].append(dict(sha256=h,content_utf8=raw.decode()));return dict(sha256=h,locator=locator)
  cfg['construction_amendment']=add(dict(schema='miniuw.synthetic-monthly-bank-amendment.v1',scenario=name,bank_quote_sha256=sha(sources['evidence_raw']),supersedes=['interest_basis','draw_schedule'],day_count=cfg['day_count'],interest_payment_every_months=cfg['interest_payment_every_months'],schedule_sha256=digest({k:cfg[k] for k in ('hard_schedule','soft_schedule','contingency_date','upfront_soft_date','allow_final_date_draws')})),'D277 fixed synthetic bank amendment')
  quote={k:v for k,v in cfg['builders_risk'].items() if k not in ('quote_source','included_in_gc','included_in_soft_percentage')};quote['schema']='miniuw.synthetic-builders-risk-quote.v1';cfg['builders_risk']['quote_source']=add(quote,'authored full-term premium, not a real offer')
  hard=c('C35')*26+c('C37')*i['construction_budget']['scenarios'][name]['parking']['spaces']+c('C38');cont=hard*c('C39');soft=(hard+cont)*c('C40');area=sum(F(v['rentable_sf']) for v in i['commercial']['uses'].values() if v['applies']);roles=dict(land=R(c('C32')*(1+c('C33'))),direct_hard=R(hard),contingency=R(cont),soft=R(soft),ti_lc=R(c('C41')*area))
  cfg['project_eligibility']=add(dict(schema=ADDENDUM,usage='synthetic_test_only',supersedes=['eligible_cost'],scenario=name,currency='USD',bank_quote_sha256=sha(sources['evidence_raw']),workbook_sha256=sha(sources[arg]),eligible_cost_basis=BASIS,eligible_roles=list(ROLES),role_amounts=roles,eligible_total=R(sum((F(v) for v in roles.values()),Q())),ltc_cap=R(c('C51')),requested_invoice_share=i['construction_financing']['scenarios'][name]['requested_invoice_fraction']),'five eligible M3 roles, synthetic terms only')
  i['bank_debt_yield'][name]['quote_source_sha256']=sha(sources['evidence_raw'])
 sources['independent_reference_raw']=encoded(dict(schema=REFERENCE_SCHEMA,inputs_sha256=inputs_digest(i),deal_id=i['deal_id'],local_revision=spec['local_sources']['revision'],sources={source_inventory(sources)[k]:sha(v) for k,v in sources.items() if k!='independent_reference_raw'}))
 for arg,filename in source_inventory(sources).items():(directory/filename).write_bytes(sources[arg])
 (directory/'settings.json').write_bytes(encoded(spec));return spec,sources


def execute(output):
 output=Path(output);spec,sources=make_sources(output/'sources');assemble(spec,register(sources,'SYNTHETIC-D277-CURRENT'),sources,output/'package');saved=read_package(output/'package');r=json.loads(saved['results.json']);print(json.dumps({s:(v['state'],v['blockers']) for s,v in r['scenarios'].items()}),flush=True)
 proof=verify(spec,sources,r);(output/'oracle.json').write_bytes(encoded(proof));(output/'validation.json').write_bytes(encoded(verify_package(output/'package',current_revision_raw=saved[CURRENT_REVISION_FILE])));return r

if __name__=='__main__':
 import sys
 execute(Path(sys.argv[1]))
