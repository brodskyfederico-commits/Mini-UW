from dataclasses import replace
from pathlib import Path
import copy,hashlib,json,tempfile,unittest
from unittest.mock import patch
from miniuw_foundation import ValidationError
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.scenario_threshold_rehearsal import simulate_scenario_thresholds
from miniuw_foundation.scenario_review import SCHEMA,evaluate_scenario_proposal,parse_scenario_proposal,ScenarioRevisionConflict
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence

R=Path(__file__).resolve().parents[1]
def raw(p):return json.dumps(p).encode()
def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}
def source():return (R/'sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx').read_bytes()
def base_case(full=False):
    p=json.loads((R/('templates/synthetic-documented-threshold-full.json'if full else'templates/synthetic-documented-threshold-base.json')).read_bytes())
    p['metric_values'][0]['value']=q(6,100)
    return raw(p)
def proposal(doc,base,run,amount=None,ident='SYNTHETIC-scenario-review-1'):
    p=json.loads(base);return {'schema':SCHEMA,'proposal_id':ident,'document_sha256':hashlib.sha256(doc).hexdigest(),
        'base_case_sha256':hashlib.sha256(base).hexdigest(),'base_run_sha256':run.sha256,'new_case_id':ident+'-case','new_run_id':ident+'-run',
        'author_label':'SYNTHETIC unverified reviewer','reason':'Explicit fictional metric correction','evidence_refs':['SYNTHETIC-evidence:v2'],
        'patches':[{'metric_id':'YoC','scenario_id':'Base','expected_before':p['metric_values'][0]['value'],'proposed_after':amount or q(7,100),'reason':'Fictional replacement measurement'}],'status':'proposal_only'}


