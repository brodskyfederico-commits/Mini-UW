import copy,hashlib,json,tempfile,unittest
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.operating_returns import OperatingReturnBinding,assemble_operating_returns
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def num(n):return q(F(n))
def sha(b):return hashlib.sha256(b).hexdigest()
def f(q):return F(int(q['numerator']),int(q['denominator']))


class OperatingReturnsTests(unittest.TestCase):
    def setUp(self):
        self.noi_raw=(R/'templates/synthetic-operating-noi.json').read_bytes();self.noi=produce_operating_noi(self.noi_raw)
        self.spec=json.loads((R/'templates/synthetic-operating-cash.json').read_bytes());self.investor=json.loads((R/'templates/synthetic-operating-investor-slots.json').read_bytes())
    def setup_runs(self,spec=None,investor=None,contribution=None):
        s=raw(self.spec if spec is None else spec);i=raw(self.investor if investor is None else investor);c=reconcile_operating_cash(self.noi_raw,self.noi,s)
        b=OperatingReturnBinding(profile_id='SYNTHETIC-EMPTY-OPERATING-EQUITY-SLOTS-v1',investor_source_sha256=sha(i),cash_spec_sha256=sha(s),cash_run_sha256=c.sha256,distribution_event_id='op1',contribution_event_id=contribution)
        return s,i,c,b
    def run_case(self,spec=None,investor=None,contribution=None):
        s,i,c,b=self.setup_runs(spec,investor,contribution);return assemble_operating_returns(self.noi_raw,self.noi,s,c,i,b)
    def test_operating_distribution_composes_into_ten_dollar_return_without_overwrite(self):
        before=raw(self.investor);p=produce_investor_returns(before).payload;self.assertEqual(p['cash_metrics_state'],'blocked')
        r=self.run_case();self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(raw(self.investor),before)
        out=r.investor_run.payload;self.assertEqual(f(out['gross_distributions']),1600);self.assertEqual(f(out['net_cash_profit']),600);self.assertEqual(f(out['equity_multiple']),F(8,5))
        e=next(e for e in out['normalized_story']['events']if e['event_id']=='op1');self.assertEqual(f(e['amount']),1);self.assertEqual(e['date'],'2027-12-31')
    def test_compiled_event_has_exact_cash_run_and_pointer_lineage(self):
        s,i,c,b=self.setup_runs();r=assemble_operating_returns(self.noi_raw,self.noi,s,c,i,b)
        p=json.loads(r.compiled_raw);event=next(e for e in p['events']if e['event_id']=='op1')
        self.assertEqual(event['source_ref'],'miniuw:operating-cash:'+c.sha256+'#/exportable_operating_distribution')
        self.assertEqual(r.payload['changes'][0]['before']['amount'],None);self.assertEqual(r.payload['changes'][0]['after'],event)
        self.assertEqual(r.payload['compiled_investor_source_sha256'],sha(r.compiled_raw));self.assertEqual(r.investor_run,produce_investor_returns(r.compiled_raw))
    def test_unrelated_investor_values_and_policies_preserved_exactly(self):
        p=json.loads(self.run_case().compiled_raw);original=copy.deepcopy(self.investor)
        p['events'][2]=original['events'][2];self.assertEqual(p,original)
    def test_populated_target_is_never_silently_replaced(self):
        self.investor['events'][2]['amount']=num(999);r=self.run_case()
        self.assertIsNone(r.compiled_raw);self.assertIn('op1:target_amount_not_empty_no_implicit_override',r.payload['blockers']);self.assertEqual(self.investor['events'][2]['amount'],num(999))
    def test_target_classification_currency_date_and_identity_guards(self):
        for field,value in [('category','net_sale_distribution'),('currency','EUR'),('date','2028-12-31'),('event_id','other')]:
            i=copy.deepcopy(self.investor);i['events'][2][field]=value;self.assertIsNone(self.run_case(investor=i).compiled_raw)
    def test_stale_source_spec_run_and_unsupported_binding_guards(self):
        s,i,c,b=self.setup_runs()
        for field in ['investor_source_sha256','cash_spec_sha256','cash_run_sha256']:
            bad=replace(b,**{field:'0'*64});r=assemble_operating_returns(self.noi_raw,self.noi,s,c,i,bad);self.assertIn(field+'_mismatch',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
        with self.assertRaises(ValidationError):replace(b,profile_id='automatic_distribution')
        with self.assertRaises(ValidationError):replace(b,contribution_event_id='op1')
    def test_context_mismatch_and_off_grid_date_do_not_shift_event(self):
        self.investor['context']['run_id']='SYNTHETIC-other';r=self.run_case();self.assertIsNone(r.compiled_raw)
        self.investor['context']=self.noi.payload['context'];self.spec['cash_date']='2027-12-30';r=self.run_case()
        self.assertIn('cash_date_not_bound_to_investor_grid',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
    def test_blocked_cash_never_becomes_investor_distribution(self):
        self.spec['amounts']['debt_fee_payment']['value']=None;r=self.run_case()
        self.assertIsNone(r.compiled_raw);self.assertIsNone(r.investor_run);self.assertIn('operating_cash_plan_blocked',r.payload['blockers']);self.assertTrue(r.payload['cash_blockers'])
    def test_positive_additional_equity_requires_explicit_empty_slot(self):
        self.spec['amounts']['equity_contribution']['value']=num(200);self.spec['amounts']['closing_free_cash_claim']['value']=num(610)
        r=self.run_case();self.assertIsNone(r.compiled_raw);self.assertIn('positive_contribution_requires_explicit_additional_capital_slot',r.payload['blockers'])
        self.investor['events'].append(dict(event_id='additional',date='2027-12-31',kind='contribution',category='additional_capital',amount=None,currency='USD',source_ref=None))
        r=self.run_case(contribution='additional');p=r.investor_run.payload
        self.assertEqual(f(p['gross_contributions']),1200);self.assertEqual(f(p['normalized_story']['total_contributions']),12);self.assertEqual(f(p['equity_multiple']),F(4,3))
        self.assertEqual(len(r.payload['changes']),2)
    def test_zero_distribution_is_preserved_and_not_missing(self):
        self.spec['amounts']['planned_operating_distribution']['value']=num(0);self.spec['amounts']['closing_free_cash_claim']['value']=num(510)
        p=self.run_case().investor_run.payload;event=next(e for e in p['events']if e['event_id']=='op1');self.assertEqual(f(event['amount']),0);self.assertEqual(f(p['gross_distributions']),1500)
    def test_other_missing_investor_event_still_blocks_complete_return(self):
        self.investor['events'][4]['amount']=None;r=self.run_case()
        self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(r.investor_run.payload['cash_metrics_state'],'blocked');self.assertEqual(r.investor_run.payload['decision'],'PENDING')
    def test_rehashed_forged_cash_run_rejected_before_consumption(self):
        s,i,c,b=self.setup_runs();p=c.payload;p['exportable_operating_distribution']=num(999);enc=canonical(p);fake=replace(c,payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):assemble_operating_returns(self.noi_raw,self.noi,s,fake,i,replace(b,cash_run_sha256=fake.sha256))
    def test_payload_copy_and_compiled_output_do_not_mutate_run(self):
        r=self.run_case();p=r.payload;p['changes'].clear();self.assertEqual(len(r.payload['changes']),1);self.assertEqual(r.sha256,digest(r.payload_json))
    def test_reopened_archive_replays_noi_cash_compilation_and_returns(self):
        s,i,c,b=self.setup_runs();r=assemble_operating_returns(self.noi_raw,self.noi,s,c,i,b)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'returns.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_operating_returns(self.noi_raw,self.noi,s,c,i,b,r);self.assertEqual(key,a.save_operating_returns(self.noi_raw,self.noi,s,c,i,b,r))
            with EvidenceArchive(path)as a:
                recovered=a.load_operating_returns(key);self.assertEqual(recovered.run,r);self.assertEqual(recovered.run.investor_run,r.investor_run)
                self.assertEqual(a.get_investor_returns_source(recovered.payload['investor_source_sha256']),i);self.assertEqual(a.get_investor_returns_source(recovered.payload['compiled_source_sha256']),r.compiled_raw)
    def test_archive_forgery_rollback_version_and_missing_compiled_source(self):
        s,i,c,b=self.setup_runs();r=assemble_operating_returns(self.noi_raw,self.noi,s,c,i,b);p=r.payload;p['changes']=[];enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_operating_returns(self.noi_raw,self.noi,s,c,i,b,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_operating_returns(self.noi_raw,self.noi,s,c,i,b,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_operating_returns(self.noi_raw,self.noi,s,c,i,b,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_operating_returns(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_operating_returns(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(r.compiled_raw)))
            with self.assertRaises(MissingEvidence):a.load_operating_returns(key)
    def test_blocked_assembly_also_replays_without_invented_compiled_source(self):
        self.spec['amounts']['debt_interest_payment']['value']=None;s,i,c,b=self.setup_runs();r=assemble_operating_returns(self.noi_raw,self.noi,s,c,i,b)
        with EvidenceArchive(':memory:')as a:
            key=a.save_operating_returns(self.noi_raw,self.noi,s,c,i,b,r);self.assertEqual(a.load_operating_returns(key).run,r);self.assertIsNone(a.load_operating_returns(key).run.compiled_raw)
    def test_complete_return_and_decision_not_claimed_by_successful_assembly(self):
        r=self.run_case();self.assertEqual(r.payload['decision'],'PENDING');self.assertEqual(r.investor_run.payload['decision'],'PENDING')
        for k in ['original_source_overwritten','whole_investor_story_complete','distribution_authorized','financially_validated','run_ready','production_authorized']:self.assertFalse(r.payload[k])

    def test_computed_residential_noi_can_feed_cash_then_investor_returns(self):
        from miniuw_foundation.rental_operations import produce_rental_operations
        from miniuw_foundation.rental_noi import assemble_rental_noi
        rental_raw=(R/'templates/synthetic-residential-operations.json').read_bytes()
        rental=produce_rental_operations(rental_raw)
        assembly=assemble_rental_noi(rental_raw,rental,(R/'templates/synthetic-residential-noi-assembly.json').read_bytes())
        self.noi_raw=assembly.compiled_raw;self.noi=assembly.noi_run
        self.spec.update(context=self.noi.payload['context'],period_ref=self.noi.payload['period_ref'],noi_source_sha256=sha(self.noi_raw),noi_run_sha256=self.noi.sha256)
        period=self.spec['period_ref']
        for pair in self.spec['working_balances'].values():
            for cutoff,prefix in [('opening','OPENING:'),('closing','CLOSING:')]:pair[cutoff].update(value=num(0),period_ref=prefix+period)
        for key,row in self.spec['amounts'].items():
            prefix='OPENING:'if key.startswith('opening_')else'CLOSING:'if key.startswith('closing_')else''
            row.update(value=num(0),period_ref=prefix+period)
        for key,value in [('operating_receipts_claim',10800),('operating_payments_claim',2800),('planned_operating_distribution',100),('closing_free_cash_claim',7900)]:self.spec['amounts'][key]['value']=num(value)
        self.investor['context']=self.noi.payload['context'];r=self.run_case()
        self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(f(r.investor_run.payload['gross_distributions']),1600)
        s,i,c,b=self.setup_runs();self.assertEqual(c.payload['noi_run_sha256'],assembly.noi_run.sha256);self.assertEqual(f(c.payload['net_operating_cash']),8000)
        # T26 replays the supplied compiled NOI; T22 retains the preceding rent chain.
        with EvidenceArchive(':memory:')as a:
            upstream=a.save_rental_noi(rental_raw,rental,(R/'templates/synthetic-residential-noi-assembly.json').read_bytes(),assembly)
            downstream=a.save_operating_returns(self.noi_raw,self.noi,s,c,i,b,r)
            self.assertEqual(a.load_rental_noi(upstream).run.noi_run.sha256,a.load_operating_returns(downstream).payload['noi_run']['sha256'])
