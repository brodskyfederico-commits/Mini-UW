import copy,json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.refinance_capacity import size_refinance,parse_refinance_capacity,RefinanceInputs
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from capacity_test_support import load_capacity,build_capacity,raw,sha

def num(n):return q(F(n))
def f(q):return F(int(q['numerator']),int(q['denominator']))


class RefinanceCapacityTests(unittest.TestCase):
    def setUp(self):self.data=load_capacity()
    def run_case(self):return size_refinance(*build_capacity(self.data))
    def test_independent_valuation_and_tied_ltv_dscr_capacity(self):
        p=self.run_case().payload;self.assertEqual(p['state'],'compatible_synthetic_refinance_capacity')
        self.assertEqual(f(p['computed_property_value']),F(10)/F(1,20));self.assertEqual(f(p['regular_annual_sizing_constant']),F(12,120))
        self.assertEqual(f(p['capacity_limits']['LTV']),100);self.assertEqual(f(p['capacity_limits']['DSCR']),F(12)/(F(6,5)*F(1,10)))
        self.assertEqual(p['binding_limit_ids'],['DSCR','LTV']);self.assertEqual(f(p['selected_principal']),100)
    def test_selected_principal_can_stay_below_capacity_without_increase(self):
        self.data['loan']['principal']=num(90);self.data['closing']['amounts']['gross_proceeds']['value']=num(90);self.data['closing']['new_loan']['principal_after_closing']['value']=num(90);self.data['spec']['selected_principal']['value']=num(90)
        p=self.run_case().payload;self.assertEqual(p['state'],'compatible_synthetic_refinance_capacity');self.assertEqual(f(p['maximum_principal_capacity']),100);self.assertEqual(f(p['selected_principal']),90)
    def test_original_integrated_project_is_blocked_by_declared_bank_capacity(self):
        self.data=load_capacity('project');p=self.run_case().payload;self.assertEqual(f(p['computed_property_value']),500)
        self.assertEqual(f(p['maximum_principal_capacity']),F(30301000,3090903));self.assertEqual(f(p['selected_principal']),F('303.01'))
        self.assertEqual(p['binding_limit_ids'],['DSCR']);self.assertIn('selected_principal_exceeds_declared_bank_capacity',p['blockers']);self.assertEqual(p['decision'],'PENDING')
    def test_distinct_bank_and_valuation_noi_never_substituted(self):
        self.data['bank']['income_rows'][0]['value']=num(6);p=self.run_case().payload
        self.assertEqual(f(p['computed_property_value']),200);self.assertEqual(f(p['maximum_principal_capacity']),50);self.assertEqual(p['state'],'blocked')
    def test_additional_limits_and_ties_are_all_retained(self):
        amount=copy.deepcopy(self.data['spec']['selected_principal']);amount.update(value=num(80),basis='additional_bank_principal_limit')
        self.data['spec']['other_limits']=[dict(limit_id='TERM-SHEET',amount=amount)];p=self.run_case().payload;self.assertEqual(f(p['maximum_principal_capacity']),80);self.assertEqual(p['binding_limit_ids'],['TERM-SHEET'])
        amount['value']=num(100);p=self.run_case().payload;self.assertEqual(p['binding_limit_ids'],['DSCR','LTV','TERM-SHEET'])
    def test_missing_other_limit_inventory_or_amount_never_assumed_unlimited(self):
        for key,value in [('other_limits_declared_complete',None),('other_limits_declared_complete',False),('other_limits_basis_ref',None)]:
            d=load_capacity();d['spec'][key]=value;self.assertIsNone(size_refinance(*build_capacity(d)).payload['maximum_principal_capacity'])
        amount=copy.deepcopy(self.data['spec']['selected_principal']);amount.update(value=None,basis='additional_bank_principal_limit');self.data['spec']['other_limits']=[dict(limit_id='UNKNOWN',amount=amount)]
        self.assertIsNone(self.run_case().payload['maximum_principal_capacity'])
    def test_cap_and_dscr_nonpositive_or_missing_block_without_financial_fail(self):
        for key in ['cap_rate','minimum_dscr']:
            for value in [None,num(0),num(-1)]:
                d=load_capacity();d['spec']['parameters'][key]['value']=value;p=size_refinance(*build_capacity(d)).payload
                self.assertIsNone(p['maximum_principal_capacity']);self.assertEqual(p['decision'],'PENDING')
    def test_ltv_above_one_not_clamped_by_an_invented_policy(self):
        self.data['spec']['parameters']['maximum_ltv']['value']=num(F(3,2));p=self.run_case().payload;self.assertEqual(f(p['capacity_limits']['LTV']),300)
        self.data['spec']['parameters']['maximum_ltv']['value']=num(-1);self.assertIsNone(self.run_case().payload['maximum_principal_capacity'])
    def test_explicit_zero_capacity_and_loan_keep_dscr_undefined(self):
        self.data['bank']['income_rows'][0]['value']=num(0);self.data['loan']['principal']=num(0);self.data['spec']['selected_principal']['value']=num(0)
        self.data['closing']['amounts']['gross_proceeds']['value']=num(0);self.data['closing']['new_loan']['principal_after_closing']['value']=num(0);self.data['closing']['equity_funding_assumption_ref']='SYNTHETIC-explicit-zero-debt-funding-scenario'
        p=self.run_case().payload;self.assertEqual(f(p['maximum_principal_capacity']),0);self.assertEqual(p['state'],'compatible_synthetic_refinance_capacity');self.assertIsNone(p['achieved_dscr_annual_sizing_only']);self.assertEqual(p['achieved_dscr_undefined_reason'],'zero_selected_service')
    def test_negative_noi_does_not_create_negative_value_or_debt(self):
        for role in ['valuation','bank']:
            d=load_capacity();d[role]['expense_rows'][0]['value']=num(100);p=size_refinance(*build_capacity(d)).payload;self.assertIsNone(p['maximum_principal_capacity']);self.assertEqual(p['state'],'blocked')
    def test_missing_selected_principal_keeps_capacity_but_not_selection(self):
        self.data['spec']['selected_principal']['value']=None;p=self.run_case().payload;self.assertEqual(f(p['maximum_principal_capacity']),100);self.assertEqual(p['state'],'blocked')
    def test_gross_draw_principal_origin_and_date_are_separate_claims(self):
        for mutate in [lambda d:d['spec']['selected_principal'].update(value=num(90)),lambda d:d['loan'].update(origination_date='2027-12-01'),lambda d:d['closing']['new_loan'].update(loan_id='SYNTHETIC-other'),lambda d:d['spec'].update(as_of_date='2028-01-02')]:
            d=load_capacity();mutate(d);self.assertEqual(size_refinance(*build_capacity(d)).payload['state'],'blocked')
    def test_present_valuation_claim_must_match_without_becoming_cash(self):
        self.data['closing']['valuation_claim']['value']=num(201);p=self.run_case().payload
        self.assertEqual(f(p['computed_property_value']),200);self.assertFalse(p['closing_valuation_claim_matches_calculation']);self.assertEqual(p['state'],'blocked')
        self.data['closing']['valuation_claim']=None;self.assertEqual(self.run_case().payload['state'],'compatible_synthetic_refinance_capacity')
    def test_parameter_units_periods_and_source_metadata_required(self):
        for key,value in [('unit','percent'),('period_ref','OTHER'),('source_ref',None)]:
            d=load_capacity();d['spec']['parameters']['minimum_dscr'][key]=value;self.assertIsNone(size_refinance(*build_capacity(d)).payload['maximum_principal_capacity'])
    def test_annual_scope_frequency_and_producer_missing_data_preserved(self):
        for key in ['valuation_annual_basis_ref','bank_annual_basis_ref','scope_comparability_basis_ref']:
            d=load_capacity();d['spec'][key]=None;self.assertEqual(size_refinance(*build_capacity(d)).payload['state'],'blocked')
        self.data['loan']['payments_per_year']=None;self.assertIsNone(self.run_case().payload['maximum_principal_capacity'])
        self.data=load_capacity();self.data['bank']['tax_coefficient']['value']=None;p=self.run_case().payload;self.assertTrue(p['bank_noi_blockers']);self.assertIsNone(p['maximum_principal_capacity'])
    def test_all_eight_source_run_bindings_context_currency_and_period_guards(self):
        inputs,s=build_capacity(self.data)
        for key in [k for k in json.loads(s)if k.endswith('_sha256')]:
            spec=json.loads(s);spec[key]='0'*64;self.assertIn(key+'_mismatch',size_refinance(inputs,raw(spec)).payload['blockers'])
        for key,value in [('currency','EUR'),('bank_noi_period_ref','OTHER')]:
            spec=json.loads(s);spec[key]=value;self.assertEqual(size_refinance(inputs,raw(spec)).payload['state'],'blocked')
        spec=json.loads(s);spec['context']['run_id']='SYNTHETIC-other';self.assertEqual(size_refinance(inputs,raw(spec)).payload['state'],'blocked')
    def test_rehashed_forged_noi_or_loan_cannot_reduce_sizing_cost(self):
        inputs,s=build_capacity(self.data);p=inputs.bank_noi_run.payload;p['noi']=num(9999);enc=canonical(p);fake=replace(inputs,bank_noi_run=replace(inputs.bank_noi_run,payload_json=enc,sha256=digest(enc)))
        with self.assertRaises(ValidationError):size_refinance(fake,s)
        p=inputs.new_loan.run.payload;p['payment_per_unit']=num(F(1,10000));enc=canonical(p);fake=replace(inputs,new_loan=replace(inputs.new_loan,run=replace(inputs.new_loan.run,payload_json=enc,sha256=digest(enc))))
        with self.assertRaises(ValidationError):size_refinance(fake,s)
    def test_duplicate_reserved_limit_live_context_and_float_rejected(self):
        inputs,s=build_capacity(self.data);spec=json.loads(s);spec['other_limits']=[dict(limit_id='LTV',amount=copy.deepcopy(spec['selected_principal']))]
        with self.assertRaises(ValidationError):parse_refinance_capacity(raw(spec))
        spec=json.loads(s);spec['context']['deal_id']='real'
        with self.assertRaises(ValidationError):parse_refinance_capacity(raw(spec))
        spec=json.loads(s);spec['parameters']['cap_rate']['value']=0.05
        with self.assertRaises(ValidationError):parse_refinance_capacity(raw(spec))
        with self.assertRaises(ValidationError):replace(inputs,valuation_noi_raw=b'x'*4_194_305)
    def test_payload_and_input_sources_immutable(self):
        inputs,s=build_capacity(self.data);r=size_refinance(inputs,s);p=r.payload;p['maximum_principal_capacity']=num(999)
        self.assertEqual(f(r.payload['maximum_principal_capacity']),100);self.assertEqual(r.sha256,digest(r.payload_json));self.assertEqual(r.payload['spec_source_sha256'],sha(s))
    def test_reopened_archive_recovers_four_sources_and_exact_retry(self):
        inputs,s=build_capacity(self.data);r=size_refinance(inputs,s)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'capacity.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_refinance_capacity(inputs,s,r);self.assertEqual(key,a.save_refinance_capacity(inputs,s,r))
            with EvidenceArchive(path)as a:
                b=a.load_refinance_capacity(key);self.assertEqual(b.run,r);self.assertEqual(a.get_refinance_capacity_spec(b.payload['spec_source_sha256']),s)
    def test_archive_fault_forgery_version_missing_and_blocked_recovery(self):
        inputs,s=build_capacity(self.data);r=size_refinance(inputs,s);p=r.payload;p['maximum_principal_capacity']=num(999);enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_refinance_capacity(inputs,s,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_refinance_capacity(inputs,s,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_refinance_capacity(inputs,s,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_refinance_capacity(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_refinance_capacity(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(inputs.bank_noi_raw)))
            with self.assertRaises(MissingEvidence):a.load_refinance_capacity(key)
        self.data=load_capacity('project');inputs,s=build_capacity(self.data);r=size_refinance(inputs,s)
        with EvidenceArchive(':memory:')as a:key=a.save_refinance_capacity(inputs,s,r);self.assertEqual(a.load_refinance_capacity(key).run,r)
    def test_no_bank_policy_or_financial_authority_follows_from_compatibility(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['annual_sizing_is_actual_dated_cash','source_scope_financially_verified','other_limits_completeness_verified','property_appraisal_verified','bank_credit_approved','funds_available_verified','bank_policy_adopted','whole_project_cash_reconciled','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])

    def test_exact_arithmetic_budget_blocks_capacity_from_valid_noi_producer(self):
        rows=[]
        for index,d in enumerate([2**845,3**535,5**365,7**301]):
            row=copy.deepcopy(self.data['valuation']['income_rows'][0]);row.update(item_id='SYNTHETIC-small-income-'+str(index),value=q(F(1,d)));rows.append(row)
        self.data['valuation']['income_rows']=rows;self.data['spec']['parameters']['cap_rate']['value']=q(F(11**244,13**229))
        inputs,s=build_capacity(self.data);self.assertEqual(inputs.valuation_noi_run.payload['calculation_status'],'computed_synthetic_profile')
        p=size_refinance(inputs,s).payload;self.assertIn('refinance_capacity_exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['maximum_principal_capacity'])
