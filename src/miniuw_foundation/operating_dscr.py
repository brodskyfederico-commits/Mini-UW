"""T20 computed conditional NOI over computed regular annual debt-service equivalent."""
from dataclasses import asdict,dataclass
from pathlib import Path
import hashlib,re
from .drafts import ValidationError,canonical,digest,nonempty
from .debt_service import DebtServiceRun,produce_debt_service,_fraction,rational,MAX_BITS
from .operating_noi import OperatingNoiRun,produce_operating_noi
from .scoped_profiles import definition_sources

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class OperatingDscrBinding:
    profile_id:str
    definition_revision:str
    noi_source_sha256:str
    loan_source_sha256:str
    noi_run_sha256:str
    debt_run_sha256:str
    currency:str
    noi_period_ref:str
    annual_equivalent_ref:str
    declared_annual_noi_basis_ref:str|None
    def __post_init__(self):
        if self.profile_id!='SYNTHETIC-COMPUTED-NOI-ANNUAL-DSCR-v1':raise ValidationError('explicit annual-equivalent-only profile required')
        for k,v in asdict(self).items():
            if k=='declared_annual_noi_basis_ref'and v is None:continue
            nonempty(v,k)
        for k in ['noi_source_sha256','loan_source_sha256','noi_run_sha256','debt_run_sha256']:
            if not re.fullmatch('[a-f0-9]{64}',getattr(self,k)):raise ValidationError('exact producer/source binding hashes required')


@dataclass(frozen=True)
class OperatingDscrRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):
        import json
        return json.loads(self.payload_json)


def calculate_operating_dscr(noi_raw,noi_run,loan_raw,windows,debt_run,binding):
    if type(binding)is not OperatingDscrBinding:raise ValidationError('explicit computed NOI/annual service binding required')
    if type(noi_run)is not OperatingNoiRun or produce_operating_noi(noi_raw)!=noi_run:raise ValidationError('NOI source and exact producer run must reproduce')
    if type(debt_run)is not DebtServiceRun or produce_debt_service(loan_raw,windows)!=debt_run:raise ValidationError('debt source/windows and exact producer run must reproduce')
    noi=noi_run.payload;debt=debt_run.payload;selected=debt['annual_sizing'];blockers=[]
    for key,actual in [('noi_source_sha256',noi['source_sha256']),('loan_source_sha256',debt['source_sha256']),('noi_run_sha256',noi_run.sha256),('debt_run_sha256',debt_run.sha256)]:
        if getattr(binding,key)!=actual:blockers.append(key+'_mismatch')
    if noi['context']!=debt['context']:blockers.append('producer_context_mismatch')
    if noi['currency']!=binding.currency or debt['currency']!=binding.currency:blockers.append('producer_currency_mismatch')
    if noi['period_ref']!=binding.noi_period_ref:blockers.append('noi_period_reference_mismatch')
    if selected['period_ref']!=binding.annual_equivalent_ref:blockers.append('annual_service_reference_mismatch')
    if binding.noi_period_ref!=binding.annual_equivalent_ref:blockers.append('noi_and_annual_equivalent_period_mismatch')
    if binding.declared_annual_noi_basis_ref is None:blockers.append('annual_noi_basis_declaration_missing')
    if noi['calculation_status']!='computed_synthetic_profile' or noi['noi']is None:blockers.append('computed_noi_unavailable')
    service=_fraction(selected['amount'],1300)if selected['state']=='computed_synthetic'else None
    if service is None:blockers.append('computed_annual_service_unavailable')
    elif service<=0:blockers.append('positive_annual_service_required')
    ratio=None
    if not blockers:
        ratio=_fraction(noi['noi'],1300)/service
        if ratio.numerator.bit_length()>MAX_BITS or ratio.denominator.bit_length()>MAX_BITS:blockers.append('technical_rational_size_bound');ratio=None
    payload={'component':'T20','purpose':'conditional_synthetic_computed_NOI_DSCR','engine_sha256':ENGINE_SHA256,
        'definition_sources':definition_sources(),'binding':asdict(binding),'context':noi['context'],
        'noi_source_sha256':noi['source_sha256'],'loan_source_sha256':debt['source_sha256'],
        'noi_run_sha256':noi_run.sha256,'debt_run_sha256':debt_run.sha256,
        'computed_noi':noi['noi'],'annual_service_equivalent':None if service is None else rational(service),
        'rational':None if ratio is None else rational(ratio),'output_unit':'x','state':'computed_synthetic'if ratio is not None else'blocked',
        'interpretation_label':'conditional_NOI_over_regular_annual_sizing_equivalent_not_dated_cash_or_balloon',
        'blockers':sorted(set(blockers)),'noi_blockers':noi['blockers'],'producer_arithmetic_replayed':True,
        'annual_noi_basis_financially_verified':False,'tax_policy_adopted':False,'loan_terms_financially_verified':False,
        'cash_paid_verified':False,'bank_dscr_minimum_applied':False,'investment_criterion_applied':False,
        'financially_validated':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(payload);return OperatingDscrRun(encoded,digest(encoded))
