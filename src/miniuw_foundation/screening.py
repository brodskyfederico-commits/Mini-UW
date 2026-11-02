"""T11 comparison simulation with explicit per-case criteria; operational state stays PENDING."""
from dataclasses import dataclass
import hashlib,json
from pathlib import Path
from .drafts import ContextSeed,ValidationError,canonical,digest,template,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction

SCHEMA='miniuw.synthetic-screening-case.v1'
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
AGGREGATION='all_pass_any_fail_pending_blocks'
BASE={'metric_id','scenario_id','definition_ref','unit','currency','period_ref','quantity_kind','applicability','applicability_evidence_ref'}


def parse_screening_case(raw):
    if type(raw) is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded synthetic screening bytes required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except (UnicodeError,ValueError,RecursionError) as error:raise ValidationError('invalid screening JSON') from error
    if type(p) is not dict or set(p)!={'schema','context','case_id','criteria_revision','criteria_status','required_metrics','required_scenarios','metric_values','criteria','aggregation_rule','hypothetical_band_policy'} or p['schema']!=SCHEMA or p['criteria_status']!='synthetic_fixture_only':
        raise ValidationError('explicit synthetic screening schema and nonadopted criteria required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required') from error
    for key in ('case_id','criteria_revision'):nonempty(p[key],key)
    known={c['metric_id'] for c in template()[0]['investment_criteria']}
    for key in ('required_metrics','required_scenarios'):
        value=p[key]
        if type(value) is not list or not value or len(value)>32 or any(type(x) is not str or not x.strip() for x in value) or len(set(value))!=len(value):
            raise ValidationError('nonempty explicit unique metric/scenario inventory required')
    if not set(p['required_metrics'])<=known:raise ValidationError('unknown investment metric; bank conditions are separate')
    if p['aggregation_rule'] not in (None,AGGREGATION) or p['hypothetical_band_policy'] not in (None,'pending','fail'):
        raise ValidationError('unsupported or implicit simulation aggregation policy')
    for key in ('metric_values','criteria'):
        if type(p[key]) is not list or len(p[key])>320:raise ValidationError('bounded explicit record list required')
        seen=set()
        for record in p[key]:
            extra={'value'} if key=='metric_values' else {'pass_condition','fail_condition'}
            if type(record) is not dict or set(record)!=BASE|extra:raise ValidationError('exact comparison record fields required')
            if any(type(record[k]) is not str or not record[k].strip() for k in ('metric_id','scenario_id')):
                raise ValidationError('metric/scenario identities must be explicit text')
            pair=(record['metric_id'],record['scenario_id'])
            if pair in seen or pair[0] not in p['required_metrics'] or pair[1] not in p['required_scenarios']:
                raise ValidationError('duplicate or outside-inventory comparison record')
            seen.add(pair)
            for name in BASE-{'metric_id','scenario_id'}:
                if record[name] is not None and (type(record[name]) is not str or not record[name].strip()):raise ValidationError('explicit metadata or null required')
            if record['quantity_kind'] not in (None,'scalar','money','money_per_period'):
                raise ValidationError('explicit supported quantity kind or unresolved null required')
            if record['applicability'] not in ('applicable','not_applicable','unresolved'):
                raise ValidationError('explicit applicability required')
            if key=='metric_values':_fraction(record['value'])
            else:
                for name in ('pass_condition','fail_condition'):
                    condition=record[name]
                    if type(condition) is not dict or set(condition)!={'operator','threshold'}:raise ValidationError('explicit condition/operator/threshold required')
                    if condition['operator'] is not None and type(condition['operator']) is not str:raise ValidationError('operator must be explicit text or null')
                    _fraction(condition['threshold'])
    return p


def definition_sources():
    root=Path(__file__).resolve().parents[2]
    refs=[('docs/decision-input-contract.md','Antes de clasificar'),
        ('docs/model-decision-audit.md','La confirmación del usuario impone'),
        ('docs/model-decision-audit.md','Resultados de comparación candidatos')]
    result=[]
    for path,marker in refs:
        raw=(root/path).read_bytes();lines=raw.decode().splitlines()
        hits=[i+1 for i,line in enumerate(lines) if line.startswith(marker)]
        if len(hits)!=1:raise ValidationError('comparison definition locator changed')
        result.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return result


def user_policy_reference():
    path=Path(__file__).resolve().parents[2]/'docs/pending-band-policy-decision.json'
    raw=path.read_bytes();policy=json.loads(raw)
    if policy.get('status')!='selected_by_user' or policy.get('current_adopted_option')!='retain_pending_in_band':
        raise ValidationError('explicit user band-policy direction unavailable or changed')
    return {'path':'docs/pending-band-policy-decision.json','sha256':hashlib.sha256(raw).hexdigest(),'decision_id':policy['decision_id']}


def _compare(value,threshold,operator):
    return {'>':value>threshold,'>=':value>=threshold,'<':value<threshold,'<=':value<=threshold}[operator]


def _overlap(p,f):
    lowops=('>','>=');highops=('<','<=')
    if (p['operator'] in lowops)==(f['operator'] in lowops):return True
    lower,upper=(p,f) if p['operator'] in lowops else (f,p)
    a,b=_fraction(lower['threshold']),_fraction(upper['threshold'])
    return a<b or (a==b and lower['operator']=='>=' and upper['operator']=='<=')


