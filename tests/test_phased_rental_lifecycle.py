from dataclasses import replace
from fractions import Fraction as F
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from phased_rental_demo_support import raw,q,change_segment,refresh_calendar,make_registry,AT
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.phased_rental_lifecycle import assemble_phased_rental_lifecycle,export_phased_rental_bundle,recover_phased_rental_bundle,parse_phased_lifecycle_manifest
from miniuw_foundation.current_phased_rental import assemble_current_phased_rental,required_phased_rental_sources
from miniuw_foundation.expense_checked_lifecycle import recover_expense_checked_bundle,assemble_expense_checked_lifecycle,export_expense_checked_bundle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency


class PhasedRentalLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.er=(ROOT/'templates/synthetic-phased-expense-base.json').read_bytes()
        cls.manifest=json.loads((ROOT/'templates/synthetic-phased-lifecycle-manifest.json').read_bytes())
        cls.bundle=(ROOT/'templates/synthetic-phased-rental-bundle.json').read_bytes()

    def run_case(self,p=None):return assemble_phased_rental_lifecycle(self.er,raw(self.manifest if p is None else p))

    def test_whole_cash_return_hand_identity_and_no_second_rent_or_equity(self):
        run=self.run_case();p=run.investor_run.payload;old=recover_expense_checked_bundle(self.er).run
        for k,v in [('gross_contributions',1400),('gross_distributions',778),('net_cash_profit',-622)]:self.assertEqual(p[k],q(v))
        self.assertEqual(p['equity_multiple'],q(F(389,700)));self.assertEqual(p['normalized_story']['total_distributions'],q(F(389,70)))
        self.assertEqual(p['cash_by_category']['net_sale_distribution'],q(578));self.assertEqual(p['cash_by_category']['operating_distribution'],q(200))
        self.assertEqual(1400+250+88+400,1000+10+50+30+100+100+40+10+20+778)
        self.assertEqual(run.compiled_raw,old.compiled_raw);self.assertEqual(run.investor_run,old.investor_run);self.assertEqual(run.payload['cash_risk_run'],old.payload['cash_risk_run'])
        self.assertFalse(run.payload['rental_income_counted_as_additional_equity_receipt']);self.assertFalse(run.payload['new_funding_or_distribution_generated'])
        self.assertIsNone(p['selected_IRR']);self.assertTrue(p['annual_irr_roots']);self.assertIsNone(run.payload['personal_investor_return'])

    def test_partial_period_same_rent_cannot_shorten_the_operating_window(self):
        def shorten(c):c.update(start_date='2027-01-16');c['segments'].pop(0)
        m=refresh_calendar(self.manifest,0,shorten);r=json.loads(m['periods'][0]['calendar_run']['payload_json'])
        self.assertEqual(r['state'],'computed_synthetic_phased_rental');self.assertEqual(r['totals']['effective_rent'],q(28))
        run=self.run_case(m);self.assertIn('SYNTHETIC-hold-1:start_date_mismatch',run.payload['blockers']);self.assertIsNone(run.investor_run)

    def test_changed_availability_or_fraction_requires_new_compatible_NOI(self):
        def fractions(c):c['segments'][0]['proration_fraction']=q(F(3,5));c['segments'][1]['proration_fraction']=q(F(2,5))
        for mutate in (fractions,lambda c:change_segment(c,1,lambda s:s['residential_groups'][0].update(units=q(6)))):
            m=refresh_calendar(self.manifest,0,mutate);self.assertEqual(json.loads(m['periods'][0]['calendar_run']['payload_json'])['state'],'computed_synthetic_phased_rental')
            run=self.run_case(m);self.assertIn('SYNTHETIC-hold-1:rental_income_does_not_equal_exact_NOI_row',run.payload['blockers']);self.assertIsNone(run.investor_run)

    def test_same_rent_total_cannot_change_physical_capacity_between_periods(self):
        m=refresh_calendar(self.manifest,1,lambda c:c['capacity'][0].update(total_units=q(20)));r=json.loads(m['periods'][1]['calendar_run']['payload_json'])
        self.assertEqual(r['state'],'computed_synthetic_phased_rental');self.assertEqual(r['totals']['effective_rent'],q(60))
        self.assertIn('SYNTHETIC-hold-2:physical_capacity_or_rental_income_identity_changed_between_periods',self.run_case(m).payload['blockers'])

    def test_all_period_source_income_context_and_basis_bindings_required(self):
        for mutate in (lambda p:p['periods'].pop(),lambda p:p['periods'].reverse(),lambda p:p['periods'][0].update(period_ref='SYNTHETIC-other'),lambda p:p.update(expense_bundle_sha256='0'*64),lambda p:p.update(currency='EUR'),lambda p:p.update(inventory_declared_complete=None),lambda p:p.update(period_recognition_basis_ref=None),lambda p:p.update(rental_scope_and_no_overlap_basis_ref=None),lambda p:p['context'].update(run_id='SYNTHETIC-other'),lambda p:p['periods'][0].update(noi_source_sha256='0'*64),lambda p:p['periods'][0].update(cash_source_sha256='0'*64),lambda p:p['periods'][0].update(other_zero_income_item_ids=[]),lambda p:p['periods'][0].update(rental_income_item_id='SYNTHETIC-other')):
            p=copy.deepcopy(self.manifest);mutate(p);self.assertIsNone(self.run_case(p).investor_run)

    def test_rehashed_child_proof_and_changed_exact_source_rejected(self):
        p=copy.deepcopy(self.manifest);r=json.loads(p['periods'][0]['calendar_run']['payload_json']);r['totals']['effective_rent']=q(999);encoded=canonical(r)
        p['periods'][0]['calendar_run']=dict(payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.manifest);p['periods'][0]['calendar_source_utf8']+='\n'
        with self.assertRaises(ValidationError):self.run_case(p)

    def test_prior_expense_blocker_remains_blocked_after_portable_recovery(self):
        rec=recover_expense_checked_bundle(self.er);m=json.loads(rec.manifest_raw);m['continuity_basis_ref']=None;mr=raw(m)
        er=export_expense_checked_bundle(rec.lifecycle_raw,mr,assemble_expense_checked_lifecycle(rec.lifecycle_raw,mr));p=copy.deepcopy(self.manifest);p['expense_bundle_sha256']=hashlib.sha256(er).hexdigest();pr=raw(p)
        run=assemble_phased_rental_lifecycle(er,pr);self.assertIn('expense_checked_lifecycle_blocked',run.payload['blockers']);self.assertTrue(all(not e['blockers']for e in run.payload['periods']))
        self.assertIsNone(run.investor_run);self.assertEqual(recover_phased_rental_bundle(export_phased_rental_bundle(er,pr,run)).run,run)

    def test_portable_exact_replay_and_rehashed_result_source_version_forgery(self):
        run=self.run_case();self.assertEqual(export_phased_rental_bundle(self.er,raw(self.manifest),run),self.bundle);self.assertEqual(recover_phased_rental_bundle(self.bundle).run,run)
        p=run.payload;p['decision']='PASS';encoded=canonical(p);fake=replace(run,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):export_phased_rental_bundle(self.er,raw(self.manifest),fake)
        for mutate in (lambda p:p.update(expected_run=dict(payload_json=encoded,sha256=digest(encoded))),lambda p:p['versions'].update(T82='0'*64),lambda p:p.update(expense_bundle_utf8=p['expense_bundle_utf8']+'\n'),lambda p:p.pop('rental_manifest_utf8')):
            p=json.loads(self.bundle);mutate(p)
            with self.assertRaises(ValidationError):recover_phased_rental_bundle(raw(p))
        p=json.loads(self.bundle);m=json.loads(p['rental_manifest_utf8']);m['period_recognition_basis_ref']=None;p['rental_manifest_utf8']=raw(m).decode()
        with self.assertRaises(ValidationError):recover_phased_rental_bundle(raw(p))

    def test_new_profile_strict_shape_invalid_UTF8_and_immutable_scope(self):
        for mutate in (lambda p:p.update(schema='miniuw.synthetic-rental-lifecycle-manifest.v1'),lambda p:p.update(extra=True),lambda p:p.update(inventory_declared_complete=1),lambda p:p['periods'].append(copy.deepcopy(p['periods'][0])),lambda p:p['periods'][0].update(calendar_source_utf8=None)):
            p=copy.deepcopy(self.manifest);mutate(p)
            with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.manifest);p['periods'][0]['calendar_source_utf8']='\ud800'
        with self.assertRaises(ValidationError):parse_phased_lifecycle_manifest(json.dumps(p,ensure_ascii=True).encode())
        for b in (b'{}',b'{"schema":1,"schema":2}',b'NaN',b'\xff',b' '*8_388_609):
            with self.assertRaises(ValidationError):parse_phased_lifecycle_manifest(b)
        run=self.run_case();p=run.payload;p['periods'].clear();self.assertEqual(len(run.payload['periods']),2);self.assertEqual(run.payload['decision'],'PENDING')
        self.assertFalse(run.payload['day_count_delivery_or_collection_authenticated']);self.assertFalse(run.payload['production_authorized'])


class CurrentPhasedRentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=(ROOT/'templates/synthetic-phased-rental-bundle.json').read_bytes();cls.registry=json.loads((ROOT/'templates/synthetic-phased-rental-evidence.json').read_bytes())

    def current(self,p=None):
        rr=raw(self.registry if p is None else p);return assemble_current_phased_rental(self.bundle,rr,evaluate_evidence_currency(rr,AT),AT)

    def test_full_source_current_return_available_fraction_and_expense_view(self):
        p=self.current().payload;self.assertEqual(len(p['required_source_bindings']),37);self.assertEqual(p['current_project_return_story']['gross_distributions'],q(778));self.assertEqual(p['current_project_return_story']['net_cash_profit'],q(-622))
        self.assertEqual([r['available_units']for r in p['current_phased_segments']],[q(v)for v in [0,5,5,10,10,10,10]])
        self.assertEqual([r['amounts']['effective_rent']for r in p['current_phased_segments']],[q(v)for v in [0,5,8,15,20,20,20]])
        self.assertEqual([r['proration_fraction']for r in p['current_phased_segments']],[q(F(1,2)),q(F(1,2))]+[q(1)]*5)
        self.assertEqual(len(p['current_capacity_inventories']),2);self.assertEqual([r['totals']['cash_payments']for r in p['current_expense_period_totals']],[q(10),q(20)])
        self.assertIn('Disponibilidad y fracción suministradas',p['markdown']);self.assertIn('-622.0000',p['markdown']);self.assertEqual(p['decision'],'PENDING')

    def test_expired_segment_capacity_calendar_original_loan_or_expense_withdraws_all_views(self):
        for path in ('/phased/periods/0/segments/1','/phased/periods/0/calendar','/phased/manifest','/transport/phased_rental_bundle','/construction/loans/0','/expense/periods/0/detail'):
            p=copy.deepcopy(self.registry);next(e for e in p['evidence']if e['requirement_id']==path)['valid_until']=AT;r=self.current(p).payload
            for k in ('current_project_return_story','current_phased_segments','current_capacity_inventories','current_expense_period_totals'):self.assertIsNone(r[k])
            self.assertNotIn('778.0000',r['markdown']);self.assertNotIn('-622.0000',r['markdown']);self.assertTrue(r['historical_calculation_preserved'])
        self.assertEqual(recover_phased_rental_bundle(self.bundle).run.investor_run.payload['gross_distributions'],q(778))

    def test_fresh_old_sources_cannot_substitute_for_missing_segment(self):
        p=copy.deepcopy(self.registry);path='/phased/periods/0/segments/0';p['requirements']=[r for r in p['requirements']if r['requirement_id']!=path];p['evidence']=[e for e in p['evidence']if e['requirement_id']!=path]
        self.assertEqual(evaluate_evidence_currency(raw(p),AT).payload['state'],'current_synthetic_evidence');self.assertIn('complete_rental_lifecycle_source_inventory_mismatch',self.current(p).payload['blockers'])

    def test_rehashed_inventory_and_context_do_not_validate_current_sources(self):
        for field,value in [('source_sha256','0'*64),('source_locator','/wrong')]:
            p=copy.deepcopy(self.registry);p['requirements'][-1][field]=value;p['evidence'][-1][field]=value
            self.assertIn('complete_rental_lifecycle_source_inventory_mismatch',self.current(p).payload['blockers'])
        p=copy.deepcopy(self.registry);p['context']['run_id']='SYNTHETIC-other';self.assertIsNone(self.current(p).payload['current_project_return_story'])

    def test_pending_estimated_or_superseded_source_does_not_authenticate_capacity_or_proration(self):
        for field,value in [('review_status','pending'),('value_status','estimate'),('superseded_by_sha256','1'*64)]:
            p=copy.deepcopy(self.registry);p['evidence'][-1][field]=value;self.assertIsNone(self.current(p).payload['current_phased_segments'])

    def test_fresh_sources_do_not_repair_available_rent_NOI_mismatch(self):
        rec=recover_phased_rental_bundle(self.bundle);m=refresh_calendar(json.loads(rec.manifest_raw),0,lambda c:change_segment(c,1,lambda s:s['residential_groups'][0].update(units=q(6))));mr=raw(m)
        run=assemble_phased_rental_lifecycle(rec.expense_raw,mr);b=export_phased_rental_bundle(rec.expense_raw,mr,run);rr=raw(make_registry(b));currency=evaluate_evidence_currency(rr,AT)
        self.assertEqual(currency.payload['state'],'current_synthetic_evidence');p=assemble_current_phased_rental(b,rr,currency,AT).payload;self.assertIn('rental_lifecycle_calculation_blocked',p['blockers']);self.assertIsNone(p['current_project_return_story'])

    def test_exact_time_and_rehashed_registry_guard_with_immutable_no_approval_flags(self):
        rr=raw(self.registry);currency=evaluate_evidence_currency(rr,AT)
        with self.assertRaises(ValidationError):assemble_current_phased_rental(self.bundle,rr,currency,'2027-07-01T12:00:01Z')
        p=currency.payload;p['blockers'].append('forged');encoded=canonical(p)
        with self.assertRaises(ValidationError):assemble_current_phased_rental(self.bundle,rr,replace(currency,payload_json=encoded,sha256=digest(encoded)),AT)
        run=self.current();self.assertEqual(run,self.current());p=run.payload;p['current_phased_segments'].clear();self.assertEqual(len(run.payload['current_phased_segments']),7)
        for k in ('live_expiry_monitor_enabled','actual_delivery_proration_contract_collection_or_review_authenticated','financial_publication_authorized','external_decision_pdf_produced','real_decisions_enabled','production_authorized'):self.assertIs(run.payload[k],False)
        self.assertEqual(len(required_phased_rental_sources(recover_phased_rental_bundle(self.bundle),self.bundle)),37)
