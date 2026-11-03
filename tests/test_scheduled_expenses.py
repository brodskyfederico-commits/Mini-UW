from dataclasses import replace
from fractions import Fraction
from io import BytesIO
from pathlib import Path
import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from pypdf import PdfReader

from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.expense_schedule import produce_expense_schedule,parse_expense_schedule
from miniuw_foundation.scheduled_expense_case import assemble_scheduled_expense_case,parse_scheduled_expense_case,parse_binding,sha
from miniuw_foundation.scheduled_expense_artifacts import (build_scheduled_expense_artifacts,export_scheduled_expense_bundle,recover_scheduled_expense_bundle,
    render_scheduled_expense_report,write_scheduled_expense_artifacts,audit_scheduled_expense_directory)
from miniuw_foundation.synthetic_onepager import PreviewLayoutError

ROOT=Path(__file__).resolve().parents[1]
raw=lambda p:(canonical(p)+'\n').encode()
q=lambda n:rational(Fraction(n))
BASE=(ROOT/'templates/miniuw-v1-scheduled-expense-case.json').read_bytes()
TAX=(ROOT/'templates/miniuw-v1-scheduled-tax-four-case.json').read_bytes()


def insurance():return json.loads((ROOT/'templates/synthetic-insurance-schedule.json').read_bytes())
def zero_tax():return json.loads((ROOT/'templates/synthetic-zero-tax-schedule.json').read_bytes())
def entry():return json.loads(BASE)


def fresh_synthetic_test_entry(p):
    # Explicit independent test-fixture evidence revision; never invoked by runtime.
    binding=json.loads(p['binding_utf8']);binding['base_case_sha256']=sha(p['base_case_utf8'].encode())
    by={json.loads(s)['schedule_id']:s.encode()for s in p['schedule_sources_utf8']}
    for row in binding['schedules']:
        if row['schedule_id']in by:row['schedule_source_sha256']=sha(by[row['schedule_id']])
    p['binding_utf8']=raw(binding).decode();required=assemble_scheduled_expense_case(raw(p)).payload['required_source_bindings']
    registry=json.loads(p['registry_utf8']);old={e['requirement_id']:e for e in registry['evidence']};seed=registry['evidence'][0];evidence=[]
    for i,r in enumerate(required):
        e=copy.deepcopy(old.get(r['requirement_id'],seed));e.update(r);e.update(evidence_id='SYNTHETIC-explicit-test-evidence-'+str(i),basis_ref='SYNTHETIC-test-revision-not-authority');evidence.append(e)
    registry.update(requirements=required,evidence=evidence);p['registry_utf8']=raw(registry).decode();return raw(p)


