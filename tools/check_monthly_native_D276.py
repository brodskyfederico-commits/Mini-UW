"""Create and replay explicit synthetic v37 source packets; never a real deal."""
from pathlib import Path
from copy import deepcopy
from fractions import Fraction as Q
from datetime import date
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import json
from argparse import ArgumentParser
from pypdf import PdfReader,PdfWriter
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
import pymupdf as fitz
from check_worksheet_scenario_program_D268 import settings,sources_for,source_cells,decimal,numeric_cells
from check_lorena_criteria_D192 import change_cells
from check_worksheet_construction_pdf_D157 import pages,ORDER
from check_worksheet_evidence_pdf_D156 import evidence_pdf
from check_worksheet_evidence_scan_D158 import add_scan
from check_worksheet_evidence_jpeg_D161 import jpeg_bundle
from check_worksheet_evidence_progressive_order_D164 import SCAN_ENCODINGS,SHUFFLED
from check_worksheet_plan_overlay_D133 import add_text_overlay
from worksheet_monthly_native_D276 import SCHEMA,PROFILE,REFERENCE_SCHEMA
from worksheet_monthly_integration_D276 import integrate
from worksheet_monthly_D275 import month
from worksheet_commercial_leaseup_D275 import SCHEMA as COMMERCIAL
from worksheet_builders_risk_D275 import SCHEMA as RISK
from worksheet_frontiers_D275 import fraction as F,rational as R,digest
from worksheet_variant_evidence_D268 import inputs_digest
from worksheet_intake_D198 import assemble,register,source_inventory
from worksheet_performance_policy_D184 import BEFORE_RESERVES
from miniuw_worksheet_v1 import encoded,read_package,verify_package,CURRENT_REVISION_FILE
from miniuw_foundation.scheduled_expense_case import sha


def clear_cells(raw,addresses):
 buffer=BytesIO();ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
 with ZipFile(BytesIO(raw)) as src,ZipFile(buffer,'w') as out:
  for info in src.infolist():
   data=src.read(info.filename)
   if info.filename=='xl/worksheets/sheet1.xml':
    root=ET.fromstring(data)
    for row in root.iter(ns+'row'):
     for cell in list(row):
      if cell.get('r') in addresses:row.remove(cell)
    data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
   out.writestr(info,data)
 return buffer.getvalue()


def set_numeric_cells(raw,values):
 """Insert numeric observations explicitly, including into formerly absent cells."""
 out=BytesIO();ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
 with ZipFile(BytesIO(raw)) as src,ZipFile(out,'w') as dst:
  for info in src.infolist():
   data=src.read(info.filename)
   if info.filename=='xl/worksheets/sheet1.xml':
    root=ET.fromstring(data);sheet=root.find(ns+'sheetData')
    for address,value in values.items():
     row_number=''.join(c for c in address if c.isdigit());rows=[r for r in sheet if r.get('r')==row_number]
     row=rows[0] if rows else ET.SubElement(sheet,ns+'row',r=row_number)
     for cell in list(row):
      if cell.get('r')==address:row.remove(cell)
     if value is not None:
      cell=ET.SubElement(row,ns+'c',r=address,t='n');ET.SubElement(cell,ns+'v').text=value
    for row in sheet:row[:]=sorted(row,key=lambda c:(len(''.join(v for v in c.get('r','') if v.isalpha())),''.join(v for v in c.get('r','') if v.isalpha())))
    sheet[:]=sorted(sheet,key=lambda row:int(row.get('r')));data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
   dst.writestr(info,data)
 return out.getvalue()


