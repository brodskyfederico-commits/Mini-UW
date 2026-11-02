"""T10 regular fixed-rate arrears debt service from explicit synthetic loan terms.

Contractual amounts due are not evidence of cash paid, bank approval or payoff.
"""
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from .drafts import ContextSeed, ValidationError, canonical, digest, nonempty
from .intake import _unique_object, _invalid_constant

SCHEMA='miniuw.synthetic-loan-terms.v1'
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
MAX_PAYMENTS=600
MAX_BITS=4096
KEYS={'schema','loan_id','regular_intervals_assumed','context','principal','currency','periodic_rate','amortization_payments',
    'maturity_payment','payments_per_year','rate_interval_ref','annual_equivalent_ref',
    'rate_basis','payment_timing','fixed_rate','new_draws','capitalized_fees',
    'interest_only','rounding','balloon_treatment','origination_date','payment_dates'}
ASSUMPTIONS={'regular_intervals_assumed':True,'rate_basis':'effective_per_payment_interval','payment_timing':'arrears',
    'fixed_rate':True,'new_draws':False,'capitalized_fees':False,'interest_only':False,
    'rounding':'none_exact','balloon_treatment':'due_after_last_scheduled_payment'}


def _fraction(record,max_digits=256):
    if record is None:return None
    if type(record) is not dict or set(record)!={'numerator','denominator'}:
        raise ValidationError('explicit rational numerator/denominator required')
    n,d=record['numerator'],record['denominator']
    if (type(n) is not str or type(d) is not str or len(n)>max_digits or len(d)>max_digits
        or not re.fullmatch('-?[0-9]+',n) or not re.fullmatch('[0-9]+',d) or int(d)==0):
        raise ValidationError('bounded rational integer strings with positive denominator required')
    return Fraction(int(n),int(d))


def rational(value):
    return {'numerator':str(value.numerator),'denominator':str(value.denominator)}


def _date(value):
    if type(value) is not str or not re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',value):
        raise ValidationError('explicit ISO calendar date required')
    try:return date.fromisoformat(value)
    except ValueError as error:raise ValidationError('invalid calendar date') from error


def parse_loan_terms(raw):
    if type(raw) is not bytes or not raw or len(raw)>1_048_576:
        raise ValidationError('bounded nonempty loan source bytes required')
    try:terms=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except (UnicodeError,json.JSONDecodeError,RecursionError,ValueError) as error:
        raise ValidationError('invalid loan source JSON') from error
    if type(terms) is not dict or set(terms)!=KEYS or terms['schema']!=SCHEMA:
        raise ValidationError('exact supported synthetic loan schema required')
    if type(terms['context']) is not dict:
        raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**terms['context'])
    except TypeError as error:raise ValidationError('exact synthetic loan context required') from error
    nonempty(terms['loan_id'],'loan_id')
    for key,expected in ASSUMPTIONS.items():
        if type(terms[key]) is not type(expected) or terms[key]!=expected:
            raise ValidationError('unsupported loan assumption: '+key)
    for key in ('currency','rate_interval_ref','annual_equivalent_ref'):
        nonempty(terms[key],key)
    _fraction(terms['principal']);_fraction(terms['periodic_rate'])
    for key in ('amortization_payments','maturity_payment','payments_per_year'):
        if terms[key] is not None and type(terms[key]) is not int:
            raise ValidationError('payment counts must be explicit integers or unresolved null')
    if terms['origination_date'] is not None:_date(terms['origination_date'])
    dates=terms['payment_dates']
    if dates is not None:
        if type(dates) is not list or len(dates)>MAX_PAYMENTS:
            raise ValidationError('bounded explicit payment-date list required')
        for value in dates:_date(value)
        if len(set(dates))!=len(dates) or dates!=sorted(dates):
            raise ValidationError('payment dates must be unique and increasing')
        if terms['origination_date'] is None or any(value<=terms['origination_date'] for value in dates):
            raise ValidationError('payment dates must follow explicit origination date')
    return terms


def definition_sources():
    root=Path(__file__).resolve().parents[2]
    refs=[('docs/model-refinance-contract.md',24,'pagos vencidos'),
        ('docs/model-refinance-contract.md',26,'i>0'),
        ('docs/model-refinance-contract.md',27,'i=0'),
        ('docs/model-refinance-contract.md',29,'servicio anual regular'),
        ('docs/model-refinance-contract.md',31,'balloon'),
        ('docs/refinance-capacity-bridge.md',13,'equivalente anualizado')]
    result=[]
    for path,line,marker in refs:
        raw=(root/path).read_bytes();lines=raw.decode('utf-8').splitlines()
        if len(lines)<line or marker not in lines[line-1]:
            raise ValidationError('debt definition source/locator changed')
        result.append({'path':path,'line':line,'sha256':hashlib.sha256(raw).hexdigest()})
    return result


@dataclass(frozen=True,kw_only=True)
class DateWindow:
    window_id:str
    start_date:str
    end_date:str
    boundary:str

    def __post_init__(self):
        nonempty(self.window_id,'window_id')
        if self.boundary!='start_inclusive_end_exclusive' or _date(self.start_date)>=_date(self.end_date):
            raise ValidationError('explicit nonempty half-open date window required')


@dataclass(frozen=True)
class DebtServiceRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def _limited(value):
    return max(abs(value.numerator).bit_length(),value.denominator.bit_length())<=MAX_BITS


