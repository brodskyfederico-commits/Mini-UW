import copy
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import json
import unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_noi import produce_operating_noi,ArithmeticBudgetError
from miniuw_foundation.exit_value import produce_exit_value,parse_exit_value
from sale_revision_test_support import raw,sha

ROOT=Path(__file__).resolve().parents[1]
def f(q):return F(int(q['numerator']),int(q['denominator']))


class ExitValueTests(unittest.TestCase):
    def setUp(self):
        self.noi_raw=(ROOT/'templates/synthetic-exit-forward-noi.json').read_bytes()
        self.noi=produce_operating_noi(self.noi_raw)
        self.spec=json.loads((ROOT/'templates/synthetic-exit-value-spec.json').read_bytes())

    def run_case(self):return produce_exit_value(self.noi_raw,self.noi,raw(self.spec))
    def bind(self):self.spec.update(noi_source_sha256=sha(self.noi_raw),noi_run_sha256=self.noi.sha256)

    def test_exact_independent_forward_noi_cap_value(self):
        p=self.run_case().payload
        self.assertEqual(f(p['forward_noi']),40);self.assertEqual(f(p['candidate_value']),400)
        self.spec['cap_rate']['value']=q(F(3,25))
        self.assertEqual(f(self.run_case().payload['candidate_value']),F(1000,3))

    def test_zero_noi_known_zero_value_not_cash(self):
        p=json.loads(self.noi_raw);p['income_rows'][0]['value']=q(F(0))
        self.noi_raw=raw(p);self.noi=produce_operating_noi(self.noi_raw);self.bind()
        result=self.run_case().payload
        self.assertEqual(f(result['candidate_value']),0);self.assertFalse(result['cash_proceeds_produced'])

    def test_negative_noi_blocks_without_clipping(self):
        p=json.loads(self.noi_raw);p['expense_rows'][0]['value']=q(F(80))
        self.noi_raw=raw(p);self.noi=produce_operating_noi(self.noi_raw);self.bind()
        result=self.run_case().payload;self.assertIsNone(result['candidate_value'])
        self.assertIn('negative_forward_noi_outside_valuation_profile',result['blockers'])

    def test_missing_zero_negative_cap_block(self):
        for value in [None,q(F(0)),q(F(-1,10))]:
            self.spec['cap_rate']['value']=value
            p=self.run_case().payload;self.assertEqual(p['state'],'blocked');self.assertIsNone(p['candidate_value'])

    def test_forward_calendar_dates_explicit_no_quarter_annualization(self):
        baseline=copy.deepcopy(self.spec)
        for key,value in [('start',None),('start','2027-08-01'),('end',None),('end','2027-10-01')]:
            self.spec=copy.deepcopy(baseline);self.spec['forward_window'][key]=value
            self.assertIsNone(self.run_case().payload['candidate_value'])

    def test_leap_day_window_not_silently_adjusted(self):
        self.spec['valuation_date']='2028-02-29'
        self.spec['forward_window'].update(start='2028-02-29',end='2029-02-28')
        p=self.run_case().payload
        self.assertIn('explicit_one_calendar_year_forward_window_required_no_date_adjustment',p['blockers'])

    def test_calendar_year_end_supported_with_explicit_dates(self):
        self.spec['valuation_date']='2027-12-31';self.spec['forward_window'].update(start='2027-12-31',end='2028-12-31')
        self.assertEqual(f(self.run_case().payload['candidate_value']),400)

    def test_cap_unit_period_source_and_valuation_basis_required(self):
        baseline=copy.deepcopy(self.spec)
        for key,value in [('unit','percent'),('period_ref','wrong'),('source_ref',None)]:
            self.spec=copy.deepcopy(baseline);self.spec['cap_rate'][key]=value
            self.assertEqual(self.run_case().payload['state'],'blocked')
        self.spec=copy.deepcopy(baseline);self.spec['valuation_basis_ref']=None
        self.assertIsNone(self.run_case().payload['candidate_value'])

    def test_noi_window_period_basis_context_currency_and_hash_bindings(self):
        baseline=copy.deepcopy(self.spec)
        for key,value in [('period_ref',None),('period_ref','wrong'),('basis_ref',None)]:
            self.spec=copy.deepcopy(baseline);self.spec['forward_window'][key]=value
            self.assertEqual(self.run_case().payload['state'],'blocked')
        for key,value in [('currency','EUR'),('noi_source_sha256','0'*64),('noi_run_sha256','0'*64)]:
            self.spec=copy.deepcopy(baseline);self.spec[key]=value
            self.assertEqual(self.run_case().payload['state'],'blocked')
        self.spec=copy.deepcopy(baseline);self.spec['context']['run_id']+='-wrong'
        self.assertEqual(self.run_case().payload['state'],'blocked')

    def test_upstream_missing_noi_not_replaced_with_zero(self):
        p=json.loads(self.noi_raw);p['income_rows'][0]['value']=None
        self.noi_raw=raw(p);self.noi=produce_operating_noi(self.noi_raw);self.bind()
        result=self.run_case().payload
        self.assertTrue(result['upstream_noi_blockers']);self.assertIsNone(result['candidate_value'])

    def test_rehashed_noi_forgery_rejected(self):
        p=self.noi.payload;p['noi']=q(F(999));text=canonical(p)
        self.noi=replace(self.noi,payload_json=text,sha256=digest(text));self.bind()
        with self.assertRaises(ValidationError):self.run_case()

    def test_budget_fault_fails_closed(self):
        with patch('miniuw_foundation.exit_value._bounded',side_effect=ArithmeticBudgetError):p=self.run_case().payload
        self.assertEqual(p['state'],'blocked');self.assertIsNone(p['candidate_value'])
        self.assertIn('exit_value_exact_arithmetic_budget_exceeded',p['blockers'])

    def test_strict_syntax_shape_and_scalar_not_float(self):
        for p in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_exit_value(p)
        self.spec['cap_rate']['value']=.1
        with self.assertRaises(ValidationError):self.run_case()

    def test_no_actual_market_scope_tax_or_cash_authority(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['actual_forward_noi_scope_verified','cash_proceeds_produced','market_price_verified','real_decisions_enabled','production_authorized']:
            self.assertIs(p[key],False)


if __name__=='__main__':unittest.main()
