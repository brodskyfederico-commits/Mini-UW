"""T15 source-specific scenario conditions; experiments remain non-operational."""
from dataclasses import asdict,dataclass
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import hashlib,json
from .drafts import canonical,digest,ValidationError
from .debt_service import _fraction
from .screening import simulate_screening,ENGINE_SHA256 as SCREEN_ENGINE_SHA256
from .threshold_rehearsal import (read_documented_thresholds,parse_rehearsal,prepare_rehearsal,NS,
    ENGINE_SHA256 as SOURCE_ENGINE_SHA256)

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class ScenarioThresholdRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def _verdict_sources(source_raw):
    with ZipFile(BytesIO(source_raw))as z:root=ET.fromstring(z.read('word/document.xml'))
    paragraphs=[''.join(t.text or ''for t in p.findall('.//w:t',NS))for p in root.findall('.//w:p',NS)]
    refs=[]
    for literal in ['Any Base metric is worse than its FAIL level.','Every Base and Downside metric meets its PASS level.']:
        hits=[i for i,p in enumerate(paragraphs)if p==literal]
        if len(hits)!=1:raise ValidationError('unique documented verdict rule required')
        refs.append({'literal':literal,'locator':f'word/document.xml/descendant-paragraph[{hits[0]}]'})
    return refs


def simulate_scenario_thresholds(source_raw,case_raw):
    profile=read_documented_thresholds(source_raw);p=parse_rehearsal(case_raw)
    refs=_verdict_sources(source_raw)
    # Reuse the existing exact Base comparator without changing its code or archived runs.
    base=json.loads(canonical(p));base['required_scenarios']=['Base']
    base['metric_values']=[r for r in base['metric_values']if r['scenario_id']=='Base']
    _,compiled=prepare_rehearsal(source_raw,canonical(base).encode());base_run=simulate_screening(compiled)
    comparisons=base_run.payload['comparisons'];blockers=list(base_run.payload['simulation_blockers'])
    values={(r['metric_id'],r['scenario_id']):r for r in p['metric_values']}
    if 'Downside'in p['required_scenarios']:
        for metric in profile['metrics']:
            key=(metric['metric_id'],'Downside');record=values.get(key);reasons=[];state='PENDING'
            threshold=metric['pass_downside']
            if threshold is None:
                reasons.append('pass_condition_and_applicability_unresolved')
            elif record is None:reasons.append('metric_record_missing')
            elif record['value']is None:reasons.append('metric_value_missing')
            else:
                value=_fraction(record['value']);limit=_fraction(threshold)
                passed=value>=limit if metric['pass_operator']=='>='else value<=limit
                state='PASS_CONDITION'if passed else'PASS_MISS_PENDING'
                if not passed:reasons.append('downside_pass_not_met_pending_review')
            blockers.extend(metric['metric_id']+':Downside:'+reason for reason in reasons)
            comparisons.append({'metric_id':metric['metric_id'],'scenario_id':'Downside','state':state,'blockers':reasons,
                'metric_record':record,'pass_condition':{'operator':metric['pass_operator']if threshold is not None else None,'threshold':threshold},
                'pass_source_locator':metric['source_locators']['pass_downside'],
                'fail_condition':None,'fail_condition_required_by_profile':False,
                'applicability':'unresolved'if threshold is None else'applicable_for_synthetic_experiment'})
    simulation='PENDING'
    if not blockers:simulation='FAIL'if any(r['state']=='FAIL_CONDITION'for r in comparisons)else'PASS'
    payload={'component':'T15','purpose':'source_specific_synthetic_scenario_comparison',
        'engine_sha256':ENGINE_SHA256,'source_engine_sha256':SOURCE_ENGINE_SHA256,'base_comparator_engine_sha256':SCREEN_ENGINE_SHA256,
        'source_sha256':profile['source_sha256'],'case_source_sha256':hashlib.sha256(case_raw).hexdigest(),
        'source_profile':profile,'source_verdict_references':refs,'base_run':asdict(base_run),
        'context':{'deal_id':p['deal_id'],'case_id':p['case_id'],'run_id':p['run_id']},
        'required_scenarios':p['required_scenarios'],'scope':'Base-only experiment'if p['required_scenarios']==['Base']else'Base/Downside experiment',
        'comparisons':comparisons,'simulation_result':simulation,'simulation_blockers':sorted(set(blockers)),
        'user_policy_reference':base_run.payload['user_policy_reference'],'definition_sources':base_run.payload['definition_sources'],
        'asking_downside_applicability_resolved':False if 'Downside'in p['required_scenarios']else None,
        'synthetic_declared_compatible_metadata_only':True,'thresholds_adopted':False,'financial_values_verified':False,
        'decision':'PENDING','run_ready':False,'review_authenticated':False,'production_authorized':False,'full_miniuw_completed':False}
    encoded=canonical(payload);return ScenarioThresholdRun(encoded,digest(encoded))
