from pathlib import Path
from fractions import Fraction as F
from io import BytesIO
import base64,copy,json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader
from inputsheet_fixture import native_workbook,ORIGINAL
from miniuw_foundation.drafts import ValidationError,canonical
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.debt_service import rational
from miniuw_foundation.phased_settled_output import assemble_phased_settled_output
from miniuw_foundation.worksheet_settled_output import (assemble_worksheet_settled_output,required_sources,parse_source,parse_claims,check_worksheet,WorksheetSettledRun,layout)
from miniuw_foundation.worksheet_settled_report import render_worksheet_settled_output
from miniuw_foundation.worksheet_settled_artifacts import (build_worksheet_settled_artifacts,write_worksheet_settled_artifacts,recover_worksheet_settled_directory,read_worksheet_settled_artifacts)

ROOT=Path(__file__).resolve().parents[1];raw=lambda p:canonical(p).encode();q=lambda v:rational(F(v))


def fixture(label='matched'):return(ROOT/('templates/worksheet-settled-'+label+'-T111.json')).read_bytes()


def refresh_registry(p):
    """Explicit test-only fresh evidence hypothesis; production adapter never renews."""
    p=copy.deepcopy(p);r=json.loads(p['registry_source_utf8']);req=required_sources(raw(p));old={v['requirement_id']:v for v in r['evidence']};r.update(requirements=req,evidence=[dict(old[v['requirement_id']],**v)for v in req]);p['registry_source_utf8']=canonical(r);return p


class WorksheetSettledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=fixture();cls.p=json.loads(cls.source);cls.result=assemble_worksheet_settled_output(cls.source);cls.claims=json.loads(cls.p['claims_source_utf8']);cls.binding=json.loads(cls.p['binding_source_utf8'])
        cls.values=dict(B3=dict(text=cls.claims['case_id']),E3=dict(text=cls.claims['as_of_UTC']),C7=dict(text='per_unit_per_month'))

    def candidate(self,values=None,claims_change=None,binding_change=None):
        p=copy.deepcopy(self.p);c=copy.deepcopy(self.claims)
        if claims_change:claims_change(c)
        workbook=native_workbook(dict(self.values,**(values or{})));p.update(workbook_base64=base64.b64encode(workbook).decode(),claims_source_utf8=canonical(c))
        b=dict(self.binding,claims_source_sha256=sha(p['claims_source_utf8'].encode()),workbook_sha256=sha(workbook),**{k:c[k]for k in ('context','case_id','case_revision','as_of_UTC')})
        if binding_change:b.update(binding_change)
        p['binding_source_utf8']=canonical(b);return raw(refresh_registry(p))

    def assert_withheld(self,result):
        p=result.payload;self.assertEqual(p['state'],'PENDING');self.assertTrue(all(v is None for k,v in p.items()if k.startswith('current_')))
        self.assertEqual(p['decision'],'PENDING');self.assertFalse(p['real_decisions_enabled'])

    def test_matched_sheet_preserves_every_parent_current_cash_stock_risk_and_root(self):
        p=self.result.payload;parent=assemble_phased_settled_output(self.p['phased_settled_source_utf8'].encode()).payload
        for k,v in parent.items():
            if k.startswith('current_'):self.assertEqual(p[k],v)
        s=p['current_project_return_story'];self.assertEqual(s['gross_contributions'],q(1400));self.assertEqual(s['gross_distributions'],q(778));self.assertEqual(s['net_cash_profit'],q(-622))
        self.assertEqual(p['current_operating_totals']['closing_free_cash_claim'],q(213));self.assertEqual(p['current_settlement_summary']['settlement_cash'],q(5));self.assertEqual(p['current_rental_totals']['effective_rent'],q(88))

    def test_explicit_premium_revision_retains_its_exact_parent_not_old_cash(self):
        p=assemble_worksheet_settled_output(fixture('twelve')).payload
        self.assertEqual(p['current_project_return_story']['gross_distributions'],q(776));self.assertEqual(p['current_project_return_story']['net_cash_profit'],q(-624));self.assertNotEqual(p['current_irr_evidence'],self.result.payload['current_irr_evidence'])

    def test_all_55_fields_keep_exact_cell_claim_pointer_and_unit_by_identity(self):
        rows=self.result.payload['worksheet_reconciliation']['rows'];self.assertEqual(len(rows),55)
        self.assertEqual([r['field_id']for r in rows],[r['field_id']for r in self.claims['original_inputs']])
        for i,r in enumerate(rows):
            self.assertEqual(r['worksheet_locator'],'xlsx:sheet:Inputs:cell:'+r['cell']);self.assertEqual(r['claim_pointer'],'/claims_source_utf8::json/original_inputs/'+str(i)+'/value');self.assertEqual(r['unit_literal'],r['claim']['unit']);self.assertFalse(r['financial_semantics_verified'])
        self.assertEqual(self.result.payload['worksheet_reconciliation']['counts'],dict(MATCHED_REPRESENTATION=1,MISSING_BOTH=54))
        spec=copy.deepcopy(layout());spec['fields'].reverse()
        with patch('miniuw_foundation.worksheet_settled_output.layout',return_value=spec):self.assertEqual(assemble_worksheet_settled_output(self.source),self.result)

    def test_each_of_59_parent_and_worksheet_sources_can_expire_independently(self):
        r0=json.loads(self.p['registry_source_utf8']);self.assertEqual(len(r0['evidence']),59)
        for i in range(len(r0['evidence'])):
            p=copy.deepcopy(self.p);r=copy.deepcopy(r0);r['evidence'][i]['valid_until']=p['evaluated_as_of_UTC'];p['registry_source_utf8']=canonical(r)
            with self.subTest(source=i):self.assert_withheld(assemble_worksheet_settled_output(raw(p)))

    def test_self_consistent_omitted_extra_or_wrong_hash_registry_does_not_pass(self):
        for mode in ('omit','extra','hash'):
            p=copy.deepcopy(self.p);r=json.loads(p['registry_source_utf8'])
            if mode=='omit':r['requirements'].pop();r['evidence'].pop()
            elif mode=='hash':r['requirements'][-1]['source_sha256']='0'*64;r['evidence'][-1]['source_sha256']='0'*64
            else:
                row=dict(r['requirements'][-1],requirement_id='/SYNTHETIC-unknown',source_locator='/SYNTHETIC-unknown');r['requirements'].append(row);r['evidence'].append(dict(r['evidence'][-1],**row,evidence_id='SYNTHETIC-unknown'))
            p['registry_source_utf8']=canonical(r);self.assert_withheld(assemble_worksheet_settled_output(raw(p)))

    def test_source_byte_changes_need_both_binding_and_evidence_not_only_equal_json(self):
        p=copy.deepcopy(self.p);p['claims_source_utf8']+='\n';self.assert_withheld(assemble_worksheet_settled_output(raw(refresh_registry(p))))
        b=json.loads(p['binding_source_utf8']);b['claims_source_sha256']=sha(p['claims_source_utf8'].encode());p['binding_source_utf8']=canonical(b)
        self.assert_withheld(assemble_worksheet_settled_output(raw(p)));self.assertEqual(assemble_worksheet_settled_output(raw(refresh_registry(p))).payload['current_project_return_story'],self.result.payload['current_project_return_story'])

    def test_matched_sheet_and_current_child_cannot_restore_expired_parent(self):
        p=assemble_worksheet_settled_output(fixture('parent-expired'));self.assert_withheld(p);self.assertTrue(p.payload['worksheet_gate_open']);self.assertIn('parent_phased_settled_output_blocked',p.payload['blockers']['gate'])
        self.assertEqual(json.loads(p.payload['registry_run']['payload_json'])['state'],'current_synthetic_evidence')

    def test_explicit_zero_conflict_and_rational_zero_match_never_adopt_model_values(self):
        p=assemble_worksheet_settled_output(fixture('zero-conflict'));self.assert_withheld(p);row=next(r for r in p.payload['worksheet_reconciliation']['rows']if r['cell']=='C8');self.assertEqual(row['decoded_representation'],q(0));self.assertEqual(row['state'],'CONFLICT')
        matched=assemble_worksheet_settled_output(fixture('zero-matched')).payload;row=next(r for r in matched['worksheet_reconciliation']['rows']if r['cell']=='C8');self.assertEqual(row['state'],'MATCHED_REPRESENTATION');self.assertEqual(row['claim']['value'],dict(numerator='0',denominator='2'));self.assertEqual(matched['current_project_return_story'],self.result.payload['current_project_return_story']);self.assertFalse(matched['projection_computed_from_55_claims'])

    def test_formulas_cache_errors_and_blank_kinds_remain_explicit(self):
        for descriptor,kind in [(dict(formula='1+1',value='2'),'formula'),(dict(type='e',value='#DIV/0!'),'excel_error'),(dict(text=''),'text'),({},'blank'),('missing','missing')]:
            r=assemble_worksheet_settled_output(self.candidate(dict(C8=descriptor)));row=next(v for v in r.payload['worksheet_reconciliation']['rows']if v['cell']=='C8');self.assertEqual(row['worksheet_cell']['kind'],kind)
            if kind in('blank','missing'):self.assertEqual(row['state'],'MISSING_BOTH');self.assertIsNotNone(r.payload['current_project_return_story'])
            else:self.assert_withheld(r)
            if kind=='formula':self.assertEqual(row['worksheet_cell']['cached_value'],'2');self.assertIsNone(row['decoded_representation'])

    def test_text_numeric_unsupported_lexemes_are_not_coerced(self):
        for descriptor in (dict(text='0'),dict(value='1e2')):
            p=assemble_worksheet_settled_output(self.candidate(dict(C8=descriptor)));self.assert_withheld(p)
        for value in ('1,25',' 1','1%'):
            with self.assertRaises(ValidationError):assemble_worksheet_settled_output(self.candidate(dict(C8=dict(value=value))))
        result=assemble_worksheet_settled_output(self.candidate(dict(C8=dict(value='-0.125')),lambda c:c['original_inputs'][1].update(value=q(F(-1,8)),source_ref='SYNTHETIC-declared-negative')))
        self.assertIsNotNone(result.payload['current_project_return_story']);self.assertFalse(result.payload['worksheet_values_adopted'])

    def test_literal_unit_and_source_reference_are_checked_without_financial_mapping(self):
        for change in (lambda c:c['original_inputs'][0].update(unit='USD'),lambda c:c['original_inputs'][0].update(source_ref=None),lambda c:c.update(source_ref=None)):
            self.assert_withheld(assemble_worksheet_settled_output(self.candidate(claims_change=change)))
        p=assemble_worksheet_settled_output(self.candidate(claims_change=lambda c:c['original_inputs'][0].update(unit=None,period_ref='SYNTHETIC-unmapped-period'))).payload
        self.assertIsNotNone(p['current_project_return_story']);self.assertFalse(p['worksheet_financial_semantics_completed']);self.assertIsNone(p['worksheet_reconciliation']['rows'][0]['claim']['unit'])

    def test_metadata_and_explicit_parent_case_context_utc_cannot_be_rebound_silently(self):
        for values in (dict(B3=dict(text='SYNTHETIC-other')),dict(E3=dict(text='2027-07-02T12:00:00Z'))):self.assert_withheld(assemble_worksheet_settled_output(self.candidate(values)))
        for change in (lambda c:c.update(case_id='SYNTHETIC-other'),lambda c:c.update(context=dict(c['context'],deal_id='SYNTHETIC-other')),lambda c:c.update(as_of_UTC='2027-07-02T12:00:00Z')):
            self.assert_withheld(assemble_worksheet_settled_output(self.candidate(claims_change=change)))
        p=copy.deepcopy(self.p);p['evaluated_as_of_UTC']='2027-07-01T13:00:00Z';self.assert_withheld(assemble_worksheet_settled_output(raw(p)))

    def test_binding_every_hash_revision_context_and_reference_is_required(self):
        for k,v in [('phased_settled_source_sha256','0'*64),('workbook_sha256','0'*64),('claims_source_sha256','0'*64),('case_revision',2),('case_id','SYNTHETIC-other'),('as_of_UTC','2027-07-02T12:00:00Z'),('context',dict(self.binding['context'],scenario_id='SYNTHETIC-other')),('source_ref',None)]:
            with self.subTest(key=k):self.assert_withheld(assemble_worksheet_settled_output(self.candidate(binding_change={k:v})))

    def test_strict_catalogue_base64_and_synthetic_original_layout_guards(self):
        for mode in ('order','omit','extra','bool_revision'):
            c=copy.deepcopy(self.claims)
            if mode=='order':c['original_inputs'].reverse()
            elif mode=='omit':c['original_inputs'].pop()
            elif mode=='extra':c['original_inputs'].append(c['original_inputs'][0])
            else:c['case_revision']=True
            with self.assertRaises(ValidationError):parse_claims(raw(c))
        for value in ('@@@','',base64.b64encode(b'x'*(1048576+1)).decode()):
            with self.assertRaises(ValidationError):parse_source(raw(dict(self.p,workbook_base64=value)))
        p=dict(self.p,workbook_base64=base64.b64encode(ORIGINAL.read_bytes()).decode())
        with self.assertRaises(ValidationError):assemble_worksheet_settled_output(raw(p))

    def test_blocked_one_page_withholds_all_current_groups_years_and_money(self):
        for label in ('zero-conflict','formula','expired','parent-expired'):
            source=fixture(label);run=assemble_worksheet_settled_output(source);self.assert_withheld(run);report=render_worksheet_settled_output(source,run);m=report.manifest
            self.assertEqual(len(PdfReader(BytesIO(report.pdf_bytes)).pages),1);self.assertTrue(m['all_current_money_withheld']);self.assertEqual(m['event_groups'],[]);self.assertEqual(m['annual_years'],[])

    def test_current_page_retains_return_zero_events_annual_rows_and_pending_definitions(self):
        report=render_worksheet_settled_output(self.source,self.result);reader=PdfReader(BytesIO(report.pdf_bytes));self.assertEqual(len(reader.pages),1);t=reader.pages[0].extract_text();m=report.manifest
        for value in ('MINI-UW | HOJA, RENTA Y VENTA','Hoja cotejada','55 campos: 1 coinciden; 54 faltan. Semantica pendiente.','Resultado T111 SHA256:','778','-622','Renta: 88 | polizas: 2','Capital declarado: Pendiente'):self.assertIn(value,t)
        self.assertNotIn('Resultado T110 SHA256:',t);self.assertTrue(all(r['text']in t for r in m['display_spans']));self.assertEqual(sorted(i for g in m['event_groups']for i in g['event_indices']),list(range(8)));self.assertEqual(sum(g['zero_event_count']for g in m['event_groups']),3);self.assertEqual(m['annual_years'],[2026,2027])

    def test_forged_rehashed_result_and_wrong_source_cannot_render(self):
        p=self.result.payload;p['current_project_return_story']['gross_distributions']=q(999);value=canonical(p)
        with self.assertRaises(ValidationError):render_worksheet_settled_output(self.source,WorksheetSettledRun(value,sha(value.encode())))
        with self.assertRaises(ValidationError):render_worksheet_settled_output(fixture('zero-conflict'),self.result)

    def test_six_file_source_first_recovery_and_rehashed_packet_rejection(self):
        for label in ('matched','zero-conflict','expired'):
            run,_=recover_worksheet_settled_directory(ROOT/('docs/review/miniuw-v1-worksheet-settled-'+label+'-example'));self.assertEqual(run,assemble_worksheet_settled_output(fixture(label)))
        for mode in ('result','version','inventory'):
            with tempfile.TemporaryDirectory()as td:
                target=Path(td)/'result';write_worksheet_settled_artifacts(self.source,target);p=json.loads((target/'package.json').read_bytes())
                if mode=='result':
                    v=json.loads((target/'current-results.json').read_bytes());v['worksheet_values_adopted']=True;data=raw(v);(target/'current-results.json').write_bytes(data)
                    for row in p['files']:
                        if row['path']=='current-results.json':row.update(bytes=len(data),sha256=sha(data))
                elif mode=='version':p['versions']['worksheet_reader']='0'*64
                else:p['files'][0]['path']='../escape'
                (target/'package.json').write_bytes(raw(p))
                with self.assertRaises(ValidationError):recover_worksheet_settled_directory(target)

    def test_safe_writer_exact_retry_no_other_overwrite_symlink_and_temp_cleanup(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'result';write_worksheet_settled_artifacts(self.source,target);values=read_worksheet_settled_artifacts(target);self.assertEqual(write_worksheet_settled_artifacts(self.source,target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_worksheet_settled_artifacts(fixture('twelve'),target)
            self.assertEqual(read_worksheet_settled_artifacts(target),values);link=Path(td)/'link';link.symlink_to(target,target_is_directory=True)
            with self.assertRaises(ValidationError):read_worksheet_settled_artifacts(link)
            with patch('miniuw_foundation.worksheet_settled_artifacts.os.rename',side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError):write_worksheet_settled_artifacts(self.source,Path(td)/'failed')
            self.assertFalse(any(p.name.startswith('.miniuw')for p in Path(td).iterdir()))

    def test_matching_claims_do_not_complete_financial_mapping_or_real_authority(self):
        p=self.result.payload
        for k in ('worksheet_values_adopted','worksheet_financial_semantics_completed','projection_computed_from_55_claims','parent_result_used_as_current_fallback','source_authority_verified','professional_review_authenticated','original_sheet_adapter_for_this_profile_implemented','financial_model_complete','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):self.assertFalse(p[k])
        self.assertTrue(all(c['threshold']is None and c['state']=='PENDING'for c in p['criterion_slots']));self.assertIsNone(p['personal_investor_return']);self.assertEqual(p['original_semantic_mappings_pending'],54);self.assertEqual(p['decision'],'PENDING')


if __name__=='__main__':unittest.main()
