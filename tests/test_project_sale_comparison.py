import copy
from dataclasses import replace
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError, canonical, digest
from miniuw_foundation.project_sale_revision import revise_project_sale
from miniuw_foundation.project_sale_comparison import (compare_project_sales, parse_sale_comparison,
                                                      verify_sale_comparison)
from sale_revision_test_support import make_evidence, revision, inventory, raw


def f(q):return F(int(q['numerator']),int(q['denominator']))


class ProjectSaleComparisonTests(unittest.TestCase):
    def setUp(self):
        self.e=make_evidence(compatible=True)
        self.specs=tuple(raw(revision(self.e,proceeds=n,revision_id='SYNTHETIC-sale-'+str(n)))for n in [0,200,400])
        self.inventory=inventory(self.e,self.specs)

    def run_case(self):return compare_project_sales(self.e,self.specs,raw(self.inventory))

    def test_independent_outputs_and_all_declared_rows(self):
        p=self.run_case().payload
        self.assertTrue(p['all_declared_revisions_compiled']);self.assertEqual(len(p['revisions']),3)
        for row,profit in zip(p['revisions'],['-101.0803','98.9197','298.9197']):
            self.assertEqual(f(row['cash_metrics']['net_cash_profit']),F(profit))
            self.assertEqual(row['state'],'compiled_synthetic');self.assertEqual(row['decision'],'PENDING')
            self.assertEqual(row['stage_states']['debt'],'matched_synthetic_debt_assumptions')
            self.assertEqual(row['stage_states']['capacity'],'compatible_synthetic_refinance_capacity')

    def test_capacity_blocker_preserved_and_no_return_zero_substitution(self):
        self.e=make_evidence()
        self.specs=tuple(raw(revision(self.e,proceeds=n,revision_id='SYNTHETIC-sale-'+str(n)))for n in [0,400,100000])
        self.inventory=inventory(self.e,self.specs);p=self.run_case().payload
        self.assertFalse(p['all_declared_revisions_compiled']);self.assertTrue(p['base_capacity_blockers'])
        for row in p['revisions']:
            self.assertIsNone(row['cash_metrics']);self.assertIsNone(row['equity_multiple']);self.assertIsNone(row['annual_irr_roots'])
            self.assertEqual(row['stage_states']['cash_window'],'reconciled_synthetic_cash_window')
            self.assertTrue(row['stage_blockers']['capacity'])

    def test_missing_claim_row_preserved_with_computable_siblings(self):
        specs=list(self.specs);specs[1]=raw(revision(self.e,proceeds=None,revision_id='SYNTHETIC-missing'))
        self.specs=tuple(specs);self.inventory=inventory(self.e,self.specs)
        p=self.run_case().payload
        self.assertEqual([r['state']for r in p['revisions']],['compiled_synthetic','blocked','compiled_synthetic'])
        self.assertIsNone(p['revisions'][1]['cash_metrics']);self.assertTrue(p['revisions'][1]['stage_blockers']['closing'])

    def test_declared_hash_order_count_and_base_mismatch_block_all(self):
        original=copy.deepcopy(self.inventory)
        changes=[('base_evidence_sha256','0'*64),('revisions',original['revisions'][::-1]),
                 ('revisions',original['revisions'][:-1])]
        for key,value in changes:
            self.inventory=copy.deepcopy(original);self.inventory[key]=value;p=self.run_case().payload
            self.assertFalse(p['declared_revision_inventory_verified']);self.assertTrue(p['blockers'])
            self.assertTrue(all(r['revision_run_sha256']is None for r in p['revisions']))

    def test_incomplete_inventory_and_missing_basis_no_complete_claim(self):
        original=copy.deepcopy(self.inventory)
        for key,value in [('inventory_declared_complete',False),('inventory_declared_complete',None),('inventory_basis_ref',None)]:
            self.inventory=copy.deepcopy(original);self.inventory[key]=value
            p=self.run_case().payload;self.assertEqual(p['state'],'pending_blocked_revisions')
            self.assertFalse(p['all_declared_revisions_compiled'])

    def test_duplicate_ids_and_oversize_sources_rejected(self):
        self.specs=(self.specs[0],self.specs[0])
        with self.assertRaises(ValidationError):self.run_case()
        with self.assertRaises(ValidationError):compare_project_sales(self.e,(),raw(self.inventory))
        with self.assertRaises(ValidationError):compare_project_sales(self.e,self.specs*7,raw(self.inventory))
        self.inventory['revisions'][1]['revision_id']=self.inventory['revisions'][0]['revision_id']
        with self.assertRaises(ValidationError):parse_sale_comparison(raw(self.inventory))

    def test_individual_wrong_base_spec_stays_blocked(self):
        import json
        altered=json.loads(self.specs[0]);altered['base_evidence_sha256']='0'*64
        self.specs=(raw(altered),)+self.specs[1:];self.inventory=inventory(self.e,self.specs)
        p=self.run_case().payload
        self.assertEqual(p['revisions'][0]['state'],'blocked');self.assertEqual(p['revisions'][1]['state'],'compiled_synthetic')

    def test_each_row_bound_to_its_full_replayed_report(self):
        for row,spec in zip(self.run_case().payload['revisions'],self.specs):
            self.assertEqual(row['revision_run_sha256'],revise_project_sale(self.e,spec).sha256)

    def test_replay_rejects_updated_hash_forgery_and_stale_inventory(self):
        report=self.run_case()
        self.assertEqual(verify_sale_comparison(self.e,self.specs,raw(self.inventory),report),report)
        p=report.payload;p['revisions'][0]['equity_multiple']={'numerator':'100','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):verify_sale_comparison(self.e,self.specs,raw(self.inventory),replace(report,payload_json=text,sha256=digest(text)))
        self.inventory['inventory_basis_ref']+='-revision'
        with self.assertRaises(ValidationError):verify_sale_comparison(self.e,self.specs,raw(self.inventory),report)

    def test_no_best_case_authority_or_full_scenario_inference(self):
        p=self.run_case().payload
        for key in ['best_case_selected','complete_market_scenarios_recomputed','downside_policy_adopted',
                    'bank_credit_approved','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return']);self.assertIsNone(p['final_economic_capital_loss'])
        self.assertEqual(p['decision'],'PENDING')

    def test_source_transport_and_json_shape_strict(self):
        for value in [b'[]',b'NaN',b'\xff',b' '*65537,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_sale_comparison(value)
        self.inventory['invented_default_shock']=.2
        with self.assertRaises(ValidationError):self.run_case()

    def test_cash_in_case_preserved_as_gross_contribution(self):
        self.e=make_evidence(compatible=True,sale_contribution_slot=True)
        self.specs=(raw(revision(self.e,proceeds=0,costs=500,funding_ref='SYNTHETIC-explicit-only')),
            raw(revision(self.e,proceeds=400,revision_id='SYNTHETIC-positive')))
        self.inventory=inventory(self.e,self.specs)
        row=self.run_case().payload['revisions'][0]
        self.assertEqual(f(row['projected_sale_distribution']),0)
        self.assertEqual(f(row['projected_sale_contribution_required']),F('134.0903'))
        self.assertEqual(f(row['cash_metrics']['additional_capital_contributions']),F('134.0903'))


if __name__=='__main__':unittest.main()
