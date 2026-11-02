"""T04 synthetic sheet and JSON/CSV evidence interoperability."""
import csv
import hashlib
import io
import json
import unittest

from miniuw_foundation import DraftStore, ValidationError, IdempotencyConflict
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic
from miniuw_foundation.intake import SCHEMA as JSON_SCHEMA
from miniuw_foundation.sheets import SCHEMA, COLUMNS, MAX_FIELD_CHARS, parse_synthetic_sheet
from miniuw_foundation.sources import parse_source_claims, import_synthetic_source
from test_foundation import seed, claim


def sheet(records, *, marker=SCHEMA, columns=COLUMNS, newline='\r\n'):
    output=io.StringIO(newline='')
    writer=csv.writer(output,lineterminator=newline)
    writer.writerow([marker])
    writer.writerow(columns)
    writer.writerows(records)
    return output.getvalue().encode('utf-8')


class SheetTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:')
        self.addCleanup(self.store.close)
        self.archive=EvidenceArchive(':memory:')
        self.addCleanup(self.archive.close)
        self.initial=self.store.create('draft',seed())
        self.slot=next(iter(self.initial.payload['input_claims']))
        self.criterion=next(iter(self.initial.payload['criterion_claims']))

    def row(self,identity='row1',literal='abc',slot=None,kind='input'):
        return [identity,kind,slot or self.slot,literal,'\\N','\\N','\\N','\\N']

    def ingest(self,raw,rev=0,op='sheet'):
        return archive_and_import(self.archive,self.store,'draft',expected_revision=rev,
            operation_id=op,raw=raw)

    def test_exact_bytes_hash_and_logical_record_column_locator(self):
        raw=sheet([self.row()])
        result=self.ingest(raw)
        record=result.snapshot.slot('input',self.slot)['claims'][0]
        self.assertEqual(record['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(record['locator'],'csv:record:3:column:D')
        self.assertEqual(self.archive.get_source(hashlib.sha256(raw).hexdigest()),raw)

    def test_zero_empty_and_null_are_distinct_and_preserved(self):
        result=self.ingest(sheet([self.row('zero','0'),self.row('empty',''),self.row('null','\\N')]))
        records=result.snapshot.slot('input',self.slot)['claims']
        self.assertEqual([r['literal'] for r in records],['0','',None])
        self.assertEqual(result.snapshot.slot('input',self.slot)['state'],'unverified_claims')
        self.assertTrue(result.snapshot.slot('input',self.slot)['has_blank_claims'])

    def test_quoted_commas_newlines_quotes_and_unicode_preserved(self):
        literal='texto, "citado"\nsegunda línea ñ'
        raw=sheet([self.row('first',literal),self.row('second',literal)])
        claims=parse_synthetic_sheet(raw)
        self.assertEqual(claims[0].literal,literal)
        self.assertEqual(claims[0].locator,'csv:record:3:column:D')
        self.assertEqual(claims[1].locator,'csv:record:4:column:D')
        self.ingest(raw)

    def test_formula_text_not_evaluated(self):
        for literal in ['=1+1','+SUM(A1:A2)','@function','-1']:
            self.assertEqual(parse_synthetic_sheet(sheet([self.row(literal=literal)]))[0].literal,literal)

    def test_no_numeric_percent_currency_date_or_space_normalization(self):
        row=self.row(literal=' 001,25% ')
        row[4:]=['percentage literal','USD','2026-01-01 / 2027-01-01','explicit-fixture-only']
        record=parse_synthetic_sheet(sheet([row]))[0]
        self.assertEqual(record.literal,' 001,25% ')
        self.assertEqual(record.unit_literal,'percentage literal')
        self.assertEqual(record.currency_literal,'USD')
        self.assertEqual(record.period_literal,'2026-01-01 / 2027-01-01')

    def test_escaped_null_token_and_backslashes_remain_literal(self):
        for encoded,expected in [('\\\\N','\\N'),('\\\\path','\\path'),('\\\\','\\')]:
            with self.subTest(encoded=encoded):
                self.assertEqual(parse_synthetic_sheet(sheet([self.row(literal=encoded)]))[0].literal,expected)
        with self.assertRaises(ValidationError):parse_synthetic_sheet(sheet([self.row(literal='\\unknown')]))

    def test_metadata_empty_strings_are_not_defaulted_to_null(self):
        row=self.row()
        row[4:]=['','','','']
        record=parse_synthetic_sheet(sheet([row]))[0]
        self.assertEqual(record.unit_literal,'')
        self.assertEqual(record.currency_literal,'')
        self.assertEqual(record.period_literal,'')
        self.assertEqual(record.definition_ref,'')

    def test_schema_marker_required_without_dialect_guessing(self):
        for marker in ['','Inputs','real-data']:
            with self.assertRaises(ValidationError):self.ingest(sheet([self.row()],marker=marker))
        raw=sheet([self.row()]).replace(b',',b';')
        with self.assertRaises(ValidationError):self.ingest(raw)
        self.assertEqual(self.store.get('draft').revision,0)

    def test_reordered_missing_extra_or_duplicate_headers_rejected(self):
        for columns in [tuple(reversed(COLUMNS)),COLUMNS[:-1],COLUMNS+('extra',),COLUMNS[:-1]+('literal',)]:
            with self.subTest(columns=columns),self.assertRaises(ValidationError):self.ingest(sheet([self.row()],columns=columns))
        self.assertEqual(self.store.get('draft').revision,0)

    def test_missing_extra_and_blank_rows_reject_entire_source(self):
        for invalid in [self.row()[:-1],self.row()+['extra'],[]]:
            with self.subTest(invalid=invalid),self.assertRaises(ValidationError):self.ingest(sheet([self.row('first'),invalid]))
        self.assertEqual(self.store.get('draft').revision,0)

    def test_invalid_utf8_bom_and_broken_quotes_rejected(self):
        for raw in [b'\xff',b'\xef\xbb\xbf'+sheet([self.row()]),sheet([])+b'"unterminated']:
            with self.assertRaises(ValidationError):parse_synthetic_sheet(raw)

    def test_empty_sheet_rejected(self):
        with self.assertRaises(ValidationError):parse_synthetic_sheet(sheet([]))
        for raw in [b'',None,'text',b' '*(1_048_576+1)]:
            with self.assertRaises(ValidationError):parse_source_claims(raw)

    def test_technical_field_bound_enforced_without_financial_limit(self):
        with self.assertRaises(ValidationError):parse_synthetic_sheet(sheet([self.row(literal='a'*(MAX_FIELD_CHARS+1))]))

    def test_duplicate_claim_id_rejects_atomic_draft_import(self):
        with self.assertRaises(ValidationError):self.ingest(sheet([self.row(),self.row()]))
        self.assertEqual(self.store.get('draft').sha256,self.initial.sha256)

    def test_unknown_slot_rejects_whole_batch_and_preserves_source(self):
        raw=sheet([self.row('valid'),self.row('unknown',slot='unknown')])
        with self.assertRaises(ValidationError):self.ingest(raw)
        self.assertEqual(self.store.get('draft').revision,0)
        self.assertEqual(self.archive.get_source(hashlib.sha256(raw).hexdigest()),raw)

    def test_conflicting_rows_retained_without_last_row_winner(self):
        result=self.ingest(sheet([self.row('first','1'),self.row('second','2')]))
        slot=result.snapshot.slot('input',self.slot)
        self.assertEqual(slot['state'],'conflicting_claims')
        self.assertEqual([r['literal'] for r in slot['claims']],['1','2'])
        self.assertEqual(result.snapshot.decision,'PENDING')

    def test_exact_sheet_retry_idempotent_and_changed_bytes_rejected(self):
        raw=sheet([self.row()])
        first=self.ingest(raw)
        retry=self.ingest(raw)
        self.assertTrue(retry.replayed)
        self.assertEqual(first.snapshot,retry.snapshot)
        with self.assertRaises(IdempotencyConflict):self.ingest(sheet([self.row()],newline='\n'))
        self.assertEqual(self.store.get('draft').revision,1)

    def test_criteria_remain_unadopted_and_new_deals_start_empty(self):
        snapshot=self.ingest(sheet([self.row(literal='5%',slot=self.criterion,kind='criterion')])).snapshot
        self.assertEqual(snapshot.slot('criterion',self.criterion)['state'],'unverified_claims')
        self.assertEqual(snapshot.decision,'PENDING')
        fresh=self.store.create('new',seed())
        self.assertTrue(all(not v for v in fresh.payload['criterion_claims'].values()))

    def test_csv_execution_bundle_recovery_verifies_cell_and_bytes(self):
        raw=sheet([self.row()])
        snapshot=self.ingest(raw).snapshot
        graph=Graph((Node(node_id='length',operation='text_length',definition_revision='fixture-v1',
            dependencies=(),slots=(SlotRef(kind='input',slot_id=self.slot),)),))
        execution=execute_synthetic(snapshot,graph)
        sha=self.archive.save_execution(snapshot,graph,execution)
        restored=self.archive.load_execution(sha)
        self.assertEqual(restored.execution,execution)
        self.assertEqual(restored.execution.payload['results']['length']['value'],3)
        self.assertEqual(restored.snapshot.slot('input',self.slot)['claims'][0]['locator'],'csv:record:3:column:D')
        self.assertFalse(restored.execution.payload['production_authorized'])

    def test_mixed_json_csv_sources_recover_in_one_snapshot(self):
        first=self.ingest(sheet([self.row()])).snapshot
        record=claim('json','abc',self.slot).record()
        record={k:v for k,v in record.items() if k not in {'source_sha256','locator','claim_kind'}}
        raw=json.dumps({'schema':JSON_SCHEMA,'claims':[record]}).encode()
        snapshot=self.ingest(raw,rev=first.revision,op='json').snapshot
        graph=Graph((Node(node_id='echo',operation='literal_echo',definition_revision='fixture-v1',
            dependencies=(),slots=(SlotRef(kind='input',slot_id=self.slot),)),))
        execution=execute_synthetic(snapshot,graph)
        restored=self.archive.load_execution(self.archive.save_execution(snapshot,graph,execution))
        self.assertEqual(len(restored.payload['source_hashes']),2)
        self.assertEqual(restored.execution,execution)
        self.assertEqual([r['locator'] for r in restored.snapshot.slot('input',self.slot)['claims']],
            ['csv:record:3:column:D','/claims/0/literal'])

    def test_direct_import_uses_same_parser_without_archive(self):
        raw=sheet([self.row()])
        result=import_synthetic_source(self.store,'draft',expected_revision=0,operation_id='direct',raw=raw)
        self.assertEqual(result.snapshot.slot('input',self.slot)['claims'][0]['literal'],'abc')
        self.assertEqual(parse_source_claims(raw),parse_synthetic_sheet(raw))

    def test_null_identity_and_unknown_kind_rejected(self):
        for column,value in [(0,'\\N'),(1,'unknown'),(2,'\\N')]:
            row=self.row()
            row[column]=value
            with self.assertRaises(ValidationError):parse_synthetic_sheet(sheet([row]))

if __name__=='__main__':unittest.main()
