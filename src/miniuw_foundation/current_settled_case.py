"""T109 source-exhaustive explicit-time gate for the supplied T108 cash path."""
from dataclasses import dataclass,asdict
from pathlib import Path
import copy,json
from .drafts import ValidationError,canonical,digest
from .expense_cash_detail import _json,_exact
from .expense_checked_lifecycle import _utf8
from .scheduled_expense_case import sha
from .settled_case import assemble_settled_case,parse_settled_case
from .settled_case_artifacts import versions as case_versions
from .construction_bundle import recover_construction_bundle
from .deferred_insurance_settlement import reconcile_deferred_insurance_settlement
from .evidence_currency import evaluate_evidence_currency,timestamp,DEFINITION_PATH as EVIDENCE_DEFINITION

ENGINE_SHA256=sha(Path(__file__).read_bytes())
ROOT=Path(__file__).resolve().parents[2]
DEFINITION=ROOT/'docs/technical-implementation-T109.md'
CATALOG=ROOT/'templates/project-draft-empty.json'
MAX_BYTES=32*1024*1024


def required_settled_sources(case_raw):
    p=parse_settled_case(case_raw);construction=recover_construction_bundle(p['construction_bundle_utf8'].encode());rows=[]
    def add(path,raw):rows.append(dict(requirement_id=path,source_sha256=sha(raw),source_locator=path))
    add('/case/source',case_raw)
    for path,key in [('/construction/bundle','construction_bundle_utf8'),('/transition/phase_contract','phase_source_utf8'),
        ('/operation/calendar','holding_source_utf8'),('/operation/sale_binding','hold_sale_source_utf8'),('/settlement/source','boundary_source_utf8'),
        ('/opening/cash_binding','cash_boundary_source_utf8'),('/window/binding','window_source_utf8'),('/investor/source','investor_source_utf8'),('/investor/binding','return_binding_source_utf8')]:add(path,p[key].encode())
    add('/construction/preopening_draft',construction.preopening_raw);add('/construction/binding',construction.binding_raw)
    for i,loan in enumerate(construction.loans):add('/construction/loans/'+str(i),loan.raw)
    phase=json.loads(p['phase_source_utf8'])
    for i,row in enumerate(phase['loan_phases']):
        add('/transition/loans/'+str(i)+'/schedule',row['schedule_source_utf8'].encode());add('/transition/loans/'+str(i)+'/windows',canonical(row['windows']).encode())
    for i,row in enumerate(p['periods']):
        add('/operation/periods/'+str(i)+'/noi',row['noi_source_utf8'].encode());add('/operation/periods/'+str(i)+'/cash',row['cash_source_utf8'].encode())
    sale=p['sale'];add('/sale/cash',sale['closing_source_utf8'].encode());add('/sale/debt_binding',sale['debt_source_utf8'].encode())
    for i,row in enumerate(sale['loans']):
        add('/sale/loans/'+str(i)+'/terms',row['source'].encode());add('/sale/loans/'+str(i)+'/windows',canonical(row['windows']).encode())
    boundary=json.loads(p['boundary_source_utf8'])
    for i,row in enumerate(boundary['periods']):add('/settlement/periods/'+str(i)+'/detail',row['detail_source_utf8'].encode())
    for path,key in [('/settlement/nominal_plan','plan_source_utf8'),('/settlement/terminal_binding','terminal_binding_source_utf8')]:add(path,boundary[key].encode())
    add('/settlement/accounting_before_after',canonical(boundary['accounting']).encode());add('/settlement/pre_cut_payment_map',canonical(boundary['payment_map']).encode())
    add('/definitions/producer_versions',canonical(case_versions()).encode());add('/definitions/current_profile',DEFINITION.read_bytes());add('/catalog/empty_original_inputs_criteria',CATALOG.read_bytes())
    add('/definitions/current_profile_engine',Path(__file__).read_bytes());add('/definitions/evidence_engine',(ROOT/'src/miniuw_foundation/evidence_currency.py').read_bytes());add('/definitions/evidence_profile',EVIDENCE_DEFINITION.read_bytes())
    if len(rows)>256 or len({r['requirement_id']for r in rows})!=len(rows):raise ValidationError('bounded unique complete settled-source inventory required')
    return rows


