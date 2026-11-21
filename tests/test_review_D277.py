"""D277 acceptance: new v3, prior immutable sources, source gates and one page."""
from pathlib import Path
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from hashlib import sha256
from io import BytesIO
import json
from pypdf import PdfReader
from worksheet_frontiers_D275 import fraction as F,digest,rational as R
from worksheet_monthly_native_D276 import build_case,REFERENCE_SCHEMA
from worksheet_intake_D198 import read_source_directory,prepare,register,source_inventory
from worksheet_documented_finance_D147 import review_documents
from worksheet_variant_evidence_D268 import inputs_digest
from check_monthly_oracle_D276 import verify
from worksheet_cash_attribution_D277 import reconcile_case
from worksheet_decision_page_D277 import report_view,render,METRICS
from worksheet_review_controls_D275 import empty_roles
from worksheet_monthly_analysis_D277 import request,asking_price,ASKING,price_analysis
from miniuw_worksheet_v1 import encoded
ROOT=Path(__file__).resolve().parents[1]
class ReviewD277Tests(TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=ROOT/'templates/golden_case_v3';cls.spec=json.loads((cls.fixture/'settings.json').read_bytes());cls.sources=read_source_directory(cls.fixture,include_reference=True);raw,current=prepare(cls.spec,register(cls.sources,'SYNTHETIC-D277-CURRENT'));cls.case=json.loads(raw);cls.raw=raw;cls.current=current;cls.local=review_documents(cls.case,cls.sources['plan_raw'],evidence_raw=cls.sources['evidence_raw'],evidence_milestone='D162');assert not cls.local['blockers'],cls.local['blockers'];cls.result,cls.pdf=cls.run_case(cls.spec);cls.proof=verify(cls.spec,cls.sources,cls.result)
 @classmethod
 def run_case(cls,spec):
  sources=dict(cls.sources);sources['independent_reference_raw']=encoded(dict(schema=REFERENCE_SCHEMA,inputs_sha256=inputs_digest(spec['rent_inputs']),deal_id=spec['rent_inputs']['deal_id'],local_revision=spec['local_sources']['revision'],sources={source_inventory(sources)[k]:sha256(v).hexdigest() for k,v in sources.items() if k!='independent_reference_raw'}));raw,current=prepare(spec,register(sources,'SYNTHETIC-D277-CURRENT'))
  # Memoize extraction ONLY of the identical source PDF bytes; gates rerun.
  with patch('worksheet_monthly_native_D276.review_documents',return_value=deepcopy(cls.local)):return build_case(json.loads(raw),raw,current_revision_raw=current,**sources)
 def note(self,price=1600000):return dict(schema=ASKING,usage='synthetic_review_assumption',case_sha256=sha256(self.raw).hexdigest(),workbooks={s:sha256(self.sources[k]).hexdigest() for s,k in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]},price=R(price),currency='USD',source_ref='SYNTHETIC-D277-test-asking',date='2026-11-21',scope='Authored asking, distinct from evaluated C32')
 def test_all_three_fixtures_are_separate_and_match_their_manifests(self):
  for version in (1,2,3):
   d=ROOT/('templates/golden_case_v'+str(version));manifest=json.loads((d/'golden_manifest.json').read_bytes())
   for name,h in manifest['files'].items():self.assertEqual(sha256((d/name).read_bytes()).hexdigest(),h,name)
 def test_independent_source_oracle_matches_frozen_v3(self):
  self.assertEqual(self.proof['state'],'PASSED');self.assertEqual(self.proof['observations'],json.loads((self.fixture/'expected_financials.json').read_bytes()));self.assertGreater(sum(v['exact_comparisons'] for v in self.proof['checks'].values()),1800)
 def test_v3_is_calibrated_but_does_not_adopt_market_or_criteria(self):
  for s,v in self.result['scenarios'].items():
   self.assertEqual(v['state'],'CALCULATED');tdc=F(v['tdc']);gsf=F(v['document_financial_binding']['verified_area_gsf']);self.assertTrue(300<=tdc/gsf<=450);self.assertTrue(350000<=tdc/26<=500000);m=self.result['computed_metrics'][s];self.assertTrue(F('.065')<=F(m['YoC']['value'])<=F('.075'));self.assertTrue(100<=F(m['spread']['value'])<=150);self.assertTrue(F('.55')<=F(v['construction_financing']['drawn'])/tdc<=F('.65'));self.assertTrue(F('.60')<=F(v['capacity']['requested_principal'])/F(v['refinance_value'])<=F('.65'));self.assertTrue(F('1.25')<=F(v['capacity']['bank_noi'])/F(v['capacity']['annual_service'])<F('1.26'))
  self.assertFalse(self.result['criteria_adopted']);self.assertFalse(self.result['deployment_enabled']);self.assertEqual(self.result['decision'],'PENDING')
 def test_common_gross_cash_is_identical_through_refi(self):
  a=reconcile_case(self.result)
  for s,v in a['scenarios'].items():self.assertEqual(v['prefix']['state'],'PASSED');self.assertEqual(v['with_refinance']['state'],'ATTRIBUTED');self.assertEqual(F(v['with_refinance']['refinance_cash_in']),0)
 def test_source_missing_altered_or_unsuperseded_addendum_blocks(self):
  for fault in ('missing','altered','basis'):
   spec=deepcopy(self.spec);cfg=spec['rent_inputs']['monthly_integration']['scenarios']['Base']
   if fault=='missing':cfg.pop('project_eligibility')
   elif fault=='altered':cfg['project_eligibility']['sha256']='0'*64
   else:spec['rent_inputs']['construction_financing']['rules']['eligible_cost']='direct_hard_excluding_contingency'
   result,_=self.run_case(spec);self.assertIsNone(result['scenarios']['Base']['cash_per_usd_10']);self.assertEqual(result['decision'],'PENDING')
 def test_v3_projects_exact_five_role_draws_and_excludes_financing(self):
  for s,c in self.result['monthly_contracts'].items():
   eligibility=c['construction_eligibility'];self.assertEqual(set(eligibility['roles']),{'land','direct_hard','contingency','soft','ti_lc'});events=[e for p in c['construction']['periods'] for e in p['events'] if e['kind']=='draw'];self.assertEqual(sum(F(e['amount']) for e in events),F(eligibility['total'])*F('0.62'));self.assertTrue(all(e['source_use_id'] and e['eligible_role'] in eligibility['roles'] for e in events));self.assertLess(F(eligibility['total']),F(self.result['scenarios'][s]['tdc']))
 def test_one_page_includes_all_ten_metrics_and_cash_dates(self):
  view=report_view(self.result,self.case,{},empty_roles());pdf,fields=render(view);self.assertEqual(len(PdfReader(BytesIO(pdf)).pages),1);text=PdfReader(BytesIO(pdf)).pages[0].extract_text();self.assertIn('NO VIGENTES',text);self.assertIn('Cash-in / equity',text);self.assertIn('Pedido/soportado',text);self.assertIn('Operación: desde',text)
  for s in ('Base','Downside'):
   for k,*_ in METRICS:self.assertIn(k,view['metrics'][s])
  self.assertIsNone(view['metrics']['Base']['asking_supported']);self.assertIn('PENDING',text)
 def test_asking_is_source_bound_and_not_inferred_from_c32(self):
  note=self.note(1700000);self.assertEqual(asking_price(note,self.raw,self.sources),1700000);self.assertNotEqual(asking_price(note,self.raw,self.sources),1600000);self.assertEqual(request(self.raw,self.sources,note)['asking_note'],note)
  for fault in ('missing','revision','price'):
   n=deepcopy(note)
   if fault=='missing':n.pop('price')
   elif fault=='revision':n['case_sha256']='0'*64
   else:n['price']=None
   with self.assertRaises((ValueError,KeyError,TypeError)):asking_price(n,self.raw,self.sources)
 def test_price_grid_has_21_points_and_exact_center_and_bounds(self):
  p=price_analysis(self.spec,self.sources,self.result,self.proof,1600000)
  for s in p:
   for route,g in p[s].items():
    self.assertEqual(len(g['price_grid']),21);self.assertEqual(F(g['price_grid'][0]['price']),1120000);self.assertEqual(F(g['price_grid'][-1]['price']),2080000);self.assertEqual([i for i,r in enumerate(g['price_grid']) if r['is_asking_price']],[10]);self.assertEqual(F(g['price_grid'][10]['price']),1600000);self.assertEqual(g['house_rlv']['state'],'PENDING');self.assertIn(g['max_price_for_targets']['state'],('BOUNDED','OUTSIDE_RANGE','PENDING'))
    self.assertTrue(all(point['state']=='CALCULATED' for point in g['price_grid']))
    if g['max_price_for_targets']['state']=='OUTSIDE_RANGE':self.assertIsNone(g['max_price_for_targets']['price'])
 def test_shock_keeps_fixed_loan_and_no_refi_when_capacity_blocks(self):
  from worksheet_monthly_experiments_D276 import evaluate
  out=evaluate(self.spec,self.sources,self.result,'interest',F(500))
  for s,v in out['scenarios'].items():self.assertFalse(v['capacity']['within_capacity']);self.assertIsNone(v['with_refinance']['cash_per_usd_10']);self.assertIsNotNone(v['horizon_without_refinance']['cash_per_usd_10']);self.assertEqual(v['capacity']['requested_principal'],self.result['scenarios'][s]['capacity']['requested_principal'])

 def test_price_cannot_hide_ltc_capacity_even_with_valid_irr(self):
  from worksheet_monthly_analysis_D277 import guard_fixed_construction_capacity
  g=dict(price_grid=[dict(price=R(10),state='CALCULATED',values={'annual_irr':'not used'},target_status='MEETS_USER_TARGETS')],max_price_for_targets=dict(state='BOUNDED',price=R(10)))
  out=guard_fixed_construction_capacity(g,eligible=100,drawn=60,ltc='0.65',p0=100,c33=0);self.assertEqual(out['price_grid'][0]['state'],'PENDING');self.assertIsNone(out['price_grid'][0]['values']);self.assertIn('LTC',out['max_price_for_targets']['reason']);self.assertIsNone(out['max_price_for_targets']['price'])
