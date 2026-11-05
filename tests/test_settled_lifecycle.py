from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import copy,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.settled_case import assemble_settled_case,source_window,parse_settled_case
from miniuw_foundation.settled_hold_sale import reconcile_settled_hold_sale_cash
from miniuw_foundation.settled_operating_window import reconcile_settled_operating_window
from miniuw_foundation.hold_sale_cash import reconcile_hold_sale_cash
from miniuw_foundation.settled_case_artifacts import (build_settled_case_artifacts,read_settled_case_artifacts,write_settled_case_artifacts,
    recover_settled_case_directory,audit_settled_case_directory,versions)

ROOT=Path(__file__).resolve().parents[1];q=lambda v:rational(F(v));enc=lambda p:canonical(p).encode()
def source(label='retained'):return(ROOT/('templates/settled-lifecycle-'+label+'-T108.json')).read_bytes()
def refresh(p):
    # Refresh only linkage of an explicitly supplied candidate; never fill money, dates or balances.
    boundary=p['boundary_source_utf8'].encode();hs=json.loads(p['hold_sale_source_utf8']);hs['boundary_source_sha256']=sha(boundary);p['hold_sale_source_utf8']=canonical(hs)
    wa,_=source_window(p);ws=json.loads(p['window_source_utf8']);ws.update(hold_sale_spec_sha256=sha(wa[3][4]),hold_sale_run_sha256=wa[4].sha256);p['window_source_utf8']=canonical(ws)
    wa,w=source_window(p);b=json.loads(p['return_binding_source_utf8']);b.update(window_run_sha256=w.sha256,investor_source_sha256=sha(p['investor_source_utf8'].encode()));p['return_binding_source_utf8']=canonical(b)
    return p
def candidate(change,link=True):
    p=json.loads(source());change(p)
    if link:refresh(p)
    return enc(p)
def boundary_change(mutate):
    def change(p):
        b=json.loads(p['boundary_source_utf8']);mutate(b);p['boundary_source_utf8']=canonical(b)
    return change