def parse_current_settled_source(raw):
    p=_json(raw,MAX_BYTES);_exact(p,{'schema','case_source_utf8','registry_source_utf8','evaluated_as_of_UTC'})
    if p['schema']!='miniuw.synthetic-current-settled-case.v1':raise ValidationError('exact current settled source profile required')
    _utf8(p['case_source_utf8'],16*1024*1024);_utf8(p['registry_source_utf8'],1048576);timestamp(p['evaluated_as_of_UTC'])
    return p


@dataclass(frozen=True)
class CurrentSettledRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_settled_case(raw):
    p=parse_current_settled_source(raw);case_raw=p['case_source_utf8'].encode();registry_raw=p['registry_source_utf8'].encode();base=assemble_settled_case(case_raw);b=base.payload
    requirements=required_settled_sources(case_raw);registry=evaluate_evidence_currency(registry_raw,p['evaluated_as_of_UTC']);r=registry.payload;blockers=[]
    supplied=[row['requirement']for row in r['requirements']]
    if sorted(requirements,key=lambda v:v['requirement_id'])!=sorted(supplied,key=lambda v:v['requirement_id']):blockers.append('complete_exact_settled_source_inventory_mismatch')
    if r['context']!=b['context']:blockers.append('registry_and_settled_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('required_settled_evidence_not_current')
    if b['project_return_story']is None:blockers.append('complete_settled_cash_path_blocked')
    catalog=json.loads(CATALOG.read_bytes());criteria=catalog['investment_criteria']
    if len(criteria)!=10 or any(c['threshold']is not None or c['state']!='missing'for c in criteria):raise ValidationError('original empty ten-criterion catalog required; no automatic policy')
    story=copy.deepcopy(b['project_return_story'])if not blockers else None
    risk=None if story is None else json.loads(b['cash_risk_run']['payload_json'])['metrics']
    nominal=None
    if story is not None:
        original=parse_settled_case(case_raw);boundary=json.loads(original['boundary_source_utf8']);nominal=reconcile_deferred_insurance_settlement(boundary['plan_source_utf8'].encode())
    result=dict(component='T109',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),source_sha256=sha(raw),case_source_sha256=sha(case_raw),registry_source_sha256=sha(registry_raw),
        parent_settled_run_sha256=base.sha256,registry_run=asdict(registry),context=b['context'],evaluated_as_of_UTC=p['evaluated_as_of_UTC'],required_sources=requirements,
        current_project_return_story=story,current_settlement_summary=b['settlement_summary']if story is not None else None,
        current_operating_totals=b['operating_totals']if story is not None else None,current_holding_sale_totals=b['holding_sale_totals']if story is not None else None,
        current_nominal_insurance_totals=None if nominal is None else nominal.payload['totals'],current_nominal_plan_run_sha256=None if nominal is None else nominal.sha256,
        current_risk_observations=risk,current_irr_evidence=b['irr_evidence']if story is not None else None,current_compiled_investor_json=b['compiled_investor_json']if story is not None else None,
        blockers=dict(gate=blockers,evidence=r['blockers'],calculation=b['blockers']),source_requirements_checked=len(requirements),
        criterion_slots=[dict(metric_id=c['metric_id'],threshold=None,state='PENDING')for c in criteria],
        original_sheet_adapter_for_this_profile_implemented=False,original_semantic_mappings_pending=54,
        state='current_synthetic_settled_output'if story is not None else'PENDING',
        synthetic_complete_source_evidence_current=not blockers,source_authority_verified=False,professional_review_authenticated=False,
        new_financial_values_generated=False,automatic_source_renewal_enabled=False,live_clock_or_monitor_enabled=False,
        personal_investor_return=None,financial_model_complete=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    text=canonical(result);return CurrentSettledRun(text,digest(text))
