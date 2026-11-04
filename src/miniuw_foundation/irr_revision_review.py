"""T102 replay two T101 snapshots for review, with no candidate adoption."""
from dataclasses import dataclass
from pathlib import Path
import json

from .drafts import ValidationError,canonical,digest
from .debt_service import _fraction,rational
from .expense_cash_detail import _json
from .scheduled_expense_case import sha
from .evidence_currency import timestamp
from .operating_noi import _bounded,ArithmeticBudgetError
from .irr_interval_output import IRRIntervalRun,assemble_irr_interval_output
from .v1_revision import (parse_comparison,differences,TOTALS,ENGINE_SHA256 as DIFF_ENGINE_SHA256)

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T102.md'
UTF8_FIELDS={'scheduled_case_utf8','base_case_utf8','binding_utf8','registry_utf8','schedule_sources_utf8','policy_books_utf8'}


def _expanded(value,depth=0):
    if depth>64:raise ValidationError('review decoded-source nesting budget exceeded')
    if type(value)is dict:
        result={}
        for key,v in value.items():
            if key in UTF8_FIELDS:
                if type(v)is str:v=_json(v.encode(),48*1024*1024)
                elif type(v)is list:v=[_json(s.encode(),48*1024*1024)for s in v]
                else:raise ValidationError('known JSON UTF8 source representation required')
                result[key+'::json']=_expanded(v,depth+1)
            else:result[key]=_expanded(v,depth+1)
        return result
    if type(value)is list:return [_expanded(v,depth+1)for v in value]
    return value


def expanded_source(raw):return _expanded(_json(raw,48*1024*1024))


def _base(source):return source['scheduled_case_utf8::json']['base_case_utf8::json']


def _comparison_blockers(ref,candidate,before,after,spec,reference_raw,candidate_raw):
    blockers=[]
    for key,raw in (('reference_case_sha256',reference_raw),('candidate_case_sha256',candidate_raw)):
        if spec[key]!=sha(raw):blockers.append(key+'_mismatch')
    if spec['comparison_basis_ref']is None:blockers.append('explicit_comparison_basis_missing')
    if ref['case_id']!=candidate['case_id']:blockers.append('case_identity_mismatch')
    if candidate['case_revision']<=ref['case_revision']:blockers.append('candidate_revision_must_be_later')
    if ref['profile']!=candidate['profile']:blockers.append('profile_mismatch')
    for key in ('deal_id','scenario_id','definition_set_revision'):
        if ref['context'][key]!=candidate['context'][key]:blockers.append('economic_context_mismatch:'+key)
    if timestamp(ref['as_of_UTC'])!=timestamp(candidate['as_of_UTC']):blockers.append('common_evaluation_instant_required')
    if ref['required_scenarios']!=candidate['required_scenarios']:blockers.append('required_scenario_inventory_mismatch')
    for side,story in (('reference',before),('candidate',after)):
        if story is None:blockers.append(side+'_current_projection_unavailable')
    if before is not None and after is not None:
        for key in ('currency','equity_level','cash_horizon'):
            if before[key]!=after[key]:blockers.append(key+'_mismatch')
        identity=lambda s:sorted((e['event_id'],e['date'],e['kind'],e['category'],e['currency'])for e in s['dated_events'])
        if identity(before)!=identity(after):blockers.append('dated_event_inventory_or_classification_mismatch')
    return sorted(set(blockers))


@dataclass(frozen=True)
class IRRRevisionReviewRun:
    payload_json:str
    sha256:str
    reference_run:IRRIntervalRun
    candidate_run:IRRIntervalRun

    @property
    def payload(self):return json.loads(self.payload_json)


def _numeric_comparison(bs,cs):
    try:
        delta=lambda b,a:rational(_bounded(_fraction(a,1300)-_fraction(b,1300)))
        totals={k:delta(bs[k],cs[k])if bs[k]is not None and cs[k]is not None else None for k in TOTALS}
        prior={e['event_id']:e for e in bs['dated_events']}
        events=[dict(event_id=e['event_id'],date=e['date'],kind=e['kind'],category=e['category'],currency=e['currency'],
            reference_amount=prior[e['event_id']]['amount'],candidate_amount=e['amount'],delta=delta(prior[e['event_id']]['amount'],e['amount']))for e in cs['dated_events']]
        bn,cn=bs['normalized_story'],cs['normalized_story'];normalized=dict(reference=bn,candidate=cn,deltas=None,blockers=[])
        keys=('reference_amount','basis_amount','basis_event_ids','basis_ref','scale_factor')
        if bn is None or cn is None or bn['scale_factor']is None or cn['scale_factor']is None:normalized['blockers'].append('normalization_missing')
        elif any(bn[k]!=cn[k]for k in keys):normalized['blockers'].append('normalization_basis_or_reference_mismatch')
        else:normalized['deltas']={k:delta(bn[k],cn[k])if bn[k]is not None and cn[k]is not None else None for k in ('total_contributions','total_distributions','net_cash_profit')}
        return totals,events,normalized,[]
    except ArithmeticBudgetError:
        return None,None,None,['delta_exact_arithmetic_budget_exceeded']


