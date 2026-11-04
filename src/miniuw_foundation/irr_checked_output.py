"""T100 source-first periodic IRR overlay on the verified T98 capital view."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import copy

from .drafts import ValidationError,canonical,digest
from .capital_checked_output import CapitalCheckedRun,assemble_capital_checked_output
from .policy_renewal_case import parse_policy_renewal_case
from .scheduled_expense_case import parse_scheduled_expense_case,sha
from .v1_case import parse_v1_case
from .investor_returns import produce_investor_returns
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError
from .primitive_periodic_returns import isolate_primitive_periodic_returns,ENGINE_SHA256 as ROOT_ENGINE_SHA256
from .long_horizon_report import _render_verified as _base_summary,ENGINE_SHA256 as SUMMARY_ENGINE_SHA256
from .synthetic_onepager import _pdf,_pdf_string,PreviewLayoutError
from .v1_report import V1Report

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T100.md'
IRR_BLOCKER='IRR_requires_unique_complete_root_or_explicit_resolution'
REPLAY_KEYS=('currency','equity_level','cash_horizon','gross_contributions','gross_distributions',
    'net_cash_profit','equity_multiple','cash_by_category','normalized_story','capital_snapshots',
    'annual_cash_receipts','periodic_irr','annual_irr_roots','selected_IRR')


@dataclass(frozen=True)
class IRRCheckedRun:
    payload_json:str
    sha256:str
    parent_run:CapitalCheckedRun

    @property
    def payload(self):
        import json
        return json.loads(self.payload_json)


def _compiled_investor(raw,parent):
    outer=parse_policy_renewal_case(raw)
    scheduled=parse_scheduled_expense_case(outer['scheduled_case_utf8'].encode())
    base=parse_v1_case(scheduled['base_case_utf8'].encode())
    source=copy.deepcopy(base['recipe']['investor_source'])
    source['events']=copy.deepcopy(parent.payload['current_project_return_story']['dated_events'])
    compiled=canonical(source).encode();prior=produce_investor_returns(compiled)
    original=parent.parent_run.payload['current_project_return_story']
    if any(prior.payload[k]!=original[k]for k in REPLAY_KEYS):
        raise ValidationError('compiled investor ledger does not reproduce prior financial/capital/IRR fields')
    if prior.payload['story_blockers']!=original['upstream_story_blockers']:
        raise ValidationError('compiled investor ledger does not reproduce prior story blockers')
    return compiled,source,prior


def _annual_roots(roots,frequency,step_months):
    if frequency is None or frequency*step_months!=12:
        return [],['annualization_frequency_missing_or_inconsistent']
    def annual(rate):
        return rational(_bounded(_bounded((1+Fraction(rate))**frequency)-1))
    try:
        rows=[]
        for root in roots:
            if root['exact_periodic_rate']is not None:
                rows.append(dict(exact_annual_rate=annual(root['exact_periodic_rate']),annual_rate_interval=None))
            else:
                interval=root['periodic_rate_interval']
                rows.append(dict(exact_annual_rate=None,annual_rate_interval=dict(interval,
                    lower=annual(interval['lower']),upper=annual(interval['upper']))))
        return rows,[]
    except ArithmeticBudgetError:
        return [],['IRR_annualization_arithmetic_budget_exceeded']


def _current_annual_roots(result,frequency,step_months):
    attempted,blockers=_annual_roots(result['roots'],frequency,step_months)
    if result['status']!='complete_synthetic':
        return [],attempted,blockers+['IRR_incomplete_root_inventory_current_intervals_withheld']
    return attempted,attempted,blockers


def _from_verified_capital(raw,parent):
    p=parent.payload;s=p['current_project_return_story'];evidence=None;blockers=[]
    if s is None:
        blockers=['current_projection_withheld'];irr_state='PENDING'
    else:
        compiled,source,prior=_compiled_investor(raw,parent)
        pp=prior.payload;params=source['irr_parameters']
        net=pp['dated_net_flows']
        roots=isolate_primitive_periodic_returns([_fraction(r['net'],1300)for r in net],
            _fraction(params['max_periodic_rate_interval_width']),params['split_budget'],params['operation_budget'])
        annual,attempted_annual,annual_blockers=_current_annual_roots(roots,params['periods_per_year'],source['grid']['step_months'])
        blockers+=annual_blockers
        unique=roots['status']=='complete_synthetic'and roots['distinct_positive_discount_roots']==1
        if not unique:blockers.append(IRR_BLOCKER)
        # Carry every unrelated parent blocker; only this numerical producer changes.
        previous=list(s['upstream_story_blockers'])
        s['upstream_story_blockers']=sorted(set([b for b in previous if b!=IRR_BLOCKER]+blockers))
        evidence=dict(compiled_investor_source_sha256=sha(compiled),compiled_investor_json=compiled.decode(),
            previous_investor_run_sha256=prior.sha256,previous_periodic_irr=pp['periodic_irr'],
            previous_annual_irr_roots=pp['annual_irr_roots'],previous_story_blockers=previous,
            grid=source['grid'],parameters=params,dated_net_flows=net,periodic_result=roots,
            annual_result=annual,attempted_annual_result=attempted_annual,annualization_blockers=annual_blockers,
            source_locator='/scheduled_case_utf8::json/base_case_utf8::json/recipe/investor_source',
            event_amounts_from_verified_parent=True,point_rate_selected=False,original_source_controls_unchanged=True)
        s.update(periodic_irr=roots,annual_irr_roots=annual,selected_IRR=None)
        irr_state=('computed_unique_conditional_annual_root_without_point'if unique and not annual_blockers
            else 'computed_conditional_roots_without_point'if annual and not annual_blockers else'PENDING')
    p['blockers']['IRR']=sorted(set(blockers+['IRR_point_for_screening_not_selected']))
    p['parent_current_projection_run_sha256']=p['current_projection_run_sha256']
    p['current_projection_run_sha256']=None
    p['current_IRR_solver_result_sha256']=None if evidence is None else digest(canonical(evidence['periodic_result']))
    p.update(component='T100',purpose='synthetic_primitive_periodic_IRR_checked_current_output',
        engine_sha256=ENGINE_SHA256,root_engine_sha256=ROOT_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        parent_capital_run_sha256=parent.sha256,irr_recalculation=evidence,irr_output_state=irr_state,
        state='current_synthetic_IRR_checked_output'if s is not None else'PENDING',
        financial_policy_adopted=False,IRR_point_comparison_enabled=False,personal_return_verified=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(p);return IRRCheckedRun(value,digest(value),parent)


def assemble_irr_checked_output(raw):
    return _from_verified_capital(raw,assemble_capital_checked_output(raw))


def _render_verified(run):
    report=_base_summary(run);m=report.manifest;spans=m['display_spans']
    commands=[b'0.06 0.17 0.25 rg 24 524 744 64 re f 1 1 1 rg']
    for i,row in enumerate(spans):
        if i==3:commands.append(b'0.06 0.17 0.25 rg')
        if row['text'].startswith('Resultado T98 SHA256: '):row['text']='Resultado T100 SHA256: '+run.sha256
        x,y,size,width=(row[k]for k in ('x','y','font_size','width'))
        if len(row['text'])*size*.6>width or x<24 or x+width>768 or y<25 or y+size>588:
            raise PreviewLayoutError('T100 one-page span exceeds layout budget')
        bold=y in (566,546,476,457,440,215,171,179,116,40)
        commands.append(f'BT /{"F2"if bold else"F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+_pdf_string(row['text'])+b') Tj ET')
    pdf=_pdf(commands)
    m.update(component='T100',engine_sha256=ENGINE_SHA256,root_engine_sha256=ROOT_ENGINE_SHA256,
        summary_engine_sha256=SUMMARY_ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        summary_composition_manifest_sha256=report.manifest_sha256,result_component='T100',result_sha256=run.sha256,
        pdf_sha256=sha(pdf),parent_capital_run_sha256=run.parent_run.sha256,irr_output_state=run.payload['irr_output_state'],
        underlying_financial_result_changed=True,changed_financial_fields=['periodic_irr','annual_irr_roots','upstream_story_blockers'],
        gross_cash_changed=False,point_rate_selected=False,new_financial_policy=False)
    value=canonical(m);return V1Report(pdf,value,digest(value))


def render_irr_checked_report(raw,run):
    if type(run)is not IRRCheckedRun or assemble_irr_checked_output(raw)!=run:
        raise ValidationError('T100 report requires exact complete source/IRR replay')
    return _render_verified(run)