def plan_pdf(area_m2=3000):
 vector=BytesIO();c=canvas.Canvas(vector,pagesize=(792,612),invariant=1);all_lines=[]
 for sheet,text in [('A101','Gross building area | '+str(area_m2)+'.00 | m2'),('A601','Declared GBA: '+format(area_m2,',')+'.00 m2')]:
  lines=[(462,'SYNTHETIC MINI-UW PLAN'),(438,'PLAN REF SYNTHETIC-PLAN-01-R1'),(420,'SHEET '+sheet),(255,text)];all_lines.append(lines)
  c.setFont('Helvetica',11)
  for y,line in lines:c.drawString(60,y,line)
  c.showPage()
 c.save();doc=fitz.open(stream=vector.getvalue(),filetype='pdf');writer=PdfWriter()
 for i,page in enumerate(doc):
  pix=page.get_pixmap(matrix=fitz.Matrix(1900/792,1900/792),colorspace=fitz.csGRAY,alpha=False);rotated=Image.frombytes('L',(pix.width,pix.height),pix.samples).rotate(180);add_scan(writer,pix.width,pix.height,rotated.tobytes());add_text_overlay(writer,writer.pages[-1],all_lines[i]);writer.pages[-1].rotate(180)
 out=BytesIO();writer.write(out);return out.getvalue()


def evidence(spec,sources,requested):
 records=pages(spec);inputs=spec['rent_inputs']
 records['gc']=[line.replace('Area | m2 | 1000','Area | m2 | 3000') for line in records['gc']]
 for name in ('Base','Downside'):
  sheet,cell=source_cells(sources,name);cfg=inputs['construction_financing']['scenarios'][name]
  changes={k:sheet[k]['literal'] for k in ('C51','C52','C53')};changes.update({'Maximum commitment':decimal(F(cfg['maximum_commitment'])),'Requested invoice share':decimal(F(cfg['requested_invoice_fraction'])),'Available per draw':decimal(F(cfg['available_per_draw_checkpoint'])),'Maturity date':cfg['maturity_date']})
  records['construction_'+name.lower()]=[' | '.join([*line.split(' | ')[:-1],changes[line.split(' | ')[0]]]) if line.split(' | ')[0] in changes else line for line in records['construction_'+name.lower()]]
  changes={k:sheet[k]['literal'] for k in ('C69','C70','C71','C72')};changes.update({'Requested principal':str(requested[name]),'Maturity':str(inputs['permanent_loan']['scenarios'][name]['maturity_payments'])})
  records[name.lower()]=[' | '.join([*line.split(' | ')[:-1],changes[line.split(' | ')[0]]]) if line.split(' | ')[0] in changes else line for line in records[name.lower()]]
  vertical=cell('C35')*sum(g['units'] for g in inputs['groups'].values())
  records['gc']=[' | '.join([*line.split(' | ')[:-1],decimal(vertical)]) if line.startswith('Vertical '+name+' |') else line for line in records['gc']]
 writer=PdfWriter();font=ImageFont.truetype('DejaVuSansMono.ttf',size=24)
 for role in ORDER:
  if role=='official':writer.add_page(PdfReader(BytesIO(evidence_pdf(records,(role,))),strict=True).pages[0])
  else:
   image=Image.new('L',(1900,1100),255);draw=ImageDraw.Draw(image)
   for index,line in enumerate(records[role]):draw.text((36,35+52*index),line,font=font,fill=0)
   add_scan(writer,*image.size,image.tobytes())
 out=BytesIO();writer.write(out);raw=jpeg_bundle(out.getvalue(),progressive_roles=SCAN_ENCODINGS,oriented=True,rgb_quality=98,jpeg_roles=SCAN_ENCODINGS)
 reader=PdfReader(BytesIO(raw));writer=PdfWriter()
 for role in SHUFFLED:writer.add_page(reader.pages[ORDER.index(role)])
 out=BytesIO();writer.write(out);return out.getvalue()


