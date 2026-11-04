from dataclasses import replace
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader

from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.irr_checked_output import assemble_irr_checked_output,render_irr_checked_report,IRR_BLOCKER
from miniuw_foundation.irr_checked_artifacts import (build_irr_checked_artifacts,export_irr_checked_bundle,
    recover_irr_checked_bundle,write_irr_checked_artifacts,audit_irr_checked_directory,versions)
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.v1_report import annual_irr

ROOT=Path(__file__).resolve().parents[1]
source=lambda label:(ROOT/('templates/miniuw-v1-'+label+'-case.json')).read_bytes()
raw=lambda p:(canonical(p)+'\n').encode()
q=lambda v:rational(F(v))


class IRRCheckedOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=source('long-window');cls.files,cls.checked=build_irr_checked_artifacts(cls.case)
        cls.manifest=json.loads(cls.files['report-manifest.json'])
        cls.text=PdfReader(BytesIO(cls.files['MiniUW_v1_Resumen.pdf'])).pages[0].extract_text()

    def test_long_case_replays_prior_ledger_and_completes_same_budget_without_selecting_point(self):
        p=self.checked.payload;e=p['irr_recalculation'];s=p['current_project_return_story'];r=s['periodic_irr']
        self.assertEqual(e['previous_periodic_irr']['root_classification'],'arithmetic_budget_exhausted')
        self.assertEqual(r['status'],'complete_synthetic');self.assertEqual(r['distinct_positive_discount_roots'],1)
        self.assertEqual(r['operation_budget'],e['parameters']['operation_budget']);self.assertEqual(r['coefficient_bit_limit'],4096)
        self.assertLessEqual(r['arithmetic_operations'],r['operation_budget'])
        self.assertEqual(len(e['dated_net_flows']),65);self.assertEqual(len(e['grid']['dates']),65)
        self.assertNotIn(IRR_BLOCKER,s['upstream_story_blockers'])
        self.assertIsNone(s['selected_IRR']);self.assertFalse(p['IRR_point_comparison_enabled'])
        self.assertEqual(p['irr_output_state'],'computed_unique_conditional_annual_root_without_point')
        self.assertEqual(p['current_IRR_solver_result_sha256'],digest(canonical(r)))
        self.assertIsNone(p['current_projection_run_sha256'])
        self.assertEqual(p['parent_current_projection_run_sha256'],self.checked.parent_run.payload['current_projection_run_sha256'])

    def test_all_cash_risk_capital_and_annual_fields_are_identical_to_verified_parent(self):
        p=self.checked.payload;s=p['current_project_return_story'];before=self.checked.parent_run.payload['current_project_return_story']
        for key in s:
            if key not in ('periodic_irr','annual_irr_roots','upstream_story_blockers'):self.assertEqual(s[key],before[key],key)
        self.assertEqual(s['gross_contributions'],q(1400));self.assertEqual(s['gross_distributions'],q(778));self.assertEqual(s['net_cash_profit'],q(-622))
        self.assertIsNone(s['capital_snapshots'][-1]['capital_still_invested'])
        self.assertIsNone(s['capital_snapshots'][-1]['retained_equity_value']);self.assertIsNone(s['personal_investor_return'])
        self.assertTrue(any('snapshot:'in b for b in s['upstream_story_blockers']))

    def test_annual_interval_matches_independent_discount_factor_transformation(self):
        s=self.checked.payload['current_project_return_story'];root=s['periodic_irr']['roots'][0]
        interval=root['discount_factor_interval'];a,b=F(interval['lower']),F(interval['upper'])
        annual=s['annual_irr_roots'][0]['annual_rate_interval']
        self.assertEqual(F(annual['lower']['numerator'])/F(annual['lower']['denominator']),b**-12-1)
        self.assertEqual(F(annual['upper']['numerator'])/F(annual['upper']['denominator']),a**-12-1)
        self.assertTrue(annual['lower_closed']);self.assertFalse(annual['upper_closed'])

    def test_one_page_keeps_exhaustive_groups_years_pending_stocks_and_current_result_hash(self):
        reader=PdfReader(BytesIO(self.files['MiniUW_v1_Resumen.pdf']));self.assertEqual(len(reader.pages),1)
        self.assertEqual(self.manifest['result_component'],'T100');self.assertEqual(self.manifest['result_sha256'],self.checked.sha256)
        self.assertIn('Resultado T100 SHA256: '+self.checked.sha256,self.text)
        self.assertIn('IRR anual: '+annual_irr(self.checked.payload['current_project_return_story']['annual_irr_roots']),self.text)
        self.assertIn('Capital declarado: Pendiente',self.text);self.assertIn('Valor retenido (no caja): Pendiente',self.text)
        self.assertEqual(self.manifest['annual_years'],list(range(2022,2028)))
        self.assertEqual(sorted(i for g in self.manifest['event_groups']for i in g['event_indices']),list(range(16)))
        self.assertTrue(all(row['text']in self.text for row in self.manifest['display_spans']))

    def test_numerical_result_does_not_fill_criteria_or_enable_financial_decisions(self):
        p=self.checked.payload
        for m in p['metrics']:
            self.assertIsNone(m['criterion']['source_ref']);self.assertEqual(m['comparison_state'],'PENDING')
        irr=next(m for m in p['metrics']if m['metric_id']=='IRR');self.assertIsNone(irr['value'])
        for key in ('financial_policy_adopted','financial_publication_authorized','deployment_enabled','real_decisions_enabled','personal_return_verified'):
            self.assertFalse(p[key])
        self.assertEqual(p['decision'],'PENDING');self.assertEqual(p['input_catalog_summary']['pending'],54)

    def test_explicit_zero_stocks_and_short_case_annual_roots_remain_exact(self):
        case=source('capital-zero');run=assemble_irr_checked_output(case);p=run.payload
        self.assertEqual(p['latest_capital_state'],'declared_synthetic_not_derived')
        self.assertEqual(p['current_project_return_story']['capital_snapshots'][0]['capital_still_invested'],q(0))
        self.assertEqual(p['current_project_return_story']['annual_irr_roots'],run.parent_run.payload['current_project_return_story']['annual_irr_roots'])
        text=PdfReader(BytesIO(render_irr_checked_report(case,run).pdf_bytes)).pages[0].extract_text()
        self.assertIn('Capital declarado: 0',text)

    def test_expired_parent_does_not_recompute_or_publish_historical_IRR(self):
        p=json.loads(self.case);reg=json.loads(p['registry_utf8']);reg['evidence'][-1]['valid_until']=p['as_of_UTC'];p['registry_utf8']=canonical(reg)
        files,run=build_irr_checked_artifacts(raw(p));recovered=recover_irr_checked_bundle(files['execution-evidence.json'])
        self.assertEqual(recovered.run,run);self.assertIsNone(run.payload['current_project_return_story']);self.assertIsNone(run.payload['irr_recalculation'])
        self.assertIsNone(run.payload['current_IRR_solver_result_sha256'])
        text=PdfReader(BytesIO(recovered.report.pdf_bytes)).pages[0].extract_text()
        self.assertIn('IRR anual: Pendiente',text);self.assertNotIn('2022 A 1000',text)

    def test_declared_tiny_budget_stays_pending_without_discarding_cash(self):
        case=source('IRR-budget');run=assemble_irr_checked_output(case);s=run.payload['current_project_return_story']
        self.assertEqual(s['periodic_irr']['operation_budget'],1);self.assertEqual(s['periodic_irr']['status'],'incomplete_synthetic')
        self.assertEqual(s['annual_irr_roots'],[]);self.assertEqual(run.payload['irr_output_state'],'PENDING')
        self.assertEqual(s['gross_distributions'],q(778));self.assertIn(IRR_BLOCKER,s['upstream_story_blockers'])
        self.assertIn('IRR_incomplete_root_inventory_current_intervals_withheld',s['upstream_story_blockers'])

    def test_missing_frequency_keeps_monthly_proof_and_withholds_annual_rate(self):
        case=source('IRR-frequency-pending');run=assemble_irr_checked_output(case);s=run.payload['current_project_return_story']
        self.assertEqual(s['periodic_irr']['status'],'complete_synthetic');self.assertEqual(len(s['periodic_irr']['roots']),1)
        self.assertEqual(s['annual_irr_roots'],[]);self.assertEqual(run.payload['irr_output_state'],'PENDING')
        self.assertIn('annualization_frequency_missing_or_inconsistent',s['upstream_story_blockers'])
        self.assertEqual(s['gross_distributions'],q(778));self.assertIsNone(run.payload['irr_recalculation']['parameters']['periods_per_year'])

    def test_rehashed_result_parent_and_report_or_changed_source_are_rejected(self):
        p=self.checked.payload;p['current_project_return_story']['annual_irr_roots']=[]
        value=canonical(p);fake=replace(self.checked,payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):render_irr_checked_report(self.case,fake)
        with self.assertRaises(ValidationError):export_irr_checked_bundle(self.case,fake)
        with self.assertRaises(ValidationError):render_irr_checked_report(self.case+b'\n',self.checked)
        actual=render_irr_checked_report(self.case,self.checked)
        with self.assertRaises(ValidationError):export_irr_checked_bundle(self.case,self.checked,replace(actual,pdf_bytes=b'forged'))

    def test_portable_source_first_roundtrip_reproduces_new_numerical_view_and_pdf(self):
        recovered=recover_irr_checked_bundle(self.files['execution-evidence.json'])
        self.assertEqual(recovered.run,self.checked);self.assertEqual(recovered.case_raw,self.case)
        self.assertEqual(recovered.report.pdf_bytes,self.files['MiniUW_v1_Resumen.pdf'])
        self.assertEqual(export_irr_checked_bundle(self.case,self.checked,recovered.report),self.files['execution-evidence.json'])

    def test_portable_blocked_numerical_inputs_keep_pending_and_do_not_gain_a_frequency(self):
        for label in ('IRR-budget','IRR-frequency-pending'):
            files,run=build_irr_checked_artifacts(source(label));recovered=recover_irr_checked_bundle(files['execution-evidence.json'])
            self.assertEqual(recovered.run,run);self.assertEqual(run.payload['irr_output_state'],'PENDING')
            self.assertEqual(run.payload['current_project_return_story']['annual_irr_roots'],[])

    def test_bundle_version_result_manifest_and_pdf_forgeries_are_rejected(self):
        original=self.files['execution-evidence.json']
        for key in versions():
            p=json.loads(original);p[key]='0'*64
            with self.assertRaises(ValidationError):recover_irr_checked_bundle(raw(p))
        for key,value in (('pdf_sha256','0'*64),('report_manifest_utf8','{}')):
            p=json.loads(original);p[key]=value
            with self.assertRaises(ValidationError):recover_irr_checked_bundle(raw(p))
        p=json.loads(original);result=json.loads(p['result']['payload_json']);result['current_project_return_story']['gross_distributions']=q(999)
        text=canonical(result);p['result']=dict(payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):recover_irr_checked_bundle(raw(p))

    def test_local_write_identical_retry_audit_and_different_source_no_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'out';write_irr_checked_artifacts(self.case,target)
            before={p.name:p.read_bytes()for p in target.iterdir()}
            self.assertEqual(audit_irr_checked_directory(target)['files_verified'],8)
            self.assertEqual(write_irr_checked_artifacts(self.case,target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_irr_checked_artifacts(self.case+b'\n',target)
            self.assertEqual(before,{p.name:p.read_bytes()for p in target.iterdir()})

    def test_rehashed_inventory_extra_path_and_symlink_cannot_replace_replayed_output(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for name,value in self.files.items():(root/name).write_bytes(value)
            restore();(root/'results.json').write_bytes(b'{}');p=json.loads(self.files['package.json'])
            row=next(r for r in p['files']if r['path']=='results.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_irr_checked_directory(root)
            restore();p=json.loads(self.files['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_irr_checked_directory(root)
            restore();(root/'extra.txt').write_bytes(b'extra')
            with self.assertRaises(ValidationError):audit_irr_checked_directory(root)
            (root/'extra.txt').unlink();(root/'audit.json').unlink();(root/'audit.json').symlink_to(root/'results.json')
            with self.assertRaises(ValidationError):audit_irr_checked_directory(root)

    def test_failed_rename_preserves_existing_sibling_and_cleans_owned_temp(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep.txt';keep.write_bytes(b'keep')
            with patch('miniuw_foundation.irr_checked_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_irr_checked_artifacts(self.case,root/'out')
            self.assertEqual(list(root.iterdir()),[keep]);self.assertEqual(keep.read_bytes(),b'keep')


if __name__=='__main__':unittest.main()
