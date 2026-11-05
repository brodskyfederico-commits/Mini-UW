from dataclasses import replace
from fractions import Fraction as F
from itertools import permutations,product
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational,_fraction
from miniuw_foundation.operating_noi import ArithmeticBudgetError
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_case_output import assemble_worksheet_case
from miniuw_foundation.cash_participation import _from_verified_parent as allocation_from_parent
from miniuw_foundation.cash_participation_artifacts import recover_cash_participation_bundle,export_cash_participation_bundle
from miniuw_foundation.participant_cash_risk import (analyze_participant_cash_risk,verify_participant_cash_risk,
    _from_verified_allocation,_cash_observations,ADDITIVE,DATED)
from miniuw_foundation.participant_cash_risk_artifacts import (build_participant_cash_risk_artifacts,versions,
    write_participant_cash_risk_artifacts,read_participant_cash_risk_artifacts,recover_participant_cash_risk_directory,
    audit_participant_cash_risk_directory)

ROOT=Path(__file__).resolve().parents[1];q=rational;encoded=lambda p:(canonical(p)+'\n').encode()
SOURCE=(ROOT/'docs/review/miniuw-v1-cash-participation-example/allocation-evidence.json').read_bytes()


def allocation_source(label,recovered=None):
    if label=='quarter':return SOURCE
    # Offline fixture composition from unchanged verified T103 evidence and existing explicit T104 terms.
    recovered=recovered or recover_cash_participation_bundle(SOURCE)
    terms=(ROOT/('templates/cash-participation-'+label+'-T104.json')).read_bytes()
    run=allocation_from_parent(terms,recovered.run.parent_run);p=json.loads(SOURCE)
    p.update(terms_utf8=terms.decode(),result=dict(payload_json=run.payload_json,sha256=run.sha256))
    return encoded(p)


def two_day_probe():
    # Exact cash-only probe; not a source-accepted case or funding availability claim.
    a,b='2025-01-01','2025-02-01'
    events=[dict(event_id='A',date=a,kind='contribution',category='initial_capital',amount=q(F(100))),
        dict(event_id='D',date=a,kind='distribution',category='operating_distribution',amount=q(F(50))),
        dict(event_id='AA',date=b,kind='contribution',category='additional_capital',amount=q(F(30))),
        dict(event_id='DD',date=b,kind='distribution',category='net_sale_distribution',amount=q(F(10)))]
    return events,[dict(date=a,net=q(F(-50))),dict(date=b,net=q(F(-20)))]


class ParticipantCashRiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files,cls.checked=build_participant_cash_risk_artifacts(SOURCE)
        cls.recovered=recover_cash_participation_bundle(SOURCE)

    def test_quarter_shortfall_peak_sale_dependency_and_cash_only_limits(self):
        p=self.checked.payload;first=p['participants'][0];m=first['metrics']
        self.assertEqual([_fraction(m[k])for k in('cash_shortfall_at_horizon','cash_surplus_at_horizon',
            'peak_cumulative_net_equity_funding_at_date_close','possible_intraday_peak_upper_bound','sale_share_of_distributions',
            'cash_shortfall_excluding_sale_receipts')],[F(311,2),F(0),F(350),F(350),F(289,389),F(300)])
        self.assertEqual(p['evaluated_as_of_UTC'],self.recovered.run.parent_run.payload['evaluated_as_of_UTC'])
        for row,source in zip(p['participants'],self.recovered.run.payload['participants']):
            self.assertEqual(row['currency'],source['currency']);self.assertEqual(row['cash_horizon'],source['cash_horizon'])
            for key in('capital_still_invested','retained_equity_value','conditional_CoC','final_economic_capital_loss','verified_personal_investor_return','actual_capital_available'):self.assertIsNone(row[key])
            self.assertEqual(row['actual_liquidity_state'],'PENDING');self.assertFalse(row['within_date_order_verified'])
        self.assertFalse(p['sale_exclusion_is_recomputed_scenario']);self.assertFalse(p['full_risk_analysis_completed']);self.assertEqual(p['decision'],'PENDING')

    def test_same_day_gross_cash_exposes_distinct_close_and_intraday_bounds(self):
        events,net=two_day_probe();m,rows=_cash_observations(events,net)
        self.assertEqual(m['gross_contributions'],q(F(130)));self.assertEqual(m['gross_distributions'],q(F(60)))
        self.assertEqual(m['peak_cumulative_net_equity_funding_at_date_close'],q(F(70)));self.assertEqual(m['possible_intraday_peak_upper_bound'],q(F(100)))
        self.assertEqual(rows[0]['within_date_peak_lower_bound'],q(F(50)));self.assertEqual(rows[1]['within_date_peak_upper_bound'],q(F(80)))
        self.assertEqual(m['sale_share_of_distributions'],q(F(1,6)));self.assertEqual(m['cash_shortfall_excluding_sale_receipts'],q(F(80)))

    def test_independent_all_order_enumeration_proves_tight_global_bounds(self):
        events,net=two_day_probe();m,_=_cash_observations(events,net);peaks=[]
        for first,second in product(permutations(events[:2]),permutations(events[2:])):
            balance=peak=F(0)
            for event in(*first,*second):
                balance+=_fraction(event['amount'])*(1 if event['kind']=='contribution'else-1);peak=max(peak,balance)
            peaks.append(peak)
        self.assertEqual(len(peaks),4);self.assertEqual(min(peaks),_fraction(m['peak_cumulative_net_equity_funding_at_date_close']))
        self.assertEqual(max(peaks),_fraction(m['possible_intraday_peak_upper_bound']))

    def test_event_list_order_does_not_assert_intraday_order_or_mutate_source(self):
        events,net=two_day_probe();before=copy.deepcopy(events);expected,dates=_cash_observations(events,net)
        for candidate in permutations(events):
            current,rows=_cash_observations(list(candidate),net);self.assertEqual(current,expected)
            self.assertEqual([{k:r[k]for k in DATED}for r in rows],[{k:r[k]for k in DATED}for r in dates])
        self.assertEqual(events,before)

    def test_signed_surplus_carries_forward_without_clamping_or_capital_available_claim(self):
        events,net=two_day_probe();events=[dict(events[1],amount=q(F(60))),dict(events[2],amount=q(F(20)))]
        net[0]['net']=q(F(60));net[1]['net']=q(F(-20));m,rows=_cash_observations(events,net)
        self.assertEqual(rows[1]['cumulative_before_date'],q(F(-60)));self.assertEqual(rows[1]['cumulative_contributions_less_distributions'],q(F(-40)))
        self.assertEqual(m['cash_shortfall_at_horizon'],q(F(0)));self.assertEqual(m['cash_surplus_at_horizon'],q(F(40)))
        self.assertEqual(m['possible_intraday_peak_upper_bound'],q(F(0)))

    def test_no_receipts_is_undefined_while_known_zero_sale_ratio_is_zero(self):
        events,net=two_day_probe();only=[dict(events[0],amount=q(F(20))),dict(events[2],amount=q(F(0)))]
        net[0]['net']=q(F(-20));net[1]['net']=q(F(0));m,rows=_cash_observations(only,net)
        self.assertIsNone(m['sale_share_of_distributions']);self.assertEqual(m['sale_share_state'],'undefined_zero_distributions')
        self.assertEqual(rows[1]['event_indices'],[1]);self.assertEqual(rows[1]['event_ids'],['AA'])
        only[1]=dict(events[1],date=net[1]['date'],amount=q(F(20)));net[1]['net']=q(F(20));m,_=_cash_observations(only,net)
        self.assertEqual(m['sale_share_of_distributions'],q(F(0)));self.assertEqual(m['sale_share_state'],'computed_synthetic')

    def test_missing_negative_off_grid_duplicate_and_inconsistent_cash_is_rejected(self):
        events,net=two_day_probe()
        for mutate in(lambda e:e[0].update(amount=None),lambda e:e[0].update(amount=q(F(-1))),
            lambda e:e[0].update(date='2025-03-01'),lambda e:e[1].update(event_id=e[0]['event_id'])):
            candidate=copy.deepcopy(events);mutate(candidate)
            with self.assertRaises(ValidationError):_cash_observations(candidate,net)
        for candidate in(list(reversed(net)),[net[0],net[0]],[dict(net[0],net=None),net[1]],[dict(net[0],net=q(F(99))),net[1]]):
            with self.assertRaises(ValidationError):_cash_observations(events,candidate)

    def test_thirds_additive_cash_and_dated_bounds_reconcile_but_ratios_are_not_summed(self):
        run=analyze_participant_cash_risk(allocation_source('third',self.recovered));p=run.payload;project=p['reconciliation']['project_metrics']
        for key in ADDITIVE:self.assertEqual(sum((_fraction(r['metrics'][key],1300)for r in p['participants']),F(0)),_fraction(project[key],1300))
        for r in p['participants']:self.assertEqual(r['metrics']['sale_share_of_distributions'],q(F(289,389)))
        self.assertFalse(p['reconciliation']['sale_ratios_summed']);self.assertEqual(project,self.recovered.run.parent_run.payload['current_project_return_story']['risk_observations'])
        for index,check in enumerate(p['reconciliation']['dated_checks']):
            for key in DATED:self.assertEqual(check['allocated'][key],q(sum((_fraction(r['dated_observations'][index][key],1300)for r in p['participants']),F(0))))

    def test_zero_share_stays_known_zero_with_undefined_sale_ratio(self):
        p=analyze_participant_cash_risk(allocation_source('zero',self.recovered)).payload;zero,whole=p['participants']
        self.assertTrue(all(zero['metrics'][k]==q(F(0))for k in ADDITIVE));self.assertIsNone(zero['metrics']['sale_share_of_distributions'])
        self.assertEqual(zero['metrics']['sale_share_state'],'undefined_zero_distributions');self.assertEqual(whole['metrics'],p['reconciliation']['project_metrics'])
        self.assertEqual(len(zero['dated_observations']),10)

    def test_missing_allocation_remains_pending_without_project_risk_fallback(self):
        run=analyze_participant_cash_risk(allocation_source('missing',self.recovered));p=run.payload
        self.assertIsNone(p['participants']);self.assertIsNone(p['reconciliation']);self.assertEqual(p['blockers'],['current_participant_cash_unavailable'])
        self.assertIsNotNone(run.parent_run.parent_run.payload['current_project_return_story']);self.assertEqual(p['upstream_allocation_state'],'PENDING')

    def test_worksheet_blocked_allocation_and_risk_stay_withdrawn_after_directory_recovery(self):
        case=self.recovered.case_raw;book=(ROOT/'templates/worksheet-case-zero-conflict-T103.xlsx').read_bytes();binding=(ROOT/'templates/worksheet-case-zero-conflict-T103.json').read_bytes()
        parent=assemble_worksheet_case(case,book,binding);terms=json.loads(self.recovered.terms_raw)
        terms.update(source_hashes=parent.payload['worksheet_reconciliation']['source_hashes'],worksheet_run_sha256=parent.sha256)
        raw=encoded(terms);allocation=allocation_from_parent(raw,parent);source=export_cash_participation_bundle(case,book,binding,raw,allocation)
        with tempfile.TemporaryDirectory()as td:
            write_participant_cash_risk_artifacts(source,Path(td)/'out');run=recover_participant_cash_risk_directory(Path(td)/'out')
            self.assertIsNone(run.payload['participants']);self.assertIsNone(run.parent_run.parent_run.payload['current_project_return_story'])
            self.assertEqual(run.payload['decision'],'PENDING')

    def test_exact_arithmetic_excess_withdraws_whole_result_without_parent_mutation(self):
        # Numerical guard probe, not a source-accepted financial case.
        parent=self.recovered.run;view=parent.parent_run.payload;huge=F(2**4095)
        chosen=[e for e in view['current_project_return_story']['dated_events']if e['kind']=='contribution'and _fraction(e['amount'])>0][:2]
        for e in chosen:
            e['amount']=q(huge)
            next(r for r in view['irr_recalculation']['dated_net_flows']if r['date']==e['date'])['net']=q(-huge)
        text=canonical(view);changed=replace(parent.parent_run,payload_json=text,sha256=digest(text));fake=replace(parent,parent_run=changed);before=fake.parent_run.payload_json
        result=_from_verified_allocation(SOURCE,fake).payload
        self.assertEqual(result['blockers'],['participant_cash_risk_exact_arithmetic_budget_exceeded']);self.assertIsNone(result['participants']);self.assertIsNone(result['reconciliation']);self.assertEqual(fake.parent_run.payload_json,before)

    def test_rehashed_risk_or_other_source_bytes_do_not_verify_and_parent_is_unchanged(self):
        p=self.checked.payload;p['participants'][0]['metrics']['cash_shortfall_at_horizon']=q(F(0));text=canonical(p);fake=replace(self.checked,payload_json=text,sha256=digest(text))
        with self.assertRaises(ValidationError):verify_participant_cash_risk(SOURCE,fake)
        with self.assertRaises(ValidationError):verify_participant_cash_risk(SOURCE+b'\n',self.checked)
        self.assertEqual(verify_participant_cash_risk(SOURCE,self.checked),self.checked)
        self.assertEqual(self.checked.parent_run,self.recovered.run)

    def test_three_file_packet_reuses_original_evidence_and_creates_no_PDF(self):
        self.assertEqual(set(self.files),{'allocation-evidence.json','participant-cash-risk.json','package.json'})
        self.assertEqual(self.files['allocation-evidence.json'],SOURCE);self.assertFalse(any(p.endswith('.pdf')for p in self.files))
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            for name,value in self.files.items():(root/name).write_bytes(value)
            self.assertEqual(recover_participant_cash_risk_directory(root),self.checked);self.assertEqual(audit_participant_cash_risk_directory(root)['files_verified'],3)

    def test_versions_rehashed_results_and_unsafe_inventories_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            def restore():
                for name,value in self.files.items():(root/name).write_bytes(value)
            for key in versions():
                restore();p=json.loads(self.files['package.json']);p[key]='0'*64;(root/'package.json').write_bytes(encoded(p))
                with self.assertRaises(ValidationError):recover_participant_cash_risk_directory(root)
            restore();p=json.loads(self.files['package.json']);(root/'participant-cash-risk.json').write_bytes(b'{}');row=next(r for r in p['files']if r['path']=='participant-cash-risk.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):recover_participant_cash_risk_directory(root)
            restore();p=json.loads(self.files['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):recover_participant_cash_risk_directory(root)

    def test_retry_no_different_overwrite_extra_symlink_and_failed_rename_cleanup(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);target=root/'out';write_participant_cash_risk_artifacts(SOURCE,target);before=read_participant_cash_risk_artifacts(target)
            self.assertEqual(write_participant_cash_risk_artifacts(SOURCE,target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_participant_cash_risk_artifacts(SOURCE+b'\n',target)
            self.assertEqual(before,read_participant_cash_risk_artifacts(target));(target/'extra').write_bytes(b'x')
            with self.assertRaises(ValidationError):read_participant_cash_risk_artifacts(target)
            (target/'extra').unlink();(target/'participant-cash-risk.json').unlink();(target/'participant-cash-risk.json').symlink_to(target/'allocation-evidence.json')
            with self.assertRaises(ValidationError):read_participant_cash_risk_artifacts(target)
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep';keep.write_bytes(b'x')
            with patch('miniuw_foundation.participant_cash_risk_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_participant_cash_risk_artifacts(SOURCE,root/'out')
            self.assertEqual(list(root.iterdir()),[keep])


if __name__=='__main__':unittest.main()
