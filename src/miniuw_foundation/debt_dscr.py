"""DSCR bridge using computed synthetic contractual service, not declared service."""
from dataclasses import asdict,dataclass
from fractions import Fraction
import hashlib,json,re
from pathlib import Path
from .drafts import ValidationError,canonical,digest,nonempty
from .calculations import CalculationRun,calculate_synthetic
from .debt_service import DebtServiceRun,produce_debt_service,_fraction,MAX_BITS
from .scoped_profiles import definition_sources

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class DebtDscrBinding:
    profile_id:str
    definition_revision:str
    noi_node:str
    noi_producer_revision:str
    noi_basis_ref:str
    loan_source_sha256:str
    service_basis_ref:str
    service_mode:str
    window_id:str|None
    include_balloon:bool
    currency:str
    period_ref:str

    def __post_init__(self):
        for key,value in asdict(self).items():
            if key not in ('window_id','include_balloon'):nonempty(value,key)
        if self.profile_id!='SYNTHETIC-COMPUTED-SERVICE-DSCR-v1' or not re.fullmatch('[a-f0-9]{64}',self.loan_source_sha256):
            raise ValidationError('explicit computed-service profile/source identity required')
        if self.service_mode not in ('annual_sizing_equivalent','dated_contractual_due') or type(self.include_balloon) is not bool:
            raise ValidationError('explicit supported service mode and balloon choice required')
        if self.service_mode=='annual_sizing_equivalent':
            if self.window_id is not None or self.include_balloon:
                raise ValidationError('annual regular sizing equivalent cannot include balloon or a dated window')
        else:nonempty(self.window_id,'window_id')


@dataclass(frozen=True)
class DebtDscrRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def calculate_debt_dscr(snapshot,profiles,normalization,graph,upstream,loan_raw,windows,debt_run,binding):
    if type(binding) is not DebtDscrBinding:
        raise ValidationError('explicit debt DSCR binding required')
    if type(upstream) is not CalculationRun or calculate_synthetic(snapshot,profiles,normalization,graph)!=upstream:
        raise ValidationError('NOI upstream must reproduce from exact source evidence')
    if type(debt_run) is not DebtServiceRun or produce_debt_service(loan_raw,windows)!=debt_run:
        raise ValidationError('debt service must reproduce from exact loan source/windows')
    prior=upstream.payload;debt=debt_run.payload
    if binding.noi_node not in prior['results']:
        raise ValidationError('NOI producer unavailable')
    blockers=[]
    if binding.loan_source_sha256!=debt['source_sha256']:blockers.append('loan_source_identity_mismatch')
    context={k:v for k,v in prior['source']['context'].items() if k!='input_revision'}
    if context!=debt['context']:blockers.append('loan_and_noi_context_mismatch')
    if debt['currency']!=binding.currency:blockers.append('loan_currency_mismatch')
    if binding.service_mode=='annual_sizing_equivalent':
        selected=debt['annual_sizing'];unit='currency/annual-sizing-equivalent'
        if selected['period_ref']!=binding.period_ref:blockers.append('annual_equivalent_period_mismatch')
        service=_fraction(selected['amount'],1300) if selected['state']=='computed_synthetic' else None
        label='synthetic_dscr_over_computed_regular_annual_sizing_equivalent'
    else:
        if binding.window_id not in debt['dated_windows']:
            raise ValidationError('explicit dated window unavailable')
        selected=debt['dated_windows'][binding.window_id];unit='currency/declared-period'
        if binding.window_id!=binding.period_ref:blockers.append('dated_window_period_identity_mismatch')
        key='scheduled_plus_balloon_due' if binding.include_balloon else 'scheduled_service_due'
        service=_fraction(selected[key],1300) if selected['state']=='computed_synthetic' else None
        label='synthetic_dscr_over_contractual_due_'+('including_balloon' if binding.include_balloon else 'scheduled_only')
    if service is None:blockers.append('computed_service_unavailable')
    elif service<=0:blockers.append('positive_computed_service_required')
    record=prior['results'][binding.noi_node]
    if record['definition']['definition_revision']!=binding.noi_producer_revision:blockers.append('noi_producer_revision_mismatch')
    if record['state']!='computed_synthetic':blockers.append('noi_upstream_blocked')
    elif record['quantity']!={'kind':'money_per_period','unit':unit,'currency':binding.currency,'period':binding.period_ref}:
        blockers.append('noi_quantity_currency_or_period_mismatch')
    value=None
    if not blockers:
        value=_fraction(record['rational'],1300)/service
        if max(abs(value.numerator).bit_length(),value.denominator.bit_length())>MAX_BITS:
            blockers.append('technical_rational_size_bound');value=None
    payload={'component':'T10-DSCR','purpose':'synthetic_development_only','engine_sha256':ENGINE_SHA256,
        'definition_sources':definition_sources(),'binding':asdict(binding),'source':prior['source'],
        'normalization_sha256':normalization.sha256,'upstream_run_sha256':upstream.sha256,
        'loan_source_sha256':debt['source_sha256'],'debt_run_sha256':debt_run.sha256,
        'selected_service':selected,'selected_service_amount':None if service is None else {'numerator':str(service.numerator),'denominator':str(service.denominator)},
        'state':'blocked' if blockers else 'computed_synthetic','rational':None if value is None else {'numerator':str(value.numerator),'denominator':str(value.denominator)},
        'output_unit':'x','interpretation_label':label,'blockers':sorted(set(blockers)),
        'debt_service_arithmetic_replayed':True,'noi_financially_verified':False,'loan_terms_financially_verified':False,
        'cash_paid_verified':False,'financially_validated':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(payload);return DebtDscrRun(encoded,digest(encoded))
