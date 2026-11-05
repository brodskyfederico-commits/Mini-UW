from pathlib import Path
from fractions import Fraction as F
from io import BytesIO
import copy,json,tempfile,unittest
from unittest.mock import patch
from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError,canonical
from miniuw_foundation.debt_service import rational,_fraction
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.phased_settled_output import assemble_phased_settled_output,required_sources,check_rental,parse_rental_binding
from miniuw_foundation.nominal_policy_book import reconcile_nominal_policy_book,parse_nominal_policy_book
from miniuw_foundation.current_settled_case import assemble_current_settled_case
from miniuw_foundation.phased_settled_report import render_phased_settled_output
from miniuw_foundation.phased_settled_artifacts import build_phased_settled_artifacts,write_phased_settled_artifacts,recover_phased_settled_directory,read_phased_settled_artifacts,versions
from miniuw_foundation.insurance_renewals import parse_policy_book
from miniuw_foundation.expense_schedule import parse_expense_schedule

ROOT=Path(__file__).resolve().parents[1]
raw=lambda p:canonical(p).encode()
q=lambda n:rational(F(n))


def fixture(label='current'):return (ROOT/('templates/phased-settled-'+label+'-T110.json')).read_bytes()


def refresh(p):
    """Explicit test-only new evidence hypothesis; runtime never renews a source."""
    p=copy.deepcopy(p);r=json.loads(p['registry_utf8']);requirements=required_sources(raw(p));r['requirements']=requirements
    old={v['requirement_id']:v for v in r['evidence']};r['evidence']=[dict(old[v['requirement_id']],**v)for v in requirements];p['registry_utf8']=canonical(r);return p


class PhasedSettledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=fixture();cls.p=json.loads(cls.source);cls.result=assemble_phased_settled_output(cls.source)
        cls.inner=json.loads(cls.p['current_settled_source_utf8']);cls.case_raw=cls.inner['case_source_utf8'].encode();cls.case=json.loads(cls.case_raw)
        cls.plan=json.loads(cls.case['boundary_source_utf8'])['plan_source_utf8'].encode();cls.book=json.loads(cls.p['policy_book_utf8']);cls.rental=json.loads(cls.p['rental_binding_utf8'])

    def assert_withheld(self,run):
        p=run.payload;self.assertEqual(p['state'],'PENDING');self.assertTrue(all(v is None for k,v in p.items()if k.startswith('current_')))
        self.assertEqual(p['decision'],'PENDING');self.assertFalse(p['real_decisions_enabled'])

    def test_phased_cash_equals_parent_and_independent_778_oracle(self):
        p=self.result.payload;s=p['current_project_return_story'];parent=assemble_current_settled_case(self.p['current_settled_source_utf8'].encode())
        self.assertEqual(s,parent.payload['current_project_return_story'])
        for k,n in [('gross_contributions',1400),('gross_distributions',778),('net_cash_profit',-622),('equity_multiple',F(389,700))]:self.assertEqual(_fraction(s[k],1300),n)
        self.assertEqual(_fraction(p['current_operating_totals']['closing_free_cash_claim']),213)
        self.assertEqual(_fraction(p['current_settlement_summary']['settlement_cash']),5)
        self.assertEqual(_fraction(s['cash_by_category']['operating_distribution']),200)
        self.assertEqual(_fraction(s['cash_by_category']['net_sale_distribution']),578)
        self.assertEqual(p['current_rental_totals'],dict(effective_rent=q(88),period_count=2));self.assertEqual(p['current_policy_totals']['policy_count'],2)
        self.assertFalse(p['rent_or_policy_counted_as_additional_equity_cash']);self.assertFalse(p['nominal_due_treated_as_payment'])

    def test_explicit_twelve_revision_changes_all_required_cash_not_rent(self):
        p=assemble_phased_settled_output(fixture('twelve')).payload;s=p['current_project_return_story']
        self.assertEqual(_fraction(s['gross_distributions']),776);self.assertEqual(_fraction(s['net_cash_profit']),-624)
        self.assertEqual(_fraction(p['current_policy_totals']['premiums']),22);self.assertEqual(_fraction(p['current_operating_totals']['closing_free_cash_claim']),211)
        self.assertEqual(_fraction(s['cash_by_category']['net_sale_distribution']),576);self.assertEqual(p['current_rental_totals'],self.result.payload['current_rental_totals'])
        self.assertNotEqual(p['current_irr_evidence'],self.result.payload['current_irr_evidence'])

    def test_every_new_and_parent_source_expiry_withdraws_all_current_money(self):
        for i in range(len(json.loads(self.p['registry_utf8'])['evidence'])):
            p=copy.deepcopy(self.p);r=json.loads(p['registry_utf8']);r['evidence'][i]['valid_until']=p['as_of_UTC'];p['registry_utf8']=canonical(r)
            with self.subTest(source=i):self.assert_withheld(assemble_phased_settled_output(raw(p)))

    def test_current_outer_registry_cannot_restore_expired_parent(self):
        p=assemble_phased_settled_output(fixture('parent-expired'));self.assert_withheld(p)
        self.assertIn('parent_current_settled_output_blocked',p.payload['blockers']['gate'])
        self.assertEqual(json.loads(p.payload['registry_run']['payload_json'])['state'],'current_synthetic_evidence')

    def test_self_consistent_omission_and_wrong_identity_do_not_pass(self):
        for mode in ('omitted','wrong_hash','extra'):
            p=copy.deepcopy(self.p);r=json.loads(p['registry_utf8'])
            if mode=='omitted':r['requirements'].pop();r['evidence'].pop()
            elif mode=='wrong_hash':r['requirements'][-1]['source_sha256']='1'*64;r['evidence'][-1]['source_sha256']='1'*64
            else:
                a=dict(r['requirements'][-1],requirement_id='/SYNTHETIC-extra',source_locator='/SYNTHETIC-extra');r['requirements'].append(a);r['evidence'].append(dict(r['evidence'][-1],**a,evidence_id='SYNTHETIC-extra'))
            p['registry_utf8']=canonical(r);self.assert_withheld(assemble_phased_settled_output(raw(p)))

    def test_source_bytes_need_new_evidence_even_equal_json(self):
        p=copy.deepcopy(self.p);p['policy_book_utf8']+='\n';self.assert_withheld(assemble_phased_settled_output(raw(p)))
        p=refresh(p);self.assertIsNotNone(assemble_phased_settled_output(raw(p)).payload['current_project_return_story'])
        p['as_of_UTC']='2027-07-01T13:00:00Z';self.assert_withheld(assemble_phased_settled_output(raw(p)))

    def test_each_rental_period_capacity_and_income_are_checked(self):
        for mode in ('income','capacity','other_income','wrong_hash','period_order','basis'):
            r=copy.deepcopy(self.rental)
            if mode in ('income','capacity'):
                c=json.loads(r['periods'][1]['calendar_source_utf8'])
                if mode=='capacity':c['capacity'][0]['total_units']=q(11)
                else:
                    s=json.loads(c['segments'][0]['rental_source_utf8']);s['residential_groups'][0]['rent']=q(3);c['segments'][0]['rental_source_utf8']=canonical(s)
                r['periods'][1]['calendar_source_utf8']=canonical(c)
            elif mode=='other_income':r['periods'][0]['other_zero_income_item_ids']=[]
            elif mode=='wrong_hash':r['periods'][0]['cash_source_sha256']='0'*64
            elif mode=='period_order':r['periods'].reverse()
            else:r['period_recognition_basis_ref']=None
            p=dict(self.p,rental_binding_utf8=canonical(r));run=assemble_phased_settled_output(raw(refresh(p)));self.assert_withheld(run);self.assertTrue(run.payload['blockers']['calculation']['rental'])

    def test_missing_proration_is_not_inferred_from_dates(self):
        r=copy.deepcopy(self.rental);c=json.loads(r['periods'][0]['calendar_source_utf8']);c['segments'][0]['proration_fraction']=None;r['periods'][0]['calendar_source_utf8']=canonical(c)
        self.assertIsNone(check_rental(self.case_raw,raw(r))['totals'])

    def test_policy_cut_due_is_nominal_and_not_generated_cash(self):
        run=reconcile_nominal_policy_book(self.plan,raw(self.book));p=run.payload
        self.assertEqual(p['state'],'matched_synthetic_nominal_successive_policies');self.assertTrue(p['installments_are_nominal_dues_not_cash_payments']);self.assertFalse(p['new_expense_or_payment_generated'])
        self.assertEqual(_fraction(p['totals']['premiums']),20);self.assertEqual(len(p['installment_groups']),3)
        self.assertEqual(self.book['policies'][1]['installments'][1]['due_date'],self.book['service_window_end'])

    def test_even_zero_extra_insurance_is_not_silently_omitted(self):
        p=copy.deepcopy(self.p);inner=json.loads(p['current_settled_source_utf8']);case=json.loads(inner['case_source_utf8']);boundary=json.loads(case['boundary_source_utf8'])
        detail=json.loads(boundary['periods'][0]['detail_source_utf8']);extra=copy.deepcopy(next(v for v in detail['items']if v['kind']=='insurance'));extra.update(item_id='SYNTHETIC-extra-insurance',expense_amount=q(0),opening_payables=q(0),closing_payables=q(0),opening_prepaid=q(0),closing_prepaid=q(0),payments=[]);detail['items'].append(extra)
        boundary['periods'][0]['detail_source_utf8']=canonical(detail);case['boundary_source_utf8']=canonical(boundary);inner['case_source_utf8']=canonical(case);p['current_settled_source_utf8']=canonical(inner)
        run=assemble_phased_settled_output(raw(refresh(p)));self.assert_withheld(run)
        self.assertIn('SYNTHETIC-hold-1:exact_single_insurance_item_required',run.payload['blockers']['calculation']['policies'])

    def test_global_equal_total_cannot_hide_group_date_or_amount_conflict(self):
        for mode in ('date','compensating_amounts','unknown_member','omit_group'):
            b=copy.deepcopy(self.book)
            if mode=='date':b['policies'][1]['installments'][0]['due_date']='2027-05-31'
            elif mode=='compensating_amounts':b['policies'][1]['installments'][0]['amount']=q(4);b['policies'][1]['installments'][1]['amount']=q(6)
            elif mode=='unknown_member':b['installment_groups'][0]['policy_installments'][0]['installment_id']='SYNTHETIC-unknown'
            else:b['installment_groups'].pop()
            run=reconcile_nominal_policy_book(self.plan,raw(b));self.assertIsNone(run.payload['totals']);self.assertTrue(all(r['sum']is None for r in run.payload['installment_groups']))

    def test_policy_coverage_fractions_basis_and_due_cannot_be_guessed(self):
        for mode in ('gap','overlap','fraction','basis','pre_service','source','premium'):
            b=copy.deepcopy(self.book)
            if mode=='gap':b['policies'][1]['coverage_start']='2027-04-02'
            elif mode=='overlap':b['policies'][1]['coverage_start']='2027-03-31'
            elif mode=='fraction':b['policies'][0]['allocations'][0]['fraction']=None
            elif mode=='basis':b['nominal_due_basis_ref']=None
            elif mode=='pre_service':b['policies'][0]['installments'][0]['due_date']='2026-12-31'
            elif mode=='source':b['policies'][0]['source_ref']=None
            else:b['policies'][0]['premium']=None
            p=reconcile_nominal_policy_book(self.plan,raw(b)).payload;self.assertIsNone(p['totals']);self.assertTrue(p['blockers'])

    def test_duplicate_members_sources_and_rental_period_rejected(self):
        b=copy.deepcopy(self.book);b['installment_groups'][1]['policy_installments'].append(b['installment_groups'][0]['policy_installments'][0])
        with self.assertRaises(ValidationError):parse_nominal_policy_book(raw(b))
        b=copy.deepcopy(self.book);b['policies'][1]['installments'][0]['source_ref']=b['policies'][0]['installments'][0]['source_ref']
        with self.assertRaises(ValidationError):parse_nominal_policy_book(raw(b))
        r=copy.deepcopy(self.rental);r['periods'].append(r['periods'][0])
        with self.assertRaises(ValidationError):parse_rental_binding(raw(r))

    def test_old_payment_window_profiles_are_not_reinterpreted(self):
        with self.assertRaises(ValidationError):parse_policy_book(raw(self.book))
        with self.assertRaises(ValidationError):parse_expense_schedule(self.plan)
        old=json.loads((ROOT/'templates/miniuw-v1-policy-renewal-case.json').read_bytes());self.assertEqual(parse_policy_book(old['policy_books_utf8'][0].encode())['payment_window_end'],'2027-07-01')

    def test_exact_arithmetic_budget_withholds_all_policy_totals(self):
        b=copy.deepcopy(self.book);seed=b['policies'][0];dates=['2027-01-01','2027-02-01','2027-03-01','2027-04-01','2027-05-01','2027-06-01','2027-07-01'];policies=[]
        for i in range(6):
            value=q(F(1,2**800+2*i+1));policy=copy.deepcopy(seed);policy.update(policy_id='SYNTHETIC-budget-'+str(i),coverage_start=dates[i],coverage_end=dates[i+1],premium=value)
            policy['allocations']=[dict(period_ref='SYNTHETIC-hold-1'if i<3 else'SYNTHETIC-hold-2',start_date=dates[i],end_date=dates[i+1],fraction=q(1),source_ref='SYNTHETIC-budget-allocation-'+str(i))]
            policy['installments']=[dict(installment_id='SYNTHETIC-budget-due-'+str(i),due_date=dates[i],amount=value,source_ref='SYNTHETIC-budget-source-'+str(i))];policies.append(policy)
        b['policies']=policies
        p=reconcile_nominal_policy_book(self.plan,raw(b)).payload
        self.assertIsNone(p['totals']);self.assertIn('exact_arithmetic_budget_exceeded',p['blockers'])

    def test_current_page_groups_all_gross_events_zero_and_annual_rows(self):
        report=render_phased_settled_output(self.source,self.result);m=report.manifest;reader=PdfReader(BytesIO(report.pdf_bytes));self.assertEqual(len(reader.pages),1);t=reader.pages[0].extract_text()
        for v in ('MINI-UW | RENTA, POLIZAS Y VENTA','Renta: 88 | polizas: 2','Aportes brutos','1400','778','-622','Resultado T110 SHA256','Capital declarado: Pendiente'):self.assertIn(v,t)
        self.assertEqual(sorted(i for r in m['event_groups']for i in r['event_indices']),list(range(8)));self.assertEqual(sum(r['zero_event_count']for r in m['event_groups']),3);self.assertEqual(m['annual_years'],[2026,2027])
        self.assertTrue(all(v['text']in t for v in m['display_spans']));self.assertEqual(self.result.payload['current_irr_evidence']['point_rate_selected'],False)

    def test_blocked_pages_do_not_display_old_financial_numbers(self):
        for label in ('blocked','expired','parent-expired'):
            source=fixture(label);run=assemble_phased_settled_output(source);self.assert_withheld(run);report=render_phased_settled_output(source,run);m=report.manifest
            self.assertTrue(m['all_current_money_withheld']);self.assertEqual(m['event_groups'],[]);self.assertEqual(m['annual_years'],[])
            self.assertIn('Renta: Pendiente | polizas: Pte',PdfReader(BytesIO(report.pdf_bytes)).pages[0].extract_text())

    def test_forged_result_even_rehashed_cannot_render(self):
        from miniuw_foundation.phased_settled_output import PhasedSettledRun
        p=self.result.payload;p['current_project_return_story']['gross_distributions']=q(900);value=canonical(p)
        with self.assertRaises(ValidationError):render_phased_settled_output(self.source,PhasedSettledRun(value,sha(value.encode())))

    def test_criteria_authority_and_personal_capital_remain_pending(self):
        p=self.result.payload;self.assertEqual(len(p['criterion_slots']),10);self.assertTrue(all(r['threshold']is None and r['state']=='PENDING'for r in p['criterion_slots']))
        for k in ('financial_model_complete','financial_publication_authorized','source_authority_verified','professional_review_authenticated','deployment_enabled','real_decisions_enabled','original_sheet_adapter_for_this_profile_implemented'):self.assertFalse(p[k])
        self.assertEqual(p['original_semantic_mappings_pending'],54);self.assertIsNone(p['personal_investor_return']);self.assertEqual(p['decision'],'PENDING')

    def test_current_and_blocked_source_first_directory_recovery(self):
        for label in ('current','blocked','expired'):
            run,report=recover_phased_settled_directory(ROOT/('docs/review/miniuw-v1-phased-settled-'+label+'-example'));self.assertEqual(run,assemble_phased_settled_output(fixture(label)))
            self.assertEqual(report.manifest['page_count_by_construction'],1)

    def test_directory_rehash_does_not_accept_forged_result_or_versions(self):
        for mode in ('result','version','inventory'):
            with tempfile.TemporaryDirectory()as td:
                target=Path(td)/'output';write_phased_settled_artifacts(self.source,target);p=json.loads((target/'package.json').read_bytes())
                if mode=='result':
                    r=json.loads((target/'current-results.json').read_bytes());r['current_project_return_story']['gross_distributions']=q(999);data=raw(r);(target/'current-results.json').write_bytes(data)
                    for entry in p['files']:
                        if entry['path']=='current-results.json':entry.update(sha256=sha(data),bytes=len(data))
                elif mode=='version':p['versions']['nominal_policy_engine']='0'*64
                else:p['files'][0]['path']='../escape'
                (target/'package.json').write_bytes(raw(p))
                with self.assertRaises(ValidationError):recover_phased_settled_directory(target)

    def test_safe_writer_retry_no_overwrite_symlink_and_own_temp_cleanup(self):
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'result';write_phased_settled_artifacts(self.source,target);before=read_phased_settled_artifacts(target)
            self.assertEqual(write_phased_settled_artifacts(self.source,target)['status'],'identical_existing_verified')
            with self.assertRaises(ValidationError):write_phased_settled_artifacts(fixture('twelve'),target)
            self.assertEqual(read_phased_settled_artifacts(target),before)
            link=Path(td)/'link';link.symlink_to(target,target_is_directory=True)
            with self.assertRaises(ValidationError):read_phased_settled_artifacts(link)
            with patch('miniuw_foundation.phased_settled_artifacts.os.rename',side_effect=OSError('synthetic rename failure')):
                with self.assertRaises(OSError):write_phased_settled_artifacts(self.source,Path(td)/'failure')
            self.assertFalse(any(p.name.startswith('.miniuw')for p in Path(td).iterdir()))


if __name__=='__main__':unittest.main()
