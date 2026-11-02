"""T16 explicit metric-revision branches for the source-specific experiment."""
from dataclasses import asdict,dataclass
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction
from .scenario_threshold_rehearsal import ScenarioThresholdRun,simulate_scenario_thresholds

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-scenario-metric-proposal.v1'
KEYS={'schema','proposal_id','document_sha256','base_case_sha256','base_run_sha256','new_case_id','new_run_id',
    'author_label','reason','evidence_refs','patches','status'}
PATCH_KEYS={'metric_id','scenario_id','expected_before','proposed_after','reason'}


class ScenarioRevisionConflict(ValidationError):pass


def parse_scenario_proposal(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded synthetic proposal bytes required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid proposal JSON')from error
    if type(p)is not dict or set(p)!=KEYS or p['schema']!=SCHEMA or p['status']!='proposal_only':raise ValidationError('exact proposal-only schema required')
    for k in ['proposal_id','new_case_id','new_run_id','author_label','reason']:nonempty(p[k],k)
    if not p['proposal_id'].startswith('SYNTHETIC-'):raise ValidationError('synthetic proposal identity required')
    for k in ['document_sha256','base_case_sha256','base_run_sha256']:
        if type(p[k])is not str or not re.fullmatch('[a-f0-9]{64}',p[k]):raise ValidationError('exact base hashes required')
    if type(p['evidence_refs'])is not list or not 1<=len(p['evidence_refs'])<=32:raise ValidationError('declared evidence references required')
    for ref in p['evidence_refs']:nonempty(ref,'evidence_ref')
    if type(p['patches'])is not list or not 1<=len(p['patches'])<=20:raise ValidationError('bounded explicit patch batch required')
    seen=set()
    for change in p['patches']:
        if type(change)is not dict or set(change)!=PATCH_KEYS:raise ValidationError('metric value patches only; rules and applicability are protected')
        for k in ['metric_id','scenario_id','reason']:nonempty(change[k],k)
        key=(change['metric_id'],change['scenario_id'])
        if key in seen:raise ValidationError('duplicate patch')
        seen.add(key)
        _fraction(change['expected_before']);_fraction(change['proposed_after'])
        if canonical(change['expected_before'])==canonical(change['proposed_after']):raise ValidationError('no-op change rejected')
    return p


@dataclass(frozen=True)
class ScenarioReviewRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def candidate_raw(self):return self.payload['candidate_case_json'].encode('utf-8')
    @property
    def candidate_run(self):return ScenarioThresholdRun(**self.payload['candidate_run'])


def evaluate_scenario_proposal(document_raw,base_raw,base_run,proposal_raw):
    if type(base_run)is not ScenarioThresholdRun or simulate_scenario_thresholds(document_raw,base_raw)!=base_run:
        raise ScenarioRevisionConflict('base run does not reproduce under current source, code and policy')
    p=parse_scenario_proposal(proposal_raw)
    if (p['document_sha256']!=hashlib.sha256(document_raw).hexdigest()or p['base_case_sha256']!=hashlib.sha256(base_raw).hexdigest()or p['base_run_sha256']!=base_run.sha256):
        raise ScenarioRevisionConflict('proposal references another document/case/run')
    base=json.loads(base_raw)
    if p['new_case_id']==base['case_id']or p['new_run_id']==base['run_id']:raise ValidationError('distinct candidate case and run identities required')
    candidate=json.loads(canonical(base));audit=[]
    for change in p['patches']:
        hits=[i for i,row in enumerate(candidate['metric_values'])if row['metric_id']==change['metric_id']and row['scenario_id']==change['scenario_id']]
        if len(hits)!=1:raise ScenarioRevisionConflict('target must exist once in exact base')
        index=hits[0];row=candidate['metric_values'][index]
        if canonical(row['value'])!=canonical(change['expected_before']):raise ScenarioRevisionConflict('expected-before representation changed')
        audit.append({'locator':'/metric_values/'+str(index)+'/value','metric_id':change['metric_id'],'scenario_id':change['scenario_id'],
            'before':row['value'],'after':change['proposed_after'],'reason':change['reason']})
        row['value']=change['proposed_after']
    candidate['case_id']=p['new_case_id'];candidate['run_id']=p['new_run_id']
    candidate_raw=(canonical(candidate)+'\n').encode();run=simulate_scenario_thresholds(document_raw,candidate_raw)
    payload={'component':'T16','purpose':'synthetic_development_only','engine_sha256':ENGINE_SHA256,
        'proposal_id':p['proposal_id'],'document_sha256':p['document_sha256'],'base_case_sha256':p['base_case_sha256'],
        'base_run_sha256':base_run.sha256,'proposal_source_sha256':hashlib.sha256(proposal_raw).hexdigest(),
        'author_label':p['author_label'],'author_identity_verified':False,'reason':p['reason'],'declared_evidence_refs':p['evidence_refs'],
        'evidence_refs_verified':False,'changes':audit,'candidate_case_json':candidate_raw.decode(),
        'candidate_case_sha256':hashlib.sha256(candidate_raw).hexdigest(),'candidate_run':asdict(run),
        'base_simulation_result':base_run.payload['simulation_result'],'candidate_simulation_result':run.payload['simulation_result'],
        'base_blockers':base_run.payload['simulation_blockers'],'candidate_blockers':run.payload['simulation_blockers'],
        'user_policy_reference':run.payload['user_policy_reference'],'proposal_accepted':False,'original_modified':False,
        'automatic_variable_optimization':False,'professional_review_authenticated':False,'decision':'PENDING',
        'production_authorized':False,'full_miniuw_completed':False}
    encoded=canonical(payload);return ScenarioReviewRun(encoded,digest(encoded))
