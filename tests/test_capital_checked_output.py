from dataclasses import replace
from fractions import Fraction
from io import BytesIO
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.capital_checked_output import (
    assemble_capital_checked_output,render_capital_checked_output,build_capital_checked_artifacts,
    export_capital_checked_bundle,recover_capital_checked_bundle,
    write_capital_checked_artifacts,audit_capital_checked_directory)
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.investor_onepage import render_investor_onepage
from miniuw_foundation.synthetic_onepager import PreviewLayoutError

ROOT=Path(__file__).resolve().parents[1]
source=lambda label:(ROOT/('templates/miniuw-v1-capital-'+label+'-case.json')).read_bytes()
raw=lambda value:(canonical(value)+'\n').encode()
q=lambda value:rational(Fraction(value))


class CapitalCheckedOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pending=source('pending-basis')
        cls.contents,cls.checked_run=build_capital_checked_artifacts(cls.pending)

    def test_pending_latest_cut_masks_paired_values_and_keeps_claims_no_fallback(self):
        p=self.checked_run.payload;s=p['current_project_return_story'];rows=s['capital_snapshots']
        self.assertEqual(p['latest_capital_snapshot_index'],1);self.assertEqual(p['latest_capital_state'],'PENDING')
        self.assertEqual(rows[0]['capital_still_invested'],q(1300))
        for key in ('capital_still_invested','retained_equity_value','normalized_capital_still_invested','normalized_retained_equity_value'):
            self.assertIsNone(rows[1][key])
        self.assertEqual(p['capital_source_claims'][1]['capital_still_invested'],q(1000))
        self.assertEqual(p['capital_source_claims'][1]['retained_equity_value'],q(900))
        self.assertIsNone(p['capital_source_claims'][1]['basis_ref'])
        self.assertFalse(p['older_valid_snapshot_substituted']);self.assertFalse(p['capital_values_derived'])

    def test_declared_and_explicit_zero_stocks_remain_separate_from_cash(self):
        for label,capital,equity in [('declared',1000,900),('zero',0,0)]:
            checked=assemble_capital_checked_output(source(label));p=checked.payload;s=p['current_project_return_story']
            self.assertEqual(s['capital_snapshots'][0]['capital_still_invested'],q(capital))
            self.assertEqual(s['capital_snapshots'][0]['retained_equity_value'],q(equity))
            self.assertEqual(p['latest_capital_state'],'declared_synthetic_not_derived')
            for key in ('gross_contributions','gross_distributions','net_cash_profit','equity_multiple','cash_by_category','annual_irr_roots','annual_cash_receipts'):
                self.assertEqual(s[key],checked.parent_run.payload['current_project_return_story'][key])
            self.assertEqual(s['gross_distributions'],q(778));self.assertEqual(s['net_cash_profit'],q(-622))
            self.assertIsNone(s['personal_investor_return']);self.assertIsNone(s['selected_IRR'])
            self.assertTrue(all(row['conditional_coc']is None for row in s['annual_cash_receipts']))
            self.assertFalse(p['retained_equity_counted_as_cash']);self.assertEqual(p['decision'],'PENDING')

    def test_missing_capital_does_not_publish_its_paired_retained_equity(self):
        p=assemble_capital_checked_output(source('missing-value')).payload
        row=p['current_project_return_story']['capital_snapshots'][0]
        self.assertIsNone(row['capital_still_invested']);self.assertIsNone(row['retained_equity_value'])
        self.assertEqual(p['capital_source_claims'][0]['retained_equity_value'],q(900))
        self.assertTrue(any('capital_still_invested_missing' in b for b in p['blockers']['capital']))

    def test_large_unresolved_claim_does_not_enter_current_page_layout(self):
        case=source('large-pending');checked=assemble_capital_checked_output(case)
        self.assertEqual(checked.payload['latest_capital_state'],'PENDING')
        with self.assertRaises(PreviewLayoutError):render_investor_onepage(case,checked.parent_run)
        report=render_capital_checked_output(case,checked)
        reader=PdfReader(BytesIO(report.pdf_bytes));self.assertEqual(len(reader.pages),1)
        text=reader.pages[0].extract_text()
        self.assertIn('capital Pendiente',text);self.assertIn('778.0000',text)
        self.assertNotIn(str(10**80),text)

    def test_one_page_pending_declared_and_zero_with_exact_current_result_link(self):
        text=PdfReader(BytesIO(self.contents['MiniUW_v1_Resumen.pdf'])).pages[0].extract_text()
        self.assertIn('Corte 2027-06-01: capital Pendiente',text)
        self.assertIn('Equity retenido (no caja): Pendiente',text)
        for wrong in ('capital 1000.0000','capital 1300.0000','Equity retenido (no caja): 900.0000'):
            self.assertNotIn(wrong,text)
        for value in ('1400.0000','778.0000','-622.0000',self.checked_run.sha256):self.assertIn(value,text)
        manifest=json.loads(self.contents['report-manifest.json'])
        self.assertEqual(manifest['result_sha256'],self.checked_run.sha256)
        self.assertEqual(manifest['parent_financial_run_sha256'],self.checked_run.parent_run.sha256)
        for label,value in [('declared','1000.0000'),('zero','0.0000')]:
            case=source(label);checked=assemble_capital_checked_output(case);report=render_capital_checked_output(case,checked)
            reader=PdfReader(BytesIO(report.pdf_bytes));self.assertEqual(len(reader.pages),1)
            extracted=reader.pages[0].extract_text();self.assertIn('capital declarado '+value,extracted)
            self.assertTrue(all(row['text']in extracted for row in report.manifest['display_spans']))

    def test_parent_expiry_withholds_all_current_values_and_recovers_blocked(self):
        p=json.loads(self.pending);registry=json.loads(p['registry_utf8'])
        registry['evidence'][-1]['valid_until']=p['as_of_UTC'];p['registry_utf8']=canonical(registry)
        case=raw(p);contents,checked=build_capital_checked_artifacts(case)
        recovered=recover_capital_checked_bundle(contents['execution-evidence.json'])
        self.assertEqual(recovered.run,checked);self.assertEqual(recovered.case_raw,case)
        self.assertIsNone(checked.payload['current_project_return_story']);self.assertEqual(checked.payload['capital_visibility'],[])
        text=PdfReader(BytesIO(recovered.report.pdf_bytes)).pages[0].extract_text()
        for value in ('1400.0000','778.0000','-622.0000','capital 1000.0000'):self.assertNotIn(value,text)

    def test_rehashed_current_view_older_cut_and_report_forgeries_rejected(self):
        for mutate in (lambda p:p['current_project_return_story']['capital_snapshots'][1].update(capital_still_invested=q(1000)),
                       lambda p:p.update(latest_capital_snapshot_index=0)):
            p=self.checked_run.payload;mutate(p);text=canonical(p)
            fake=replace(self.checked_run,payload_json=text,sha256=digest(text))
            with self.assertRaises(ValidationError):render_capital_checked_output(self.pending,fake)
            with self.assertRaises(ValidationError):export_capital_checked_bundle(self.pending,fake)
        with self.assertRaises(ValidationError):render_capital_checked_output(self.pending+b'\n',self.checked_run)

    def test_portable_replay_versions_and_rehashed_result_proof_forgeries(self):
        original=self.contents['execution-evidence.json'];recovered=recover_capital_checked_bundle(original)
        self.assertEqual(recovered.run,self.checked_run);self.assertEqual(recovered.report.pdf_bytes,self.contents['MiniUW_v1_Resumen.pdf'])
        self.assertEqual(recovered.run.payload['latest_capital_state'],'PENDING')
        for key in ('engine_sha256','composition_engine_sha256','base_view_engine_sha256','parent_bundle_engine_sha256','definition_sha256','composition_definition_sha256','inventory_engine_sha256'):
            p=json.loads(original);p[key]='0'*64
            with self.assertRaises(ValidationError):recover_capital_checked_bundle(raw(p))
        p=json.loads(original);result=json.loads(p['result']['payload_json'])
        result['current_project_return_story']['capital_snapshots'][1]['capital_still_invested']=q(1000)
        text=canonical(result);p['result']=dict(payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):recover_capital_checked_bundle(raw(p))
        p=json.loads(original);p['pdf_sha256']='0'*64
        with self.assertRaises(ValidationError):recover_capital_checked_bundle(raw(p))

    def test_local_write_retry_audit_and_different_input_preserve_existing(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'out';write_capital_checked_artifacts(self.pending,target)
            before={p.name:p.read_bytes()for p in target.iterdir()}
            self.assertEqual(write_capital_checked_artifacts(self.pending,target)['status'],'identical_existing_verified')
            self.assertEqual(audit_capital_checked_directory(target)['files_verified'],8)
            with self.assertRaises(ValidationError):write_capital_checked_artifacts(self.pending+b'\n',target)
            self.assertEqual(before,{p.name:p.read_bytes()for p in target.iterdir()})

    def test_rehashed_artifact_unsafe_inventory_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for key,value in self.contents.items():(root/key).write_bytes(value)
            restore();(root/'results.json').write_bytes(b'{}');package=json.loads(self.contents['package.json'])
            row=next(r for r in package['files']if r['path']=='results.json');row.update(bytes=2,sha256=sha(b'{}'))
            (root/'package.json').write_bytes(raw(package))
            with self.assertRaises(ValidationError):audit_capital_checked_directory(root)
            restore();package=json.loads(self.contents['package.json']);package['files'][0]['path']='../outside'
            (root/'package.json').write_bytes(raw(package))
            with self.assertRaises(ValidationError):audit_capital_checked_directory(root)
            restore();(root/'extra.txt').write_bytes(b'extra')
            with self.assertRaises(ValidationError):audit_capital_checked_directory(root)
            (root/'extra.txt').unlink();(root/'audit.json').unlink();(root/'audit.json').symlink_to(root/'results.json')
            with self.assertRaises(ValidationError):audit_capital_checked_directory(root)

    def test_failed_rename_cleans_only_own_temporary_files(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);marker=root/'keep.txt';marker.write_bytes(b'preserve')
            with patch('miniuw_foundation.capital_checked_output.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_capital_checked_artifacts(self.pending,root/'out')
            self.assertEqual(list(root.iterdir()),[marker]);self.assertEqual(marker.read_bytes(),b'preserve')


if __name__=='__main__':unittest.main()
