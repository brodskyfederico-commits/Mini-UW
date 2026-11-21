from copy import deepcopy
from unittest import TestCase
from fractions import Fraction as Q
from worksheet_user_price_D275 import SCHEMA,RULE,price_point,grid
from worksheet_frontiers_D275 import fraction


def source(c33='0'):
 return dict(schema=SCHEMA,rule=RULE,source_check='INDEPENDENTLY_VERIFIED',source_ref='SYNTHETIC-golden-price-cells',source_sha256='a'*64,purchase_price='20',closing_fraction=c33,tdc='100',applied_equity='100',fixed_debt='0',noi_uw='10',dates=['2027-01-01','2027-04-01','2027-07-01'],initial_event_id='initial',gross_events=[dict(id='initial',date='2027-01-01',kind='contribution',amount='100',source_ref='SYNTHETIC-first'),dict(id='explicit-zero',date='2027-04-01',kind='distribution',amount='0',source_ref='SYNTHETIC-zero'),dict(id='sale',date='2027-07-01',kind='distribution',amount='120',source_ref='SYNTHETIC-sale')])
def config():return dict(schema=SCHEMA,source_ref='SYNTHETIC-user-targets',lower='0',upper='60',step='10',user_targets=dict(equity_multiple=dict(operator='>=',value='1')))

class UserPriceTests(TestCase):
 def test_fixed_debt_delta_tdc_and_cash_from_literal_sources(self):
  for c33 in ['0','0.02']:
   a=price_point(source(c33),30,config()['user_targets']);delta=10*(1+Q(c33))
   self.assertEqual(fraction(a['delta_tdc']),delta);self.assertEqual(fraction(a['tdc']),100+delta);self.assertEqual(fraction(a['fixed_debt']),0)
   self.assertEqual(fraction(a['values']['equity_multiple']),Q(120)/(100+delta))
   self.assertEqual(fraction(a['gross_cash_per_usd10'][0]['amount']),10)
 def test_target_grid_maximum_and_neighbors(self):
  x=grid(source(),config());self.assertEqual(x['max_price_for_targets']['state'],'BOUNDED');self.assertEqual(fraction(x['max_price_for_targets']['price']),40);self.assertEqual(fraction(x['max_price_for_targets']['next_price']),50)
 def test_house_rlv_is_never_activated(self):
  x=grid(source(),config());self.assertEqual(x['house_rlv']['state'],'PENDING');self.assertTrue(all(p['house_rlv']['state']=='PENDING' for p in x['price_grid']))
 def test_negative_maximum_is_published_with_flag(self):
  s=source();s['gross_events'][-1]['amount']='70';c=config();c.update(lower='-40',upper='20',step='10');a=grid(s,c)['max_price_for_targets']
  self.assertEqual(a['state'],'BOUNDED');self.assertEqual(fraction(a['price']),-10);self.assertTrue(a['negative_price_flag'])
 def test_no_attainable_price_is_pending_not_zero(self):
  s=source();s['gross_events'][-1]['amount']='1';a=grid(s,config())['max_price_for_targets'];self.assertEqual(a['state'],'PENDING');self.assertIsNone(a['price'])
 def test_no_hidden_defaults_for_targets_or_closing_rate(self):
  for blank in [None,'',False]:
   s=source();s['closing_fraction']=blank;self.assertEqual(price_point(s,20,config()['user_targets'])['state'],'PENDING')
  self.assertEqual(price_point(source(),20,{})['state'],'PENDING')
 def test_equity_tdc_can_limit_without_yield_or_irr(self):
  s=source();s.update(fixed_debt='60',applied_equity='40');c=config();c['user_targets']=dict(equity_tdc=dict(operator='<=',value='0.5'));a=grid(s,c)['max_price_for_targets'];self.assertEqual(fraction(a['price']),40)
 def test_cash_dates_and_explicit_zeros_preserved(self):
  s=source();a=price_point(s,20,config()['user_targets']);self.assertEqual(fraction(a['gross_cash_per_usd10'][1]['amount']),0)
  s['gross_events'].pop(1);self.assertEqual(price_point(s,20,config()['user_targets'])['state'],'PENDING')
 def test_unique_irr_certificate_and_target_comparison(self):
  a=price_point(source(),20,dict(annual_irr=dict(operator='>=',value='0.40')));self.assertEqual(a['irr']['state'],'CERTIFIED');self.assertTrue(a['targets']['annual_irr'])
 def test_price_at_upper_grid_does_not_claim_maximum(self):
  c=config();c['user_targets']['equity_multiple']['value']='0';a=grid(source(),c)['max_price_for_targets'];self.assertEqual(a['state'],'BEYOND_GRID');self.assertIsNone(a['price'])
 def test_source_and_config_not_mutated(self):
  s=source();c=config();before=deepcopy((s,c));grid(s,c);self.assertEqual((s,c),before)
