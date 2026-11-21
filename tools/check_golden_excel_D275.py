"""Independent spreadsheet recalculation, line-by-line comparison and mutations."""
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from io import BytesIO
from fractions import Fraction as Q
from hashlib import sha256
import json,os,subprocess
from worksheet_frontiers_D275 import fraction,rational

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'


def read_cells(raw):
 with ZipFile(BytesIO(raw)) as z:
  strings=[]
  if 'xl/sharedStrings.xml' in z.namelist():
   for si in ET.fromstring(z.read('xl/sharedStrings.xml')):strings.append(''.join(v.text or '' for v in si.iter('{'+M+'}t')))
  links={v.get('Id'):v.get('Target') for v in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
  result={}
  for sheet in ET.fromstring(z.read('xl/workbook.xml')).iter('{'+M+'}sheet'):
   target=links[sheet.get('{'+REL+'}id')];path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
   cells={}
   for c in ET.fromstring(z.read(path)).iter('{'+M+'}c'):
    v=c.find('{'+M+'}v');value=None if v is None else v.text
    if c.get('t')=='s' and value is not None:value=strings[int(value)]
    elif c.get('t')=='inlineStr':value=''.join(v.text or '' for v in c.iter('{'+M+'}t'))
    elif c.get('t')=='e':value={'error':value}
    elif value is not None and c.get('t') not in ('str','b'):
     try:value=Q(value)
     except ValueError:pass
    cells[c.get('r')]=value
   result[sheet.get('name')]=cells
 return result


def compare(raw,result,tolerances):
 tol={k:fraction(tolerances.get(k)) for k in ('usd_per_initial10','project_usd','multiple','annual_irr')}
 if any(v<0 for v in tol.values()):raise ValueError('Tolerancia negativa')
 cells=read_cells(raw);checks=[]
 def check(locator,actual,expected,tolerance):
  try:
   if isinstance(actual,bool) or not isinstance(actual,(int,Q)):raise ValueError('Resultado recalculado no numérico')
   value=fraction(actual)
   if isinstance(expected,dict) and 'lower' in expected:lo,hi=fraction(expected['lower']),fraction(expected['upper'])
   else:lo=hi=fraction(expected)
   passed=lo-tolerance<=value<=hi+tolerance
   checks.append(dict(locator=locator,state='MATCH' if passed else 'DIFFERENCE',actual=rational(value),expected_interval=dict(lower=rational(lo),upper=rational(hi)),tolerance=rational(tolerance)))
  except (ValueError,TypeError,ZeroDivisionError):checks.append(dict(locator=locator,state='PENDING',actual=None,reason='Falta valor numérico recalculado; no se interpreta como cero'))
 for row,(scenario,route) in enumerate([(s,r) for s in ('Base','Downside') for r in ('with_refinance','without_refinance')],2):
  view=result['scenarios'][scenario];data=view if route=='with_refinance' else view['horizon_without_refinance'];cash=data['cash_per_usd_10'];short='B' if scenario=='Base' else 'D'
  fields={'C':'total_contributions','D':'total_distributions','E':'unrecovered_after_sale','F':'equity_multiple'}
  for col,key in fields.items():check('Cotejo!'+col+str(row),cells['Cotejo'].get(col+str(row)),cash[key],tol['multiple' if col=='F' else 'usd_per_initial10'])
  irr=(result['screening']['irr_by_scenario'][scenario] if route=='with_refinance' else data['irr'])['annual_enclosure']
  check('Cotejo!G'+str(row),cells['Cotejo'].get('G'+str(row)),irr,tol['annual_irr'])
  ledger=short+(' Caja refi' if route=='with_refinance' else ' Caja sin refi');net={}
  for e in cash['events']:
   group=net.setdefault(e['date'],dict(contribution=Q(),distribution=Q()));group[e['kind']]+=fraction(e['amount'])
  rows=sorted(int(k[1:]) for k in cells[ledger] if k.startswith('A') and k[1:].isdigit() and int(k[1:])>1)
  observed_dates=[]
  for r in rows:
   day=cells[ledger]['A'+str(r)];observed_dates.append(day)
   for col,kind in [('B','contribution'),('C','distribution')]:check(ledger+'!'+col+str(r),cells[ledger].get(col+str(r)),net.get(day,{}).get(kind),tol['usd_per_initial10'])
  if observed_dates!=sorted(net):checks.append(dict(locator=ledger,state='DIFFERENCE',reason='Fechas de caja incompletas o diferentes'))
 for scenario in ('Base','Downside'):
  view=result['scenarios'][scenario];short='B' if scenario=='Base' else 'D'
  cols={'B':'project_uses','C':'loan_draw','D':'interest_paid','E':'origination_fee_paid','F':'opening_free_cash','G':'equity_contribution','H':'closing_free_cash'}
  for r,row in enumerate(view['construction_financing']['cash_by_date'],2):
   if cells[short+' Obra'].get('A'+str(r))!=row['date']:checks.append(dict(locator=short+' Obra!A'+str(r),state='DIFFERENCE',reason='Fecha de obra distinta'))
   for col,key in cols.items():check(short+' Obra!'+col+str(r),cells[short+' Obra'].get(col+str(r)),row[key],tol['project_usd'])
  for r,row in enumerate(view['permanent_loan']['projected_schedule'],2):
   for col,key in [('B','opening_balance'),('C','interest_due'),('D','principal_due'),('E','closing_balance'),('F','balloon_due'),('G','scheduled_plus_balloon_due')]:check(short+' Permanente!'+col+str(r),cells[short+' Permanente'].get(col+str(r)),row.get(key),tol['project_usd'])
  for route,letter in [('with_refinance','F'),('without_refinance','H')]:
   data=view['holding_horizon'] if route=='with_refinance' else view['horizon_without_refinance'];scale=fraction(view['cash_per_usd_10']['scale_factor'])
   rows=[p for y in data['annual_cash'] for p in y['payments']]
   for r,pay in enumerate(rows,2):
    expected=(fraction(pay['receipt'])-fraction(pay['contribution']))/scale
    check(short+' Operacion!'+letter+str(r),cells[short+' Operacion'].get(letter+str(r)),expected,tol['project_usd'])
  model=cells[short+' Calculo'];labels={v:int(k[1:]) for k,v in model.items() if k.startswith('A') and k[1:].isdigit() and isinstance(v,str)}
  for label,expected in [('TDC integrado',result['screening']['metric_evidence_by_scenario'][scenario]['cost_basis']['tdc']),('Precio venta',view['valuation_and_sale']['gross_sale_price'])]:
   r=labels[label];check(short+' Calculo!B'+str(r),model.get('B'+str(r)),expected,tol['project_usd'])
 return dict(state='MATCH' if all(c['state']=='MATCH' for c in checks) else 'PENDING',checks=checks,compared_cells=len(checks),
  mismatches=sum(c['state']=='DIFFERENCE' for c in checks),missing_values=sum(c['state']=='PENDING' for c in checks),
  real_decision='PENDING',criteria_adopted=False)


def mutate(raw,mode):
 result=BytesIO()
 with ZipFile(BytesIO(raw)) as src,ZipFile(result,'w') as dst:
  for info in src.infolist():
   data=src.read(info.filename)
   if info.filename=='xl/worksheets/sheet2.xml':
    root=ET.fromstring(data);target='C53' if mode=='explicit_zero' else 'C8';found=False
    for row in root.iter('{'+M+'}row'):
     for cell in list(row):
      if cell.get('r')==target:
       found=True
       if mode=='blank':row.remove(cell)
       else:
        v=cell.find('{'+M+'}v');v.text='0' if mode=='explicit_zero' else str(float(Q(v.text)*Q(101,100)))
    if not found:raise ValueError('No se encontró la celda fuente a mutar')
    data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
   dst.writestr(info,data)
 return result.getvalue()


def recalculate(executable,book,output):
 output.mkdir(parents=True,exist_ok=False)
 version=subprocess.run([str(executable),'--headless','--version'],capture_output=True,text=True,timeout=30,check=True).stdout.strip()
 process=subprocess.run([str(executable),'--headless','--norestore','--convert-to','xlsx:Calc MS Excel 2007 XML','--outdir',str(output),str(book)],capture_output=True,text=True,timeout=120,check=True)
 (output/'conversion.log').write_text(process.stdout+process.stderr)
 p=output/book.name
 if not p.is_file():raise ValueError('El motor externo no generó el archivo recalculado')
 return p.read_bytes(),dict(engine=version,executable=str(executable),input_sha256=sha256(book.read_bytes()).hexdigest(),recalculated_sha256=sha256(p.read_bytes()).hexdigest())


def main():
 p=ArgumentParser(description=__doc__);p.add_argument('--book',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--soffice',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False);result=json.loads(a.results.read_bytes());original=a.book.read_bytes()
 tolerances=dict(usd_per_initial10='0.01',project_usd='0.01',multiple='0.000001',annual_irr='0.0001')
 records={}
 for mode in ('baseline','changed','blank','explicit_zero'):
  source=a.output/(mode+'.xlsx');source.write_bytes(original if mode=='baseline' else mutate(original,mode))
  raw,receipt=recalculate(a.soffice,source,a.output/(mode+'-recalculated'));checked=compare(raw,result,tolerances)
  if mode=='baseline' and checked['state']!='MATCH':raise ValueError('El cotejo independiente no cierra: '+json.dumps([v for v in checked['checks'] if v['state']!='MATCH'][:8]))
  if mode in ('changed','blank','explicit_zero') and checked['state']=='MATCH':raise ValueError('La alteración no fue detectada: '+mode)
  if mode=='blank' and checked['missing_values']==0:raise ValueError('El vacío no quedó bloqueado')
  if mode=='explicit_zero' and checked['missing_values']!=0:raise ValueError('El cero explícito válido fue tratado como dato ausente')
  records[mode]=dict(recalculation=receipt,comparison=checked)
 report=dict(status='passed',synthetic_only=True,tolerances=tolerances,cases=records,real_decision='PENDING',deployment_enabled=False)
 (a.output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status='passed',baseline_compared_cells=records['baseline']['comparison']['compared_cells'],mutations_detected=3)))
if __name__=='__main__':main()
