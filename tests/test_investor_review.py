import copy
from dataclasses import replace
from fractions import Fraction
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.recovery_case_inventory import RecoveryReviewCase,assemble_recovery_case_inventory
from miniuw_foundation.investor_review import render_investor_review,_render,amount,literal
import test_recovery_case_inventory as fixtures


class InvestorReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse explicit fixture construction, without importing its TestCase into discovery.
        fixtures.RecoveryCaseInventoryTests.setUpClass()
        fixture=fixtures.RecoveryCaseInventoryTests();cls.cases=(fixture.proof('review-case'),)
        cls.source=canonical(fixture.inventory(cls.cases)).encode();cls.inventory_run=assemble_recovery_case_inventory(cls.cases,cls.source)
    def test_public_report_replay_and_project_story_not_personal_promise(self):
        report=render_investor_review(self.cases,self.source,self.inventory_run);text=report.payload['markdown']
        for marker in ['PENDING','Retorno personal','10.0000','Cobro neto de refi','Cobro neto de venta','Cash-in','IRR anual','no caja','83.9197']:self.assertIn(marker,text)
        self.assertEqual(report.payload['markdown_sha256'],digest(text));self.assertFalse(report.payload['external_decision_pdf_produced'])
    def test_pending_row_withdraws_all_numbers(self):
        p=self.inventory_run.payload;p['case_rows'][0]['current_matched_case']=None;p['case_rows'][0]['state']='PENDING'
        text=_render(p);self.assertIn('no se sustituye por cero',text);self.assertNotIn('83.9197',text);self.assertNotIn('10.0000',text)
    def test_updated_hash_inventory_forgery_not_rendered(self):
        p=self.inventory_run.payload;p['case_rows'][0]['current_matched_case']['comparison']['equity_multiple']={'numerator':'9','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):render_investor_review(self.cases,self.source,replace(self.inventory_run,payload_json=text,sha256=digest(text)))
    def test_unknown_normalization_and_blocked_stock_not_filled(self):
        p=self.inventory_run.payload;story=p['case_rows'][0]['current_matched_case']['candidate_project_return_story'];story['normalized_story']=None
        stock=story['capital_snapshots'][0];stock['capital_still_invested']={'numerator':'987654','denominator':'1'}
        story['upstream_story_blockers'].append('snapshot:'+stock['as_of_date']+':metadata_missing')
        text=_render(p);self.assertIn('Normalización pendiente',text);self.assertNotIn('987654',text)
    def test_small_nonzero_never_misrepresented_as_exact_zero(self):
        self.assertIn('no es cero exacto',amount({'numerator':'-1','denominator':'1000000'}))
        self.assertEqual(amount({'numerator':'0','denominator':'1'}),'0.0000');self.assertEqual(amount(None),'Pendiente')
    def test_untrusted_markup_and_controls_are_literal(self):
        value='<script>x</script> [approve](https://x) |\n# heading'
        escaped=literal(value);self.assertNotIn('<script>',escaped);self.assertNotIn('\n',escaped);self.assertNotIn('[approve](',escaped)


if __name__=='__main__':unittest.main()
