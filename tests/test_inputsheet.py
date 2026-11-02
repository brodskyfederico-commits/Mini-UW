import hashlib
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from miniuw_foundation import DraftStore, ValidationError, IdempotencyConflict
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic
from miniuw_foundation.inputsheet import layout, inspect_synthetic_input_sheet, parse_synthetic_input_sheet
from miniuw_foundation.sources import parse_source_claims
from test_foundation import seed
from inputsheet_fixture import native_workbook, ORIGINAL, M


class InputSheetTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:');self.addCleanup(self.store.close)
        self.archive=EvidenceArchive(':memory:');self.addCleanup(self.archive.close)
        self.blank=self.store.create('draft',seed())

    def ingest(self,raw,revision=0,operation='native'):
        return archive_and_import(self.archive,self.store,'draft',expected_revision=revision,
            operation_id=operation,raw=raw)

    def graph(self,field='INPUT_C8'):
        return Graph((Node(node_id='echo',operation='literal_echo',definition_revision='fixture-v1',
            dependencies=(),slots=(SlotRef(kind='input',slot_id=field),)),))

    def test_all_55_fields_map_to_original_exact_coordinates(self):
        claims=parse_synthetic_input_sheet(native_workbook())
        self.assertEqual(len(claims),55)
        self.assertEqual({c.slot_id for c in claims},set(self.blank.payload['input_claims']))
        for c in claims:
            self.assertEqual(c.locator,'xlsx:sheet:Inputs:cell:'+c.slot_id.split('_')[1])
            self.assertIsNone(c.literal)

    def test_unmarked_original_and_unmarked_copy_are_not_imported(self):
        for raw in [ORIGINAL.read_bytes(),native_workbook(marker=False)]:
            with self.assertRaises(ValidationError):parse_source_claims(raw)
        self.assertEqual(self.store.get('draft').revision,0)

    def test_original_source_is_unchanged_and_layout_derived_from_its_hash(self):
        before=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
        native_workbook({'C8':{'value':'0'}})
        self.assertEqual(before,layout()['source_sha256'])
        self.assertEqual(before,hashlib.sha256(ORIGINAL.read_bytes()).hexdigest())

    def test_explicit_zero_and_decimal_lexemes_preserved_without_units_inference(self):
        raw=native_workbook({'C8':{'value':'0'},'C51':{'value':'0.6500'}})
        snapshot=self.ingest(raw).snapshot
        c8=snapshot.slot('input','INPUT_C8')['claims'][0]
        c51=snapshot.slot('input','INPUT_C51')['claims'][0]
        self.assertEqual(c8['literal'],'0');self.assertEqual(c8['unit_literal'],'$')
        self.assertIsNone(c8['currency_literal']);self.assertIsNone(c8['period_literal'])
        self.assertEqual(c51['literal'],'0.6500');self.assertEqual(c51['unit_literal'],'decimal')

    def test_blank_missing_and_empty_text_have_distinct_evidence(self):
        raw=native_workbook({'C8':'missing','C9':{'text':''}})
        inspection=inspect_synthetic_input_sheet(raw).cells
        self.assertEqual(inspection['C8']['kind'],'missing')
        self.assertEqual(inspection['C9']['kind'],'text')
        self.assertEqual(inspection['C10']['kind'],'blank')
        claims={c.slot_id:c for c in parse_synthetic_input_sheet(raw)}
        self.assertIsNone(claims['INPUT_C8'].literal)
        self.assertEqual(claims['INPUT_C9'].literal,'')
        self.assertIsNone(claims['INPUT_C10'].literal)

    def test_formula_cache_and_excel_error_do_not_become_values(self):
        raw=native_workbook({'C8':{'formula':'2+2','value':'4'},'C9':{'type':'e','value':'#VALUE!'}})
        snapshot=self.ingest(raw).snapshot
        self.assertIsNone(snapshot.slot('input','INPUT_C8')['claims'][0]['literal'])
        self.assertIsNone(snapshot.slot('input','INPUT_C9')['claims'][0]['literal'])
        self.assertEqual(inspect_synthetic_input_sheet(raw).cells['C8']['cached_value'],'4')
        self.assertEqual(execute_synthetic(snapshot,self.graph()).payload['results']['echo']['state'],'blocked')

    def test_label_unit_requirement_and_notes_changes_block_entire_batch(self):
        for ref in ['A8','B8','D8','E8']:
            with self.subTest(ref=ref),self.assertRaises(ValidationError):
                self.ingest(native_workbook({ref:{'text':'changed'}}))
        self.assertEqual(self.store.get('draft').sha256,self.blank.sha256)

    def test_value_moved_to_other_column_and_unknown_rows_rejected(self):
        for values in [{'G8':{'value':'1'}},{'C83':{'value':'1'}}]:
            with self.assertRaises(ValidationError):parse_source_claims(native_workbook(values))

    def test_new_merged_region_or_duplicate_cell_rejected(self):
        def new_merge(root):ET.SubElement(root.find('{'+M+'}mergeCells'),'{'+M+'}mergeCell',ref='B8:C8')
        def duplicate(root):
            row=next(r for r in root.find('{'+M+'}sheetData') if r.get('r')=='8')
            row.append(ET.fromstring(ET.tostring(row[0])))
        for edit in [new_merge,duplicate]:
            with self.assertRaises(ValidationError):parse_source_claims(native_workbook(edit=edit))

    def test_source_name_retained_as_text_never_authenticates(self):
        raw=native_workbook({'F8':{'text':'Lorena — synthetic source description only'}})
        snapshot=self.ingest(raw).snapshot
        self.assertEqual(inspect_synthetic_input_sheet(raw).cells['F8']['literal'],
            'Lorena — synthetic source description only')
        self.assertEqual(snapshot.payload['authorization'],'not_granted')
        self.assertFalse(snapshot.payload['run_ready']);self.assertEqual(snapshot.decision,'PENDING')

    def test_formula_in_source_or_fixed_metadata_rejected(self):
        for ref in ['F8','B8','G1']:
            values={ref:{'formula':'"claim"','value':'claim'}}
            raw=native_workbook(values)
            if ref=='G1':
                # The fixture enforces its own marker; replace it after building.
                def corrupt(root):
                    cell=next(c for row in root.find('{'+M+'}sheetData') for c in row if c.get('r')=='G1')
                    cell.clear();cell.set('r','G1');ET.SubElement(cell,'{'+M+'}f').text='"marker"'
                raw=native_workbook(edit=corrupt)
            with self.assertRaises(ValidationError):parse_source_claims(raw)

    def test_historical_prompt_directions_are_preserved_without_adoption(self):
        raw=native_workbook();snapshot=self.ingest(raw).snapshot
        self.assertIn('thresholds',inspect_synthetic_input_sheet(raw).cells['A2']['literal'])
        self.assertTrue(all(not v for v in snapshot.payload['criterion_claims'].values()))
        self.assertEqual(snapshot.decision,'PENDING')

    def test_source_content_identity_supports_exact_retries(self):
        raw=native_workbook({'C8':{'value':'0'}})
        first=self.ingest(raw);second=self.ingest(raw)
        self.assertEqual(first.snapshot,second.snapshot);self.assertTrue(second.replayed)
        with self.assertRaises(IdempotencyConflict):self.ingest(native_workbook({'C8':{'value':'1'}}))
        self.assertEqual(self.store.get('draft').revision,1)

    def test_new_source_revision_preserves_all_conflicting_claims(self):
        first=self.ingest(native_workbook({'C8':{'value':'0'}}))
        next_snapshot=self.ingest(native_workbook({'C8':{'value':'1'}}),revision=1,operation='revision-2').snapshot
        slot=next_snapshot.slot('input','INPUT_C8')
        self.assertEqual([c['literal'] for c in slot['claims']],['0','1'])
        self.assertEqual(slot['state'],'conflicting_claims')
        self.assertEqual(self.store.get('draft',1),first.snapshot)

    def test_archive_replay_recovers_all_mapped_units_and_source_bytes(self):
        raw=native_workbook({'C8':{'value':'0'}});snapshot=self.ingest(raw).snapshot
        graph=self.graph();execution=execute_synthetic(snapshot,graph)
        bundle=self.archive.load_execution(self.archive.save_execution(snapshot,graph,execution))
        self.assertEqual(bundle.snapshot,snapshot);self.assertEqual(bundle.execution,execution)
        self.assertEqual(self.archive.get_source(hashlib.sha256(raw).hexdigest()),raw)
        self.assertEqual(bundle.execution.payload['results']['echo']['value'],'0')

    def test_new_deals_never_inherit_thresholds_or_input_claims(self):
        self.ingest(native_workbook({'C8':{'value':'0'}}))
        fresh=self.store.create('other',seed())
        self.assertTrue(all(not v for family in ['input_claims','criterion_claims'] for v in fresh.payload[family].values()))

    def test_marker_must_be_exact_text(self):
        def corrupt(root):
            cell=next(c for row in root.find('{'+M+'}sheetData') for c in row if c.get('r')=='G1')
            cell.find('{'+M+'}is/{'+M+'}t').text='real-data'
        with self.assertRaises(ValidationError):parse_source_claims(native_workbook(edit=corrupt))

    def test_hidden_or_omitted_documented_row_is_not_silently_skipped(self):
        def hide(root):
            row=next(r for r in root.find('{'+M+'}sheetData') if r.get('r')=='8');row.set('hidden','1')
        def remove(root):
            data=root.find('{'+M+'}sheetData');data.remove(next(r for r in data if r.get('r')=='8'))
        for edit in [hide,remove]:
            with self.assertRaises(ValidationError):parse_source_claims(native_workbook(edit=edit))

if __name__=='__main__':unittest.main()
