from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import copy
import hashlib
import json
import re
import tempfile
import unittest
from unittest.mock import patch

from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.v1_case import run_v1_case
from miniuw_foundation.v1_revision import compare_v1_cases,parse_comparison,differences
from miniuw_foundation.v1_revision_bundle import (build_comparison_artifacts,export_comparison_bundle,recover_comparison_bundle,
    write_comparison_artifacts,audit_comparison_directory)

ROOT=Path(__file__).resolve().parents[1]
raw=lambda p:(canonical(p)+'\n').encode()
q=lambda n:rational(Fraction(n))
sha=lambda b:hashlib.sha256(b).hexdigest()
REF=(ROOT/'templates/miniuw-v1-synthetic-case.json').read_bytes()
CANDIDATE=(ROOT/'templates/miniuw-v1-sale-500-candidate.json').read_bytes()
SPEC=(ROOT/'templates/miniuw-v1-revision-comparison.json').read_bytes()


def specification(ref=REF,candidate=CANDIDATE):
    p=json.loads(SPEC);p.update(reference_case_sha256=sha(ref),candidate_case_sha256=sha(candidate));return raw(p)


def renew_explicit_test_evidence(p):
    # Test fixture's explicit synthetic evidence revision, never runtime auto-renewal.
    requirements=run_v1_case(raw(p)).payload['required_source_bindings']
    if len(requirements)!=37:raise AssertionError('expected structurally valid complete test chain')
    p['source_registry']['requirements']=requirements;by={r['requirement_id']:r for r in requirements}
    for e in p['source_registry']['evidence']:
        e.update(by[e['requirement_id']]);e['basis_ref']='SYNTHETIC-explicit-test-evidence-revision-not-authority'
    return raw(p)


