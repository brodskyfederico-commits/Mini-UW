"""Immutable quarterly source fixture and live-formula independent workbook.

The workbook is built from original cells and source contracts, not result
values. Recalculation by an external spreadsheet engine remains an explicit
acceptance gate; opening a formula file is not evidence of recalculation.
"""
from pathlib import Path
from fractions import Fraction as Q
from datetime import date
from hashlib import sha256
from argparse import ArgumentParser
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import json,shutil,subprocess
from worksheet_review_templates_D275 import xlsx
from worksheet_frontiers_D275 import fraction,rational
from check_worksheet_scenario_program_D268 import source_cells,independently_verify
from miniuw_worksheet_v1 import encoded,read_package,verify_package,CURRENT_REVISION_FILE,write_package
from worksheet_intake_D198 import read_source_directory

SCHEMA='miniuw.synthetic-golden-case.v1'

def _numeric(text):
 try:Q(text);return True
 except (ValueError,TypeError,ZeroDivisionError):return False
SOURCE_FILES=('case.json','Inputs.xlsx','Downside_Inputs.xlsx','Plan.pdf','Evidence.pdf','Criterios_Lorena.xlsx','Independent_Reference.json','current_revision.json')


def workbook(spec,sources):
 sheets={'Instrucciones':[['Caso dorado v1','Sólo cotejo sintético independiente; no criterio vigente ni dictamen.'],['Estado','PENDING hasta recalcular en LibreOffice / Excel y cotejar con el paquete reproducido.'],['Fuentes','Cada valor primario viene de los XLSX y contratos fuente congelados; no de results.json.'],['Vacíos','Los cálculos exigen COUNT de los operandos: un vacío produce #N/A, nunca cero.'],['Tolerancia propuesta del ensayo','USD 0,01 por USD 10 y 0,0001 de TIR anual; no es tolerancia de inversión.'],['TIR','IRR es contraste de hoja de cálculo del caso dorado con una raíz probada; no sustituye la certificación del motor.']]}
 inputs=spec['rent_inputs'];summary=[['Escenario','Ruta','Aportado por USD10','Cobrado por USD10','Sin recuperar','Múltiplo','TIR anual']]
 def F(text):return dict(formula=text)
 for scenario in ('Base','Downside'):
  short='B' if scenario=='Base' else 'D';I=short+' Inputs';C=short+' Calculo';T=short+' Impuestos';K=short+' Obra';L=short+' Permanente';O=short+' Operacion'
  literal,cell=source_cells(sources,scenario);rows=[[None,None,None] for _ in range(83)]
  for key,value in literal.items():
   if not key.startswith('C') or not key[1:].isdigit():continue
   idx=int(key[1:]);raw=value.get('literal')
   if raw is None or raw=='':continue
   try:number=float(Q(raw))
   except (ValueError,TypeError,ZeroDivisionError):number=raw
   rows[idx-1]=[key,None,number]
  sheets[I]=rows;calc=[['Variable / fuente','Valor o fórmula'],['Guardia: entradas completas',F('NA()')]];refs={};constant_refs=[];guard=f"'{C}'!B2"
  def add(name,value):
   calc.append([name,value]);refs[name]=f"'{C}'!B{len(calc)}";return refs[name]
  def const(name,value):
   ref=add(name,float(fraction(value)));constant_refs.append(ref);return ref
  def ci(key):return f"'{I}'!{key}"
  def form(name,expression,dependencies):
   dep=','.join(dependencies)
   return add(name,F(f'IF(COUNT({dep})={len(dependencies)},{expression},NA())'))
  def taxform(start,months,forward=False):
   terms=[]
   for offset in range(months):
    k=start.year*12+start.month-1+offset;year=k//12
    owner='buyer' if forward and year>=sale.year+1 else 'seller'
    ref=taxrefs.get((owner,year))
    if ref is None:return 'NA()'
    terms.append(f'{ref}/12')
   return '('+'+'.join(terms)+')'
  group_refs=[];area_refs=[]
  for group in ('studio','1BR','2BR','3BR'):
   group_refs.append(const('Unidades '+group,inputs['groups'][group]['units']));area_refs.append(const('SF por unidad '+group,inputs['groups'][group]['rentable_sf_per_unit']))
  units=form('Unidades totales','+'.join(group_refs),group_refs)
  area=[]
  for use in ('retail','restaurant','office'):area.append(const('Comercial SF '+use,inputs['commercial']['uses'][use]['rentable_sf']))
  totalarea=form('Comercial SF total','+'.join(area),area)
  otherunits=const('Unidades otros ingresos',inputs['other_income']['eligible_units'])
  fixed=const('Gastos fijos base',inputs['annual_expenses']['fixed_opex'])
  insured=const('Unidades aseguradas',inputs['operating_costs']['scenarios'][scenario]['insured_units'])
  reserveunits=const('Unidades reserva',inputs['replacement_reserve']['scenarios'][scenario]['eligible_units'])
  permanentunits=const('Unidades reserva permanente',inputs['refinance_costs']['scenarios'][scenario]['eligible_units'])
  park=const('Parking spaces',inputs['construction_budget']['scenarios'][scenario]['parking']['spaces'])
  cfg=inputs['holding_horizon']['scenarios'][scenario]
  initial=const('Equity inicial',cfg['initial_equity']['value'])
  loan=const('Préstamo permanente solicitado',inputs['requested_principal'])
  bankcfg=inputs['construction_financing']['scenarios'][scenario]
  maxloan=const('Compromiso máximo obra',bankcfg['maximum_commitment']);share=const('Share invoice',bankcfg['requested_invoice_fraction'])
  upfront=const('Hard upfront share',inputs['project_calendar']['scenarios'][scenario]['upfront_direct_hard_share'])
  shortfall=const('Lease-up mensual',inputs['project_calendar']['scenarios'][scenario]['lease_up_shortfall_per_month'])
  fixedsale=const('Venta costo fijo',inputs['supplemental_scope'][scenario]['fixed_sale_cost']['value'])
  release=const('Reserva reposición fracción liberada',inputs['replacement_reserve']['scenarios'][scenario]['sale_release_fraction'])
  permrelease=const('Reserva permanente fracción liberada',inputs['refinance_costs']['scenarios'][scenario]['sale_release_fraction'])
  holdfee=const('Fee extensión sin refi',cfg['without_refinance']['fee_at_stabilization']['value'])
  taxstress=const('Estrés fiscal declarado',inputs['stabilized_tax_stress']['scenarios'][scenario]['relative_change'])
  purchase=date.fromisoformat(inputs['development']['scenarios'][scenario]['purchase_date'])
  def month(d,m):
   k=d.year*12+d.month-1+m;return date(k//12,k%12+1,d.day)
  finish=month(purchase,int(cell('C46')));stable=month(finish,int(cell('C47')));hold=cfg['holding_months'];sale=month(stable,hold)
  tax=inputs['florida_property_tax']['scenarios'][scenario];taxrows=[['Owner','Año','Just value','School taxable','School mills','No escolar mills','Sin cambio','Previo no escolar','No escolar aplicado','Impuesto anual']];taxrefs={}
  previous=float(fraction(tax['opening_assessment']['non_school_assessed_value']))
  for owner in ('seller','buyer'):
   for year,roll in sorted(tax['rolls'][owner].items()):
    rates=tax['rolls']['millage'][year];r=len(taxrows)+1
    prior=previous if owner=='seller' and not isinstance(previous,str) else F(previous) if owner=='seller' else None
    unchanged=1 if roll['assessment_treatment']=='confirmed_no_change' else 0
    applied=F(f'IF(COUNT(C{r}:G{r})=5,IF(G{r}=1,IF(COUNT(H{r})=1,MIN(C{r},H{r}*(1+IF(B{r}>=2027,0.05,0.10))),NA()),C{r}),NA())')
    total=F(f'IF(COUNT(D{r}:F{r},I{r})=4,(D{r}*E{r}+I{r}*F{r})/1000,NA())')
    taxrows.append([owner,int(year),float(fraction(roll['just_value'])),float(fraction(roll['school_taxable_value'])),float(fraction(rates['school_mills'])),float(fraction(rates['non_school_mills'])),unchanged,prior,applied,total])
    taxrefs[owner,int(year)]=f"'{T}'!J{r}"
    if owner=='seller':previous=f'I{r}'
  sheets[T]=taxrows
  quantity=1 if literal['C34']['literal']=='TOTAL' else sum(g['units'] for g in inputs['groups'].values()) if literal['C34']['literal']=='$/UNIT' else inputs['development']['scenarios'][scenario]['plan_gsf']['value']
  qty=const('Cantidad vertical compatible',quantity)
  vertical=form('Costo vertical',f'{ci("C35")}*{qty}',[ci('C35'),qty])
  direct=form('Hard directo',f'{vertical}+{ci("C37")}*{park}+{ci("C38")}',[vertical,ci('C37'),park,ci('C38')])
  hard=form('Hard con contingencia',f'{direct}*(1+{ci("C39")})',[direct,ci('C39')])
  soft=form('Soft',f'{hard}*{ci("C40")}',[hard,ci('C40')])
  land=form('Terreno y C33',f'{ci("C32")}*(1+{ci("C33")})',[ci('C32'),ci('C33')])
  total=form('Presupuesto preapertura',f'{land}+{hard}+{soft}+{ci("C41")}*{totalarea}+{shortfall}*{ci("C47")}',[land,hard,soft,ci('C41'),totalarea,shortfall,ci('C47')])
  commitment=form('Compromiso obra',f'MIN({ci("C51")}*{direct},{maxloan})',[ci('C51'),direct,maxloan])
  fee=form('Fee obra',f'{commitment}*{ci("C53")}',[commitment,ci('C53')])
  payment=form('Pago trimestral permanente',f'IF({ci("C69")}=0,{loan}/({ci("C70")}*4),{loan}*({ci("C69")}/4)/(1-(1+{ci("C69")}/4)^(-{ci("C70")}*4)))',[loan,ci('C69'),ci('C70')])
  annualreserve=form('Reserva anual',f'{ci("C60")}*{reserveunits}',[ci('C60'),reserveunits])
  perres=form('Reserva permanente',f'{ci("C74")}*{permanentunits}',[ci('C74'),permanentunits])
  refifee=form('Fee refi',f'{loan}*{ci("C73")}',[loan,ci('C73')])
  # Construction: exact declared checkpoints, with fully separate gross calls.
  dates=[month(purchase,i) for i in range(0,(stable.year-purchase.year)*12+stable.month-purchase.month+1,3)]
  rows=[['Fecha','Usos proyecto','Draw','Interés pagado','Fee','Caja apertura','Equity','Caja cierre','Principal acumulado']]
  for j,day in enumerate(dates):
   r=j+2;uses=[];eligible=[]
   if day==purchase:uses.append(land)
   if day==month(purchase,3):uses.append(f'{direct}*{upfront}+{soft}*{ci("C42")}');eligible.append(f'{direct}*{upfront}')
   if day==finish:uses.append(f'{total}-{land}-{direct}*{upfront}-{soft}*{ci("C42")}');eligible.append(f'{direct}*(1-{upfront})')
   if j:uses.append(taxform(month(day,-3),3))
   use_expr='+'.join(uses) or '0'
   draw_expr='('+('+'.join(eligible) or '0')+f')*{share}' if j<len(dates)-1 else '0'
   interest='0' if j==0 else f'I{r-1}*{ci("C52")}/4'
   opening='0' if j==0 else f'H{r-1}'
   principal=f'C{r}' if j==0 else f'I{r-1}+C{r}'
   equity=initial if j==0 else f'MAX(0,B{r}+D{r}+E{r}-F{r}-C{r})'
   rows.append([str(day),F(use_expr),F(draw_expr),F(interest),F(fee if j==0 else '0'),F(opening),F(equity),F(f'F{r}+C{r}+G{r}-B{r}-D{r}-E{r}'),F(principal)])
  sheets[K]=rows;last=len(rows);payoff=f"'{K}'!I{last}";free=f"'{K}'!H{last}"
  tdc=form('TDC integrado',f"SUM('{K}'!B2:B{last})+SUM('{K}'!D2:E{last})",[total,fee])
  refinet=form('Refi neta',f'{loan}+{free}-{payoff}-{refifee}-{perres}',[loan,free,payoff,refifee,perres])
  newloanrows=[['Número','Saldo apertura','Interés','Principal','Saldo cierre','Balloon contractual','Servicio más balloon']]
  maturity=inputs['permanent_loan']['scenarios'][scenario]['maturity_payments']
  for j in range(maturity):
   r=j+2;opening=loan if j==0 else f'E{r-1}'
   newloanrows.append([j+1,F(opening),F(f'B{r}*{ci("C69")}/4'),F(f'{payment}-C{r}'),F(f'B{r}-D{r}'),F(f'E{r}' if j+1==maturity else '0'),F(f'{payment}+F{r}')])
  sheets[L]=newloanrows
  # First year and following quarters, using the complete literal operating basis.
  op=[['Fecha cobro','NOI pre impuesto anual','Impuesto trimestral','Reserva','Servicio con refi','Caja neta con refi','Servicio sin refi','Caja neta sin refi']]
  def pretax(year):
   rent='+'.join(f'{ci("C"+str(8+j))}*{u}'+(f'*{area_refs[j]}' if literal['C7']['literal']=='PER SF' else '') for j,u in enumerate(group_refs))
   residential=f'12*({rent})*(1+{ci("C75")})^{year}*(1-{ci("C14")}-{ci("C15")})'
   # C20 applies as a multiplicative non-recoverable fraction.
   commercial=f'({"+".join(f"{ci(chr(67)+str(16+j))}*{ar}" for j,ar in enumerate(area))})*(1+{ci("C75")})^{year}*(1-{ci("C19")})*(1-{ci("C20")})'
   other=f'{ci("C13")}*{otherunits}*12'
   expense=f'({fixed}+{ci("C57")}*{units}+{ci("C59")}*{insured})*(1+{ci("C76")})^{year}+{ci("C58")}*(({residential})+({other}))'
   return f'({residential})+({commercial})+({other})-({expense})'
  for j in range(hold//3):
   r=j+2;end=month(stable,3*(j+1));qstart=month(stable,3*j)
   taxamount=taxform(qstart,3)+f'*(1+{taxstress})'
   op.append([str(end),F(pretax(j//4)),F(taxamount),F(f'{annualreserve}/4'),F(payment),F(f'B{r}/4-C{r}-D{r}-E{r}'),F(f'{payoff}*{ci("C52")}/4'),F(f'B{r}/4-C{r}-D{r}-G{r}')])
  sheets[O]=op
  saleprice=form('Precio venta',f'(({pretax(hold//12)})-({taxform(sale,12,True)})*(1+{taxstress}))/{ci("C67")}',[ci('C67'),taxstress])
  salecost=form('Costo venta',f'{saleprice}*{ci("C68")}+{fixedsale}',[saleprice,ci('C68'),fixedsale])
  releaseall=form('Reposición liberada',f'{annualreserve}*{hold//12}*{release}',[annualreserve,release])
  for route,withrefi in [('Con refi',True),('Sin refi',False)]:
   name=short+(' Caja refi' if withrefi else ' Caja sin refi');ledger=[['Fecha','Aporte bruto','Cobro bruto','Flujo neto','Base normalización']]
   all_dates=[month(purchase,i) for i in range(0,(sale.year-purchase.year)*12+sale.month-purchase.month+1,3)]
   net_sale=f'{saleprice}-{salecost}-'+(f"'{L}'!E{hold//3+1}+{perres}*{permrelease}" if withrefi else f'{payoff}+MAX(0,{free}-{holdfee})')+f'+{releaseall}'
   for j,day in enumerate(all_dates):
    r=j+2;call=[];receipt=[]
    if day in dates:call.append(f"'{K}'!G{dates.index(day)+2}")
    if day==stable:
     call.append(f'MAX(0,-{refinet})' if withrefi else f'MAX(0,{holdfee}-{free})')
     if withrefi:receipt.append(f'MAX(0,{refinet})')
    if stable<day<=sale:
     idx=((day.year-stable.year)*12+day.month-stable.month)//3+1
     operating=f"'{O}'!{'F' if withrefi else 'H'}{idx}"
     call.append(f'MAX(0,-{operating})');receipt.append(f'MAX(0,{operating})')
    if day==sale:call.append(f'MAX(0,-({net_sale}))');receipt.append(f'MAX(0,({net_sale}))')
    ledger.append([str(day),F(f'({"+".join(call) or "0"})*10/{initial}'),F(f'({"+".join(receipt) or "0"})*10/{initial}'),F(f'C{r}-B{r}'),F(initial)])
   sheets[name]=ledger;n=len(ledger)
   summary.append([scenario,route,F(f"SUM('{name}'!B2:B{n})"),F(f"SUM('{name}'!C2:C{n})"),F(f"MAX(0,SUM('{name}'!B2:B{n})-SUM('{name}'!C2:C{n}))"),F(f"SUM('{name}'!C2:C{n})/SUM('{name}'!B2:B{n})"),F(f"(1+IRR('{name}'!D2:D{n},0))^4-1")])
  numeric=[ci(k) for k,v in literal.items() if k.startswith('C') and v.get('literal') is not None and _numeric(v['literal'])]
  checked=numeric+constant_refs
  textchecks=','.join(ci(k)+'="'+v['literal'].replace('"','""')+'"' for k,v in literal.items() if k.startswith('C') and isinstance(v.get('literal'),str) and v['literal'] and not _numeric(v['literal']))
  calc[1][1]=F(f'IF(AND(COUNT({",".join(checked)})={len(checked)},{ci("C46")}={cell("C46")},{ci("C47")}={cell("C47")},{textchecks}),1,NA())')
  sheets[C]=calc
  for sheetname in (C,T,K,L,O,short+' Caja refi',short+' Caja sin refi'):
   for row_index,row in enumerate(sheets[sheetname]):
    for column,value in enumerate(row):
     if isinstance(value,dict) and 'formula' in value and not (sheetname==C and row_index==1 and column==1):
      value['formula']=f'IF(IFERROR({guard}=1,FALSE()),{value["formula"]},NA())'
 sheets['Cotejo']=summary
 return xlsx(sheets)


def freeze(package,output):
 output.mkdir(parents=True,exist_ok=False);saved=read_package(package)
 for name in SOURCE_FILES:(output/name).write_bytes(saved[name])
 manifest=dict(schema=SCHEMA,usage='synthetic_fixed_source_only',files={name:sha256(saved[name]).hexdigest() for name in SOURCE_FILES},
  expected_financial_cash={s:{r:sha256(encoded((view if r=='with_refinance' else view['horizon_without_refinance'])['cash_per_usd_10'])).hexdigest() for r in ('with_refinance','without_refinance')} for s,view in json.loads(saved['results.json'])['scenarios'].items()},
  criteria_adopted=False,decision='PENDING')
 (output/'golden_manifest.json').write_bytes(encoded(manifest));return manifest


def run(root,output,*,soffice=None):
 frozen=json.loads((root/'golden_manifest.json').read_bytes())
 for name,h in frozen['files'].items():
  if sha256((root/name).read_bytes()).hexdigest()!=h:raise ValueError('El caso dorado fue modificado: '+name)
 sources=read_source_directory(root,include_reference=True);case=json.loads((root/'case.json').read_bytes())
 output.mkdir(parents=True,exist_ok=False)
 write_package((root/'case.json').read_bytes(),output/'package',current_revision_raw=(root/CURRENT_REVISION_FILE).read_bytes(),**sources)
 saved=read_package(output/'package');result=json.loads(saved['results.json']);audit=verify_package(output/'package',current_revision_raw=saved[CURRENT_REVISION_FILE])
 if audit['vigencia']!='VIGENTE':raise ValueError('No reproduce el caso dorado')
 independent=independently_verify(case,sources,result)
 for scenario,view in result['scenarios'].items():
  for route in ('with_refinance','without_refinance'):
   cash=(view if route=='with_refinance' else view['horizon_without_refinance'])['cash_per_usd_10']
   if sha256(encoded(cash)).hexdigest()!=frozen['expected_financial_cash'][scenario][route]:raise ValueError('Cambio no explicado del caso dorado: '+scenario+route)
 book=workbook(case,sources);(output/'golden_case_tieout.xlsx').write_bytes(book)
 runtime=shutil.which('libreoffice') or shutil.which('soffice')
 report=dict(schema=SCHEMA,case_reproduced=True,independent_source_check=independent,audit=audit,live_workbook_sha256=sha256(book).hexdigest(),
  external_recalculation='PENDING',external_tieout='PENDING',reason='Se requiere motor externo de hoja de cálculo y comparación de sus valores recalculados',
  spreadsheet_runtime_available=runtime is not None,decision='PENDING',deployment_enabled=False)
 if soffice is not None:
  import sys
  command=[sys.executable,str(Path(__file__).with_name('check_golden_excel_D275.py')),'--book',str((output/'golden_case_tieout.xlsx').resolve()),'--results',str((output/'package/results.json').resolve()),'--soffice',str(soffice.resolve()),'--output',str((output/'external-excel').resolve())]
  process=subprocess.run(command,capture_output=True,text=True,timeout=600)
  (output/'external-excel.log').write_text(process.stdout+process.stderr)
  if process.returncode!=0:raise ValueError('El cotejo externo del caso dorado falló; ver external-excel.log')
  external=json.loads((output/'external-excel/validation.json').read_bytes())
  report.update(external_recalculation='passed',external_tieout='passed',external_compared_cells=external['cases']['baseline']['comparison']['compared_cells'],external_validation_sha256=sha256((output/'external-excel/validation.json').read_bytes()).hexdigest(),reason=None,spreadsheet_runtime_available=True)
 (output/'validation.json').write_bytes(encoded(report));return report


def main():
 p=ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','run']);p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--soffice',type=Path);a=p.parse_args()
 x=freeze(a.input,a.output) if a.command=='freeze' else run(a.input,a.output,soffice=a.soffice);print(json.dumps({k:v for k,v in x.items() if k not in ('independent_source_check','files','expected_financial_cash','audit')}))
if __name__=='__main__':main()
