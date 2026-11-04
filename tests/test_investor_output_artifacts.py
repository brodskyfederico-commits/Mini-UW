from dataclasses import replace
from io import BytesIO
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.investor_output_artifacts import (
    build_investor_output_artifacts, export_investor_output_bundle, recover_investor_output_bundle,
    write_investor_output_artifacts, audit_investor_output_directory,
)
from miniuw_foundation.scheduled_expense_case import sha

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT/'templates/miniuw-v1-policy-renewal-case.json').read_bytes()
encoded = lambda value:(canonical(value)+'\n').encode()


class InvestorOutputArtifactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contents,cls.case_run = build_investor_output_artifacts(BASE)

    def copy_package(self,directory):
        for name,value in self.contents.items():
            (directory/name).write_bytes(value)

    def test_eight_artifacts_one_page_unchanged_result_and_portable_recovery(self):
        self.assertEqual(set(self.contents),{'case.json','results.json','execution-evidence.json','MiniUW_v1_Resumen.pdf',
            'report-manifest.json','audit.json','schedule-review.txt','package.json'})
        self.assertEqual(self.contents['results.json'],(ROOT/'docs/review/miniuw-v1-investor-output-example/results.json').read_bytes())
        self.assertEqual(self.contents['MiniUW_v1_Resumen.pdf'],(ROOT/'docs/review/miniuw-v1-investor-output-example/MiniUW_v1_Resumen.pdf').read_bytes())
        reader = PdfReader(BytesIO(self.contents['MiniUW_v1_Resumen.pdf']))
        self.assertEqual(len(reader.pages),1)
        self.assertIn('2027 A0.0000 C778.0000 N778.0000 O200.0000 CoC:Pendiente',reader.pages[0].extract_text())
        recovered = recover_investor_output_bundle(self.contents['execution-evidence.json'])
        self.assertEqual(recovered.case_raw,BASE); self.assertEqual(recovered.run,self.case_run)
        self.assertEqual(recovered.report.pdf_bytes,self.contents['MiniUW_v1_Resumen.pdf'])
        self.assertEqual(recovered.report.manifest_json+'\n',self.contents['report-manifest.json'].decode())
        self.assertFalse(json.loads(self.contents['audit.json'])['new_financial_calculations'])

    def test_blocked_source_recovers_without_restoring_current_money(self):
        p = json.loads(BASE); registry = json.loads(p['registry_utf8'])
        registry['evidence'][-1]['valid_until'] = p['as_of_UTC']; p['registry_utf8'] = canonical(registry)
        source = encoded(p); contents,case_run = build_investor_output_artifacts(source)
        recovered = recover_investor_output_bundle(contents['execution-evidence.json'])
        self.assertEqual(recovered.case_raw,source); self.assertEqual(recovered.run,case_run)
        self.assertIsNone(recovered.run.payload['current_project_return_story'])
        text = PdfReader(BytesIO(recovered.report.pdf_bytes)).pages[0].extract_text()
        for token in ('1400.0000','778.0000','-622.0000','578.0000','Moneda USD'):
            self.assertNotIn(token,text)
        self.assertIn('CIFRAS ACTUALES RETIRADAS',contents['schedule-review.txt'].decode())
        self.assertEqual(case_run.payload['decision'],'PENDING')

    def test_version_schema_source_manifest_and_pdf_forgeries_are_rejected(self):
        original = json.loads(self.contents['execution-evidence.json'])
        for key in ('engine_sha256','renderer_engine_sha256','parent_bundle_engine_sha256','inventory_engine_sha256','definition_sha256','renderer_definition_sha256'):
            p = json.loads(self.contents['execution-evidence.json']); p[key] = '0'*64
            with self.assertRaises(ValidationError):recover_investor_output_bundle(encoded(p))
        with self.assertRaises(ValidationError):recover_investor_output_bundle(original['parent_bundle_utf8'].encode())
        p = json.loads(self.contents['execution-evidence.json']); parent = json.loads(p['parent_bundle_utf8'])
        result = json.loads(parent['result']['payload_json']); result['current_project_return_story']['gross_distributions'] = {'numerator':'999','denominator':'1'}
        text = canonical(result); parent['result'] = dict(payload_json=text,sha256=digest(text)); p['parent_bundle_utf8'] = canonical(parent)
        with self.assertRaises(ValidationError):recover_investor_output_bundle(encoded(p))
        p = json.loads(self.contents['execution-evidence.json']); manifest = json.loads(p['report_manifest_utf8'])
        manifest['display_spans'][0]['text'] = 'SYNTHETIC-forged-title'; p['report_manifest_utf8'] = canonical(manifest)
        with self.assertRaises(ValidationError):recover_investor_output_bundle(encoded(p))
        p = json.loads(self.contents['execution-evidence.json']); p['pdf_sha256'] = '0'*64
        with self.assertRaises(ValidationError):recover_investor_output_bundle(encoded(p))

    def test_local_write_retry_audit_and_different_revision_preserve_output(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)/'output'
            self.assertEqual(write_investor_output_artifacts(BASE,target)['status'],'synthetic_investor_output_written')
            before = {p.name:p.read_bytes() for p in target.iterdir()}
            self.assertEqual(write_investor_output_artifacts(BASE,target)['status'],'identical_existing_verified')
            self.assertEqual(audit_investor_output_directory(target)['files_verified'],8)
            with self.assertRaises(ValidationError):write_investor_output_artifacts(BASE+b'\n',target)
            self.assertEqual(before,{p.name:p.read_bytes() for p in target.iterdir()})

    def test_rehashed_file_path_extra_missing_and_symlink_inventory_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.copy_package(root)
            (root/'results.json').write_bytes(b'{}')
            package = json.loads(self.contents['package.json'])
            row = next(row for row in package['files'] if row['path']=='results.json')
            row.update(bytes=2,sha256=sha(b'{}')); (root/'package.json').write_bytes(encoded(package))
            with self.assertRaises(ValidationError):audit_investor_output_directory(root)
            self.copy_package(root); package = json.loads(self.contents['package.json']); package['files'][0]['path']='../outside'
            (root/'package.json').write_bytes(encoded(package))
            with self.assertRaises(ValidationError):audit_investor_output_directory(root)
            self.copy_package(root); (root/'extra.txt').write_bytes(b'not an artifact')
            with self.assertRaises(ValidationError):audit_investor_output_directory(root)
            (root/'extra.txt').unlink(); (root/'audit.json').unlink()
            with self.assertRaises(ValidationError):audit_investor_output_directory(root)
            (root/'audit.json').symlink_to(root/'results.json')
            with self.assertRaises(ValidationError):audit_investor_output_directory(root)

    def test_failed_rename_cleans_own_temporary_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); marker = root/'keep.txt'; marker.write_bytes(b'preserve')
            with patch('miniuw_foundation.investor_output_artifacts.os.rename',side_effect=OSError('injected rename failure')):
                with self.assertRaises(OSError):write_investor_output_artifacts(BASE,root/'output')
            self.assertEqual(list(root.iterdir()),[marker]); self.assertEqual(marker.read_bytes(),b'preserve')

    def test_public_export_rejects_rehashed_report_different_bytes_and_budget(self):
        recovered = recover_investor_output_bundle(self.contents['execution-evidence.json'])
        manifest = recovered.report.manifest; manifest['pdf_sha256'] = sha(recovered.report.pdf_bytes+b'\n')
        text = canonical(manifest)
        fake = replace(recovered.report,pdf_bytes=recovered.report.pdf_bytes+b'\n',manifest_json=text,manifest_sha256=digest(text))
        with self.assertRaises(ValidationError):export_investor_output_bundle(BASE,self.case_run,fake)
        with self.assertRaises(ValidationError):export_investor_output_bundle(BASE+b'\n',self.case_run)
        with patch('miniuw_foundation.investor_output_artifacts.MAX_BUNDLE_BYTES',8):
            with self.assertRaises(ValidationError):recover_investor_output_bundle(self.contents['execution-evidence.json'])
            with self.assertRaises(ValidationError):export_investor_output_bundle(BASE,self.case_run)

    def test_cli_invalid_input_reports_pending_without_creating_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root/'bad.json'; source.write_bytes(b'{"schema":1,"schema":2}')
            target = root/'output'
            process = subprocess.run([sys.executable,str(ROOT/'tools/investor_miniuw_v1.py'),'run',str(source),'--output',str(target)],
                text=True,capture_output=True,env=os.environ.copy(),timeout=30)
            self.assertEqual(process.returncode,2); self.assertFalse(target.exists())
            self.assertEqual(json.loads(process.stderr)['decision'],'PENDING')
            self.assertEqual(json.loads(process.stderr)['status'],'blocked')


if __name__=='__main__':
    unittest.main()