def make_sources(directory,*,requested=None,quarter_control=False,edits=None):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);spec=settings();inputs=spec['rent_inputs'];sources=sources_for(spec,directory/'seed')
 spec['schema']=SCHEMA;spec['investment_criteria']=None;spec['rules']=[];spec['criteria_revision']='SYNTHETIC-D276-UNCONFIRMED';spec['local_sources']['revision']='SYNTHETIC-D276-V2';inputs['deal_id']='SYNTHETIC-D276-LEVERED';inputs.pop('requested_principal')
 inputs['holding_horizon']['profile']=PROFILE;inputs['holding_horizon']['rules']={'cash_grid':'monthly_first_day_with_explicit_operating_bridge','holding_months':60};inputs.pop('holding_tax_cash',None)
 inputs['project_calendar']['policy']='SYNTHETIC-D276-monthly-calendar';inputs['project_calendar']['rules']={'calendar':'first_day_monthly','lease_up':'net_residential_shortfall_prefunded_at_TCO'}
 inputs['monthly_integration']=dict(profile=PROFILE,source_ref='SYNTHETIC-D276-native-monthly-source-contract',scenarios={})
 requested=requested or {'Base':1400000,'Downside':1400000}
 for name,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
  change={'C32':'1100000','C35':'90000' if name=='Base' else '99000','C51':'0.65','C69':'0.07' if name=='Base' else '0.08','C70':'30','C71':'0.625','C72':'1.25','C66':'0.065' if name=='Base' else '0.075','C67':'0.07' if name=='Base' else '0.08'}
  change.update((edits or {}).get(name,{}));sources[arg]=numeric_cells(sources[arg],change);sources[arg]=change_cells(sources[arg],{'C34':'$/UNIT','B3':inputs['deal_id']});sources[arg]=clear_cells(sources[arg],{'C21','C36','C80','C81','C82'})
  confirmation=spec['native_mapping']['scenarios'][name]
  for cell in ('C21','C36','C80','C81','C82'):
   fid='INPUT_'+cell
   if fid in confirmation['confirmed_fields']:confirmation['confirmed_fields'].remove(fid)
   if fid not in confirmation['not_applicable_fields']:confirmation['not_applicable_fields'].append(fid)
  _,cell=source_cells(sources,name);purchase=date.fromisoformat(inputs['development']['scenarios'][name]['purchase_date']);finish=month(purchase,int(cell('C46')));stable=month(finish,int(cell('C47')));sale=month(stable,60)
  inputs['development']['scenarios'][name].update(evaluated_purchase_price=R(cell('C32')),plan_gsf=dict(state='declared',value=R(Q(3000)/Q('0.09290304')),source_ref='SYNTHETIC-D276-common-plan-3000m2'))
  inputs['project_calendar']['scenarios'][name]['tco_date']=str(finish);inputs['holding_horizon']['scenarios'][name]['initial_equity']=dict(value=R(1250000),source_ref='SYNTHETIC-D276-initial-equity')
  inputs['supplemental_scope'][name]['sale_date']['value']=str(sale);inputs['integrated_screening'][name]['reference_cap'].update(noi_basis=BEFORE_RESERVES,period_ref=str(stable)+'/'+str(month(stable,12)),source_ref='SYNTHETIC-D276-explicit-before-reserve-comparable')
  bank=inputs['construction_financing']['scenarios'][name];bank.update(maximum_commitment=R(4000000),requested_invoice_fraction=R(Q(5,8)),available_per_draw_checkpoint=R(4000000),maturity_date='2040-01-01',source_ref='SYNTHETIC-D276-bank-commitment')
  dy=inputs['bank_debt_yield'][name];dy['minimum']=R(Q(8,100));dy['source_ref']='SYNTHETIC-D276-bank-debt-yield'
  # These are explicitly authored synthetic forecasts, not inferred official data.
  tax=inputs['florida_property_tax']['scenarios'][name]
  from check_worksheet_horizon_fiscal_D267 import roll
  for year in range(2027,2042):
   if str(year) not in tax['rolls']['seller']:tax['rolls']['seller'][str(year)]=roll(2000000+(year-2027)*(300000 if name=='Base' else 400000),ref='SYNTHETIC-D276-seller-forecast-'+str(year))
   tax['rolls']['millage'][str(year)]=dict(school_mills=R(4),non_school_mills=R(9),source_ref='SYNTHETIC-D276-millage-forecast-'+str(year))
   tax['rolls']['buyer'][str(year)]=roll(5000000 if name=='Base' else 5500000,'ownership_or_control_reset',str(sale),ref='SYNTHETIC-D276-buyer-forecast-'+str(year))
  for role,record in inputs['market_evidence']['scenarios'][name].items():
   doc=record['document']
   if 'ranges' in doc:
    for field in doc['ranges']:doc['ranges'][field]=dict(minimum=R(cell(field)),maximum=R(cell(field)))
   if role=='insurance':doc['premium_per_insured_unit']=R(cell('C59'))
   doc['deal_id']=inputs['deal_id']
   doc['source_ref']='SYNTHETIC-D276-counterfactual-'+name+'-'+role;record['sha256']=sha(encoded(doc))
 sources['plan_raw']=plan_pdf();spec['local_sources']['plan_pdf']['sheet_rotations_clockwise']={'A101':180,'A601':180};sources['evidence_raw']=evidence(spec,sources,requested)
 sources['criteria_raw']=clear_cells(change_cells(sources['criteria_raw'],{'B18':spec['criteria_revision']}),{c+str(r) for c in 'EFGH' for r in range(7,17)})
 for name in ('Base','Downside'):
  inputs['bank_debt_yield'][name]['quote_source_sha256']=sha(sources['evidence_raw']);_,cell=source_cells(sources,name)
  purchase=date.fromisoformat(inputs['development']['scenarios'][name]['purchase_date']);finish=month(purchase,int(cell('C46')));stable=month(finish,int(cell('C47')));sale=month(stable,60);count=int(cell('C46'))
  if quarter_control:hard=[dict(date=str(month(purchase,3)),fraction=R(Q(1,2)),source_ref='SYNTHETIC-quarter-control'),dict(date=str(finish),fraction=R(Q(1,2)),source_ref='SYNTHETIC-quarter-control')]
  else:hard=[dict(date=str(month(purchase,i+1)),fraction=R(Q(1,count)),source_ref='SYNTHETIC-monthly-invoice-'+str(i+1)) for i in range(count)]
  upfront=str(month(purchase,3));soft=[dict(date=upfront,fraction=R(cell('C42')),source_ref='SYNTHETIC-soft-upfront-C42'),dict(date=str(finish),fraction=R(1-cell('C42')),source_ref='SYNTHETIC-soft-remainder')]
  commercial=dict(schema=COMMERCIAL,currency='USD',inventory_complete=True,source_ref='SYNTHETIC-D276-space-inventory',area_reconciliation='RECONCILED',reconciled_area_sf=R(sum(F(r['rentable_sf']) for r in inputs['commercial']['uses'].values() if r['applies'])),owner_cost_scope='commercial_only_excluding_M2_property_tax_insurance_and_residential',start=str(purchase),end=str(month(sale,12)),spaces=[])
  for index,(use,field) in enumerate([('retail','C16'),('restaurant','C17'),('office','C18')]):
   record=inputs['commercial']['uses'][use]
   if not record['applies']:continue
   lease=stable if quarter_control else month(stable,index);sf=F(record['rentable_sf']);steps=[dict(effective_date=str(month(stable,12*i)),relative_increase=R(cell('C75')),source_ref='SYNTHETIC-C75-commercial-anniversary') for i in range(1,7) if lease<=month(stable,12*i)<month(sale,12)]
   commercial['spaces'].append(dict(id='SYNTHETIC-'+use,use=use,source_ref='SYNTHETIC-D276-'+name+'-'+use,area_sf=R(sf),annual_rent_per_sf=R(cell(field)),collection_loss_fraction=R(cell('C19')),owner_cost_mode='legacy_C20_collected_rent_fraction',owner_cost_per_month=None,owner_cost_fraction=R(cell('C20')),recovery_fraction=R(0),lease_start=str(lease),lease_end=commercial['end'],free_rent_months=0 if quarter_control else index,recoveries_waived_during_free_rent=False,noi_bases=dict(bank='collected_net',refinance_valuation='collected_net',sale_valuation='collected_net'),rent_steps=steps,ti_lc_events=[dict(date=str(finish),kind='TI',budget_location='M3',amount=R(cell('C41')*sf),source_ref='SYNTHETIC-D276-TI-C41-'+use)]))
  cfg=dict(source_ref='SYNTHETIC-D276-'+name+'-monthly-terms',requested_principal=R(requested[name]),day_count='30E/360' if quarter_control else 'ACT/360',interest_payment_every_months=3 if quarter_control else 1,tax_payment_every_months=3 if quarter_control else 1,operating_cash_every_months=3 if quarter_control else 1,hard_schedule=hard,soft_schedule=soft,contingency_date=str(finish),upfront_soft_date=upfront,allow_final_date_draws=False,commercial=commercial,commercial_field_modes={'C19':'uniform_C19','C20':'legacy_C20_collected_rent_fraction','C21':'per_space_only'},residential_leaseup_mode='prefunded_net_residential_shortfall_at_TCO',valuation_bases={'refinance':'before_reserves','sale':'before_reserves'},documents=[])
  def add_document(document,locator):
   raw=encoded(document);h=sha(raw);cfg['documents'].append(dict(sha256=h,content_utf8=raw.decode()));return dict(sha256=h,locator=locator)
  amendment=dict(schema='miniuw.synthetic-monthly-bank-amendment.v1',scenario=name,bank_quote_sha256=sha(sources['evidence_raw']),supersedes=['interest_basis','draw_schedule'],day_count=cfg['day_count'],interest_payment_every_months=cfg['interest_payment_every_months'],schedule_sha256=digest({k:cfg[k] for k in ('hard_schedule','soft_schedule','contingency_date','upfront_soft_date','allow_final_date_draws')}))
  cfg['construction_amendment']=add_document(amendment,'monthly bank amendment')
  quote=dict(schema='miniuw.synthetic-builders-risk-quote.v1',currency='USD',premium_basis='quoted_premium',base=None,rate=None,quoted_premium=R(0 if quarter_control else 15000 if name=='Base' else 18000),term_start=str(purchase),term_end=str(finish),payment_date=str(purchase))
  cfg['builders_risk']=quote|dict(schema=RISK,quote_source=add_document(quote,'premium for full term'),included_in_gc=False,included_in_soft_percentage=False)
  inputs['monthly_integration']['scenarios'][name]=cfg
 sources['independent_reference_raw']=encoded(dict(schema=REFERENCE_SCHEMA,inputs_sha256=inputs_digest(inputs),deal_id=inputs['deal_id'],local_revision=spec['local_sources']['revision'],sources={source_inventory(sources)[k]:sha(v) for k,v in sources.items()}))
 for arg,filename in source_inventory(sources).items():(directory/filename).write_bytes(sources[arg])
 (directory/'settings.json').write_bytes(encoded(spec));return spec,sources


def execute(directory,**kwargs):
 directory=Path(directory);spec,sources=make_sources(directory/'sources',**kwargs);receipt=assemble(spec,register(sources,'SYNTHETIC-D276-CURRENT'),sources,directory/'package');saved=read_package(directory/'package');result=json.loads(saved['results.json']);audit=verify_package(directory/'package',current_revision_raw=saved[CURRENT_REVISION_FILE]);(directory/'validation.json').write_bytes(encoded(dict(audit=audit,receipt=receipt,scenario_status={s:dict(state=v['state'],blockers=v['blockers']) for s,v in result['scenarios'].items()})));print(json.dumps(dict(output=str(directory),states={s:v['state'] for s,v in result['scenarios'].items()},blockers={s:v['blockers'] for s,v in result['scenarios'].items()})),flush=True);return result


def main():
 p=ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--quarter-control',action='store_true');args=p.parse_args();execute(args.output,quarter_control=args.quarter_control)
if __name__=='__main__':main()
