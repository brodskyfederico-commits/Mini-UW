from dataclasses import replace
from fractions import Fraction
from io import BytesIO
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader

from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.capital_checked_output import assemble_capital_checked_output,render_capital_checked_output
from miniuw_foundation.long_horizon_report import render_long_horizon_report,_render_verified,_groups
from miniuw_foundation.long_horizon_artifacts import (build_long_horizon_artifacts,export_long_horizon_bundle,
    recover_long_horizon_bundle,write_long_horizon_artifacts,audit_long_horizon_directory,versions)
from miniuw_foundation.synthetic_onepager import PreviewLayoutError
from miniuw_foundation.scheduled_expense_case import sha

ROOT=Path(__file__).resolve().parents[1]
source=lambda label:(ROOT/('templates/miniuw-v1-'+label+'-case.json')).read_bytes()
raw=lambda p:(canonical(p)+'\n').encode()
q=lambda v:rational(Fraction(v))


class LongHorizonOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=source('long-window');cls.files,cls.checked=build_long_horizon_artifacts(cls.case)
        cls.manifest=json.loads(cls.files['report-manifest.json'])
        cls.text=PdfReader(BytesIO(cls.files['MiniUW_v1_Resumen.pdf'])).pages[0].extract_text()

    def test_six_years_and_all_sixteen_events_including_zeros_are_accounted_for(self):
        m=self.manifest;groups=m['event_groups']
        self.assertEqual(m['annual_years'],list(range(2022,2028)))
        indices=[i for g in groups for i in g['event_indices']]
        self.assertEqual(sorted(indices),list(range(16)));self.assertEqual(len(indices),len(set(indices)))
        self.assertEqual(m['event_count'],16);self.assertEqual(len(groups),7)
        extra=next(g for g in groups if g['category']=='additional_capital')
        self.assertEqual(extra['event_count'],12);self.assertEqual(extra['zero_event_count'],11)
        self.assertEqual(extra['amount'],q(400));self.assertEqual(extra['first_date'],'2023-01-01')
        self.assertEqual(extra['last_date'],'2027-07-01')
        absent=next(g for g in groups if g['category']=='net_refinance_distribution')
        self.assertEqual(absent['amount'],q(0));self.assertEqual(absent['event_count'],0);self.assertIsNone(absent['first_date'])

    def test_annual_cashless_years_and_explicit_initial_contribution_timing_remain_visible(self):
        years=self.checked.payload['current_project_return_story']['annual_cash_receipts']
        self.assertEqual([r['calendar_cash_receipt_year']for r in years],list(range(2022,2028)))
        for y in (2023,2024,2025):
            row=next(r for r in years if r['calendar_cash_receipt_year']==y)
            self.assertEqual(row['gross_contributions'],q(0));self.assertEqual(row['gross_distributions'],q(0))
            self.assertIn(str(y)+' A 0 C 0 N 0',self.text)
        self.assertIn('2022 A 1000 C 0 N -1000',self.text)
        self.assertIn('2026 A 400 C 0 N -400',self.text)
        self.assertIn('2027 A 0 C 778 N 778',self.text)
        self.assertIn('2022-03-01 a 2022-03-01 | n=1',self.text)
        self.assertTrue(all(r['conditional_coc']is None for r in years))

    def test_many_events_and_long_window_render_without_legacy_limits_or_financial_changes(self):
        for label in ('many-events','long-window','years-only'):
            case=source(label);run=assemble_capital_checked_output(case)
            with self.assertRaises(PreviewLayoutError):render_capital_checked_output(case,run)
            report=render_long_horizon_report(case,run)
            self.assertEqual(len(PdfReader(BytesIO(report.pdf_bytes)).pages),1)
            self.assertEqual(report.manifest['result_sha256'],run.sha256)
            self.assertEqual(run.payload['current_project_return_story']['gross_contributions'],q(1400))
            self.assertEqual(run.payload['current_project_return_story']['gross_distributions'],q(778))
            self.assertFalse(report.manifest['underlying_financial_result_changed'])
        baseline=assemble_capital_checked_output(source('capital-pending-basis'))
        self.assertNotEqual(self.checked.payload['current_project_return_story']['annual_irr_roots'],baseline.payload['current_project_return_story']['annual_irr_roots'])

    def test_all_spans_fit_one_page_and_columns_do_not_overlap(self):
        reader=PdfReader(BytesIO(self.files['MiniUW_v1_Resumen.pdf']))
        self.assertEqual(len(reader.pages),1);self.assertEqual(tuple(float(v)for v in reader.pages[0].mediabox),(0,0,792,612))
        for row in self.manifest['display_spans']:
            self.assertIn(row['text'],self.text)
            self.assertLessEqual(len(row['text'])*row['font_size']*.6,row['width'])
            self.assertLessEqual(row['x']+row['width'],768)
        body=[r for r in self.manifest['display_spans']if 125<r['y']<445]
        for i,a in enumerate(body):
            for b in body[i+1:]:
                horizontal=a['x']<b['x']+b['width']and b['x']<a['x']+a['width']
                vertical=a['y']<b['y']+b['font_size']and b['y']<a['y']+a['font_size']
                self.assertFalse(horizontal and vertical,(a['text'],b['text']))

    def test_capital_pending_and_explicit_zero_protections_survive_new_presentation(self):
        self.assertIn('Capital declarado: Pendiente',self.text);self.assertIn('Valor retenido (no caja): Pendiente',self.text)
        self.assertNotIn('Capital declarado: 1000',self.text);self.assertNotIn('Valor retenido (no caja): 900',self.text)
        case=source('capital-zero');run=assemble_capital_checked_output(case);report=render_long_horizon_report(case,run)
        text=PdfReader(BytesIO(report.pdf_bytes)).pages[0].extract_text()
        self.assertIn('Capital declarado: 0',text);self.assertIn('Valor retenido (no caja): 0',text)
        self.assertIsNone(run.payload['current_project_return_story']['personal_investor_return'])

    def test_pending_source_withdraws_current_groups_annual_rows_and_money_after_recovery(self):
        p=json.loads(self.case);reg=json.loads(p['registry_utf8']);reg['evidence'][-1]['valid_until']=p['as_of_UTC'];p['registry_utf8']=canonical(reg)
        files,run=build_long_horizon_artifacts(raw(p));recovered=recover_long_horizon_bundle(files['execution-evidence.json'])
        self.assertEqual(recovered.run,run);self.assertIsNone(run.payload['current_project_return_story'])
        m=recovered.report.manifest;self.assertEqual(m['event_groups'],[]);self.assertEqual(m['annual_years'],[])
        text=PdfReader(BytesIO(recovered.report.pdf_bytes)).pages[0].extract_text()
        self.assertNotIn('2022 A 1000',text);self.assertNotIn('Cobro venta: 578',text)
        self.assertEqual(m['decision'],'PENDING')

    def test_rehashed_run_or_report_does_not_replace_exact_source_replay(self):
        p=self.checked.payload;p['current_project_return_story']['dated_events'][0]['amount']=q(1)
        value=canonical(p);fake=replace(self.checked,payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):render_long_horizon_report(self.case,fake)
        with self.assertRaises(ValidationError):export_long_horizon_bundle(self.case,fake)
        with self.assertRaises(ValidationError):render_long_horizon_report(self.case+b'\n',self.checked)
        real=render_long_horizon_report(self.case,self.checked)
        bad=replace(real,pdf_bytes=b'not the reproduced page')
        with self.assertRaises(ValidationError):export_long_horizon_bundle(self.case,self.checked,bad)

    def test_presentation_bounds_reject_excess_years_events_and_inconsistent_group_totals(self):
        # Unit probes of private layout limits; fabricated payloads are not source-accepted runs.
        p=self.checked.payload;s=p['current_project_return_story']
        rows=[]
        for y in range(2022,2034):
            row=dict(s['annual_cash_receipts'][1],calendar_cash_receipt_year=y);rows.append(row)
        s['annual_cash_receipts']=rows
        value=canonical(p);probe=replace(self.checked,payload_json=value,sha256=digest(value))
        report=_render_verified(probe)
        self.assertEqual(report.manifest['annual_years'],list(range(2022,2034)))
        self.assertEqual(len(PdfReader(BytesIO(report.pdf_bytes)).pages),1)
        p=self.checked.payload;s=p['current_project_return_story'];s['annual_cash_receipts']*=3
        value=canonical(p);fake=replace(self.checked,payload_json=value,sha256=digest(value))
        with self.assertRaises(PreviewLayoutError):_render_verified(fake)
        s=self.checked.payload['current_project_return_story'];s['dated_events']*=17
        with self.assertRaises(PreviewLayoutError):_groups(s)
        s=self.checked.payload['current_project_return_story'];s['cash_by_category']['initial_capital']=q(1)
        with self.assertRaises(ValidationError):_groups(s)

    def test_source_first_bundle_roundtrip_and_rehashed_group_or_pdf_forgeries(self):
        bundle=self.files['execution-evidence.json'];recovered=recover_long_horizon_bundle(bundle)
        self.assertEqual(recovered.run,self.checked);self.assertEqual(recovered.case_raw,self.case)
        self.assertEqual(recovered.report.pdf_bytes,self.files['MiniUW_v1_Resumen.pdf'])
        exported=export_long_horizon_bundle(self.case,self.checked,recovered.report);self.assertEqual(exported,bundle)
        for mutate in (lambda p:p.update(pdf_sha256='0'*64),lambda p:p.update(render_engine_sha256='0'*64),
                       lambda p:p.update(report_manifest_utf8=canonical(dict(json.loads(p['report_manifest_utf8']),event_groups=[])))):
            p=json.loads(bundle);mutate(p)
            with self.assertRaises(ValidationError):recover_long_horizon_bundle(raw(p))
        self.assertGreaterEqual(len(versions()),7)

    def test_local_package_retry_audit_and_no_different_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'out';write_long_horizon_artifacts(self.case,target)
            before={p.name:p.read_bytes()for p in target.iterdir()}
            self.assertEqual(audit_long_horizon_directory(target)['files_verified'],8)
            self.assertEqual(write_long_horizon_artifacts(self.case,target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_long_horizon_artifacts(self.case+b'\n',target)
            self.assertEqual(before,{p.name:p.read_bytes()for p in target.iterdir()})

    def test_rehashed_inventory_extra_file_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for name,value in self.files.items():(root/name).write_bytes(value)
            restore();(root/'report-manifest.json').write_bytes(b'{}');package=json.loads(self.files['package.json'])
            row=next(r for r in package['files']if r['path']=='report-manifest.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(raw(package))
            with self.assertRaises(ValidationError):audit_long_horizon_directory(root)
            restore();(root/'extra.txt').write_bytes(b'extra')
            with self.assertRaises(ValidationError):audit_long_horizon_directory(root)
            (root/'extra.txt').unlink();(root/'audit.json').unlink();(root/'audit.json').symlink_to(root/'results.json')
            with self.assertRaises(ValidationError):audit_long_horizon_directory(root)

    def test_failed_rename_cleans_only_own_temporary_directory(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep.txt';keep.write_bytes(b'keep')
            with patch('miniuw_foundation.long_horizon_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_long_horizon_artifacts(self.case,root/'out')
            self.assertEqual(list(root.iterdir()),[keep])


if __name__=='__main__':unittest.main()
