"""T90 supplied full-window insurance/tax cost allocations and due installments."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib
import json

from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .debt_service import _date,_fraction,rational
from .expense_cash_detail import _json,_exact
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T90-T92.md'
ASSUMPTIONS={'fractions':'supplied_not_derived_from_days','settlement':'full_within_service_window',
             'refunds_credits_fees':False,'installment_mapping':'one_to_one_same_date_and_amount','rounding':'none_exact'}


def parse_expense_schedule(raw):
    p=_json(raw)
    _exact(p,{'schema','context','currency','schedule_id','economic_item_id','kind','service_start_date','service_end_date','total_cost',
              'source_ref','allocation_basis_ref','period_inventory_declared_complete','installment_inventory_declared_complete','assumptions','allocations','installments'})
    if p['schema']!='miniuw.synthetic-expense-schedule.v1':raise ValidationError('supported expense schedule required')
    if type(p['context'])is not dict:raise ValidationError('explicit schedule context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    for k in ('currency','schedule_id','economic_item_id'):nonempty(p[k],k)
    if p['kind']not in ('insurance','property_tax'):raise ValidationError('insurance or property tax schedule required')
    if _date(p['service_start_date'])>=_date(p['service_end_date']):raise ValidationError('increasing service window required')
    _fraction(p['total_cost'])
    for k in ('source_ref','allocation_basis_ref'):
        if p[k]is not None:nonempty(p[k],k)
    for k in ('period_inventory_declared_complete','installment_inventory_declared_complete'):
        if p[k]is not None and type(p[k])is not bool:raise ValidationError('explicit completeness declaration required')
    _exact(p['assumptions'],ASSUMPTIONS)
    if any(type(p['assumptions'][k])is not type(v)or p['assumptions'][k]!=v for k,v in ASSUMPTIONS.items()):raise ValidationError('unsupported expense schedule assumptions')
    for family,maximum in [('allocations',64),('installments',128)]:
        if type(p[family])is not list or len(p[family])>maximum:raise ValidationError('bounded explicit schedule inventory required')
    ids=set()
    for row in p['allocations']:
        _exact(row,{'period_ref','start_date','end_date','fraction','source_ref'})
        nonempty(row['period_ref'],'period_ref')
        if row['period_ref']in ids:raise ValidationError('duplicate allocated period')
        ids.add(row['period_ref'])
        if _date(row['start_date'])>=_date(row['end_date']):raise ValidationError('increasing allocation period required')
        _fraction(row['fraction'])
        if row['source_ref']is not None:nonempty(row['source_ref'],'source_ref')
    ids=set();refs=set()
    for row in p['installments']:
        _exact(row,{'installment_id','due_date','amount','source_ref'})
        nonempty(row['installment_id'],'installment_id')
        if row['installment_id']in ids:raise ValidationError('duplicate installment ID')
        ids.add(row['installment_id']);_date(row['due_date']);_fraction(row['amount'])
        if row['source_ref']is not None:
            nonempty(row['source_ref'],'source_ref')
            if row['source_ref']in refs:raise ValidationError('installment source reused without split profile')
            refs.add(row['source_ref'])
    return p


@dataclass(frozen=True)
class ExpenseScheduleRun:
    payload_json:str
    sha256:str

    @property
    def payload(self):return json.loads(self.payload_json)


def produce_expense_schedule(raw):
    p=parse_expense_schedule(raw);blockers=[];rows=[];fractions=Fraction(0);expense=Fraction(0);paid=Fraction(0)
    total=_fraction(p['total_cost']);amounts=[];previous=p['service_start_date']
    if total is None or total<0:blockers.append('total_cost_missing_or_negative')
    for k in ('source_ref','allocation_basis_ref'):
        if p[k]is None:blockers.append(k+'_missing')
    for k in ('period_inventory_declared_complete','installment_inventory_declared_complete'):
        if p[k]is not True:blockers.append(k+'_not_explicitly_complete')
    if not p['allocations']:blockers.append('explicit_allocated_periods_required')
    try:
        for row in p['allocations']:
            f=_fraction(row['fraction']);issues=[];allocated=None
            if row['start_date']!=previous or row['start_date']<p['service_start_date']or row['end_date']>p['service_end_date']:issues.append('period_gap_overlap_or_outside_window')
            previous=row['end_date']
            if f is None or f<0 or f>1:issues.append('fraction_missing_or_outside_zero_one')
            else:
                fractions=_bounded(fractions+f)
                if total is not None and total>=0:allocated=_bounded(total*f);expense=_bounded(expense+allocated)
            if row['source_ref']is None:issues.append('allocation_source_missing')
            blockers.extend(row['period_ref']+':'+s for s in issues)
            rows.append(dict(**row,allocated_expense=None if allocated is None else rational(allocated),blockers=issues))
        if previous!=p['service_end_date']:blockers.append('complete_service_window_partition_required')
        if fractions!=1:blockers.append('supplied_allocation_fractions_must_sum_one')
        for row in p['installments']:
            value=_fraction(row['amount']);issues=[]
            if value is None or value<0:issues.append('installment_amount_missing_or_negative')
            else:paid=_bounded(paid+value)
            if not p['service_start_date']<=row['due_date']<p['service_end_date']:issues.append('installment_outside_half_open_service_window')
            if row['source_ref']is None:issues.append('installment_source_missing')
            blockers.extend(row['installment_id']+':'+s for s in issues);amounts.append(dict(**row,blockers=issues))
        if total is not None and paid!=total:blockers.append('complete_installment_sum_differs_from_total_cost')
    except ArithmeticBudgetError:blockers.append('exact_arithmetic_budget_exceeded')
    compatible=not blockers
    result=dict(component='T90',engine_sha256=ENGINE_SHA256,definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(raw).hexdigest(),
        context=p['context'],currency=p['currency'],schedule_id=p['schedule_id'],economic_item_id=p['economic_item_id'],kind=p['kind'],service_start_date=p['service_start_date'],service_end_date=p['service_end_date'],
        allocations=rows,installments=amounts,totals=None if not compatible else dict(expense=rational(expense),installments=rational(paid),fraction_sum=rational(fractions)),
        blockers=sorted(set(blockers)),state='computed_synthetic_full_window_expense_schedule'if compatible else'PENDING',
        coverage_adequacy_verified=False,source_or_due_date_authority_verified=False,tax_or_accounting_policy_adopted=False,bank_payments_verified=False,
        financial_publication_authorized=False,decision='PENDING',deployment_enabled=False,real_decisions_enabled=False)
    if not compatible:
        for row in result['allocations']:row['allocated_expense']=None
    text=canonical(result);return ExpenseScheduleRun(text,digest(text))
