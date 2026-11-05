from dataclasses import replace
from pathlib import Path
from io import BytesIO
import copy,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.settled_case import assemble_settled_case
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_settled_case import assemble_current_settled_case,required_settled_sources
from miniuw_foundation.settled_output_report import render_settled_output,_render_verified
from miniuw_foundation.synthetic_onepager import PreviewLayoutError
from miniuw_foundation.settled_output_artifacts import (build_current_settled_artifacts,read_current_settled_artifacts,write_current_settled_artifacts,
    recover_current_settled_directory,audit_current_settled_directory,validate_report,versions)

ROOT=Path(__file__).resolve().parents[1];enc=lambda p:canonical(p).encode()
def source(label='current'):return(ROOT/('templates/current-settled-'+label+'-T109.json')).read_bytes()
def candidate(change=None,registry_change=None):
    p=json.loads(source())
    if registry_change:
        r=json.loads(p['registry_source_utf8']);registry_change(r);p['registry_source_utf8']=canonical(r)
    if change:change(p)
    return enc(p)


class CurrentSettledOutputTests(unittest.TestCase):
    def pending(self,raw):
        run=assemble_current_settled_case(raw);p=run.payload;self.assertEqual(p['state'],'PENDING')
        for key in('current_project_return_story','current_settlement_summary','current_operating_totals','current_holding_sale_totals','current_risk_observations','current_irr_evidence','current_compiled_investor_json','current_nominal_insurance_totals','current_nominal_plan_run_sha256'):self.assertIsNone(p[key],key)
        return run

    def test_complete_current_source_gate_preserves_exact_full_parent_money_and_roots(self):
        p=json.loads(source());base=assemble_settled_case(p['case_source_utf8'].encode()).payload;run=assemble_current_settled_case(source());s=run.payload
        self.assertEqual(s['current_project_return_story'],base['project_return_story']);self.assertEqual(s['current_settlement_summary'],base['settlement_summary']);self.assertEqual(s['current_irr_evidence'],base['irr_evidence'])
        self.assertEqual(s['source_requirements_checked'],35);self.assertTrue(s['synthetic_complete_source_evidence_current']);self.assertEqual(s['decision'],'PENDING')

    def test_every_one_of_35_sources_can_independently_withdraw_current_cash(self):
        p=json.loads(source());registry=json.loads(p['registry_source_utf8'])
        self.assertEqual(len(registry['requirements']),35)
        for i,row in enumerate(registry['evidence']):
            r=copy.deepcopy(registry);r['evidence'][i]['valid_until']=p['evaluated_as_of_UTC'];raw=enc(dict(p,registry_source_utf8=canonical(r)));run=self.pending(raw)
            self.assertTrue(any(row['requirement_id']+':evidence_expired'in b for b in run.payload['blockers']['evidence']))

    def test_self_consistent_registry_cannot_omit_a_required_child_or_add_unknown_source(self):
        def omit(r):
            r['requirements'].pop();r['evidence'].pop()
        raw=candidate(registry_change=omit);p=json.loads(raw);self.assertEqual(evaluate_evidence_currency(p['registry_source_utf8'].encode(),p['evaluated_as_of_UTC']).payload['state'],'current_synthetic_evidence')
        self.assertIn('complete_exact_settled_source_inventory_mismatch',self.pending(raw).payload['blockers']['gate'])
        def extra(r):
            row=dict(requirement_id='/unknown',source_sha256='1'*64,source_locator='/unknown');r['requirements'].append(row);r['evidence'].append(dict(r['evidence'][0],**row,evidence_id='SYNTHETIC-extra'))
        self.pending(candidate(registry_change=extra))

    def test_self_consistent_wrong_hash_and_locator_still_fail_exact_source_inventory(self):
        for key,value in(('source_sha256','0'*64),('source_locator','/wrong/location')):
            def change(r):r['requirements'][0][key]=value;r['evidence'][0][key]=value
            raw=candidate(registry_change=change);p=json.loads(raw);self.assertEqual(evaluate_evidence_currency(p['registry_source_utf8'].encode(),p['evaluated_as_of_UTC']).payload['state'],'current_synthetic_evidence')
            self.pending(raw)

    def test_review_estimate_superseded_or_missing_dates_never_becomes_authentication(self):
        fields=[('review_status','pending'),('review_status','rejected'),('value_status','estimate'),('value_status','unresolved'),('superseded_by_sha256','0'*64),('basis_ref',None),('issued_at',None),('valid_from',None),('valid_until',None)]
        for key,value in fields:self.pending(candidate(registry_change=lambda r:r['evidence'][0].update({key:value})))

    def test_explicit_as_of_start_inclusive_end_exclusive_and_no_automatic_renewal(self):
        raw=candidate(change=lambda p:p.update(evaluated_as_of_UTC='2027-01-01T00:00:00Z'));run=assemble_current_settled_case(raw);self.assertIsNotNone(run.payload['current_project_return_story'])
        self.pending(candidate(change=lambda p:p.update(evaluated_as_of_UTC='2027-07-02T00:00:00Z')))
        self.pending(candidate(change=lambda p:p.update(evaluated_as_of_UTC='2026-12-31T23:59:59Z')))
        self.assertFalse(run.payload['live_clock_or_monitor_enabled']);self.assertFalse(run.payload['automatic_source_renewal_enabled'])

    def test_missing_and_multiple_evidence_do_not_resolve_by_parent_recency(self):
        self.pending(candidate(registry_change=lambda r:r['evidence'].pop()))
        def duplicate(r):r['evidence'].append(dict(r['evidence'][0],evidence_id='SYNTHETIC-second-candidate'))
        self.pending(candidate(registry_change=duplicate))

    def test_registry_context_mismatch_with_all_dates_current_withholds_projection(self):
        raw=candidate(registry_change=lambda r:r['context'].update(run_id='SYNTHETIC-different-run'))
        self.assertIn('registry_and_settled_context_mismatch',self.pending(raw).payload['blockers']['gate'])

    def test_current_evidence_does_not_restore_blocked_accounting_calculation(self):
        run=self.pending(source('blocked'));p=json.loads(source('blocked'))
        self.assertEqual(evaluate_evidence_currency(p['registry_source_utf8'].encode(),p['evaluated_as_of_UTC']).payload['state'],'current_synthetic_evidence')
        self.assertIn('complete_settled_cash_path_blocked',run.payload['blockers']['gate'])

    def test_new_complete_same_context_case_requires_its_own_evidence(self):
        other=json.loads(source('distributed'))['case_source_utf8'];self.pending(candidate(change=lambda p:p.update(case_source_utf8=other)))
        current=assemble_current_settled_case(source('distributed'));self.assertIsNotNone(current.payload['current_project_return_story'])
        self.assertNotEqual(current.payload['current_project_return_story']['dated_net_flows'],assemble_current_settled_case(source()).payload['current_project_return_story']['dated_net_flows'])

    def test_raw_byte_identity_is_preserved_without_semantic_source_reuse(self):
        self.pending(candidate(change=lambda p:p.update(case_source_utf8=p['case_source_utf8']+'\n')))
        raw=candidate(change=lambda p:p.update(registry_source_utf8=p['registry_source_utf8']+'\n'));a,b=assemble_current_settled_case(source()),assemble_current_settled_case(raw)
        self.assertEqual(a.payload['current_project_return_story'],b.payload['current_project_return_story']);self.assertNotEqual(a.sha256,b.sha256)

    def test_one_page_full_money_reference_dates_annual_cash_criteria_and_spans(self):
        run=assemble_current_settled_case(source());report=render_settled_output(source(),run);audit=validate_report(source(),run,report);text=PdfReader(BytesIO(report.pdf_bytes)).pages[0].extract_text()
        self.assertEqual(audit['page_count'],1);self.assertIn('Por 10 aportado: cobros 6',text);self.assertIn('Neto escalado: -4',text);self.assertIn('Gasto del seguro: 20',text);self.assertIn('Pago en cierre: 5',text)
        self.assertIn('n=4 z=3',text);self.assertIn('current-results.json',text)
        self.assertIn('2026 A1400 C0 N-1400 OP0 CoC:Pte',text);self.assertIn('2027 A0 C840 N840 OP200 CoC:Pte',text)
        m=report.manifest;self.assertEqual(m['event_count'],8);self.assertEqual(m['annual_years'],[2026,2027]);self.assertEqual(m['annual_rows_omitted'],0);self.assertEqual(sorted(i for g in m['event_groups']for i in g['event_indices']),list(range(8)))
        self.assertEqual(sum(g['zero_event_count']for g in m['event_groups']),3);self.assertEqual(len(run.payload['criterion_slots']),10)

    def test_expired_and_blocked_page_contains_no_current_or_historical_money_fallback(self):
        for label in('expired','blocked'):
            raw=source(label);run=self.pending(raw);report=render_settled_output(raw,run);m=report.manifest
            self.assertTrue(m['all_current_money_withheld']);self.assertEqual(m['event_groups'],[]);self.assertEqual(m['annual_years'],[])
            for span in m['display_spans']:
                if any(ref.startswith('/current_')for ref in span['result_pointers']):self.assertIn('pendiente',span['text'].lower())
            self.assertEqual(validate_report(raw,run,report)['page_count'],1)

    def test_twelve_years_all_fit_thirteen_overflow_and_unsupported_text_are_rejected(self):
        run=assemble_current_settled_case(source());p=run.payload;s=p['current_project_return_story'];row=s['annual_cash_receipts'][0]
        s['annual_cash_receipts']=[dict(row,calendar_cash_receipt_year=2026+i)for i in range(12)];text=canonical(p);probe=replace(run,payload_json=text,sha256=digest(text));m=_render_verified(probe).manifest;self.assertEqual(len(m['annual_years']),12)
        s['annual_cash_receipts'].append(dict(row,calendar_cash_receipt_year=2038));text=canonical(p)
        with self.assertRaises(PreviewLayoutError):_render_verified(replace(run,payload_json=text,sha256=digest(text)))
        for value in('SYNTHETIC-'+('x'*1000),'SYNTHETIC-\U0001f600'):
            p=run.payload;p['context']['deal_id']=value;text=canonical(p)
            with self.assertRaises(PreviewLayoutError):_render_verified(replace(run,payload_json=text,sha256=digest(text)))

    def test_public_renderer_rejects_rehashed_run_or_other_source(self):
        run=assemble_current_settled_case(source());p=run.payload;p['current_project_return_story']['gross_distributions']={'numerator':'845','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):render_settled_output(source(),replace(run,payload_json=text,sha256=digest(text)))
        with self.assertRaises(ValidationError):render_settled_output(source()+b'\n',run)

    def test_six_file_one_PDF_recovery_replays_current_expired_and_blocked_sources(self):
        for label in('current','expired','blocked'):
            raw=source(label);values,run,report=build_current_settled_artifacts(raw);self.assertEqual(len(values),6);self.assertEqual(sum(k.endswith('.pdf')for k in values),1)
            with tempfile.TemporaryDirectory()as td:
                root=Path(td)
                for k,v in values.items():(root/k).write_bytes(v)
                self.assertEqual(recover_current_settled_directory(root),(run,report));self.assertEqual(audit_current_settled_directory(root)['files_verified'],6)

    def test_incompatible_versions_and_rehashed_PDF_result_or_inventory_are_rejected(self):
        values,_,_=build_current_settled_artifacts(source())
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for k,v in values.items():(root/k).write_bytes(v)
            for key in('current_engine_sha256','report_engine_sha256','evidence_engine_sha256'):
                restore();p=json.loads(values['package.json']);p['versions'][key]='0'*64;(root/'package.json').write_bytes(enc(p))
                with self.assertRaises(ValidationError):recover_current_settled_directory(root)
            for name,data in(('MiniUW_Resumen.pdf',b'changed'),('current-results.json',b'{}')):
                restore();p=json.loads(values['package.json']);row=next(r for r in p['files']if r['path']==name);row.update(bytes=len(data),sha256=sha(data));(root/name).write_bytes(data);(root/'package.json').write_bytes(enc(p))
                with self.assertRaises(ValidationError):recover_current_settled_directory(root)
            restore();p=json.loads(values['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(enc(p))
            with self.assertRaises(ValidationError):recover_current_settled_directory(root)

    def test_retry_no_different_overwrite_extra_symlink_size_and_own_temp_cleanup(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);out=root/'out';write_current_settled_artifacts(source(),out);before=read_current_settled_artifacts(out);self.assertEqual(write_current_settled_artifacts(source(),out)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_current_settled_artifacts(source('distributed'),out)
            self.assertEqual(read_current_settled_artifacts(out),before);(out/'extra').write_bytes(b'x')
            with self.assertRaises(ValidationError):read_current_settled_artifacts(out)
            (out/'extra').unlink();(out/'MiniUW_Resumen.pdf').unlink();(out/'MiniUW_Resumen.pdf').symlink_to(out/'current-results.json')
            with self.assertRaises(ValidationError):read_current_settled_artifacts(out)
        with patch('miniuw_foundation.settled_output_artifacts.MAX_FILE_BYTES',10):
            with self.assertRaises(ValidationError):build_current_settled_artifacts(source())
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep';keep.write_bytes(b'x')
            with patch('miniuw_foundation.settled_output_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_current_settled_artifacts(source(),root/'out')
            self.assertEqual(list(root.iterdir()),[keep])

    def test_separate_process_hash_seeds_preserve_exact_run_and_PDF(self):
        code="from pathlib import Path;from miniuw_foundation.current_settled_case import assemble_current_settled_case;from miniuw_foundation.settled_output_report import render_settled_output;from miniuw_foundation.scheduled_expense_case import sha;r=Path('templates/current-settled-current-T109.json').read_bytes();p=assemble_current_settled_case(r);print(p.sha256,sha(render_settled_output(r,p).pdf_bytes))"
        values=[]
        for seed in('1','42'):
            env=dict(os.environ,PYTHONHASHSEED=seed,PYTHONDONTWRITEBYTECODE='1');env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+os.environ.get('PYTHONPATH','')
            p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60);self.assertEqual(p.returncode,0,p.stderr);values.append(p.stdout.strip())
        self.assertEqual(values[0],values[1])

    def test_synthetic_current_evidence_does_not_adopt_criteria_financial_policy_or_authority(self):
        p=assemble_current_settled_case(source()).payload;self.assertTrue(p['synthetic_complete_source_evidence_current']);self.assertEqual(p['decision'],'PENDING');self.assertIsNone(p['personal_investor_return'])
        for key in('source_authority_verified','professional_review_authenticated','new_financial_values_generated','automatic_source_renewal_enabled','live_clock_or_monitor_enabled','original_sheet_adapter_for_this_profile_implemented','financial_model_complete','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):self.assertIs(p[key],False)
        self.assertEqual(len(p['criterion_slots']),10);self.assertTrue(all(c['threshold']is None and c['state']=='PENDING'for c in p['criterion_slots']))


if __name__=='__main__':unittest.main()
