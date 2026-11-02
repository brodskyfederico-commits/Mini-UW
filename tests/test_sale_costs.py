import copy
from fractions import Fraction as F
import unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.sale_costs import produce_sale_costs,parse_sale_costs
from sale_cost_test_support import valuation,cost_source,raw

def f(q):return F(int(q['numerator']),int(q['denominator']))


class SaleCostsTests(unittest.TestCase):
    def setUp(self):self.p=cost_source(valuation()[-1])
    def run_case(self):return produce_sale_costs(raw(self.p)).payload

    def test_independent_fixed_plus_gross_fraction(self):
        p=self.run_case();self.assertEqual(f(p['total_closing_cost']),30)
        self.assertEqual([f(r['computed_cost'])for r in p['cost_rows']],[10,20])

    def test_exact_fractional_price_and_multiple_percentage_rows(self):
        self.p['gross_price']['value']=q(F(100,3))
        extra=copy.deepcopy(self.p['costs'][1]);extra.update(cost_id='other-percentage',value=q(F(1,10)))
        self.p['costs'].append(extra)
        self.assertEqual(f(self.run_case()['total_closing_cost']),15)

    def test_zero_price_keeps_fixed_cost(self):
        self.p['gross_price']['value']=q(F(0));self.assertEqual(f(self.run_case()['total_closing_cost']),10)

    def test_explicit_zero_costs_not_missing(self):
        for r in self.p['costs']:r['value']=q(F(0))
        self.assertEqual(f(self.run_case()['total_closing_cost']),0)
        self.p['costs'][0]['value']=None;self.assertIsNone(self.run_case()['total_closing_cost'])

    def test_unresolved_tax_blocks_complete_total(self):
        tax=copy.deepcopy(self.p['costs'][0]);tax.update(cost_id='tax',classification='tax',applicability='unresolved',value=None)
        self.p['costs'].append(tax);p=self.run_case()
        self.assertIsNone(p['total_closing_cost']);self.assertEqual(p['state'],'blocked')
        self.assertEqual(f(p['cost_rows'][0]['computed_cost']),10)
        self.assertIn('tax:cost_applicability_unresolved',p['blockers'])

    def test_not_applicable_requires_basis_and_absent_amount(self):
        row=self.p['costs'][0];row.update(applicability='not_applicable',value=None)
        p=self.run_case();self.assertEqual(f(p['total_closing_cost']),20)
        self.assertTrue(p['cost_rows'][0]['excluded_by_explicit_applicability'])
        self.assertIsNone(p['cost_rows'][0]['computed_cost'])
        row['value']=q(F(0));self.assertIsNone(self.run_case()['total_closing_cost'])

    def test_missing_applicability_basis_not_silently_excluded(self):
        self.p['costs'][0].update(applicability='not_applicable',value=None,applicability_basis_ref=None)
        self.assertEqual(self.run_case()['state'],'blocked')

    def test_inventory_complete_basis_and_nonoverlap_all_required(self):
        original=copy.deepcopy(self.p)
        for key,value in [('inventory_declared_complete',None),('inventory_declared_complete',False),('inventory_basis_ref',None),('nonoverlap_basis_ref',None)]:
            self.p=copy.deepcopy(original);self.p[key]=value
            self.assertIsNone(self.run_case()['total_closing_cost'])

    def test_empty_inventory_only_zero_with_explicit_complete_bases(self):
        self.p['costs']=[];self.assertEqual(f(self.run_case()['total_closing_cost']),0)
        self.p['inventory_declared_complete']=False;self.assertIsNone(self.run_case()['total_closing_cost'])

    def test_price_metadata_and_domain_guard(self):
        original=copy.deepcopy(self.p)
        for key,value in [('value',None),('value',q(F(-1))),('currency','EUR'),('as_of_date',None),('basis','net_price'),('source_ref',None)]:
            self.p=copy.deepcopy(original);self.p['gross_price'][key]=value
            self.assertEqual(self.run_case()['state'],'blocked')

    def test_cost_metadata_and_negative_amount_guard(self):
        original=copy.deepcopy(self.p)
        for key,value in [('value',q(F(-1))),('currency','EUR'),('as_of_date','2027-06-01'),('source_ref',None),('unit','percent')]:
            self.p=copy.deepcopy(original);self.p['costs'][1][key]=value
            self.assertEqual(self.run_case()['state'],'blocked')

    def test_fraction_above_one_not_clipped_by_undeclared_policy(self):
        self.p['costs'][1]['value']=q(F(3,2));self.assertEqual(f(self.run_case()['total_closing_cost']),610)

    def test_duplicate_ids_unsupported_profile_and_bound_rejected(self):
        self.p['costs'].append(copy.deepcopy(self.p['costs'][0]))
        with self.assertRaises(ValidationError):self.run_case()
        self.p['costs']=self.p['costs'][:1]*65
        with self.assertRaises(ValidationError):self.run_case()
        self.p['costs']=self.p['costs'][:1];self.p['costs'][0]['kind']='percent_of_net'
        with self.assertRaises(ValidationError):self.run_case()

    def test_syntax_numbers_and_source_budget_strict(self):
        for b in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_sale_costs(b)
        self.p['costs'][1]['value']=.05
        with self.assertRaises(ValidationError):self.run_case()

    def test_arithmetic_budget_fault_fails_without_partial_total(self):
        with patch('miniuw_foundation.sale_costs._bounded',side_effect=ArithmeticBudgetError):p=self.run_case()
        self.assertIsNone(p['total_closing_cost']);self.assertEqual(p['cost_rows'],[])
        self.assertIn('sale_cost_exact_arithmetic_budget_exceeded',p['blockers'])

    def test_source_and_run_payload_immutable(self):
        before=copy.deepcopy(self.p);run=produce_sale_costs(raw(self.p));run.payload['cost_rows'].clear()
        self.assertEqual(self.p,before);self.assertEqual(len(run.payload['cost_rows']),2)

    def test_fixed_tax_is_hypothesis_not_legal_verification(self):
        self.p['costs'][0]['classification']='tax';p=self.run_case()
        self.assertEqual(f(p['total_closing_cost']),30)
        for key in ['tax_rule_verified','tax_policy_adopted','costs_paid_verified','cost_inventory_financially_verified','cost_nonoverlap_financially_verified','real_decisions_enabled','production_authorized']:
            self.assertIs(p[key],False)
        self.assertEqual(p['decision'],'PENDING')


if __name__=='__main__':unittest.main()
