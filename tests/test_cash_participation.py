from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import _fraction,rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.worksheet_case_artifacts import recover_worksheet_case_bundle
from miniuw_foundation.worksheet_case_output import assemble_worksheet_case
from miniuw_foundation.cash_participation import assemble_cash_participation,_from_verified_parent,_allocate,parse_terms
from miniuw_foundation.cash_participation_artifacts import (build_cash_participation_artifacts,export_cash_participation_bundle,
    recover_cash_participation_bundle,versions,write_cash_participation_artifacts,audit_cash_participation_directory,read_cash_participation_artifacts)

ROOT=Path(__file__).resolve().parents[1];q=rational;encoded=lambda p:(canonical(p)+'\n').encode()
def terms(label):return(ROOT/('templates/cash-participation-'+label+'-T104.json')).read_bytes()


def cash_probe(same_day=False):
    # Standalone mathematical ledger, not an accepted case or actual payment claim.
    categories=('initial_capital','additional_capital','refinance_cash_in','net_refinance_distribution','operating_distribution','net_sale_distribution','other_distribution')
    events=[dict(event_id='A',date='2025-01-01',kind='contribution',category='initial_capital',currency='USD',amount=q(F(100)),source_ref='SYNTHETIC-A'),
        dict(event_id='D',date='2027-01-01',kind='distribution',category='net_sale_distribution',currency='USD',amount=q(F(121)),source_ref='SYNTHETIC-D')]
    if same_day:events[1:1]=[dict(event_id='AA',date='2026-01-01',kind='contribution',category='additional_capital',currency='USD',amount=q(F(50)),source_ref='SYNTHETIC-AA'),
        dict(event_id='DD',date='2026-01-01',kind='distribution',category='operating_distribution',currency='USD',amount=q(F(50)),source_ref='SYNTHETIC-DD')]
    a,d=F(150 if same_day else 100),F(171 if same_day else 121)
    category={k:q(sum((_fraction(e['amount'])for e in events if e['category']==k),F(0)))for k in categories}
    years=[dict(calendar_cash_receipt_year=2025,gross_contributions=q(F(100)),gross_distributions=q(F(0)),net_equity_cash=q(F(-100)),operating_distributions_only=q(F(0))),
        dict(calendar_cash_receipt_year=2026,gross_contributions=q(F(50 if same_day else 0)),gross_distributions=q(F(50 if same_day else 0)),net_equity_cash=q(F(0)),operating_distributions_only=q(F(50 if same_day else 0))),
        dict(calendar_cash_receipt_year=2027,gross_contributions=q(F(0)),gross_distributions=q(F(121)),net_equity_cash=q(F(121)),operating_distributions_only=q(F(0)))]
    story=dict(currency='USD',cash_horizon=dict(start='2025-01-01',end='2027-01-01'),dated_events=events,gross_contributions=q(a),gross_distributions=q(d),net_cash_profit=q(d-a),cash_by_category=category,annual_cash_receipts=years)
    evidence=dict(grid=dict(dates=['2025-01-01','2026-01-01','2027-01-01'],step_months=12),
        parameters=dict(max_periodic_rate_interval_width=q(F(1,10**6)),split_budget=2048,operation_budget=200000,periods_per_year=1),
        dated_net_flows=[dict(date=day,net=q(value))for day,value in zip(['2025-01-01','2026-01-01','2027-01-01'],[F(-100),F(0),F(121)])])
    return story,evidence


class CashParticipationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        recovered=recover_worksheet_case_bundle((ROOT/'docs/review/miniuw-v1-worksheet-case-example/execution-evidence.json').read_bytes())
        cls.args=(recovered.case_raw,recovered.workbook_raw,recovered.binding_raw);cls.parent=recovered.run
        cls.files,cls.checked=build_cash_participation_artifacts(*cls.args,terms('quarter'))

    def hypothetical(self,label='quarter',mutate=None,parent=None):
        p=json.loads(terms(label))
        if mutate:mutate(p)
        return _from_verified_parent(encoded(p),parent or self.parent)

    def test_quarter_exact_contributions_receipts_sale_and_pending_personal_scope(self):
        p=self.checked.payload;first,second=p['participants']
        self.assertEqual([_fraction(first[k])for k in('gross_contributions','gross_distributions','net_cash_profit','equity_multiple')],[F(350),F(389,2),F(-311,2),F(389,700)])
        self.assertEqual(first['cash_by_category']['initial_capital'],q(F(250)));self.assertEqual(first['cash_by_category']['additional_capital'],q(F(100)))
        self.assertEqual(first['cash_by_category']['operating_distribution'],q(F(50)));self.assertEqual(first['cash_by_category']['net_sale_distribution'],q(F(289,2)))
        self.assertEqual(second['gross_contributions'],q(F(1050)))
        for row in p['participants']:
            for key in('capital_still_invested','retained_equity_value','conditional_CoC','verified_personal_investor_return','selected_IRR'):self.assertIsNone(row[key])
            self.assertEqual(row['verified_personal_investor_return_state'],'PENDING')
        self.assertEqual(p['decision'],'PENDING');self.assertFalse(p['allocation_terms_adopted']);self.assertFalse(p['personal_investor_return_verified'])
        self.assertEqual(self.checked.parent_run,self.parent)

    def test_thirds_reconcile_every_gross_event_category_and_year_without_cent_rounding(self):
        p=self.hypothetical('third').payload;s=self.parent.payload['current_project_return_story']
        self.assertEqual(p['participants'][0]['gross_distributions'],q(F(778,3)))
        for i,e in enumerate(s['dated_events']):
            self.assertEqual(sum((_fraction(row['dated_events'][i]['amount'])for row in p['participants']),F(0)),_fraction(e['amount']))
            for row in p['participants']:
                event=row['dated_events'][i];self.assertEqual(event['event_id'],e['event_id']);self.assertEqual(event['date'],e['date']);self.assertEqual(event['category'],e['category'])
                self.assertEqual(event['project_event_pointer'],'/current_project_return_story/dated_events/'+str(i))
        self.assertEqual(p['reconciliation']['category_totals'],s['cash_by_category'])
        self.assertEqual(len(p['reconciliation']['annual_checks']),len(s['annual_cash_receipts']))

    def test_zero_fraction_is_known_cash_zero_but_not_zero_multiple_or_IRR(self):
        zero,whole=self.hypothetical('zero').payload['participants']
        self.assertEqual(zero['gross_contributions'],q(F(0)));self.assertEqual(zero['gross_distributions'],q(F(0)))
        self.assertIsNone(zero['equity_multiple']);self.assertEqual(zero['periodic_IRR']['root_classification'],'identically_zero_net_polynomial')
        self.assertEqual(zero['annual_IRR_roots'],[]);self.assertIsNone(zero['selected_IRR']);self.assertFalse(zero['positive_scalar_net_flow_identity_verified'])
        self.assertEqual(whole['gross_distributions'],self.parent.payload['current_project_return_story']['gross_distributions'])

    def test_missing_invalid_or_partial_shares_do_not_create_residual_or_partial_allocation(self):
        cases=[lambda p:p['participants'][1].update(share_fraction=None),lambda p:p['participants'][1].update(share_fraction=q(F(1,2))),
            lambda p:p['participants'][0].update(share_fraction=q(F(-1,4))),lambda p:p['participants'][0].update(share_fraction=q(F(2))),
            lambda p:p.update(participant_inventory_complete=None),lambda p:p['participants'][0].update(source_ref=None)]
        for mutate in cases:
            p=self.hypothetical(mutate=mutate).payload;self.assertEqual(p['state'],'PENDING');self.assertTrue(p['blockers']);self.assertIsNone(p['participants']);self.assertIsNone(p['reconciliation'])

    def test_binding_context_currency_window_source_and_profile_assumptions_are_explicit(self):
        cases=[lambda p:p.update(worksheet_run_sha256='0'*64),lambda p:p['source_hashes'].update(case='0'*64),
            lambda p:p['context'].update(deal_id='OTHER'),lambda p:p.update(currency='EUR'),lambda p:p.update(share_unit='%'),
            lambda p:p.update(allocation_end_date='2027-06-01'),lambda p:p.update(source_ref=None),lambda p:p.update(whole_ledger_scope_ref=None),
            lambda p:p['assumptions'].update(fees_promotes_taxes_or_priority_adjustments=True),lambda p:p['assumptions'].update(same_fraction_for_all_contributions_and_distributions=None)]
        for mutate in cases:self.assertEqual(self.hypothetical(mutate=mutate).payload['state'],'PENDING')
        p=json.loads(terms('quarter'));p['participants'].append(p['participants'][0])
        with self.assertRaises(ValidationError):parse_terms(encoded(p))
        p=json.loads(terms('quarter'));p['participants']*=3
        with self.assertRaises(ValidationError):parse_terms(encoded(p))
        with self.assertRaises(ValidationError):parse_terms(terms('quarter').replace(b'"profile":',b'"profile":null,"profile":',1))

    def test_blocked_worksheet_stays_blocked_through_allocation_and_portable_recovery(self):
        root=ROOT/'templates';book=(root/'worksheet-case-zero-conflict-T103.xlsx').read_bytes();binding=(root/'worksheet-case-zero-conflict-T103.json').read_bytes()
        parent=assemble_worksheet_case(self.args[0],book,binding);p=json.loads(terms('quarter'));p.update(source_hashes=parent.payload['worksheet_reconciliation']['source_hashes'],worksheet_run_sha256=parent.sha256)
        raw=encoded(p);run=assemble_cash_participation(self.args[0],book,binding,raw)
        self.assertEqual(run.payload['blockers'],['current_project_cash_unavailable']);self.assertIsNone(run.payload['participants'])
        restored=recover_cash_participation_bundle(export_cash_participation_bundle(self.args[0],book,binding,raw,run))
        self.assertEqual(restored.run,run);self.assertIsNone(restored.run.payload['participants'])

    def test_equal_net_series_with_different_gross_same_day_events_has_different_EM(self):
        t=json.loads(terms('quarter'));a,_=_allocate(*cash_probe(False),t,[F(1,4),F(3,4)]);b,_=_allocate(*cash_probe(True),t,[F(1,4),F(3,4)])
        self.assertEqual(a[0]['dated_net_flows'],b[0]['dated_net_flows'])
        self.assertEqual(a[0]['equity_multiple'],q(F(121,100)));self.assertEqual(b[0]['equity_multiple'],q(F(57,50)))
        self.assertEqual(b[0]['gross_contributions'],q(F(75,2)));self.assertEqual(b[0]['gross_distributions'],q(F(171,4)))

    def test_independent_known_ten_percent_root_and_positive_scaling_identity(self):
        rows,_=_allocate(*cash_probe(),json.loads(terms('third')),[F(1,3),F(2,3)])
        for row in rows:
            result=row['periodic_IRR'];self.assertEqual(result['status'],'complete_synthetic');self.assertEqual(result['distinct_positive_discount_roots'],1)
            self.assertEqual(result['coefficient_bit_limit'],4096);self.assertEqual(result['operation_budget'],200000)
            interval=row['annual_IRR_roots'][0]['annual_rate_interval']
            self.assertLessEqual(_fraction(interval['lower'],1300),F(1,10));self.assertGreaterEqual(_fraction(interval['upper'],1300),F(1,10))
            self.assertTrue(row['positive_scalar_net_flow_identity_verified']);self.assertIsNone(row['selected_IRR'])

    def test_cashless_years_and_explicit_zero_events_are_never_omitted(self):
        story,evidence=cash_probe();story['dated_events'].append(dict(event_id='ZERO',date='2026-01-01',kind='contribution',category='additional_capital',currency='USD',amount=q(F(0)),source_ref='SYNTHETIC-zero'))
        rows,reconciliation=_allocate(story,evidence,json.loads(terms('quarter')),[F(1,4),F(3,4)])
        for row in rows:
            self.assertEqual([y['calendar_cash_receipt_year']for y in row['annual_cash']],[2025,2026,2027])
            self.assertEqual(row['annual_cash'][1]['gross_contributions'],q(F(0)));self.assertEqual(row['annual_cash'][1]['gross_distributions'],q(F(0)))
            self.assertEqual(row['dated_events'][-1]['event_id'],'ZERO');self.assertEqual(row['dated_events'][-1]['amount'],q(F(0)))
        self.assertEqual(len(reconciliation['event_checks']),3)

    def test_incomplete_or_unannualized_IRR_keeps_cash_but_withholds_annual_current_roots(self):
        for control,value in(('operation_budget',1),('periods_per_year',None)):
            story,evidence=cash_probe();evidence['parameters'][control]=value
            rows,_=_allocate(story,evidence,json.loads(terms('quarter')),[F(1,4),F(3,4)])
            for row in rows:
                self.assertEqual(row['gross_distributions'],q(F(121,4))if row['share_fraction']==q(F(1,4))else q(F(363,4)))
                self.assertEqual(row['annual_IRR_roots'],[]);self.assertTrue(row['annualization_blockers']);self.assertIsNone(row['selected_IRR'])

    def test_exact_arithmetic_budget_withdraws_all_allocations_without_parent_mutation(self):
        # Unit budget probe, deliberately not a source-accepted parent case.
        p=self.parent.payload;p['current_project_return_story']['dated_events'][0]['amount']=q(F(1,2**4090-1))
        value=canonical(p);parent=replace(self.parent,payload_json=value,sha256=digest(value));before=parent.payload_json;den=10**250+7
        t=json.loads(terms('quarter'));t['worksheet_run_sha256']=parent.sha256;t['participants'][0]['share_fraction']=q(F(1,den));t['participants'][1]['share_fraction']=q(F(den-1,den))
        result=_from_verified_parent(encoded(t),parent).payload
        self.assertEqual(result['blockers'],['cash_allocation_exact_arithmetic_budget_exceeded']);self.assertIsNone(result['participants']);self.assertIsNone(result['reconciliation']);self.assertEqual(parent.payload_json,before)

    def test_rehashed_results_or_changed_sources_cannot_be_exported_as_verified(self):
        p=self.checked.payload;p['participants'][0]['gross_distributions']=q(F(999));value=canonical(p);fake=replace(self.checked,payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):export_cash_participation_bundle(*self.args,terms('quarter'),fake)
        with self.assertRaises(ValidationError):export_cash_participation_bundle(self.args[0]+b'\n',*self.args[1:],terms('quarter'),self.checked)

    def test_portable_recovers_exact_four_sources_and_complete_result(self):
        raw=export_cash_participation_bundle(*self.args,terms('quarter'),self.checked);restored=recover_cash_participation_bundle(raw)
        self.assertEqual((restored.case_raw,restored.workbook_raw,restored.binding_raw,restored.terms_raw),(*self.args,terms('quarter')));self.assertEqual(restored.run,self.checked)

    def test_portable_versions_rehashed_money_and_source_changes_are_not_trusted(self):
        raw=self.files['allocation-evidence.json']
        for key in versions():
            p=json.loads(raw);p[key]='0'*64
            with self.assertRaises(ValidationError):recover_cash_participation_bundle(encoded(p))
        p=json.loads(raw);result=json.loads(p['result']['payload_json']);result['allocation_terms_adopted']=True;value=canonical(result);p['result']=dict(payload_json=value,sha256=digest(value))
        with self.assertRaises(ValidationError):recover_cash_participation_bundle(encoded(p))
        p=json.loads(raw);p['terms_utf8']=terms('third').decode()
        with self.assertRaises(ValidationError):recover_cash_participation_bundle(encoded(p))

    def test_internal_four_file_packet_retry_and_no_different_overwrite_or_new_PDF(self):
        page=ROOT/'docs/review/miniuw-v1-worksheet-case-example/MiniUW_v1_Resumen.pdf';before_page=page.read_bytes()
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'out';write_cash_participation_artifacts(*self.args,terms('quarter'),target);before=read_cash_participation_artifacts(target)
            self.assertEqual(len(before),4);self.assertFalse(any(n.endswith('.pdf')for n in before));self.assertEqual(audit_cash_participation_directory(target)['files_verified'],4)
            self.assertEqual(write_cash_participation_artifacts(*self.args,terms('quarter'),target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_cash_participation_artifacts(*self.args,terms('third'),target)
            self.assertEqual(before,read_cash_participation_artifacts(target))
        self.assertEqual(before_page,page.read_bytes())

    def test_rehashed_unsafe_extra_symlink_packets_and_failed_rename_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td)
            for k,v in self.files.items():(root/k).write_bytes(v)
            p=json.loads(self.files['package.json']);(root/'allocation-results.json').write_bytes(b'{}');row=next(r for r in p['files']if r['path']=='allocation-results.json');row.update(bytes=2,sha256=sha(b'{}'));(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):audit_cash_participation_directory(root)
            for k,v in self.files.items():(root/k).write_bytes(v)
            p=json.loads(self.files['package.json']);p['files'][0]['path']='../outside';(root/'package.json').write_bytes(encoded(p))
            with self.assertRaises(ValidationError):audit_cash_participation_directory(root)
            (root/'extra').write_bytes(b'x')
            with self.assertRaises(ValidationError):read_cash_participation_artifacts(root)
            (root/'extra').unlink();(root/'allocation-terms.json').unlink();(root/'allocation-terms.json').symlink_to(root/'allocation-results.json')
            with self.assertRaises(ValidationError):read_cash_participation_artifacts(root)
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);keep=root/'keep';keep.write_bytes(b'x')
            with patch('miniuw_foundation.cash_participation_artifacts.os.rename',side_effect=OSError('injected')):
                with self.assertRaises(OSError):write_cash_participation_artifacts(*self.args,terms('quarter'),root/'out')
            self.assertEqual(list(root.iterdir()),[keep])


if __name__=='__main__':unittest.main()
