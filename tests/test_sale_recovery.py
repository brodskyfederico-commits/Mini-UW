import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.costed_exit_sale import assemble_costed_exit_sale
from miniuw_foundation.sale_recovery import analyze_sale_recovery,verify_sale_recovery,parse_sale_recovery,_solve,_caps
from sale_cost_test_support import evidence,valuation,cost_source,bridge_spec,raw
from sale_revision_test_support import make_evidence

def f(q):return F(int(q['numerator']),int(q['denominator']))


class SaleRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.e=evidence();self.nr,self.n,self.vr,self.v=valuation();self.cost=cost_source(self.v);self.bind()
    def bind(self):
        cr=raw(self.cost);c=produce_sale_costs(cr);s=bridge_spec(self.e,self.vr,self.v,cr,c)
        self.args=(self.e,self.nr,self.n,self.vr,self.v,cr,c,raw(s));self.base=assemble_costed_exit_sale(*self.args)
        self.spec=dict(schema='miniuw.synthetic-affine-sale-cash-recovery.v1',base_costed_run_sha256=self.base.sha256,
            gross_price_domain=dict(lower=q(F(0)),upper=q(F(1000))),cost_profile_domain_basis_ref='SYNTHETIC-affine-costs-only-in-this-domain',other_sources_fixed_basis_ref='SYNTHETIC-fixed-debt-dates-and-other-cash-not-market-model')
    def run_case(self):return analyze_sale_recovery(self.args,self.base,raw(self.spec))

    def test_independent_cash_profit_identity_and_boundary(self):
        p=self.run_case().payload;a=p['analysis']
        self.assertEqual(p['state'],'computed_synthetic_recovery_domain')
        self.assertEqual(f(a['profit_slope_per_unit_gross_price']),F(19,20))
        self.assertEqual(f(a['profit_intercept']),F('-91.0803'))
        boundary=F('91.0803')/F(19,20)
        self.assertEqual(f(a['cash_profit_zero_price']),boundary)
        self.assertEqual(f(a['recovering_price_interval']['lower']),boundary)
        self.assertEqual(f(a['recovering_price_interval']['upper']),1000)
        for price,expected_sign in [(boundary-1,-1),(boundary,0),(boundary+1,1)]:
            gain=F(19,20)*price-F('91.0803')
            self.assertEqual((gain>0)-(gain<0),expected_sign)

    def test_exit_cap_interval_inverts_price_endpoints_exactly(self):
        a=self.run_case().payload['analysis'];caps=a['recovering_exit_cap_interval']
        self.assertEqual(f(caps['lower']),F(40,1000))
        self.assertEqual(f(caps['upper']),F(40)/(F('91.0803')/F(19,20)))
        self.assertTrue(caps['lower_closed']);self.assertTrue(caps['upper_closed'])

    def test_recovery_boundary_invariant_after_full_price_and_cost_replay(self):
        from miniuw_foundation.exit_value import produce_exit_value
        before=self.run_case().payload['analysis']
        spec=json.loads(self.vr);spec['cap_rate']['value']=q(F(1,5))
        self.vr=raw(spec);self.v=produce_exit_value(self.nr,self.n,self.vr)
        self.cost=cost_source(self.v);self.bind()
        after=self.run_case().payload['analysis']
        self.assertNotEqual(before['base_gross_price'],after['base_gross_price'])
        self.assertNotEqual(before['base_net_cash_profit'],after['base_net_cash_profit'])
        for field in ['profit_intercept','cash_profit_zero_price','recovering_price_interval','recovering_exit_cap_interval']:
            self.assertEqual(before[field],after[field])

    def test_domain_truncation_can_exclude_boundary_without_moving_it(self):
        self.spec['gross_price_domain'].update(lower=q(F(200)),upper=q(F(500)))
        a=self.run_case().payload['analysis']
        self.assertIsNone(a['cash_profit_zero_price'])
        self.assertEqual(f(a['recovering_price_interval']['lower']),200)

    def test_slope_zero_no_division_and_no_recovery(self):
        self.cost['costs'][1]['value']=q(F(1));self.bind()
        a=self.run_case().payload['analysis']
        self.assertEqual(f(a['profit_slope_per_unit_gross_price']),0)
        self.assertFalse(a['recovery_possible_in_declared_price_domain']);self.assertIsNone(a['cash_profit_zero_price'])

    def test_negative_slope_not_misreported_as_price_floor(self):
        from project_test_support import load_case
        project=load_case();project['closings'][1]['valuation_claim']=None
        project['closings'][1]['amounts']['other_cash_sources']['value']=q(F(1000))
        self.e=make_evidence(compatible=True,project=project)
        self.cost['costs'][1]['value']=q(F(3,1));self.bind()
        a=self.run_case().payload['analysis']
        self.assertEqual(f(a['profit_slope_per_unit_gross_price']),-2)
        self.assertEqual(f(a['recovering_price_interval']['lower']),0)
        self.assertEqual(f(a['recovering_price_interval']['upper']),F('908.9197')/2)

    def test_linear_solver_zero_positive_negative_and_empty_sets(self):
        cases=[(0,0,0,100,(0,100)),(0,1,0,100,(0,100)),(0,-1,0,100,None),
               (2,-10,0,100,(5,100)),(-2,10,0,100,(0,5)),(2,-10,0,3,None),(-2,-1,0,100,None)]
        for s,b,lo,hi,expected in cases:
            result=_solve(F(s),F(b),F(lo),F(hi))
            self.assertEqual(result,None if expected is None else tuple(map(F,expected)))

    def test_cap_zero_noi_and_zero_price_endpoint_semantics(self):
        self.assertIsNone(_caps(F(40),(F(0),F(0))))
        caps=_caps(F(40),(F(0),F(100)))
        self.assertEqual(f(caps['lower']),F(2,5));self.assertIsNone(caps['upper']);self.assertFalse(caps['upper_closed'])
        caps=_caps(F(0),(F(0),F(100)))
        self.assertEqual(f(caps['lower']),0);self.assertFalse(caps['lower_closed']);self.assertIsNone(caps['upper'])
        self.assertIsNone(_caps(F(0),(F(1),F(100))))

    def test_source_domain_and_basis_guards_block(self):
        baseline=copy.deepcopy(self.spec)
        for key,value in [('base_costed_run_sha256','0'*64),('cost_profile_domain_basis_ref',None),('other_sources_fixed_basis_ref',None)]:
            self.spec=copy.deepcopy(baseline);self.spec[key]=value
            self.assertIsNone(self.run_case().payload['analysis'])
        for lower,upper in [(-1,1000),(500,400),(0,100),(None,1000)]:
            self.spec=copy.deepcopy(baseline);self.spec['gross_price_domain']=dict(lower=None if lower is None else q(F(lower)),upper=q(F(upper)))
            self.assertIsNone(self.run_case().payload['analysis'])

    def test_blocked_bank_or_tax_never_produces_recovery_range(self):
        self.e=evidence(compatible=False);self.bind()
        self.assertIsNone(self.run_case().payload['analysis'])
        self.e=evidence();row=copy.deepcopy(self.cost['costs'][0]);row.update(cost_id='tax',classification='tax',applicability='unresolved',value=None)
        self.cost['costs'].append(row);self.bind()
        self.assertIsNone(self.run_case().payload['analysis'])

    def test_existing_valuation_prevents_range_extrapolation(self):
        self.e=make_evidence(compatible=True)
        # NOI 40/cap 8% matches existing value 500 before the range check.
        from miniuw_foundation.exit_value import produce_exit_value
        s=json.loads(self.vr);s['cap_rate']['value']=q(F(2,25));self.vr=raw(s);self.v=produce_exit_value(self.nr,self.n,self.vr)
        self.cost=cost_source(self.v);self.bind()
        p=self.run_case().payload
        self.assertIn('existing_valuation_claim_requires_separate_domain_consistency',p['blockers'])
        self.spec['gross_price_domain']=dict(lower=q(F(500)),upper=q(F(500)))
        self.assertEqual(self.run_case().payload['state'],'computed_synthetic_recovery_domain')

    def test_rehashed_base_and_report_forgery_rejected(self):
        p=self.base.payload;p['state']='forged';text=canonical(p)
        with self.assertRaises(ValidationError):analyze_sale_recovery(self.args,replace(self.base,payload_json=text,sha256=digest(text)),raw(self.spec))
        report=self.run_case();self.assertEqual(verify_sale_recovery(self.args,self.base,raw(self.spec),report),report)
        p=report.payload;p['analysis']['profit_intercept']=q(F(100000));text=canonical(p)
        with self.assertRaises(ValidationError):verify_sale_recovery(self.args,self.base,raw(self.spec),replace(report,payload_json=text,sha256=digest(text)))

    def test_changed_domain_invalidates_report(self):
        report=self.run_case();self.spec['gross_price_domain']['upper']=q(F(900))
        with self.assertRaises(ValidationError):verify_sale_recovery(self.args,self.base,raw(self.spec),report)

    def test_arithmetic_budget_fault_blocks_without_partial_analysis(self):
        with patch('miniuw_foundation.sale_recovery._bounded',side_effect=ArithmeticBudgetError):p=self.run_case().payload
        self.assertIsNone(p['analysis']);self.assertIn('sale_recovery_exact_arithmetic_budget_exceeded',p['blockers'])

    def test_syntax_shape_and_undeclared_domain_rejected(self):
        for b in [b'[]',b'NaN',b'\xff',b' '*65537,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_sale_recovery(b)
        self.spec['gross_price_domain']['upper']=None
        self.assertEqual(self.run_case().payload['state'],'blocked')

    def test_no_new_ledger_policy_funding_or_loss_claim(self):
        p=self.run_case().payload
        self.assertTrue(p['analysis']['EM_ge_one_equivalence_defined_over_price_domain'])
        for key in ['new_scenario_or_investor_ledger_generated','cost_profile_financially_valid_over_domain','funding_availability_verified_over_domain',
                    'tax_rule_verified','investment_criterion_adopted','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return']);self.assertIsNone(p['final_economic_capital_loss'])


if __name__=='__main__':unittest.main()
