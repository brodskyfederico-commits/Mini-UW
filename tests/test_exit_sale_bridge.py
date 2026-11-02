import copy
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.exit_sale_bridge import assemble_exit_sale,verify_exit_sale,parse_exit_sale_bridge
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from sale_revision_test_support import make_evidence,revision,raw,sha
from project_test_support import load_case

ROOT=Path(__file__).resolve().parents[1]
def f(q):return F(int(q['numerator']),int(q['denominator']))


class ExitSaleBridgeTests(unittest.TestCase):
    def setUp(self):
        project=load_case();project['closings'][1]['valuation_claim']=None
        self.e=make_evidence(compatible=True,project=project)
        self.nr=(ROOT/'templates/synthetic-exit-forward-noi.json').read_bytes();self.n=produce_operating_noi(self.nr)
        self.vr=(ROOT/'templates/synthetic-exit-value-spec.json').read_bytes();self.v=produce_exit_value(self.nr,self.n,self.vr)
        self.b=dict(schema='miniuw.synthetic-exit-value-to-sale.v1',revision_id='SYNTHETIC-generated-price-revision',
            base_evidence_sha256=evidence_fingerprint(self.e),exit_spec_sha256=sha(self.vr),exit_run_sha256=self.v.sha256,
            sale_node_id='SYNTHETIC-project-sale',sale_at_value_hypothesis_ref='SYNTHETIC-explicit-sale-at-value-not-market-proof',
            unchanged_other_sources_basis_ref='SYNTHETIC-frozen-other-source-hypothesis',equity_funding_assumption_ref=None,
            closing_cost_claim=revision(self.e)['replacement_claims']['closing_costs_paid'])

    def run_case(self):return assemble_exit_sale(self.e,self.nr,self.n,self.vr,self.v,raw(self.b))
    def value_revision(self,s):
        self.vr=raw(s);self.v=produce_exit_value(self.nr,self.n,self.vr)
        self.b.update(exit_spec_sha256=sha(self.vr),exit_run_sha256=self.v.sha256)

    def test_independent_value_to_guarded_cash_return(self):
        run=self.run_case();self.assertEqual(run.payload['state'],'compiled_synthetic')
        p=run.sale_revision_run.guarded_run.investor_run.payload
        self.assertEqual(f(run.payload['candidate_value']),400)
        self.assertEqual(f(p['gross_distributions']),F('1298.9197'))
        self.assertEqual(f(p['net_cash_profit']),F('298.9197'))

    def test_exit_cap_change_recalculates_gross_sale_then_net_return(self):
        s=json.loads(self.vr);s['cap_rate']['value']={'numerator':'1','denominator':'5'};self.value_revision(s)
        run=self.run_case();self.assertEqual(f(run.payload['candidate_value']),200)
        self.assertEqual(f(run.sale_revision_run.guarded_run.investor_run.payload['net_cash_profit']),F('98.9197'))

    def test_no_separate_value_or_forward_noi_distribution(self):
        p=self.run_case().sale_revision_run.guarded_run.investor_run.payload
        self.assertEqual(len(p['events']),5)
        self.assertEqual([e['event_id']for e in p['events']],['initial','op-before','refi','op-after','sale'])
        self.assertEqual(f(p['cash_by_category']['operating_distribution']),200)
        self.assertEqual(f(p['cash_by_category']['net_sale_distribution']),F('745.9097'))

    def test_sale_at_value_hypothesis_required_not_inferred(self):
        self.b['sale_at_value_hypothesis_ref']=None
        p=self.run_case().payload;self.assertIsNone(p['sale_revision_run'])
        self.assertIn('explicit_hypothetical_sale_at_value_basis_missing',p['blockers'])

    def test_value_date_currency_context_must_match_sale(self):
        for kind in ['date','currency','context']:
            s=json.loads((ROOT/'templates/synthetic-exit-value-spec.json').read_bytes())
            if kind=='date':s['valuation_date']='2027-08-01';s['forward_window'].update(start='2027-08-01',end='2028-08-01')
            elif kind=='currency':s['currency']='EUR'
            else:s['context']['run_id']+='-other'
            self.value_revision(s);p=self.run_case().payload
            self.assertEqual(p['state'],'blocked');self.assertIsNone(p['sale_revision_run'])

    def test_missing_cost_no_auto_zero_or_default_percentage(self):
        self.b['closing_cost_claim']['value']=None
        run=self.run_case();self.assertEqual(run.payload['state'],'blocked')
        self.assertIsNone(run.sale_revision_run.guarded_run.compiled_raw)

    def test_computable_value_from_other_context_or_currency_cannot_join_project(self):
        for kind in ['context','currency']:
            noi=json.loads((ROOT/'templates/synthetic-exit-forward-noi.json').read_bytes())
            spec=json.loads((ROOT/'templates/synthetic-exit-value-spec.json').read_bytes())
            if kind=='context':
                noi['context']['run_id']+='-other';spec['context']=copy.deepcopy(noi['context'])
            else:
                noi['currency']='EUR';spec['currency']='EUR'
                for family in ['income_rows','expense_rows']:
                    for row in noi[family]:row['currency']='EUR'
                noi['tax_floor']['currency']='EUR'
            self.nr=raw(noi);self.n=produce_operating_noi(self.nr)
            spec.update(noi_source_sha256=sha(self.nr),noi_run_sha256=self.n.sha256)
            self.value_revision(spec)
            self.assertEqual(self.v.payload['state'],'computed_synthetic_exit_value')
            p=self.run_case().payload
            self.assertIn('sale_and_value_context_or_currency_mismatch',p['blockers'])
            self.assertIsNone(p['sale_revision_run'])

    def test_bank_blocker_not_removed_by_positive_value(self):
        project=load_case();project['closings'][1]['valuation_claim']=None
        self.e=make_evidence(project=project);self.b['base_evidence_sha256']=evidence_fingerprint(self.e)
        run=self.run_case();self.assertEqual(run.payload['state'],'blocked')
        self.assertEqual(f(run.payload['candidate_value']),400)
        self.assertIn('refinance_capacity_or_selection_blocked',run.payload['blockers'])
        self.assertIsNone(run.sale_revision_run.guarded_run.compiled_raw)

    def test_existing_valuation_conflict_preserved_not_silently_replaced(self):
        self.e=make_evidence(compatible=True);self.b['base_evidence_sha256']=evidence_fingerprint(self.e)
        p=self.run_case().payload
        self.assertEqual(f(p['existing_sale_valuation_claim']['value']),500)
        self.assertEqual(f(p['candidate_value']),400)
        self.assertIn('existing_sale_valuation_claim_conflicts_with_computed_value',p['blockers'])
        self.assertIsNone(p['sale_revision_run'])
        spec=json.loads(self.vr);spec['cap_rate']['value']={'numerator':'2','denominator':'25'};self.value_revision(spec)
        self.assertEqual(self.run_case().payload['state'],'compiled_synthetic')

    def test_blocked_value_not_used_as_zero_cash(self):
        s=json.loads(self.vr);s['cap_rate']['value']=None;self.value_revision(s)
        run=self.run_case();self.assertIsNone(run.payload['sale_revision_run'])
        self.assertIn('computed_exit_value_unavailable',run.payload['blockers'])

    def test_spec_base_hash_target_and_other_sources_basis_guards(self):
        original=copy.deepcopy(self.b)
        for key,value in [('base_evidence_sha256','0'*64),('exit_spec_sha256','0'*64),('exit_run_sha256','0'*64),
                           ('sale_node_id','unknown'),('sale_node_id','SYNTHETIC-project-refinance'),('unchanged_other_sources_basis_ref',None)]:
            self.b=copy.deepcopy(original);self.b[key]=value
            self.assertIsNone(self.run_case().payload['sale_revision_run'])

    def test_value_result_forgery_rejected_even_with_updated_hash(self):
        p=self.v.payload;p['candidate_value']={'numerator':'9999','denominator':'1'};text=canonical(p)
        self.v=replace(self.v,payload_json=text,sha256=digest(text));self.b['exit_run_sha256']=self.v.sha256
        with self.assertRaises(ValidationError):self.run_case()

    def test_full_report_replay_rejects_forgery_and_changed_bridge(self):
        run=self.run_case()
        self.assertEqual(verify_exit_sale(self.e,self.nr,self.n,self.vr,self.v,raw(self.b),run),run)
        p=run.payload;p['state']='PASS';text=canonical(p)
        with self.assertRaises(ValidationError):verify_exit_sale(self.e,self.nr,self.n,self.vr,self.v,raw(self.b),replace(run,payload_json=text,sha256=digest(text)))
        self.b['sale_at_value_hypothesis_ref']+='-revision'
        with self.assertRaises(ValidationError):verify_exit_sale(self.e,self.nr,self.n,self.vr,self.v,raw(self.b),run)

    def test_generated_proceeds_have_explicit_value_and_hypothesis_lineage(self):
        p=self.run_case().payload;s=json.loads(p['sale_revision_spec_json'])
        claim=s['replacement_claims']['gross_proceeds']
        self.assertIn(self.v.sha256,claim['source_ref']);self.assertIn(self.b['sale_at_value_hypothesis_ref'],claim['source_ref'])
        self.assertEqual(claim['basis'],'cash_flow_at_closing');self.assertEqual(claim['as_of_date'],'2027-07-01')

    def test_syntax_budget_and_unrequested_profiles_rejected(self):
        for p in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_exit_sale_bridge(p)
        self.b['fees_percent']=.05
        with self.assertRaises(ValidationError):self.run_case()

    def test_no_actual_sale_approval_policy_or_personal_return(self):
        p=self.run_case().payload
        for key in ['value_also_added_as_separate_investor_receipt','actual_sale_price_or_cash_verified',
                    'costs_recomputed_from_price','bank_credit_approved','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return']);self.assertEqual(p['decision'],'PENDING')


if __name__=='__main__':unittest.main()
