"""T1: exact capital recovery, peak and certified rates, with replay gates."""
from copy import deepcopy
from datetime import date
from fractions import Fraction as Q
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import (build_results,encoded,write_package,verify_package,read_package,
    deliver_package,read_case_source,CURRENT_REVISION_FILE)
from worksheet_return_summary_D273 import ledger_summary,baseline,SCHEMA,render
from worksheet_project_calendar_D145 import offset
from worksheet_revision_D128 import snapshot_for_case
from check_worksheet_irr_certificate_D270 import method_config
from check_worksheet_return_summary_D273 import fixture,capacity_fixture,independently_verify_summary


def value(x):return Q(x['numerator'])/Q(x['denominator'])


def cash(coefficients):
    dates=[str(offset(date(2027,1,1),3*i)) for i in range(len(coefficients))]
    events=[]
    for i,(day,flow) in enumerate(zip(dates,coefficients,strict=True)):
        for kind,amount in [('contribution',max(Q(),-Q(flow))),('distribution',max(Q(),Q(flow)))]:
            events.append(dict(event_id=f'{i}-{kind}',date=day,amount=rational(amount),kind=kind,
                currency='USD',source_ref='SYNTHETIC-D273-explicit-observed-event'))
    calls=sum(max(Q(),-Q(x)) for x in coefficients);receipts=sum(max(Q(),Q(x)) for x in coefficients)
    return dict(basis_amount=rational(100),scale_factor=rational(Q(1,10)),reference_amount=rational(10),
        basis_event_ids=['0-contribution'],events=events,total_contributions=rational(calls),
        total_distributions=rational(receipts),equity_multiple=rational(receipts/calls),
        unrecovered_after_sale=rational(max(Q(),calls-receipts))),dates


