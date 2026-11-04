"""T101 one synthetic IRR condition over a verified annual enclosure, not a deal PASS."""
from dataclasses import dataclass
from pathlib import Path
import json

from .drafts import ValidationError,canonical,digest
from .debt_service import _fraction,rational
from .irr_checked_output import IRRCheckedRun,assemble_irr_checked_output
from .screening import _overlap,user_policy_reference,ENGINE_SHA256 as SCREEN_ENGINE_SHA256
from .scheduled_expense_case import sha
from .long_horizon_report import _render_verified as _base_summary,ENGINE_SHA256 as SUMMARY_ENGINE_SHA256
from .synthetic_onepager import _pdf,_pdf_string,PreviewLayoutError
from .v1_report import V1Report

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T101.md'
VALUE_DEFINITION='SYNTHETIC-ANNUAL-PERIODIC-IRR-ENCLOSURE-v1'
OPERATORS=('>','>=','<','<=')


def _enclosure(raw):
    if type(raw)is not dict or set(raw)!={'lower','upper','lower_closed','upper_closed'}:
        raise ValidationError('exact enclosure endpoints and closure required')
    lo,hi=_fraction(raw['lower'],1300),_fraction(raw['upper'],1300)
    if lo is None or hi is None or type(raw['lower_closed'])is not bool or type(raw['upper_closed'])is not bool:
        raise ValidationError('known rational enclosure and boolean closure required')
    if lo>hi or lo==hi and not(raw['lower_closed']and raw['upper_closed']):
        raise ValidationError('nonempty ordered enclosure required')
    return lo,hi,raw['lower_closed'],raw['upper_closed']


def condition_relation(enclosure,threshold,operator):
    """Exact every/none/mixed on a nonempty rational enclosure."""
    lo,hi,lc,hc=_enclosure(enclosure);t=_fraction(threshold,1300)
    if t is None or operator not in OPERATORS:raise ValidationError('explicit supported condition required')
    if operator=='>=':
        every=lo>=t;none=hi<t or hi==t and not hc
    elif operator=='>':
        every=lo>t or lo==t and not lc;none=hi<=t
    elif operator=='<=':
        every=hi<=t;none=lo>t or lo==t and not lc
    else:
        every=hi<t or hi==t and not hc;none=lo>=t
    return 'every'if every else'none'if none else'mixed'


def _annual_enclosure(story,evidence):
    if story is None or evidence is None:return None,['current_projection_or_IRR_evidence_unavailable']
    r=story['periodic_irr']
    if r is None or r['status']!='complete_synthetic':return None,['complete_periodic_root_inventory_required']
    if r['distinct_positive_discount_roots']!=1 or len(r['roots'])!=1:
        return None,['unique_distinct_periodic_root_required_without_selection']
    annual=story['annual_irr_roots']
    if len(annual)!=1 or evidence['annualization_blockers']:
        return None,['compatible_current_annual_root_required']
    row=annual[0]
    if row['exact_annual_rate']is not None:
        interval=dict(lower=row['exact_annual_rate'],upper=row['exact_annual_rate'],lower_closed=True,upper_closed=True)
    elif row['annual_rate_interval']is not None:interval=row['annual_rate_interval']
    else:return None,['current_annual_enclosure_missing']
    _enclosure(interval);return interval,[]


def _compare(interval,criterion,expected_period):
    blockers=[];relations={};state='PENDING'
    for key,expected in (('definition_ref',VALUE_DEFINITION),('unit','fraction'),('period_ref',expected_period)):
        if expected is None or criterion[key]!=expected:blockers.append(key+'_missing_or_mismatch')
    if criterion['source_ref']is None:blockers.append('criterion_source_ref_missing')
    for name in ('pass_condition','fail_condition'):
        c=criterion[name]
        if c['operator']not in OPERATORS or c['threshold']is None:blockers.append(name+'_rule_missing_or_unsupported')
    if interval is None:blockers.append('current_unique_annual_enclosure_unavailable')
    if not blockers:
        pc,fc=criterion['pass_condition'],criterion['fail_condition']
        if _overlap(pc,fc):state='CONFLICT';blockers.append('pass_fail_regions_overlap')
        else:
            relations={name:condition_relation(interval,criterion[name]['threshold'],criterion[name]['operator'])
                for name in ('pass_condition','fail_condition')}
            a,b=relations['pass_condition'],relations['fail_condition']
            if(a,b)==('every','none'):state='PASS_CONDITION'
            elif(a,b)==('none','every'):state='FAIL_CONDITION'
            elif(a,b)==('none','none'):state='BAND';blockers.append('intermediate_band_pending_professional_review')
            else:blockers.append('IRR_enclosure_crosses_criterion_boundary')
    return state,relations,sorted(set(blockers))


@dataclass(frozen=True)
class IRRIntervalRun:
    payload_json:str
    sha256:str
    parent_run:IRRCheckedRun

    @property
    def payload(self):return json.loads(self.payload_json)


