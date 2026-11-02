"""Durable synthetic evidence recovery and integrity tests; no real-deal use."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from miniuw_foundation import DraftStore, RevisionConflict, ValidationError
from miniuw_foundation.archive import (EvidenceArchive, MissingEvidence, CorruptArchive,
    UnsupportedArchive, archive_and_import)
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic, observe_freshness
from miniuw_foundation.intake import SCHEMA
from test_foundation import seed, claim


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name)/'evidence.sqlite3')
        self.archive = EvidenceArchive(self.path)
        self.addCleanup(self.archive.close)
        self.store = DraftStore(':memory:')
        self.addCleanup(self.store.close)
        self.blank = self.store.create('draft',seed())
        self.slot = next(iter(self.blank.payload['input_claims']))
        self.raw = self.envelope()
        self.snapshot = archive_and_import(self.archive,self.store,'draft',
            expected_revision=0,operation_id='source',raw=self.raw).snapshot
        self.graph = Graph((Node(node_id='length',operation='text_length',
            definition_revision='synthetic-text-v1',dependencies=(),
            slots=(SlotRef(kind='input',slot_id=self.slot),)),))
        self.execution = execute_synthetic(self.snapshot,self.graph)

    def envelope(self, identity='source-claim', literal='abc', slot=None):
        record=claim(identity,literal,slot or self.slot).record()
        record={k:v for k,v in record.items() if k not in {'source_sha256','locator','claim_kind'}}
        return json.dumps({'schema':SCHEMA,'claims':[record]},ensure_ascii=False).encode()

    def save(self):
        return self.archive.save_execution(self.snapshot,self.graph,self.execution)

    def count(self,kind):
        return self.archive._connection.execute('SELECT COUNT(*) FROM objects WHERE kind=?',(kind,)).fetchone()[0]

    def rewrite_bundle(self,sha,mutator):
        payload=json.loads(self.archive.read_bundle_bytes(sha))
        mutator(payload)
        raw=canonical(payload).encode()
        with self.archive._transaction():return self.archive._put('bundle',raw)

    def test_sources_preserve_exact_bytes_and_distinguish_whitespace(self):
        sha=self.archive.put_source(self.raw)
        self.assertEqual(sha,hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.archive.get_source(sha),self.raw)
        other=self.archive.put_source(self.raw+b' ')
        self.assertNotEqual(sha,other)
        self.assertEqual(self.archive.get_source(other),self.raw+b' ')

    def test_duplicate_source_and_bundle_writes_are_idempotent(self):
        for _ in range(2):self.archive.put_source(self.raw)
        first=self.save()
        self.assertEqual(first,self.save())
        self.assertEqual(self.count('source'),1)
        self.assertEqual(self.count('bundle'),1)

    def test_reopen_recovers_source_snapshot_graph_and_execution(self):
        sha=self.save()
        with EvidenceArchive(self.path) as reopened:
            bundle=reopened.load_execution(sha)
            self.assertEqual(bundle.snapshot,self.snapshot)
            self.assertEqual(bundle.graph.sha256,self.graph.sha256)
            self.assertEqual(bundle.execution,self.execution)
            self.assertEqual(reopened.get_source(hashlib.sha256(self.raw).hexdigest()),self.raw)
            self.assertEqual(reopened._connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_copy_to_another_path_recovers_independent_archive(self):
        sha=self.save()
        target=str(Path(self.temp.name)/'restored.sqlite3')
        # SQLite backup obtains a consistent archive copy, not a VPS backup.
        with sqlite3.connect(target) as restored:self.archive._connection.backup(restored)
        with EvidenceArchive(target) as reopened:
            self.assertEqual(reopened.load_execution(sha).execution.sha256,self.execution.sha256)
            self.assertEqual(reopened.get_source(hashlib.sha256(self.raw).hexdigest()),self.raw)

    def test_advanced_draft_does_not_overwrite_old_evidence(self):
        sha=self.save()
        newer=archive_and_import(self.archive,self.store,'draft',expected_revision=1,
            operation_id='later-source',raw=self.envelope('second','abc')).snapshot
        old=self.archive.load_execution(sha)
        self.assertEqual(old.snapshot.revision,1)
        self.assertEqual(old.execution,self.execution)
        report=observe_freshness(old.execution,newer,old.graph)
        self.assertFalse(report['entire_run_current'])
        self.assertEqual(report['affected_nodes'],['length'])

    def test_missing_source_blocks_capture_without_partial_bundle(self):
        other=DraftStore(':memory:')
        self.addCleanup(other.close)
        other.create('other',seed())
        snapshot=other.append('other',expected_revision=0,operation_id='declared-only',
            claims=[claim('declared','abc',self.slot)]).snapshot
        with self.assertRaises(MissingEvidence):self.archive.save_execution(snapshot,self.graph,execute_synthetic(snapshot,self.graph))
        self.assertEqual(self.count('bundle'),0)

    def test_source_locator_and_literal_must_match_actual_bytes(self):
        for field,value in [('locator','/claims/99/literal'),('literal','forged')]:
            payload=self.snapshot.payload
            payload['input_claims'][self.slot][0][field]=value
            encoded=canonical(payload)
            snapshot=replace(self.snapshot,payload_json=encoded,sha256=digest(encoded))
            execution=execute_synthetic(snapshot,self.graph)
            with self.assertRaises(CorruptArchive):self.archive.save_execution(snapshot,self.graph,execution)
        self.assertEqual(self.count('bundle'),0)

    def test_forged_result_with_correct_hash_cannot_be_captured(self):
        payload=self.execution.payload
        payload['results']['length']['value']=999
        encoded=canonical(payload)
        forged=replace(self.execution,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):self.archive.save_execution(self.snapshot,self.graph,forged)
        self.assertEqual(self.count('bundle'),0)

    def test_source_corruption_detected_without_repair_or_overwrite(self):
        sha=hashlib.sha256(self.raw).hexdigest()
        self.archive._connection.execute("UPDATE objects SET payload=? WHERE kind='source' AND sha256=?",(b'corrupt',sha))
        with self.assertRaises(CorruptArchive):self.archive.get_source(sha)
        with self.assertRaises(CorruptArchive):self.archive.put_source(self.raw)
        with self.assertRaises(CorruptArchive):self.save()
        self.assertEqual(self.count('bundle'),0)

    def test_bundle_corruption_detected(self):
        sha=self.save()
        self.archive._connection.execute("UPDATE objects SET payload=? WHERE kind='bundle' AND sha256=?",(b'corrupt',sha))
        with self.assertRaises(CorruptArchive):self.archive.load_execution(sha)

    def test_missing_archived_dependency_blocks_recovery(self):
        sha=self.save()
        self.archive._connection.execute("DELETE FROM objects WHERE kind='source'")
        with self.assertRaises(MissingEvidence):self.archive.load_execution(sha)

    def test_recovery_reexecutes_instead_of_trusting_result_hash(self):
        sha=self.save()
        def forge(payload):
            execution=json.loads(payload['execution']['payload_json'])
            execution['results']['length']['value']=123
            encoded=canonical(execution)
            payload['execution']={'payload_json':encoded,'sha256':digest(encoded)}
        forged=self.rewrite_bundle(sha,forge)
        with self.assertRaises(CorruptArchive):self.archive.load_execution(forged)

    def test_engine_mismatch_requires_original_engine_but_bytes_are_retrievable(self):
        sha=self.save()
        altered=self.rewrite_bundle(sha,lambda p:p['graph'].update(engine_sha256='0'*64))
        with self.assertRaises(UnsupportedArchive):self.archive.load_execution(altered)
        self.assertEqual(hashlib.sha256(self.archive.read_bundle_bytes(altered)).hexdigest(),altered)

    def test_changed_graph_or_source_inventory_rejected(self):
        sha=self.save()
        for mutator in [lambda p:p['graph'].update(sha256='0'*64),lambda p:p.update(source_hashes=[])]:
            altered=self.rewrite_bundle(sha,mutator)
            with self.assertRaises(CorruptArchive):self.archive.load_execution(altered)

    def test_commit_failure_rolls_back_bundle_and_source_write(self):
        with patch.object(self.archive,'_commit',side_effect=RuntimeError('pre-commit fault')):
            with self.assertRaises(RuntimeError):self.save()
        self.assertEqual(self.count('bundle'),0)
        self.assertEqual(self.archive.load_execution(self.save()).execution,self.execution)
        extra=self.envelope('extra')
        with patch.object(self.archive,'_commit',side_effect=RuntimeError('pre-commit fault')):
            with self.assertRaises(RuntimeError):self.archive.put_source(extra)
        with self.assertRaises(MissingEvidence):self.archive.get_source(hashlib.sha256(extra).hexdigest())

    def test_concurrent_identical_source_writers_preserve_one_object(self):
        raw=self.envelope('concurrent')
        barrier=threading.Barrier(2)
        def writer(_):
            with EvidenceArchive(self.path) as archive:
                barrier.wait(timeout=5)
                return archive.put_source(raw)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(writer,[1,2]))
        self.assertEqual(results,[hashlib.sha256(raw).hexdigest()]*2)
        self.assertEqual(self.count('source'),2)

    def test_draft_failure_leaves_recoverable_source_without_false_draft_success(self):
        raw=self.envelope('orphan')
        with self.assertRaises(RevisionConflict):archive_and_import(self.archive,self.store,'draft',expected_revision=0,operation_id='stale',raw=raw)
        self.assertEqual(self.archive.get_source(hashlib.sha256(raw).hexdigest()),raw)
        self.assertEqual(self.store.get('draft').revision,1)
        self.assertEqual(self.count('bundle'),0)

    def test_archived_import_retry_preserves_source_and_draft_identity(self):
        retry=archive_and_import(self.archive,self.store,'draft',expected_revision=0,operation_id='source',raw=self.raw)
        self.assertTrue(retry.replayed)
        self.assertEqual(retry.snapshot,self.snapshot)
        self.assertEqual(self.count('source'),1)

    def test_empty_pending_execution_can_be_archived_without_invented_sources(self):
        execution=execute_synthetic(self.blank,self.graph)
        sha=self.archive.save_execution(self.blank,self.graph,execution)
        bundle=self.archive.load_execution(sha)
        self.assertEqual(bundle.payload['source_hashes'],[])
        self.assertEqual(bundle.execution.payload['results']['length']['state'],'blocked')
        self.assertEqual(bundle.execution.payload['decision'],'PENDING')

    def test_invalid_source_or_hash_does_not_enter_archive(self):
        for raw in [b'{}',b'not JSON',b'{"schema":"real-data","claims":[]}']:
            with self.assertRaises(ValidationError):self.archive.put_source(raw)
        for sha in ['../path',None,'0'*63]:
            with self.assertRaises(ValidationError):self.archive.get_source(sha)
        self.assertEqual(self.count('source'),1)

    def test_unrelated_newer_and_draft_databases_rejected_without_changes(self):
        for name,sql in [('unrelated','CREATE TABLE important(value TEXT)'),('newer','PRAGMA user_version=99')]:
            path=str(Path(self.temp.name)/(name+'.sqlite3'))
            with sqlite3.connect(path) as connection:connection.execute(sql)
            before=Path(path).read_bytes()
            with self.assertRaises(UnsupportedArchive):EvidenceArchive(path)
            self.assertEqual(Path(path).read_bytes(),before)
        draft_path=str(Path(self.temp.name)/'draft.sqlite3')
        with DraftStore(draft_path) as store:store.create('d',seed())
        before=Path(draft_path).read_bytes()
        with self.assertRaises(UnsupportedArchive):EvidenceArchive(draft_path)
        self.assertEqual(Path(draft_path).read_bytes(),before)

    def test_returned_bundle_copy_cannot_change_stored_execution_or_guards(self):
        sha=self.save()
        bundle=self.archive.load_execution(sha)
        payload=bundle.payload
        payload['execution']['payload_json']='{}'
        restored=self.archive.load_execution(sha)
        self.assertEqual(restored.execution,self.execution)
        self.assertEqual(restored.execution.payload['decision'],'PENDING')
        self.assertFalse(restored.execution.payload['run_ready'])
        self.assertFalse(restored.execution.payload['production_authorized'])

if __name__=='__main__':unittest.main()
