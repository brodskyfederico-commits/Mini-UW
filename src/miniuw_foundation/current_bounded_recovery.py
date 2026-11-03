"""T52 explicit-time full-source gate for bounded piecewise recovery observations."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .bounded_sale_recovery import BoundedSaleRecoveryRun,analyze_bounded_sale_recovery
from .current_bounded_exit_output import required_bounded_exit_sources
from .evidence_currency import EvidenceCurrencyRun,evaluate_evidence_currency

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T51-T52.md'


def required_bounded_recovery_sources(arguments,recovery_spec_raw):
    if type(recovery_spec_raw)is not bytes:raise ValidationError('piecewise specification bytes required')
    rows=required_bounded_exit_sources(arguments)
    rows.append(dict(requirement_id='/recovery/piecewise_spec',source_sha256=hashlib.sha256(recovery_spec_raw).hexdigest(),source_locator='/recovery/piecewise_spec'))
    return rows


@dataclass(frozen=True)
class CurrentBoundedRecoveryRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_bounded_recovery(arguments,base_run,recovery_spec_raw,recovery_run,registry_raw,registry_run,as_of):
    if type(recovery_run)is not BoundedSaleRecoveryRun or analyze_bounded_sale_recovery(arguments,base_run,recovery_spec_raw)!=recovery_run:raise ValidationError('entire piecewise recovery must reproduce')
    if type(registry_run)is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw,as_of)!=registry_run:raise ValidationError('entire registry must reproduce at exact evaluation time')
    p=recovery_run.payload;r=registry_run.payload;required=required_bounded_recovery_sources(arguments,recovery_spec_raw);blockers=[]
    if sorted(required,key=lambda x:x['requirement_id'])!=sorted([row['requirement']for row in r['requirements']],key=lambda x:x['requirement_id']):blockers.append('complete_piecewise_recovery_source_inventory_mismatch')
    if r['context']!=p['context']:blockers.append('registry_and_recovery_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('required_evidence_not_current')
    if p['state']!='computed_synthetic_piecewise_recovery':blockers.append('piecewise_recovery_calculation_blocked')
    output=None if blockers else p['analysis']
    result={'component':'T52','purpose':'synthetic_current_evidence_piecewise_recovery_gate',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'base_bounded_run_sha256':base_run.sha256,'recovery_run_sha256':recovery_run.sha256,
        'recovery_spec_sha256':hashlib.sha256(recovery_spec_raw).hexdigest(),'registry_source_sha256':hashlib.sha256(registry_raw).hexdigest(),'registry_run_sha256':registry_run.sha256,
        'evaluated_as_of_UTC':as_of,'context':p['context'],'currency':p['currency'],'forward_window':p['forward_window'],'exit_cap_unit':p['exit_cap_unit'],
        'required_source_bindings':required,'state':'current_synthetic_piecewise_recovery_at_declared_time'if output is not None else'PENDING',
        'current_recovery_analysis':output,'blockers':sorted(set(blockers)),'recovery_blockers':p['blockers'],
        'underlying_calculation_blockers':p['underlying_calculation_blockers'],'original_cost_blockers':p['original_cost_blockers'],'evidence_blockers':r['blockers'],
        'historical_analysis_preserved':True,'professional_review_authenticated':False,'cost_profile_financially_valid_over_domain':False,
        'funding_availability_verified_over_domain':False,'financial_publication_authorized':False,'live_expiry_monitor_enabled':False,
        'investment_criterion_adopted':False,'personal_investor_return':None,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return CurrentBoundedRecoveryRun(encoded,digest(encoded))


def verify_current_bounded_recovery(arguments,base_run,recovery_spec_raw,recovery_run,registry_raw,registry_run,as_of,report):
    if type(report)is not CurrentBoundedRecoveryRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed current piecewise report with matching hash required')
    if assemble_current_bounded_recovery(arguments,base_run,recovery_spec_raw,recovery_run,registry_raw,registry_run,as_of)!=report:raise ValidationError('current piecewise report replay mismatch')
    return report
