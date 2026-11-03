from dataclasses import replace
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path
import copy
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pypdf import PdfReader

from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.v1_case import run_v1_case,parse_v1_case,blank_input_catalog,blank_criteria,pointer
from miniuw_foundation.v1_projection import construct_projection
from miniuw_foundation.v1_report import render_v1_report,amount,annual_irr,PreviewLayoutError
from miniuw_foundation.v1_artifacts import build_artifacts,write_case_artifacts,audit_directory,technical_audit
from miniuw_foundation.v1_contracts import load_contracts
from miniuw_foundation.phased_rental_lifecycle import recover_phased_rental_bundle
from miniuw_foundation.current_phased_rental import required_phased_rental_sources

ROOT=Path(__file__).resolve().parents[1]
raw=lambda p:(canonical(p)+'\n').encode()
q=lambda n:rational(F(n))


def case():return json.loads((ROOT/'templates/miniuw-v1-synthetic-case.json').read_bytes())


class V1CaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'templates/miniuw-v1-synthetic-case.json').read_bytes();cls.result_run=run_v1_case(cls.source)

    def test_one_declarative_entry_rebuilds_exact_previous_financial_chain(self):
        r=self.result_run;p=r.payload;s=p['current_project_return_story']
        self.assertEqual(r.execution_bundle,(ROOT/'templates/synthetic-phased-rental-bundle.json').read_bytes())
        for key,n in [('gross_contributions',1400),('gross_distributions',778),('net_cash_profit',-622)]:self.assertEqual(s[key],q(n))
        self.assertEqual(s['equity_multiple'],q(F(389,700)));self.assertEqual(len(p['required_source_bindings']),37)
        self.assertGreater(len(p['stages']),15);self.assertEqual(p['state'],'computed_synthetic_profile_with_pending_decision')

    def test_all_55_fields_ten_fresh_criteria_and_scope_pending_visible(self):
        p=self.result_run.payload;self.assertEqual(len(p['original_inputs']),55);self.assertEqual(len(p['metrics']),10)
        self.assertEqual(p['input_catalog_summary'],dict(total=55,bound=1,pending=54));self.assertEqual(p['decision'],'PENDING')
        self.assertEqual(len(p['blockers']['input_catalog']),54)
        a,b=blank_criteria(),blank_criteria();a[0]['pass_condition']['threshold']=q(0);self.assertIsNone(b[0]['pass_condition']['threshold'])
        self.assertTrue(all(c['pass_condition']['threshold']is None and c['fail_condition']['threshold']is None for c in b));self.assertEqual(len(blank_input_catalog()),55)
        for k in ('full_input_sheet_adapter_completed','full_financial_model_completed','independent_financial_audit_completed','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):self.assertIs(p[k],False)

    def test_missing_cash_value_stops_dependencies_without_zero_or_old_numbers(self):
        p=case();p['recipe']['operating_periods'][0]['cash_source']['amounts']['debt_principal_payment']['value']=None
        r=run_v1_case(raw(p));self.assertIsNone(r.payload['current_project_return_story']);self.assertIsNone(r.execution_bundle)
        self.assertTrue(any('operating_cash' in b for b in r.payload['blockers']['projection']))
        self.assertNotIn('sale_cash',[e['stage']for e in r.payload['stages']])

    def test_earlier_cash_deficit_not_repaired_with_generated_equity(self):
        p=case();p['recipe']['preopening_source']['events'][0]['amount']['value']=q(1)
        r=run_v1_case(raw(p));self.assertIsNone(r.payload['current_project_return_story']);self.assertTrue(any('construction_cash' in b for b in r.payload['blockers']['projection']))
        self.assertEqual(p['recipe']['preopening_source']['events'][0]['amount']['value'],q(1))

    def test_expired_source_withdraws_current_story_but_preserves_recovery_bundle(self):
        p=case();p['source_registry']['evidence'][0]['valid_until']=p['as_of_UTC'];r=run_v1_case(raw(p))
        self.assertIsNone(r.payload['current_project_return_story']);self.assertIsNotNone(r.execution_bundle)
        historical=recover_phased_rental_bundle(r.execution_bundle).run.investor_run.payload
        self.assertEqual(historical['gross_distributions'],q(778));self.assertTrue(any('expired' in b for b in r.payload['blockers']['projection']))

    def test_original_mapping_conflict_blocks_projection_and_keeps_both_values(self):
        p=case();p['original_inputs'][0]['value']='per_rentable_sf_per_month';r=run_v1_case(raw(p)).payload
        self.assertIsNone(r['current_project_return_story']);self.assertIn('original_input_and_recipe_conflict',r['blockers']['projection'])
        self.assertEqual(r['original_inputs'][0]['value'],'per_rentable_sf_per_month');self.assertEqual(p['recipe']['operating_periods'][0]['rental_calendar']['capacity'][0]['rent_basis'],'per_unit_per_month')

    def test_zero_is_not_blank_and_pointer_escapes_are_literal(self):
        p=case();p['original_inputs'][1]['value']=q(0);r=run_v1_case(raw(p)).payload['original_inputs'][1]
        self.assertEqual(r['value'],q(0));self.assertNotIn('original_value_missing',r['blockers']);self.assertEqual(r['state'],'PENDING')
        self.assertEqual(pointer({'a/b':{'~key':[q(0)]}},'/a~1b/~0key/0'),q(0))
        for path in ('/missing','/a~2b','/a~1b/~0key/00'):
            with self.assertRaises(ValidationError):pointer({'a/b':{'~key':[q(0)]}},path)

    def test_criteria_bands_or_known_failure_stay_globally_pending_when_incomplete(self):
        base=self.result_run.payload['metrics'][7]
        for fail,expected in [(F(1,2),'BAND'),(F(7,10),'FAIL_CONDITION')]:
            p=case();c=p['criteria'][7];c.update(definition_ref=base['definition_ref'],unit='multiple',period_ref=base['period_ref'],source_ref='SYNTHETIC-new-test-criterion-not-real-adoption',pass_condition=dict(operator='>=',threshold=q(1)),fail_condition=dict(operator='<',threshold=q(fail)))
            r=run_v1_case(raw(p)).payload;self.assertEqual(r['metrics'][7]['comparison_state'],expected);self.assertEqual(r['screening_simulation_result'],'PENDING');self.assertEqual(r['decision'],'PENDING')

    def test_no_historical_defaults_or_selected_IRR_or_personal_return(self):
        p=self.result_run.payload;self.assertIsNone(p['metrics'][8]['value']);s=p['current_project_return_story']
        self.assertTrue(s['annual_irr_roots']);self.assertIsNone(s['selected_IRR']);self.assertIsNone(s['personal_investor_return'])
        self.assertTrue(all(m['criterion']['source_ref']is None for m in p['metrics']));self.assertIsNone(p['metrics'][0]['value'])

    def test_extra_requested_scenario_and_cross_case_context_cannot_use_existing_story(self):
        for mutate in (lambda p:p['required_scenarios'].append('SYNTHETIC-Downside'),lambda p:p['context'].update(run_id='SYNTHETIC-other')):
            p=case();mutate(p);r=run_v1_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(r['blockers']['projection'])

    def test_changed_data_requires_new_explicit_evidence_no_automatic_renewal(self):
        p=case();amounts=p['recipe']['operating_periods'][0]['cash_source']['amounts'];amounts['equity_contribution']['value']=q(10);amounts['capital_expenditure']['value']=q(30)
        stale=run_v1_case(raw(p));self.assertIsNone(stale.payload['current_project_return_story']);self.assertIsNotNone(stale.execution_bundle)
        rec=recover_phased_rental_bundle(stale.execution_bundle);requirements=required_phased_rental_sources(rec,stale.execution_bundle)
        p['case_revision']=2;p['source_registry']['requirements']=requirements
        by_id={r['requirement_id']:r for r in requirements}
        for e in p['source_registry']['evidence']:
            e.update(by_id[e['requirement_id']]);e['basis_ref']='SYNTHETIC-explicit-new-test-evidence-revision'
        changed=run_v1_case(raw(p));s=changed.payload['current_project_return_story'];self.assertEqual(s['gross_contributions'],q(1410));self.assertEqual(s['gross_distributions'],q(778));self.assertEqual(s['net_cash_profit'],q(-632))
        report=render_v1_report(raw(p),changed);self.assertIn('1410.0000',PdfReader(BytesIO(report.pdf_bytes)).pages[0].extract_text())

    def test_computed_linkages_and_expected_results_cannot_be_supplied_or_silently_ignored(self):
        for mutate in (lambda p:p['recipe']['operating_periods'][0]['cash_source'].update(noi_run_sha256='0'*64),lambda p:p['recipe']['expense_manifest']['periods'][0].update(detail_run={'forged':True}),lambda p:p['recipe'].update(expected_run={'fake':True})):
            p=case();mutate(p);r=run_v1_case(raw(p)).payload;self.assertIsNone(r['current_project_return_story']);self.assertTrue(any('source_contract_error' in s for s in r['blockers']['projection']))

    def test_strict_root_and_complete_catalogue_and_synthetic_context(self):
        for mutate in (lambda p:p.update(extra=True),lambda p:p.update(profile='live'),lambda p:p['context'].update(deal_id='actual-deal'),lambda p:p.update(case_revision=True),lambda p:p.update(title='line\nbreak'),lambda p:p['original_inputs'].pop(),lambda p:p['criteria'].reverse(),lambda p:p['criteria'][0]['pass_condition'].update(threshold=0.2)):
            p=case();mutate(p)
            with self.assertRaises(ValidationError):parse_v1_case(raw(p))
        for b in (b'{}',b'{"schema":1,"schema":2}',b'NaN',b'\xff',b' '*16_777_217):
            with self.assertRaises(ValidationError):parse_v1_case(b)

    def test_immutable_repeatable_input_and_result_versions(self):
        again=run_v1_case(self.source);self.assertEqual(again,self.result_run);p=again.payload;p['metrics'].clear();self.assertEqual(len(again.payload['metrics']),10)
        whitespace=run_v1_case(self.source+b'\n');self.assertNotEqual(whitespace.sha256,self.result_run.sha256);self.assertEqual(whitespace.execution_bundle,self.result_run.execution_bundle)


class V1ReportArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'templates/miniuw-v1-synthetic-case.json').read_bytes();cls.contents,cls.result_run,cls.report=build_artifacts(cls.source)

    def test_exactly_one_readable_page_with_investor_story_and_ten_metrics(self):
        reader=PdfReader(BytesIO(self.report.pdf_bytes));self.assertEqual(len(reader.pages),1);text=reader.pages[0].extract_text()
        for value in ('PENDIENTE','1400.0000','778.0000','-622.0000','5.5571','2026-10-01','2027-07-01','Cash-in','CoC','IRR anual','54 pendientes','Retorno personal pendiente'):self.assertIn(value,text)
        self.assertEqual(len(self.result_run.payload['metrics']),10)
        for span in self.report.manifest['display_spans']:
            self.assertIn(span['text'],text);self.assertGreaterEqual(span['x'],24);self.assertLessEqual(span['x']+span['width'],768);self.assertGreaterEqual(span['y'],25)

    def test_expired_case_gets_one_page_pending_without_old_financial_numbers(self):
        p=case();p['source_registry']['evidence'][0]['valid_until']=p['as_of_UTC'];source=raw(p);run=run_v1_case(source);report=render_v1_report(source,run)
        reader=PdfReader(BytesIO(report.pdf_bytes));self.assertEqual(len(reader.pages),1);text=reader.pages[0].extract_text()
        self.assertIn('PENDIENTE',text)
        for value in ('778.0000','1400.0000','-622.0000','578.0000'):self.assertNotIn(value,text)

    def test_rehashed_results_and_report_forgery_rejected(self):
        p=self.result_run.payload;p['current_project_return_story']['gross_distributions']=q(999);s=canonical(p);fake=replace(self.result_run,payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):render_v1_report(self.source,fake)
        manifest=self.report.manifest;manifest['pdf_sha256']='0'*64;s=canonical(manifest);bad=replace(self.report,manifest_json=s,manifest_sha256=digest(s))
        with self.assertRaises(ValidationError):technical_audit(self.source,self.result_run,bad)

    def test_layout_and_unsupported_glyphs_fail_without_clipping_or_extra_page(self):
        p=case();p['title']='SYNTHETIC \U0001f600';source=raw(p);run=run_v1_case(source)
        with self.assertRaises(PreviewLayoutError):render_v1_report(source,run)
        self.assertIn('no cero',amount(q(F(1,1000000))));self.assertEqual(amount(q(0)),'0.0000')
        roots=self.result_run.payload['current_project_return_story']['annual_irr_roots'];self.assertIn('Ambigua',annual_irr(roots+roots))

    def test_atomic_local_output_retries_and_full_directory_audit(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'run';first=write_case_artifacts(self.source,out);self.assertEqual(first['page_count'],1)
            before={p.name:p.read_bytes()for p in out.iterdir()};second=write_case_artifacts(self.source,out);self.assertEqual(second['status'],'identical_existing_verified')
            self.assertEqual(audit_directory(out)['files_verified'],8);self.assertEqual(before,{p.name:p.read_bytes()for p in out.iterdir()})
            other=case();other['case_revision']=2
            with self.assertRaises(ValidationError):write_case_artifacts(raw(other),out)
            self.assertEqual(before,{p.name:p.read_bytes()for p in out.iterdir()})

    def test_altered_bytes_rehashed_package_extra_file_and_unsafe_path_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'run';out.mkdir()
            for name,data in self.contents.items():(out/name).write_bytes(data)
            (out/'results.json').write_bytes(b'{}')
            with self.assertRaises(ValidationError):audit_directory(out)
            package=json.loads(self.contents['package.json']);row=next(r for r in package['files']if r['path']=='results.json');row.update(bytes=2,sha256=hashlib.sha256(b'{}').hexdigest());(out/'package.json').write_bytes(raw(package))
            with self.assertRaises(ValidationError):audit_directory(out)
            for name,data in self.contents.items():(out/name).write_bytes(data)
            (out/'unexpected').write_text('extra')
            with self.assertRaises(ValidationError):audit_directory(out)
            (out/'unexpected').unlink();package=json.loads(self.contents['package.json']);package['files'][0]['path']='../../outside'
            (out/'package.json').write_bytes(raw(package))
            with self.assertRaises(ValidationError):audit_directory(out)

    def test_failed_local_materialization_leaves_no_partial_final_directory(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'run'
            with patch('miniuw_foundation.v1_artifacts.os.rename',side_effect=OSError('injected rename failure')):
                with self.assertRaises(OSError):write_case_artifacts(self.source,out)
            self.assertFalse(out.exists());self.assertEqual(list(Path(td).iterdir()),[])


class V1DotBotContractTests(unittest.TestCase):
    def test_all_seven_dots_and_seventeen_bots_have_io_blockers_and_dependencies(self):
        p,sha=load_contracts();self.assertEqual(len(p['dots']),7);self.assertEqual(len(p['bots']),17);self.assertEqual(len(sha),64)
        for row in p['dots']+p['bots']:
            for key in ('inputs','outputs','blockers','status'):self.assertTrue(row[key])

    def test_unimplemented_extractors_and_independent_audit_not_claimed_active(self):
        p,_=load_contracts();bots={b['bot_id']:b for b in p['bots']}
        for bid in ('B03','B05','B06','B07','B08','B09','B10','B11'):self.assertEqual(bots[bid]['status'],'contract_only_pending')
        self.assertEqual(bots['B16']['status'],'deterministic_check_only');self.assertEqual(bots['B17']['status'],'release_test_contract');self.assertFalse(p['external_actions_enabled']);self.assertFalse(p['independent_financial_audit_implemented'])

    def test_contract_cycle_and_unimplemented_role_promotion_rejected(self):
        p,_=load_contracts()
        for mutate in (lambda x:x['bots'][0].update(depends_on=['B16']),lambda x:x['bots'][4].update(status='synthetic_callable'),lambda x:x['dots'][0]['bot_ids'].pop()):
            data=copy.deepcopy(p);mutate(data)
            with tempfile.TemporaryDirectory()as td:
                path=Path(td)/'contracts.json';path.write_bytes(raw(data))
                with patch('miniuw_foundation.v1_contracts.PATH',path):
                    with self.assertRaises(ValidationError):load_contracts()
