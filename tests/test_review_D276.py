from unittest import TestCase
from copy import deepcopy
import json
from hashlib import sha256
from fractions import Fraction as Q
from worksheet_frontiers_D275 import digest,rational
from worksheet_decision_page_D275 import shared_gsf,certified_irr_display,render
from worksheet_review_findings_D276 import findings,SCHEMA
from miniuw_foundation.lorena_screening import BASES
from test_worksheet_decision_page import view
from pypdf import PdfReader
from io import BytesIO

class PresentationReviewTests(TestCase):
 def test_certified_irr_rounded_to_one_decimal_without_choosing_a_root(self):
  self.assertEqual(certified_irr_display({'lower':rational(Q(17525,100000)),'upper':rational(Q(17526,100000))}),'17,5 %')
  self.assertEqual(certified_irr_display(None),'PENDING · raíz')
 def test_crossing_a_rounding_boundary_keeps_the_certified_range(self):
  self.assertEqual(certified_irr_display({'lower':'0.17549','upper':'0.17551'}),'17,5–17,6 %')
 def test_same_building_area_requires_both_declarations_and_plan_binding(self):
  source=dict(groups={'A':{'units':2,'rentable_sf_per_unit':'10'}},commercial={'uses':{'retail':{'applies':True,'rentable_sf':'12'}}},development={'scenarios':{s:{'plan_gsf':{'state':'declared','value':'100','source_ref':'SYNTHETIC-plan'}} for s in ('Base','Downside')}})
  data={s:{'document_financial_binding':{'state':'checked_synthetic','blockers':[],'verified_area_gsf':'100'}} for s in ('Base','Downside')}
  self.assertEqual(shared_gsf(source,data),rational(100))
  for fault in ('missing','different','unverified','too_small'):
   a,b=deepcopy(source),deepcopy(data)
   if fault=='missing':a['development']['scenarios']['Base']['plan_gsf'].update(state='TBD',value=None)
   elif fault=='different':a['development']['scenarios']['Downside']['plan_gsf']['value']='101'
   elif fault=='unverified':b['Base']['document_financial_binding']['state']='PENDING'
   else:
    for s in ('Base','Downside'):a['development']['scenarios'][s]['plan_gsf']['value']='30';b[s]['document_financial_binding']['verified_area_gsf']='30'
   self.assertIsNone(shared_gsf(a,b),fault)
 def test_unit_count_is_integer_and_spread_has_bps(self):
  a=view();a['scenario']['Base']['units']=26
  raw,fields=render(a);text=PdfReader(BytesIO(raw)).pages[0].extract_text();self.assertIn('26 unidades',text);self.assertIn('Spread (bps)',text)
 def test_missing_shared_area_never_becomes_zero(self):
  a=view();raw,fields=render(a);gsf=[x for x in fields if x['path']=='scenario/Base/gsf'];self.assertEqual(gsf[0]['display'],'PENDING')


def comparisons():return [dict(scenario=s,metric_id=m,state='FAIL_SIMULATED' if m in ('YoC','spread') else 'PASS_SIMULATED') for s in ('Base','Downside') for m in BASES]

def cause(rows,scenario='Base'):
 declaration=dict(schema=SCHEMA,scenario=scenario,metric_ids=['YoC','spread'],criteria_revision='SYNTHETIC-R1',common_cause_proved=True,cause_id='SYNTHETIC-common-NOI',source_ref='SYNTHETIC-review-causal-record',comparison_sha256=digest([r for m in ('YoC','spread') for r in rows if r['scenario']==scenario and r['metric_id']==m]))
 raw=json.dumps(declaration,sort_keys=True).encode();h=sha256(raw).hexdigest();return dict(scenario=scenario,declaration=declaration,source=dict(sha256=h,locator='case/NOI-and-TDC-lineage')), {h:raw}

