import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs,parse_cost_bounds
from sale_cost_test_support import valuation,cost_source,raw
from bounded_cost_test_support import bounds_spec

def f(q):return F(int(q['numerator']),int(q['denominator']))


class BoundedSaleCostsTests(unittest.TestCase):
    def setUp(self):
        self.source=cost_source(valuation()[-1]);self.bind()
    def bind(self):
        self.cr=raw(self.source);self.c=produce_sale_costs(self.cr);self.spec=bounds_spec(self.cr,self.c)
    def run_case(self):return produce_bounded_sale_costs(self.cr,self.c,raw(self.spec))
    def fee(self):return next(r for r in self.spec['rules']if r['cost_id']=='fee')

    def test_independent_floor_total_and_original_preserved(self):
        p=self.run_case().payload;fee=p['adjusted_costs'][1]
        self.assertEqual(f(fee['original_computed_cost']),20);self.assertEqual(f(fee['bounded_cost']),25)
        self.assertEqual(f(p['total_closing_cost']),35);self.assertEqual(fee['binding_constraints'],['minimum'])
        self.assertEqual(f(self.c.payload['total_closing_cost']),30)

    def test_cap_total_from_higher_price(self):
        self.source['gross_price']['value']=q(F(2000));self.bind();p=self.run_case().payload
        self.assertEqual(f(p['adjusted_costs'][1]['original_computed_cost']),100)
        self.assertEqual(f(p['total_closing_cost']),50);self.assertEqual(p['adjusted_costs'][1]['binding_constraints'],['maximum'])

    def test_all_tied_binding_limits_retained(self):
        self.fee()['minimum']['value']=q(F(20));self.fee()['maximum']['value']=q(F(20))
        p=self.run_case().payload
        self.assertEqual(p['adjusted_costs'][1]['binding_constraints'],['original_formula','minimum','maximum'])

    def test_disabled_bounds_require_absent_values(self):
        for key in ['minimum','maximum']:self.fee()[key].update(enabled=False,value=None)
        self.assertEqual(f(self.run_case().payload['total_closing_cost']),30)
        self.fee()['minimum']['value']=q(F(0));self.assertIsNone(self.run_case().payload['total_closing_cost'])

    def test_zero_cap_is_known_without_floor(self):
        self.fee()['minimum'].update(enabled=False,value=None);self.fee()['maximum']['value']=q(F(0))
        p=self.run_case().payload;self.assertEqual(f(p['total_closing_cost']),10)

    def test_floor_above_cap_blocks_without_reordering(self):
        self.fee()['minimum']['value']=q(F(50));p=self.run_case().payload
        self.assertIsNone(p['total_closing_cost']);self.assertIn('fee:minimum_exceeds_maximum',p['blockers'])
        self.assertEqual(f(p['adjusted_costs'][1]['rule']['minimum']['value']),50)

    def test_missing_enabled_value_rule_basis_or_metadata_block(self):
        original=copy.deepcopy(self.spec)
        for key,value in [('enabled',None),('value',None),('value',q(F(-1))),('currency','EUR'),('as_of_date',None),('source_ref',None)]:
            self.spec=copy.deepcopy(original);self.fee()['minimum'][key]=value
            self.assertIsNone(self.run_case().payload['total_closing_cost'])
        self.spec=copy.deepcopy(original);self.fee()['rule_basis_ref']=None
        self.assertIsNone(self.run_case().payload['total_closing_cost'])

    def test_exact_included_inventory_hash_and_complete_declaration_required(self):
        original=copy.deepcopy(self.spec)
        for key,value in [('cost_source_sha256','0'*64),('cost_run_sha256','0'*64),('rule_inventory_declared_complete',False),('rule_inventory_basis_ref',None),('rules',original['rules'][:-1])]:
            self.spec=copy.deepcopy(original);self.spec[key]=value
            self.assertIsNone(self.run_case().payload['total_closing_cost'])

    def test_not_applicable_row_preserved_and_not_given_limits(self):
        self.source['costs'][0].update(applicability='not_applicable',value=None);self.bind()
        p=self.run_case().payload
        self.assertEqual(f(p['total_closing_cost']),25);self.assertEqual(len(p['excluded_original_rows']),1)

    def test_unresolved_tax_cannot_be_fixed_by_limits(self):
        tax=copy.deepcopy(self.source['costs'][0]);tax.update(cost_id='tax',classification='tax',applicability='unresolved',value=None)
        self.source['costs'].append(tax);self.bind();p=self.run_case().payload
        self.assertIsNone(p['total_closing_cost']);self.assertTrue(p['original_cost_blockers'])

    def test_no_limits_does_not_mean_defaults_on_empty_inventory(self):
        self.source['costs']=[];self.bind()
        self.assertEqual(f(self.run_case().payload['total_closing_cost']),0)

    def test_rational_floor_and_cap_no_cent_rounding(self):
        self.fee()['minimum']['value']=q(F(76,3));self.fee()['maximum']['value']=q(F(100,3))
        self.assertEqual(f(self.run_case().payload['total_closing_cost']),F(106,3))

    def test_budget_fault_no_partial_total(self):
        with patch('miniuw_foundation.bounded_sale_costs._bounded',side_effect=ArithmeticBudgetError):p=self.run_case().payload
        self.assertIsNone(p['total_closing_cost']);self.assertEqual(p['adjusted_costs'],[])

    def test_rehashed_original_cost_run_forgery_rejected(self):
        p=self.c.payload;p['total_closing_cost']=q(F(0));text=canonical(p)
        self.c=replace(self.c,payload_json=text,sha256=digest(text));self.spec['cost_run_sha256']=self.c.sha256
        with self.assertRaises(ValidationError):self.run_case()

    def test_strict_shapes_duplicate_ids_and_budget(self):
        for b in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_cost_bounds(b)
        self.spec['rules'].append(copy.deepcopy(self.spec['rules'][0]))
        with self.assertRaises(ValidationError):self.run_case()

    def test_sources_payload_and_financial_authority_unchanged(self):
        saved=self.c.payload_json;run=self.run_case();run.payload['adjusted_costs'].clear()
        self.assertEqual(self.c.payload_json,saved);self.assertEqual(len(run.payload['adjusted_costs']),2)
        for key in ['result_is_global_affine_cost_profile','contract_or_tax_rule_verified','costs_paid_verified','real_decisions_enabled','production_authorized']:self.assertIs(run.payload[key],False)


if __name__=='__main__':unittest.main()
