import copy,json,sys,unittest
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demo_preopening_cash import make_source,make_operation,make_binding,raw,claim
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.preopening_cash import reconcile_preopening_cash,parse_preopening_cash,link_preopening_to_operation

def f(record):return Fraction(int(record['numerator']),int(record['denominator']))


class PreopeningCashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.period=make_operation()
    def setUp(self):self.source=make_source(self.period.cash_run.payload['context'])
    def run_source(self):return reconcile_preopening_cash(raw(self.source))
    def test_hand_cash_principal_and_reserve_conservation(self):
        p=self.run_source().payload;t=p['totals'];last=p['date_close_balances'][-1]
        self.assertEqual(p['state'],'reconciled_synthetic_preopening_cash');self.assertEqual(f(last['free_cash']),1000);self.assertEqual(f(last['restricted_cash']),0)
        self.assertEqual(f(last['loan_principal']['SYNTHETIC-preopening-loan']),500);self.assertEqual(f(p['cash_conservation_residual']),0)
        self.assertEqual(f(t['initial_equity_contribution'])+f(t['additional_equity_contribution']),1800)
        self.assertEqual(1800+600+100,400+800+100+100+20+5+25+50+1000)
        self.assertEqual(f(t['reserve_deposit']),200);self.assertEqual(f(t['reserve_release']),200)
    def test_gross_same_day_equity_and_explicit_zero_preserved(self):
        p=self.run_source().payload;events=p['exportable_equity_movements']
        self.assertEqual([f(e['amount'])for e in events],[1500,300,25,0]);self.assertEqual(events[1]['date'],events[2]['date'])
        self.assertEqual(events[-1]['category'],'additional_capital');self.assertEqual(events[0]['source_pointer'],'/events/0/amount')
        self.assertEqual(events[0]['source_sha256'],p['source_sha256'])
    def test_paid_interest_and_fee_do_not_reduce_principal(self):
        p=self.run_source().payload;self.assertEqual(f(p['date_close_balances'][-1]['loan_principal']['SYNTHETIC-preopening-loan']),600-100)
        self.assertTrue(p['interest_and_fees_are_supplied_cash_not_calculated']);self.assertFalse(p['debt_schedule_and_maturity_verified'])
    def test_missing_zero_negative_currency_and_provenance_are_distinct(self):
        for key,value,marker in [('value',None,'amount_missing'),('value',claim(-1)['value'],'gross_amount_negative'),('currency','EUR','currency_mismatch'),('source_ref',None,'source_ref_missing')]:
            self.setUp();self.source['events'][0]['amount'][key]=value;p=self.run_source().payload
            self.assertTrue(any(marker in b for b in p['blockers']));self.assertIsNone(p['totals']);self.assertIsNone(p['exportable_equity_movements'])
    def test_scope_and_all_basis_declarations_required(self):
        for key in ['inventory_declared_complete','zero_opening_basis_ref','classification_basis_ref','boundary_basis_ref']:
            self.setUp();self.source[key]=None;p=self.run_source().payload;self.assertEqual(p['state'],'blocked');self.assertIsNone(p['exportable_equity_movements'])
    def test_terminal_cash_and_each_loan_claim_must_match(self):
        for account in ['free_cash','restricted_cash','loan_principal']:
            self.setUp();row=self.source['terminal_claims'][account]
            if account=='loan_principal':row=row['SYNTHETIC-preopening-loan']
            row['value']=claim(999)['value'];p=self.run_source().payload
            self.assertTrue(any('terminal_claim_mismatch'in b for b in p['blockers']));self.assertIsNone(p['exportable_equity_movements'])
    def test_terminal_metadata_or_value_missing_blocks(self):
        for key,value in [('value',None),('currency','EUR'),('source_ref',None)]:
            self.setUp();self.source['terminal_claims']['free_cash'][key]=value;self.assertEqual(self.run_source().payload['state'],'blocked')
    def test_unknown_or_missing_loan_not_implicitly_created(self):
        for loan in [None,'SYNTHETIC-unknown']:
            self.setUp();self.source['events'][2]['loan_id']=loan;p=self.run_source().payload
            self.assertIn('SYNTHETIC-preopening-event-2:declared_loan_identity_missing_or_unknown',p['blockers']);self.assertIsNone(p['totals'])
    def test_early_cash_deficit_not_repaired_by_later_contribution(self):
        self.source['events'][0]['amount']=claim(300);self.source['events'][6]['amount']=claim(1500)
        p=self.run_source().payload;self.assertEqual(f(p['date_close_balances'][-1]['free_cash']),1000)
        self.assertIn('2026-10-01:free_cash:negative_date_close_balance',p['blockers']);self.assertIsNone(p['exportable_equity_movements'])
    def test_restricted_cash_cannot_be_spent_as_free_or_released_without_deposit(self):
        self.source['events'][13]['amount']=claim(201);p=self.run_source().payload
        self.assertIn('2026-12-01:restricted_cash:negative_date_close_balance',p['blockers'])
    def test_principal_overpayment_blocks_even_with_enough_cash(self):
        self.source['events'][7]['amount']=claim(601);p=self.run_source().payload
        self.assertIn('2026-12-01:loan:SYNTHETIC-preopening-loan:negative_date_close_balance',p['blockers'])
    def test_same_date_order_is_not_intraday_liquidity_proof(self):
        original=self.run_source().payload;self.source['events'][:2]=reversed(self.source['events'][:2]);changed=self.run_source().payload
        self.assertEqual(changed['date_close_balances'],original['date_close_balances']);self.assertEqual(changed['state'],'reconciled_synthetic_preopening_cash')
        self.assertFalse(changed['intraday_order_and_liquidity_verified'])
    def test_loan_free_and_zero_cash_profile_is_explicit(self):
        self.source['loan_ids']=[];self.source['events']=[dict(event_id='SYNTHETIC-zero',date='2026-10-01',category='initial_equity_contribution',loan_id=None,amount=claim(0))]
        self.source['terminal_claims']=dict(free_cash=claim(0),restricted_cash=claim(0),loan_principal={})
        p=self.run_source().payload;self.assertEqual(p['state'],'reconciled_synthetic_preopening_cash');self.assertEqual(p['date_close_balances'][0]['loan_principal'],{})
    def test_strict_schema_date_order_duplicates_and_unsupported_non_cash(self):
        variants=[]
        for key,value in [('events',[]),('loan_ids',['same','same']),('profile','real'),('opening_operation_date','2026-10-01')]:
            s=copy.deepcopy(self.source);s[key]=value;variants.append(s)
        for key,value in [('event_id',self.source['events'][1]['event_id']),('date','2026-09-01'),('category','capitalized_interest')]:
            s=copy.deepcopy(self.source);s['events'][0][key]=value;variants.append(s)
        s=copy.deepcopy(self.source);s['events'][2],s['events'][0]=s['events'][0],s['events'][2];variants.append(s)
        s=copy.deepcopy(self.source);s['events'][0]['loan_id']='SYNTHETIC-improper';variants.append(s)
        s=copy.deepcopy(self.source);s['context']['deal_id']='real';variants.append(s)
        s=copy.deepcopy(self.source);s['terminal_claims']['loan_principal']={};variants.append(s)
        for s in variants:
            with self.assertRaises(ValidationError):parse_preopening_cash(raw(s))
    def test_duplicate_json_constants_byte_and_size_limits(self):
        for data in [b'{"schema":1,"schema":2}',b'{"schema":NaN}',b'\xff',b'x'*1_048_577,'{}']:
            with self.assertRaises(ValidationError):parse_preopening_cash(data)
    def test_arithmetic_failure_never_exports_partial_equity(self):
        with patch('miniuw_foundation.preopening_cash._bounded',side_effect=ArithmeticBudgetError('test')):p=self.run_source().payload
        self.assertEqual(p['blockers'],['preopening_exact_arithmetic_budget_exceeded']);self.assertIsNone(p['totals']);self.assertIsNone(p['date_close_balances']);self.assertIsNone(p['exportable_equity_movements'])
    def test_real_denominator_growth_budget_stops_without_approximation(self):
        self.source['loan_ids']=[];self.source['terminal_claims']=dict(free_cash=claim(0),restricted_cash=claim(0),loan_principal={})
        denominators=[2**845,3**535,5**365,7**301,11**244,13**229]
        self.source['events']=[dict(event_id='SYNTHETIC-fraction-'+str(i),date='2026-10-01',category='initial_equity_contribution',loan_id=None,amount=claim(Fraction(1,d)))for i,d in enumerate(denominators)]
        p=self.run_source().payload;self.assertEqual(p['blockers'],['preopening_exact_arithmetic_budget_exceeded']);self.assertIsNone(p['totals']);self.assertIsNone(p['exportable_equity_movements'])
    def test_each_loan_balance_kept_separate_including_unused_zero(self):
        self.source['loan_ids'].append('SYNTHETIC-unused');self.source['terminal_claims']['loan_principal']['SYNTHETIC-unused']=claim(0)
        p=self.run_source().payload;self.assertEqual(p['state'],'reconciled_synthetic_preopening_cash');self.assertEqual(f(p['date_close_balances'][-1]['loan_principal']['SYNTHETIC-unused']),0)
        self.source['events'][7]['loan_id']='SYNTHETIC-unused';p=self.run_source().payload
        self.assertIn('2026-12-01:loan:SYNTHETIC-unused:negative_date_close_balance',p['blockers']);self.assertIsNone(p['exportable_equity_movements'])
    def test_payload_immutable_and_run_bound_to_source_definition(self):
        run=self.run_source();p=run.payload;p['events'].clear();self.assertEqual(len(run.payload['events']),15);self.assertEqual(run.sha256,digest(run.payload_json))
        self.assertEqual(len(run.payload['definition_sources']),3)
    def link(self,source=None,period=None,binding_change=None,run_change=None):
        source=raw(self.source)if source is None else source;period=self.period if period is None else period;run=reconcile_preopening_cash(source)
        b=make_binding(source,run,period)
        if binding_change:b.update(binding_change)
        if run_change:run=run_change(run)
        return link_preopening_to_operation(source,run,period,raw(b))
    def test_full_cash_only_link_and_no_double_counted_seed(self):
        p=self.link().payload;self.assertEqual(p['state'],'matched_synthetic_cash_only');self.assertEqual(len(p['cash_boundary_checks']),2)
        self.assertTrue(all(c['equal_exact_value']for c in p['cash_boundary_checks']));self.assertTrue(p['opening_cash_must_not_be_added_as_another_equity_contribution'])
        self.assertTrue(p['debt_carry_reconciliation_pending']);self.assertFalse(p['whole_project_investor_returns_connected'])
    def test_balanced_preopening_free_and_restricted_reset_not_accepted(self):
        self.source['events'][13]['amount']=claim(199);self.source['terminal_claims']['free_cash']=claim(999);self.source['terminal_claims']['restricted_cash']=claim(1)
        self.assertEqual(self.run_source().payload['state'],'reconciled_synthetic_preopening_cash');p=self.link().payload
        self.assertIn('free_cash:opening_does_not_equal_preopening_close',p['blockers']);self.assertIn('restricted_cash:opening_does_not_equal_preopening_close',p['blockers'])
    def test_link_hashes_time_context_currency_and_basis_guards(self):
        for key in ['preopening_source_sha256','preopening_run_sha256','operating_source_sha256','operating_run_sha256']:
            self.assertIn(key+'_mismatch',self.link(binding_change={key:'0'*64}).payload['blockers'])
        self.assertEqual(self.link(binding_change={'boundary_basis_ref':None}).payload['state'],'blocked')
        self.source['opening_operation_date']='2027-02-01';self.assertIn('preopening_operation_boundary_date_mismatch',self.link().payload['blockers'])
        self.setUp();self.source['context']['run_id']='SYNTHETIC-other';self.assertIn('preopening_operation_context_mismatch',self.link().payload['blockers'])
        self.setUp();self.source['currency']='EUR'
        for event in self.source['events']:event['amount']['currency']='EUR'
        for row in [self.source['terminal_claims']['free_cash'],self.source['terminal_claims']['restricted_cash'],*self.source['terminal_claims']['loan_principal'].values()]:row['currency']='EUR'
        self.assertIn('preopening_operation_currency_mismatch',self.link().payload['blockers'])
    def test_preopening_blocker_and_operating_blocker_remain_visible(self):
        self.source['events'][0]['amount']['value']=None;p=self.link().payload;self.assertIn('preopening_cash_blocked',p['blockers']);self.assertTrue(p['preopening_blockers'])
        self.setUp();spec=json.loads(self.period.spec_raw);spec['amounts']['noncash_expense']['value']=None;sr=raw(spec)
        period=replace(self.period,spec_raw=sr,cash_run=reconcile_operating_cash(self.period.noi_raw,self.period.noi_run,sr));p=self.link(period=period).payload
        self.assertIn('opening_operating_cash_blocked',p['blockers']);self.assertTrue(p['operating_blockers'])
    def test_nonzero_opening_accruals_need_separate_profile(self):
        spec=json.loads(self.period.spec_raw)
        for key in ['opening','closing']:spec['working_balances']['receivables'][key]['value']=claim(1)['value']
        sr=raw(spec);period=replace(self.period,spec_raw=sr,cash_run=reconcile_operating_cash(self.period.noi_raw,self.period.noi_run,sr))
        self.assertEqual(period.cash_run.payload['state'],'reconciled_synthetic_plan');self.assertIn('receivables:nonzero_opening_working_balance_requires_separate_profile',self.link(period=period).payload['blockers'])
    def test_rehashed_preopening_and_operating_forgery_rejected(self):
        def fake(run):
            p=run.payload;p['state']='reconciled_synthetic_preopening_cash';p['date_close_balances'][-1]['free_cash']=claim(999)['value'];s=canonical(p)
            return replace(run,payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):self.link(run_change=fake)
        p=self.period.cash_run.payload;p['state']='forged';s=canonical(p);period=replace(self.period,cash_run=replace(self.period.cash_run,payload_json=s,sha256=digest(s)))
        with self.assertRaises(ValidationError):self.link(period=period)
    def test_cash_profile_does_not_claim_financial_completion(self):
        p=self.run_source().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['loan_commitment_or_availability_verified','debt_schedule_and_maturity_verified','intraday_order_and_liquidity_verified','asset_cost_basis_or_complete_TDC_verified','actual_cash_and_payment_history_verified','investor_returns_connected','financial_module_closed','production_authorized']:self.assertFalse(p[key])


if __name__=='__main__':unittest.main()
