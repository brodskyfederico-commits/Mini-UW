import copy,json,sys,unittest
from pathlib import Path
from fractions import Fraction
from dataclasses import replace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from construction_demo_support import sources,build,raw,sha,q,money
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.construction_draws import produce_construction_draws,parse_construction_draws
from miniuw_foundation.construction_cash import assemble_construction_cash
from miniuw_foundation.construction_bundle import export_construction_bundle,recover_construction_bundle
from miniuw_foundation.current_construction_cash import required_construction_sources,assemble_current_construction_cash
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.operating_noi import ArithmeticBudgetError

def f(r):return Fraction(int(r['numerator']),int(r['denominator']))
def forge(run,change):
    p=run.payload;change(p);s=canonical(p);return replace(run,payload_json=s,sha256=digest(s))
AT='2027-01-01T12:00:00Z'
def registry(recovered,bundle):
    req=required_construction_sources(recovered,bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=recovered.run.payload['context'],inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-all-staged-source-bindings',requirements=req,
        evidence=[dict(evidence_id='SYNTHETIC-staged-'+str(i),**r,issued_at='2026-10-01T00:00:00Z',valid_from='2026-10-01T00:00:00Z',valid_until='2027-01-02T00:00:00Z',review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,basis_ref='SYNTHETIC-test-validity-not-professional-approval')for i,r in enumerate(req)])


