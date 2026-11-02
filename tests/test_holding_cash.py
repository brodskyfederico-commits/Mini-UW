import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.operating_cash import WORKING,STOCKS
from miniuw_foundation.holding_cash import reconcile_holding_cash,parse_holding_cash,OperatingPeriodEvidence
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from holding_test_support import load_case,build,raw,sha,R

def f(q):return F(int(q['numerator']),int(q['denominator']))


class HoldingCashTests(unittest.TestCase):
    def setUp(self):self.nois,self.specs,self.manifest,self.investor=load_case()
    def case(self):return build(self.nois,self.specs,self.manifest)
    def run_case(self):return reconcile_holding_cash(*self.case())
    def test_three_period_conservation_matches_independent_sources_and_uses(self):
        p=self.run_case().payload;t=p['totals'];self.assertEqual(p['state'],'reconciled_synthetic_operating_chain')
        self.assertEqual(f(t['operating_receipts']),1390+0+1700);self.assertEqual(f(t['operating_payments']),435+0+420)
        self.assertEqual(f(t['net_operating_cash']),2235);self.assertEqual(f(t['planned_operating_distribution']),300)
        self.assertEqual(f(t['closing_free_cash_claim']),995);self.assertEqual(f(t['closing_restricted_cash_claim']),360)
        self.assertEqual(50+100+3090,855+400+200+10+100+20+300+995+360);self.assertEqual(f(p['cash_conservation_residual']),0)
    def test_all_six_balance_families_checked_at_every_boundary(self):
        checks=self.run_case().payload['continuity_checks'];self.assertEqual(len(checks),12)
        self.assertEqual({c['balance']for c in checks},set(WORKING)|{'free_cash','restricted_cash'});self.assertTrue(all(c['equal_exact_value']for c in checks))
    def test_zero_cash_period_and_zero_distribution_remain_in_calendar(self):
        p=self.run_case().payload;self.assertEqual(len(p['periods']),3);self.assertEqual(f(p['periods'][1]['net_operating_cash']),0)
        self.assertEqual([f(r['distribution'])for r in p['exportable_equity_movements']],[100,0,200]);self.assertEqual(p['exportable_equity_movements'][1]['cash_date'],'2028-12-31')
    def test_each_working_balance_reset_blocks_even_individually_valid_periods(self):
        for family in WORKING:
            specs=copy.deepcopy(self.specs)
            for cutoff in ['opening','closing']:specs[1]['working_balances'][family][cutoff]['value']=q(F(0))
            periods,m=build(self.nois,specs,self.manifest);self.assertTrue(all(e.cash_run.payload['state']=='reconciled_synthetic_plan'for e in periods))
            p=reconcile_holding_cash(periods,m).payload;self.assertEqual(p['state'],'blocked');self.assertIsNone(p['exportable_equity_movements'])
            self.assertTrue(any(family+':opening_does_not_equal_previous_close'in b for b in p['blockers']))
    def test_free_and_restricted_cash_cannot_restart_from_zero(self):
        for family in ['free','restricted']:
            specs=copy.deepcopy(self.specs)
            for field in ['opening_'+family+'_cash','closing_'+family+'_cash_claim']:specs[1]['amounts'][field]['value']=q(F(0))
            periods,m=build(self.nois,specs,self.manifest);self.assertTrue(all(e.cash_run.payload['state']=='reconciled_synthetic_plan'for e in periods))
            p=reconcile_holding_cash(periods,m).payload;self.assertTrue(any(family+'_cash:opening_does_not_equal_previous_close'in b for b in p['blockers']));self.assertIsNone(p['totals'])
    def test_equal_rational_values_with_different_literals_are_continuous(self):
        self.specs[1]['amounts']['opening_free_cash']['value']={'numerator':'820','denominator':'2'}
        p=self.run_case().payload;self.assertEqual(p['state'],'reconciled_synthetic_operating_chain')
        check=next(c for c in p['continuity_checks']if c['balance']=='free_cash');self.assertNotEqual(check['previous_closing_claim']['value'],check['next_opening_claim']['value'])
    def test_calendar_gap_overlap_and_wrong_order_are_not_repaired(self):
        for date in ['2028-01-02','2027-12-31']:
            specs=copy.deepcopy(self.specs);specs[1]['start_date']=date;p=reconcile_holding_cash(*build(self.nois,specs,self.manifest)).payload
            self.assertTrue(any('calendar_gap_overlap_or_wrong_order'in b for b in p['blockers']));self.assertIsNone(p['exportable_equity_movements'])
        self.manifest['periods'].reverse();self.assertEqual(self.run_case().payload['state'],'blocked')
    def test_omitted_zero_period_is_detected_by_calendar_gap(self):
        del self.nois[1];del self.specs[1];del self.manifest['periods'][1]
        p=self.run_case().payload;self.assertEqual(p['state'],'blocked');self.assertTrue(any('calendar_gap'in b for b in p['blockers']))
    def test_missing_extra_and_entirely_absent_evidence_stay_blocked(self):
        periods,m=self.case()
        for supplied in [periods[:1],()]:
            p=reconcile_holding_cash(supplied,m).payload;self.assertIsNone(p['exportable_equity_movements']);self.assertTrue(any('period_evidence_missing'in b for b in p['blockers']))
        plan=json.loads(m);del plan['periods'][1];p=reconcile_holding_cash(periods,raw(plan)).payload
        self.assertTrue(any('extra_period_evidence_not_in_calendar'in b for b in p['blockers']))
    def test_any_blocked_period_prevents_all_exports_and_retains_causes(self):
        self.nois[1]['tax_coefficient']['value']=None;p=self.run_case().payload
        self.assertEqual(p['state'],'blocked');self.assertTrue(p['periods'][1]['cash_blockers']);self.assertIsNone(p['exportable_equity_movements']);self.assertIsNotNone(p['periods'][0]['proposed_distribution'])
    def test_stale_manifest_source_run_and_dates_block(self):
        periods,m=self.case()
        for key,value in [('noi_source_sha256','0'*64),('noi_run_sha256','0'*64),('spec_source_sha256','0'*64),('cash_run_sha256','0'*64),('cash_date','2027-12-30')]:
            plan=json.loads(m);plan['periods'][0][key]=value;p=reconcile_holding_cash(periods,raw(plan)).payload
            self.assertIn(key+'_mismatch',p['periods'][0]['binding_blockers']);self.assertIsNone(p['exportable_equity_movements'])
    def test_horizon_basis_inventory_context_currency_guards(self):
        periods,m=self.case()
        for key,value in [('start_date','2026-01-01'),('end_date','2031-01-01'),('calendar_basis_ref',None),('scope_inventory_declared_complete',False),('scope_inventory_declared_complete',None),('currency','EUR')]:
            plan=json.loads(m);plan[key]=value;self.assertEqual(reconcile_holding_cash(periods,raw(plan)).payload['state'],'blocked')
        plan=json.loads(m);plan['context']['run_id']='SYNTHETIC-other';self.assertEqual(reconcile_holding_cash(periods,raw(plan)).payload['state'],'blocked')
    def test_duplicate_periods_evidence_and_live_context_rejected(self):
        periods,m=self.case();plan=json.loads(m);plan['periods'].append(plan['periods'][0])
        with self.assertRaises(ValidationError):parse_holding_cash(raw(plan))
        with self.assertRaises(ValidationError):reconcile_holding_cash(periods+(periods[0],),m)
        plan=json.loads(m);plan['context']['deal_id']='real-deal'
        with self.assertRaises(ValidationError):parse_holding_cash(raw(plan))
    def test_every_extra_period_must_replay_before_it_can_be_ignored(self):
        periods,m=self.case();p=periods[1].cash_run.payload;p['exportable_operating_distribution']=q(F(999));enc=canonical(p)
        fake=replace(periods[1],cash_run=replace(periods[1].cash_run,payload_json=enc,sha256=digest(enc)))
        plan=json.loads(m);del plan['periods'][1]
        with self.assertRaises(ValidationError):reconcile_holding_cash((periods[0],fake,periods[2]),raw(plan))
    def test_strict_immutable_inputs_transport_limits_and_schema(self):
        periods,m=self.case()
        with self.assertRaises(ValidationError):reconcile_holding_cash(list(periods),m)
        with self.assertRaises(ValidationError):reconcile_holding_cash((periods[0],)*66,m)
        huge=replace(periods[0],noi_raw=b'x'*8_388_609)
        with self.assertRaises(ValidationError):reconcile_holding_cash((huge,),m)
        plan=json.loads(m);plan['profile']='automatically_fill_gaps'
        with self.assertRaises(ValidationError):parse_holding_cash(raw(plan))
    def test_single_period_is_supported_without_fabricated_continuity_checks(self):
        periods,m=self.case();plan=json.loads(m);plan['periods']=plan['periods'][:1];plan['end_date']=plan['periods'][0]['end_date']
        p=reconcile_holding_cash(periods[:1],raw(plan)).payload;self.assertEqual(p['state'],'reconciled_synthetic_operating_chain');self.assertEqual(p['continuity_checks'],[])
    def test_holding_arithmetic_budget_can_block_valid_individual_periods(self):
        nois=[];specs=[];plan=copy.deepcopy(self.manifest);plan['periods']=[];plan['end_date']='2033-01-01'
        denominators=[2**845,3**535,5**365,7**301,11**244,13**229]
        for index,d in enumerate(denominators):
            n=copy.deepcopy(self.nois[1]);s=copy.deepcopy(self.specs[1]);pid='SYNTHETIC-budget-'+str(index);n['period_ref']=pid
            for row in n['income_rows']+n['expense_rows']+[n['tax_floor']]:row['period_ref']=pid
            s.update(period_ref=pid,start_date=str(2027+index)+'-01-01',end_date=str(2028+index)+'-01-01',cash_date=str(2027+index)+'-12-31')
            for pair in s['working_balances'].values():
                for cutoff,prefix in [('opening','OPENING:'),('closing','CLOSING:')]:pair[cutoff]['period_ref']=prefix+pid
            for key,row in s['amounts'].items():row['period_ref']=STOCKS.get(key,'')+pid
            s['amounts']['nonfinancing_other_cash_receipt']['value']=q(F(1,d));s['amounts']['other_cash_payment']['value']=q(F(1,d))
            nois.append(n);specs.append(s);plan['periods'].append(dict(self.manifest['periods'][0],period_ref=pid))
        periods,m=build(nois,specs,plan);self.assertTrue(all(e.cash_run.payload['state']=='reconciled_synthetic_plan'for e in periods))
        p=reconcile_holding_cash(periods,m).payload;self.assertIn('holding_exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['exportable_equity_movements'])
    def test_immutable_payload_and_source_hashes(self):
        periods,m=self.case();r=reconcile_holding_cash(periods,m);p=r.payload;p['periods'].clear()
        self.assertEqual(len(r.payload['periods']),3);self.assertEqual(r.payload['manifest_source_sha256'],sha(m));self.assertEqual(r.sha256,digest(r.payload_json))
    def test_reopened_archive_replays_every_source_period_and_manifest(self):
        periods,m=self.case();r=reconcile_holding_cash(periods,m)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'holding.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_holding_cash(periods,m,r);self.assertEqual(key,a.save_holding_cash(periods,m,r))
            with EvidenceArchive(path)as a:
                b=a.load_holding_cash(key);self.assertEqual(b.run,r);self.assertEqual(a.get_holding_cash_manifest(b.payload['manifest_source_sha256']),m)
                self.assertEqual(a.get_holding_periods(key),periods);self.assertEqual(reconcile_holding_cash(a.get_holding_periods(key),m),r)
    def test_archive_fault_forgery_version_missing_and_blocked_recovery(self):
        periods,m=self.case();r=reconcile_holding_cash(periods,m);p=r.payload;p['blockers']=['invented'];enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_holding_cash(periods,m,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_holding_cash(periods,m,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_holding_cash(periods,m,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_holding_cash(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_holding_cash(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(periods[1].spec_raw)))
            with self.assertRaises(MissingEvidence):a.load_holding_cash(key)
        blocked=reconcile_holding_cash((),m)
        with EvidenceArchive(':memory:')as a:
            key=a.save_holding_cash((),m,blocked);self.assertEqual(a.load_holding_cash(key).run,blocked)
    def test_declared_continuity_does_not_certify_project_or_distribution(self):
        p=self.run_case().payload;self.assertTrue(p['declared_plan_continuity_reconciled']);self.assertEqual(p['decision'],'PENDING')
        for key in ['opening_balance_sources_financially_verified','actual_period_inventory_verified','whole_project_cash_reconciled','intraperiod_liquidity_verified','debt_cash_schedule_verified','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])
