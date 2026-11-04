from dataclasses import replace
from io import BytesIO
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.irr_interval_output import assemble_irr_interval_output,render_irr_interval_report
from miniuw_foundation.irr_interval_artifacts import (build_irr_interval_artifacts,export_irr_interval_bundle,
    recover_irr_interval_bundle,write_irr_interval_artifacts,audit_irr_interval_directory,versions)
from miniuw_foundation.scheduled_expense_case import sha

ROOT=Path(__file__).resolve().parents[1]
source=lambda label:(ROOT/('templates/miniuw-v1-IRR-condition-'+label+'-case.json')).read_bytes()
raw=lambda p:(canonical(p)+'\n').encode()


class IRRIntervalOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=source('band');cls.files,cls.checked=build_irr_interval_artifacts(cls.case)
        cls.manifest=json.loads(cls.files['report-manifest.json'])
        cls.text=PdfReader(BytesIO(cls.files['MiniUW_v1_Resumen.pdf'])).pages[0].extract_text()

    def test_six_explicit_synthetic_condition_states_do_not_become_deal_pass_or_fail(self):
        for label,state in (('pass','PASS_CONDITION'),('fail','FAIL_CONDITION'),('band','BAND'),
            ('conflict','CONFLICT'),('budget','PENDING'),('frequency','PENDING')):
            run=self.checked if label=='band'else assemble_irr_interval_output(source(label))
            p=run.payload;check=p['IRR_interval_comparison']
            self.assertEqual(check['row_state'],state,label);self.assertEqual(p['decision'],'PENDING')
            self.assertEqual(p['screening_simulation_result'],'PENDING');self.assertEqual(check['decision'],'PENDING')
            self.assertEqual(check['scope'],'single_synthetic_IRR_condition_not_deal')
            self.assertFalse(check['full_deal_result_recomputed']);self.assertFalse(check['criteria_adopted'])
            self.assertIsNone(p['current_project_return_story']['selected_IRR'])
            self.assertIsNone(next(m for m in p['metrics']if m['metric_id']=='IRR')['value'])

    def test_band_preserves_explicit_user_policy_and_professional_pending_without_variable_adjustment(self):
        p=self.checked.payload;c=p['IRR_interval_comparison']
        self.assertEqual(c['row_state'],'BAND');self.assertEqual(c['relations'],dict(pass_condition='none',fail_condition='none'))
        self.assertIn('intermediate_band_pending_professional_review',c['blockers'])
        self.assertTrue(c['professional_review_needed_for_band']);self.assertEqual(c['band_policy'],'pending_professional_review')
        self.assertIn('sha256',c['user_band_policy_reference'])
        for key in ('point_rate_selected','precision_automatically_increased','variables_automatically_adjusted','criterion_source_authenticated'):
            self.assertFalse(c[key])
        for key in ('real_decisions_enabled','deployment_enabled','financial_publication_authorized','financial_policy_adopted','IRR_point_comparison_enabled'):
            self.assertFalse(p[key])

    def test_parent_cash_roots_stocks_criteria_and_point_screening_are_byte_equivalent(self):
        p=self.checked.payload;parent=self.checked.parent_run.payload
        for key in ('current_project_return_story','metrics','screening_run_sha256','screening_simulation_result',
            'input_catalog_summary','capital_source_claims','capital_visibility','irr_recalculation','current_IRR_solver_result_sha256'):
            self.assertEqual(p[key],parent[key],key)
        self.assertEqual(p['parent_IRR_checked_run_sha256'],self.checked.parent_run.sha256)
        self.assertEqual(p['input_catalog_summary']['pending'],54)
        self.assertIsNone(p['current_project_return_story']['capital_snapshots'][-1]['capital_still_invested'])

    def test_original_blank_criteria_remain_pending_without_inherited_hurdles(self):
        case=(ROOT/'templates/miniuw-v1-long-window-case.json').read_bytes();p=assemble_irr_interval_output(case).payload
        c=p['IRR_interval_comparison'];self.assertEqual(c['row_state'],'PENDING');self.assertIsNotNone(c['enclosure'])
        self.assertIsNone(c['criterion']['source_ref']);self.assertIsNone(c['criterion']['pass_condition']['threshold'])
        self.assertIn('criterion_source_ref_missing',c['blockers']);self.assertIn('definition_ref_missing_or_mismatch',c['blockers'])

    def test_expired_parent_withdraws_current_condition_and_root_and_recovers_pending(self):
        p=json.loads(self.case);reg=json.loads(p['registry_utf8']);reg['evidence'][-1]['valid_until']=p['as_of_UTC'];p['registry_utf8']=canonical(reg)
        files,run=build_irr_interval_artifacts(raw(p));recovered=recover_irr_interval_bundle(files['execution-evidence.json'])
        self.assertEqual(recovered.run,run);c=run.payload['IRR_interval_comparison']
        self.assertIsNone(run.payload['current_project_return_story']);self.assertIsNone(c['enclosure']);self.assertEqual(c['row_state'],'PENDING')
        text=PdfReader(BytesIO(recovered.report.pdf_bytes)).pages[0].extract_text()
        self.assertIn('IRR por intervalo: pendiente',text);self.assertIn('IRR anual: Pendiente',text)
        self.assertNotIn('2022 A 1000',text)

    def test_one_page_explicit_simulation_labels_keep_deal_pending_and_all_years(self):
        labels={'pass':'cumple regla (sim.)','fail':'no cumple regla (sim.)','band':'banda pendiente','conflict':'reglas en conflicto'}
        for label,value in labels.items():
            if label=='band':pdf=self.files['MiniUW_v1_Resumen.pdf'];manifest=self.manifest;run=self.checked
            else:
                case=source(label);run=assemble_irr_interval_output(case);report=render_irr_interval_report(case,run)
                pdf=report.pdf_bytes;manifest=report.manifest
            pages=PdfReader(BytesIO(pdf));self.assertEqual(len(pages.pages),1);text=pages.pages[0].extract_text()
            self.assertIn('IRR por intervalo: '+value,text);self.assertIn('Decision: PENDIENTE',text)
            self.assertIn('[fraccion anual]',text)
            self.assertIn('Resultado T101 SHA256: '+run.sha256,text)
            self.assertTrue(all(row['text']in text for row in manifest['display_spans']))
            self.assertEqual(manifest['annual_years'],list(range(2022,2028)))
            body=[r for r in manifest['display_spans']if 125<r['y']<445]
            for i,a in enumerate(body):
                for b in body[i+1:]:
                    overlap_x=a['x']<b['x']+b['width']and b['x']<a['x']+a['width']
                    overlap_y=a['y']<b['y']+b['font_size']and b['y']<a['y']+a['font_size']
                    self.assertFalse(overlap_x and overlap_y,(a['text'],b['text']))

    def test_rehashed_condition_parent_or_report_cannot_replace_complete_source_replay(self):
        p=self.checked.payload;p['IRR_interval_comparison']['row_state']='PASS_CONDITION'
        text=canonical(p);fake=replace(self.checked,payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):render_irr_interval_report(self.case,fake)
        with self.assertRaises(ValidationError):export_irr_interval_bundle(self.case,fake)
        with self.assertRaises(ValidationError):render_irr_interval_report(self.case+b'\n',self.checked)
        report=render_irr_interval_report(self.case,self.checked)
        with self.assertRaises(ValidationError):export_irr_interval_bundle(self.case,self.checked,replace(report,pdf_bytes=b'forged'))

    def test_exact_portable_roundtrip_replays_criterion_policy_condition_and_pdf(self):
        recovered=recover_irr_interval_bundle(self.files['execution-evidence.json'])
        self.assertEqual(recovered.run,self.checked);self.assertEqual(recovered.case_raw,self.case)
        self.assertEqual(recovered.report.pdf_bytes,self.files['MiniUW_v1_Resumen.pdf'])
        self.assertEqual(export_irr_interval_bundle(self.case,self.checked,recovered.report),self.files['execution-evidence.json'])

    def test_bundle_version_rehashed_state_manifest_and_pdf_forgeries_are_rejected(self):
        original=self.files['execution-evidence.json']
        for key in versions():
            p=json.loads(original);p[key]='0'*64
            with self.assertRaises(ValidationError):recover_irr_interval_bundle(raw(p))
        for key,value in (('pdf_sha256','0'*64),('report_manifest_utf8','{}')):
            p=json.loads(original);p[key]=value
            with self.assertRaises(ValidationError):recover_irr_interval_bundle(raw(p))
        p=json.loads(original);result=json.loads(p['result']['payload_json']);result['IRR_interval_comparison']['row_state']='PASS_CONDITION'
        text=canonical(result);p['result']=dict(payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):recover_irr_interval_bundle(raw(p))

    def test_local_write_retry_audit_and_different_output_preserve_existing_folder(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'out';write_irr_interval_artifacts(self.case,target)
            before={p.name:p.read_bytes()for p in target.iterdir()}
            self.assertEqual(audit_irr_interval_directory(target)['files_verified'],8)
            self.assertEqual(write_irr_interval_artifacts(self.case,target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_irr_interval_artifacts(self.case+b'\n',target)
            self.assertEqual(before,{p.name:p.read_bytes()for p in target.iterdir()})

    def test_rehashed_unsafe_extra_and_symlink_inventory_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for name,value in self.files.items():(root/name).write_bytes(value)
            restore();(root/'results.json').write_bytes(b'{}');p=json.loads(self.files['package.json'])
            row=next(r for r in p['files']if r['path']=='results.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_irr_interval_directory(root)
            restore();p=json.loads(self.files['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_irr_interval_directory(root)
            restore();(root/'extra.txt').write_bytes(b'extra')
            with self.assertRaises(ValidationError):audit_irr_interval_directory(root)
            (root/'extra.txt').unlink();(root/'audit.json').unlink();(root/'audit.json').symlink_to(root/'results.json')
            with self.assertRaises(ValidationError):audit_irr_interval_directory(root)

    def test_failed_rename_removes_only_its_owned_temporary_directory(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);marker=root/'keep.txt';marker.write_bytes(b'keep')
            with patch('miniuw_foundation.irr_interval_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_irr_interval_artifacts(self.case,root/'out')
            self.assertEqual(list(root.iterdir()),[marker]);self.assertEqual(marker.read_bytes(),b'keep')

    def test_missing_numerical_data_remains_pending_after_portable_recovery_with_complete_criterion(self):
        for label,blocker in (('budget','complete_periodic_root_inventory_required'),('frequency','compatible_current_annual_root_required')):
            files,run=build_irr_interval_artifacts(source(label));recovered=recover_irr_interval_bundle(files['execution-evidence.json'])
            self.assertEqual(recovered.run,run);check=run.payload['IRR_interval_comparison']
            self.assertIsNotNone(check['criterion']['source_ref']);self.assertIsNone(check['enclosure'])
            self.assertEqual(check['row_state'],'PENDING');self.assertIn(blocker,check['blockers'])
            self.assertEqual(run.payload['current_project_return_story']['gross_distributions'],dict(numerator='778',denominator='1'))


if __name__=='__main__':unittest.main()