class ConstructionDrawTests(unittest.TestCase):
    def setUp(self):self.source=sources()['loans'][0]
    def produce(self):return produce_construction_draws(raw(self.source))
    def test_hand_exposure_interest_fee_and_principal(self):
        p=self.produce().payload;self.assertEqual(p['state'],'computed_synthetic_construction_draw_plan')
        self.assertEqual([f(r['interest_exposure'])for r in p['periods']],[100,200,200]);self.assertEqual([f(r['interest_due_at_end'])for r in p['periods']],[1,2,2]);self.assertEqual([f(r['fee_due_at_start'])for r in p['periods']],[2,2,1])
        self.assertEqual([f(r['closing_principal'])for r in p['periods']],[100,150,200]);self.assertEqual({k:f(v)for k,v in p['totals'].items()},dict(gross_draws=250,principal_repaid=50,interest_due=5,fees_due=5,terminal_principal=200))
    def test_gross_nonrevolving_commitment_not_restored_by_repayment(self):
        self.source['principal_commitment']=money(200);p=self.produce().payload;self.assertEqual(f(p['periods'][-1]['closing_principal']),200)
        self.assertTrue(any('cumulative_gross_draws_exceed_nonrevolving_commitment'in b for b in p['blockers']));self.assertIsNone(p['exportable_proposed_debt_cash_events']);self.assertFalse(p['commitment_restored_by_repayment'])
    def test_available_new_draw_is_separate_required_limit(self):
        self.source['periods'][1]['available_new_draw']=money(99);self.assertTrue(any('draw_exceeds_declared_available_new_draw'in b for b in self.produce().payload['blockers']))
        self.source['periods'][1]['available_new_draw']=money(None);self.assertTrue(any('value_missing'in b for b in self.produce().payload['blockers']))
    def test_interest_is_before_end_repayment_and_never_capitalized(self):
        p=self.produce().payload;self.assertEqual(f(p['periods'][1]['interest_due_at_end']),2);self.assertEqual(f(p['periods'][1]['closing_principal']),150);self.assertFalse(p['capitalized_interest_supported'])
    def test_maturity_is_not_extended_or_balloon_silently_ignored(self):
        self.source['maturity_date']='2026-12-01';self.assertIn('schedule_past_maturity_no_extension_inferred',self.produce().payload['blockers'])
        self.source['maturity_date']='2027-01-01';self.assertIn('matured_principal_not_repaid_in_declared_schedule',self.produce().payload['blockers'])
        self.source['periods'][-1]['principal_repayment_at_end']=money(200);p=self.produce().payload;self.assertEqual(p['state'],'computed_synthetic_construction_draw_plan');self.assertEqual(f(p['totals']['terminal_principal']),0)
    def test_excess_repayment_stops_invalid_principal_path(self):
        self.source['periods'][1]['principal_repayment_at_end']=money(201);p=self.produce().payload;self.assertEqual(len(p['periods']),2);self.assertIsNone(p['exportable_proposed_debt_cash_events']);self.assertTrue(any('repayment_exceeds_principal'in b for b in p['blockers']))
    def test_annual_rate_or_wrong_interval_not_inferred(self):
        self.source['periods'][0]['interest_fraction']['unit']='annual_fraction';self.assertTrue(any('unit_mismatch_no_annual_conversion'in b for b in self.produce().payload['blockers']))
        self.setUp();self.source['periods'][0]['interest_fraction']['interval_ref']='SYNTHETIC-wrong';self.assertTrue(any('interval_ref_mismatch'in b for b in self.produce().payload['blockers']))
    def test_missing_zero_negative_source_unit_and_currency_distinct(self):
        for key,value in [('value',None),('value',q(-1)),('currency','EUR'),('source_ref',None)]:
            self.setUp();self.source['principal_commitment'][key]=value;self.assertEqual(self.produce().payload['state'],'blocked')
        self.setUp();self.source['draw_fee_fraction']['value']=q(0)
        for row in self.source['periods']:row['interest_fraction']['value']=q(0)
        p=self.produce().payload;self.assertEqual(f(p['totals']['interest_due']),0);self.assertEqual(f(p['totals']['fees_due']),0)
    def test_all_basis_inventory_and_exact_calendar_required(self):
        for key in ['zero_opening_principal_basis_ref','nonrevolving_commitment_basis_ref','inventory_declared_complete']:
            self.setUp();self.source[key]=None;self.assertEqual(self.produce().payload['state'],'blocked')
        self.setUp();self.source['periods'][1]['start_date']='2026-11-02';self.assertIn('draw_interval_gap_overlap_or_wrong_order',self.produce().payload['blockers'])
        self.setUp();self.source['periods'][0]['interval_basis_ref']=None;self.assertTrue(any('interval_basis_missing'in b for b in self.produce().payload['blockers']))
    def test_strict_source_shape_duplicate_ids_and_transport(self):
        for change in [lambda p:p.update(profile='capitalized'),lambda p:p['periods'][1].update(period_id=p['periods'][0]['period_id']),lambda p:p['context'].update(deal_id='real'),lambda p:p.update(extra=1)]:
            p=copy.deepcopy(self.source);change(p)
            with self.assertRaises(ValidationError):parse_construction_draws(raw(p))
        for b in [b'{"schema":1,"schema":2}',b'NaN',b'x'*1_048_577,'{}']:
            with self.assertRaises(ValidationError):parse_construction_draws(b)
    def test_real_denominator_growth_budget_rejects_partial_schedule(self):
        denominators=[2**845,3**535,5**365,7**301,11**244,13**229];template=self.source['periods'][0];self.source.update(start_date='2026-10-01',end_date='2026-10-07');self.source['periods']=[]
        for i,d in enumerate(denominators):
            row=copy.deepcopy(template);pid='SYNTHETIC-budget-'+str(i);row.update(period_id=pid,start_date='2026-10-0'+str(i+1),end_date='2026-10-0'+str(i+2),draw_at_start=money(100 if i==0 else 0),principal_repayment_at_end=money(0));row['interest_fraction'].update(interval_ref=pid,value=q(Fraction(1,d)));self.source['periods'].append(row)
        p=self.produce().payload;self.assertIn('construction_draw_exact_arithmetic_budget_exceeded',p['blockers']);self.assertEqual(p['periods'],[]);self.assertIsNone(p['totals'])
    def test_gross_event_dates_zeroes_and_immutable_proof(self):
        r=self.produce();p=r.payload;events=p['exportable_proposed_debt_cash_events'];self.assertEqual(len(events),12);self.assertEqual(events[0]['date'],'2026-10-01');self.assertEqual(events[2]['date'],'2026-11-01');self.assertEqual(f(events[3]['amount']),0)
        p['periods'].clear();self.assertEqual(len(r.payload['periods']),3);self.assertEqual(r.sha256,digest(r.payload_json))


class ConstructionCashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=build(sources())
    def test_cash_interest_fee_and_principal_hand_reconciliation(self):
        c=self.case;p=c[-1].payload;cash=c[-1].preopening_run.payload;self.assertEqual(p['state'],'reconciled_synthetic_staged_preopening_cash');last=cash['date_close_balances'][-1]
        self.assertEqual(f(last['free_cash']),590);self.assertEqual(f(last['loan_principal']['SYNTHETIC-staged-loan']),200);self.assertEqual(f(cash['totals']['debt_interest_payment']),5);self.assertEqual(f(cash['totals']['debt_fee_payment']),5)
        self.assertEqual(1400+250,1000+50+5+5+590);self.assertEqual(len(p['changes']),12);self.assertEqual(f(cash['cash_conservation_residual']),0)
    def test_deficit_not_repaired_by_later_funding_or_calculated_interest(self):
        d=sources();d['draft']['events'][0]['amount']=money(200);d['draft']['events'][2]['amount']=money(1200);c=build(d);self.assertEqual(c[-1].payload['state'],'blocked');self.assertIsNotNone(c[-1].compiled_raw)
        self.assertTrue(any('negative_date_close_balance'in b for b in c[-1].payload['cash_blockers']));self.assertIsNone(c[-1].preopening_run.payload['exportable_equity_movements']);self.assertFalse(c[-1].payload['equity_or_draws_generated_to_cover_deficit'])
    def test_multiple_loans_complete_inventory_and_separate_balances(self):
        d=sources();second=copy.deepcopy(d['loans'][0]);second['loan_id']='SYNTHETIC-second-loan'
        for row in second['periods']:
            for key in ['draw_at_start','available_new_draw','principal_repayment_at_end']:row[key]['value']=q(f(row[key]['value'])/10)
        second['principal_commitment']=money(30);d['loans'].append(second);d['draft']['loan_ids'].append(second['loan_id']);d['draft']['terminal_claims']['loan_principal'][second['loan_id']]=money(20);d['draft']['terminal_claims']['free_cash']=money(609)
        c=build(d);self.assertEqual(c[-1].payload['state'],'reconciled_synthetic_staged_preopening_cash');self.assertEqual(len(c[-1].payload['changes']),24);self.assertEqual(f(c[-1].preopening_run.payload['date_close_balances'][-1]['free_cash']),609)
    def test_source_inventory_target_inventory_and_basis_are_complete(self):
        for change in [lambda p:p['event_slots'].pop(),lambda p:p.update(loans=[]),lambda p:p.update(scope_basis_ref=None),lambda p:p.update(preopening_source_sha256='0'*64)]:
            c=build(sources(),binding_change=change);self.assertEqual(c[-1].payload['state'],'blocked');self.assertIsNone(c[-1].compiled_raw)
    def test_prefilled_zero_wrong_metadata_and_date_not_overridden(self):
        for key,value in [('date','2026-10-02'),('loan_id','SYNTHETIC-unknown'),('category','debt_interest_payment')]:
            def change(p):
                next(e for e in p['events']if e['category']=='loan_draw').update({key:value});p['events'].sort(key=lambda e:e['date'])
            c=build(sources(),draft_change=change);self.assertIsNone(c[-1].compiled_raw)
        def prefill(p):next(e for e in p['events']if e['category']=='loan_draw')['amount']['value']=q(0)
        c=build(sources(),draft_change=prefill);self.assertTrue(any('debt_target_not_empty'in b for b in c[-1].payload['blockers']))
    def test_cash_claim_and_other_missing_input_not_silently_replaced(self):
        d=sources();d['draft']['terminal_claims']['free_cash']=money(591);c=build(d);self.assertIn('compiled_preopening_cash_or_principal_blocked',c[-1].payload['blockers'])
        d=sources();d['draft']['events'][1]['amount']['value']=None;c=build(d);self.assertTrue(any('amount_missing'in b for b in c[-1].payload['cash_blockers']))
    def test_loan_plan_context_time_and_limits_preserved(self):
        for change in [lambda d:d['loans'][0]['context'].update(run_id='SYNTHETIC-other'),lambda d:d['draft'].update(opening_operation_date='2027-01-02'),lambda d:d['loans'][0].update(principal_commitment=money(200))]:
            d=sources();change(d);c=build(d);self.assertEqual(c[-1].payload['state'],'blocked');self.assertIsNone(c[-1].compiled_raw)
    def test_rehashed_loan_forgery_rejected(self):
        c=self.case;e=c[0][0];bad=replace(e,run=forge(e.run,lambda p:p.update(state='forged')))
        with self.assertRaises(ValidationError):assemble_construction_cash((bad,),c[1],c[2])
    def test_exact_source_pointers_and_original_null_inputs_preserved(self):
        c=self.case
        for change in c[-1].payload['changes']:
            value=c[0][0].run.payload
            for part in change['source_pointer'].strip('/').split('/'):value=value[int(part)]if type(value)is list else value[part]
            self.assertEqual(value,change['after']['amount']['value']);self.assertIsNone(change['before']['amount']['value'])
        self.assertTrue(all(e['amount']['value']is None for e in json.loads(c[1])['events']if e['loan_id']is not None));self.assertFalse(c[-1].payload['whole_project_return_connected'])


class ConstructionRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=build(sources());cls.bundle=export_construction_bundle(*cls.case)
    def test_complete_source_recovery_and_deterministic_export(self):
        r=recover_construction_bundle(self.bundle);self.assertEqual(r.run,self.case[-1]);self.assertEqual(r.bundle_sha256,sha(self.bundle));self.assertEqual(export_construction_bundle(r.loans,r.preopening_raw,r.binding_raw,r.run),self.bundle)
    def test_blocked_cash_and_commitment_roundtrip_stay_blocked(self):
        for mutate in [lambda d:d['loans'][0].update(principal_commitment=money(200)),lambda d:d['draft']['terminal_claims'].update(free_cash=money(591))]:
            d=sources();mutate(d);c=build(d);r=recover_construction_bundle(export_construction_bundle(*c));self.assertEqual(r.run,c[-1]);self.assertEqual(r.run.payload['state'],'blocked')
    def test_rehashed_result_and_changed_source_rejected(self):
        b=json.loads(self.bundle);p=json.loads(b['expected_run']['payload_json']);p['decision']='PASS';s=canonical(p);b['expected_run']=dict(payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):recover_construction_bundle(raw(b))
        b=json.loads(self.bundle);p=json.loads(b['loans'][0]['source']);p['periods'][0]['draw_at_start']=money(99);b['loans'][0]['source']=canonical(p)
        with self.assertRaises(ValidationError):recover_construction_bundle(raw(b))
    def test_wrong_version_missing_or_duplicate_json_rejected(self):
        for change in [lambda b:b['versions'].update(T68='0'*64),lambda b:b.update(loans=[]),lambda b:b.update(extra=1)]:
            b=json.loads(self.bundle);change(b)
            with self.assertRaises(ValidationError):recover_construction_bundle(raw(b))
        for b in [self.bundle.decode(),b'{"schema":1,"schema":2}',b'NaN']:
            with self.assertRaises(ValidationError):recover_construction_bundle(b)


class CurrentConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.case=build(sources());cls.bundle=export_construction_bundle(*cls.case);cls.recovered=recover_construction_bundle(cls.bundle);cls.source=registry(cls.recovered,cls.bundle)
    def evaluate(self,change=None):
        p=copy.deepcopy(self.source)
        if change:change(p)
        source=raw(p);return assemble_current_construction_cash(self.bundle,source,evaluate_evidence_currency(source,AT),AT)
    def test_current_review_has_proposed_costs_and_no_final_return(self):
        p=self.evaluate().payload;self.assertEqual(p['state'],'current_synthetic_staged_construction_cash');self.assertEqual(len(p['required_source_bindings']),4);self.assertIn('590.0000',p['markdown']);self.assertIn('1.0000',p['markdown']);self.assertFalse(p['whole_project_return_connected']);self.assertEqual(p['decision'],'PENDING')
    def test_any_expired_source_withdraws_current_numbers(self):
        for req in self.source['requirements']:
            p=self.evaluate(lambda d:next(e for e in d['evidence']if e['requirement_id']==req['requirement_id']).update(valid_until=AT)).payload
            self.assertIsNone(p['current_construction_summary']);self.assertNotIn('590.0000',p['markdown']);self.assertNotIn('1000.0000',p['markdown']);self.assertTrue(p['historical_calculation_preserved'])
    def test_current_evidence_cannot_repair_deficit_or_credit_limit(self):
        for mutate in [lambda d:d['loans'][0].update(principal_commitment=money(200)),lambda d:d['draft']['terminal_claims'].update(free_cash=money(591))]:
            d=sources();mutate(d);c=build(d);b=export_construction_bundle(*c);r=recover_construction_bundle(b);s=raw(registry(r,b));p=assemble_current_construction_cash(b,s,evaluate_evidence_currency(s,AT),AT).payload
            self.assertIn('construction_cash_calculation_blocked',p['blockers']);self.assertIsNone(p['current_construction_summary'])
    def test_missing_pending_estimate_context_and_rehashed_alias_block(self):
        def omit(p):p['requirements'].pop();p['evidence'].pop()
        self.assertIn('complete_construction_source_binding_inventory_mismatch',self.evaluate(omit).payload['blockers'])
        for key,value in [('review_status','pending'),('value_status','estimate')]:self.assertIsNone(self.evaluate(lambda p:p['evidence'][0].update({key:value})).payload['current_construction_summary'])
        self.assertIn('construction_registry_context_mismatch',self.evaluate(lambda p:p['context'].update(run_id='SYNTHETIC-other')).payload['blockers'])
        def stale(p):p['requirements'][0]['source_sha256']='0'*64;p['evidence'][0]['source_sha256']='0'*64
        self.assertIn('complete_construction_source_binding_inventory_mismatch',self.evaluate(stale).payload['blockers'])
    def test_time_and_rehashed_registry_proof_rejected(self):
        s=raw(self.source);r=evaluate_evidence_currency(s,AT)
        with self.assertRaises(ValidationError):assemble_current_construction_cash(self.bundle,s,r,'2027-01-01T12:00:01Z')
        with self.assertRaises(ValidationError):assemble_current_construction_cash(self.bundle,s,forge(r,lambda p:p.update(blockers=['forged'])),AT)


if __name__=='__main__':unittest.main()
