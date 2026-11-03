"""T54 require both reference and candidate source currency for a matched case."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .recovery_case_check import RecoveryCaseCheckRun,check_recovery_case
from .current_bounded_recovery import assemble_current_bounded_recovery
from .current_bounded_exit_output import assemble_current_bounded_exit_output

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T54.md'


@dataclass(frozen=True)
class CurrentRecoveryCaseRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_recovery_case(check_arguments,check_run,reference_registry_raw,reference_registry_run,candidate_registry_raw,candidate_registry_run,as_of):
    if type(check_arguments)is not tuple or len(check_arguments)!=6 or type(check_run)is not RecoveryCaseCheckRun:
        raise ValidationError('complete immutable case comparison and typed result required')
    if check_recovery_case(*check_arguments)!=check_run:raise ValidationError('complete reference/candidate comparison must reproduce')
    ref,ref_run,spec,recovery,candidate,candidate_run=check_arguments
    reference=assemble_current_bounded_recovery(ref,ref_run,spec,recovery,reference_registry_raw,reference_registry_run,as_of)
    current_candidate=assemble_current_bounded_exit_output(candidate,candidate_run,candidate_registry_raw,candidate_registry_run,as_of)
    p=check_run.payload;r=reference.payload;c=current_candidate.payload;blockers=[];output=None
    if p['state']!='matched_synthetic_full_case':blockers.append('full_case_comparison_not_matched')
    if r['current_recovery_analysis']is None:blockers.append('reference_curve_not_current')
    if c['current_project_return_summary']is None:blockers.append('candidate_story_not_current')
    if not blockers:
        output=dict(comparison=p['comparison'],reference_recovery_analysis=r['current_recovery_analysis'],
            candidate_project_return_story=c['current_project_return_summary'],decision='PENDING')
    result={'component':'T54','purpose':'synthetic_current_reference_and_candidate_recovery_check',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'comparison_run_sha256':check_run.sha256,'reference_current_run_sha256':reference.sha256,'candidate_current_run_sha256':current_candidate.sha256,
        'reference_registry_source_sha256':hashlib.sha256(reference_registry_raw).hexdigest(),
        'candidate_registry_source_sha256':hashlib.sha256(candidate_registry_raw).hexdigest(),'evaluated_as_of_UTC':as_of,
        'state':'current_synthetic_matched_case_at_declared_time'if output is not None else'PENDING','current_matched_case':output,
        'blockers':blockers,'comparison_blockers':p['blockers'],'reference_blockers':r['blockers'],'candidate_blockers':c['blockers'],
        'reference_evidence_blockers':r['evidence_blockers'],'candidate_evidence_blockers':c['evidence_blockers'],
        'reference_calculation_blockers':r['underlying_calculation_blockers'],'candidate_calculation_blockers':c['calculation_blockers'],
        'reference_original_cost_blockers':r['original_cost_blockers'],
        'candidate_original_cost_blockers':c['original_cost_blockers'],
        'reference_source_binding_count':len(r['required_source_bindings']),'candidate_source_binding_count':len(c['required_source_bindings']),
        'historical_comparison_and_calculations_preserved':True,'professional_review_authenticated':False,
        'contract_or_tax_rule_verified':False,'financial_publication_authorized':False,'live_expiry_monitor_enabled':False,
        'funding_availability_verified':False,'personal_investor_return':None,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return CurrentRecoveryCaseRun(encoded,digest(encoded))


def verify_current_recovery_case(check_arguments,check_run,reference_registry_raw,reference_registry_run,candidate_registry_raw,candidate_registry_run,as_of,report):
    if type(report)is not CurrentRecoveryCaseRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed current case report with matching hash required')
    if assemble_current_recovery_case(check_arguments,check_run,reference_registry_raw,reference_registry_run,candidate_registry_raw,candidate_registry_run,as_of)!=report:raise ValidationError('current case report replay mismatch')
    return report