class V1RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result_run=compare_v1_cases(REF,CANDIDATE,SPEC)

    def test_rebuild_both_full_cases_and_exact_deltas_without_choosing_candidate(self):
        p=self.result_run.payload
        self.assertEqual(p['comparison_blockers'],[]);self.assertEqual(p['projection_deltas'],dict(gross_contributions=q(0),gross_distributions=q(100),net_cash_profit=q(100),equity_multiple=q(Fraction(1,14))))
        self.assertEqual(p['reference']['current_project_return_story']['gross_distributions'],q(778));self.assertEqual(p['candidate']['current_project_return_story']['gross_distributions'],q(878))
        self.assertEqual(p['candidate']['current_project_return_story']['net_cash_profit'],q(-522));self.assertIsNone(p['chosen_candidate']);self.assertEqual(p['decision'],'PENDING')
        rows=p['input_changes'];sale=next(r for r in rows if r['pointer']=='/recipe/sale/closing_source/amounts/gross_proceeds/value');self.assertEqual(sale['before'],q(400));self.assertEqual(sale['after'],q(500))
        self.assertTrue(any(r['pointer'].startswith('/source_registry/')for r in rows));self.assertEqual(sum(Fraction(int(e['delta']['numerator']),int(e['delta']['denominator']))for e in p['event_deltas']),100)

    def test_stale_either_case_withdraws_all_deltas_and_keeps_source_blockers(self):
        for side in ('reference','candidate'):
            ref=json.loads(REF);cand=json.loads(CANDIDATE);target=ref if side=='reference'else cand;target['source_registry']['evidence'][0]['valid_until']=target['as_of_UTC']
            a,b=raw(ref),raw(cand);p=compare_v1_cases(a,b,specification(a,b)).payload
            self.assertIsNone(p['projection_deltas']);self.assertIsNone(p['event_deltas']);self.assertIsNone(p[side]['current_project_return_story']);self.assertIn(side+'_current_projection_unavailable',p['comparison_blockers']);self.assertTrue(p[side]['blockers']['projection'])

    def test_missing_or_conflicting_candidate_is_pending_without_repair(self):
        for change in (lambda p:p['recipe']['operating_periods'][0]['cash_source']['amounts']['debt_principal_payment'].update(value=None),lambda p:p['original_inputs'][0].update(value='conflicting-rent-basis')):
            p=json.loads(CANDIDATE);change(p);cand=raw(p);r=compare_v1_cases(REF,cand,specification(candidate=cand)).payload
            self.assertIsNone(r['projection_deltas']);self.assertTrue(r['candidate']['blockers']['projection']);self.assertIsNotNone(r['reference']['current_project_return_story'])

    def test_exact_case_pins_and_missing_comparison_basis_block(self):
        for change in (lambda s:s.update(reference_case_sha256='0'*64),lambda s:s.update(candidate_case_sha256='0'*64),lambda s:s.update(comparison_basis_ref=None)):
            s=json.loads(SPEC);change(s);p=compare_v1_cases(REF,CANDIDATE,raw(s)).payload;self.assertIsNone(p['projection_deltas']);self.assertTrue(p['comparison_blockers'])

    def test_case_identity_and_revision_order_are_required(self):
        for change in (lambda p:p.update(case_id='SYNTHETIC-another-case'),lambda p:p.update(case_revision=1)):
            c=json.loads(CANDIDATE);change(c);cand=raw(c);p=compare_v1_cases(REF,cand,specification(candidate=cand)).payload;self.assertIsNone(p['projection_deltas']);self.assertTrue(p['comparison_blockers'])

    def test_common_time_economic_context_and_scenario_inventory_required(self):
        for key in ('as_of_UTC','deal_id','required_scenarios'):
            c=json.loads(CANDIDATE)
            if key=='as_of_UTC':c[key]='2027-07-01T12:01:00Z'
            elif key=='deal_id':c['context'][key]='SYNTHETIC-another-deal'
            else:c[key].append('SYNTHETIC-Downside-not-inferred')
            cand=raw(c);p=compare_v1_cases(REF,cand,specification(candidate=cand)).payload;self.assertIsNone(p['projection_deltas']);self.assertTrue(p['comparison_blockers'])

    def test_strict_specification_and_invalid_bytes_rejected(self):
        for change in (lambda p:p.update(extra=True),lambda p:p.update(schema='live'),lambda p:p.update(comparison_id='real-case'),lambda p:p.update(candidate_case_sha256='short'),lambda p:p.update(comparison_basis_ref='')):
            p=json.loads(SPEC);change(p)
            with self.assertRaises(ValidationError):parse_comparison(raw(p))
        for b in (b'{}',b'\xff',b'{"schema":1,"schema":2}',b'NaN',b'x'*65537):
            with self.assertRaises(ValidationError):parse_comparison(b)

    def test_differences_preserve_presence_null_zero_types_escapes_and_budget(self):
        rows=differences({'a/b':{'~value':None},'r':q(1),'arr':[0]},{'a/b':{'~value':0},'r':q(2),'arr':[False,None],'new':None})
        by={r['pointer']:r for r in rows};self.assertEqual(by['/a~1b/~0value']['before'],None);self.assertEqual(by['/a~1b/~0value']['after'],0)
        self.assertEqual(by['/r']['before'],q(1));self.assertEqual(by['/r']['after'],q(2));self.assertIs(by['/arr/0']['after'],False);self.assertFalse(by['/arr/1']['before_exists']);self.assertFalse(by['/new']['before_exists'])
        self.assertEqual(differences({'x':0},{'x':0}),[]);self.assertEqual(len(differences([],list(range(4096)))),4096)
        with self.assertRaises(ValidationError):differences([],list(range(4097)))
        a,b={},{};na,nb=a,b
        for _ in range(130):na['x']={};nb['x']={};na,nb=na['x'],nb['x']
        nb['value']=1
        with self.assertRaises(ValidationError):differences(a,b)

    def test_all_irr_roots_policy_pending_and_immutable_repeated_result(self):
        p=self.result_run.payload
        for side in ('reference','candidate'):
            self.assertTrue(p['annual_IRR'][side+'_roots']);self.assertEqual(p[side]['input_catalog_summary']['pending'],54);self.assertTrue(all(m['criterion']['source_ref']is None for m in p[side]['metrics']))
        self.assertIsNone(p['annual_IRR']['selected_rate']);self.assertIsNone(p['annual_IRR']['rate_delta']);self.assertFalse(p['real_decisions_enabled']);self.assertFalse(p['isolated_variable_causality_claimed'])
        p['input_changes'].clear();self.assertTrue(self.result_run.payload['input_changes']);self.assertEqual(compare_v1_cases(REF,CANDIDATE,SPEC),self.result_run)

    def test_normalization_different_reference_is_not_same_investment_delta(self):
        c=json.loads(CANDIDATE);c['recipe']['investor_source']['normalization']['reference_amount']=q(20);cand=renew_explicit_test_evidence(c)
        p=compare_v1_cases(REF,cand,specification(candidate=cand)).payload
        self.assertEqual(p['projection_deltas']['gross_distributions'],q(100));n=p['normalization_comparison'];self.assertIsNone(n['deltas']);self.assertEqual(n['blockers'],['normalization_basis_or_reference_mismatch']);self.assertEqual(n['reference']['reference_amount'],q(10));self.assertEqual(n['candidate']['reference_amount'],q(20))

    def test_different_finite_cash_horizon_withdraws_cash_and_EM_deltas(self):
        c=json.loads(CANDIDATE)
        # Independently supplied complete alternate dated sources, not a grid-only patch.
        def shifted(value):
            if type(value)is dict:return {k:shifted(v)for k,v in value.items()}
            if type(value)is list:return [shifted(v)for v in value]
            if type(value)is str and re.fullmatch(r'\d{4}-\d{2}(-\d{2})?',value):return str(int(value[:4])-1)+value[4:]
            return value
        c['recipe']=shifted(c['recipe']);cand=renew_explicit_test_evidence(c)
        p=compare_v1_cases(REF,cand,specification(candidate=cand)).payload
        self.assertIsNotNone(p['candidate']['current_project_return_story']);self.assertIn('cash_horizon_mismatch',p['comparison_blockers']);self.assertIsNone(p['projection_deltas'])

    def test_renamed_gross_event_even_with_same_cash_requires_explicit_reconciliation(self):
        c=json.loads(CANDIDATE);s=c['recipe']['investor_source'];old='operating_slots-5';new='SYNTHETIC-renamed-zero-contribution'
        next(e for e in s['events']if e['event_id']==old)['event_id']=new
        s['normalization']['contribution_event_ids']=[new if e==old else e for e in s['normalization']['contribution_event_ids']]
        next(e for e in c['recipe']['investor_binding']['operating_slots']if e['investor_event_id']==old)['investor_event_id']=new
        cand=renew_explicit_test_evidence(c);p=compare_v1_cases(REF,cand,specification(candidate=cand)).payload
        self.assertIsNotNone(p['candidate']['current_project_return_story']);self.assertIn('dated_event_inventory_or_classification_mismatch',p['comparison_blockers']);self.assertIsNone(p['event_deltas'])


