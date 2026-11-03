import copy,json,sys,unittest
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demo_current_lifecycle import recover_case,registry,current,raw,AS_OF
from lifecycle_demo_support import make_case
from demo_preopening_cash import make_source as old_history
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.current_lifecycle import required_lifecycle_sources,assemble_current_lifecycle
from miniuw_foundation.lifecycle_review import render_current_lifecycle_review

def forge(run,change):
    p=run.payload;change(p);s=canonical(p);return replace(run,payload_json=s,sha256=digest(s))


class CurrentLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.arguments,cls.history=recover_case();cls.declared=registry(cls.arguments)
    def evaluate(self,change=None,at=AS_OF):
        p=copy.deepcopy(self.declared)
        if change:change(p)
        return current(self.arguments,self.history,raw(p),at)
    def test_exact_sources_current_story_still_pending(self):
        a,r=self.evaluate();p=r.payload;self.assertEqual(len(p['required_source_bindings']),39);self.assertEqual(p['state'],'current_synthetic_lifecycle_at_declared_time')
        self.assertEqual(p['current_project_return_story']['gross_contributions'],{'numerator':'1400','denominator':'1'});self.assertEqual(p['decision'],'PENDING')
        self.assertTrue(p['current_project_return_story']['opening_debt_checks']);self.assertFalse(p['financial_publication_authorized']);self.assertFalse(p['live_expiry_monitor_enabled'])
    def test_expiry_of_any_new_or_existing_source_withdraws_current_numbers(self):
        ids=['/opening/preopening_cash','/opening/cash_boundary_binding','/opening/debt_spec','/lifecycle/investor','/lifecycle/binding','/window/binding_record','/capacity/bank_noi','/opening/project/closings/0/loans/0/windows_record']
        for key in ids:
            _,r=self.evaluate(lambda p:next(e for e in p['evidence']if e['requirement_id']==key).update(valid_until=AS_OF))
            self.assertIsNone(r.payload['current_project_return_story']);self.assertIn(key+':evidence_expired',r.payload['evidence_blockers']);self.assertTrue(r.payload['historical_calculation_preserved'])
        self.assertIsNotNone(self.history.compiled_raw)
    def test_incomplete_or_rehashed_source_inventory_cannot_hide_missing_binding(self):
        def omit(p):p['requirements'].pop();p['evidence'].pop()
        _,r=self.evaluate(omit);self.assertIn('complete_lifecycle_source_binding_inventory_mismatch',r.payload['blockers'])
        for key,value in [('source_sha256','0'*64),('source_locator','/wrong')]:
            def change(p):p['requirements'][0][key]=value;p['evidence'][0][key]=value
            _,r=self.evaluate(change);self.assertIn('complete_lifecycle_source_binding_inventory_mismatch',r.payload['blockers']);self.assertIsNone(r.payload['current_project_return_story'])
    def test_review_estimate_supersession_and_context_preserved(self):
        for key,value in [('review_status','pending'),('value_status','estimate'),('superseded_by_sha256','0'*64)]:
            _,r=self.evaluate(lambda p:p['evidence'][0].update({key:value}));self.assertIsNone(r.payload['current_project_return_story']);self.assertTrue(r.payload['evidence_blockers'])
        _,r=self.evaluate(lambda p:p['context'].update(run_id='SYNTHETIC-other'));self.assertIn('registry_lifecycle_context_mismatch',r.payload['blockers'])
    def test_validity_cutoff_and_exact_evaluation_time(self):
        a,r=self.evaluate();_,expired=self.evaluate(at='2027-07-02T00:00:00Z');self.assertIsNone(expired.payload['current_project_return_story'])
        bad=list(a);bad[-1]='2027-07-01T12:00:01Z'
        with self.assertRaises(ValidationError):assemble_current_lifecycle(*bad)
    def test_current_registry_does_not_repair_original_bank_failure(self):
        c=make_case(bank_noi=50);args=tuple(c[:6]);_,r=current(args,c[-1],raw(registry(args)));self.assertIsNone(r.payload['current_project_return_story'])
        self.assertIn('historical_lifecycle_calculation_blocked',r.payload['blockers']);self.assertTrue(r.payload['bank_capacity_blockers'])
    def test_current_registry_does_not_repair_unmatched_opening_debt(self):
        def change(p):p.clear();p.update(old_history(self.history.payload['context']))
        c=make_case(pre_change=change);args=tuple(c[:6]);_,r=current(args,c[-1],raw(registry(args)));self.assertIsNone(r.payload['current_project_return_story']);self.assertTrue(r.payload['opening_debt_blockers'])
    def test_rehashed_base_and_registry_forgery_rejected(self):
        a,_=self.evaluate()
        for index,change in [(1,lambda p:p.update(decision='PASS')),(3,lambda p:p.update(state='current_synthetic_evidence',blockers=['forged']))]:
            bad=list(a);bad[index]=forge(bad[index],change)
            with self.assertRaises(ValidationError):assemble_current_lifecycle(*bad)
    def test_reordered_bindings_valid_extra_identity_rejected(self):
        _,r=self.evaluate(lambda p:(p['requirements'].reverse(),p['evidence'].reverse()));self.assertIsNotNone(r.payload['current_project_return_story'])
        def extra(p):
            req=copy.deepcopy(p['requirements'][0]);req.update(requirement_id='/extra',source_locator='/extra');p['requirements'].append(req)
            e=copy.deepcopy(p['evidence'][0]);e.update(evidence_id='SYNTHETIC-extra',requirement_id='/extra',source_locator='/extra');p['evidence'].append(e)
        _,r=self.evaluate(extra);self.assertIn('complete_lifecycle_source_binding_inventory_mismatch',r.payload['blockers'])


class LifecycleReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.arguments,cls.history=recover_case();cls.source=registry(cls.arguments)
    def test_replayed_current_report_preserves_returns_and_debt_without_approval(self):
        a,r=current(self.arguments,self.history,raw(self.source));report=render_current_lifecycle_review(a,r);text=report.payload['markdown']
        for marker in ['1400.0000','1298.9197','-101.0803','120.0000','Deuda de apertura','PENDING','Retorno personal','no caja']:self.assertIn(marker,text)
        self.assertEqual(report.payload['markdown_sha256'],digest(text));self.assertFalse(report.payload['external_decision_pdf_produced'])
    def test_expired_report_withdraws_numbers_without_deleting_history(self):
        source=copy.deepcopy(self.source);source['evidence'][0]['valid_until']=AS_OF;a,r=current(self.arguments,self.history,raw(source));text=render_current_lifecycle_review(a,r).payload['markdown']
        for value in ['1400.0000','1298.9197','120.0000','-101.0803']:self.assertNotIn(value,text)
        self.assertIn('evidence',text);self.assertIn('no se sustituye por cero',text);self.assertIsNotNone(self.history.compiled_raw)
    def test_rehashed_current_report_forgery_not_rendered(self):
        a,r=current(self.arguments,self.history,raw(self.source));bad=forge(r,lambda p:p['current_project_return_story'].update(gross_contributions={'numerator':'9','denominator':'1'}))
        with self.assertRaises(ValidationError):render_current_lifecycle_review(a,bad)


if __name__=='__main__':unittest.main()
