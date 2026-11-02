import hashlib
import json
import unittest
from miniuw_foundation import DraftStore, ValidationError, IdempotencyConflict
from miniuw_foundation.intake import SCHEMA, MAX_BYTES, import_synthetic_claims, parse_synthetic_claims
from test_foundation import seed, claim


class SyntheticIntakeTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:')
        self.addCleanup(self.store.close)
        self.initial=self.store.create('draft',seed())
        self.slot=next(iter(self.initial.payload['input_claims']))
        record=claim(slot=self.slot,literal='=SUM(A1:A2)').record()
        self.record={k:v for k,v in record.items() if k not in {'source_sha256','locator','claim_kind'}}

    def raw(self,records=None):
        return json.dumps({'schema':SCHEMA,'claims':records or [self.record]},ensure_ascii=False).encode()

    def ingest(self,raw):
        return import_synthetic_claims(self.store,'draft',expected_revision=0,operation_id='file-1',raw=raw)

    def test_actual_source_hash_pointer_and_formula_literal(self):
        raw=self.raw()
        result=self.ingest(raw)
        record=result.snapshot.slot('input',self.slot)['claims'][0]
        self.assertEqual(record['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(record['locator'],'/claims/0/literal')
        self.assertEqual(record['literal'],'=SUM(A1:A2)')
        self.assertEqual(result.snapshot.decision,'PENDING')

    def test_same_bytes_retry_once_and_different_bytes_same_operation_rejected(self):
        raw=self.raw()
        self.ingest(raw)
        self.assertTrue(self.ingest(raw).replayed)
        with self.assertRaises(IdempotencyConflict):self.ingest(raw+b' ')
        self.assertEqual(self.store.get('draft').revision,1)

    def test_duplicate_json_keys_rejected_at_any_level(self):
        for raw in [b'{"schema":"a","schema":"b","claims":[]}',
                    self.raw().replace(b'"literal":',b'"literal": "override", "literal":')]:
            with self.subTest(raw=raw),self.assertRaises(ValidationError):self.ingest(raw)
        self.assertEqual(self.store.get('draft').revision,0)

    def test_invalid_encoding_size_and_nonstandard_numbers_rejected(self):
        for raw in [b'\xff',b'{',b'',b' '*(MAX_BYTES+1),b'{"schema":NaN,"claims":[]}', 'text']:
            with self.subTest(kind=type(raw)),self.assertRaises(ValidationError):parse_synthetic_claims(raw)

    def test_supplied_provenance_or_release_flags_cannot_override_envelope(self):
        for record in [dict(self.record,source_sha256='b'*64),dict(self.record,decision='PASS')]:
            with self.assertRaises(ValidationError):self.ingest(self.raw([record]))
        envelope={'schema':SCHEMA,'claims':[self.record],'run_ready':True}
        with self.assertRaises(ValidationError):self.ingest(json.dumps(envelope).encode())
        self.assertEqual(self.store.get('draft').revision,0)

    def test_no_numeric_coercion_and_no_defaults_for_missing_fields(self):
        for record in [dict(self.record,literal=0),{k:v for k,v in self.record.items() if k!='period_literal'}]:
            with self.assertRaises(ValidationError):self.ingest(self.raw([record]))
        self.assertEqual(self.store.get('draft').revision,0)

    def test_whole_batch_rejected_if_later_slot_unknown(self):
        second=dict(self.record,claim_id='second',slot_id='unknown')
        with self.assertRaises(ValidationError):self.ingest(self.raw([self.record,second]))
        self.assertEqual(self.store.get('draft').sha256,self.initial.sha256)

    def test_unmarked_wrong_schema_and_empty_claims_rejected(self):
        for envelope in [{}, {'schema':'real-data','claims':[self.record]}, {'schema':SCHEMA,'claims':[]}]:
            with self.assertRaises(ValidationError):self.ingest(json.dumps(envelope).encode())

if __name__=='__main__':unittest.main()
