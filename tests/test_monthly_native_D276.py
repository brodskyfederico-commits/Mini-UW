"""Source contract and regression tests; no real documents or approvals."""
from pathlib import Path
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from hashlib import sha256
import json
from worksheet_frontiers_D275 import fraction as F,rational as R,digest
from worksheet_monthly_native_D276 import build_case,REFERENCE_SCHEMA
from worksheet_variant_evidence_D268 import inputs_digest
from worksheet_intake_D198 import read_source_directory,prepare,register,source_inventory
from worksheet_documented_finance_D147 import review_documents
from worksheet_native_mapping_D139 import review_native_mapping
from check_monthly_native_D276 import set_numeric_cells
from check_monthly_oracle_D276 import verify
from miniuw_worksheet_v1 import encoded

ROOT=Path(__file__).resolve().parents[1];FIXTURE=ROOT/'templates/golden_case_v2'

class MonthlyNativeSourceTests(TestCase):
 @classmethod
 def setUpClass(cls):
  cls.spec=json.loads((FIXTURE/'settings.json').read_bytes());cls.sources=read_source_directory(FIXTURE,include_reference=True);cls.raw,cls.current=prepare(cls.spec,register(cls.sources,'SYNTHETIC-D276-CURRENT'));cls.case=json.loads(cls.raw)
  cls.local=review_documents(cls.case,cls.sources['plan_raw'],evidence_raw=cls.sources['evidence_raw'],evidence_milestone='D162');assert not cls.local['blockers'],cls.local['blockers']
  cls.result,cls.pdf=cls.run_case(cls.spec,cls.sources)
 @classmethod
 def run_case(cls,spec,sources):
  # Only the expensive OCR extraction of identical PDF bytes is memoized by
  # this test harness. No modified PDF is substituted for the extracted bytes.
  assert sources['plan_raw']==cls.sources['plan_raw'] and sources['evidence_raw']==cls.sources['evidence_raw']
  raw,current=prepare(spec,register(sources,'SYNTHETIC-D276-CURRENT'));case=json.loads(raw)
  args={k:sources[k] for k in ('workbook_raw','downside_workbook_raw','plan_raw','evidence_raw','criteria_raw','independent_reference_raw')}
  with patch('worksheet_monthly_native_D276.review_documents',return_value=deepcopy(cls.local)):
   return build_case(case,raw,current_revision_raw=current,**args)
 def test_all_frozen_v2_files_match_hash_and_v1_is_a_separate_case(self):
  manifest=json.loads((FIXTURE/'golden_manifest.json').read_bytes())
  for file,h in manifest['files'].items():self.assertEqual(sha256((FIXTURE/file).read_bytes()).hexdigest(),h,file)
  self.assertNotEqual((ROOT/'templates/golden_case_v1/Plan.pdf').read_bytes(),self.sources['plan_raw'])
 def test_literal_source_oracle_and_frozen_expected_financials(self):
  checked=verify(self.spec,self.sources,self.result);self.assertEqual(checked['state'],'PASSED');expected=json.loads((FIXTURE/'expected_financials.json').read_bytes());self.assertEqual(checked['observations'],expected)
 def test_realistic_debt_near_binding_dscr_with_unadopted_criteria(self):
  for s,v in self.result['scenarios'].items():
   ratio=F(v['capacity']['bank_noi'])/F(v['capacity']['annual_service']);self.assertTrue(F('1.25')<=ratio<F('1.26'));ltv=F(v['capacity']['requested_principal'])/F(v['refinance_value']);self.assertTrue(F('0.60')<=ltv<=F('0.65'));self.assertEqual(v['capacity']['active_limits'],['DSCR'])
  self.assertEqual(self.result['decision'],'PENDING');self.assertTrue(all(r['state']=='PENDING' for r in self.result['screening']['criteria_comparisons']));self.assertFalse(self.result['deployment_enabled'])
 def test_each_critical_field_is_cited_not_two_case_level_greens(self):
  audit=self.result['critical_evidence_review'];self.assertEqual(audit['status'],'PASSED');self.assertEqual(audit['counts']['FALSE_GREEN'],0);self.assertGreater(len(audit['fields']),900)
  for field,row in audit['fields'].items():self.assertEqual(row['status'],'VERIFIED_GREEN');self.assertTrue(row['source_sha256']);self.assertTrue(row['locator'])
 def test_missing_reference_withdraws_cash_and_cannot_be_zero(self):
  src=dict(self.sources);src['independent_reference_raw']=None;x,_=self.run_case(self.spec,src);self.assertEqual(x['critical_evidence_review']['status'],'PENDING');self.assertTrue(all(v['cash_per_usd_10'] is None for v in x['scenarios'].values()))
 def test_blank_and_numeric_zero_for_all_55_cells_are_different_observations(self):
  for scenario,arg in [('Base','workbook_raw'),('Downside','downside_workbook_raw')]:
   cfg=deepcopy(self.case['native_mapping']);all_ids={r['field_id'] for r in self.result['native_mapping_review']['scenarios'][scenario]['rows']};cfg['scenarios'][scenario]['confirmed_fields']=sorted(all_ids);cfg['scenarios'][scenario]['not_applicable_fields']=[]
   self.assertEqual(len(all_ids),55)
   for fid in sorted(all_ids):
    cell=fid.removeprefix('INPUT_')
    for value in (None,'0'):
     raw=set_numeric_cells(self.sources[arg],{cell:value});workbooks={'Base':self.sources['workbook_raw'],'Downside':self.sources['downside_workbook_raw']};workbooks[scenario]=raw;hashes={s:sha256(v).hexdigest() for s,v in workbooks.items()};local=deepcopy(cfg)
     for s,h in hashes.items():local['scenarios'][s]['workbook_sha256']=h
     review=review_native_mapping(local,workbooks,hashes,calculation_fields={f'INPUT_C{i}' for i in range(7,16)},require_template_identity=True);row=next(r for r in review['scenarios'][scenario]['rows'] if r['field_id']==fid)
     if value is None:self.assertIsNone(row['value']);self.assertNotEqual(row['state'],'CONFIRMED_SYNTHETIC')
     elif row['role']=='arithmetic_candidate':self.assertEqual(F(row['value']),0);self.assertEqual(row['state'],'CONFIRMED_SYNTHETIC')
     else:self.assertEqual(row['source_literal'],'0');self.assertNotIn('confirmed_field_value_missing',row['blockers']);self.assertEqual(row['state'],'PENDING')
 def test_missing_market_evidence_is_pending_even_if_workbook_has_numbers(self):
  spec=deepcopy(self.spec);spec['rent_inputs']['market_evidence']['scenarios']['Base'].pop('rent');src=self.updated_sources(spec);x,_=self.run_case(spec,src);self.assertIsNone(x['scenarios']['Base']['cash_per_usd_10']);self.assertIn('B11',x['scenarios']['Base']['blockers'][0])
 def test_altered_amendment_and_missing_tax_never_use_original_quarter_cash(self):
  for kind in ('amendment','tax'):
   spec=deepcopy(self.spec)
   if kind=='amendment':spec['rent_inputs']['monthly_integration']['scenarios']['Base']['day_count']='30E/360'
   else:spec['rent_inputs']['florida_property_tax']['scenarios']['Base']['rolls']['millage'].pop('2033')
   x,_=self.run_case(spec,self.updated_sources(spec));self.assertIsNone(x['scenarios']['Base']['cash_per_usd_10']);self.assertIsNone(x['scenarios']['Base']['horizon_without_refinance']['cash_per_usd_10'])
 def test_cap_per_use_cannot_be_silently_replaced_by_combined_cap(self):
  spec=deepcopy(self.spec);spec['rent_inputs']['monthly_integration']['scenarios']['Base']['per_use_caps']={};x,_=self.run_case(spec,self.updated_sources(spec));self.assertIsNone(x['scenarios']['Base']['cash_per_usd_10'])
 def test_interest_stress_keeps_requested_loan_and_blocks_refi_without_erasing_no_refi(self):
  from worksheet_monthly_experiments_D276 import evaluate
  out=evaluate(self.spec,self.sources,self.result,'interest',F('500'))
  for s,v in out['scenarios'].items():
   self.assertEqual(F(v['capacity']['requested_principal']),F(self.result['scenarios'][s]['capacity']['requested_principal']));self.assertFalse(v['capacity']['within_capacity']);self.assertIsNone(v['with_refinance']['cash_per_usd_10']);self.assertIsNotNone(v['horizon_without_refinance']['cash_per_usd_10'])
 def test_lease_up_stress_rebuilds_fiscal_sale_and_cash_windows(self):
  from worksheet_monthly_experiments_D276 import evaluate
  old=digest(self.spec);out=evaluate(self.spec,self.sources,self.result,'lease_up',F('6'))
  self.assertEqual(digest(self.spec),old)
  for s,v in out['scenarios'].items():self.assertNotEqual(v['gross_sale'],self.result['scenarios'][s]['gross_sale']);self.assertIsNotNone(v['horizon_without_refinance']['cash_per_usd_10'])
 def test_favorable_outside_domain_is_pending_not_vacancy_zero(self):
  from worksheet_monthly_experiments_D276 import evaluate
  with self.assertRaises(ValueError):evaluate(self.spec,self.sources,self.result,'vacancy',F('-30'))
 def test_favorable_outside_base_domain_does_not_hide_valid_downside(self):
  from worksheet_monthly_experiments_D276 import evaluate
  x=evaluate(self.spec,self.sources,self.result,'lease_up',F('-4'));self.assertEqual(x['scenarios']['Base']['state'],'PENDING');self.assertEqual(x['scenarios']['Downside']['state'],'CALCULATED');self.assertIsNotNone(x['scenarios']['Downside']['horizon_without_refinance']['cash_per_usd_10'])
 def test_price_target_rejects_a_claim_from_other_sources_or_revision(self):
  from worksheet_monthly_experiments_D276 import price_analysis
  proof=verify(self.spec,self.sources,self.result);bad=dict(self.sources);bad['workbook_raw']=set_numeric_cells(bad['workbook_raw'],{'C32':'1000000'})
  with self.assertRaises(ValueError):price_analysis(self.spec,bad,self.result,proof)
 def test_construction_currency_and_cost_base_cannot_be_silently_reinterpreted(self):
  for fault in ('currency','eligible_cost'):
   spec=deepcopy(self.spec)
   if fault=='currency':spec['rent_inputs']['construction_financing']['scenarios']['Base']['currency']='EUR'
   else:spec['rent_inputs']['construction_financing']['rules']['eligible_cost']='total_development_cost'
   out,_=self.run_case(spec,self.updated_sources(spec));self.assertIsNone(out['scenarios']['Base']['cash_per_usd_10']);self.assertIn('base contractual',out['scenarios']['Base']['blockers'][0])
 @classmethod
 def updated_sources(cls,spec):
  sources=dict(cls.sources);reference=dict(schema=REFERENCE_SCHEMA,inputs_sha256=inputs_digest(spec['rent_inputs']),deal_id=spec['rent_inputs']['deal_id'],local_revision=spec['local_sources']['revision'],sources={source_inventory(sources)[k]:sha256(v).hexdigest() for k,v in sources.items() if k!='independent_reference_raw'});sources['independent_reference_raw']=encoded(reference);return sources
