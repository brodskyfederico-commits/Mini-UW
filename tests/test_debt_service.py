from dataclasses import replace
from fractions import Fraction
import hashlib,json,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from miniuw_foundation import DraftStore,ValidationError
from miniuw_foundation.archive import EvidenceArchive,archive_and_import,CorruptArchive,UnsupportedArchive,MissingEvidence
from miniuw_foundation.debt_service import produce_debt_service,parse_loan_terms,DateWindow,_fraction
from miniuw_foundation.debt_dscr import DebtDscrBinding,calculate_debt_dscr
from miniuw_foundation.normalization import NumericProfile,normalize_synthetic
from miniuw_foundation.calculations import CalculationGraph,CalculationNode,Operand,calculate_synthetic
from miniuw_foundation.drafts import canonical,digest
from loan_fixture import loan_source
from test_foundation import seed
from miniuw_foundation.intake import SCHEMA


def windows():
    return (DateWindow(window_id='maturity',start_date='2027-08-01',end_date='2027-09-01',boundary='start_inclusive_end_exclusive'),
        DateWindow(window_id='first_two',start_date='2027-06-01',end_date='2027-08-01',boundary='start_inclusive_end_exclusive'))


class DebtServiceTests(unittest.TestCase):
    def test_zero_rate_payment_and_maturity_balloon_are_distinct(self):
        p=produce_debt_service(loan_source(),windows()).payload
        self.assertEqual(_fraction(p['regular_payment_due']),100)
        self.assertEqual(len(p['schedule']),3)
        self.assertEqual(_fraction(p['schedule'][-1]['closing_balance']),900)
        self.assertEqual(_fraction(p['schedule'][-1]['balloon_due']),900)
        self.assertEqual(_fraction(p['schedule'][-1]['scheduled_plus_balloon_due']),1000)
        self.assertFalse(p['payoff_verified']);self.assertFalse(p['cash_paid_verified'])

    def test_positive_rate_payment_matches_independent_present_value_and_recurrence(self):
        raw=loan_source(periodic_rate={'numerator':'1','denominator':'100'},amortization_payments=6,maturity_payment=3)
        p=produce_debt_service(raw,()).payload;a=_fraction(p['payment_per_unit']);rate=Fraction(1,100)
        self.assertEqual(sum(a/(1+rate)**k for k in range(1,7)),1)
        balance=Fraction(1200);payment=_fraction(p['regular_payment_due'])
        for row in p['schedule']:
            self.assertEqual(_fraction(row['opening_balance']),balance)
            self.assertEqual(_fraction(row['interest_due']),balance*rate)
            balance=balance*(1+rate)-payment
            self.assertEqual(_fraction(row['closing_balance']),balance)
            self.assertEqual(_fraction(row['principal_due'])+_fraction(row['interest_due']),payment)

    def test_full_amortization_has_no_balloon(self):
        raw=loan_source(amortization_payments=3,maturity_payment=3,periodic_rate={'numerator':'1','denominator':'10'})
        p=produce_debt_service(raw,()).payload
        self.assertEqual(_fraction(p['schedule'][-1]['balloon_due']),0)
        self.assertEqual(_fraction(p['schedule'][-1]['closing_balance']),0)

    def test_annual_sizing_is_not_a_dated_partial_year(self):
        p=produce_debt_service(loan_source(),windows()).payload
        self.assertEqual(_fraction(p['annual_sizing']['amount']),1200)
        self.assertEqual(_fraction(p['dated_windows']['first_two']['scheduled_service_due']),200)
        self.assertEqual(_fraction(p['dated_windows']['maturity']['scheduled_service_due']),100)
        self.assertEqual(_fraction(p['dated_windows']['maturity']['balloon_due']),900)
        self.assertFalse(p['calendar_interval_consistency_verified'])

    def test_half_open_window_boundaries_and_empty_known_window(self):
        w=(DateWindow(window_id='one',start_date='2027-06-30',end_date='2027-07-31',boundary='start_inclusive_end_exclusive'),
            DateWindow(window_id='empty',start_date='2027-09-01',end_date='2027-10-01',boundary='start_inclusive_end_exclusive'))
        p=produce_debt_service(loan_source(),w).payload['dated_windows']
        self.assertEqual(p['one']['payment_indices'],[1])
        self.assertEqual(_fraction(p['empty']['scheduled_service_due']),0)
        self.assertEqual(p['empty']['state'],'computed_synthetic')

    def test_missing_dates_block_dated_windows_without_inventing_calendar(self):
        p=produce_debt_service(loan_source(payment_dates=None,origination_date=None),windows()).payload
        self.assertEqual(p['schedule_state'],'computed_synthetic')
        self.assertEqual(p['annual_sizing']['state'],'computed_synthetic')
        self.assertEqual(p['dated_windows']['maturity']['state'],'blocked')
        self.assertTrue(all(row['date'] is None for row in p['schedule']))

    def test_frequency_missing_blocks_only_annual_sizing(self):
        p=produce_debt_service(loan_source(payments_per_year=None),windows()).payload
        self.assertEqual(p['annual_sizing']['state'],'blocked')
        self.assertEqual(p['dated_windows']['maturity']['state'],'computed_synthetic')

    def test_missing_maturity_does_not_extend_amortization_to_a_contract_date(self):
        p=produce_debt_service(loan_source(maturity_payment=None,payment_dates=None),()).payload
        self.assertEqual(p['annual_sizing']['state'],'computed_synthetic')
        self.assertEqual(p['schedule'],[])
        self.assertIn('maturity_count_missing_no_extension_inferred',p['schedule_blockers'])

    def test_missing_amount_or_rate_never_defaults_to_zero(self):
        for key in ('principal','periodic_rate'):
            p=produce_debt_service(loan_source(**{key:None}),windows()).payload
            self.assertEqual(p['state'],'blocked');self.assertIsNone(p['regular_payment_due'])
            self.assertEqual(p['dated_windows']['maturity']['state'],'blocked')

    def test_explicit_zero_principal_is_known_zero_service(self):
        p=produce_debt_service(loan_source(principal={'numerator':'0','denominator':'1'}),windows()).payload
        self.assertEqual(_fraction(p['regular_payment_due']),0)
        self.assertEqual(p['state'],'computed_synthetic')

    def test_unsupported_profile_assumptions_and_annual_rate_are_rejected(self):
        for changes in [dict(rate_basis='nominal_annual'),dict(payment_timing='advance'),dict(fixed_rate=False),
            dict(new_draws=True),dict(capitalized_fees=True),dict(interest_only=True),dict(rounding='cents'),dict(regular_intervals_assumed=False)]:
            with self.assertRaises(ValidationError):produce_debt_service(loan_source(**changes),())

    def test_negative_rates_principal_and_invalid_counts_block_without_fail(self):
        for changes in [dict(principal={'numerator':'-1','denominator':'1'}),dict(periodic_rate={'numerator':'-1','denominator':'10'}),dict(amortization_payments=0)]:
            p=produce_debt_service(loan_source(**changes),()).payload
            self.assertEqual(p['state'],'blocked');self.assertEqual(p['decision'],'PENDING')
        p=produce_debt_service(loan_source(maturity_payment=13,payment_dates=None),()).payload
        self.assertEqual(p['schedule_state'],'blocked')

    def test_dates_must_be_explicit_ordered_unique_and_after_origination(self):
        for dates in [['2027-02-30'],['2027-07-31','2027-06-30'],['2027-06-30']*3,['2027-06-01']]:
            with self.assertRaises(ValidationError):produce_debt_service(loan_source(payment_dates=dates),())
        p=produce_debt_service(loan_source(payment_dates=['2027-06-30']),windows()).payload
        self.assertEqual(p['dated_windows']['first_two']['state'],'blocked')

    def test_technical_budget_exhaustion_blocks_instead_of_approximating(self):
        for raw in [loan_source(amortization_payments=601),loan_source(amortization_payments=600,periodic_rate={'numerator':'1','denominator':str(10**100)})]:
            p=produce_debt_service(raw,()).payload
            self.assertEqual(p['state'],'blocked');self.assertIsNone(p['regular_payment_due'])

    def test_windows_are_explicit_immutable_and_not_automatically_aggregated(self):
        with self.assertRaises(ValidationError):DateWindow(window_id='x',start_date='2027-01-01',end_date='2027-01-01',boundary='start_inclusive_end_exclusive')
        with self.assertRaises(ValidationError):produce_debt_service(loan_source(),[windows()[0]])
        with self.assertRaises(ValidationError):produce_debt_service(loan_source(),(windows()[0],windows()[0]))
        self.assertEqual(produce_debt_service(loan_source(),windows()),produce_debt_service(loan_source(),tuple(reversed(windows()))))

    def test_raw_term_types_and_schema_are_explicit(self):
        for raw in [b'{}',loan_source(payments_per_year=True),loan_source(principal={'numerator':1200,'denominator':'1'}),loan_source(principal={'numerator':'1','denominator':'0'})]:
            with self.assertRaises(ValidationError):parse_loan_terms(raw)

    def test_archive_reopen_recovers_exact_typed_loan_source_and_schedule(self):
        raw=loan_source();run=produce_debt_service(raw,windows())
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'debt.sqlite3'
            with EvidenceArchive(path) as archive:
                key=archive.save_debt_service(raw,windows(),run)
                self.assertEqual(key,archive.save_debt_service(raw,windows(),run))
            with EvidenceArchive(path) as archive:
                bundle=archive.load_debt_service(key)
                self.assertEqual(bundle.run,run)
                self.assertEqual(archive.get_loan_source(hashlib.sha256(raw).hexdigest()),raw)

    def test_debt_archive_detects_forgery_version_change_and_atomic_failure(self):
        raw=loan_source();run=produce_debt_service(raw,windows())
        with EvidenceArchive(':memory:') as archive:
            with patch.object(archive,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):archive.save_debt_service(raw,windows(),run)
            self.assertEqual(archive._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=archive.save_debt_service(raw,windows(),run)
            p=json.loads(archive.read_bundle_bytes(key));p['engine_sha256']='0'*64
            with archive._transaction():altered=archive._put('bundle',canonical(p).encode())
            with self.assertRaises(UnsupportedArchive):archive.load_debt_service(altered)
            p=json.loads(archive.read_bundle_bytes(key));value=json.loads(p['run']['payload_json']);value['regular_payment_due']['numerator']='99';encoded=canonical(value)
            p['run']={'payload_json':encoded,'sha256':digest(encoded)}
            with archive._transaction():altered=archive._put('bundle',canonical(p).encode())
            with self.assertRaises(CorruptArchive):archive.load_debt_service(altered)


class ComputedDebtDscrTests(unittest.TestCase):
    def setUp(self):
        self.store=DraftStore(':memory:');self.addCleanup(self.store.close)
        self.archive=EvidenceArchive(':memory:');self.addCleanup(self.archive.close)
        blank=self.store.create('noi',seed());self.slot=list(blank.payload['input_claims'])[1]
        self.loan=loan_source();self.windows=windows();self.debt=produce_debt_service(self.loan,self.windows)

    def case(self,mode='dated_contractual_due',include=False,noi='300',currency='USD',period=None):
        period=period or ('maturity' if mode=='dated_contractual_due' else 'SYNTHETIC-annual-equivalent-1')
        unit='currency/declared-period' if mode=='dated_contractual_due' else 'currency/annual-sizing-equivalent'
        source={'schema':SCHEMA,'claims':[{'claim_id':'noi','slot_kind':'input','slot_id':self.slot,'literal':noi,'unit_literal':unit,'currency_literal':currency,'period_literal':period,'definition_ref':'SYNTHETIC-declared-NOI'}]}
        raw=json.dumps(source).encode()
        self.store.create('case-'+mode+str(include)+str(noi)+currency+period,seed());identity='case-'+mode+str(include)+str(noi)+currency+period
        snapshot=archive_and_import(self.archive,self.store,identity,expected_revision=0,operation_id='source',raw=raw).snapshot
        profile=NumericProfile(profile_id='SYNTHETIC-noi',definition_revision='v1',slot_id=self.slot,source_definition_ref='SYNTHETIC-declared-NOI',decimal_mark='.',notation='decimal',trim_outer_whitespace=False,source_unit_literal=unit,target_unit=unit,quantity_kind='money_per_period',currency_literal=currency,period_literal=period)
        profiles=(profile,);numeric=normalize_synthetic(snapshot,profiles)
        graph=CalculationGraph(graph_id='SYNTHETIC-noi',definition_revision='v1',nodes=(CalculationNode(node_id='noi',definition_revision='SYNTHETIC-declared-NOI',operation='identity',operands=(Operand(kind='input',ref=self.slot),)),))
        upstream=calculate_synthetic(snapshot,profiles,numeric,graph)
        binding=DebtDscrBinding(profile_id='SYNTHETIC-COMPUTED-SERVICE-DSCR-v1',definition_revision='v1',noi_node='noi',noi_producer_revision='SYNTHETIC-declared-NOI',noi_basis_ref='SYNTHETIC-provided-NOI-only',loan_source_sha256=hashlib.sha256(self.loan).hexdigest(),service_basis_ref='SYNTHETIC-modeled-due',service_mode=mode,window_id='maturity' if mode=='dated_contractual_due' else None,include_balloon=include,currency=currency,period_ref=period)
        return snapshot,profiles,numeric,graph,upstream,self.loan,self.windows,self.debt,binding

    def test_computed_service_used_with_explicit_balloon_choice(self):
        ordinary=calculate_debt_dscr(*self.case());gross=calculate_debt_dscr(*self.case(include=True))
        self.assertEqual(_fraction(ordinary.payload['rational']),3)
        self.assertEqual(_fraction(gross.payload['rational']),Fraction(3,10))
        self.assertNotEqual(ordinary.payload['interpretation_label'],gross.payload['interpretation_label'])
        self.assertFalse(gross.payload['cash_paid_verified']);self.assertEqual(gross.payload['decision'],'PENDING')

    def test_annual_sizing_service_not_dated_window_or_balloon(self):
        case=self.case(mode='annual_sizing_equivalent',noi='2400');run=calculate_debt_dscr(*case)
        self.assertEqual(_fraction(run.payload['rational']),2)
        with self.assertRaises(ValidationError):replace(case[-1],include_balloon=True)
        with self.assertRaises(ValidationError):replace(case[-1],window_id='maturity')

    def test_missing_noi_currency_period_and_loan_context_block(self):
        run=calculate_debt_dscr(*self.case(noi=None));self.assertIsNone(run.payload['rational'])
        run=calculate_debt_dscr(*self.case(currency='EUR'));self.assertIn('loan_currency_mismatch',run.payload['blockers'])
        run=calculate_debt_dscr(*self.case(period='other'));self.assertIn('dated_window_period_identity_mismatch',run.payload['blockers'])
        case=list(self.case(noi='301'));terms=json.loads(self.loan);terms['context']['scenario_id']='other';case[5]=json.dumps(terms).encode();case[7]=produce_debt_service(case[5],self.windows);case[-1]=replace(case[-1],loan_source_sha256=hashlib.sha256(case[5]).hexdigest())
        self.assertIn('loan_and_noi_context_mismatch',calculate_debt_dscr(*case).payload['blockers'])

    def test_zero_loan_service_never_produces_infinite_dscr(self):
        case=list(self.case());case[5]=loan_source(principal={'numerator':'0','denominator':'1'});case[7]=produce_debt_service(case[5],self.windows);case[-1]=replace(case[-1],loan_source_sha256=hashlib.sha256(case[5]).hexdigest())
        run=calculate_debt_dscr(*case);self.assertIsNone(run.payload['rational']);self.assertIn('positive_computed_service_required',run.payload['blockers'])

    def test_forged_debt_or_wrong_loan_identity_rejected(self):
        case=list(self.case());case[-1]=replace(case[-1],loan_source_sha256='0'*64)
        self.assertIn('loan_source_identity_mismatch',calculate_debt_dscr(*case).payload['blockers'])
        case=list(self.case(noi='302'));p=case[7].payload;p['regular_payment_due']['numerator']='99';encoded=canonical(p);case[7]=replace(case[7],payload_json=encoded,sha256=digest(encoded))
        with self.assertRaises(ValidationError):calculate_debt_dscr(*case)

    def test_full_bridge_archive_replays_and_keeps_noi_unverified(self):
        case=self.case();run=calculate_debt_dscr(*case)
        key=self.archive.save_debt_dscr(*case,run);restored=self.archive.load_debt_dscr(key)
        self.assertEqual(restored.run,run);self.assertEqual(restored.debt_run,self.debt)
        self.assertFalse(run.payload['noi_financially_verified']);self.assertFalse(run.payload['loan_terms_financially_verified'])
        self.assertEqual(self.archive.get_loan_source(restored.payload['loan_source_sha256']),self.loan)
        self.assertTrue(all(not v for v in case[0].payload['criterion_claims'].values()))

if __name__=='__main__':unittest.main()
