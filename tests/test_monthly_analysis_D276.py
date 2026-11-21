from unittest import TestCase
from copy import deepcopy
from worksheet_monthly_analysis_D276 import request,validate_request,bounded_grid
from worksheet_frontiers_D275 import fraction as F

class MonthlyAnalyticalDeliveryTests(TestCase):
 def test_request_is_bound_to_case_sources_and_allows_no_claimed_results(self):
  case=b'{"synthetic":"case"}';sources={'workbook_raw':b'xlsx','plan_raw':b'pdf'};r=request(case,sources);validate_request(r,case,sources)
  for fault in ('case','source','table','scope'):
   x=deepcopy(r);c=case;s=dict(sources)
   if fault=='case':c=b'{"synthetic":"other revision"}'
   elif fault=='source':s['plan_raw']=b'other pdf'
   elif fault=='table':x['price_grid']={'Base':{'price':'1'}}
   else:x['usage']='real_deal_approval'
   with self.assertRaises(ValueError):validate_request(x,c,s)
 def test_missing_point_is_not_safe_or_zero(self):
  x=bounded_grid([(F('0'),F('1')),(F('1'),None)],1,1,'bps');self.assertEqual(x['state'],'PENDING');self.assertIsNone(x['value'])
 def test_known_initial_loss_visible_even_when_adverse_cash_is_blocked(self):
  x=bounded_grid([(F('0'),F('-1')),(F('1'),None)],1,1,'bps');self.assertEqual(x['state'],'BASELINE_BREACHED');self.assertEqual(F(x['value']),0)
 def test_nonmonotone_grid_cannot_claim_first_boundary(self):
  x=bounded_grid([(F('0'),F('1')),(F('1'),F('-1')),(F('2'),F('1'))],2,1,'bps');self.assertEqual(x['state'],'PENDING')
 def test_complete_grid_brackets_breach_and_does_not_extrapolate(self):
  x=bounded_grid([(F('0'),F('1')),(F('1'),F('0')),(F('2'),F('-1'))],2,1,'bps');self.assertEqual(x['state'],'BOUNDED');self.assertEqual(F(x['safe_movement']),1);self.assertEqual(F(x['breached_movement']),2)
