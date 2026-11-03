"""T85 one synthetic case file, preserved source catalogue and explicit pending criteria."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .drafts import ContextSeed, ValidationError, canonical, digest, template, nonempty
from .expense_cash_detail import _json, _exact
from .debt_service import _fraction
from .evidence_currency import timestamp
from .screening import simulate_screening, AGGREGATION
from .v1_projection import construct_projection, ENGINE_SHA256 as PROJECTION_ENGINE_SHA256
from .v1_contracts import load_contracts

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PROFILE = 'SYNTHETIC-V1-STAGED-PHASED-RENTAL-HOLD-SALE-v1'
DEFINITION = Path(__file__).resolve().parents[2]/'docs/technical-implementation-T85-T87.md'
METRIC_REASONS = {
    'YoC':'NOI estabilizado y TDC all-in compatibles pendientes',
    'spread':'YoC y cap de referencia compatibles pendientes',
    'equity_recovered':'Base de equity y alcance de refinanciacion pendientes',
    'equity_cash_in':'Base de equity y alcance de refinanciacion pendientes',
    'breakeven_occupancy':'Funcion de ocupacion/costos/impuesto/deuda pendiente',
    'post_refi_CoC':'Base de capital remanente y estrategia pendientes',
    'equity_TDC':'Definicion y conciliacion de equity/TDC pendientes',
    'equity_multiple':None,
    'IRR':'Conservar intervalos y todas las raices; no elegir valor puntual',
    'asking_relative_to_supported_price':'Definicion RLV/objetivos y alcance de precio pendientes',
}


def catalog():
    p = template()[0]
    return p['project_inputs']+p['financing_inputs']+p['requested_alternatives'], p['investment_criteria']


def blank_input_catalog():
    return [dict(field_id=r['field_id'],value=None,recipe_pointer=None,unit=None,period_ref=None,mapping_basis_ref=None)
            for r in catalog()[0]]


def blank_criteria():
    return [dict(metric_id=r['metric_id'],definition_ref=None,unit=None,period_ref=None,
                 pass_condition=dict(operator=None,threshold=None),fail_condition=dict(operator=None,threshold=None),source_ref=None)
            for r in catalog()[1]]


def pointer(root, path):
    if type(path) is not str or not path.startswith('/'):
        raise ValidationError('explicit absolute recipe JSON Pointer required')
    node = root
    for part in path.split('/')[1:]:
        if '~' in part:
            import re
            if re.search('~(?![01])',part):raise ValidationError('invalid JSON Pointer escape')
        key = part.replace('~1','/').replace('~0','~')
        try:
            if type(node) is list:
                if not key.isdigit() or (key != '0' and key.startswith('0')):raise KeyError(key)
                node = node[int(key)]
            elif type(node) is dict:node = node[key]
            else:raise KeyError(key)
        except (IndexError,KeyError) as error:
            raise ValidationError('recipe mapping pointer not found') from error
    return node


def parse_v1_case(raw):
    p = _json(raw,16*1024*1024)
    _exact(p,{'schema','profile','case_id','case_revision','title','context','as_of_UTC',
              'required_scenarios','original_inputs','criteria','recipe','source_registry'})
    if p['schema']!='miniuw.synthetic-v1-case.v1' or p['profile']!=PROFILE:
        raise ValidationError('supported synthetic v1 case/profile required')
    if type(p['context']) is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    for key in ('case_id','title'):
        nonempty(p[key],key)
        if len(p[key])>64 or any(ord(c)<32 or ord(c)==127 for c in p[key]):raise ValidationError('bounded printable case identity required')
    if not p['case_id'].startswith('SYNTHETIC-') or type(p['case_revision'])is not int or p['case_revision']<1:
        raise ValidationError('synthetic case ID and positive revision required')
    timestamp(p['as_of_UTC'])
    if type(p['required_scenarios'])is not list or not p['required_scenarios'] or len(p['required_scenarios'])>4 or any(type(x)is not str or not x.strip() for x in p['required_scenarios']) or len(set(p['required_scenarios']))!=len(p['required_scenarios']):
        raise ValidationError('explicit unique scenario inventory required')
    slots,metrics=catalog()
    if type(p['original_inputs'])is not list or [r.get('field_id')for r in p['original_inputs']if type(r)is dict]!=[r['field_id']for r in slots]:
        raise ValidationError('all 55 original fields required in original order')
    for r in p['original_inputs']:
        _exact(r,{'field_id','value','recipe_pointer','unit','period_ref','mapping_basis_ref'})
        for k in ('recipe_pointer','unit','period_ref','mapping_basis_ref'):
            if r[k]is not None:nonempty(r[k],k)
        if r['value']is not None and type(r['value'])is not str:_fraction(r['value'])
    if type(p['criteria'])is not list or [r.get('metric_id')for r in p['criteria']if type(r)is dict]!=[r['metric_id']for r in metrics]:
        raise ValidationError('exact ten metric/criteria inventory required')
    for r in p['criteria']:
        _exact(r,{'metric_id','definition_ref','unit','period_ref','pass_condition','fail_condition','source_ref'})
        for k in ('definition_ref','unit','period_ref','source_ref'):
            if r[k]is not None:nonempty(r[k],k)
        for k in ('pass_condition','fail_condition'):
            _exact(r[k],{'operator','threshold'})
            if r[k]['operator']not in (None,'>=','<=','>','<'):raise ValidationError('explicit comparison operator required')
            _fraction(r[k]['threshold'])
    return p


@dataclass(frozen=True)
class MiniUWV1Run:
    payload_json:str
    sha256:str
    execution_bundle:bytes|None

    @property
    def payload(self):return json.loads(self.payload_json)


def run_v1_case(raw):
    p=parse_v1_case(raw);_,contracts_sha=load_contracts();slots,_=catalog();original=[];input_blockers=[]
    for source,row in zip(slots,p['original_inputs']):
        reasons=[]
        if row['value']is None:reasons.append('original_value_missing')
        if any(row[k]is None for k in ('recipe_pointer','unit','period_ref','mapping_basis_ref')):reasons.append('original_field_mapping_or_definition_pending')
        if row['recipe_pointer']is not None:
            try:
                actual=pointer(p['recipe'],row['recipe_pointer'])
                if canonical(actual)!=canonical(row['value']):reasons.append('original_value_differs_from_mapped_recipe_source')
            except ValidationError:reasons.append('original_mapping_pointer_unresolved')
        if reasons:input_blockers.append(row['field_id']+':'+','.join(reasons))
        original.append(dict(**row,label=source['label'],original_cell=source['source_cell'],historical_requirement=source['historical_requirement'],
                             state='bound_synthetic_claim'if not reasons else'PENDING',blockers=reasons))
    conflicts=[r for r in original if any('differs_from' in s or 'pointer_unresolved' in s for s in r['blockers'])]
    projection=None;projection_blockers=[]
    if conflicts:projection_blockers=['original_input_and_recipe_conflict']
    elif p['required_scenarios']!=[p['context']['scenario_id']]:projection_blockers=['requested_scenario_inventory_outside_single_synthetic_profile']
    else:
        try:
            projection=construct_projection(p['recipe'],p['source_registry'],p['as_of_UTC'])
            projection_blockers=projection['blockers']
        except (ValidationError,KeyError,TypeError,IndexError) as error:
            projection_blockers=['source_contract_error:'+str(error)[:160]]
    current=None if projection is None else projection['current']
    if current is not None:
        if current['context']!=p['context']:
            projection_blockers.append('case_and_calculation_context_mismatch');current=None
        elif current['current_project_return_story']is None:projection_blockers+=current['blockers']+current['evidence_blockers']+current['calculation_blockers']
    story=None if current is None or projection_blockers else current['current_project_return_story']
    metrics=[];values=[];conditions=[]
    for r in p['criteria']:
        mid=r['metric_id'];value=None;reason=METRIC_REASONS[mid]
        definition='SYNTHETIC-V1-GROSS-EQUITY-MULTIPLE-v1'if mid=='equity_multiple'else None
        period=None if story is None else 'SYNTHETIC-lifecycle:'+story['cash_horizon']['start']+':'+story['cash_horizon']['end']
        if mid=='equity_multiple'and story is not None:value=story['equity_multiple']
        if mid=='equity_multiple'and value is None:reason='Proyeccion actual no disponible'
        meta=dict(metric_id=mid,scenario_id=p['context']['scenario_id'],definition_ref=definition,unit='multiple'if mid=='equity_multiple'else None,
                  currency=None,period_ref=period,quantity_kind='scalar',applicability='applicable',applicability_evidence_ref=None)
        values.append(dict(meta,value=value))
        cmeta=dict(meta,definition_ref=r['definition_ref'],unit=r['unit'],period_ref=r['period_ref'])
        pc=r['pass_condition'] if r['source_ref']is not None else dict(operator=None,threshold=None)
        fc=r['fail_condition'] if r['source_ref']is not None else dict(operator=None,threshold=None)
        conditions.append(dict(cmeta,pass_condition=pc,fail_condition=fc))
        metrics.append(dict(metric_id=mid,value=value,value_state='computed_synthetic'if value is not None else'PENDING',
                            reason=reason,definition_ref=definition,period_ref=period,criterion=r))
    screening=dict(schema='miniuw.synthetic-screening-case.v1',context=p['context'],case_id=p['case_id'],criteria_revision=str(p['case_revision']),criteria_status='synthetic_fixture_only',
                   required_metrics=[r['metric_id']for r in p['criteria']],required_scenarios=[p['context']['scenario_id']],metric_values=values,criteria=conditions,aggregation_rule=AGGREGATION,hypothetical_band_policy=None)
    screen=simulate_screening(canonical(screening).encode())
    for r,c in zip(metrics,screen.payload['comparisons']):r.update(comparison_state=c['state'],comparison_blockers=c['blockers'])
    blockers=dict(input_catalog=input_blockers,projection=sorted(set(projection_blockers)),criteria=screen.payload['simulation_blockers'],
                  financial_scope=['financial_policy_and_independent_acceptance_pending','authentic_professional_review_missing','original_plan_and_official_source_verification_pending','production_and_real_decisions_not_authorized'])
    result=dict(component='T85',purpose='Mini-UW v1 synthetic integrated run',engine_sha256=ENGINE_SHA256,projection_engine_sha256=PROJECTION_ENGINE_SHA256,
                definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),case_source_sha256=hashlib.sha256(raw).hexdigest(),case_id=p['case_id'],case_revision=p['case_revision'],title=p['title'],
                dot_bot_contracts_sha256=contracts_sha,
                context=p['context'],profile=p['profile'],evaluated_as_of_UTC=p['as_of_UTC'],original_inputs=original,
                input_catalog_summary=dict(total=55,bound=sum(r['state']=='bound_synthetic_claim'for r in original),pending=sum(r['state']=='PENDING'for r in original)),
                requested_scenarios=p['required_scenarios'],metrics=metrics,screening_run_sha256=screen.sha256,screening_simulation_result=screen.payload['simulation_result'],
                stages=[]if projection is None else projection['stages'],current_project_return_story=story,
                current_projection_run_sha256=None if current is None else digest(canonical(current)),
                required_source_bindings=[]if current is None else current['required_source_bindings'],
                execution_bundle_sha256=None if projection is None or projection['bundle']is None else hashlib.sha256(projection['bundle']).hexdigest(),
                blockers=blockers,state='computed_synthetic_profile_with_pending_decision'if story is not None else'PENDING',decision='PENDING',
                full_input_sheet_adapter_completed=False,full_financial_model_completed=False,personal_return_verified=False,
                independent_financial_audit_completed=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False)
    encoded=canonical(result)
    return MiniUWV1Run(encoded,digest(encoded),None if projection is None else projection['bundle'])
