import copy
from dataclasses import replace
from fractions import Fraction as F
import json
import unittest
from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.project_sale_revision import (revise_project_sale, recover_sale_revision,
    evidence_fingerprint, parse_sale_revision)
from sale_revision_test_support import make_evidence, revision, raw, sha


def f(q): return F(int(q['numerator']), int(q['denominator']))
def stage(p, name): return json.loads(p[name]['payload_json'])


class ProjectSaleRevisionTests(unittest.TestCase):
    def setUp(self):
        self.e = make_evidence(compatible=True)
        self.spec = revision(self.e)

    def run_case(self): return revise_project_sale(self.e, raw(self.spec))

    def test_independent_same_values_preserve_cash_and_returns(self):
        p=self.run_case().payload
        self.assertEqual(p['state'],'compiled_synthetic')
        self.assertEqual(f(stage(p,'closing_run')['projected_equity_distribution']),F('745.9097'))
        self.assertEqual(f(self.run_case().guarded_run.investor_run.payload['gross_distributions']),F('1298.9197'))
        self.assertEqual(p['decision'],'PENDING')

    def test_gross_sale_change_propagates_through_closing_and_investor(self):
        self.spec=revision(self.e,proceeds=200)
        run=self.run_case();p=run.payload
        self.assertEqual(f(stage(p,'closing_run')['projected_equity_distribution']),F('545.9097'))
        self.assertEqual(f(run.guarded_run.investor_run.payload['net_cash_profit']),F('98.9197'))
        self.assertEqual(f(run.guarded_run.investor_run.payload['equity_multiple']),F('1.0989197'))
        self.assertEqual(stage(p,'debt_run')['state'],'matched_synthetic_debt_assumptions')

    def test_cost_change_is_independent_of_proceeds(self):
        self.spec=revision(self.e,proceeds=200,costs=70)
        run=self.run_case()
        self.assertEqual(f(stage(run.payload,'closing_run')['projected_equity_distribution']),F('495.9097'))
        self.assertEqual(f(run.guarded_run.investor_run.payload['net_cash_profit']),F('48.9197'))

    def test_zero_proceeds_is_known_not_missing(self):
        self.spec=revision(self.e,proceeds=0)
        run=self.run_case()
        self.assertEqual(run.payload['state'],'compiled_synthetic')
        self.assertEqual(f(run.guarded_run.investor_run.payload['net_cash_profit']),F('-101.0803'))

    def test_missing_claim_and_metadata_block_returns(self):
        baseline=copy.deepcopy(self.spec)
        for key,value in [('value',None),('currency','EUR'),('as_of_date','2027-06-01'),('basis',None),('source_ref',None)]:
            self.spec=copy.deepcopy(baseline);self.spec['replacement_claims']['gross_proceeds'][key]=value
            run=self.run_case();self.assertEqual(run.payload['state'],'blocked');self.assertIsNone(run.guarded_run.compiled_raw)
            self.assertTrue(stage(run.payload,'closing_run')['blockers'])

    def test_cash_in_needs_explicit_assumption_and_gross_slot(self):
        self.spec=revision(self.e,proceeds=0,costs=500)
        run=self.run_case();p=stage(run.payload,'closing_run')
        self.assertEqual(f(p['projected_equity_contribution_required']),F('134.0903'))
        self.assertEqual(p['state'],'blocked');self.assertIsNone(run.guarded_run.compiled_raw)
        self.spec['equity_funding_assumption_ref']='SYNTHETIC-explicit-funding-hypothesis-not-funds'
        run=self.run_case()
        self.assertEqual(stage(run.payload,'closing_run')['state'],'computed_synthetic_closing')
        self.assertIsNone(run.guarded_run.compiled_raw)
        self.assertIn('SYNTHETIC-project-sale:positive_contribution_requires_separate_gross_slot',run.payload['blockers'])

    def test_cash_in_separate_from_distribution_with_explicit_slot(self):
        self.e=make_evidence(compatible=True,sale_contribution_slot=True)
        self.spec=revision(self.e,proceeds=0,costs=500,funding_ref='SYNTHETIC-explicit-funding-hypothesis')
        run=self.run_case();self.assertEqual(run.payload['state'],'compiled_synthetic')
        p=run.guarded_run.investor_run.payload
        self.assertEqual(f(p['gross_contributions']),F('1134.0903'))
        self.assertEqual(f(p['gross_distributions']),F('553.01'))
        sale=next(e for e in p['events'] if e['event_id']=='sale')
        cashin=next(e for e in p['events'] if e['event_id']=='sale-cash-in')
        self.assertEqual(f(sale['amount']),0);self.assertEqual(f(cashin['amount']),F('134.0903'))

    def test_bank_blocker_preserved_even_if_sale_cash_is_high(self):
        self.e=make_evidence();self.spec=revision(self.e,proceeds=999999)
        run=self.run_case();self.assertEqual(stage(run.payload,'project_run')['state'],'reconciled_synthetic_cash_window')
        self.assertEqual(run.payload['state'],'blocked');self.assertIsNone(run.guarded_run.compiled_raw)
        self.assertIn('refinance_capacity_or_selection_blocked',run.payload['blockers'])

    def test_no_debt_operation_reserve_valuation_or_refinance_edits(self):
        before=json.loads(self.e.closings[1].closing_raw);saved=self.e
        self.spec=revision(self.e,proceeds=100,costs=90)
        run=self.run_case();new=json.loads(run.payload['revised_closing_json'])
        self.assertEqual(before['old_debts'],new['old_debts']);self.assertEqual(before['valuation_claim'],new['valuation_claim'])
        for k in before['amounts']:
            if k not in self.spec['replacement_claims']:self.assertEqual(before['amounts'][k],new['amounts'][k])
        recovered=recover_sale_revision(self.e,raw(self.spec),run)
        self.assertEqual(recovered.periods,self.e.periods);self.assertEqual(recovered.closings[0],self.e.closings[0])
        self.assertEqual(recovered.capacity_inputs,self.e.capacity_inputs);self.assertEqual(recovered.capacity_run,self.e.capacity_run)
        self.assertEqual(self.e,saved)

    def test_only_sale_node_hashes_change_in_manifest(self):
        p=self.run_case().payload
        old=json.loads(self.e.manifest_raw);new=json.loads(p['revised_manifest_json'])
        self.assertEqual(old['nodes'][:-1],new['nodes'][:-1]);self.assertNotEqual(old['nodes'][-1],new['nodes'][-1])
        self.assertEqual(stage(p,'project_run')['cash_conservation_residual'],{'numerator':'0','denominator':'1'})

    def test_wrong_base_unknown_target_or_missing_basis_block_before_revision(self):
        original=copy.deepcopy(self.spec)
        for key,value in [('base_evidence_sha256','0'*64),('sale_node_id','unknown'),
                           ('sale_node_id','SYNTHETIC-project-refinance'),('unchanged_other_sources_basis_ref',None)]:
            self.spec=copy.deepcopy(original);self.spec[key]=value
            p=self.run_case().payload;self.assertEqual(p['state'],'blocked');self.assertIsNone(p['revised_closing_json'])

    def test_rehashed_base_run_forgery_rejected_before_revision(self):
        p=self.e.guarded_run.payload;p['state']='forged';text=canonical(p)
        self.e=replace(self.e,guarded_run=replace(self.e.guarded_run,payload_json=text,sha256=digest(text)))
        self.spec=revision(self.e)
        with self.assertRaises(ValidationError):self.run_case()

    def test_recovery_reproduces_then_rejects_rehashed_report_forgery(self):
        run=self.run_case();recovered=recover_sale_revision(self.e,raw(self.spec),run)
        self.assertEqual(evidence_fingerprint(recovered),run.payload['revised_evidence_sha256'])
        p=run.payload;p['state']='PASS';text=canonical(p)
        with self.assertRaises(ValidationError):recover_sale_revision(self.e,raw(self.spec),replace(run,payload_json=text,sha256=digest(text)))
        with self.assertRaises(ValidationError):recover_sale_revision(self.e,raw(self.spec),replace(run,sha256='0'*64))

    def test_recovery_changed_source_invalidates_result(self):
        run=self.run_case();self.spec['replacement_claims']['closing_costs_paid']['value']={'numerator':'30','denominator':'1'}
        with self.assertRaises(ValidationError):recover_sale_revision(self.e,raw(self.spec),run)

    def test_negative_proceeds_block_not_clipped(self):
        self.spec=revision(self.e,proceeds=-1)
        run=self.run_case();self.assertEqual(run.payload['state'],'blocked');self.assertIsNone(run.guarded_run.compiled_raw)

    def test_strict_shape_and_budget_reject_no_silent_extra_edits(self):
        for value in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_sale_revision(value)
        self.spec['replacement_claims']['old_debts']=[]
        with self.assertRaises(ValidationError):self.run_case()

    def test_empty_investor_target_guard_not_bypassed(self):
        from project_test_support import load_case
        project=load_case();project['investor']['events'][-1]['amount']={'numerator':'123','denominator':'1'}
        self.e=make_evidence(compatible=True,project=project);self.spec=revision(self.e)
        self.assertIsNone(self.run_case().guarded_run.compiled_raw)

    def test_blocked_base_cash_boundary_not_repaired_by_sale_revision(self):
        from project_test_support import load_case
        project=load_case();project['closings'][1]['amounts']['opening_free_cash']['value']={'numerator':'1','denominator':'1'}
        self.e=make_evidence(compatible=True,project=project);self.spec=revision(self.e,proceeds=10000)
        self.assertIsNone(self.run_case().guarded_run.compiled_raw)

    def test_personal_return_and_authority_never_inferred(self):
        p=self.run_case().payload
        for key in ['bank_credit_approved','actual_funding_available','complete_market_scenario_recomputed',
                    'real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return']);self.assertIsNone(p['final_economic_capital_loss'])


if __name__=='__main__':unittest.main()