def _from_verified_pair(reference_raw,candidate_raw,spec_raw,before,after):
    ref_source=expanded_source(reference_raw);new_source=expanded_source(candidate_raw)
    ref,new=_base(ref_source),_base(new_source);spec=parse_comparison(spec_raw)
    bp,ap=before.payload,after.payload;bs,cs=bp['current_project_return_story'],ap['current_project_return_story']
    blockers=_comparison_blockers(ref,new,bs,cs,spec,reference_raw,candidate_raw)
    deltas=event_deltas=normalized=None
    if not blockers:
        deltas,event_deltas,normalized,numeric_blockers=_numeric_comparison(bs,cs)
        blockers+=numeric_blockers
    changes=differences(ref_source,new_source)
    prefix='/scheduled_case_utf8::json/base_case_utf8::json/criteria/'
    def side(case,run):
        p=run.payload;story=p['current_project_return_story']
        return dict(case_id=case['case_id'],case_revision=case['case_revision'],source_sha256=p['case_source_sha256'],run_sha256=run.sha256,
            context=p['context'],evaluated_as_of_UTC=p['evaluated_as_of_UTC'],current_story_available=story is not None,
            current_project_return_story=story,IRR_interval_condition=p['IRR_interval_comparison'],metrics=p['metrics'],
            blockers=p['blockers'],input_catalog_summary=p['input_catalog_summary'],screening_simulation_result=p['screening_simulation_result'],decision=p['decision'])
    result=dict(component='T102',schema='miniuw.synthetic-IRR-revision-review.v1',engine_sha256=ENGINE_SHA256,
        diff_engine_sha256=DIFF_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),comparison_id=spec['comparison_id'],
        comparison_spec_sha256=sha(spec_raw),comparison_basis_ref=spec['comparison_basis_ref'],
        reference_snapshot=side(ref,before),candidate_snapshot=side(new,after),source_bytes_equal=reference_raw==candidate_raw,
        decoded_source_changes=changes,criterion_source_changes=[r for r in changes if r['pointer'].startswith(prefix)],
        financial_story_changes=differences(bs,cs),comparison_blockers=blockers,
        state='comparable_synthetic_candidate_review'if not blockers else'PENDING',delta_direction='candidate_minus_reference',
        projection_deltas=deltas,event_deltas=event_deltas,normalization_comparison=normalized,
        annual_IRR=dict(reference_roots=None if bs is None else bs['annual_irr_roots'],candidate_roots=None if cs is None else cs['annual_irr_roots'],selected_rate=None,rate_delta=None),
        source_or_rule_automatically_adjusted=False,isolated_variable_causality_claimed=False,candidate_generated=False,
        candidate_adopted=False,active_revision_changed=False,chosen_candidate=None,reference_snapshot_is_candidate_fallback=False,
        professional_review_authenticated=False,financial_publication_authorized=False,independent_financial_audit=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(result);return IRRRevisionReviewRun(value,digest(value),before,after)


def compare_irr_revisions(reference_raw,candidate_raw,spec_raw):
    # Complete independent replays; no historical figures are installed as candidate output.
    before=assemble_irr_interval_output(reference_raw);after=assemble_irr_interval_output(candidate_raw)
    return _from_verified_pair(reference_raw,candidate_raw,spec_raw,before,after)


def review_text(run):
    p=run.payload;b,a=p['reference_snapshot'],p['candidate_snapshot']
    rows=['MINI-UW | REVISION CANDIDATA SINTETICA','DECISION PENDIENTE | Candidato no adoptado; sin despliegue ni decisiones reales.',
        'Referencia: revision '+str(b['case_revision'])+' | UTC '+b['evaluated_as_of_UTC']+' | '+b['source_sha256'],
        'Candidato: revision '+str(a['case_revision'])+' | UTC '+a['evaluated_as_of_UTC']+' | '+a['source_sha256'],
        'Ensayo IRR: '+b['IRR_interval_condition']['row_state']+' -> '+a['IRR_interval_condition']['row_state'],
        'Diferencias candidato menos referencia (racionales exactos): '+canonical(p['projection_deltas']),
        'Bloqueos de comparacion: '+canonical(p['comparison_blockers']),
        'Cambios logicos de fuente: '+str(len(p['decoded_source_changes']))+'; cambios de criterio: '+str(len(p['criterion_source_changes'])),
        'Cambios en historia financiera: '+str(len(p['financial_story_changes'])),
        'Las fuentes/evidencia/revisiones tambien pueden cambiar. No se afirma causalidad exclusiva.',
        'Si el candidato esta bloqueado, la referencia es otro snapshot y no lo sustituye.',
        'Cambios de criterio: '+canonical(p['criterion_source_changes']),
        'Fuentes, cambios completos y pruebas reproducibles incluidos en los JSON del paquete.',
        'El PDF es exclusivamente del candidato. No hay aprobacion o version activa nueva.']
    return ('\n'.join(rows)+'\n').encode()