class V1RevisionBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.contents,cls.result_run=build_comparison_artifacts(REF,CANDIDATE,SPEC)

    def test_portable_exact_sources_results_and_every_change_in_internal_review(self):
        bundle=self.contents['comparison-evidence.json'];self.assertEqual(recover_comparison_bundle(bundle),self.result_run)
        p=json.loads(bundle);self.assertEqual(p['reference_utf8'].encode(),REF);self.assertEqual(p['candidate_utf8'].encode(),CANDIDATE);self.assertEqual(p['spec_utf8'].encode(),SPEC)
        text=self.contents['review.txt'].decode();self.assertIn('778.0000 | 878.0000 | 100.0000',text);self.assertIn('PENDIENTE',text)
        for row in self.result_run.payload['input_changes']:self.assertIn(canonical(row),text)
        self.assertEqual(set(self.contents),{'comparison.json','comparison-evidence.json','review.txt','package.json'})

    def test_rehashed_forged_result_does_not_bypass_export_or_recovery(self):
        p=self.result_run.payload;p['projection_deltas']['gross_distributions']=q(999);s=canonical(p);fake=replace(self.result_run,payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):export_comparison_bundle(REF,CANDIDATE,SPEC,fake)
        bundle=json.loads(self.contents['comparison-evidence.json']);bundle['result']=dict(payload_json=s,sha256=digest(s))
        with self.assertRaises(ValidationError):recover_comparison_bundle(raw(bundle))

    def test_changed_exact_source_versions_and_malformed_bundles_rejected(self):
        for key,value in [('engine_sha256','0'*64),('comparison_engine_sha256','0'*64),('definition_sha256','0'*64),('reference_utf8',REF.decode()+' '),('schema','live')]:
            p=json.loads(self.contents['comparison-evidence.json']);p[key]=value
            with self.assertRaises(ValidationError):recover_comparison_bundle(raw(p))
        for b in (b'{}',b'\xff',b'{"schema":1,"schema":2}'):
            with self.assertRaises(ValidationError):recover_comparison_bundle(b)
        with patch('miniuw_foundation.v1_revision_bundle.MAX_BUNDLE_BYTES',100):
            with self.assertRaises(ValidationError):export_comparison_bundle(REF,CANDIDATE,SPEC,self.result_run)

    def test_real_local_output_idempotent_retry_and_full_directory_replay(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'comparison';write_comparison_artifacts(REF,CANDIDATE,SPEC,out);before={p.name:p.read_bytes()for p in out.iterdir()}
            self.assertEqual(write_comparison_artifacts(REF,CANDIDATE,SPEC,out)['status'],'identical_existing_verified');self.assertEqual(audit_comparison_directory(out)['files_verified'],4)
            self.assertEqual(before,{p.name:p.read_bytes()for p in out.iterdir()})

    def test_different_existing_output_and_symlink_are_not_overwritten(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'comparison';out.mkdir()
            for k,v in self.contents.items():(out/k).write_bytes(v)
            s=json.loads(SPEC);s['comparison_id']='SYNTHETIC-other-comparison'
            with self.assertRaises(ValidationError):write_comparison_artifacts(REF,CANDIDATE,raw(s),out)
            link=Path(td)/'linked';link.symlink_to(out,target_is_directory=True)
            with self.assertRaises(ValidationError):audit_comparison_directory(link)
            self.assertEqual(self.contents,{p.name:p.read_bytes()for p in out.iterdir()})

    def test_altered_result_and_rehashed_package_still_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)
            for k,v in self.contents.items():(out/k).write_bytes(v)
            bad=b'{}';(out/'comparison.json').write_bytes(bad)
            with self.assertRaises(ValidationError):audit_comparison_directory(out)
            p=json.loads(self.contents['package.json']);row=next(r for r in p['files']if r['path']=='comparison.json');row.update(bytes=len(bad),sha256=sha(bad));(out/'package.json').write_bytes(raw(p))
            with self.assertRaises(ValidationError):audit_comparison_directory(out)

    def test_exact_inventory_malformed_unsafe_paths_and_symlink_file_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)
            for k,v in self.contents.items():(out/k).write_bytes(v)
            for files in (None,[None],['../../outside'],[dict(path='../../outside',bytes=0,sha256='0'*64)]*3):
                p=json.loads(self.contents['package.json']);p['files']=files;(out/'package.json').write_bytes(raw(p))
                with self.assertRaises(ValidationError):audit_comparison_directory(out)
            (out/'package.json').write_bytes(self.contents['package.json']);(out/'extra').write_text('extra')
            with self.assertRaises(ValidationError):audit_comparison_directory(out)
            (out/'extra').unlink();(out/'review.txt').unlink();(out/'review.txt').symlink_to(out/'comparison.json')
            with self.assertRaises(ValidationError):audit_comparison_directory(out)

    def test_failed_final_rename_leaves_no_partial_final_output(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'comparison'
            with patch('miniuw_foundation.v1_revision_bundle.os.rename',side_effect=OSError('injected rename failure')),patch('miniuw_foundation.v1_revision_bundle.build_comparison_artifacts',return_value=(self.contents,self.result_run)):
                with self.assertRaises(OSError):write_comparison_artifacts(REF,CANDIDATE,SPEC,out)
            self.assertFalse(out.exists());self.assertEqual(list(Path(td).iterdir()),[])

    def test_blocked_candidate_bundle_recovery_and_review_never_restore_old_numbers(self):
        candidate=json.loads(CANDIDATE);candidate['source_registry']['evidence'][0]['valid_until']=candidate['as_of_UTC'];source=raw(candidate);spec=specification(candidate=source)
        contents,run=build_comparison_artifacts(REF,source,spec);recovered=recover_comparison_bundle(contents['comparison-evidence.json'])
        self.assertEqual(recovered,run);self.assertEqual(recovered.payload['state'],'PENDING');self.assertIsNone(recovered.payload['projection_deltas']);self.assertIsNone(recovered.payload['candidate']['current_project_return_story'])
        text=contents['review.txt'].decode();self.assertIn('CIFRAS COMPARATIVAS RETIRADAS',text);self.assertNotIn('878.0000',text);self.assertTrue(recovered.payload['candidate']['blockers']['projection'])
