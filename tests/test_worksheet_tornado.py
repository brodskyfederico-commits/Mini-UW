from fractions import Fraction as Q
from unittest import TestCase
from copy import deepcopy
from worksheet_tornado_D275 import tornado,SCHEMA,enclosure
from worksheet_frontiers_D275 import DRIVERS,rational


def config():return dict(schema=SCHEMA,drivers={k:dict(unit=v['unit'],magnitude='3' if k=='lease_up' else '1',source_ref='SYNTHETIC-shock') for k,v in DRIVERS.items()})
def evaluator(driver,x,s,r):
 effect=Q(x)*({'exit_cap':2}.get(driver,1))/1000
 v=Q(1,10)-effect
 return dict(state='VERIFIED',b12='PASSED',b16='PASSED',independent_check='PASSED',irr_annual=dict(lower=rational(v),upper=rational(v)),equity_multiple=rational(2-effect),case_sha256='a'*64,results_sha256='b'*64,cash_sha256='c'*64)

class TornadoTests(TestCase):
 def test_six_drivers_and_four_routes_remain_visible_and_ties_share_rank(self):
  a=tornado(config(),evaluator)
  for scenario in ['Base','Downside']:
   for route in ['with_refinance','without_refinance']:
    rows=a['tornado'][scenario][route];self.assertEqual(len(rows),6)
    self.assertEqual(rows[0]['driver'],'lease_up');self.assertEqual(rows[1]['driver'],'exit_cap')
    self.assertEqual({r['rank_min'] for r in rows[2:]},{3});self.assertEqual({r['rank_max'] for r in rows[2:]},{6})
 def test_symmetric_positive_and_negative_shocks(self):
  a=tornado(config(),evaluator)['tornado']['Base']['with_refinance']
  for r in a:
   x,y=r['shocks'];self.assertEqual(enclosure(x['delta_irr_annual'])[0],-enclosure(y['delta_irr_annual'])[1])
 def test_blocked_shock_does_not_disappear(self):
  def fn(d,x,s,r):return dict(state='PENDING',reason='Falta cita') if d=='exit_cap' and x>0 else evaluator(d,x,s,r)
  a=tornado(config(),fn)['tornado']['Base']['with_refinance'];row=next(v for v in a if v['driver']=='exit_cap')
  self.assertEqual(row['state'],'PENDING');self.assertEqual(len(row['shocks']),2);self.assertNotIn('rank_min',row)
 def test_audit_or_independent_gate_missing_blocks(self):
  for key in ['b12','b16','independent_check']:
   def fn(d,x,s,r):
    a=evaluator(d,x,s,r)
    if x:a.pop(key)
    return a
   self.assertTrue(all(r['state']=='PENDING' for r in tornado(config(),fn)['tornado']['Base']['with_refinance']))
 def test_zero_does_not_get_substituted_for_missing_irr(self):
  def fn(d,x,s,r):
   a=evaluator(d,x,s,r);a['irr_annual']=None;return a
  self.assertTrue(all(v['state']=='PENDING' for v in tornado(config(),fn)['tornado']['Base']['with_refinance']))
 def test_output_deterministic_and_input_preserved(self):
  c=config();before=deepcopy(c);self.assertEqual(tornado(c,evaluator),tornado(c,evaluator));self.assertEqual(c,before)
 def test_blank_shock_stays_pending(self):
  for val in [None,'',False,0]:
   c=config();c['drivers']['exit_cap']['magnitude']=val
   row=next(r for r in tornado(c,evaluator)['tornado']['Base']['with_refinance'] if r['driver']=='exit_cap');self.assertEqual(row['state'],'PENDING')
