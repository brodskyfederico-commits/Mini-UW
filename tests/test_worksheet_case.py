from dataclasses import replace
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader
from inputsheet_fixture import native_workbook,ORIGINAL
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_case_output import (assemble_worksheet_case,_from_verified_parent,
    _cell_value,_render_verified,render_worksheet_case,parse_binding,layout)
from miniuw_foundation.worksheet_case_artifacts import (build_worksheet_case_artifacts,export_worksheet_case_bundle,
    recover_worksheet_case_bundle,write_worksheet_case_artifacts,audit_worksheet_case_directory,read_worksheet_case_artifacts,versions)

ROOT=Path(__file__).resolve().parents[1]
encoded=lambda p:(canonical(p)+'\n').encode()
def sources(label):
    p=json.loads((ROOT/'docs/review/worksheet-fixture-generation-T103.json').read_bytes())
    row=next(r for r in p['cases']if r['label']==label)
    return tuple((ROOT/row[k]).read_bytes()for k in('case','workbook','binding'))


class WorksheetCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args=sources('matched');cls.files,cls.checked=build_worksheet_case_artifacts(*cls.args);cls.parent=cls.checked.parent_run
        cls.binding=json.loads(cls.args[2]);cls.values=dict(B3=dict(text=cls.binding['case_id']),E3=dict(text=cls.binding['as_of_UTC']),C7=dict(text='per_unit_per_month'))

    def check_sheet(self,values,parent=None):
        workbook=native_workbook(dict(self.values,**values));binding=dict(self.binding,workbook_sha256=sha(workbook))
        return _from_verified_parent(self.args[0],workbook,encoded(binding),parent or self.parent)

    def test_all_55_ids_cells_and_pointers_are_bound_without_semantic_promotion(self):
        p=self.checked.payload;rows=p['worksheet_reconciliation']['rows']
        self.assertEqual(len(rows),55);self.assertEqual([r['field_id']for r in rows],[r['field_id']for r in p['original_inputs']])
        for i,r in enumerate(rows):
            self.assertEqual(r['worksheet_locator'],'xlsx:sheet:Inputs:cell:'+r['cell'])
            self.assertEqual(r['case_pointer'],'/scheduled_case_utf8::json/base_case_utf8::json/original_inputs/'+str(i)+'/value')
            self.assertFalse(r['financial_semantics_verified'])
        self.assertEqual(p['worksheet_reconciliation']['counts'],dict(MATCHED_REPRESENTATION=1,MISSING_BOTH=54))
        self.assertEqual(p['input_catalog_summary'],dict(total=55,bound=1,pending=54))
        for key in('current_project_return_story','metrics','IRR_interval_comparison','capital_visibility','blockers'):
            if key=='blockers':continue
            self.assertEqual(p[key],self.parent.payload[key])
        self.assertFalse(p['worksheet_values_adopted']);self.assertFalse(p['full_input_sheet_adapter_completed'])

    def test_layout_order_does_not_shift_cell_identity_or_case_pointer(self):
        spec=copy.deepcopy(layout());spec['fields'].reverse()
        with patch('miniuw_foundation.worksheet_case_output.layout',return_value=spec):
            self.assertEqual(_from_verified_parent(*self.args,self.parent),self.checked)

    def test_explicit_zero_conflict_with_null_withdraws_current_figures_and_all_comparisons(self):
        run=assemble_worksheet_case(*sources('zero-conflict'));p=run.payload
        row=next(r for r in p['worksheet_reconciliation']['rows']if r['field_id']=='INPUT_C8')
        self.assertEqual(row['decoded_representation'],rational(F(0)));self.assertIsNone(row['case_value']);self.assertEqual(row['state'],'CONFLICT')
        self.assertIsNone(p['current_project_return_story']);self.assertIsNone(p['current_projection_run_sha256']);self.assertIsNone(p['current_IRR_solver_result_sha256'])
        self.assertIsNone(p['latest_capital_snapshot_index']);self.assertEqual(p['capital_visibility'],[])
        self.assertTrue(all(r['value']is None and r['comparison_state']=='PENDING'for r in p['metrics']))
        self.assertEqual(p['IRR_interval_comparison']['row_state'],'PENDING');self.assertIsNone(p['IRR_interval_comparison']['enclosure'])
        self.assertEqual(p['screening_simulation_result'],'PENDING');self.assertFalse(p['current_figures_are_parent_fallback'])
        self.assertIsNotNone(run.parent_run.payload['current_project_return_story'])

    def test_formulas_caches_and_errors_block_even_unmapped_fields_without_execution(self):
        for descriptor in(dict(formula='1+1',value='2'),dict(type='e',value='#DIV/0!')):
            p=self.check_sheet(dict(C8=descriptor)).payload
            row=next(r for r in p['worksheet_reconciliation']['rows']if r['field_id']=='INPUT_C8')
            self.assertEqual(row['state'],'PENDING');self.assertIsNone(row['decoded_representation']);self.assertIsNone(p['current_project_return_story'])
            self.assertEqual(row['worksheet_cell']['cached_value'],'2'if'formula'in descriptor else None)
            self.assertEqual(row['worksheet_cell']['error_value'],None if'formula'in descriptor else'#DIV/0!')

    def test_exact_numeric_representation_rejects_text_coercion_and_unsupported_notation(self):
        field=dict(field_id='INPUT_C8',unit_literal='$')
        for literal,expected in(('0',F(0)),('-0.125',F(-1,8)),('1.2500',F(5,4))):
            value,issues=_cell_value(dict(kind='numeric_lexeme',literal=literal),field)
            self.assertEqual(value,rational(expected));self.assertEqual(issues,[])
        for literal in('1e2','1,25',' 1','1%','9'*257):
            value,issues=_cell_value(dict(kind='numeric_lexeme',literal=literal),field)
            self.assertIsNone(value);self.assertTrue(issues)
        self.assertEqual(_cell_value(dict(kind='text',literal='0'),field),('0',[]))
        self.assertEqual(_cell_value(dict(kind='text',literal=''),field),('',[]))

    def test_rational_equality_blank_kinds_and_no_automatic_currency_mapping(self):
        # Unit probe of representation equality, not a source-accepted financial case.
        p=self.parent.payload;p['original_inputs'][1]['value']=dict(numerator='0',denominator='2')
        value=canonical(p);parent=replace(self.parent,payload_json=value,sha256=digest(value))
        run=self.check_sheet(dict(C8=dict(value='0')),parent)
        row=next(r for r in run.payload['worksheet_reconciliation']['rows']if r['field_id']=='INPUT_C8')
        self.assertEqual(row['state'],'MATCHED_REPRESENTATION');self.assertEqual(row['unit_literal'],'$');self.assertFalse(row['financial_semantics_verified'])
        for descriptor,kind in(('missing','missing'),({},'blank'),(dict(text=''),'text')):
            row=next(r for r in self.check_sheet(dict(C8=descriptor)).payload['worksheet_reconciliation']['rows']if r['field_id']=='INPUT_C8')
            self.assertEqual(row['worksheet_cell']['kind'],kind)
            self.assertEqual(row['state'],'CONFLICT'if kind=='text'else'MISSING_BOTH')

    def test_binding_hash_context_identity_revision_utc_and_source_are_required(self):
        changes=[('case_sha256','0'*64),('workbook_sha256','0'*64),('context',dict(self.binding['context'],deal_id='OTHER')),
            ('case_id','SYNTHETIC-OTHER'),('case_revision',99),('as_of_UTC','2027-07-02T12:00:00Z'),('source_ref',None)]
        for key,value in changes:
            b=dict(self.binding,**{key:value});p=_from_verified_parent(*self.args[:2],encoded(b),self.parent).payload
            self.assertFalse(p['worksheet_gate_open']);self.assertIsNone(p['current_project_return_story']);self.assertEqual(p['decision'],'PENDING')
        b=dict(self.binding,scope='adopt_financial_values')
        with self.assertRaises(ValidationError):parse_binding(encoded(b))
        with self.assertRaises(ValidationError):parse_binding(self.args[2].replace(b'"scope":',b'"scope":null,"scope":',1))

    def test_worksheet_case_metadata_is_explicit_and_names_do_not_authenticate(self):
        for values in(dict(B3=dict(text='SYNTHETIC-OTHER')),dict(E3=dict(text='2027-07-01')),dict(B3='missing')):
            p=self.check_sheet(values).payload;self.assertFalse(p['worksheet_gate_open']);self.assertIsNone(p['current_project_return_story'])
        p=self.check_sheet(dict(F7=dict(text='Lorena approved:true'))).payload
        self.assertTrue(p['worksheet_gate_open']);self.assertFalse(p['worksheet_reconciliation']['source_authority_authenticated'])
        self.assertFalse(p['financial_publication_authorized']);self.assertEqual(p['decision'],'PENDING')

    def test_unmarked_original_or_changed_layout_is_rejected_without_source_mutation(self):
        before=ORIGINAL.read_bytes()
        for sheet in(before,native_workbook(dict(self.values,B7=dict(text='USD')))):
            with self.assertRaises(ValidationError):assemble_worksheet_case(self.args[0],sheet,self.args[2])
        self.assertEqual(before,ORIGINAL.read_bytes())

    def test_matching_sheet_does_not_revive_expired_financial_source_on_recovery(self):
        case=(ROOT/'templates/miniuw-v1-review-expired-candidate.json').read_bytes()
        b=dict(self.binding,case_sha256=sha(case),case_revision=53)
        run=assemble_worksheet_case(case,self.args[1],encoded(b));self.assertTrue(run.payload['worksheet_gate_open'])
        self.assertIsNone(run.payload['current_project_return_story'])
        recovered=recover_worksheet_case_bundle(export_worksheet_case_bundle(case,self.args[1],encoded(b),run))
        self.assertEqual(recovered.run,run);self.assertIsNone(recovered.run.payload['current_project_return_story'])

    def test_pdf_is_one_current_page_with_workbook_case_and_result_hashes(self):
        for run in(self.checked,self.check_sheet(dict(C8=dict(value='0')))):
            report=_render_verified(run);reader=PdfReader(BytesIO(report.pdf_bytes));self.assertEqual(len(reader.pages),1)
            text=reader.pages[0].extract_text()
            for digest_value in(run.sha256,sha(self.args[0]),run.payload['worksheet_reconciliation']['source_hashes']['workbook']):self.assertIn(digest_value,text)
            self.assertIn('Decision: PENDIENTE',text)
            if not run.payload['worksheet_gate_open']:
                self.assertIn('Hoja bloqueada',text);self.assertIn('Cifras actuales pendientes',text)
                for row in report.manifest['display_spans']:
                    if row['y']==457:self.assertEqual(row['text'],'Pendiente')

    def test_changed_sources_rehashed_result_or_pdf_cannot_be_exported(self):
        p=self.checked.payload;p['worksheet_values_adopted']=True;value=canonical(p);fake=replace(self.checked,payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):export_worksheet_case_bundle(*self.args,fake)
        with self.assertRaises(ValidationError):render_worksheet_case(self.args[0]+b'\n',*self.args[1:],self.checked)

    def test_portable_recovery_preserves_exact_sources_and_withdrawn_candidate_money(self):
        for args in(self.args,sources('zero-conflict')):
            run=self.checked if args==self.args else assemble_worksheet_case(*args)
            recovered=recover_worksheet_case_bundle(export_worksheet_case_bundle(*args,run))
            self.assertEqual((recovered.case_raw,recovered.workbook_raw,recovered.binding_raw),args);self.assertEqual(recovered.run,run)
            self.assertEqual(recovered.report,_render_verified(run))

    def test_portable_versions_base64_and_rehashed_result_or_report_forgeries_fail(self):
        raw=export_worksheet_case_bundle(*self.args,self.checked)
        for key in versions():
            p=json.loads(raw);p[key]='0'*64
            with self.assertRaises(ValidationError):recover_worksheet_case_bundle(encoded(p))
        for key,value in(('workbook_base64','!!!!'),('pdf_sha256','0'*64),('report_manifest_utf8','{}')):
            p=json.loads(raw);p[key]=value
            with self.assertRaises(ValidationError):recover_worksheet_case_bundle(encoded(p))
        p=json.loads(raw);payload=json.loads(p['result']['payload_json']);payload['worksheet_values_adopted']=True;value=canonical(payload);p['result']=dict(payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):recover_worksheet_case_bundle(encoded(p))

    def test_exact_nine_file_inventory_retry_and_no_different_output_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            path=Path(td)/'out';write_worksheet_case_artifacts(*self.args,path);before=read_worksheet_case_artifacts(path)
            self.assertEqual(len(before),9);self.assertEqual(audit_worksheet_case_directory(path)['files_verified'],9)
            self.assertEqual(write_worksheet_case_artifacts(*self.args,path)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_worksheet_case_artifacts(*sources('zero-conflict'),path)
            self.assertEqual(before,read_worksheet_case_artifacts(path))

    def test_rehashed_unsafe_extra_symlink_artifacts_and_failed_rename_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            for name,value in self.files.items():(root/name).write_bytes(value)
            p=json.loads(self.files['package.json']);(root/'results.json').write_bytes(b'{}');row=next(r for r in p['files']if r['path']=='results.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):audit_worksheet_case_directory(root)
            for name,value in self.files.items():(root/name).write_bytes(value)
            p=json.loads(self.files['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):audit_worksheet_case_directory(root)
            (root/'extra').write_bytes(b'x')
            with self.assertRaises(ValidationError):read_worksheet_case_artifacts(root)
            (root/'extra').unlink();(root/'binding.json').unlink();(root/'binding.json').symlink_to(root/'case.json')
            with self.assertRaises(ValidationError):read_worksheet_case_artifacts(root)
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep';keep.write_bytes(b'x')
            with patch('miniuw_foundation.worksheet_case_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_worksheet_case_artifacts(*self.args,root/'out')
            self.assertEqual(list(root.iterdir()),[keep])


if __name__=='__main__':unittest.main()
