"""Recompute analytical views from audited source packets, not saved claims."""
from pathlib import Path
from fractions import Fraction as Q
import json
from copy import deepcopy
from check_worksheet_frontiers_D275 import AuditedSourceRuns
from check_worksheet_scenario_program_D268 import independently_verify,source_cells
from worksheet_scenario_program_D268 import unchanged_support
from worksheet_frontiers_D275 import DRIVERS,matrix,rational,fraction,digest
from worksheet_tornado_D275 import tornado
from worksheet_user_price_D275 import grid,SCHEMA as PRICE,RULE as PRICE_RULE
from worksheet_intake_D198 import read_source_directory
from worksheet_variant_evidence_D268 import inputs_digest
from miniuw_worksheet_v1 import encoded,read_package,verify_package,CURRENT_REVISION_FILE
from miniuw_foundation.scheduled_expense_case import sha


def key(driver,movement):return 'baseline' if movement==0 else driver+'-'+str(movement).replace('/','_').replace('-','m')

def validate_changes(base,sources,spec,current,driver,movement):
 for scenario,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
  old,read=source_cells(sources,scenario);new,now=source_cells(current,scenario)
  if old.keys()!=new.keys():raise ValueError('Cambió el inventario de celdas durante una sensibilidad')
  allowed=set() if movement==0 else set(DRIVERS[driver]['cells'])
  for cell in old:
   if cell not in allowed:
    if old[cell]!=new[cell]:raise ValueError('Se alteró una celda no declarada: '+cell)
   else:
    before=read(cell)
    if driver=='residential_rent':expected=before*(1-movement)
    elif driver=='vertical_cost':expected=before*(1+movement)
    else:expected=before+movement/({'bps':10000,'months':1,'percentage_points':100}[DRIVERS[driver]['unit']])
    if now(cell)!=expected:raise ValueError('Shock no coincide con la celda fuente: '+cell)
  # Source ranges for the counterfactual are new labelled synthetic documents.
 before=unchanged_support(base['rent_inputs']);after=unchanged_support(spec['rent_inputs'])
 for scenario in ('Base','Downside'):
  if driver in ('residential_rent','exit_cap') and movement:
   role='rent' if driver=='residential_rent' else 'exit_cap'
   for obj in (before,after):obj['market_evidence']['scenarios'][scenario].pop(role)
 if before!=after:raise ValueError('Se cambiaron deuda fija, programa, presupuesto, criterios u otros términos no declarados')


def price_source(spec,sources,result,scenario,record):
 _,read=source_cells(sources,scenario);v=result['scenarios'][scenario];cash=v.get('cash_per_usd_10')
 if cash is None:return None
 scale=fraction(cash['scale_factor']);cost=result['screening']['metric_evidence_by_scenario'][scenario]['cost_basis'];evidence=result['screening']['metric_evidence_by_scenario'][scenario]['candidate_definitions']['YoC']
 events=[dict(id=e['event_id'],date=e['date'],kind=e['kind'],amount=rational(fraction(e['amount'])/scale),source_ref=e['source_ref']) for e in cash['events']]
 if len(cash['basis_event_ids'])!=1:raise ValueError('La grilla requiere una contribución inicial verificable única')
 return dict(schema=PRICE,rule=PRICE_RULE,source_check='INDEPENDENTLY_VERIFIED',source_ref='SYNTHETIC-D275-source-replayed-price-'+scenario,
  source_sha256=record['results_sha256'],purchase_price=rational(read('C32')),closing_fraction=rational(read('C33')),tdc=cost['tdc'],applied_equity=cost['applied_equity'],
  fixed_debt=cost['components']['loan_draw'],noi_uw=evidence['noi_after_reserve'],gross_events=events,initial_event_id=cash['basis_event_ids'][0],dates=v['project_calendar']['equity_dates'])


