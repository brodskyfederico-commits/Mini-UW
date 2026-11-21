from unittest import TestCase
from copy import deepcopy
from worksheet_cash_attribution_D277 import route_attribution,compare_prefix
from worksheet_frontiers_D275 import fraction as F,digest


def event(i,day,kind,category,amount):return dict(event_id=i,date=day,kind=kind,category=category,amount=str(amount),source_ref='SYNTHETIC-test')
def cash(events):return dict(reference_amount=10,basis_amount=100,basis_event_ids=['initial'],events=events,total_contributions=str(sum(F(e['amount']) for e in events if e['kind']=='contribution')),total_distributions=str(sum(F(e['amount']) for e in events if e['kind']=='distribution')))
class DatedCashAttributionTests(TestCase):
 def setUp(self):
  self.events=[event('initial','2027-01-01','contribution','initial_capital',10),event('shared','2028-01-01','contribution','additional_capital',1),event('refi','2028-01-01','distribution','net_refinance_distribution',8),event('cashin','2028-01-01','contribution','refinance_cash_in',3),event('later','2028-04-01','contribution','operating_funding',2)]
 def test_same_day_gross_receipt_and_cash_in_net_only_the_closing(self):
  c=cash(self.events);h=digest(c);a=route_attribution(c,'2028-01-01',with_refinance=True,expected_refinance_net=5)
  self.assertEqual(a['state'],'ATTRIBUTED');self.assertEqual(F(a['equity_recovered_net']),F('5/11'));self.assertEqual(F(a['cash_in_over_equity']),F('3/11'));self.assertEqual(F(a['same_day_all_cash_net']),4);self.assertEqual(F(a['post_refinance_contributions']),2);self.assertEqual(h,digest(c));self.assertEqual(F(c['total_contributions']),16)
 def test_identical_common_prefix_and_separate_refinance_legs(self):
  a=cash(self.events);b=cash(self.events[:2]);self.assertEqual(compare_prefix(a,b,'2028-01-01')['state'],'PASSED')
 def test_changed_pre_refi_or_common_closing_blocks(self):
  for index in (0,1):
   b=deepcopy(self.events[:2]);b[index]['amount']='12';self.assertEqual(compare_prefix(cash(self.events),cash(b),'2028-01-01')['state'],'PENDING')
 def test_missing_amount_total_source_or_category_never_becomes_zero(self):
  for field in ('amount','source_ref','category'):
   rows=deepcopy(self.events);rows[2][field]=None;a=route_attribution(dict(cash(self.events),events=rows),'2028-01-01',with_refinance=True,expected_refinance_net=5);self.assertEqual(a['state'],'PENDING');self.assertIsNone(a['cash_in_over_equity'])
  c=cash(self.events);c['total_contributions']=None;self.assertEqual(route_attribution(c,'2028-01-01',with_refinance=True,expected_refinance_net=5)['state'],'PENDING')
 def test_closing_date_and_expected_net_are_required(self):
  for net in (None,0):self.assertEqual(route_attribution(cash(self.events),'2028-01-01',with_refinance=True,expected_refinance_net=net)['state'],'PENDING')
  self.assertEqual(route_attribution(cash(self.events),'2028-02-01',with_refinance=True,expected_refinance_net=5)['state'],'PENDING')
 def test_explicit_zero_cash_in_is_respected_and_later_call_not_netted(self):
  rows=deepcopy(self.events);rows[3]['amount']='0';a=route_attribution(cash(rows),'2028-01-01',with_refinance=True,expected_refinance_net=8);self.assertEqual(F(a['cash_in_over_equity']),0);self.assertEqual(F(a['equity_recovered_net']),F('8/11'));self.assertEqual(F(a['post_refinance_contributions']),2)
