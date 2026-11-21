from unittest import TestCase
from copy import deepcopy
from fractions import Fraction as Q
from worksheet_monthly_D275 import construction,monthly_irr,SCHEMA,day_fraction
from worksheet_frontiers_D275 import fraction
from datetime import date


def fixture():
 return dict(schema=SCHEMA,currency='USD',scenario='Base',start='2026-10-01',stabilization='2027-04-01',maturity='2027-04-01',annual_rate='0.12',ltc='1',eligible_total='100',maximum_commitment='100',fee_fraction='0',initial_equity='10',opening_free_cash='0',opening_principal='0',principal_payment_mode='interest_only_until_stabilization',other_costs_and_limits_complete=True,equity_policy='initial_then_top_up_for_sourced_uses',interest_payment_every_months=3,pay_interest_at_stabilization=True,day_count='30E/360',source_ref='SYNTHETIC-monthly-bank',periods=[dict(start=a,end=b,inventory_complete=True,source_ref='SYNTHETIC-month-'+a,events=([dict(id='draw',invoice_id='SYNTHETIC-INVOICE1',kind='draw',date=a,amount='100',eligible_invoice='100',available_new_draw='100',source_ref='SYNTHETIC-draw'),dict(id='invoice',kind='use',date=a,amount='110',source_ref='SYNTHETIC-use')] if i==0 else [])) for i,(a,b) in enumerate(zip(['2026-10-01','2026-11-01','2026-12-01','2027-01-01','2027-02-01','2027-03-01'],['2026-11-01','2026-12-01','2027-01-01','2027-02-01','2027-03-01','2027-04-01']))])

class MonthlyTests(TestCase):
 def test_quarter_checkpoint_cash_exactly_matches_quarterly_simple_convention(self):
  a=construction(fixture());self.assertEqual(a['state'],'CALCULATED');self.assertEqual(fraction(a['interest_total']),6);self.assertEqual(fraction(a['total_contributions']),16)
  self.assertEqual([(e['date'],fraction(e['amount'])) for e in a['equity_events']],[('2026-10-01',10),('2027-01-01',3),('2027-04-01',3)])
 def test_draw_mid_month_accrues_only_remaining_actual_days(self):
  s=fixture();s['day_count']='ACT/360';s['periods'][0]['events'][0]['date']='2026-10-16';s['periods'][0]['events'][1]['date']='2026-10-16'
  a=construction(s);self.assertEqual(fraction(a['months'][0]['interest_accrued']),100*Q(12,100)*Q(16,360))
 def test_calendar_crosses_first_january_without_losing_month(self):
  a=construction(fixture());self.assertEqual(len(a['months']),6);self.assertEqual(a['months'][2]['end'],'2027-01-01')
 def test_missing_month_or_inventory_never_becomes_zero(self):
  for fault in ['month','inventory','events','rate','convention']:
   s=fixture()
   if fault=='month':s['periods'].pop(1)
   if fault=='inventory':s['periods'][1].pop('inventory_complete')
   if fault=='events':s['periods'][1]['events']=None
   if fault=='rate':s['annual_rate']=None
   if fault=='convention':s['day_count']=None
   self.assertEqual(construction(s)['state'],'PENDING',fault)
 def test_ambiguous_30_360_is_not_assumed(self):
  s=fixture();s['day_count']='30/360';self.assertEqual(construction(s)['state'],'PENDING')
 def test_explicit_zero_interest_is_preserved(self):
  s=fixture();s['annual_rate']='0';a=construction(s);self.assertEqual(a['state'],'CALCULATED');self.assertEqual(fraction(a['interest_total']),0)
 def test_requested_draw_exceeding_capacity_stays_pending(self):
  for key in ['ltc','maximum_commitment']:
   s=fixture();s[key]='0.5' if key=='ltc' else '50';self.assertEqual(construction(s)['state'],'PENDING')
 def test_monthly_interest_cash_has_own_dates(self):
  s=fixture();s['interest_payment_every_months']=1;a=construction(s);self.assertEqual(len(a['equity_events']),7);self.assertEqual(fraction(a['total_contributions']),16)
 def test_monthly_irr_matches_quarterly_annualization(self):
  dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01'];a=monthly_irr(dates,[-10,0,0,11],'SYNTHETIC-monthly-ledger')
  self.assertEqual(a['state'],'CERTIFIED');exact=Q(11,10)**4-1
  self.assertLessEqual(fraction(a['annual_enclosure']['lower']),exact);self.assertGreaterEqual(fraction(a['annual_enclosure']['upper']),exact)
 def test_missing_month_irr_pending_and_multiple_roots_not_selected(self):
  a=monthly_irr(['2027-01-01','2027-03-01'],[-10,11],'SYNTHETIC-missing');self.assertEqual(a['state'],'PENDING')
  a=monthly_irr(['2027-01-01','2027-02-01','2027-03-01'],[-100,230,-132],'SYNTHETIC-multiple');self.assertEqual(a['state'],'PENDING');self.assertIsNone(a['annual_enclosure'])
 def test_input_not_mutated(self):
  s=fixture();old=deepcopy(s);construction(s);self.assertEqual(s,old)

class MonthlySettlementTests(TestCase):
 def test_same_day_draw_and_interest_are_net_funded_without_intraday_assumption(self):
  s=fixture();s['periods'][0]['events'][0].update(amount='50',eligible_invoice='50');s['periods'][0]['events'][1]['amount']='60'
  s['periods'][3]['events']=[dict(id='draw2',invoice_id='SYNTHETIC-INVOICE2',kind='draw',date='2027-01-01',amount='50',eligible_invoice='50',available_new_draw='50',source_ref='SYNTHETIC-second-draw'),dict(id='use2',kind='use',date='2027-01-01',amount='48.5',source_ref='SYNTHETIC-use2')]
  a=construction(s);self.assertEqual(a['state'],'CALCULATED');self.assertEqual([(e['date'],fraction(e['amount'])) for e in a['equity_events']],[('2026-10-01',10),('2027-04-01',3)])
 def test_duplicate_invoice_or_eligible_inventory_overrun_blocks(self):
  s=fixture();extra=deepcopy(s['periods'][0]['events'][0]);extra.update(id='draw2',amount='0');s['periods'][0]['events'].append(extra);self.assertEqual(construction(s)['state'],'PENDING')
 def test_initial_topup_is_not_hidden_in_the_basis(self):
  s=fixture();s['initial_equity']='1';self.assertEqual(construction(s)['state'],'PENDING')

class ExplicitOpeningTermsTests(TestCase):
 def test_missing_opening_principal_or_interest_only_terms_are_not_zero(self):
  for key in ['opening_principal','principal_payment_mode','other_costs_and_limits_complete']:
   s=fixture();s.pop(key);self.assertEqual(construction(s)['state'],'PENDING')
