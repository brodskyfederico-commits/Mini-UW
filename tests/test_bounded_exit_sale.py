import copy,json
from dataclasses import replace
from fractions import Fraction as F
import unittest
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale,verify_bounded_exit_sale,parse_bounded_exit_sale
from miniuw_foundation.sale_recovery import analyze_sale_recovery
from miniuw_foundation.current_exit_output import assemble_current_exit_output
from bounded_cost_test_support import case,bounds_spec
from sale_cost_test_support import cost_source,bridge_spec,raw,sha

def f(q):return F(int(q['numerator']),int(q['denominator']))


class BoundedExitSaleTests(unittest.TestCase):
    def setUp(self):self.args=case()
    def run_case(self):return assemble_bounded_exit_sale(*self.args)
    def with_spec(self,change):
        spec=json.loads(self.args[-1]);spec.update(change);self.args=(*self.args[:-1],raw(spec))

    def test_independent_cash_return_cost_replaced_once(self):
        run=self.run_case();self.assertEqual(run.payload['state'],'compiled_synthetic')
        p=run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload
        self.assertEqual(f(run.payload['computed_closing_cost']),35)
        self.assertEqual(f(p['net_cash_profit']),F('283.9197'))
        self.assertEqual(f(p['cash_by_category']['net_sale_distribution']),F('730.9097'))

    def test_new_price_replays_cost_and_limit_and_returns(self):
        e,nr,n,vr,v,cr,c,br,bounded,sr=self.args
        spec=json.loads(vr);spec['cap_rate']['value']={'numerator':'1','denominator':'5'}
        vr=raw(spec);v=produce_exit_value(nr,n,vr);cr=raw(cost_source(v));c=produce_sale_costs(cr)
        br=raw(bounds_spec(cr,c));bounded=produce_bounded_sale_costs(cr,c,br)
        s=bridge_spec(e,vr,v,cr,c);s.update(schema='miniuw.synthetic-bounded-exit-sale.v1',bounds_source_sha256=sha(br),bounded_run_sha256=bounded.sha256)
        self.args=(e,nr,n,vr,v,cr,c,br,bounded,raw(s))
        run=self.run_case();self.assertEqual(f(run.payload['computed_closing_cost']),35)
        self.assertEqual(f(run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload['net_cash_profit']),F('83.9197'))

    def test_all_seven_binding_hashes_required(self):
        original=self.args
        for key in ['base_evidence_sha256','exit_spec_sha256','exit_run_sha256','cost_source_sha256','cost_run_sha256','bounds_source_sha256','bounded_run_sha256']:
            self.args=original;self.with_spec({key:'0'*64})
            self.assertIsNone(self.run_case().exit_sale_run)

    def test_limit_conflict_never_exported_as_partial_total(self):
        args=list(self.args);bounds=json.loads(args[7]);bounds['rules'][1]['minimum']['value']={'numerator':'50','denominator':'1'}
        args[7]=raw(bounds);args[8]=produce_bounded_sale_costs(args[5],args[6],args[7]);s=json.loads(args[9]);s.update(bounds_source_sha256=sha(args[7]),bounded_run_sha256=args[8].sha256);args[9]=raw(s);self.args=tuple(args)
        run=self.run_case();self.assertIsNone(run.payload['computed_closing_cost']);self.assertIsNone(run.exit_sale_run)

    def test_price_lineage_even_if_bounded_total_looks_right(self):
        args=list(self.args);cost=json.loads(args[5]);cost['gross_price']['source_ref']='SYNTHETIC-other-run'
        args[5]=raw(cost);args[6]=produce_sale_costs(args[5]);args[7]=raw(bounds_spec(args[5],args[6]));args[8]=produce_bounded_sale_costs(args[5],args[6],args[7])
        spec=json.loads(args[9]);spec.update(cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256,bounds_source_sha256=sha(args[7]),bounded_run_sha256=args[8].sha256);args[9]=raw(spec);self.args=tuple(args)
        self.assertIn('bounded_cost_price_or_exit_run_lineage_mismatch',self.run_case().payload['blockers'])

    def test_bank_blocker_preserved(self):
        self.args=case(False);run=self.run_case()
        self.assertIn('refinance_capacity_or_selection_blocked',run.payload['blockers'])
        self.assertIsNone(run.exit_sale_run.sale_revision_run.guarded_run.compiled_raw)

    def test_missing_sale_hypothesis_still_blocks(self):
        self.with_spec({'sale_at_value_hypothesis_ref':None})
        self.assertIsNone(self.run_case().exit_sale_run.sale_revision_run)

    def test_rehashed_bounded_result_forgery_rejected(self):
        args=list(self.args);p=args[8].payload;p['total_closing_cost']={'numerator':'0','denominator':'1'};text=canonical(p)
        args[8]=replace(args[8],payload_json=text,sha256=digest(text));spec=json.loads(args[9]);spec['bounded_run_sha256']=args[8].sha256;args[9]=raw(spec);self.args=tuple(args)
        with self.assertRaises(ValidationError):self.run_case()

    def test_full_report_replay_forgery_and_stale_spec_rejected(self):
        run=self.run_case();self.assertEqual(verify_bounded_exit_sale(*self.args,run),run)
        p=run.payload;p['computed_closing_cost']={'numerator':'0','denominator':'1'};text=canonical(p)
        with self.assertRaises(ValidationError):verify_bounded_exit_sale(*self.args,replace(run,payload_json=text,sha256=digest(text)))
        self.with_spec({'revision_id':'SYNTHETIC-next-revision'})
        with self.assertRaises(ValidationError):verify_bounded_exit_sale(*self.args,run)

    def test_generated_claim_has_result_pointer_and_metadata(self):
        run=self.run_case();spec=json.loads(run.payload['generated_exit_sale_spec_json']);claim=spec['closing_cost_claim']
        self.assertIn(self.args[8].sha256,claim['source_ref']);self.assertEqual(claim['basis'],'cash_flow_at_closing')
        self.assertEqual(claim['as_of_date'],'2027-07-01')

    def test_old_affine_and_freshness_paths_reject_new_result_type(self):
        run=self.run_case();old_args=(*self.args[:7],raw(bridge_spec(self.args[0],self.args[3],self.args[4],self.args[5],self.args[6])))
        spec=raw(dict(schema='miniuw.synthetic-affine-sale-cash-recovery.v1',base_costed_run_sha256=run.sha256,gross_price_domain=dict(lower={'numerator':'0','denominator':'1'},upper={'numerator':'1000','denominator':'1'}),cost_profile_domain_basis_ref='SYNTHETIC-test',other_sources_fixed_basis_ref='SYNTHETIC-test'))
        with self.assertRaises(ValidationError):analyze_sale_recovery(old_args,run,spec)
        with self.assertRaises(ValidationError):assemble_current_exit_output(old_args,run,b'{}',None,'2027-07-01T00:00:00Z')

    def test_syntax_shape_budget_and_authority(self):
        for b in [b'[]',b'NaN',b'\xff',b' '*131073,b'{"schema":1,"schema":2}']:
            with self.assertRaises(ValidationError):parse_bounded_exit_sale(b)
        p=self.run_case().payload
        for key in ['global_affine_recovery_analysis_produced','evidence_currency_checked','contract_or_tax_rule_verified','bank_credit_approved','real_decisions_enabled','production_authorized']:self.assertIs(p[key],False)
        self.assertIsNone(p['personal_investor_return']);self.assertEqual(p['decision'],'PENDING')


if __name__=='__main__':unittest.main()
