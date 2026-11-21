from unittest import TestCase
from copy import deepcopy
from fractions import Fraction as Q
from datetime import date
import json
from hashlib import sha256
from worksheet_monthly_integration_D276 import integrate,SCHEMA,ledger
from worksheet_monthly_D275 import month,SCHEMA as CONSTRUCTION,construction
from worksheet_commercial_leaseup_D275 import SCHEMA as COMMERCIAL
from worksheet_builders_risk_D275 import SCHEMA as RISK
from worksheet_frontiers_D275 import fraction as F,rational as R


def fixture():
 start=date(2026,10,1);stable=date(2027,4,1);sale=date(2028,4,1);end=month(sale,12)
 quote=dict(schema='miniuw.synthetic-builders-risk-quote.v1',currency='USD',premium_basis='quoted_premium',base=None,rate=None,quoted_premium='0',term_start=str(start),term_end=str(stable),payment_date=str(start));raw=json.dumps(quote,sort_keys=True).encode();h=sha256(raw).hexdigest()
 cfg=dict(schema=CONSTRUCTION,currency='USD',scenario='Base',start=str(start),stabilization=str(stable),maturity=str(sale),annual_rate='0.12',ltc='1',eligible_total='100',maximum_commitment='100',fee_fraction='0',initial_equity='10',opening_free_cash='0',opening_principal='0',principal_payment_mode='interest_only_until_stabilization',other_costs_and_limits_complete=True,equity_policy='initial_then_top_up_for_sourced_uses',interest_payment_every_months=3,pay_interest_at_stabilization=True,day_count='30E/360',source_ref='SYNTHETIC-bank',periods=[])
 for i in range(6):
  a,b=month(start,i),month(start,i+1);cfg['periods'].append(dict(start=str(a),end=str(b),inventory_complete=True,source_ref='SYNTHETIC-month-'+str(i),events=[dict(id='initial-cost',kind='use',date=str(a),amount='110',source_ref='SYNTHETIC-cost'),dict(id='initial-draw',invoice_id='SYNTHETIC-invoice',kind='draw',date=str(a),amount='100',eligible_invoice='100',available_new_draw='100',source_ref='SYNTHETIC-draw')] if i==0 else []))
 dates=[str(month(start,i)) for i in range(30)]
 spec=dict(schema=SCHEMA,currency='USD',scenario='Base',source_ref='SYNTHETIC-integrated',source_adapter_verified=True,source_inputs_sha256='a'*64,purchase_date=str(start),construction_finish=str(stable),stabilization_date=str(stable),sale_date=str(sale),construction=cfg,commercial=dict(schema=COMMERCIAL,currency='USD',inventory_complete=True,source_ref='SYNTHETIC-commercial',area_reconciliation='RECONCILED',reconciled_area_sf='0',owner_cost_scope='commercial_only_excluding_M2_property_tax_insurance_and_residential',start=str(start),end=str(end),spaces=[]),builders_risk=quote|dict(schema=RISK,quote_source=dict(sha256=h,locator='premium'),included_in_gc=False,included_in_soft_percentage=False),budget=dict(land='10',direct_hard='100',contingency='0',soft='0',ti_lc='0',residential_leaseup='0'),monthly_taxes=[dict(start=d,amount='0',source_ref='SYNTHETIC-tax') for d in dates],residential_monthly=[dict(start=d,operating_before_tax='2',bank_before_tax='2',refinance_before_tax='2',sale_before_tax='2',source_ref='SYNTHETIC-rents') for d in dates],preopening_scope='budget_excludes_tax_risk_and_commercial_net_cash',tax_payment_every_months=3,operating_cash_every_months=3,valuation_bases=dict(refinance='before_reserves',sale='before_reserves'),replacement_reserve=dict(deposit_every_months=3,annual_amount='0',sale_release_fraction='0',source_ref='SYNTHETIC-C60'),refinance_cap='0.12',sale_cap='0.12',permanent=dict(requested_principal='100',annual_nominal_rate='0',maximum_ltv='1',minimum_dscr='1',amortization_years=10,maturity_payments=40,payments_per_year=4,source_ref='SYNTHETIC-bank',debt_yield=dict(applicability='not_applicable',minimum=None,source_ref='SYNTHETIC-DY')),refinance=dict(cost_fraction='0',reserve_amount='0',sale_release_fraction='0',source_ref='SYNTHETIC-refi'),sale_cost_fraction='0',fixed_sale_cost='0',without_refinance=dict(retention_terms='same_committed_facility_C52_until_documented_maturity',maturity_date=str(sale),fee_at_stabilization='0',source_ref='SYNTHETIC-carry'))
 return spec,{h:raw}

