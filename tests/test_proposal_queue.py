from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import copy,json,tempfile,threading,unittest
from unittest.mock import patch
from miniuw_foundation import ValidationError
from miniuw_foundation.archive import EvidenceArchive,MissingEvidence
from miniuw_foundation.scenario_threshold_rehearsal import simulate_scenario_thresholds
from miniuw_foundation.scenario_review import evaluate_scenario_proposal
from miniuw_foundation.proposal_queue import ProposalQueue,QueueRevisionConflict,QueueOperationConflict,QueueIntegrityError
from test_scenario_review import source,base_case,proposal,raw,q


class ProposalQueueTests(unittest.TestCase):
    def setUp(self):
        self.doc=source();self.base=base_case();self.base_run=simulate_scenario_thresholds(self.doc,self.base)
        self.archive=EvidenceArchive(':memory:');self.queue=ProposalQueue(':memory:')
        self.parent=self.make_bundle(self.base,self.base_run,'SYNTHETIC-parent',q(7,100))
    def tearDown(self):self.queue.close();self.archive.close()
    def make_bundle(self,base,run,ident,amount,archive=None):
        p=raw(proposal(self.doc,base,run,amount,ident));result=evaluate_scenario_proposal(self.doc,base,run,p)
        return (archive or self.archive).save_scenario_review(self.doc,base,run,p,result)
    def record(self,key=None,op='record-1',rev=0,queue=None,archive=None):
        return(queue or self.queue).record(archive or self.archive,key or self.parent,operation_id=op,expected_revision=rev,actor_label='SYNTHETIC label',reason='Record fictional review proposal')
    def withdraw(self,op='withdraw-1',rev=1):
        return self.queue.withdraw('SYNTHETIC-parent',operation_id=op,expected_revision=rev,actor_label='SYNTHETIC label',reason='Explicit synthetic withdrawal')
    def child(self):
        first=self.archive.load_scenario_review(self.parent).run
        return self.make_bundle(first.candidate_raw,first.candidate_run,'SYNTHETIC-child',q(5,100))

    def test_record_queues_evidence_without_acceptance_or_review(self):
        r=self.record();self.assertEqual(r.payload['revision'],1);snap=self.queue.snapshot()
        self.assertEqual(snap['entries'][0]['state'],'recorded');self.assertFalse(snap['evidence_replayed'])
        self.assertFalse(r.payload['proposal_accepted']);self.assertFalse(r.payload['professional_review_authenticated']);self.assertEqual(r.payload['decision'],'PENDING')
        self.assertTrue(self.queue.verify_entry(self.archive,'SYNTHETIC-parent')['evidence_replayed'])

    def test_withdraw_retains_original_evidence_and_event_history(self):
        self.record();self.withdraw();snap=self.queue.snapshot()
        self.assertEqual(snap['revision'],2);self.assertEqual(snap['entries'][0]['state'],'withdrawn')
        self.assertEqual(len(self.queue.history()),2);self.assertEqual(self.archive.load_scenario_review(self.parent).run.payload['proposal_id'],'SYNTHETIC-parent')

    def test_supersede_requires_exact_parent_and_is_one_transaction(self):
        self.record();child=self.child()
        r=self.queue.supersede(self.archive,'SYNTHETIC-parent',child,operation_id='supersede',expected_revision=1,actor_label='SYNTHETIC label',reason='Explicit chained revision')
        rows={x['proposal_id']:x for x in self.queue.snapshot()['entries']}
        self.assertEqual(rows['SYNTHETIC-parent']['state'],'superseded');self.assertEqual(rows['SYNTHETIC-child']['parent_proposal_id'],'SYNTHETIC-parent')
        self.assertEqual(r.payload['revision'],2);self.assertFalse(r.payload['proposal_accepted'])

    def test_unrelated_fork_cannot_silently_replace_a_candidate(self):
        self.record();other=self.make_bundle(self.base,self.base_run,'SYNTHETIC-unrelated',q(5,100))
        with self.assertRaises(QueueRevisionConflict):self.queue.supersede(self.archive,'SYNTHETIC-parent',other,operation_id='bad',expected_revision=1,actor_label='SYNTHETIC label',reason='bad parent')
        self.assertEqual(self.queue.snapshot()['revision'],1);self.assertEqual(len(self.queue.snapshot()['entries']),1)

    def test_exact_operation_retry_returns_historical_receipt_after_state_changes(self):
        first=self.record();self.withdraw();again=self.record()
        self.assertEqual(again,first);self.assertEqual(self.queue.snapshot()['revision'],2);self.assertEqual(len(self.queue.history()),2)

    def test_operation_identity_cannot_be_reused_for_another_request(self):
        self.record()
        with self.assertRaises(QueueOperationConflict):self.queue.record(self.archive,self.parent,operation_id='record-1',expected_revision=0,actor_label='different label',reason='different request')
        self.assertEqual(self.queue.snapshot()['revision'],1)

    def test_stale_epoch_blocks_even_when_target_state_would_otherwise_match(self):
        self.record()
        with self.assertRaises(QueueRevisionConflict):self.withdraw(rev=0)
        self.withdraw()
        with self.assertRaises(QueueRevisionConflict):self.withdraw(op='withdraw-again',rev=2)
        self.assertEqual(self.queue.snapshot()['revision'],2)

    def test_same_proposal_name_does_not_overwrite_evidence(self):
        self.record();other=self.make_bundle(self.base,self.base_run,'SYNTHETIC-parent',q(5,100))
        with self.assertRaises(QueueRevisionConflict):self.record(other,'record-different',1)
        self.assertEqual(self.queue.snapshot()['entries'][0]['bundle_sha'],self.parent)

    def test_failed_commit_rolls_back_projection_revision_and_receipt(self):
        with patch.object(self.queue,'_commit',side_effect=RuntimeError('fault')):
            with self.assertRaises(RuntimeError):self.record()
        self.assertEqual(self.queue.snapshot()['revision'],0);self.assertEqual(self.queue.snapshot()['entries'],[]);self.assertEqual(self.queue.history(),())
        self.record();child=self.child()
        with patch.object(self.queue,'_commit',side_effect=RuntimeError('fault')):
            with self.assertRaises(RuntimeError):self.queue.supersede(self.archive,'SYNTHETIC-parent',child,operation_id='failed',expected_revision=1,actor_label='SYNTHETIC label',reason='fault')
        self.assertEqual(self.queue.snapshot()['revision'],1);self.assertEqual(len(self.queue.snapshot()['entries']),1);self.assertEqual(self.queue.snapshot()['entries'][0]['state'],'recorded')

    def test_missing_archive_evidence_blocks_record_and_verified_read(self):
        missing='0'*64
        with self.assertRaises(MissingEvidence):self.record(missing)
        self.assertEqual(self.queue.snapshot()['revision'],0)
        self.record();self.archive._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('bundle',self.parent))
        with self.assertRaises(MissingEvidence):self.queue.verify_entry(self.archive,'SYNTHETIC-parent')
        # Withdrawal records intent and does not need to pretend unavailable evidence was replayed.
        self.withdraw();self.assertEqual(self.queue.snapshot()['entries'][0]['state'],'withdrawn')

    def test_reopen_preserves_receipts_and_projection(self):
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'queue.sqlite3'
            with ProposalQueue(path)as queue:first=self.record(queue=queue)
            with ProposalQueue(path)as queue:
                self.assertEqual(queue.snapshot()['revision'],1);self.assertEqual(queue.history()[0],first)
                self.assertTrue(queue.verify_entry(self.archive,'SYNTHETIC-parent')['evidence_replayed'])

    def test_runtime_archive_database_is_not_accepted_as_queue(self):
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'archive.sqlite3'
            with EvidenceArchive(path):pass
            with self.assertRaises(QueueIntegrityError):ProposalQueue(path)

    def test_receipt_corruption_is_detected_on_read_and_retry(self):
        self.record();self.queue._connection.execute("UPDATE events SET payload_json='{}'")
        with self.assertRaises(QueueIntegrityError):self.queue.history()
        with self.assertRaises(QueueIntegrityError):self.record()

    def test_bad_revision_or_missing_operation_reason_is_rejected(self):
        for revision in [-1,True,'0']:
            with self.assertRaises(ValidationError):self.record(rev=revision)
        with self.assertRaises(ValidationError):self.queue.record(self.archive,self.parent,operation_id='x',expected_revision=0,actor_label='SYNTHETIC',reason='')
        self.assertEqual(self.queue.snapshot()['revision'],0)

    def test_two_concurrent_writers_cannot_commit_the_same_expected_revision(self):
        with tempfile.TemporaryDirectory()as t:
            archive_path=Path(t)/'archive.sqlite3';queue_path=Path(t)/'queue.sqlite3'
            with EvidenceArchive(archive_path)as archive:
                keys=[self.make_bundle(self.base,self.base_run,'SYNTHETIC-thread-'+str(i),q(7+i,100),archive)for i in range(2)]
            with ProposalQueue(queue_path):pass
            barrier=threading.Barrier(2)
            def worker(index):
                with EvidenceArchive(archive_path)as archive,ProposalQueue(queue_path)as queue:
                    barrier.wait(timeout=5)
                    try:self.record(keys[index],op='thread-'+str(index),queue=queue,archive=archive);return 'committed'
                    except QueueRevisionConflict:return 'conflict'
            with ThreadPoolExecutor(max_workers=2)as pool:outcomes=list(pool.map(worker,range(2)))
            self.assertCountEqual(outcomes,['committed','conflict'])
            with ProposalQueue(queue_path)as queue:self.assertEqual(queue.snapshot()['revision'],1);self.assertEqual(len(queue.history()),1)

    def test_projection_copies_do_not_change_persisted_queue(self):
        self.record();snap=self.queue.snapshot();snap['entries'][0]['state']='approved'
        self.assertEqual(self.queue.snapshot()['entries'][0]['state'],'recorded')

    def test_missing_parent_evidence_blocks_supersession_without_partial_changes(self):
        self.record();child=self.child()
        self.archive._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('bundle',self.parent))
        with self.assertRaises(MissingEvidence):self.queue.supersede(self.archive,'SYNTHETIC-parent',child,operation_id='missing-parent',expected_revision=1,actor_label='SYNTHETIC label',reason='Cannot verify prior proposal')
        self.assertEqual(self.queue.snapshot()['revision'],1);self.assertEqual(len(self.queue.snapshot()['entries']),1)