def _from_verified_irr(parent):
    p=parent.payload;story=p['current_project_return_story'];policy=user_policy_reference()
    index=next(i for i,m in enumerate(p['metrics'])if m['metric_id']=='IRR');criterion=p['metrics'][index]['criterion']
    interval,root_blockers=_annual_enclosure(story,p['irr_recalculation'])
    period=None if story is None else'SYNTHETIC-lifecycle:'+story['cash_horizon']['start']+':'+story['cash_horizon']['end']
    state,relations,blockers=_compare(interval,criterion,period)
    blockers=sorted(set(root_blockers+blockers))
    if root_blockers:state='PENDING'
    check=dict(scope='single_synthetic_IRR_condition_not_deal',row_state=state,relations=relations,
        blockers=blockers,enclosure=interval,value_definition_ref=VALUE_DEFINITION,value_unit='fraction',
        value_period_ref=period,context=p['context'],criterion=criterion,criterion_pointer='/metrics/'+str(index)+'/criterion',
        enclosure_pointer='/current_project_return_story/annual_irr_roots/0',parent_IRR_run_sha256=parent.sha256,
        user_band_policy_reference=policy,band_policy='pending_professional_review',
        professional_review_needed_for_band=state=='BAND',criterion_source_authenticated=False,
        criteria_adopted=False,point_rate_selected=False,precision_automatically_increased=False,
        variables_automatically_adjusted=False,full_deal_result_recomputed=False,decision='PENDING')
    p['blockers']['IRR_interval_comparison']=blockers
    p.update(component='T101',purpose='synthetic_single_IRR_condition_from_complete_enclosure',title='Mini-UW v1 | Criterio IRR por intervalo',engine_sha256=ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),scalar_screening_engine_sha256=SCREEN_ENGINE_SHA256,
        parent_IRR_checked_run_sha256=parent.sha256,IRR_interval_comparison=check,
        state='current_synthetic_IRR_interval_condition'if story is not None else'PENDING',
        IRR_point_comparison_enabled=False,financial_policy_adopted=False,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(p);return IRRIntervalRun(value,digest(value),parent)


def assemble_irr_interval_output(raw):
    return _from_verified_irr(assemble_irr_checked_output(raw))


def _render_verified(run):
    report=_base_summary(run);m=report.manifest;spans=m['display_spans'];p=run.payload
    labels={'PASS_CONDITION':'cumple regla (sim.)','FAIL_CONDITION':'no cumple regla (sim.)',
        'BAND':'banda pendiente','CONFLICT':'reglas en conflicto','PENDING':'pendiente'}
    check=p['IRR_interval_comparison']
    # The rate value is shown as percent; rules retain their explicit source unit.
    unit_displayed=False
    for row in spans:
        if row['result_pointers']==[check['criterion_pointer']]and row['text']!='P/F: Pendiente':
            unit=check['criterion']['unit']
            label='fraccion anual'if unit=='fraction'and check['criterion']['definition_ref']==VALUE_DEFINITION else unit
            row['text']+=' ['+label+']'
            unit_displayed=True
    spans.append(dict(text='IRR por intervalo: '+labels[check['row_state']],x=528,y=190,font_size=6.2,width=236,
        result_pointers=['/IRR_interval_comparison/row_state','/decision']))
    commands=[b'0.06 0.17 0.25 rg 24 524 744 64 re f 1 1 1 rg']
    for i,row in enumerate(spans):
        if i==3:commands.append(b'0.06 0.17 0.25 rg')
        if row['text'].startswith('Resultado T98 SHA256: '):row['text']='Resultado T101 SHA256: '+run.sha256
        x,y,size,width=(row[k]for k in ('x','y','font_size','width'))
        if len(row['text'])*size*.6>width or x<24 or x+width>768 or y<25 or y+size>588:
            raise PreviewLayoutError('T101 span exceeds one-page budget')
        bold=y in(566,546,476,457,440,215,171,179,116,40)
        commands.append(f'BT /{"F2"if bold else"F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+_pdf_string(row['text'])+b') Tj ET')
    pdf=_pdf(commands)
    m.update(component='T101',engine_sha256=ENGINE_SHA256,summary_engine_sha256=SUMMARY_ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),summary_composition_manifest_sha256=report.manifest_sha256,
        result_component='T101',result_sha256=run.sha256,pdf_sha256=sha(pdf),
        parent_IRR_checked_run_sha256=run.parent_run.sha256,IRR_interval_condition_state=check['row_state'],
        criterion_source_unit_displayed=unit_displayed,criterion_thresholds_converted_to_percent=False,
        point_rate_selected=False,full_deal_result_recomputed=False,underlying_financial_result_changed=False,
        gross_cash_changed=False,new_financial_policy=False,decision='PENDING')
    value=canonical(m);return V1Report(pdf,value,digest(value))


def render_irr_interval_report(raw,run):
    if type(run)is not IRRIntervalRun or assemble_irr_interval_output(raw)!=run:
        raise ValidationError('T101 report requires exact complete sources and interval-condition replay')
    return _render_verified(run)
