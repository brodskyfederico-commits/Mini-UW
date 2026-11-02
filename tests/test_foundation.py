"""Behavioral tests for synthetic draft persistence; no financial approval tests."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from miniuw_foundation import (ContextSeed, RawClaim, DraftStore, ValidationError,
    AlreadyExists, NotFound, RevisionConflict, IdempotencyConflict,
    CorruptSnapshot, UnsupportedDatabase)


def seed():
    return ContextSeed(deal_id='SYNTHETIC-test', scenario_id='scenario-test',
        run_id='run-test', definition_set_revision='unadopted-test')


def claim(identity='c1', literal='0', slot=None, kind='input', **kwargs):
    values = dict(claim_id=identity, slot_kind=kind, slot_id=slot,
        literal=literal, unit_literal=None, currency_literal=None,
        period_literal=None, source_sha256='a'*64, locator='fixture:row:1',
        definition_ref=None)
    values.update(kwargs)
    return RawClaim(**values)


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name)/'draft.sqlite3')
        self.store = DraftStore(self.path)
        self.addCleanup(self.store.close)
        self.initial = self.store.create('draft', seed())
        self.slot = next(iter(self.initial.payload['input_claims']))
        self.criterion = next(iter(self.initial.payload['criterion_claims']))

    def append(self, claims=None, rev=0, op='op1'):
        return self.store.append('draft', expected_revision=rev,
            operation_id=op, claims=claims or [claim(slot=self.slot)])

    def test_fresh_template_matches_original_and_all_slots_empty(self):
        bundled = Path(__import__('miniuw_foundation').__file__).parent/'data/project-draft-empty.json'
        original = Path(__file__).resolve().parents[1]/'templates/project-draft-empty.json'
        self.assertEqual(bundled.read_bytes(), original.read_bytes())
        payload = self.initial.payload
        self.assertEqual(len(payload['input_claims']),55)
        self.assertEqual(len(payload['criterion_claims']),10)
        self.assertTrue(all(v == [] for f in ['input_claims','criterion_claims'] for v in payload[f].values()))
        self.assertEqual(payload['source_template_sha256'],hashlib.sha256(original.read_bytes()).hexdigest())

    def test_new_draft_never_inherits_criteria(self):
        self.append([claim(slot=self.criterion, kind='criterion', literal='5%')])
        other = self.store.create('other', seed())
        self.assertTrue(all(v == [] for v in other.payload['criterion_claims'].values()))

    def test_zero_and_blank_are_preserved_separately(self):
        result = self.append([claim('zero','0',self.slot),claim('null',None,self.slot),claim('empty','',self.slot)])
        slot = result.snapshot.slot('input',self.slot)
        self.assertEqual([c['literal'] for c in slot['claims']],['0',None,''])
        self.assertEqual(slot['state'],'unverified_claims')
        self.assertTrue(slot['has_blank_claims'])
        self.assertFalse(slot['financially_normalized'])

    def test_blank_only_is_missing(self):
        result = self.append([claim('blank','  ',self.slot)])
        self.assertEqual(result.snapshot.slot('input',self.slot)['state'],'missing')

    def test_conflicts_keep_all_claims_without_percent_conversion(self):
        result = self.append([claim('a','5%',self.slot),claim('b','0.05',self.slot)])
        self.assertEqual(result.snapshot.slot('input',self.slot)['state'],'conflicting_claims')
        self.assertEqual(len(result.snapshot.slot('input',self.slot)['claims']),2)

    def test_units_periods_and_currency_are_not_silently_equated(self):
        result = self.append([claim('a','5',self.slot,currency_literal='USD',period_literal='year'),
                              claim('b','5',self.slot,currency_literal='EUR',period_literal='month')])
        self.assertEqual(result.snapshot.slot('input',self.slot)['state'],'conflicting_claims')

    def test_repeated_matching_claims_are_unverified(self):
        result = self.append([claim('a','TBD',self.slot),claim('b','TBD',self.slot)])
        self.assertEqual(result.snapshot.slot('input',self.slot)['state'],'unverified_claims')

    def test_snapshot_copy_cannot_mutate_store_and_history_is_immutable(self):
        copy = self.initial.payload
        copy['decision']='PASS'
        self.append()
        self.assertEqual(self.initial.payload['revision'],0)
        self.assertEqual(self.store.get('draft',0).sha256,self.initial.sha256)
        self.assertEqual(self.store.get('draft').payload['context']['input_revision'],'draft@1')
        self.assertEqual(self.store.get('draft').decision,'PENDING')

    def test_source_literal_provenance_and_sql_text_are_preserved(self):
        literal="'); DROP TABLE drafts; -- ñ"
        snap = self.append([claim(slot=self.slot,literal=literal)]).snapshot
        record = snap.slot('input',self.slot)['claims'][0]
        self.assertEqual(record['literal'],literal)
        self.assertEqual(record['source_sha256'],'a'*64)
        self.assertEqual(record['locator'],'fixture:row:1')
        self.assertEqual(self.store.get('draft').revision,1)

    def test_bad_context_and_raw_types_rejected(self):
        with self.assertRaises(ValidationError):
            ContextSeed(deal_id='real-deal',scenario_id='s',run_id='r',definition_set_revision='d')
        for kwargs in [dict(literal=1.5),dict(source_sha256='not-a-hash'),dict(locator='')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                claim(slot=self.slot,**kwargs)
        with self.assertRaises(ValidationError):
            self.store.create('x',{})

    def test_unknown_slot_and_duplicate_claim_batch_are_atomic(self):
        for claims in [[claim('a','0',self.slot),claim('b','0','unknown')],
                       [claim('a','0',self.slot),claim('a','1',self.slot)]]:
            with self.assertRaises(ValidationError):self.append(claims)
            self.assertEqual(self.store.get('draft').revision,0)
        self.assertEqual(self.append().snapshot.revision,1)

    def test_claim_identity_cannot_be_reused_under_new_operation(self):
        self.append()
        with self.assertRaises(ValidationError):self.append(rev=1,op='op2')
        self.assertEqual(self.store.get('draft').revision,1)

    def test_exact_retry_is_idempotent(self):
        first = self.append()
        retry = self.append()
        self.assertFalse(first.replayed)
        self.assertTrue(retry.replayed)
        self.assertEqual(retry.snapshot.sha256,first.snapshot.sha256)
        self.assertEqual(self.store.get('draft').revision,1)

    def test_historical_retry_reports_observed_current_head(self):
        first = self.append()
        self.append([claim('second','2',self.slot)],rev=1,op='op2')
        retry = self.append()
        self.assertEqual(retry.snapshot.revision,first.snapshot.revision)
        self.assertEqual(retry.current_revision_observed,2)
        self.assertEqual(self.store.get('draft').revision,2)

    def test_reused_operation_with_different_request_rejected(self):
        self.append()
        with self.assertRaises(IdempotencyConflict):self.append([claim('other','2',self.slot)])
        self.assertEqual(self.store.get('draft').revision,1)

    def test_stale_revision_rejected(self):
        self.append()
        with self.assertRaises(RevisionConflict):self.append([claim('other','2',self.slot)],op='op2')
        self.assertEqual(self.store.get('draft').revision,1)

    def test_commit_failure_rolls_back_head_claims_and_retry_identity(self):
        with patch.object(self.store,'_commit',side_effect=RuntimeError('injected pre-commit failure')):
            with self.assertRaises(RuntimeError):self.append()
        self.assertEqual(self.store.get('draft').revision,0)
        self.assertEqual(self.store._connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0],0)
        self.assertEqual(self.store._connection.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],1)
        self.assertFalse(self.append().replayed)

    def test_two_connections_cannot_overwrite_same_revision(self):
        barrier = threading.Barrier(2)
        def writer(identity):
            with DraftStore(self.path) as store:
                barrier.wait(timeout=5)
                try:
                    store.append('draft',expected_revision=0,operation_id=identity,
                        claims=[claim(identity,'1',self.slot)])
                    return 'written'
                except RevisionConflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(writer,['thread-a','thread-b']))
        self.assertCountEqual(results,['written','conflict'])
        self.assertEqual(self.store.get('draft').revision,1)
        self.assertEqual(len(self.store.get('draft').slot('input',self.slot)['claims']),1)

    def test_reopen_restores_snapshot_and_database_integrity(self):
        expected = self.append().snapshot
        with DraftStore(self.path) as reopened:
            self.assertEqual(reopened.get('draft').sha256,expected.sha256)
            self.assertEqual(reopened._connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_snapshot_corruption_is_detected(self):
        self.store._connection.execute("UPDATE revisions SET payload='{}' WHERE revision=0")
        with self.assertRaises(CorruptSnapshot):self.store.get('draft')

    def test_unrelated_and_future_database_rejected_without_rewrite(self):
        for name,sql in [('unrelated','CREATE TABLE important(value TEXT)'),('future','PRAGMA user_version=99')]:
            path = str(Path(self.temp.name)/(name+'.sqlite3'))
            with sqlite3.connect(path) as connection:connection.execute(sql)
            before = Path(path).read_bytes()
            with self.assertRaises(UnsupportedDatabase):DraftStore(path)
            self.assertEqual(Path(path).read_bytes(),before)

    def test_identity_and_command_validation(self):
        with self.assertRaises(AlreadyExists):self.store.create('draft',seed())
        with self.assertRaises(NotFound):self.store.get('missing')
        for rev in [True,-1,None]:
            with self.assertRaises(ValidationError):self.append(rev=rev)
        for op in ['',None]:
            with self.assertRaises(ValidationError):self.append(op=op)

    def test_every_persisted_revision_stays_pending_and_unauthorized(self):
        self.append()
        for revision in [0,1]:
            payload=self.store.get('draft',revision).payload
            self.assertEqual(payload['decision'],'PENDING')
            self.assertFalse(payload['run_ready'])
            self.assertEqual(payload['authorization'],'not_granted')
            self.assertIn('financial_engine_not_implemented',payload['blockers'])

if __name__=='__main__':unittest.main()
