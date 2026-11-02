"""Synthetic review proposals are auditable branches, never authenticated approvals."""
from dataclasses import replace
import copy,hashlib,json,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from miniuw_foundation import ValidationError
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive
from miniuw_foundation.review_proposals import (SCHEMA,parse_review_proposal,evaluate_review_proposal,ReviewRevisionConflict)
from miniuw_foundation.screening import simulate_screening
from miniuw_foundation.drafts import canonical,digest
from test_screening import case,q


def proposal(base_raw,base_run,after=None,patches=None,criteria_revision=None):
    base=json.loads(base_raw)
    patch={'table':'metric_values','metric_id':'YoC','scenario_id':'Downside','field':'value',
        'expected_before':base['metric_values'][1]['value'],'proposed_after':after if after is not None else q(55,1000),
        'reason':'SYNTHETIC proposed measured-value revision, not an actual professional input'}
    return {'schema':SCHEMA,'proposal_id':'SYNTHETIC-review-1','base_source_sha256':hashlib.sha256(base_raw).hexdigest(),
        'base_run_sha256':base_run.sha256,'new_case_id':'SYNTHETIC-candidate-1','new_run_id':'candidate-run-1',
        'new_criteria_revision':criteria_revision,'author_label':'SYNTHETIC reviewer label only',
        'proposal_reason':'Explicit review proposal fixture','evidence_refs':['SYNTHETIC-evidence:proposed-source-v2'],
        'patches':patches if patches is not None else [patch],'status':'proposal_only'}


def raw(value):return json.dumps(value).encode()