def produce_debt_service(raw,windows):
    terms=parse_loan_terms(raw)
    if type(windows) is not tuple or any(type(w) is not DateWindow for w in windows) or len(windows)>128 or len({w.window_id for w in windows})!=len(windows):
        raise ValidationError('bounded immutable explicit date-window tuple required')
    ordered=tuple(sorted(windows,key=lambda w:w.window_id))
    principal,rate=_fraction(terms['principal']),_fraction(terms['periodic_rate'])
    n=terms['amortization_payments'];maturity=terms['maturity_payment'];frequency=terms['payments_per_year']
    blockers=[];payment=unit=None;rows=[];schedule_blockers=[]
    if principal is None:blockers.append('principal_missing')
    elif principal<0:blockers.append('nonnegative_principal_required')
    if rate is None:blockers.append('periodic_rate_missing')
    elif rate<0:blockers.append('nonnegative_fixed_periodic_rate_required')
    if n is None:blockers.append('amortization_count_missing')
    elif n<=0:blockers.append('positive_amortization_count_required')
    elif n>MAX_PAYMENTS:blockers.append('technical_payment_count_bound')
    if not blockers:
        base=1+rate
        if rate!=0 and max(base.numerator.bit_length(),base.denominator.bit_length())*n>MAX_BITS*2:
            blockers.append('technical_exact_power_bound')
        else:
            unit=Fraction(1,n) if rate==0 else rate/(1-base**(-n))
            payment=principal*unit
            if not _limited(unit) or not _limited(payment):
                blockers.append('technical_rational_size_bound');unit=payment=None
    if maturity is None:schedule_blockers.append('maturity_count_missing_no_extension_inferred')
    elif n is None or maturity<=0 or maturity>n:schedule_blockers.append('unsupported_maturity_count')
    if not blockers and not schedule_blockers:
        balance=principal
        for k in range(1,maturity+1):
            interest=balance*rate;capital=payment-interest;closing=balance-capital
            if any(not _limited(v) for v in (interest,capital,closing)):
                schedule_blockers.append('technical_rational_size_bound');rows=[];break
            balloon=closing if k==maturity else Fraction(0)
            rows.append({'payment_index':k,'date':None,'opening_balance':rational(balance),
                'interest_due':rational(interest),'principal_due':rational(capital),
                'scheduled_service_due':rational(payment),'closing_balance':rational(closing),
                'balloon_due':rational(balloon),'scheduled_plus_balloon_due':rational(payment+balloon)})
            balance=closing
    annual_blockers=list(blockers)
    if frequency is None:annual_blockers.append('payments_per_year_missing')
    elif frequency<=0 or frequency>MAX_PAYMENTS:annual_blockers.append('unsupported_payments_per_year_or_technical_bound')
    annual=frequency*payment if not annual_blockers else None
    if annual is not None and not _limited(annual):annual=None;annual_blockers.append('technical_rational_size_bound')
    date_blockers=list(blockers)+list(schedule_blockers)
    dates=terms['payment_dates']
    if dates is None:date_blockers.append('explicit_payment_dates_missing')
    elif maturity is None or len(dates)!=maturity:date_blockers.append('date_count_differs_from_maturity')
    if not date_blockers:
        for row,value in zip(rows,dates):row['date']=value
    reports={}
    for window in ordered:
        indices=[];scheduled=balloon=interest=capital=None
        if not date_blockers:
            selected=[row for row in rows if window.start_date<=row['date']<window.end_date]
            indices=[row['payment_index'] for row in selected]
            def total(key):return sum((_fraction(row[key],1300) for row in selected),Fraction(0))
            scheduled,balloon,interest,capital=(total(k) for k in ('scheduled_service_due','balloon_due','interest_due','principal_due'))
        window_blockers=list(date_blockers)
        if scheduled is not None and any(not _limited(v) for v in (scheduled,balloon,interest,capital,scheduled+balloon)):
            window_blockers.append('technical_rational_size_bound');scheduled=balloon=interest=capital=None
        reports[window.window_id]={'state':'blocked' if window_blockers else 'computed_synthetic',
            'window':{'window_id':window.window_id,'start_date':window.start_date,'end_date':window.end_date,'boundary':window.boundary},
            'payment_indices':indices,'scheduled_service_due':rational(scheduled) if scheduled is not None else None,
            'balloon_due':rational(balloon) if balloon is not None else None,
            'interest_due':rational(interest) if interest is not None else None,
            'principal_due':rational(capital) if capital is not None else None,
            'scheduled_plus_balloon_due':rational(scheduled+balloon) if scheduled is not None else None,
            'blockers':window_blockers}
    payload={'component':'T10','purpose':'synthetic_development_only','engine_sha256':ENGINE_SHA256,
        'definition_sources':definition_sources(),'source_sha256':hashlib.sha256(raw).hexdigest(),
        'loan_id':terms['loan_id'],'context':terms['context'],'regular_intervals_assumed':True,'calendar_interval_consistency_verified':False,'currency':terms['currency'],'rate_interval_ref':terms['rate_interval_ref'],
        'state':'blocked' if blockers else 'computed_synthetic',
        'payment_per_unit':rational(unit) if unit is not None else None,
        'regular_payment_due':rational(payment) if payment is not None else None,'payment_blockers':blockers,
        'schedule_state':'blocked' if blockers or schedule_blockers else 'computed_synthetic',
        'schedule_blockers':sorted(set(blockers+schedule_blockers)),'schedule':rows,
        'annual_sizing':{'state':'blocked' if annual_blockers else 'computed_synthetic',
            'amount':rational(annual) if annual is not None else None,
            'period_ref':terms['annual_equivalent_ref'],'unit':'currency/annual-sizing-equivalent',
            'label':'regular_payment_annual_sizing_equivalent_not_dated_cash','blockers':annual_blockers},
        'dated_windows':reports,'modeled_due_scope':'scheduled_service_and_principal_balloon_only','other_due_items_completeness_verified':False,'cash_paid_verified':False,'payoff_verified':False,
        'financially_validated':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(payload)
    return DebtServiceRun(encoded,digest(encoded))
