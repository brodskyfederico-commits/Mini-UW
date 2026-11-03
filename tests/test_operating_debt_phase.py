import copy,json,sys,unittest
from pathlib import Path
from dataclasses import replace
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from staged_phase_demo_support import make_case,raw,q,sha
from construction_demo_support import money
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.operating_debt_phase import produce_operating_debt_phase
from miniuw_foundation.staged_operating_window import reconcile_staged_operating_window
from miniuw_foundation.staged_lifecycle_returns import assemble_staged_lifecycle_returns
from miniuw_foundation.staged_lifecycle_bundle import export_staged_lifecycle_bundle,recover_staged_lifecycle_bundle,required_staged_lifecycle_sources,assemble_current_staged_lifecycle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency

def f(r):return Fraction(int(r['numerator']),int(r['denominator']))
def forged(run,change):
    p=run.payload;change(p);s=canonical(p);return replace(run,payload_json=s,sha256=digest(s))
AT='2027-07-01T12:00:00Z'
def registry(recovered,bundle):
    req=required_staged_lifecycle_sources(recovered,bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=recovered.run.payload['context'],inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-all-linked-staged-lifecycle-sources',requirements=req,
        evidence=[dict(evidence_id='SYNTHETIC-phase-evidence-'+str(i),**r,issued_at='2027-01-01T00:00:00Z',valid_from='2027-01-01T00:00:00Z',valid_until='2027-07-02T00:00:00Z',review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,basis_ref='SYNTHETIC-express-test-validity-no-real-authority')for i,r in enumerate(req)])


class OperatingDebtPhaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=make_case()
    def test_carry_matches_same_liability_schedule_without_funding_again(self):
        r=self.case[0][2];p=r.payload;self.assertEqual(p['state'],'matched_synthetic_same_liability_operating_phase');self.assertEqual(f(p['loan_phases'][0]['construction_terminal_principal']),200)
        self.assertFalse(p['schedule_anchor_is_new_funding_date']);self.assertFalse(p['new_cash_at_phase_start_generated']);self.assertEqual(p['loan_phases'][0]['phase_start_date'],'2027-01-01');self.assertEqual(p['loan_phases'][0]['original_maturity_date'],'2027-07-01')
        self.assertEqual(r.operating_loans[0].run.payload['loan_id'],'SYNTHETIC-staged-loan');self.assertEqual(f(r.operating_loans[0].run.payload['regular_payment_due']),20)
    def test_capitalized_or_changed_principal_not_inferred(self):
        for value in [201,205,0,None]:
            c=make_case(terms_change=lambda t:t.update(principal=None if value is None else q(value)));self.assertTrue(any('phase_principal_differs_from_construction_carry'in b for b in c[0][2].payload['blockers']));self.assertIsNone(c[0][2].operating_loans)
    def test_original_maturity_not_extended_by_new_calendar(self):
        c=make_case(terms_change=lambda t:t['payment_dates'].__setitem__(-1,'2027-08-01'));self.assertTrue(any('operating_maturity_differs_no_extension_inferred'in b for b in c[0][2].payload['blockers']));self.assertIsNone(c[-1].compiled_raw)
    def test_anchor_must_be_exact_construction_cutoff(self):
        c=make_case(terms_change=lambda t:t.update(origination_date='2027-01-02'));self.assertTrue(any('schedule_anchor_does_not_match_construction_cutoff'in b for b in c[0][2].payload['blockers']))
    def test_explicit_same_liability_no_cash_and_settlement_declarations_required(self):
        for key in ['same_liability_declared','no_new_cash_declared','no_principal_adjustments_declared','prior_interest_fees_settled_declared']:
            c=make_case(phase_change=lambda p:p['loan_phases'][0].update({key:None}));self.assertTrue(any(key+'_not_explicitly_true'in b for b in c[0][2].payload['blockers']))
        c=make_case(phase_change=lambda p:p['loan_phases'][0].update(continuity_basis_ref=None));self.assertTrue(any('continuity_basis_ref_missing'in b for b in c[0][2].payload['blockers']))
    def test_inventory_source_hash_context_and_rate_availability_guards(self):
        for change in [lambda p:p.update(construction_bundle_sha256='0'*64),lambda p:p.update(phase_basis_ref=None),lambda p:p['loan_phases'][0].update(construction_loan_source_sha256='0'*64),lambda p:p['loan_phases'][0].update(loan_id='SYNTHETIC-unknown')]:
            c=make_case(phase_change=change);self.assertEqual(c[0][2].payload['state'],'blocked')
        c=make_case(terms_change=lambda t:t['context'].update(run_id='SYNTHETIC-other'));self.assertTrue(any('context_or_currency_mismatch'in b for b in c[0][2].payload['blockers']))
        c=make_case(terms_change=lambda t:t.update(periodic_rate=None));self.assertTrue(any('complete_dated_operating_schedule_unavailable'in b for b in c[0][2].payload['blockers']))
    def test_preceding_cash_deficit_not_repaired_by_valid_phase_terms(self):
        def change(d):d['draft']['events'][0]['amount']=money(200);d['draft']['events'][2]['amount']=money(1200)
        c=make_case(construction_change=change);self.assertIn('construction_cash_or_draws_blocked',c[0][2].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
    def test_strict_contract_shape_duplicate_phase_and_boolean_type(self):
        c=self.case
        for change in [lambda p:p.update(profile='new_funding'),lambda p:p['loan_phases'].append(copy.deepcopy(p['loan_phases'][0])),lambda p:p['loan_phases'][0].update(no_new_cash_declared=1)]:
            p=json.loads(c[0][1]);change(p)
            with self.assertRaises(ValidationError):produce_operating_debt_phase(c[0][0],raw(p))
    def test_rehashed_construction_package_forgery_rejected(self):
        c=self.case;b=json.loads(c[0][0]);p=json.loads(b['expected_run']['payload_json']);p['decision']='PASS';s=canonical(p);b['expected_run']=dict(payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):produce_operating_debt_phase(raw(b),c[0][1])


class StagedOperatingWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=make_case()
    def test_cash_and_dated_principal_continue_through_sale(self):
        c=self.case;p=c[1].payload;self.assertEqual(p['state'],'matched_synthetic_staged_operating_window');self.assertTrue(all(r['operating_source_windows_and_run_match']for r in p['loan_phase_checks']))
        holding=c[0][4].payload;self.assertEqual([f(r['scheduled_principal'])for r in holding['operating_debt_checks']],[40,60]);self.assertFalse(p['new_cash_draw_or_equity_at_phase_boundary_generated']);self.assertFalse(p['maturity_extension_generated'])
    def test_balanced_operating_cash_reset_does_not_match_construction(self):
        def change(d):
            for i,value in [(0,441),(1,301)]:d['ops'][i]['amounts']['closing_free_cash_claim']['value']=q(value)
            d['ops'][0]['amounts']['opening_free_cash']['value']=q(591);d['ops'][1]['amounts']['opening_free_cash']['value']=q(441);d['sale']['amounts']['opening_free_cash']['value']=q(301)
        c=make_case(holding_change=change);self.assertEqual(c[0][4].payload['state'],'reconciled_synthetic_no_refinance_cash');self.assertIn('construction_operating_cash_boundary_blocked',c[1].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
    def test_different_but_cash_equivalent_operating_loan_source_cannot_be_grafted(self):
        c=make_case(holding_change=lambda d:d['loans'][0].update(rate_interval_ref='SYNTHETIC-different-source-revision'));self.assertEqual(c[0][4].payload['state'],'reconciled_synthetic_no_refinance_cash')
        self.assertTrue(any('operating_schedule_source_windows_or_run_differs'in b for b in c[1].payload['blockers']));self.assertIsNone(c[-1].compiled_raw)
    def test_all_window_source_hashes_and_basis_checked(self):
        c=self.case
        for key in ['construction_bundle_sha256','phase_run_sha256','holding_manifest_sha256','hold_sale_spec_sha256','hold_sale_run_sha256','cash_binding_sha256']:
            a=list(c[0]);s=json.loads(a[-1]);s[key]='0'*64;a[-1]=raw(s);self.assertIn(key+'_mismatch',reconcile_staged_operating_window(*a).payload['blockers'])
        c=make_case(window_change=lambda p:p.update(same_cash_and_liability_basis_ref=None));self.assertIn('same_cash_and_liability_basis_missing',c[1].payload['blockers'])
    def test_underlying_operating_defect_not_bypassed(self):
        c=make_case(holding_change=lambda d:d['ops'][0]['amounts']['debt_principal_payment'].update(value=None));self.assertIn('operating_holding_or_sale_blocked',c[1].payload['blockers']);self.assertIsNone(c[-1].compiled_raw)
    def test_rehashed_phase_and_holding_proofs_not_accepted(self):
        c=self.case
        for index in [2,4]:
            a=list(c[0]);a[index]=forged(a[index],lambda p:p.update(decision='PASS'))
            with self.assertRaises(ValidationError):reconcile_staged_operating_window(*a)


class StagedLifecycleReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=make_case()
    def test_full_history_hand_cash_result_and_multiple(self):
        p=self.case[-1].investor_run.payload;self.assertEqual(f(p['gross_contributions']),1400);self.assertEqual(f(p['gross_distributions']),870);self.assertEqual(f(p['net_cash_profit']),-530);self.assertEqual(f(p['equity_multiple']),Fraction(87,140))
        self.assertEqual(f(p['cash_by_category']['operating_distribution']),200);self.assertEqual(f(p['cash_by_category']['net_sale_distribution']),670);self.assertEqual(f(p['normalized_story']['total_distributions']),Fraction(87,14))
    def test_no_second_draw_principal_receipt_or_opening_equity(self):
        r=self.case[-1];p=r.investor_run.payload;self.assertEqual(len(p['events']),8);self.assertFalse(r.payload['phase_principal_or_opening_cash_counted_as_new_equity']);self.assertEqual(f(p['cash_by_category']['initial_capital']),1000)
        self.assertEqual(f(p['cash_by_category']['additional_capital']),400);self.assertEqual(f(p['cash_by_category']['net_refinance_distribution']),0);self.assertEqual(sum(1 for e in p['events']if e['kind']=='contribution'and f(e['amount'])==0),3)
    def test_all_historical_interest_costs_and_grid_survive_to_cash_risk(self):
        c=self.case;p=c[-1].investor_run.payload;r=json.loads(c[-1].payload['cash_risk_run']['payload_json']);self.assertEqual(p['cash_horizon']['start'],'2026-10-01');self.assertEqual(len(p['dated_net_flows']),10)
        self.assertEqual(f(r['metrics']['cash_shortfall_at_horizon']),530);self.assertIsNone(p['selected_IRR']);self.assertTrue(p['annual_irr_roots'])
        # Whole declared cash: equity + all construction draws + operating receipts + sale.
        self.assertEqual(1400+250+150+400,1000+5+5+50+100+100+40+10+20+870)
    def test_extra_boundary_seed_and_missing_mapping_block_without_override(self):
        def extra(p):p['events'].append(dict(event_id='phase-seed',kind='contribution',category='initial_capital',date='2027-01-01',currency='USD',amount=q(590),source_ref='SYNTHETIC-invalid-duplicate-cash'))
        c=make_case(investor_change=extra);self.assertIsNone(c[-1].compiled_raw)
        c=make_case(binding_change=lambda p:p['preopening_slots'].pop());self.assertIsNone(c[-1].compiled_raw)
    def test_prefilled_wrong_date_and_scope_basis_not_adopted(self):
        for change in [lambda p:p['events'][0].update(amount=q(0)),lambda p:p['events'][0].update(date='2026-12-01')]:
            c=make_case(investor_change=change);self.assertIsNone(c[-1].compiled_raw);self.assertEqual(c[-1].payload['changes'],[])
        c=make_case(binding_change=lambda p:p.update(scope_basis_ref=None));self.assertIn('scope_basis_ref_missing',c[-1].payload['blockers'])
    def test_additional_operating_equity_is_gross_not_a_balance_reset(self):
        def change(d):d['ops'][0]['amounts']['equity_contribution']['value']=q(500);d['ops'][0]['amounts']['capital_expenditure']['value']=q(520)
        c=make_case(holding_change=change);p=c[-1].investor_run.payload;self.assertEqual(f(p['gross_contributions']),1900);self.assertEqual(f(p['gross_distributions']),870);self.assertEqual(f(p['net_cash_profit']),-1030)
    def test_capital_coc_personal_and_actual_approval_stay_pending(self):
        r=self.case[-1].payload;p=self.case[-1].investor_run.payload;self.assertEqual(r['decision'],'PENDING');self.assertFalse(r['financial_model_complete']);self.assertIsNone(r['personal_investor_return']);self.assertTrue(p['story_blockers']);self.assertTrue(all(y['conditional_coc']is None for y in p['annual_cash_receipts']))
    def test_exact_source_pointers_and_rehashed_window_forgery(self):
        c=self.case
        from miniuw_foundation.construction_bundle import recover_construction_bundle
        pre=recover_construction_bundle(c[0][0]).run.preopening_run
        for change in c[-1].payload['changes']:
            v=pre.payload if change['source_run_sha256']==pre.sha256 else c[0][4].payload
            for part in change['source_pointer'].strip('/').split('/'):v=v[int(part)]if type(v)is list else v[part]
            self.assertEqual(v['amount']if type(v)is dict and 'amount'in v else v,change['after']['amount'])
        with self.assertRaises(ValidationError):assemble_staged_lifecycle_returns(c[0],forged(c[1],lambda p:p.update(decision='PASS')),c[2],c[3])


class StagedLifecycleRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=make_case();cls.bundle=export_staged_lifecycle_bundle(*cls.case);cls.recovered=recover_staged_lifecycle_bundle(cls.bundle);cls.source=registry(cls.recovered,cls.bundle)
    def evaluate(self,change=None):
        p=copy.deepcopy(self.source)
        if change:change(p)
        s=raw(p);return assemble_current_staged_lifecycle(self.bundle,s,evaluate_evidence_currency(s,AT),AT)
    def test_full_exact_recovery_and_deterministic_repeat_export(self):
        r=self.recovered;self.assertEqual(r.run,self.case[-1]);self.assertEqual(r.bundle_sha256,sha(self.bundle));self.assertEqual(export_staged_lifecycle_bundle(r.window_args,r.window_run,r.investor_raw,r.binding_raw,r.run),self.bundle)
    def test_incompatible_phase_stays_blocked_after_recovery(self):
        c=make_case(terms_change=lambda t:t.update(principal=q(201)));r=recover_staged_lifecycle_bundle(export_staged_lifecycle_bundle(*c));self.assertIsNone(r.run.compiled_raw);self.assertTrue(r.run.payload['phase_blockers'])
    def test_rehashed_result_changed_phase_and_forged_export_rejected(self):
        b=json.loads(self.bundle);p=json.loads(b['expected_run']['payload_json']);p['decision']='PASS';s=canonical(p);b['expected_run']=dict(payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):recover_staged_lifecycle_bundle(raw(b))
        b=json.loads(self.bundle);p=json.loads(b['phase_contract']);p['loan_phases'][0]['no_new_cash_declared']=None;b['phase_contract']=canonical(p)
        with self.assertRaises(ValidationError):recover_staged_lifecycle_bundle(raw(b))
        c=list(self.case);c[-1]=forged(c[-1],lambda p:p.update(decision='PASS'))
        with self.assertRaises(ValidationError):export_staged_lifecycle_bundle(*c)
    def test_wrong_version_omitted_source_and_duplicate_json_rejected(self):
        for change in [lambda b:b['versions'].update(T72='0'*64),lambda b:b['periods'].pop(),lambda b:b.update(extra=True)]:
            b=json.loads(self.bundle);change(b)
            with self.assertRaises(ValidationError):recover_staged_lifecycle_bundle(raw(b))
        for b in [self.bundle.decode(),b'NaN',b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):recover_staged_lifecycle_bundle(b)
    def test_current_complete_review_and_phase_principal_not_cash(self):
        p=self.evaluate().payload;self.assertEqual(len(p['required_source_bindings']),22);self.assertEqual(p['state'],'current_synthetic_staged_lifecycle_at_declared_time')
        for marker in ['870.0000','-530.0000','200.0000','Continuidad del principal','PENDING']:self.assertIn(marker,p['markdown'])
        self.assertFalse(p['financial_publication_authorized']);self.assertEqual(p['markdown_sha256'],digest(p['markdown']))
    def test_expired_construction_phase_boundary_or_investor_withdraws_current_numbers(self):
        for path in ['/construction/loans/0','/transition/phase_contract','/transition/loans/0/schedule','/boundary/cash_binding','/investor/source']:
            p=self.evaluate(lambda d:next(e for e in d['evidence']if e['requirement_id']==path).update(valid_until=AT)).payload
            self.assertIsNone(p['current_project_return_story']);self.assertNotIn('870.0000',p['markdown']);self.assertNotIn('200.0000',p['markdown']);self.assertTrue(p['historical_calculation_preserved'])
    def test_incomplete_pending_estimated_context_or_rehashed_inventory_not_accepted(self):
        def omit(p):p['requirements'].pop();p['evidence'].pop()
        self.assertIn('complete_staged_lifecycle_source_inventory_mismatch',self.evaluate(omit).payload['blockers'])
        for key,value in [('review_status','pending'),('value_status','estimate')]:self.assertIsNone(self.evaluate(lambda p:p['evidence'][0].update({key:value})).payload['current_project_return_story'])
        self.assertIn('staged_lifecycle_evidence_context_mismatch',self.evaluate(lambda p:p['context'].update(run_id='SYNTHETIC-other')).payload['blockers'])
    def test_current_evidence_cannot_repair_phase_and_wrong_evaluation_time_rejects(self):
        c=make_case(terms_change=lambda t:t.update(principal=q(201)));b=export_staged_lifecycle_bundle(*c);r=recover_staged_lifecycle_bundle(b);s=raw(registry(r,b));p=assemble_current_staged_lifecycle(b,s,evaluate_evidence_currency(s,AT),AT).payload
        self.assertIn('staged_lifecycle_calculation_blocked',p['blockers']);self.assertIsNone(p['current_project_return_story'])
        s=raw(self.source);r=evaluate_evidence_currency(s,AT)
        with self.assertRaises(ValidationError):assemble_current_staged_lifecycle(self.bundle,s,r,'2027-07-01T12:00:01Z')


if __name__=='__main__':unittest.main()
