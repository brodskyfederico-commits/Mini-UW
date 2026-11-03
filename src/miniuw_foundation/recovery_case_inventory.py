"""T55 complete declared case inventory; no best-case selection or approval."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .current_recovery_case import CurrentRecoveryCaseRun,assemble_current_recovery_case
from .evidence_currency import timestamp

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T55.md'


@dataclass(frozen=True)
class RecoveryReviewCase:
    case_id:str
    arguments:tuple
    run:CurrentRecoveryCaseRun
    def __post_init__(self):
        nonempty(self.case_id,'case_id')
        if type(self.arguments)is not tuple or len(self.arguments)!=7 or type(self.run)is not CurrentRecoveryCaseRun:
            raise ValidationError('complete immutable T54 case source/run required')


def parse_case_inventory(raw):
    if type(raw)is not bytes or not raw or len(raw)>131072:raise ValidationError('bounded declared case inventory required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid case inventory JSON')from error
    keys={'schema','as_of_UTC','reference_bounded_run_sha256','recovery_run_sha256','reference_registry_source_sha256','inventory_declared_complete','inventory_basis_ref','cases'}
    if type(p)is not dict or set(p)!=keys or p['schema']!='miniuw.synthetic-recovery-case-inventory.v1':raise ValidationError('exact case inventory profile required')
    timestamp(p['as_of_UTC'])
    for key in ['reference_bounded_run_sha256','recovery_run_sha256','reference_registry_source_sha256']:
        if type(p[key])is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):raise ValidationError('exact shared reference hash required')
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('explicit inventory completeness required')
    if p['inventory_basis_ref']is not None:nonempty(p['inventory_basis_ref'],'inventory_basis_ref')
    if type(p['cases'])is not list or not 1<=len(p['cases'])<=12:raise ValidationError('one to twelve declared cases required')
    seen=set()
    for row in p['cases']:
        if type(row)is not dict or set(row)!={'case_id','current_case_run_sha256'}:raise ValidationError('exact case ID/result hash required')
        nonempty(row['case_id'],'case_id')
        if row['case_id']in seen:raise ValidationError('duplicate declared case identity')
        seen.add(row['case_id'])
        if type(row['current_case_run_sha256'])is not str or not re.fullmatch('[a-f0-9]{64}',row['current_case_run_sha256']):raise ValidationError('exact current case hash required')
    return p


@dataclass(frozen=True)
class RecoveryCaseInventoryRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_recovery_case_inventory(cases,inventory_raw):
    spec=parse_case_inventory(inventory_raw)
    if type(cases)is not tuple or not 1<=len(cases)<=12 or any(type(c)is not RecoveryReviewCase for c in cases):raise ValidationError('immutable complete case proof inventory required')
    ids=[c.case_id for c in cases]
    if len(set(ids))!=len(ids):raise ValidationError('duplicate supplied case identity')
    blockers=[];rows=[]
    actual=[dict(case_id=c.case_id,current_case_run_sha256=c.run.sha256)for c in cases]
    if actual!=spec['cases']:blockers.append('declared_and_supplied_case_inventory_mismatch')
    if spec['inventory_declared_complete']is not True or spec['inventory_basis_ref']is None:blockers.append('case_inventory_not_explicitly_complete_with_basis')
    context=None
    for case in cases:
        if assemble_current_recovery_case(*case.arguments)!=case.run:raise ValidationError('every complete current case must reproduce')
        comparison_args=case.arguments[0];reference,base,sr,recovery,_,_=comparison_args
        p=case.run.payload
        if context is None:context=reference[4].payload['context']
        elif context!=reference[4].payload['context']:blockers.append(case.case_id+':reference_context_mismatch')
        if base.sha256!=spec['reference_bounded_run_sha256']or recovery.sha256!=spec['recovery_run_sha256']:blockers.append(case.case_id+':shared_reference_or_recovery_revision_mismatch')
        if hashlib.sha256(case.arguments[2]).hexdigest()!=spec['reference_registry_source_sha256']:blockers.append(case.case_id+':shared_reference_evidence_revision_mismatch')
        if p['evaluated_as_of_UTC']!=spec['as_of_UTC']:blockers.append(case.case_id+':evaluation_time_mismatch')
        rows.append(dict(case_id=case.case_id,current_case_run_sha256=case.run.sha256,state=p['state'],
            current_matched_case=p['current_matched_case'],blockers=p['blockers'],comparison_blockers=p['comparison_blockers'],
            reference_evidence_blockers=p['reference_evidence_blockers'],candidate_evidence_blockers=p['candidate_evidence_blockers'],
            reference_calculation_blockers=p['reference_calculation_blockers'],candidate_calculation_blockers=p['candidate_calculation_blockers'],
            reference_original_cost_blockers=p['reference_original_cost_blockers'],candidate_original_cost_blockers=p['candidate_original_cost_blockers'],decision='PENDING'))
    # Global inconsistency invalidates the comparison view without discarding rows/reasons.
    if blockers:
        for row in rows:row['current_matched_case']=None;row['state']='PENDING'
    all_current=not blockers and all(row['current_matched_case']is not None for row in rows)
    result={'component':'T55','purpose':'declared_synthetic_recovery_case_review_inventory',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'inventory_sha256':hashlib.sha256(inventory_raw).hexdigest(),'context':context,'evaluated_as_of_UTC':spec['as_of_UTC'],
        'reference_bounded_run_sha256':spec['reference_bounded_run_sha256'],'recovery_run_sha256':spec['recovery_run_sha256'],
        'reference_registry_source_sha256':spec['reference_registry_source_sha256'],'case_rows':rows,'blockers':sorted(set(blockers)),
        'state':'complete_synthetic_current_case_inventory'if all_current else'PENDING',
        'all_declared_cases_current_and_matched':all_current,'declared_inventory_verified':not blockers,
        'best_case_selected':False,'average_return_generated':False,'scenarios_automatically_generated':False,
        'downside_policy_adopted':False,'professional_review_authenticated':False,'financial_publication_authorized':False,
        'personal_investor_return':None,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return RecoveryCaseInventoryRun(encoded,digest(encoded))


def verify_recovery_case_inventory(cases,inventory_raw,report):
    if type(report)is not RecoveryCaseInventoryRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed case inventory result with matching hash required')
    if assemble_recovery_case_inventory(cases,inventory_raw)!=report:raise ValidationError('case inventory result replay mismatch')
    return report
