"""T94 full scheduled Mini-UW return gated by every insurance renewal book."""
from dataclasses import asdict,dataclass
from pathlib import Path
import hashlib,json

from .drafts import ValidationError,canonical,digest
from .expense_cash_detail import _json,_exact
from .expense_schedule import parse_expense_schedule
from .insurance_renewals import parse_policy_book,reconcile_insurance_renewals,DEFINITION
from .scheduled_expense_case import parse_scheduled_expense_case,assemble_scheduled_expense_case,utf8,sha
from .evidence_currency import timestamp,evaluate_evidence_currency

ENGINE_SHA256=sha(Path(__file__).read_bytes())


def parse_policy_renewal_case(raw):
    p=_json(raw,48*1024*1024)
    _exact(p,{'schema','scheduled_case_utf8','policy_books_utf8','registry_utf8','as_of_UTC'})
    if p['schema']!='miniuw.synthetic-v1-policy-renewal-case.v1':raise ValidationError('supported policy renewal case required')
    parse_scheduled_expense_case(utf8(p['scheduled_case_utf8'],32*1024*1024));timestamp(p['as_of_UTC']);utf8(p['registry_utf8'],131072)
    if type(p['policy_books_utf8'])is not list or not 1<=len(p['policy_books_utf8'])<=64:raise ValidationError('one to 64 insurance books required')
    ids=set()
    for source in p['policy_books_utf8']:
        book=parse_policy_book(utf8(source,2*1024*1024))
        if book['schedule_id']in ids:raise ValidationError('duplicate insurance book schedule')
        ids.add(book['schedule_id'])
    return p


@dataclass(frozen=True)
class PolicyRenewalCaseRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_policy_renewal_case(raw):
    p=parse_policy_renewal_case(raw);parent_raw=p['scheduled_case_utf8'].encode();parent_source=parse_scheduled_expense_case(parent_raw);parent=assemble_scheduled_expense_case(parent_raw);view=parent.payload
    registry_raw=p['registry_utf8'].encode();currency=evaluate_evidence_currency(registry_raw,p['as_of_UTC']);ep=currency.payload
    sources=[s.encode()for s in p['policy_books_utf8']];books=[parse_policy_book(s)for s in sources]
    aggregate_sources={parse_expense_schedule(s.encode())['schedule_id']:s.encode()for s in parent_source['schedule_sources_utf8']if parse_expense_schedule(s.encode())['kind']=='insurance'}
    blockers=[];histories=[];totals=[]
    if p['as_of_UTC']!=parent_source['as_of_UTC']:blockers.append('parent_and_policy_evaluation_time_mismatch')
    if ep['context']!=view['context']:blockers.append('policy_registry_context_mismatch')
    if view['current_project_return_story']is None:blockers.append('scheduled_parent_current_projection_unavailable')
    if {b['schedule_id']for b in books}!=set(aggregate_sources):blockers.append('exact_all_insurance_policy_book_inventory_required')
    for source,book in zip(sources,books):
        aggregate=aggregate_sources.get(book['schedule_id'])
        if aggregate is None:blockers.append(book['schedule_id']+':unknown_insurance_schedule');continue
        run=reconcile_insurance_renewals(aggregate,source);rp=run.payload;histories.append(asdict(run))
        if rp['state']!='matched_synthetic_successive_insurance_policies':blockers += [book['schedule_id']+':'+b for b in rp['blockers']]
        else:totals.append(dict(schedule_id=rp['schedule_id'],currency=rp['currency'],totals=rp['totals']))
    required=list(view['required_source_bindings'])
    def add(path,value):required.append(dict(requirement_id=path,source_sha256=sha(value),source_locator=path))
    add('/policy-renewals/scheduled-case',parent_raw)
    for i,source in enumerate(sources):add('/policy-renewals/books/'+str(i),source)
    if len(required)>256:raise ValidationError('policy source requirement budget exceeded')
    if sorted(required,key=lambda x:x['requirement_id'])!=sorted([r['requirement']for r in ep['requirements']],key=lambda x:x['requirement_id']):blockers.append('complete_policy_renewal_source_inventory_mismatch')
    if ep['state']!='current_synthetic_evidence':blockers+=['policy_renewal_sources_not_current']+ep['blockers']
    prior_engine=view['engine_sha256'];prior_time=view['evaluated_as_of_UTC']
    view.update(component='T94',purpose='synthetic_current_miniuw_return_with_successive_insurance_policy_checks',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),title='Mini-UW v1 | Renovaciones de seguros',
        scheduled_case_source_sha256=sha(parent_raw),scheduled_case_run_sha256=parent.sha256,scheduled_case_engine_sha256=prior_engine,case_source_sha256=sha(raw),parent_evaluated_as_of_UTC=prior_time,evaluated_as_of_UTC=p['as_of_UTC'],
        policy_renewal_profile='SYNTHETIC-SUCCESSIVE-INSURANCE-RENEWALS-v1',required_source_bindings=required,historical_policy_runs=histories,policy_blockers=sorted(set(blockers)),current_policy_cost_totals=None if blockers else totals,
        policy_registry_source_sha256=sha(registry_raw),policy_registry_run_sha256=currency.sha256,coverage_adequacy_verified=False,contract_or_due_date_authority_verified=False,new_expense_payment_or_equity_generated=False,
        independent_financial_audit=False,professional_review_authenticated=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    view['blockers']['projection']=sorted(set(view['blockers']['projection']+blockers));view['state']='current_synthetic_policy_renewal_case'if not blockers else'PENDING'
    if blockers:
        view['current_project_return_story']=None;view['current_schedule_totals']=None;view['policy_parent_screening_run_sha256']=view['screening_run_sha256'];view['screening_run_sha256']=None;view['screening_simulation_result']='PENDING'
        for metric in view['metrics']:metric.update(value=None,value_state='PENDING',comparison_state='PENDING',reason='Renovaciones o fuentes actuales pendientes',comparison_blockers=sorted(set(metric['comparison_blockers']+['policy_renewal_or_evidence_gate_blocked'])))
    text=canonical(view);return PolicyRenewalCaseRun(text,digest(text))
