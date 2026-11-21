from unittest import TestCase
from copy import deepcopy
from hashlib import sha256
import json
from worksheet_builders_risk_D275 import SCHEMA,line,budget_extension
from worksheet_frontiers_D275 import fraction

DOCS={}
def backed(s):
 q={k:s[k] for k in ('currency','premium_basis','base','rate','quoted_premium','term_start','term_end','payment_date')};q['schema']='miniuw.synthetic-builders-risk-quote.v1';raw=json.dumps(q,sort_keys=True).encode();h=sha256(raw).hexdigest();DOCS[h]=raw;s['quote_source']=dict(sha256=h,locator='cotización JSON / prima');return s
def included(s):
 raw=json.dumps(dict(schema='miniuw.synthetic-gc-risk-inclusion.v1',included=True,premium='30')).encode();h=sha256(raw).hexdigest();DOCS[h]=raw;s['gc_inclusion_source']=dict(sha256=h,locator='GC / prima incluida');return s
def spec():return backed(dict(schema=SCHEMA,currency='USD',term_start='2027-01-01',term_end='2028-01-01',payment_date='2027-01-01',premium_basis='quoted_premium',base=None,rate=None,quoted_premium='30',quote_source=None,included_in_gc=False,included_in_soft_percentage=False,gc_inclusion_source=None))

class BuildersRiskTests(TestCase):
 def test_explicit_line_reconciles_cost_and_dated_uses(self):
  a=budget_extension(dict(total_development_cost='1000'),spec(),DOCS);self.assertEqual(fraction(a['total_development_cost']),1030);self.assertEqual(fraction(a['incremental_uses'][0]['amount']),30)
 def test_gc_inclusion_with_evidence_adds_zero_once(self):
  s=spec();s['included_in_gc']=True;included(s)
  a=budget_extension(dict(total_development_cost='1000'),s,DOCS);self.assertEqual(fraction(a['total_development_cost']),1000);self.assertEqual(fraction(a['builders_risk']['quoted_or_computed_premium']),30)
 def test_inclusion_without_backing_not_assumed(self):
  s=spec();s['included_in_gc']=True;self.assertEqual(line(s,DOCS)['state'],'PENDING')
 def test_unknown_or_soft_percentage_not_used_as_zero(self):
  for field in ['quoted_premium','included_in_soft_percentage','included_in_gc']:
   s=spec();s[field]=None;self.assertEqual(line(s,DOCS)['state'],'PENDING',field)
 def test_no_automatic_annualization_of_rate(self):
  s=spec();s.update(premium_basis='rate_times_base_for_full_declared_term',quoted_premium=None,base='1000',rate='0.03');backed(s);a=line(s,DOCS);self.assertEqual(fraction(a['incremental_budget_cost']),30)
 def test_explicit_zero_premium_preserved(self):
  s=spec();s['quoted_premium']='0';backed(s);a=line(s,DOCS);self.assertEqual(a['state'],'CALCULATED');self.assertEqual(fraction(a['incremental_budget_cost']),0)
 def test_repeated_application_is_rejected(self):
  a=budget_extension(dict(total_development_cost='1000'),spec(),DOCS);self.assertEqual(budget_extension(a,spec(),DOCS)['state'],'PENDING')
 def test_missing_quote_or_date_blocks(self):
  self.assertEqual(line(spec(),{})['state'],'PENDING');s=spec();s['term_end']='2026-01-01';self.assertEqual(line(s,DOCS)['state'],'PENDING')
 def test_preserve_operating_insurance_and_inputs(self):
  b=dict(total_development_cost='1000',operating_insurance='12');old=deepcopy(b);a=budget_extension(b,spec(),DOCS);self.assertEqual(b,old);self.assertEqual(a['operating_insurance'],'12')

class QuoteBindingTests(TestCase):
 def test_number_with_a_real_hash_but_different_literal_is_pending(self):
  s=spec();s['quoted_premium']='31';self.assertEqual(line(s,DOCS)['state'],'PENDING')
