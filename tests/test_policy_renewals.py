from dataclasses import replace
from fractions import Fraction
from io import BytesIO
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader

from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.insurance_renewals import reconcile_insurance_renewals,parse_policy_book
from miniuw_foundation.policy_renewal_case import assemble_policy_renewal_case,parse_policy_renewal_case
from miniuw_foundation.policy_renewal_artifacts import (build_policy_renewal_artifacts,render_policy_renewal_report,export_policy_renewal_bundle,recover_policy_renewal_bundle,write_policy_renewal_artifacts,audit_policy_renewal_directory)
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import PreviewLayoutError

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'templates/miniuw-v1-policy-renewal-case.json').read_bytes()
TWELVE=(ROOT/'templates/miniuw-v1-policy-renewal-twelve-case.json').read_bytes()
raw=lambda p:(canonical(p)+'\n').encode()
q=lambda n:rational(Fraction(n))
def entry():return json.loads(BASE)
def book():return json.loads((ROOT/'templates/synthetic-insurance-policy-book.json').read_bytes())
def aggregate():return (ROOT/'templates/synthetic-insurance-schedule.json').read_bytes()


def explicit_test_registry(p):
    # Test-fixture-only declared evidence revision; runtime never refreshes sources.
    req=assemble_policy_renewal_case(raw(p)).payload['required_source_bindings'];reg=json.loads(p['registry_utf8']);old={e['requirement_id']:e for e in reg['evidence']};seed=reg['evidence'][0];evidence=[]
    for i,r in enumerate(req):
        e=copy.deepcopy(old.get(r['requirement_id'],seed));e.update(r);e.update(evidence_id='SYNTHETIC-policy-test-'+str(i),basis_ref='SYNTHETIC-explicit-test-source-revision');evidence.append(e)
    reg.update(requirements=req,evidence=evidence);p['registry_utf8']=raw(reg).decode();return raw(p)


