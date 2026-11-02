import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.holding_cash import reconcile_holding_cash
from miniuw_foundation.holding_returns import HoldingReturnBinding,HoldingEventSlot,assemble_holding_returns,binding_from_record
from miniuw_foundation.operating_returns import OperatingReturnBinding,assemble_operating_returns
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from holding_test_support import load_case,build,raw,sha

def f(q):return F(int(q['numerator']),int(q['denominator']))


class HoldingReturnsTests(unittest.TestCase):
    def setUp(self):self.nois,self.specs,self.manifest,self.investor=load_case()
    def case(self):
        periods,m=build(self.nois,self.specs,self.manifest);h=reconcile_holding_cash(periods,m);i=raw(self.investor)
        slots=tuple(HoldingEventSlot(period_ref=p['period_ref'],distribution_event_id=eid,contribution_event_id=None)for p,eid in zip(json.loads(m)['periods'],['op1','op-zero','op3']))
        b=HoldingReturnBinding(profile_id='SYNTHETIC-HOLDING-EMPTY-EQUITY-SLOTS-v1',manifest_source_sha256=sha(m),holding_run_sha256=h.sha256,investor_source_sha256=sha(i),slots=slots)
        return periods,m,h,i,b
    def run_case(self):return assemble_holding_returns(*self.case())
    def test_complete_operating_chain_compiles_into_dated_ten_dollar_return(self):
        before=raw(self.investor);r=self.run_case();p=r.investor_run.payload
        self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(raw(self.investor),before)
        self.assertEqual([f(e['amount'])for e in p['events']if e['category']=='operating_distribution'],[100,0,200])
        self.assertEqual(f(p['gross_distributions']),1700);self.assertEqual(f(p['net_cash_profit']),700);self.assertEqual(f(p['equity_multiple']),F(17,10))
        self.assertEqual(f(p['normalized_story']['total_distributions']),17);self.assertEqual(f(p['normalized_story']['net_cash_profit']),7)
    def test_zero_year_remains_in_cash_vector_and_annual_distributions(self):
        p=self.run_case().investor_run.payload;self.assertEqual([f(e['net'])for e in p['dated_net_flows']],[-1000,600,0,1100])
        annual=p['annual_cash_receipts'];self.assertEqual([r['calendar_cash_receipt_year']for r in annual],[2026,2027,2028,2029])
        self.assertEqual([f(r['operating_distributions_only'])for r in annual],[0,100,0,200]);self.assertEqual(len(p['annual_irr_roots']),1)
        root=p['annual_irr_roots'][0]['annual_rate_interval'];lo,hi=f(root['lower']),f(root['upper'])
        poly=lambda r:-1000*(1+r)**3+600*(1+r)**2+1100
        self.assertGreaterEqual(poly(lo),0);self.assertLessEqual(poly(hi),0)
    def test_every_event_retains_its_exact_period_cash_hash_and_output_pointer(self):
        periods,m,h,i,b=self.case();r=assemble_holding_returns(periods,m,h,i,b);changes=r.payload['changes']
        self.assertEqual(len(changes),3)
        for change,e in zip(changes,periods):
            self.assertEqual(change['cash_run_sha256'],e.cash_run.sha256);self.assertIsNone(change['before']['amount'])
            self.assertEqual(change['after']['source_ref'],'miniuw:operating-cash:'+e.cash_run.sha256+'#/exportable_operating_distribution')
        self.assertEqual(r.payload['compiled_investor_source_sha256'],sha(r.compiled_raw));self.assertEqual(r.investor_run,produce_investor_returns(r.compiled_raw))
    def test_preserves_unbound_refinance_sale_capital_stocks_and_criteria(self):
        r=self.run_case();p=json.loads(r.compiled_raw);base=copy.deepcopy(self.investor)
        for e in p['events']:
            original=next(x for x in base['events']if x['event_id']==e['event_id'])
            if e['category']=='operating_distribution':e.update(original)
        self.assertEqual(p,base);self.assertEqual(set(r.payload['events_outside_this_operating_binding']),{'initial','refi','sale'})
        self.assertFalse(r.payload['whole_project_cash_reconciled'])
    def test_one_bad_target_prevents_entire_compilation_without_partial_changes(self):
        self.investor['events'][-1]['amount']=q(F(200));r=self.run_case()
        self.assertIsNone(r.compiled_raw);self.assertIsNone(r.investor_run);self.assertEqual(r.payload['changes'],[])
        self.assertTrue(any('target_amount_not_empty'in b for b in r.payload['blockers']));self.assertIsNone(self.investor['events'][2]['amount'])
    def test_missing_zero_distribution_slot_is_not_silently_dropped(self):
        self.investor['events']=[e for e in self.investor['events']if e['event_id']!='op-zero'];r=self.run_case()
        self.assertIn('op-zero:target_event_missing',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
    def test_unbound_operating_or_additional_event_in_horizon_blocks(self):
        for kind,category in [('distribution','operating_distribution'),('contribution','additional_capital')]:
            self.investor=load_case()[3];self.investor['events'].append(dict(event_id='unbound',date='2028-12-31',kind=kind,category=category,amount=q(F(1)),currency='USD',source_ref='SYNTHETIC-extra-claim'))
            r=self.run_case();self.assertIn('unbound:unbound_operating_or_additional_equity_event_in_horizon',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
    def test_every_calendar_period_requires_a_unique_event_binding(self):
        periods,m,h,i,b=self.case();r=assemble_holding_returns(periods,m,h,i,replace(b,slots=b.slots[:2]));self.assertIsNone(r.compiled_raw)
        with self.assertRaises(ValidationError):replace(b,slots=(b.slots[0],b.slots[0]))
        with self.assertRaises(ValidationError):replace(b,slots=(b.slots[0],replace(b.slots[1],distribution_event_id='op1')))
        with self.assertRaises(ValidationError):replace(b,slots=(replace(b.slots[0],contribution_event_id='op1'),))
    def test_missing_cash_or_discontinuous_stock_blocks_all_return_exports(self):
        for mutate in [lambda:self.specs[1]['amounts']['debt_fee_payment'].update(value=None),lambda:self.specs[1]['amounts']['opening_free_cash'].update(value=q(F(0)))]:
            self.nois,self.specs,self.manifest,self.investor=load_case();mutate();r=self.run_case()
            self.assertIsNone(r.compiled_raw);self.assertIn('holding_chain_blocked',r.payload['blockers']);self.assertTrue(r.payload['holding_blockers'])
    def test_hash_context_currency_target_date_and_grid_guards(self):
        periods,m,h,i,b=self.case()
        for field in ['manifest_source_sha256','holding_run_sha256','investor_source_sha256']:
            r=assemble_holding_returns(periods,m,h,i,replace(b,**{field:'0'*64}));self.assertIn(field+'_mismatch',r.payload['blockers']);self.assertIsNone(r.compiled_raw)
        for field,value in [('category','net_sale_distribution'),('date','2028-12-31'),('currency','EUR')]:
            self.investor=load_case()[3];self.investor['events'][2][field]=value;self.assertIsNone(self.run_case().compiled_raw)
        self.investor=load_case()[3];self.investor['context']['run_id']='SYNTHETIC-another';self.assertIsNone(self.run_case().compiled_raw)
        self.investor=load_case()[3];self.specs[1]['cash_date']='2028-12-30';r=self.run_case();self.assertTrue(any('not_bound_to_investor_grid'in b for b in r.payload['blockers']))
    def test_positive_gross_additional_capital_cannot_be_netted_out(self):
        self.specs[1]['amounts']['equity_contribution']['value']=q(F(100));self.specs[1]['amounts']['closing_free_cash_claim']['value']=q(F(510))
        self.specs[2]['amounts']['opening_free_cash']['value']=q(F(510));self.specs[2]['amounts']['closing_free_cash_claim']['value']=q(F(1095))
        self.assertIsNone(self.run_case().compiled_raw)
        self.investor['events'].append(dict(event_id='additional',date='2028-12-31',kind='contribution',category='additional_capital',amount=None,currency='USD',source_ref=None))
        periods,m,h,i,b=self.case();b=replace(b,slots=(b.slots[0],replace(b.slots[1],contribution_event_id='additional'),b.slots[2]))
        r=assemble_holding_returns(periods,m,h,i,b);p=r.investor_run.payload
        self.assertEqual(f(p['gross_contributions']),1100);self.assertEqual(f(p['gross_distributions']),1700);self.assertEqual(f(p['equity_multiple']),F(17,11))
        self.assertEqual([f(e['net'])for e in p['dated_net_flows']],[-1000,600,-100,1100]);self.assertEqual(f(p['normalized_story']['total_contributions']),11)
    def test_other_missing_investor_data_remains_pending_after_operating_compilation(self):
        self.investor['events'][3]['amount']=None;r=self.run_case()
        self.assertEqual(r.payload['state'],'compiled_synthetic');self.assertEqual(r.investor_run.payload['cash_metrics_state'],'blocked');self.assertEqual(r.investor_run.payload['decision'],'PENDING')
    def test_rehashed_forged_chain_is_rejected_before_consumption(self):
        periods,m,h,i,b=self.case();p=h.payload;p['exportable_equity_movements'][0]['distribution']=q(F(9999));enc=canonical(p);fake=replace(h,payload_json=enc,sha256=digest(enc))
        with self.assertRaises(ValidationError):assemble_holding_returns(periods,m,fake,i,replace(b,holding_run_sha256=fake.sha256))
    def test_single_period_compilation_matches_existing_T26_semantics(self):
        periods,m,h,i,b=self.case();plan=json.loads(m);plan['periods']=plan['periods'][:1];plan['end_date']=plan['periods'][0]['end_date'];m=raw(plan);periods=periods[:1];h=reconcile_holding_cash(periods,m)
        b=replace(b,manifest_source_sha256=sha(m),holding_run_sha256=h.sha256,slots=b.slots[:1]);new=assemble_holding_returns(periods,m,h,i,b)
        e=periods[0];old_binding=OperatingReturnBinding(profile_id='SYNTHETIC-EMPTY-OPERATING-EQUITY-SLOTS-v1',investor_source_sha256=sha(i),cash_spec_sha256=sha(e.spec_raw),cash_run_sha256=e.cash_run.sha256,distribution_event_id='op1',contribution_event_id=None)
        old=assemble_operating_returns(e.noi_raw,e.noi_run,e.spec_raw,e.cash_run,i,old_binding)
        self.assertEqual(new.compiled_raw,old.compiled_raw);self.assertEqual(new.investor_run,old.investor_run)
    def test_payload_is_immutable_and_binding_roundtrips(self):
        periods,m,h,i,b=self.case();r=assemble_holding_returns(periods,m,h,i,b);p=r.payload;p['changes'].clear()
        self.assertEqual(len(r.payload['changes']),3);self.assertEqual(binding_from_record(r.payload['binding']),b);self.assertEqual(r.sha256,digest(r.payload_json))
    def test_reopened_bundle_replays_all_periods_and_final_return(self):
        periods,m,h,i,b=self.case();r=assemble_holding_returns(periods,m,h,i,b)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'returns.sqlite3'
            with EvidenceArchive(path)as a:
                first=a.save_holding_cash(periods,m,h);second=a.save_holding_returns(periods,m,h,i,b,r);self.assertEqual(second,a.save_holding_returns(periods,m,h,i,b,r))
            with EvidenceArchive(path)as a:
                recovered=a.load_holding_returns(second);self.assertEqual(recovered.run,r);self.assertEqual(recovered.run.investor_run,r.investor_run)
                self.assertEqual(a.get_investor_returns_source(recovered.payload['investor_source_sha256']),i);self.assertEqual(a.get_investor_returns_source(recovered.payload['compiled_source_sha256']),r.compiled_raw)
                self.assertEqual(a.load_holding_cash(first).run.sha256,recovered.payload['holding_run']['sha256'])
    def test_archive_rollback_forgery_version_and_missing_middle_period(self):
        periods,m,h,i,b=self.case();r=assemble_holding_returns(periods,m,h,i,b);p=r.payload;p['changes']=[];enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_holding_returns(periods,m,h,i,b,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_holding_returns(periods,m,h,i,b,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_holding_returns(periods,m,h,i,b,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_holding_returns(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_holding_returns(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(periods[1].spec_raw)))
            with self.assertRaises(MissingEvidence):a.load_holding_returns(key)
    def test_blocked_chain_replays_without_compiled_output_and_no_authority(self):
        self.specs[1]['amounts']['debt_fee_payment']['value']=None;periods,m,h,i,b=self.case();r=assemble_holding_returns(periods,m,h,i,b)
        with EvidenceArchive(':memory:')as a:
            key=a.save_holding_returns(periods,m,h,i,b,r);self.assertEqual(a.load_holding_returns(key).run,r);self.assertIsNone(a.load_holding_returns(key).run.compiled_raw)
        self.assertEqual(r.payload['decision'],'PENDING')
        for key in ['original_source_overwritten','whole_project_cash_reconciled','whole_investor_story_complete','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(r.payload[key])
