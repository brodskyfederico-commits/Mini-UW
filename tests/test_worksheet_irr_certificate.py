"""Exact IRR inventories, gross-cash completeness and the worksheet gates."""
from copy import deepcopy
from datetime import date
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

from check_worksheet_irr_certificate_D270 import method_config,source_base,source_case,certified_sources,execute
from check_worksheet_scenario_program_D268 import reference,independently_verify
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import encoded,build_results,read_case_source
from worksheet_intake_D198 import register,prepare
from worksheet_project_calendar_D145 import offset
from worksheet_irr_certificate_D270 import verify_cash,positive_inventory
import worksheet_irr_certificate_D270 as kernel


def amount(raw):return Q(raw['numerator'])/Q(raw['denominator'])


def cash_fixture(coefficients):
    dates=[str(offset(date(2027,1,1),3*i)) for i in range(len(coefficients))]
    events=[]
    for i,(day,value) in enumerate(zip(dates,coefficients,strict=True)):
        for kind,number in [('contribution',max(Q(),-Q(value))),('distribution',max(Q(),Q(value)))]:
            events.append(dict(date=day,kind=kind,currency='USD',amount=rational(number),event_id=f'event-{i}-{kind}'))
    return dict(events=events),dates


class ExactIRRCertificateTests(TestCase):
    def verified(self,coefficients):
        cash,dates=cash_fixture(coefficients)
        return verify_cash(cash,dates,method_config())

    def test_unique_positive_rate_is_bounded_and_endpoint_signs_match_separate_NPV(self):
        coefficients=[-10,15]
        result=self.verified(coefficients)
        self.assertEqual(result['state'],'checked_synthetic')
        enclosure=result['annual_enclosure']
        self.assertLessEqual(amount(enclosure['lower']),Q(65,16))
        self.assertGreaterEqual(amount(enclosure['upper']),Q(65,16))
        check=result['endpoint_check']
        for field,sign in [('lower_discount',-1),('upper_discount',1)]:
            x=amount(check[field]);npv=sum(Q(c)*x**i for i,c in enumerate(coefficients))
            self.assertGreaterEqual(npv*sign,0)
        self.assertEqual(result['complete_root_inventory']['positive_roots'],1)

    def test_negative_IRR_is_not_clamped_and_exact_zero_is_not_missing(self):
        negative=self.verified([-10,5])
        self.assertEqual(amount(negative['annual_enclosure']['lower']),Q(-15,16))
        self.assertEqual(amount(negative['annual_enclosure']['upper']),Q(-15,16))
        zero=self.verified([-10,20,-10])
        self.assertEqual(zero['state'],'checked_synthetic')
        self.assertEqual(zero['complete_root_inventory']['positive_roots'],1)
        self.assertEqual(amount(zero['annual_enclosure']['lower']),0)
        self.assertEqual(amount(zero['annual_enclosure']['upper']),0)

    def test_two_and_three_admissible_roots_do_not_select_the_favorable_IRR(self):
        for coefficients,count in [([-100,250,-100],2),([-100,350,-350,100],3)]:
            result=self.verified(coefficients)
            self.assertEqual(result['state'],'PENDING')
            self.assertIsNone(result['annual_enclosure'])
            self.assertEqual(result['complete_root_inventory']['positive_roots'],count)
        # Two roots on the same side require more than this sufficient proof;
        # the existing isolator still cannot select one of them.
        result=self.verified([-100,230,-132])
        self.assertEqual(result['state'],'PENDING')
        self.assertIsNone(result['annual_enclosure'])

    def test_no_root_and_infinite_roots_are_not_reported_as_zero_return(self):
        for coefficients in ([10,10],[-10,-10],[0,0,0]):
            result=self.verified(coefficients)
            self.assertEqual(result['state'],'PENDING')
            self.assertIsNone(result['annual_enclosure'])

    def test_missing_cash_date_or_amount_is_not_an_implicit_zero(self):
        cash,dates=cash_fixture([-10,0,15])
        present=verify_cash(cash,dates,method_config())
        self.assertEqual(present['state'],'checked_synthetic')
        missing=deepcopy(cash);missing['events']=[e for e in missing['events'] if e['date']!=dates[1]]
        result=verify_cash(missing,dates,method_config())
        self.assertIsNone(result['annual_enclosure'])
        self.assertIn('IRR_certificate_missing_cash_date_not_zero',result['blockers'])
        for blank in (None,'',' ',False):
            changed=deepcopy(cash);changed['events'][0]['amount']=blank
            self.assertEqual(verify_cash(changed,dates,method_config())['state'],'PENDING')

    def test_invalid_kind_currency_grid_or_configuration_cannot_fall_back_silently(self):
        cash,dates=cash_fixture([-10,15])
        for key,value in [('kind','unknown'),('currency','EUR')]:
            changed=deepcopy(cash);changed['events'][0][key]=value
            self.assertIsNone(verify_cash(changed,dates,method_config())['annual_enclosure'])
        shifted=deepcopy(cash);shifted['events'][-1]['date']='2027-05-01'
        shifted['events'][-2]['date']='2027-05-01'
        self.assertEqual(verify_cash(shifted,['2027-01-01','2027-05-01'],method_config())['state'],'PENDING')
        for config in (None,{},method_config()|dict(algorithm_sha256='0'*64),method_config()|dict(source_ref='')):
            self.assertIsNone(verify_cash(cash,dates,config)['annual_enclosure'])
        self.assertIsNone(verify_cash(cash,{},method_config())['annual_enclosure'])

    def test_budget_exhaustion_and_mutated_runtime_definition_remain_pending(self):
        result=self.verified([-(1<<5000),1])
        self.assertEqual(result['state'],'PENDING')
        cash,dates=cash_fixture([-10,15]);config=method_config()
        original=deepcopy(kernel.RULES)
        try:
            kernel.RULES['bisection_steps']=0
            self.assertEqual(verify_cash(cash,dates,config)['state'],'PENDING')
        finally:
            kernel.RULES.clear();kernel.RULES.update(original)
        with patch.object(kernel.Path,'read_bytes',return_value=b'changed code on disk'):
            self.assertEqual(verify_cash(cash,dates,config)['state'],'PENDING')

    def test_positive_cash_scaling_does_not_change_the_rate(self):
        original=self.verified([-10,0,15])
        scaled=self.verified([Q(-1,100),0,Q(15,1000)])
        self.assertEqual(original['annual_enclosure'],scaled['annual_enclosure'])

    def test_larger_definition_payload_requires_the_explicit_profile_and_remains_bounded(self):
        case=dict(schema='miniuw.synthetic-native-rental-inputs.v34',rent_inputs=dict(irr_certificate=None),padding='x'*60_000)
        self.assertEqual(read_case_source(encoded(case))['schema'],case['schema'])
        for changed in (case|dict(rent_inputs={}),case|dict(schema='miniuw.synthetic-native-rental-inputs.v33'),
                        case|dict(padding='x'*100_000)):
            with self.assertRaises(ValueError):read_case_source(encoded(changed))


class IRRCertificateWorksheetTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(prefix='miniuw-d270-integration-');cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name)
        base,parent=source_base(root)
        original,sources=source_case(base,parent,'18',root/'source')
        cls.spec,cls.sources=certified_sources(original,sources)
        cls.result,cls.saved,cls.audit=execute(cls.spec,cls.sources,root/'current','SYNTHETIC-D270-unit')

    def variant(self,spec,sources,revision):
        raw,current=prepare(spec,register(sources,revision))
        return build_results(raw,current_revision_raw=current,**sources)[0]

    def test_new_numerical_method_closes_the_pending_IRR_and_reconciles_all_financial_cash(self):
        irr=self.result['screening']['irr_by_scenario']['Downside']
        self.assertEqual(irr['state'],'checked_synthetic')
        self.assertEqual(irr['complete_root_inventory']['positive_roots'],1)
        independently_verify(self.spec,self.sources,self.result)
        self.assertEqual(self.result['decision'],'PENDING')
        self.assertFalse(self.result['real_decisions_enabled'])

    def test_missing_criterion_remains_pending_despite_a_computed_IRR(self):
        sources=self.sources|dict(criteria_raw=None)
        result=self.variant(self.spec,sources,'SYNTHETIC-D270-missing-criterion')
        self.assertEqual(result['decision'],'PENDING')
        self.assertEqual(result['simulation_result'],'PENDING')
        self.assertTrue(result['screening']['simulation_blockers'])

    def test_missing_numerical_definition_is_not_an_old_method_or_zero_default(self):
        spec=deepcopy(self.spec);spec['rent_inputs']['irr_certificate']=None
        sources=dict(self.sources)
        sources['independent_reference_raw']=encoded(reference(spec,{k:v for k,v in sources.items() if k!='independent_reference_raw'}))
        result=self.variant(spec,sources,'SYNTHETIC-D270-missing-definition')
        self.assertEqual(result['simulation_result'],'PENDING')
        for name in ('Base','Downside'):
            self.assertIsNone(result['screening']['irr_by_scenario'][name]['annual_enclosure'])
            self.assertEqual(result['scenarios'][name]['cash_per_usd_10'],self.result['scenarios'][name]['cash_per_usd_10'])

    def test_complete_math_cannot_override_missing_critical_evidence(self):
        ref=json.loads(self.sources['independent_reference_raw'])
        del ref['bank']['Downside']['permanent']['terms']['minimum_dscr']
        result=self.variant(self.spec,self.sources|dict(independent_reference_raw=encoded(ref)),
                            'SYNTHETIC-D270-missing-DSCR-reference')
        self.assertEqual(result['critical_evidence_review']['status'],'PENDING')
        for name in ('Base','Downside'):
            self.assertIsNone(result['scenarios'][name]['cash_per_usd_10'])
            self.assertIsNone(result['screening']['irr_by_scenario'][name]['annual_enclosure'])

