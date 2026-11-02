import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.costed_exit_sale import assemble_costed_exit_sale,verify_costed_exit_sale,parse_costed_exit_sale
from sale_cost_test_support import evidence,valuation,cost_source,bridge_spec,raw

def f(q):return F(int(q['numerator']),int(q['denominator']))


class CostedExitSaleTests(unittest.TestCase):
    def setUp(self):
        self.e=evidence();self.nr,self.n,self.vr,self.v=valuation()
        self.cost=cost_source(self.v);self.bind_cost()
    def bind_cost(self):
        self.cr=raw(self.cost);self.c=produce_sale_costs(self.cr)
        self.s=bridge_spec(self.e,self.vr,self.v,self.cr,self.c)
    def args(self):return(self.e,self.nr,self.n,self.vr,self.v,self.cr,self.c,raw(self.s))
    def run_case(self):return assemble_costed_exit_sale(*self.args())
    def investor(self,run):return run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload

    def test_independent_cost_replaces_previous_cost_not_added_twice(self):
        run=self.run_case();self.assertEqual(run.payload['state'],'compiled_synthetic')
        self.assertEqual(f(run.payload['computed_closing_cost']),30)
        p=self.investor(run)
        self.assertEqual(f(p['net_cash_profit']),F('288.9197'))
        self.assertEqual(f(p['cash_by_category']['net_sale_distribution']),F('735.9097'))

    def test_price_revision_recomputes_cost_then_cash_return(self):
        s=json.loads(self.vr);s['cap_rate']['value']={'numerator':'1','denominator':'5'}
        self.vr=raw(s);self.v=produce_exit_value(self.nr,self.n,self.vr)
        self.cost=cost_source(self.v);self.bind_cost()
        run=self.run_case();self.assertEqual(f(run.payload['computed_closing_cost']),20)
        self.assertEqual(f(self.investor(run)['net_cash_profit']),F('98.9197'))

    def test_stale_price_value_or_lineage_blocks(self):
        original=copy.deepcopy(self.cost)
        for key,value in [('value',{'numerator':'200','denominator':'1'}),('source_ref','SYNTHETIC-other-run')]:
            self.cost=copy.deepcopy(original);self.cost['gross_price'][key]=value;self.bind_cost()
            p=self.run_case().payload;self.assertIsNone(p['exit_sale_run'])
            self.assertIn('cost_gross_price_or_exit_run_lineage_mismatch',p['blockers'])

    def test_equivalent_rational_price_accepted(self):
        self.cost['gross_price']['value']={'numerator':'800','denominator':'2'};self.bind_cost()
        self.assertEqual(self.run_case().payload['state'],'compiled_synthetic')

    def test_unresolved_tax_blocks_no_partial_total_export(self):
        tax=copy.deepcopy(self.cost['costs'][0]);tax.update(cost_id='tax',classification='tax',applicability='unresolved',value=None)
        self.cost['costs'].append(tax);self.bind_cost()
        p=self.run_case().payload;self.assertIsNone(p['computed_closing_cost']);self.assertIsNone(p['exit_sale_run'])
        self.assertTrue(p['cost_blockers'])

    def test_bank_blocker_and_no_sale_hypothesis_preserved(self):
        self.e=evidence(compatible=False);self.s['base_evidence_sha256']=evidence_fingerprint(self.e)
        run=self.run_case();self.assertEqual(run.payload['state'],'blocked')
        self.assertIn('refinance_capacity_or_selection_blocked',run.payload['blockers'])
        self.assertIsNone(run.exit_sale_run.sale_revision_run.guarded_run.compiled_raw)
        self.s['sale_at_value_hypothesis_ref']=None
        self.assertIsNone(self.run_case().exit_sale_run.sale_revision_run)

    def test_all_hash_bindings_required(self):
        original=copy.deepcopy(self.s)
        for key in ['base_evidence_sha256','exit_spec_sha256','exit_run_sha256','cost_source_sha256','cost_run_sha256']:
            self.s=copy.deepcopy(original);self.s[key]='0'*64
            self.assertIsNone(self.run_case().payload['exit_sale_run'])

    def test_computable_cost_from_other_context_cannot_join(self):
        self.cost['context']['run_id']+='-other';self.bind_cost()
        self.assertEqual(self.c.payload['state'],'computed_synthetic_sale_costs')
        p=self.run_case().payload;self.assertIn('cost_and_exit_context_currency_or_date_mismatch',p['blockers'])

    def test_rehashed_cost_forgery_rejected(self):
        p=self.c.payload;p['total_closing_cost']={'numerator':'0','denominator':'1'};text=canonical(p)
        self.c=replace(self.c,payload_json=text,sha256=digest(text));self.s['cost_run_sha256']=self.c.sha256
        with self.assertRaises(ValidationError):self.run_case()

    def test_report_replay_forgery_and_changed_spec(self):
        run=self.run_case();self.assertEqual(verify_costed_exit_sale(*self.args(),run),run)
        p=run.payload;p['computed_closing_cost']={'numerator':'0','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):verify_costed_exit_sale(*self.args(),replace(run,payload_json=text,sha256=digest(text)))
        self.s['revision_id']+='-new'
        with self.assertRaises(ValidationError):verify_costed_exit_sale(*self.args(),run)

    def test_generated_cost_has_run_pointer_and_full_metadata(self):
        p=self.run_case().payload;b=json.loads(p['generated_exit_sale_spec_json']);claim=b['closing_cost_claim']
        self.assertIn(self.c.sha256,claim['source_ref']);self.assertEqual(claim['basis'],'cash_flow_at_closing')
        self.assertEqual(claim['as_of_date'],'2027-07-01')

    def test_syntax_budget_undeclared_tax_profile_and_authority(self):
        for b in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_costed_exit_sale(b)
        p=self.run_case().payload
        for key in ['tax_rule_verified','costs_paid_verified','bank_credit_approved','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return']);self.assertEqual(p['decision'],'PENDING')
        self.s['historical_tax_default']=.01
        with self.assertRaises(ValidationError):self.run_case()


if __name__=='__main__':unittest.main()
