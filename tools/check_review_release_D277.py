"""Reproduce the D277 synthetic reference, analyses and current-only PDF gates."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import json
from worksheet_intake_D198 import assemble,register,read_source_directory,prepare
from miniuw_worksheet_v1 import encoded,read_package,CURRENT_REVISION_FILE
from worksheet_decision_page_D277 import deliver,render
from worksheet_monthly_analysis_D277 import request,ASKING
from worksheet_review_controls_D275 import empty_roles
from check_monthly_oracle_D276 import verify
from worksheet_frontiers_D275 import rational as R,digest
from worksheet_cash_attribution_D277 import reconcile_case
ROOT=Path(__file__).resolve().parents[1]


def execute(output,fixture=None):
 out=Path(output);out.mkdir(parents=True,exist_ok=False);fixture=Path(fixture or ROOT/'templates/golden_case_v3');spec=json.loads((fixture/'settings.json').read_bytes());sources=read_source_directory(fixture,include_reference=True);assemble(spec,register(sources,'SYNTHETIC-D277-CURRENT'),sources,out/'package');saved=read_package(out/'package');result=json.loads(saved['results.json']);case=json.loads(saved['case.json']);proof=verify(case,sources,result);assert proof['observations']==json.loads((fixture/'expected_financials.json').read_bytes());(out/'oracle.json').write_bytes(encoded(proof));current=out/'current_revision.json';current.write_bytes(saved[CURRENT_REVISION_FILE]);raw=saved['case.json'];note=dict(schema=ASKING,usage='synthetic_review_assumption',case_sha256=sha256(raw).hexdigest(),workbooks={s:sha256(sources[k]).hexdigest() for s,k in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]},price=R(1600000),currency='USD',source_ref='SYNTHETIC-D277-explicit-authored-asking-note',date='2026-11-21',scope='Authored new v3 asking, not a market observation; evaluated C32 is separately preserved');analysis=out/'analysis_request.json';analysis.write_bytes(encoded(request(raw,sources,note)));page=out/'MiniUW_Resultado_Una_Pagina_D277.pdf';receipt=deliver(out/'package',page,current,analysis,empty_roles());again,fields=render(receipt['view']);assert again==page.read_bytes() and fields==receipt['rendered_fields'];(out/'delivery.json').write_bytes(encoded(receipt));(out/'analysis.json').write_bytes(encoded(receipt['view']['analyses']));attribution=reconcile_case(result);assert all(v['prefix']['state']=='PASSED' for v in attribution['scenarios'].values());(out/'attribution.json').write_bytes(encoded(attribution));blocked=[]
 stale=out/'obsolete_revision.json';record=json.loads(current.read_bytes());record['local_revision']='SYNTHETIC-OBSOLETE-D277';stale.write_bytes(encoded(record))
 for kind,current_path,claimed_analysis in [('stale',stale,None),('manual_analysis',current,dict(claimed='green'))]:
  destination=out/('BLOCKED-'+kind+'.pdf')
  try:deliver(out/'package',destination,current_path,claimed_analysis,empty_roles());raise AssertionError('Unsafe PDF delivered: '+kind)
  except ValueError:assert not destination.exists();blocked.append(kind)
 before=(out/'package/results.json').read_bytes();destination=out/'BLOCKED-edited-financials.pdf'
 try:
  (out/'package/results.json').write_bytes(before+b' ')
  try:deliver(out/'package',destination,current,None,empty_roles());raise AssertionError('Edited results delivered')
  except ValueError:assert not destination.exists();blocked.append('edited_financial_results')
 finally:(out/'package/results.json').write_bytes(before)
 for s in ('Base','Downside'):
  for d,routes in receipt['view']['analyses']['breakeven_matrix'][s]['with_refinance'].items():
   for f,record in routes.items():
    if record['state']=='PENDING':assert record.get('visible_reason'),(s,d,f)
  for record in receipt['view']['analyses']['tornado']['tornado'][s]['with_refinance']:
   if record['state']=='PENDING':assert record.get('visible_reason')
 proof_summary=dict(state='PASSED',independent_checks=proof['checks'],current_pdf_sha256=receipt['pdf_sha256'],rendered_fields=len(fields),blocked_deliveries=blocked,initial_equity_normalization=10,all_gross_cash_unchanged=True,criteria_adopted=False,real_decision='PENDING',deployment_enabled=False);(out/'validation.json').write_bytes(encoded(proof_summary));print(json.dumps(proof_summary),flush=True);return proof_summary

if __name__=='__main__':
 import sys
 execute(Path(sys.argv[1]))
