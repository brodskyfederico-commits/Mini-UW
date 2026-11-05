"""T110 source-bound phased rent and nominal policies, without extra cash."""
from dataclasses import dataclass,asdict
from pathlib import Path
import copy,json
from .drafts import ValidationError,canonical,digest,nonempty
from .expense_cash_detail import _json,_exact
from .expense_checked_lifecycle import _utf8
from .scheduled_expense_case import sha
from .current_settled_case import assemble_current_settled_case,parse_current_settled_source,required_settled_sources
from .settled_case import parse_settled_case
from .phased_rental import produce_phased_rental,capacity_equal,DEFINITION as RENT_DEFINITION
from .nominal_policy_book import reconcile_nominal_policy_book,parse_nominal_policy_book
from .evidence_currency import evaluate_evidence_currency,timestamp,_sha
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError

ROOT=Path(__file__).resolve().parents[2]
ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=ROOT/'docs/technical-implementation-T110.md'


def parse_source(raw):
    p=_json(raw,32*1024*1024)
    _exact(p,{'schema','current_settled_source_utf8','rental_binding_utf8','policy_book_utf8','registry_utf8','as_of_UTC'})
    if p['schema']!='miniuw.synthetic-phased-settled-output.v1':raise ValidationError('exact phased settled output source required')
    for k in ('current_settled_source_utf8','rental_binding_utf8','policy_book_utf8','registry_utf8'):_utf8(p[k],24*1024*1024 if k=='current_settled_source_utf8'else 8*1024*1024)
    timestamp(p['as_of_UTC']);return p


def parse_rental_binding(raw):
    p=_json(raw,8*1024*1024)
    _exact(p,{'schema','context','currency','case_source_sha256','inventory_declared_complete','rental_scope_and_no_overlap_basis_ref','period_recognition_basis_ref','periods'})
    if p['schema']!='miniuw.synthetic-phased-settled-rental-binding.v1':raise ValidationError('exact phased settled rental binding required')
    _sha(p['case_source_sha256']);nonempty(p['currency'],'currency')
    if type(p['context'])is not dict:raise ValidationError('explicit rental context required')
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('explicit rental completeness required')
    for k in ('rental_scope_and_no_overlap_basis_ref','period_recognition_basis_ref'):
        if p[k]is not None:nonempty(p[k],k)
    if type(p['periods'])is not list or not 1<=len(p['periods'])<=64:raise ValidationError('bounded nonempty rental periods required')
    ids=set()
    for r in p['periods']:
        _exact(r,{'period_ref','calendar_source_utf8','noi_source_sha256','cash_source_sha256','rental_income_item_id','other_zero_income_item_ids'})
        for k in ('period_ref','rental_income_item_id'):nonempty(r[k],k)
        if r['period_ref']in ids:raise ValidationError('duplicate rental period')
        ids.add(r['period_ref']);_utf8(r['calendar_source_utf8'],1048576)
        for k in ('noi_source_sha256','cash_source_sha256'):_sha(r[k])
        others=r['other_zero_income_item_ids']
        if type(others)is not list or any(type(v)is not str or not v.strip()for v in others)or len(set(others))!=len(others):raise ValidationError('exact unique other income inventory required')
    return p


def required_sources(raw):
    p=parse_source(raw);inner=parse_current_settled_source(p['current_settled_source_utf8'].encode());rental=parse_rental_binding(p['rental_binding_utf8'].encode())
    rows=required_settled_sources(inner['case_source_utf8'].encode())
    def add(path,data):rows.append(dict(requirement_id=path,source_locator=path,source_sha256=sha(data)))
    for key in ('current_settled_source_utf8','rental_binding_utf8','policy_book_utf8'):add('/T110/'+key,p[key].encode())
    for i,r in enumerate(rental['periods']):add('/T110/rental_calendars/'+str(i),r['calendar_source_utf8'].encode())
    for name in ('phased_settled_output','nominal_policy_book','phased_rental','rental_calendar','rental_operations'):add('/T110/engines/'+name,(ROOT/('src/miniuw_foundation/'+name+'.py')).read_bytes())
    add('/T110/definition',DEFINITION.read_bytes());add('/T110/rental_definition',RENT_DEFINITION.read_bytes())
    if len(rows)>256 or len({r['requirement_id']for r in rows})!=len(rows):raise ValidationError('bounded unique complete phased settled inventory required')
    return rows


