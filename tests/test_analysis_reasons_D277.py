from unittest import TestCase
from worksheet_monthly_analysis_D277 import reason,guard_fixed_construction_capacity
class AnalysisReasonTests(TestCase):
 def test_names_only_the_limits_actually_exceeded(self):
  r=dict(reason_code='CAPACITY',within_capacity=False,capacity=dict(requested_principal='100',limits=dict(LTV='120',DSCR='90',DEBT_YIELD='130')))
  self.assertEqual(reason(r),'DSCR');r['capacity']['limits']['LTV']='80';self.assertEqual(reason(r),'LTV/DSCR')
 def test_missing_reason_does_not_mean_zero_margin(self):
  self.assertEqual(reason({}),'faltan caja / evidencia');self.assertEqual(reason(dict(reason='No monotonía en grilla')),'no monotonía');self.assertEqual(reason(dict(reason='Sin TIR certificada')),'TIR sin raíz certificada')
 def test_fixed_draw_capacity_respects_c33_and_explicit_zero(self):
  def g():return dict(price_grid=[dict(price='90',state='CALCULATED',values={'equity_multiple':'2'},target_status='MEETS_USER_TARGETS')],max_price_for_targets=dict(state='BOUNDED',price='90'))
  a=guard_fixed_construction_capacity(g(),eligible='100',drawn='58',ltc='0.65',p0='100',c33=0);self.assertEqual(a['price_grid'][0]['state'],'CALCULATED')
  b=guard_fixed_construction_capacity(g(),eligible='100',drawn='58',ltc='0.65',p0='100',c33='0.1');self.assertEqual(b['price_grid'][0]['state'],'PENDING');self.assertIsNone(b['price_grid'][0]['values']);self.assertIsNone(b['max_price_for_targets']['price'])
  with self.assertRaises(ValueError):guard_fixed_construction_capacity(g(),eligible='100',drawn='58',ltc='0.65',p0='100',c33=None)

 def test_no_refi_maturity_does_not_inherit_unrelated_refi_capacity(self):
  from worksheet_monthly_experiments_D276 import pending_reason
  cap=dict(within_capacity=False,requested_principal='100',limits=dict(DSCR='90'))
  route=dict(state='PENDING',blockers=['Deuda de obra vence antes de la venta sin refi; no se supone extensión'])
  record=pending_reason('without_refinance',route,cap)|dict(within_capacity=False,capacity=cap)
  self.assertEqual(record['reason_code'],'STRATEGY');self.assertEqual(reason(record),'vencimiento de deuda');self.assertIn('no se supone extensión',record['reason'])
  self.assertEqual(reason(pending_reason('with_refinance',route,cap)|dict(capacity=cap)),'DSCR')
