"""T13 explicit synthetic review branches; labels are never authenticated approvals."""
from dataclasses import asdict,dataclass
import hashlib,json,re
from pathlib import Path
from .drafts import ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction
from .screening import ScreeningRun,parse_screening_case,simulate_screening,user_policy_reference

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-screening-review-proposal.v1'
KEYS={'schema','proposal_id','base_source_sha256','base_run_sha256','new_case_id','new_run_id',
    'new_criteria_revision','author_label','proposal_reason','evidence_refs','patches','status'}
PATCH_KEYS={'table','metric_id','scenario_id','field','expected_before','proposed_after','reason'}
CRITERION_FIELDS={'pass_condition.threshold','fail_condition.threshold','pass_condition.operator','fail_condition.operator'}


class ReviewRevisionConflict(ValidationError):
    pass


def parse_review_proposal(raw):
    if type(raw) is not bytes or not raw or len(raw)>1_048_576:
        raise ValidationError('bounded nonempty review proposal bytes required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except (UnicodeError,ValueError,RecursionError) as error:raise ValidationError('invalid proposal JSON') from error
    if type(p) is not dict or set(p)!=KEYS or p['schema']!=SCHEMA or p['status']!='proposal_only':
        raise ValidationError('exact synthetic proposal schema/status required; no approval fields')
    for key in ('proposal_id','new_case_id','new_run_id','author_label','proposal_reason'):
        nonempty(p[key],key)
    if not p['proposal_id'].startswith('SYNTHETIC-'):
        raise ValidationError('explicit synthetic proposal identity required')
    for key in ('base_source_sha256','base_run_sha256'):
        if type(p[key]) is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):
            raise ValidationError('exact base source/run hashes required')
    if p['new_criteria_revision'] is not None:nonempty(p['new_criteria_revision'],'new_criteria_revision')
    if type(p['evidence_refs']) is not list or not 1<=len(p['evidence_refs'])<=32:
        raise ValidationError('explicit declared evidence references required')
    for ref in p['evidence_refs']:nonempty(ref,'evidence_ref')
    if type(p['patches']) is not list or not 1<=len(p['patches'])<=128:
        raise ValidationError('explicit bounded nonempty patch batch required')
    seen=set()
    for patch in p['patches']:
        if type(patch) is not dict or set(patch)!=PATCH_KEYS:
            raise ValidationError('exact explicit patch fields required')
        for key in ('table','metric_id','scenario_id','field','reason'):nonempty(patch[key],key)
        if ((patch['table']=='metric_values' and patch['field']!='value')
            or (patch['table']=='criteria' and patch['field'] not in CRITERION_FIELDS)
            or patch['table'] not in ('metric_values','criteria')):
            raise ValidationError('only existing metric values and criterion conditions may be proposed')
        identity=tuple(patch[k] for k in ('table','metric_id','scenario_id','field'))
        if identity in seen:raise ValidationError('duplicate patch; no last-wins edits')
        seen.add(identity)
        for key in ('expected_before','proposed_after'):
            value=patch[key]
            if patch['field'].endswith('operator'):
                if value is not None:nonempty(value,'operator')
            else:_fraction(value)
        if canonical(patch['expected_before'])==canonical(patch['proposed_after']):
            raise ValidationError('no-op patch is not a proposed variable change')
    return p


@dataclass(frozen=True)
class ReviewProposalRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def candidate_raw(self):return self.payload['candidate_source_json'].encode('utf-8')
    @property
    def candidate_run(self):return ScreeningRun(**self.payload['candidate_run'])


def evaluate_review_proposal(base_raw,base_run,proposal_raw):
    base=parse_screening_case(base_raw)
    if type(base_run) is not ScreeningRun or simulate_screening(base_raw)!=base_run:
        raise ReviewRevisionConflict('base screening no longer reproduces; refresh the proposal base')
    p=parse_review_proposal(proposal_raw)
    if p['base_source_sha256']!=hashlib.sha256(base_raw).hexdigest() or p['base_run_sha256']!=base_run.sha256:
        raise ReviewRevisionConflict('proposal was written for another source/run revision')
    if p['new_case_id']==base['case_id'] or p['new_run_id']==base['context']['run_id']:
        raise ValidationError('distinct explicit candidate case and run identities required')
    changes_criteria=any(change['table']=='criteria' for change in p['patches'])
    if changes_criteria:
        if p['new_criteria_revision'] is None or p['new_criteria_revision']==base['criteria_revision']:
            raise ValidationError('criterion proposals need a new explicit criterion revision')
    elif p['new_criteria_revision'] is not None:
        raise ValidationError('metric-only proposal must preserve criteria revision')
    candidate=json.loads(canonical(base));audit=[]
    for patch in p['patches']:
        table=candidate[patch['table']]
        matches=[i for i,row in enumerate(table) if row['metric_id']==patch['metric_id'] and row['scenario_id']==patch['scenario_id']]
        if len(matches)!=1:raise ReviewRevisionConflict('target metric/scenario is absent from the base')
        index=matches[0];parts=patch['field'].split('.');parent=table[index]
        for part in parts[:-1]:parent=parent[part]
        old=parent[parts[-1]]
        if canonical(old)!=canonical(patch['expected_before']):
            raise ReviewRevisionConflict('expected-before does not match exact source representation')
        parent[parts[-1]]=patch['proposed_after']
        audit.append({'locator':'/'+patch['table']+'/'+str(index)+'/'+'/'.join(parts),
            'metric_id':patch['metric_id'],'scenario_id':patch['scenario_id'],
            'before':old,'after':patch['proposed_after'],'reason':patch['reason']})
    candidate['case_id']=p['new_case_id'];candidate['context']['run_id']=p['new_run_id']
    if changes_criteria:candidate['criteria_revision']=p['new_criteria_revision']
    candidate_raw=(canonical(candidate)+'\n').encode('utf-8')
    proposed=simulate_screening(candidate_raw)
    payload={'component':'T13','purpose':'synthetic_development_only','engine_sha256':ENGINE_SHA256,
        'proposal_id':p['proposal_id'],'proposal_source_sha256':hashlib.sha256(proposal_raw).hexdigest(),
        'base_source_sha256':p['base_source_sha256'],'base_run_sha256':base_run.sha256,
        'author_label':p['author_label'],'author_identity_verified':False,
        'proposal_reason':p['proposal_reason'],'declared_evidence_refs':p['evidence_refs'],'evidence_refs_verified':False,
        'changes':audit,'base_simulation_result':base_run.payload['simulation_result'],
        'candidate_source_json':candidate_raw.decode('utf-8'),
        'candidate_source_sha256':hashlib.sha256(candidate_raw).hexdigest(),'candidate_run':asdict(proposed),
        'candidate_simulation_result':proposed.payload['simulation_result'],
        'user_policy_reference':user_policy_reference(),'proposal_accepted':False,'professional_review_authenticated':False,
        'original_source_modified':False,'automatic_variable_optimization':False,
        'criteria_adopted':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(payload);return ReviewProposalRun(encoded,digest(encoded))