class ReviewProposalTests(unittest.TestCase):
    def setUp(self):
        p=case();p['metric_values'][1]['value']=q(45,1000)
        self.base=raw(p);self.screen=simulate_screening(self.base)

    def evaluate(self,p=None):return evaluate_review_proposal(self.base,self.screen,raw(p or proposal(self.base,self.screen)))

    def test_explicit_value_revision_can_simulate_pass_without_mutating_original(self):
        before=bytes(self.base);run=self.evaluate()
        self.assertEqual(run.payload['base_simulation_result'],'PENDING')
        self.assertEqual(run.payload['candidate_simulation_result'],'PASS')
        self.assertEqual(self.base,before);self.assertEqual(self.screen,simulate_screening(before))
        self.assertFalse(run.payload['original_source_modified']);self.assertFalse(run.payload['automatic_variable_optimization'])
        self.assertEqual(run.payload['changes'][0]['locator'],'/metric_values/1/value')

    def test_explicit_value_revision_can_simulate_fail_or_remain_pending(self):
        for value,state in [(q(35,1000),'FAIL'),(q(46,1000),'PENDING')]:
            run=self.evaluate(proposal(self.base,self.screen,after=value))
            self.assertEqual(run.payload['candidate_simulation_result'],state)
            self.assertEqual(run.payload['decision'],'PENDING')

    def test_explicit_null_clears_candidate_only_without_default_zero(self):
        p=proposal(self.base,self.screen);p['patches'][0]['proposed_after']=None
        run=self.evaluate(p);value=json.loads(run.candidate_raw)['metric_values'][1]['value']
        self.assertIsNone(value);self.assertEqual(run.payload['candidate_simulation_result'],'PENDING')
        self.assertEqual(json.loads(self.base)['metric_values'][1]['value'],q(45,1000))

    def test_changed_criterion_requires_new_revision_and_keeps_metric_unchanged(self):
        p=proposal(self.base,self.screen,criteria_revision='SYNTHETIC-criteria-v2')
        p['patches']=[{'table':'criteria','metric_id':'YoC','scenario_id':'Downside','field':'pass_condition.threshold',
            'expected_before':q(5,100),'proposed_after':q(45,1000),'reason':'SYNTHETIC revised criterion'}]
        run=self.evaluate(p);candidate=json.loads(run.candidate_raw)
        self.assertEqual(run.payload['candidate_simulation_result'],'PASS')
        self.assertEqual(candidate['metric_values'],json.loads(self.base)['metric_values'])
        self.assertEqual(candidate['criteria_revision'],'SYNTHETIC-criteria-v2')
        p['new_criteria_revision']=None
        with self.assertRaises(ValidationError):self.evaluate(p)

    def test_operator_revision_respects_exact_equality_and_band_rule(self):
        p=proposal(self.base,self.screen,criteria_revision='SYNTHETIC-criteria-v2')
        p['patches']=[{'table':'criteria','metric_id':'YoC','scenario_id':'Downside','field':'pass_condition.operator',
            'expected_before':'>=','proposed_after':'>','reason':'SYNTHETIC equality convention proposal'}]
        run=self.evaluate(p)
        self.assertEqual(run.payload['candidate_simulation_result'],'PENDING')
        self.assertEqual(run.candidate_run.payload['band_policy_applied'],'pending_professional_review')

    def test_wrong_base_source_hash_or_run_hash_is_stale(self):
        for field in ['base_source_sha256','base_run_sha256']:
            p=proposal(self.base,self.screen);p[field]='0'*64
            with self.assertRaises(ReviewRevisionConflict):self.evaluate(p)

    def test_forged_base_run_does_not_become_a_reviewable_baseline(self):
        p=self.screen.payload;p['simulation_result']='PASS';encoded=canonical(p)
        forged=replace(self.screen,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ReviewRevisionConflict):evaluate_review_proposal(self.base,forged,raw(proposal(self.base,forged)))

    def test_expected_before_matches_source_representation_not_only_numeric_equality(self):
        p=proposal(self.base,self.screen);p['patches'][0]['expected_before']=q(9,200)
        with self.assertRaises(ReviewRevisionConflict):self.evaluate(p)

    def test_nonexistent_target_and_locked_scope_fields_rejected(self):
        p=proposal(self.base,self.screen);p['patches'][0]['scenario_id']='Upside'
        with self.assertRaises(ReviewRevisionConflict):self.evaluate(p)
        for table,field in [('metric_values','unit'),('criteria','applicability'),('context','run_id'),('criteria','hypothetical_band_policy')]:
            p=proposal(self.base,self.screen);p['patches'][0].update(table=table,field=field)
            with self.assertRaises(ValidationError):self.evaluate(p)

    def test_duplicate_patch_and_noop_patch_rejected_without_last_wins(self):
        p=proposal(self.base,self.screen);p['patches'].append(copy.deepcopy(p['patches'][0]))
        with self.assertRaises(ValidationError):self.evaluate(p)
        p=proposal(self.base,self.screen);p['patches'][0]['proposed_after']=p['patches'][0]['expected_before']
        with self.assertRaises(ValidationError):self.evaluate(p)

    def test_batch_failure_leaves_no_partial_candidate_or_archived_objects(self):
        p=proposal(self.base,self.screen);bad=copy.deepcopy(p['patches'][0]);bad.update(metric_id='IRR',expected_before=q(99),proposed_after=q(1))
        p['patches'].append(bad)
        with EvidenceArchive(':memory:') as archive:
            with self.assertRaises(ReviewRevisionConflict):self.evaluate(p)
            self.assertEqual(archive._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
        self.assertEqual(simulate_screening(self.base),self.screen)

    def test_candidate_identities_and_criterion_version_must_be_explicit(self):
        for field,value in [('new_case_id',json.loads(self.base)['case_id']),('new_run_id',json.loads(self.base)['context']['run_id']),
            ('new_criteria_revision','invented-without-criterion-change')]:
            p=proposal(self.base,self.screen);p[field]=value
            with self.assertRaises(ValidationError):self.evaluate(p)

    def test_author_names_evidence_labels_and_approval_flags_do_not_authenticate(self):
        p=proposal(self.base,self.screen);p['author_label']='Lorena — fixture label only'
        run=self.evaluate(p)
        self.assertFalse(run.payload['author_identity_verified']);self.assertFalse(run.payload['evidence_refs_verified'])
        self.assertFalse(run.payload['professional_review_authenticated']);self.assertFalse(run.payload['proposal_accepted'])
        p['approved']=True
        with self.assertRaises(ValidationError):self.evaluate(p)
        p.pop('approved');p['status']='approved'
        with self.assertRaises(ValidationError):self.evaluate(p)

    def test_evidence_reason_and_explicit_nonempty_change_batch_required(self):
        for field,value in [('evidence_refs',[]),('proposal_reason',''),('patches',[]),('proposal_id','real-review')]:
            p=proposal(self.base,self.screen);p[field]=value
            with self.assertRaises(ValidationError):parse_review_proposal(raw(p))

    def test_candidate_metadata_inventory_and_selected_policy_cannot_drift(self):
        run=self.evaluate();candidate=json.loads(run.candidate_raw);original=json.loads(self.base)
        for key in ('required_metrics','required_scenarios','aggregation_rule','hypothetical_band_policy','criteria_status'):
            self.assertEqual(candidate[key],original[key])
        self.assertEqual(candidate['context']['deal_id'],original['context']['deal_id'])
        self.assertFalse(run.candidate_run.payload['production_authorized'])

    def test_run_properties_return_isolated_copies(self):
        run=self.evaluate();changed=run.payload;changed['changes'][0]['after']=q(999)
        self.assertEqual(run.payload['changes'][0]['after'],q(55,1000))
        self.assertEqual(simulate_screening(run.candidate_raw),run.candidate_run)

    def test_reopen_restores_original_proposal_and_candidate_bytes(self):
        p=raw(proposal(self.base,self.screen));run=evaluate_review_proposal(self.base,self.screen,p)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'review.sqlite3'
            with EvidenceArchive(path) as archive:
                key=archive.save_review_proposal(self.base,self.screen,p,run)
                self.assertEqual(key,archive.save_review_proposal(self.base,self.screen,p,run))
            with EvidenceArchive(path) as archive:
                restored=archive.load_review_proposal(key)
                self.assertEqual(restored.run,run);self.assertEqual(restored.base_run,self.screen)
                self.assertEqual(archive.get_screening_source(restored.payload['base_source_sha256']),self.base)
                self.assertEqual(archive.get_review_proposal_source(restored.payload['proposal_source_sha256']),p)
                self.assertEqual(archive.get_screening_source(restored.payload['candidate_source_sha256']),run.candidate_raw)

    def test_independent_proposals_fork_without_accepting_or_replacing_each_other(self):
        with EvidenceArchive(':memory:') as archive:
            keys=[]
            for value,state in [(q(55,1000),'PASS'),(q(35,1000),'FAIL')]:
                p=raw(proposal(self.base,self.screen,after=value));run=evaluate_review_proposal(self.base,self.screen,p)
                key=archive.save_review_proposal(self.base,self.screen,p,run);keys.append(key)
                self.assertEqual(archive.load_review_proposal(key).run.payload['candidate_simulation_result'],state)
            self.assertNotEqual(*keys)
            self.assertEqual(archive.load_review_proposal(keys[0]).base_run,self.screen)

    def test_forgery_version_change_and_atomic_fault_do_not_create_accepted_review(self):
        p=raw(proposal(self.base,self.screen));run=evaluate_review_proposal(self.base,self.screen,p)
        forged=run.payload;forged['proposal_accepted']=True;encoded=canonical(forged)
        changed=replace(run,payload_json=encoded,sha256=digest(encoded))
        with EvidenceArchive(':memory:') as archive:
            with self.assertRaises(ValidationError):archive.save_review_proposal(self.base,self.screen,p,changed)
            with patch.object(archive,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):archive.save_review_proposal(self.base,self.screen,p,run)
            self.assertEqual(archive._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=archive.save_review_proposal(self.base,self.screen,p,run)
            body=json.loads(archive.read_bundle_bytes(key));body['versions'][0]='0'*64
            with archive._transaction():bad=archive._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):archive.load_review_proposal(bad)
            body=json.loads(archive.read_bundle_bytes(key));body['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with archive._transaction():bad=archive._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):archive.load_review_proposal(bad)

if __name__=='__main__':unittest.main()
