import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.project_cash import reconcile_project_cash,parse_project_cash
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
from project_test_support import load_case,build,raw,sha

def f(q):return F(int(q['numerator']),int(q['denominator']))
def num(n):return q(F(n))


class ProjectCashTests(unittest.TestCase):
    def setUp(self):self.data=load_case()
    def run_case(self):return reconcile_project_cash(*build(self.data))
    def test_full_declared_window_conserves_external_cash_without_reserve_double_count(self):
        p=self.run_case().payload;t=p['totals'];self.assertEqual(p['state'],'reconciled_synthetic_cash_window');self.assertEqual(f(p['cash_conservation_residual']),0)
        self.assertEqual(f(t['equity_distributions']),F('1298.9197'));self.assertEqual(f(t['reserve_deposits']),300);self.assertEqual(f(t['reserve_releases']),300)
        self.assertEqual(F(1000)+150+F('303.01')+400,30+F('423.01')+F('6.0803')+15+40+40+F('1298.9197'))
        self.assertEqual(f(t['terminal_free_cash']),0);self.assertEqual(f(t['terminal_restricted_cash']),0)
    def test_all_six_cash_boundaries_and_working_balances_match(self):
        p=self.run_case().payload;self.assertEqual(len(p['cash_boundary_checks']),6);self.assertTrue(all(c['equal_exact_value']for c in p['cash_boundary_checks']))
        self.assertEqual(len(p['working_balance_checks']),4);self.assertTrue(all(c['equal_exact_value']for c in p['working_balance_checks']))
        self.assertTrue(p['refinance_to_sale_loan_links'][0]['sale_loan_inventory_matches_refinance_origin_principal'])
    def test_operating_debt_cash_matches_regular_rows_before_closing_cutoff(self):
        checks=self.run_case().payload['operating_debt_checks'];self.assertEqual(len(checks),2)
        self.assertEqual([f(c['computed_principal'])for c in checks],[30,201]);self.assertEqual([f(c['computed_interest'])for c in checks],[0,F('5.0602')])
        self.assertEqual([[r['payment_index']for r in c['selected_regular_payments']]for c in checks],[[1,2,3],[1,2]])
        self.assertTrue(all(c['equal_with_zero_unmodeled_fee']for c in checks))
    def test_each_cash_boundary_rejects_individually_balanced_reset(self):
        for which in ['refinance-opening','post-operation-opening','sale-opening']:
            d=load_case()
            if which=='refinance-opening':d['closings'][0]['amounts']['opening_free_cash']['value']=num(821)
            elif which=='sale-opening':d['closings'][1]['amounts']['opening_free_cash']['value']=num(F('274.9398'))
            else:
                d['ops'][1]['amounts']['opening_free_cash']['value']=num(601);d['ops'][1]['amounts']['closing_free_cash_claim']['value']=num(F('274.9398'))
            ops,closings,m=build(d);self.assertTrue(all(e.cash_run.payload['state']=='reconciled_synthetic_plan'for e in ops));self.assertTrue(all(e.debt_run.payload['state']=='matched_synthetic_debt_assumptions'for e in closings))
            p=reconcile_project_cash(ops,closings,m).payload;self.assertEqual(p['state'],'blocked');self.assertTrue(any('opening_cash_does_not_equal_previous_close'in b for b in p['blockers']));self.assertIsNone(p['exportable_equity_movements'])
    def test_restricted_cash_cannot_restart_or_be_released_twice(self):
        self.data['closings'][0]['amounts']['opening_restricted_cash']['value']=num(101);self.data['closings'][0]['amounts']['closing_restricted_cash_claim']['value']=num(151)
        p=self.run_case().payload;self.assertTrue(any(':restricted:opening_cash_does_not_equal_previous_close'in b for b in p['blockers']));self.assertIsNone(p['totals'])
    def test_gap_overlap_and_wrong_order_never_repaired(self):
        self.data['ops'][1]['start_date']='2027-04-02';p=self.run_case().payload;self.assertTrue(any('cash_date_gap_overlap'in b for b in p['blockers']))
        self.data=load_case();self.data['manifest']['nodes'][0],self.data['manifest']['nodes'][1]=self.data['manifest']['nodes'][1],self.data['manifest']['nodes'][0]
        self.assertEqual(self.run_case().payload['state'],'blocked')
    def test_terminal_working_balances_need_explicit_settlement_not_silent_zero(self):
        for family in ['receivables','advance_income','payables','prepaid_expenses']:
            self.data=load_case()
            for op in self.data['ops']:
                for cutoff in ['opening','closing']:op['working_balances'][family][cutoff]['value']=num(1)
            p=self.run_case().payload;self.assertTrue(any(family+':terminal_working_balance_requires_explicit_settlement_profile'in b for b in p['blockers']));self.assertIsNone(p['exportable_equity_movements'])
    def test_working_balances_must_carry_across_refinance(self):
        for cutoff in ['opening','closing']:self.data['ops'][1]['working_balances']['receivables'][cutoff]['value']=num(1)
        p=self.run_case().payload;self.assertTrue(any('receivables:working_balance_discontinuity_across_boundary'in b for b in p['blockers']))
    def test_nonzero_receivable_can_carry_then_be_collected_before_sale(self):
        for cutoff in ['opening','closing']:self.data['ops'][0]['working_balances']['receivables'][cutoff]['value']=num(1)
        self.data['ops'][1]['working_balances']['receivables']['opening']['value']=num(1)
        self.data['ops'][1]['amounts']['operating_receipts_claim']['value']=num(91);self.data['ops'][1]['amounts']['closing_free_cash_claim']['value']=num(F('274.9398'))
        self.data['closings'][1]['amounts']['opening_free_cash']['value']=num(F('274.9398'))
        p=self.run_case().payload;self.assertEqual(p['state'],'reconciled_synthetic_cash_window');self.assertEqual(f(p['totals']['equity_distributions']),F('1299.9197'))
    def test_double_charged_or_unmodeled_operating_debt_blocks_even_balanced_cash(self):
        for key in ['debt_principal_payment','debt_interest_payment','debt_fee_payment']:
            self.data=load_case();row=self.data['ops'][1]['amounts'][key];row['value']=num(f(row['value'])+1)
            self.data['ops'][1]['amounts']['closing_free_cash_claim']['value']=num(F('272.9398'));self.data['closings'][1]['amounts']['opening_free_cash']['value']=num(F('272.9398'))
            p=self.run_case().payload;self.assertTrue(all(c['equal_exact_value']for c in p['cash_boundary_checks']))
            self.assertTrue(any('operating_debt_cash_differs'in b for b in p['blockers']));self.assertIsNone(p['exportable_equity_movements'])
    def test_after_regular_payment_closing_is_not_allowed_to_hide_unbooked_cash(self):
        self.data['debt_specs'][0]['loans'][0]['payment_cutoff']='after_regular_payment_before_balloon'
        for suffix in ['due','paid']:self.data['closings'][0]['old_debts'][0]['principal_'+suffix]['value']=num(80)
        ops,closes,m=build(self.data);self.assertEqual(closes[0].debt_run.payload['state'],'matched_synthetic_debt_assumptions')
        p=reconcile_project_cash(ops,closes,m).payload;self.assertTrue(any('integrated_profile_requires_before_regular_payment_cutoff'in b for b in p['blockers']))
    def test_refinance_draw_and_sale_loan_must_match_principal_and_origin(self):
        self.data['closings'][0]['amounts']['gross_proceeds']['value']=num(F('304.01'));self.data['closings'][0]['new_loan']['principal_after_closing']['value']=num(F('304.01'))
        p=self.run_case().payload;self.assertIn('sale_debt_does_not_match_refinance_new_loan_origin_and_principal',p['blockers'])
        self.data=load_case();self.data['loans'][1][0]['origination_date']='2027-03-01';self.assertIn('sale_debt_does_not_match_refinance_new_loan_origin_and_principal',self.run_case().payload['blockers'])
    def test_missing_upstream_data_debt_evidence_and_extra_nodes_do_not_export(self):
        self.data['ops'][0]['amounts']['noncash_expense']['value']=None;p=self.run_case().payload;self.assertTrue(p['nodes'][0]['producer_blockers']);self.assertIsNone(p['exportable_equity_movements'])
        self.data=load_case();ops,closes,m=build(self.data)
        for o,c in [(ops[:1],closes),(ops,closes[:1])]:self.assertEqual(reconcile_project_cash(o,c,m).payload['state'],'blocked')
        extra=replace(closes[0],closing_id='SYNTHETIC-extra');p=reconcile_project_cash(ops,closes+(extra,),m).payload;self.assertTrue(any('extra_node_evidence'in b for b in p['blockers']))
    def test_manifest_hash_kind_context_currency_horizon_and_basis_guards(self):
        ops,closes,m=build(self.data)
        for key in ['source_sha256','run_sha256','upstream_source_sha256','upstream_run_sha256']:
            manifest=json.loads(m);manifest['nodes'][0][key]='0'*64;self.assertEqual(reconcile_project_cash(ops,closes,raw(manifest)).payload['state'],'blocked')
        for key,value in [('currency','EUR'),('opening_date','2026-12-01'),('terminal_date','2027-08-01'),('timeline_basis_ref',None),('opening_state_basis_ref',None),('refinance_working_balance_carry_basis_ref',None),('scope_inventory_declared_complete',False)]:
            manifest=json.loads(m);manifest[key]=value;self.assertEqual(reconcile_project_cash(ops,closes,raw(manifest)).payload['state'],'blocked')
        manifest=json.loads(m);manifest['context']['run_id']='SYNTHETIC-other';self.assertEqual(reconcile_project_cash(ops,closes,raw(manifest)).payload['state'],'blocked')
    def test_each_extra_source_must_replay_even_if_not_in_manifest(self):
        ops,closes,m=build(self.data);p=closes[0].debt_run.payload;p['state']='wrong';enc=canonical(p)
        fake=replace(closes[0],closing_id='SYNTHETIC-extra',debt_run=replace(closes[0].debt_run,payload_json=enc,sha256=digest(enc)))
        with self.assertRaises(ValidationError):reconcile_project_cash(ops,closes+(fake,),m)
    def test_strict_schema_duplicate_inventory_and_transport_guards(self):
        ops,closes,m=build(self.data)
        for a,b in [(list(ops),closes),(ops,list(closes)),(ops+ops,closes),(ops,closes+closes)]:
            with self.assertRaises(ValidationError):reconcile_project_cash(a,b,m)
        huge=replace(ops[0],noi_raw=b'x'*8_388_609)
        with self.assertRaises(ValidationError):reconcile_project_cash((huge,),closes,m)
        manifest=json.loads(m);manifest['nodes'][1]['node_id']=manifest['nodes'][0]['node_id']
        with self.assertRaises(ValidationError):parse_project_cash(raw(manifest))
        manifest=json.loads(m);manifest['context']['deal_id']='real'
        with self.assertRaises(ValidationError):parse_project_cash(raw(manifest))
    def test_payload_source_claims_and_run_hash_immutable(self):
        ops,closes,m=build(self.data);r=reconcile_project_cash(ops,closes,m);p=r.payload;p['nodes'].clear()
        self.assertEqual(len(r.payload['nodes']),4);self.assertEqual(r.payload['manifest_source_sha256'],sha(m));self.assertEqual(r.sha256,digest(r.payload_json))
    def test_reopened_archive_replays_all_operating_closing_and_debt_inputs(self):
        ops,closes,m=build(self.data);r=reconcile_project_cash(ops,closes,m)
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'project.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_project_cash(ops,closes,m,r);self.assertEqual(key,a.save_project_cash(ops,closes,m,r))
            with EvidenceArchive(path)as a:
                b=a.load_project_cash(key);self.assertEqual(b.run,r);self.assertEqual(a.get_project_cash_manifest(b.payload['manifest_source_sha256']),m)
                self.assertEqual(len(b.payload['closings']),2);self.assertEqual(len(b.payload['periods']),2)
    def test_archive_fault_forgery_version_missing_and_blocked_recovery(self):
        ops,closes,m=build(self.data);r=reconcile_project_cash(ops,closes,m);p=r.payload;p['totals']['equity_distributions']=num(9999);enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_project_cash(ops,closes,m,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_project_cash(ops,closes,m,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_project_cash(ops,closes,m,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_project_cash(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_project_cash(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',sha(closes[1].loans[0].loan_raw)))
            with self.assertRaises(MissingEvidence):a.load_project_cash(key)
        blocked=reconcile_project_cash((),(),m)
        with EvidenceArchive(':memory:')as a:key=a.save_project_cash((),(),m,blocked);self.assertEqual(a.load_project_cash(key).run,blocked)
    def test_window_reconciliation_is_not_actual_bank_or_complete_project_approval(self):
        p=self.run_case().payload;self.assertTrue(p['declared_cash_window_reconciled']);self.assertEqual(p['decision'],'PENDING')
        for key in ['whole_project_cash_reconciled','historical_construction_and_asset_funding_verified','actual_cash_and_payment_history_verified','intraperiod_liquidity_verified','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])

    def test_global_arithmetic_budget_blocks_valid_individual_cash_nodes(self):
        original=load_case();nois=[];ops=[];rows=[];balance=F(1000)
        boundaries=['2027-01-01','2027-01-15','2027-02-01','2027-02-15','2027-03-01','2027-03-15','2027-04-01']
        denominators=[2**845,3**535,5**365,7**301,11**244,13**229]
        for index,denominator in enumerate(denominators):
            n=copy.deepcopy(original['nois'][0]);s=copy.deepcopy(original['ops'][0]);pid='SYNTHETIC-split-'+str(index);n['period_ref']=pid
            for row in n['income_rows']+n['expense_rows']+[n['tax_floor']]:row.update(value=num(0),period_ref=pid)
            s.update(period_ref=pid,start_date=boundaries[index],end_date=boundaries[index+1],cash_date=boundaries[index])
            for pair in s['working_balances'].values():
                for cutoff,prefix in [('opening','OPENING:'),('closing','CLOSING:')]:pair[cutoff].update(value=num(0),period_ref=prefix+pid)
            for key,row in s['amounts'].items():row.update(value=num(0),period_ref=('OPENING:'if key.startswith('opening_')else'CLOSING:'if key.startswith('closing_')else'')+pid)
            payment=10 if index in [0,2,4]else 0;s['amounts']['opening_free_cash']['value']=num(balance);balance-=payment
            s['amounts']['closing_free_cash_claim']['value']=num(balance);s['amounts']['debt_principal_payment']['value']=num(payment)
            s['amounts']['nonfinancing_other_cash_receipt']['value']=s['amounts']['other_cash_payment']['value']=q(F(1,denominator))
            nois.append(n);ops.append(s);rows.append(dict(original['manifest']['nodes'][0],node_id=pid))
        self.data['nois']=nois+[original['nois'][1]];self.data['ops']=ops+[original['ops'][1]]
        self.data['manifest']['nodes']=rows+original['manifest']['nodes'][1:]
        self.data['closings'][0]['amounts']['opening_free_cash']['value']=num(970);self.data['closings'][0]['amounts']['opening_restricted_cash']['value']=num(0);self.data['closings'][0]['amounts']['reserve_release']['value']=num(0)
        periods,closes,m=build(self.data);self.assertTrue(all(e.cash_run.payload['state']=='reconciled_synthetic_plan'for e in periods))
        p=reconcile_project_cash(periods,closes,m).payload;self.assertIn('project_cash_exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['exportable_equity_movements'])
