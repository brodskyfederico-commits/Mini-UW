import copy,hashlib,json,tempfile,unittest
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.investor_returns import produce_investor_returns,parse_investor_returns,definition_sources
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def f(p):return F(int(p['numerator']),int(p['denominator']))


class InvestorReturnsTests(unittest.TestCase):
    def setUp(self):self.source=(R/'templates/synthetic-investor-returns.json').read_bytes();self.case=json.loads(self.source)
    def run_case(self,p=None):return produce_investor_returns(raw(self.case if p is None else p))

    def test_gross_profit_and_multiple_independent_hand_calculation(self):
        p=self.run_case().payload
        self.assertEqual([p[k]for k in ['gross_contributions','gross_distributions','net_cash_profit','equity_multiple']],[q(F(1000)),q(F(1600)),q(F(600)),q(F(8,5))])
        self.assertEqual([f(r['net'])for r in p['dated_net_flows']],[-1000,600,1000]);self.assertTrue(p['declared_cash_story_computable'])

    def test_ten_dollar_story_preserves_dates_and_categories(self):
        n=self.run_case().payload['normalized_story'];self.assertEqual([f(e['amount'])for e in n['events']],[10,5,1,1,9])
        self.assertEqual([e['date']for e in n['events']],[e['date']for e in self.case['events']])
        self.assertEqual(f(n['total_distributions']),16);self.assertEqual(f(n['net_cash_profit']),6)

    def test_retained_value_and_capital_are_not_cash(self):
        p=self.run_case().payload;s=p['capital_snapshots'][0]
        self.assertEqual(f(s['normalized_capital_still_invested']),5);self.assertEqual(f(s['normalized_retained_equity_value']),8)
        self.case['capital_snapshots'][0]['retained_equity_value']=q(F(999999))
        changed=self.run_case().payload
        for field in ['gross_distributions','net_cash_profit','equity_multiple','periodic_irr']:self.assertEqual(p[field],changed[field])
        self.assertFalse(p['retained_equity_included_in_cash_receipts'])

    def test_same_date_gross_events_not_reconstructed_from_net(self):
        before=self.run_case().payload
        for kind,cat in [('contribution','additional_capital'),('distribution','other_distribution')]:
            self.case['events'].append(dict(event_id='circular-'+kind,date='2028-01-01',kind=kind,category=cat,amount=q(F(100)),currency='USD',source_ref='SYNTHETIC-explicit-movement'))
        after=self.run_case().payload;self.assertEqual(before['dated_net_flows'],after['dated_net_flows'])
        self.assertEqual(f(after['equity_multiple']),F(17,11));self.assertNotEqual(before['equity_multiple'],after['equity_multiple'])
        self.assertEqual(f(after['normalized_story']['total_contributions']),11)

    def test_explicit_additional_cash_in_and_normalization_basis(self):
        self.case['events'].append(dict(event_id='cash-in',date='2028-01-01',kind='contribution',category='refinance_cash_in',amount=q(F(200)),currency='USD',source_ref='SYNTHETIC-cash-in'))
        p=self.run_case().payload;self.assertEqual(f(p['cash_by_category']['refinance_cash_in']),200)
        self.assertEqual(f(p['normalized_story']['total_contributions']),12);self.assertEqual(f(p['net_cash_profit']),400)
        self.case['normalization']['contribution_event_ids'].append('cash-in')
        n=self.run_case().payload['normalized_story'];self.assertEqual(f(n['total_contributions']),10);self.assertEqual(f(n['events'][0]['amount']),F(25,3))

    def test_missing_inventory_blocks_all_cash_totals(self):
        for value in [None,False]:
            self.case['event_inventory_declared_complete']=value;p=self.run_case().payload
            self.assertIsNone(p['gross_distributions']);self.assertIsNone(p['periodic_irr']);self.assertFalse(p['declared_cash_story_computable'])

    def test_missing_amount_negative_currency_date_and_source_each_block(self):
        for field,value in [('amount',None),('amount',q(F(-1))),('currency','EUR'),('date','2028-02-01'),('source_ref',None)]:
            c=copy.deepcopy(self.case);c['events'][1][field]=value;p=self.run_case(c).payload
            self.assertEqual(p['cash_metrics_state'],'blocked');self.assertIsNone(p['gross_contributions']);self.assertTrue(p['cash_blockers'])
            self.assertEqual(p['events'][1][field],value)

    def test_explicit_zero_kept_distinct_from_missing(self):
        self.case['events'][1]['amount']=q(F(0));p=self.run_case().payload
        self.assertEqual(f(p['cash_by_category']['net_refinance_distribution']),0);self.assertEqual(f(p['gross_distributions']),1100)

    def test_normalization_needs_declared_positive_amount_basis_and_contribution(self):
        for field,value in [('reference_amount',None),('reference_amount',q(F(0))),('basis_ref',None),('contribution_event_ids',[]),('contribution_event_ids',['sale']),('contribution_event_ids',['unknown'])]:
            c=copy.deepcopy(self.case);c['normalization'][field]=value;p=self.run_case(c).payload
            self.assertEqual(p['cash_metrics_state'],'computed_synthetic');self.assertIsNone(p['normalized_story']['events']);self.assertFalse(p['declared_cash_story_computable'])

    def test_annual_operating_cash_and_conditional_coc_exclude_sale_and_refi(self):
        rows=self.run_case().payload['annual_cash_receipts'];self.assertEqual([f(r['operating_distributions_only'])for r in rows],[0,100,100])
        self.assertEqual([f(r['conditional_coc'])for r in rows],[0,F(1,5),F(1,5)])
        self.assertTrue(all(not r['operating_year_coverage_financially_verified']for r in rows))

    def test_missing_or_zero_annual_capital_base_keeps_cash_not_coc(self):
        for bases in [[],[dict(self.case['annual_cash_bases'][0],capital_base=q(F(0)))]]:
            c=copy.deepcopy(self.case);c['annual_cash_bases']=bases;p=self.run_case(c).payload
            self.assertEqual(f(p['gross_distributions']),1600);self.assertIsNone(p['annual_cash_receipts'][0]['conditional_coc']);self.assertTrue(p['story_blockers'])

    def test_snapshots_are_required_declared_not_derived_and_metadata_guarded(self):
        self.case['capital_snapshots']=[];p=self.run_case().payload;self.assertFalse(p['declared_cash_story_computable']);self.assertEqual(f(p['net_cash_profit']),600)
        self.case=json.loads(self.source);self.case['capital_snapshots'][0]['currency']='EUR';s=self.run_case().payload['capital_snapshots'][0]
        self.assertIsNone(s['normalized_retained_equity_value']);self.assertFalse(s['retained_value_included_in_receipts'])

    def test_periodic_and_annual_root_intervals_certify_quadratic(self):
        p=self.run_case().payload;self.assertEqual(p['periodic_irr']['distinct_positive_discount_roots'],1)
        i=p['annual_irr_roots'][0]['annual_rate_interval'];lo,hi=f(i['lower']),f(i['upper'])
        # -1000(1+r)^2+600(1+r)+1000 changes sign across the isolated root.
        poly=lambda r:-1000*(1+r)**2+600*(1+r)+1000
        self.assertGreaterEqual(poly(lo),0);self.assertLessEqual(poly(hi),0);self.assertLessEqual(hi-lo,F(1,1000000))
        self.assertIsNone(p['selected_IRR'])

    def test_annualization_missing_or_inconsistent_does_not_invent_rate(self):
        for freq in [None,12]:
            self.case['irr_parameters']['periods_per_year']=freq;p=self.run_case().payload
            self.assertEqual(p['annual_irr_roots'],[]);self.assertFalse(p['declared_cash_story_computable']);self.assertEqual(f(p['net_cash_profit']),600)

    def test_monthly_annualization_is_compounding_with_open_endpoints_preserved(self):
        self.case['grid']['step_months']=1;self.case['grid']['dates']=['2027-01-01','2027-02-01','2027-03-01'];self.case['irr_parameters']['periods_per_year']=12
        for e in self.case['events']:e['date']={'2028-01-01':'2027-02-01','2029-01-01':'2027-03-01'}.get(e['date'],e['date'])
        self.case['capital_snapshots'][0]['as_of_date']='2027-02-01';p=self.run_case().payload
        periodic=p['periodic_irr']['roots'][0]['periodic_rate_interval'];annual=p['annual_irr_roots'][0]['annual_rate_interval']
        self.assertEqual(f(annual['lower']),(1+F(periodic['lower']))**12-1);self.assertEqual(annual['upper_closed'],periodic['upper_closed'])

    def test_multiple_roots_retained_and_pending(self):
        self.case['events']=[dict(self.case['events'][0],event_id='a',amount=q(F(100))),dict(self.case['events'][1],event_id='d',amount=q(F(230))),dict(self.case['events'][0],event_id='b',date='2029-01-01',category='additional_capital',amount=q(F(132)))]
        self.case['normalization']['contribution_event_ids']=['a'];p=self.run_case().payload
        self.assertEqual(p['periodic_irr']['distinct_positive_discount_roots'],2);self.assertEqual(len(p['annual_irr_roots']),2);self.assertFalse(p['declared_cash_story_computable']);self.assertIsNone(p['selected_IRR'])

    def test_irr_work_exhaustion_keeps_gross_cash_and_pending(self):
        self.case['irr_parameters']['operation_budget']=1;p=self.run_case().payload
        self.assertEqual(f(p['net_cash_profit']),600);self.assertFalse(p['declared_cash_story_computable']);self.assertEqual(p['periodic_irr']['status'],'incomplete_synthetic')

    def test_zero_capital_undefined_multiple_and_no_events_not_approved(self):
        self.case['events']=[];p=self.run_case().payload
        self.assertEqual(f(p['gross_contributions']),0);self.assertIsNone(p['equity_multiple']);self.assertEqual(p['periodic_irr']['status'],'indeterminate');self.assertFalse(p['declared_cash_story_computable'])

    def test_no_cash_year_or_grid_point_compressed(self):
        self.case['grid']['dates']=['2027-01-01','2028-01-01','2029-01-01','2030-01-01'];p=self.run_case().payload
        self.assertEqual(len(p['dated_net_flows']),4);self.assertEqual(f(p['dated_net_flows'][-1]['net']),0)
        self.assertEqual(p['annual_cash_receipts'][-1]['calendar_cash_receipt_year'],2030);self.assertEqual(f(p['annual_cash_receipts'][-1]['operating_distributions_only']),0)

    def test_duplicate_unclassified_and_live_data_rejected(self):
        for mutate in [lambda c:c['events'].append(copy.deepcopy(c['events'][0])),lambda c:c['events'][0].update(category='bank_draw'),lambda c:c['context'].update(deal_id='real-deal'),lambda c:c.update(equity_level='LP')]:
            c=copy.deepcopy(self.case);mutate(c)
            with self.assertRaises(ValidationError):self.run_case(c)

    def test_irregular_grid_and_month_end_not_adjusted(self):
        self.case['grid']['dates'][1]='2028-02-01'
        with self.assertRaises(ValidationError):self.run_case()
        self.case['grid'].update(step_months=1,dates=['2027-01-31','2027-02-28'])
        with self.assertRaises(ValidationError):parse_investor_returns(raw(self.case))

    def test_source_identity_payload_immutability_and_definition_locators(self):
        run=self.run_case();p=run.payload;p['net_cash_profit']=q(F(999))
        self.assertEqual(f(run.payload['net_cash_profit']),600);self.assertEqual(run.sha256,digest(run.payload_json))
        self.assertEqual(run.payload['source_sha256'],hashlib.sha256(raw(self.case)).hexdigest())
        for ref in definition_sources():self.assertEqual(ref['sha256'],hashlib.sha256((R/ref['path']).read_bytes()).hexdigest())
        self.case['events'][0]['source_ref']='SYNTHETIC-new-evidence';self.assertNotEqual(run.sha256,self.run_case().sha256)

    def test_reopened_archive_exact_retry_and_source_preserved(self):
        run=produce_investor_returns(self.source)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'investor.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_investor_returns(self.source,run);self.assertEqual(key,a.save_investor_returns(self.source,run))
            with EvidenceArchive(path)as a:
                b=a.load_investor_returns(key);self.assertEqual(b.run,run);self.assertEqual(a.get_investor_returns_source(b.payload['source_sha256']),self.source)

    def test_archive_rejects_forgery_rollback_incompatible_and_missing_source(self):
        run=produce_investor_returns(self.source);p=run.payload;p['net_cash_profit']=q(F(9999));enc=canonical(p);fake=replace(run,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_investor_returns(self.source,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_investor_returns(self.source,run)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_investor_returns(self.source,run);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_investor_returns(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_investor_returns(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',hashlib.sha256(self.source).hexdigest()))
            with self.assertRaises(MissingEvidence):a.load_investor_returns(key)

    def test_operational_decisions_remain_pending(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for k in ['run_ready','review_authenticated','production_authorized','financial_module_closed','LP_allocation_applied','cash_source_and_scope_financially_verified']:self.assertFalse(p[k])