class FindingsReviewTests(TestCase):
 def test_common_cause_is_one_finding_but_both_criteria_remain_failed(self):
  rows=comparisons();record,docs=cause(rows);old=deepcopy(rows);out=findings(rows,[record],docs,'SYNTHETIC-R1')
  self.assertEqual(out['counts']['Base']['failing_metrics'],2);self.assertEqual(out['counts']['Base']['review_findings'],1);self.assertEqual(out['comparisons'],old);self.assertEqual(rows,old);self.assertTrue(out['all_applicable_criteria_preserved'])
 def test_without_causal_evidence_do_not_suppress_independent_failures(self):
  rows=comparisons();out=findings(rows,[],{},'SYNTHETIC-R1');self.assertEqual(out['counts']['Base']['review_findings'],2)
 def test_altered_or_stale_cause_does_not_group(self):
  rows=comparisons();record,docs=cause(rows)
  for fault in ('no_source','stale_revision','changed_comparison'):
   data=deepcopy(rows);documents={} if fault=='no_source' else docs;rev='SYNTHETIC-R2' if fault=='stale_revision' else 'SYNTHETIC-R1'
   if fault=='changed_comparison':next(r for r in data if r['scenario']=='Base' and r['metric_id']=='YoC')['extra']='changed'
   out=findings(data,[record],documents,rev);self.assertEqual(out['counts']['Base']['review_findings'],2);self.assertEqual(len(out['unproved_causes']),1)
 def test_one_pass_is_not_hidden_inside_a_common_fail(self):
  rows=comparisons();next(r for r in rows if r['scenario']=='Base' and r['metric_id']=='YoC')['state']='PASS_SIMULATED';record,docs=cause(rows);out=findings(rows,[record],docs,'SYNTHETIC-R1');self.assertEqual(out['counts']['Base']['review_findings'],1);self.assertEqual(out['findings'][0]['kind'],'INDIVIDUAL')
 def test_missing_comparisons_are_not_zero_findings(self):
  for rows in (None,[],comparisons()[:-1]):
   out=findings(rows,[],{},'SYNTHETIC-R1');self.assertEqual(out['state'],'PENDING');self.assertIsNone(out['counts'])
 def test_explicit_pending_metrics_stay_pending(self):
  rows=[r|dict(state='PENDING') for r in comparisons()];out=findings(rows,[],{},None);self.assertEqual(out['counts']['Base']['pending_metrics'],10);self.assertEqual(out['decision'],'PENDING')

class FindingsPlugIntegrationTests(TestCase):
 def test_plug_groups_causes_without_altering_finance_or_joint_rlv(self):
  from worksheet_criteria_plug_D275 import apply,SCHEMA as PLUG,UNITS
  snapshot={'computed_metrics':{s:{m:dict(value='0',basis=BASES[m],unit=UNITS[m],period_ref='SYNTHETIC-period') for m in BASES} for s in ('Base','Downside')},'scenarios':{'cash':'unchanged'}}
  config=dict(schema=PLUG,usage='synthetic_plug_test_only',criteria_adopted=False,revision='SYNTHETIC-R1',valid_from='2026-01-01',valid_until='2027-12-31',rules=[dict(scenario=s,metric_id=m,unit=UNITS[m],basis=BASES[m],period_ref='SYNTHETIC-period',source_ref='SYNTHETIC-rule',applicability='applicable',**{'pass':{'operator':'>=','threshold':'1'},'fail':{'operator':'<','threshold':'1'}}) for s in ('Base','Downside') for m in BASES],house_rlv_definition={'all_applicable_criteria_jointly':True})
  baseline=apply(snapshot,config,'2026-11-21');record,docs=cause(baseline['criteria_comparisons']);x=apply(snapshot,config,'2026-11-21',common_causes=[record],causal_documents=docs)
  self.assertEqual(x['financial_snapshot_sha256'],baseline['financial_snapshot_sha256']);self.assertEqual(x['criteria_comparisons'],baseline['criteria_comparisons']);self.assertEqual(x['review_findings']['counts']['Base']['failing_metrics'],10);self.assertEqual(x['review_findings']['counts']['Base']['review_findings'],9);self.assertEqual(x['house_rlv']['state'],'PENDING')
