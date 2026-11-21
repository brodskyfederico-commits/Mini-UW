from unittest import TestCase
from copy import deepcopy
from worksheet_user_price_D275 import price_point,grid,SCHEMA,MONTHLY_SCHEMA,RULE
from worksheet_frontiers_D275 import fraction as F,rational as R
from datetime import date
from worksheet_monthly_D275 import month


def fixture():
 dates=[str(month(date(2026,1,1),i)) for i in range(13)]
 events=[dict(id='i'+str(i),date=d,kind='contribution' if i==0 else 'distribution',amount='10' if i==0 else '12' if i==12 else '0',source_ref='SYNTHETIC-cash') for i,d in enumerate(dates)]
 return dict(schema=MONTHLY_SCHEMA,rule=RULE,source_check='INDEPENDENTLY_VERIFIED',source_ref='SYNTHETIC-price',source_sha256='a'*64,purchase_price='5',closing_fraction='0',tdc='10',applied_equity='10',fixed_debt='0',fixed_other_sources='0',noi_uw='1',gross_events=events,initial_event_id='i0',dates=dates,periods_per_year=12)

class MonthlyPriceTests(TestCase):
 def test_annual_tir_not_quarterly_annualization(self):
  x=price_point(fixture(),5,{'annual_irr':dict(operator='>=',value='0.15')});self.assertEqual(x['target_status'],'MEETS_USER_TARGETS');lo,hi=(F(x['irr']['annual_enclosure'][k]) for k in ('lower','upper'));self.assertLessEqual(lo,F('0.20'));self.assertGreaterEqual(hi,F('0.20'))
 def test_explicit_other_source_blank_is_not_zero(self):
  s=fixture();s['fixed_other_sources']=None;self.assertEqual(price_point(s,5,{'equity_multiple':dict(operator='>=',value='1')})['state'],'PENDING')
 def test_quarter_schema_rejects_monthly_schedule(self):
  s=fixture();s['schema']=SCHEMA;self.assertEqual(price_point(s,5,{'equity_multiple':dict(operator='>=',value='1')})['state'],'PENDING')
 def test_c33_land_delta_and_fixed_cash_future_events(self):
  s=fixture();s['closing_fraction']='0.1';old=deepcopy(s);x=price_point(s,6,{'annual_irr':dict(operator='>=',value='0.15')});self.assertEqual(F(x['delta_tdc']),F('1.1'));self.assertEqual(F(x['initial_equity']),F('11.1'));self.assertEqual(s,old)
 def test_target_not_house_rlv_or_lorena_approval(self):
  s=fixture();x=grid(s,dict(schema=MONTHLY_SCHEMA,source_ref='SYNTHETIC-target-15',lower='4',upper='7',step='1',user_targets={'annual_irr':dict(operator='>=',value='0.15')}));self.assertEqual(x['max_price_for_targets']['state'],'BOUNDED');self.assertEqual(F(x['max_price_for_targets']['price']),5);self.assertFalse(x['criteria_adopted']);self.assertEqual(x['house_rlv']['state'],'PENDING')

 def test_no_price_in_grid_is_distinct_from_missing_data_and_zero_price(self):
  x=grid(fixture(),dict(schema=MONTHLY_SCHEMA,source_ref='SYNTHETIC-high-mathematical-target',lower='4',upper='6',step='1',user_targets={'annual_irr':dict(operator='>=',value='10')}));self.assertEqual(x['max_price_for_targets']['state'],'NO_PRICE_IN_GRID');self.assertIsNone(x['max_price_for_targets']['price']);self.assertTrue(all(p['state']=='CALCULATED' for p in x['price_grid']))
