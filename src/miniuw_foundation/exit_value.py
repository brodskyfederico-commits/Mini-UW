"""T41 conditional forward-NOI/exit-cap value; valuation never becomes cash here."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import hashlib
import json
import re

from .drafts import ContextSeed, ValidationError, canonical, digest, nonempty
from .intake import _unique_object, _invalid_constant
from .debt_service import _fraction, rational
from .investor_returns import _date
from .operating_noi import OperatingNoiRun, produce_operating_noi, _bounded, ArithmeticBudgetError

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T41-T42.md'


def parse_exit_value(raw):
    if type(raw) is not bytes or not raw or len(raw) > 131072:
        raise ValidationError('bounded explicit exit valuation specification required')
    try:
        p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except (UnicodeError,ValueError,RecursionError) as error:
        raise ValidationError('invalid exit valuation JSON') from error
    if type(p) is not dict or set(p)!={'schema','context','currency','valuation_date','noi_source_sha256',
            'noi_run_sha256','forward_window','cap_rate','valuation_basis_ref'} or p['schema']!='miniuw.synthetic-exit-value.v1':
        raise ValidationError('exact forward NOI/exit cap profile required')
    if type(p['context']) is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required') from error
    nonempty(p['currency'],'currency');_date(p['valuation_date'])
    for key in ['noi_source_sha256','noi_run_sha256']:
        if type(p[key]) is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):raise ValidationError('exact NOI source/run SHA required')
    if p['valuation_basis_ref'] is not None:nonempty(p['valuation_basis_ref'],'valuation_basis_ref')
    window=p['forward_window']
    if type(window) is not dict or set(window)!={'start','end','period_ref','basis_ref'}:
        raise ValidationError('exact explicit forward window required')
    for key in ['start','end']:
        if window[key] is not None:_date(window[key])
    for key in ['period_ref','basis_ref']:
        if window[key] is not None:nonempty(window[key],key)
    cap=p['cap_rate']
    if type(cap) is not dict or set(cap)!={'value','unit','period_ref','source_ref'}:
        raise ValidationError('exact annual cap metadata required')
    _fraction(cap['value'])
    for key in ['unit','period_ref','source_ref']:
        if cap[key] is not None:nonempty(cap[key],key)
    return p


@dataclass(frozen=True)
class ExitValueRun:
    payload_json:str
    sha256:str

    @property
    def payload(self):return json.loads(self.payload_json)


def produce_exit_value(noi_raw,noi_run,spec_raw):
    spec=parse_exit_value(spec_raw)
    if type(noi_run) is not OperatingNoiRun or produce_operating_noi(noi_raw)!=noi_run:
        raise ValidationError('forward NOI source/run must reproduce exactly')
    p=noi_run.payload;blockers=[];value=None
    for key,actual in [('noi_source_sha256',hashlib.sha256(noi_raw).hexdigest()),('noi_run_sha256',noi_run.sha256),
                       ('context',p['context']),('currency',p['currency'])]:
        if spec[key]!=actual:blockers.append(key+'_mismatch')
    if p['calculation_status']!='computed_synthetic_profile':blockers.append('forward_noi_unavailable')
    window=spec['forward_window'];cap=spec['cap_rate'];rate=_fraction(cap['value'])
    if window['period_ref']!=p['period_ref'] or window['basis_ref'] is None:
        blockers.append('forward_noi_period_or_basis_missing_or_mismatch')
    if window['start']!=spec['valuation_date'] or window['end'] is None:
        blockers.append('forward_window_must_start_at_valuation_date_and_have_end')
    else:
        start=_date(window['start'])
        try:expected=date(start.year+1,start.month,start.day).isoformat()
        except ValueError:expected=None
        if expected is None or window['end']!=expected:
            blockers.append('explicit_one_calendar_year_forward_window_required_no_date_adjustment')
    if cap['unit']!='annual_cap_fraction' or cap['period_ref']!=p['period_ref'] or cap['source_ref'] is None:
        blockers.append('cap_unit_period_or_source_missing_or_mismatch')
    if rate is None or rate<=0:blockers.append('positive_exit_cap_required')
    if spec['valuation_basis_ref'] is None:blockers.append('valuation_basis_missing')
    noi=None if p['noi'] is None else _fraction(p['noi'],max_digits=1300)
    if noi is not None and noi<0:blockers.append('negative_forward_noi_outside_valuation_profile')
    if not blockers:
        try:value=rational(_bounded(noi/rate))
        except ArithmeticBudgetError:blockers.append('exit_value_exact_arithmetic_budget_exceeded')
    result={'component':'T41','purpose':'conditional_synthetic_forward_noi_exit_value',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'spec_sha256':hashlib.sha256(spec_raw).hexdigest(),'noi_source_sha256':hashlib.sha256(noi_raw).hexdigest(),
        'noi_run_sha256':noi_run.sha256,'context':p['context'],'currency':spec['currency'],
        'valuation_date':spec['valuation_date'],'forward_window':window,'cap_rate':cap,
        'valuation_basis_ref':spec['valuation_basis_ref'],'forward_noi':p['noi'],'candidate_value':value,
        'state':'computed_synthetic_exit_value' if value is not None else 'blocked',
        'blockers':sorted(set(blockers)),'upstream_noi_blockers':p['blockers'],
        'calendar_window_verified_arithmetically_only':not any('window' in b for b in blockers),
        'actual_forward_noi_scope_verified':False,'cash_proceeds_produced':False,'market_price_verified':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return ExitValueRun(encoded,digest(encoded))