class ScenarioReviewTests(unittest.TestCase):
    def setUp(self):self.doc=source();self.base=base_case();self.run=simulate_scenario_thresholds(self.doc,self.base)
    def evaluate(self,p=None):return evaluate_scenario_proposal(self.doc,self.base,self.run,raw(p or proposal(self.doc,self.base,self.run)))

    def test_pending_base_can_fork_to_pass_fail_or_pending_without_mutation(self):
        old=bytes(self.base)
        for amount,state in [(q(7,100),'PASS'),(q(5,100),'FAIL'),(q(61,1000),'PENDING')]:
            r=self.evaluate(proposal(self.doc,self.base,self.run,amount));self.assertEqual(r.payload['candidate_simulation_result'],state)
            self.assertEqual(self.base,old);self.assertEqual(simulate_scenario_thresholds(self.doc,self.base),self.run)

    def test_full_scenario_revision_cannot_solve_asking_applicability(self):
        base=base_case(True);run=simulate_scenario_thresholds(self.doc,base);p=proposal(self.doc,base,run)
        r=evaluate_scenario_proposal(self.doc,base,run,raw(p))
        self.assertEqual(r.payload['candidate_simulation_result'],'PENDING')
        self.assertEqual(r.payload['candidate_blockers'],['asking_relative_to_supported_price:Downside:pass_condition_and_applicability_unresolved'])

    def test_downside_correction_reclassifies_row_without_fabricated_fail_rule(self):
        base=base_case(True);run=simulate_scenario_thresholds(self.doc,base);p=proposal(self.doc,base,run)
        p['patches']=[{'metric_id':'YoC','scenario_id':'Downside','expected_before':q(6,100),'proposed_after':q(1,100),'reason':'Synthetic adverse revision'}]
        r=evaluate_scenario_proposal(self.doc,base,run,raw(p))
        row=next(r for r in r.candidate_run.payload['comparisons']if r['metric_id']=='YoC'and r['scenario_id']=='Downside')
        self.assertEqual(row['state'],'PASS_MISS_PENDING');self.assertIsNone(row['fail_condition'])

    def test_document_case_and_run_hashes_guard_stale_proposals(self):
        for key in ['document_sha256','base_case_sha256','base_run_sha256']:
            p=proposal(self.doc,self.base,self.run);p[key]='0'*64
            with self.assertRaises(ScenarioRevisionConflict):self.evaluate(p)

    def test_base_result_forged_with_recomputed_hash_is_not_accepted(self):
        payload=self.run.payload;payload['simulation_result']='PASS';encoded=canonical(payload)
        forged=replace(self.run,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ScenarioRevisionConflict):evaluate_scenario_proposal(self.doc,self.base,forged,raw(proposal(self.doc,self.base,forged)))

    def test_expected_before_requires_exact_representation(self):
        p=proposal(self.doc,self.base,self.run);p['patches'][0]['expected_before']=q(3,50)
        with self.assertRaises(ScenarioRevisionConflict):self.evaluate(p)

    def test_null_is_missing_in_candidate_only_not_zero(self):
        p=proposal(self.doc,self.base,self.run);p['patches'][0]['proposed_after']=None;r=self.evaluate(p)
        self.assertIsNone(json.loads(r.candidate_raw)['metric_values'][0]['value'])
        self.assertEqual(r.payload['candidate_simulation_result'],'PENDING');self.assertEqual(json.loads(self.base)['metric_values'][0]['value'],q(6,100))

    def test_scope_rules_and_applicability_cannot_be_patched(self):
        for extra in ['threshold','applicability','required_scenarios','approved']:
            p=proposal(self.doc,self.base,self.run);p['patches'][0][extra]='arbitrary'
            with self.assertRaises(ValidationError):self.evaluate(p)

    def test_batch_failure_duplicate_and_noop_do_not_create_partial_candidate(self):
        p=proposal(self.doc,self.base,self.run);p['patches'].append(copy.deepcopy(p['patches'][0]))
        with self.assertRaises(ValidationError):self.evaluate(p)
        p=proposal(self.doc,self.base,self.run);p['patches'][0]['proposed_after']=q(6,100)
        with self.assertRaises(ValidationError):self.evaluate(p)
        p=proposal(self.doc,self.base,self.run);p['patches'].append({'metric_id':'IRR','scenario_id':'Base','expected_before':q(0),'proposed_after':q(1),'reason':'bad stale patch'})
        with self.assertRaises(ScenarioRevisionConflict):self.evaluate(p)
        self.assertEqual(simulate_scenario_thresholds(self.doc,self.base),self.run)

    def test_missing_target_and_reused_candidate_identity_rejected(self):
        p=proposal(self.doc,self.base,self.run);p['patches'][0]['scenario_id']='Downside'
        with self.assertRaises(ScenarioRevisionConflict):self.evaluate(p)
        for key,basekey in [('new_case_id','case_id'),('new_run_id','run_id')]:
            p=proposal(self.doc,self.base,self.run);p[key]=json.loads(self.base)[basekey]
            with self.assertRaises(ValidationError):self.evaluate(p)

    def test_claimed_identity_and_evidence_do_not_authenticate_or_optimize(self):
        p=proposal(self.doc,self.base,self.run);p['author_label']='Lorena label only';r=self.evaluate(p)
        for key in ['author_identity_verified','evidence_refs_verified','proposal_accepted','professional_review_authenticated','original_modified','automatic_variable_optimization','production_authorized']:
            self.assertFalse(r.payload[key])
        self.assertEqual(r.payload['decision'],'PENDING')
        p['approved']=True
        with self.assertRaises(ValidationError):self.evaluate(p)

    def test_empty_evidence_reason_and_live_proposal_identity_rejected(self):
        for key,value in [('evidence_refs',[]),('reason',''),('proposal_id','real-proposal'),('status','approved')]:
            p=proposal(self.doc,self.base,self.run);p[key]=value
            with self.assertRaises(ValidationError):self.evaluate(p)

    def test_chained_revision_binds_exact_parent_candidate(self):
        first=self.evaluate();p=proposal(self.doc,first.candidate_raw,first.candidate_run,q(5,100),'SYNTHETIC-second')
        second=evaluate_scenario_proposal(self.doc,first.candidate_raw,first.candidate_run,raw(p))
        self.assertEqual(second.payload['base_case_sha256'],first.payload['candidate_case_sha256'])
        self.assertEqual(second.payload['candidate_simulation_result'],'FAIL')

    def test_payload_copies_and_context_preserve_original_deal_and_inventory(self):
        r=self.evaluate();p=r.payload;p['changes'].clear();self.assertEqual(len(r.payload['changes']),1)
        candidate=json.loads(r.candidate_raw);base=json.loads(self.base)
        for key in ['deal_id','required_scenarios']:self.assertEqual(candidate[key],base[key])

    def test_reopened_archive_recovers_document_base_proposal_candidate_and_runs(self):
        prop=raw(proposal(self.doc,self.base,self.run));r=self.evaluate()
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'review.sqlite3'
            with EvidenceArchive(path)as a:
                key=a.save_scenario_review(self.doc,self.base,self.run,prop,r);self.assertEqual(key,a.save_scenario_review(self.doc,self.base,self.run,prop,r))
            with EvidenceArchive(path)as a:
                b=a.load_scenario_review(key);self.assertEqual(b.run,r);self.assertEqual(b.base_run,self.run)
                self.assertEqual(a.get_documented_threshold_source(b.payload['document_source_sha256']),self.doc)
                self.assertEqual(a.get_scenario_threshold_case(b.payload['base_case_sha256']),self.base)
                self.assertEqual(a.get_scenario_proposal_source(b.payload['proposal_source_sha256']),prop)
                self.assertEqual(a.get_scenario_threshold_case(b.payload['candidate_case_sha256']),r.candidate_raw)

    def test_archive_forgery_and_atomic_capture_failure(self):
        prop=raw(proposal(self.doc,self.base,self.run));r=self.evaluate();p=r.payload;p['proposal_accepted']=True;encoded=canonical(p);forged=replace(r,payload_json=encoded,sha256=digest(encoded))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_scenario_review(self.doc,self.base,self.run,prop,forged)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_scenario_review(self.doc,self.base,self.run,prop,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_scenario_review(self.doc,self.base,self.run,prop,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_scenario_review(bad)

    def test_missing_candidate_and_incompatible_version_are_explicit(self):
        prop=raw(proposal(self.doc,self.base,self.run));r=self.evaluate()
        with EvidenceArchive(':memory:')as a:
            key=a.save_scenario_review(self.doc,self.base,self.run,prop,r);body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_scenario_review(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',r.payload['candidate_case_sha256']))
            with self.assertRaises(MissingEvidence):a.load_scenario_review(key)
