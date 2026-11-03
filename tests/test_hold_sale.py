import copy,json,sys,unittest
from pathlib import Path
from fractions import Fraction
from dataclasses import replace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hold_sale_demo_support import sources,build,raw,q,claim,sha
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.hold_sale_cash import reconcile_hold_sale_cash
from miniuw_foundation.hold_sale_opening import reconcile_hold_sale_opening
from miniuw_foundation.hold_sale_returns import assemble_hold_sale_returns
from miniuw_foundation.hold_sale_bundle import export_hold_sale_bundle,recover_hold_sale_bundle
from miniuw_foundation.current_hold_sale import required_hold_sale_sources,assemble_current_hold_sale
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.operating_noi import ArithmeticBudgetError

def f(r):return Fraction(int(r['numerator']),int(r['denominator']))
def forged(run,change):
    p=run.payload;change(p);s=canonical(p);return replace(run,payload_json=s,sha256=digest(s))
def data_case(change=None,**kw):
    d=sources()
    if change:change(d)
    return build(d,**kw)
def current_registry(recovered,bundle):
    rows=required_hold_sale_sources(recovered,bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=recovered.run.payload['context'],inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-declared-all-transport',requirements=rows,
        evidence=[dict(evidence_id='SYNTHETIC-hold-sale-'+str(i),**r,issued_at='2027-01-01T00:00:00Z',valid_from='2027-01-01T00:00:00Z',valid_until='2027-07-02T00:00:00Z',review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,basis_ref='SYNTHETIC-express-test-validity-not-professional-review')for i,r in enumerate(rows)])
AT='2027-07-01T12:00:00Z'


class HoldSaleCashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=data_case()
    def test_hand_cash_conservation_debt_and_reserves(self):
        p=self.case[0][7].payload;t=p['totals'];self.assertEqual(p['state'],'reconciled_synthetic_no_refinance_cash');self.assertEqual(f(p['cash_conservation_residual']),0)
        self.assertEqual(f(t['debt_principal']),120);self.assertEqual(f(t['debt_fees']),10);self.assertEqual(f(t['reserve_deposits']),100);self.assertEqual(f(t['reserve_releases']),100)
        self.assertEqual(f(t['equity_distributions']),1360);self.assertEqual(1000+150+400,120+10+40+20+1360)
        self.assertEqual([f(r['scheduled_principal'])for r in p['operating_debt_checks']],[30,30]);self.assertEqual(len(p['cash_boundary_checks']),2)
    def test_original_april_maturity_is_not_extended_to_sale(self):
        def change(d):d['loans'][0].update(maturity_payment=4,payment_dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01'])
        c=data_case(change);p=c[0][7].payload;self.assertEqual(p['state'],'blocked');self.assertTrue(p['sale_debt_blockers']);self.assertFalse(p['refinance_or_loan_extension_generated']);self.assertIsNone(c[-1].compiled_raw)
    def test_balanced_sale_cash_reset_is_rejected(self):
        c=data_case(lambda d:d['sale']['amounts']['opening_free_cash'].update(value=q(751)));self.assertEqual(c[0][3].closing_run.payload['state'],'computed_synthetic_closing')
        self.assertIn('free:sale_opening_cash_does_not_match_holding_close',c[0][7].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
    def test_restricted_account_checked_separately(self):
        def change(d):
            d['sale']['amounts']['opening_restricted_cash']['value']=q(101);d['sale']['amounts']['closing_restricted_cash_claim']['value']=q(1)
        c=data_case(change);self.assertEqual(c[0][3].closing_run.payload['state'],'computed_synthetic_closing');self.assertIn('restricted:sale_opening_cash_does_not_match_holding_close',c[0][7].payload['blockers'])
    def test_individually_balanced_wrong_principal_cash_not_accepted(self):
        def change(d):
            for i,value in [(0,859),(1,749)]:d['ops'][i]['amounts']['closing_free_cash_claim']['value']=q(value)
            d['ops'][0]['amounts']['debt_principal_payment']['value']=q(31);d['ops'][1]['amounts']['opening_free_cash']['value']=q(859);d['sale']['amounts']['opening_free_cash']['value']=q(749)
        c=data_case(change);self.assertEqual(c[0][5].payload['state'],'reconciled_synthetic_operating_chain');self.assertTrue(any('operating_debt_cash_differs'in b for b in c[0][7].payload['blockers']))
    def test_terminal_working_balances_not_silently_zeroed(self):
        def change(d):
            for op in d['ops']:
                for cutoff in ['opening','closing']:op['working_balances']['receivables'][cutoff]['value']=q(1)
        c=data_case(change);self.assertEqual(c[0][5].payload['state'],'reconciled_synthetic_operating_chain');self.assertIn('receivables:terminal_working_balance_requires_settlement_profile',c[0][7].payload['blockers'])
    def test_holding_gap_and_missing_payment_claim_remain_blocked(self):
        c=data_case(lambda d:d['ops'][1].update(start_date='2027-04-02'));self.assertIn('holding_cash_chain_blocked',c[0][7].payload['blockers'])
        c=data_case(lambda d:d['ops'][0]['amounts']['debt_principal_payment'].update(value=None));self.assertIsNone(c[-1].compiled_raw)
    def test_all_hashes_and_scope_basis_guards(self):
        for key in ['holding_source_sha256','holding_run_sha256','sale_source_sha256','sale_run_sha256','debt_binding_source_sha256','debt_run_sha256']:
            c=data_case(hold_change=lambda p:p.update({key:'0'*64}));self.assertIn(key+'_mismatch',c[0][7].payload['blockers'])
        for key in ['cash_boundary_basis_ref','loan_continuity_basis_ref','terminal_working_balance_basis_ref','scope_inventory_declared_complete']:
            c=data_case(hold_change=lambda p:p.update({key:None}));self.assertEqual(c[0][7].payload['state'],'blocked')
    def test_updated_hash_holding_and_sale_forgeries_rejected(self):
        a=self.case[0];args=[a[2],a[3],a[4],a[5],a[6]];args[3]=forged(args[3],lambda p:p.update(state='forged'))
        with self.assertRaises(ValidationError):reconcile_hold_sale_cash(*args)
        args=[a[2],replace(a[3],debt_run=forged(a[3].debt_run,lambda p:p.update(state='forged'))),a[4],a[5],a[6]]
        with self.assertRaises(ValidationError):reconcile_hold_sale_cash(*args)
    def test_arithmetic_budget_cannot_export_partial_equity(self):
        a=self.case[0]
        with patch('miniuw_foundation.hold_sale_cash._bounded',side_effect=ArithmeticBudgetError('test')):p=reconcile_hold_sale_cash(a[2],a[3],a[4],a[5],a[6]).payload
        self.assertIn('hold_sale_exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['exportable_equity_movements']);self.assertIsNone(p['totals'])


class HoldSaleOpeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=data_case()
    def test_full_preopening_cash_and_loan_reconcile(self):
        p=self.case[1].payload;self.assertEqual(p['state'],'matched_synthetic_no_refinance_opening');self.assertEqual(f(p['opening_loan_checks'][0]['scheduled_opening_principal']),120);self.assertEqual(p['decision'],'PENDING')
        self.assertFalse(p['actual_funding_payments_or_assets_verified'])
    def test_explicit_empty_loan_inventory_supported(self):
        c=build(sources(True));self.assertEqual(c[1].payload['state'],'matched_synthetic_no_refinance_opening');self.assertEqual(c[1].payload['opening_loan_checks'],[]);self.assertIsNotNone(c[-1].compiled_raw)
    def test_wrong_opening_principal_with_same_cash_does_not_match(self):
        def change(d):
            d['pre']['events'][4]['amount']=claim(121);d['pre']['events'][5]['amount']=claim(21);d['pre']['terminal_claims']['loan_principal']['SYNTHETIC-hold-sale-loan']=claim(121)
        c=data_case(change);self.assertEqual(c[0][1].payload['state'],'reconciled_synthetic_preopening_cash');self.assertTrue(any('scheduled_opening_balance'in b for b in c[1].payload['blockers']))
    def test_prior_service_checked_before_operation(self):
        def change(d):
            d['loans'][0].update(origination_date='2026-11-01',maturity_payment=8,payment_dates=['2026-12-01']+['2027-0'+str(i)+'-01'for i in range(1,8)])
            d['pre']['events'][4]['date']='2026-11-01';d['pre']['events'][2]['amount']=claim(410)
            d['pre']['events'].append(dict(event_id='SYNTHETIC-prior-principal',date='2026-12-01',category='loan_principal_repayment',loan_id='SYNTHETIC-hold-sale-loan',amount=claim(10)))
            d['pre']['terminal_claims']['loan_principal']['SYNTHETIC-hold-sale-loan']=claim(110)
            for suffix in ['due','paid']:d['sale']['old_debts'][0]['principal_'+suffix]['value']=q(50)
        c=data_case(change);self.assertEqual(c[1].payload['state'],'matched_synthetic_no_refinance_opening');r=c[1].payload['opening_loan_checks'][0]
        self.assertEqual(f(r['scheduled_opening_principal']),110);self.assertTrue(all(p['date']=='2026-12-01'for p in r['payment_checks']));self.assertIsNotNone(c[-1].compiled_raw)
    def test_loan_inventory_and_binding_basis_are_exact(self):
        c=data_case(opening_change=lambda p:p.update(loans=[]));self.assertIn('preopening_and_sale_loan_inventories_do_not_match_exactly',c[1].payload['blockers'])
        for key in ['preopening_source_sha256','preopening_run_sha256','hold_sale_spec_sha256','hold_sale_run_sha256','cash_binding_sha256']:
            c=data_case(opening_change=lambda p:p.update({key:'0'*64}));self.assertIn(key+'_mismatch',c[1].payload['blockers'])
        c=data_case(opening_change=lambda p:p.update(payment_basis_ref=None));self.assertIn('payment_basis_ref_missing',c[1].payload['blockers'])
    def test_rehashed_upstream_proof_rejected(self):
        a=list(self.case[0]);a[7]=forged(a[7],lambda p:p.update(state='forged'))
        with self.assertRaises(ValidationError):reconcile_hold_sale_opening(*a)


class HoldSaleReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=data_case()
    def test_full_return_hand_totals_and_normalization(self):
        p=self.case[-1].investor_run.payload;self.assertEqual(f(p['gross_contributions']),1400);self.assertEqual(f(p['gross_distributions']),1360);self.assertEqual(f(p['net_cash_profit']),-40);self.assertEqual(f(p['equity_multiple']),Fraction(34,35))
        self.assertEqual(f(p['normalized_story']['total_distributions']),Fraction(68,7));self.assertEqual(p['cash_horizon']['start'],'2026-10-01');self.assertFalse(self.case[-1].payload['opening_cash_counted_as_new_equity'])
    def test_refinance_receipts_not_invented_and_zero_contributions_retained(self):
        p=self.case[-1].investor_run.payload;self.assertEqual(f(p['cash_by_category']['net_refinance_distribution']),0);self.assertEqual(f(p['cash_by_category']['refinance_cash_in']),0)
        self.assertEqual(len(p['events']),8);self.assertEqual(sum(1 for e in p['events']if e['kind']=='contribution'and f(e['amount'])==0),3);self.assertEqual(f(p['cash_by_category']['net_sale_distribution']),1160)
    def test_explicit_additional_operation_contribution_is_gross(self):
        def change(d):d['ops'][0]['amounts']['equity_contribution']['value']=q(500);d['ops'][0]['amounts']['capital_expenditure']['value']=q(520)
        c=data_case(change);p=c[-1].investor_run.payload;self.assertEqual(f(p['gross_contributions']),1900);self.assertEqual(f(p['gross_distributions']),1360);self.assertEqual(f(p['net_cash_profit']),-540)
    def test_sale_cash_in_requires_express_funding_and_separate_contribution(self):
        def change(d):d['sale']['amounts']['closing_costs_paid']['value']=q(2000)
        c=data_case(change);self.assertIsNone(c[-1].compiled_raw)
        d=sources();change(d);d['sale']['equity_funding_assumption_ref']='SYNTHETIC-projected-equity-not-availability-proof';c=build(d);p=c[-1].investor_run.payload
        self.assertEqual(f(p['gross_contributions']),2220);self.assertEqual(f(p['cash_by_category']['net_sale_distribution']),0);self.assertEqual(f(p['gross_distributions']),200)
    def test_extra_opening_cash_seed_or_missing_mapping_cannot_compile(self):
        def extra(p):p['events'].append(dict(event_id='duplicate-opening',kind='contribution',category='initial_capital',date='2027-01-01',currency='USD',amount=q(1000),source_ref='SYNTHETIC-invalid-seed'))
        c=data_case(investor_change=extra);self.assertIsNone(c[-1].compiled_raw)
        c=data_case(binding_change=lambda p:p['holding_slots'].pop());self.assertIsNone(c[-1].compiled_raw)
    def test_prefilled_wrong_date_or_currency_targets_not_overridden(self):
        for key,value in [('amount',q(999)),('date','2026-12-01'),('currency','EUR')]:
            c=data_case(investor_change=lambda p:p['events'][0].update({key:value}));self.assertIsNone(c[-1].compiled_raw);self.assertEqual(c[-1].payload['changes'],[])
    def test_source_lineage_points_to_exact_gross_values(self):
        c=self.case
        for change in c[-1].payload['changes']:
            record=c[0][1].payload if change['source_run_sha256']==c[0][1].sha256 else c[0][7].payload
            value=record
            for part in change['source_pointer'].strip('/').split('/'):value=value[int(part)]if type(value)is list else value[part]
            self.assertEqual(value['amount']if type(value)is dict and 'amount'in value else value,change['after']['amount'])
    def test_no_financial_scenario_ranking_personal_return_or_implicit_capital_base(self):
        r=self.case[-1].payload;p=self.case[-1].investor_run.payload;self.assertEqual(r['decision'],'PENDING');self.assertFalse(r['financial_scenario_comparison_or_ranking']);self.assertIsNone(r['personal_investor_return']);self.assertFalse(r['financial_model_complete'])
        self.assertTrue(all(x['conditional_coc']is None for x in p['annual_cash_receipts']));self.assertTrue(p['story_blockers']);self.assertIsNone(p['selected_IRR'])


class HoldSaleRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=data_case();cls.bundle=export_hold_sale_bundle(*cls.case)
    def test_exact_recovery_and_repeat_export(self):
        r=recover_hold_sale_bundle(self.bundle);self.assertEqual(r.run,self.case[-1]);self.assertEqual(r.bundle_sha256,sha(self.bundle));self.assertEqual(export_hold_sale_bundle(r.opening_args,r.opening_run,r.investor_raw,r.binding_raw,r.run),self.bundle)
    def test_explicit_no_debt_case_recovers(self):
        c=build(sources(True));self.assertEqual(recover_hold_sale_bundle(export_hold_sale_bundle(*c)).run,c[-1])
    def test_expired_maturity_stays_blocked_after_recovery(self):
        c=data_case(lambda d:d['loans'][0].update(maturity_payment=4,payment_dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01']));r=recover_hold_sale_bundle(export_hold_sale_bundle(*c));self.assertIsNone(r.run.compiled_raw);self.assertTrue(r.run.payload['sale_debt_blockers'])
    def test_rehashed_forged_result_or_changed_source_rejected(self):
        b=json.loads(self.bundle);p=json.loads(b['expected_run']['payload_json']);p['decision']='PASS';b['expected_run']=dict(payload_json=canonical(p),sha256=digest(canonical(p)))
        with self.assertRaises(ValidationError):recover_hold_sale_bundle(raw(b))
        b=json.loads(self.bundle);p=json.loads(b['preopening_source']);p['events'][0]['amount']['value']=q(999);b['preopening_source']=canonical(p)
        with self.assertRaises(ValidationError):recover_hold_sale_bundle(raw(b))
    def test_versions_missing_source_duplicate_json_and_transport_guards(self):
        for change in [lambda b:b['versions'].update(T65='0'*64),lambda b:b['periods'].pop(),lambda b:b.update(extra=True)]:
            b=json.loads(self.bundle);change(b)
            with self.assertRaises(ValidationError):recover_hold_sale_bundle(raw(b))
        for b in [b'{"schema":1,"schema":2}',b'NaN',self.bundle.decode()]:
            with self.assertRaises(ValidationError):recover_hold_sale_bundle(b)


class CurrentHoldSaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=data_case();cls.bundle=export_hold_sale_bundle(*cls.case);cls.recovered=recover_hold_sale_bundle(cls.bundle);cls.registry=current_registry(cls.recovered,cls.bundle)
    def evaluate(self,change=None):
        p=copy.deepcopy(self.registry)
        if change:change(p)
        source=raw(p);r=evaluate_evidence_currency(source,AT);return assemble_current_hold_sale(self.bundle,source,r,AT)
    def test_current_full_source_view_and_numeric_story(self):
        p=self.evaluate().payload;self.assertEqual(len(p['required_source_bindings']),16);self.assertEqual(p['state'],'current_synthetic_hold_sale_at_declared_time');self.assertIn('1360.0000',p['markdown']);self.assertEqual(p['decision'],'PENDING');self.assertFalse(p['financial_publication_authorized'])
    def test_expiry_withdraws_all_current_numbers_preserving_history(self):
        for key in ['/preopening/cash','/sale/loans/0/terms','/investor/source','/transport/bundle']:
            p=self.evaluate(lambda d:next(e for e in d['evidence']if e['requirement_id']==key).update(valid_until=AT)).payload
            self.assertIsNone(p['current_project_return_story']);self.assertNotIn('1360.0000',p['markdown']);self.assertNotIn('1400.0000',p['markdown']);self.assertTrue(p['historical_calculation_preserved'])
    def test_source_inventory_and_pending_review_not_hidden(self):
        def omit(p):p['requirements'].pop();p['evidence'].pop()
        self.assertIn('complete_hold_sale_source_binding_inventory_mismatch',self.evaluate(omit).payload['blockers'])
        p=self.evaluate(lambda d:d['evidence'][0].update(review_status='pending')).payload;self.assertIsNone(p['current_project_return_story']);self.assertTrue(p['evidence_blockers'])
    def test_current_evidence_never_repairs_early_maturity(self):
        c=data_case(lambda d:d['loans'][0].update(maturity_payment=4,payment_dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01']));b=export_hold_sale_bundle(*c);r=recover_hold_sale_bundle(b);s=raw(current_registry(r,b));p=assemble_current_hold_sale(b,s,evaluate_evidence_currency(s,AT),AT).payload
        self.assertIn('hold_sale_calculation_blocked',p['blockers']);self.assertIsNone(p['current_project_return_story']);self.assertTrue(p['calculation_blockers'])
    def test_wrong_time_or_rehashed_registry_run_rejected(self):
        s=raw(self.registry);r=evaluate_evidence_currency(s,AT)
        with self.assertRaises(ValidationError):assemble_current_hold_sale(self.bundle,s,r,'2027-07-01T12:00:01Z')
        with self.assertRaises(ValidationError):assemble_current_hold_sale(self.bundle,s,forged(r,lambda p:p.update(blockers=['forged'])),AT)


if __name__=='__main__':unittest.main()
