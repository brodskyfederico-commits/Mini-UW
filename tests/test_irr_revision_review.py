from dataclasses import replace
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.irr_revision_review import (compare_irr_revisions,expanded_source,_base,
    _comparison_blockers,_numeric_comparison,differences)
from miniuw_foundation.irr_review_artifacts import (build_review_artifacts,export_review_bundle,recover_review_bundle,
    read_review_artifacts,write_review_artifacts,audit_review_directory,versions)
from miniuw_foundation.scheduled_expense_case import sha

ROOT=Path(__file__).resolve().parents[1]
raw=lambda p:(canonical(p)+'\n').encode()
q=lambda v:rational(F(v))
def sources(label):
    p=json.loads((ROOT/'docs/review/revision-fixture-generation-T102.json').read_bytes())
    c=next(c for c in p['cases']if c['label']==label)
    return tuple((ROOT/c[key]).read_bytes()for key in ('reference','candidate','spec'))


class IRRRevisionReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args=sources('criteria');cls.files,cls.checked=build_review_artifacts(*cls.args)
        cls.reference=_base(expanded_source(cls.args[0]));cls.candidate=_base(expanded_source(cls.args[1]))

    def test_criterion_revision_changes_condition_with_zero_financial_deltas_and_no_adoption(self):
        p=self.checked.payload;b,a=p['reference_snapshot'],p['candidate_snapshot']
        self.assertEqual(p['state'],'comparable_synthetic_candidate_review')
        self.assertEqual((b['case_revision'],a['case_revision']),(42,50))
        self.assertEqual(b['IRR_interval_condition']['row_state'],'BAND');self.assertEqual(a['IRR_interval_condition']['row_state'],'PASS_CONDITION')
        self.assertEqual(b['current_project_return_story'],a['current_project_return_story'])
        self.assertTrue(all(value==q(0)for value in p['projection_deltas'].values()))
        self.assertEqual(p['financial_story_changes'],[]);self.assertTrue(p['criterion_source_changes'])
        self.assertTrue(any('/registry_utf8::json/'in r['pointer']for r in p['decoded_source_changes']))

    def test_financial_renewal_deltas_reproduce_receipts_sale_and_normalization(self):
        p=compare_irr_revisions(*sources('renewal')).payload;d=p['projection_deltas']
        self.assertEqual(d['gross_contributions'],q(0));self.assertEqual(d['gross_distributions'],q(-2))
        self.assertEqual(d['net_cash_profit'],q(-2));self.assertEqual(d['equity_multiple'],q(F(-1,700)))
        sale=next(r for r in p['event_deltas']if r['category']=='net_sale_distribution')
        self.assertEqual(sale['delta'],q(-2));self.assertEqual(p['normalization_comparison']['deltas']['total_distributions'],q(F(-1,70)))
        self.assertIsNone(p['annual_IRR']['selected_rate']);self.assertIsNone(p['annual_IRR']['rate_delta'])
        self.assertFalse(p['isolated_variable_causality_claimed'])

    def test_expired_candidate_does_not_install_reference_figures_or_compute_a_delta(self):
        args=sources('expired');p=compare_irr_revisions(*args).payload
        self.assertIsNotNone(p['reference_snapshot']['current_project_return_story'])
        self.assertIsNone(p['candidate_snapshot']['current_project_return_story'])
        self.assertIn('candidate_current_projection_unavailable',p['comparison_blockers'])
        self.assertIsNone(p['projection_deltas']);self.assertIsNone(p['event_deltas']);self.assertIsNone(p['annual_IRR']['candidate_roots'])
        self.assertFalse(p['reference_snapshot_is_candidate_fallback']);self.assertEqual(p['decision'],'PENDING')

    def test_decoded_source_diff_preserves_nested_locators_missing_null_zero_and_atomic_rationals(self):
        a=raw(dict(scheduled_case_utf8=canonical(dict(base_case_utf8=canonical(dict(value=None,amount=q(0),items=[0]))))))
        b=raw(dict(scheduled_case_utf8=canonical(dict(base_case_utf8=canonical(dict(amount=q(1),items=[0,None],extra=0))))))
        rows=differences(expanded_source(a),expanded_source(b));base='/scheduled_case_utf8::json/base_case_utf8::json/'
        removed=next(r for r in rows if r['pointer']==base+'value')
        self.assertTrue(removed['before_exists']);self.assertIsNone(removed['before']);self.assertFalse(removed['after_exists'])
        added=next(r for r in rows if r['pointer']==base+'extra');self.assertEqual(added['after'],0);self.assertFalse(added['before_exists'])
        rational_row=next(r for r in rows if r['pointer']==base+'amount')
        self.assertEqual(rational_row['before'],q(0));self.assertEqual(rational_row['after'],q(1))
        self.assertTrue(any(r['pointer']==base+'items/1'and r['after_exists']and r['after']is None for r in rows))

    def test_protocol_incompatibilities_block_deltas_without_assuming_compatible_context(self):
        p=self.checked.payload;bs=p['reference_snapshot']['current_project_return_story'];cs=p['candidate_snapshot']['current_project_return_story']
        spec=json.loads(self.args[2])
        mutations=[('case_identity_mismatch',lambda c:c.update(case_id='OTHER')),
            ('candidate_revision_must_be_later',lambda c:c.update(case_revision=self.reference['case_revision'])),
            ('profile_mismatch',lambda c:c.update(profile='OTHER')),
            ('economic_context_mismatch:deal_id',lambda c:c['context'].update(deal_id='OTHER')),
            ('economic_context_mismatch:scenario_id',lambda c:c['context'].update(scenario_id='OTHER')),
            ('economic_context_mismatch:definition_set_revision',lambda c:c['context'].update(definition_set_revision='OTHER')),
            ('common_evaluation_instant_required',lambda c:c.update(as_of_UTC='2027-07-02T12:00:00Z')),
            ('required_scenario_inventory_mismatch',lambda c:c.update(required_scenarios=['OTHER']))]
        for expected,mutate in mutations:
            c=copy.deepcopy(self.candidate);mutate(c)
            self.assertIn(expected,_comparison_blockers(self.reference,c,bs,cs,spec,*self.args[:2]))
        for key in ('currency','cash_horizon'):
            candidate_story=copy.deepcopy(cs);candidate_story[key]='OTHER'
            self.assertIn(key+'_mismatch',_comparison_blockers(self.reference,self.candidate,bs,candidate_story,spec,*self.args[:2]))

    def test_wrong_source_hash_missing_basis_and_old_revision_remain_pending(self):
        for mutate,expected in ((lambda s:s.update(candidate_case_sha256='0'*64),'candidate_case_sha256_mismatch'),
            (lambda s:s.update(comparison_basis_ref=None),'explicit_comparison_basis_missing')):
            spec=json.loads(self.args[2]);mutate(spec);p=compare_irr_revisions(*self.args[:2],raw(spec)).payload
            self.assertIn(expected,p['comparison_blockers']);self.assertIsNone(p['projection_deltas']);self.assertEqual(p['state'],'PENDING')
        spec=json.loads(self.args[2]);spec['candidate_case_sha256']=sha(self.args[0])
        p=compare_irr_revisions(self.args[0],self.args[0],raw(spec)).payload
        self.assertIn('candidate_revision_must_be_later',p['comparison_blockers']);self.assertFalse(p['active_revision_changed'])

    def test_zero_missing_and_changed_normalization_base_do_not_become_automatic_values(self):
        before=self.checked.payload['reference_snapshot']['current_project_return_story'];after=copy.deepcopy(before)
        after['equity_multiple']=None
        totals,events,norm,blockers=_numeric_comparison(before,after)
        self.assertEqual(totals['gross_distributions'],q(0));self.assertIsNone(totals['equity_multiple']);self.assertEqual(blockers,[])
        after=copy.deepcopy(before);after['normalized_story']['basis_ref']='OTHER'
        _,_,norm,_=_numeric_comparison(before,after)
        self.assertIsNone(norm['deltas']);self.assertIn('normalization_basis_or_reference_mismatch',norm['blockers'])
        before=copy.deepcopy(before);before['normalized_story']['scale_factor']=None
        after=copy.deepcopy(before)
        _,_,norm,_=_numeric_comparison(before,after)
        self.assertIsNone(norm['deltas']);self.assertIn('normalization_missing',norm['blockers'])

    def test_delta_arithmetic_budget_withdraws_comparison_values_without_mutating_snapshots(self):
        # Unit probe of the exact delta guard, not a source-accepted financial case.
        before=copy.deepcopy(self.checked.payload['reference_snapshot']['current_project_return_story']);after=copy.deepcopy(before)
        before['gross_distributions']=q(F(1,2**3000-1));after['gross_distributions']=q(F(1,2**3001-1))
        saved=copy.deepcopy(before);a,b,c,blockers=_numeric_comparison(before,after)
        self.assertEqual((a,b,c),(None,None,None));self.assertEqual(blockers,['delta_exact_arithmetic_budget_exceeded']);self.assertEqual(before,saved)

    def test_decoded_source_and_complete_diff_budgets_reject_instead_of_truncating(self):
        nested=0
        for _ in range(66):nested=dict(child=nested)
        with self.assertRaises(ValidationError):expanded_source(raw(nested))
        with self.assertRaises(ValidationError):differences(dict(a=1,b=1),dict(a=2,b=2),limit=1)
        with self.assertRaises(ValidationError):expanded_source(raw(dict(registry_utf8='not JSON')))

    def test_candidate_pdf_and_flags_are_reproduced_from_candidate_only(self):
        pages=PdfReader(BytesIO(self.files['candidate-MiniUW_v1_Resumen.pdf']));self.assertEqual(len(pages.pages),1)
        text=pages.pages[0].extract_text();self.assertIn('cumple regla (sim.)',text);self.assertIn('Decision: PENDIENTE',text)
        self.assertIn(self.checked.candidate_run.sha256,text)
        p=self.checked.payload
        for key in ('candidate_generated','candidate_adopted','active_revision_changed','professional_review_authenticated',
            'financial_publication_authorized','deployment_enabled','real_decisions_enabled','source_or_rule_automatically_adjusted'):
            self.assertFalse(p[key])
        self.assertEqual(p['decision'],'PENDING')

    def test_rehashed_review_or_changed_source_cannot_be_exported_as_verified(self):
        p=self.checked.payload;p['candidate_adopted']=True;value=canonical(p)
        fake=replace(self.checked,payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):export_review_bundle(*self.args,fake)
        with self.assertRaises(ValidationError):export_review_bundle(self.args[0]+b'\n',*self.args[1:],self.checked)

    def test_portable_review_replays_both_exact_sources_spec_and_candidate_report(self):
        bundle=export_review_bundle(*self.args,self.checked);recovered=recover_review_bundle(bundle)
        self.assertEqual(recovered.run,self.checked)
        self.assertEqual((recovered.reference_raw,recovered.candidate_raw,recovered.spec_raw),self.args)
        self.assertEqual(recovered.candidate_report.pdf_bytes,self.files['candidate-MiniUW_v1_Resumen.pdf'])
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            for name,value in self.files.items():(root/name).write_bytes(value)
            self.assertEqual(audit_review_directory(root)['files_verified'],7)

    def test_portable_versions_rehashed_review_and_pdf_forgeries_are_rejected(self):
        bundle=export_review_bundle(*self.args,self.checked)
        for key in versions():
            p=json.loads(bundle);p[key]='0'*64
            with self.assertRaises(ValidationError):recover_review_bundle(raw(p))
        p=json.loads(bundle);result=json.loads(p['result']['payload_json']);result['candidate_adopted']=True
        value=canonical(result);p['result']=dict(payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):recover_review_bundle(raw(p))
        p=json.loads(bundle);p['candidate_pdf_sha256']='0'*64
        with self.assertRaises(ValidationError):recover_review_bundle(raw(p))

    def test_writer_retry_audit_and_different_review_do_not_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'out';write_review_artifacts(*self.args,target)
            before={p.name:p.read_bytes()for p in target.iterdir()};self.assertEqual(len(before),7)
            self.assertEqual(sum(p.suffix=='.pdf'for p in target.iterdir()),1)
            self.assertEqual(write_review_artifacts(*self.args,target)['status'],'identical_existing_verified')
            spec=json.loads(self.args[2]);spec['comparison_basis_ref']='OTHER'
            with self.assertRaises(ValidationError):write_review_artifacts(*self.args[:2],raw(spec),target)
            self.assertEqual(before,{p.name:p.read_bytes()for p in target.iterdir()})

    def test_rehashed_unsafe_extra_and_symlink_packet_entries_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for name,value in self.files.items():(root/name).write_bytes(value)
            restore();(root/'revision-review.json').write_bytes(b'{}');p=json.loads(self.files['package.json'])
            row=next(r for r in p['files']if r['path']=='revision-review.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_review_directory(root)
            restore();p=json.loads(self.files['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_review_directory(root)
            restore();(root/'extra.txt').write_bytes(b'extra')
            with self.assertRaises(ValidationError):read_review_artifacts(root)
            (root/'extra.txt').unlink();(root/'revision-review.txt').unlink();(root/'revision-review.txt').symlink_to(root/'revision-review.json')
            with self.assertRaises(ValidationError):read_review_artifacts(root)

    def test_failed_rename_cleans_owned_temporaries_and_preserves_siblings(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep.txt';keep.write_bytes(b'keep')
            with patch('miniuw_foundation.irr_review_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_review_artifacts(*self.args,root/'out')
            self.assertEqual(list(root.iterdir()),[keep]);self.assertEqual(keep.read_bytes(),b'keep')


if __name__=='__main__':unittest.main()
