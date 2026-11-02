from dataclasses import asdict,replace
from fractions import Fraction
import json,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from miniuw_foundation import ValidationError
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive
from miniuw_foundation.screening import SCHEMA,AGGREGATION,simulate_screening,parse_screening_case
from miniuw_foundation.drafts import canonical,digest
from test_foundation import seed


def q(n,d=1):return {'numerator':str(n),'denominator':str(d)}
def case():
    values=[];criteria=[]
    for metric,amount,passing,failing in [('YoC',q(6,100),q(5,100),q(4,100)),('IRR',q(18,100),q(15,100),q(10,100))]:
        for scenario in ['Base','Downside']:
            base={'metric_id':metric,'scenario_id':scenario,'definition_ref':'SYNTHETIC-'+metric+'-v1','unit':'fraction','quantity_kind':'scalar','currency':None,'period_ref':'SYNTHETIC-scope-1','applicability':'applicable','applicability_evidence_ref':None}
            values.append(dict(base,value=amount))
            criteria.append(dict(base,pass_condition={'operator':'>=','threshold':passing},fail_condition={'operator':'<','threshold':failing}))
    return {'schema':SCHEMA,'context':asdict(seed()),'case_id':'SYNTHETIC-screen-1','criteria_revision':'SYNTHETIC-criteria-v1','criteria_status':'synthetic_fixture_only','required_metrics':['YoC','IRR'],'required_scenarios':['Base','Downside'],'metric_values':values,'criteria':criteria,'aggregation_rule':AGGREGATION,'hypothetical_band_policy':None}


def encoded(p):return json.dumps(p).encode()


