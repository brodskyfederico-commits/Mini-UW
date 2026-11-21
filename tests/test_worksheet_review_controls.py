from copy import deepcopy
from hashlib import sha256
from unittest import TestCase
from worksheet_review_controls_D275 import (empty_roles,review_roles,ROLE_FIELDS,false_green_study,wilson,zero_event_sample_size,STUDY_SCHEMA)

RAW=b'SYNTHETIC-independent-label';H=sha256(RAW).hexdigest();DOCS={H:RAW}
def fixture():
 human=dict(reviewer_id='SYNTHETIC-REVIEWER',supported=True,value='0',unit='USD',basis='declared_test',scenario='Base',evidence=dict(sha256=H,locator='p. 1 / campo de prueba'))
 return dict(schema=STUDY_SCHEMA,population='synthetic_test',confidence='0.95',maximum_rate='0.01',expected_ids=['SYNTHETIC-A'],critical_fields=[dict(id='SYNTHETIC-A',document_type='term_sheet',bot='B08',independent_human_reference=human,bot_claim={k:v for k,v in human.items() if k not in ('reviewer_id','supported')}|dict(state='GREEN'))])

class ReviewControlTests(TestCase):
 def test_empty_roles_stay_pending_without_inventing_people(self):
  a=empty_roles();b=deepcopy(a);x=review_roles(a,'2027-01-01',{});self.assertFalse(x['structurally_complete']);self.assertEqual(a,b)
  self.assertTrue(all(r['label']=='responsable por designar' for r in x['roles'].values()))
 def test_fictional_complete_roles_do_not_authenticate_an_approval(self):
  r=empty_roles()
  for key,row in r['roles'].items():row.update(name='PERSONA FICTICIA',actor_id='SYNTHETIC-'+key,scope='Prueba sin autoridad real',designated_on='2026-12-01',valid_from='2027-01-01',valid_until='2027-12-31',appointment_sha256=H)
  a=review_roles(r,'2027-01-01',DOCS);self.assertTrue(a['structurally_complete']);self.assertEqual(a['real_decision'],'PENDING');self.assertFalse(a['deployment_enabled'])
  self.assertTrue(all(not v['identity_authenticated'] for v in a['roles'].values()))
 def test_roles_expiration_and_missing_evidence_are_blocking(self):
  r=empty_roles()
  for row in r['roles'].values():row.update(dict(zip(ROLE_FIELDS,['X','SYNTHETIC-X','scope','2026-01-01','2026-01-01','2026-12-31',H])))
  self.assertFalse(review_roles(r,'2027-01-01',DOCS)['structurally_complete']);self.assertFalse(review_roles(r,'2026-01-01',{})['structurally_complete'])
 def test_zero_is_reviewed_and_not_missing(self):
  x=false_green_study(fixture(),DOCS);self.assertEqual(x['overall']['false_greens'],0);self.assertEqual(x['overall']['rate'],0)
 def test_any_green_without_citation_is_false_even_when_value_matches(self):
  s=fixture();s['critical_fields'][0]['bot_claim']['evidence']=None
  x=false_green_study(s,DOCS);self.assertEqual(x['overall']['false_greens'],1);self.assertTrue(x['rows'][0]['green_without_citation'])
 def test_disagreement_or_wrong_unit_basis_or_scenario_is_false(self):
  for key,val in [('value','1'),('unit','SF'),('basis','wrong'),('scenario','Downside')]:
   s=fixture();s['critical_fields'][0]['bot_claim'][key]=val;self.assertEqual(false_green_study(s,DOCS)['overall']['false_greens'],1,key)
 def test_human_missing_does_not_create_a_correct_negative(self):
  s=fixture();s['critical_fields'][0]['independent_human_reference']=None
  x=false_green_study(s,DOCS);self.assertEqual(x['overall']['state'],'PENDING');self.assertIsNone(x['overall']['rate']);self.assertEqual(x['overall']['reviewed'],0)
 def test_blank_claim_value_never_matches_explicit_zero(self):
  for blank in [None,'',False]:
   s=fixture();s['critical_fields'][0]['bot_claim']['value']=blank;self.assertEqual(false_green_study(s,DOCS)['overall']['false_greens'],1)
 def test_no_citation_does_not_count_human_label_as_verified(self):
  s=fixture();s['critical_fields'][0]['independent_human_reference']['evidence']['sha256']='a'*64
  self.assertIsNone(false_green_study(s,DOCS)['overall']['rate'])
 def test_missing_and_duplicate_critical_fields_are_rejected(self):
  for fault in ['omit','duplicate']:
   s=fixture()
   if fault=='omit':s['expected_ids'].append('missing')
   else:s['critical_fields']*=2
   with self.assertRaises(ValueError):false_green_study(s,DOCS)
 def test_groups_do_not_hide_injected_false_greens(self):
  s=fixture();row=deepcopy(s['critical_fields'][0]);row.update(id='SYNTHETIC-B',document_type='plano',bot='B05');row['bot_claim']['value']='1';s['critical_fields'].append(row);s['expected_ids'].append(row['id'])
  a=false_green_study(s,DOCS);self.assertEqual(a['overall']['rate'],.5);self.assertEqual(a['by_bot']['B05']['rate'],1);self.assertEqual(a['by_document_type']['plano']['rate'],1)
 def test_zero_sample_not_zero_error_rate(self):
  self.assertEqual(wilson(0,0,.95)['state'],'PENDING')
 def test_interval_positive_upper_at_zero_events_and_sample_requirement(self):
  ci=wilson(0,100,.95);self.assertGreater(ci['upper'],.036);self.assertLess(ci['upper'],.038)
  n=zero_event_sample_size('0.01','0.95');self.assertEqual(n,381);self.assertLessEqual(wilson(0,n,.95)['upper'],.01);self.assertGreater(wilson(0,n-1,.95)['upper'],.01)
 def test_real_flag_never_certifies_synthetic_study_or_authority(self):
  s=fixture();s['population']='real_documents';a=false_green_study(s,DOCS);self.assertFalse(a['real_empirical_certification']);self.assertEqual(a['real_decision'],'PENDING')

class ExactCitationTests(TestCase):
 def test_correct_value_with_wrong_locator_is_false_green(self):
  s=deepcopy(fixture());s['critical_fields'][0]['bot_claim']['evidence']=dict(sha256=H,locator='p. 99 / campo ajeno');self.assertEqual(false_green_study(s,DOCS)['overall']['false_greens'],1)

class ReviewMissingnessTests(TestCase):
 def test_malformed_evidence_hash_is_missing_not_a_crash_or_zero(self):
  s=fixture();s['critical_fields'][0]['bot_claim']['evidence']={'sha256':[],'locator':'p. 1'};a=false_green_study(s,DOCS);self.assertEqual(a['overall']['false_greens'],1)
  r=empty_roles();r['roles']['criteria_owner']['appointment_sha256']=[];self.assertFalse(review_roles(r,'2027-01-01',{})['structurally_complete'])
 def test_abstention_coverage_visible_even_when_no_false_greens_are_observed(self):
  s=fixture();s['critical_fields'][0]['bot_claim']['state']='PENDING';a=false_green_study(s,DOCS);self.assertEqual(a['overall']['rate'],0);self.assertEqual(a['overall']['green_coverage'],0);self.assertEqual(a['overall']['abstentions'],1);self.assertFalse(a['real_empirical_certification'])