@dataclass(frozen=True)
class ScreeningRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def _simulate_screening(raw,what_if_only):
    p=parse_screening_case(raw)
    policy_ref=user_policy_reference()
    values={(r['metric_id'],r['scenario_id']):(i,r) for i,r in enumerate(p['metric_values'])}
    criteria={(r['metric_id'],r['scenario_id']):(i,r) for i,r in enumerate(p['criteria'])}
    results=[];global_blockers=[]
    for metric in p['required_metrics']:
        for scenario in p['required_scenarios']:
            key=(metric,scenario);v=values.get(key);c=criteria.get(key);blockers=[];state='PENDING'
            if v is None:blockers.append('metric_record_missing')
            if c is None:blockers.append('criterion_record_missing')
            if v and c:
                value,criterion=v[1],c[1]
                for field in ('definition_ref','unit','period_ref','quantity_kind'):
                    if value[field] is None or criterion[field] is None or value[field]!=criterion[field]:blockers.append(field+'_missing_or_mismatch')
                if value['currency']!=criterion['currency']:blockers.append('currency_mismatch')
                if value['quantity_kind'] in ('money','money_per_period') and (value['currency'] is None or criterion['currency'] is None):blockers.append('currency_required_but_missing')
                if value['applicability']!=criterion['applicability'] or value['applicability']=='unresolved':blockers.append('applicability_unresolved_or_conflicting')
                if value['applicability']=='not_applicable' and criterion['applicability']=='not_applicable':
                    if not value['applicability_evidence_ref'] or not criterion['applicability_evidence_ref']:blockers.append('not_applicable_evidence_missing')
                    if not blockers:state='NOT_APPLICABLE_DECLARED'
                else:
                    if value['value'] is None:blockers.append('metric_value_missing')
                    for name in ('pass_condition','fail_condition'):
                        condition=criterion[name]
                        if condition['operator'] not in ('>','>=','<','<=') or condition['threshold'] is None:blockers.append(name+'_rule_missing_or_unsupported')
                    if not blockers:
                        pc,fc=criterion['pass_condition'],criterion['fail_condition']
                        if _overlap(pc,fc):state='CONFLICT';blockers.append('pass_fail_regions_overlap')
                        else:
                            amount=_fraction(value['value'])
                            ispass=_compare(amount,_fraction(pc['threshold']),pc['operator'])
                            isfail=_compare(amount,_fraction(fc['threshold']),fc['operator'])
                            state='PASS_CONDITION' if ispass else 'FAIL_CONDITION' if isfail else 'BAND'
            if blockers:global_blockers.extend(metric+':'+scenario+':'+b for b in blockers)
            results.append({'metric_id':metric,'scenario_id':scenario,'state':state,'blockers':sorted(set(blockers)),
                'metric_locator':None if not v else '/metric_values/'+str(v[0])+'/value',
                'criterion_locator':None if not c else '/criteria/'+str(c[0]),
                'metric_record':None if not v else v[1],'criterion_record':None if not c else c[1]})
    states=[r['state'] for r in results]
    if p['aggregation_rule'] is None:global_blockers.append('aggregation_rule_missing')
    if 'BAND' in states:
        if not what_if_only:global_blockers.append('intermediate_band_pending_professional_review')
        elif p['hypothetical_band_policy']!='fail':global_blockers.append('band_is_pending_by_explicit_fixture_policy' if p['hypothetical_band_policy']=='pending' else 'band_policy_missing')
    applicable=[s for s in states if s!='NOT_APPLICABLE_DECLARED']
    if not applicable:global_blockers.append('no_applicable_comparisons')
    result='PENDING'
    if not global_blockers:
        result='FAIL' if any(s in ('FAIL_CONDITION','BAND') for s in applicable) else 'PASS'
    payload={'component':'T11','purpose':'synthetic_development_only','engine_sha256':ENGINE_SHA256,
        'definition_sources':definition_sources(),'source_sha256':hashlib.sha256(raw).hexdigest(),'context':p['context'],'case_id':p['case_id'],
        'criteria_revision':p['criteria_revision'],'required_metrics':p['required_metrics'],
        'required_scenarios':p['required_scenarios'],'aggregation_rule':p['aggregation_rule'],
        'hypothetical_band_policy':p['hypothetical_band_policy'],'comparisons':results,
        'what_if_only':what_if_only,'band_policy_applied':'hypothetical_preview' if what_if_only else 'pending_professional_review',
        'user_policy_reference':policy_ref,
        'professional_review_needed_for_band':('BAND' in states),
        'pending_review_metrics':[{'metric_id':r['metric_id'],'scenario_id':r['scenario_id'],'metric_locator':r['metric_locator'],'criterion_locator':r['criterion_locator']} for r in results if r['state']=='BAND'],
        'variables_automatically_adjusted':False,
        'simulation_result':result,'simulation_blockers':sorted(set(global_blockers)),
        'criteria_adopted':False,'metric_values_financially_verified':False,'declared_inventory_verified':False,
        'review_authenticated':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(payload);return ScreeningRun(encoded,digest(encoded))


def simulate_screening(raw):
    """Canonical synthetic screening follows the explicit user band decision."""
    return _simulate_screening(raw,False)


def simulate_policy_whatif(raw):
    """Explicit research preview only; cannot be saved as canonical screening evidence."""
    return _simulate_screening(raw,True)