class MonthlyIntegratedTests(TestCase):
 def test_quarter_equivalence_from_construction_to_sale_exact_gross_cash(self):
  s,d=fixture();x=integrate(s,d);self.assertEqual(x['state'],'CALCULATED',x);self.assertEqual(F(x['tdc']),116)
  # Independent quarter arithmetic: equity 10+3+3; net refi0;
  # operations four*(6-2.5); sale200-90; no-refi four*(6-3),sale100.
  for route,receipts in [(x['with_refinance'],124),(x['horizon_without_refinance'],112)]:
   cash=route['cash_per_usd_10'];self.assertEqual(F(cash['total_contributions']),16);self.assertEqual(F(cash['total_distributions']),receipts);self.assertEqual(route['return_summary']['irr_annual']['state'],'CERTIFIED')
 def test_midquarter_draw_recalculates_interest_without_rounding(self):
  s,d=fixture();e=s['construction']['periods'][0]['events'];s['construction']['periods'][1]['events']=e;s['construction']['periods'][0]['events']=[]
  for event in e:event['date']='2026-11-01'
  x=integrate(s,d);self.assertEqual(x['state'],'CALCULATED');self.assertEqual(F(x['construction_financing']['interest_total']),5)
 def test_bank_capacity_failure_only_blocks_refinance_route(self):
  s,d=fixture();s['permanent']['minimum_dscr']='100';x=integrate(s,d);self.assertEqual(x['state'],'CALCULATED');self.assertIsNone(x['with_refinance']['cash_per_usd_10']);self.assertIsNotNone(x['horizon_without_refinance']['cash_per_usd_10'])
 def test_no_refi_maturity_failure_does_not_remove_refi_cash(self):
  s,d=fixture();s['without_refinance']['maturity_date']='2027-05-01';x=integrate(s,d);self.assertIsNotNone(x['with_refinance']['cash_per_usd_10']);self.assertIsNone(x['horizon_without_refinance']['cash_per_usd_10'])
 def test_missing_month_or_empty_value_never_becomes_zero(self):
  for fault in ('month','tax','NOI','risk'):
   s,d=fixture()
   if fault=='month':s['monthly_taxes'].pop()
   elif fault=='tax':s['monthly_taxes'][0]['amount']=None
   elif fault=='NOI':s['residential_monthly'][0]['operating_before_tax']=''
   else:s['builders_risk']['quote_source']=None
   x=integrate(s,d);self.assertEqual(x['state'],'PENDING',fault);self.assertIsNone(x['cash_per_usd_10'])
 def test_zero_tax_and_zero_premium_are_explicit_source_values(self):
  s,d=fixture();x=integrate(s,d);self.assertEqual(x['state'],'CALCULATED');self.assertEqual(F(x['builders_risk']['incremental_budget_cost']),0)
 def test_premium_enters_tdc_once_and_changes_cash_without_changing_operating_insurance(self):
  s,d=fixture();old=deepcopy(s['residential_monthly']);q=json.loads(next(iter(d.values())));q['quoted_premium']='2';raw=json.dumps(q,sort_keys=True).encode();h=sha256(raw).hexdigest();s['builders_risk'].update(quoted_premium='2',quote_source=dict(sha256=h,locator='premium'));s['construction']['initial_equity']='12';x=integrate(s,{h:raw});self.assertEqual(x['state'],'CALCULATED',x);self.assertEqual(F(x['tdc']),118);self.assertEqual(s['residential_monthly'],old)
 def test_january_tax_at_closing_enters_funding_and_tdc(self):
  s,d=fixture();s['monthly_taxes'][2]['amount']='3';s['monthly_taxes'][5]['amount']='4';x=integrate(s,d);self.assertEqual(x['state'],'CALCULATED',x);self.assertEqual(F(x['tdc']),123)
 def test_partial_commercial_leaseup_changes_operations_and_sale_basis(self):
  s,d=fixture();c=s['commercial'];c.update(reconciled_area_sf='10',spaces=[dict(id='SYNTHETIC-shop',source_ref='SYNTHETIC-lease',area_sf='10',annual_rent_per_sf='12',collection_loss_fraction='0',owner_cost_per_month='0',recovery_fraction='0',lease_start='2027-05-01',lease_end=c['end'],free_rent_months=1,recoveries_waived_during_free_rent=False,noi_bases=dict(bank='collected_net',refinance_valuation='collected_net',sale_valuation='collected_net'),rent_steps=[],ti_lc_events=[])])
  x=integrate(s,d);self.assertEqual(x['state'],'CALCULATED',x);self.assertEqual(F(x['annual_noi']),124);self.assertEqual(F(x['gross_sale']),1200)
 def test_commercial_area_conflict_blocks_dependent_cash(self):
  s,d=fixture();s['commercial']['area_reconciliation']='DISCREPANT';self.assertEqual(integrate(s,d)['state'],'PENDING')
 def test_m3_ti_lc_mismatch_does_not_silently_add_or_ignore_amount(self):
  s,d=fixture();s['budget']['ti_lc']='1';self.assertEqual(integrate(s,d)['state'],'PENDING')
 def test_undeclared_cap_basis_is_pending(self):
  s,d=fixture();s['valuation_bases']['sale']=None;self.assertEqual(integrate(s,d)['state'],'PENDING')
 def test_source_not_mutated(self):
  s,d=fixture();old=deepcopy(s);integrate(s,d);self.assertEqual(s,old)

 def test_positive_c60_uses_declared_quarterly_cadence_once(self):
  s,d=fixture();s['replacement_reserve'].update(annual_amount='4',sale_release_fraction='1');x=integrate(s,d);rows=x['with_refinance']['operating_months'];self.assertEqual([F(r['reserve_deposit']) for r in rows],[Q(),Q(),Q(1)]*4);self.assertEqual(F(x['with_refinance']['replacement_reserve_released']),4);self.assertEqual(F(x['tdc']),116)


 def test_refinance_cash_in_increases_coc_denominator_without_changing_other_flows(self):
  s,d=fixture();s['refinance']['cost_fraction']='0.1';x=integrate(s,d);r=x['with_refinance'];self.assertEqual(r['state'],'CALCULATED');self.assertEqual(F(r['refinance_net']),-10);self.assertEqual(F(r['first_year_cash']),14);self.assertEqual(F(r['post_refi_coc']),Q(14,26));self.assertEqual(F(r['cash_per_usd_10']['total_contributions']),26);self.assertEqual(F(r['cash_per_usd_10']['total_distributions']),124)

class MonthlyComponentBoundaryTests(TestCase):
 def test_source_use_on_stabilization_date_is_paid_at_actual_date(self):
  s,d=fixture();c=s['construction'];c['periods'][-1]['events'].append(dict(id='closing-tax',kind='use',date=c['stabilization'],amount='4',source_ref='SYNTHETIC-tax'));r=construction(c);self.assertEqual(r['state'],'CALCULATED',r);self.assertEqual(F(r['total_contributions']),20)
 def test_commercial_receipt_is_a_separate_source_not_negative_cost(self):
  s,d=fixture();c=s['construction'];c['periods'][1]['events'].append(dict(id='receipt',kind='receipt',date='2026-11-01',amount='1',source_ref='SYNTHETIC-rent'));r=construction(c);self.assertEqual(r['state'],'CALCULATED');self.assertEqual(F(r['other_sources']),1);self.assertEqual(F(r['total_contributions']),15)