def replay(report_path):
 report_path=Path(report_path);raw=json.loads(report_path.read_bytes());source_root=(report_path.parent/'source-runs').resolve()
 records=raw.get('runs')
 if not isinstance(records,list) or not records:raise ValueError('No hay expedientes de las sensibilidades para auditar')
 native=AuditedSourceRuns.__new__(AuditedSourceRuns);native.root=source_root;native.cache={};native.initial={};native.failures={};native.runs=[]
 base_entry=None;audits=[];point_identities={}
 for rec in records:
  path=Path(rec['source_directory']).resolve()
  if path.parent!=source_root or path.is_symlink():raise ValueError('Fuente de sensibilidad fuera del expediente')
  saved=read_package(path/'package');result=json.loads(saved['results.json']);case=json.loads(saved['case.json']);spec=json.loads((path/'settings.json').read_bytes());sources=read_source_directory(path,include_reference=True)
  for filename,field in [('case.json','case_sha256'),('results.json','results_sha256')]:
   if sha(saved[filename])!=rec[field]:raise ValueError('Huellas de caso / resultado alteradas')
  if inputs_digest(spec['rent_inputs'])!=inputs_digest(case['rent_inputs']):raise ValueError('Los settings de la referencia discrepan de los inputs ejecutados')
  source_hash=sha(encoded({k:sha(v) for k,v in sorted(sources.items()) if v is not None}))
  if source_hash!=rec['sources_sha256']:raise ValueError('Se modificaron fuentes de la sensibilidad')
  audit=verify_package(path/'package',current_revision_raw=saved[CURRENT_REVISION_FILE])
  if audit['vigencia']!='VIGENTE' or result['critical_evidence_review']['status']!='PASSED':raise ValueError('Falso verde, evidencia pendiente o revisión antigua: bloquear análisis')
  independently_verify(spec,sources,result)
  hashes={k:rec[k] for k in ('case_sha256','results_sha256','sources_sha256','independent_reference_sha256')}
  entry=(spec,sources,result,hashes);native.cache[rec['id']]=entry
  if rec['id']=='baseline':base_entry=entry;point_identities[rec['id']]=('residential_rent',Q())
  else:
   driver,m=rec['id'].rsplit('-',1);movement=-Q(m[1:].replace('_','/')) if m.startswith('m') else Q(m.replace('_','/'))
   if driver not in DRIVERS or rec['id']!=key(driver,movement):raise ValueError('Identidad de driver / movimiento inválida')
   point_identities[rec['id']]=(driver,movement)
  audits.append(dict(id=rec['id'],case_sha256=rec['case_sha256'],results_sha256=rec['results_sha256'],vigencia=audit['vigencia'],independent_check='PASSED'))
 if base_entry is None:raise ValueError('Falta el caso original de las sensibilidades')
 for name,entry in native.cache.items():validate_changes(base_entry[0],base_entry[1],entry[0],entry[1],*point_identities[name])
 # Never generate new evidence during an audit. Missing points remain PENDING.
 def cached(driver,movement):
  entry=native.cache.get(key(driver,movement))
  if entry is None:raise ValueError('Falta expediente fuente auditado para este movimiento')
  return entry
 native.replay=cached
 rebuilt=matrix(raw['configuration'],native)
 rebuilt['tornado']=tornado(raw['tornado_configuration'],native)
 rebuilt['audited_source_points']=audits
 rebuilt['price_grid']={}
 for scenario in ('Base','Downside'):
  source=price_source(*base_entry[:3],scenario,base_entry[-1])
  if source is None:rebuilt['price_grid'][scenario]=dict(state='PENDING',reason='Falta caja base');continue
  p=fraction(source['purchase_price']);configuration=dict(schema=PRICE,source_ref='SYNTHETIC-D275-user-math-target-EM1-not-Lorena',lower=rational(p*Q(8,10)),upper=rational(p*Q(12,10)),step=rational(p/10),user_targets=dict(equity_multiple=dict(operator='>=',value='1')))
  value=grid(source,configuration)
  # Independent affine checks at both ends, from original C32/C33 and the
  # gross dated basis whose literal-source oracle was checked above.
  original_calls=sum((fraction(e['amount']) for e in source['gross_events'] if e['kind']=='contribution'),Q())
  original_receipts=sum((fraction(e['amount']) for e in source['gross_events'] if e['kind']=='distribution'),Q())
  for row in (value['price_grid'][0],value['price_grid'][-1]):
   if row['state']!='CALCULATED':raise ValueError('Punto de grilla no calculado')
   change=(fraction(row['price'])-p)*(1+fraction(source['closing_fraction']))
   if fraction(row['tdc'])!=fraction(source['tdc'])+change or fraction(row['fixed_debt'])!=fraction(source['fixed_debt']) or fraction(row['values']['equity_multiple'])!=original_receipts/(original_calls+change):raise ValueError('No cierra el verificador afín independiente de precio')
  rebuilt['price_grid'][scenario]=value|dict(configuration=configuration,independent_endpoints_checked=True)
 rebuilt['source_report_sha256']=sha(report_path.read_bytes());rebuilt['baseline_results_sha256']=base_entry[-1]['results_sha256'];rebuilt['state']='SOURCE_REPLAYED';return rebuilt
