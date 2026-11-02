"""T32 closing-to-investor compilation gated by replayed T31 debt reconciliation."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest
from .debt_closing import DebtClosingRun,reconcile_debt_closing
from .closing_returns import ClosingReturnRun,ClosingReturnBinding,assemble_closing_returns
from .investor_returns import parse_investor_returns
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class DebtClosingReturnBinding:
    profile_id:str
    reconciliation_spec_sha256:str
    reconciliation_run_sha256:str
    closing_return_binding:ClosingReturnBinding
    def __post_init__(self):
        if self.profile_id!='SYNTHETIC-DEBT-CHECKED-CLOSING-RETURN-v1':raise ValidationError('explicit debt-checked closing-return profile required')
        for key in ['reconciliation_spec_sha256','reconciliation_run_sha256']:
            value=getattr(self,key)
            if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact reconciliation source/run hashes required')
        if type(self.closing_return_binding)is not ClosingReturnBinding:raise ValidationError('typed exact closing-return binding required')


def binding_from_record(p):
    if type(p)is not dict or set(p)!={'profile_id','reconciliation_spec_sha256','reconciliation_run_sha256','closing_return_binding'}or type(p['closing_return_binding'])is not dict:raise ValidationError('exact archived debt-checked binding required')
    return DebtClosingReturnBinding(**dict(p,closing_return_binding=ClosingReturnBinding(**p['closing_return_binding'])))


@dataclass(frozen=True)
class DebtClosingReturnRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def closing_return_run(self):
        p=self.payload['closing_return_run'];return None if p is None else ClosingReturnRun(**p)
    @property
    def compiled_raw(self):
        r=self.closing_return_run;return None if r is None else r.compiled_raw
    @property
    def investor_run(self):
        r=self.closing_return_run;return None if r is None else r.investor_run


def assemble_debt_checked_returns(loans,closing_raw,closing_run,spec_raw,reconciliation_run,investor_raw,binding):
    if type(binding)is not DebtClosingReturnBinding:raise ValidationError('explicit typed debt-checked binding required')
    parse_investor_returns(investor_raw)
    if type(reconciliation_run)is not DebtClosingRun or reconcile_debt_closing(loans,closing_raw,closing_run,spec_raw)!=reconciliation_run:raise ValidationError('complete dated debt/closing reconciliation must reproduce')
    r=reconciliation_run.payload;blockers=[];underlying=None
    if binding.reconciliation_spec_sha256!=hashlib.sha256(spec_raw).hexdigest():blockers.append('reconciliation_spec_sha256_mismatch')
    if binding.reconciliation_run_sha256!=reconciliation_run.sha256:blockers.append('reconciliation_run_sha256_mismatch')
    if r['state']!='matched_synthetic_debt_assumptions':blockers.append('dated_debt_closing_reconciliation_blocked')
    if not blockers:
        underlying=assemble_closing_returns(closing_raw,closing_run,investor_raw,binding.closing_return_binding)
        blockers.extend(underlying.payload['blockers'])
    p={'component':'T32','purpose':'synthetic_debt_checked_closing_investor_return','engine_sha256':ENGINE_SHA256,
        'binding':asdict(binding),'reconciliation_run_sha256':reconciliation_run.sha256,
        'reconciliation_spec_sha256':hashlib.sha256(spec_raw).hexdigest(),'closing_run_sha256':closing_run.sha256,
        'original_investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),
        'closing_return_run':None if underlying is None else asdict(underlying),'blockers':sorted(set(blockers)),
        'debt_reconciliation_blockers':r['blockers'],'state':'compiled_synthetic'if underlying is not None and underlying.compiled_raw is not None and not blockers else'blocked',
        'all_debt_sources_and_closing_replayed':True,'original_source_overwritten':False,
        'scheduled_payment_history_actually_verified':False,'bank_payoff_statement_verified':False,'whole_project_cash_reconciled':False,
        'distribution_authorized':False,'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return DebtClosingReturnRun(encoded,digest(encoded))
