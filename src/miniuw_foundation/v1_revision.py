"""T88 explicit full-case synthetic revision comparison, never candidate generation."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re

from .drafts import ValidationError,canonical,digest,nonempty
from .debt_service import _fraction,rational
from .expense_cash_detail import _json,_exact
from .evidence_currency import timestamp
from .v1_case import parse_v1_case,run_v1_case

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T88-T89.md'
TOTALS=('gross_contributions','gross_distributions','net_cash_profit','equity_multiple')
MAX_CHANGES=4096


def sha(raw):return hashlib.sha256(raw).hexdigest()


def parse_comparison(raw):
    p=_json(raw,65536)
    _exact(p,{'schema','comparison_id','reference_case_sha256','candidate_case_sha256','comparison_basis_ref'})
    if p['schema']!='miniuw.synthetic-v1-revision-comparison.v1':raise ValidationError('supported comparison schema required')
    nonempty(p['comparison_id'],'comparison_id')
    if not p['comparison_id'].startswith('SYNTHETIC-')or len(p['comparison_id'])>128:raise ValidationError('bounded synthetic comparison ID required')
    for key in ('reference_case_sha256','candidate_case_sha256'):
        if type(p[key])is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):raise ValidationError('exact case byte hash required')
    if p['comparison_basis_ref']is not None:nonempty(p['comparison_basis_ref'],'comparison_basis_ref')
    return p


def differences(before,after,limit=MAX_CHANGES):
    rows=[]
    def escaped(key):return str(key).replace('~','~0').replace('/','~1')
    def add(path,b,a,bexists=True,aexists=True):
        if len(rows)>=limit:raise ValidationError('comparison difference budget exceeded; no truncated inventory')
        rows.append(dict(pointer=path,before_exists=bexists,before=b,after_exists=aexists,after=a))
    def visit(b,a,path,depth=0):
        if depth>128:raise ValidationError('comparison nesting budget exceeded')
        if type(b)is not type(a):add(path,b,a)
        elif type(b)is dict and set(b)=={'numerator','denominator'}and set(a)==set(b):
            if b!=a:add(path,b,a)
        elif type(b)is dict:
            for k in sorted(set(b)|set(a)):
                child=path+'/'+escaped(k)
                if k not in b:add(child,None,a[k],False,True)
                elif k not in a:add(child,b[k],None,True,False)
                else:visit(b[k],a[k],child,depth+1)
        elif type(b)is list:
            for i in range(max(len(b),len(a))):
                child=path+'/'+str(i)
                if i>=len(b):add(child,None,a[i],False,True)
                elif i>=len(a):add(child,b[i],None,True,False)
                else:visit(b[i],a[i],child,depth+1)
        elif b!=a:add(path,b,a)
    visit(before,after,'');return rows


@dataclass(frozen=True)
class V1ComparisonRun:
    payload_json:str
    sha256:str

    @property
    def payload(self):return json.loads(self.payload_json)


def compare_v1_cases(reference_raw,candidate_raw,spec_raw):
    ref=parse_v1_case(reference_raw);candidate=parse_v1_case(candidate_raw);spec=parse_comparison(spec_raw)
    before=run_v1_case(reference_raw);after=run_v1_case(candidate_raw);bp,ap=before.payload,after.payload
    blockers=[]
    if spec['reference_case_sha256']!=sha(reference_raw):blockers.append('reference_case_hash_mismatch')
    if spec['candidate_case_sha256']!=sha(candidate_raw):blockers.append('candidate_case_hash_mismatch')
    if spec['comparison_basis_ref']is None:blockers.append('explicit_comparison_basis_missing')
    if ref['case_id']!=candidate['case_id']:blockers.append('case_identity_mismatch')
    if candidate['case_revision']<=ref['case_revision']:blockers.append('candidate_revision_must_be_later')
    if ref['profile']!=candidate['profile']:blockers.append('profile_mismatch')
    for key in ('deal_id','scenario_id','definition_set_revision'):
        if ref['context'][key]!=candidate['context'][key]:blockers.append('economic_context_mismatch:'+key)
    if timestamp(ref['as_of_UTC'])!=timestamp(candidate['as_of_UTC']):blockers.append('common_evaluation_instant_required')
    if ref['required_scenarios']!=candidate['required_scenarios']:blockers.append('required_scenario_inventory_mismatch')
    bs,cs=bp['current_project_return_story'],ap['current_project_return_story']
    for side,story in [('reference',bs),('candidate',cs)]:
        if story is None:blockers.append(side+'_current_projection_unavailable')
    if bs is not None and cs is not None:
        if bs['currency']!=cs['currency']:blockers.append('currency_mismatch')
        if bs['cash_horizon']!=cs['cash_horizon']:blockers.append('cash_horizon_mismatch')
        identity=lambda s:sorted((e['event_id'],e['date'],e['kind'],e['category'],e['currency'])for e in s['dated_events'])
        if identity(bs)!=identity(cs):blockers.append('dated_event_inventory_or_classification_mismatch')
    deltas=None;event_deltas=None;normalized=None
    if not blockers:
        delta=lambda b,a:rational(_fraction(a,1300)-_fraction(b,1300))
        deltas={k:delta(bs[k],cs[k])if bs[k]is not None and cs[k]is not None else None for k in TOTALS}
        by_id={e['event_id']:e for e in bs['dated_events']}
        event_deltas=[dict(event_id=e['event_id'],date=e['date'],category=e['category'],kind=e['kind'],currency=e['currency'],reference_amount=by_id[e['event_id']]['amount'],candidate_amount=e['amount'],delta=delta(by_id[e['event_id']]['amount'],e['amount']))for e in cs['dated_events']]
        bn,cn=bs['normalized_story'],cs['normalized_story'];normalized=dict(reference=bn,candidate=cn,deltas=None,blockers=[])
        keys=('basis_amount','reference_amount','basis_event_ids','basis_ref','scale_factor')
        if bn is None or cn is None:normalized['blockers'].append('normalization_missing')
        elif any(bn[k]!=cn[k]for k in keys):normalized['blockers'].append('normalization_basis_or_reference_mismatch')
        else:normalized['deltas']={k:delta(bn[k],cn[k])for k in ('total_contributions','total_distributions','net_cash_profit')}
    def side(case,run):
        p=run.payload
        return dict(case_id=case['case_id'],case_revision=case['case_revision'],case_source_sha256=p['case_source_sha256'],run_sha256=run.sha256,context=case['context'],as_of_UTC=case['as_of_UTC'],input_catalog_summary=p['input_catalog_summary'],blockers=p['blockers'],decision=p['decision'],current_project_return_story=p['current_project_return_story'],metrics=p['metrics'])
    p=dict(component='T88',schema='miniuw.synthetic-v1-revision-result.v1',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),comparison_spec_sha256=sha(spec_raw),comparison_id=spec['comparison_id'],comparison_basis_ref=spec['comparison_basis_ref'],
           reference=side(ref,before),candidate=side(candidate,after),input_changes=differences(ref,candidate),
           comparison_blockers=sorted(set(blockers)),state='comparable_synthetic_projections_decision_pending'if not blockers else'PENDING',
           delta_direction='candidate_minus_reference',projection_deltas=deltas,event_deltas=event_deltas,normalization_comparison=normalized,
           annual_IRR=dict(reference_roots=None if bs is None else bs['annual_irr_roots'],candidate_roots=None if cs is None else cs['annual_irr_roots'],selected_rate=None,rate_delta=None),
           isolated_variable_causality_claimed=False,chosen_candidate=None,decision='PENDING',professional_review_authenticated=False,financial_publication_authorized=False,independent_financial_audit=False,deployment_enabled=False,real_decisions_enabled=False)
    result=canonical(p);return V1ComparisonRun(result,digest(result))