class InsuranceRenewalTests(unittest.TestCase):
    def test_successive_policies_grouped_dues_and_no_duplicate_expense(self):
        p=reconcile_insurance_renewals(aggregate(),raw(book())).payload;self.assertEqual(p['blockers'],[]);self.assertEqual(p['totals']['premiums'],q(20));self.assertEqual(list(p['totals']['expense_by_period'].values()),[q(10),q(10)])
        self.assertEqual([g['sum']for g in p['installment_groups']],[q(5),q(15)]);self.assertEqual(p['policy_rows'][0]['coverage_end'],'2027-04-01');self.assertFalse(p['coverage_adequacy_verified']);self.assertFalse(p['new_expense_or_payment_generated'])

    def test_policy_crossing_operating_boundary_uses_supplied_fractions_not_days(self):
        a=json.loads(aggregate());a['allocations'][0]['fraction']=q(Fraction(1,4));a['allocations'][1]['fraction']=q(Fraction(3,4));ar=raw(a);p=book();p['aggregate_source_sha256']=sha(ar)
        first,second=p['policies'];first['coverage_end']='2027-04-15';second['coverage_start']='2027-04-15';first['allocations'][0]['fraction']=q(Fraction(1,2));first['allocations'].append(dict(a['allocations'][1],start_date='2027-04-01',end_date='2027-04-15',fraction=q(Fraction(1,2))));second['allocations'][0]['start_date']='2027-04-15'
        r=reconcile_insurance_renewals(ar,raw(p)).payload;self.assertEqual(r['blockers'],[]);self.assertEqual(list(r['totals']['expense_by_period'].values()),[q(5),q(15)])

    def test_gaps_overlaps_order_and_incomplete_coverage_withhold_all_exports(self):
        for change in (lambda p:p['policies'][1].update(coverage_start='2027-04-02'),lambda p:p['policies'][1].update(coverage_start='2027-03-31'),lambda p:p['policies'].reverse(),lambda p:p['policies'].pop()):
            p=book();change(p);r=reconcile_insurance_renewals(aggregate(),raw(p)).payload;self.assertIsNone(r['totals']);self.assertTrue(r['blockers']);self.assertTrue(all(row['expense']is None for row in r['policy_rows']))

    def test_missing_premium_or_fraction_even_at_zero_is_not_zero(self):
        for change in (lambda p:p['policies'][0].update(premium=None),lambda p:p['policies'][0]['allocations'][0].update(fraction=None),lambda p:p['policies'][0]['allocations'][0].update(fraction=q(-1))):
            p=book();change(p);r=reconcile_insurance_renewals(aggregate(),raw(p)).payload;self.assertIsNone(r['totals']);self.assertTrue(all(a['allocated_expense']is None for row in r['policy_rows']for a in row['allocations']))

    def test_unchanged_money_does_not_allow_wrong_coverage_intersections(self):
        p=book();p['policies'][0]['coverage_end']='2027-04-02';p['policies'][1]['coverage_start']='2027-04-02'
        r=reconcile_insurance_renewals(aggregate(),raw(p)).payload;self.assertIsNone(r['totals']);self.assertTrue(any('operating_intersections' in b for b in r['blockers']))

    def test_group_inventory_unknown_members_and_duplicate_mapping_rejected(self):
        p=book();p['installment_groups'].pop();self.assertIsNone(reconcile_insurance_renewals(aggregate(),raw(p)).payload['totals'])
        p=book();p['installment_groups'][0]['policy_installments'][0]['installment_id']='SYNTHETIC-unknown';r=reconcile_insurance_renewals(aggregate(),raw(p)).payload;self.assertTrue(any('unknown_policy_installment' in b for b in r['blockers']))
        p=book();p['installment_groups'][1]['policy_installments'].append(copy.deepcopy(p['installment_groups'][0]['policy_installments'][0]))
        with self.assertRaises(ValidationError):parse_policy_book(raw(p))

    def test_same_total_installments_cannot_offset_differences_between_groups(self):
        p=book();p['policies'][0]['installments'][0]['amount']=q(6);p['policies'][0]['installments'][1]['amount']=q(4)
        r=reconcile_insurance_renewals(aggregate(),raw(p)).payload;self.assertIsNone(r['totals']);self.assertTrue(any('group_sum_differs' in b for b in r['blockers']));self.assertTrue(all(g['sum']is None for g in r['installment_groups']))

    def test_due_after_coverage_allowed_only_as_supplied_within_payment_window(self):
        p=book();self.assertGreater(p['policies'][0]['installments'][1]['due_date'],p['policies'][0]['coverage_end']);self.assertIsNotNone(reconcile_insurance_renewals(aggregate(),raw(p)).payload['totals'])
        for change in (lambda p:p['policies'][0]['installments'][1].update(due_date='2027-07-01'),lambda p:p['policies'][0]['installments'][1].update(source_ref=None),lambda p:p['installment_groups'][0].update(source_ref=None)):
            p=book();change(p);self.assertIsNone(reconcile_insurance_renewals(aggregate(),raw(p)).payload['totals'])

    def test_zero_cost_retains_policies_and_explicit_fraction_inventory(self):
        a=json.loads(aggregate());a['total_cost']=q(0);a['installments']=[];ar=raw(a);p=book();p['aggregate_source_sha256']=sha(ar);p['installment_groups']=[]
        for policy in p['policies']:policy.update(premium=q(0),installments=[])
        r=reconcile_insurance_renewals(ar,raw(p)).payload;self.assertEqual(r['totals']['premiums'],q(0));self.assertEqual(len(r['policy_rows']),2)
        p['policies'][0]['allocations'][0]['fraction']=None;self.assertIsNone(reconcile_insurance_renewals(ar,raw(p)).payload['totals'])

    def test_strict_schema_context_hashes_and_identity_domains(self):
        for change in (lambda p:p.update(extra=True),lambda p:p.update(schema='live'),lambda p:p['context'].update(deal_id='real-deal'),lambda p:p['policies'][0].update(premium=0.5),lambda p:p['policies'].append(copy.deepcopy(p['policies'][0]))):
            p=book();change(p)
            with self.assertRaises(ValidationError):parse_policy_book(raw(p))
        p=book();p['aggregate_source_sha256']='0'*64;r=reconcile_insurance_renewals(aggregate(),raw(p)).payload;self.assertIn('aggregate_source_hash_mismatch',r['blockers'])
        for b in (b'{}',b'NaN',b'\xff',b'{"schema":1,"schema":2}'):
            with self.assertRaises(ValidationError):parse_policy_book(b)

    def test_injected_and_real_denominator_budget_withdraw_all_computed_amounts(self):
        with patch('miniuw_foundation.insurance_renewals._bounded',side_effect=ArithmeticBudgetError('injected')):
            r=reconcile_insurance_renewals(aggregate(),raw(book())).payload;self.assertIn('exact_arithmetic_budget_exceeded',r['blockers']);self.assertIsNone(r['totals'])
        p=book();seed=p['policies'][0];dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01','2027-05-01','2027-06-01','2027-07-01'];policies=[]
        for i in range(6):
            value=q(Fraction(1,2**800+2*i+1));policy=copy.deepcopy(seed);policy.update(policy_id='SYNTHETIC-budget-policy-'+str(i),coverage_start=dates[i],coverage_end=dates[i+1],premium=value)
            policy['allocations']=[dict(period_ref=('SYNTHETIC-hold-1'if i<3 else'SYNTHETIC-hold-2'),start_date=dates[i],end_date=dates[i+1],fraction=q(1),source_ref='SYNTHETIC-a'+str(i))];policy['installments']=[dict(installment_id='SYNTHETIC-due'+str(i),due_date=dates[i],amount=value,source_ref='SYNTHETIC-due-source'+str(i))];policies.append(policy)
        p['policies']=policies;r=reconcile_insurance_renewals(aggregate(),raw(p)).payload;self.assertIn('exact_arithmetic_budget_exceeded',r['blockers']);self.assertIsNone(r['totals'])

    def test_repeat_immutability_and_exact_byte_source_identity(self):
        source=raw(book());a=reconcile_insurance_renewals(aggregate(),source);self.assertEqual(a,reconcile_insurance_renewals(aggregate(),source));p=a.payload;p['policy_rows'].clear();self.assertTrue(a.payload['policy_rows'])
        b=reconcile_insurance_renewals(aggregate(),source+b'\n');self.assertNotEqual(a.sha256,b.sha256);self.assertEqual(a.payload['totals'],b.payload['totals'])


class PolicyRenewalCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result_run=assemble_policy_renewal_case(BASE)

    def test_all_43_sources_keep_existing_return_criteria_and_pending_scope(self):
        p=self.result_run.payload;self.assertEqual(p['policy_blockers'],[]);self.assertEqual(len(p['required_source_bindings']),43);s=p['current_project_return_story'];self.assertEqual(s['gross_contributions'],q(1400));self.assertEqual(s['gross_distributions'],q(778));self.assertEqual(s['net_cash_profit'],q(-622));self.assertEqual(s['equity_multiple'],q(Fraction(389,700)))
        self.assertEqual(p['input_catalog_summary']['pending'],54);self.assertFalse(p['new_expense_payment_or_equity_generated']);self.assertTrue(all(m['criterion']['source_ref']is None for m in p['metrics']));self.assertEqual(p['decision'],'PENDING')

    def test_explicit_premium_twelve_complete_case_counts_increment_only_once(self):
        p=assemble_policy_renewal_case(TWELVE).payload;self.assertEqual(p['policy_blockers'],[]);s=p['current_project_return_story'];self.assertEqual(s['gross_distributions'],q(776));self.assertEqual(s['net_cash_profit'],q(-624));self.assertEqual(s['equity_multiple'],q(Fraction(97,175)));self.assertEqual(p['current_policy_cost_totals'][0]['totals']['premiums'],q(22))

    def test_unknown_or_missing_and_duplicate_book_cannot_skip_insurance_control(self):
        p=entry();b=json.loads(p['policy_books_utf8'][0]);b['schedule_id']='SYNTHETIC-unknown';p['policy_books_utf8'][0]=raw(b).decode();r=assemble_policy_renewal_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('insurance_policy_book_inventory' in s for s in r['policy_blockers']))
        p=entry();p['policy_books_utf8'].append(p['policy_books_utf8'][0])
        with self.assertRaises(ValidationError):parse_policy_renewal_case(raw(p))
        p=entry();p['policy_books_utf8']=[]
        with self.assertRaises(ValidationError):parse_policy_renewal_case(raw(p))

    def test_newly_rehashed_inconsistent_policy_cost_still_withdraws_parent_current_numbers(self):
        p=entry();b=json.loads(p['policy_books_utf8'][0]);b['policies'][1]['premium']=q(11);p['policy_books_utf8'][0]=raw(b).decode();r=assemble_policy_renewal_case(explicit_test_registry(p)).payload
        for key in ('current_project_return_story','current_schedule_totals','current_policy_cost_totals'):self.assertIsNone(r[key])
        self.assertIsNone(r['metrics'][7]['value']);self.assertTrue(r['policy_blockers'])

    def test_parent_and_policy_evidence_expiry_independently_withdraw_all_current_views(self):
        for layer in ('parent','policy'):
            p=entry()
            if layer=='parent':
                parent=json.loads(p['scheduled_case_utf8']);reg=json.loads(parent['registry_utf8']);reg['evidence'][-1]['valid_until']=parent['as_of_UTC'];parent['registry_utf8']=raw(reg).decode();p['scheduled_case_utf8']=raw(parent).decode();source=explicit_test_registry(p)
            else:
                reg=json.loads(p['registry_utf8']);reg['evidence'][-1]['valid_until']=p['as_of_UTC'];p['registry_utf8']=raw(reg).decode();source=raw(p)
            r=assemble_policy_renewal_case(source).payload;self.assertIsNone(r['current_project_return_story']);self.assertIsNone(r['current_policy_cost_totals']);self.assertIsNone(r['current_schedule_totals']);self.assertTrue(r['policy_blockers'])

    def test_common_time_context_and_currency_required_without_automatic_evidence_renewal(self):
        for change in (lambda p:p.update(as_of_UTC='2027-07-01T12:01:00Z'),lambda p:p.update(policy_books_utf8=[raw(dict(json.loads(p['policy_books_utf8'][0]),currency='EUR')).decode()])):
            p=entry();change(p);r=assemble_policy_renewal_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(r['policy_blockers'])

    def test_group_mapping_unknown_target_with_fresh_source_evidence_remains_pending(self):
        p=entry();b=json.loads(p['policy_books_utf8'][0]);b['installment_groups'][0]['aggregate_installment_id']='SYNTHETIC-unknown-due';p['policy_books_utf8'][0]=raw(b).decode();r=assemble_policy_renewal_case(explicit_test_registry(p)).payload
        self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('aggregate_installment' in s for s in r['policy_blockers']))

    def test_missing_base_cash_value_does_not_crash_or_get_filled(self):
        p=entry();parent=json.loads(p['scheduled_case_utf8']);base=json.loads(parent['base_case_utf8']);base['recipe']['operating_periods'][0]['cash_source']['amounts']['debt_principal_payment']['value']=None;parent['base_case_utf8']=raw(base).decode();p['scheduled_case_utf8']=raw(parent).decode()
        r=assemble_policy_renewal_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertIn('scheduled_parent_current_projection_unavailable',r['policy_blockers']);self.assertFalse(r['real_decisions_enabled'])

    def test_same_total_changed_coverage_boundaries_require_exact_period_intersections(self):
        p=entry();b=json.loads(p['policy_books_utf8'][0]);b['policies'][0]['coverage_end']='2027-04-02';b['policies'][1]['coverage_start']='2027-04-02';p['policy_books_utf8'][0]=raw(b).decode();r=assemble_policy_renewal_case(explicit_test_registry(p)).payload
        self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('operating_intersections' in s for s in r['policy_blockers']))


class PolicyRenewalArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.contents,cls.result_run=build_policy_renewal_artifacts(BASE)

    def test_exact_one_page_eight_artifacts_manifest_and_complete_current_story(self):
        reader=PdfReader(BytesIO(self.contents['MiniUW_v1_Resumen.pdf']));self.assertEqual(len(reader.pages),1);text=reader.pages[0].extract_text()
        for value in ('Renovaciones de seguros','1400.0000','778.0000','-622.0000','PENDIENTE'):self.assertIn(value,text)
        manifest=json.loads(self.contents['report-manifest.json']);self.assertEqual(manifest['component'],'T95');self.assertEqual(manifest['input_sha256'],sha(BASE))
        for row in manifest['display_spans']:self.assertIn(row['text'],text)
        self.assertEqual(len(self.contents),8)

    def test_exact_portable_replay_versions_and_rehashed_forgery_rejected(self):
        bundle=self.contents['execution-evidence.json'];self.assertEqual(recover_policy_renewal_bundle(bundle),self.result_run)
        for key in ('engine_sha256','case_engine_sha256','policy_engine_sha256','inventory_engine_sha256','definition_sha256'):
            p=json.loads(bundle);p[key]='0'*64
            with self.assertRaises(ValidationError):recover_policy_renewal_bundle(raw(p))
        p=self.result_run.payload;p['current_project_return_story']['gross_distributions']=q(999);s=canonical(p);fake=replace(self.result_run,payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):render_policy_renewal_report(BASE,fake)
        with self.assertRaises(ValidationError):export_policy_renewal_bundle(BASE,fake)
        b=json.loads(bundle);b['result']=dict(payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):recover_policy_renewal_bundle(raw(b))

    def test_expired_policy_withholds_pdf_money_and_blocked_bundle_replays(self):
        p=entry();reg=json.loads(p['registry_utf8']);reg['evidence'][-1]['valid_until']=p['as_of_UTC'];p['registry_utf8']=raw(reg).decode();contents,run=build_policy_renewal_artifacts(raw(p));text=PdfReader(BytesIO(contents['MiniUW_v1_Resumen.pdf'])).pages[0].extract_text()
        for value in ('778.0000','1400.0000','-622.0000','578.0000'):self.assertNotIn(value,text)
        self.assertIn('CIFRAS ACTUALES RETIRADAS',contents['schedule-review.txt'].decode());self.assertEqual(recover_policy_renewal_bundle(contents['execution-evidence.json']),run)

    def test_local_atomic_output_retry_audit_and_no_different_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'case';write_policy_renewal_artifacts(BASE,out);before={p.name:p.read_bytes()for p in out.iterdir()};self.assertEqual(write_policy_renewal_artifacts(BASE,out)['status'],'identical_existing_verified');self.assertEqual(audit_policy_renewal_directory(out)['files_verified'],8)
            with self.assertRaises(ValidationError):write_policy_renewal_artifacts(BASE+b'\n',out)
            self.assertEqual(before,{p.name:p.read_bytes()for p in out.iterdir()})

    def test_rehashed_altered_artifact_extra_path_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)
            for k,v in self.contents.items():(out/k).write_bytes(v)
            (out/'results.json').write_bytes(b'{}');p=json.loads(self.contents['package.json']);row=next(r for r in p['files']if r['path']=='results.json');row.update(bytes=2,sha256=sha(b'{}'));(out/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_policy_renewal_directory(out)
            for k,v in self.contents.items():(out/k).write_bytes(v)
            p=json.loads(self.contents['package.json']);p['files'][0]['path']='../../outside';(out/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_policy_renewal_directory(out)
            (out/'package.json').write_bytes(self.contents['package.json']);(out/'audit.json').unlink();(out/'audit.json').symlink_to(out/'results.json')
            with self.assertRaises(ValidationError):audit_policy_renewal_directory(out)

    def test_failed_final_rename_cleans_temp_without_partial_output(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'case'
            with patch('miniuw_foundation.policy_renewal_artifacts.os.rename',side_effect=OSError('injected rename failure')),patch('miniuw_foundation.policy_renewal_artifacts.build_policy_renewal_artifacts',return_value=(self.contents,self.result_run)):
                with self.assertRaises(OSError):write_policy_renewal_artifacts(BASE,out)
            self.assertFalse(out.exists());self.assertEqual(list(Path(td).iterdir()),[])

    def test_strict_root_and_export_size_budget_preserve_no_release(self):
        for change in (lambda p:p.update(extra=True),lambda p:p.update(schema='live'),lambda p:p.update(policy_books_utf8=[])):
            p=entry();change(p)
            with self.assertRaises(ValidationError):parse_policy_renewal_case(raw(p))
        for b in (b'{}',b'\xff',b'{"schema":1,"schema":2}'):
            with self.assertRaises(ValidationError):recover_policy_renewal_bundle(b)
        with patch('miniuw_foundation.policy_renewal_artifacts.MAX_BUNDLE_BYTES',100):
            with self.assertRaises(ValidationError):export_policy_renewal_bundle(BASE,self.result_run)
