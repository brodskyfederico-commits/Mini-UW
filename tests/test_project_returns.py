import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.project_cash import reconcile_project_cash
from miniuw_foundation.project_returns import ProjectEventSlot,ProjectReturnBinding,assemble_project_returns,binding_from_record
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from project_test_support import load_case,build,raw,sha

def f(q):return F(int(q['numerator']),int(q['denominator']))
def num(n):return q(F(n))


class ProjectReturnTests(unittest.TestCase):
    def setUp(self):self.data=load_case()
    def case(self):
        ops,closes,m=build(self.data);p=reconcile_project_cash(ops,closes,m);i=raw(self.data['investor'])
        slots=tuple(ProjectEventSlot(node_id=row['node_id'],distribution_event_id=eid,contribution_event_id=None)for row,eid in zip(json.loads(m)['nodes'],['op-before','refi','op-after','sale']))
        b=ProjectReturnBinding(profile_id='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1',manifest_source_sha256=sha(m),project_run_sha256=p.sha256,investor_source_sha256=sha(i),opening_contribution_event_ids=('initial',),slots=slots)
        return ops,closes,m,p,i,b
    def run_case(self):return assemble_project_returns(*self.case())
    def test_entire_window_compiles_once_into_investor_cash_profit_multiple_and_timing(self):
        r=self.run_case();p=r.investor_run.payload;self.assertEqual(r.payload['state'],'compiled_synthetic')
        self.assertEqual(f(p['gross_contributions']),1000);self.assertEqual(f(p['gross_distributions']),F('1298.9197'));self.assertEqual(f(p['net_cash_profit']),F('298.9197'))
        self.assertEqual(f(p['equity_multiple']),F('1.2989197'));self.assertEqual(f(p['normalized_story']['total_distributions']),F('12.989197'))
        self.assertEqual([e['date']for e in p['events']],['2027-01-01','2027-03-01','2027-04-01','2027-06-01','2027-07-01'])
        self.assertEqual([f(e['net'])for e in p['dated_net_flows']],[-1000,0,100,F('353.01'),0,100,F('745.9097')])
    def test_every_equity_event_matches_exact_operation_or_closing_hash_pointer(self):
        ops,closes,m,p,i,b=self.case();r=assemble_project_returns(ops,closes,m,p,i,b)
        hashes=[ops[0].cash_run.sha256,closes[0].closing_run.sha256,ops[1].cash_run.sha256,closes[1].closing_run.sha256]
        for c,h in zip(r.payload['changes'],hashes):self.assertEqual(c['source_run_sha256'],h);self.assertIn(h,c['after']['source_ref']);self.assertIsNone(c['before']['amount'])
        self.assertEqual(r.investor_run,produce_investor_returns(r.compiled_raw));self.assertEqual(r.payload['compiled_investor_source_sha256'],sha(r.compiled_raw))
    def test_seed_is_counted_once_and_must_match_declared_opening_cash(self):
        self.data['investor']['events'][0]['amount']=num(1001);r=self.run_case();self.assertIsNone(r.compiled_raw)
        self.assertIn('initial_contributions_do_not_match_declared_opening_cash',r.payload['blockers'])
        for field,value in [('amount',None),('source_ref',None),('category','additional_capital'),('date','2027-02-01')]:
            self.data=load_case();self.data['investor']['events'][0][field]=value;self.assertIsNone(self.run_case().compiled_raw)
    def test_any_populated_target_blocks_all_changes(self):
        self.data['investor']['events'][-1]['amount']=num(700);r=self.run_case();self.assertIsNone(r.compiled_raw);self.assertEqual(r.payload['changes'],[])
        self.assertIsNone(self.data['investor']['events'][1]['amount'])
    def test_any_cash_boundary_or_debt_mismatch_blocks_all_returns(self):
        self.data['closings'][0]['amounts']['opening_free_cash']['value']=num(821);r=self.run_case()
        self.assertIsNone(r.compiled_raw);self.assertIn('project_cash_window_blocked',r.payload['blockers']);self.assertTrue(r.payload['project_cash_blockers'])
    def test_no_unbound_or_duplicate_investor_event_can_be_laundered(self):
        self.data['investor']['events'].append(dict(event_id='extra',date='2027-05-01',kind='distribution',category='other_distribution',amount=num(1),currency='USD',source_ref='SYNTHETIC-extra-claim'))
        self.assertIsNone(self.run_case().compiled_raw)
        self.data=load_case();ops,closes,m,p,i,b=self.case()
        with self.assertRaises(ValidationError):replace(b,slots=(b.slots[0],replace(b.slots[1],distribution_event_id='initial'),b.slots[2],b.slots[3]))
        with self.assertRaises(ValidationError):replace(b,opening_contribution_event_ids=('initial','initial'))
        with self.assertRaises(ValidationError):replace(b,slots=(b.slots[0],b.slots[0],b.slots[2],b.slots[3]))
    def test_missing_zero_or_nonzero_target_and_wrong_classification_block(self):
        for field,value in [('event_id','other'),('category','operating_distribution'),('date','2027-05-01'),('currency','EUR')]:
            self.data=load_case();self.data['investor']['events'][2][field]=value;self.assertIsNone(self.run_case().compiled_raw)
    def test_zero_operating_distribution_and_empty_grid_points_are_retained(self):
        for row in self.data['nois'][1]['income_rows']+self.data['nois'][1]['expense_rows']:row['value']=num(0)
        a=self.data['ops'][1]['amounts']
        for key in ['operating_receipts_claim','operating_payments_claim','planned_operating_distribution']:a[key]['value']=num(0)
        a['closing_free_cash_claim']['value']=num(F('303.9398'));self.data['closings'][1]['amounts']['opening_free_cash']['value']=num(F('303.9398'))
        r=self.run_case();self.assertEqual(r.payload['state'],'compiled_synthetic')
        e=next(e for e in r.investor_run.payload['events']if e['event_id']=='op-after');self.assertEqual(f(e['amount']),0)
        self.assertEqual(len(r.investor_run.payload['dated_net_flows']),7);self.assertEqual(f(r.investor_run.payload['dated_net_flows'][5]['net']),0)
    def test_refinance_cash_in_needs_separate_gross_event_and_never_fake_funding(self):
        self.data['closings'][0]['amounts']['retained_free_cash']['value']=num(F('1053.01'));self.data['closings'][0]['equity_funding_assumption_ref']='SYNTHETIC-projected-cash-in-not-committed-funds'
        self.data['ops'][1]['amounts']['opening_free_cash']['value']=num(F('1053.01'));self.data['ops'][1]['amounts']['closing_free_cash_claim']['value']=num(F('726.9498'));self.data['closings'][1]['amounts']['opening_free_cash']['value']=num(F('726.9498'))
        self.assertIsNone(self.run_case().compiled_raw)
        self.data['investor']['events'].append(dict(event_id='refi-in',date='2027-04-01',kind='contribution',category='refinance_cash_in',amount=None,currency='USD',source_ref=None))
        ops,closes,m,p,i,b=self.case();b=replace(b,slots=(b.slots[0],replace(b.slots[1],contribution_event_id='refi-in'),b.slots[2],b.slots[3]))
        r=assemble_project_returns(ops,closes,m,p,i,b);out=r.investor_run.payload
        self.assertEqual(f(out['gross_contributions']),1100);self.assertEqual(f(out['gross_distributions']),F('1398.9197'));self.assertEqual(f(out['net_cash_profit']),F('298.9197'))
        self.assertEqual(f(next(e for e in out['events']if e['event_id']=='refi')['amount']),0)
        self.assertEqual(f(next(e for e in out['events']if e['event_id']=='refi-in')['amount']),100);self.assertEqual(r.payload['decision'],'PENDING')
    def test_missing_capital_or_retained_value_not_reconstructed_from_cash(self):
        r=self.run_case();p=r.investor_run.payload;self.assertEqual(p['cash_metrics_state'],'computed_synthetic')
        self.assertIsNone(p['capital_snapshots'][0]['capital_still_invested']);self.assertIsNone(p['capital_snapshots'][0]['retained_equity_value'])
        self.assertFalse(p['investor_story_complete']);self.assertFalse(p['declared_cash_story_computable']);self.assertEqual(p['decision'],'PENDING')
    def test_hashes_context_and_exact_grid_horizon_guards(self):
        ops,closes,m,p,i,b=self.case()
        for key in ['manifest_source_sha256','project_run_sha256','investor_source_sha256']:
            result=assemble_project_returns(ops,closes,m,p,i,replace(b,**{key:'0'*64}));self.assertIn(key+'_mismatch',result.payload['blockers']);self.assertIsNone(result.compiled_raw)
        self.data['investor']['context']['run_id']='SYNTHETIC-other';self.assertIsNone(self.run_case().compiled_raw)
        self.data=load_case();self.data['investor']['grid']['dates'].append('2027-08-01');self.assertIsNone(self.run_case().compiled_raw)
    def test_rehashed_project_result_cannot_forge_distribution_or_skip_debt(self):
        ops,closes,m,p,i,b=self.case();body=p.payload;body['exportable_equity_movements'][-1]['distribution']=num(9999);enc=canonical(body);fake=replace(p,payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):assemble_project_returns(ops,closes,m,fake,i,replace(b,project_run_sha256=fake.sha256))
    def test_original_sources_payload_and_typed_binding_roundtrip(self):
        ops,closes,m,p,i,b=self.case();r=assemble_project_returns(ops,closes,m,p,i,b);out=r.payload;out['changes']=[]
        self.assertEqual(len(r.payload['changes']),4);self.assertEqual(binding_from_record(r.payload['binding']),b);self.assertEqual(i,raw(self.data['investor']));self.assertEqual(r.sha256,digest(r.payload_json))
        with self.assertRaises(ValidationError):replace(b,profile_id='approved_project')
    def test_reopened_archive_recovers_entire_cash_window_and_investor_ledger(self):
        ops,closes,m,p,i,b=self.case();r=assemble_project_returns(ops,closes,m,p,i,b)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'project-return.sqlite3'
            with EvidenceArchive(path)as a:
                cash=a.save_project_cash(ops,closes,m,p);ret=a.save_project_returns(ops,closes,m,p,i,b,r);self.assertEqual(ret,a.save_project_returns(ops,closes,m,p,i,b,r))
            with EvidenceArchive(path)as a:
                recovered=a.load_project_returns(ret);self.assertEqual(recovered.run,r);self.assertEqual(recovered.run.investor_run,r.investor_run)
                self.assertEqual(a.load_project_cash(cash).run.sha256,recovered.payload['project_run']['sha256']);self.assertEqual(a.get_investor_returns_source(recovered.payload['investor_source_sha256']),i)
                self.assertEqual(a.get_investor_returns_source(recovered.payload['compiled_source_sha256']),r.compiled_raw)
    def test_archive_rollback_forgery_version_missing_and_blocked_recovery(self):
        ops,closes,m,p,i,b=self.case();r=assemble_project_returns(ops,closes,m,p,i,b);body=r.payload;body['changes']=[];enc=canonical(body);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_project_returns(ops,closes,m,p,i,b,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_project_returns(ops,closes,m,p,i,b,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_project_returns(ops,closes,m,p,i,b,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_project_returns(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_project_returns(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(closes[0].debt_spec_raw)))
            with self.assertRaises(MissingEvidence):a.load_project_returns(key)
        self.data['ops'][1]['amounts']['debt_principal_payment']['value']=None;ops,closes,m,p,i,b=self.case();r=assemble_project_returns(ops,closes,m,p,i,b)
        with EvidenceArchive(':memory:')as a:key=a.save_project_returns(ops,closes,m,p,i,b,r);self.assertEqual(a.load_project_returns(key).run,r)
    def test_no_scope_expansion_into_actual_underwriting_or_approval(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['original_source_overwritten','whole_project_cash_reconciled','whole_investor_story_complete','actual_cash_and_payment_history_verified','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])

    def test_irr_bounds_certify_full_monthly_vector_and_conditional_annualization(self):
        p=self.run_case().investor_run.payload;self.assertEqual(p['periodic_irr']['distinct_positive_discount_roots'],1)
        interval=p['periodic_irr']['roots'][0]['periodic_rate_interval'];lo,hi=F(interval['lower']),F(interval['upper'])
        poly=lambda r:-1000*(1+r)**6+100*(1+r)**4+F('353.01')*(1+r)**3+100*(1+r)+F('745.9097')
        self.assertGreaterEqual(poly(lo),0);self.assertLessEqual(poly(hi),0)
        annual=p['annual_irr_roots'][0]['annual_rate_interval'];self.assertEqual(f(annual['lower']),(1+lo)**12-1);self.assertEqual(f(annual['upper']),(1+hi)**12-1);self.assertIsNone(p['selected_IRR'])
