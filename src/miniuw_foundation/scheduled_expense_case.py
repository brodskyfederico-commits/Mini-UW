"""T91 current full v1 return gated by supplied insurance/tax schedules."""
from dataclasses import asdict,dataclass
from pathlib import Path
import hashlib
import json

from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .expense_cash_detail import _json,_exact
from .expense_schedule import produce_expense_schedule,parse_expense_schedule,DEFINITION
from .evidence_currency import evaluate_evidence_currency,timestamp,_sha
from .debt_service import _fraction
from .v1_case import run_v1_case,parse_v1_case

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(p):return canonical(p).encode('utf-8')


def utf8(value,limit):
    if type(value)is not str:raise ValidationError('exact source UTF-8 text required')
    try:raw=value.encode('utf-8')
    except UnicodeError as error:raise ValidationError('valid source Unicode required')from error
    if not raw or len(raw)>limit:raise ValidationError('nested source byte budget exceeded')
    return raw


def parse_binding(raw):
    p=_json(raw,2*1024*1024)
    _exact(p,{'schema','base_case_sha256','context','currency','inventory_declared_complete','binding_basis_ref','schedules'})
    if p['schema']!='miniuw.synthetic-v1-expense-schedule-binding.v1':raise ValidationError('supported expense schedule binding required')
    _sha(p['base_case_sha256'])
    if type(p['context'])is not dict:raise ValidationError('binding context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact binding context required')from error
    nonempty(p['currency'],'currency')
    if p['binding_basis_ref']is not None:nonempty(p['binding_basis_ref'],'binding_basis_ref')
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('explicit binding completeness required')
    if type(p['schedules'])is not list or len(p['schedules'])>65:raise ValidationError('bounded explicit schedule binding inventory required')
    ids=set();items=set();payment_ids=set()
    for row in p['schedules']:
        _exact(row,{'schedule_id','schedule_source_sha256','detail_item_id','kind','installment_links'})
        for k in ('schedule_id','detail_item_id'):nonempty(row[k],k)
        if row['schedule_id']in ids or row['detail_item_id']in items:raise ValidationError('duplicate schedule or expense target')
        ids.add(row['schedule_id']);items.add(row['detail_item_id']);_sha(row['schedule_source_sha256'])
        if row['kind']not in ('insurance','property_tax'):raise ValidationError('supported scheduled expense kind required')
        if type(row['installment_links'])is not list or len(row['installment_links'])>128:raise ValidationError('bounded installment mapping required')
        installments=set()
        for link in row['installment_links']:
            _exact(link,{'installment_id','period_ref','payment_id'})
            for k,v in link.items():nonempty(v,k)
            if link['installment_id']in installments or link['payment_id']in payment_ids:raise ValidationError('installment or payment mapped more than once')
            installments.add(link['installment_id']);payment_ids.add(link['payment_id'])
    return p


def parse_scheduled_expense_case(raw):
    p=_json(raw,32*1024*1024)
    _exact(p,{'schema','base_case_utf8','schedule_sources_utf8','binding_utf8','registry_utf8','as_of_UTC'})
    if p['schema']!='miniuw.synthetic-v1-scheduled-expense-case.v1':raise ValidationError('supported scheduled expense case required')
    timestamp(p['as_of_UTC']);base=utf8(p['base_case_utf8'],16*1024*1024);parse_v1_case(base)
    parse_binding(utf8(p['binding_utf8'],2*1024*1024));utf8(p['registry_utf8'],131072)
    if type(p['schedule_sources_utf8'])is not list or not 1<=len(p['schedule_sources_utf8'])<=65:raise ValidationError('one to 65 explicit scheduled sources required')
    ids=set()
    for source in p['schedule_sources_utf8']:
        s=parse_expense_schedule(utf8(source,1024*1024))
        if s['schedule_id']in ids:raise ValidationError('duplicate scheduled source ID')
        ids.add(s['schedule_id'])
    return p


