import json,tempfile,unittest,copy
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q,produce_debt_service
from miniuw_foundation.project_cash import reconcile_project_cash
from miniuw_foundation.project_returns import ProjectEventSlot,ProjectReturnBinding,assemble_project_returns
from miniuw_foundation.refinance_capacity import size_refinance
from miniuw_foundation.capacity_project_returns import CapacityProjectBinding,assemble_capacity_checked_returns,binding_from_record
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from capacity_test_support import load_capacity,build_capacity,raw,sha
from project_test_support import load_case,build

def f(q):return F(int(q['numerator']),int(q['denominator']))
def num(n):return q(F(n))


class CapacityProjectTests(unittest.TestCase):
    def setUp(self):self.project=load_case();self.cap=load_capacity('project')
    def case(self):
        ops,closings,m=build(self.project);p=reconcile_project_cash(ops,closings,m);inputs,s=build_capacity(self.cap);c=size_refinance(inputs,s);i=raw(self.project['investor'])
        slots=tuple(ProjectEventSlot(node_id=row['node_id'],distribution_event_id=eid,contribution_event_id=None)for row,eid in zip(json.loads(m)['nodes'],['op-before','refi','op-after','sale']))
        inner=ProjectReturnBinding(profile_id='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1',manifest_source_sha256=sha(m),project_run_sha256=p.sha256,investor_source_sha256=sha(i),opening_contribution_event_ids=('initial',),slots=slots)
        b=CapacityProjectBinding(profile_id='SYNTHETIC-CAPACITY-CHECKED-PROJECT-RETURN-v1',capacity_spec_sha256=sha(s),capacity_run_sha256=c.sha256,refinance_node_id='SYNTHETIC-project-refinance',project_return_binding=inner)
        return ops,closings,m,p,inputs,s,c,i,b
    def run_case(self):return assemble_capacity_checked_returns(*self.case())
    def allow_counterfactual_bank_noi(self):
        # Explicit test-only source revision, not a change to the saved project fixture.
        self.cap['bank']['income_rows'][0]['value']=num(2000)
    def test_balanced_legacy_cash_window_cannot_bypass_bank_capacity(self):
        ops,closings,m,p,inputs,s,c,i,b=self.case();self.assertEqual(p.payload['state'],'reconciled_synthetic_cash_window')
        self.assertEqual(assemble_project_returns(ops,closings,m,p,i,b.project_return_binding).payload['state'],'compiled_synthetic')
        r=assemble_capacity_checked_returns(ops,closings,m,p,inputs,s,c,i,b);self.assertIsNone(r.compiled_raw);self.assertIsNone(r.project_return_run)
        self.assertIn('selected_principal_exceeds_declared_bank_capacity',r.payload['capacity_blockers']);self.assertEqual(r.payload['decision'],'PENDING')
    def test_explicit_counterfactual_compatible_source_preserves_legacy_compilation(self):
        self.allow_counterfactual_bank_noi();args=self.case();r=assemble_capacity_checked_returns(*args);ops,closings,m,p,inputs,s,c,i,b=args
        self.assertEqual(c.payload['state'],'compatible_synthetic_refinance_capacity');self.assertEqual(r.payload['state'],'compiled_synthetic')
        self.assertEqual(r.compiled_raw,assemble_project_returns(ops,closings,m,p,i,b.project_return_binding).compiled_raw);self.assertEqual(f(r.investor_run.payload['gross_distributions']),F('1298.9197'))
    def test_compatible_capacity_does_not_ignore_a_cash_boundary_failure(self):
        self.allow_counterfactual_bank_noi();self.project['closings'][1]['amounts']['opening_free_cash']['value']=num(F('274.9398'))
        r=self.run_case();self.assertIn('project_cash_window_blocked',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
    def test_stale_capacity_spec_or_run_and_wrong_refinance_identity_block(self):
        self.allow_counterfactual_bank_noi();args=self.case();b=args[-1]
        for key,value in [('capacity_spec_sha256','0'*64),('capacity_run_sha256','0'*64),('refinance_node_id','SYNTHETIC-project-sale')]:
            r=assemble_capacity_checked_returns(*args[:-1],replace(b,**{key:value}));self.assertIsNone(r.compiled_raw)
    def test_different_sizing_closing_cannot_be_substituted_into_project(self):
        self.allow_counterfactual_bank_noi();self.cap['closing']['amounts']['retained_free_cash']['value']=num(599)
        args=self.case();self.assertEqual(args[6].payload['state'],'compatible_synthetic_refinance_capacity');r=assemble_capacity_checked_returns(*args)
        self.assertIn('sizing_closing_source_or_run_does_not_match_cash_refinance_node',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
    def test_same_id_principal_with_different_permanent_terms_is_not_same_loan(self):
        self.allow_counterfactual_bank_noi();self.cap['loan']['periodic_rate']=num(0)
        args=self.case();self.assertEqual(args[6].payload['state'],'compatible_synthetic_refinance_capacity');r=assemble_capacity_checked_returns(*args)
        self.assertIn('capacity_loan_source_and_run_do_not_match_project_permanent_loan',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
    def test_nested_project_binding_and_empty_target_guards_retained(self):
        self.allow_counterfactual_bank_noi();args=self.case();b=args[-1];bad=replace(b,project_return_binding=replace(b.project_return_binding,investor_source_sha256='0'*64))
        self.assertIsNone(assemble_capacity_checked_returns(*args[:-1],bad).compiled_raw)
        self.project['investor']['events'][1]['amount']=num(100);self.assertIsNone(self.run_case().compiled_raw)
    def test_rehashed_capacity_result_cannot_clear_funding_blocker(self):
        args=self.case();c=args[6];p=c.payload;p['state']='compatible_synthetic_refinance_capacity';p['blockers']=[];enc=canonical(p);fake=replace(c,payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):assemble_capacity_checked_returns(*args[:6],fake,args[7],replace(args[8],capacity_run_sha256=fake.sha256))
    def test_forged_cash_run_cannot_be_hidden_behind_blocked_bank_sizing(self):
        args=self.case();p=args[3].payload;p['totals']['loan_draws']=num(999);enc=canonical(p);fake=replace(args[3],payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):assemble_capacity_checked_returns(*args[:3],fake,*args[4:])
    def test_typed_binding_live_scope_and_immutable_payload(self):
        args=self.case();b=args[-1]
        with self.assertRaises(ValidationError):replace(b,profile_id='credit_approved')
        with self.assertRaises(ValidationError):replace(b,project_return_binding={})
        self.project['investor']['context']['deal_id']='real-deal'
        with self.assertRaises(ValidationError):self.run_case()
        self.project=load_case();r=self.run_case();p=r.payload;p['capacity_blockers']=[];self.assertTrue(r.payload['capacity_blockers']);self.assertEqual(binding_from_record(r.payload['binding']),self.case()[-1]);self.assertEqual(r.sha256,digest(r.payload_json))
    def test_reopened_archive_restores_blocked_and_compatible_paths(self):
        for compatible in [False,True]:
            if compatible:self.allow_counterfactual_bank_noi()
            args=self.case();r=assemble_capacity_checked_returns(*args)
            with tempfile.TemporaryDirectory()as t:
                path=Path(t)/'capacity-project.sqlite3'
                with EvidenceArchive(path)as a:key=a.save_capacity_project_returns(*args,r);self.assertEqual(key,a.save_capacity_project_returns(*args,r))
                with EvidenceArchive(path)as a:
                    recovered=a.load_capacity_project_returns(key);self.assertEqual(recovered.run,r);self.assertEqual(recovered.run.investor_run,r.investor_run)
                    if compatible:self.assertEqual(a.get_investor_returns_source(recovered.payload['compiled_source_sha256']),r.compiled_raw)
                    else:self.assertIsNone(recovered.payload['compiled_source_sha256'])
    def test_archive_fault_forgery_version_and_missing_capacity_source(self):
        self.allow_counterfactual_bank_noi();args=self.case();r=assemble_capacity_checked_returns(*args);p=r.payload;p['blockers']=['invented'];enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_capacity_project_returns(*args,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_capacity_project_returns(*args,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_capacity_project_returns(*args,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_capacity_project_returns(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_capacity_project_returns(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(args[4].bank_noi_raw)))
            with self.assertRaises(MissingEvidence):a.load_capacity_project_returns(key)
    def test_arithmetic_compatibility_is_not_a_credit_or_investment_decision(self):
        self.allow_counterfactual_bank_noi();r=self.run_case();self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(r.payload['decision'],'PENDING')
        for key in ['original_source_overwritten','bank_credit_approved','funds_available_verified','bank_policy_adopted','whole_project_cash_reconciled','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(r.payload[key])
