from copy import deepcopy
from unittest import TestCase
from worksheet_commercial_leaseup_D275 import schedule,combine_residential_noi,SCHEMA
from worksheet_frontiers_D275 import fraction

def fixture():return dict(schema=SCHEMA,currency='USD',inventory_complete=True,source_ref='SYNTHETIC-commercial',area_reconciliation='RECONCILED',reconciled_area_sf='120',owner_cost_scope='commercial_only_excluding_M2_property_tax_insurance_and_residential',start='2027-01-01',end='2027-07-01',spaces=[dict(id='SYNTHETIC-SHOP',source_ref='SYNTHETIC-lease',area_sf='120',annual_rent_per_sf='12',collection_loss_fraction='0.1',owner_cost_per_month='20',recovery_fraction='0.5',lease_start='2027-02-01',lease_end='2027-07-01',free_rent_months=1,recoveries_waived_during_free_rent=False,noi_bases=dict(bank='collected_net',refinance_valuation='contractual_net',sale_valuation='collected_net'),rent_steps=[dict(effective_date='2027-04-01',relative_increase='0.1',source_ref='SYNTHETIC-step')],ti_lc_events=[dict(date='2027-01-15',kind='TI',budget_location='M3',amount='50',source_ref='SYNTHETIC-TI'),dict(date='2027-03-15',kind='LC',budget_location='operating_capex',amount='5',source_ref='SYNTHETIC-LC')])])

class CommercialLeaseupTests(TestCase):
 def test_months_before_lease_free_rent_and_escalator(self):
  a=schedule(fixture());self.assertEqual(a['state'],'CALCULATED');rows=a['monthly']
  self.assertEqual(fraction(rows[0]['operating_noi']),-20);self.assertEqual(fraction(rows[1]['operating_noi']),-11);self.assertEqual(fraction(rows[2]['operating_noi']),97);self.assertEqual(fraction(rows[3]['operating_noi']),fraction('107.8'))
 def test_bank_and_valuation_bases_are_separate(self):
  a=schedule(fixture())['monthly'][2];self.assertEqual(fraction(a['noi_by_basis']['bank']),97);self.assertEqual(fraction(a['noi_by_basis']['refinance_valuation']),110)
 def test_m3_and_operating_capex_not_double_counted_in_noi(self):
  a=schedule(fixture());self.assertEqual(fraction(a['m3_ti_lc']),50);self.assertEqual(fraction(a['monthly'][2]['operating_capex']),5);self.assertEqual(fraction(a['monthly'][2]['cash_after_commercial_capex']),92)
 def test_missing_or_discrepant_area_blocks(self):
  for field,value in [('area_reconciliation','DISCREPANT'),('reconciled_area_sf','121'),('reconciled_area_sf',None)]:
   s=fixture();s[field]=value;self.assertEqual(schedule(s)['state'],'PENDING')
 def test_missing_bank_basis_never_inherits_valuation_basis(self):
  s=fixture();s['spaces'][0]['noi_bases'].pop('bank');self.assertEqual(schedule(s)['state'],'PENDING')
 def test_missing_zero_is_not_assumed_for_free_rent_or_capex(self):
  for key in ['free_rent_months','collection_loss_fraction','ti_lc_events','rent_steps','recovery_fraction']:
   s=fixture();s['spaces'][0].pop(key);self.assertEqual(schedule(s)['state'],'PENDING',key)
 def test_zero_commercial_inventory_preserves_residential_numbers(self):
  s=fixture();s.update(spaces=[],reconciled_area_sf='0');a=schedule(s);self.assertEqual(a['state'],'CALCULATED')
  residential=[dict(start=r['start'],end=r['end'],noi='10') for r in a['monthly']];combined=combine_residential_noi(residential,a)
  self.assertTrue(all(fraction(r['total_operating_noi'])==10 for r in combined['monthly']))
 def test_multiple_spaces_reconcile_and_input_is_preserved(self):
  s=fixture();extra=deepcopy(s['spaces'][0]);extra['id']='SYNTHETIC-SHOP2';s['spaces'].append(extra);s['reconciled_area_sf']='240';old=deepcopy(s);a=schedule(s);self.assertEqual(a['state'],'CALCULATED');self.assertEqual(s,old);self.assertEqual(fraction(a['monthly'][2]['operating_noi']),194)
