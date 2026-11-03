import copy
import unittest
from miniuw_foundation.drafts import ValidationError,ContextSeed
from miniuw_foundation.evidence_currency import parse_evidence_currency,evaluate_evidence_currency,timestamp
from evidence_currency_test_support import registry,raw,AS_OF


class EvidenceCurrencyTests(unittest.TestCase):
    def setUp(self):
        self.p=registry(dict(deal_id='SYNTHETIC-currency-test',scenario_id='SYNTHETIC-Base',run_id='SYNTHETIC-currency-run',definition_set_revision='SYNTHETIC-explicit-validity'),
            [dict(requirement_id='income',source_sha256='1'*64,source_locator='Sheet!B2')])
    def run_case(self,at=AS_OF):return evaluate_evidence_currency(raw(self.p),at)

    def test_current_with_explicit_interval_and_source(self):
        p=self.run_case().payload;self.assertEqual(p['state'],'current_synthetic_evidence')
        self.assertEqual(p['requirements'][0]['state'],'current_synthetic');self.assertEqual(p['decision'],'PENDING')

    def test_exact_start_included_and_expiry_excluded(self):
        self.assertEqual(self.run_case('2027-07-01T00:00:00Z').payload['state'],'current_synthetic_evidence')
        self.assertEqual(self.run_case('2027-07-31T23:59:59Z').payload['state'],'current_synthetic_evidence')
        p=self.run_case('2027-08-01T00:00:00Z').payload
        self.assertIn('income:evidence_expired',p['blockers']);self.assertEqual(p['state'],'PENDING')

    def test_future_and_not_issued_evidence_pending(self):
        p=self.run_case('2027-05-31T23:59:59Z').payload
        self.assertIn('income:evidence_not_yet_current',p['blockers'])

    def test_no_missing_date_becomes_unlimited_or_default_TTL(self):
        before=copy.deepcopy(self.p)
        for key in ['issued_at','valid_from','valid_until']:
            self.p=copy.deepcopy(before);self.p['evidence'][0][key]=None
            self.assertIn('income:explicit_validity_dates_missing_no_inferred_TTL',self.run_case().payload['blockers'])

    def test_invalid_interval_order_blocks(self):
        for key,value in [('valid_until','2027-07-01T00:00:00Z'),('issued_at','2027-07-02T00:00:00Z')]:
            self.p['evidence'][0][key]=value
            self.assertIn('income:validity_date_order_invalid',self.run_case().payload['blockers'])

    def test_review_pending_or_rejected_cannot_unlock(self):
        for status in ['pending','rejected']:
            self.p['evidence'][0]['review_status']=status
            self.assertEqual(self.run_case().payload['state'],'PENDING')

    def test_estimate_and_unresolved_remain_pending(self):
        for status in ['estimate','unresolved']:
            self.p['evidence'][0]['value_status']=status
            self.assertIn('income:value_'+status,self.run_case().payload['blockers'])

    def test_superseded_record_not_replaced_automatically(self):
        self.p['evidence'][0]['superseded_by_sha256']='2'*64
        p=self.run_case().payload;self.assertIn('income:evidence_superseded',p['blockers'])
        self.assertEqual(p['requirements'][0]['evidence_records'][0]['source_sha256'],'1'*64)

    def test_hash_and_locator_mismatch_preserved(self):
        for key,value in [('source_sha256','2'*64),('source_locator','Sheet!B3')]:
            self.p['evidence'][0][key]=value
            p=self.run_case().payload;self.assertIn('income:source_hash_or_locator_mismatch',p['blockers'])
            self.assertEqual(p['requirements'][0]['evidence_records'][0][key],value)

    def test_missing_evidence_and_multiple_records_no_latest_wins(self):
        record=copy.deepcopy(self.p['evidence'][0]);self.p['evidence']=[]
        self.assertIn('income:required_evidence_missing',self.run_case().payload['blockers'])
        second=copy.deepcopy(record);second['evidence_id']+='-revision';second['issued_at']='2027-06-02T00:00:00Z'
        self.p['evidence']=[record,second]
        self.assertIn('income:multiple_evidence_records_require_explicit_resolution',self.run_case().payload['blockers'])

    def test_missing_basis_and_incomplete_inventory_block(self):
        self.p['evidence'][0]['basis_ref']=None;self.assertEqual(self.run_case().payload['state'],'PENDING')
        self.p['evidence'][0]['basis_ref']='SYNTHETIC-restored'
        for key,value in [('inventory_declared_complete',False),('inventory_basis_ref',None)]:
            self.p[key]=value;self.assertEqual(self.run_case().payload['state'],'PENDING')

    def test_unknown_requirement_record_not_ignored(self):
        self.p['evidence'][0]['requirement_id']='unknown'
        p=self.run_case().payload;self.assertIn('evidence_for_unknown_requirement',p['blockers'])

    def test_timestamp_strict_UTC_and_valid_calendar(self):
        for value in ['2027-07-01','2027-07-01T00:00:00+00:00','2027-07-01T00:00:00.0Z','2027-02-29T00:00:00Z',None]:
            with self.assertRaises(ValidationError):self.run_case(value)

    def test_duplicate_requirement_or_record_and_transport_bounds(self):
        self.p['requirements']*=2
        with self.assertRaises(ValidationError):self.run_case()
        self.p['requirements']=self.p['requirements'][:1];self.p['evidence']*=2
        with self.assertRaises(ValidationError):self.run_case()
        for value in [b'[]',b'NaN',b'\xff',b' '*1048577,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_evidence_currency(value)

    def test_real_context_and_professional_status_rejected(self):
        self.p['context']['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case()
        self.p['context']['deal_id']='SYNTHETIC-test';self.p['evidence'][0]['review_status']='professional_approved'
        with self.assertRaises(ValidationError):self.run_case()

    def test_evaluation_time_changes_run_but_not_source(self):
        before=copy.deepcopy(self.p);a=self.run_case();b=self.run_case('2027-08-01T00:00:00Z')
        self.assertNotEqual(a.sha256,b.sha256);self.assertEqual(a.payload['source_sha256'],b.payload['source_sha256']);self.assertEqual(self.p,before)

    def test_no_authentication_monitor_or_authority_claim(self):
        p=self.run_case().payload
        for key in ['review_authenticated','source_authority_verified','financial_policy_adopted','automatic_clock_or_monitor_enabled','real_decisions_enabled','production_authorized']:
            self.assertIs(p[key],False)


if __name__=='__main__':unittest.main()