class ReturnSummaryTests(TestCase):
    def test_first_recovery_and_later_reversal_are_disclosed(self):
        c,d=cash([-10,15,-10]);r=ledger_summary(c,d,method_config())
        self.assertEqual(r['payback_date'],'2027-04-01')
        self.assertTrue(r['recovery_reversed_after_first_payback'])
        self.assertEqual(value(r['peak_equity']),10)
        self.assertEqual(value(r['project_peak_equity']),100)

    def test_not_recovered_is_null_with_reason_never_zero_date(self):
        c,d=cash([-10,0,5]);r=ledger_summary(c,d,method_config())
        self.assertIsNone(r['payback_date'])
        self.assertEqual(r['payback_reason'],'capital no recuperado en el horizonte')
        self.assertEqual(r['peak_dates'],['2027-01-01','2027-04-01'])
        self.assertEqual(value(r['peak_equity']),10)

    def test_multiple_IRR_does_not_hide_observed_recovery_or_choose_a_rate(self):
        c,d=cash([-10,25,-10]);r=ledger_summary(c,d,method_config())
        self.assertIsNone(r['irr_annual']['annual_enclosure'])
        self.assertEqual(r['irr_annual']['reason'],'PENDING · raíz no probada')
        self.assertEqual(r['payback_date'],'2027-04-01')

    def test_exact_zero_IRR_is_a_proven_zero_not_an_empty(self):
        c,d=cash([-10,0,10]);r=ledger_summary(c,d,method_config())
        self.assertEqual(value(r['irr_annual']['annual_enclosure']['lower']),0)
        self.assertEqual(value(r['irr_annual']['annual_enclosure']['upper']),0)
        self.assertEqual(r['payback_date'],'2027-07-01')

    def test_valid_large_rationals_keep_cash_exact_and_excess_precision_is_PENDING(self):
        precise=Q(15*10**300+1,10**300)
        c,d=cash([-10,0,precise]);r=ledger_summary(c,d,method_config())
        self.assertFalse(r['blockers'])
        self.assertEqual(r['payback_date'],'2027-07-01')
        self.assertEqual(value(r['peak_equity']),10)
        c['events'][-1]['amount']=rational(Q(10**1400+1,10**1400))
        blocked=ledger_summary(c,d,method_config())
        self.assertIsNone(blocked['peak_equity']);self.assertIsNone(blocked['payback_date'])
        self.assertEqual(blocked['state'],'PENDING')

    def test_year_outside_a_verified_route_is_not_reported_as_zero(self):
        from pypdf import PdfReader
        from io import BytesIO
        short,sd=cash([-10,0,15]);long,ld=cash([-10,0,0,0,0,0,0,0,15])
        result=dict(scenarios={},return_summary=dict(scenarios={}))
        for name,c,dates in [('Base',short,sd),('Downside',long,ld)]:
            result['scenarios'][name]=dict(cash_per_usd_10=c,horizon_without_refinance=dict(cash_per_usd_10=c),
                project_calendar=dict(purchase_date=dates[0],stabilization_date=dates[1],sale_date=dates[-1]))
            summary=ledger_summary(c,dates,method_config())
            result['return_summary']['scenarios'][name]=dict(with_refinance=summary,without_refinance=summary)
        text=PdfReader(BytesIO(render(result))).pages[0].extract_text()
        self.assertIn('Fuera de horizonte',text)
        self.assertEqual(text.count('Fuera de horizonte'),4)

    def test_missing_amount_date_basis_and_source_do_not_become_zero(self):
        original,dates=cash([-10,0,15])
        for fault in ('amount','date','source','basis','event_id','total'):
            c=deepcopy(original)
            if fault=='amount':c['events'][2]['amount']=None
            elif fault=='date':c['events']=[e for e in c['events'] if e['date']!=dates[1]]
            elif fault=='source':c['events'][0]['source_ref']=' '
            elif fault=='basis':c['basis_amount']=None
            elif fault=='event_id':c['events'][0]['event_id']=c['events'][1]['event_id']
            else:c['total_contributions']=rational(0)
            with self.subTest(fault=fault):
                r=ledger_summary(c,dates,method_config());self.assertEqual(r['state'],'PENDING')
                self.assertIsNone(r['peak_equity']);self.assertIsNone(r['payback_date'])

    def test_invalid_certificate_only_withholds_the_rate(self):
        c,d=cash([-10,15]);r=ledger_summary(c,d,None)
        self.assertIsNone(r['irr_annual']['annual_enclosure'])
        self.assertEqual(value(r['peak_equity']),10)
        self.assertEqual(r['payback_date'],'2027-04-01')

    def test_no_missing_quarter_can_be_hidden_by_removing_dates_too(self):
        c,d=cash([-10,0,15]);c['events']=[e for e in c['events'] if e['date']!=d[1]]
        d=[d[0],d[-1]];r=ledger_summary(c,d,method_config())
        self.assertIsNone(r['irr_annual']['annual_enclosure'])
        self.assertIsNone(r['payback_date'])
        self.assertIsNone(r['peak_equity'])

    def test_unknown_currency_and_negative_gross_are_blocked(self):
        for key,bad in [('currency','EUR'),('amount',rational(-1))]:
            c,d=cash([-10,15]);c['events'][0][key]=bad
            self.assertEqual(ledger_summary(c,d,method_config())['state'],'PENDING')

    def test_same_date_gross_calls_are_not_assigned_an_invented_intraday_order(self):
        c,d=cash([-10,5,0])
        for kind in ('contribution','distribution'):
            c['events'].append(dict(event_id='same-day-'+kind,date=d[1],amount=rational(20),
                kind=kind,currency='USD',source_ref='SYNTHETIC-D273-same-date-observation'))
        c.update(total_contributions=rational(30),total_distributions=rational(25),
                 equity_multiple=rational(Q(5,6)),unrecovered_after_sale=rational(5))
        first=ledger_summary(c,d,method_config())
        c['events'].reverse();second=ledger_summary(c,d,method_config())
        self.assertEqual(value(first['peak_equity']),10)
        self.assertEqual(first['peak_equity'],second['peak_equity'])
        self.assertEqual(first['payback_date'],second['payback_date'])

    def test_only_v36_uses_extended_source_bound_and_nested_profiles_are_rejected(self):
        self.assertEqual(read_case_source(encoded(dict(schema=SCHEMA,padding='x'*100_000)))['schema'],SCHEMA)
        with self.assertRaises(ValueError):read_case_source(encoded(dict(schema=SCHEMA,padding='x'*262_144)))
        with self.assertRaises(ValueError):baseline(dict(schema=SCHEMA,baseline_case=dict(schema=SCHEMA),return_summary={}))


class ReturnSummaryIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(prefix='miniuw-d273-summary-');cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        cls.case,cls.current,cls.sources=fixture(cls.root/'sources')
        cls.result,cls.pdf=build_results(encoded(cls.case),current_revision_raw=cls.current,**cls.sources)

    def test_all_four_routes_reconcile_from_literal_sources(self):
        proof=independently_verify_summary(self.case['baseline_case'],self.sources,self.result)
        self.assertEqual(set(proof),{'Base','Downside'})
        for name in proof:
            self.assertEqual(set(proof[name]['return_summary_from_sources']),{'with_refinance','without_refinance'})
            for row in self.result['return_summary']['scenarios'][name].values():
                self.assertIsNotNone(row['irr_annual']['annual_enclosure'])
                self.assertFalse(row['blockers'])
        self.assertEqual(self.result['decision'],'PENDING')

    def test_financial_results_and_gross_cash_are_unchanged_from_base(self):
        base=self.case['baseline_case'];cur=encoded(snapshot_for_case(base,'SYNTHETIC-D273-summary-current'))
        prior,_=build_results(encoded(base),current_revision_raw=cur,**self.sources)
        self.assertEqual(prior['scenarios'],self.result['scenarios'])
        self.assertEqual(prior['screening'],self.result['screening'])
        self.assertEqual(self.result['pipeline']['case_sha256'],sha(encoded(self.case)))
        self.assertEqual(self.result['pipeline']['case_sha256'],self.result['case_sha256'])
        self.assertEqual(self.result['baseline_case_sha256'],prior['case_sha256'])

    def test_stale_summary_definition_blocks_current_cash_and_delivery(self):
        changed=deepcopy(self.case);changed['return_summary']['source_ref']='SYNTHETIC-D273-another-definition'
        result,_=build_results(encoded(changed),current_revision_raw=self.current,**self.sources)
        self.assertTrue(result['revision_review']['blockers'])
        self.assertTrue(all(v['cash_per_usd_10'] is None for v in result['scenarios'].values()))

    def test_source_first_package_rejects_changed_result_and_stale_revision(self):
        path=self.root/'audited'
        write_package(encoded(self.case),path,current_revision_raw=self.current,**self.sources)
        self.assertEqual(verify_package(path,current_revision_raw=self.current)['vigencia'],'VIGENTE')
        snapshot=json.loads(self.current);snapshot['revision']='SYNTHETIC-D273-superseding-revision'
        self.assertEqual(verify_package(path,current_revision_raw=encoded(snapshot))['vigencia'],'HISTORICO')
        saved=read_package(path);changed=json.loads(saved['results.json']);changed['return_summary']['scenarios']['Base']['with_refinance']['peak_equity']=rational(0)
        (path/'results.json').write_bytes(encoded(changed))
        with self.assertRaises(ValueError):verify_package(path,current_revision_raw=self.current)

    def test_visible_pdf_has_IRR_payback_peak_and_no_simulated_verdict(self):
        from pypdf import PdfReader
        from io import BytesIO
        pdf=PdfReader(BytesIO(self.pdf));self.assertEqual(len(pdf.pages),1)
        text=pdf.pages[0].extract_text()
        for s in ['TIR anual certificada','Fecha de primer recupero','Pico de equity por fecha',
                  'Aporte inicial','Aportes adicionales','Criterios por confirmar']:
            self.assertIn(s,text)
        self.assertNotIn('PASS',text);self.assertNotIn('FAIL',text)
        stages=[stage for stage in self.result['pipeline']['stages'] if 'B15' in stage.get('bots',[])]
        self.assertEqual(len(stages),1)
        self.assertEqual(stages[0]['pdf_sha256'],sha(self.pdf))
        self.assertEqual(stages[0]['pdf_sha256'],self.result['pdf_sha256'])
        self.assertEqual(stages[0]['pages'],1)

    def test_sourced_capacity_block_retains_no_refi_cash_and_delivers_the_current_summary(self):
        from check_worksheet_scenario_program_D268 import independently_verify
        from pypdf import PdfReader
        case,current,sources=capacity_fixture(self.root/'capacity-sources')
        path=self.root/'capacity-package'
        write_package(encoded(case),path,current_revision_raw=current,**sources)
        saved=read_package(path);result=json.loads(saved['results.json'])
        self.assertEqual(result['critical_evidence_review']['status'],'PASSED')
        self.assertEqual(result['scenarios']['Downside']['blockers'],['selected_principal_exceeds_declared_bank_capacity'])
        self.assertIsNone(result['scenarios']['Downside']['cash_per_usd_10'])
        self.assertIsNotNone(result['scenarios']['Downside']['horizon_without_refinance']['cash_per_usd_10'])
        self.assertIsNone(result['return_summary']['scenarios']['Downside']['with_refinance']['peak_equity'])
        self.assertIsNotNone(result['return_summary']['scenarios']['Downside']['without_refinance']['peak_equity'])
        self.assertEqual(set(independently_verify(case['baseline_case'],sources,result)),{'Base','Downside'})
        self.assertEqual(verify_package(path,current_revision_raw=current)['vigencia'],'VIGENTE')
        (self.root/'capacity-current.json').write_bytes(current)
        destination=self.root/'capacity-current.pdf'
        deliver_package(path,destination,self.root/'capacity-current.json')
        self.assertEqual(destination.read_bytes(),saved['MiniUW_Resumen.pdf'])
        self.assertEqual(len(PdfReader(destination).pages),1)
