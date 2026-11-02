"""Independent numeric expectations for the preserved source and its comparator bridge."""
import copy,json
from fractions import Fraction
from pathlib import Path
import unittest
from miniuw_foundation import ValidationError
from miniuw_foundation.threshold_rehearsal import read_documented_thresholds,prepare_rehearsal,rehearse,parse_rehearsal
from miniuw_foundation.screening import simulate_screening
from miniuw_foundation.archive import EvidenceArchive

R=Path(__file__).resolve().parents[1]
def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}
def raw(p):return json.dumps(p).encode()
def f(p):return None if p is None else Fraction(int(p['numerator']),int(p['denominator']))


class ThresholdRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.source=(R/'sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx').read_bytes()
        self.base=json.loads((R/'templates/synthetic-documented-threshold-base.json').read_bytes())
        self.full=json.loads((R/'templates/synthetic-documented-threshold-full.json').read_bytes())
    def run_case(self,p=None):return rehearse(self.source,raw(self.base if p is None else p))

    def test_all_thirty_source_cells_match_independent_exact_expectations(self):
        rows=read_documented_thresholds(self.source)['metrics']
        expected=[('YoC','13/200','23/400','21/400'),('spread','1/100','1/200','0'),
            ('equity_recovered','3/5','2/5','1/4'),('equity_cash_in','1/20','1/10','1/5'),
            ('breakeven_occupancy','17/20','9/10','93/100'),('post_refi_CoC','3/50','1/25','3/100'),
            ('asking_relative_to_supported_price','0',None,'3/20'),('equity_TDC','7/20','2/5','9/20'),
            ('IRR','3/20','3/25','1/10'),('equity_multiple','7/4','3/2','27/20')]
        self.assertEqual([(r['metric_id'],f(r['pass_base']),f(r['pass_downside']),f(r['fail_base']))for r in rows],
            [(m,Fraction(a),None if b is None else Fraction(b),Fraction(c))for m,a,b,c in expected])

    def test_missing_downside_thresholds_remain_null_without_na_inference(self):
        profile=read_documented_thresholds(self.source)
        self.assertTrue(all(m['fail_downside']is None for m in profile['metrics']))
        self.assertIsNone(profile['metrics'][6]['pass_downside'])
        _,case=prepare_rehearsal(self.source,raw(self.full));p=json.loads(case)
        down=[r for r in p['criteria']if r['scenario_id']=='Downside']
        self.assertTrue(all(r['fail_condition']=={'operator':None,'threshold':None}for r in down))
        self.assertTrue(all(r['applicability']=='applicable'for r in down))

    def test_source_changes_rejected_before_parsing_or_reusing_profile(self):
        for source in [self.source+b' ',b'not a zip',None]:
            with self.assertRaises(ValidationError):rehearse(source,raw(self.base))

    def test_source_locators_bind_literals_to_exact_original_xml_cells(self):
        from zipfile import ZipFile
        from io import BytesIO
        from xml.etree import ElementTree as ET
        from miniuw_foundation.threshold_rehearsal import NS
        profile=read_documented_thresholds(self.source)
        with ZipFile(BytesIO(self.source))as z:root=ET.fromstring(z.read('word/document.xml'))
        table=root.findall('.//w:tbl',NS)[profile['source_table_index_zero_based']]
        for index,metric in enumerate(profile['metrics'],1):
            cells=table.findall('w:tr',NS)[index].findall('w:tc',NS)
            self.assertEqual([''.join(t.text or ''for t in c.findall('.//w:t',NS))for c in cells[1:]],metric['source_literals'])
            self.assertIn('/row['+str(index)+']/cell[1]',metric['source_locators']['pass_base'])

    def test_base_only_pass_is_labelled_partial_not_full_miniuw(self):
        r=self.run_case();self.assertEqual(r['simulation_result'],'PASS');self.assertIn('Base-only',r['scope'])
        self.assertFalse(r['full_miniuw_completed']);self.assertEqual(r['decision'],'PENDING')

    def test_pass_boundaries_inclusive_for_all_ten_base_metrics(self):
        profile=read_documented_thresholds(self.source);p=copy.deepcopy(self.base)
        for row,criterion in zip(p['metric_values'],profile['metrics']):row['value']=criterion['pass_base']
        self.assertEqual(self.run_case(p)['simulation_result'],'PASS')

    def test_documented_base_failure_is_simulated_without_operational_decision(self):
        p=copy.deepcopy(self.base);p['metric_values'][0]['value']=q(5,100)
        r=self.run_case(p);self.assertEqual(r['simulation_result'],'FAIL');self.assertEqual(r['decision'],'PENDING')

    def test_intermediate_base_band_uses_user_pending_rule(self):
        p=copy.deepcopy(self.base);p['metric_values'][0]['value']=q(6,100)
        r=self.run_case(p);self.assertEqual(r['simulation_result'],'PENDING');self.assertEqual(r['comparison_states'][0]['state'],'BAND')

    def test_exact_fail_boundary_is_band_not_fail(self):
        p=copy.deepcopy(self.base);p['metric_values'][0]['value']=q(525,10000)
        self.assertEqual(self.run_case(p)['comparison_states'][0]['state'],'BAND')
        p['metric_values'][0]['value']=q(52499,1000000)
        self.assertEqual(self.run_case(p)['comparison_states'][0]['state'],'FAIL_CONDITION')

    def test_max_metric_uses_strict_failure_and_inclusive_pass(self):
        for value,state in [(q(5,100),'PASS_CONDITION'),(q(20,100),'BAND'),(q(20001,100000),'FAIL_CONDITION')]:
            p=copy.deepcopy(self.base);p['metric_values'][3]['value']=value
            self.assertEqual(self.run_case(p)['comparison_states'][3]['state'],state)

    def test_explicit_zero_threshold_and_value_are_not_missing(self):
        r=self.run_case();self.assertEqual(r['comparison_states'][6]['state'],'PASS_CONDITION')
        p=copy.deepcopy(self.base);p['metric_values'][1]['value']=q(0)
        self.assertEqual(self.run_case(p)['comparison_states'][1]['state'],'BAND')

    def test_missing_required_metric_overrides_known_failure(self):
        p=copy.deepcopy(self.base);p['metric_values'][0]['value']=q(5,100);p['metric_values'].pop()
        r=self.run_case(p);self.assertEqual(r['simulation_result'],'PENDING')
        self.assertEqual(r['comparison_states'][0]['state'],'FAIL_CONDITION')
        self.assertIn('equity_multiple:Base:metric_record_missing',r['simulation_blockers'])

    def test_full_source_table_exposes_current_comparator_integration_gap(self):
        r=self.run_case(self.full);self.assertEqual(r['simulation_result'],'PENDING')
        self.assertEqual(len(r['comparison_states']),20)
        self.assertEqual(sum('fail_condition_rule_missing_or_unsupported'in row['blockers']for row in r['comparison_states']),10)
        self.assertIn('asking_relative_to_supported_price:Downside:pass_condition_rule_missing_or_unsupported',r['simulation_blockers'])

    def test_live_deal_and_duplicate_unknown_or_outside_inventory_rejected(self):
        p=copy.deepcopy(self.base);p['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case(p)
        for mutation in ['duplicate','unknown','scenario']:
            p=copy.deepcopy(self.base)
            if mutation=='duplicate':p['metric_values'].append(copy.deepcopy(p['metric_values'][0]))
            elif mutation=='unknown':p['metric_values'][0]['metric_id']='bank_DSCR'
            else:p['metric_values'][0]['scenario_id']='Downside'
            with self.assertRaises(ValidationError):self.run_case(p)

    def test_implicit_context_extra_fields_and_numeric_float_rejected(self):
        for key,value in [('required_scenarios',[]),('run_id','')]:
            p=copy.deepcopy(self.base);p[key]=value
            with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.base);p['approved']=True
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.base);p['metric_values'][0]['value']=0.07
        with self.assertRaises(ValidationError):self.run_case(p)

    def test_compiled_case_archive_recovers_exact_case_and_run(self):
        _,case=prepare_rehearsal(self.source,raw(self.base));run=simulate_screening(case)
        with EvidenceArchive(':memory:')as archive:
            bundle=archive.load_screening(archive.save_screening(case,run))
            self.assertEqual(bundle.run,run)
            self.assertEqual(archive.get_screening_source(run.payload['source_sha256']),case)

    def test_input_unchanged_and_adoption_identity_and_verification_never_claimed(self):
        before=copy.deepcopy(self.base);r=self.run_case();self.assertEqual(before,self.base)
        for key in ['metric_values_financially_verified','thresholds_adopted','review_authenticated','production_authorized']:
            self.assertFalse(r[key])
        self.assertFalse(r['source_profile']['source_author_authenticated']);self.assertTrue(r['metric_values_are_fictitious'])
