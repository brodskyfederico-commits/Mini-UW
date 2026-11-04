from dataclasses import replace
from io import BytesIO
from pathlib import Path
import json
import unittest

from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.investor_onepage import render_investor_onepage, _compose_verified
from miniuw_foundation.policy_renewal_case import assemble_policy_renewal_case
from miniuw_foundation.policy_renewal_artifacts import render_policy_renewal_report
from miniuw_foundation.synthetic_onepager import PreviewLayoutError

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT/'templates/miniuw-v1-policy-renewal-case.json').read_bytes()


class InvestorOnePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_run = assemble_policy_renewal_case(BASE)
        cls.parent = render_policy_renewal_report(BASE,cls.case_run)
        cls.report = render_investor_onepage(BASE,cls.case_run)

    def test_exact_annual_cash_context_and_one_page_without_financial_changes(self):
        for source,run,report,receipts in [(BASE,self.case_run,self.report,'778.0000'),
                ((ROOT/'templates/miniuw-v1-policy-renewal-twelve-case.json').read_bytes(),None,None,'776.0000')]:
            run = run or assemble_policy_renewal_case(source)
            report = report or render_investor_onepage(source,run)
            reader = PdfReader(BytesIO(report.pdf_bytes)); self.assertEqual(len(reader.pages),1)
            text = reader.pages[0].extract_text()
            self.assertIn('2026 A1400.0000 C0.0000 N-1400.0000 O0.0000 CoC:Pendiente',text)
            self.assertIn('2027 A0.0000 C'+receipts+' N'+receipts+' O200.0000 CoC:Pendiente',text)
            self.assertIn('Moneda USD | Ventana 2026-10-01 a 2027-07-01',text)
            refs = {ref for span in report.manifest['display_spans'] for ref in span['result_pointers']}
            for path in ('/currency','/equity_level','/cash_horizon','/annual_cash_receipts/0/net_equity_cash','/annual_cash_receipts/1/gross_contributions'):
                self.assertIn('/current_project_return_story'+path,refs)
            self.assertTrue(all(span['text'] in text for span in report.manifest['display_spans']))
            self.assertFalse(report.manifest['new_financial_calculations'])
            self.assertEqual(run,assemble_policy_renewal_case(source))
        self.assertEqual(self.parent,render_policy_renewal_report(BASE,self.case_run))
        self.assertEqual(BASE,(ROOT/'templates/miniuw-v1-policy-renewal-case.json').read_bytes())

    def test_expiry_withdraws_context_money_and_annual_values(self):
        p = json.loads(BASE); registry = json.loads(p['registry_utf8'])
        registry['evidence'][-1]['valid_until'] = p['as_of_UTC']
        p['registry_utf8'] = canonical(registry); source = canonical(p).encode()
        run = assemble_policy_renewal_case(source); report = render_investor_onepage(source,run)
        reader = PdfReader(BytesIO(report.pdf_bytes)); self.assertEqual(len(reader.pages),1)
        text = reader.pages[0].extract_text()
        self.assertIn('Moneda/ventana actuales: pendientes',text)
        for token in ('1400.0000','778.0000','-622.0000','578.0000','A0.0000','Moneda USD','Ventana 2026-10-01'):
            self.assertNotIn(token,text)
        self.assertIsNone(run.payload['current_project_return_story'])
        self.assertFalse(report.manifest['financial_publication_authorized'])

    def test_rehashed_forged_results_and_different_input_are_rejected(self):
        for path,value in [('currency','EUR'),('cash_horizon',{'start':'2026-01-01','end':'2028-01-01'}),('gross_distributions',{'numerator':'999','denominator':'1'})]:
            p = self.case_run.payload; p['current_project_return_story'][path] = value
            text = canonical(p); fake = replace(self.case_run,payload_json=text,sha256=digest(text))
            with self.assertRaises(ValidationError):render_investor_onepage(BASE,fake)
        with self.assertRaises(ValidationError):render_investor_onepage(BASE+b'\n',self.case_run)

    def test_recomposition_rejects_overflow_instead_of_clipping(self):
        manifest = self.parent.manifest
        manifest['display_spans'][0]['text'] = 'SYNTHETIC-'+'X'*500
        text = canonical(manifest)
        altered = replace(self.parent,manifest_json=text,manifest_sha256=digest(text))
        with self.assertRaises(PreviewLayoutError):_compose_verified(self.case_run,altered)


if __name__ == '__main__':
    unittest.main()