@dataclass(frozen=True)
class ScheduledExpenseCaseRun:
    payload_json:str
    sha256:str

    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_scheduled_expense_case(raw):
    entry=parse_scheduled_expense_case(raw);base_raw=entry['base_case_utf8'].encode();case=parse_v1_case(base_raw);base=run_v1_case(base_raw);bp=base.payload
    binding_raw=entry['binding_utf8'].encode();binding=parse_binding(binding_raw);registry_raw=entry['registry_utf8'].encode();currency=evaluate_evidence_currency(registry_raw,entry['as_of_UTC']);ep=currency.payload
    sources=[s.encode()for s in entry['schedule_sources_utf8']];runs=[produce_expense_schedule(s)for s in sources];run_by_id={r.payload['schedule_id']:r for r in runs};source_by_id={parse_expense_schedule(s)['schedule_id']:s for s in sources}
    blockers=[];checks=[]
    if binding['base_case_sha256']!=sha(base_raw):blockers.append('binding_base_case_hash_mismatch')
    if binding['context']!=case['context']or ep['context']!=case['context']:blockers.append('binding_or_evidence_context_mismatch')
    if binding['inventory_declared_complete']is not True or binding['binding_basis_ref']is None:blockers.append('binding_inventory_or_basis_pending')
    if entry['as_of_UTC']!=case['as_of_UTC']:blockers.append('base_and_schedule_evaluation_time_mismatch')
    if bp['current_project_return_story']is None:blockers.append('base_current_projection_unavailable')
    if not bp['required_source_bindings']:blockers.append('base_complete_source_inventory_unavailable')
    periods=case['recipe']['operating_periods']if base.execution_bundle is not None else []
    target_sets=[]
    for period in periods:
        detail=period.get('expense_detail',{});items=detail.get('items',[])
        target_sets.append({(row['item_id'],row['kind'])for row in items if row.get('kind')in ('insurance','property_tax')})
    expected=target_sets[0]if target_sets else set()
    if not periods or any(t!=expected for t in target_sets):blockers.append('complete_same_scheduled_expense_inventory_required')
    if {(row['detail_item_id'],row['kind'])for row in binding['schedules']}!=expected:blockers.append('exact_all_insurance_and_tax_target_inventory_required')
    if {r['schedule_id']for r in binding['schedules']}!=set(run_by_id):blockers.append('exact_schedule_source_inventory_required')
    ordered=[p.get('cash_source',{}).get('period_ref')for p in periods]
    for row in binding['schedules']:
        sid=row['schedule_id'];run=run_by_id.get(sid);issues=[]
        if run is None:blockers.append(sid+':source_missing');continue
        sp=run.payload;source=parse_expense_schedule(source_by_id[sid])
        if row['schedule_source_sha256']!=sha(source_by_id[sid]):issues.append('source_hash_mismatch')
        if sp['state']!='computed_synthetic_full_window_expense_schedule':issues+=['schedule_calculation_blocked']+sp['blockers']
        if sp['context']!=case['context']or sp['currency']!=binding['currency']:issues.append('schedule_context_or_currency_mismatch')
        if sp['kind']!=row['kind']or sp['economic_item_id']!=row['detail_item_id']:issues.append('schedule_economic_item_or_kind_mismatch')
        if [r['period_ref']for r in sp['allocations']]!=ordered:issues.append('exact_ordered_operating_allocations_required')
        actual_payments={};matched=[]
        for index,period in enumerate(periods):
            cash=period.get('cash_source',{});detail=period.get('expense_detail',{});target=next((r for r in detail.get('items',[])if r.get('item_id')==row['detail_item_id']and r.get('kind')==row['kind']),None)
            if cash.get('currency')!=binding['currency']or detail.get('currency')!=binding['currency']:issues.append('period_currency_mismatch')
            if target is None:issues.append('period_target_missing');continue
            if index==0 and any(_fraction(target[k])!=0 for k in ('opening_payables','opening_prepaid')):issues.append('initial_scheduled_liability_or_prepaid_outside_window_profile')
            if index==len(periods)-1 and any(_fraction(target[k])!=0 for k in ('closing_payables','closing_prepaid')):issues.append('terminal_scheduled_liability_or_prepaid_outside_window_profile')
            for payment in target['payments']:actual_payments[(cash['period_ref'],payment['payment_id'])]=payment
            allocation=next((a for a in sp['allocations']if a['period_ref']==cash['period_ref']),None)
            if allocation is None:issues.append('period_allocation_missing');continue
            if (allocation['start_date'],allocation['end_date'])!=(cash['start_date'],cash['end_date']):issues.append('allocation_and_operating_dates_mismatch')
            if allocation['allocated_expense']is None or _fraction(allocation['allocated_expense'],1300)!=_fraction(target['expense_amount']):issues.append('scheduled_allocation_differs_from_exact_NOI_expense')
            matched.append(dict(period_ref=cash['period_ref'],detail_item_id=target['item_id'],allocated_expense=allocation['allocated_expense'],declared_expense=target['expense_amount']))
        installments={r['installment_id']:r for r in sp['installments']}
        if {link['installment_id']for link in row['installment_links']}!=set(installments):issues.append('exact_installment_mapping_inventory_required')
        if {(link['period_ref'],link['payment_id'])for link in row['installment_links']}!=set(actual_payments):issues.append('exact_planned_payment_mapping_inventory_required')
        for link in row['installment_links']:
            installment=installments.get(link['installment_id']);payment=actual_payments.get((link['period_ref'],link['payment_id']))
            if installment is None or payment is None:issues.append('unknown_mapped_installment_or_payment');continue
            if installment['due_date']!=payment['date']:issues.append('supplied_due_date_differs_from_proposed_payment_date')
            if _fraction(installment['amount'])!=_fraction(payment['amount']):issues.append('installment_and_proposed_payment_amount_mismatch')
        blockers.extend(sid+':'+s for s in issues);checks.append(dict(schedule_id=sid,kind=row['kind'],detail_item_id=row['detail_item_id'],period_checks=matched,blockers=sorted(set(issues))))
    required=list(bp['required_source_bindings'])
    def add(path,value):required.append(dict(requirement_id=path,source_sha256=sha(value),source_locator=path))
    add('/scheduled-expense/base-case',base_raw);add('/scheduled-expense/binding',binding_raw)
    for i,s in enumerate(sources):add('/scheduled-expense/sources/'+str(i),s)
    if len(required)>256:raise ValidationError('full scheduled source inventory exceeds currency profile budget')
    if sorted(required,key=lambda r:r['requirement_id'])!=sorted([r['requirement']for r in ep['requirements']],key=lambda r:r['requirement_id']):blockers.append('complete_scheduled_expense_source_inventory_mismatch')
    if ep['state']!='current_synthetic_evidence':blockers+=['scheduled_expense_sources_not_current']+ep['blockers']
    view=bp
    view.update(component='T91',purpose='synthetic_current_v1_return_with_supplied_insurance_and_tax_schedule_checks',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        title='Mini-UW v1 | Seguros e impuestos',scheduled_expense_profile='SYNTHETIC-FULL-WINDOW-INSURANCE-TAX-v1',base_case_source_sha256=sha(base_raw),base_case_run_sha256=base.sha256,base_case_engine_sha256=bp['engine_sha256'],case_source_sha256=sha(raw),
        base_current_projection_run_sha256=bp['current_projection_run_sha256'],current_projection_run_sha256=None,base_evaluated_as_of_UTC=case['as_of_UTC'],evaluated_as_of_UTC=entry['as_of_UTC'],schedule_binding_source_sha256=sha(binding_raw),schedule_registry_source_sha256=sha(registry_raw),schedule_registry_run_sha256=currency.sha256,
        required_source_bindings=required,historical_schedule_runs=[asdict(r)for r in runs],schedule_checks=checks,schedule_blockers=sorted(set(blockers)),
        current_schedule_totals=None if blockers else [dict(schedule_id=r.payload['schedule_id'],kind=r.payload['kind'],totals=r.payload['totals'])for r in runs],
        coverage_adequacy_or_legal_tax_authority_verified=False,bank_payments_verified=False,professional_review_authenticated=False,
        new_expense_payment_or_equity_generated=False,base_financial_pipeline_preserved=True,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    view['blockers']['projection']=sorted(set(view['blockers']['projection']+blockers))
    view['state']='current_synthetic_scheduled_expense_case'if not blockers else'PENDING'
    if blockers:
        view['current_project_return_story']=None;view['base_screening_run_sha256']=view['screening_run_sha256'];view['screening_run_sha256']=None;view['screening_simulation_result']='PENDING'
        for metric in view['metrics']:
            metric.update(value=None,value_state='PENDING',comparison_state='PENDING',reason='Calendarios de gasto o fuentes actuales pendientes',comparison_blockers=sorted(set(metric['comparison_blockers']+['scheduled_expense_or_evidence_gate_blocked'])))
    text=canonical(view);return ScheduledExpenseCaseRun(text,digest(text))
