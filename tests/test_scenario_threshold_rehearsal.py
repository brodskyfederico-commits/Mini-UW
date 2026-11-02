"""Source-specific scenario roles without invented failure rules or exclusions."""
from dataclasses import replace
import copy,hashlib,json,tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
from miniuw_foundation import ValidationError
from miniuw_foundation.drafts import canonical,digest
from miniuw_foundation.scenario_threshold_rehearsal import simulate_scenario_thresholds
from miniuw_foundation.threshold_rehearsal import rehearse
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence

R=Path(__file__).resolve().parents[1]
def raw(p):return json.dumps(p).encode()
def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}


class ScenarioThresholdTests(unittest.TestCase):
    def setUp(self):
        self.doc=(R/'sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx').read_bytes()
        self.base=json.loads((R/'templates/synthetic-documented-threshold-base.json').read_bytes())
        self.full=json.loads((R/'templates/synthetic-documented-threshold-full.json').read_bytes())
    def run_case(self,p=None):return simulate_scenario_thresholds(self.doc,raw(self.full if p is None else p))
    def row(self,run,metric,scenario='Downside'):
        return next(r for r in run.payload['comparisons']if r['metric_id']==metric and r['scenario_id']==scenario)
    def value(self,p,metric,amount,scenario='Downside'):
        next(r for r in p['metric_values']if r['metric_id']==metric and r['scenario_id']==scenario)['value']=amount

    def test_nine_downside_rows_pass_without_requiring_invented_fail_thresholds(self):
        run=self.run_case();rows=[r for r in run.payload['comparisons']if r['scenario_id']=='Downside']
        self.assertEqual(sum(r['state']=='PASS_CONDITION'for r in rows),9)
        self.assertTrue(all(r['fail_condition']is None and not r['fail_condition_required_by_profile']for r in rows))
        self.assertEqual(run.payload['simulation_blockers'],['asking_relative_to_supported_price:Downside:pass_condition_and_applicability_unresolved'])

    def test_asking_dash_remains_unresolved_even_when_value_is_zero(self):
        run=self.run_case();row=self.row(run,'asking_relative_to_supported_price')
        self.assertEqual(row['applicability'],'unresolved');self.assertEqual(row['state'],'PENDING')
        self.assertFalse(run.payload['asking_downside_applicability_resolved'])
        self.assertEqual(run.payload['simulation_result'],'PENDING')

    def test_downside_min_threshold_equality_passes_and_below_is_pending_not_fail(self):
        for amount,state in [(q(575,10000),'PASS_CONDITION'),(q(57499,1000000),'PASS_MISS_PENDING')]:
            p=copy.deepcopy(self.full);self.value(p,'YoC',amount)
            run=self.run_case(p);self.assertEqual(self.row(run,'YoC')['state'],state)
            self.assertEqual(run.payload['simulation_result'],'PENDING')

    def test_downside_max_threshold_equality_passes_and_above_is_pending(self):
        for amount,state in [(q(10,100),'PASS_CONDITION'),(q(10001,100000),'PASS_MISS_PENDING')]:
            p=copy.deepcopy(self.full);self.value(p,'equity_cash_in',amount)
            self.assertEqual(self.row(self.run_case(p),'equity_cash_in')['state'],state)

    def test_downside_below_base_failure_line_does_not_create_downside_fail(self):
        p=copy.deepcopy(self.full);self.value(p,'YoC',q(1,100))
        run=self.run_case(p);self.assertEqual(self.row(run,'YoC')['state'],'PASS_MISS_PENDING')
        self.assertNotIn('FAIL_CONDITION',[r['state']for r in run.payload['comparisons']if r['scenario_id']=='Downside'])

    def test_base_only_pass_fail_and_intermediate_band_preserve_canonical_behavior(self):
        for amount,state in [(q(7,100),'PASS'),(q(5,100),'FAIL'),(q(6,100),'PENDING'),(q(525,10000),'PENDING')]:
            p=copy.deepcopy(self.base);self.value(p,'YoC',amount,'Base')
            self.assertEqual(self.run_case(p).payload['simulation_result'],state)

    def test_missing_downside_value_and_absent_record_remain_distinct(self):
        p=copy.deepcopy(self.full);self.value(p,'IRR',None)
        self.assertEqual(self.row(self.run_case(p),'IRR')['blockers'],['metric_value_missing'])
        p['metric_values']=[r for r in p['metric_values']if not(r['metric_id']=='IRR'and r['scenario_id']=='Downside')]
        self.assertEqual(self.row(self.run_case(p),'IRR')['blockers'],['metric_record_missing'])

    def test_known_base_failure_plus_unresolved_required_scope_stays_pending(self):
        p=copy.deepcopy(self.full);self.value(p,'YoC',q(5,100),'Base')
        run=self.run_case(p);self.assertEqual(self.row(run,'YoC','Base')['state'],'FAIL_CONDITION')
        self.assertEqual(run.payload['simulation_result'],'PENDING')

    def test_source_and_synthetic_context_guards_are_not_bypassed(self):
        with self.assertRaises(ValidationError):simulate_scenario_thresholds(self.doc+b' ',raw(self.full))
        p=copy.deepcopy(self.full);p['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case(p)
        p=copy.deepcopy(self.full);p['applicability_override']='approved'
        with self.assertRaises(ValidationError):self.run_case(p)

    def test_policy_and_source_verdict_rules_bound_to_the_run(self):
        run=self.run_case();p=run.payload
        self.assertEqual(p['source_sha256'],hashlib.sha256(self.doc).hexdigest())
        self.assertEqual(len(p['source_verdict_references']),2)
        self.assertTrue(all('descendant-paragraph['in r['locator']for r in p['source_verdict_references']))
        self.assertEqual(p['user_policy_reference'],json.loads(p['base_run']['payload_json'])['user_policy_reference'])

    def test_payload_copy_does_not_change_run_or_source_case(self):
        before=copy.deepcopy(self.full);run=self.run_case();payload=run.payload
        payload['comparisons'][0]['state']='forged';self.assertNotEqual(run.payload['comparisons'][0]['state'],'forged')
        self.assertEqual(before,self.full)

    def test_raw_case_identity_and_source_bytes_are_retained(self):
        original=raw(self.full);a=simulate_scenario_thresholds(self.doc,original);b=simulate_scenario_thresholds(self.doc,original+b'\n')
        self.assertNotEqual(a.sha256,b.sha256);self.assertEqual(a.payload['case_source_sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(a.payload['simulation_result'],b.payload['simulation_result'])

    def test_reopened_archive_restores_docx_case_and_result_exactly(self):
        case=raw(self.full);run=self.run_case()
        with tempfile.TemporaryDirectory()as temporary:
            path=Path(temporary)/'scenario.sqlite3'
            with EvidenceArchive(path)as archive:
                key=archive.save_scenario_thresholds(self.doc,case,run)
                self.assertEqual(key,archive.save_scenario_thresholds(self.doc,case,run))
            with EvidenceArchive(path)as archive:
                bundle=archive.load_scenario_thresholds(key);self.assertEqual(bundle.run,run)
                self.assertEqual(archive.get_documented_threshold_source(bundle.payload['document_source_sha256']),self.doc)
                self.assertEqual(archive.get_scenario_threshold_case(bundle.payload['case_source_sha256']),case)

    def test_forged_result_rejected_before_capture_and_on_replay_even_with_new_hash(self):
        run=self.run_case();payload=run.payload;payload['simulation_result']='PASS';encoded=canonical(payload)
        forged=replace(run,payload_json=encoded,sha256=digest(encoded))
        with EvidenceArchive(':memory:')as archive:
            with self.assertRaises(ValidationError):archive.save_scenario_thresholds(self.doc,raw(self.full),forged)
            key=archive.save_scenario_thresholds(self.doc,raw(self.full),run);body=json.loads(archive.read_bundle_bytes(key))
            body['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with archive._transaction():bad=archive._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):archive.load_scenario_thresholds(bad)

    def test_atomic_archive_failure_leaves_no_partial_sources_or_bundle(self):
        run=self.run_case()
        with EvidenceArchive(':memory:')as archive:
            with patch.object(archive,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):archive.save_scenario_thresholds(self.doc,raw(self.full),run)
            self.assertEqual(archive._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)

    def test_unsupported_versions_and_missing_evidence_are_explicit(self):
        run=self.run_case()
        with EvidenceArchive(':memory:')as archive:
            key=archive.save_scenario_thresholds(self.doc,raw(self.full),run);body=json.loads(archive.read_bundle_bytes(key))
            body['versions'][0]='0'*64
            with archive._transaction():bad=archive._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):archive.load_scenario_thresholds(bad)
            archive._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',run.payload['source_sha256']))
            with self.assertRaises(MissingEvidence):archive.load_scenario_thresholds(key)

    def test_old_comparator_experiment_retains_its_eleven_gaps(self):
        old=rehearse(self.doc,raw(self.full));self.assertEqual(len(old['simulation_blockers']),11)
        self.assertEqual(len(self.run_case().payload['simulation_blockers']),1)

    def test_no_real_decision_adoption_verification_or_full_run_claimed(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for k in ['thresholds_adopted','financial_values_verified','run_ready','review_authenticated','production_authorized','full_miniuw_completed']:
            self.assertFalse(p[k])
