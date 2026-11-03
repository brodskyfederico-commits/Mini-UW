import copy,json,sys,unittest
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from lifecycle_demo_support import make_case,raw,q,claim,sha
from demo_preopening_cash import make_source as old_preopening
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.opening_debt import reconcile_opening_debt
from miniuw_foundation.lifecycle_returns import assemble_lifecycle_returns
from miniuw_foundation.lifecycle_bundle import export_lifecycle_bundle,recover_lifecycle_bundle,MAX_BYTES
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.debt_service import DateWindow

def f(r):return Fraction(int(r['numerator']),int(r['denominator']))
def forged(run,change):
    p=run.payload;change(p);s=canonical(p);return replace(run,payload_json=s,sha256=digest(s))


class OpeningDebtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=make_case()
    def test_full_draw_matches_first_operating_loan_and_cash(self):
        r=self.case[1].payload;self.assertEqual(r['state'],'matched_synthetic_opening_debt_and_cash');self.assertEqual(r['blockers'],[])
        row=r['loan_checks'][0];self.assertEqual(f(row['scheduled_opening_principal']),120);self.assertEqual(f(row['preopening_closing_principal']),120)
        self.assertTrue(row['opening_date_payment_belongs_to_operation']);self.assertEqual(row['payment_checks'],[])
    def test_previous_unmatched_cash_example_is_not_repaired(self):
        def change(p):p.clear();p.update(old_preopening(self.case[1].payload['context']))
        c=make_case(pre_change=change);self.assertEqual(c[0][1].payload['state'],'reconciled_synthetic_preopening_cash')
        self.assertIn('opening_loan_inventories_do_not_match_exactly',c[1].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
    def test_same_cash_with_wrong_principal_or_origination_is_rejected(self):
        def amount(p):
            p['events'][4]['amount']=claim(121);p['events'][5]['amount']=claim(21);p['terminal_claims']['loan_principal']['SYNTHETIC-project-old-loan']=claim(121)
        c=make_case(pre_change=amount);self.assertEqual(c[0][1].payload['state'],'reconciled_synthetic_preopening_cash')
        self.assertTrue(any('single_full_draw'in x for x in c[1].payload['blockers']));self.assertTrue(any('opening_balance'in x for x in c[1].payload['blockers']))
        def date(p):p['events'][4]['date']='2026-11-01'
        c=make_case(pre_change=date);self.assertTrue(any('single_full_draw'in x for x in c[1].payload['blockers']))
    def test_split_draw_not_accepted_as_no_new_draw_schedule(self):
        def change(p):
            p['events'][4]['amount']=claim(60);other=copy.deepcopy(p['events'][4]);other['event_id']='SYNTHETIC-second-draw';p['events'].insert(5,other)
        c=make_case(pre_change=change);self.assertTrue(any('single_full_draw'in x for x in c[1].payload['blockers']))
    def test_prior_scheduled_principal_is_checked_and_opening_day_left_to_operation(self):
        def project(d):
            loan=d['loans'][0][0];loan.update(origination_date='2026-11-01',maturity_payment=5,payment_dates=['2026-12-01','2027-01-01','2027-02-01','2027-03-01','2027-04-01'])
            for suffix in ['due','paid']:d['closings'][0]['old_debts'][0]['principal_'+suffix]['value']=q(80)
        def history(p):
            p['events'][4]['date']='2026-11-01';p['events'][2]['amount']=claim(410)
            p['events'].append(dict(event_id='SYNTHETIC-prior-payment',date='2026-12-01',category='loan_principal_repayment',loan_id='SYNTHETIC-project-old-loan',amount=claim(10)))
            p['terminal_claims']['loan_principal']['SYNTHETIC-project-old-loan']=claim(110)
        c=make_case(project_change=project,pre_change=history);self.assertEqual(c[1].payload['state'],'matched_synthetic_opening_debt_and_cash');row=c[1].payload['loan_checks'][0]
        self.assertEqual(f(row['scheduled_opening_principal']),110);self.assertTrue(all(r['date']=='2026-12-01'for r in row['payment_checks']));self.assertEqual(c[-1].payload['state'],'compiled_synthetic_purchase_to_sale')
    def test_off_schedule_payment_not_hidden_by_later_total(self):
        def history(p):
            p['events'][2]['amount']=claim(410);p['events'].append(dict(event_id='SYNTHETIC-wrong-payment',date='2026-12-02',category='loan_principal_repayment',loan_id='SYNTHETIC-project-old-loan',amount=claim(10)))
            p['terminal_claims']['loan_principal']['SYNTHETIC-project-old-loan']=claim(110)
        c=make_case(pre_change=history);self.assertTrue(any('2026-12-02:loan_principal_repayment' in b for b in c[1].payload['blockers']));self.assertIsNone(c[-1].compiled_raw)
    def test_cash_interest_is_matched_separately_from_principal(self):
        def history(p):
            p['events'][2]['amount']=claim(401);p['events'].append(dict(event_id='SYNTHETIC-unsupported-interest',date='2026-12-02',category='debt_interest_payment',loan_id='SYNTHETIC-project-old-loan',amount=claim(1)))
        c=make_case(pre_change=history);self.assertTrue(any('debt_interest_payment:cash_payment_differs' in b for b in c[1].payload['blockers']))
    def test_every_binding_and_basis_checked(self):
        for key in ['preopening_source_sha256','preopening_run_sha256','project_manifest_sha256','project_cash_run_sha256','cash_binding_sha256']:
            args=list(self.case[0]);s=json.loads(args[-1]);s[key]='0'*64;args[-1]=raw(s);self.assertIn(key+'_mismatch',reconcile_opening_debt(*args).payload['blockers'])
        for key in ['payment_basis_ref','debt_change_scope_basis_ref']:
            c=make_case(opening_change=lambda s:s.update({key:None}));self.assertIn(key+'_missing',c[1].payload['blockers'])
        c=make_case(opening_change=lambda s:s['loans'][0].update(loan_source_sha256='0'*64));self.assertTrue(any('loan_source_sha256_mismatch'in b for b in c[1].payload['blockers']))
    def test_inventory_and_strict_profile_guards(self):
        c=make_case(opening_change=lambda s:s.update(loans=[]));self.assertIn('opening_loan_inventories_do_not_match_exactly',c[1].payload['blockers'])
        for mutate in [lambda s:s.update(profile='other'),lambda s:s['loans'].append(copy.deepcopy(s['loans'][0])),lambda s:s.update(cash_binding_sha256='invalid')]:
            args=list(self.case[0]);s=json.loads(args[-1]);mutate(s);args[-1]=raw(s)
            with self.assertRaises(ValidationError):reconcile_opening_debt(*args)
    def test_source_and_rehashed_project_forgery_rejected(self):
        args=list(self.case[0]);args[1]=forged(args[1],lambda p:p['totals'].update(loan_draw=q(999)))
        with self.assertRaises(ValidationError):reconcile_opening_debt(*args)
        args=list(self.case[0]);args[5]=forged(args[5],lambda p:p.update(state='forged'))
        with self.assertRaises(ValidationError):reconcile_opening_debt(*args)
    def test_math_budget_and_underlying_cash_blocker_remain_pending(self):
        with patch('miniuw_foundation.opening_debt._bounded',side_effect=ArithmeticBudgetError('test')):
            # Baseline has no prior scheduled payments; supply an off-schedule zero to exercise the paid accumulator.
            c=make_case(pre_change=lambda p:p['events'].append(dict(event_id='SYNTHETIC-zero-debt',date='2026-12-01',category='debt_interest_payment',loan_id='SYNTHETIC-project-old-loan',amount=claim(0))))
        self.assertIn('opening_debt_exact_arithmetic_budget_exceeded',c[1].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
        c=make_case(pre_change=lambda p:p['events'][0]['amount'].update(value=None));self.assertIn('preopening_cash_blocked',c[1].payload['blockers'])
    def test_schedule_match_never_claims_actual_funding_or_assets(self):
        p=self.case[1].payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['actual_bank_payments_verified','commitment_and_funds_available_verified','asset_basis_and_complete_TDC_verified','professional_review_authenticated','production_authorized']:self.assertFalse(p[key])


class LifecycleReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=make_case()
    def test_hand_full_cash_and_seed_exclusion_changes_return(self):
        run=self.case[-1];p=run.investor_run.payload;old=self.case[3].investor_run.payload
        self.assertEqual(run.payload['state'],'compiled_synthetic_purchase_to_sale');self.assertEqual(f(p['gross_contributions']),1400);self.assertEqual(f(p['gross_distributions']),Fraction('1298.9197'))
        self.assertEqual(f(p['net_cash_profit']),Fraction('-101.0803'));self.assertEqual(f(p['equity_multiple']),Fraction('1298.9197')/1400)
        self.assertEqual(f(old['gross_contributions']),1000);self.assertFalse(run.payload['operating_opening_cash_counted_as_new_equity'])
        self.assertEqual(len(p['events']),6);self.assertNotIn('initial',[e['event_id']for e in p['events']]);self.assertEqual(p['cash_horizon']['start'],'2026-10-01')
    def test_all_categories_and_normalization_keep_historical_basis(self):
        p=self.case[-1].investor_run.payload;n=p['normalized_story'];self.assertEqual(f(n['basis_amount']),1400);self.assertEqual(f(n['total_contributions']),10)
        self.assertEqual(f(p['cash_by_category']['initial_capital']),1000);self.assertEqual(f(p['cash_by_category']['additional_capital']),400)
        self.assertEqual(f(p['cash_by_category']['operating_distribution']),200);self.assertEqual(f(p['cash_by_category']['net_refinance_distribution']),Fraction('353.01'));self.assertEqual(f(p['cash_by_category']['net_sale_distribution']),Fraction('745.9097'))
    def test_irr_horizon_and_risks_use_full_history(self):
        p=self.case[-1].investor_run.payload;r=json.loads(self.case[-1].payload['cash_risk_run']['payload_json'])
        self.assertEqual(len(p['dated_net_flows']),10);self.assertEqual(f(p['dated_net_flows'][0]['net']),-1000);self.assertEqual(f(p['dated_net_flows'][1]['net']),-400)
        self.assertEqual(p['periodic_irr']['distinct_positive_discount_roots'],1);self.assertIsNone(p['selected_IRR']);self.assertTrue(p['annual_irr_roots'])
        self.assertEqual(f(r['metrics']['cash_shortfall_at_horizon']),Fraction('101.0803'));self.assertEqual(f(r['metrics']['peak_cumulative_net_equity_funding_at_date_close']),1400)
    def test_bank_failure_not_bypassed_by_lifecycle(self):
        c=make_case(bank_noi=50);self.assertEqual(c[1].payload['state'],'matched_synthetic_opening_debt_and_cash');self.assertEqual(c[3].payload['state'],'blocked');self.assertIsNone(c[-1].compiled_raw)
        self.assertIn('capacity_checked_operating_return_blocked',c[-1].payload['blockers']);self.assertTrue(c[-1].payload['capacity_blockers'])
    def test_positive_refinance_cash_in_preserved_as_gross_contribution(self):
        def change(d):
            d['closings'][0]['amounts']['closing_costs_paid']['value']=q(1020)
            d['closings'][0]['equity_funding_assumption_ref']='SYNTHETIC-explicit-projected-cash-in-not-available-funds-proof'
        c=make_case(project_change=change,include_refinance_cash_in=True);self.assertEqual(c[-1].payload['state'],'compiled_synthetic_purchase_to_sale');p=c[-1].investor_run.payload
        self.assertEqual(f(p['cash_by_category']['refinance_cash_in']),Fraction('646.99'));self.assertEqual(f(p['cash_by_category']['net_refinance_distribution']),0)
        self.assertEqual(f(p['gross_contributions']),Fraction('2046.99'));self.assertEqual(f(p['net_cash_profit']),Fraction('-1101.0803'))
        events={e['event_id']:e for e in p['events']};self.assertEqual(events['refi']['date'],events['refi-in']['date']);self.assertEqual(f(events['refi']['amount']),0)
    def test_cash_in_without_funding_assumption_remains_blocked(self):
        c=make_case(project_change=lambda d:d['closings'][0]['amounts']['closing_costs_paid'].update(value=q(1020)),include_refinance_cash_in=True)
        self.assertIsNone(c[-1].compiled_raw);self.assertTrue(any('cash_in_required_but_projected_equity_funding_assumption_missing'in b for b in c[0][3][0].closing_run.payload['blockers']))
    def test_mapping_requires_all_history_and_operating_events(self):
        for key in ['preopening_slots','operating_slots']:
            c=make_case(binding_change=lambda b:b[key].pop());self.assertTrue(c[-1].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
    def test_extra_opening_seed_is_not_another_contribution(self):
        def change(p):p['events'].append(dict(event_id='extra-initial-cash',kind='contribution',category='initial_capital',date='2027-01-01',currency='USD',amount=q(1000),source_ref='SYNTHETIC-invalid-double-seed'))
        c=make_case(investor_change=change);self.assertIn('lifecycle_event_inventory_not_exactly_all_bound_gross_events',c[-1].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
    def test_prefilled_or_wrong_date_and_classification_targets_never_overridden(self):
        for key,value in [('amount',q(999)),('date','2027-02-01'),('category','other_distribution')]:
            c=make_case(investor_change=lambda p:p['events'][0].update({key:value}));self.assertTrue(c[-1].payload['blockers']);self.assertIsNone(c[-1].compiled_raw);self.assertEqual(c[-1].payload['changes'],[])
    def test_source_hash_basis_context_currency_and_horizon_guards(self):
        for key in ['opening_debt_run_sha256','capacity_project_run_sha256','investor_source_sha256']:
            c=make_case(binding_change=lambda b:b.update({key:'0'*64}));self.assertIn(key+'_mismatch',c[-1].payload['blockers'])
        for key in ['equity_scope_basis_ref','calendar_basis_ref']:
            c=make_case(binding_change=lambda b:b.update({key:None}));self.assertIn(key+'_missing',c[-1].payload['blockers'])
        c=make_case(investor_change=lambda p:p['context'].update(run_id='SYNTHETIC-another'));self.assertTrue(c[-1].payload['blockers'])
        c=make_case(investor_change=lambda p:p['grid']['dates'].insert(0,'2026-09-01'));self.assertIn('lifecycle_investor_grid_does_not_cover_exact_purchase_to_sale_horizon',c[-1].payload['blockers'])
    def test_opening_and_capacity_sources_cannot_be_grafted(self):
        # A logically valid independent window with a different timeline basis is not the bound opening window.
        other=make_case(project_change=lambda d:d['manifest'].update(timeline_basis_ref='SYNTHETIC-other-timeline-revision'))
        c=self.case;r=assemble_lifecycle_returns(c[0],c[1],other[2],other[3],c[4],raw(dict(json.loads(c[5]),capacity_project_run_sha256=other[3].sha256)))
        self.assertIn('opening_and_capacity_project_sources_or_runs_differ',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
    def test_rehashed_opening_and_capacity_forgery_rejected(self):
        c=self.case
        for pos,change in [(1,lambda p:p.update(state='forged')),(3,lambda p:p.update(state='forged'))]:
            args=list(c[:6]);args[pos]=forged(args[pos],change)
            with self.assertRaises(ValidationError):assemble_lifecycle_returns(*args)
    def test_no_implicit_basis_capital_or_personal_return(self):
        p=self.case[-1].investor_run.payload;self.assertTrue(all(r['conditional_coc']is None for r in p['annual_cash_receipts']))
        self.assertTrue(any('snapshot:'in b for b in p['story_blockers']));r=self.case[-1].payload;self.assertIsNone(r['personal_investor_return']);self.assertFalse(r['financial_model_complete']);self.assertEqual(r['decision'],'PENDING')
    def test_exact_input_lineage_and_immutable_results(self):
        c=self.case;before=c[4];p=c[-1].payload
        for change in p['changes']:
            record=c[0][1].payload if change['source_family']=='preopening_slots'else c[3].investor_run.payload
            key,index=change['source_pointer'].strip('/').split('/');original=record[key][int(index)];self.assertEqual(original['amount'],change['after']['amount'])
        p['changes'].clear();self.assertTrue(c[-1].payload['changes']);self.assertEqual(c[4],before)


class LifecycleBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=make_case();cls.bundle=export_lifecycle_bundle(*cls.case)
    def test_exact_roundtrip_and_repeat_export(self):
        r=recover_lifecycle_bundle(self.bundle);self.assertEqual(r.run,self.case[-1]);self.assertEqual(r.bundle_sha256,sha(self.bundle));self.assertEqual(r.opening_run,self.case[1]);self.assertEqual(r.capacity_run,self.case[3])
        self.assertEqual(export_lifecycle_bundle(r.opening_args,r.opening_run,r.capacity_args,r.capacity_run,r.investor_raw,r.binding_raw,r.run),self.bundle)
    def test_blocked_bank_case_stays_blocked_on_recovery(self):
        c=make_case(bank_noi=50);b=export_lifecycle_bundle(*c);r=recover_lifecycle_bundle(b);self.assertEqual(r.run,c[-1]);self.assertIsNone(r.run.compiled_raw)
    def test_rehashed_stored_results_rejected(self):
        for key in ['opening_run','capacity_run','lifecycle_run']:
            b=json.loads(self.bundle);r=b[key];p=json.loads(r['payload_json']);p['decision']='PASS';r['payload_json']=canonical(p);r['sha256']=digest(r['payload_json'])
            with self.assertRaises(ValidationError):recover_lifecycle_bundle(raw(b))
    def test_changed_source_or_missing_source_never_accepted(self):
        b=json.loads(self.bundle);s=json.loads(b['preopening_source']);s['events'][0]['amount']['value']=q(999);b['preopening_source']=canonical(s)
        with self.assertRaises(ValidationError):recover_lifecycle_bundle(raw(b))
        b=json.loads(self.bundle);b['periods'].pop()
        with self.assertRaises(ValidationError):recover_lifecycle_bundle(raw(b))
    def test_version_and_strict_transport_guards(self):
        for mutate in [lambda b:b['versions'].update(T59='0'*64),lambda b:b.update(extra=True),lambda b:b.update(periods=[{}]*66),lambda b:b.update(preopening_source='\ud800')]:
            b=json.loads(self.bundle);mutate(b)
            # Surrogate is deliberately represented as an escape in valid transport JSON.
            with self.assertRaises(ValidationError):recover_lifecycle_bundle(json.dumps(b,ensure_ascii=True).encode())
        for value in [self.bundle.decode(),b'{}',b'{"x":1,"x":2}',b'NaN',b'x'*(MAX_BYTES+1)]:
            with self.assertRaises(ValidationError):recover_lifecycle_bundle(value)
    def test_forged_export_never_becomes_valid_bundle(self):
        c=list(self.case);c[-1]=forged(c[-1],lambda p:p.update(decision='PASS'))
        with self.assertRaises(ValidationError):export_lifecycle_bundle(*c)
    def test_dated_window_metadata_survives_transport(self):
        from miniuw_foundation.lifecycle_bundle import _loan_record,_loan
        from miniuw_foundation.debt_service import produce_debt_service
        e=self.case[0][3][0].loans[0];windows=(DateWindow(window_id='SYNTHETIC-preopening-service',start_date='2026-12-01',end_date='2027-01-01',boundary='start_inclusive_end_exclusive'),)
        e=replace(e,windows=windows,run=produce_debt_service(e.loan_raw,windows));self.assertEqual(_loan(_loan_record(e)),e)


if __name__=='__main__':unittest.main()
