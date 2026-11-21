"""Replay frozen v2 and test current-only delivery with real source reads."""
from pathlib import Path
from copy import deepcopy
import json
from hashlib import sha256
from argparse import ArgumentParser
from miniuw_worksheet_v1 import encoded,read_package,verify_package,deliver_package,CURRENT_REVISION_FILE
from worksheet_intake_D198 import assemble,register,read_source_directory,source_inventory
from worksheet_monthly_native_D276 import REFERENCE_SCHEMA
from worksheet_variant_evidence_D268 import inputs_digest
from check_monthly_native_D276 import set_numeric_cells
from check_monthly_oracle_D276 import verify

ROOT=Path(__file__).resolve().parents[1]


def refreshed(spec,sources):
 out=dict(sources);out['independent_reference_raw']=encoded(dict(schema=REFERENCE_SCHEMA,inputs_sha256=inputs_digest(spec['rent_inputs']),deal_id=spec['rent_inputs']['deal_id'],local_revision=spec['local_sources']['revision'],sources={source_inventory(out)[k]:sha256(v).hexdigest() for k,v in out.items() if k!='independent_reference_raw'}));return out


def run(output):
 output=Path(output);output.mkdir(parents=True,exist_ok=True);fixture=ROOT/'templates/golden_case_v2';spec=json.loads((fixture/'settings.json').read_bytes());sources=read_source_directory(fixture,include_reference=True);receipts={}
 def case(label,settings,raw):
  directory=output/label
  if not directory.exists():assemble(settings,register(raw,'SYNTHETIC-D276-'+label),raw,directory)
  saved=read_package(directory)
  (output/(label+'-current-revision.json')).write_bytes(saved[CURRENT_REVISION_FILE]);result=json.loads(saved['results.json']);audit=verify_package(directory,current_revision_raw=saved[CURRENT_REVISION_FILE]);receipts[label]=dict(case_sha256=sha256(saved['case.json']).hexdigest(),results_sha256=sha256(saved['results.json']).hexdigest(),audit=audit);print(label,audit['critical_evidence']['status'],flush=True);return result,saved
 result,saved=case('current',spec,sources);proof=verify(spec,sources,result);expected=json.loads((fixture/'expected_financials.json').read_bytes());assert proof['observations']==expected;(output/'independent-oracle.json').write_bytes(encoded(proof));receipts['independent_oracle']=proof['checks'];delivery=deliver_package(output/'current',output/'current.pdf',output/'current-current-revision.json');receipts['current_delivery']=delivery
 bad=dict(sources);bad['downside_workbook_raw']=set_numeric_cells(bad['downside_workbook_raw'],{'C14':'0.45'});bad=refreshed(spec,bad);limited,lim_saved=case('capacity',spec,bad);assert limited['scenarios']['Downside']['with_refinance']['cash_per_usd_10'] is None;assert limited['scenarios']['Downside']['horizon_without_refinance']['cash_per_usd_10'] is not None;receipts['capacity_delivery']=deliver_package(output/'capacity',output/'capacity.pdf',output/'capacity-current-revision.json')
 try:deliver_package(output/'current',output/'stale-must-not-exist.pdf',output/'capacity-current-revision.json')
 except ValueError as err:receipts['stale_blocked']=str(err)
 else:raise AssertionError('Stale PDF delivered')
 assert not (output/'stale-must-not-exist.pdf').exists()
 missing=dict(sources);missing['workbook_raw']=set_numeric_cells(missing['workbook_raw'],{'C59':None});missing=refreshed(spec,missing);blocked,empty_saved=case('missing',spec,missing);assert blocked['scenarios']['Base']['cash_per_usd_10'] is None
 try:deliver_package(output/'missing',output/'missing-must-not-exist.pdf',output/'missing-current-revision.json')
 except ValueError as err:receipts['missing_blocked']=str(err)
 else:raise AssertionError('Missing source PDF delivered')
 assert not (output/'missing-must-not-exist.pdf').exists()
 v1=ROOT/'templates/golden_case_v1';manifest=json.loads((v1/'golden_manifest.json').read_bytes());records=manifest.get('files',{})
 for name,record in records.items():
  h=record if isinstance(record,str) else record['sha256'];assert sha256((v1/name).read_bytes()).hexdigest()==h,name
 receipts.update(state='PASSED',frozen_v1_unchanged=True,criteria_adopted=False,deployment_enabled=False,real_decision='PENDING',historical_return='PENDING');(output/'validation.json').write_bytes(encoded(receipts));print('SOURCE + DELIVERY ACCEPTANCE PASSED',flush=True)
 return receipts

if __name__=='__main__':
 p=ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