def check_rental(case_raw,binding_raw):
    c=parse_settled_case(case_raw);p=parse_rental_binding(binding_raw);holding=json.loads(c['holding_source_utf8']);issues=[];rows=[];capacity=identity=None;total=0
    if p['case_source_sha256']!=sha(case_raw):issues.append('exact_settled_case_hash_mismatch')
    if p['context']!=holding['context']or p['currency']!=holding['currency']:issues.append('rental_context_or_currency_mismatch')
    if p['inventory_declared_complete']is not True:issues.append('rental_inventory_not_complete')
    for k in ('rental_scope_and_no_overlap_basis_ref','period_recognition_basis_ref'):
        if p[k]is None:issues.append(k+'_missing')
    period_sources={json.loads(r['cash_source_utf8'])['period_ref']:r for r in c['periods']}
    if [r['period_ref']for r in p['periods']]!=[r['period_ref']for r in holding['periods']]:issues.append('exact_ordered_rental_inventory_required')
    try:
        for row in p['periods']:
            source=period_sources.get(row['period_ref']);local=[]
            if source is None:issues.append(row['period_ref']+':unknown_period');continue
            cash=json.loads(source['cash_source_utf8']);noi=json.loads(source['noi_source_utf8']);run=produce_phased_rental(row['calendar_source_utf8'].encode());r=run.payload
            for k in ('context','currency','period_ref','start_date','end_date'):
                if r[k]!=cash[k]:local.append(k+'_mismatch')
            for k in ('noi','cash'):
                if row[k+'_source_sha256']!=sha(source[k+'_source_utf8'].encode()):local.append('exact_'+k+'_source_mismatch')
            incomes={v['item_id']:v for v in noi['income_rows']};target=incomes.get(row['rental_income_item_id']);others=set(incomes)-{row['rental_income_item_id']}
            if target is None or set(row['other_zero_income_item_ids'])!=others:local.append('exact_rental_and_other_income_inventory_required')
            if any(_fraction(incomes[k]['value'])!=0 for k in others):local.append('other_income_requires_another_profile')
            if r['state']!='computed_synthetic_phased_rental':local.append('rental_calendar_blocked')
            else:
                amount=_fraction(r['totals']['effective_rent'],1300);total=_bounded(total+amount)
                if target is not None and _fraction(target['value'])!=amount:local.append('rental_differs_from_NOI_income')
                if capacity is None:capacity=r['capacity'];identity=row['rental_income_item_id']
                elif not capacity_equal(capacity,r['capacity'])or identity!=row['rental_income_item_id']:local.append('capacity_or_income_identity_changed')
            issues.extend(row['period_ref']+':'+v for v in local);rows.append(dict(period_ref=row['period_ref'],calendar_run=asdict(run),blockers=local))
    except ArithmeticBudgetError:issues.append('exact_arithmetic_budget_exceeded')
    return dict(periods=rows,blockers=sorted(set(issues)),totals=None if issues else dict(effective_rent=rational(total),period_count=len(rows)))


@dataclass(frozen=True)
class PhasedSettledRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_phased_settled_output(raw):
    p=parse_source(raw);inner_raw=p['current_settled_source_utf8'].encode();inner=parse_current_settled_source(inner_raw);case_raw=inner['case_source_utf8'].encode();case=parse_settled_case(case_raw)
    parent=assemble_current_settled_case(inner_raw);result=copy.deepcopy(parent.payload);rental=check_rental(case_raw,p['rental_binding_utf8'].encode());boundary=json.loads(case['boundary_source_utf8'])
    book=parse_nominal_policy_book(p['policy_book_utf8'].encode());policies=reconcile_nominal_policy_book(boundary['plan_source_utf8'].encode(),p['policy_book_utf8'].encode())
    requirements=required_sources(raw);registry=evaluate_evidence_currency(p['registry_utf8'].encode(),p['as_of_UTC']);r=registry.payload;gate=[];policy_issues=list(policies.payload['blockers'])
    for row in boundary['periods']:
        items=json.loads(row['detail_source_utf8'])['items']
        if {v['item_id']for v in items if v['kind']=='insurance'}!={boundary['economic_item_id']}:policy_issues.append(row['period_ref']+':exact_single_insurance_item_required')
    supplied=[v['requirement']for v in r['requirements']]
    if sorted(requirements,key=lambda v:v['requirement_id'])!=sorted(supplied,key=lambda v:v['requirement_id']):gate.append('complete_exact_phased_settled_inventory_mismatch')
    if r['context']!=result['context']:gate.append('outer_registry_context_mismatch')
    if r['state']!='current_synthetic_evidence':gate.append('phased_settled_evidence_not_current')
    if inner['evaluated_as_of_UTC']!=p['as_of_UTC']:gate.append('parent_and_child_evaluation_UTC_mismatch')
    if rental['blockers']:gate.append('phased_rental_binding_blocked')
    if policy_issues:gate.append('nominal_policy_binding_blocked')
    if result['current_project_return_story']is None:gate.append('parent_current_settled_output_blocked')
    result['blockers']['gate']+=gate;result['blockers']['evidence']+=r['blockers'];result['blockers']['calculation'].update(rental=rental['blockers'],policies=sorted(set(policy_issues)))
    compatible=not result['blockers']['gate']
    if not compatible:
        for k in list(result):
            if k.startswith('current_'):result[k]=None
    result.update(component='T110',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),source_sha256=sha(raw),parent_current_input_sha256=sha(inner_raw),parent_current_run_sha256=parent.sha256,
        parent_registry_run_sha256=parent.payload['registry_run']['sha256'],registry_source_sha256=sha(p['registry_utf8'].encode()),registry_run=asdict(registry),required_sources=requirements,source_requirements_checked=len(requirements),
        rental_check=rental,nominal_policy_run=asdict(policies),current_rental_totals=rental['totals']if compatible else None,
        current_policy_totals=dict(**policies.payload['totals'],policy_count=len(book['policies']))if compatible else None,
        state='current_synthetic_phased_settled_output'if compatible else'PENDING',synthetic_complete_source_evidence_current=compatible,
        rent_or_policy_counted_as_additional_equity_cash=False,nominal_due_treated_as_payment=False)
    value=canonical(result);return PhasedSettledRun(value,digest(value))