class SettledLifecycleTests(unittest.TestCase):
    def blocked(self,raw):
        p=assemble_settled_case(raw).payload;self.assertEqual(p['state'],'PENDING')
        for key in('settlement_summary','operating_totals','holding_sale_totals','cash_conservation_residual','project_return_story','compiled_investor_json','irr_evidence','cash_risk_run'):self.assertIsNone(p[key],key)
        return p

    def test_retained_cash_settles_five_once_and_preserves_full_direct_control_return(self):
        p=assemble_settled_case(source()).payload;s=p['project_return_story'];self.assertEqual(s['gross_contributions'],q(1400));self.assertEqual(s['gross_distributions'],q(840));self.assertEqual(s['net_cash_profit'],q(-560));self.assertEqual(s['equity_multiple'],q(F(3,5)))
        self.assertEqual(p['settlement_summary']['settlement_cash'],q(5));self.assertEqual(p['operating_totals']['closing_free_cash_claim'],q(275))
        self.assertEqual(p['holding_sale_totals']['operating_payments'],q(25));self.assertEqual(p['holding_sale_totals']['closing_other_uses'],q(5));self.assertEqual(p['cash_conservation_residual'],q(0))
        self.assertEqual(s['cash_by_category']['net_sale_distribution'],q(640));self.assertEqual(s['cash_by_category']['operating_distribution'],q(200))

    def test_explicit_distribution_revision_changes_dates_but_not_total_receipts(self):
        a=assemble_settled_case(source()).payload;b=assemble_settled_case(source('distributed')).payload;x,y=a['project_return_story'],b['project_return_story']
        self.assertEqual(x['gross_distributions'],y['gross_distributions']);self.assertNotEqual(x['dated_net_flows'],y['dated_net_flows'])
        self.assertEqual(y['cash_by_category']['operating_distribution'],q(205));self.assertEqual(y['cash_by_category']['net_sale_distribution'],q(635));self.assertEqual(b['operating_totals']['closing_free_cash_claim'],q(270))
        self.assertNotEqual(x['periodic_irr']['roots'],y['periodic_irr']['roots']);self.assertEqual(a['source_run_hashes']['phase'],b['source_run_hashes']['phase'])

    def test_gross_zero_events_and_normalization_are_not_net_flow_or_funding_shortcuts(self):
        p=assemble_settled_case(source()).payload;s=p['project_return_story'];self.assertEqual(len(s['events']),8);self.assertEqual(sum(e['kind']=='contribution'for e in s['events']),5)
        self.assertEqual(sum(e['amount']==q(0)for e in s['events']),3);self.assertEqual(s['normalized_story']['total_contributions'],q(10));self.assertEqual(s['normalized_story']['total_distributions'],q(6))
        self.assertFalse(p['phase_principal_counted_as_new_equity']);self.assertEqual(s['cash_by_category']['refinance_cash_in'],q(0))

    def test_IRR_all_root_inventory_and_annualization_keep_same_source_budgets(self):
        p=assemble_settled_case(source()).payload;s=p['project_return_story'];proof=p['irr_evidence'];self.assertEqual(s['periodic_irr']['status'],'complete_synthetic');self.assertEqual(s['periodic_irr']['distinct_positive_discount_roots'],1)
        self.assertIsNone(s['selected_IRR']);self.assertFalse(proof['point_rate_selected']);self.assertEqual(s['periodic_irr'],proof['primitive_roots']);self.assertEqual(s['annual_irr_roots'],proof['annual_roots'])
        self.assertEqual(proof['parameters'],json.loads(json.loads(source())['investor_source_utf8'])['irr_parameters'])

    def test_missing_supplied_accounting_stock_never_becomes_nominal_tail_or_zero(self):
        for key in('before_payables','after_payables','before_prepaid','after_prepaid','basis_ref'):
            p=self.blocked(candidate(boundary_change(lambda b:b['accounting'].update({key:None}))));self.assertTrue(p['blockers']['boundary'])

    def test_wrong_before_after_accounting_balances_with_fresh_hashes_stay_pending(self):
        for key,value in(('before_payables',4),('after_payables',1),('before_prepaid',1),('after_prepaid',1)):
            p=self.blocked(candidate(boundary_change(lambda b:b['accounting'].update({key:q(value)}))));self.assertTrue(p['blockers']['boundary'])

    def test_pre_cut_payment_identity_date_and_complete_inventory_cannot_be_guessed(self):
        for mutate in(lambda b:b['payment_map'][0].update(detail_payment_id='SYNTHETIC-wrong'),lambda b:b['payment_map'][0].update(plan_payment_id='SYNTHETIC-wrong'),lambda b:b['payment_map'].pop(),lambda b:b.update(inventory_declared_complete=None)):
            self.blocked(candidate(boundary_change(mutate)))
        def change(b):
            d=json.loads(b['periods'][0]['detail_source_utf8']);d['items'][0]['payments'][0]['date']='2027-02-01';b['periods'][0]['detail_source_utf8']=canonical(d)
        p=self.blocked(candidate(boundary_change(change)));self.assertTrue(any('pre_cut_payment_date_or_amount_mismatch'in b for b in p['blockers']['boundary']))

    def test_complete_ordered_period_inventory_preserves_missing_and_zero_items(self):
        for mutate in(lambda b:b['periods'].pop(),lambda b:b['periods'].reverse()):self.blocked(candidate(boundary_change(mutate)))
        def omit(b):
            d=json.loads(b['periods'][0]['detail_source_utf8']);d['items'].pop();b['periods'][0]['detail_source_utf8']=canonical(d)
        self.blocked(candidate(boundary_change(omit)))

    def test_same_aggregate_stocks_and_payments_cannot_hide_per_item_discontinuity(self):
        def change(b):
            d=json.loads(b['periods'][1]['detail_source_utf8']);insurance,other=d['items'][:2]
            insurance.update(opening_payables=q(4));insurance['payments'][0]['amount']=q(9);other.update(opening_payables=q(1));other['payments'][0]['amount']=q(6)
            b['periods'][1]['detail_source_utf8']=canonical(d)
        p=self.blocked(candidate(boundary_change(change)));self.assertTrue(any('per_item_continuity_mismatch'in b for b in p['blockers']['boundary']))

    def test_incompatible_plan_allocation_or_future_payment_withdraws_full_return(self):
        def mutate(b,kind):
            plan=json.loads(b['plan_source_utf8'])
            if kind=='fraction':plan['allocations'][0]['fraction']=q(F(1,4));plan['allocations'][1]['fraction']=q(F(3,4))
            else:plan['planned_payments'][-1]['payment_date']='2027-08-01'
            b['plan_source_utf8']=canonical(plan);terminal=json.loads(b['terminal_binding_source_utf8']);terminal['plan_source_sha256']=sha(b['plan_source_utf8'].encode());b['terminal_binding_source_utf8']=canonical(terminal)
        for kind in('fraction','future'):self.blocked(candidate(boundary_change(lambda b:mutate(b,kind))))

    def test_old_zero_terminal_profile_still_rejects_this_supplied_payable(self):
        p=json.loads(source());wa,_=source_window(p);ha=wa[3];spec=json.loads(ha[4]);spec.pop('boundary_source_sha256');spec.update(schema='miniuw.synthetic-hold-sale-cash.v1',profile='SYNTHETIC-OPERATING-HOLD-TERMINAL-SALE-NO-REFINANCE-v1')
        old=reconcile_hold_sale_cash(*ha[:4],enc(spec));self.assertIsNone(old.payload['exportable_equity_movements']);self.assertIn('payables:terminal_working_balance_requires_settlement_profile',old.payload['blockers'])

    def test_boundary_cash_or_sale_debt_proof_cannot_be_bypassed(self):
        def change(p,key):
            if key=='cash':b=json.loads(p['cash_boundary_source_utf8']);b['operation_source_sha256']='0'*64;p['cash_boundary_source_utf8']=canonical(b)
            else:b=json.loads(p['sale']['debt_source_utf8']);b['closing_run_sha256']='0'*64;p['sale']['debt_source_utf8']=canonical(b)
        # Changing exact source text always invalidates the preserved boundary binding even if unknown schema fields reject early.
        p=json.loads(source());debt=json.loads(p['sale']['debt_source_utf8']);debt['closing_run_sha256']='0'*64;p['sale']['debt_source_utf8']=canonical(debt);self.blocked(enc(refresh(p)))
        p=json.loads(source());ws=json.loads(p['window_source_utf8']);ws['cash_binding_sha256']='0'*64;p['window_source_utf8']=canonical(ws);self.blocked(enc(refresh(p)))

    def test_event_mapping_unknown_prepopulated_or_off_grid_is_never_filled(self):
        for kind in('filled','date','mapping'):
            def change(p):
                if kind=='mapping':b=json.loads(p['return_binding_source_utf8']);b['operating_slots'].pop();p['return_binding_source_utf8']=canonical(b)
                else:
                    s=json.loads(p['investor_source_utf8']);s['events'][0]['amount']=q(1)if kind=='filled'else None
                    if kind=='date':s['events'][0]['date']='2026-10-02'
                    p['investor_source_utf8']=canonical(s)
            self.blocked(candidate(change))

    def test_all_process_hash_seeds_produce_identical_full_run(self):
        code="from pathlib import Path;from miniuw_foundation.settled_case import assemble_settled_case;print(assemble_settled_case(Path('templates/settled-lifecycle-retained-T108.json').read_bytes()).sha256)"
        values=[]
        for seed in('1','2','42'):
            env=dict(os.environ,PYTHONHASHSEED=seed,PYTHONDONTWRITEBYTECODE='1');env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+os.environ.get('PYTHONPATH','')
            p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60);self.assertEqual(p.returncode,0,p.stderr);values.append(p.stdout.strip())
        self.assertEqual(len(set(values)),1);self.assertEqual(values[0],assemble_settled_case(source()).sha256)

    def test_rehashed_current_return_and_other_raw_source_do_not_verify(self):
        from miniuw_foundation.settled_case import verify_settled_case
        result=assemble_settled_case(source());p=result.payload;p['project_return_story']['gross_distributions']=q(845);text=canonical(p)
        with self.assertRaises(ValidationError):verify_settled_case(source(),replace(result,payload_json=text,sha256=digest(text)))
        with self.assertRaises(ValidationError):verify_settled_case(source()+b'\n',result)

    def test_three_file_source_first_recovery_handles_current_and_blocked_cases(self):
        blocked=candidate(boundary_change(lambda b:b['accounting'].update(before_payables=None)))
        for raw in(source(),blocked):
            values,result=build_settled_case_artifacts(raw);self.assertEqual(len(values),3);self.assertFalse(any(k.endswith('.pdf')for k in values))
            with tempfile.TemporaryDirectory()as td:
                root=Path(td)
                for k,v in values.items():(root/k).write_bytes(v)
                self.assertEqual(recover_settled_case_directory(root),result);self.assertEqual(audit_settled_case_directory(root)['files_verified'],3)

    def test_versions_rehashed_results_and_unsafe_manifest_cannot_replace_replay(self):
        values,_=build_settled_case_artifacts(source())
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for k,v in values.items():(root/k).write_bytes(v)
            restore();p=json.loads(values['package.json']);p['versions']['modules']['settled_case']='0'*64;(root/'package.json').write_bytes(enc(p))
            with self.assertRaises(ValidationError):recover_settled_case_directory(root)
            restore();p=json.loads(values['package.json']);row=next(r for r in p['files']if r['path']=='settled-case-results.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'settled-case-results.json').write_bytes(b'{}');(root/'package.json').write_bytes(enc(p))
            with self.assertRaises(ValidationError):recover_settled_case_directory(root)
            restore();p=json.loads(values['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(enc(p))
            with self.assertRaises(ValidationError):recover_settled_case_directory(root)

    def test_retry_no_other_overwrite_size_symlink_and_own_temp_cleanup(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);out=root/'out';write_settled_case_artifacts(source(),out);before=read_settled_case_artifacts(out);self.assertEqual(write_settled_case_artifacts(source(),out)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_settled_case_artifacts(source('distributed'),out)
            self.assertEqual(read_settled_case_artifacts(out),before);(out/'extra').write_bytes(b'x')
            with self.assertRaises(ValidationError):read_settled_case_artifacts(out)
            (out/'extra').unlink();(out/'settled-case-results.json').unlink();(out/'settled-case-results.json').symlink_to(out/'settled-case-source.json')
            with self.assertRaises(ValidationError):read_settled_case_artifacts(out)
        with patch('miniuw_foundation.settled_case_artifacts.MAX_FILE_BYTES',10):
            with self.assertRaises(ValidationError):build_settled_case_artifacts(source())
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep';keep.write_bytes(b'x')
            with patch('miniuw_foundation.settled_case_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_settled_case_artifacts(source(),root/'out')
            self.assertEqual(list(root.iterdir()),[keep])

    def test_strict_schema_duplicate_mapping_and_bounded_sources_reject(self):
        p=json.loads(source());p['unknown']=True
        with self.assertRaises(ValidationError):parse_settled_case(enc(p))
        def duplicate(b):b['payment_map'].append(copy.deepcopy(b['payment_map'][0]))
        with self.assertRaises(ValidationError):candidate(boundary_change(duplicate))
        with self.assertRaises(ValidationError):parse_settled_case(source().replace(b'"schema":',b'"schema":null,"schema":',1))

    def test_full_cash_path_does_not_approve_personal_capital_policy_or_real_decisions(self):
        p=assemble_settled_case(source()).payload;self.assertTrue(p['full_supplied_synthetic_cash_path_connected']);self.assertEqual(p['decision'],'PENDING');self.assertIsNone(p['personal_investor_return'])
        for key in('accounting_stocks_inferred','extra_expense_payment_or_equity_generated','phase_principal_counted_as_new_equity','all_model_profiles_or_financial_validation_complete',
            'current_source_authority_verified','one_page_for_this_new_profile_integrated','capital_or_CoC_definitions_adopted','new_external_PDF_created','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):self.assertIs(p[key],False)
        self.assertTrue(all(row['conditional_coc']is None for row in p['project_return_story']['annual_cash_receipts']))


if __name__=='__main__':unittest.main()