class ExpenseScheduleTests(unittest.TestCase):
    def test_explicit_insurance_cost_fractions_and_installments(self):
        p=produce_expense_schedule(raw(insurance())).payload
        self.assertEqual(p['totals'],dict(expense=q(20),installments=q(20),fraction_sum=q(1)));self.assertEqual([r['allocated_expense']for r in p['allocations']],[q(10),q(10)])
        self.assertEqual([r['amount']for r in p['installments']],[q(5),q(15)])
        for k in ('coverage_adequacy_verified','source_or_due_date_authority_verified','tax_or_accounting_policy_adopted','bank_payments_verified','real_decisions_enabled'):self.assertFalse(p[k])

    def test_explicit_zero_tax_keeps_complete_empty_installment_inventory(self):
        s=zero_tax();p=produce_expense_schedule(raw(s)).payload;self.assertEqual(p['totals']['expense'],q(0));self.assertEqual(p['installments'],[])
        s['installment_inventory_declared_complete']=None;r=produce_expense_schedule(raw(s)).payload;self.assertIsNone(r['totals']);self.assertTrue(r['blockers'])

    def test_missing_fraction_blocks_even_with_zero_cost(self):
        s=zero_tax();s['allocations'][0]['fraction']=None;p=produce_expense_schedule(raw(s)).payload
        self.assertIsNone(p['totals']);self.assertTrue(all(r['allocated_expense']is None for r in p['allocations']))

    def test_gaps_overlaps_order_and_incomplete_window_block(self):
        for change in (lambda p:p['allocations'][1].update(start_date='2027-04-02'),lambda p:p['allocations'][1].update(start_date='2027-03-31'),lambda p:p['allocations'].reverse(),lambda p:p['allocations'].pop()):
            s=insurance();change(s);p=produce_expense_schedule(raw(s)).payload;self.assertIsNone(p['totals']);self.assertTrue(p['blockers'])

    def test_supplied_half_fractions_are_not_derived_from_unequal_day_counts(self):
        from datetime import date
        s=insurance();a,b=s['allocations'];self.assertNotEqual((date.fromisoformat(a['end_date'])-date.fromisoformat(a['start_date'])).days,(date.fromisoformat(b['end_date'])-date.fromisoformat(b['start_date'])).days)
        p=produce_expense_schedule(raw(s)).payload;self.assertEqual(p['allocations'][0]['allocated_expense'],q(10));self.assertEqual(p['allocations'][1]['allocated_expense'],q(10))

    def test_fraction_domain_and_complete_sum_required(self):
        for f in (q(-1),q(2),q(Fraction(1,4))):
            s=insurance();s['allocations'][0]['fraction']=f;p=produce_expense_schedule(raw(s)).payload;self.assertIsNone(p['totals']);self.assertTrue(p['blockers'])

    def test_missing_incomplete_and_wrong_total_installments_withhold_all_totals(self):
        for change in (lambda p:p.update(installment_inventory_declared_complete=False),lambda p:p['installments'].pop(),lambda p:p['installments'][0].update(amount=None),lambda p:p['installments'][0].update(amount=q(-1))):
            s=insurance();change(s);p=produce_expense_schedule(raw(s)).payload;self.assertIsNone(p['totals']);self.assertTrue(p['blockers'])

    def test_installment_dates_obey_half_open_service_window(self):
        for day in ('2026-12-31','2027-07-01'):
            s=insurance();s['installments'][0]['due_date']=day;p=produce_expense_schedule(raw(s)).payload;self.assertIsNone(p['totals']);self.assertTrue(any('outside_half_open' in b for b in p['blockers']))

    def test_required_source_and_allocation_basis_references(self):
        for change in (lambda p:p.update(source_ref=None),lambda p:p.update(allocation_basis_ref=None),lambda p:p['allocations'][0].update(source_ref=None),lambda p:p['installments'][0].update(source_ref=None)):
            s=insurance();change(s);p=produce_expense_schedule(raw(s)).payload;self.assertIsNone(p['totals']);self.assertTrue(p['blockers'])

    def test_strict_schema_context_exact_rationals_and_assumptions(self):
        for change in (lambda p:p.update(extra=1),lambda p:p.update(kind='income_tax'),lambda p:p['context'].update(deal_id='real-deal'),lambda p:p.update(total_cost=0.2),lambda p:p['assumptions'].update(refunds_credits_fees=True),lambda p:p.update(period_inventory_declared_complete=1)):
            s=insurance();change(s)
            with self.assertRaises(ValidationError):parse_expense_schedule(raw(s))
        for b in (b'{}',b'NaN',b'\xff',b'{"schema":1,"schema":2}'):
            with self.assertRaises(ValidationError):parse_expense_schedule(b)

    def test_duplicate_period_installment_or_source_identity_rejected(self):
        for change in (lambda p:p['allocations'].append(copy.deepcopy(p['allocations'][0])),lambda p:p['installments'].append(copy.deepcopy(p['installments'][0])),lambda p:p['installments'][1].update(source_ref=p['installments'][0]['source_ref'])):
            s=insurance();change(s)
            with self.assertRaises(ValidationError):parse_expense_schedule(raw(s))

    def test_injected_and_real_arithmetic_budget_withholds_every_allocated_number(self):
        with patch('miniuw_foundation.expense_schedule._bounded',side_effect=ArithmeticBudgetError('injected')):
            p=produce_expense_schedule(raw(insurance())).payload;self.assertIn('exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['totals'])
        s=insurance();dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01','2027-05-01','2027-06-01','2027-07-01'];s['allocations']=[dict(period_ref='SYNTHETIC-p'+str(i),start_date=dates[i],end_date=dates[i+1],fraction=q(Fraction(1,2**800+2*i+1)),source_ref='SYNTHETIC-f'+str(i))for i in range(6)]
        p=produce_expense_schedule(raw(s)).payload;self.assertIn('exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['totals']);self.assertTrue(all(r['allocated_expense']is None for r in p['allocations']))

    def test_repeated_immutable_result_and_input(self):
        source=raw(insurance());r=produce_expense_schedule(source);self.assertEqual(r,produce_expense_schedule(source));p=r.payload;p['allocations'].clear();self.assertTrue(r.payload['allocations']);self.assertEqual(source,raw(insurance()))

    def test_zero_does_not_allow_missing_periods_and_explicit_zero_installment_is_retained(self):
        s=zero_tax();s['allocations']=[];self.assertIsNone(produce_expense_schedule(raw(s)).payload['totals'])
        s=zero_tax();s['installments']=[dict(installment_id='SYNTHETIC-zero-due',due_date='2027-03-01',amount=q(0),source_ref='SYNTHETIC-zero-due-source')]
        p=produce_expense_schedule(raw(s)).payload;self.assertEqual(p['totals']['installments'],q(0));self.assertEqual(len(p['installments']),1)


class ScheduledExpenseCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result_run=assemble_scheduled_expense_case(BASE)

    def test_all_41_sources_and_existing_cash_return_are_preserved_without_new_flows(self):
        p=self.result_run.payload;self.assertEqual(p['schedule_blockers'],[]);self.assertEqual(len(p['required_source_bindings']),41)
        s=p['current_project_return_story'];self.assertEqual(s['gross_contributions'],q(1400));self.assertEqual(s['gross_distributions'],q(778));self.assertEqual(s['net_cash_profit'],q(-622));self.assertEqual(s['equity_multiple'],q(Fraction(389,700)))
        self.assertEqual(p['input_catalog_summary']['pending'],54);self.assertFalse(p['new_expense_payment_or_equity_generated']);self.assertIsNone(s['selected_IRR']);self.assertEqual(p['decision'],'PENDING')

    def test_independently_supplied_tax_four_reaches_sale_and_return_once(self):
        p=assemble_scheduled_expense_case(TAX).payload;self.assertEqual(p['schedule_blockers'],[]);s=p['current_project_return_story']
        self.assertEqual(s['gross_contributions'],q(1400));self.assertEqual(s['gross_distributions'],q(774));self.assertEqual(s['net_cash_profit'],q(-626));self.assertEqual(s['equity_multiple'],q(Fraction(387,700)))
        tax=next(s for s in p['current_schedule_totals']if s['kind']=='property_tax');self.assertEqual(tax['totals']['expense'],q(4));self.assertTrue(all(m['criterion']['source_ref']is None for m in p['metrics']))

    def test_missing_schedule_or_unbound_target_cannot_hide_other_compatible_totals(self):
        p=entry();p['schedule_sources_utf8'].pop(0);r=assemble_scheduled_expense_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertIsNone(r['current_schedule_totals']);self.assertTrue(r['schedule_blockers'])
        p=entry();b=json.loads(p['binding_utf8']);b['schedules'].pop(0);p['binding_utf8']=raw(b).decode();r=assemble_scheduled_expense_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('target_inventory' in b for b in r['schedule_blockers']))

    def test_equal_total_with_different_insurance_allocations_is_not_same_NOI(self):
        p=entry();s=json.loads(p['schedule_sources_utf8'][0]);s['allocations'][0]['fraction']=q(Fraction(1,4));s['allocations'][1]['fraction']=q(Fraction(3,4));p['schedule_sources_utf8'][0]=raw(s).decode()
        r=assemble_scheduled_expense_case(fresh_synthetic_test_entry(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('differs_from_exact_NOI_expense' in b for b in r['schedule_blockers']));self.assertIsNone(r['metrics'][7]['value'])

    def test_due_date_change_needs_resolution_even_when_amounts_match(self):
        p=entry();s=json.loads(p['schedule_sources_utf8'][0]);s['installments'][0]['due_date']='2027-03-02';p['schedule_sources_utf8'][0]=raw(s).decode()
        r=assemble_scheduled_expense_case(fresh_synthetic_test_entry(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('due_date_differs' in b for b in r['schedule_blockers']))

    def test_installment_amounts_cannot_offset_each_other(self):
        p=entry();s=json.loads(p['schedule_sources_utf8'][0]);s['installments'][0]['amount']=q(6);s['installments'][1]['amount']=q(14);p['schedule_sources_utf8'][0]=raw(s).decode()
        r=assemble_scheduled_expense_case(fresh_synthetic_test_entry(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('payment_amount_mismatch' in b for b in r['schedule_blockers']))

    def test_old_and_new_evidence_gates_cannot_substitute_for_each_other(self):
        for layer in ('base','schedule'):
            p=entry()
            if layer=='base':
                b=json.loads(p['base_case_utf8']);b['source_registry']['evidence'][0]['valid_until']=b['as_of_UTC'];p['base_case_utf8']=raw(b).decode();source=fresh_synthetic_test_entry(p)
            else:
                reg=json.loads(p['registry_utf8']);e=next(e for e in reg['evidence']if e['requirement_id'].startswith('/scheduled-expense/sources/'));e['valid_until']=p['as_of_UTC'];p['registry_utf8']=raw(reg).decode();source=raw(p)
            r=assemble_scheduled_expense_case(source).payload;self.assertIsNone(r['current_project_return_story']);self.assertIsNone(r['current_schedule_totals']);self.assertTrue(r['schedule_blockers'])

    def test_currency_item_class_and_unchanged_amount_different_periods_block(self):
        for change in (lambda s:s.update(currency='EUR'),lambda s:s.update(kind='property_tax'),lambda s:(s['allocations'][0].update(end_date='2027-03-31'),s['allocations'][1].update(start_date='2027-03-31'))):
            p=entry();s=json.loads(p['schedule_sources_utf8'][0]);change(s);p['schedule_sources_utf8'][0]=raw(s).decode();r=assemble_scheduled_expense_case(fresh_synthetic_test_entry(p)).payload
            self.assertIsNone(r['current_project_return_story']);self.assertTrue(r['schedule_blockers'])

    def test_missing_base_cash_value_withholds_new_profile_without_repair_or_crash(self):
        p=entry();b=json.loads(p['base_case_utf8']);b['recipe']['operating_periods'][0]['cash_source']['amounts']['debt_principal_payment']['value']=None;p['base_case_utf8']=raw(b).decode()
        r=assemble_scheduled_expense_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertIsNone(r['current_schedule_totals']);self.assertIn('base_current_projection_unavailable',r['schedule_blockers'])
        self.assertEqual(json.loads(p['base_case_utf8'])['recipe']['operating_periods'][0]['cash_source']['amounts']['debt_principal_payment']['value'],None)

    def test_exact_case_source_binding_and_common_time_required(self):
        for change in (lambda p:p.update(as_of_UTC='2027-07-01T12:01:00Z'),lambda p:p.update(binding_utf8=raw(dict(json.loads(p['binding_utf8']),base_case_sha256='0'*64)).decode())):
            p=entry();change(p);r=assemble_scheduled_expense_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(r['schedule_blockers'])


class ScheduledExpenseArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.contents,cls.result_run=build_scheduled_expense_artifacts(BASE)

    def test_one_page_41_source_current_story_and_exact_manifest_text(self):
        reader=PdfReader(BytesIO(self.contents['MiniUW_v1_Resumen.pdf']));self.assertEqual(len(reader.pages),1);text=reader.pages[0].extract_text()
        for v in ('Seguros e impuestos','1400.0000','778.0000','-622.0000','PENDIENTE'):self.assertIn(v,text)
        manifest=json.loads(self.contents['report-manifest.json']);self.assertEqual(manifest['component'],'T92');self.assertEqual(manifest['input_sha256'],sha(BASE))
        for span in manifest['display_spans']:self.assertIn(span['text'],text)
        self.assertEqual(len(self.contents),8)

    def test_expired_schedule_withdraws_page_numbers_and_blocked_bundle_still_replays(self):
        p=entry();reg=json.loads(p['registry_utf8']);reg['evidence'][-1]['valid_until']=p['as_of_UTC'];p['registry_utf8']=raw(reg).decode();contents,run=build_scheduled_expense_artifacts(raw(p))
        text=PdfReader(BytesIO(contents['MiniUW_v1_Resumen.pdf'])).pages[0].extract_text()
        for v in ('778.0000','1400.0000','-622.0000','578.0000'):self.assertNotIn(v,text)
        self.assertIsNone(run.payload['metrics'][7]['value']);self.assertIn('CIFRAS ACTUALES RETIRADAS',contents['schedule-review.txt'].decode());self.assertEqual(recover_scheduled_expense_bundle(contents['execution-evidence.json']),run)

    def test_exact_source_portable_positive_replay_and_changed_version_rejection(self):
        bundle=self.contents['execution-evidence.json'];self.assertEqual(recover_scheduled_expense_bundle(bundle),self.result_run);self.assertEqual(json.loads(bundle)['case_utf8'].encode(),BASE)
        for k in ('engine_sha256','case_engine_sha256','schedule_engine_sha256','definition_sha256'):
            p=json.loads(bundle);p[k]='0'*64
            with self.assertRaises(ValidationError):recover_scheduled_expense_bundle(raw(p))
        with patch('miniuw_foundation.scheduled_expense_artifacts.MAX_BUNDLE_BYTES',100):
            with self.assertRaises(ValidationError):export_scheduled_expense_bundle(BASE,self.result_run)

    def test_rehashed_result_forgery_does_not_bypass_report_export_or_recovery(self):
        p=self.result_run.payload;p['current_project_return_story']['gross_distributions']=q(999);s=canonical(p);fake=replace(self.result_run,payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):render_scheduled_expense_report(BASE,fake)
        with self.assertRaises(ValidationError):export_scheduled_expense_bundle(BASE,fake)
        b=json.loads(self.contents['execution-evidence.json']);b['result']=dict(payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):recover_scheduled_expense_bundle(raw(b))

    def test_materialization_exact_retry_audit_and_different_input_not_overwritten(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'case';write_scheduled_expense_artifacts(BASE,out);before={p.name:p.read_bytes()for p in out.iterdir()};self.assertEqual(write_scheduled_expense_artifacts(BASE,out)['status'],'identical_existing_verified')
            self.assertEqual(audit_scheduled_expense_directory(out)['files_verified'],8)
            with self.assertRaises(ValidationError):write_scheduled_expense_artifacts(BASE+b'\n',out)
            self.assertEqual(before,{p.name:p.read_bytes()for p in out.iterdir()})

    def test_altered_rehashed_artifacts_unsafe_inventory_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)
            for k,v in self.contents.items():(out/k).write_bytes(v)
            (out/'results.json').write_bytes(b'{}');p=json.loads(self.contents['package.json']);r=next(r for r in p['files']if r['path']=='results.json');r.update(bytes=2,sha256=sha(b'{}'));(out/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_scheduled_expense_directory(out)
            for k,v in self.contents.items():(out/k).write_bytes(v)
            p=json.loads(self.contents['package.json']);p['files'][0]['path']='../../outside';(out/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_scheduled_expense_directory(out)
            (out/'package.json').write_bytes(self.contents['package.json']);(out/'audit.json').unlink();(out/'audit.json').symlink_to(out/'results.json')
            with self.assertRaises(ValidationError):audit_scheduled_expense_directory(out)

    def test_failed_rename_leaves_no_partial_final_output(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'case'
            with patch('miniuw_foundation.scheduled_expense_artifacts.os.rename',side_effect=OSError('injected rename error')),patch('miniuw_foundation.scheduled_expense_artifacts.build_scheduled_expense_artifacts',return_value=(self.contents,self.result_run)):
                with self.assertRaises(OSError):write_scheduled_expense_artifacts(BASE,out)
            self.assertFalse(out.exists());self.assertEqual(list(Path(td).iterdir()),[])

    def test_strict_wrapper_binding_and_unsupported_pdf_glyph_prevent_output(self):
        for change in (lambda p:p.update(extra=True),lambda p:p.update(schema='live'),lambda p:p.update(schedule_sources_utf8=[])):
            p=entry();change(p)
            with self.assertRaises(ValidationError):parse_scheduled_expense_case(raw(p))
        b=json.loads(entry()['binding_utf8']);b['schedules'][0]['installment_links'].append(b['schedules'][0]['installment_links'][0])
        with self.assertRaises(ValidationError):parse_binding(raw(b))
        p=entry();b=json.loads(p['base_case_utf8']);b['case_id']='SYNTHETIC-\U0001f600';p['base_case_utf8']=raw(b).decode();source=fresh_synthetic_test_entry(p)
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'case'
            with self.assertRaises(PreviewLayoutError):write_scheduled_expense_artifacts(source,out)
            self.assertFalse(out.exists())