class ScreeningTests(unittest.TestCase):
    def test_complete_explicit_case_simulates_pass_but_operational_decision_pending(self):
        p=simulate_screening(encoded(case())).payload
        self.assertEqual(p['simulation_result'],'PASS');self.assertEqual(p['decision'],'PENDING')
        self.assertFalse(p['criteria_adopted']);self.assertFalse(p['production_authorized']);self.assertFalse(p['review_authenticated'])

    def test_complete_known_fail_simulates_fail_only(self):
        p=case();p['metric_values'][0]['value']=q(3,100)
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'FAIL')

    def test_missing_data_overrides_known_fail_without_partial_decision(self):
        p=case();p['metric_values'][0]['value']=q(3,100);p['metric_values'][1]['value']=None
        run=simulate_screening(encoded(p)).payload
        self.assertEqual(run['comparisons'][0]['state'],'FAIL_CONDITION')
        self.assertEqual(run['simulation_result'],'PENDING')

    def test_missing_criterion_or_operator_threshold_is_pending_not_zero(self):
        for mutator in [lambda p:p['criteria'].pop(),lambda p:p['criteria'][0]['pass_condition'].update(operator=None),lambda p:p['criteria'][0]['fail_condition'].update(threshold=None)]:
            p=case();mutator(p);self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')

    def test_missing_metric_record_and_scenario_are_not_skipped(self):
        p=case();p['metric_values'].pop()
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')
        p=case();p['required_scenarios'].append('Extra')
        self.assertEqual(len(simulate_screening(encoded(p)).payload['comparisons']),6)
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')

    def test_band_preserved_with_both_explicit_hypothetical_policies(self):
        p=case();p['metric_values'][1]['value']=q(45,1000)
        a=simulate_screening(encoded(p)).payload
        self.assertEqual(a['comparisons'][1]['state'],'BAND');self.assertEqual(a['simulation_result'],'PENDING')
        p['hypothetical_band_policy']='pending'
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')
        p['hypothetical_band_policy']='fail';b=simulate_screening(encoded(p)).payload
        self.assertEqual(b['comparisons'][1]['state'],'BAND');self.assertEqual(b['simulation_result'],'FAIL')
        self.assertFalse(b['criteria_adopted']);self.assertEqual(b['decision'],'PENDING')

    def test_conflicting_regions_block_even_outside_their_overlap(self):
        p=case();p['criteria'][0]['pass_condition']['threshold']=q(3,100)
        # PASS >=3%, FAIL <4% overlap even though the observed 6% is outside overlap.
        run=simulate_screening(encoded(p)).payload
        self.assertEqual(run['comparisons'][0]['state'],'CONFLICT');self.assertEqual(run['simulation_result'],'PENDING')

    def test_strict_and_inclusive_equality_is_not_inferred(self):
        p=case();p['metric_values'][0]['value']=q(5,100)
        self.assertEqual(simulate_screening(encoded(p)).payload['comparisons'][0]['state'],'PASS_CONDITION')
        p['criteria'][0]['pass_condition']['operator']='>'
        self.assertEqual(simulate_screening(encoded(p)).payload['comparisons'][0]['state'],'BAND')
        p=case();p['metric_values'][0]['value']=q(4,100)
        self.assertEqual(simulate_screening(encoded(p)).payload['comparisons'][0]['state'],'BAND')
        p['criteria'][0]['fail_condition']['operator']='<='
        self.assertEqual(simulate_screening(encoded(p)).payload['comparisons'][0]['state'],'FAIL_CONDITION')

    def test_lower_is_better_only_when_operators_explicit(self):
        p=case();p['criteria'][0]['pass_condition']={'operator':'<=','threshold':q(7,100)};p['criteria'][0]['fail_condition']={'operator':'>','threshold':q(8,100)}
        self.assertEqual(simulate_screening(encoded(p)).payload['comparisons'][0]['state'],'PASS_CONDITION')

    def test_unrounded_boundary_and_explicit_zero(self):
        p=case();p['metric_values'][0]['value']=q(49999,1000000)
        self.assertEqual(simulate_screening(encoded(p)).payload['comparisons'][0]['state'],'BAND')
        p['metric_values'][0]['value']=q(0);p['criteria'][0]['pass_condition']['threshold']=q(0);p['criteria'][0]['fail_condition']['threshold']=q(0)
        self.assertEqual(simulate_screening(encoded(p)).payload['comparisons'][0]['state'],'PASS_CONDITION')

    def test_definition_unit_period_currency_mismatch_blocks(self):
        for field,value in [('definition_ref','other'),('unit','percent'),('period_ref','other'),('currency','USD'),('quantity_kind','money')]:
            p=case();p['metric_values'][0][field]=value
            self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')

        p=case()
        for k in ('metric_values','criteria'):p[k][0]['quantity_kind']='money'
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')

    def test_unresolved_applicability_or_unaudited_na_cannot_hide_failure(self):
        p=case();p['metric_values'][0]['applicability']='unresolved'
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')
        for key in ['metric_values','criteria']:
            p[key][0]['applicability']='not_applicable';p[key][0]['applicability_evidence_ref']=None
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')
        for key in ['metric_values','criteria']:p[key][0]['applicability_evidence_ref']='SYNTHETIC-declared-waiver'
        run=simulate_screening(encoded(p)).payload
        self.assertEqual(run['comparisons'][0]['state'],'NOT_APPLICABLE_DECLARED')
        self.assertFalse(run['declared_inventory_verified'])

    def test_all_na_does_not_vacuously_pass(self):
        p=case()
        for key in ['metric_values','criteria']:
            for row in p[key]:row.update(applicability='not_applicable',applicability_evidence_ref='SYNTHETIC-waiver')
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')

    def test_aggregation_must_be_explicit(self):
        p=case();p['aggregation_rule']=None
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')

    def test_duplicate_extra_and_bank_metric_records_rejected(self):
        for mutator in [lambda p:p['metric_values'].append(dict(p['metric_values'][0])),lambda p:p['metric_values'][0].update(scenario_id='Upside'),lambda p:p['required_metrics'].append('DSCR')]:
            p=case();mutator(p)
            with self.assertRaises(ValidationError):parse_screening_case(encoded(p))

    def test_synthetic_marker_context_and_review_are_not_faked(self):
        for mutator in [lambda p:p.update(criteria_status='approved'),lambda p:p['context'].update(deal_id='REAL-deal'),lambda p:p.update(approved=True)]:
            p=case();mutator(p)
            with self.assertRaises(ValidationError):parse_screening_case(encoded(p))

    def test_fresh_case_never_inherits_other_deal_criteria(self):
        simulate_screening(encoded(case()))
        p=case();p['case_id']='other';p['context']['deal_id']='SYNTHETIC-other';p['criteria']=[]
        self.assertEqual(simulate_screening(encoded(p)).payload['simulation_result'],'PENDING')

    def test_criteria_revision_changes_run_identity_and_locator_provenance(self):
        p=case();first=simulate_screening(encoded(p));p['criteria_revision']='SYNTHETIC-v2';second=simulate_screening(encoded(p))
        self.assertNotEqual(first.sha256,second.sha256)
        self.assertEqual(first.payload['comparisons'][0]['metric_locator'],'/metric_values/0/value')
        self.assertEqual(first.payload['comparisons'][0]['criterion_locator'],'/criteria/0')

    def test_archive_reopens_and_reproduces_case_source_and_result(self):
        raw=encoded(case());run=simulate_screening(raw)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'screen.sqlite3'
            with EvidenceArchive(path) as archive:key=archive.save_screening(raw,run)
            with EvidenceArchive(path) as archive:
                restored=archive.load_screening(key)
                self.assertEqual(restored.run,run)
                self.assertEqual(archive.get_screening_source(restored.payload['source_sha256']),raw)

    def test_recomputed_hash_does_not_authorize_forged_simulation(self):
        raw=encoded(case());run=simulate_screening(raw);p=run.payload;p['simulation_result']='FAIL';s=canonical(p);forged=replace(run,payload_json=s,sha256=digest(s))
        with EvidenceArchive(':memory:') as archive:
            with self.assertRaises(ValidationError):archive.save_screening(raw,forged)
            key=archive.save_screening(raw,run);bundle=json.loads(archive.read_bundle_bytes(key));bundle['run']=asdict(forged)
            with archive._transaction():bad=archive._put('bundle',canonical(bundle).encode())
            with self.assertRaises(CorruptArchive):archive.load_screening(bad)

    def test_archive_atomic_failure_and_version_requirement(self):
        raw=encoded(case());run=simulate_screening(raw)
        with EvidenceArchive(':memory:') as archive:
            with patch.object(archive,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):archive.save_screening(raw,run)
            self.assertEqual(archive._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=archive.save_screening(raw,run);bundle=json.loads(archive.read_bundle_bytes(key));bundle['engine_sha256']='0'*64
            with archive._transaction():bad=archive._put('bundle',canonical(bundle).encode())
            with self.assertRaises(UnsupportedArchive):archive.load_screening(bad)

if __name__=='__main__':unittest.main()
