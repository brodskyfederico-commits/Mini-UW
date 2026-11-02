import copy,json,tempfile,unittest,hashlib
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.closing_returns import ClosingReturnBinding,assemble_closing_returns
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(p):return hashlib.sha256(p).hexdigest()
def num(n):return q(F(n))
def f(q):return F(int(q['numerator']),int(q['denominator']))


class ClosingReturnsTests(unittest.TestCase):
    def setUp(self):self.refi=json.loads((R/'templates/synthetic-refinance-closing.json').read_bytes());self.sale=json.loads((R/'templates/synthetic-sale-closing.json').read_bytes());self.investor=json.loads((R/'templates/synthetic-closing-investor-slots.json').read_bytes())
    def case(self,source=None,investor=None,contribution=None):
        s=raw(self.refi if source is None else source);i=raw(self.investor if investor is None else investor);c=produce_closing_cash(s)
        b=ClosingReturnBinding(profile_id='SYNTHETIC-CLOSING-EMPTY-EQUITY-SLOTS-v1',closing_source_sha256=sha(s),closing_run_sha256=c.sha256,investor_source_sha256=sha(i),distribution_event_id='refi'if c.payload['kind']=='refinance'else'sale',contribution_event_id=contribution)
        return s,c,i,b
    def run_case(self,**kw):return assemble_closing_returns(*self.case(**kw))
    def test_refinance_and_sale_compose_net_receipts_into_return(self):
        original=raw(self.investor);first=self.run_case();second=self.run_case(source=self.sale,investor=json.loads(first.compiled_raw));p=second.investor_run.payload
        self.assertEqual(f(p['gross_distributions']),1600);self.assertEqual(f(p['net_cash_profit']),600);self.assertEqual(f(p['equity_multiple']),F(8,5))
        n=p['normalized_story'];self.assertEqual(f(n['total_distributions']),16);self.assertEqual([f(e['amount'])for e in n['events']],[10,5,1,1,9]);self.assertEqual(raw(self.investor),original)
    def test_exact_closing_output_pointer_and_date_provenance(self):
        s,c,i,b=self.case();r=assemble_closing_returns(s,c,i,b);change=r.payload['changes'][0]
        self.assertIsNone(change['before']['amount']);self.assertEqual(change['after']['source_ref'],'miniuw:closing-cash:'+c.sha256+'#/exportable_equity_distribution')
        self.assertEqual(change['after']['date'],c.payload['closing_date']);self.assertEqual(r.investor_run,produce_investor_returns(r.compiled_raw));self.assertEqual(r.payload['compiled_investor_source_sha256'],sha(r.compiled_raw))
    def test_other_missing_event_keeps_return_pending_even_after_refi_compiles(self):
        r=self.run_case();self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(r.investor_run.payload['cash_metrics_state'],'blocked');self.assertEqual(r.investor_run.payload['decision'],'PENDING')
    def test_only_target_event_changes_and_stocks_stay_outside_cash(self):
        r=self.run_case();p=json.loads(r.compiled_raw);p['events'][1]=copy.deepcopy(self.investor['events'][1]);self.assertEqual(p,self.investor)
        self.assertFalse(r.investor_run.payload['retained_equity_included_in_cash_receipts'])
    def test_existing_amount_date_currency_and_wrong_classification_block(self):
        for field,value in [('amount',num(500)),('date','2029-01-01'),('currency','EUR'),('category','operating_distribution')]:
            i=copy.deepcopy(self.investor);i['events'][1][field]=value;r=self.run_case(investor=i);self.assertIsNone(r.compiled_raw);self.assertEqual(r.payload['changes'],[])
    def test_stale_source_run_investor_hash_and_binding_identity_guards(self):
        s,c,i,b=self.case()
        for key in ['closing_source_sha256','closing_run_sha256','investor_source_sha256']:
            r=assemble_closing_returns(s,c,i,replace(b,**{key:'0'*64}));self.assertIn(key+'_mismatch',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
        with self.assertRaises(ValidationError):replace(b,contribution_event_id=b.distribution_event_id)
        with self.assertRaises(ValidationError):replace(b,profile_id='approved_payout')
    def test_context_and_off_grid_cutoff_are_not_adjusted(self):
        self.investor['context']['run_id']='SYNTHETIC-other';self.assertIsNone(self.run_case().compiled_raw)
        self.investor=json.loads((R/'templates/synthetic-closing-investor-slots.json').read_bytes());self.refi['closing_date']='2028-01-02'
        # All dated amounts still refer to the prior cutoff, so the producer blocks first.
        r=self.run_case();self.assertIn('closing_plan_blocked',r.payload['blockers']);self.assertIn('closing_date_not_bound_to_investor_grid',r.payload['blockers'])
    def test_partial_payoff_never_exports_as_complete_closing(self):
        self.refi['old_debts'][0]['fees_paid']['value']=None;r=self.run_case();self.assertIsNone(r.compiled_raw);self.assertTrue(r.payload['closing_blockers'])
    def test_cash_in_requires_separate_refinance_contribution_slot(self):
        self.refi['amounts']['gross_proceeds']['value']=num(900);self.refi['new_loan']['principal_after_closing']['value']=num(900);self.refi['equity_funding_assumption_ref']='SYNTHETIC-only-projected-funding'
        self.assertIsNone(self.run_case().compiled_raw)
        self.investor['events'].append(dict(event_id='cash-in',date='2028-01-01',kind='contribution',category='refinance_cash_in',amount=None,currency='USD',source_ref=None))
        r=self.run_case(contribution='cash-in');p=json.loads(r.compiled_raw);self.assertEqual(f(p['events'][1]['amount']),0);self.assertEqual(f(p['events'][-1]['amount']),200)
        self.assertFalse(r.payload['equity_funding_available_verified']);self.assertEqual(r.payload['decision'],'PENDING')
    def test_sale_shortfall_uses_additional_capital_not_refinance_cash_in(self):
        self.sale['amounts']['gross_proceeds']['value']=num(1300);self.sale['equity_funding_assumption_ref']='SYNTHETIC-projected-sale-shortfall'
        self.investor['events'].append(dict(event_id='sale-cash-in',date='2029-01-01',kind='contribution',category='refinance_cash_in',amount=None,currency='USD',source_ref=None))
        self.assertIsNone(self.run_case(source=self.sale,contribution='sale-cash-in').compiled_raw)
        self.investor['events'][-1]['category']='additional_capital';r=self.run_case(source=self.sale,contribution='sale-cash-in');p=json.loads(r.compiled_raw)
        self.assertEqual(f(next(e for e in p['events']if e['event_id']=='sale')['amount']),0);self.assertEqual(f(p['events'][-1]['amount']),200)
    def test_rehashed_closing_result_cannot_invent_investor_receipt(self):
        s,c,i,b=self.case();p=c.payload;p['exportable_equity_distribution']=num(9999);enc=canonical(p);fake=replace(c,payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):assemble_closing_returns(s,fake,i,replace(b,closing_run_sha256=fake.sha256))
    def test_immutable_payload_and_original_source(self):
        r=self.run_case();p=r.payload;p['changes']=[];self.assertEqual(len(r.payload['changes']),1);self.assertEqual(r.sha256,digest(r.payload_json));self.assertIsNone(self.investor['events'][1]['amount'])
    def test_reopened_two_closing_bundles_preserve_intermediate_source_link(self):
        s,c,i,b=self.case();first=assemble_closing_returns(s,c,i,b);s2,c2,i2,b2=self.case(source=self.sale,investor=json.loads(first.compiled_raw));second=assemble_closing_returns(s2,c2,i2,b2)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'closings.sqlite3'
            with EvidenceArchive(path)as a:
                k1=a.save_closing_returns(s,c,i,b,first);k2=a.save_closing_returns(s2,c2,i2,b2,second);self.assertEqual(k2,a.save_closing_returns(s2,c2,i2,b2,second))
            with EvidenceArchive(path)as a:
                a1=a.load_closing_returns(k1);a2=a.load_closing_returns(k2);self.assertEqual(a1.run,first);self.assertEqual(a2.run,second)
                self.assertEqual(a1.run.payload['compiled_investor_source_sha256'],a2.payload['investor_source_sha256']);self.assertEqual(a2.run.investor_run,second.investor_run)
    def test_archive_fault_forgery_version_missing_and_blocked_recovery(self):
        s,c,i,b=self.case();r=assemble_closing_returns(s,c,i,b);p=r.payload;p['changes']=[];enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_closing_returns(s,c,i,b,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_closing_returns(s,c,i,b,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_closing_returns(s,c,i,b,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_closing_returns(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_closing_returns(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(r.compiled_raw)))
            with self.assertRaises(MissingEvidence):a.load_closing_returns(key)
        self.refi['debt_inventory_declared_complete']=None;s,c,i,b=self.case();r=assemble_closing_returns(s,c,i,b)
        with EvidenceArchive(':memory:')as a:key=a.save_closing_returns(s,c,i,b,r);self.assertEqual(a.load_closing_returns(key).run,r)
    def test_computation_never_enables_real_distribution_or_model_closure(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['original_source_overwritten','whole_project_cash_reconciled','whole_investor_story_complete','equity_funding_available_verified','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])
