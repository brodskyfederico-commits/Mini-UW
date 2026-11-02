from dataclasses import replace
from io import BytesIO
from pathlib import Path
import copy,hashlib,json,unittest
from pypdf import PdfReader
from miniuw_foundation import ValidationError
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.scenario_threshold_rehearsal import simulate_scenario_thresholds
from miniuw_foundation.synthetic_onepager import render_synthetic_onepager,PreviewLayoutError
from test_scenario_review import source,base_case,raw,q


class SyntheticOnepagerTests(unittest.TestCase):
    def setUp(self):
        self.doc=source();self.case=base_case(True);self.run=simulate_scenario_thresholds(self.doc,self.case)
    def render(self,case=None):
        case=self.case if case is None else case;run=simulate_scenario_thresholds(self.doc,case)
        return render_synthetic_onepager(self.doc,case,run)
    def text(self,pdf):return PdfReader(BytesIO(pdf)).pages[0].extract_text()

    def test_pdf_is_exactly_one_landscape_page_with_no_active_content(self):
        p=self.render();reader=PdfReader(BytesIO(p.pdf_bytes));self.assertEqual(len(reader.pages),1)
        page=reader.pages[0];self.assertEqual(tuple(page.mediabox), (0,0,792,612))
        self.assertNotIn('/Annots',page);self.assertNotIn('/OpenAction',reader.trailer['/Root']);self.assertNotIn('/Names',reader.trailer['/Root'])
    def test_all_ten_metrics_and_required_blockers_are_present(self):
        p=self.render();text=self.text(p.pdf_bytes)
        self.assertEqual(len(p.manifest['displayed_metrics']),10)
        for row in p.manifest['displayed_metrics']:self.assertIn(row['base_value'],text)
        self.assertEqual(p.manifest['blockers_displayed'],self.run.payload['simulation_blockers'])
        for blocker in p.manifest['blocker_display_texts']:self.assertIn(blocker,text)
        self.assertIn('SIN REGLA',text)
    def test_pending_and_internal_status_cannot_be_confused_with_operational_pass(self):
        text=self.text(self.render().pdf_bytes)
        for marker in ['VISTA SINTETICA INTERNA','ESTADO OPERATIVO: PENDIENTE','No publicar como dictamen','NO adoptados']:self.assertIn(marker,text)
    def test_base_only_pass_is_identified_as_partial_and_downside_not_tested(self):
        case=json.loads(base_case());case['metric_values'][0]['value']=q(7,100);p=self.render(raw(case));text=self.text(p.pdf_bytes)
        self.assertIn('Simulacion: PASS | Alcance: Solo Base',text);self.assertIn('NO ENSAYADO',text)
        self.assertIn('ESTADO OPERATIVO: PENDIENTE',text)
    def test_display_scaling_is_exact_for_percent_bps_and_multiple(self):
        rows={r['metric_id']:r for r in self.render().manifest['displayed_metrics']}
        self.assertEqual(rows['YoC']['base_value'],'6%');self.assertEqual(rows['spread']['base_value'],'150 bps');self.assertEqual(rows['equity_multiple']['base_value'],'2x')
    def test_unrounded_boundary_remains_visible_and_matches_comparison(self):
        case=json.loads(base_case());case['metric_values'][0]['value']=q(64999,1000000);p=self.render(raw(case))
        row=p.manifest['displayed_metrics'][0];self.assertEqual(row['base_value'],'6.4999%');self.assertEqual(row['base_state'],'BANDA')
    def test_pdf_strings_escape_parentheses_and_backslashes_without_injection(self):
        case=json.loads(base_case());case['case_id']='SYNTHETIC-(escaped)\\marker';p=self.render(raw(case))
        self.assertIn('SYNTHETIC-(escaped)\\marker',self.text(p.pdf_bytes));self.assertEqual(len(PdfReader(BytesIO(p.pdf_bytes)).pages),1)
    def test_control_or_unrepresentable_identity_is_blocked_not_replaced(self):
        for value in ['SYNTHETIC-injection\nPASS','SYNTHETIC-\U0001f600']:
            case=json.loads(base_case());case['case_id']=value
            with self.assertRaises(PreviewLayoutError):self.render(raw(case))
    def test_oversized_identity_and_blockers_fail_before_delivering_pdf(self):
        case=json.loads(base_case());case['case_id']='SYNTHETIC-'+('x'*200)
        with self.assertRaises(PreviewLayoutError):self.render(raw(case))
        case=json.loads(base_case());case['metric_values']=[]
        with self.assertRaises(PreviewLayoutError):self.render(raw(case))
    def test_forged_or_cross_case_result_is_rejected_before_rendering(self):
        p=self.run.payload;p['simulation_result']='PASS';encoded=canonical(p);forged=replace(self.run,payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):render_synthetic_onepager(self.doc,self.case,forged)
        with self.assertRaises(ValidationError):render_synthetic_onepager(self.doc,base_case(),self.run)
    def test_manifest_binds_actual_pdf_and_all_input_versions(self):
        p=self.render();self.assertEqual(p.manifest['pdf_sha256'],hashlib.sha256(p.pdf_bytes).hexdigest())
        self.assertEqual(p.manifest['scenario_run_sha256'],self.run.sha256);self.assertEqual(p.manifest['case_sha256'],hashlib.sha256(self.case).hexdigest())
        altered=p.manifest;altered['decision']='PASS';self.assertEqual(p.manifest['decision'],'PENDING')
        self.assertFalse(p.manifest['publication_authorized']);self.assertFalse(p.manifest['financial_values_verified'])
    def test_output_is_deterministic_for_exact_same_evidence(self):
        self.assertEqual(self.render(),self.render())
