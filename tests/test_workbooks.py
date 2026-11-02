import hashlib
import io
import unittest
import warnings
import zipfile
import xml.etree.ElementTree as ET

from miniuw_foundation import DraftStore, ValidationError
from miniuw_foundation.archive import EvidenceArchive, archive_and_import
from miniuw_foundation.execution import Graph, Node, SlotRef, execute_synthetic
from miniuw_foundation.workbooks import inspect_synthetic_xlsx, parse_synthetic_xlsx
from miniuw_foundation.sources import parse_source_claims
from test_foundation import seed
from xlsx_fixture import workbook, M, R, D

PART='xl/worksheets/sheet1.xml'


def edit_xml(raw,change):
    root=ET.fromstring(raw);change(root);return ET.tostring(root)


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:');self.addCleanup(self.store.close)
        self.archive=EvidenceArchive(':memory:');self.addCleanup(self.archive.close)
        self.blank=self.store.create('draft',seed())
        self.slot=next(iter(self.blank.payload['input_claims']))

    def raw(self,**kwargs):return workbook(self.slot,**kwargs)

    def ingest(self,raw):
        return archive_and_import(self.archive,self.store,'draft',expected_revision=0,operation_id='xlsx',raw=raw).snapshot

    def graph(self):
        return Graph((Node(node_id='echo',operation='literal_echo',definition_revision='fixture-v1',
            dependencies=(),slots=(SlotRef(kind='input',slot_id=self.slot),)),))

    def test_inline_text_hash_exact_cell_locator_and_source_bytes(self):
        raw=self.raw();snapshot=self.ingest(raw)
        claim=snapshot.slot('input',self.slot)['claims'][0]
        self.assertEqual(claim['literal'],'abc')
        self.assertEqual(claim['locator'],'xlsx:sheet:Synthetic:cell:D3')
        self.assertEqual(claim['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.archive.get_source(claim['source_sha256']),raw)

    def test_shared_strings_recover_exact_unicode_whitespace(self):
        rows=[['id','input',self.slot,' ñ, "texto"\nsegunda línea ',chr(92)+'N',chr(92)+'N',chr(92)+'N','fixture']]
        raw=self.raw(rows=rows,shared=True)
        self.assertEqual(parse_synthetic_xlsx(raw)[0].literal,rows[0][3])
        self.assertEqual(parse_source_claims(raw),parse_synthetic_xlsx(raw))

    def test_zero_numeric_lexemes_not_formatted_or_rounded(self):
        for value in ['0','-0','001.2500','1E-3']:
            raw=self.raw(literals={'D3':{'value':value,'attributes':{'s':'14'}}})
            self.assertEqual(parse_synthetic_xlsx(raw)[0].literal,value)
            self.assertEqual(inspect_synthetic_xlsx(raw).cells['D3']['style_id'],'14')

    def test_blank_missing_and_empty_text_distinguished_in_inspection(self):
        cases=[({'D3':{}},'blank',None),({'D3':'missing'},'missing',None)]
        for descriptors,kind,literal in cases:
            raw=self.raw(literals=descriptors)
            self.assertEqual(inspect_synthetic_xlsx(raw).cells['D3']['kind'],kind)
            self.assertIsNone(parse_synthetic_xlsx(raw)[0].literal)
        rows=[['id','input',self.slot,'',chr(92)+'N',chr(92)+'N',chr(92)+'N','fixture']]
        self.assertEqual(parse_synthetic_xlsx(self.raw(rows=rows))[0].literal,'')

    def test_formula_and_zero_cache_preserved_but_not_used(self):
        raw=self.raw(literals={'D3':{'formula':'1-1','value':'0'}})
        inspection=inspect_synthetic_xlsx(raw).cells['D3']
        self.assertEqual(inspection['formula'],'1-1')
        self.assertEqual(inspection['cached_value'],'0')
        snapshot=self.ingest(raw)
        self.assertIsNone(snapshot.slot('input',self.slot)['claims'][0]['literal'])
        execution=execute_synthetic(snapshot,self.graph())
        self.assertEqual(execution.payload['results']['echo']['state'],'blocked')
        self.assertEqual(execution.payload['decision'],'PENDING')

    def test_shared_formula_without_expression_is_not_inferred(self):
        raw=self.raw(literals={'D3':{'formula':None,'formula_attributes':{'t':'shared','si':'0'},'value':'123'}})
        cell=inspect_synthetic_xlsx(raw).cells['D3']
        self.assertEqual(cell['kind'],'formula')
        self.assertEqual(cell['formula_attributes'],{'t':'shared','si':'0'})
        self.assertIsNone(parse_synthetic_xlsx(raw)[0].literal)

    def test_formula_without_cache_still_blocks(self):
        raw=self.raw(literals={'D3':{'formula':'SUM(A1:A2)'}})
        self.assertIsNone(inspect_synthetic_xlsx(raw).cells['D3']['cached_value'])
        self.assertIsNone(parse_synthetic_xlsx(raw)[0].literal)

    def test_error_cell_is_preserved_as_unresolved(self):
        raw=self.raw(literals={'D3':{'attributes':{'t':'e'},'value':'#DIV/0!'}})
        self.assertEqual(inspect_synthetic_xlsx(raw).cells['D3']['error_value'],'#DIV/0!')
        self.assertIsNone(parse_synthetic_xlsx(raw)[0].literal)

    def test_formula_text_stored_as_text_is_not_executed(self):
        rows=[['id','input',self.slot,'=1+1',chr(92)+'N',chr(92)+'N',chr(92)+'N','fixture']]
        raw=self.raw(rows=rows)
        self.assertEqual(inspect_synthetic_xlsx(raw).cells['D3']['kind'],'text')
        self.assertEqual(parse_synthetic_xlsx(raw)[0].literal,'=1+1')

    def test_formula_identity_and_numeric_metadata_rejected(self):
        for cell in [{'formula':'"id"','value':'id'}, {'value':'1'}]:
            with self.assertRaises(ValidationError):self.ingest(self.raw(literals={'A3':cell}))
        self.assertEqual(self.store.get('draft').revision,0)

    def test_wrong_marker_headers_and_sheet_name_rejected(self):
        for replacements in [
            {PART:lambda raw:raw.replace(b'miniuw.synthetic-xlsx.v1',b'other')},
            {PART:lambda raw:raw.replace(b'claim_id',b'unknown')},
            {'xl/workbook.xml':lambda raw:raw.replace(b'Synthetic',b'Inputs')}]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements=replacements))

    def test_duplicate_cells_and_rows_rejected(self):
        def duplicate_cell(root):
            row=root.find('{'+M+'}sheetData')[2]
            row.append(ET.fromstring(ET.tostring(row[0])))
        def duplicate_row(root):
            data=root.find('{'+M+'}sheetData');data.append(ET.fromstring(ET.tostring(data[2])))
        for change in [duplicate_cell,duplicate_row]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements={PART:lambda raw:edit_xml(raw,change)}))

    def test_missing_metadata_sparse_rows_and_extra_columns_rejected(self):
        for descriptors in [{'A3':'missing'}, {'H3':'missing'}]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(literals=descriptors))
        for mutate in [lambda raw:raw.replace(b'r="3"',b'r="4"').replace(b'3"',b'4"'),
                       lambda raw:raw.replace(b'r="D3"',b'r="I3"')]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements={PART:mutate}))

    def test_hidden_and_merged_structures_rejected(self):
        def merge(root):ET.SubElement(root,'{'+M+'}mergeCells')
        for mutate in [lambda raw:raw.replace(b'r="3"',b'r="3" hidden="1"'),lambda raw:edit_xml(raw,merge)]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements={PART:mutate}))
        with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements={'xl/workbook.xml':lambda raw:raw.replace(b'name="Synthetic"',b'name="Synthetic" state="hidden"')}))

    def test_external_links_and_macros_rejected_without_fetch_or_execution(self):
        for extras in [{'xl/vbaProject.bin':b'no execution'}, {'xl/externalLinks/externalLink1.xml':b'unsupported'}]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(extras=extras))
        def external(raw):
            return edit_xml(raw,lambda root:ET.SubElement(root,'{'+R+'}Relationship',Id='external',Type=D+'/hyperlink',Target='https://example.invalid',TargetMode='External'))
        with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements={'xl/_rels/workbook.xml.rels':external}))

    def test_xml_dtd_and_malformed_xml_rejected(self):
        for raw in [b'<!DOCTYPE x [<!ENTITY a "unsafe">]><x/>',b'<invalid']:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements={PART:raw}))

    def test_traversal_duplicate_zip_entries_and_expansion_bound_rejected(self):
        for extras in [{'../outside':b'bad'},{'/absolute':b'bad'},{'xl/large.xml':b'x'*1_048_577}]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(extras=extras))
        output=io.BytesIO(self.raw())
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(output,'a') as archive:archive.writestr('xl/workbook.xml',b'duplicate')
        with self.assertRaises(ValidationError):parse_synthetic_xlsx(output.getvalue())

    def test_bad_zip_missing_part_and_unsupported_cell_type_rejected(self):
        with self.assertRaises(ValidationError):parse_synthetic_xlsx(b'PKinvalid')
        with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(replacements={'xl/workbook.xml':None}))
        for value in [{'attributes':{'t':'b'},'value':'1'}, {'value':'NaN'}, {'attributes':{'t':'s'},'value':'99999999'}]:
            with self.assertRaises(ValidationError):parse_synthetic_xlsx(self.raw(literals={'D3':value}))

    def test_archive_recovery_keeps_formula_and_cache_evidence(self):
        raw=self.raw(literals={'D3':{'formula':'2+2','value':'4'}})
        snapshot=self.ingest(raw);graph=self.graph();execution=execute_synthetic(snapshot,graph)
        restored=self.archive.load_execution(self.archive.save_execution(snapshot,graph,execution))
        recovered=self.archive.get_source(hashlib.sha256(raw).hexdigest())
        self.assertEqual(recovered,raw)
        self.assertEqual(inspect_synthetic_xlsx(recovered).cells['D3']['cached_value'],'4')
        self.assertEqual(restored.execution,execution)
        self.assertEqual(restored.execution.payload['results']['echo']['state'],'blocked')

    def test_inspection_copy_and_new_deal_criteria_are_isolated(self):
        inspection=inspect_synthetic_xlsx(self.raw());copy=inspection.cells;copy['D3']['literal']='changed'
        self.assertEqual(inspection.cells['D3']['literal'],'abc')
        self.ingest(self.raw())
        fresh=self.store.create('new',seed())
        self.assertTrue(all(not v for v in fresh.payload['criterion_claims'].values()))

    def test_ambiguous_cell_and_duplicate_data_tables_rejected(self):
        with self.assertRaises(ValidationError):
            parse_synthetic_xlsx(self.raw(literals={'D3':{'attributes':{'t':'inlineStr'},'value':'1'}}))
        def duplicate_data(root):
            root.append(ET.fromstring(ET.tostring(root.find('{'+M+'}sheetData'))))
        with self.assertRaises(ValidationError):
            parse_synthetic_xlsx(self.raw(replacements={PART:lambda raw:edit_xml(raw,duplicate_data)}))

    def test_delivered_workbook_fixture_keeps_formula_cache_inactive(self):
        from pathlib import Path
        raw=(Path(__file__).resolve().parents[1]/'templates/synthetic-workbook-example.xlsx').read_bytes()
        records=parse_synthetic_xlsx(raw)
        self.assertEqual(len(records),2)
        self.assertEqual(records[0].literal,'abc')
        self.assertIsNone(records[1].literal)
        self.assertEqual(inspect_synthetic_xlsx(raw).cells['D4']['cached_value'],'4')
        snapshot=self.ingest(raw)
        self.assertEqual(snapshot.slot('input',records[1].slot_id)['state'],'missing')

if __name__=='__main__':unittest.main()
